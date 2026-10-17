"""V2 only: source recipe versus final FBX UCX geometry. Run when scheduled."""
import os,json,hashlib,collections,sys
from pathlib import Path
import bpy,numpy as np
from scipy.spatial import ConvexHull
from mathutils import Matrix,Vector
from io_scene_fbx import parse_fbx
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'iterations/export';SOURCE=PROJECT/'iterations/Cycle_10.blend'
approved=os.environ.get('CARNIVAL_V2_SOURCE_SHA256','')
m=json.loads((ROOT/'unreal/prop_placements.json').read_text())
if len(approved)!=64 or m['source_blend_sha256']!=approved or hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=approved:raise RuntimeError('V2 source/manifest/approved hash mismatch')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare_refined_prop_collision_v2 import prepare_collision_recipes
bundle=prepare_collision_recipes();recipes={r['source_object']:r for r in bundle['actors']};assets={a['asset_name']:a for a in m['assets']}
C=Matrix.Diagonal((100.,-100.,100.));results=[]
def child(e,k):return next((c for c in e.elems if c.id==k),None)
for p in m['placements']:
 if p['source_object'] not in recipes:continue
 recipe=recipes[p['source_object']];a=assets[p['asset_name']];o=bpy.data.objects[p['source_object']];linear=C@o.matrix_world.to_3x3();path=ROOT/'unreal'/a['fbx']
 tree,_=parse_fbx.parse(str(path));objects=child(tree,b'Objects');connections=child(tree,b'Connections')
 models={e.props[1].split(b'\x00')[0].decode():e for e in objects.elems if e.id==b'Model' and e.props[1].split(b'\x00')[0].decode().startswith('UCX_')}
 hulls=[]
 for index,expected in enumerate(recipe['hulls']):
  name='UCX_'+a['asset_name']+'_'+str(index).zfill(3);model=models[name];ids=[c.props[1] for c in connections.elems if c.props[0]==b'OO' and c.props[2]==model.props[0]]
  geo=next(e for e in objects.elems if e.id==b'Geometry' and e.props[0] in ids)
  actual=np.asarray(child(geo,b'Vertices').props[0]).reshape((-1,3));want=np.asarray([tuple(linear@Vector(v)) for v in expected['vertices_local_m']]);error=float(np.max(np.abs(actual-want))) if actual.shape==want.shape else None
  faces=[];f=[]
  for i in child(geo,b'PolygonVertexIndex').props[0]:
   f.append(-i-1 if i<0 else i)
   if i<0:faces.append(f);f=[]
  expectedfaces=[list(reversed(f)) if linear.determinant()<0 else f for f in expected['faces']]
  edges=collections.Counter(tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in faces for i in range(len(f)))
  volume=abs(sum(float(np.dot(actual[f[0]],np.cross(actual[f[i]],actual[f[i+1]])))/6 for f in faces for i in range(1,len(f)-1)))
  ch=ConvexHull(actual);relative=abs(volume-ch.volume)/ch.volume
  passed=error is not None and error<1e-4 and faces==expectedfaces and all(x==2 for x in edges.values()) and relative<1e-5 and len(actual)<=255
  hulls.append({'part':expected['part'],'vertices':len(actual),'max_vertex_error_cm':error,'faces_exact':faces==expectedfaces,'closed_manifold_edges':all(x==2 for x in edges.values()),'relative_convex_volume_error':relative,'passed':passed})
 results.append({'source_object':p['source_object'],'asset_name':a['asset_name'],'expected_hulls':len(recipe['hulls']),'exported_hulls':len(models),'source_world_matrix_exact':p['source_world_matrix_blender_m']==recipe['source_world_matrix_blender_m'],'recipe_guard_qa':recipe['qa'],'hulls':hulls,'passed':len(models)==len(recipe['hulls']) and all(h['passed'] for h in hulls) and p['source_world_matrix_blender_m']==recipe['source_world_matrix_blender_m']})
eligible={o.name for o in bpy.context.scene.objects if o.type=='MESH' and o.get('PropActorTag') and not any(o.get(k) for k in ('_assembly_source','visual_replaced','render_only')) and not(o.hide_render or o.hide_viewport or o.hide_get())}
identities=eligible=={p['source_object'] for p in m['placements']} and len(m['placements'])==153
untouched=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==approved
report={'source_blend_sha256':approved,'all_passed':len(results)==19 and sum(r['exported_hulls'] for r in results)==160 and all(r['passed'] for r in results) and identities and untouched,'placed_actors':len(results),'placed_hulls':sum(r['exported_hulls'] for r in results),'all_153_actor_identities_preserved':identities,'source_untouched':untouched,'actors':results,'unreal_runtime_verified':False}
(ROOT/'qa/prop_refined_collision_fbx.json').write_text(json.dumps(report,indent=2));print('REFINED_PROP_FBX',report['all_passed'],report['placed_hulls'])
