"""Read-only, current-editor-map diagnostics for the premium v3 UE 5.7.4 handoff.

Importing this module does nothing. In the Unreal Python console:
    import json, premium_preflight574 as p
    print(json.dumps(p.inspect(), indent=2, allow_nan=False))

This module never loads an asset/map, switches worlds, runs a trace, edits a
Blueprint, changes selection, starts/stops PIE, imports, saves, or writes a file.
It reads loaded references and cached Asset Registry metadata only. Source counts
are diagnostic expectations, not a gameplay/cooked-collision certification.
"""
from collections import Counter, defaultdict
import math
import re

NAMESPACE = "/Game/PremiumStoreV3"
EXPECTED_MAP = NAMESPACE + "/FullPreview574_v001/Maps/L_V3_AllPlacements"
EXPECTED_VERSION = "5.7.4"
SOURCE_COUNTS = {
    "placements": 6593, "prop_placements": 5574, "canonical_asset_ids": 264,
    "canonical_mesh_paths": 264, "fixture_lights": 67, "spawn_markers": 10,
    "boundary_markers": 4, "boundary_barriers": 4,
}
SOURCE_CONVEX_TOTAL = 235
KNOWN_HULL_COUNTS = {"SM_EG_PremiumShelfBay": 12,
                     "SM_FULL_OpenFrontRefrigeratedBay": 10}
SHAPE_FIELDS = ("convex_elems", "box_elems", "sphere_elems", "sphyl_elems",
                "tapered_capsule_elems", "level_set_elems", "ml_level_set_elems",
                "skinned_level_set_elems", "skinned_triangle_mesh_elems")
# Every engine method invoked by this module must be on this audited read list.
READ_METHODS = frozenset({
    "get_engine_version", "get_editor_subsystem", "get_editor_world",
    "get_path_name", "get_name", "get_class", "get_editor_property",
    "get_dirty_map_packages", "get_dirty_content_packages", "get_asset_registry",
    "get_assets_by_path", "is_loading_assets", "get_all_level_actors",
    "get_world", "get_components_by_class", "get_actor_label",
    "get_collision_enabled", "get_collision_profile_name", "get_collision_object_type",
    "get_collision_response_to_channel", "get_simple_collision_count",
    "get_convex_collision_count", "get_bounds", "get_num_uv_channels",
    "get_pie_worlds", "get_player_pawn", "get_local_role", "get_remote_role",
    "get_actor_location", "get_scaled_capsule_radius", "get_scaled_capsule_half_height",
})


class _Read:
    def __init__(self):
        self.missing = Counter()

    def note(self, key):
        self.missing[key] += 1

    def call(self, obj, method, *args, **kwargs):
        if method not in READ_METHODS:
            raise RuntimeError("Non-read API rejected: " + method)
        try:
            if obj is None:
                raise AttributeError("no object")
            return getattr(obj, method)(*args, **kwargs)
        except Exception as exc:
            self.note(method + ": " + type(exc).__name__)
            return None

    def prop(self, obj, name):
        try:
            if obj is None:
                raise AttributeError("no object")
            return obj.get_editor_property(name)
        except Exception as exc:
            self.note("property " + name + ": " + type(exc).__name__)
            return None

    def cls(self, u, name):
        value = getattr(u, name, None)
        if value is None:
            self.note("Unreal type " + name + " unavailable")
        return value

    def subsystem(self, u, name):
        cls = self.cls(u, name)
        return self.call(u, "get_editor_subsystem", cls) if cls else None

    def path(self, obj):
        return self.call(obj, "get_path_name") if obj is not None else None


def _token(value):
    if value is None:
        return None
    text = str(value)
    # UE enum strings may be 'CollisionEnabled.X' or '<CollisionEnabled.X: n>'.
    return text.strip("<>").split(":", 1)[0].rsplit(".", 1)[-1]


def _vector(value):
    if value is None:
        return None
    try:
        result = [float(value.x), float(value.y), float(value.z)]
        return result if all(math.isfinite(x) for x in result) else None
    except (AttributeError, TypeError, ValueError):
        return None


def _package(path):
    return str(path).split(".", 1)[0] if path else None


def _within(path, root=NAMESPACE):
    return bool(path and (path == root or path.startswith(root + "/")))


def _tag_values(tags, prefix):
    return [tag[len(prefix):] for tag in tags if tag.startswith(prefix)]


def _bounded(rows, limit):
    return {"total": len(rows), "items": rows[:limit], "omitted": max(0, len(rows) - limit)}


def _dirty(r, u, limit):
    api = r.cls(u, "EditorLoadingAndSavingUtils")
    result, complete, full = {}, True, {}
    for kind, method in (("maps", "get_dirty_map_packages"),
                         ("content", "get_dirty_content_packages")):
        packages = r.call(api, method)
        if packages is None:
            result[kind], full[kind], complete = None, None, False
        else:
            names = [r.path(p) for p in packages]
            if any(p is None for p in names):
                complete = False
            names = sorted(str(p) for p in names if p is not None)
            result[kind], full[kind] = _bounded(names, limit), names
    result["status"] = ("UNAVAILABLE" if not complete else
                        "DIRTY_WORK_PRESENT" if any(full.values()) else "CLEAN")
    return result, full


def _registry(r, u, limit):
    registry = r.call(r.cls(u, "AssetRegistryHelpers"), "get_asset_registry")
    if registry is None:
        return {"status": "UNAVAILABLE", "maps": None, "assets": None}
    gathering = r.call(registry, "is_loading_assets")
    data = r.call(registry, "get_assets_by_path", NAMESPACE,
                  recursive=True, include_only_on_disk_assets=True)
    if data is None:
        return {"status": "UNAVAILABLE", "maps": None, "assets": None,
                "note": "No forced Asset Registry scan or asset load was attempted."}
    rows, incomplete = [], False
    for item in data:
        package = r.prop(item, "package_name")
        name = r.prop(item, "asset_name")
        class_path = r.prop(item, "asset_class_path")
        if package is None or name is None or class_path is None:
            incomplete = True
        rows.append({"package": str(package) if package is not None else None,
                     "name": str(name) if name is not None else None,
                     "class": str(class_path) if class_path is not None else None})
    rows.sort(key=lambda row: row["package"] or "")
    maps = [row["package"] for row in rows if row["class"] == "/Script/Engine.World"]
    return {"status": "PARTIAL" if incomplete or gathering is not False else "SNAPSHOT",
            "scope": "Cached on-disk assets only; missing metadata is not proof of absence.",
            "initial_registry_scan_active": gathering,
            "maps": _bounded(maps, limit), "assets": _bounded(rows, limit),
            "classes": dict(sorted(Counter(row["class"] or "UNKNOWN" for row in rows).items()))}


def _collision(r, u, component):
    channels = r.cls(u, "CollisionChannel")
    out = {"enabled": _token(r.call(component, "get_collision_enabled")),
           "profile": _token(r.call(component, "get_collision_profile_name")),
           "object_type": _token(r.call(component, "get_collision_object_type"))}
    for name, channel in (("pawn", "ECC_PAWN"), ("visibility", "ECC_VISIBILITY")):
        enum = getattr(channels, channel, None) if channels else None
        out[name] = _token(r.call(component, "get_collision_response_to_channel", enum)) if enum is not None else None
        if enum is None:
            r.note("CollisionChannel." + channel + " unavailable")
    return out


def _mesh(r, mesh, mesh_ss):
    body = r.prop(mesh, "body_setup")
    aggregate = r.prop(body, "agg_geom") if body is not None else None
    shapes = {}
    for kind in SHAPE_FIELDS:
        values = r.prop(aggregate, kind) if aggregate is not None else None
        shapes[kind] = len(values) if values is not None else None
    bounds = r.call(mesh, "get_bounds")
    def count(method, *args):
        value = r.call(mesh_ss, method, *args)
        if type(value) is not int or value < 0:
            r.note(method + ": unavailable or invalid negative/non-integer count")
            return None
        return value

    out = {"path": r.path(mesh), "collision_trace_flag": _token(r.prop(body, "collision_trace_flag")),
           "shapes": shapes,
           "convex_count": shapes["convex_elems"],
           "subsystem_convex_count": count("get_convex_collision_count", mesh),
           "subsystem_simple_count": count("get_simple_collision_count", mesh),
           "uv_channels_lod0": count("get_num_uv_channels", mesh, 0),
           "bounds_origin_cm": _vector(getattr(bounds, "origin", None)),
           "bounds_extent_cm": _vector(getattr(bounds, "box_extent", None))}
    if body is None:
        r.note("Loaded mesh BodySetup unavailable")
    mesh_name = (out["path"] or "").rsplit(".", 1)[-1]
    if mesh_name in KNOWN_HULL_COUNTS:
        out["source_expected_convex_count"] = KNOWN_HULL_COUNTS[mesh_name]
        out["source_count_match"] = (None if out["convex_count"] is None else
                                     out["convex_count"] == KNOWN_HULL_COUNTS[mesh_name])
    return out


def _representative_groups(aid, mesh_path):
    text = (str(aid) + " " + str(mesh_path)).lower()
    groups = []
    if "shelf" in text:
        groups.append("shelves")
    if "main_floor" in text or "mainfloor" in text:
        groups.append("floor")
    if "crushed_tomatoes" in text or re.search(r"(?:^|[^a-z0-9])(can|cans|canned)(?:[^a-z0-9]|$)", text):
        groups.append("can")
    if "refrigerat" in text:
        groups.append("refrigerated_bay")
    return groups


def _actors(r, u, world, map_path, limit):
    if not _within(map_path):
        return {"status": "SKIPPED_NON_PREMIUM_MAP",
                "note": "Open the intended premium map yourself only after dealing with unsaved work. No map was changed."}
    subsystem = r.subsystem(u, "EditorActorSubsystem")
    actors = r.call(subsystem, "get_all_level_actors")
    if actors is None:
        return {"status": "UNAVAILABLE"}
    mesh_type = r.cls(u, "StaticMeshComponent")
    mesh_ss = r.subsystem(u, "StaticMeshEditorSubsystem")
    counts = Counter({key: 0 for key in SOURCE_COUNTS})
    counts.update({"owner_tagged": 0, "prop_outside_placement": 0, "non_native_static_mesh_actor_placements": 0,
                   "premium_mesh_without_owner_tag": 0, "actors_with_unreadable_tags": 0})
    errors, error_counts, signatures = [], Counter(), Counter()
    ids, mesh_ids, phase_counts, seen_placements = defaultdict(set), defaultdict(set), Counter(), Counter()
    mesh_cache, reps = {}, {key: [] for key in ("shelves", "floor", "can", "refrigerated_bay")}
    unknown_component_count = 0

    def issue(code, actor_path, detail=None):
        error_counts[code] += 1
        if len(errors) < limit:
            row = {"code": code, "actor": actor_path}
            if detail is not None:
                row["detail"] = detail
            errors.append(row)

    for actor in actors:
        # EditorActorSubsystem omits PIE actors; get_world additionally prevents cross-world leakage.
        actor_world = r.call(actor, "get_world")
        if actor_world is None:
            issue("ACTOR_WORLD_UNAVAILABLE", r.path(actor))
            continue
        if actor_world != world:
            continue
        tags_value = r.prop(actor, "tags")
        if tags_value is None:
            counts["actors_with_unreadable_tags"] += 1
            continue
        tags = [str(tag) for tag in tags_value]
        owned = "PremiumStoreV3" in tags
        placements, aids = _tag_values(tags, "V3Placement="), _tag_values(tags, "V3Asset=")
        phases = _tag_values(tags, "V3Phase=")
        prop = "Prop" in tags
        if owned:
            counts["owner_tagged"] += 1
            for prefix, key in (("V3FixtureLight=", "fixture_lights"), ("V3SpawnMarker=", "spawn_markers"),
                                ("V3BoundaryMarker=", "boundary_markers"), ("V3BoundaryBarrier=", "boundary_barriers")):
                if _tag_values(tags, prefix):
                    counts[key] += 1
        if prop and not placements:
            counts["prop_outside_placement"] += 1
        # Referenced components are already loaded. No AssetData.get_asset/load_asset call is used.
        components = r.call(actor, "get_components_by_class", mesh_type) if mesh_type else None
        if components is None:
            unknown_component_count += 1
            continue
        premium_components = []
        for comp in components:
            mesh = r.prop(comp, "static_mesh")
            mesh_path = r.path(mesh)
            if owned or placements or _within(_package(mesh_path)):
                premium_components.append((comp, mesh, mesh_path))
                if not owned and _within(_package(mesh_path)):
                    counts["premium_mesh_without_owner_tag"] += 1
                    issue("MISSING_OWNER_TAG", r.path(actor))
        if not owned and not placements:
            continue
        actor_path = r.path(actor)
        if not placements:
            if _tag_values(tags, "V3BoundaryBarrier="):
                for comp, unused, unused_path in premium_components:
                    col = _collision(r, u, comp)
                    if any(col[key] is None for key in ("enabled", "pawn", "visibility")):
                        issue("BARRIER_COLLISION_UNAVAILABLE", actor_path)
                    elif (col["enabled"], col["pawn"], col["visibility"]) != ("QUERY_AND_PHYSICS", "ECR_BLOCK", "ECR_IGNORE"):
                        issue("BARRIER_COLLISION_MISMATCH", actor_path, col)
            continue
        counts["placements"] += 1
        counts["prop_placements"] += int(prop)
        actor_class = r.path(r.call(actor, "get_class"))
        if actor_class != "/Script/Engine.StaticMeshActor":
            counts["non_native_static_mesh_actor_placements"] += 1
            issue("EXPECTED_NATIVE_STATIC_MESH_ACTOR", actor_path, actor_class)
        if len(placements) != 1 or len(aids) != 1 or len(phases) != 1 or not owned or not all(placements + aids + phases):
            issue("OWNERSHIP_TAGS_MALFORMED", actor_path)
        for placement in placements:
            seen_placements[placement] += 1
        phase_counts.update(phases)
        if phases != ["full"]:
            issue("PLACEMENT_PHASE_NOT_FULL", actor_path, phases)
        if len(premium_components) != 1:
            issue("EXPECTED_ONE_STATIC_MESH_COMPONENT", actor_path, len(premium_components))
        for comp, mesh, mesh_path in premium_components:
            if mesh is None or not mesh_path:
                issue("MISSING_MESH_REFERENCE", actor_path)
                continue
            if not _within(_package(mesh_path)):
                issue("PLACEMENT_MESH_OUTSIDE_PREMIUM_NAMESPACE", actor_path, mesh_path)
            aid = aids[0] if len(aids) == 1 else None
            if aid:
                ids[aid].add(mesh_path)
                mesh_ids[mesh_path].add(aid)
            if mesh_path not in mesh_cache:
                mesh_cache[mesh_path] = _mesh(r, mesh, mesh_ss)
            info = mesh_cache[mesh_path]
            col = _collision(r, u, comp)
            signatures[tuple(col[key] for key in ("enabled", "profile", "object_type", "pawn", "visibility"))] += 1
            convex = info["convex_count"]
            if convex is None or any(v is None for v in col.values()):
                issue("COLLISION_READ_INCOMPLETE", actor_path)
            else:
                wanted = ("QUERY_AND_PHYSICS", "ECR_BLOCK") if convex else ("NO_COLLISION", "ECR_IGNORE")
                if (col["enabled"], col["pawn"]) != wanted or col["visibility"] != wanted[1]:
                    issue("SOURCE_COLLISION_SETTINGS_DIFFER", actor_path, col)
                if prop and convex == 0:
                    issue("PROP_WITHOUT_CONVEX_COLLISION", actor_path)
            for group in _representative_groups(aid, mesh_path):
                if len(reps[group]) < 3:
                    reps[group].append({"actor": actor_path, "label": r.call(actor, "get_actor_label", False),
                                        "location_cm": _vector(r.call(actor, "get_actor_location")),
                                        "asset_id": aid, "prop_tag": prop, "phase": phases,
                                        "component_collision": col, "mesh": info})
    counts["canonical_asset_ids"] = len(ids)
    counts["canonical_mesh_paths"] = len(mesh_cache)
    conflicts = [{"asset_id": aid, "mesh_paths": sorted(paths)} for aid, paths in sorted(ids.items()) if len(paths) != 1]
    aliases = [{"mesh": path, "asset_ids": sorted(aids)} for path, aids in sorted(mesh_ids.items()) if len(aids) != 1]
    duplicates = [{"placement_id": sid, "count": n} for sid, n in sorted(seen_placements.items()) if n != 1]
    comparison = {key: {"observed": counts[key], "source_full_map": expected,
                        "count_matches": counts[key] == expected} for key, expected in SOURCE_COUNTS.items()}
    convex_values = [row["convex_count"] for row in mesh_cache.values()]
    total = sum(convex_values) if convex_values and all(v is not None for v in convex_values) else None
    mesh_problems = []
    for path, row in sorted(mesh_cache.items()):
        problems = []
        if row.get("source_count_match") is False:
            problems.append("known_source_convex_count_differs")
        if row["collision_trace_flag"] != "CTF_USE_SIMPLE_AND_COMPLEX":
            problems.append("collision_trace_flag_differs_or_unavailable")
        if row["subsystem_convex_count"] is not None and row["convex_count"] is not None and row["subsystem_convex_count"] != row["convex_count"]:
            problems.append("convex_readers_disagree")
        if any(row["shapes"][key] for key in SHAPE_FIELDS if key != "convex_elems"):
            problems.append("non_convex_shapes_present")
        if any(row["shapes"][key] is None for key in SHAPE_FIELDS):
            problems.append("shape_counts_unavailable")
        if problems:
            mesh_problems.append({"mesh": path, "issues": problems, "convex_count": row["convex_count"]})
    mismatch = any(not row["count_matches"] for row in comparison.values())
    needs_review = (mismatch or errors or conflicts or aliases or duplicates or mesh_problems
                    or unknown_component_count or total != SOURCE_CONVEX_TOTAL
                    or counts["actors_with_unreadable_tags"] or counts["prop_outside_placement"])
    return {"status": "REVIEW_REQUIRED" if needs_review else "COUNTS_AND_READABLE_SETTINGS_MATCH_REFERENCE",
            "scope": "Loaded actors in current editor world only; unloaded/partitioned actors are not inferred.",
            "counts": dict(counts), "source_count_comparison": comparison, "phase_counts": dict(phase_counts),
            "unreadable_component_actor_count": unknown_component_count,
            "placement_id_duplicates": _bounded(duplicates, limit), "canonical_id_conflicts": _bounded(conflicts, limit),
            "mesh_aliases": _bounded(aliases, limit),
            "collision_setting_histogram": [{"settings": dict(zip(("enabled", "profile", "object_type", "pawn", "visibility"), key)), "components": value}
                                            for key, value in sorted(signatures.items(), key=lambda item: str(item[0]))],
            "asset_collision": {"inspected_unique_referenced_meshes": len(mesh_cache),
                                "observed_convex_total": total, "source_canonical_ucx_reference": SOURCE_CONVEX_TOTAL,
                                "all_264_and_235_counts_match": len(mesh_cache) == 264 and total == SOURCE_CONVEX_TOTAL,
                                "provenance": "NOT_PROVEN: convex count does not prove UCX origin, geometric equivalence, or collision cooking.",
                                "exceptions": _bounded(mesh_problems, limit)},
            "exceptions": {"counts_by_code": dict(error_counts), "sample": errors, "omitted": sum(error_counts.values()) - len(errors)},
            "representatives": {key: {"status": "OBSERVED" if rows else "NOT_FOUND_IN_LOADED_PLACEMENTS",
                                       "selection": "Asset ID/mesh-name heuristic; maximum three actors.", "actors": rows}
                                for key, rows in reps.items()}}


def _pie(r, u, limit, inspect_premium_world):
    worlds = r.call(r.cls(u, "EditorLevelLibrary"), "get_pie_worlds", True)
    contract = {"status": "HISTORICAL_SOURCE_CONTRACT_UNVERIFIED_IN_CURRENT_BLUEPRINT",
                "shape": "single sphere", "channel": "Visibility (historical TraceTypeQuery1)",
                "trace_complex": True, "radius_cm": 100,
                "start_and_end": "ActorLocation + (0, 0, 10 cm)",
                "executed": False, "current_graph_read": False,
                "note": "No current graph literals or trace hit were read. These are historical source values."}
    if worlds is None:
        return {"status": "PIE_STATE_UNAVAILABLE", "worlds": None, "trace": contract}
    if not worlds:
        return {"status": "NOT_IN_PIE", "worlds": [], "trace": contract,
                "note": "No live pawn is assumed; no class default object or placed pawn substitutes for it."}
    rows = []
    for world in worlds[:limit]:
        path = r.path(world)
        row = {"world": path}
        # PIE package leaf has UEDPIE_n_; namespace still identifies premium worlds.
        if not inspect_premium_world or not _within(_package(path)):
            row["status"] = "SKIPPED_NON_PREMIUM_EDITOR_OR_PIE_WORLD"
            rows.append(row)
            continue
        pawn = r.call(r.cls(u, "GameplayStatics"), "get_player_pawn", world, 0)
        if pawn is None:
            row["status"] = "NO_PLAYER_INDEX_0_PAWN_OR_READ_UNAVAILABLE"
            rows.append(row)
            continue
        row.update(status="OBSERVED_PLAYER_INDEX_0", pawn=r.path(pawn),
                   pawn_class=r.path(r.call(pawn, "get_class")),
                   local_role=_token(r.call(pawn, "get_local_role")),
                   remote_role=_token(r.call(pawn, "get_remote_role")),
                   location_cm=_vector(r.call(pawn, "get_actor_location")))
        root = r.prop(pawn, "root_component")
        row["root_component"] = r.path(root)
        capsule = r.prop(pawn, "capsule_component")
        row["capsule"] = None if capsule is None else {
            "component": r.path(capsule), "is_root": capsule == root,
            "radius_cm": r.call(capsule, "get_scaled_capsule_radius"),
            "half_height_cm": r.call(capsule, "get_scaled_capsule_half_height"),
            "collision": _collision(r, u, capsule)}
        mesh_type = r.cls(u, "StaticMeshComponent")
        components = r.call(pawn, "get_components_by_class", mesh_type) if mesh_type else None
        meshes = []
        if components is not None:
            for comp in components[:limit]:
                name = r.call(comp, "get_name")
                meshes.append({"component": r.path(comp), "name": name,
                               "is_prop_mesh_name": str(name).lower() == "propmesh",
                               "actual_static_mesh": r.path(r.prop(comp, "static_mesh")),
                               "collision": _collision(r, u, comp)})
        row["static_mesh_components"] = None if components is None else _bounded(meshes, limit)
        row["note"] = "Actual loaded mesh is reported; no cone/can/disguise is assumed. Only player index 0 is sampled."
        rows.append(row)
    return {"status": "PIE_SNAPSHOT", "world_count": len(worlds), "worlds": rows,
            "omitted_worlds": max(0, len(worlds) - limit), "trace": contract,
            "note": "Not a replication, trace reachability, movement, collision cooking, or multiplayer test."}


def inspect(unreal_module=None, max_items=20, include_asset_registry=True):
    """Return a bounded JSON-serializable read-only report; never alter the project.

    unreal_module is an optional test seam. No local source package is required.
    max_items bounds output lists, not actor/mesh inspection. Default 20; 1..100.
    Missing APIs/properties are reported rather than converted to false passes.
    """
    if type(max_items) is not int or not 1 <= max_items <= 100:
        raise ValueError("max_items must be an integer from 1 to 100")
    if unreal_module is None:
        try:
            import unreal as unreal_module
        except ImportError:
            return {"schema": "premium-readonly-preflight574-v1", "status": "UNREAL_UNAVAILABLE",
                    "read_only": True, "action": "Run inspect() in the already-open Unreal Editor Python console."}
    u, r = unreal_module, _Read()
    before, dirty_before = _dirty(r, u, max_items)
    version = r.call(r.cls(u, "SystemLibrary"), "get_engine_version")
    version_match = bool(version and re.fullmatch(r"5\.7\.4(?:[-+][A-Za-z0-9_+./-]+)?", str(version)))
    editor = r.subsystem(u, "UnrealEditorSubsystem")
    world = r.call(editor, "get_editor_world")
    path = _package(r.path(world))
    premium = _within(path)
    map_status = ("UNAVAILABLE" if path is None else "EXPECTED_MAP" if path == EXPECTED_MAP else
                  "PREMIUM_VARIANT_REVIEW" if premium else "OPEN_PREMIUM_MAP_FIRST")
    report = {"schema": "premium-readonly-preflight574-v1", "read_only": True,
              "engine": {"observed": version, "expected": EXPECTED_VERSION,
                         "status": "MATCH" if version_match else "VERSION_UNAVAILABLE" if version is None else "WRONG_ENGINE_VERSION"},
              "current_map": {"package": path, "expected": EXPECTED_MAP, "status": map_status},
              "dirty_before": before,
              "asset_registry": _registry(r, u, max_items) if include_asset_registry else {"status": "NOT_REQUESTED"},
              "placements": _actors(r, u, world, path, max_items),
              "pie": _pie(r, u, max_items, premium)}
    after, dirty_after = _dirty(r, u, max_items)
    report["dirty_after"] = after
    report["dirty_snapshot_unchanged"] = (dirty_before == dirty_after if before["status"] != "UNAVAILABLE" and after["status"] != "UNAVAILABLE" else None)
    report["missing_data"] = [{"read": key, "occurrences": count} for key, count in sorted(r.missing.items())]
    actions = []
    if not version_match:
        actions.append("Use Unreal 5.7.4 for this handoff; this observation did not change or close the editor.")
    if before["status"] == "DIRTY_WORK_PRESENT":
        actions.append("Unsaved work exists. Decide yourself whether to save or discard it before any later map change; this tool does neither.")
    elif before["status"] == "UNAVAILABLE":
        actions.append("Dirty package status is unknown. Check unsaved work in the editor before any later map change.")
    if not premium:
        actions.append("After protecting current work, open the intended existing premium map yourself and run inspect() again. Carnival was not changed.")
    elif map_status == "PREMIUM_VARIANT_REVIEW":
        actions.append("Confirm this premium/UVRepair map is the intended map. Reference full-map counts may differ in other variants.")
    if report["placements"]["status"] == "REVIEW_REQUIRED":
        actions.append("Review placement/collision exceptions and missing data before treating the premium map as gameplay-ready.")
    if r.missing:
        actions.append("Unavailable reads are not passes; retain this JSON when checking API/plugin differences.")
    if report["dirty_snapshot_unchanged"] is False:
        actions.append("Dirty package sets changed during the snapshot. Background/editor activity may have changed state; inspect unsaved work.")
    if path is None:
        status = "CURRENT_WORLD_UNAVAILABLE"
    elif not premium:
        status = "OPEN_PREMIUM_MAP_FIRST"
    elif not version_match:
        status = "BLOCKED_ENGINE_VERSION"
    elif (r.missing or report["placements"]["status"] != "COUNTS_AND_READABLE_SETTINGS_MATCH_REFERENCE"
          or before["status"] != "CLEAN" or after["status"] != "CLEAN"
          or report["dirty_snapshot_unchanged"] is not True):
        status = "REVIEW_REQUIRED"
    else:
        status = "READ_ONLY_SNAPSHOT_COMPLETE_RUNTIME_UNVERIFIED"
    report.update(status=status, next_actions=actions,
                  limitations=["Only loaded editor actors and referenced meshes are inspected; no level/asset is loaded.",
                               "Counts/tags/settings do not certify source identity, visual parity, UCX geometry, cooked collision, PIE selection, multiplayer, or performance.",
                               "Blueprint graphs, project settings, carnival content, and historical trace behavior are not modified."])
    return report
