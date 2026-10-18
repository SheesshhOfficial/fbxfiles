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
import re
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

    def test_slot_aliases_are_only_three_explicit_source_spellings(self):
        self.assertEqual(f._slot_aliases('Aged tan plush fabric.001'),
                         {'Aged tan plush fabric.001', 'Aged tan plush fabric_001', 'Aged_tan_plush_fabric_001'})

    def test_slot_alias_collision_in_another_mesh_material_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '[Aa]mbigu|[Cc]ollision'):
            f._check_slot_names(['A_B'], ['A.B'], universe=['A.B', 'A_B'])

    def test_exact_slot_name_cannot_hide_cross_source_alias_collision(self):
        with self.assertRaisesRegex(ValueError, '[Aa]mbigu|[Cc]ollision'):
            f._check_slot_names(['A_B'], ['A_B'], universe=['A.B', 'A_B'])

    def test_repeated_same_source_slots_are_not_ambiguous(self):
        f._check_slot_names(['A_B', 'A_B'], ['A.B', 'A.B'], universe=['A.B', 'A.B'])

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

    def teddy_item(self):
        return next(a for a in self.p['assets'] if a['materials'][0] == 'Aged tan plush fabric.001')

    def set_imported_slot_names(self, names):
        def mutate(mesh):
            mesh.props['static_materials'] = [g.Obj(imported_material_slot_name=name) for name in names]
        self.u.import_mutator = mutate

    def test_original_material_slot_names_remain_valid(self):
        item = self.teddy_item()
        mesh, report = self.mesh(item)
        self.assertEqual(report['meshes'][0]['imported_material_slot_names'], item['materials'])
        self.assertEqual([slot.props['imported_material_slot_name'] for slot in mesh.props['static_materials']], item['materials'])

    def test_native_dot_only_slot_alias_preserves_spaces_and_source(self):
        item = self.teddy_item()
        before = copy.deepcopy(item)
        names = [name.replace('.', '_') for name in item['materials']]
        self.assertEqual(names[0], 'Aged tan plush fabric_001')
        self.set_imported_slot_names(names)
        mesh, report = self.mesh(item)
        self.assertEqual(report['meshes'][0]['imported_material_slot_names'], names)
        self.assertEqual([slot.props['imported_material_slot_name'] for slot in mesh.props['static_materials']], names)
        self.assertEqual(item, before)

    def test_legacy_all_nonalphanumeric_slot_alias_remains_valid(self):
        item = self.teddy_item()
        names = [re.sub(r'[^A-Za-z0-9_]', '_', name) for name in item['materials']]
        self.set_imported_slot_names(names)
        _, report = self.mesh(item)
        self.assertEqual(report['meshes'][0]['imported_material_slot_names'], names)

    def test_mixed_exact_and_known_slot_aliases_remain_valid(self):
        item = self.teddy_item()
        names = [item['materials'][0].replace('.', '_'), item['materials'][1],
                 re.sub(r'[^A-Za-z0-9_]', '_', item['materials'][2])]
        self.set_imported_slot_names(names)
        _, report = self.mesh(item)
        self.assertEqual(report['meshes'][0]['imported_material_slot_names'], names)

    def test_known_slot_aliases_still_require_exact_slot_order(self):
        item = self.teddy_item()
        names = [name.replace('.', '_') for name in item['materials']]
        names[0], names[2] = names[2], names[0]
        self.set_imported_slot_names(names)
        with self.assertRaisesRegex(Exception, '[Ss]lot|[Mm]aterial'):
            self.mesh(item)

    def test_slot_alias_does_not_accept_case_suffix_or_partial_normalization(self):
        item = self.teddy_item()
        for wrong in ('aged tan plush fabric_001', 'Aged tan plush fabric_001_1',
                      'Aged_tan plush fabric_001', 'Aged tan plush fabric_002',
                      'Aged tan plush fabric001'):
            with self.subTest(wrong=wrong):
                self.u.assets.clear()
                self.set_imported_slot_names([wrong] + item['materials'][1:])
                with self.assertRaisesRegex(Exception, '[Ss]lot|[Mm]aterial'):
                    self.mesh(item)

    def test_cross_source_slot_alias_collision_is_rejected(self):
        item = self.teddy_item()
        item['materials'] = ['A.B', 'A_B']
        self.set_imported_slot_names(['A_B', 'A_B'])
        with self.assertRaisesRegex(Exception, '[Aa]mbigu|[Cc]ollision'):
            self.mesh(item)

    def test_cross_source_legacy_slot_alias_collision_is_rejected(self):
        item = self.teddy_item()
        item['materials'] = ['A B', 'A-B']
        self.set_imported_slot_names(['A_B', 'A_B'])
        with self.assertRaisesRegex(Exception, '[Aa]mbigu|[Cc]ollision'):
            self.mesh(item)

    def test_readonly_validation_accepts_dot_only_aliases_without_rewriting(self):
        report = self.import_success()
        self.assertEqual(report['status'], 'FULL_IMPORT_CREATED_UNSAVED')
        changed = []
        for mesh in self.u.assets.values():
            if isinstance(mesh, g.StaticMesh):
                for slot in mesh.props['static_materials']:
                    old = slot.props['imported_material_slot_name']
                    if '.' in old:
                        slot.props['imported_material_slot_name'] = old.replace('.', '_')
                        changed.append((slot, slot.props['imported_material_slot_name']))
        self.assertGreater(len(changed), 0)
        self.u.events.clear()
        report = f.validate(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_STRUCTURE_PASS', report)
        self.assertTrue(all(slot.props['imported_material_slot_name'] == name for slot, name in changed))
        self.assertEqual(self.u.events, [])

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

    def resume_checkpoint(self):
        """Replay import up to the independently fixed native Teddy failure boundary.

        This fixture exercises the same importer and real fake-engine object inventory.
        It does not claim the mock proves the historical native checkpoint is intact.
        """
        real_import = f._import_mesh
        def stop_after_teddy(u, core, item, report):
            mesh = real_import(u, core, item, report)
            if item['asset_name'] == 'SM_TeddyPrize_7adfe5d511':
                raise ValueError('injected historical Teddy slot-name checkpoint')
            return mesh
        with patch.object(f, '_import_mesh', side_effect=stop_after_teddy):
            with self.assertRaises(f.FullImportError) as caught:
                f.import_full(self.tmp.name)
        self.assertEqual(caught.exception.report['status'], 'FULL_IMPORT_FAILED_PARTIAL')
        self.assertEqual(len(self.u.assets), 168)
        self.assertEqual(sum(isinstance(o, g.StaticMesh) for o in self.u.assets.values()), 68)
        self.assertEqual(sum(isinstance(o, g.Texture2D) for o in self.u.assets.values()), 41)
        self.assertEqual(sum(isinstance(o, g.Material) for o in self.u.assets.values()), 59)
        self.assertEqual(self.u.actors, [])
        self.u.world.path = '/Temp/Untitled_3.Untitled'
        self.u.existing_namespace = True
        dirty_map = g.Obj(); dirty_map.path = '/Temp/Untitled_3'
        self.u.dirty_maps = [dirty_map]
        self.u.dirty_content = []
        for path in self.u.assets:
            package = g.Obj(); package.path = path
            self.u.dirty_content.append(package)
        for mesh in self.u.assets.values():
            if isinstance(mesh, g.StaticMesh):
                for slot in mesh.props['static_materials']:
                    slot.props['imported_material_slot_name'] = slot.props['imported_material_slot_name'].replace('.', '_')
        self.u.events.clear()
        self.u.import_tasks.clear()
        return caught.exception.report

    def resume_mesh(self, name=None):
        name = name or self.p['assets'][0]['asset_name']
        return next(o for o in self.u.assets.values() if isinstance(o, g.StaticMesh) and o.item['asset_name'] == name)

    def assert_resume_blocked(self, expected=None):
        self.u.events.clear()
        before_assets = dict(self.u.assets)
        before_actors = list(self.u.actors)
        before_world = self.u.world
        before_files = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                        for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}
        before_assignments = {path: list(obj.materials) for path, obj in self.u.assets.items() if isinstance(obj, g.StaticMesh)}
        with self.assertRaises(f.FullImportError) as caught:
            f.resume_full(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_RESUME_BLOCKED', report)
        self.assertFalse(report['mutation_started'])
        if expected:
            self.assertRegex(' '.join(report['errors']), expected)
        self.assertEqual(self.u.events, [])
        self.assertEqual(self.u.assets, before_assets)
        self.assertEqual(self.u.actors, before_actors)
        self.assertIs(self.u.world, before_world)
        self.assertEqual({str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                          for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}, before_files)
        self.assertEqual({path: list(obj.materials) for path, obj in self.u.assets.items() if isinstance(obj, g.StaticMesh)}, before_assignments)
        return report

    def test_resume_exact_checkpoint_imports_only_missing_meshes_in_same_world(self):
        self.resume_checkpoint()
        existing = dict(self.u.assets)
        completed = [self.resume_mesh(item['asset_name']) for item in self.p['assets'][:65]]
        completed_setters = [list(mesh.material_set_calls) for mesh in completed]
        world = self.u.world
        old_files = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                     for p in Path(self.u.saved_dir).rglob('*') if p.is_file()}
        report = f.resume_full(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_RESUME_CREATED_UNSAVED', report)
        self.assertIs(self.u.world, world)
        self.assertTrue(all(self.u.assets[path] is obj for path, obj in existing.items()))
        self.assertEqual(len(self.u.assets), 281)
        self.assertEqual(len(self.u.actors), 247)
        self.assertEqual(len(report['reused_assets']), 168)
        self.assertEqual(len(report['meshes']), 113)
        self.assertEqual(report['textures'], [])
        self.assertEqual(report['materials'], [])
        self.assertEqual({row['name'] for row in report['completed_assignment_changes']},
                         set(f.SENTINELS) | {'SM_TeddyPrize_7adfe5d511'})
        self.assertEqual([mesh.material_set_calls for mesh in completed], completed_setters)
        self.assertEqual(self.u.events.count('import_mesh'), 113)
        self.assertEqual(len(self.u.import_tasks), 113)
        self.assertTrue(all(isinstance(task.props['factory'], g.FbxFactory) for task in self.u.import_tasks))
        for forbidden in ('import_texture', 'create_material', 'create_material_expression',
                          'connect_material_property', 'connect_material_expressions',
                          'request_shader_compile', 'new_blank_map'):
            self.assertNotIn(forbidden, self.u.events)
        self.assertEqual({path: (Path(path).read_bytes(), Path(path).stat().st_mtime_ns) for path in old_files}, old_files)
        self.assertFalse(any('save' in e or 'delete' in e or 'destroy' in e for e in self.u.events))
        self.assertEqual(report['saves_performed'], 0)
        self.assertFalse(report['visual_pass'])
        self.assertEqual(report['shader_compilation'], 'NOT_VERIFIED')
        self.assertIn('NOT_PERFORMED', report['material_graph_retraversal'])
        self.assertEqual(f.validate(self.tmp.name)['status'], 'FULL_STRUCTURE_PASS')

    def test_resume_accepts_engine_default_only_for_three_unassigned_meshes(self):
        self.resume_checkpoint()
        for name in (*f.SENTINELS, 'SM_TeddyPrize_7adfe5d511'):
            mesh = self.resume_mesh(name)
            self.assertTrue(all(material is None for material in mesh.materials))
            mesh.materials[:] = [self.u.default_material] * len(mesh.materials)
        report = f.resume_full(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_RESUME_CREATED_UNSAVED', report)

    def test_resume_normal_import_still_refuses_checkpoint(self):
        self.resume_checkpoint()
        with self.assertRaises(f.FullImportError) as caught:
            f.import_full(self.tmp.name)
        self.assertEqual(caught.exception.report['status'], 'FULL_IMPORT_BLOCKED')
        self.assertEqual(self.u.events, [])

    def test_resume_blocks_other_unsaved_or_saved_world_without_mutation(self):
        self.resume_checkpoint()
        for path in ('/Temp/Untitled.Untitled', '/Temp/Untitled_4.Untitled', '/Game/Other.Other'):
            with self.subTest(path=path):
                self.u.world.path = path
                self.assert_resume_blocked()

    def test_resume_blocks_play_world(self):
        self.resume_checkpoint()
        self.u.game_world = g.World()
        self.assert_resume_blocked('[Pp]lay|[Ss]imulate|PIE')

    def test_resume_blocks_any_authored_actor_even_without_import_tag(self):
        self.resume_checkpoint()
        actor = g.StaticMeshActor(); actor.path = self.u.world.path + ':UnrelatedActor'
        self.u.actors.append(actor)
        self.assert_resume_blocked('[Aa]ctor|[Ee]mpty')

    def test_resume_blocks_unrelated_dirty_map(self):
        self.resume_checkpoint()
        other = g.Obj(); other.path = '/Game/UserWork'
        self.u.dirty_maps.append(other)
        self.assert_resume_blocked('[Dd]irty|[Mm]ap')

    def test_resume_blocks_unrelated_dirty_content(self):
        self.resume_checkpoint()
        other = g.Obj(); other.path = '/Game/UserWork/Material'
        self.u.dirty_content.append(other)
        self.assert_resume_blocked('[Dd]irty|[Pp]ackage')

    def test_resume_blocks_new_extra_namespace_asset(self):
        self.resume_checkpoint()
        other = g.Obj(); other.path = f.DEST + '/Props/Untracked.Untracked'
        self.u.assets[other.path.split('.')[0]] = other
        self.assert_resume_blocked('[Ii]nventory|[Aa]sset|[Cc]heckpoint')

    def test_resume_blocks_unregistered_missing_mesh_package_with_mixed_case(self):
        self.resume_checkpoint()
        missing = self.p['assets'][66]
        folder = 'Props' if missing['kind'] == 'props' else 'Environment'
        physical = (Path(self.u.content_dir) / f.DEST.removeprefix('/Game/').swapcase() /
                    folder.swapcase() / (missing['asset_name'].swapcase() + '.UaSsEt'))
        physical.parent.mkdir(parents=True)
        physical.write_bytes(b'unregistered user package must not be overwritten')
        self.assert_resume_blocked('[Pp]hysical|[Dd]isk|[Ff]ile|[Pp]ackage|[Uu]nexpected')
        self.assertEqual(physical.read_bytes(), b'unregistered user package must not be overwritten')

    def test_resume_blocks_unexpected_physical_map_package(self):
        self.resume_checkpoint()
        physical = Path(self.u.content_dir) / f.DEST.removeprefix('/Game/') / 'Maps' / 'Existing.umap'
        physical.parent.mkdir(parents=True)
        physical.write_bytes(b'unregistered map')
        self.assert_resume_blocked('[Pp]hysical|[Dd]isk|[Ff]ile|[Pp]ackage|[Uu]nexpected')
        self.assertEqual(physical.read_bytes(), b'unregistered map')

    def test_resume_blocks_nested_physical_namespace_symlink(self):
        self.resume_checkpoint()
        target = Path(self.u.content_dir) / 'UnrelatedContent'
        target.mkdir()
        namespace = Path(self.u.content_dir) / f.DEST.removeprefix('/Game/')
        namespace.mkdir()
        link = namespace / 'LinkedSubfolder'
        link.symlink_to(target, target_is_directory=True)
        self.assert_resume_blocked('[Ss]ymlink|[Ll]ink')
        self.assertTrue(link.is_symlink())

    def test_resume_blocks_missing_checkpoint_mesh_material_or_texture(self):
        self.resume_checkpoint()
        for cls in (g.StaticMesh, g.Material, g.Texture2D):
            path = next(path for path, obj in self.u.assets.items() if isinstance(obj, cls))
            obj = self.u.assets.pop(path)
            with self.subTest(cls=cls.__name__):
                self.assert_resume_blocked()
            self.u.assets[path] = obj

    def test_resume_blocks_wrong_asset_type_even_at_expected_path(self):
        self.resume_checkpoint()
        path = next(path for path, obj in self.u.assets.items() if isinstance(obj, g.StaticMesh))
        wrong = g.Obj(); wrong.path = self.u.assets[path].path
        self.u.assets[path] = wrong
        self.assert_resume_blocked()

    def test_resume_blocks_completed_mesh_assignment_drift(self):
        self.resume_checkpoint()
        mesh = self.resume_mesh()
        self.assertIsInstance(mesh.materials[0], g.Material)
        mesh.materials[0] = None
        self.assert_resume_blocked('[Aa]ssign|[Mm]aterial')

    def test_resume_blocks_foreign_material_on_pending_mesh(self):
        self.resume_checkpoint()
        foreign = g.MaterialInterface(); foreign.path = '/Game/UserWork/Material.Material'
        self.resume_mesh('SM_TeddyPrize_7adfe5d511').materials[0] = foreign
        self.assert_resume_blocked('[Aa]ssign|[Mm]aterial')

    def test_resume_blocks_geometry_drift_before_any_new_import(self):
        self.resume_checkpoint()
        mesh = self.resume_mesh()
        mesh.item['bounds_cm']['max'][0] += 50
        self.assert_resume_blocked('[Bb]ounds|[Gg]eometry')

    def test_resume_blocks_collision_drift_before_any_new_import(self):
        self.resume_checkpoint()
        mesh = self.resume_mesh()
        mesh.props['body_setup'].props['agg_geom'].props['convex_elems'].append(g.Obj())
        self.assert_resume_blocked('[Cc]onvex|[Hh]ull|[Cc]ollision')

    def test_resume_blocks_uv_drift_before_any_new_import(self):
        self.resume_checkpoint()
        self.resume_mesh().uv = 0
        self.assert_resume_blocked('UV')

    def test_resume_blocks_build_setting_drift_without_repair(self):
        self.resume_checkpoint()
        mesh = self.resume_mesh()
        key = next(key for key, value in self.c.BUILD_FIELDS.items() if isinstance(value, bool))
        mesh.build.props[key] = not mesh.build.props[key]
        self.assert_resume_blocked()
        self.assertNotEqual(mesh.build.props[key], self.c.BUILD_FIELDS[key])

    def test_resume_blocks_import_settings_drift_without_repair(self):
        self.resume_checkpoint()
        mesh = self.resume_mesh()
        mesh.props['asset_import_data'].props['import_uniform_scale'] = 2.
        self.assert_resume_blocked()
        self.assertEqual(mesh.props['asset_import_data'].props['import_uniform_scale'], 2.)

    def test_resume_blocks_mesh_source_provenance_drift(self):
        self.resume_checkpoint()
        mesh = self.resume_mesh()
        mesh.props['asset_import_data'].filename = mesh.item['source_path']
        self.assert_resume_blocked('[Ss]ource|[Pp]rovenance')

    def test_resume_blocks_missing_cache_without_recreating_it(self):
        self.resume_checkpoint()
        path = Path(self.resume_mesh().props['asset_import_data'].filename)
        path.unlink()
        self.assert_resume_blocked('[Cc]ache|[Dd]erived|recreate')
        self.assertFalse(path.exists())

    def test_resume_blocks_changed_original_source_before_mutation(self):
        self.resume_checkpoint()
        Path(self.p['assets'][0]['source_path']).write_bytes(b'changed after native attempt')
        self.assert_resume_blocked('[Hh]ash|[Cc]hanged|[Ss]ource')

    def test_resume_blocks_texture_setting_drift_without_repair(self):
        self.resume_checkpoint()
        texture = next(o for o in self.u.assets.values() if isinstance(o, g.Texture2D))
        texture.props['virtual_texture_streaming'] = True
        self.assert_resume_blocked('[Tt]exture|[Ss]etting')
        self.assertTrue(texture.props['virtual_texture_streaming'])

    def test_resume_blocks_texture_source_drift(self):
        self.resume_checkpoint()
        texture = next(o for o in self.u.assets.values() if isinstance(o, g.Texture2D))
        texture.props['asset_import_data'].filename = str(Path(self.tmp.name) / 'wrong.png')
        self.assert_resume_blocked('[Tt]exture|[Ss]ource')

    def test_resume_blocks_texture_provenance_drift(self):
        self.resume_checkpoint()
        texture = next(o for o in self.u.assets.values() if isinstance(o, g.Texture2D))
        texture.props['asset_import_data'] = g.InterchangeAssetImportData(texture.props['asset_import_data'].filename)
        self.assert_resume_blocked('[Tt]exture|[Pp]rovenance')

    def test_resume_blocks_material_policy_drift_without_repair(self):
        self.resume_checkpoint()
        material = next(o for o in self.u.assets.values() if isinstance(o, g.Material))
        material.props['two_sided'] = not material.props['two_sided']
        wrong = material.props['two_sided']
        self.assert_resume_blocked('[Mm]aterial|[Ss]ided')
        self.assertEqual(material.props['two_sided'], wrong)

    def test_resume_blocks_glass_policy_drift_without_repair(self):
        self.resume_checkpoint()
        material = next(o for o in self.u.assets.values() if isinstance(o, g.Material) and o.props['blend_mode'] == 'TRANSLUCENT')
        material.props['refraction_method'] = 'PIXEL_NORMAL_OFFSET'
        self.assert_resume_blocked('[Mm]aterial|[Gg]lass|[Rr]efraction')

    def test_resume_new_import_failure_retains_partial_boundary_without_cleanup(self):
        self.resume_checkpoint()
        previous = dict(self.u.assets)
        self.u.raise_after_import = True
        with self.assertRaises(f.FullImportError) as caught:
            f.resume_full(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_RESUME_FAILED_PARTIAL', report)
        self.assertTrue(report['mutation_started'])
        self.assertTrue(report['partial'])
        self.assertEqual(len(self.u.assets), 169)
        self.assertTrue(all(self.u.assets[path] is obj for path, obj in previous.items()))
        self.assertEqual(self.u.actors, [])
        self.assertEqual(self.u.events.count('import_mesh'), 1)
        self.assertFalse(any('save' in e or 'delete' in e or 'destroy' in e for e in self.u.events))

    def test_resume_cannot_run_again_after_successful_actor_placement(self):
        self.resume_checkpoint()
        self.assertEqual(f.resume_full(self.tmp.name)['status'], 'FULL_RESUME_CREATED_UNSAVED')
        self.assert_resume_blocked()

class RestartRecoveryTests(unittest.TestCase):
    """Restart recovery contract, with fake saved packages and unrelated saved map.

    These files are portable persistence fixtures, not valid Unreal packages.
    They establish guard/order policy only, not native loading or durability.
    """
    @classmethod
    def setUpClass(cls):
        cls.c, cls.m = f._vendors()

    def setUp(self):
        MockEngineTests.setUp(self)

    def resume_checkpoint(self):
        return MockEngineTests.resume_checkpoint(self)

    def resume_mesh(self, name=None):
        return MockEngineTests.resume_mesh(self, name)

    def restart_checkpoint(self):
        self.resume_checkpoint()
        self.saved_packages = {}
        for package in self.u.assets:
            path = Path(self.u.content_dir) / (package.removeprefix('/Game/') + '.uasset')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('fake saved checkpoint package: ' + package).encode())
            self.saved_packages[package] = path
        self.u.dirty_maps = []
        self.u.dirty_content = []
        self.u.world.path = '/Game/ExistingUserMap.ExistingUserMap'
        actor = g.StaticMeshActor()
        actor.path = self.u.world.path + ':ExistingUserActor'
        actor.props['tags'] = ['UnrelatedUserTag']
        actor.label = 'Keep this existing saved actor'
        self.u.actors.append(actor)
        return actor

    def file_snapshot(self):
        result = {}
        for root in (self.u.content_dir, self.u.saved_dir):
            for path in Path(root).rglob('*'):
                if path.is_symlink():
                    result[str(path)] = ('symlink', os.readlink(path))
                elif path.is_file():
                    result[str(path)] = ('file', path.read_bytes(), path.stat().st_mtime_ns)
        return result

    def assert_restart_blocked(self, expected=None):
        self.u.events.clear()
        before_assets = dict(self.u.assets)
        before_actors = list(self.u.actors)
        before_world = self.u.world
        before_files = self.file_snapshot()
        before_assignments = {path: list(obj.materials) for path, obj in self.u.assets.items()
                              if isinstance(obj, g.StaticMesh)}
        with self.assertRaises(f.FullImportError) as caught:
            f.resume_after_restart(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_RESTART_RESUME_BLOCKED', report)
        self.assertFalse(report['mutation_started'])
        self.assertFalse(report['partial'])
        self.assertEqual(report['saves_performed'], 0)
        if expected:
            self.assertRegex(' '.join(report['errors']), expected)
        self.assertEqual(self.u.events, [])
        self.assertEqual(self.u.assets, before_assets)
        self.assertEqual(self.u.actors, before_actors)
        self.assertIs(self.u.world, before_world)
        self.assertEqual(self.file_snapshot(), before_files)
        self.assertEqual({path: list(obj.materials) for path, obj in self.u.assets.items()
                          if isinstance(obj, g.StaticMesh)}, before_assignments)
        return report

    def test_restart_reuses_saved_checkpoint_in_new_world_and_preserves_old_actors(self):
        actor = self.restart_checkpoint()
        old_world, old_actor_list = self.u.world, self.u.actors
        old_actor_props = dict(actor.props)
        old_files = self.file_snapshot()
        existing = dict(self.u.assets)
        completed = [self.resume_mesh(item['asset_name']) for item in self.p['assets'][:65]]
        old_setters = [list(mesh.material_set_calls) for mesh in completed]
        report = f.resume_after_restart(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_RESTART_RESUME_CREATED_UNSAVED', report)
        self.assertEqual(report['mode'], 'resume_after_restart')
        self.assertIsNot(self.u.world, old_world)
        self.assertFalse(self.u.world.path.startswith('/Game/'))
        self.assertEqual(old_world.path, '/Game/ExistingUserMap.ExistingUserMap')
        self.assertEqual(old_actor_list, [actor])
        self.assertEqual(actor.props, old_actor_props)
        self.assertEqual(actor.label, 'Keep this existing saved actor')
        self.assertNotIn(actor, self.u.actors)
        self.assertTrue(all(self.u.assets[path] is obj for path, obj in existing.items()))
        self.assertEqual(len(self.u.assets), 281)
        self.assertEqual(len(self.u.actors), 247)
        self.assertEqual(len(report['reused_assets']), 168)
        self.assertEqual(len(report['reused_mesh_checks']), 68)
        self.assertEqual(len(report['meshes']), 113)
        self.assertEqual(report['textures'], [])
        self.assertEqual(report['materials'], [])
        self.assertEqual({row['name'] for row in report['completed_assignment_changes']},
                         set(f.SENTINELS) | {f.RESUME_FAILED_MESH})
        self.assertTrue(all(row['status'] == 'ASSIGNED_UNSAVED' for row in report['completed_assignment_changes']))
        self.assertEqual([mesh.material_set_calls for mesh in completed], old_setters)
        self.assertEqual(self.u.events[0], 'new_blank_map')
        self.assertEqual(self.u.events.count('new_blank_map'), 1)
        self.assertEqual(self.u.events.count('import_mesh'), 113)
        self.assertEqual(len(self.u.import_tasks), 113)
        for task in self.u.import_tasks:
            self.assertIsInstance(task.props['factory'], g.FbxFactory)
            for key in ('save', 'replace_existing', 'replace_existing_settings'):
                self.assertIs(task.props[key], False)
        for forbidden in ('import_texture', 'create_material', 'create_material_expression',
                          'connect_material_property', 'connect_material_expressions', 'request_shader_compile'):
            self.assertNotIn(forbidden, self.u.events)
        self.assertFalse(any('save' in e or 'delete' in e or 'destroy' in e for e in self.u.events))
        self.assertEqual({path: self.file_snapshot()[path] for path in old_files}, old_files)
        self.assertEqual(report['saves_performed'], 0)
        self.assertFalse(report['visual_pass'])
        self.assertEqual(report['shader_compilation'], 'NOT_VERIFIED')
        self.assertIn('NOT_PERFORMED', report['material_graph_retraversal'])
        self.assertEqual(f.validate(self.tmp.name)['status'], 'FULL_STRUCTURE_PASS')

    def test_restart_checks_all_168_assets_and_68_caches_before_new_map(self):
        self.restart_checkpoint()
        counters = dict(material=0, texture=0, mesh=0, cache=0, sentinel=0)
        def counted(kind, original):
            def call(*args, **kwargs):
                counters[kind] += 1
                return original(*args, **kwargs)
            return call
        real_new = self.u.EditorLoadingAndSavingUtils.new_blank_map
        def observed_new(save_existing_map):
            self.assertEqual(counters, dict(material=59, texture=41, mesh=68, cache=68, sentinel=2))
            self.assertEqual(self.u.events, [])
            self.assertIs(save_existing_map, False)
            return real_new(save_existing_map)
        with patch.object(f, '_check_reused_material', side_effect=counted('material', f._check_reused_material)), \
             patch.object(f, '_check_reused_texture', side_effect=counted('texture', f._check_reused_texture)), \
             patch.object(f, '_validate_mesh', side_effect=counted('mesh', f._validate_mesh)), \
             patch.object(f, '_derived_source', side_effect=counted('cache', f._derived_source)), \
             patch.object(f, '_signed_landmark_probe', side_effect=counted('sentinel', f._signed_landmark_probe)), \
             patch.object(self.u.EditorLoadingAndSavingUtils, 'new_blank_map', side_effect=observed_new):
            report = f.resume_after_restart(self.tmp.name)
        self.assertEqual(report['status'], 'FULL_RESTART_RESUME_CREATED_UNSAVED')

    def test_restart_accepts_native_defaults_only_on_three_pending_meshes(self):
        self.restart_checkpoint()
        for name in (*f.SENTINELS, f.RESUME_FAILED_MESH):
            mesh = self.resume_mesh(name)
            mesh.materials[:] = [self.u.default_material] * len(mesh.materials)
        self.assertEqual(f.resume_after_restart(self.tmp.name)['status'], 'FULL_RESTART_RESUME_CREATED_UNSAVED')

    def test_restart_blocks_unsaved_checkpoint_packages_even_with_clean_fake_dirty_lists(self):
        self.resume_checkpoint()
        self.u.dirty_maps = []
        self.u.dirty_content = []
        self.assert_restart_blocked('[Ss]av|[Pp]ersist|[Pp]hysical|[Uu]asset')

    def test_restart_blocks_one_missing_saved_package_of_each_asset_type(self):
        self.restart_checkpoint()
        for cls in (g.StaticMesh, g.Material, g.Texture2D):
            package = next(path for path, obj in self.u.assets.items() if isinstance(obj, cls))
            path = self.saved_packages[package]
            original = path.read_bytes()
            path.unlink()
            with self.subTest(asset_type=cls.__name__):
                self.assert_restart_blocked('[Ss]av|[Pp]ersist|[Pp]hysical|[Uu]asset')
            path.write_bytes(original)

    def test_restart_sidecars_cannot_substitute_for_saved_uasset(self):
        self.restart_checkpoint()
        path = next(iter(self.saved_packages.values()))
        raw = path.read_bytes()
        path.unlink()
        path.with_suffix('.uexp').write_bytes(raw)
        path.with_suffix('.ubulk').write_bytes(raw)
        self.assert_restart_blocked('[Ss]av|[Pp]ersist|[Pp]hysical|[Uu]asset')

    def test_restart_allows_sidecars_for_registered_saved_assets(self):
        self.restart_checkpoint()
        path = next(iter(self.saved_packages.values()))
        path.with_suffix('.uexp').write_bytes(b'owned fake sidecar')
        path.with_suffix('.ubulk').write_bytes(b'owned fake bulk data')
        self.assertEqual(f.resume_after_restart(self.tmp.name)['status'], 'FULL_RESTART_RESUME_CREATED_UNSAVED')

    def test_restart_blocks_dirty_current_map_even_if_it_is_old_failure_world(self):
        self.restart_checkpoint()
        self.u.world.path = f.RESUME_WORLD
        package = g.Obj(); package.path = f.RESUME_WORLD.split('.')[0]
        self.u.dirty_maps = [package]
        self.assert_restart_blocked('[Dd]irty|[Cc]lean|[Ss]ave')

    def test_restart_blocks_dirty_checkpoint_content(self):
        self.restart_checkpoint()
        package = g.Obj(); package.path = next(iter(self.u.assets))
        self.u.dirty_content = [package]
        self.assert_restart_blocked('[Dd]irty|[Cc]lean|[Ss]ave')

    def test_restart_blocks_unrelated_dirty_content(self):
        self.restart_checkpoint()
        package = g.Obj(); package.path = '/Game/UserWork/Material'
        self.u.dirty_content = [package]
        self.assert_restart_blocked('[Dd]irty|[Cc]lean|[Ss]ave')

    def test_restart_blocks_play_world(self):
        self.restart_checkpoint()
        self.u.game_world = g.World()
        self.assert_restart_blocked('[Pp]lay|[Ss]imulate|PIE')

    def test_restart_blocks_absent_editor_world(self):
        self.restart_checkpoint()
        self.u.world = None
        self.assert_restart_blocked('[Ww]orld|[Mm]ap')

    def test_restart_blocks_existing_full_import_tag(self):
        actor = self.restart_checkpoint()
        actor.props['tags'].append(f.TAG)
        self.assert_restart_blocked('[Aa]ctor|[Ss]cene|[Dd]uplicate|[Tt]ag')

    def test_restart_blocks_existing_full_actor_identity_without_primary_tag(self):
        actor = self.restart_checkpoint()
        actor.props['tags'].append('Full57Id=prop:ExistingObject')
        self.assert_restart_blocked('[Aa]ctor|[Ss]cene|[Dd]uplicate|[Ii]dentity')

    def test_restart_blocks_existing_untagged_actor_using_namespace_mesh(self):
        actor = self.restart_checkpoint()
        actor.props['static_mesh_component'].props['static_mesh'] = self.resume_mesh()
        self.assert_restart_blocked('[Aa]ctor|[Ss]cene|[Dd]uplicate|[Mm]esh')

    def test_restart_blocks_namespace_mesh_in_second_actor_component(self):
        actor = self.restart_checkpoint()
        unrelated = actor.props['static_mesh_component']
        extra = g.StaticMeshComponent()
        extra.props['static_mesh'] = self.resume_mesh()
        actor.props['components'] = [unrelated, extra]
        self.assert_restart_blocked('[Aa]ctor|[Ss]cene|[Dd]uplicate|[Mm]esh')

    def test_restart_blocks_missing_multi_component_inspection_api(self):
        self.restart_checkpoint()
        with patch.object(self.u.Actor, 'get_components_by_class', None):
            self.assert_restart_blocked('get_components_by_class')

    def test_restart_blocks_empty_saved_package(self):
        self.restart_checkpoint()
        next(iter(self.saved_packages.values())).write_bytes(b'')
        self.assert_restart_blocked('[Ee]mpty|[Pp]hysical|[Uu]asset')

    def test_restart_blocks_duplicate_case_variant_package(self):
        self.restart_checkpoint()
        path = next(iter(self.saved_packages.values()))
        duplicate = path.with_name(path.stem.swapcase() + '.UaSsEt')
        duplicate.write_bytes(b'duplicate case-variant package')
        self.assert_restart_blocked('[Dd]uplicate|[Aa]mbiguous|[Cc]ase')

    def test_restart_blocks_current_map_within_owned_namespace(self):
        self.restart_checkpoint()
        self.u.world.path = f.MAP_PATH + '.AbandonedCarnivalFull57'
        self.assert_restart_blocked('[Cc]urrent|[Mm]ap|[Nn]amespace')

    def test_restart_allows_unrelated_mesh_actor_without_namespace_prefix_confusion(self):
        actor = self.restart_checkpoint()
        foreign = g.Obj(); foreign.path = f.DEST + '_Other/Props/Keep.Keep'
        actor.props['static_mesh_component'].props['static_mesh'] = foreign
        self.assertEqual(f.resume_after_restart(self.tmp.name)['status'], 'FULL_RESTART_RESUME_CREATED_UNSAVED')
        self.assertIs(actor.props['static_mesh_component'].props['static_mesh'], foreign)

    def test_restart_blocks_extra_registered_namespace_asset(self):
        self.restart_checkpoint()
        obj = g.Obj(); obj.path = f.DEST + '/Props/Untracked.Untracked'
        self.u.assets[obj.path.split('.')[0]] = obj
        self.assert_restart_blocked('[Ii]nventory|[Cc]heckpoint|[Aa]sset')

    def test_restart_blocks_missing_registered_asset_despite_saved_package(self):
        self.restart_checkpoint()
        self.u.assets.pop(next(iter(self.u.assets)))
        self.assert_restart_blocked('[Ii]nventory|[Cc]heckpoint|[Aa]sset')

    def test_restart_blocks_unregistered_physical_mesh(self):
        self.restart_checkpoint()
        item = self.p['assets'][66]
        path = Path(self.u.content_dir) / (f._asset_path(item).removeprefix('/Game/') + '.uasset')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'foreign file must not be overwritten')
        self.assert_restart_blocked('[Uu]nregistered|[Uu]nexpected|[Pp]hysical')

    def test_restart_blocks_unexpected_physical_map(self):
        self.restart_checkpoint()
        path = Path(self.u.content_dir) / f.DEST.removeprefix('/Game/') / 'Maps' / 'UserMap.umap'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'existing map must not be overwritten')
        self.assert_restart_blocked('[Uu]nregistered|[Uu]nexpected|[Pp]hysical')

    def test_restart_blocks_symlinked_saved_package(self):
        self.restart_checkpoint()
        path = next(iter(self.saved_packages.values()))
        target = Path(self.tmp.name) / 'fake_external.uasset'
        target.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(target)
        self.assert_restart_blocked('[Ss]ymlink|[Ll]ink|[Uu]nsafe')

    def test_restart_blocks_nested_namespace_directory_symlink(self):
        self.restart_checkpoint()
        target = Path(self.tmp.name) / 'outside_namespace'; target.mkdir()
        link = Path(self.u.content_dir) / f.DEST.removeprefix('/Game/') / 'Linked'
        link.symlink_to(target, target_is_directory=True)
        self.assert_restart_blocked('[Ss]ymlink|[Ll]ink|[Uu]nsafe')

    def test_restart_blocks_missing_cache_before_map_and_never_recreates_it(self):
        self.restart_checkpoint()
        path = Path(self.resume_mesh().props['asset_import_data'].filename)
        path.unlink()
        self.assert_restart_blocked('[Cc]ache|[Dd]erived|recreate')
        self.assertFalse(path.exists())

    def test_restart_blocks_changed_cache_before_map_without_overwrite(self):
        self.restart_checkpoint()
        path = Path(self.resume_mesh().props['asset_import_data'].filename)
        path.write_bytes(b'changed derived file')
        self.assert_restart_blocked('[Cc]ache|[Dd]erived|[Oo]verwrite|[Hh]ash')
        self.assertEqual(path.read_bytes(), b'changed derived file')

    def test_restart_blocks_changed_original_source_before_map(self):
        self.restart_checkpoint()
        Path(self.p['assets'][0]['source_path']).write_bytes(b'changed original source')
        self.assert_restart_blocked('[Ss]ource|[Cc]hanged|[Hh]ash')

    def test_restart_blocks_wrong_reused_asset_type_before_map(self):
        self.restart_checkpoint()
        path = next(path for path, obj in self.u.assets.items() if isinstance(obj, g.StaticMesh))
        wrong = g.Obj(); wrong.path = self.u.assets[path].path
        self.u.assets[path] = wrong
        self.assert_restart_blocked('[Ii]dentity|[Tt]ype|[Mm]esh')

    def test_restart_blocks_completed_assignment_drift_before_map(self):
        self.restart_checkpoint()
        self.resume_mesh().materials[0] = None
        self.assert_restart_blocked('[Aa]ssign|[Mm]aterial')

    def test_restart_blocks_pending_assignment_drift_before_map(self):
        self.restart_checkpoint()
        foreign = g.MaterialInterface(); foreign.path = '/Game/UserWork/Material.Material'
        self.resume_mesh(f.RESUME_FAILED_MESH).materials[0] = foreign
        self.assert_restart_blocked('[Aa]ssign|[Mm]aterial')

    def test_restart_blocks_geometry_collision_uv_slots_build_and_import_setting_drift(self):
        self.restart_checkpoint()
        mesh = self.resume_mesh()
        changes = [
            ('bounds', mesh.item['bounds_cm']['max'], 0, mesh.item['bounds_cm']['max'][0] + 50),
            ('uv', mesh.__dict__, 'uv', 0),
            ('slot', mesh.props['static_materials'][0].props, 'imported_material_slot_name', 'WrongSource'),
            ('build', mesh.build.props, 'use_full_precision_u_vs', False),
            ('import', mesh.props['asset_import_data'].props, 'import_uniform_scale', 2.),
            ('collision', mesh.props['body_setup'].props, 'collision_trace_flag', 'COMPLEX_AS_SIMPLE'),
        ]
        # Select a real boolean build field and flip it instead of relying on spelling/defaults.
        key = next(key for key, value in self.c.BUILD_FIELDS.items() if isinstance(value, bool))
        changes[3] = ('build', mesh.build.props, key, not mesh.build.props[key])
        for label, container, key, wrong in changes:
            original = container[key]
            container[key] = wrong
            with self.subTest(drift=label):
                self.assert_restart_blocked()
            self.assertEqual(container[key], wrong)
            container[key] = original

    def test_restart_blocks_mesh_import_provenance_drift_before_map(self):
        self.restart_checkpoint()
        mesh = self.resume_mesh()
        mesh.props['asset_import_data'].filename = mesh.item['source_path']
        self.assert_restart_blocked('[Ss]ource|[Pp]rovenance')

    def test_restart_blocks_texture_policy_and_source_drift_before_map(self):
        self.restart_checkpoint()
        tex = next(obj for obj in self.u.assets.values() if isinstance(obj, g.Texture2D))
        tex.props['virtual_texture_streaming'] = True
        self.assert_restart_blocked('[Tt]exture|[Ss]etting')
        tex.props['virtual_texture_streaming'] = False
        tex.props['asset_import_data'].filename = str(Path(self.tmp.name) / 'wrong_texture.png')
        self.assert_restart_blocked('[Tt]exture|[Ss]ource')

    def test_restart_blocks_material_and_glass_policy_drift_before_map(self):
        self.restart_checkpoint()
        mat = next(obj for obj in self.u.assets.values() if isinstance(obj, g.Material))
        original = mat.props['two_sided']
        mat.props['two_sided'] = not original
        self.assert_restart_blocked('[Mm]aterial|[Ss]ided')
        mat.props['two_sided'] = original
        glass = next(obj for obj in self.u.assets.values()
                     if isinstance(obj, g.Material) and obj.props['blend_mode'] == 'TRANSLUCENT')
        glass.props['refraction_method'] = 'PIXEL_NORMAL_OFFSET'
        self.assert_restart_blocked('[Mm]aterial|[Rr]efraction|[Gg]lass')

    def test_restart_rechecks_dirty_map_immediately_before_new_map(self):
        self.restart_checkpoint()
        real_guard = f._restart_guard
        def changed_after_validation(*args, **kwargs):
            state = real_guard(*args, **kwargs)
            package = g.Obj(); package.path = self.u.world.path.split('.')[0]
            self.u.dirty_maps = [package]
            return state
        with patch.object(f, '_restart_guard', side_effect=changed_after_validation):
            self.assert_restart_blocked('[Dd]irty|[Cc]lean|[Ss]ave')

    def test_restart_rechecks_dirty_content_immediately_before_new_map(self):
        self.restart_checkpoint()
        real_guard = f._restart_guard
        def changed_after_validation(*args, **kwargs):
            state = real_guard(*args, **kwargs)
            package = g.Obj(); package.path = next(iter(self.u.assets))
            self.u.dirty_content = [package]
            return state
        with patch.object(f, '_restart_guard', side_effect=changed_after_validation):
            self.assert_restart_blocked('[Dd]irty|[Cc]lean|[Ss]ave')

    def test_restart_rechecks_world_identity_immediately_before_new_map(self):
        self.restart_checkpoint()
        real_guard = f._restart_guard
        new_world = g.World(); new_world.path = '/Game/NewUserWorld.NewUserWorld'
        def changed_after_validation(*args, **kwargs):
            state = real_guard(*args, **kwargs)
            self.u.world = new_world
            return state
        with patch.object(f, '_restart_guard', side_effect=changed_after_validation):
            with self.assertRaises(f.FullImportError) as caught:
                f.resume_after_restart(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_RESTART_RESUME_BLOCKED', report)
        self.assertFalse(report['mutation_started'])
        self.assertEqual(self.u.events, [])
        self.assertIs(self.u.world, new_world)

    def test_restart_new_map_failure_is_partial_and_does_not_start_imports(self):
        self.restart_checkpoint()
        before = dict(self.u.assets)
        def fail_new_map(save_existing_map):
            self.assertIs(save_existing_map, False)
            self.u.events.append('new_blank_map')
            raise RuntimeError('injected map creation failure')
        with patch.object(self.u.EditorLoadingAndSavingUtils, 'new_blank_map', side_effect=fail_new_map):
            with self.assertRaises(f.FullImportError) as caught:
                f.resume_after_restart(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_RESTART_RESUME_FAILED_PARTIAL', report)
        self.assertTrue(report['mutation_started'])
        self.assertTrue(report['partial'])
        self.assertEqual(self.u.events, ['new_blank_map'])
        self.assertEqual(self.u.assets, before)
        self.assertEqual(report['saves_performed'], 0)

    def test_restart_refuses_same_saved_or_nonempty_returned_map(self):
        self.restart_checkpoint()
        old = self.u.world
        def same_map(_):
            self.u.events.append('new_blank_map')
            return old
        def saved_map(_):
            self.u.events.append('new_blank_map')
            self.u.world = g.World(); self.u.world.path = '/Game/Other.Other'
            self.u.actors = []
            return self.u.world
        def nonempty_map(_):
            self.u.events.append('new_blank_map')
            self.u.world = g.World(); self.u.world.path = '/Temp/Fresh.Fresh'
            self.u.actors = [g.StaticMeshActor()]
            return self.u.world
        for scenario in (same_map, saved_map, nonempty_map):
            with self.subTest(scenario=scenario.__name__):
                self.u.world = old
                self.u.actors = []
                self.u.events.clear()
                with patch.object(self.u.EditorLoadingAndSavingUtils, 'new_blank_map', side_effect=scenario):
                    with self.assertRaises(f.FullImportError) as caught:
                        f.resume_after_restart(self.tmp.name)
                self.assertEqual(caught.exception.report['status'], 'FULL_RESTART_RESUME_FAILED_PARTIAL')
                self.assertTrue(caught.exception.report['mutation_started'])
                self.assertEqual(self.u.events, ['new_blank_map'])
                self.assertEqual(len(self.u.assets), 168)

    def test_restart_import_failure_leaves_old_map_and_reused_assets_intact(self):
        actor = self.restart_checkpoint()
        old_world, old_actors = self.u.world, self.u.actors
        existing = dict(self.u.assets)
        self.u.raise_after_import = True
        with self.assertRaises(f.FullImportError) as caught:
            f.resume_after_restart(self.tmp.name)
        report = caught.exception.report
        self.assertEqual(report['status'], 'FULL_RESTART_RESUME_FAILED_PARTIAL', report)
        self.assertTrue(report['mutation_started'])
        self.assertTrue(report['partial'])
        self.assertIsNot(self.u.world, old_world)
        self.assertEqual(old_actors, [actor])
        self.assertEqual(len(self.u.assets), 169)
        self.assertTrue(all(self.u.assets[path] is obj for path, obj in existing.items()))
        self.assertEqual(self.u.actors, [])
        self.assertEqual(self.u.events.count('new_blank_map'), 1)
        self.assertEqual(self.u.events.count('import_mesh'), 1)
        self.assertFalse(any('save' in e or 'delete' in e or 'destroy' in e for e in self.u.events))

    def test_restart_cannot_repeat_after_successful_scene_placement(self):
        self.restart_checkpoint()
        self.assertEqual(f.resume_after_restart(self.tmp.name)['status'], 'FULL_RESTART_RESUME_CREATED_UNSAVED')
        self.assert_restart_blocked()

    def test_restart_changes_do_not_relax_live_resume_world_contract(self):
        self.restart_checkpoint()
        with self.assertRaises(f.FullImportError) as caught:
            f.resume_full(self.tmp.name)
        self.assertEqual(caught.exception.report['status'], 'FULL_RESUME_BLOCKED')
        self.assertEqual(self.u.events, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
