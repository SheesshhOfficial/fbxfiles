"""Pure stdlib/offline tests. The fake engine is NOT Unreal runtime evidence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import carnival_calibration57 as c

REAL_ROOT = Path(os.environ.get("CARNIVAL_PACKAGE_ROOT", str(Path(__file__).resolve().parents[2] / "CarnivalMap_Refined_Delivery/repository/AbandonedCarnival")))


class Obj:
    def __init__(self, **properties):
        self.props = properties
        self.path = "/Transient/Mock"
    def get_editor_property(self, key):
        if key not in self.props:
            raise AttributeError(key)
        return self.props[key]
    def set_editor_property(self, key, value):
        self.props[key] = value
    def get_path_name(self):
        return self.path
    def get_class(self):
        return types.SimpleNamespace(get_name=lambda: type(self).__name__)


class Vector:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    def __eq__(self, other):
        return isinstance(other, Vector) and vars(self) == vars(other)


class Rotator:
    def __init__(self, roll=0, pitch=0, yaw=0):
        self.roll, self.pitch, self.yaw = roll, pitch, yaw
    def __eq__(self, other):
        return isinstance(other, Rotator) and vars(self) == vars(other)


class MaterialInterface(Obj):
    pass


class BodySetup(Obj):
    def __init__(self, hulls=0):
        super().__init__(agg_geom=Obj(**{k: [Obj() for _ in range(hulls)] if k == "convex_elems" else []
                                        for k in ("convex_elems",) + c.OTHER_SHAPES}),
                         collision_trace_flag="SIMPLE_AND_COMPLEX")


class FbxStaticMeshImportData(Obj):
    def __init__(self):
        super().__init__(**dict(c.FBX_FIELDS, normal_import_method="IMPORT_NORMALS", normal_generation_method="MIKK",
                                import_translation=Vector(), import_rotation=Rotator(),
                                coordinate_system_policy="MATCH_UP_FORWARD_AXES", using_luf_coordinate_sysem=False))
        self.filename = ""
    def extract_filenames(self):
        return [self.filename]


class FbxImportUI(Obj):
    def __init__(self):
        super().__init__(static_mesh_import_data=FbxStaticMeshImportData(),
             **{k: None for k in ("import_mesh", "import_as_skeletal", "import_animations", "import_materials",
                "import_textures", "automated_import_should_detect_type", "mesh_type_to_import", "original_import_type", "override_full_name")})


class FbxFactory(Obj):
    pass


class AssetImportTask(Obj):
    def __init__(self):
        super().__init__(**{k: None for k in ("filename", "destination_path", "destination_name", "automated", "async_", "save",
                  "replace_existing", "replace_existing_settings", "factory", "options", "imported_object_paths")})
        self.objects = []
    def get_objects(self):
        return self.objects


class StaticMesh(Obj):
    def __init__(self, item, data):
        super().__init__(asset_import_data=data, body_setup=BodySetup(item["collision_hulls"]),
             static_materials=[Obj(imported_material_slot_name=name) for name in item["materials"]])
        self.item = item
        self.path = c.MESH_FOLDER + "/" + item["asset_name"] + "." + item["asset_name"]
        self.build = Obj(**c.BUILD_FIELDS)
        self.materials = [None] * len(item["materials"])
        self.uv = 1
    def get_bounds(self):
        lo, hi = self.item["bounds_cm"]["min"], self.item["bounds_cm"]["max"]
        return types.SimpleNamespace(origin=Vector(*[(a+b)/2 for a,b in zip(lo,hi)]),
                                     box_extent=Vector(*[(b-a)/2 for a,b in zip(lo,hi)]))
    def set_material(self, index, material):
        self.materials[index] = material
    def get_material(self, index):
        return self.materials[index]


class StaticMeshComponent(Obj):
    def __init__(self):
        super().__init__(static_mesh=None)
    def set_static_mesh(self, mesh):
        self.props["static_mesh"] = mesh
        return True
    def set_simulate_physics(self, value):
        self.props["simulate_physics"] = value


class StaticMeshActor(Obj):
    def __init__(self, location=None):
        super().__init__(tags=[], static_mesh_component=StaticMeshComponent())
        self.location = location or Vector()
        self.scale = Vector(1, 1, 1)
    def set_actor_label(self, value):
        self.label = value
    def set_actor_scale3d(self, value):
        self.scale = value
    def get_actor_location(self):
        return self.location
    def get_actor_scale3d(self):
        return self.scale


class World(Obj):
    pass


def fake_engine(contract):
    u = types.ModuleType("unreal")
    u.events, u.assets, u.actors = [], {}, []
    u.dirty_maps, u.dirty_content = [], []
    u.version = "5.7.4-12345+++UE5+Release-5.7"
    u.existing_namespace = False
    u.import_mutator = None
    u.default_material = MaterialInterface()
    u.world = World()
    u.world.path = "/Game/Previous.Previous"
    u.game_world = None
    u.content_dir = tempfile.mkdtemp(prefix="calibration57-fake-content-")
    for cls in (Obj, Vector, Rotator, MaterialInterface, BodySetup, FbxStaticMeshImportData,
                FbxImportUI, FbxFactory, AssetImportTask, StaticMesh, StaticMeshComponent, StaticMeshActor, World):
        setattr(u, cls.__name__, cls)
    u.Name = str
    u.FBXImportType = types.SimpleNamespace(FBXIT_STATIC_MESH="STATIC")
    u.FBXNormalImportMethod = types.SimpleNamespace(FBXNIM_IMPORT_NORMALS="IMPORT_NORMALS")
    u.FBXNormalGenerationMethod = types.SimpleNamespace(MIKK_T_SPACE="MIKK")
    u.CollisionTraceFlag = types.SimpleNamespace(CTF_USE_SIMPLE_AND_COMPLEX="SIMPLE_AND_COMPLEX",
            CTF_USE_DEFAULT="DEFAULT", CTF_USE_SIMPLE_AS_COMPLEX="SIMPLE_AS_COMPLEX", CTF_USE_COMPLEX_AS_SIMPLE="COMPLEX_AS_SIMPLE")
    class SystemLibrary:
        @staticmethod
        def get_engine_version(): return u.version
    class Paths:
        @staticmethod
        def project_content_dir(): return u.content_dir
        @staticmethod
        def convert_relative_path_to_full(path): return str(Path(path).resolve())
    class Loading:
        @staticmethod
        def get_dirty_map_packages(): return u.dirty_maps
        @staticmethod
        def get_dirty_content_packages(): return u.dirty_content
        @staticmethod
        def new_blank_map(save_existing_map):
            assert save_existing_map is False
            u.events.append("new_blank_map")
            u.world = World()
            u.world.path = "/Temp/Untitled.Untitled"
            u.actors = []
            return u.world
    class Library:
        @staticmethod
        def does_directory_exist(path): return u.existing_namespace
        @staticmethod
        def does_asset_exist(path): return path in u.assets
        @staticmethod
        def list_assets(path, **kwargs): return list(u.assets)
    class EditorActorSubsystem:
        def get_all_level_actors(self): return list(u.actors)
        def spawn_actor_from_class(self, cls, location, rotation, transient=False):
            u.events.append("spawn_actor")
            actor = cls(location)
            actor.path = u.world.path + ":Actor" + str(len(u.actors))
            u.actors.append(actor)
            return actor
    class UnrealEditorSubsystem:
        def get_editor_world(self): return u.world
        def get_game_world(self): return u.game_world
    class StaticMeshEditorSubsystem:
        def get_num_uv_channels(self, mesh, index): return mesh.uv
        def get_simple_collision_count(self, mesh): return 0
        def get_convex_collision_count(self, mesh): return len(mesh.props["body_setup"].props["agg_geom"].props["convex_elems"])
        def get_lod_build_settings(self, mesh, index): return mesh.build
        def set_lod_build_settings(self, mesh, index, build):
            u.events.append("set_build")
            mesh.build = build
    class AssetTools:
        def import_asset_tasks(self, tasks):
            assert len(tasks) == 1
            task = tasks[0]
            u.events.append("import_asset")
            assert task.props["save"] is False
            assert task.props["replace_existing"] is False
            assert task.props["replace_existing_settings"] is False
            assert isinstance(task.props["factory"], FbxFactory)
            opts = task.props["options"]
            assert opts.props["automated_import_should_detect_type"] is False
            assert opts.props["import_materials"] is False and opts.props["import_textures"] is False
            item = next(i for i in contract["selected"] if i["asset_name"] == task.props["destination_name"])
            data = copy.deepcopy(opts.props["static_mesh_import_data"])
            data.filename = task.props["filename"]
            mesh = StaticMesh(copy.deepcopy(item), data)
            if u.import_mutator:
                u.import_mutator(mesh)
            task.objects = [mesh]
            task.props["imported_object_paths"] = [mesh.path]
            u.assets[mesh.path.split(".")[0]] = mesh
    tool = AssetTools()
    class Helpers:
        @staticmethod
        def get_asset_tools(): return tool
    for name, cls in dict(SystemLibrary=SystemLibrary, Paths=Paths, EditorLoadingAndSavingUtils=Loading,
         EditorAssetLibrary=Library, EditorActorSubsystem=EditorActorSubsystem, UnrealEditorSubsystem=UnrealEditorSubsystem,
         StaticMeshEditorSubsystem=StaticMeshEditorSubsystem, AssetToolsHelpers=Helpers).items():
        setattr(u, name, cls)
    u.get_default_object = lambda cls: cls()
    u.get_editor_subsystem = lambda cls: cls()
    u.load_asset = lambda path: u.default_material
    return u


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((Path(__file__).parent / "sample_contract_fixture.json").read_text())
    def setUp(self):
        local_contract = copy.deepcopy(self.contract)
        source_dir = tempfile.TemporaryDirectory(prefix="calibration57-fake-source-")
        self.addCleanup(source_dir.cleanup)
        for item in local_contract["selected"]:
            path = Path(source_dir.name) / (item["asset_name"] + ".fbx")
            path.write_bytes(b"MOCK FBX bytes, not a renderable mesh")
            item["source_path"] = str(path)
            item["fbx_sha256"] = c._sha(path)
        self.u = fake_engine(local_contract)
        self.engine_patch = patch.dict(sys.modules, {"unreal": self.u})
        self.engine_patch.start()
        self.addCleanup(self.engine_patch.stop)
        self.contract_patch = patch.object(c, "_contract", return_value=local_contract)
        self.contract_patch.start()
        self.addCleanup(self.contract_patch.stop)
        self.addCleanup(lambda: __import__("shutil").rmtree(self.u.content_dir))
    def test_preflight_is_read_only(self):
        report = c.preflight(REAL_ROOT)
        self.assertEqual(report["status"], "PREFLIGHT_PASS")
        self.assertTrue(report["ready_to_import"])
        self.assertEqual(self.u.events, [])
        self.assertEqual(self.u.assets, {})
    def test_dirty_map_rejected_before_mutation(self):
        self.u.dirty_maps = ["unsaved"]
        with self.assertRaises(c.CalibrationError) as caught:
            c.import_sample(REAL_ROOT)
        self.assertEqual(caught.exception.report["status"], "SAMPLE_BLOCKED")
        self.assertEqual(self.u.events, [])
    def test_dirty_content_rejected_before_mutation(self):
        self.u.dirty_content = ["unsaved asset"]
        self.assertEqual(c.preflight(REAL_ROOT)["status"], "PREFLIGHT_BLOCKED")
        self.assertEqual(self.u.events, [])
    def test_existing_namespace_rejected(self):
        self.u.existing_namespace = True
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events, [])
    def test_physical_empty_folder_rejected(self):
        (Path(self.u.content_dir) / "AbandonedCarnivalCalibration57").mkdir()
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events, [])
    def test_slot_order_rejected(self):
        self.u.import_mutator = lambda mesh: mesh.props["static_materials"].reverse()
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(len(self.u.actors), 0)
    def test_existing_sample_asset_rejected(self):
        self.u.assets[c.MESH_FOLDER + "/" + c.SAMPLES[0][0]] = "existing"
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events, [])
    def test_wrong_engine_rejected(self):
        for version in ("5.8.0-1", "5.7.3-1", "5.7.40-1", "4.27.2"):
            self.u.version = version
            self.assertEqual(c.preflight(REAL_ROOT)["status"], "PREFLIGHT_BLOCKED")
        self.assertEqual(self.u.events, [])
    def test_missing_api_rejected(self):
        delattr(self.u, "FbxFactory")
        self.assertEqual(c.preflight(REAL_ROOT)["status"], "PREFLIGHT_BLOCKED")
        self.assertEqual(self.u.events, [])
    def test_pie_rejected(self):
        self.u.game_world = World()
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events, [])
    def test_success_exactly_three_assets_four_actors_unsaved(self):
        report = c.import_sample(REAL_ROOT)
        self.assertEqual(report["status"], "SAMPLE_GEOMETRY_COLLISION_PASS_UNSAVED")
        self.assertEqual([r["convex_count"] for r in report["mesh_checks"]], [8, 9, 1])
        self.assertEqual(len(self.u.assets), 3)
        self.assertEqual(len(self.u.actors), 4)
        self.assertEqual(self.u.events.count("import_asset"), 3)
        self.assertIs(self.u.actors[2].props["static_mesh_component"].props["static_mesh"],
                      self.u.actors[3].props["static_mesh_component"].props["static_mesh"])
        self.assertEqual(report["saves_performed"], 0)
        self.assertFalse(report["map_saved"])
        self.assertTrue(all("PropActor" in a.props["tags"] for a in self.u.actors))
        self.assertEqual(report["material_validation"], "NOT_RUN")
    def test_repeat_rejected_without_more_mutation(self):
        c.import_sample(REAL_ROOT)
        before = list(self.u.events)
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events, before)
    def test_wrong_actual_name_stops_partial(self):
        self.u.import_mutator = lambda mesh: setattr(mesh, "path", mesh.path + "_Wrong")
        with self.assertRaises(c.CalibrationError) as caught: c.import_sample(REAL_ROOT)
        self.assertEqual(caught.exception.report["status"], "SAMPLE_FAILED_PARTIAL")
        self.assertTrue(caught.exception.report["imported_objects"])
        self.assertEqual(self.u.events.count("import_asset"), 1)
        self.assertEqual(len(self.u.assets), 1)
    def test_interchange_import_data_rejected(self):
        self.u.import_mutator = lambda mesh: mesh.props.update(asset_import_data=Obj())
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events.count("import_asset"), 1)
    def test_wrong_bounds_rejected(self):
        self.u.import_mutator = lambda mesh: mesh.item["bounds_cm"]["max"].__setitem__(0, 999999)
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(len(self.u.actors), 0)
    def test_extra_primitive_collision_rejected(self):
        self.u.import_mutator = lambda mesh: mesh.props["body_setup"].props["agg_geom"].props["box_elems"].append(Obj())
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
    def test_wrong_hull_count_rejected(self):
        self.u.import_mutator = lambda mesh: mesh.props["body_setup"].props["agg_geom"].props["convex_elems"].pop()
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
    def test_missing_uv_rejected(self):
        self.u.import_mutator = lambda mesh: setattr(mesh, "uv", 0)
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
    def test_material_slots_rejected(self):
        self.u.import_mutator = lambda mesh: mesh.props["static_materials"].pop()
        with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
    def test_source_verification_failure_no_mutation(self):
        self.contract_patch.stop()
        with patch.object(c, "_contract", side_effect=ValueError("Whole sample FBX SHA256 mismatch")):
            with self.assertRaises(c.CalibrationError): c.import_sample(REAL_ROOT)
        self.assertEqual(self.u.events, [])
    def test_change_after_preflight_no_import(self):
        with patch.object(c, "_sha", return_value="wrong"):
            with self.assertRaises(c.CalibrationError) as caught: c.import_sample(REAL_ROOT)
        self.assertTrue(caught.exception.report["partial_import"])
        self.assertEqual(self.u.events, ["new_blank_map"])


class OfflineIntegrityTests(unittest.TestCase):
    def test_json_crlf_only_normalization(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "example.json"
            original = b'{\n  "key": 1\n}\n'
            expected = hashlib.sha256(original).hexdigest()
            path.write_bytes(original.replace(b"\n", b"\r\n"))
            actual, normalized = c._pinned_json_sha(path, expected)
            self.assertTrue(normalized)
            self.assertNotEqual(actual, expected)
            path.write_bytes(original.replace(b"1", b"2"))
            with self.assertRaises(ValueError): c._pinned_json_sha(path, expected)
    def test_binary_hash_never_normalized(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.fbx"
            path.write_bytes(b"binary\r\ndata")
            self.assertNotEqual(c._sha(path), hashlib.sha256(b"binary\ndata").hexdigest())

    @unittest.skipUnless(REAL_ROOT.is_dir(), "Set CARNIVAL_PACKAGE_ROOT for real-package hash integration test")
    def test_real_frozen_source_and_sample_hashes(self):
        result = c._contract(REAL_ROOT)
        self.assertEqual(result["source_sha256"], c.SOURCE_SHA256)
        self.assertEqual(result["source_bytes"], 136393382)
        self.assertEqual(len(result["verified_files"]), 23)
        self.assertEqual(len(result["selected"]), 3)
    def test_pinned_manifest_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "FILE_MANIFEST.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Pinned file SHA256 mismatch"):
                c._contract(td)
    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            for path in ("../x", "/tmp/x", "C:/x", "x\\y"):
                with self.assertRaises(ValueError): c._safe_file(Path(td), path)
    @unittest.skipUnless(REAL_ROOT.is_dir(), "Set CARNIVAL_PACKAGE_ROOT for real-package preflight integration test")
    def test_offline_preflight_does_not_claim_engine_check(self):
        with patch.dict(sys.modules, {"unreal": None}):
            report = c.preflight(REAL_ROOT)
        self.assertEqual(report["status"], "FILES_VERIFIED_ENGINE_NOT_CHECKED")
        self.assertFalse(report["ready_to_import"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
