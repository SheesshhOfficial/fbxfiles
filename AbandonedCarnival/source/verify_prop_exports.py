"""Blender FBX roundtrip verification; not an Unreal runtime/import test."""
import bpy,json,os,math
from io_scene_fbx import parse_fbx
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d=json.load(open(ROOT+'/unreal/prop_placements.json'));results=[]
for a in d['assets']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
 bpy.ops.import_scene.fbx(filepath=ROOT+'/unreal/'+a['fbx'],use_custom_props=True)
 render=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX_')]
 collision=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('UCX_')]
 points=[o.matrix_world@v.co for o in render for v in o.data.vertices]
 bounds={'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
 error=max(abs(bounds[k][i]-a['bounds_cm'][k][i]) for k in ['min','max'] for i in range(3))
 tree,_=parse_fbx.parse(ROOT+'/unreal/'+a['fbx'])
 def child(e,name):return next((c for c in e.elems if c.id==name),None)
 objects=child(tree,b'Objects');connections=child(tree,b'Connections')
 model=next(e for e in objects.elems if e.id==b'Model' and e.props[1].split(b'\x00')[0].decode()==a['asset_name'])
 ids=[e.props[1] for e in connections.elems if e.props[0]==b'OO' and e.props[2]==model.props[0]]
 geo=next(e for e in objects.elems if e.id==b'Geometry' and e.props[0] in ids)
 layer=child(geo,b'LayerElementNormal');ns=child(layer,b'Normals').props[0];ni=child(layer,b'NormalsIndex');ni=ni.props[0] if ni else range(len(ns)//3)
 expected=[ns[i*3:i*3+3] for i in ni]
 actual=[n.vector for n in render[0].data.corner_normals]
 normal_error=max(math.sqrt(sum((x-y)**2 for x,y in zip(n,actual[i]))) for i,n in enumerate(expected)) if len(expected)==len(actual) else None
 results.append({'asset':a['asset_name'],'render_meshes':len(render),'max_roundtrip_corner_normal_vector_error':normal_error,'collision_meshes':len(collision),'expected_collision_meshes':a['collision_hulls'],'max_bounds_error_cm':error,'has_uv':all(bool(o.data.uv_layers) for o in render),'material_slot_count':sum(len(o.material_slots) for o in render),'expected_material_slot_count':len(a['materials']),'custom_prop_tag':all(bool(o.get('PropActorTag')) for o in render),'passed':normal_error is not None and normal_error<.001 and len(render)==1 and len(collision)==a['collision_hulls'] and error<.01 and all(bool(o.data.uv_layers) for o in render) and all(bool(o.get('PropActorTag')) for o in render) and sum(len(o.material_slots) for o in render)==len(a['materials'])})
report={'source_blend_sha256':d['source_blend_sha256'],'method':'Blender 4.3 FBX roundtrip in centimetre-scale scene; checks mesh counts, hull counts, cm bounds and UV presence. Not Unreal validation.','all_passed':all(r['passed'] for r in results),'assets':results,'unreal_runtime_verified':False}
open(ROOT+'/qa/prop_fbx_roundtrip.json','w').write(json.dumps(report,indent=2));print('PROP_ROUNDTRIP_DONE',report['all_passed'],len(results))
