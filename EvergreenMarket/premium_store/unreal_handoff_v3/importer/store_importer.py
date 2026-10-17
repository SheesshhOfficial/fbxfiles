"""Approved v3 all-placement reconstruction for Unreal Editor 5.8.

DEFAULT: dry-run only. Nothing happens at import. Actual Unreal execution is
UNTESTED until the user runs sample, reviews it in PIE, and explicitly approves.
No existing asset, map, Blueprint, project setting or collision profile is edited.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import secrets
from datetime import datetime, timezone
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import materials

APPROVED_SOURCE_SHA256 = 'c4abf30a478051c30e00536642416c53fefb7db4911128dbb8114c0732975519'
SCHEMA = 'premium-store-unreal-v3'
MAPPING = 'candidate_A_diag_1_minus1_1_metres_to_centimetres'
REVIEW_CHECKS = ('axis_probe_100_200_300_cm_and_handedness', 'source_layout_and_pivots',
    'all_sample_copies_individually_selectable', 'materials_labels_normal_uvs_glass',
    'shader_compile_errors_absent', 'player_capsule_floor_walls_openings',
    'e_trace_shelf_basket_chair_cart_large_prop', 'trace_reachability_first_hit_occlusion',
    'fixture_lighting_no_directional', 'spawn_and_boundary_review', 'save_close_reopen',
    'copied_prop_collision_and_capsule_clearance', 'two_client_server_multicast', 'invisible_perimeter_contains_players')
BOUNDARY_POLICY = dict(source='SCENE_SUPPORT authored perimeter markers',
    reconstruction='Four invisible perimeter barriers, plus metadata TargetPoints; source metadata preserved verbatim',
    runtime_barriers_enabled=True, engine_mesh='/Engine/BasicShapes/Cube.Cube',
    engine_mesh_modified=False, collision='QUERY_AND_PHYSICS', pawn='BLOCK', visibility='IGNORE',
    note='Explicit runtime reconstruction supersedes source metadata_only/duplicate_blocker_creation annotations without rewriting source evidence')
LIGHT_POLICY = dict(lumens_per_blender_watt=10.0, attenuation_radius_cm=1000.0,
    status='ARTISTIC_STARTING_VALUES_UNCALIBRATED', source_watts_are_not_lumens=True,
    mobility='MOVABLE', cast_shadows=True, exposure_unchanged=True)
FBX_SETTINGS = dict(convert_scene=True, convert_scene_unit=True, force_front_x_axis=False,
    import_uniform_scale=1.0, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
    combine_meshes=False, auto_generate_collision=False, one_convex_hull_per_ucx=True,
    generate_lightmap_u_vs=False, reorder_material_to_fbx_order=True, remove_degenerates=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def safe_file(root, relative):
    require(isinstance(relative, str) and relative and '\\' not in relative, 'Invalid package-relative path')
    rel = PurePosixPath(relative)
    require(not rel.is_absolute() and '..' not in rel.parts and ':' not in relative, 'Unsafe package path: ' + relative)
    result = (root / relative).resolve()
    require(root in result.parents and result.is_file(), 'Missing/outside-package file: ' + relative)
    return result


def numbers(value, size, label):
    require(isinstance(value, (tuple, list)) and len(value) == size, label + ': wrong length')
    require(all(type(x) in (int, float) and math.isfinite(x) for x in value), label + ': nonfinite/nonnumeric')
    return value


def quat_from_matrix(r):
    # Unit quaternion xyzw, representing a proper right-handed numeric matrix.
    t = sum(r[i][i] for i in range(3))
    if t > 0:
        s = math.sqrt(t + 1) * 2
        q = [(r[2][1] - r[1][2]) / s, (r[0][2] - r[2][0]) / s,
             (r[1][0] - r[0][1]) / s, .25 * s]
    else:
        i = max(range(3), key=lambda j: r[j][j]); j = (i + 1) % 3; k = (i + 2) % 3
        s = math.sqrt(max(0, 1 + r[i][i] - r[j][j] - r[k][k])) * 2
        require(s > 1e-12, 'Degenerate rotation')
        q = [0., 0., 0., 0.]; q[i] = .25 * s
        q[j] = (r[i][j] + r[j][i]) / s; q[k] = (r[i][k] + r[k][i]) / s
        q[3] = (r[k][j] - r[j][k]) / s
    norm = math.sqrt(sum(x*x for x in q))
    return [x / norm for x in q]


def source_matrix(record):
    if 'source_world_matrix_m' in record:
        m = record['source_world_matrix_m']
        require(isinstance(m, list) and len(m) == 4, 'Expected 4x4 world matrix')
        for row in m: numbers(row, 4, 'matrix row')
        require(max(abs(m[3][i] - [0, 0, 0, 1][i]) for i in range(4)) < 1e-6, 'Invalid affine matrix')
        return m
    x, y, z = [math.radians(v) for v in numbers(record.get('rotation_euler_deg', [0, 0, 0]), 3, 'rotation')]
    c, s = [math.cos(v) for v in (x, y, z)], [math.sin(v) for v in (x, y, z)]
    r = [[c[2]*c[1], c[2]*s[1]*s[0]-s[2]*c[0], c[2]*s[1]*c[0]+s[2]*s[0]],
         [s[2]*c[1], s[2]*s[1]*s[0]+c[2]*c[0], s[2]*s[1]*c[0]-c[2]*s[0]],
         [-s[1], c[1]*s[0], c[1]*c[0]]]
    scale = numbers(record.get('scale', [1, 1, 1]), 3, 'scale')
    p = numbers(record['position_m'], 3, 'position')
    return [[r[i][j] * scale[j] for j in range(3)] + [p[i]] for i in range(3)] + [[0, 0, 0, 1]]


def transform_record(record, light=False):
    m = source_matrix(record)
    scale = [math.sqrt(sum(m[i][j]**2 for i in range(3))) for j in range(3)]
    require(min(scale) > 1e-8, 'Zero scale unsupported')
    r = [[m[i][j] / scale[j] for j in range(3)] for i in range(3)]
    for i in range(3):
        for j in range(3):
            require(abs(sum(r[k][i]*r[k][j] for k in range(3)) - (i == j)) < 2e-5, 'Sheared transform unsupported')
    det = r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0])
    require(abs(det - 1) < 2e-5, 'Mirrored transform unsupported')
    a = (1, -1, 1)
    if light:
        # UE +X emission -> Blender -Z; UE +Y width -> Blender +X;
        # UE +Z height -> Blender +Y, then reflect source world Y.
        u = [[a[i]*(-r[i][2]), a[i]*r[i][0], a[i]*r[i][1]] for i in range(3)]
    else:
        u = [[a[i]*r[i][j]*a[j] for j in range(3)] for i in range(3)]
    return dict(location_cm=[a[i]*m[i][3]*100 for i in range(3)],
                quaternion_xyzw=quat_from_matrix(u), scale=[1, 1, 1] if light else scale)


def expected_bounds(asset):
    render = asset['objects'][0]
    lo, hi = render['bounds_min_m'], render['bounds_max_m']
    numbers(lo, 3, 'local minimum'); numbers(hi, 3, 'local maximum')
    return dict(min_cm=[100*lo[0], -100*hi[1], 100*lo[2]],
                max_cm=[100*hi[0], -100*lo[1], 100*hi[2]])


def destination_guard(destination):
    require(bool(re.fullmatch(r'/Game/PremiumStoreV3/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+_v[0-9]+', destination)),
            'Use a NEW /Game/PremiumStoreV3/..._vNNN destination')


def _load_export(root, folder, pinned, approved=False):
    prefix = folder.rstrip('/') + '/'
    for name in ('EXPORT_VALIDATION_MANIFEST.json', 'MATERIAL_CONTRACT.json', 'TEXTURE_UV_BINDINGS.json'):
        path = safe_file(root, prefix + name); pinned[prefix + name] = sha(path)
    doc = read(root / prefix / 'EXPORT_VALIDATION_MANIFEST.json')
    require(doc.get('schema') == 'evergreen-fbx-export-v1', 'Unsupported export schema')
    require(doc.get('source_unchanged') is True, 'Exporter source integrity did not pass')
    if approved:
        require(doc.get('source_lineage', {}).get('approved_source_sha256') == APPROVED_SOURCE_SHA256,
                'Approved v3 source hash mismatch; do not run the v1 exporter output')
    ids = set()
    for asset in doc['assets']:
        aid = asset['asset_id']; require(aid not in ids, 'Duplicate canonical asset ' + aid); ids.add(aid)
        require(asset['collision_mode'] in ('AUTHORED_SIMPLE', 'NONE'), 'Unsupported collision mode ' + aid)
        require(asset['auto_generate_collision'] is False, 'Automatic collision is forbidden')
        require(bool(asset['hulls']) == (asset['collision_mode'] == 'AUTHORED_SIMPLE'), 'UCX/collision mismatch ' + aid)
        require(not asset['eligible'] or asset['hulls'], 'Eligible asset lacks authored collision ' + aid)
        require(all(h.startswith('UCX_' + asset['mesh'] + '_') for h in asset['hulls']), 'Invalid UCX names ' + aid)
        for rel, digest in [(asset['fbx'], asset['sha256'])]:
            path = safe_file(root, prefix + rel); require(sha(path) == digest, 'FBX hash mismatch ' + rel); pinned[prefix + rel] = digest
        expected_bounds(asset)
    for im in doc['images']:
        path = safe_file(root, prefix + im['path']); require(sha(path) == im['sha256'], 'Texture hash mismatch ' + im['path']); pinned[prefix + im['path']] = im['sha256']
    # Passing source-export evidence is mandatory; it remains a Blender test.
    for name in ('FBX_ROUNDTRIP_VALIDATION.json', 'PIPELINE_RUN.json'):
        p = safe_file(root, prefix + name); pinned[prefix + name] = sha(p)
        evidence = read(p); require(evidence.get('status') == 'PASS', name + ': export validation did not pass')
        if name == 'PIPELINE_RUN.json':
            require(evidence.get('source_unchanged') is True, 'Pipeline source was changed')
            require(evidence.get('source_checksums_before') == evidence.get('source_checksums_after'), 'Pipeline source checksum drift')
            require(doc['source_sha256'] in evidence.get('source_checksums_before',{}).values(), 'Pipeline source does not match export')
            stages={r['stage']:r['returncode'] for r in evidence.get('processes',[])}
            require(stages.get('export') == 0 and stages.get('roundtrip') == 0, 'Exporter/reimport process failed')
        else:
            require(evidence.get('source_sha256') == doc['source_sha256'], 'Roundtrip source mismatch')
            require(evidence.get('assets_tested') == evidence.get('assets_passed') == len(doc['assets']), 'Roundtrip asset coverage mismatch')
            require(evidence.get('collision_hulls_tested') == sum(len(a['hulls']) for a in doc['assets']), 'Roundtrip UCX coverage mismatch')
            require(evidence.get('total_placements_preserved') == doc['total_actor_count'] and evidence.get('eligible_placements_preserved') == doc['eligible_actor_count'], 'Roundtrip placement coverage mismatch')
            tested={r['asset_id']:r for r in evidence.get('results',[])}
            require(set(tested) == {a['asset_id'] for a in doc['assets']}, 'Roundtrip individual asset rows missing')
            for a in doc['assets']: require(tested[a['asset_id']].get('passed') is True and tested[a['asset_id']].get('fbx_sha256') == a['sha256'], 'Roundtrip FBX evidence mismatch')
    require(doc.get('unit_contract', {}).get('import_uniform_scale') == 1, 'Unexpected unit scale')
    for key in ('convert_scene', 'convert_scene_unit', 'force_front_x_axis'):
        require(doc['unit_contract'].get(key) == FBX_SETTINGS[key], 'Import unit/axis settings mismatch')
    return doc


def load_package(package_root):
    root = Path(package_root).expanduser().resolve(); pinned = {}
    doc = _load_export(root, 'export', pinned, approved=True)
    probe = _load_export(root, 'qa_axis/export', pinned)
    require(len(probe['assets']) == 1 and probe['assets'][0]['asset_id'] == 'unit_axis_probe', 'Missing asymmetric probe')
    require(len(probe['assets'][0]['hulls']) == 3, 'Axis probe must contain three UCX bars')
    support_path = safe_file(root, 'export/SCENE_SUPPORT.json'); pinned['export/SCENE_SUPPORT.json'] = sha(support_path)
    support = read(support_path)
    require(support.get('schema') == 'premium-store-scene-support-v3', 'Missing v3 support schema')
    require(support.get('approved_source_sha256') == APPROVED_SOURCE_SHA256, 'Support metadata source mismatch')
    require(isinstance(support.get('boundaries'), list) and isinstance(support.get('spawn_markers'), list), 'Missing boundary/spawn arrays')
    assets = {a['asset_id']: a for a in doc['assets']}; seen = set()
    for p in doc['placements']:
        sid = p['stable_id']; require(sid not in seen, 'Duplicate stable placement ' + sid); seen.add(sid)
        require(p['asset_id'] in assets, 'Unknown asset for ' + sid)
        require(p['intended_unreal_actor_class'] == 'StaticMeshActor', 'Every placement must be StaticMeshActor')
        a = assets[p['asset_id']]
        require(p['eligible'] == a['eligible'], 'Asset/placement eligibility mismatch')
        require(('Prop' in p['tags']) == bool(a['eligible']), 'Actor Prop tag/eligibility mismatch ' + sid)
        require(not p.get('instance_material_overrides'), 'Unresolved material override ' + sid)
        transform_record(p)
    require(len(seen) == doc['total_actor_count'], 'Placement count mismatch')
    require(sum(bool(p['eligible']) for p in doc['placements']) == doc['eligible_actor_count'], 'Eligible count mismatch')
    require(len(doc['lights']) == 67, 'Expected exactly 67 fixture-light metadata rows')
    light_ids = set()
    for light in doc['lights']:
        require(light['id'] not in light_ids, 'Duplicate fixture-light ID'); light_ids.add(light['id'])
        require(light['type'] in ('AREA', 'POINT', 'SPOT') and light.get('export_to_unreal') is True and not light.get('render_only'), 'Excluded/directional light in interior list')
        require(type(light.get('energy_watts')) in (int, float) and math.isfinite(light['energy_watts']) and light['energy_watts'] >= 0, 'Missing source light energy')
        numbers(light['color_rgb'], 3, 'light color'); transform_record(light, light=True)
        if light['type'] == 'AREA':
            require(light.get('shape') in ('RECTANGLE', 'SQUARE'), 'Unsupported area light shape')
            require(min(numbers(light['size_m'], 2, 'light size')) > 0, 'Invalid area light dimensions')
    require(len({m['id'] for m in support['spawn_markers']}) == len(support['spawn_markers']), 'Duplicate spawn marker ID')
    for boundary in support['boundaries']:
        require(boundary.get('metadata_only') is True and boundary.get('duplicate_blocker_creation') is False, 'Source boundary provenance annotations changed; review runtime reconstruction policy')
        require(all(sid in seen for sid in boundary.get('placement_ids', [])), 'Boundary references missing placement')
        require(boundary.get('placement_ids'), 'Boundary lacks authored blocker placement references')
        transform_record(boundary)
        require(min(numbers(boundary['dimensions_m'],3,'boundary dimensions')) > 0,'Invalid boundary dimensions')
        numbers(boundary['centre_m'],3,'boundary centre')
    for marker in support['spawn_markers']:
        require(isinstance(marker.get('id'), str) and marker.get('kind') == 'PlayerStart', 'Expected source PlayerStart marker'); transform_record(marker)
    for p in sorted(Path(__file__).parent.glob('*.py')) + sorted(Path(__file__).parent.glob('*profiles.json')):
        pinned['importer/' + p.name] = sha(p)
    fingerprint = json_sha(pinned)
    return dict(root=root, manifest=doc, probe=probe, support=support, assets=assets,
                fingerprint=fingerprint, file_hashes=pinned)


def sample_placements(contract):
    doc, assets = contract['manifest'], contract['assets']; groups = {}
    for p in doc['placements']: groups.setdefault(p['asset_id'], []).append(p)
    required = ('main_floor', 'wall_left', 'premium_shelf_bay', 'shopping_basket', 'cafe_chair',
                'shopping_cart', 'service_counter', 'shipping_carton_large', 'crushed_tomatoes')
    require(all(a in groups for a in required), 'Required floor/wall/shelf/basket/chair/cart/large/duplicate sample asset missing')
    selected = set(required)
    for asset in doc['assets']:
        if any(b.get('normal_convention') for b in asset.get('image_uv_bindings', [])):
            selected.add(asset['asset_id']); break
    for asset in doc['assets']:
        if asset.get('optical_slot_geometry'):
            selected.add(asset['asset_id']); break
    chosen = []
    for aid in sorted(selected):
        rows = sorted(groups[aid], key=lambda p: p['stable_id'])
        if aid == 'crushed_tomatoes':
            require(len(rows) >= 3, 'At least three copies of same item required in sample'); chosen.extend(rows[:3])
        else:
            chosen.append(rows[0])
    # Include a bounded, real authored v3 sign assembly (text + nearest carrier
    # and its hardware), plus one actual refined tree variant.
    all_rows = doc['placements']
    texts = [p for p in all_rows if p.get('object_name') == 'SIGN 01  BREAKFAST']
    boards = [p for p in all_rows if re.fullmatch(r'V3_Sign_backing_[0-9]+',p.get('object_name',''))]
    trees = [p for p in all_rows if 'pine_tall_v3_variant_' in p['asset_id']]
    require(texts and boards and trees, 'Required refined sign/tree sample geometry missing')
    text = texts[0]; tp=transform_record(text)['location_cm']
    board=min(boards,key=lambda p:sum((a-b)**2 for a,b in zip(transform_record(p)['location_cm'],tp)))
    index=board['object_name'].rsplit('_',1)[1]
    hardware=re.compile(r'V3_(?:Sign_backing|Sign_brass_rule|Sign_hanger|Ceiling_anchor|Sign_top_clamp|Plaque_stud)_([0-9]+)(?:_[0-9]+)?$')
    assembly=[p for p in all_rows if (m:=hardware.fullmatch(p.get('object_name',''))) and int(m.group(1))==int(index)]
    require(len(assembly)>1,'Mounted sign sample lacks hardware')
    chosen.extend([text]+assembly+[sorted(trees,key=lambda p:p['stable_id'])[0]])
    unique={p['stable_id']:p for p in chosen}
    require(len(unique)<=40, 'Calibration sample unexpectedly expanded beyond 40 scene placements')
    return list(unique.values())


def _subset_material_plan(plan, mesh_names):
    result = copy.deepcopy(plan)
    result['slot_assignments'] = [a for a in result['slot_assignments'] if a['mesh'] in mesh_names]
    needed = {a['material_path'] for a in result['slot_assignments']}
    result['materials'] = [m for m in result['materials'] if m['asset_path'] in needed]
    needed_tex = {v['texture']['asset_path'] for m in result['materials'] for v in m['channels'].values() if v['kind'] == 'texture'}
    result['textures'] = [t for t in result['textures'] if t['asset_path'] in needed_tex]
    result['blocked_materials'] = [dict(m, uses=[a for a in m['uses'] if a['mesh'] in mesh_names]) for m in result['blocked_materials'] if any(a['mesh'] in mesh_names for a in m['uses'])]
    result['all_slots_supported'] = not result['blocked_materials']
    result['canonical_asset_count'] = len(mesh_names); result['canonical_material_slot_count'] = len(result['slot_assignments'])
    return result


def build_plan(contract, phase='sample', destination=None):
    require(phase in ('sample', 'full'), 'phase must be sample or full')
    destination = destination or '/Game/PremiumStoreV3/' + phase.title() + '_v' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + str(secrets.randbelow(1000000)).zfill(6)
    destination_guard(destination)
    doc = contract['manifest']; rows = sample_placements(contract) if phase == 'sample' else doc['placements']
    selected = {p['asset_id'] for p in rows}; assets = [a for a in doc['assets'] if a['asset_id'] in selected]
    material_plan = materials.build_plan(contract['root'] / 'export', destination + '/PBR_v001')
    full_blockers = material_plan['blocked_materials']
    if phase == 'sample': material_plan = _subset_material_plan(material_plan, {a['mesh'] for a in assets})
    probe_plan = materials.build_plan(contract['root'] / 'qa_axis/export', destination + '/ProbePBR_v001') if phase == 'sample' else None
    return dict(schema=SCHEMA, mode='DRY_RUN', phase=phase, destination=destination,
        map_path=destination + '/Maps/' + ('L_V3_CalibrationSample' if phase == 'sample' else 'L_V3_AllPlacements'),
        package_fingerprint=contract['fingerprint'], file_hashes=contract['file_hashes'],
        approved_source_sha256=APPROVED_SOURCE_SHA256, coordinate_mapping=MAPPING, fbx_settings=FBX_SETTINGS,
        assets=assets, placements=[dict(p, unreal_transform=transform_record(p)) for p in rows],
        expected_placement_count=len(rows), expected_eligible_count=sum(p['eligible'] for p in rows),
        expected_role_actor_count=len(rows)+(1 if phase=='sample' else 0)+len(doc['lights'])+len(contract['support']['spawn_markers'])+2*len(contract['support']['boundaries']),
        expected_full_placement_count=len(doc['placements']), expected_full_eligible_count=doc['eligible_actor_count'],
        actor_representation='ONE_STATIC_MESH_ACTOR_PER_PLACEMENT_NO_ISM', materials=material_plan, probe_materials=probe_plan,
        full_material_blockers=full_blockers, probe_asset=contract['probe']['assets'][0] if phase == 'sample' else None,
        lights=doc['lights'], render_only_lights_excluded=doc['render_only_lights'], light_policy=LIGHT_POLICY,
        scene_support=contract['support'], boundary_policy=BOUNDARY_POLICY, manual_checks=list(REVIEW_CHECKS), unreal_execution_tested=False,
        qualifications=['Candidate axis conversion requires asymmetric probe review before full apply.',
        'Material compilation/render parity, collision cooking, E-trace reachability, gameplay, multiplayer and performance are untested.',
        'All source placements are separate actors. Shared mesh assets are intentional. No instancing/grouping replacement.',
        '67 fixture lights use explicit uncalibrated artistic lumen scaling. No directional/sun/render-only light is spawned.',
        'Ten PlayerStarts, four boundary metadata TargetPoints and four invisible Pawn-blocking perimeter barriers are reconstructed; GameMode unchanged.'])


def dry_run(package_root, phase='sample', destination=None, output=None):
    plan = build_plan(load_package(package_root), phase, destination)
    if output: write(output, plan, exclusive=True)
    return plan


def _identity(obj):
    return obj.get_path_name().split('.')[0]


def _tag_map(actor):
    return {str(t).split('=', 1)[0]: str(t).split('=', 1)[1] for t in actor.get_editor_property('tags') if '=' in str(t)}


def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _quat(v):
    return [float(v.x), float(v.y), float(v.z), float(v.w)]


def _ue_transform(u, data):
    return u.Transform(location=u.Vector(*data['location_cm']),
        rotation=u.Quat(*data['quaternion_xyzw']).rotator(), scale=u.Vector(*data['scale']))


def _guard_api(u, plan):
    version = str(u.SystemLibrary.get_engine_version())
    require(re.match(r'^5\.8(?:\.|-)', version) is not None, 'This importer requires Unreal 5.8.x; actual version: ' + version)
    required = {
        'EditorAssetLibrary': ('does_asset_exist', 'does_directory_exist', 'list_assets', 'save_loaded_asset'),
        'EditorLoadingAndSavingUtils': ('get_dirty_map_packages', 'get_dirty_content_packages'),
        'LevelEditorSubsystem': ('new_level', 'save_current_level', 'load_level'),
        'EditorActorSubsystem': ('spawn_actor_from_class', 'set_actor_transform', 'get_all_level_actors'),
        'StaticMeshEditorSubsystem': ('get_simple_collision_count', 'get_convex_collision_count', 'get_num_uv_channels', 'get_lod_build_settings', 'set_lod_build_settings'),
        'StaticMesh': ('get_bounds', 'get_num_triangles', 'get_material', 'set_material'),
        'StaticMeshComponent': ('set_static_mesh', 'set_mobility', 'set_collision_profile_name', 'set_collision_enabled', 'set_collision_response_to_all_channels', 'set_collision_response_to_channel', 'set_collision_object_type', 'set_visibility', 'set_cast_shadow', 'get_collision_enabled', 'get_collision_response_to_channel'),
        'Actor': ('get_actor_transform', 'get_components_by_class', 'get_component_by_class', 'set_actor_label', 'set_actor_hidden_in_game', 'get_editor_property', 'set_editor_property'),
        'Texture': ('set_virtual_texture_streaming',),
        'MaterialEditingLibrary': ('create_material_expression', 'connect_material_expressions', 'connect_material_property', 'recompile_material', 'layout_material_expressions', 'get_material_expression_input_names'),
        'LightComponent': ('set_intensity', 'set_light_color'),
    }
    for cls, methods in required.items():
        target = getattr(u, cls, None); require(target is not None, 'Required API class missing: ' + cls)
        for name in methods: require(callable(getattr(target, name, None)), 'Required API method missing: ' + cls + '.' + name)
    for cls in ('FbxFactory','FbxImportUI','AssetImportTask','StaticMeshActor','InstancedStaticMeshComponent','HierarchicalInstancedStaticMeshComponent','TargetPoint','PlayerStart', 'RectLight','PointLight','SpotLight','RectLightComponent','PointLightComponent','SpotLightComponent','DirectionalLight','TextureFactory','Texture2D','BodySetup','MeshBuildSettings','Material','MaterialFactoryNew','Vector','Quat','Transform','Rotator','LinearColor','AssetToolsHelpers','MaterialExpressionTextureCoordinate','MaterialExpressionTextureSample','MaterialExpressionConstant','MaterialExpressionConstant3Vector','MaterialExpressionLinearInterpolate','MaterialExpressionNormalize'):
        require(hasattr(u, cls), 'Required API class missing: ' + cls)
    enums = dict(CollisionEnabled=['NO_COLLISION','QUERY_AND_PHYSICS'], CollisionChannel=['ECC_WORLD_STATIC','ECC_PAWN','ECC_VISIBILITY'],
        CollisionResponseType=['ECR_BLOCK','ECR_IGNORE'], ComponentMobility=['STATIC','MOVABLE'], CollisionTraceFlag=['CTF_USE_SIMPLE_AND_COMPLEX'],
        FBXImportType=['FBXIT_STATIC_MESH'], FBXNormalImportMethod=['FBXNIM_IMPORT_NORMALS'], FBXNormalGenerationMethod=['MIKK_T_SPACE'], LightUnits=['LUMENS'])
    for cls, members in enums.items():
        for name in members: require(hasattr(getattr(u, cls, None), name), 'Required enum missing: ' + cls + '.' + name)
    # Exercise import-option property setters on transient options before any asset or map exists.
    _fbx_options(u)
    for cls, props in ((u.RectLightComponent, ['intensity_units','attenuation_radius','source_width','source_height','cast_shadows']), (u.PointLightComponent, ['intensity_units','attenuation_radius','source_radius','cast_shadows']), (u.SpotLightComponent, ['inner_cone_angle','outer_cone_angle'])):
        obj = cls()
        for prop in props: obj.get_editor_property(prop)
    body = u.BodySetup()
    body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    aggregate=body.get_editor_property('agg_geom')
    for prop in ('convex_elems','box_elems','sphere_elems','sphyl_elems','tapered_capsule_elems','level_set_elems','ml_level_set_elems','skinned_level_set_elems','skinned_triangle_mesh_elems'): aggregate.get_editor_property(prop)
    build = u.MeshBuildSettings()
    for k,v in dict(recompute_normals=False, recompute_tangents=True, use_mikk_t_space=True, generate_lightmap_u_vs=False, use_full_precision_u_vs=True).items(): build.set_editor_property(k,v)
    # Check every material enum up front, including those only present in the probe.
    enum_types={'blend_mode':'BlendMode','shading_model':'MaterialShadingModel','translucency_lighting_mode':'TranslucencyLightingMode','refraction_method':'RefractionMode'}
    for mp in [plan['materials']] + ([plan['probe_materials']] if plan['probe_materials'] else []):
        for t in mp['textures']:
            for cls, name in [('TextureFilter',t['filter']),('TextureAddress',t['address_x']),('TextureAddress',t['address_y']),('TextureCompressionSettings',t['compression']),('MaterialSamplerType',{'normal':'SAMPLERTYPE_NORMAL','scalar':'SAMPLERTYPE_MASKS','color':'SAMPLERTYPE_COLOR'}[t['role']])]:
                require(hasattr(getattr(u, cls, None), name), 'Missing material enum ' + cls + '.' + name)
        for mat in mp['materials']:
            transient = u.Material()
            for prop, value in mat['engine_properties'].items():
                transient.set_editor_property(prop, getattr(getattr(u, enum_types[prop]),value) if prop in enum_types else value)
            for prop, value in mat['engine_properties'].items():
                if prop in enum_types: require(hasattr(getattr(u, enum_types[prop], None), value), 'Missing material enum ' + value)
            for channel in mat['channels']: require(hasattr(u.MaterialProperty, materials.PROPERTIES[channel]), 'Missing material property ' + channel)
    require(callable(getattr(u,'get_default_object',None)),'Required API get_default_object missing')
    u.get_default_object(u.StaticMeshActor).get_editor_property('hidden')
    component=u.StaticMeshComponent()
    for prop in ('visible','cast_shadow'): component.get_editor_property(prop)
    _boundary_cube(u)
    return version


def _fbx_options(u):
    options = u.FbxImportUI()
    fields = dict(import_mesh=True, import_as_skeletal=False, import_animations=False,
                  import_materials=False, import_textures=False, automated_import_should_detect_type=False,
                  mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    for k,v in fields.items(): options.set_editor_property(k,v)
    data = options.get_editor_property('static_mesh_import_data')
    for k,v in FBX_SETTINGS.items(): data.set_editor_property(k,v)
    for k,v in dict(import_translation=u.Vector(0,0,0), import_rotation=u.Rotator(0,0,0),
                    normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                    normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE).items(): data.set_editor_property(k,v)
    return options


def _fresh_destination(u, plan):
    destination_guard(plan['destination']); lib = u.EditorAssetLibrary
    require(not lib.does_directory_exist(plan['destination']) and not lib.list_assets(plan['destination'], recursive=True, include_folder=True), 'Existing destination rejected: ' + plan['destination'])
    require(not lib.does_asset_exist(plan['map_path']), 'Existing map rejected')
    require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save or discard current dirty maps yourself before importing')
    require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Save or discard current dirty content yourself before importing')


def _mesh_check(u, mesh, asset):
    require(isinstance(mesh, u.StaticMesh), 'Imported asset is not a StaticMesh')
    b = mesh.get_bounds(); origin, ext = _vec(b.origin), _vec(b.box_extent)
    actual = dict(min_cm=[origin[i]-ext[i] for i in range(3)], max_cm=[origin[i]+ext[i] for i in range(3)])
    expected = expected_bounds(asset)
    for key in expected:
        for i, want in enumerate(expected[key]):
            tolerance = max(.05, abs(expected['max_cm'][i]-expected['min_cm'][i])*.001)
            require(abs(actual[key][i]-want) <= tolerance, asset['asset_id'] + ': local bounds/pivot/axis mismatch ' + str(actual) + ' expected ' + str(expected))
    ss = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    simple = ss.get_simple_collision_count(mesh); convex = ss.get_convex_collision_count(mesh)
    require(simple >= 0 and convex == len(asset['hulls']), asset['asset_id'] + ': UCX convex count mismatch (no auto hull replacement)')
    body=mesh.get_editor_property('body_setup'); require(body is not None, 'Missing mesh BodySetup')
    aggregate=body.get_editor_property('agg_geom')
    require(len(aggregate.get_editor_property('convex_elems')) == len(asset['hulls']), 'Aggregate convex count mismatch')
    for kind in ('box_elems','sphere_elems','sphyl_elems','tapered_capsule_elems','level_set_elems','ml_level_set_elems','skinned_level_set_elems','skinned_triangle_mesh_elems'):
        require(not aggregate.get_editor_property(kind), 'Unexpected non-UCX collision shape '+kind)
    # get_simple_collision_count is reported diagnostically: documentation is
    # not explicit about whether its aggregate count includes convex entries.
    uv_count = ss.get_num_uv_channels(mesh, 0)
    source_uv_count=len(asset['objects'][0]['uv_layers'])
    blank_uv0_fallback=source_uv_count==0 and not asset.get('image_uv_bindings') and uv_count==1
    require(uv_count == source_uv_count or blank_uv0_fallback, asset['asset_id'] + ': UV channel count mismatch')
    slots = mesh.get_editor_property('static_materials')
    require(len(slots) == len(asset['objects'][0]['materials']), asset['asset_id'] + ': material slot count mismatch')
    # FBX importer may sanitize spaces to underscores. Preserve order and accept only
    # the exact original or the exact deterministic sanitizer, never arbitrary remapping.
    names = [str(s.get_editor_property('imported_material_slot_name')) for s in slots]
    for got, want in zip(names, asset['objects'][0]['materials']):
        require(got in (want, re.sub(r'[^A-Za-z0-9_]', '_', want)), asset['asset_id'] + ': imported material slot order/name mismatch ' + got + ' != ' + want)
    require(mesh.get_num_triangles(0) == asset['objects'][0]['triangles'], asset['asset_id'] + ': triangle count changed')
    return dict(bounds_cm=actual, expected_bounds_cm=expected, simple_collision_count=simple,
        convex_collision_count=convex, uv_channels=uv_count, source_uv_channels=source_uv_count, untextured_blank_uv0_fallback=blank_uv0_fallback, imported_slot_names=names,
        triangles=mesh.get_num_triangles(0), mesh_path=_identity(mesh))


def _import_mesh(u, source, folder, asset, assignments):
    expected = folder + '/' + asset['mesh']; require(not u.EditorAssetLibrary.does_asset_exist(expected), 'Mesh overwrite rejected')
    task = u.AssetImportTask()
    for k,v in dict(filename=str(source), destination_path=folder, destination_name=asset['mesh'], automated=True,
        async_=False, replace_existing=False, replace_existing_settings=False, save=False,
        factory=u.FbxFactory(), options=_fbx_options(u)).items(): task.set_editor_property(k,v)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    require(len(objects) == 1 and isinstance(objects[0], u.StaticMesh), 'Expected exactly one render StaticMesh; UCX must not be render assets')
    mesh = objects[0]; require(_identity(mesh) == expected, 'Importer changed destination/name; stop rather than use wrong asset')
    _mesh_check(u, mesh, asset)
    ss = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    settings = ss.get_lod_build_settings(mesh, 0)
    for k,v in dict(recompute_normals=False, recompute_tangents=True, use_mikk_t_space=True,
                    generate_lightmap_u_vs=False, use_full_precision_u_vs=True).items(): settings.set_editor_property(k,v)
    ss.set_lod_build_settings(mesh, 0, settings)
    body = mesh.get_editor_property('body_setup'); require(body is not None, 'Missing mesh BodySetup')
    body.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    for assignment in assignments:
        require(assignment['status'] == 'PLANNED' and assignment['material_path'], 'Unresolved material slot')
        mat = u.load_asset(assignment['material_path']); require(mat is not None, 'Created material missing')
        mesh.set_material(assignment['slot'], mat)
        require(_identity(mesh.get_material(assignment['slot'])) == assignment['material_path'], 'Material assignment failed')
    require(u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False), 'Mesh save failed')
    return mesh


def _spawn_mesh(u, actors, asset, mesh, placement, transform, phase, probe=False):
    actor = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0,0,0), transient=False)
    require(actor is not None and isinstance(actor, u.StaticMeshActor), 'Could not create independent StaticMeshActor')
    sid = placement['stable_id']
    actor.set_actor_label(sid)
    tags = list(placement.get('tags', [])) + ['PremiumStoreV3', 'V3Placement=' + sid, 'V3Asset=' + asset['asset_id'], 'V3Phase=' + phase]
    if probe: tags.append('CalibrationProbe')
    actor.set_editor_property('tags', tags)
    component = actor.get_editor_property('static_mesh_component')
    component.set_mobility(u.ComponentMobility.STATIC)
    require(component.set_static_mesh(mesh), 'Could not assign canonical mesh')
    component.set_collision_profile_name('BlockAll' if asset['hulls'] else 'NoCollision', update_overlaps=False)
    component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if asset['hulls'] else u.CollisionEnabled.NO_COLLISION)
    component.set_collision_object_type(u.CollisionChannel.ECC_WORLD_STATIC)
    response = u.CollisionResponseType.ECR_BLOCK if asset['hulls'] else u.CollisionResponseType.ECR_IGNORE
    component.set_collision_response_to_all_channels(response)
    # Visibility is explicit. Pawn stays BLOCK on authored blockers, including props.
    component.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY, response)
    component.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN, response)
    require(actors.set_actor_transform(actor, _ue_transform(u, transform)), 'Placement transform failed ' + sid)
    return actor


def _spawn_lights(u, actors, plan):
    for rec in plan['lights']:
        cls = {'AREA':u.RectLight, 'POINT':u.PointLight, 'SPOT':u.SpotLight}[rec['type']]
        actor = actors.spawn_actor_from_class(cls, u.Vector(0,0,0), transient=False)
        require(actor is not None, 'Fixture light spawn failed')
        actor.set_actor_label(rec['id']); actor.set_editor_property('tags', ['PremiumStoreV3','V3FixtureLight='+rec['id'],'PhotometryUncalibrated'])
        require(actors.set_actor_transform(actor, _ue_transform(u, transform_record(rec, light=True))), 'Light orientation failed')
        comp = actor.get_component_by_class(u.LightComponent)
        require(comp is not None, 'Fixture LightComponent missing')
        comp.set_mobility(u.ComponentMobility.MOVABLE)
        comp.set_editor_property('intensity_units', u.LightUnits.LUMENS)
        comp.set_intensity(rec['energy_watts']*plan['light_policy']['lumens_per_blender_watt'])
        comp.set_light_color(u.LinearColor(*rec['color_rgb'], 1), srgb=False)
        comp.set_editor_property('attenuation_radius', plan['light_policy']['attenuation_radius_cm'])
        comp.set_editor_property('cast_shadows', True)
        if rec['type'] == 'AREA':
            comp.set_editor_property('source_width', rec['size_m'][0]*100)
            comp.set_editor_property('source_height', rec['size_m'][1]*100)
        else:
            comp.set_editor_property('source_radius', rec['shadow_soft_size_m']*100)
            if rec['type'] == 'SPOT':
                outer = math.degrees(rec['spot_size_radians'])/2
                comp.set_editor_property('outer_cone_angle', outer)
                comp.set_editor_property('inner_cone_angle', outer*(1-rec['spot_blend']))


def _boundary_cube(u):
    cube=u.load_asset(BOUNDARY_POLICY['engine_mesh'])
    require(cube is not None and isinstance(cube,u.StaticMesh), 'Engine BasicShapes Cube is unavailable; no barrier fallback is created')
    bounds=cube.get_bounds()
    require(max(abs(x) for x in _vec(bounds.origin)) < .01 and max(abs(x-50) for x in _vec(bounds.box_extent)) < .01, 'Engine Cube must be centred and exactly 100 cm on all axes')
    ss=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    aggregate=cube.get_editor_property('body_setup').get_editor_property('agg_geom')
    require(len(aggregate.get_editor_property('box_elems'))+len(aggregate.get_editor_property('convex_elems')) > 0, 'Engine Cube has no usable authored simple collision')
    require(ss.get_simple_collision_count(cube)>=0 and ss.get_convex_collision_count(cube)>=0,'Engine Cube collision query failed')
    return cube


def _boundary_transform(rec):
    data=transform_record(rec)
    centre=numbers(rec['centre_m'],3,'boundary centre')
    wanted=[centre[0]*100,-centre[1]*100,centre[2]*100]
    require(max(abs(a-b) for a,b in zip(data['location_cm'],wanted))<.01,'Boundary matrix and centre disagree')
    data['location_cm']=wanted
    # The source EMPTY matrix carries HALF extents. Engine Cube is 1 metre wide,
    # so use full dimensions_m as scale, never the source half-extent scale.
    data['scale']=list(rec['dimensions_m'])
    return data


def _spawn_boundaries(u,actors,plan):
    cube=_boundary_cube(u)
    for rec in plan['scene_support']['boundaries']:
        actor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,0),transient=False)
        require(actor is not None,'Boundary barrier spawn failed')
        actor.set_actor_label('V3_INVISIBLE_'+rec['id'])
        actor.set_editor_property('tags',['PremiumStoreV3','V3BoundaryBarrier='+rec['id'],'InvisiblePerimeter','NonProp'])
        comp=actor.get_editor_property('static_mesh_component'); comp.set_mobility(u.ComponentMobility.STATIC)
        require(comp.set_static_mesh(cube),'Could not assign read-only engine Cube')
        comp.set_collision_profile_name('BlockAll',update_overlaps=False)
        comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_collision_object_type(u.CollisionChannel.ECC_WORLD_STATIC)
        comp.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_BLOCK)
        comp.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_BLOCK)
        comp.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY,u.CollisionResponseType.ECR_IGNORE)
        comp.set_visibility(False,propagate_to_children=True); comp.set_cast_shadow(False)
        actor.set_actor_hidden_in_game(True)
        require(actors.set_actor_transform(actor,_ue_transform(u,_boundary_transform(rec))),'Boundary barrier transform failed')


def _marker_transform(rec):
    data=transform_record(rec); data['scale']=[1,1,1]
    return data


def _spawn_markers(u, actors, plan):
    rows=[(r,'V3SpawnMarker','SourcePlayerStart',u.PlayerStart) for r in plan['scene_support']['spawn_markers']]
    rows += [(r,'V3BoundaryMarker','SourceBoundaryMetadata',u.TargetPoint) for r in plan['scene_support']['boundaries']]
    for rec,tag,role,cls in rows:
        actor = actors.spawn_actor_from_class(cls, u.Vector(0,0,0), transient=False)
        require(actor is not None, 'Spawn marker creation failed')
        actor.set_actor_label(rec['id']); actor.set_editor_property('tags', ['PremiumStoreV3',tag+'='+rec['id'],role])
        require(actors.set_actor_transform(actor, _ue_transform(u, _marker_transform(rec))), 'Marker transform failed')


def _check_transform(actual, expected, label):
    for a,b in zip(_vec(actual.translation), expected['location_cm']): require(abs(a-b) <= .05, label + ': saved location mismatch')
    for a,b in zip(_vec(actual.scale3d), expected['scale']): require(abs(a-b) <= 1e-5, label + ': saved scale mismatch')
    q = _quat(actual.rotation); e = expected['quaternion_xyzw']
    require(min(max(abs(a-b) for a,b in zip(q,e)), max(abs(a+b) for a,b in zip(q,e))) <= 1e-5, label + ': saved rotation mismatch')


def _verify_material_assets(u, plan):
    enums={'blend_mode':'BlendMode','shading_model':'MaterialShadingModel','translucency_lighting_mode':'TranslucencyLightingMode','refraction_method':'RefractionMode'}
    count = 0
    for mp in [plan['materials']] + ([plan['probe_materials']] if plan['probe_materials'] else []):
        for record in mp['materials']:
            obj = u.load_asset(record['asset_path']); require(obj is not None, 'Persisted material missing')
            for prop,value in record['engine_properties'].items():
                want=getattr(getattr(u,enums[prop]),value) if prop in enums else value
                require(obj.get_editor_property(prop)==want, 'Persisted material policy mismatch '+record['name']+' '+prop)
            count += 1
        for record in mp['textures']:
            obj = u.load_asset(record['asset_path']); require(obj is not None, 'Persisted texture missing')
            props=dict(srgb=record['srgb'],flip_green_channel=record['flip_green_channel'],virtual_texture_streaming=False,
                filter=getattr(u.TextureFilter,record['filter']),address_x=getattr(u.TextureAddress,record['address_x']),
                address_y=getattr(u.TextureAddress,record['address_y']),compression_settings=getattr(u.TextureCompressionSettings,record['compression']))
            for prop,want in props.items(): require(obj.get_editor_property(prop)==want, 'Persisted texture flag mismatch '+record['name']+' '+prop)
    return count


def verify_scene(u, plan, report):
    material_count = _verify_material_assets(u, plan)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    found = {}; lights = {}; markers = {}; boundaries = {}; barriers = {}
    for actor in actors:
        require(not isinstance(actor, u.DirectionalLight), 'Unexpected directional light in generated scene')
        require(not actor.get_components_by_class(u.InstancedStaticMeshComponent) and not actor.get_components_by_class(u.HierarchicalInstancedStaticMeshComponent), 'ISM/HISM found: contract violation')
        tags = _tag_map(actor)
        if 'V3Placement' in tags:
            sid = tags['V3Placement']; require(sid not in found, 'Duplicate actor stable ID'); found[sid] = actor
        if 'V3FixtureLight' in tags:
            lid = tags['V3FixtureLight']; require(lid not in lights, 'Duplicate light'); lights[lid] = actor
        if 'V3BoundaryBarrier' in tags:
            bid=tags['V3BoundaryBarrier']; require(bid not in barriers, 'Duplicate boundary barrier'); barriers[bid]=actor
        if 'V3BoundaryMarker' in tags:
            bid=tags['V3BoundaryMarker']; require(bid not in boundaries, 'Duplicate boundary marker'); boundaries[bid]=actor
        if 'V3SpawnMarker' in tags:
            mid = tags['V3SpawnMarker']; require(mid not in markers, 'Duplicate spawn marker'); markers[mid] = actor
    expected = {p['stable_id']:p for p in plan['placements']}
    assets = {a['asset_id']:a for a in plan['assets']}
    if plan['phase'] == 'sample':
        expected['V3_QA_AXIS_PROBE'] = dict(stable_id='V3_QA_AXIS_PROBE', asset_id='unit_axis_probe', eligible=False,
            unreal_transform=dict(location_cm=[-500,500,0], quaternion_xyzw=[0,0,0,1], scale=[1,1,1]))
        assets['unit_axis_probe'] = plan['probe_asset']
    require(set(found) == set(expected), 'Missing/extra placement IDs after reconstruction')
    actual_prop_count=sum('Prop' in [str(t) for t in a.get_editor_property('tags')] for a in actors)
    require(actual_prop_count==plan['expected_eligible_count'],'Unexpected Prop tag on non-source/support actor')
    eligible_count = 0
    for sid,p in expected.items():
        actor = found[sid]; require(isinstance(actor, u.StaticMeshActor), sid + ': not StaticMeshActor')
        tags = [str(t) for t in actor.get_editor_property('tags')]
        require(('Prop' in tags) == bool(p['eligible']), sid + ': incorrect Actor Prop tag')
        eligible_count += int('Prop' in tags)
        _check_transform(actor.get_actor_transform(), p['unreal_transform'], sid)
        comp = actor.get_editor_property('static_mesh_component'); mesh = comp.get_editor_property('static_mesh')
        require(_identity(mesh) == report['meshes'][p['asset_id']]['mesh_path'], sid + ': wrong canonical mesh')
        blocks = bool(assets[p['asset_id']]['hulls'])
        require(comp.get_collision_enabled() == (u.CollisionEnabled.QUERY_AND_PHYSICS if blocks else u.CollisionEnabled.NO_COLLISION), sid + ': wrong physical collision mode')
        for channel in (u.CollisionChannel.ECC_PAWN,u.CollisionChannel.ECC_VISIBILITY):
            require(comp.get_collision_response_to_channel(channel) == (u.CollisionResponseType.ECR_BLOCK if blocks else u.CollisionResponseType.ECR_IGNORE), sid + ': wrong collision response')
    require(eligible_count == plan['expected_eligible_count'], 'Eligible Actor count mismatch')
    for aid, asset in assets.items():
        mesh = u.load_asset(report['meshes'][aid]['mesh_path']); _mesh_check(u, mesh, asset)
        for slot, path in enumerate(report['meshes'][aid]['material_paths']):
            require(_identity(mesh.get_material(slot)) == path, aid + ': material slot persistence mismatch')
    require(set(lights) == {r['id'] for r in plan['lights']}, 'Fixture-light count/identity mismatch')
    for r in plan['lights']:
        actor = lights[r['id']]; _check_transform(actor.get_actor_transform(), transform_record(r, light=True), r['id'])
        comp = actor.get_component_by_class(u.LightComponent)
        require(comp.get_editor_property('intensity_units') == u.LightUnits.LUMENS, 'Fixture units changed')
        require(abs(comp.get_editor_property('intensity')-r['energy_watts']*plan['light_policy']['lumens_per_blender_watt']) < .01, 'Fixture intensity changed')
    require(set(markers) == {r['id'] for r in plan['scene_support']['spawn_markers']}, 'Spawn marker count/identity mismatch')
    for r in plan['scene_support']['spawn_markers']:
        require(isinstance(markers[r['id']],u.PlayerStart),'Spawn is not PlayerStart')
        _check_transform(markers[r['id']].get_actor_transform(), _marker_transform(r), r['id'])
    require(set(boundaries) == {r['id'] for r in plan['scene_support']['boundaries']}, 'Boundary marker count/identity mismatch')
    for r in plan['scene_support']['boundaries']: _check_transform(boundaries[r['id']].get_actor_transform(), _marker_transform(r), r['id'])
    require(set(barriers)=={r['id'] for r in plan['scene_support']['boundaries']},'Invisible boundary count mismatch')
    cube=_boundary_cube(u)
    for rec in plan['scene_support']['boundaries']:
        actor=barriers[rec['id']]; require(isinstance(actor,u.StaticMeshActor),'Boundary is not StaticMeshActor')
        require('Prop' not in [str(t) for t in actor.get_editor_property('tags')],'Boundary must never be Prop')
        _check_transform(actor.get_actor_transform(),_boundary_transform(rec),rec['id'])
        comp=actor.get_editor_property('static_mesh_component')
        require(_identity(comp.get_editor_property('static_mesh'))==_identity(cube),'Boundary mesh changed')
        require(comp.get_collision_enabled()==u.CollisionEnabled.QUERY_AND_PHYSICS,'Boundary physical collision disabled')
        require(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)==u.CollisionResponseType.ECR_BLOCK,'Boundary must block Pawn')
        require(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY)==u.CollisionResponseType.ECR_IGNORE,'Boundary must ignore Visibility')
        require(actor.get_editor_property('hidden') is True and comp.get_editor_property('visible') is False and comp.get_editor_property('cast_shadow') is False,'Boundary visibility/shadow flags changed')
    total_roles=len(found)+len(lights)+len(markers)+len(boundaries)+len(barriers)
    require(total_roles==plan['expected_role_actor_count'],'Generated role actor count mismatch')
    return dict(status='PASS_STRUCTURAL_CHECKS_ONLY', total_role_actors=total_roles, independent_actors=len(found), eligible_actors=eligible_count,
        fixture_lights=len(lights), player_starts=len(markers), boundary_markers=len(boundaries), invisible_boundaries=len(barriers), total_gameplay_support_actors=len(markers)+len(boundaries)+len(barriers), ism_hism_count=0, directional_lights=0,
        manual_trace_reachability_tested=False, shader_compilation_tested=False, material_policies_checked=material_count)


def _validate_approval(contract, approval_file, token):
    require(approval_file and token, 'Full import requires an explicit sample approval file and its matching success token')
    approval = read(approval_file)
    require(approval.get('schema') == SCHEMA + '-approval' and approval.get('approved') is True, 'Missing explicit sample approval')
    require(approval.get('package_fingerprint') == contract['fingerprint'], 'Package/importer changed after sample; run a new sample')
    require(secrets.compare_digest(str(approval.get('success_token', '')), str(token)), 'Sample success token mismatch')
    require(all(approval.get('manual_checks', {}).get(k) is True for k in REVIEW_CHECKS), 'Manual sample checks incomplete')
    report_path = Path(approval['sample_report'])
    require(report_path.is_file() and sha(report_path) == approval['sample_report_sha256'], 'Sample report missing or modified')
    report = read(report_path)
    require(report.get('phase') == 'sample' and report.get('status') == 'SAVED_RELOADED_PENDING_MANUAL_REVIEW', 'Sample did not persist successfully')
    require(report.get('package_fingerprint') == contract['fingerprint'] and report.get('success_token') == token, 'Sample report approval mismatch')
    cold_path=_cold_proof(report_path,report)
    require(sha(cold_path)==approval.get('cold_report_sha256'), 'Cold approval evidence changed')
    return approval


def verify_after_editor_restart(sample_report, ue=None):
    """Read-only verification, except loading the generated map and a new local log.

    Run after completely closing and restarting Unreal Editor. It refuses the
    same editor process as the original import; map reload alone is not cold QA.
    """
    report_path=Path(sample_report).resolve(); report=read(report_path)
    require(report.get('actual_unreal_run') is True, 'An actual engine import report is required')
    require(report.get('status') in ('SAVED_RELOADED_PENDING_MANUAL_REVIEW','FULL_SAVED_RELOADED_GAMEPLAY_ACCEPTANCE_PENDING'), 'Import must have passed structural reload checks')
    require(report.get('editor_process_id') != os.getpid(), 'Close and restart Unreal Editor before cold asset verification')
    plan_path=report_path.with_name('PLAN.json'); require(sha(plan_path)==report['plan_sha256'], 'Saved plan changed')
    plan=read(plan_path); contract=load_package(report['package_root'])
    require(plan['package_fingerprint']==report['package_fingerprint']==contract['fingerprint'], 'Package changed after import')
    if ue is None:
        import unreal as ue
    version=_guard_api(ue,plan)
    require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Save/discard dirty work before cold verification')
    level=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    require(level.load_level(report['map_path']), 'Could not load generated map')
    result=verify_scene(ue,plan,report)
    output=report_path.with_name('COLD_REOPEN_VERIFICATION.json')
    proof=dict(schema=SCHEMA+'-cold-reopen',status='PASS',actual_unreal_run=getattr(ue,'__name__','')=='unreal',verification=result,package_fingerprint=contract['fingerprint'],
        sample_report_sha256=sha(report_path),plan_sha256=sha(plan_path),editor_process_id=os.getpid(),engine_version=version,
        utc=datetime.now(timezone.utc).isoformat(),shader_compilation_and_gameplay_still_manual=True)
    write(output,proof,exclusive=True)
    return str(output)


def _cold_proof(report_path,report):
    path=report_path.with_name('COLD_REOPEN_VERIFICATION.json'); require(path.is_file(), 'Restart Unreal and run verify_after_editor_restart before approval')
    proof=read(path)
    require(proof.get('schema')==SCHEMA+'-cold-reopen' and proof.get('status')=='PASS' and proof.get('actual_unreal_run') is True, 'Cold reopen verification failed or used a mock backend')
    require(proof.get('sample_report_sha256')==sha(report_path) and proof.get('package_fingerprint')==report['package_fingerprint'], 'Cold reopen evidence is stale')
    require(proof.get('editor_process_id') != report.get('editor_process_id'), 'Cold verification must come from a restarted editor')
    return path


def approve_sample(sample_report, checked, approval_text, output=None):
    """Run only after completing every manual check. This never inspects gameplay for you."""
    require(approval_text == 'I reviewed the v3 sample in Unreal 5.8 and approve the full import', 'Exact manual acceptance phrase required')
    require(isinstance(checked, dict) and all(checked.get(k) is True for k in REVIEW_CHECKS), 'Every manual check must be explicitly true')
    report_path = Path(sample_report).resolve(); report = read(report_path)
    require(report.get('status') == 'SAVED_RELOADED_PENDING_MANUAL_REVIEW' and report.get('phase') == 'sample', 'Successful persisted sample report required')
    require(report.get('actual_unreal_run') is True and re.match(r'^5\.8(?:\.|-)', str(report.get('engine_version',''))), 'Actual Unreal 5.8 sample report required')
    require(isinstance(report.get('success_token'),str) and len(report['success_token']) >= 24, 'Sample success token missing')
    require(report.get('after_reload', {}).get('status') == 'PASS_STRUCTURAL_CHECKS_ONLY', 'Sample reload verification incomplete')
    contract = load_package(report['package_root'])
    require(contract['fingerprint'] == report['package_fingerprint'], 'Package changed after sample')
    cold_path=_cold_proof(report_path,report)
    output = Path(output or report_path.with_name('SAMPLE_MANUAL_APPROVAL.json'))
    approval = dict(schema=SCHEMA+'-approval', approved=True, manual_checks={k:True for k in REVIEW_CHECKS},
        approval_text=approval_text, success_token=report['success_token'], package_fingerprint=contract['fingerprint'],
        sample_report=str(report_path), sample_report_sha256=sha(report_path), cold_report=str(cold_path), cold_report_sha256=sha(cold_path), utc=datetime.now(timezone.utc).isoformat())
    write(output, approval, exclusive=True)
    return dict(approval_file=str(output), success_token=approval['success_token'])


def run(package_root, phase='sample', destination=None, approval_file=None, success_token=None, ue=None):
    """Apply into a new destination. Full is locked until explicit sample approval."""
    contract = load_package(package_root)
    approval = _validate_approval(contract, approval_file, success_token) if phase == 'full' else None
    plan = build_plan(contract, phase, destination)
    require(not plan['materials']['blocked_materials'], 'Unsupported sample/full material slots: ' + repr(plan['materials']['blocked_materials']))
    if phase == 'full': require(not plan['full_material_blockers'], 'Full material blockers remain')
    if plan['probe_materials']: require(not plan['probe_materials']['blocked_materials'], 'Probe material blockers remain')
    if ue is None:
        import unreal as ue
    version = _guard_api(ue, plan); _fresh_destination(ue, plan)
    report_dir = contract['root'] / 'runtime_reports' / plan['destination'].split('/')[-1]
    require(not report_dir.exists(), 'Report destination exists; choose a fresh version')
    report_dir.mkdir(parents=True)
    report_path = report_dir / 'IMPORT_REPORT.json'
    report = dict(schema=SCHEMA+'-report', status='PREFLIGHT_PASSED', phase=phase, destination=plan['destination'],
        map_path=plan['map_path'], engine_version=version, package_root=str(contract['root']),
        package_fingerprint=contract['fingerprint'], started_utc=datetime.now(timezone.utc).isoformat(),
        actual_unreal_run=getattr(ue,'__name__','')=='unreal', editor_process_id=os.getpid(), meshes={}, manual_checks_pending=list(REVIEW_CHECKS),
        success_token=secrets.token_urlsafe(24) if phase == 'sample' else None,
        approved_sample=approval, lights_source_metadata=plan['lights'], light_policy=plan['light_policy'],
        scene_support=plan['scene_support'], boundary_policy=plan['boundary_policy'], tests_not_performed=['PIE gameplay','multiplayer','performance','visual fidelity','shader compile completion'])
    write(report_dir/'PLAN.json', plan, exclusive=True); report['plan_sha256']=sha(report_dir/'PLAN.json'); write(report_path, report, exclusive=True)
    try:
        # Rehash before any mutation: plan paths and bytes must still match preflight.
        require(load_package(package_root)['fingerprint'] == contract['fingerprint'], 'Files changed during preflight')
        materials.apply_plan(plan['materials'], ue=ue)
        if plan['probe_materials']: materials.apply_plan(plan['probe_materials'], ue=ue)
        meshes = {}
        for asset in plan['assets'] + ([plan['probe_asset']] if plan['probe_asset'] else []):
            probe = asset['asset_id'] == 'unit_axis_probe'
            mp = plan['probe_materials'] if probe else plan['materials']
            assignments = sorted([a for a in mp['slot_assignments'] if a['mesh'] == asset['mesh']], key=lambda a:a['slot'])
            source = contract['root']/('qa_axis/export' if probe else 'export')/asset['fbx']
            mesh = _import_mesh(ue, source, plan['destination'] + ('/ProbeMesh' if probe else '/Meshes'), asset, assignments)
            meshes[asset['asset_id']] = mesh
            report['meshes'][asset['asset_id']] = dict(_mesh_check(ue, mesh, asset), material_paths=[a['material_path'] for a in assignments])
            write(report_path, report)
        require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Current map became dirty; refusing level switch')
        level = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        require(level.new_level(plan['map_path'], is_partitioned_world=False), 'New empty map creation failed')
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        for p in plan['placements']:
            _spawn_mesh(ue, actors, contract['assets'][p['asset_id']], meshes[p['asset_id']], p, p['unreal_transform'], phase)
        if phase == 'sample':
            _spawn_mesh(ue, actors, plan['probe_asset'], meshes['unit_axis_probe'], dict(stable_id='V3_QA_AXIS_PROBE',tags=['CalibrationProbe']),
                dict(location_cm=[-500,500,0], quaternion_xyzw=[0,0,0,1], scale=[1,1,1]), phase, probe=True)
        _spawn_lights(ue, actors, plan); _spawn_markers(ue, actors, plan); _spawn_boundaries(ue, actors, plan)
        report['before_save'] = verify_scene(ue, plan, report)
        require(level.save_current_level(), 'Map save failed')
        require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Map remains dirty; refusing reload')
        require(level.load_level(plan['map_path']), 'Map reload failed')
        report['after_reload'] = verify_scene(ue, plan, report)
        report['status'] = 'SAVED_RELOADED_PENDING_MANUAL_REVIEW' if phase == 'sample' else 'FULL_SAVED_RELOADED_GAMEPLAY_ACCEPTANCE_PENDING'
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write(report_path, report)
        ue.log('V3 '+phase+' map saved and structurally rechecked. Manual gameplay/visual checks remain. Report: '+str(report_path))
        return str(report_path)
    except Exception as exc:
        report.update(status='FAILED_PARTIAL_NEW_CONTENT_ONLY', error=repr(exc), finished_utc=datetime.now(timezone.utc).isoformat())
        write(report_path, report)
        ue.log_error('V3 import stopped. New partial content remains at '+plan['destination']+'. No destructive cleanup attempted. '+str(exc))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description='Safe offline dry run. Apply only by explicit run() in UE 5.8.')
    parser.add_argument('--package', required=True); parser.add_argument('--phase', choices=['sample','full'], default='sample')
    parser.add_argument('--destination'); parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    result = dry_run(args.package, args.phase, args.destination, args.output)
    print(json.dumps(dict(mode='DRY_RUN_NO_UNREAL_MUTATION', phase=args.phase, placements=result['expected_placement_count'],
        eligible=result['expected_eligible_count'], full_material_blockers=len(result['full_material_blockers']), output=args.output), indent=2))

if __name__ == '__main__': main()
