"""Build auditable source metadata; never import or modify Unreal assets."""
import argparse, collections, hashlib, json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'evergreen_publish/EvergreenMarket/source/unreal'))
import setup_market_collision as ec
import fresh_preview_setup as fp

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def local_boxes(asset):
    name=asset['name']
    if name in ec.COMPOUND_BOXES:
        return [dict(center=list(c),full_size=list(s)) for c,s in ec.COMPOUND_BOXES[name]]
    if name in ec.STRUCTURE|ec.FIXTURE_PIECES:
        d=asset['bounds_cm'];return [dict(center=[0,0,d[2]/2],full_size=d)]
    return []
def inverse_point(p,world):
    # Inverse rotation via quaternion conjugate, then inverse scale.
    delta=[world[i]-p['location_cm'][i] for i in range(3)]
    q=p['quaternion_xyzw'];r=dict(location_cm=[0,0,0],scale=[1,1,1],quaternion_xyzw=[-q[0],-q[1],-q[2],q[3]])
    rotated=ec.world_offset(r,delta)
    return [v/s for v,s in zip(rotated,p['scale'])]

def build(manifest):
    assets={a['asset_id']:a for a in manifest['assets']}
    plan=ec.make_plan(dict(assets=assets,placements=manifest['placements']))
    rows={}
    for aid,a in assets.items():
        boxes=local_boxes(a);candidate=a['category']=='disguise_candidate';legacy=a['collision']['strategy']=='box'
        row=dict(asset_id=aid,name=a['name'],placement_count=a['instance_count'],category=a['category'],
                 legacy_collision=a['collision'],legacy_ubx= ('UBX_'+aid+'_00') if legacy else None,
                 local_boxes_cm=boxes,runtime=dict(profile='Custom',enabled='QueryOnly' if (legacy or boxes) else 'NoCollision',
                     object_type='WorldStatic',default_response='Ignore',Pawn='Block' if boxes else 'Ignore',Visibility='Block' if (a['name'] in ec.STRUCTURE or legacy) else 'Ignore',physics_simulation=False))
        if boxes:
            row.update(strategy='reviewed_local_boxes',purpose='walkable_structure' if a['name'] in ec.STRUCTURE else 'fixture_clearance',
                       reason='Canonical local subparts reproduce the reviewed walking proxies; preserve gaps between separate pieces.',export_action='Replace blocking geometry with listed UBX boxes; do not combine the entire fixture bounds.')
        elif candidate:
            carton=('Carton' in a['name'])
            row.update(strategy='existing_ubx_query_then_shape_review',purpose='prop_selection',
                       reason='Selection proxy only. Character capsule fit is separate; proxy presence does not enable Pawn blocking.',
                       export_action='Retain existing UBX; verify tight fit against corrected mesh.' if carton else 'Retain legacy query UBX until shape-specific UCX decomposition passes QA. Open handles, carts, chairs and crates require separate convex pieces.',
                       shape_tightness_verified=False,proposed_geometry='tight_box' if carton else 'geometry_derived_convex_parts')
        elif a['name'] in ec.EXCLUDED_DOORS:
            row.update(strategy='opening_opt_out',purpose='entry_clearance',reason='Static closed entrance representation must not seal the entry route; requires explicit door behavior before blocking.',export_action='Preserve existing query proxy if present; Pawn Ignore.')
        elif legacy:
            row.update(strategy='existing_ubx_query_only',purpose='scenery_query',reason='Legacy source proxy retained for trace parity, including small trim/labels. Not approved as a player obstacle.',export_action='Retain UBX for existing query behavior; no blanket BlockAll.')
        else:
            row.update(strategy='explicit_nonblocking_baseline',purpose='scenery_no_block',reason='No source simple collision and outside the reviewed walking allowlist. Decorative pieces remain nonblocking; solid furniture/boundary gaps require geometry-specific review before enabling.',export_action='No generated hull by default; retain explicit opt-out metadata, review solid omitted fixtures and fence spans separately.')
        # A render mesh has ONE aggregate simple body: channel policies cannot
        # differ between its UBX shapes. Keep walking companion bodies separate.
        row['runtime'] = dict(profile='Custom', enabled='QueryOnly' if legacy else 'NoCollision', object_type='WorldStatic', default_response='Ignore', Pawn='Ignore', Visibility='Block' if legacy else 'Ignore', physics_simulation=False)
        row['export_roles'] = dict(render_query_body=dict(collection='EG_Collision_LegacyQuery', shapes='legacy_ubx' if legacy else 'none', runtime=row['runtime']),
            walking_companion_body=dict(asset_id='SM_EG_Walk_'+aid.removeprefix('SM_EG_'), ubx_name_pattern='UBX_SM_EG_Walk_'+aid.removeprefix('SM_EG_')+'_{index:02d}', collection='EG_Collision_WalkProxies', export_as='separate companion mesh/component, never append to render simple body', shapes='local_boxes_cm', enabled=bool(boxes), runtime=dict(profile='Custom', enabled='QueryOnly', object_type='WorldStatic', default_response='Ignore', Pawn='Block', Visibility='Block' if a['name'] in ec.STRUCTURE else 'Ignore', physics_simulation=False)),
            provenance=dict(collection='EG_Collision_Provenance', export_enabled=False))
        if boxes:
            row['export_action']='Export listed boxes into a separate walking companion body; preserve render query body independently. Do not fill openings with whole bounds.'
        rows[aid]=row
    checked=0
    for b in plan['boxes']:
        p=b['placement'];boxes=rows[b['asset_id']]['local_boxes_cm']
        matches=[v for v in boxes if max(abs(x-y) for x,y in zip(ec.world_offset(p,v['center']),b['center']))<1e-5 and v['full_size']==[2*x for x in b['extent']]]
        assert len(matches)==1, b['instance_id']
        recovered=inverse_point(p,b['center'])
        assert max(abs(x-y) for x,y in zip(recovered,matches[0]['center']))<0.001
        assert all(math.isfinite(s) and s>0 for s in p['scale'])
        checked+=1
    assert checked==568
    return dict(schema='evergreen-source-collision-policy-v1',status='source_metadata_and_export_plan_not_runtime_validation',
        coordinates=dict(space='canonical_asset_local',length_unit='centimetres',axis='Unreal X forward Y right Z up',pivot='bottom_center',native_blender_metres='[x/100, -y/100, z/100]',transform_order='local scale, quaternion rotation, world translation'),
        invariants=dict(asset_count=len(rows),placement_count=len(manifest['placements']),legacy_box_assets=sum(a['collision']['strategy']=='box' for a in assets.values()),legacy_none_assets=sum(a['collision']['strategy']=='none' for a in assets.values()),candidate_assets=sum(a['category']=='disguise_candidate' for a in assets.values()),candidate_placements=sum(a['instance_count'] for a in assets.values() if a['category']=='disguise_candidate'),walking_boxes_reconstructed=checked,canonical_blocker_assets=sum(bool(r['local_boxes_cm']) for r in rows.values()),canonical_blocker_boxes=sum(len(r['local_boxes_cm']) for r in rows.values())),
        assets=rows)

def lights():
    rows=[]
    for source in fp.LIGHTS:
        r=dict(source);r.update(location_cm=r.pop('location'),rotation_degrees_pitch_yaw_roll=r.pop('rotation'),scale=[1,1,1],color_linear_rgba=[1,1,1,1],mobility='Movable',cast_shadows=r['actor']=='DirectionalLight',intensity_unit='lux' if r['actor']=='DirectionalLight' else 'lumens')
        if 'radius' in r:r['attenuation_radius_cm']=r.pop('radius');r['inverse_squared_falloff']=True
        r['blender_location_metres']=[r['location_cm'][0]/100,-r['location_cm'][1]/100,r['location_cm'][2]/100]
        rows.append(r)
    return dict(schema='evergreen-neutral-light-layout-v1',purpose='neutral inspection preview, not production lighting',lights=rows,blender_note='Positions may be represented by typed empties. Do not copy Unreal lumen/lux numbers into Blender watt energy. Preserve Unreal rotation metadata; orientation conversion requires a tested local light-axis adapter.',player_start_included=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',default=str(ROOT/'supermarket_unreal_handoff/manifest.json'));parser.add_argument('--out',default=str(Path(__file__).parent));args=parser.parse_args()
    manifest=json.loads(Path(args.manifest).read_text());policy=build(manifest)
    policy['original_manifest_sha256']=sha(args.manifest)
    policy['walking_helper_sha256']=sha(ec.__file__)
    out=Path(args.out);out.mkdir(exist_ok=True,parents=True)
    for name,data in [('collision_policy_v1.json',policy),('neutral_light_layout_v1.json',lights())]:
        (out/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(policy['invariants'],indent=2))
