"""Portable stdlib contract and safety tests. Mocks do not prove UE runtime behavior.
The fake geometry happy path copies expected bounds; the independent measured-bounds
regression verifies rejection of the actual uncorrected UE Y-reflection failure.

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
import struct
import zlib
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass annotations resolve through the defining module
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


def binary_fixture(compressed=False, model_translation=None, invalid_tangent=False):
    """Small independently encoded FBX7400 with render and UCX geometry.

    The writer is intentionally separate from the production parser/encoder.
    It models only the frozen contract, not the whole FBX specification.
    """
    def prop(kind, value):
        if kind in ('S', 'R'):
            raw = value.encode() if isinstance(value, str) else value
            return kind.encode() + struct.pack('<I', len(raw)) + raw
        if kind in ('L', 'I', 'D'):
            fmt = {'L':'q', 'I':'i', 'D':'d'}[kind]
            return kind.encode() + struct.pack('<' + fmt, value)
        fmt = {'d':'d', 'i':'i'}[kind]
        raw = struct.pack('<' + str(len(value)) + fmt, *value)
        packed = zlib.compress(raw) if compressed else raw
        return kind.encode() + struct.pack('<III', len(value), int(compressed), len(packed)) + packed
    def node(name, properties=(), children=()):
        return (name.encode(), list(properties), list(children))
    def value_node(name, kind, value):
        return node(name, [prop(kind, value)])
    def layer(name, mapping, reference, values):
        children = [value_node('MappingInformationType','S',mapping), value_node('ReferenceInformationType','S',reference)]
        children += [value_node(key,kind,value) for key,kind,value in values]
        return node(name,[prop('I',0)],children)
    vertices = [1.,2.,3., 4.,5.,7., 8.,11.,13., 16.,17.,19.]
    normals = [1.,0.,0., 0.,1.,0., 0.,0.,1., -1.,0.,0., 0.,-1.,0., 0.,0.,-1.]
    objects=[]; connections=[]
    for index, name in enumerate(('SM_AsymmetricFixture','UCX_SM_AsymmetricFixture_00'),1):
        geometry = [value_node('Vertices','d',vertices), value_node('PolygonVertexIndex','i',[0,1,-3,0,2,-4]),
            value_node('Edges','i',[0,1,2,4,5]),
            layer('LayerElementNormal','ByPolygonVertex','Direct',[('Normals','d',normals)]),
            layer('LayerElementUV','ByPolygonVertex','IndexToDirect', [('UV','d',[.1,.2,.3,.4,.5,.6,.7,.8]),('UVIndex','i',[0,1,2,0,2,3])]),
            layer('LayerElementSmoothing','ByPolygon','Direct',[('Smoothing','i',[1,0])]),
            layer('LayerElementMaterial','ByPolygon','IndexToDirect',[('Materials','i',[0,1])])]
        if invalid_tangent:
            geometry.append(node('LayerElementTangent',[prop('I',0)]))
        objects.append(node('Geometry',[prop('L',index),prop('S',name + '\x00\x01Geometry'),prop('S','Mesh')],geometry))
        model_children=[]
        if model_translation is not None:
            transform = [prop('S',v) for v in ('Lcl Translation','Lcl Translation','','A')]
            transform += [prop('D',v) for v in model_translation]
            model_children = [node('Properties70',children=[node('P',transform)])]
        objects.append(node('Model',[prop('L',100+index),prop('S',name + '\x00\x01Model'),prop('S','Mesh')],model_children))
        connections += [node('C',[prop('S','OO'),prop('L',index),prop('L',100+index)]),
                        node('C',[prop('S','OO'),prop('L',100+index),prop('L',0)])]
    roots = [node('Objects',children=objects),node('Connections',children=connections),
             node('OpaquePreserved',[prop('S','unchanged text'),prop('R',b'opaque\x00payload'),prop('I',123)])]
    output=bytearray(b'Kaydara FBX Binary  \x00\x1a\x00'+struct.pack('<I',7400))
    def emit(n):
        name, props, children=n
        start=len(output); body=b''.join(props)
        output.extend(b'\x00'*13);output.extend(name);output.extend(body)
        for child in children:emit(child)
        if children:output.extend(b'\x00'*13)
        struct.pack_into('<IIIB',output,start,len(output),len(props),len(body),len(name))
    for n in roots:emit(n)
    output.extend(b'\x00'*13)
    offset=len(output)
    padding=(-offset-16)%16 or 16
    if padding < 4: padding += 16
    output.extend(bytes.fromhex('fabcab09d0c8d466b176fb831cf7267e'))
    output.extend(b'\x00'*padding+struct.pack('<I',7400)+b'\x00'*120+bytes.fromhex('f85a8c6adef5d97eece90ce3758f290b'))
    return bytes(output)


class PureFbxAdapterTests(unittest.TestCase):
    def geometries(self, raw):
        doc = f._fbx_parse(raw)
        objects = next(n for n in doc.nodes if n.name == b'Objects')
        return doc, [n for n in objects.children if n.name == b'Geometry']

    def values(self, node, child):
        return list(f._fbx_single(f._fbx_child(node, child)).value())

    def test_reflects_render_and_ucx_vertices_and_face_winding(self):
        original = binary_fixture()
        derived, proof = f._counterreflect_fbx(original)
        _, geometries = self.geometries(derived)
        self.assertEqual(len(geometries), 2)
        for geometry in geometries:
            self.assertEqual(self.values(geometry,b'Vertices'), [1.,-2.,3.,4.,-5.,7.,8.,-11.,13.,16.,-17.,19.])
            self.assertEqual(self.values(geometry,b'PolygonVertexIndex'), [2,1,-1,3,2,-1])
            self.assertEqual(self.values(geometry,b'Edges'), [1,0,2,3,5])
        self.assertEqual(proof['geometry_count'], 2)
        self.assertEqual(proof['vertices'], 8)
        self.assertEqual(proof['polygons'], 4)
        self.assertFalse(proof['unreal_import_tested'])
        self.assertEqual(proof['source_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(proof['derived_sha256'], hashlib.sha256(derived).hexdigest())

    def test_corner_normals_and_uv_indices_follow_reversed_winding(self):
        derived, _ = f._counterreflect_fbx(binary_fixture())
        _, geometries = self.geometries(derived)
        for geometry in geometries:
            normals = f._fbx_child(geometry,b'LayerElementNormal')
            self.assertEqual(self.values(normals,b'Normals'), [0.,0.,1.,0.,-1.,0.,1.,0.,0.,0.,0.,-1.,0.,1.,0.,-1.,0.,0.])
            uv = f._fbx_child(geometry,b'LayerElementUV')
            self.assertEqual(self.values(uv,b'UVIndex'), [2,1,0,3,2,0])
            self.assertEqual(self.values(uv,b'UV'), [.1,.2,.3,.4,.5,.6,.7,.8])
            self.assertEqual(self.values(f._fbx_child(geometry,b'LayerElementMaterial'),b'Materials'), [0,1])
            self.assertEqual(self.values(f._fbx_child(geometry,b'LayerElementSmoothing'),b'Smoothing'), [1,0])

    def test_transform_is_deterministic_and_semantically_involutive(self):
        original = binary_fixture()
        first, proof = f._counterreflect_fbx(original)
        same, same_proof = f._counterreflect_fbx(original)
        restored, _ = f._counterreflect_fbx(first)
        self.assertEqual(first,same)
        self.assertEqual(proof,same_proof)
        self.assertEqual(f._fbx_decoded_digest(f._fbx_parse(restored)), f._fbx_decoded_digest(f._fbx_parse(original)))
        self.assertEqual(restored, original)  # no compressed-array representation differences

    def test_footer_and_untouched_properties_are_preserved_exactly(self):
        original = binary_fixture()
        derived, proof = f._counterreflect_fbx(original)
        before, _ = self.geometries(original)
        after, _ = self.geometries(derived)
        self.assertEqual(before.footer, after.footer)
        self.assertTrue(proof['footer_preserved_exact'])
        before_node = next(n for n in before.nodes if n.name == b'OpaquePreserved')
        after_node = next(n for n in after.nodes if n.name == b'OpaquePreserved')
        self.assertEqual([p.encoded for p in before_node.props], [p.encoded for p in after_node.props])

    def test_compressed_fixture_preserves_footer_and_correct_geometry(self):
        original = binary_fixture(compressed=True)
        derived, proof = f._counterreflect_fbx(original)
        self.assertEqual(f._fbx_parse(original).footer, f._fbx_parse(derived).footer)
        self.assertTrue(proof['footer_preserved_exact'])
        self.assertEqual(f._counterreflect_fbx(original)[0], derived)
        _, geometries = self.geometries(derived)
        self.assertEqual(self.values(geometries[0],b'PolygonVertexIndex'), [2,1,-1,3,2,-1])

    def test_rejects_nonidentity_models_instead_of_guessing(self):
        with self.assertRaisesRegex(ValueError, 'Nonidentity Model transform'):
            f._counterreflect_fbx(binary_fixture(model_translation=(1.,0.,0.)))

    def test_rejects_unsupported_tangent_payload(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported geometry element'):
            f._counterreflect_fbx(binary_fixture(invalid_tangent=True))

    def test_rejects_unknown_version_and_truncated_footer(self):
        original = binary_fixture()
        bad = original[:23] + struct.pack('<I',7500) + original[27:]
        with self.assertRaisesRegex(ValueError, 'Only FBX7400'):
            f._counterreflect_fbx(bad)
        with self.assertRaises(ValueError):
            f._counterreflect_fbx(original[:-20])


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
        self.addCleanup(shutil.rmtree, self.u.saved_dir, True)
        self.transform_patch = patch.object(f, '_counterreflect_fbx',
            side_effect=lambda raw: (b'MOCK_COUNTER_REFLECTION\n' + raw, {'mock_transform_only': True}), create=True)
        self.transform_patch.start(); self.addCleanup(self.transform_patch.stop)
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
        with self.assertRaisesRegex(ValueError, 'Original FBX changed'):
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
        self.assertEqual(len(report['namespace_assets_on_failure']), 3)
        self.assertEqual(len(report['meshes']), 2)
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


    def test_corrected_namespace_is_distinct_from_failed_namespace(self):
        self.assertEqual(f.DEST, '/Game/AbandonedCarnivalFull57_Corrected')
        old = g.Obj(); old.path = '/Game/AbandonedCarnivalFull57/Environment/Old.Old'
        self.u.assets[old.path.split('.')[0]] = old
        (Path(self.u.content_dir) / 'AbandonedCarnivalFull57').mkdir()
        report = f.preflight(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_PREFLIGHT_PASS', report)
        self.assertIs(self.u.assets[old.path.split('.')[0]], old)
        self.assertEqual(self.u.events, [])

    def test_sentinel_geometry_precedes_all_textures_and_materials(self):
        report = self.import_success()
        self.assertEqual(report['axis_sentinels_passed'], list(f.SENTINELS))
        self.assertEqual([t.props['destination_name'] for t in self.u.import_tasks[:2]], list(f.SENTINELS))
        self.assertTrue(all(isinstance(t.props['factory'], g.FbxFactory) for t in self.u.import_tasks[:2]))
        first_texture = self.u.events.index('import_texture')
        first_material = self.u.events.index('create_material')
        self.assertEqual(self.u.events[:first_texture].count('import_mesh'), 2)
        self.assertEqual(self.u.events[:first_material].count('import_mesh'), 2)
        self.assertEqual([row['name'] for row in report['meshes'][:2]], list(f.SENTINELS))

    def test_logged_uncorrected_y_reflection_fails_first_sentinel(self):
        observed = {
            'min': [669.30615234375, 672.6940307617188, -29.212182998657227],
            'max': [1477.0469970703125, 1563.056884765625, 1282.4898681640625],
        }
        expected = next(a for a in self.p['assets'] if a['asset_name'] == f.SENTINELS[0])
        self.assertLess(expected['bounds_cm']['max'][1], 0)
        self.assertEqual(expected['collision_hulls'], 0)
        def measured_failure(mesh):
            if mesh.item['asset_name'] == f.SENTINELS[0]:
                mesh.item['bounds_cm'] = copy.deepcopy(observed)
        self.u.import_mutator = measured_failure
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        report = caught.exception.report
        self.assertIn('bounds/pivot/axis mismatch', ' '.join(report['errors']))
        self.assertEqual(report['status'], 'FULL_IMPORT_FAILED_PARTIAL')
        self.assertEqual(len(report['meshes']), 1)
        self.assertEqual(len(report['namespace_assets_on_failure']), 1)
        self.assertEqual(report['current_actor_paths_on_failure'], [])
        self.assertEqual(report['textures'], [])
        self.assertEqual(report['materials'], [])
        self.assertEqual(self.u.events.count('import_texture'), 0)
        self.assertEqual(self.u.events.count('create_material'), 0)
        self.assertEqual(len(report['derived_files']), 1)
        self.assertLess(expected['bounds_cm']['max'][1], 0)

    def test_compound_collision_sentinel_failure_stops_before_textures(self):
        expected = next(a for a in self.p['assets'] if a['asset_name'] == f.SENTINELS[1])
        self.assertEqual(expected['collision_hulls'], 21)
        def wrong_hulls(mesh):
            if mesh.item['asset_name'] == f.SENTINELS[1]:
                mesh.props['body_setup'].props['agg_geom'].props['convex_elems'].pop()
        self.u.import_mutator = wrong_hulls
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(len(report['meshes']), 2)
        self.assertEqual(len(report['namespace_assets_on_failure']), 2)
        self.assertEqual(report['textures'], [])
        self.assertEqual(report['materials'], [])
        self.assertEqual(report['actors'], [])
        self.assertNotIn('axis_sentinels_passed', report)

    def test_preflight_never_creates_derived_cache_files(self):
        saved = Path(self.u.saved_dir)
        self.assertEqual(list(saved.iterdir()), [])
        self.assertEqual(f.preflight(self.tmp.name)['status'], 'FULL_PREFLIGHT_PASS')
        self.assertEqual(list(saved.iterdir()), [])

    def test_readonly_missing_cache_is_not_recreated(self):
        with self.assertRaisesRegex(ValueError, 'read-only validation will not recreate'):
            f._derived_source(self.u, self.c, self.p['assets'][0], write=False)
        self.assertEqual(list(Path(self.u.saved_dir).iterdir()), [])
        self.assertEqual(self.u.events, [])

    def test_derived_cache_preserves_original_and_reports_provenance(self):
        item = self.p['assets'][0]
        raw = Path(item['source_path']).read_bytes()
        original = copy.deepcopy(item)
        report = f._report('test')
        derived = f._derived_source(self.u, self.c, item, report, write=True)
        self.assertEqual(item, original)
        self.assertEqual(Path(item['source_path']).read_bytes(), raw)
        self.assertEqual(derived['original_source_path'], item['source_path'])
        self.assertEqual(derived['original_fbx_sha256'], item['fbx_sha256'])
        self.assertEqual(Path(derived['source_path']).read_bytes(), b'MOCK_COUNTER_REFLECTION\n' + raw)
        self.assertNotEqual(derived['fbx_sha256'], item['fbx_sha256'])
        self.assertTrue(Path(derived['source_path']).is_relative_to(Path(self.u.saved_dir)))
        self.assertEqual(len(report['derived_files'][0]['files_written']), 2)
        metadata = json.loads(Path(report['derived_files'][0]['metadata_path']).read_text())
        self.assertEqual(metadata['original_sha256'], item['fbx_sha256'])
        self.assertEqual(metadata['derived_sha256'], derived['fbx_sha256'])
        self.assertEqual(metadata['adapter'], f.AXIS_ADAPTER)

    def test_existing_exact_cache_is_reused_without_writes(self):
        item = self.p['assets'][0]
        derived = f._derived_source(self.u, self.c, item, write=True)
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}
        report = f._report('test')
        self.assertEqual(f._derived_source(self.u, self.c, item, report, write=True), derived)
        self.assertEqual(report['derived_files'][0]['files_written'], [])
        self.assertEqual(f._derived_source(self.u, self.c, item, write=False), derived)
        after = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_conflicting_derived_fbx_is_rejected_without_overwrite(self):
        item = self.p['assets'][0]
        derived = f._derived_source(self.u, self.c, item, write=True)
        path = Path(derived['source_path']); path.write_bytes(b'conflicting existing cache')
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            f._derived_source(self.u, self.c, item, write=True)
        self.assertEqual(path.read_bytes(), b'conflicting existing cache')
        self.assertEqual(self.u.events, [])

    def test_conflicting_cache_metadata_is_rejected_without_overwrite(self):
        report = f._report('test')
        item = self.p['assets'][0]
        f._derived_source(self.u, self.c, item, report, write=True)
        path = Path(report['derived_files'][0]['metadata_path']); path.write_text('conflicting metadata')
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            f._derived_source(self.u, self.c, item, write=True)
        self.assertEqual(path.read_text(), 'conflicting metadata')

    def test_import_provenance_points_to_verified_derived_copy(self):
        item = self.p['assets'][0]
        original_bytes = Path(item['source_path']).read_bytes()
        mesh, report = self.mesh(item)
        row = report['meshes'][0]
        data = mesh.props['asset_import_data']
        self.assertEqual(data.extract_filenames(), [row['derived_source_path']])
        self.assertNotEqual(row['derived_source_path'], item['source_path'])
        self.assertEqual(row['original_source_path'], item['source_path'])
        self.assertEqual(row['original_fbx_sha256'], item['fbx_sha256'])
        self.assertEqual(Path(item['source_path']).read_bytes(), original_bytes)
        derived = f._derived_source(self.u, self.c, item, write=False)
        data.filename = item['source_path']
        with self.assertRaisesRegex(Exception, 'source path mismatch'):
            self.c._validate_mesh(self.u, mesh, derived)

    def test_validate_cannot_recreate_missing_derived_copy(self):
        self.import_success()
        cache = next(Path(self.u.saved_dir).rglob('*.fbx'))
        # Test setup simulates a missing cache file. Production never deletes it.
        cache.unlink()
        remaining = {str(p): p.read_bytes() for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_MISMATCH', report)
        self.assertIn('read-only validation will not recreate', ' '.join(report['validation']['errors']))
        self.assertFalse(cache.exists())
        self.assertEqual({str(p): p.read_bytes() for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}, remaining)
        self.assertEqual(self.u.events, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
