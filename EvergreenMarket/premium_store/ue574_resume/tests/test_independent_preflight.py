"""Independent hostile-fake and contract review. No Unreal runtime is emulated."""
import ast
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
MODULE = Path(__file__).parents[1] / 'premium_preflight574.py'
spec = importlib.util.spec_from_file_location('review_preflight574', MODULE)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

class Node:
    """Frozen fake; unimplemented engine access and every attempted write is recorded."""
    def __init__(self, name, calls, props=None, methods=None):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_calls', calls)
        object.__setattr__(self, '_props', props or {})
        object.__setattr__(self, '_methods', methods or {})
    def __getattr__(self, name):
        if name in self._methods:
            def invoke(*args, **kwargs):
                self._calls.append((self._name, name, args, kwargs))
                result = self._methods[name]
                return result(*args, **kwargs) if callable(result) else result
            return invoke
        if name in self._props:
            return self._props[name]
        self._calls.append((self._name, 'UNIMPLEMENTED:' + name, (), {}))
        raise AttributeError(name)
    def __setattr__(self, name, value):
        self._calls.append((self._name, 'WRITE:' + name, (), {}))
        raise AssertionError('Attempted fake-object mutation: ' + name)
    def get_editor_property(self, name):
        self._calls.append((self._name, 'get_editor_property', (name,), {}))
        if name not in self._props:
            raise AttributeError(name)
        return self._props[name]

class Fixture:
    def __init__(self, version='5.7.4-12345+++UE5+Release-5.7', map_path=None, dirty_after=None,
                 tags=None, simple_count=1, convex_count=1, uv_channels=1, optional_missing=False):
        self.calls = []
        n = lambda name, props=None, methods=None: Node(name, self.calls, props, methods)
        path = map_path or pp.EXPECTED_MAP
        world = n('world', methods={'get_path_name': path + '.' + path.rsplit('/',1)[-1]})
        self.world = world
        geom = n('geom', {key: [object()] if key == 'convex_elems' else [] for key in pp.SHAPE_FIELDS})
        body = n('body', {'agg_geom': geom, 'collision_trace_flag': 'CTF_USE_SIMPLE_AND_COMPLEX'})
        vector = n('vector', {'x': 1.0, 'y': 2.0, 'z': 3.0})
        bounds = n('bounds', {'origin': vector, 'box_extent': vector})
        mesh = n('mesh', {'body_setup': body}, {'get_path_name': pp.NAMESPACE + '/FullPreview574_v001/Meshes/SM_CAN.SM_CAN', 'get_bounds': bounds})
        collision = {'get_collision_enabled': 'QUERY_AND_PHYSICS', 'get_collision_profile_name': 'BlockAll',
                     'get_collision_object_type': 'ECC_WORLD_STATIC', 'get_collision_response_to_channel': lambda channel: 'ECR_BLOCK'}
        comp = n('component', {'static_mesh': mesh}, collision)
        actor = n('actor', {'tags': tags if tags is not None else ['PremiumStoreV3','V3Placement=one','V3Asset=can','V3Phase=full','Prop']},
                  {'get_world': world, 'get_components_by_class': [comp], 'get_path_name': path + '.L:PersistentLevel.A',
                   'get_actor_label': lambda create_if_none: self._label(create_if_none),
                   'get_class': n('actor_class', methods={'get_path_name': '/Script/Engine.StaticMeshActor'}),
                   'get_actor_location': vector})
        self.actor, self.mesh = actor, mesh
        actor_ss = n('actor_ss', methods={'get_all_level_actors': [actor]})
        editor_ss = n('editor_ss', methods={'get_editor_world': world, 'get_game_world': None})
        mesh_ss = n('mesh_ss', methods={'get_simple_collision_count': simple_count, 'get_convex_collision_count': convex_count, 'get_num_uv_channels': uv_channels})
        subsystems = {'UnrealEditorSubsystem': editor_ss, 'EditorActorSubsystem': actor_ss, 'StaticMeshEditorSubsystem': mesh_ss}
        dirty_reads = {'maps': 0, 'content': 0}
        def dirty(kind):
            dirty_reads[kind] += 1
            if dirty_reads[kind] > 1 and kind == 'content' and dirty_after is not None:
                if dirty_after == 'unavailable':
                    raise RuntimeError('simulated post-snapshot error')
                return [n('dirty_package', methods={'get_path_name': dirty_after})]
            return []
        dirty_api = n('dirty_api', methods={'get_dirty_map_packages': lambda: dirty('maps'), 'get_dirty_content_packages': lambda: dirty('content')})
        registry = n('registry', methods={'get_assets_by_path': [], 'is_loading_assets': False})
        props = {key: key for key in subsystems}
        props.update(SystemLibrary=n('system', methods={'get_engine_version': version}),
                     EditorLoadingAndSavingUtils=dirty_api,
                     AssetRegistryHelpers=n('registry_helpers', methods={'get_asset_registry': registry}),
                     EditorLevelLibrary=n('level_library', methods={'get_pie_worlds': []}),
                     StaticMeshComponent='StaticMeshComponent',
                     CollisionChannel=n('channels', {'ECC_PAWN': 'ECC_PAWN', 'ECC_VISIBILITY': 'ECC_VISIBILITY'}))
        if optional_missing:
            props.pop('AssetRegistryHelpers')
            props.pop('EditorLevelLibrary')
        self.u = n('unreal', props, {'get_editor_subsystem': lambda cls: subsystems[cls]})
    def _label(self, create_if_none):
        if create_if_none:
            self.calls.append(('actor', 'MUTATED_LABEL', (), {}))
            raise AssertionError('label creation')
        return ''
    def inspect(self, **kwargs):
        # A one-placement miniature tests the report logic, not the real map's counts.
        expected = {key: (1 if key in ('placements','prop_placements','canonical_asset_ids','canonical_mesh_paths') else 0) for key in pp.SOURCE_COUNTS}
        with patch.object(pp, 'SOURCE_COUNTS', expected), patch.object(pp, 'SOURCE_CONVEX_TOTAL', 1):
            result = pp.inspect(unreal_module=self.u, **kwargs)
        json.dumps(result, allow_nan=False)
        return result

class IndependentReview(unittest.TestCase):
    def test_ast_has_no_mutators_files_network_or_dynamic_eval(self):
        tree = ast.parse(MODULE.read_text())
        forbidden = ('set_', 'save_', 'load_', 'import_', 'spawn_', 'destroy_', 'delete_', 'duplicate_', 'new_', 'scan_', 'search_all_assets', 'wait_for_completion', 'line_trace', 'sphere_trace')
        errors = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ''
                if name.startswith(forbidden) or name in {'open','exec','eval','__import__','get_asset'}:
                    errors.append((node.lineno, name))
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module]
                self.assertTrue(all(x in {'collections','math','re','unreal'} for x in names), names)
        self.assertEqual(errors, [])
        self.assertFalse(any(x.startswith(forbidden) for x in pp.READ_METHODS))
    def test_happy_snapshot_does_not_mutate(self):
        fixture = Fixture()
        result = fixture.inspect()
        self.assertEqual(result['status'], 'READ_ONLY_SNAPSHOT_COMPLETE_RUNTIME_UNVERIFIED')
        self.assertTrue(result['dirty_snapshot_unchanged'])
        self.assertFalse(result['pie']['trace']['executed'])
        self.assertEqual(result['missing_data'], [])
        self.assertFalse(any(call[1].startswith(('WRITE:','MUTATED')) for call in fixture.calls))
        self.assertTrue(all(call[2] == (False,) for call in fixture.calls if call[1] == 'get_actor_label'))
    def test_wrong_map_does_not_enumerate_actors(self):
        for path in ('/Game/AbandonedCarnivalFull57_Corrected/Maps/AbandonedCarnivalFull57', '/Game/PremiumStoreV3Evil/Maps/L_V3_AllPlacements'):
            fixture = Fixture(map_path=path)
            result = fixture.inspect()
            self.assertEqual(result['status'], 'OPEN_PREMIUM_MAP_FIRST')
            self.assertFalse(any(call[1] == 'get_all_level_actors' for call in fixture.calls))
    def test_exact_engine_version(self):
        for value in ('5.8.0', '5.7.40', '5.7.4.1', '5.7.4garbage', '5.7.3', '15.7.4'):
            with self.subTest(version=value):
                result = Fixture(version=value).inspect()
                self.assertEqual(result['engine']['status'], 'WRONG_ENGINE_VERSION')
                self.assertEqual(result['status'], 'BLOCKED_ENGINE_VERSION')
    def test_negative_simple_collision_result_is_unavailable(self):
        result = Fixture(simple_count=-1).inspect()
        self.assertNotEqual(result['status'], 'READ_ONLY_SNAPSHOT_COMPLETE_RUNTIME_UNVERIFIED')
        self.assertTrue(result['missing_data'])
    def test_negative_convex_collision_result_is_unavailable(self):
        result = Fixture(convex_count=-1).inspect()
        self.assertTrue(result['missing_data'])
    def test_negative_uv_result_is_unavailable(self):
        result = Fixture(uv_channels=-1).inspect()
        self.assertTrue(result['missing_data'])
    def test_changed_dirty_after_not_complete(self):
        result = Fixture(dirty_after='/Game/Other/Changed').inspect()
        self.assertFalse(result['dirty_snapshot_unchanged'])
        self.assertNotEqual(result['status'], 'READ_ONLY_SNAPSHOT_COMPLETE_RUNTIME_UNVERIFIED')
    def test_unknown_dirty_after_not_complete(self):
        result = Fixture(dirty_after='unavailable').inspect()
        self.assertIsNone(result['dirty_snapshot_unchanged'])
        self.assertNotEqual(result['status'], 'READ_ONLY_SNAPSHOT_COMPLETE_RUNTIME_UNVERIFIED')
    def test_empty_tag_identity_is_malformed(self):
        for empty in ('V3Placement=', 'V3Asset='):
            tags = ['PremiumStoreV3', 'V3Placement=one', 'V3Asset=can', 'V3Phase=full', 'Prop']
            prefix = empty.split('=')[0] + '='
            tags = [empty if value.startswith(prefix) else value for value in tags]
            result = Fixture(tags=tags).inspect()
            self.assertGreater(result['placements']['exceptions']['counts_by_code'].get('OWNERSHIP_TAGS_MALFORMED', 0), 0)
    def test_optional_apis_missing_report_unknown(self):
        result = Fixture(optional_missing=True).inspect()
        self.assertEqual(result['asset_registry']['status'], 'UNAVAILABLE')
        self.assertEqual(result['pie']['status'], 'PIE_STATE_UNAVAILABLE')
        self.assertTrue(result['missing_data'])
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
    def test_max_items_rejects_bool_zero_and_excess(self):
        for value in (True, 0, -1, 101, 1.5):
            with self.assertRaises(ValueError):
                pp.inspect(unreal_module=Fixture().u, max_items=value)
    def test_read_allowlist_rejects_mutation_before_call(self):
        fixture = Fixture()
        with self.assertRaisesRegex(RuntimeError, 'Non-read API rejected'):
            pp._Read().call(fixture.actor, 'set_actor_label', 'new')
        self.assertFalse(any(call[1] == 'set_actor_label' for call in fixture.calls))

if __name__ == '__main__':
    unittest.main(verbosity=2)
