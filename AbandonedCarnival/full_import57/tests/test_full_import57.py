"""Portable stdlib contract and safety tests. Mocks do not prove UE runtime behavior.

Run: python -m unittest discover -s full_import57/tests -v
Optional frozen-package integration: CARNIVAL_PACKAGE_ROOT=/path/to/AbandonedCarnival
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module

f = load('full_import_under_test', HERE.parent / 'carnival_full_import57.py')
g = load('full_import_mock_unreal', HERE / 'mock_unreal.py')
FIXTURE = json.loads((HERE / 'full_plan_fixture.json').read_text())


class ContractTests(unittest.TestCase):
    def test_full_fixture_counts_and_unique_identities(self):
        p = FIXTURE
        self.assertEqual(p['counts'], f.COUNTS)
        self.assertEqual(len(p['assets']), 181)
        self.assertEqual(sum(a['kind'] == 'props' for a in p['assets']), 138)
        self.assertEqual(sum(a['kind'] == 'environment' for a in p['assets']), 43)
        self.assertEqual(len(p['materials']), 59)
        self.assertEqual(len(p['textures']), 41)
        self.assertEqual(len(p['placements']), 196)
        self.assertEqual(sum(a['kind'] == 'props' for a in p['placements']), 153)
        self.assertEqual(sum(a['class'] == 'PlayerStart' for a in p['metadata']), 10)
        self.assertEqual(sum(a['class'] != 'PlayerStart' for a in p['metadata']), 41)
        identities = [a['id'] for a in p['placements']] + ['meta:' + a['source_object'] for a in p['metadata']]
        self.assertEqual(len(identities), 247)
        self.assertEqual(len(identities), len(set(identities)))
        names = {a['asset_name'] for a in p['assets']}
        self.assertEqual(len(names), 181)
        self.assertTrue(all(a['asset_name'] in names for a in p['placements']))

    def test_collision_material_bounds_and_uv_contract(self):
        mats = {a['source_name'] for a in FIXTURE['materials']}
        self.assertEqual(sum(a['collision_hulls'] for a in FIXTURE['assets']), 2276)
        self.assertTrue(any(a['collision_hulls'] == 0 for a in FIXTURE['assets']))
        for a in FIXTURE['assets']:
            self.assertTrue(set(a['materials']) <= mats)
            self.assertEqual(a['expected_uv_channels'], 1)
            self.assertGreaterEqual(a['collision_hulls'], 1 if a['kind'] == 'props' else 0)
            self.assertTrue(all(math.isfinite(v) for axis in a['bounds_cm'].values() for v in axis))
            self.assertTrue(all(lo < hi for lo, hi in zip(a['bounds_cm']['min'], a['bounds_cm']['max'])))
        self.assertEqual(len({(a['path'], a['usage']) for a in FIXTURE['textures']}), 41)
        self.assertEqual(len({a['asset_name'] for a in FIXTURE['textures']}), 41)

    def test_all_metadata_orientation_basis(self):
        for a in FIXTURE['metadata']:
            forward, up = f.basis(a['rotation_pitch_yaw_roll_deg'])
            for actual, expected in ((forward, a['forward_ue']), (up, a['up_ue'])):
                self.assertLess(max(abs(x-y) for x,y in zip(actual, expected)), 1e-5, a['source_object'])
        self.assertTrue(any(abs(a['rotation_pitch_yaw_roll_deg'][2]) > 1 for a in FIXTURE['metadata']))

    def test_frozen_vendor_hashes(self):
        for relative, expected in f.VENDORS.items():
            raw = (HERE.parent / relative).read_bytes()
            self.assertEqual(hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest(), expected)
        c, m = f._vendors()
        self.assertEqual(m.DEST, f.DEST)

    def test_no_save_delete_or_project_setting_calls(self):
        tree = ast.parse((HERE.parent / 'carnival_full_import57.py').read_text())
        forbidden = ('save_', 'delete_', 'destroy_', 'set_console_variable', 'set_project_setting')
        bad = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr.startswith(forbidden)]
        self.assertEqual(bad, [])

    @unittest.skipUnless(os.environ.get('CARNIVAL_PACKAGE_ROOT'), 'optional real pinned-source integration; set CARNIVAL_PACKAGE_ROOT')
    def test_real_frozen_package(self):
        _, _, p = f.plan(os.environ['CARNIVAL_PACKAGE_ROOT'])
        self.assertEqual(p['counts'], f.COUNTS)
        self.assertEqual(p['canonical_hulls'], 2276)
        self.assertEqual(len(p['verified_files']), 246)


class MockEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c, cls.m = f._vendors()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='full57-test-')
        self.addCleanup(self.tmp.cleanup)
        self.p = copy.deepcopy(FIXTURE)
        self.p['root'] = self.tmp.name
        for kind, rows, pathkey, hashkey in (
                ('fbx', self.p['assets'], 'source_path', 'fbx_sha256'),
                ('texture', self.p['textures'], 'filename', 'sha256')):
            for index, row in enumerate(rows):
                path = Path(self.tmp.name) / (kind + str(index) + '.mock')
                raw = ('bounded mock ' + kind + str(index)).encode()
                path.write_bytes(raw)
                row[pathkey] = str(path)
                row[hashkey] = hashlib.sha256(raw).hexdigest()
        self.u = g.full_engine(self.p, self.c)
        self.addCleanup(shutil.rmtree, self.u.content_dir, True)
        self.engine_patch = patch.dict(sys.modules, {'unreal': self.u})
        self.engine_patch.start(); self.addCleanup(self.engine_patch.stop)
        self.plan_patch = patch.object(f, 'plan', return_value=(self.c, self.m, self.p))
        self.plan_patch.start(); self.addCleanup(self.plan_patch.stop)

    def preflight_blocked(self, expected):
        report = f.preflight(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_PREFLIGHT_BLOCKED', report)
        self.assertIn(expected.lower(), ' '.join(report['errors']).lower())
        self.assertEqual(self.u.events, [])
        self.assertFalse(report['mutation_started'])
        return report

    def mesh(self, item=None):
        report = f._report('test')
        item = item or self.p['assets'][0]
        return f._import_mesh(self.u, self.c, item, report), report

    def import_success(self):
        report = f.import_full(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_IMPORT_CREATED_UNSAVED', report)
        return report

    def test_preflight_is_read_only(self):
        original_world = self.u.world
        report = f.preflight(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_PREFLIGHT_PASS', report)
        self.assertEqual(self.u.events, [])
        self.assertEqual(self.u.assets, {})
        self.assertIs(self.u.world, original_world)
        self.assertFalse(report['mutation_started'])

    def test_offline_preflight_without_unreal(self):
        with patch.dict(sys.modules, {'unreal': None}):
            report = f.preflight(self.tmp.name)
        self.assertEqual(report['status'], 'FILES_VERIFIED_ENGINE_NOT_CHECKED', report)
        self.assertEqual(self.u.events, [])

    def test_guard_blocks_dirty_maps(self):
        self.u.dirty_maps = [g.Obj()]
        self.preflight_blocked('dirty maps')

    def test_guard_blocks_dirty_assets(self):
        self.u.dirty_content = [g.Obj()]
        self.preflight_blocked('dirty assets')

    def test_guard_blocks_play_world(self):
        self.u.game_world = g.World()
        self.preflight_blocked('Play/Simulate')

    def test_guard_blocks_existing_namespace(self):
        self.u.existing_namespace = True
        self.preflight_blocked('already exists')

    def test_guard_blocks_physical_empty_namespace(self):
        (Path(self.u.content_dir) / f.DEST.removeprefix('/Game/')).mkdir()
        self.preflight_blocked('Physical')

    def test_guard_blocks_existing_tagged_actor(self):
        actor = g.StaticMeshActor(); actor.props['tags'] = [f.TAG]; self.u.actors.append(actor)
        self.preflight_blocked('Existing full-import actors')

    def test_guard_blocks_wrong_engine(self):
        self.u.version = '5.6.1-12345'
        self.preflight_blocked('5.7.4')

    def test_guard_blocks_forward_renderer_without_changing_it(self):
        self.u.forward_renderer = 1
        self.preflight_blocked('deferred')
        self.assertEqual(self.u.forward_renderer, 1)

    def test_apply_guard_blocks_before_mutation(self):
        self.u.dirty_maps = [g.Obj()]
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        self.assertEqual(caught.exception.report['status'], 'FULL_IMPORT_BLOCKED')
        self.assertFalse(caught.exception.report['partial'])
        self.assertEqual(self.u.events, [])

    def test_mesh_import_uses_legacy_factory_and_actual_paths(self):
        mesh, report = self.mesh()
        row = report['meshes'][0]
        self.assertEqual(row['actual'], [mesh.get_path_name()])
        self.assertEqual(row['task_paths'], row['actual'])
        task = self.u.import_tasks[0]
        self.assertIsInstance(task.props['factory'], g.FbxFactory)
        self.assertFalse(task.props['save'])
        self.assertFalse(task.props['async_'])
        self.assertFalse(task.props['replace_existing'])
        opts = task.props['options'].props
        self.assertFalse(opts['automated_import_should_detect_type'])
        self.assertFalse(opts['import_materials'])
        self.assertFalse(opts['import_textures'])
        self.assertEqual(mesh.props['body_setup'].props['collision_trace_flag'], 'SIMPLE_AND_COMPLEX')

    def test_zero_hull_environment_is_allowed_and_noncolliding(self):
        item = next(a for a in self.p['assets'] if not a['collision_hulls'])
        mesh, report = self.mesh(item)
        placement = next(a for a in self.p['placements'] if a['asset_name'] == item['asset_name'])
        actor = f._spawn_mesh(self.u, self.c, item, mesh, placement, report)
        self.assertEqual(actor.props['static_mesh_component'].get_collision_enabled(), 'NONE')
        self.assertEqual(len(mesh.props['body_setup'].props['agg_geom'].props['convex_elems']), 0)

    def test_convex_mesh_actor_preserves_prop_tag_and_blocks_visibility(self):
        item = next(a for a in self.p['assets'] if a['kind'] == 'props')
        mesh, report = self.mesh(item)
        placement = next(a for a in self.p['placements'] if a['asset_name'] == item['asset_name'])
        actor = f._spawn_mesh(self.u, self.c, item, mesh, placement, report)
        component = actor.props['static_mesh_component']
        self.assertIn('PropActor', actor.props['tags'])
        self.assertEqual(component.get_collision_enabled(), 'QUERY_AND_PHYSICS')
        self.assertEqual(component.get_collision_response_to_channel('VISIBILITY'), 'BLOCK')

    def test_source_hash_rechecked_before_mesh_import(self):
        item = self.p['assets'][0]
        Path(item['source_path']).write_bytes(b'changed after preflight')
        with self.assertRaisesRegex(ValueError, 'changed after preflight'):
            self.mesh(item)
        self.assertEqual(self.u.events, [])

    def test_rejects_interchange_mesh_provenance(self):
        self.u.import_mutator = lambda obj: obj.props.__setitem__('asset_import_data', g.InterchangeAssetImportData())
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.mesh()

    def test_rejects_actual_path_renaming(self):
        self.u.import_mutator = lambda obj: setattr(obj, 'path', obj.path + '_1')
        with self.assertRaisesRegex(ValueError, 'identity/count'):
            self.mesh()

    def test_rejects_wrong_bounds(self):
        self.u.import_mutator = lambda obj: obj.item['bounds_cm']['max'].__setitem__(0, obj.item['bounds_cm']['max'][0] + 50)
        with self.assertRaisesRegex(Exception, '[Bb]ounds'):
            self.mesh()

    def test_rejects_wrong_hull_count(self):
        self.u.import_mutator = lambda obj: obj.props['body_setup'].props['agg_geom'].props['convex_elems'].append(g.Obj())
        with self.assertRaisesRegex(Exception, '[Cc]onvex|[Hh]ull|[Cc]ollision'):
            self.mesh()

    def test_rejects_extra_simple_collision_shapes(self):
        self.u.import_mutator = lambda obj: obj.props['body_setup'].props['agg_geom'].props[self.c.OTHER_SHAPES[0]].append(g.Obj())
        with self.assertRaisesRegex(Exception, '[Ss]hape|[Cc]ollision'):
            self.mesh()

    def test_rejects_missing_uv(self):
        self.u.import_mutator = lambda obj: setattr(obj, 'uv', 0)
        with self.assertRaisesRegex(Exception, 'UV'):
            self.mesh()

    def test_failed_import_retains_boundary_ledger_and_created_asset(self):
        self.u.raise_after_import = True
        report = f._report('test')
        with self.assertRaisesRegex(RuntimeError, 'after creation'):
            f._import_mesh(self.u, self.c, self.p['assets'][0], report)
        self.assertEqual(len(report['meshes']), 1)
        self.assertEqual(len(report['meshes'][0]['actual']), 1)
        self.assertEqual(report['meshes'][0]['actual'], report['meshes'][0]['task_paths'])
        self.assertEqual(len(self.u.assets), 1)

    def test_all_metadata_rotation_keywords_and_source_basis(self):
        report = f._report('test')
        for row in self.p['metadata']:
            actor = f._spawn_metadata(self.u, self.c, row, report)
            rotation = actor.get_actor_rotation()
            self.assertEqual([rotation.pitch, rotation.yaw, rotation.roll], row['rotation_pitch_yaw_roll_deg'])
            self.assertIn('BlenderSource:' + row['source_object'], actor.props['tags'])
        self.assertEqual(len(report['actors']), 51)
        self.assertEqual(len(self.u.spawn_records), 51)
        self.assertTrue(all(x['transient'] is False for x in self.u.spawn_records))

    def test_full_import_sequential_counts_and_unsaved_map(self):
        report = self.import_success()
        self.assertEqual(len(self.u.assets), 281)
        self.assertEqual(len(self.u.actors), 247)
        self.assertEqual(len(report['textures']), 41)
        self.assertEqual(len(report['materials']), 59)
        self.assertEqual(len(report['meshes']), 181)
        self.assertEqual(len(report['actors']), 247)
        self.assertEqual(self.u.events.count('new_blank_map'), 1)
        self.assertEqual(self.u.events.count('import_texture'), 41)
        self.assertEqual(self.u.events.count('import_mesh'), 181)
        self.assertEqual(self.u.events.count('create_material'), 59)
        self.assertEqual(len(self.u.import_tasks), 222)
        self.assertTrue(self.u.world.path.startswith('/Temp/'))
        self.assertEqual(report['saves_performed'], 0)
        self.assertFalse(report['visual_pass'])
        self.assertEqual(report['shader_compilation'], 'NOT_VERIFIED')
        self.assertEqual(report['gameplay'], 'NOT_VERIFIED')
        self.assertTrue(report['validation']['passed'])
        self.assertFalse(any('save' in e or 'delete' in e for e in self.u.events))

    def test_full_failure_stops_at_texture_and_reports_partial_assets(self):
        self.u.texture_mutator = lambda obj: obj.props.__setitem__('asset_import_data', g.InterchangeAssetImportData())
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_IMPORT_FAILED_PARTIAL')
        self.assertTrue(report['partial'])
        self.assertEqual(len(report['namespace_assets_on_failure']), 1)
        self.assertEqual(len(self.u.actors), 0)
        self.assertEqual(len(report['textures']), 1)
        self.assertFalse(any('save' in e or 'delete' in e for e in self.u.events))

    def test_second_apply_is_blocked_without_touching_created_work(self):
        self.import_success()
        previous = list(self.u.events)
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        self.assertEqual(caught.exception.report['status'], 'FULL_IMPORT_BLOCKED')
        self.assertEqual(self.u.events, previous)
        self.assertEqual(len(self.u.assets), 281)

    def test_readonly_validate_allows_dirty_full_map(self):
        self.import_success()
        dirty_map = g.Obj(); dirty_map.path = '/Temp/Untitled'
        dirty_asset = g.Obj(); dirty_asset.path = next(iter(self.u.assets))
        self.u.dirty_maps = [dirty_map]; self.u.dirty_content = [dirty_asset]
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_PASS', report)
        self.assertEqual(report['dirty_maps'], [dirty_map.path])
        self.assertEqual(report['dirty_content'], [dirty_asset.path])
        self.assertEqual(self.u.events, [])
        self.assertFalse(report['visual_pass'])

    def test_validate_diagnoses_assignment_and_actor_drift(self):
        self.import_success()
        mesh = next(a for a in self.u.assets.values() if isinstance(a, g.StaticMesh))
        mesh.materials[0] = None
        self.u.actors[0].location.x += 100
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_MISMATCH', report)
        errors = ' '.join(report['validation']['errors'])
        self.assertIn('Material slot assignment', errors)
        self.assertIn('Actor position', errors)
        self.assertEqual(self.u.events, [])


    def test_required_api_missing_blocks_before_mutation(self):
        with patch.object(g.StaticMeshComponent, 'is_simulating_physics', None):
            self.preflight_blocked('is_simulating_physics')

    def test_rejects_imported_material_slot_name_drift(self):
        self.u.import_mutator = lambda obj: obj.props['static_materials'][0].props.__setitem__('imported_material_slot_name', 'WrongSlot')
        with self.assertRaisesRegex(Exception, '[Ss]lot|[Mm]aterial'):
            self.mesh()

    def test_texture_hash_rechecked_before_import(self):
        texture = self.p['textures'][0]
        Path(texture['filename']).write_bytes(b'changed texture')
        report = f._report('test')
        with self.assertRaisesRegex(Exception, '[Hh]ash|changed'):
            self.m.import_texture(self.u, self.c, texture, report)
        self.assertEqual(self.u.events, [])

    def test_texture_virtual_streaming_readback_is_enforced(self):
        def ignore_setter(obj):
            obj.props['virtual_texture_streaming'] = True
            obj.ignore_virtual_setter = True
        self.u.texture_mutator = ignore_setter
        with self.assertRaisesRegex(Exception, '[Vv]irtual texture'):
            self.m.import_texture(self.u, self.c, self.p['textures'][0], f._report('test'))

    def test_validate_diagnoses_collision_mode_drift(self):
        self.import_success()
        actor = next(a for a in self.u.actors if type(a) is g.StaticMeshActor and
                     a.props['static_mesh_component'].get_collision_enabled() == 'QUERY_AND_PHYSICS')
        actor.props['static_mesh_component'].set_collision_enabled('NONE')
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_MISMATCH', report)
        self.assertIn('collision mode', ' '.join(report['validation']['errors']))
        self.assertEqual(self.u.events, [])

    def test_validate_diagnoses_light_settings_and_color_drift(self):
        self.import_success()
        light = next(a for a in self.u.actors if type(a) is g.PointLight)
        light.light_component.props['intensity'] += 1000
        light.light_component.props['light_color'] = g.LinearColor(1, 0, 0)
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_MISMATCH', report)
        self.assertIn('intensity', ' '.join(report['validation']['errors']))
        self.assertEqual(self.u.events, [])

    def test_validate_diagnoses_player_start_tag_drift(self):
        self.import_success()
        start = next(a for a in self.u.actors if type(a) is g.PlayerStart)
        start.props['player_start_tag'] = 'Unexpected'
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_MISMATCH', report)
        self.assertIn('PlayerStart tag', ' '.join(report['validation']['errors']))
        self.assertEqual(self.u.events, [])

    def test_all_local_lights_receive_derived_attenuation(self):
        report = f._report('test')
        for row in self.p['metadata']:
            if row['class'] in ('PointLight', 'RectLight'):
                actor = f._spawn_metadata(self.u, self.c, row, report)
                expected = max(1200., 2.*row.get('area_width_cm', 0), 2.*max(0., row['location_cm'][2]))
                self.assertEqual(actor.light_component.props['attenuation_radius'], expected)
                self.assertEqual(report['actors'][-1]['attenuation_radius_cm'], expected)

    def test_validate_blocks_wrong_saved_map(self):
        self.u.world.path = '/Game/Unrelated.Unrelated'
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_VALIDATE_BLOCKED', report)
        self.assertIn('not the full-import target', ' '.join(report['errors']))
        self.assertEqual(self.u.events, [])

    def test_metadata_wrong_rotator_mapping_is_rejected(self):
        self.u.spawn_mutator = lambda actor: setattr(actor, 'rotation', g.Rotator(roll=20, pitch=30, yaw=40))
        with self.assertRaisesRegex(ValueError, 'direction/up'):
            f._spawn_metadata(self.u, self.c, self.p['metadata'][0], f._report('test'))


    def test_spawn_boundary_exception_reports_created_actor_without_cleanup(self):
        def fail_after_creation(actor):
            raise RuntimeError('injected spawn failure after creation')
        self.u.spawn_mutator = fail_after_creation
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_IMPORT_FAILED_PARTIAL')
        self.assertEqual(len(self.u.actors), 1)
        self.assertEqual(report['current_actor_paths_on_failure'], [self.u.actors[0].get_path_name()])
        self.assertEqual(len(report['namespace_assets_on_failure']), 281)
        self.assertEqual(len(report['actors']), 1)
        self.assertEqual(report['actors'][0]['status'], 'ATTEMPTED')
        self.assertFalse(any('save' in e or 'delete' in e for e in self.u.events))


if __name__ == '__main__':
    unittest.main(verbosity=2)
