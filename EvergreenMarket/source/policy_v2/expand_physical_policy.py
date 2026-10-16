"""Geometry-authored additions; preserves all original walking boxes verbatim."""
import json,copy,collections
from pathlib import Path
from build_policy import build,lights,ROOT,sha,ec
# Single solid authored cuboids (bounds in canonical space, never dimensions baked twice).
SOLID={
'Impulse display':'build_supermarket.py:377 solid oak checkout impulse cabinet',
'Entrance planter':'polish_details.py:59 solid concrete planter body; excludes separate foliage',
'Chilled case body':'build_supermarket.py:331 closed authored cabinet cuboid',
'Rooftop air handling unit':'polish_details.py:48 closed mechanical housing',
'Promotional island top':'polish_details.py:29-30 counter and merchandise riser cuboids',
'Bagging well':'build_supermarket.py:365 actual shallow platform above checkout',
'Rubber conveyor belt':'build_supermarket.py:360 solid belt surface, no enlarged enclosure',
'POS pedestal':'build_supermarket.py:366 solid post',
'POS monitor':'build_supermarket.py:367 rotated solid monitor housing',
'Card reader':'build_supermarket.py:370 small solid reader housing',
'Checkout scanner glass':'build_supermarket.py:364 actual scanner plate',
'Checkout lane sign':'build_supermarket.py:375 actual overhead sign body, does not extend to ground',
'Chilled header':'build_supermarket.py:343 actual cabinet top trim',
'Glass refrigerator door':'build_supermarket.py:337 closed refrigerator panel; not a passage door',
'Freezer sliding glass lid':'build_supermarket.py:350 actual horizontal closed lids',
'Service swing door bumper':'build_supermarket.py:520 side bumper only; open passage not filled',
'Impact protection':'build_supermarket.py:177 narrow existing wall scuff board',
'Notice board':'build_supermarket.py:476 solid wall board',
}
# These share canonical geometry with decorative scenery. Enable only role-matched placements.
MASKS={'Promotional feature sign':('Promotional island plinth',),'Planter soil':('Promotional island timber box',)}
def run(out=None):
 out=Path(out or Path(__file__).parent);m=json.loads((ROOT/'supermarket_unreal_handoff/manifest.json').read_text());p=build(m)
 p['original_manifest_sha256']=sha(ROOT/'supermarket_unreal_handoff/manifest.json');p['walking_helper_sha256']=sha(ec.__file__)
 original=copy.deepcopy(p); placements=collections.defaultdict(list)
 for row in m['placements']:placements[row['asset_id']].append(row)
 additions=[]
 for aid,r in p['assets'].items():
  a=next(a for a in m['assets'] if a['asset_id']==aid);name=r['name'];pp=placements[aid]
  enabled=pp if r['local_boxes_cm'] else [];new=[];reason=None
  if not r['local_boxes_cm']:
   if name in SOLID or name in MASKS or name in {'SafetyBollard','Fence post','Fence rails','Lane sign post'}:
    dims=a['bounds_cm'];new=[dict(center=[0,0,dims[2]/2],full_size=dims)]
    reason=SOLID.get(name,'Authored physical cylinder/rail enclosed by a local AABB; slim circumscribed simple proxy, not a fence-plane fill.')
    enabled=pp
    if name in MASKS:
     enabled=[x for x in pp if any(s.startswith(MASKS[name]) for s in x['source_names'])]
     reason='polish_details.py:27-28 solid promotional base role; shared decorative sign/soil placements explicitly excluded'
   elif name.startswith('StaffLocker_'):
    # Canonical pivot includes recessed doors/handle; body centre must not use whole assembly AABB.
    pivot_y=pp[0]['location_cm'][1];new=[dict(center=[0,-2935-pivot_y,105],full_size=[170,100,210])];enabled=pp
    reason='build_supermarket.py:453 closed locker carcass only; excludes handle/text protrusions'
   elif name=='BakeryWallCabinet':
    px=pp[0]['location_cm'][0]
    new=[dict(center=[-2050-px,0,52],full_size=[220,280,104])]
    new += [dict(center=[-2040-px,0,z],full_size=[200,265,7]) for z in (112,168,224)]
    new += [dict(center=[-2045-px,y,150],full_size=[220,6,290]) for y in (-140,140)]
    enabled=pp;reason='build_supermarket.py:310-320 cabinet base, three shelves and two side uprights; preserves shelf cavities, excludes loaves and top light'
   if new:
    r.update(local_boxes_cm=new,strategy='reviewed_physical_addition',purpose='physical_fixture',reason=reason,export_action='Separate walking companion body using exact local boxes and explicit instance mask.')
    r['export_roles']['walking_companion_body']['enabled']=True
    additions.append(dict(asset_id=aid,name=name,local_box_count=len(new),placement_count=len(enabled),world_box_count=len(new)*len(enabled),source_evidence=reason))
  r['walking_instance_ids']=[x['instance_id'] for x in enabled]
  r['walking_selection']='explicit_instance_ids_only'
  r['baseline_walking_boxes']=bool(original['assets'][aid]['local_boxes_cm'])
 # Exact unchanged 568 previous colliders and coverage check, including all duplicate-name assets.
 for aid,r in original['assets'].items():
  if r['local_boxes_cm']:assert p['assets'][aid]['local_boxes_cm']==r['local_boxes_cm']
 world=sum(len(r['local_boxes_cm'])*len(r['walking_instance_ids']) for r in p['assets'].values())
 p['invariants'].update(original_walking_boxes_preserved=568,additional_world_boxes=world-568,total_world_boxes=world,canonical_blocker_assets=sum(bool(r['local_boxes_cm']) for r in p['assets'].values()),canonical_blocker_boxes=sum(len(r['local_boxes_cm']) for r in p['assets'].values()))
 p['revision']='physical-coverage-v2';p['additions']=additions
 p['source_files_sha256']={n:sha(ROOT/'supermarket_delivery/source'/n) for n in ('build_supermarket.py','polish_details.py')}
 (out/'collision_policy_v2.json').write_text(json.dumps(p,indent=2)+'\n')
 (out/'physical_additions_report.json').write_text(json.dumps(dict(invariants=p['invariants'],additions=additions),indent=2)+'\n')
 return p
if __name__=='__main__':print(json.dumps(run()['invariants'],indent=2))
