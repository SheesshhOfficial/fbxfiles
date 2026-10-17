"""Validate final exported small-prop UCX meshes independently of the builder."""
import os,json,math,collections,hashlib
import numpy as np
from scipy.spatial import ConvexHull
from io_scene_fbx import parse_fbx
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
ROOT=str(PROJECT/'iterations/export')
m=json.load(open(ROOT+'/unreal/prop_placements.json'))
import hashlib
_approved=os.environ.get('CARNIVAL_V2_SOURCE_SHA256','')
if len(_approved)!=64 or m.get('source_blend_sha256')!=_approved or hashlib.sha256((PROJECT/'iterations/Cycle_10.blend').read_bytes()).hexdigest()!=_approved:raise RuntimeError('V2 validator requires matching approved Cycle10 source and manifest hash')
r=json.load(open(ROOT+'/qa/prop_collision_optimization.json'));assets={a['asset_name']:a for a in m['assets']};results=[]
def child(e,name):return next((c for c in e.elems if c.id==name),None)
for expected in r['assets']:
 a=assets[expected['asset']];path=ROOT+'/unreal/'+a['fbx'];tree,_=parse_fbx.parse(path);objects=child(tree,b'Objects');connections=child(tree,b'Connections')
 models=[e for e in objects.elems if e.id==b'Model' and e.props[1].split(b'\x00')[0].decode().startswith('UCX_')]
 assert len(models)==1
 model=models[0];ids=[e.props[1] for e in connections.elems if e.props[0]==b'OO' and e.props[2]==model.props[0]];geo=next(e for e in objects.elems if e.id==b'Geometry' and e.props[0] in ids)
 xyz=np.asarray(child(geo,b'Vertices').props[0]).reshape((-1,3));indices=child(geo,b'PolygonVertexIndex').props[0];faces=[];f=[]
 for i in indices:
  f.append(-i-1 if i<0 else i)
  if i<0:faces.append(f);f=[]
 edges=collections.Counter(tuple(sorted((face[i],face[(i+1)%len(face)]))) for face in faces for i in range(len(face)))
 volume=abs(sum(float(np.dot(xyz[face[0]],np.cross(xyz[face[i]],xyz[face[i+1]])))/6 for face in faces for i in range(1,len(face)-1)))
 ch=ConvexHull(xyz);ratio=abs(volume-ch.volume)/ch.volume
 be=max(abs(float(fun(xyz[:,i]))-expected['source_render_bounds_cm'][k][i]) for k,fun in [('min',np.min),('max',np.max)] for i in range(3))
 passed=len(models)==1 and len(xyz)<=255 and all(c==2 for c in edges.values()) and ratio<1e-5 and be<.001 and np.isfinite(xyz).all() and hashlib.sha256(open(path,'rb').read()).hexdigest()==a['fbx_sha256']
 results.append({'asset':a['asset_name'],'ucx_objects':len(models),'vertices':len(xyz),'faces':len(faces),'closed_manifold_edges':all(c==2 for c in edges.values()),'max_bounds_error_cm':be,'relative_volume_difference_from_independent_convex_hull':ratio,'passed':bool(passed)})
report={'source_blend_sha256':m['source_blend_sha256'],'all_passed':all(a['passed'] for a in results),'method':'Independent raw-FBX UCX closed-edge, finite-coordinate, exact-bounds, vertex-budget, file-hash and convex-volume validation. No Unreal execution.','assets':results}
open(ROOT+'/qa/prop_collision_proxy_fbx.json','w').write(json.dumps(report,indent=2));print('PROXY_FBX_QA',report['all_passed'],len(results))
