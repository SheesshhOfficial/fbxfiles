"""Read exported logical blend; roundtrip EVERY FBX in isolated Blender scenes.
Writes QA reports and adds face-used material names to the JSON contract.
Never saves either .blend. Run with the new logical .blend as input.
"""
import bpy,json,hashlib,math
from pathlib import Path
from collections import Counter
from mathutils import Vector,Matrix,Quaternion
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'manifest.json').read_text());assets={a['asset_id']:a for a in m['assets']}
obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
byid={o['instance_id']:o for o in obs if 'instance_id' in o}
assert len(byid)==len(m['placements'])==len(obs)
meshes={o['asset_id']:o.data for o in obs}
assert len(meshes)==len(assets)
reopened_error=0.;axis_math_error=0.
for p in m['placements']:
 o=byid[p['instance_id']];mat=Matrix(p['blender_matrix']);reopened_error=max(reopened_error,max(abs(o.matrix_world[i][j]-mat[i][j]) for i in range(4) for j in range(4)))
 assert o.data.name==p['asset_id'];assert all(math.isfinite(x) for row in mat for x in row)
 q=p['quaternion_xyzw'];rot=Quaternion((q[3],q[0],q[1],q[2])).to_matrix().to_4x4();scale=Matrix.Diagonal(Vector((*p['scale'],1)));ue=Matrix.Translation(Vector(p['location_cm']))@rot@scale
 for v in list(o.data.vertices)[:3]:
  bp=mat@v.co;expected=Vector((bp.x*100,-bp.y*100,bp.z*100));local=Vector((v.co.x*100,-v.co.y*100,v.co.z*100));axis_math_error=max(axis_math_error,((ue@local)-expected).length)
assert reopened_error<.00002,reopened_error
assert axis_math_error<.05,axis_math_error
reference={}
for aid,me in meshes.items():
 me.calc_loop_triangles()
 reference[aid]={'verts':[tuple(v.co) for v in me.vertices],'tris':len(me.loop_triangles),'materials':[s.name for s in me.materials]}
 assets[aid]['used_materials']=sorted({me.materials[p.material_index].name for p in me.polygons})
# Record enriched reproducible contract before tests; importer validates used slots.
(ROOT/'manifest.json').write_text(json.dumps(m,indent=2))
newscene=bpy.data.scenes.new('VERIFY_FBX_ROUNDTRIP');newscene.unit_settings.system='METRIC';newscene.unit_settings.scale_length=1.;bpy.context.window.scene=newscene
results=[];failed=[]
for i,(aid,a) in enumerate(sorted(assets.items())):
 for o in list(newscene.objects):bpy.data.objects.remove(o,do_unlink=True)
 try:
  bpy.ops.import_scene.fbx(filepath=str(ROOT/a['fbx_path']),use_custom_normals=True,use_anim=False)
  imported=[o for o in newscene.objects if o.type=='MESH' and not o.name.startswith(('UBX_','UCX_'))]
  colliders=[o for o in newscene.objects if o.type=='MESH' and o.name.startswith(('UBX_','UCX_'))]
  assert len(imported)==1,(aid,len(imported))
  o=imported[0];me=o.data;me.calc_loop_triangles();coords=[o.matrix_world@v.co for v in me.vertices]
  lo=[min(v[j] for v in coords) for j in range(3)];hi=[max(v[j] for v in coords) for j in range(3)]
  size=[(hi[j]-lo[j])*100 for j in range(3)];delta=max(abs(size[j]-a['bounds_cm'][j]) for j in range(3))
  pivot_error=max(abs((lo[0]+hi[0])/2),abs((lo[1]+hi[1])/2),abs(lo[2]))*100
  names=[s.name.split('.00')[0] for s in me.materials] # Blender suffixes conflicts on import
  # Exact FBX material names are recovered from source node names by suffix removal only if needed.
  mats=[s.name if s.name in a['materials'] else s.name.rsplit('.',1)[0] for s in me.materials]
  assert delta<.015,(aid,'bounds',delta,size,a['bounds_cm'])
  assert pivot_error<.015,(aid,'pivot',pivot_error)
  assert len(me.loop_triangles)==reference[aid]['tris'],(aid,'triangles')
  assert mats==a['materials'],(aid,'materials',mats,a['materials'])
  assert len(colliders)==(1 if a['collision']['strategy']=='box' else 0),(aid,'collision')
  # Import may reorder vertices; sorted quantized points compare without relying on vertex IDs.
  exp=reference[aid]['verts']
  assert len(coords)==len(exp),(aid,'vertex count')
  tree=KDTree(len(exp))
  for j,v in enumerate(exp):tree.insert(Vector(v),j)
  tree.balance()
  vertex_error=max(tree.find(v)[2] for v in coords)
  assert vertex_error<.0002,(aid,'vertex geometry',vertex_error)
  results.append({'asset_id':aid,'status':'pass','bounds_error_cm':delta,'pivot_error_cm':pivot_error,'vertex_error_metres':vertex_error,'triangles':len(me.loop_triangles),'material_slots':mats,'collision_mesh_count':len(colliders)})
 except Exception as exc:
  failed.append({'asset_id':aid,'error':str(exc)})
 if i%50==0:print('ROUNDTRIP',i,'/',len(assets),'failed',len(failed),flush=True)
report={'status':'passed' if not failed else 'failed','logical_blend_mesh_objects':len(obs),'logical_blend_unique_meshes':len(meshes),'manifest_placements':len(m['placements']),'assets_checked':len(assets),'fbx_passed':len(results),'fbx_failed':failed,'max_reopen_matrix_error':reopened_error,'max_coordinate_contract_math_error_cm':axis_math_error,'unreal_tested':False,'note':'Blender FBX roundtrip and mathematical coordinate mapping only. Target Unreal import/sample validation still required.','assets':results}
(ROOT/'qa/blender_roundtrip.json').write_text(json.dumps(report,indent=2));print('VERIFY_RESULT',json.dumps({k:v for k,v in report.items() if k!='assets'}),flush=True)
if failed:raise RuntimeError('FBX roundtrip failures: '+str(len(failed)))
