"""Standalone offline tests. No project, Unreal installation or source files needed."""
import ast
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "premium_preflight574.py"
spec = importlib.util.spec_from_file_location("premium_preflight574", MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
ATTEMPTED_MUTATIONS = []
FORBIDDEN = ("set_", "save", "load", "spawn", "destroy", "delete", "import_", "export_",
             "scan_", "search_all", "modify", "compile", "build_", "create_", "execute",
             "get_asset", "get_default_object", "sphere_trace", "line_trace", "editor_play")


class ReadOnly:
    def __getattr__(self, name):
        if name.startswith(FORBIDDEN):
            def forbidden(*args, **kwargs):
                ATTEMPTED_MUTATIONS.append(name)
                raise AssertionError("Forbidden mutation/load/trace: " + name)
            return forbidden
        raise AttributeError(name)


class Node(ReadOnly):
    def __init__(self, path=None, **properties):
        self.path, self.properties = path, properties

    def get_editor_property(self, name):
        if name not in self.properties:
            raise AttributeError(name)
        return self.properties[name]

    def get_path_name(self):
        return self.path

    def get_name(self):
        return (self.path or "").rsplit(".", 1)[-1]


def vec(x=0, y=0, z=0):
    return types.SimpleNamespace(x=x, y=y, z=z)


class Mesh(Node):
    def __init__(self, name, convex=1, root=None):
        root = root or p.NAMESPACE + "/FullPreview574_v001/Meshes"
        agg = Node(**{key: [None] * (convex if key == "convex_elems" else 0) for key in p.SHAPE_FIELDS})
        super().__init__(root + "/" + name + "." + name,
                         body_setup=Node(agg_geom=agg, collision_trace_flag="CTF_USE_SIMPLE_AND_COMPLEX"))
        self.convex = convex

    def get_bounds(self):
        return types.SimpleNamespace(origin=vec(), box_extent=vec(100, 50, 200))


class Component(Node):
    def __init__(self, mesh=None, name="StaticMeshComponent0"):
        super().__init__("Actor." + name, static_mesh=mesh)
        self.enabled = "QUERY_AND_PHYSICS" if mesh and mesh.convex else "NO_COLLISION"
        self.pawn = self.visibility = "ECR_BLOCK" if mesh and mesh.convex else "ECR_IGNORE"

    def get_collision_enabled(self):
        return self.enabled

    def get_collision_profile_name(self):
        return "BlockAll" if self.enabled == "QUERY_AND_PHYSICS" else "NoCollision"

    def get_collision_object_type(self):
        return "ECC_WORLD_STATIC"

    def get_collision_response_to_channel(self, channel):
        return {"ECC_PAWN": self.pawn, "ECC_VISIBILITY": self.visibility}[channel]

    def get_scaled_capsule_radius(self):
        return 42.0

    def get_scaled_capsule_half_height(self):
        return 96.0


class Actor(Node):
    def __init__(self, world, sid, aid, mesh, prop=True, tags=None):
        tags = tags if tags is not None else ["PremiumStoreV3", "V3Placement=" + sid,
                    "V3Asset=" + aid, "V3Phase=full"] + (["Prop"] if prop else [])
        super().__init__(world.path + ":PersistentLevel." + sid, tags=tags)
        self.world, self.components = world, [Component(mesh)]
        self.class_path, self.label_reads = "/Script/Engine.StaticMeshActor", []

    def get_world(self):
        return self.world

    def get_components_by_class(self, cls):
        return self.components

    def get_class(self):
        return Node(self.class_path)

    def get_actor_location(self):
        return vec(10, 20, 30)

    def get_actor_label(self, create_if_none=True):
        self.label_reads.append(create_if_none)
        if create_if_none:
            ATTEMPTED_MUTATIONS.append("get_actor_label(True)")
            raise AssertionError("Label mutation")
        return self.get_name()

    def get_local_role(self):
        return "ROLE_Authority"

    def get_remote_role(self):
        return "ROLE_SimulatedProxy"


class FakeUnreal(ReadOnly):
    UnrealEditorSubsystem = "UnrealEditorSubsystem"
    EditorActorSubsystem = "EditorActorSubsystem"
    StaticMeshEditorSubsystem = "StaticMeshEditorSubsystem"
    StaticMeshComponent = "StaticMeshComponent"
    CollisionChannel = types.SimpleNamespace(ECC_PAWN="ECC_PAWN", ECC_VISIBILITY="ECC_VISIBILITY")

    def __init__(self, map_path=p.EXPECTED_MAP, version="5.7.4-12345+++UE5+Release-5.7"):
        self.world = Node(map_path + "." + map_path.rsplit("/", 1)[-1]) if map_path else None
        self.actors, self.actor_reads, self.registry_reads, self.pawn_reads = [], 0, [], []
        self.dirty_maps, self.dirty_content, self.pie_worlds, self.pawns = [], [], [], {}
        self.SystemLibrary = types.SimpleNamespace(get_engine_version=lambda: version)
        self.EditorLoadingAndSavingUtils = types.SimpleNamespace(
            get_dirty_map_packages=lambda: self.dirty_maps,
            get_dirty_content_packages=lambda: self.dirty_content)
        self.registry_data = [Node(package_name=p.EXPECTED_MAP, asset_name="L_V3_AllPlacements",
                                   asset_class_path="/Script/Engine.World")]
        self.registry = types.SimpleNamespace(get_assets_by_path=self.registry_assets, is_loading_assets=lambda: False)
        self.AssetRegistryHelpers = types.SimpleNamespace(get_asset_registry=lambda: self.registry)
        self.EditorLevelLibrary = types.SimpleNamespace(get_pie_worlds=lambda include: self.pie_worlds)
        self.GameplayStatics = types.SimpleNamespace(get_player_pawn=self.player_pawn)
        self.mesh_ss = types.SimpleNamespace(get_convex_collision_count=lambda mesh: mesh.convex,
                                            get_simple_collision_count=lambda mesh: mesh.convex,
                                            get_num_uv_channels=lambda mesh, lod: 1)
        self.subsystems = {
            self.UnrealEditorSubsystem: types.SimpleNamespace(get_editor_world=lambda: self.world),
            self.EditorActorSubsystem: types.SimpleNamespace(get_all_level_actors=self.all_actors),
            self.StaticMeshEditorSubsystem: self.mesh_ss}

    def get_editor_subsystem(self, cls):
        return self.subsystems[cls]

    def all_actors(self):
        self.actor_reads += 1
        return self.actors

    def registry_assets(self, root, recursive, include_only_on_disk_assets):
        self.registry_reads.append((root, recursive, include_only_on_disk_assets))
        assert root == p.NAMESPACE and recursive and include_only_on_disk_assets
        return self.registry_data

    def player_pawn(self, world, index):
        self.pawn_reads.append((world, index))
        return self.pawns.get(world)

    def add(self, sid="shelf_1", aid="premium_shelf_bay", mesh=None, prop=True, tags=None):
        actor = Actor(self.world, sid, aid, mesh or Mesh("SM_EG_PremiumShelfBay", 12), prop, tags)
        self.actors.append(actor)
        return actor


class PreflightTests(unittest.TestCase):
    def setUp(self):
        ATTEMPTED_MUTATIONS.clear()

    def tearDown(self):
        self.assertEqual(ATTEMPTED_MUTATIONS, [], "Forbidden call attempted")

    def inspect(self, u, **kwargs):
        result = p.inspect(u, **kwargs)
        json.dumps(result, allow_nan=False)
        return result

    def test_import_is_inert_and_no_file_io(self):
        tree = ast.parse(MODULE.read_text())
        self.assertNotIn("unreal", p.__dict__)
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open" for n in ast.walk(tree)))
        self.assertFalse(any(isinstance(n, ast.If) and "__name__" in ast.unparse(n.test) for n in tree.body))

    def test_read_gate_forbids_mutators(self):
        for method in ("save_map", "load_asset", "set_editor_property", "sphere_trace_single", "compile_blueprint"):
            with self.assertRaises(RuntimeError):
                p._Read().call(Node(), method)

    def test_wrong_map_skips_all_editor_and_runtime_pawn_reads(self):
        for path in ("/Game/Carnival/Map", "/Game/PremiumStoreV30/Map", "/Game/PremiumStoreV3Other/Map"):
            u = FakeUnreal(path)
            u.pie_worlds.append(Node(p.NAMESPACE + "/Maps/UEDPIE_0_Map.Map"))
            self.assertEqual(self.inspect(u)["status"], "OPEN_PREMIUM_MAP_FIRST")
            self.assertEqual(u.actor_reads, 0)
            self.assertEqual(u.pawn_reads, [])

    def test_uvrepair_variant_is_observed(self):
        u = FakeUnreal(p.NAMESPACE + "/UVRepair574_v002/Maps/L_V3_AllPlacements")
        u.add()
        result = self.inspect(u)
        self.assertEqual(result["current_map"]["status"], "PREMIUM_VARIANT_REVIEW")
        self.assertEqual(result["placements"]["counts"]["placements"], 1)

    def test_exact_version(self):
        for version in ("5.8.0", "5.7.40", "5.7.4.1", "5.7.4garbage", "5.7.3"):
            result = self.inspect(FakeUnreal(version=version))
            self.assertEqual(result["status"], "BLOCKED_ENGINE_VERSION")
            self.assertIn("dirty_after", result)

    def test_correct_read_only_shelf_snapshot(self):
        u = FakeUnreal()
        actor = u.add()
        result = self.inspect(u)
        shelf = result["placements"]["representatives"]["shelves"]["actors"][0]
        self.assertEqual(result["engine"]["status"], "MATCH")
        self.assertTrue(result["dirty_snapshot_unchanged"])
        self.assertEqual(shelf["mesh"]["convex_count"], 12)
        self.assertTrue(shelf["mesh"]["source_count_match"])
        self.assertEqual(shelf["location_cm"], [10, 20, 30])
        self.assertEqual(actor.label_reads, [False])
        self.assertEqual(result["pie"]["status"], "NOT_IN_PIE")
        self.assertEqual(u.pawn_reads, [])

    def test_dirty_work_retained_and_reported(self):
        u = FakeUnreal()
        u.dirty_maps.append(Node("/Game/Carnival/Map"))
        u.dirty_content.append(Node("/Game/Blueprints/BP_propChar"))
        result = self.inspect(u)
        self.assertEqual(result["dirty_before"]["status"], "DIRTY_WORK_PRESENT")
        self.assertTrue(result["dirty_snapshot_unchanged"])
        self.assertEqual(len(u.dirty_maps), 1)
        self.assertEqual(len(u.dirty_content), 1)

    def test_missing_dirty_and_registry_are_unknown(self):
        u = FakeUnreal()
        u.EditorLoadingAndSavingUtils = u.AssetRegistryHelpers = None
        u.add()
        result = self.inspect(u)
        self.assertEqual(result["dirty_before"]["status"], "UNAVAILABLE")
        self.assertIsNone(result["dirty_snapshot_unchanged"])
        self.assertEqual(result["asset_registry"]["status"], "UNAVAILABLE")
        self.assertEqual(result["placements"]["counts"]["placements"], 1)

    def test_registry_can_be_disabled_and_never_loads_assets(self):
        u = FakeUnreal()
        self.assertEqual(self.inspect(u, include_asset_registry=False)["asset_registry"]["status"], "NOT_REQUESTED")
        self.assertEqual(u.registry_reads, [])
        result = self.inspect(u)
        self.assertEqual(result["asset_registry"]["maps"]["items"], [p.EXPECTED_MAP])
        self.assertEqual(u.registry_reads, [(p.NAMESPACE, True, True)])

    def test_missing_world(self):
        u = FakeUnreal(None)
        self.assertEqual(self.inspect(u)["status"], "CURRENT_WORLD_UNAVAILABLE")
        self.assertEqual(u.actor_reads, 0)

    def test_duplicate_placement_and_canonical_conflict(self):
        u = FakeUnreal()
        u.add(sid="same")
        u.add(sid="same", mesh=Mesh("AnotherShelf"))
        result = self.inspect(u)["placements"]
        self.assertEqual(result["placement_id_duplicates"]["total"], 1)
        self.assertEqual(result["canonical_id_conflicts"]["total"], 1)

    def test_missing_owner_and_invalid_phase(self):
        u = FakeUnreal()
        u.add(tags=[])
        u.add(sid="shelf_2", tags=["PremiumStoreV3", "V3Placement=2", "V3Asset=premium_shelf_bay", "V3Phase=sample", "Prop"])
        result = self.inspect(u)["placements"]
        self.assertEqual(result["counts"]["premium_mesh_without_owner_tag"], 1)
        self.assertEqual(result["exceptions"]["counts_by_code"]["PLACEMENT_PHASE_NOT_FULL"], 1)

    def test_blueprint_derived_actor_flagged(self):
        u = FakeUnreal()
        u.add().class_path = "/Game/Props/BP_Prop.BP_Prop_C"
        result = self.inspect(u)["placements"]
        self.assertEqual(result["counts"]["non_native_static_mesh_actor_placements"], 1)
        self.assertEqual(result["exceptions"]["counts_by_code"]["EXPECTED_NATIVE_STATIC_MESH_ACTOR"], 1)

    def test_missing_body_is_unknown_not_zero(self):
        u = FakeUnreal()
        mesh = Mesh("Shelf")
        del mesh.properties["body_setup"]
        u.add(mesh=mesh)
        result = self.inspect(u)
        self.assertIsNone(result["placements"]["asset_collision"]["observed_convex_total"])
        self.assertTrue(result["missing_data"])

    def test_negative_subsystem_counts_are_unknown(self):
        for name in ("get_simple_collision_count", "get_convex_collision_count", "get_num_uv_channels"):
            u = FakeUnreal()
            setattr(u.mesh_ss, name, lambda *args: -1)
            u.add()
            result = self.inspect(u)
            self.assertTrue(result["missing_data"])
            self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_floor_known_can_fridge_representatives(self):
        u = FakeUnreal()
        for aid, name, hulls in (("main_floor", "SM_FULL_MainFloor", 1),
                                  ("crushed_tomatoes", "SM_MV_crushed_tomatoes", 1),
                                  ("refrigerated_bay", "SM_FULL_OpenFrontRefrigeratedBay", 10)):
            u.add(sid=aid, aid=aid, mesh=Mesh(name, hulls))
        reps = self.inspect(u)["placements"]["representatives"]
        for key in ("floor", "can", "refrigerated_bay"):
            self.assertEqual(reps[key]["status"], "OBSERVED")

    def test_output_caps_do_not_cap_actor_inspection(self):
        u, mesh = FakeUnreal(), Mesh("SM_EG_PremiumShelfBay", 12)
        for i in range(100):
            u.add(sid="shelf_" + str(i), mesh=mesh)
        result = self.inspect(u, max_items=2)["placements"]
        self.assertEqual(result["counts"]["placements"], 100)
        self.assertEqual(result["counts"]["canonical_mesh_paths"], 1)
        self.assertLessEqual(len(result["representatives"]["shelves"]["actors"]), 3)

    def test_pie_actual_cone_capsule_role_and_no_trace(self):
        u = FakeUnreal()
        world = Node(p.NAMESPACE + "/Maps/UEDPIE_0_Map.Map")
        u.pie_worlds.append(world)
        pawn = Actor(world, "BP_propChar_C_0", "", Mesh("Cone", root="/Engine/BasicShapes"), tags=[])
        pawn.components[0].path = "Pawn.PropMesh"
        capsule = Component(name="CapsuleComponent")
        pawn.properties.update(root_component=capsule, capsule_component=capsule)
        u.pawns[world] = pawn
        pie = self.inspect(u)["pie"]
        row = pie["worlds"][0]
        self.assertEqual(row["local_role"], "ROLE_Authority")
        self.assertEqual(row["capsule"]["radius_cm"], 42)
        self.assertTrue(row["capsule"]["is_root"])
        mesh = row["static_mesh_components"]["items"][0]
        self.assertTrue(mesh["is_prop_mesh_name"])
        self.assertEqual(mesh["actual_static_mesh"], "/Engine/BasicShapes/Cone.Cone")
        self.assertFalse(pie["trace"]["executed"])
        self.assertFalse(pie["trace"]["current_graph_read"])

    def test_pie_without_player_does_not_infer_pawn(self):
        u = FakeUnreal()
        u.pie_worlds.append(Node(p.NAMESPACE + "/Maps/UEDPIE_0_Map.Map"))
        pie = self.inspect(u)["pie"]
        self.assertEqual(pie["worlds"][0]["status"], "NO_PLAYER_INDEX_0_PAWN_OR_READ_UNAVAILABLE")

    def test_carnival_pie_not_inspected(self):
        u = FakeUnreal()
        u.pie_worlds.append(Node("/Game/Carnival/UEDPIE_0_Map.Map"))
        self.inspect(u)
        self.assertEqual(u.pawn_reads, [])

    def test_bad_limits_rejected_before_reads(self):
        for value in (0, 101, False, 2.5):
            with self.assertRaises(ValueError):
                p.inspect(FakeUnreal(), max_items=value)

    def test_fake_mutation_guard_is_live(self):
        for name in ("save_map", "load_asset", "set_editor_property", "sphere_trace_single"):
            with self.assertRaises(AssertionError):
                getattr(Node(), name)()
        self.assertEqual(len(ATTEMPTED_MUTATIONS), 4)
        ATTEMPTED_MUTATIONS.clear()


if __name__ == "__main__":
    unittest.main()
