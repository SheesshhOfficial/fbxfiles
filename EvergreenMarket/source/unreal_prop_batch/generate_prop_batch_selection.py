"""Offline original-placement audit only; never edits source or Unreal assets."""
import copy, hashlib, itertools, json, math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'evergreen_source_v2'
sys.path.insert(0,str(PACKAGE/'source/unreal'))
import setup_market_collision as ec
import setup_prop_actor_pilot as pilot
IDS=(
'EGI_0f8d6343f4f54f9d','EGI_5451cd109bab56e9',
'EGI_01eca130f35d655e','EGI_7ff75102d10dd13b',
'EGI_4c0fd92658e86b28','EGI_3ba9a0d6328c5647',
'EGI_3013a88f914ebc03','EGI_869f7db65feb4ccd',
'EGI_33de12349a45541a','EGI_9dfa86a010edad0a',
'EGI_b74ac46863b43864','EGI_4c207ecbd1ac569b',
'EGI_4fb051d8175da0d7','EGI_18fc8f491c214f5f',
'EGI_40290a2b7eaefcbc','EGI_9ca5fc6b0e622d49')

def aabb(points):
 return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}

def mesh_bounds(p,d):
 return aabb([ec.world_offset(p,[x*d[0]/2,y*d[1]/2,z*d[2]]) for x,y,z in itertools.product((-1,1),(-1,1),(0,1))])

def box_bounds(b):
 p=dict(b['placement'],location_cm=b['center'])
 return aabb([ec.world_offset(p,[s[i]*b['extent'][i] for i in range(3)]) for s in itertools.product((-1,1),repeat=3)])

def distance(point,b):
 return math.sqrt(sum(max(b['min'][i]-point[i],0,point[i]-b['max'][i])**2 for i in range(3)))

def build():
 raw=(PACKAGE/'manifest.json').read_bytes();m=json.loads(raw)
 assets={a['asset_id']:a for a in m['assets']}; ps={p['instance_id']:p for p in m['placements']}
 c={'root':str(PACKAGE),'assets':assets,'placements':m['placements']}
 collision=ec.make_plan(c); boxes=[(b,box_bounds(b)) for b in collision['boxes']]
 excluded=[]
 for name,_,_ in pilot.PILOT:
  candidates=[p for p in ps.values() if assets[p['asset_id']]['name']==name and max(abs(s-1) for s in p['scale'])<1e-6]
  excluded.append(min(candidates,key=lambda p:(p['location_cm'][2],p['instance_id']))['instance_id'])
 rows=[]
 for iid in IDS:
  p=ps[iid];a=assets[p['asset_id']]; bounds=mesh_bounds(p,a['bounds_cm']);center=[(bounds['min'][i]+bounds['max'][i])/2 for i in range(3)]
  low_endcap=a['name'].startswith('SKU_')
  if low_endcap:
   shelf=min([b for b in collision['boxes'] if b['name']=='Endcap shelf'],key=lambda b:sum((p['location_cm'][i]-b['center'][i])**2 for i in (0,1)))
   # Six authored shelf rows alternate forward/backward ends of gondolas.
   outward=1 if min(abs(center[1]-y) for y in (849,99,-651))<2 else -1
   approach=[center[0],center[1]+80*outward,center[2]]
   zone='Sales floor low endcap'; support=shelf['instance_id']
  else:
   approach=[center[0],center[1]+80,center[2]];zone='Stockroom pallet-level floor carton';support=None
  nearby=sorted([(distance(approach,bounds_),b) for b,bounds_ in boxes],key=lambda t:t[0])
  hazards=[{'instance_id':b['instance_id'],'name':b['name'],'visibility_block':b['block_visibility'],'distance_from_illustrative_probe_center_cm':round(d,4)} for d,b in nearby if d<=100]
  rows.append({'instance_id':iid,'asset_id':p['asset_id'],'asset_name':a['name'],'category':a['category'],'label':a['name']+'_'+iid[-6:],'source_placement':copy.deepcopy(p),'target_placement':copy.deepcopy(p),'canonical_bounds_cm':a['bounds_cm'],'world_aabb_cm':bounds,'bottom_top_cm':[bounds['min'][2],bounds['max'][2]],'zone':zone,'support_fixture_instance_id':support,'illustrative_approach_probe_center_cm':approach,'nearby_694_boxes_within_100cm':hazards,'accessibility_status':'offline_low_height_candidate_requires_PIE_test','accessibility_note':'Original placement preserved. Low outward-facing endcap; approach from cross-aisle.' if low_endcap else 'Original placement preserved. Low stockroom carton on pallet; adjacent cartons/pallet can obstruct approach.'})
 return {'schema':'evergreen-prop-batch-selection-v1','source_manifest_sha256':hashlib.sha256(raw).hexdigest(),'selection_count':len(rows),'original_logical_placement_count':len(ps),'original_disguise_candidate_count':sum(assets[p['asset_id']]['category']=='disguise_candidate' for p in ps.values()),'existing_collision_box_count':collision['box_count'],'excluded_pilot_instance_ids':excluded,'allowed_asset_names':sorted({r['asset_name'] for r in rows}),'canonical_scale_tolerance':1e-6,'selected':rows,'limitations':['Selection is a geometry-based review, not an Unreal runtime/reachability certification.','AABB estimates derive from bottom-center canonical bounds, original quaternion and scale; actual mesh collision and gameplay trace can differ.','Illustrative probe centers are 80 cm toward an endcap cross-aisle (floor cartons use +Y); they are diagnostic points, not approved pawn positions or navigation routes.','Nearby-box lists use point-to-world-AABB distance and a hypothetical 100 cm radius; conservative for rotated boxes and not an actual sweep, occlusion test, or first-hit proof.','The character Visibility sphere may hit fixtures, floor, neighboring props or another actor before the selected prop. Fixture collision is preserved. Confirm radius versus sweep length and trace origin in the actual character Blueprint.','Original non-selected stock can crowd each shelf. Test from aisle while aiming down; standing height alone does not guarantee a low prop can be selected.','No props moved/added and no bulk conversion of 6695 disguise-candidate placements; only these 16 existing instances are proposed.']}

if __name__=='__main__':
 result=build();out=Path(__file__).with_name('prop_batch_selection_v1.json');out.write_text(json.dumps(result,indent=2)+'\n');print(out);print('Selected',result['selection_count'],'; excluded pilot',result['excluded_pilot_instance_ids'])
