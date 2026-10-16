"""Add conservative walk-test collision to a NEW copy of a verified Full map.
Dry-run by default. No mesh assets, original ISMs, project settings or gameplay
Blueprints are edited. UE execution remains untested in the build environment.
"""
from pathlib import Path
import json
import re
import uuid
from datetime import datetime, timezone
from collections import Counter
import import_supermarket_unreal as em

STRUCTURE = {
    'Site terrain', 'Raised building slab', 'Sales floor', 'Service floor',
    'Front walkway', 'Front kerb', 'Loading yard paving', 'Loading threshold',
    'West external wall', 'East external wall', 'East external wall_lintel',
    'Rear external wall', 'Shop service partition', 'Shop service partition_lintel',
    'Staff stock partition', 'Staff stock partition_lintel', 'Structural column',
    'Column scuff guard', 'Shopfront glass', 'Shopfront mullion', 'Shopfront header',
    'Entrance transom', 'Roof membrane', 'Ceiling acoustic deck', 'Entrance canopy',
    'Canopy timber soffit', 'Steel main roof beam', 'Ceiling purlin',
    'Yard portal steel jamb', 'Roller shutter housing',
}
# Only independently authored cuboids, never a compound fixture's full bounds.
FIXTURE_PIECES = {
    'Aisle 01 backing', 'Aisle 01 recessed plinth', 'Gondola timber end panel',
    'Powder coated shelf', 'Endcap shelf', 'Shelf slotted upright',
    'Stock rack upright', 'Warehouse shelf', 'Warehouse orange beam',
    'Checkout base', 'Checkout stainless rim', 'Freezer island',
    'Chilled back', 'Chilled wire shelf', 'Impulse shelf',
}
# Local center/full-size pairs measured from original authored subparts (cm).
# Deliberately omit taps, decorative trim and objects resting on furniture.
COMPOUND_BOXES = {
    'BakeryIsland': [([0,0,50],[350,250,100]), ([0,0,105],[370,270,13])],
    'ProduceIsland': [([0,0,24],[260,340,48]), ([0,0,78],[285,365,14])] +
                     [([x,y,53],[13,13,80]) for x in (-115,115) for y in (-150,150)],
    'StaffKitchenette': [([0,0,45],[280,150,90]), ([0,0,96],[300,165,12])],
    'StaffTable': [([0,0,79],[340,200,12])] +
                  [([x,y,39],[9,9,78]) for x in (-145,145) for y in (-75,75)],
}
EXCLUDED_DOORS = {'Sliding entrance glass', 'Entrance door frame', 'Door visibility strip'}
TAG = 'EvergreenWalkCollisionV1'


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate_report(contract, report):
    check(report.get('schema') == em.SCHEMA and report.get('phase') == 'full'
          and report.get('status') == 'verified_persistence',
          'A successful FULL import_report.json is required; sample/failed reports are rejected')
    check(report.get('package_fingerprint') == contract['fingerprint'],
          'Package differs from the completed full import')
    map_path = report.get('map_path', '')
    check(re.fullmatch(r'/Game/EvergreenHandoff/Full_[A-Za-z0-9_]+/Maps/L_Evergreen_full', map_path),
          'Only an original generated Evergreen Full map is accepted')
    rows = [p for g in report.get('groups', {}).values() for p in g.get('instances', [])]
    expected = {p['instance_id'] for p in contract['placements']}
    check(len(rows) == len(expected) and {p['instance_id'] for p in rows} == expected,
          'Full report placement coverage does not match the package')
    check(report.get('placement_count') == len(expected), 'Full report count mismatch')
    return map_path


def world_offset(placement, local):
    """Scale then rotate a local point using the manifest quaternion."""
    x,y,z,w = placement['quaternion_xyzw']
    v = [a*b for a,b in zip(local,placement['scale'])]
    matrix = ((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
              (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
              (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
    return [placement['location_cm'][i] + sum(matrix[i][j]*v[j] for j in range(3)) for i in range(3)]


def world_center(placement, height):
    return world_offset(placement, [0,0,height/2])


def make_plan(contract):
    boxes = []
    excluded = Counter()
    for p in contract['placements']:
        a = contract['assets'][p['asset_id']]
        name = a['name']
        if name in COMPOUND_BOXES:
            for index, (center, fullsize) in enumerate(COMPOUND_BOXES[name]):
                boxes.append({'instance_id': p['instance_id'] + '__c' + str(index),
                              'asset_id': p['asset_id'], 'name': name,
                              'center': world_offset(p, center), 'extent': [v/2 for v in fullsize],
                              'placement': p, 'block_visibility': False})
            continue
        if name not in STRUCTURE | FIXTURE_PIECES:
            excluded[name] += 1
            continue
        dims = a['bounds_cm']
        check(all(n > 0 for n in dims), 'Non-volume collider rejected: ' + name)
        check('quaternion_xyzw' in p, 'Missing quaternion: ' + p['instance_id'])
        boxes.append({'instance_id': p['instance_id'], 'asset_id': p['asset_id'],
                      'name': name, 'center': world_center(p, dims[2]),
                      'extent': [v/2 for v in dims], 'placement': p,
                      'block_visibility': name in STRUCTURE})
    check(any(b['name'] == 'Sales floor' for b in boxes), 'Sales floor missing')
    check(not any(b['name'] in EXCLUDED_DOORS for b in boxes), 'Door opening policy failed')
    return {'boxes': boxes, 'excluded': dict(sorted(excluded.items())),
            'box_count': len(boxes), 'by_name': dict(sorted(Counter(b['name'] for b in boxes).items()))}


def _transform(u, box):
    p = box['placement']
    return u.Transform(location=u.Vector(*box['center']),
                       rotation=u.Quat(*p['quaternion_xyzw']).rotator(),
                       scale=u.Vector(*p['scale']))


def _api(u):
    em._check_collision_api(u)
    for owner, methods in (
        (u.LevelEditorSubsystem, ('new_level_from_template', 'get_current_level', 'save_current_level', 'load_level', 'is_in_play_in_editor')),
        (u.BoxComponent, ('set_box_extent', 'get_unscaled_box_extent', 'set_world_transform',
                          'get_world_transform', 'get_collision_enabled',
                          'get_collision_response_to_channel', 'get_collision_object_type')),
        (u.SubobjectDataSubsystem, ('add_new_subobject', 'k2_gather_subobject_data_for_instance')),
        (u.SubobjectDataBlueprintFunctionLibrary, ('get_associated_object', 'is_actor', 'is_handle_valid', 'get_data'))):
        for method in methods:
            check(hasattr(owner, method), 'Required Unreal API unavailable: ' + owner.__name__ + '.' + method)
    for name in ('ECC_PAWN', 'ECC_WORLD_STATIC', 'ECC_VISIBILITY', 'ECC_CAMERA', 'ECC_PHYSICS_BODY'):
        check(hasattr(u.CollisionChannel, name), 'Missing CollisionChannel.' + name)


def _tagged(u):
    return [a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            if TAG in [str(t) for t in a.get_editor_property('tags')]]


def _check_original_collision(u, contract):
    # Refuse an already modified source instead of silently mixing policies.
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            tags = [str(t) for t in c.get_editor_property('component_tags')]
            if not any(t.startswith('EMGroup=') for t in tags):
                continue
            ids = [t[len('EMAsset='):] for t in tags if t.startswith('EMAsset=')]
            check(len(ids) == 1 and ids[0] in contract['assets'], 'Unrecognized generated mesh identity')
            mode = (u.CollisionEnabled.NO_COLLISION if contract['assets'][ids[0]]['collision']['strategy'] == 'none'
                    else u.CollisionEnabled.QUERY_ONLY)
            check(c.get_collision_enabled() == mode
                  and c.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN) == u.CollisionResponseType.ECR_IGNORE
                  and c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY) == u.CollisionResponseType.ECR_BLOCK,
                  'Original ISM collision was changed; use an unmodified import copy: ' + ids[0])


def _spawn(u, box):
    actor = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.Actor, u.Vector(0, 0, 0), transient=False)
    check(actor is not None, 'Could not create collision actor')
    actor.set_actor_label('EM_Walk_' + box['instance_id'])
    actor.set_editor_property('tags', [TAG, 'EMSource=' + box['instance_id']])
    sub = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    lib = u.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_instance(actor)
    parent = next((h for h in handles if lib.is_actor(lib.get_data(h))), None)
    check(parent is not None, 'No persistent actor subobject handle')
    handle, reason = sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent, new_class=u.BoxComponent))
    check(lib.is_handle_valid(handle), 'Box creation failed: ' + str(reason))
    component = lib.get_associated_object(lib.get_data(handle))
    check(isinstance(component, u.BoxComponent), 'Expected persistent BoxComponent')
    if not actor.get_editor_property('root_component'):
        actor.set_editor_property('root_component', component)
    component.set_editor_property('component_tags', [TAG, 'EMSource=' + box['instance_id']])
    component.set_mobility(u.ComponentMobility.STATIC)
    component.set_box_extent(u.Vector(*box['extent']), update_overlaps=False)
    component.set_world_transform(_transform(u, box), sweep=False, teleport=True)
    component.set_collision_object_type(u.CollisionChannel.ECC_WORLD_STATIC)
    component.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
    component.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_IGNORE)
    component.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN, u.CollisionResponseType.ECR_BLOCK)
    if box['block_visibility']:
        component.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY, u.CollisionResponseType.ECR_BLOCK)
    component.set_editor_property('hidden_in_game', True)
    component.set_editor_property('generate_overlap_events', False)
    component.set_editor_property('can_ever_affect_navigation', False)
    return component


def verify(u, plan):
    expected = {b['instance_id']: b for b in plan['boxes']}
    actual = {}
    for actor in _tagged(u):
        for c in actor.get_components_by_class(u.BoxComponent):
            ids = [str(t)[9:] for t in c.get_editor_property('component_tags') if str(t).startswith('EMSource=')]
            check(len(ids) == 1 and ids[0] not in actual, 'Duplicate/missing collider identity')
            actual[ids[0]] = c
    check(set(actual) == set(expected), 'Collider membership changed')
    for iid, c in actual.items():
        b = expected[iid]
        check(c.get_world_transform().is_near_equal(_transform(u, b), location_tolerance=0.1,
                  rotation_tolerance=0.001, scale3d_tolerance=0.0001), 'Collider transform mismatch: ' + iid)
        extent = c.get_unscaled_box_extent()
        check(all(abs(x-y) < 0.01 for x, y in zip((extent.x, extent.y, extent.z), b['extent'])), 'Extent mismatch: ' + iid)
        check(c.get_collision_enabled() == u.CollisionEnabled.QUERY_ONLY, 'Collision mode mismatch: ' + iid)
        check(c.get_collision_object_type() == u.CollisionChannel.ECC_WORLD_STATIC, 'Object type mismatch: ' + iid)
        check(c.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN) == u.CollisionResponseType.ECR_BLOCK,
              'Pawn response mismatch: ' + iid)
        visibility = u.CollisionResponseType.ECR_BLOCK if b['block_visibility'] else u.CollisionResponseType.ECR_IGNORE
        check(c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY) == visibility,
              'Visibility response mismatch: ' + iid)
        check(c.get_collision_response_to_channel(u.CollisionChannel.ECC_CAMERA) == u.CollisionResponseType.ECR_IGNORE
              and c.get_collision_response_to_channel(u.CollisionChannel.ECC_PHYSICS_BODY) == u.CollisionResponseType.ECR_IGNORE,
              'Unexpected camera/physics response: ' + iid)
        check(c.get_editor_property('hidden_in_game')
              and not c.get_editor_property('generate_overlap_events')
              and not c.get_editor_property('can_ever_affect_navigation'), 'Proxy flags changed: ' + iid)
    return {'box_count': len(actual), 'transforms_extents_and_collision_responses_checked': True}


def run(package_root, full_import_report, *, execute=False, backup_confirmed=False):
    contract = em.load_contract(package_root)
    report = json.loads(Path(full_import_report).read_text(encoding='utf-8'))
    source_map = validate_report(contract, report)
    plan = make_plan(contract)
    summary = {k: v for k, v in plan.items() if k != 'boxes'}
    summary['source_map'] = source_map
    if not execute:
        print(json.dumps(summary, indent=2))
        return summary
    check(backup_confirmed is True, 'Back up/checkpoint the project first, then pass backup_confirmed=True')
    import unreal as u
    _api(u)
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(not level.is_in_play_in_editor(), 'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
          and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Save or discard all unsaved changes first')
    current = level.get_current_level().get_path_name().split('.')[0]
    check(current == source_map, 'Open the ORIGINAL Full map from this import report first: ' + source_map)
    check(not _tagged(u), 'Existing walk colliders found; use the original Full map, not a prior collision copy')
    em.verify_scene(u, report)
    _check_original_collision(u, contract)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
    target = source_map + '_WalkTest_' + stamp
    # New UUID destination, additionally check the on-disk map without using
    # EditorAssetLibrary's level-unsupported duplicate/existence operations.
    target_file = Path(u.Paths.project_content_dir()).resolve() / (target[len('/Game/'):] + '.umap')
    check(not target_file.exists(), 'Destination already exists')
    out = Path(u.Paths.project_saved_dir()).resolve() / 'EvergreenHandoff' / ('Collision_' + stamp)
    out.mkdir(parents=True, exist_ok=False)
    report_path = out / 'collision_report.json'
    result = dict(summary, target_map=target, status='started', runtime_walk_test_passed=False)
    def write():
        report_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    write()
    try:
        check(level.new_level_from_template(target, source_map), 'Could not create walk-test map copy')
        check(level.get_current_level().get_path_name().split('.')[0] == target, 'Wrong loaded target map')
        em.verify_scene(u, report)
        check(not _tagged(u), 'Copy unexpectedly contains colliders')
        with u.ScopedEditorTransaction('Evergreen walk-test collision'):
            for box in plan['boxes']:
                _spawn(u, box)
        result['before_save'] = verify(u, plan)
        em.verify_scene(u, report)
        check(level.save_current_level(), 'Could not save collision copy')
        check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Map remains dirty; reload stopped')
        check(level.load_level(target), 'Could not reload collision copy')
        result['after_reload'] = verify(u, plan)
        em.verify_scene(u, report)
        _check_original_collision(u, contract)
        result['status'] = 'verified_collision_persistence'
        write()
        u.log('Evergreen walk-test collision saved and reloaded. Original map unchanged. Manual walk test required. Report: ' + str(report_path))
        return str(report_path)
    except Exception as exc:
        result.update(status='failed_partial_copy', error=str(exc))
        write()
        u.log_error('Collision setup stopped. Original map remains unchanged; partial COPY may remain: ' + target)
        raise
