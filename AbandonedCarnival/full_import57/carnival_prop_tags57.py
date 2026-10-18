"""Add the gameplay eligibility tag to the 153 known carnival prop actors.

preview() reads only. apply() changes actor tags in an editor transaction, never
saves, and never edits transforms, lights, Blueprints, components or assets.
The full importer beside this file and its source contract must remain pinned.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys

DEST = "/Game/AbandonedCarnivalFull57_Corrected"
MAP_PATH = DEST + "/Maps/AbandonedCarnivalFull57"
WORLD_PATH = MAP_PATH + ".AbandonedCarnivalFull57"
TAG = "AbandonedCarnivalFull57_Corrected"
CORE_SHA256 = "ffd17f5ae4f81ce1f19cd173b98b9cfcfa26203d40952d6d2ca08d4dd1f3ba00"
NATIVE_CLASS = "/Script/Engine.StaticMeshActor"
IDENTITY_PREFIX = "Full57Id="
EXPECTED_COUNT = 153


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _plan(package_root):
    path = Path(__file__).resolve().with_name("carnival_full_import57.py")
    raw = path.read_bytes()
    _require(CORE_SHA256 in (hashlib.sha256(raw).hexdigest(),
                            hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()),
             "Pinned full importer changed; no helper code executed")
    name = "_carnival_prop_tags_pinned_plan57"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # Needed by the importer's dataclass declarations.
    exec(compile(raw, str(path), "exec"), module.__dict__)
    _require(module.MAP_PATH == MAP_PATH and module.TAG == TAG, "Pinned target differs")
    return module.plan(package_root)[2]


def _report(mode):
    return dict(schema="carnival_prop_tags57/v1", mode=mode,
                status="PROP_TAGS_BLOCKED", target_map=MAP_PATH,
                eligible=0, needs_tag=0, already_tagged=0, changed=0,
                mutation_attempted=0, partial=False, actors=[], errors=[],
                saved_by_helper=False, gameplay_validated=False,
                limitations=["Eligibility tags only; gameplay and native undo are not validated.",
                             "Failures do not automatically roll back; inspect the actor ledger and use editor Undo if needed."])


def _world(u):
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    _require(editor.get_game_world() is None, "Stop Play/Simulate before changing prop tags")
    world = editor.get_editor_world()
    _require(world is not None and str(world.get_path_name()) == WORLD_PATH,
             "Open the saved full-import map: " + MAP_PATH)
    _require(u.EditorAssetLibrary.does_asset_exist(MAP_PATH), "Full-import map must already be saved")
    return world


def _expected(plan):
    props = [row for row in plan["placements"] if row["kind"] == "props"]
    expected = {row["id"]: row for row in props}
    _require(len(props) == len(expected) == EXPECTED_COUNT, "Pinned plan must contain exactly 153 unique prop identities")
    _require(all(key.startswith("prop:") and "PropActor" in row["tags"]
                 for key, row in expected.items()), "Pinned prop identity/tag contract differs")
    return expected


def _snapshot(u, actor, expected, expected_id=None):
    tags = list(actor.get_editor_property("tags"))
    strings = [str(tag) for tag in tags]
    ids = [tag[len(IDENTITY_PREFIX):] for tag in strings if tag.startswith(IDENTITY_PREFIX)]
    _require(len(ids) == 1 and ids[0] in expected, "Unknown/missing/multiple importer prop identity: " + str(actor.get_path_name()))
    identity = ids[0]
    _require(expected_id is None or identity == expected_id, "Prop identity changed before mutation")
    _require(TAG in strings and "PropActor" in strings, "Prop ownership tags missing: " + identity)
    _require(isinstance(actor, u.StaticMeshActor) and str(actor.get_class().get_path_name()) == NATIVE_CLASS,
             "Expected a native StaticMeshActor: " + identity)
    component = actor.get_editor_property("static_mesh_component")
    mesh = component.get_editor_property("static_mesh")
    name = expected[identity]["asset_name"]
    mesh_path = DEST + "/Props/" + name + "." + name
    _require(isinstance(mesh, u.StaticMesh) and str(mesh.get_path_name()) == mesh_path,
             "Unexpected prop mesh: " + identity)
    return dict(actor=actor, id=identity, path=str(actor.get_path_name()), mesh=mesh_path,
                tags=tags, before_tags=strings,
                needs_tag=not any(tag.casefold() == "prop" for tag in strings))


def _scan(u, expected, world=None):
    current = _world(u)
    _require(world is None or current == world, "Editor world changed during tag operation")
    found = {}
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        tags = [str(tag) for tag in actor.get_editor_property("tags")]
        candidate = any(tag.startswith(IDENTITY_PREFIX + "prop:") for tag in tags)
        candidate = candidate or (TAG in tags and "PropActor" in tags)
        # Catch an importer-owned prop mesh whose identity/PropActor tags were removed.
        if not candidate and TAG in tags and isinstance(actor, u.StaticMeshActor):
            mesh = actor.get_editor_property("static_mesh_component").get_editor_property("static_mesh")
            candidate = mesh is not None and str(mesh.get_path_name()).startswith(DEST + "/Props/")
        if not candidate:
            continue  # Unrelated actors, environment, lights and their edits are out of scope.
        row = _snapshot(u, actor, expected)
        _require(row["id"] not in found, "Duplicate importer prop identity: " + row["id"])
        found[row["id"]] = row
    _require(set(found) == set(expected), "Missing importer prop identities: " + ", ".join(sorted(set(expected) - set(found))))
    return current, [found[key] for key in expected]


def _public(row):
    return {key: row[key] for key in ("id", "path", "mesh", "before_tags", "needs_tag")}


def _prepare(package_root, report, mutate=False):
    plan = _plan(package_root)
    expected = _expected(plan)
    u = importlib.import_module("unreal")
    version = str(u.SystemLibrary.get_engine_version())
    _require(version.startswith("5.7."), "This helper requires Unreal Engine 5.7")
    world, rows = _scan(u, expected)
    report.update(engine_version=version, world_path=str(world.get_path_name()),
                  eligible=len(rows), needs_tag=sum(row["needs_tag"] for row in rows),
                  already_tagged=sum(not row["needs_tag"] for row in rows),
                  actors=[dict(_public(row), status="NEEDS_PROP" if row["needs_tag"] else "ALREADY_PRESENT") for row in rows])
    if mutate:
        _require(callable(getattr(u, "Name", None)) and callable(getattr(u, "ScopedEditorTransaction", None)),
                 "Unreal Name/editor transaction APIs unavailable")
        for row in rows:
            _require(callable(getattr(row["actor"], "modify", None)) and
                     callable(getattr(row["actor"], "set_editor_property", None)), "Actor undo/property APIs unavailable")
    return u, expected, world, rows


def preview(package_root):
    """Read-only identity/mesh/tag preview. Dirty maps and light edits are allowed."""
    report = _report("preview")
    try:
        _prepare(package_root, report)
        report["status"] = "PROP_TAGS_PREVIEW_READY"
    except Exception as exc:
        report["errors"].append(str(exc))
    return report


def apply(package_root):
    """Append Prop only after complete validation; preserve tags and leave unsaved."""
    report = _report("apply")
    try:
        u, expected, world, rows = _prepare(package_root, report, mutate=True)
        if not any(row["needs_tag"] for row in rows):
            report["status"] = "PROP_TAGS_ALREADY_PRESENT"
            return report
        with u.ScopedEditorTransaction("Add Prop eligibility tag to carnival props"):
            # Complete revalidation occurs before any actor.modify or tag setter.
            world, rows = _scan(u, expected, world)
            report["actors"] = []
            for original in rows:
                _require(_world(u) == world, "Editor world changed during tag operation")
                actor = original["actor"]
                row = _snapshot(u, actor, expected, original["id"])
                ledger = dict(_public(row), status="ALREADY_PRESENT")
                report["actors"].append(ledger)
                if not row["needs_tag"]:
                    continue
                ledger["status"] = "ATTEMPTED"
                report["mutation_attempted"] += 1
                try:
                    _require(actor.modify() is True, "Actor could not be recorded for undo: " + row["id"])
                    # Use the actual current Name list, never the earlier preview snapshot.
                    row = _snapshot(u, actor, expected, original["id"])
                    ledger.update(_public(row))
                    if not row["needs_tag"]:
                        ledger["status"] = "ALREADY_PRESENT"
                        continue
                    desired = row["tags"] + [u.Name("Prop")]
                    actor.set_editor_property("tags", desired)
                    observed = [str(tag) for tag in actor.get_editor_property("tags")]
                    ledger["after_tags"] = observed
                    _require(observed[:-1] == row["before_tags"] and len(observed) == len(row["tags"]) + 1 and
                             observed[-1].casefold() == "prop", "Prop tag readback/preservation failed: " + row["id"])
                    report["changed"] += 1
                    ledger["status"] = "ADDED_PROP_UNSAVED"
                except Exception as exc:
                    ledger["status"] = "FAILED_MUTATION"
                    ledger["error"] = str(exc)
                    try:
                        observed = [str(tag) for tag in actor.get_editor_property("tags")]
                        ledger["after_tags"] = observed
                        ledger["changed_on_failure"] = observed != ledger["before_tags"]
                        if ledger["changed_on_failure"]:
                            report["changed"] += 1
                    except Exception as read_exc:
                        ledger["readback_error"] = str(read_exc)
                    raise
            _, final_rows = _scan(u, expected, world)
            _require(all(not row["needs_tag"] for row in final_rows), "Final prop tag verification failed")
        report["status"] = "PROP_TAGS_APPLIED_UNSAVED" if report["changed"] else "PROP_TAGS_ALREADY_PRESENT"
    except Exception as exc:
        report["partial"] = report["mutation_attempted"] > 0
        report["status"] = "PROP_TAGS_FAILED_PARTIAL" if report["partial"] else "PROP_TAGS_BLOCKED"
        report["errors"].append(str(exc))
    return report
