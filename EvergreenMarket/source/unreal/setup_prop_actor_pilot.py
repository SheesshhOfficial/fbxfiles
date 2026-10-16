"""Four-prop StaticMeshActor compatibility pilot on a NEW walk-map copy.
User-described BP_propChar logic is not independently verified. No Blueprint edits.
Dry run by default; original maps and mesh assets are untouched.
"""
from pathlib import Path
import copy
import csv
import json
import re
import uuid
from datetime import datetime, timezone
import import_supermarket_unreal as em
import setup_market_collision as ec

TAG = 'EvergreenPropActorPilotV1'
PILOT = (
    ('SKU_06_can', 'TomatoCan', [-600.0, 2100.0, 0.0]),
    ('SKU_08_can', 'CoffeeCan', [-400.0, 2100.0, 0.0]),
    ('SKU_00_Carton', 'OatsCarton', [-200.0, 2100.0, 0.0]),
    ('ShippingCarton_Floor', 'ShippingBox', [0.0, 2100.0, 0.0]),
)
check = ec.check


def make_plan(contract, full, collision):
    source_full = ec.validate_report(contract, full)
    check(collision.get('status') == 'verified_collision_persistence', 'Successful collision_report.json required')
    check(collision.get('source_map') == source_full, 'Collision and full-import reports refer to different maps')
    source = collision.get('target_map', '')
    check(re.fullmatch(re.escape(source_full) + r'_WalkTest_[A-Za-z0-9_]+', source), 'Expected an original WalkTest map')
    collision_plan = ec.make_plan(contract)
    check(collision.get('box_count') == collision_plan['box_count'], 'Collision policy/count mismatch')
    lookup = {}
    for key, group in full['groups'].items():
        for p in group['instances']:
            check(p['instance_id'] not in lookup, 'Duplicate source ID')
            lookup[p['instance_id']] = (key, p)
    promoted = []
    for name, label, location in PILOT:
        aids = [a['asset_id'] for a in contract['assets'].values() if a['name'] == name]
        check(len(aids) == 1, 'Pilot mesh missing/ambiguous: ' + name)
        aid = aids[0]
        check(contract['assets'][aid]['category'] == 'disguise_candidate', 'Not a candidate: ' + name)
        candidates = [p for p in contract['placements'] if p['asset_id'] == aid
                      and max(abs(s-1.0) for s in p['scale']) < 1e-6]
        check(candidates, 'No canonical-scale source placement: ' + name)
        original = min(candidates, key=lambda p:(p['location_cm'][2],p['instance_id']))
        key, row = lookup[original['instance_id']]
        # Explicit pilot staging on the front walkway; remove the old placement.
        target = dict(original, location_cm=list(location), rotation_deg=[0.0,0.0,0.0],
                      quaternion_xyzw=[0.0,0.0,0.0,1.0], scale=[1.0,1.0,1.0])
        promoted.append({'instance_id': original['instance_id'], 'asset_id': aid, 'label': label,
                         'source_group': key, 'source_index': row['instance_index'],
                         'source_placement': original, 'target_placement': target,
                         'mesh_path': full['groups'][key]['mesh_path'],
                         'canonical_bounds_cm': contract['assets'][aid]['bounds_cm']})
    selected = {p['instance_id'] for p in promoted}
    check(len(selected) == 4, 'Pilot must contain exactly four distinct sources')
    remaining = copy.deepcopy(full)
    remaining.update(phase='pilot_remaining', status='planned', map_path=None)
    changed = []
    for key, group in remaining['groups'].items():
        before = group['instances']
        after = [p for p in before if p['instance_id'] not in selected]
        if len(after) != len(before):
            changed.append(key)
            group['instances'] = after
    remaining['placement_count'] = len(contract['placements']) - 4
    return {'source_map': source, 'promoted': promoted, 'changed_groups': changed,
            'remaining_scene': remaining, 'collision_plan': collision_plan}


def apply_rebuild(component, rows, to_transform):
    """Rebuild only an affected group; never assume remove-at-swap index rules."""
    component.clear_instances()
    indices = list(component.add_instances([to_transform(p) for p in rows],
                   should_return_indices=True, world_space=True, update_navigation=False)) if rows else []
    check(len(indices) == len(rows) and len(set(indices)) == len(rows), 'Incomplete/duplicate survivor indices')
    check(all(isinstance(i, int) and 0 <= i < len(rows) for i in indices), 'Invalid survivor indices')
    for p, index in zip(rows, indices):
        p['instance_index'] = index
    return indices


def _groups(u):
    result = {}
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            for t in c.get_editor_property('component_tags'):
                if str(t).startswith('EMGroup='):
                    key = str(t)[len('EMGroup='):]
                    check(key not in result, 'Duplicate group tag')
                    result[key] = c
    return result


def _pilot_actors(u):
    return [a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            if TAG in [str(t) for t in a.get_editor_property('tags')]]


def _material_contract(component):
    mesh = component.get_editor_property('static_mesh')
    check(mesh is not None, 'Missing mesh')
    count = component.get_num_materials()
    materials = []
    for i in range(count):
        actual, canonical = component.get_material(i), mesh.get_material(i)
        check(actual is not None and canonical is not None and actual == canonical,
              'Source has material overrides: GetStaticMesh alone would lose them')
        materials.append(canonical.get_path_name())
    return materials


def _spawn(u, p, mesh):
    actor = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.StaticMeshActor, u.Vector(0,0,0), transient=False)
    check(isinstance(actor, u.StaticMeshActor), 'Could not create StaticMeshActor')
    actor.set_actor_label('EM_PILOT_' + p['label'])
    actor.set_editor_property('tags', ['Prop', TAG, 'EMSource=' + p['instance_id']])
    actor.set_editor_property('static_mesh_replicate_movement', False)
    actor.set_editor_property('replicate_movement', False)
    actor.set_editor_property('replicates', False)
    c = actor.get_editor_property('static_mesh_component')
    c.set_mobility(u.ComponentMobility.STATIC)
    check(c.set_static_mesh(mesh), 'Could not set pilot mesh')
    c.set_world_transform(em._transform(u,p['target_placement']), sweep=False, teleport=True)
    c.set_simulate_physics(False)
    c.set_collision_object_type(u.CollisionChannel.ECC_WORLD_STATIC)
    c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
    c.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_IGNORE)
    c.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY,u.CollisionResponseType.ECR_BLOCK)
    c.set_editor_property('generate_overlap_events',False)
    c.set_editor_property('can_ever_affect_navigation',False)
    p['actor_path'] = actor.get_path_name()
    p['canonical_materials'] = _material_contract(c)
    return actor


def verify(u, plan):
    em.verify_scene(u, plan['remaining_scene'])
    ec.verify(u, plan['collision_plan'])
    expected = {p['instance_id']:p for p in plan['promoted']}
    seen = set()
    for a in _pilot_actors(u):
        tags = [str(t) for t in a.get_editor_property('tags')]
        ids = [t[len('EMSource='):] for t in tags if t.startswith('EMSource=')]
        check(isinstance(a,u.StaticMeshActor) and 'Prop' in tags and len(ids)==1, 'Pilot class/tag mismatch')
        iid = ids[0]
        check(iid in expected and iid not in seen, 'Unknown/duplicate pilot ID')
        seen.add(iid); p=expected[iid]
        c = a.get_editor_property('static_mesh_component')
        check(a.get_path_name()==p['actor_path'], 'Pilot actor identity changed after reload')
        check(c.get_editor_property('static_mesh').get_path_name()==p['mesh_path'], 'Pilot mesh mismatch')
        check(c.get_world_transform().is_near_equal(em._transform(u,p['target_placement']),
                  location_tolerance=0.1,rotation_tolerance=0.001,scale3d_tolerance=0.0001), 'Pilot transform mismatch')
        check(c.get_collision_enabled()==u.CollisionEnabled.QUERY_ONLY
              and c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY)==u.CollisionResponseType.ECR_BLOCK
              and c.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)==u.CollisionResponseType.ECR_IGNORE,
              'Pilot collision mismatch')
        check(not a.get_editor_property('replicates') and not a.get_editor_property('replicate_movement')
              and not a.get_editor_property('static_mesh_replicate_movement'), 'Unexpected replication')
        check(not c.is_simulating_physics()
              and c.get_collision_object_type()==u.CollisionChannel.ECC_WORLD_STATIC
              and c.get_editor_property('mobility')==u.ComponentMobility.STATIC, 'Pilot static/query policy changed')
        check(_material_contract(c)==p['canonical_materials'], 'Pilot materials changed')
    check(seen==set(expected),'Pilot actor count mismatch')
    remaining_ids = [p['instance_id'] for g in plan['remaining_scene']['groups'].values() for p in g['instances']]
    check(not set(remaining_ids)&set(expected),'Pilot instance was not removed')
    return {'promoted_actors':len(seen),'remaining_ism_instances':len(remaining_ids),
            'preserved_collision_boxes':plan['collision_plan']['box_count']}


def _write_lookup(path, plan):
    # New schema explicitly distinguishes ordinary actors and surviving ISMs.
    fields = ['Name','SourceKind','ComponentKey','InstanceIndex','ActorPath','StableInstanceId','AssetId','LocationX','LocationY','LocationZ']
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for key,g in plan['remaining_scene']['groups'].items():
            for p in g['instances']:
                x,y,z=p['location_cm']
                writer.writerow(dict(Name=p['instance_id'],SourceKind='ISM',ComponentKey=key,InstanceIndex=p['instance_index'],
                    ActorPath='',StableInstanceId=p['instance_id'],AssetId=p['asset_id'],LocationX=x,LocationY=y,LocationZ=z))
        for p in plan['promoted']:
            x,y,z=p['target_placement']['location_cm']
            writer.writerow(dict(Name=p['instance_id'],SourceKind='StaticMeshActor',ComponentKey='',InstanceIndex=-1,
                ActorPath=p['actor_path'],StableInstanceId=p['instance_id'],AssetId=p['asset_id'],LocationX=x,LocationY=y,LocationZ=z))


def run(package_root, full_import_report, collision_report, *, execute=False, backup_confirmed=False):
    contract=em.load_contract(package_root)
    full=json.loads(Path(full_import_report).read_text(encoding='utf-8'))
    collision=json.loads(Path(collision_report).read_text(encoding='utf-8'))
    plan=make_plan(contract,full,collision)
    summary={'source_map':plan['source_map'],'promoted':plan['promoted'],'changed_groups':plan['changed_groups'],
             'remaining_ism_instances':plan['remaining_scene']['placement_count'],'collision_boxes':plan['collision_plan']['box_count']}
    if not execute:
        print(json.dumps(summary,indent=2));return summary
    check(backup_confirmed is True,'Back up/checkpoint first and pass backup_confirmed=True')
    import unreal as u
    ec._api(u)
    for method in ('clear_instances','add_instances','modify'):
        check(hasattr(u.InstancedStaticMeshComponent,method),'Required ISM API missing: '+method)
    check(hasattr(u,'StaticMeshActor'), 'StaticMeshActor API unavailable')
    for owner, methods in ((u.StaticMesh, ('get_material',)),
                           (u.StaticMeshComponent, ('set_static_mesh','get_num_materials','get_material',
                             'set_world_transform','set_simulate_physics','is_simulating_physics'))):
        for method in methods:
            check(hasattr(owner,method), 'Required API missing: '+owner.__name__+'.'+method)
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(not level.is_in_play_in_editor(),'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
          'Save or discard all unsaved changes first')
    check(level.get_current_level().get_path_name().split('.')[0]==plan['source_map'],'Open the original verified WalkTest map first')
    check(not _pilot_actors(u),'Pilot already present; start from the original WalkTest map')
    em.verify_scene(u,full);ec.verify(u,plan['collision_plan']);ec._check_original_collision(u,contract)
    groups=_groups(u)
    for p in plan['promoted']:
        c=groups[p['source_group']]
        check(c.get_editor_property('num_custom_data_floats') == 0, 'Modified per-instance custom data would be lost; use the original generated WalkTest map')
        _material_contract(c)
        check(u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_simple_collision_count(c.get_editor_property('static_mesh'))>0,
              'Pilot mesh has no simple query collision')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    target=plan['source_map']+'_PropPilot_'+stamp
    check(not (Path(u.Paths.project_content_dir()).resolve()/(target[len('/Game/'):]+'.umap')).exists(),'Destination exists')
    output=Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff'/('PropPilot_'+stamp)
    output.mkdir(parents=True,exist_ok=False)
    result=dict(schema='evergreen-prop-actor-pilot-v1',status='started',source_map=plan['source_map'],target_map=target,
                gameplay_verified=False,blueprint_modified=False,package_fingerprint=contract['fingerprint'])
    path=output/'prop_pilot_report.json'
    def save_report():
        result['plan']=plan
        path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    save_report()
    try:
        check(level.new_level_from_template(target,plan['source_map']),'Could not copy WalkTest map')
        check(level.get_current_level().get_path_name().split('.')[0]==target,'Wrong target map loaded')
        em.verify_scene(u,full);ec.verify(u,plan['collision_plan'])
        groups=_groups(u)
        with u.ScopedEditorTransaction('Evergreen four-prop compatibility pilot'):
            for p in plan['promoted']:
                _spawn(u,p,groups[p['source_group']].get_editor_property('static_mesh'))
            for key in plan['changed_groups']:
                c=groups[key];c.modify()
                apply_rebuild(c,plan['remaining_scene']['groups'][key]['instances'],lambda p:em._transform(u,p))
        plan['remaining_scene']['map_path']=target
        result['before_save']=verify(u,plan)
        check(level.save_current_level(),'Could not save pilot map')
        check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Map remains dirty; reload stopped')
        check(level.load_level(target),'Could not reload pilot map')
        result['after_reload']=verify(u,plan)
        ec._check_original_collision(u,contract)
        plan['remaining_scene']['status']='verified_persistence'
        _write_lookup(output/'instance_lookup_pilot.csv',plan)
        result.update(status='verified_pilot_persistence',lookup_csv=str(output/'instance_lookup_pilot.csv'))
        save_report()
        u.log('Evergreen four-prop pilot persisted. E input/trace/Blueprint/multiplayer still require testing. Report: '+str(path))
        return str(path)
    except Exception as exc:
        result.update(status='failed_partial_pilot_copy',error=str(exc));save_report()
        u.log_error('Pilot setup stopped. Original WalkTest map unchanged; partial pilot copy may remain: '+target)
        raise
