"""Source-preserving exact FBX normal payload repair; no geometry/topology changes.
Run with frozen saved source loaded. Hash guard prevents mixing source versions.
"""
import bpy,json,hashlib,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
from fbx_exact_normals import replace_corner_normals
from io_scene_fbx import parse_fbx
m=json.loads((ROOT/'unreal/environment_manifest.json').read_text())
sourcehash=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();assert sourcehash==m['source_sha256']
dg=bpy.context.evaluated_depsgraph_get();results=[]
for a in m['assets']:
 normals=[]
 for name in a['source_objects']:
  o=bpy.data.objects[name];ev=o.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
  linear=o.matrix_world.to_3x3();nm=linear.inverted().transposed();ns=[(nm@n.vector).normalized() for n in me.corner_normals]
  for p in me.polygons:
   loops=list(p.loop_indices)
   if linear.determinant()>0:loops.reverse()
   for i in loops:n=ns[i];normals.append((n.x,-n.y,n.z))
  ev.to_mesh_clear()
 path=ROOT/a['fbx'];r=replace_corner_normals(path,a['asset_name'],normals);r['asset']=a['asset_name']
 tree,_=parse_fbx.parse(str(path))
 def child(e,k):return next((c for c in e.elems if c.id==k),None)
 geo=next(e for e in child(tree,b'Objects').elems if e.id==b'Geometry' and e.props[1].split(b'\x00')[0].decode()==a['asset_name'])
 layer=child(geo,b'LayerElementNormal');values=child(layer,b'Normals').props[0];idx=child(layer,b'NormalsIndex');idx=idx.props[0] if idx else range(len(normals))
 r['max_raw_normal_vector_error']=max(math.sqrt(sum((values[j*3+k]-normals[i][k])**2 for k in range(3))) for i,j in enumerate(idx))
 r['passed']=r['max_raw_normal_vector_error']==0;r['fbx_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();results.append(r)
 a['fbx_bytes']=path.stat().st_size;a['fbx_sha256']=r['fbx_sha256'];a['normal_payload']='Exact numeric transformed source corner normals; raw FBX replacement bypasses Blender packed-normal loss.'
 print('EXACT_NORMALS',a['asset_name'],r['passed'],flush=True)
m['normal_payload_method']='Raw per-corner normals retained numerically from evaluated source, inverse-transpose transformed and Y-reflected; direct FBX normal arrays bypass Blender packed custom-normal encoding.'
(ROOT/'unreal/environment_manifest.json').write_text(json.dumps(m,indent=2))
r=json.loads((ROOT/'qa/environment_export.json').read_text());r['assets']=m['assets'];r['normal_payload_method']=m['normal_payload_method'];(ROOT/'qa/environment_export.json').write_text(json.dumps(r,indent=2))
report={'asset_count':len(results),'source_sha256':sourcehash,'all_passed':all(r['passed'] for r in results),'unreal_executed':False,'geometry_changed':False,'assets':results}
(ROOT/'qa/environment_exact_normals.json').write_text(json.dumps(report,indent=2));print('ALL_PASS',report['all_passed'])
