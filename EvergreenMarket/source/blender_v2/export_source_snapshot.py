"""Guarded exact export of this approved source checkpoint, not a general exporter.

blender -b Evergreen_Market_Source_v2.blend --python source/blender/export_source_snapshot.py -- PACKAGE NEW_OUTPUT

All 256 native meshes and authoritative corner normals are compared to the
validated canonical FBX payloads before copying any output. Geometry, UV, normal,
material, smooth-flag or placement edits fail closed: re-baseline edited assets
instead of exporting stale stored normals. This deliberately avoids Blender's
lossy split-normal codec. Walking bodies are exported separately from query bodies.
"""
import bpy,sys,json,hashlib,shutil
from pathlib import Path
from collections import Counter
from mathutils import Matrix, Vector
from io_scene_fbx import parse_fbx
sys.path.insert(0,str(Path(__file__).resolve().parent))
from consolidate_native import sha,digest,geometry,faces,layers,prop,vectors,attributes,analyze,NORMAL_ATTRIBUTE,BOX_FACES

def verify_collision_model_names(path,expected_names):
    tree,_=parse_fbx.parse(str(path))
    objects=next(e for e in tree.elems if e.id==b'Objects')
    models={e.props[1].split(b'\x00')[0].decode():e for e in objects.elems if e.id==b'Model'}
    collision_models={n:e for n,e in models.items() if n.startswith(('UBX_','UCX_'))}
    assert set(collision_models)==set(expected_names),'Collision Model names/count mismatch: '+str(path)
    connections=next(e for e in tree.elems if e.id==b'Connections')
    links={(e.props[1],e.props[2]) for e in connections.elems if e.id==b'C' and e.props[0]==b'OO'}
    geos=[e for e in objects.elems if e.id==b'Geometry']
    for name,model in collision_models.items():
        linked=[g for g in geos if (g.props[0],model.props[0]) in links]
        assert len(linked)==1,'Each UBX Model must connect to exactly one Geometry: '+name
        assert len(vectors(prop(linked[0],b'Vertices'),3))==8 and len(faces(linked[0]))==6
    return len(collision_models)

def audit_added_physical_geometry(root,manifest,policy):
    baseline=json.loads((root/'collision_policy_v1.json').read_text())
    assets={a['asset_id']:a for a in manifest['assets']};rows=[]
    for aid,entry in policy['assets'].items():
        if not entry['local_boxes_cm'] or baseline['assets'][aid]['local_boxes_cm']:continue
        me=bpy.data.meshes[aid];a=assets[aid]
        lo=[min(v.co[j] for v in me.vertices)*100 for j in range(3)]
        hi=[max(v.co[j] for v in me.vertices)*100 for j in range(3)]
        size=[hi[j]-lo[j] for j in range(3)]
        expected_lo=[-a['bounds_cm'][0]/2,-a['bounds_cm'][1]/2,0]
        expected_hi=[a['bounds_cm'][0]/2,a['bounds_cm'][1]/2,a['bounds_cm'][2]]
        error=max(abs(x-y) for x,y in zip(lo+hi,expected_lo+expected_hi))
        assert error<.01,'Native bottom-center bounds do not match collision policy: '+aid
        max_outside=0
        for box in entry['local_boxes_cm']:
            center=[box['center'][0],-box['center'][1],box['center'][2]]
            for j in range(3):max_outside=max(max_outside,lo[j]-(center[j]-box['full_size'][j]/2),(center[j]+box['full_size'][j]/2)-hi[j])
        assert max_outside<.01,'Additional proxy exceeds its physical source bounds: '+aid
        row=dict(asset_id=aid,name=a['name'],native_min_cm=lo,native_max_cm=hi,bottom_center_bound_error_cm=error,
                 maximum_proxy_outside_source_bounds_cm=max_outside,selected_instances=len(entry['walking_instance_ids']),
                 source_component_count=a['source_component_count'])
        if a['name']=='Fence rails':
            placements=[p for p in manifest['placements'] if p['asset_id']==aid]
            assert a['source_component_count']==1 and len(placements)==3
            assert all(len(p['source_names'])==1 and p['source_names'][0].startswith('Fence rails') for p in placements)
            assert size[0]<3 and size[2]<3 and abs(size[1]-2600)<.01
            row['single_thin_rail_per_instance_verified']=True
        if a['name']=='SafetyBollard':
            shells=analyze(me);assert len(shells)==2 and a['source_component_count']==2
            bb=[]
            for shell in shells:
                vids={v for pi in shell['polygon_indices'] for v in me.polygons[pi].vertices}
                mn=[min(me.vertices[v].co[j] for v in vids)*100 for j in range(3)]
                mx=[max(me.vertices[v].co[j] for v in vids)*100 for j in range(3)]
                assert abs(mn[0]+mx[0])<.01 and abs(mn[1]+mx[1])<.01
                bb.append((mn,mx))
            assert max(x[0][2] for x in bb)<min(x[1][2] for x in bb),'Bollard pieces are separated in height'
            row['two_coaxial_overlapping_cylinder_parts_verified']=True
        rows.append(row)
    assert len(rows)==31
    return dict(passed=True,additional_assets_verified=31,bounds_tolerance_cm=.01,assets=rows)

def verify(root):
    info=json.loads((root/'source_manifest.json').read_text())
    manifest=json.loads((root/'original_manifest.json').read_text())
    assert info['schema']=='evergreen-consolidated-native-v2'
    assert Path(bpy.data.filepath).name==info['blend_file']
    render_objects=[o for o in bpy.data.objects if o.type=='MESH' and o.get('instance_id')]
    byid={o.get('instance_id'):o for o in render_objects}
    assert len(byid)==len(render_objects)==len(manifest['placements'])==11316
    matrices={iid:[list(r) for r in o.matrix_world] for iid,o in byid.items()}
    assert hashlib.sha256(json.dumps(matrices,sort_keys=True,separators=(',',':')).encode()).hexdigest()==info['placement_transforms_sha256'],'Original placement transforms changed'
    max_matrix_error=0
    for p in manifest['placements']:
        o=byid[p['instance_id']];assert o.get('asset_id')==p['asset_id'] and o.data.name==p['asset_id']
        err=max(abs(o.matrix_world[i][j]-p['blender_matrix'][i][j]) for i in range(4) for j in range(4))
        max_matrix_error=max(max_matrix_error,err);assert err<2e-5,'Manifest coordinate contract mismatch'
    result=[]
    for i,a in enumerate(manifest['assets']):
        aid=a['asset_id'];me=bpy.data.meshes[aid];rec=info['assets'][aid]
        attr=me.attributes.get(NORMAL_ATTRIBUTE);assert attr and attr.domain=='CORNER' and attr.data_type=='FLOAT_VECTOR'
        nn=[tuple(x.vector) for x in attr.data]
        signature=digest([attributes(me),[tuple(p.vertices) for p in me.polygons],nn])
        assert signature==rec['signature']==me['EG_ExportSignature'],'Stale exact-normal attributes or edited geometry: '+aid
        path=root/rec['fbx_path'];assert sha(path)==rec['file_sha256'],'Canonical FBX changed: '+aid
        verify_collision_model_names(path,['UBX_'+aid+'_00'] if a['collision']['strategy']=='box' else [])
        g,gs=geometry(path);ff=faces(g)
        assert [tuple(v.co) for v in me.vertices]==vectors(prop(g,b'Vertices'),3)
        ns=layers(g,b'LayerElementNormal',b'Normals',b'NormalsIndex',3)[0]
        us=layers(g,b'LayerElementUV',b'UV',b'UVIndex',2);k=0
        assert len(me.polygons)==len(ff)==a['triangles'] and len(me.vertices)==a['vertices']
        assert [m.name for m in me.materials]==a['materials']
        for p,f in zip(me.polygons,ff):
            pv=list(p.vertices);assert any(pv==f[j:]+f[:j] for j in range(len(f))),'Triangle orientation mismatch'
            corner={vi:k+j for j,vi in enumerate(f)}
            for li in p.loop_indices:
                ci=corner[me.loops[li].vertex_index]
                assert nn[li]==ns[ci],'Authoritative normals differ from validated FBX'
                for ui,u in enumerate(me.uv_layers):assert tuple(u.data[li].uv)==us[ui][ci]
            k+=len(f)
        shells=analyze(me);assert not any(s['eligible_for_flip'] for s in shells)
        result.append(dict(asset_id=aid,passed=True,coordinates_exact=True,uv_corner_associations_exact=True,
                authoritative_normals_exact=True,triangle_orientation_correct=True,materials_and_smooth_flags_preserved=True,
                closed_shells_inward=0,source_signature=signature,canonical_fbx_sha256=sha(path)))
        if i%50==0:print('SOURCE CHECK',i+1,256,flush=True)
    prototypes=bpy.data.collections['EG_Collision_WalkProxies'].objects
    legacy=bpy.data.collections['EG_Collision_LegacyQuery'].objects
    placed=bpy.data.collections['EG_Collision_Walking_Placements'].objects
    policy=json.loads((root/info['collision_policy_file']).read_text())
    expected_boxes=sum(len(a['local_boxes_cm']) for a in policy['assets'].values())
    expected_placed=sum(len(a['local_boxes_cm'])*len(a['walking_instance_ids']) for a in policy['assets'].values())
    assert len(prototypes)==expected_boxes and len(legacy)==111 and len(placed)==expected_placed
    for o in list(prototypes)+list(legacy):
        shells=analyze(o.data);assert len(shells)==1 and shells[0]['closed'] and shells[0]['signed_volume_m3']>0
        assert o.matrix_world==Matrix.Identity(4),'Collision prototype transform changed'
    # Native collision shapes are independently verified against approved source metadata.
    placement_by_asset={a['asset_id']:[] for a in manifest['assets']}
    for p in manifest['placements']:placement_by_asset[p['asset_id']].append(p)
    native_by_name={o.name:o for o in prototypes}
    placed_by_name={o.name:o for o in placed}
    for a in manifest['assets']:
        aid=a['asset_id'];entry=policy['assets'][aid]
        if a['collision']['strategy']=='box':
            render,gs=geometry(root/info['assets'][aid]['fbx_path'])
            others=[g for g in gs if g is not render];assert len(others)==1
            cg=others[0]  # Original FBX geometry is named Collision; its connected Model has the UBX name.
            native=bpy.data.objects['UBX_'+aid+'_00']
            assert [tuple(v.co) for v in native.data.vertices]==vectors(prop(cg,b'Vertices'),3)
            assert [list(p.vertices) for p in native.data.polygons]==faces(cg)
        for bi,box in enumerate(entry['local_boxes_cm']):
            role=entry['export_roles']['walking_companion_body'];name=role['ubx_name_pattern'].format(index=bi)
            ob=native_by_name[name];assert ob['EG_CompanionAssetId']==role['asset_id'] and ob['EG_AssetId']==aid
            center=[box['center'][0]/100,-box['center'][1]/100,box['center'][2]/100]
            size=[v/100 for v in box['full_size']]
            lo=[center[j]-size[j]/2 for j in range(3)];hi=[center[j]+size[j]/2 for j in range(3)]
            expected=[(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
            assert [tuple(v.co) for v in ob.data.vertices]==[tuple(Vector(v)) for v in expected],'Walking prototype coordinates edited'
            assert [tuple(p.vertices) for p in ob.data.polygons]==BOX_FACES
            for p in placement_by_asset[aid]:
                if p['instance_id'] not in set(entry['walking_instance_ids']):continue
                po=placed_by_name['EG_WALK_'+p['instance_id']+'_'+str(bi).zfill(2)]
                # Hidden collections are not depsgraph-evaluated on reopen, so world matrices
                # can remain identity until unhidden. Both objects are unparented; basis is authoritative.
                assert po.parent is None and byid[p['instance_id']].parent is None
                assert po.data==ob.data and po.matrix_basis==byid[p['instance_id']].matrix_basis,'Walking placement changed'
    assert len(bpy.data.collections['EG_Unreal_Light_Positions'].objects)==11
    assert sum(o.type=='LIGHT' for o in bpy.data.scenes['Evergreen_Market_Source_v2'].objects)==31
    (root/'qa/additional_physical_geometry.json').write_text(json.dumps(audit_added_physical_geometry(root,manifest,policy),indent=2))
    return info,manifest,dict(schema='evergreen-source-snapshot-verification-v2',passed=True,assets_verified=256,
            placements_verified=11316,max_placement_matrix_error=max_matrix_error,
            legacy_query_boxes=111,walking_box_prototypes=expected_boxes,walking_box_instances=expected_placed,
            authoritative_normal_attribute=NORMAL_ATTRIBUTE,authoritative_normal_max_error=0,
            original_blender_lights=31,unreal_light_position_markers=11,unreal_runtime_tested=False,assets=result)

def export_companions(root,out):
    policy=json.loads((root/'collision_policy_v2.json').read_text())
    records=[];scene=bpy.data.scenes.new('EG_Temporary_Companion_Export')
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    bpy.context.window.scene=scene
    prototypes=list(bpy.data.collections['EG_Collision_WalkProxies'].objects)
    for aid,entry in policy['assets'].items():
        boxes=entry['local_boxes_cm']
        if not boxes:continue
        for o in list(scene.objects):bpy.data.objects.remove(o,do_unlink=True)
        companion=entry['export_roles']['walking_companion_body']['asset_id']
        selected=[o for o in prototypes if o.get('EG_CompanionAssetId')==companion]
        assert len(selected)==len(boxes)
        vertices=[];polygons=[]
        for proto in selected:
            offset=len(vertices);vertices.extend(tuple(v.co) for v in proto.data.vertices)
            polygons.extend(tuple(offset+v for v in p.vertices) for p in proto.data.polygons)
        me=bpy.data.meshes.new(companion);me.from_pydata(vertices,[],polygons);me.update()
        ob=bpy.data.objects.new(companion,me);scene.collection.objects.link(ob);ob.select_set(True)
        bpy.context.view_layer.objects.active=ob
        # Linking existing prototypes avoids Blender's .001 name suffix, retaining exact UBX naming.
        for proto in selected:scene.collection.objects.link(proto);proto.select_set(True)
        path=out/'collision_assets'/f'{companion}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,
            apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='Y',axis_up='Z',
            use_space_transform=True,bake_space_transform=False,use_mesh_modifiers=True,
            mesh_smooth_type='FACE',use_tspace=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False,use_custom_props=False)
        for proto in selected:scene.collection.objects.unlink(proto)
        verify_collision_model_names(path,[proto.name for proto in selected])
        # Parse exported collision geometry independently; every box must remain outward and closed.
        g,gs=geometry(path);assert len(gs)==len(boxes)+1
        assert len(faces(g))==len(polygons)
        for exported,proto in zip([x for x in gs if x.props[1].startswith(b'UBX_')],selected):
            assert exported.props[1].split(b'\x00')[0].decode()==proto.name
            assert vectors(prop(exported,b'Vertices'),3)==[tuple(v.co) for v in proto.data.vertices]
            assert faces(exported)==[list(p.vertices) for p in proto.data.polygons]
        records.append(dict(source_asset_id=aid,asset_id=companion,fbx_path='collision_assets/'+path.name,
            file_sha256=sha(path),boxes=len(boxes),runtime=entry['export_roles']['walking_companion_body']['runtime'],
            instance_ids=entry['walking_instance_ids'],
            render_hidden_required=True,attach_same_transform_as_source_instance=True))
    assert len(records)==sum(bool(a['local_boxes_cm']) for a in policy['assets'].values())
    assert sum(x['boxes'] for x in records)==sum(len(a['local_boxes_cm']) for a in policy['assets'].values())
    return records

def main(root,out=None):
    info,manifest,qa=verify(root)
    (root/'qa/native_reopen_verification.json').write_text(json.dumps(qa,indent=2))
    if out is None:
        print('VERIFIED NATIVE CHECKPOINT',flush=True);return
    assert not out.exists(),'Choose a NEW export folder; existing data is never overwritten'
    out.mkdir(parents=True);(out/'assets').mkdir();(out/'collision_assets').mkdir();(out/'qa').mkdir()
    # Exact-byte emission is intentional after native verification, preserving every FBX layer,
    # material slot and legacy collision payload while avoiding any lossy normal re-encoding.
    for a in manifest['assets']:
        rec=info['assets'][a['asset_id']];shutil.copy2(root/rec['fbx_path'],out/rec['fbx_path'])
        a['file_sha256']=rec['file_sha256'];a['source_checkpoint_signature']=rec['signature']
    companions=export_companions(root,out)
    manifest['source_checkpoint']='Evergreen_Market_Source_v2.blend'
    manifest['source_checkpoint_schema']=info['schema'];manifest['source_blend_sha256']=sha(Path(bpy.data.filepath))
    manifest['lighting']='Original Blender lights retained; neutral Unreal layout supplied separately, with explicit units.'
    manifest['unreal_tested']=False
    for name in ['materials.json','collision_policy_v2.json','neutral_light_layout_v1.json']:shutil.copy2(root/name,out/name)
    shutil.copytree(root/'textures',out/'textures')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'walking_companions.json').write_text(json.dumps(dict(schema='evergreen-walking-companions-v1',
        assets=companions,placement_mapping='Use source instance transform for each source_asset_id. Render hidden. Separate Pawn-blocking body.',
        total_canonical_boxes=qa['walking_box_prototypes'],total_world_placements=qa['walking_box_instances'],unreal_runtime_tested=False),indent=2))
    qa['emitted_render_assets']=256;qa['exact_template_emission']=True;qa['separate_companion_assets']=len(companions)
    (out/'qa/source_export_verification.json').write_text(json.dumps(qa,indent=2))
    print('EXPORTED SOURCE CHECKPOINT',out,flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    main(Path(args[0]).resolve(),Path(args[1]).resolve() if len(args)>1 else None)
