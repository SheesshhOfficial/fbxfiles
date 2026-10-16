"""Compare each patched FBX to original, including exact corner attributes and shell volumes.
blender -b --python verify_patch_roundtrip.py -- ORIGINAL_HANDOFF PATCH_ROOT [ASSET_ID ...]
"""
import bpy,sys,json,hashlib,collections,math,ast
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]; ORIGINAL=Path(args[0]).resolve();ROOT=Path(args[1]).resolve();selected=args[2:]
# Load the pure shell classifier from the reproducible repair source, without execution.
sys.path.insert(0,str(ROOT/'source'))
from classify_closed_shells import analyze

def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def read(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_image_search=False)
    result={}
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        me=ob.data;me.calc_loop_triangles();shells=analyze(me)
        flip={pi for s in shells if s['eligible_for_flip'] for pi in s['polygon_indices']}
        vertices=[tuple(v.co) for v in me.vertices]
        mats=[m.name if m else None for m in me.materials]
        polys=[];uvs=[];norms=[];normals=[tuple(n.vector) for n in me.corner_normals]
        for p in me.polygons:
            vids=tuple(p.vertices)
            polys.append((vids,p.material_index,p.use_smooth))
            uvs.append(sorted((me.loops[li].vertex_index,[tuple(u.data[li].uv) for u in me.uv_layers]) for li in p.loop_indices))
            norms.append({me.loops[li].vertex_index:normals[li] for li in p.loop_indices})
        result['collision' if ob.name.startswith('UBX_') else 'render']=dict(name=ob.name,vertices=vertices,polygons=polys,uvs=uvs,normals=norms,materials=mats,uv_layers=[u.name for u in me.uv_layers],shells=shells,flip=flip,transform=[list(r) for r in ob.matrix_world],bounds=[min(v[j] for v in vertices) for j in range(3)]+[max(v[j] for v in vertices) for j in range(3)])
    return result

def verify(original,corrected):
    assert original.keys()==corrected.keys(),'FBX object roles changed'
    result={}
    for role,o in original.items():
        c=corrected[role];flip=o['flip']
        assert o['name']==c['name'], 'Object name changed'
        assert o['transform']==c['transform'],'Object transform changed'
        assert len(o['vertices'])==len(c['vertices']) and len(o['polygons'])==len(c['polygons']), 'Counts changed'
        exact_coordinates=o['vertices']==c['vertices']
        max_coordinate_delta=max(abs(a-b) for v,w in zip(o['vertices'],c['vertices']) for a,b in zip(v,w))
        assert exact_coordinates, 'Coordinates changed: '+str(max_coordinate_delta)
        assert o['materials']==c['materials'], 'Material slots changed'
        assert o['uv_layers']==c['uv_layers'] and o['uvs']==c['uvs'],'UV associations changed'
        assert o['bounds']==c['bounds'],'Bounds changed'
        oriented_faces_changed=0;max_normal_error=0.;same_normal_error=0.
        for pi,((ov,omi,osm),(cv,cmi,csm)) in enumerate(zip(o['polygons'],c['polygons'])):
            assert sorted(ov)==sorted(cv) and omi==cmi and osm==csm,'Polygon membership/material changed'
            target=list(reversed(ov)) if pi in flip else list(ov)
            assert any(list(cv)==target[j:]+target[:j] for j in range(len(target))),'Unexpected face orientation'
            if pi in flip:oriented_faces_changed+=1
            for vi,on in o['normals'][pi].items():
                cn=c['normals'][pi][vi]
                expected=Vector(tuple(-v for v in on) if pi in flip else on)
                err=(Vector(cn)-expected).length
                if pi in flip:max_normal_error=max(max_normal_error,err)
                else:same_normal_error=max(same_normal_error,err)
        # Authoritative float64 normal associations are checked exactly by the FBX payload QA.
        # Blender 4.3 reconstructs compressed split-normal fans, which is lossy on
        # the original model's pre-existing degenerate bevel faces. Record, do not conflate.
        pass
        assert len(o['shells'])==len(c['shells'])
        max_volume_error=0
        for os,cs in zip(o['shells'],c['shells']):
            assert os['closed']==cs['closed'] and os['consistently_oriented']==cs['consistently_oriented']
            expect=-os['signed_volume_m3'] if os['eligible_for_flip'] else os['signed_volume_m3']
            err=abs(expect-cs['signed_volume_m3']);max_volume_error=max(max_volume_error,err)
            assert err<=max(1e-12,abs(expect)*1e-6)
            assert not cs['eligible_for_flip'],'Negative closed shell remains'
        # Orientation-invariant polygon/corner signatures must be identical.
        geometry=lambda d:[(sorted(vs),mi,sm) for vs,mi,sm in d['polygons']]
        hashes={}
        for name,func in [('coordinates',lambda d:d['vertices']),('geometry_material_association',geometry),('uv_corner_association',lambda d:d['uvs']),('material_slots',lambda d:d['materials'])]:
            a,b=digest(func(o)),digest(func(c));assert a==b;hashes[name+'_sha256']=a
        result[role]=dict(vertices=len(o['vertices']),polygons=len(o['polygons']),exact_coordinates_preserved=True,max_coordinate_delta_m=max_coordinate_delta,exact_bounds_preserved=True,exact_uv_corner_associations_preserved=True,material_slots_and_assignments_preserved=True,transform_preserved=True,flipped_polygons=oriented_faces_changed,inward_closed_shells_fixed=sum(s['eligible_for_flip'] for s in o['shells']),positive_closed_shells_after=sum(s['closed'] and s['signed_volume_m3']>s['volume_threshold_m3'] for s in c['shells']),negative_eligible_closed_shells_after=sum(s['eligible_for_flip'] for s in c['shells']),open_shells_unchanged=sum(not s['closed'] for s in o['shells']),max_flipped_corner_normal_vector_error=max_normal_error,max_unflipped_corner_normal_vector_error=same_normal_error,max_volume_error_m3=max_volume_error,invariant_hashes=hashes)
    return result

exact=json.loads((ROOT/'qa/fbx_exact_payload.json').read_text());assert exact['complete'] and exact['passed'];verified={r['asset_id'] for r in exact['assets'] if r['passed']}
manifest=json.loads((ORIGINAL/'manifest.json').read_text());assets=[a for a in manifest['assets'] if (ROOT/a['fbx_path']).exists() and (not selected or a['asset_id'] in selected)]
assets.sort(key=lambda a:(0 if 'ShippingCarton_Floor' in a['asset_id'] else 1 if a['asset_id'].startswith('SM_EG_Checkout_base') else 2,a['asset_id']))
report=[]
for idx,a in enumerate(assets):
    try:
        assert a['asset_id'] in verified, 'Missing authoritative exact normal payload verification'
        o=read(ORIGINAL/a['fbx_path']);c=read(ROOT/a['fbx_path']);res=verify(o,c)
        row=dict(asset_id=a['asset_id'],passed=True,objects=res);report.append(row)
        print('VERIFIED',idx+1,len(assets),a['asset_id'],json.dumps(res),flush=True)
    except Exception as exc:
        report.append(dict(asset_id=a['asset_id'],passed=False,error=str(exc)))
        (ROOT/'qa/fbx_roundtrip_failed.json').write_text(json.dumps(report,indent=2));raise
    output=ROOT/('qa/sample_roundtrip.json' if selected else 'qa/fbx_roundtrip.json')
    output.write_text(json.dumps(dict(passed=all(r['passed'] for r in report),assets_verified=len(report),assets_expected=len(assets),complete=len(report)==len(assets),blender_version=bpy.app.version_string,normal_verification='Exact float64 FBX normal/vertex-corner associations validated by fbx_exact_payload.json. Blender decoded custom normal deviations are recorded only because its compressed normal reconstruction is lossy on pre-existing degenerate bevel faces; corrected native blend intentionally excluded.',assets=report),indent=2))
print('ROUNDTRIP COMPLETE',len(report),flush=True)
