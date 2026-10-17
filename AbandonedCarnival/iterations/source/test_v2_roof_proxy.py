"""Pure Python analytical test of the V2 roof strip proxy, no Blender import."""
import math,json
from collections import Counter
from pathlib import Path
sub=lambda a,b:tuple(x-y for x,y in zip(a,b))
dot=lambda a,b:sum(x*y for x,y in zip(a,b))
cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
vs=[]
for y in (-3.55,3.55):
 for inner in (False,True):
  for i in range(49):
   x=-1.44+2.88*i/48;vs.append((x,y,3.48+.30*math.sqrt(max(0,1-(x/1.48)**2))-(.035 if inner else 0)))
faces=[(0,1,5,4),(3,7,6,2),(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5)]
results=[]
for i in range(0,48,4):
 j=i+4;a=49;verts=[vs[k] for k in [i,j,a+j,a+i,2*a+i,2*a+j,3*a+j,3*a+i]]
 edges=Counter();volume=0;convex=True
 for f in faces:
  for u,v in zip(f,f[1:]+f[:1]):edges[tuple(sorted((u,v)))]+=1
  normal=cross(sub(verts[f[1]],verts[f[0]]),sub(verts[f[2]],verts[f[0]]))
  if max(dot(normal,sub(v,verts[f[0]])) for v in verts)>1e-8:convex=False
  for k in range(1,len(f)-1):volume+=dot(verts[f[0]],cross(verts[f[k]],verts[f[k+1]]))/6
 results.append({'strip':i//4,'closed':all(c==2 for c in edges.values()),'convex_outward':convex,'volume_m3':volume,'minimum_height_m':min(v[2] for v in verts)})
assert all(r['closed'] and r['convex_outward'] and r['volume_m3']>0 and r['minimum_height_m']>3.4 for r in results)
out={'scope':'Analytical authoring-template proxy test only; no Blender source loaded, export, or Unreal test','all_passed':True,'strips':results}
p=Path(__file__).resolve().parents[1]/'qa/v2_roof_proxy_preparation.json';p.write_text(json.dumps(out,indent=2));print('PASS twelve closed convex roof-only strips')
