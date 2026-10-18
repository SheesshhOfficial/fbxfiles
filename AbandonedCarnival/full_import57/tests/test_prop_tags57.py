"""Focused, portable contract tests for the additive Prop-tag helper.

Only the new helper is imported. These stdlib fakes intentionally expose no save,
asset-editing, transform, Blueprint, or light-setting mutation APIs. Passing these
checks does not establish behavior in a live Unreal Editor.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / "full_plan_fixture.json").read_text(encoding="utf-8"))
PROP_PLACEMENTS = [row for row in FIXTURE["placements"] if row["kind"] == "props"]
DEST = "/Game/AbandonedCarnivalFull57_Corrected"
MAP_PATH = DEST + "/Maps/AbandonedCarnivalFull57"
TAG = "AbandonedCarnivalFull57_Corrected"
NATIVE_CLASS = "/Script/Engine.StaticMeshActor"
ROOT = "MOCK_PACKAGE_ROOT"

_spec = importlib.util.spec_from_file_location(
    "prop_tags57_under_test", HERE.parent / "carnival_prop_tags57.py"
)
helper = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = helper
_spec.loader.exec_module(helper)
REAL_PLAN_LOADER = helper._plan


class FakeName:
    """Non-string Name objects make accidental stringification observable."""

    def __init__(self, text):
        self.text = str(text)

    def __str__(self):
        return self.text

    def __repr__(self):
        return "FakeName(%r)" % self.text

    def __eq__(self, other):
        return isinstance(other, FakeName) and self.text.casefold() == other.text.casefold()

    def __hash__(self):
        return hash(self.text.casefold())


class FakeClass:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path

    def get_name(self):
        return self.path.rsplit(".", 1)[-1]


class FakePackage:
    def __init__(self, path, dirty=False):
        self.path, self.dirty = path, dirty

    def get_path_name(self):
        return self.path

    def get_name(self):
        return self.path

    def is_dirty(self):
        return self.dirty


class FakeWorld:
    def __init__(self, path=MAP_PATH):
        self.path = path + "." + path.rsplit("/", 1)[-1]
        self.package = FakePackage(path, dirty=True)

    def get_path_name(self):
        return self.path

    def get_name(self):
        return self.path.rsplit(".", 1)[-1]

    def get_outermost(self):
        return self.package

    def get_package(self):
        return self.package


class FakeStaticMesh:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path

    def get_class(self):
        return FakeClass("/Script/Engine.StaticMesh")


class FakeStaticMeshComponent:
    def __init__(self, mesh):
        self.mesh = mesh

    def get_editor_property(self, key):
        if key == "static_mesh":
            return self.mesh
        raise AssertionError("Unexpected component read: " + key)

    def set_editor_property(self, key, value):
        raise AssertionError("Component mutation is forbidden: " + key)


class FakeActor:
    def __init__(self, name, tags=(), mesh=None, class_path=NATIVE_CLASS):
        self.name = name
        self.tags = [tag if isinstance(tag, FakeName) else FakeName(tag) for tag in tags]
        self.component = FakeStaticMeshComponent(mesh) if mesh is not None else None
        self.class_path = class_path
        self.world = None
        self.owner = None
        self.writes = []
        self.on_set = None
        self.on_modify = None
        self.modify_calls = 0
        self.modify_result = True
        self.fail_set = False
        self.discard_set = False
        self.transform = {"location": (11.0, 22.0, 33.0), "rotation": (9.0, 8.0, 7.0), "scale": (1.0, 1.0, 1.0)}
        self.light_settings = {"intensity": 4321.0, "temperature": 2900.0}

    def get_path_name(self):
        return self.world.get_path_name() + ":PersistentLevel." + self.name

    def get_name(self):
        return self.name

    def get_actor_label(self):
        return self.name

    def get_class(self):
        return FakeClass(self.class_path)

    def get_world(self):
        return self.world

    def get_editor_property(self, key):
        if key == "tags":
            return list(self.tags)
        if key == "static_mesh_component":
            return self.component
        raise AssertionError("Unexpected actor read: " + key)

    def get_component_by_class(self, cls):
        if cls is FakeStaticMeshComponent:
            return self.component
        raise AssertionError("Unexpected component class")

    def get_components_by_class(self, cls):
        component = self.get_component_by_class(cls)
        return [] if component is None else [component]

    def set_editor_property(self, key, value):
        if key != "tags":
            raise AssertionError("Only actor tags may be mutated: " + key)
        if self.owner is None or not self.owner.transaction_active:
            raise AssertionError("Tag mutation must be inside the transaction")
        self.writes.append(list(value))
        self.owner.setter_calls.append(self)
        if self.fail_set:
            raise RuntimeError("injected tag setter failure")
        if not self.discard_set:
            self.tags = list(value)
        if self.on_set:
            self.on_set()

    def modify(self):
        if self.owner is None or not self.owner.transaction_active:
            raise AssertionError("Undo recording must be inside the transaction")
        self.modify_calls += 1
        self.owner.modify_calls.append(self)
        if self.on_modify:
            self.on_modify()
        return self.modify_result


class FakeStaticMeshActor(FakeActor):
    pass


class FakeUnreal(types.ModuleType):
    def __init__(self):
        super().__init__("unreal")
        self.Name = FakeName
        self.World = FakeWorld
        self.Actor = FakeActor
        self.StaticMeshActor = FakeStaticMeshActor
        self.StaticMesh = FakeStaticMesh
        self.StaticMeshComponent = FakeStaticMeshComponent
        self.EditorActorSubsystem = type("EditorActorSubsystem", (), {})
        self.UnrealEditorSubsystem = type("UnrealEditorSubsystem", (), {})
        self.world = FakeWorld()
        self.game_world = None
        self.actors = []
        self.setter_calls = []
        self.modify_calls = []
        self.transaction_count = 0
        self.transaction_active = False
        self.on_transaction_enter = None
        self.actor_reads = 0
        self.on_actor_read = None
        self.version = "5.7.4-0+++UE5+Release-5.7"
        self.map_exists = True
        self.SystemLibrary = types.SimpleNamespace(get_engine_version=lambda: self.version)
        self.EditorAssetLibrary = types.SimpleNamespace(
            does_asset_exist=lambda path: self.map_exists and path == MAP_PATH,
        )
        self.actor_system = types.SimpleNamespace(get_all_level_actors=self.get_all_level_actors)
        self.editor_system = types.SimpleNamespace(
            get_editor_world=lambda: self.world,
            get_game_world=lambda: self.game_world,
        )
        self.EditorLoadingAndSavingUtils = types.SimpleNamespace(
            get_dirty_map_packages=lambda: [self.world.package],
            get_dirty_content_packages=lambda: [],
        )
        self.EditorLevelLibrary = types.SimpleNamespace(
            get_editor_world=lambda: self.world,
            get_all_level_actors=self.get_all_level_actors,
            get_game_world=lambda: self.game_world,
        )
        self.is_valid = lambda obj: obj is not None
        self.ScopedEditorTransaction = self.transaction
        for index, row in enumerate(PROP_PLACEMENTS):
            name = row["asset_name"]
            mesh_path = DEST + "/Props/" + name + "." + name
            self.add(FakeStaticMeshActor(
                "Prop_%03d" % index,
                row["tags"] + [TAG, "Full57Id=" + row["id"]],
                FakeStaticMesh(mesh_path),
            ))
        self.props = list(self.actors)
        self.foreign = self.add(FakeStaticMeshActor(
            "UserProp", ["UserTag"], FakeStaticMesh("/Game/User/Mesh.Mesh")
        ))
        self.environment = self.add(FakeStaticMeshActor(
            "Environment", [TAG, "MoonfallEnvironment", "Full57Id=env:Environment"],
            FakeStaticMesh(DEST + "/Environment/SM_Environment.SM_Environment"),
        ))
        self.light = self.add(FakeActor(
            "UserAdjustedLight", [TAG, "Full57Id=meta:UserAdjustedLight"],
            class_path="/Script/Engine.PointLight",
        ))

    def add(self, actor):
        actor.world, actor.owner = self.world, self
        self.actors.append(actor)
        return actor

    def get_all_level_actors(self):
        self.actor_reads += 1
        if self.on_actor_read:
            self.on_actor_read(self.actor_reads)
        return list(self.actors)

    def get_editor_subsystem(self, cls):
        if cls is self.EditorActorSubsystem:
            return self.actor_system
        if cls is self.UnrealEditorSubsystem:
            return self.editor_system
        raise AssertionError("Unexpected subsystem")

    def transaction(self, title):
        owner = self
        owner.transaction_count += 1

        class Transaction:
            def __enter__(self):
                owner.transaction_active = True
                if owner.on_transaction_enter:
                    owner.on_transaction_enter()
                return self

            def __exit__(self, exc_type, exc, tb):
                owner.transaction_active = False
                return False

            def cancel(self):
                raise AssertionError("Automatic rollback/cancel is forbidden")

        return Transaction()


class PropTags57Tests(unittest.TestCase):
    def setUp(self):
        self.u = FakeUnreal()
        self.plan = copy.deepcopy(FIXTURE)
        self.plan_patch = patch.object(helper, "_plan", return_value=self.plan)
        self.plan_patch.start()
        self.unreal_patch = patch.dict(sys.modules, {"unreal": self.u})
        self.unreal_patch.start()
        self.addCleanup(self.plan_patch.stop)
        self.addCleanup(self.unreal_patch.stop)

    def run_helper(self, mode="apply"):
        report = getattr(helper, mode)(ROOT)
        self.assertIsInstance(report, dict)
        json.dumps(report, allow_nan=False)
        self.assertIn("errors", report)
        self.assertIsInstance(report["errors"], list)
        self.assertIsInstance(report["partial"], bool)
        return report

    def assert_blocked_without_writes(self, report, transaction_count=0):
        self.assertEqual(report["status"], "PROP_TAGS_BLOCKED", report)
        self.assertTrue(report["errors"], report)
        self.assertFalse(report["partial"], report)
        self.assertEqual(report["changed"], 0, report)
        self.assertEqual(self.u.setter_calls, [])
        self.assertEqual(self.u.modify_calls, [])
        self.assertEqual(self.u.transaction_count, transaction_count)

    @staticmethod
    def strings(actor):
        return [str(tag) for tag in actor.tags]

    def test_fixture_has_exactly_153_unique_prop_identities(self):
        self.assertEqual(len(PROP_PLACEMENTS), 153)
        self.assertEqual(len({row["id"] for row in PROP_PLACEMENTS}), 153)
        self.assertTrue(all(row["id"].startswith("prop:") for row in PROP_PLACEMENTS))

    def test_preview_is_read_only_and_counts_all_exact_props(self):
        before = [list(actor.tags) for actor in self.u.actors]
        report = self.run_helper("preview")
        self.assertEqual(report["status"], "PROP_TAGS_PREVIEW_READY", report)
        self.assertEqual(report["eligible"], 153)
        self.assertEqual(report["needs_tag"], 153)
        self.assertEqual(report["already_tagged"], 0)
        self.assertEqual(report["changed"], 0)
        self.assertFalse(report["partial"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(self.u.transaction_count, 0)
        self.assertEqual(self.u.setter_calls, [])
        self.assertEqual(before, [actor.tags for actor in self.u.actors])
        self.assertEqual(self.u.modify_calls, [])
        self.assertEqual(len(report["actors"]), 153)
        self.assertEqual({row["id"] for row in report["actors"]}, {row["id"] for row in PROP_PLACEMENTS})
        self.assertTrue(all(row["status"] == "NEEDS_PROP" for row in report["actors"]))

    def test_preview_does_not_require_mutation_apis(self):
        self.u.ScopedEditorTransaction = None
        self.u.Name = None
        for actor in self.u.props:
            actor.modify = None
            actor.set_editor_property = None
        report = self.run_helper("preview")
        self.assertEqual(report["status"], "PROP_TAGS_PREVIEW_READY", report)
        self.assertEqual(self.u.setter_calls, [])
        self.assertEqual(self.u.modify_calls, [])

    def test_apply_appends_only_prop_preserving_tag_objects_and_other_state(self):
        for index, actor in enumerate(self.u.props):
            actor.tags += [FakeName("Custom_%03d" % index), FakeName("Mixed_CASE")]
        before_tags = [list(actor.tags) for actor in self.u.props]
        transforms = [copy.deepcopy(actor.transform) for actor in self.u.actors]
        light_settings = copy.deepcopy(self.u.light.light_settings)
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_APPLIED_UNSAVED", report)
        self.assertEqual(report["changed"], 153)
        self.assertEqual(report["eligible"], 153)
        self.assertEqual(report["errors"], [])
        self.assertFalse(report["partial"])
        self.assertEqual(self.u.transaction_count, 1)
        self.assertEqual(len(report["actors"]), 153)
        self.assertTrue(all(row["status"] == "ADDED_PROP_UNSAVED" for row in report["actors"]))
        self.assertTrue(all(row["after_tags"] == row["before_tags"] + ["Prop"] for row in report["actors"]))
        self.assertFalse(report["saved_by_helper"])
        for actor, original in zip(self.u.props, before_tags):
            self.assertEqual(len(actor.writes), 1)
            self.assertEqual(actor.modify_calls, 1)
            self.assertEqual(len(actor.tags), len(original) + 1)
            for old, current in zip(original, actor.tags):
                self.assertIs(old, current)
            self.assertIsInstance(actor.tags[-1], FakeName)
            self.assertEqual(str(actor.tags[-1]), "Prop")
        self.assertEqual(transforms, [actor.transform for actor in self.u.actors])
        self.assertEqual(light_settings, self.u.light.light_settings)
        self.assertEqual(self.u.foreign.writes, [])
        self.assertEqual(self.u.environment.writes, [])
        self.assertEqual(self.u.light.writes, [])

    def test_second_apply_is_idempotent_without_a_second_transaction(self):
        first = self.run_helper()
        self.assertEqual(first["status"], "PROP_TAGS_APPLIED_UNSAVED", first)
        self.u.setter_calls.clear()
        second = self.run_helper()
        self.assertEqual(second["status"], "PROP_TAGS_ALREADY_PRESENT", second)
        self.assertEqual(second["changed"], 0)
        self.assertEqual(second["needs_tag"], 0)
        self.assertEqual(second["already_tagged"], 153)
        self.assertEqual(self.u.transaction_count, 1)
        self.assertEqual(self.u.setter_calls, [])

    def test_all_already_prop_casefolded_needs_no_transaction(self):
        variants = ("Prop", "prop", "PROP", "pRoP")
        for index, actor in enumerate(self.u.props):
            actor.tags.append(FakeName(variants[index % len(variants)]))
        originals = [list(actor.tags) for actor in self.u.props]
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_ALREADY_PRESENT", report)
        self.assertEqual(report["changed"], 0)
        self.assertEqual(report["needs_tag"], 0)
        self.assertEqual(report["already_tagged"], 153)
        self.assertEqual(self.u.transaction_count, 0)
        self.assertEqual(self.u.setter_calls, [])
        for actor, original in zip(self.u.props, originals):
            self.assertTrue(all(a is b for a, b in zip(actor.tags, original)))

    def test_mixed_existing_prop_case_variants_only_writes_missing(self):
        existing = self.u.props[::3]
        for actor in existing:
            actor.tags.append(FakeName("pRoP"))
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_APPLIED_UNSAVED", report)
        self.assertEqual(report["changed"], 102)
        self.assertEqual(report["already_tagged"], 51)
        self.assertEqual(len(self.u.setter_calls), 102)
        self.assertTrue(all(actor.writes == [] for actor in existing))
        self.assertTrue(all(sum(str(tag).casefold() == "prop" for tag in actor.tags) == 1 for actor in self.u.props))

    def test_unrelated_native_props_and_lights_are_untouched(self):
        self.u.foreign.tags.extend([FakeName("PropActor"), FakeName("Prop")])
        self.u.light.tags.append(FakeName("Prop"))
        originals = {actor: list(actor.tags) for actor in (self.u.foreign, self.u.environment, self.u.light)}
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_APPLIED_UNSAVED", report)
        for actor, tags in originals.items():
            self.assertEqual(actor.writes, [])
            self.assertEqual(len(actor.tags), len(tags))
            self.assertTrue(all(a is b for a, b in zip(actor.tags, tags)))

    def test_dirty_saved_map_and_changed_light_settings_are_allowed(self):
        self.u.world.package.dirty = True
        self.u.light.light_settings.update(intensity=99887.0, temperature=6500.0, casts_shadows=False)
        before = copy.deepcopy(self.u.light.light_settings)
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_APPLIED_UNSAVED", report)
        self.assertEqual(self.u.light.light_settings, before)
        self.assertTrue(self.u.world.package.dirty)

    def test_wrong_saved_map_is_blocked(self):
        self.u.world = FakeWorld("/Game/Other/OtherMap")
        self.assert_blocked_without_writes(self.run_helper())

    def test_unsaved_map_is_blocked(self):
        self.u.world = FakeWorld("/Temp/Untitled_1")
        self.assert_blocked_without_writes(self.run_helper())

    def test_correct_path_without_saved_map_asset_is_blocked(self):
        self.u.map_exists = False
        self.assert_blocked_without_writes(self.run_helper())

    def test_unsupported_engine_version_is_blocked(self):
        self.u.version = "5.6.1"
        self.assert_blocked_without_writes(self.run_helper())

    def test_no_editor_world_is_blocked(self):
        self.u.world = None
        self.assert_blocked_without_writes(self.run_helper())

    def test_pie_is_blocked(self):
        self.u.game_world = FakeWorld("/Temp/UEDPIE_0_AbandonedCarnivalFull57")
        self.assert_blocked_without_writes(self.run_helper())

    def test_missing_prop_identity_is_blocked(self):
        self.u.actors.remove(self.u.props[0])
        self.assert_blocked_without_writes(self.run_helper())

    def test_extra_importer_owned_prop_identity_is_blocked(self):
        original = self.u.props[0]
        self.u.add(FakeStaticMeshActor(
            "ExtraOwnedProp", ["PropActor", TAG, "Full57Id=prop:Unexpected"], original.component.mesh
        ))
        self.assert_blocked_without_writes(self.run_helper())

    def test_duplicate_prop_identity_is_blocked(self):
        original = self.u.props[0]
        self.u.add(FakeStaticMeshActor("DuplicateOwnedProp", original.tags, original.component.mesh))
        self.assert_blocked_without_writes(self.run_helper())

    def test_two_identity_tags_on_one_prop_are_blocked(self):
        self.u.props[0].tags.append(FakeName("Full57Id=" + PROP_PLACEMENTS[1]["id"]))
        self.assert_blocked_without_writes(self.run_helper())

    def test_missing_ownership_or_propactor_or_identity_tags_are_blocked(self):
        for text in (TAG, "PropActor", "Full57Id=" + PROP_PLACEMENTS[0]["id"]):
            with self.subTest(missing=text):
                actor = self.u.props[0]
                original = actor.tags
                actor.tags = [tag for tag in original if str(tag) != text]
                self.assert_blocked_without_writes(self.run_helper())
                actor.tags = original

    def test_wrong_mesh_path_is_blocked(self):
        self.u.props[0].component.mesh.path = "/Game/Other/Other.Other"
        self.assert_blocked_without_writes(self.run_helper())

    def test_missing_mesh_is_blocked(self):
        self.u.props[0].component.mesh = None
        self.assert_blocked_without_writes(self.run_helper())

    def test_expected_mesh_path_on_wrong_object_type_is_blocked(self):
        expected_path = self.u.props[0].component.mesh.path
        self.u.props[0].component.mesh = types.SimpleNamespace(get_path_name=lambda: expected_path)
        self.assert_blocked_without_writes(self.run_helper())

    def test_blueprint_or_spoofed_native_name_is_blocked(self):
        self.u.props[0].class_path = "/Game/Blueprints/StaticMeshActor.StaticMeshActor"
        self.assert_blocked_without_writes(self.run_helper())

    def test_wrong_native_actor_class_is_blocked(self):
        self.u.props[0].class_path = "/Script/Engine.Actor"
        self.assert_blocked_without_writes(self.run_helper())

    def test_native_class_path_on_wrong_actor_type_is_blocked(self):
        original = self.u.props[0]
        self.u.actors.remove(original)
        self.u.add(FakeActor("SpoofedProp", original.tags, original.component.mesh))
        self.assert_blocked_without_writes(self.run_helper())

    def test_source_plan_failure_is_reported_without_mutation(self):
        with patch.object(helper, "_plan", side_effect=ValueError("pinned source check failed")):
            self.assert_blocked_without_writes(self.run_helper())

    def test_tampered_pinned_core_is_rejected_before_import_or_execution(self):
        core_path = (HERE.parent / "carnival_full_import57.py").resolve()
        original_read = Path.read_bytes

        def read_bytes(path):
            if path.resolve() == core_path:
                return b"raise RuntimeError('UNTRUSTED CORE EXECUTED')\n"
            return original_read(path)

        with patch.object(Path, "read_bytes", new=read_bytes), patch.object(
            helper.importlib.util, "spec_from_file_location"
        ) as create_spec:
            with self.assertRaisesRegex(ValueError, "Pinned full importer changed"):
                REAL_PLAN_LOADER(ROOT)
            create_spec.assert_not_called()
        self.assertEqual(self.u.transaction_count, 0)
        self.assertEqual(self.u.modify_calls, [])
        self.assertEqual(self.u.setter_calls, [])

    def test_invalid_prop_count_in_plan_is_blocked(self):
        self.plan["placements"].remove(next(row for row in self.plan["placements"] if row["kind"] == "props"))
        self.assert_blocked_without_writes(self.run_helper())

    def test_duplicate_prop_identity_in_plan_is_blocked(self):
        rows = [row for row in self.plan["placements"] if row["kind"] == "props"]
        rows[1]["id"] = rows[0]["id"]
        self.assert_blocked_without_writes(self.run_helper())

    def test_revalidation_inside_transaction_blocks_stale_identity_mesh_or_tags(self):
        for change in ("identity", "mesh", "tags"):
            with self.subTest(change=change):
                actor = self.u.props[0]
                old_tags, old_mesh = list(actor.tags), actor.component.mesh

                def mutate():
                    if change == "identity":
                        actor.tags = [tag for tag in actor.tags if not str(tag).startswith("Full57Id=")]
                        actor.tags.append(FakeName("Full57Id=prop:StaleIdentity"))
                    elif change == "mesh":
                        actor.component.mesh = FakeStaticMesh("/Game/Wrong/Wrong.Wrong")
                    else:
                        actor.tags = [tag for tag in actor.tags if str(tag) != "PropActor"]

                before_transactions = self.u.transaction_count
                self.u.on_transaction_enter = mutate
                report = self.run_helper()
                self.assert_blocked_without_writes(report, before_transactions + 1)
                actor.tags, actor.component.mesh = old_tags, old_mesh
                self.u.on_transaction_enter = None

    def test_midrun_setter_failure_is_partial_and_keeps_previous_changes(self):
        self.u.props[2].fail_set = True
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_FAILED_PARTIAL", report)
        self.assertTrue(report["partial"])
        self.assertTrue(report["errors"])
        self.assertGreaterEqual(report["changed"], 1)
        self.assertLess(report["changed"], 153)
        changed = [actor for actor in self.u.props if "Prop" in self.strings(actor)]
        self.assertEqual(report["changed"], len(changed))
        self.assertEqual(self.u.props[0].writes[-1][-1], FakeName("Prop"))
        self.assertEqual(len(self.u.props[0].writes), 1, "No automatic tag rollback")
        self.assertEqual(self.u.transaction_count, 1)
        self.assertEqual(self.u.foreign.writes, [])
        self.assertEqual(self.u.light.writes, [])
        ledger = {row["id"]: row for row in report["actors"]}
        self.assertEqual(ledger[PROP_PLACEMENTS[0]["id"]]["status"], "ADDED_PROP_UNSAVED")
        failed = ledger[PROP_PLACEMENTS[2]["id"]]
        self.assertEqual(failed["status"], "FAILED_MUTATION")
        self.assertIn("injected tag setter failure", failed["error"])
        self.assertEqual(failed["before_tags"], failed["after_tags"])
        self.assertFalse(failed["changed_on_failure"])

    def test_readback_failure_is_reported_and_does_not_rollback_prior_changes(self):
        self.u.props[2].discard_set = True
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_FAILED_PARTIAL", report)
        self.assertTrue(report["partial"])
        self.assertTrue(report["errors"])
        self.assertIn("Prop", self.strings(self.u.props[0]))
        self.assertEqual(len(self.u.props[0].writes), 1)
        self.assertNotIn("Prop", self.strings(self.u.props[2]))
        self.assertEqual(len(self.u.props[2].writes), 1)
        self.assertEqual(report["actors"][-1]["status"], "FAILED_MUTATION")

    def test_latest_custom_tag_objects_are_preserved_after_undo_recording(self):
        actor = self.u.props[0]
        custom = FakeName("AddedDuringUndoRecording")
        actor.on_modify = lambda: actor.tags.append(custom)
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_APPLIED_UNSAVED", report)
        self.assertIs(actor.tags[-2], custom)
        self.assertEqual(str(actor.tags[-1]), "Prop")

    def test_identity_mesh_or_ownership_change_after_modify_blocks_the_setter(self):
        for change in ("identity", "mesh", "tags"):
            with self.subTest(change=change):
                actor = self.u.props[0]
                old_tags, old_mesh = list(actor.tags), actor.component.mesh

                def mutate():
                    if change == "identity":
                        actor.tags = [tag for tag in actor.tags if not str(tag).startswith("Full57Id=")]
                        actor.tags.append(FakeName("Full57Id=prop:ChangedAfterModify"))
                    elif change == "mesh":
                        actor.component.mesh = FakeStaticMesh("/Game/Wrong/Wrong.Wrong")
                    else:
                        actor.tags = [tag for tag in actor.tags if str(tag) != TAG]

                actor.on_modify = mutate
                report = self.run_helper()
                self.assertEqual(report["status"], "PROP_TAGS_FAILED_PARTIAL", report)
                self.assertTrue(report["partial"])
                self.assertTrue(report["errors"])
                self.assertEqual(self.u.setter_calls, [])
                self.assertEqual(report["actors"][0]["status"], "FAILED_MUTATION")
                actor.tags, actor.component.mesh = old_tags, old_mesh
                actor.on_modify = None

    def test_failed_undo_recording_blocks_tag_setter(self):
        self.u.props[0].modify_result = False
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_FAILED_PARTIAL", report)
        self.assertTrue(report["partial"])
        self.assertEqual(self.u.setter_calls, [])
        self.assertEqual(report["changed"], 0)
        self.assertTrue(report["errors"])

    def test_midrun_stale_target_is_not_written(self):
        stale = self.u.props[1]
        self.u.props[0].on_set = lambda: setattr(
            stale.component, "mesh", FakeStaticMesh("/Game/Wrong/Wrong.Wrong")
        )
        report = self.run_helper()
        self.assertEqual(report["status"], "PROP_TAGS_FAILED_PARTIAL", report)
        self.assertTrue(report["partial"])
        self.assertTrue(report["errors"])
        self.assertEqual(stale.writes, [])
        self.assertNotIn("Prop", self.strings(stale))
        self.assertIn("Prop", self.strings(self.u.props[0]))
        self.assertLess(report["changed"], 153)


if __name__ == "__main__":
    unittest.main()
