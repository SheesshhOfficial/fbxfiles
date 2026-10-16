import bpy,json,math,statistics
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'));bpy.context.view_layer.update()
cover=list(bpy.data.collections['03_DENSE_COVER'].objects);eye=Vector(bpy.data.objects['SNIPER_EYE'].location)
def bbox(o):
 ps=[o.matrix_world@Vector(c) for c in o.bound_box];return [min(v[i] for v in ps) for i in range(3)],[max(v[i] for v in ps) for i in range(3)]
def blocks(o,p):
 inv=o.matrix_world.inverted();q=inv@Vector(p);end=inv@eye;delta=end-q;hit,loc,normal,face=o.ray_cast(q,delta.normalized());return hit and (loc-q).length<delta.length-.01
results=[]
for o in cover:
 if not o.name.startswith('Cover '):continue
 lo,hi=bbox(o);cx=(lo[0]+hi[0])/2;found=None;best=0
 for yy in [.25,.55,1.0,1.5]:
  for xx in [0]+[(lo[0]+.4+(hi[0]-lo[0]-.8)*i/12)-cx for i in range(13)]:
   p=(cx+xx,lo[1]-yy);pts=[(p[0],p[1],.15),(p[0],p[1],.95),(p[0],p[1],1.8),(p[0]-.25,p[1],1.45),(p[0]+.25,p[1],1.45)];hits=sum(blocks(o,v) for v in pts);best=max(best,hits)
   if hits==5:found=[*p,0];break
  if found:break
 results.append({'cover':o.name,'safe_sample':found,'body_rays_blocked':best,'body_rays_total':5})
# Bounding-box separations are approximations, not actual navigation gaps.
gaps=[]
for lane in [1,2,3]:
 obs=sorted([o for o in cover if o.name.startswith(f'Cover L{lane} ') or (lane==1 and o.name=='Open collapsed arch landmark')],key=lambda o:o.location.y)
 for a,b in zip(obs,obs[1:]):
  al,ah=bbox(a);bl,bh=bbox(b);dx=max(0,bl[0]-ah[0],al[0]-bh[0]);dy=max(0,bl[1]-ah[1],al[1]-bh[1]);gaps.append({'from':a.name,'to':b.name,'planar_bbox_gap_m':math.hypot(dx,dy),'centre_distance_m':(a.location-b.location).length})
# Open transition samples: visible torso count at midpoints between successive lane stations.
open_samples=[]
for lane in [1,2,3]:
 obs=sorted([o for o in cover if o.name.startswith(f'Cover L{lane} ') or (lane==1 and o.name=='Open collapsed arch landmark')],key=lambda o:o.location.y)
 for a,b in zip(obs,obs[1:]):
  p=(a.location+b.location)/2;p.z=1.45;occluded=any(blocks(o,p) for o in cover);open_samples.append({'position':list(p),'visible_to_sniper':not occluded})
report={'cover_objects_total':len(cover),'primary_stations':len(results),'fully_occluded_five_point_samples':sum(x['safe_sample'] is not None for x in results),'hiding_samples':results,'gap_method':'Planar axis-aligned bounding-box separation between consecutive primary stations in each lane; conservative footprint proxy, not collision/navigation distance.','bbox_gap_min_m':min(g['planar_bbox_gap_m'] for g in gaps),'bbox_gap_median_m':statistics.median(g['planar_bbox_gap_m'] for g in gaps),'bbox_gap_max_m':max(g['planar_bbox_gap_m'] for g in gaps),'gaps':gaps,'transition_visible_samples':sum(p['visible_to_sniper'] for p in open_samples),'transition_samples':open_samples,'warning':'Static ray samples only. No Unity physics, movement, collision, timing, balance or multiplayer testing.'}
(O/'Geometry_QA.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['hiding_samples','gaps','transition_samples']}),flush=True)
