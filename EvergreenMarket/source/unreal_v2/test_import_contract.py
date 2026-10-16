"""Pure-Python contract tests. These do not emulate or validate Unreal APIs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import import_supermarket_unreal as importer


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "assets").mkdir()
        (self.root / "assets/a.fbx").write_bytes(b"TEST FIXTURE ONLY, not real FBX")
        self.materials = {"schema_version": 1, "materials": [
            {"material_id": "Mat1", "base_color_rgba": [1, 1, 1, 1], "roughness": 0.6, "metallic": 0}]}
        self.manifest = {"coordinate_system": importer.COORDINATES, "rotation_order": "pitch_yaw_roll",
            "fbx_import": {"convert_scene": False, "convert_scene_unit": False,
                           "force_front_x_axis": False, "import_uniform_scale": 1.0,
                           "transform_vertex_to_absolute": True},
            "assets": [{"asset_id": "a", "name": "Shopping_Cart", "fbx_path": "assets/a.fbx",
                        "bounds_cm": [10, 20, 30], "default_pivot": "bottom_center", "materials": ["Mat1"],
                        "category": "disguise_candidate", "disguise_tier": "conditional",
                        "collision": {"strategy": "box"}}],
            "placements": [{"instance_id": "i1", "asset_id": "a", "location_cm": [1, -1, 30],
                            "rotation_deg": [0, 0, 0], "quaternion_xyzw": [0, 0, 0, 1], "scale": [1, 1, 1]}]}
        self.write()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        (self.root / "materials.json").write_text(json.dumps(self.materials))

    def load(self):
        self.write()
        return importer.load_contract(self.root)

    def test_valid_and_nonmutating_plan(self):
        contract = self.load()
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        plan = importer.run(self.root)
        self.assertEqual(plan["placement_count"], 1)
        self.assertEqual(before, sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*")))
        self.assertIn("a__sector_0_-1", importer.make_plan(contract)["groups"])

    def test_missing_fbx(self):
        (self.root / "assets/a.fbx").unlink()
        with self.assertRaisesRegex(ValueError, "Missing source"):
            self.load()

    def test_path_escape(self):
        self.manifest["assets"][0]["fbx_path"] = "../a.fbx"
        with self.assertRaisesRegex(ValueError, "escapes package"):
            self.load()

    def test_duplicate_instance(self):
        self.manifest["placements"].append(copy.deepcopy(self.manifest["placements"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate instance"):
            self.load()

    def test_unknown_material(self):
        self.manifest["assets"][0]["materials"] = ["Unknown"]
        with self.assertRaisesRegex(ValueError, "unknown material"):
            self.load()

    def test_nan_location(self):
        self.manifest["placements"][0]["location_cm"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.load()

    def test_bad_quaternion(self):
        self.manifest["placements"][0]["quaternion_xyzw"] = [0, 0, 0, 0]
        with self.assertRaisesRegex(ValueError, "not normalized"):
            self.load()

    def test_negative_scale(self):
        self.manifest["placements"][0]["scale"] = [-1, 1, 1]
        with self.assertRaisesRegex(ValueError, "positive"):
            self.load()

    def test_flat_surface_allowed(self):
        self.manifest["assets"][0]["bounds_cm"] = [10, 20, 0]
        self.manifest["assets"][0]["collision"] = {"strategy": "none"}
        self.assertEqual(importer.make_plan(self.load())["asset_count"], 1)

    def test_fingerprint_tracks_fbx(self):
        previous = self.load()["fingerprint"]
        (self.root / "assets/a.fbx").write_bytes(b"CHANGED")
        self.assertNotEqual(previous, self.load()["fingerprint"])

    def test_sample_caps_and_full_keeps_all(self):
        for i in range(2, 9):
            p = copy.deepcopy(self.manifest["placements"][0])
            p["instance_id"] = f"i{i}"
            p["rotation_deg"] = [0, i * 10, 0]
            self.manifest["placements"].append(p)
        contract = self.load()
        self.assertEqual(importer.make_plan(contract)["placement_count"], 3)
        self.assertEqual(importer.make_plan(contract, "full")["placement_count"], 8)

    def test_unused_slot_may_be_stripped(self):
        asset = {"asset_id": "a", "materials": ["A", "B", "unused"], "used_materials": ["A", "B"]}
        importer._validate_material_slots(asset, ["B", "A"])

    def test_missing_used_slot_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing used material"):
            importer._validate_material_slots({"asset_id": "a", "materials": ["A", "B"]}, ["A"])

    def test_unknown_slot_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown imported slot"):
            importer._validate_material_slots({"asset_id": "a", "materials": ["A"]}, ["A", "C"])

    def test_duplicate_slot_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate imported slot"):
            importer._validate_material_slots({"asset_id": "a", "materials": ["A"]}, ["A", "A"])

    def test_full_needs_review_before_unreal_import(self):
        with self.assertRaisesRegex(ValueError, "Inspect a sample"):
            importer.run(self.root, execute=True, phase="full")


class CollisionEnumRegressionTests(unittest.TestCase):
    def api(self):
        return SimpleNamespace(
            CollisionResponseType=SimpleNamespace(ECR_IGNORE=0, ECR_BLOCK=2),
            CollisionChannel=SimpleNamespace(ECC_VISIBILITY=3),
            CollisionEnabled=SimpleNamespace(NO_COLLISION=0, QUERY_ONLY=1))

    def test_documented_collision_enum_names(self):
        importer._check_collision_api(self.api())
        import inspect
        source = inspect.getsource(importer._new_ism)
        self.assertIn("u.CollisionResponseType.ECR_IGNORE", source)
        self.assertIn("u.CollisionResponseType.ECR_BLOCK", source)
        self.assertNotIn("u.CollisionResponseType.IGNORE", source)
        self.assertNotIn("u.CollisionResponseType.BLOCK", source)

    def test_wrong_names_fail_preflight(self):
        api = self.api()
        api.CollisionResponseType = SimpleNamespace(IGNORE=0, BLOCK=2)
        with self.assertRaisesRegex(ValueError, "ECR_IGNORE unavailable"):
            importer._check_collision_api(api)

    def test_missing_block_fails_preflight(self):
        api = self.api()
        del api.CollisionResponseType.ECR_BLOCK
        with self.assertRaisesRegex(ValueError, "ECR_BLOCK unavailable"):
            importer._check_collision_api(api)


if __name__ == "__main__":
    unittest.main()
