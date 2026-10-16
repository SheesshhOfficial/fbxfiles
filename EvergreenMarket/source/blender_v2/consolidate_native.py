"""Versioned, geometry-preserving source snapshot. Never saves the input blend.

blender -b ORIGINAL/Evergreen_Market_Unreal_Ready.blend --python THIS.py -- ORIGINAL PATCH POLICY OUTPUT
The explicit EG_ExportNormal corner attribute is authoritative for export. Blender
4.3's compressed display normals cannot represent every original degenerate fan.
"""
import bpy, sys, json, hashlib, math, shutil
from pathlib import Path
from collections import Counter
from mathutils import Matrix, Vector
from io_scene_fbx import parse_fbx

sys.path.insert(0,str(Path(__file__).resolve().parent))
from classify_closed_shells import analyze

NORMAL_ATTRIBUTE='EG_ExportNormal'
BOX_FACES=[(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)]

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,separators=(',',':')).encode()).hexdigest()
def child(e,name): return next(x for x in e.elems if x.id==name)
def prop(e,name): return child(e,name).props[0]
def faces(g):
    out=[]; face=[]
    for v in prop(g,b'PolygonVertexIndex'):
        face.append(v if v>=0 else -v-1)
        if v<0: out.append(face);face=[]
    assert not face
    return out
def geometry(path):
    tree,version=parse_fbx.parse(str(path))
    geos=[e for e in child(tree,b'Objects').elems if e.id==b'Geometry']
    render=next(g for g in geos if not g.props[1].startswith((b'UBX_',b'UCX_')))
    return render,geos
def vectors(a,size): return [tuple(a[i:i+size]) for i in range(0,len(a),size)]
def layers(g,kind,values,index,size):
    result=[]
    for lay in [e for e in g.elems if e.id==kind]:
        assert prop(lay,b'MappingInformationType')==b'ByPolygonVertex'
        assert prop(lay,b'ReferenceInformationType')==b'IndexToDirect'
        direct=vectors(prop(lay,values),size)
        result.append([direct[i] for i in prop(lay,index)])
    return result
def attributes(me):
    coordinates=[tuple(v.co) for v in me.vertices]
    geometry_material=[(sorted(p.vertices),p.material_index,p.use_smooth) for p in me.polygons]
    uvs=[sorted((me.loops[i].vertex_index,[tuple(u.data[i].uv) for u in me.uv_layers]) for i in p.loop_indices) for p in me.polygons]
    return {'coordinates':digest(coordinates),'geometry_material':digest(geometry_material),
            'uv_corner':digest(uvs),'slots':digest([m.name if m else None for m in me.materials]),
            'uv_names':digest([u.name for u in me.uv_layers])}
def full_transform(o): return [[float(v) for v in row] for row in o.matrix_world]
def snapshot_objects(scene):
    return {o.name:dict(type=o.type,data=o.data.name if o.data else None,matrix=full_transform(o)) for o in scene.objects}
def make_collection(name,parent):
    c=bpy.data.collections.new(name);parent.children.link(c);return c
def make_box(name,center,size,collection):
    lo=[center[i]-size[i]/2 for i in range(3)];hi=[center[i]+size[i]/2 for i in range(3)]
    vs=[(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],BOX_FACES);me.update()
    ob=bpy.data.objects.new(name,me);collection.objects.link(ob)
    ob.display_type='WIRE';ob.hide_render=True
    s=analyze(me);assert len(s)==1 and s[0]['closed'] and s[0]['signed_volume_m3']>0
    return ob
def store_text(name,data):
    t=bpy.data.texts.new(name);t.write(json.dumps(data,indent=2));return t

def build(original,patch,policy_dir,root):
    root.mkdir(parents=True,exist_ok=True);(root/'qa').mkdir(exist_ok=True);(root/'assets').mkdir(exist_ok=True)
    source=Path(bpy.data.filepath).resolve();out=root/'Evergreen_Market_Source_v2.blend'
    assert source==original/'Evergreen_Market_Unreal_Ready.blend' and source!=out and not out.exists()
    initial_hashes={str(p):sha(p) for p in [source,original/'manifest.json',patch/'patch_manifest.json']}
    manifest=json.loads((original/'manifest.json').read_text());patch_info=json.loads((patch/'patch_manifest.json').read_text())
    assert sha(original/'manifest.json')==patch_info['original_manifest_sha256']
    patched={x['asset_id']:x for x in patch_info['assets']}
    collision_file='collision_policy_v2.json'
    collision=json.loads((policy_dir/collision_file).read_text())
    lighting=json.loads((policy_dir/'neutral_light_layout_v1.json').read_text())
    assert len(manifest['assets'])==256 and len(manifest['placements'])==11316
    scene=bpy.context.scene;scene.name='Evergreen_Market_Source_v2'
    originals=snapshot_objects(scene);orig_lights=sum(o.type=='LIGHT' for o in scene.objects)
    rows=[];native_exports={};total_flipped=0
    for ai,a in enumerate(manifest['assets']):
        aid=a['asset_id'];me=bpy.data.meshes[aid];before=attributes(me)
        assert len(me.vertices)==a['vertices'] and len(me.polygons)==a['triangles']
        orig_g,_=geometry(original/a['fbx_path']);of=faces(orig_g)
        assert [tuple(v.co) for v in me.vertices]==vectors(prop(orig_g,b'Vertices'),3)
        assert [list(p.vertices) for p in me.polygons]==of
        before_shells=analyze(me);flip={pi for s in before_shells if s['eligible_for_flip'] for pi in s['polygon_indices']}
        canonical=patch/a['fbx_path'] if aid in patched else original/a['fbx_path']
        assert sha(canonical)==(patched[aid]['file_sha256'] if aid in patched else a['file_sha256'])
        g,_=geometry(canonical);cf=faces(g)
        assert cf==[list(reversed(f)) if i in flip else f for i,f in enumerate(of)]
        cn=layers(g,b'LayerElementNormal',b'Normals',b'NormalsIndex',3);cu=layers(g,b'LayerElementUV',b'UV',b'UVIndex',2)
        assert len(cn)==1 and len(cu)==len(me.uv_layers)
        mapping=[];k=0
        for f in cf:
            mapping.append({vi:k+j for j,vi in enumerate(f)});k+=len(f)
        for pi in sorted(flip):me.polygons[pi].flip()
        me.update()
        expected=[]
        for p in me.polygons:
            f=list(p.vertices);target=cf[p.index]
            assert any(f==target[j:]+target[:j] for j in range(len(f)))
            for li in p.loop_indices:
                ci=mapping[p.index][me.loops[li].vertex_index];expected.append(cn[0][ci])
                for ui,u in enumerate(me.uv_layers):u.data[li].uv=cu[ui][ci]
        attr=me.attributes.new(NORMAL_ATTRIBUTE,'FLOAT_VECTOR','CORNER')
        attr.data.foreach_set('vector',[v for n in expected for v in n])
        assert [tuple(d.vector) for d in attr.data]==expected,'Authoritative normals must be exactly representable'
        if flip:me.normals_split_custom_set(expected);me.update()
        assert attributes(me)==before,'Geometry, materials or UV associations changed'
        after_shells=analyze(me);assert len(before_shells)==len(after_shells)
        for b,s in zip(before_shells,after_shells):
            expected_volume=-b['signed_volume_m3'] if b['eligible_for_flip'] else b['signed_volume_m3']
            assert b['closed']==s['closed'] and b['consistently_oriented']==s['consistently_oriented']
            assert abs(s['signed_volume_m3']-expected_volume)<=max(1e-12,abs(expected_volume)*1e-6)
            assert not s['eligible_for_flip']
        errors=[(me.corner_normals[i].vector-Vector(n)).length for i,n in enumerate(expected)]
        degenerate_loops={li for p in me.polygons if p.area<=1e-16 for li in p.loop_indices}
        export_signature=digest([before,[tuple(p.vertices) for p in me.polygons],expected])
        me['EG_AssetId']=aid;me['EG_ExportNormalAttribute']=NORMAL_ATTRIBUTE
        me['EG_ExportSignature']=export_signature;me['EG_CanonicalFBXSHA256']=sha(canonical)
        me['EG_CollisionPolicy']=json.dumps(collision['assets'][aid],separators=(',',':'))
        shutil.copy2(canonical,root/a['fbx_path'])
        native_exports[aid]={'signature':export_signature,'fbx_path':a['fbx_path'],'file_sha256':sha(canonical)}
        row=dict(asset_id=aid,passed=True,hashes=before,vertices=len(me.vertices),polygons=len(me.polygons),
                 corrected_closed_shells=sum(s['eligible_for_flip'] for s in before_shells),flipped_polygons=len(flip),
                 open_shells_preserved=sum(not s['closed'] for s in before_shells),
                 zero_or_near_zero_closed_shells_preserved=sum(s['closed'] and abs(s['signed_volume_m3'])<=s['volume_threshold_m3'] for s in before_shells),
                 negative_eligible_shells_after=0,authoritative_corner_normals_exact=True,
                 blender_display_normal_max_vector_error=max(errors,default=0),
                 blender_display_normal_loops_over_002=sum(e>.002 for e in errors),
                 blender_display_normal_nondegenerate_loops_over_002=sum(e>.002 and i not in degenerate_loops for i,e in enumerate(errors)),
                 export_signature=export_signature)
        rows.append(row);total_flipped+=len(flip)
        if ai%25==0:print('NATIVE',ai+1,256,'flipped',total_flipped,flush=True)
    assert sum(r['corrected_closed_shells'] for r in rows)==246 and total_flipped==45192
    assert snapshot_objects(scene)==originals
    library=bpy.data.scenes.new('EG_Collision_Asset_Library');library.unit_settings.system='METRIC';library.unit_settings.scale_length=1
    legacy=make_collection('EG_Collision_LegacyQuery',library.collection)
    walking=make_collection('EG_Collision_WalkProxies',library.collection)
    placed=make_collection('EG_Collision_Walking_Placements',scene.collection);placed.hide_render=True
    placements_by_asset={a['asset_id']:[] for a in manifest['assets']}
    native_instances={o.get('instance_id'):o for o in scene.objects if o.get('instance_id')}
    for p in manifest['placements']:placements_by_asset[p['asset_id']].append(p)
    counts=Counter();proxy_records=[]
    for a in manifest['assets']:
        aid=a['asset_id'];me=bpy.data.meshes[aid];entry=collision['assets'][aid]
        if a['collision']['strategy']=='box':
            lo=[min(v.co[j] for v in me.vertices) for j in range(3)];hi=[max(v.co[j] for v in me.vertices) for j in range(3)]
            ob=make_box('UBX_'+aid+'_00',[(lo[j]+hi[j])/2 for j in range(3)],[hi[j]-lo[j] for j in range(3)],legacy)
            ob['EG_AssetId']=aid;ob['EG_Role']='legacy_query_only';ob['EG_PawnResponse']='Ignore';counts['legacy_query_prototypes']+=1
        boxes=entry.get('local_boxes_cm',[])
        for bi,box in enumerate(boxes):
            c=box['center'];size=box['full_size']
            center=[c[0]/100,-c[1]/100,c[2]/100];dimensions=[s/100 for s in size]
            companion=entry['export_roles']['walking_companion_body']['asset_id']
            ob=make_box('UBX_'+companion+'_'+str(bi).zfill(2),center,dimensions,walking)
            ob['EG_AssetId']=aid;ob['EG_CompanionAssetId']=companion;ob['EG_Role']='walking_blocker';ob['EG_PawnResponse']='Block'
            counts['walking_prototypes']+=1
            proxy_records.append(dict(asset_id=aid,companion_asset_id=companion,object_name=ob.name,box_index=bi,center_blender_metres=center,full_size_metres=dimensions))
            mask=set(entry['walking_instance_ids'])
            assert mask.issubset({p['instance_id'] for p in placements_by_asset[aid]})
            for p in placements_by_asset[aid]:
                if p['instance_id'] not in mask:continue
                po=bpy.data.objects.new('EG_WALK_'+p['instance_id']+'_'+str(bi).zfill(2),ob.data);placed.objects.link(po)
                po.matrix_world=native_instances[p['instance_id']].matrix_world.copy();po.display_type='WIRE';po.hide_render=True
                po['EG_AssetId']=aid;po['EG_InstanceId']=p['instance_id'];po['EG_Role']='walking_blocker';counts['walking_placed_boxes']+=1
    expected_boxes=sum(len(a['local_boxes_cm']) for a in collision['assets'].values())
    expected_placed=sum(len(a['local_boxes_cm'])*len(a['walking_instance_ids']) for a in collision['assets'].values())
    assert counts['legacy_query_prototypes']==111 and counts['walking_prototypes']==expected_boxes and counts['walking_placed_boxes']==expected_placed
    # Hide overlays by default; they remain available as wireframes for inspection.
    placed.hide_viewport=True
    lights=make_collection('EG_Unreal_Light_Positions',scene.collection)
    for item in lighting['lights']:
        ob=bpy.data.objects.new('UE_LIGHT_'+item['key'],None);lights.objects.link(ob)
        ob.location=item['blender_location_metres'];ob.empty_display_type='PLAIN_AXES';ob.empty_display_size=.6
        ob['EG_UnrealLight']=json.dumps(item,separators=(',',':'));ob['EG_Role']='unreal_light_position_metadata'
        ob['EG_OrientationNote']='UE rotation metadata is authoritative; this empty is a position marker, not a Blender light-axis conversion.'
    assert len(lights.objects)==11 and sum(o.type=='LIGHT' for o in scene.objects)==orig_lights
    for name,snap in originals.items():
        ob=bpy.data.objects[name];assert dict(type=ob.type,data=ob.data.name if ob.data else None,matrix=full_transform(ob))==snap
    metadata=dict(schema='evergreen-consolidated-native-v2',source_blend_sha256=initial_hashes[str(source)],
                  original_manifest_sha256=sha(original/'manifest.json'),patch_manifest_sha256=sha(patch/'patch_manifest.json'),
                  assets=native_exports,normal_attribute=NORMAL_ATTRIBUTE,collision_counts=dict(counts),
                  collision_policy_file=collision_file,
                  source_lights_preserved=orig_lights,unreal_light_position_markers=11,
                  normal_note='Exact export normals live in EG_ExportNormal. Blender compressed display normals differ on some pre-existing degenerate fans. Use the guarded canonical exporter, not an unqualified stock FBX export.',
                  runtime_note='Collision channels, Character capsule/movement and Blueprint transform logic are Unreal runtime configuration, not properties fixed by saving this blend.')
    placement_matrices={o.get('instance_id'):full_transform(o) for o in scene.objects if o.get('instance_id')}
    metadata['placement_transforms_sha256']=hashlib.sha256(json.dumps(placement_matrices,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    store_text('EG_SOURCE_MANIFEST.json',metadata);store_text('EG_COLLISION_POLICY.json',collision);store_text('EG_UNREAL_LIGHT_LAYOUT.json',lighting)
    store_text('EG_COLLISION_PROTOTYPES.json',proxy_records)
    readme=bpy.data.texts.new('READ_ME_FIRST');readme.write('Evergreen Market consolidated source v2\n\n'+metadata['normal_note']+'\n\n'+metadata['runtime_note']+'\n\nRender geometry and original placements are preserved. Collision prototypes are in the separate EG_Collision_Asset_Library scene. The walking overlay is hidden in the main scene. Original Blender lights remain; UE_LIGHT_* empties store Unreal light positions/settings without pretending watts equal lumens.\n')
    for filename in ['collision_policy_v1.json',collision_file,'neutral_light_layout_v1.json']:shutil.copy2(policy_dir/filename,root/filename)
    shutil.copy2(original/'manifest.json',root/'original_manifest.json');shutil.copy2(original/'materials.json',root/'materials.json')
    if (original/'textures').exists():shutil.copytree(original/'textures',root/'textures',dirs_exist_ok=True)
    for image in bpy.data.images:
        if image.packed_file:continue
        if image.source=='FILE' and image.filepath:
            name=Path(image.filepath).name
            if (root/'textures'/name).exists():image.filepath='//textures/'+name
    scene['EG_ConsolidationVersion']='v2';scene['EG_NormalExportAttribute']=NORMAL_ATTRIBUTE
    bpy.context.window.scene=scene;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
    metadata['blend_file']=out.name;metadata['blend_sha256']=sha(out)
    (root/'source_manifest.json').write_text(json.dumps(metadata,indent=2))
    (root/'qa/native_build.json').write_text(json.dumps(dict(passed=True,assets_verified=256,placements_preserved=11316,
            geometry_coordinates_uv_materials_exact=True,closed_shells_corrected=246,render_polygons_reversed=45192,
            collision_counts=dict(counts),original_objects_preserved=len(originals),original_lights_preserved=orig_lights,
            display_normals_are_not_export_authority=True,unreal_runtime_tested=False,assets=rows),indent=2))
    assert all(sha(Path(p))==h for p,h in initial_hashes.items())
    print('NATIVE BUILD COMPLETE',out,dict(counts),flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    build(*(Path(p).resolve() for p in args))
