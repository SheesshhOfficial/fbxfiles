"""Evergreen Market editor import/reconstruction helper.

Python syntax and pure-data tests can run outside Unreal. UE execution has NOT
been tested in the delivery environment. API reference: UE Python 5.7.
No automatic execution on import. Call run(...), as described in the guide.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone

SCHEMA = "evergreen-import-report-v1"
COORDINATES = "UE_X_FORWARD_Y_RIGHT_Z_UP_CM"
ID_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _numbers(value, count, label, positive=False):
    _require(isinstance(value, (list, tuple)) and len(value) == count,
             f"{label}: expected {count} numbers")
    _require(all(isinstance(x, (int, float)) and not isinstance(x, bool)
                 and math.isfinite(x) for x in value), f"{label}: non-finite/non-numeric value")
    if positive:
        _require(all(x > 0 for x in value), f"{label}: all values must be positive")
    return value


def _id(value, label):
    _require(isinstance(value, str) and ID_PATTERN.fullmatch(value),
             f"{label}: use a nonempty, at most 128-character safe identifier")
    return value


def _path(root, relative, suffix=None):
    _require(isinstance(relative, str) and relative, "Missing relative file path")
    rel = Path(relative)
    _require(not rel.is_absolute(), f"Absolute source path rejected: {relative}")
    result = (root / rel).resolve()
    _require(root in result.parents, f"Source path escapes package: {relative}")
    _require(result.is_file(), f"Missing source file: {result}")
    if suffix:
        _require(result.suffix.lower() == suffix, f"Expected {suffix}: {result}")
    return result


def _asset_name(prefix, identifier):
    # Hash suffix avoids collisions after punctuation replacement or truncation.
    stem = re.sub(r"[^A-Za-z0-9_]", "_", identifier)[:80]
    return prefix + stem + "_" + hashlib.sha256(identifier.encode()).hexdigest()[:10]


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract(package_root):
    """Validate all references before any UE mutation. Returns plain Python data."""
    root = Path(package_root).expanduser().resolve()
    manifest_path = _path(root, "manifest.json", ".json")
    materials_path = _path(root, "materials.json", ".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    materials = json.loads(materials_path.read_text(encoding="utf-8"))
    _require(manifest.get("coordinate_system") == COORDINATES,
             f"Expected coordinate_system={COORDINATES}; do not guess axes")
    _require(manifest.get("rotation_order") == "pitch_yaw_roll", "Expected pitch_yaw_roll")
    settings = manifest.get("fbx_import", {})
    for key in ("convert_scene", "convert_scene_unit", "force_front_x_axis", "transform_vertex_to_absolute"):
        _require(type(settings.get(key)) is bool, f"fbx_import.{key} must be explicit")
    _require(settings.get("import_uniform_scale") == 1.0,
             "This contract requires import_uniform_scale=1.0; bake the export once")
    _require(isinstance(materials, dict), "materials.json must be an object")
    if "schema_version" in materials:
        _require(materials.get("schema_version") == 1 and isinstance(materials.get("materials"), list),
                 "Expected materials schema_version 1 and a material record list")
        records = materials["materials"]
        materials = {record["material_id"]: record for record in records}
        _require(len(materials) == len(records), "Duplicate material IDs")
    files = {manifest_path, materials_path}
    for mid, material in materials.items():
        _id(mid, "material ID")
        _numbers(material.get("base_color_rgba"), 4, f"{mid}.base_color_rgba")
        _require(all(0 <= x <= 1 for x in material["base_color_rgba"]), f"{mid}: color outside [0,1]")
        for field in ("roughness", "metallic"):
            value = material.get(field)
            _require(isinstance(value, (int, float)) and not isinstance(value, bool)
                     and math.isfinite(value) and 0 <= value <= 1, f"{mid}.{field}: expected [0,1]")
        mode = material.get("alpha_mode", "OPAQUE")
        _require(mode in ("OPAQUE", "MASK", "BLEND"), f"{mid}: unrecognized alpha_mode")
        if "base_color_texture" in material:
            files.add(_path(root, material["base_color_texture"], ".png"))
        if "emissive_rgb" in material:
            _numbers(material["emissive_rgb"], 3, f"{mid}.emissive_rgb")
            _require(all(x >= 0 for x in material["emissive_rgb"]), f"{mid}: negative emission")
        if "opacity" in material:
            _require(isinstance(material["opacity"], (int, float)) and math.isfinite(material["opacity"])
                     and 0 <= material["opacity"] <= 1, f"{mid}: opacity outside [0,1]")
        if "opacity_mask_clip" in material:
            _require(0 <= material["opacity_mask_clip"] <= 1, f"{mid}: opacity mask clip outside [0,1]")
    assets = manifest.get("assets")
    placements = manifest.get("placements")
    _require(isinstance(assets, list) and assets, "Manifest has no asset records")
    _require(isinstance(placements, list) and placements, "Manifest has no placement records")
    by_id = {}
    for asset in assets:
        aid = _id(asset.get("asset_id"), "asset_id")
        _require(aid not in by_id, f"Duplicate asset_id: {aid}")
        _require(asset.get("default_pivot") == "bottom_center", f"{aid}: expected bottom_center pivot")
        size = _numbers(asset.get("bounds_cm"), 3, f"{aid}.bounds_cm")
        _require(all(x >= 0 for x in size) and sum(x > 0 for x in size) >= 2,
                 f"{aid}: bounds must describe at least a surface")
        _require(isinstance(asset.get("materials"), list) and asset["materials"], f"{aid}: missing material slots")
        _require(all(x in materials for x in asset["materials"]), f"{aid}: unknown material ID")
        used_materials = asset.get("used_materials", asset["materials"])
        _require(isinstance(used_materials, list) and used_materials
                 and set(used_materials).issubset(asset["materials"]), f"{aid}: invalid used_materials")
        _require(isinstance(asset.get("category"), str), f"{aid}: missing category")
        _require(isinstance(asset.get("disguise_tier"), str), f"{aid}: missing disguise_tier")
        _require(asset.get("collision", {}).get("strategy") in ("box", "none"),
                 f"{aid}: expected explicit box/none collision strategy")
        files.add(_path(root, asset["fbx_path"], ".fbx"))
        by_id[aid] = asset
    seen = set()
    for p in placements:
        iid = _id(p.get("instance_id"), "instance_id")
        _require(iid not in seen, f"Duplicate instance_id: {iid}")
        seen.add(iid)
        _require(p.get("asset_id") in by_id, f"{iid}: unknown asset")
        _numbers(p.get("location_cm"), 3, f"{iid}.location_cm")
        _numbers(p.get("rotation_deg"), 3, f"{iid}.rotation_deg")
        if "quaternion_xyzw" in p:
            q = _numbers(p["quaternion_xyzw"], 4, f"{iid}.quaternion_xyzw")
            _require(abs(sum(x*x for x in q) - 1.0) < 0.0001, f"{iid}: quaternion is not normalized")
        _numbers(p.get("scale"), 3, f"{iid}.scale", positive=True)
    # Detect changes to binaries/textures as well as manifest metadata between phases.
    file_hashes = {str(p.relative_to(root)).replace("\\", "/"): _sha(p) for p in sorted(files)}
    fingerprint = hashlib.sha256(json.dumps(file_hashes, sort_keys=True).encode()).hexdigest()
    return {"root": root, "manifest": manifest, "materials": materials, "assets": by_id,
            "placements": placements, "fingerprint": fingerprint, "file_hashes": file_hashes}


def select_sample(contract):
    """Select across categories, texture usage, aspect ratio and rotated placements."""
    assets = contract["assets"]
    selected = set()
    for category in sorted({a["category"] for a in assets.values()}):
        candidates = [a for a in assets.values() if a["category"] == category]
        selected.add(sorted(candidates, key=lambda a: a["asset_id"])[0]["asset_id"])
    textured = [a for a in assets.values() if any("base_color_texture" in contract["materials"][m]
                                                  for m in a["materials"])]
    if textured:
        selected.add(sorted(textured, key=lambda a: a["asset_id"])[0]["asset_id"])
    selected.add(max(assets.values(), key=lambda a: max(a["bounds_cm"]) / max(min(a["bounds_cm"]), 0.001))["asset_id"])
    for word in ("shippingcarton", "cart", "chair", "sales_floor", "powder_coated_shelf"):
        candidates = [a for a in assets.values() if word in a.get("name", a["asset_id"]).lower().replace(" ", "_")
                      and (word != "cart" or "carton" not in a.get("name", a["asset_id"]).lower())]
        if candidates:
            selected.add(sorted(candidates, key=lambda a: a["asset_id"])[0]["asset_id"])
    # Bottle/can imports exercise rounded normals and unused material slots.
    for shape in ("bottle", "can"):
        candidates = [a for a in assets.values() if "sku" in a.get("name", "").lower()
                      and shape in a.get("name", "").lower()]
        if candidates:
            selected.add(sorted(candidates, key=lambda a: a["asset_id"])[0]["asset_id"])
    transparent = [a for a in assets.values() if any(contract["materials"][m].get("alpha_mode", "OPAQUE") != "OPAQUE"
                                                    for m in a["materials"])]
    if transparent:
        selected.add(sorted(transparent, key=lambda a: a["asset_id"])[0]["asset_id"])
    for p in contract["placements"]:
        if any(abs(x) > 0.01 for x in p["rotation_deg"]):
            selected.add(p["asset_id"])
            break
    return sorted(selected)


def make_plan(contract, phase="sample", sample_asset_ids=None, sector_size_cm=2000.0):
    _require(phase in ("sample", "full"), "phase must be sample or full")
    _require(isinstance(sector_size_cm, (int, float)) and math.isfinite(sector_size_cm)
             and sector_size_cm > 0, "sector_size_cm must be positive")
    selected = (sorted(contract["assets"]) if phase == "full" else
                (sorted(set(sample_asset_ids)) if sample_asset_ids else select_sample(contract)))
    _require(selected and all(a in contract["assets"] for a in selected), "Unknown/empty sample asset selection")
    groups = defaultdict(list)
    chosen = []
    by_asset = defaultdict(list)
    for p in contract["placements"]:
        if p["asset_id"] in selected:
            by_asset[p["asset_id"]].append(p)
    for aid in selected:
        rows = sorted(by_asset[aid], key=lambda p: p["instance_id"])
        if phase == "sample":
            # First placement plus distinct rotations/scales; at most three per asset.
            representatives = {}
            for p in rows:
                representatives.setdefault(tuple(p["rotation_deg"] + p["scale"]), p)
            rows = list(representatives.values())[:3]
        chosen.extend(rows)
    for p in chosen:
        x, y, _ = p["location_cm"]
        sector = (math.floor(x / sector_size_cm), math.floor(y / sector_size_cm))
        group = f"{p['asset_id']}__sector_{sector[0]}_{sector[1]}"
        groups[group].append(p)
    return {"phase": phase, "selected_asset_ids": selected, "groups": dict(sorted(groups.items())),
            "asset_count": len(selected), "placement_count": len(chosen),
            "ism_actor_count": len(groups), "sector_size_cm": sector_size_cm,
            "package_fingerprint": contract["fingerprint"]}


def _save_asset(u, asset):
    _require(u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False),
             f"Unable to save generated asset {asset.get_path_name()}")


def _import_file(u, source, folder, name, asset_class, options=None, factory=None):
    task = u.AssetImportTask()
    for key, value in {"filename": str(source), "destination_path": folder,
                       "destination_name": name, "automated": True, "async_": False,
                       "replace_existing": False, "replace_existing_settings": False,
                       "save": False}.items():
        task.set_editor_property(key, value)
    if options:
        task.set_editor_property("options", options)
    if factory:
        task.set_editor_property("factory", factory)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = [obj for obj in task.get_objects() if isinstance(obj, asset_class)]
    _require(len(objects) == 1, f"Expected one {asset_class.__name__} from {source}; got {len(objects)}")
    asset = objects[0]
    # Interchange may ignore destination_name. Never silently map the wrong result.
    _require(asset.get_path_name().startswith(folder + "/"), "Import produced an unexpected destination")
    return asset


def _fbx_options(u, contract):
    options = u.FbxImportUI()
    for key, value in {"import_mesh": True, "import_as_skeletal": False,
                       "import_animations": False, "import_materials": False,
                       "import_textures": False, "automated_import_should_detect_type": False,
                       "mesh_type_to_import": u.FBXImportType.FBXIT_STATIC_MESH}.items():
        options.set_editor_property(key, value)
    mesh_options = options.get_editor_property("static_mesh_import_data")
    fields = {key: contract["manifest"]["fbx_import"][key] for key in
              ("convert_scene", "convert_scene_unit", "force_front_x_axis",
               "transform_vertex_to_absolute", "import_uniform_scale")}
    fields.update({"combine_meshes": False, "auto_generate_collision": False,
                   "generate_lightmap_u_vs": True,
                   "bake_pivot_in_vertex": False, "reorder_material_to_fbx_order": True,
                   "import_translation": u.Vector(0, 0, 0),
                   "import_rotation": u.Rotator(pitch=0, yaw=0, roll=0),
                   "normal_import_method": u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS})
    for key, value in fields.items():
        # Unknown properties fail clearly rather than silently changing transforms.
        mesh_options.set_editor_property(key, value)
    return options


def _build_material(u, material_id, data, folder, textures):
    name = _asset_name("M_", material_id)
    mat = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    _require(mat is not None, f"Unable to create material {name}")
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    lib = u.MaterialEditingLibrary

    def node(cls, y=0):
        result = lib.create_material_expression(mat, cls, -400, y)
        _require(result is not None, f"Unable to add material node to {name}")
        return result

    def connect(expression, output, prop):
        _require(lib.connect_material_property(expression, output, prop), f"Material connection failed: {name}")

    def scalar(value, prop, y):
        expr = node(u.MaterialExpressionConstant, y)
        expr.set_editor_property("r", float(value))
        connect(expr, "", prop)

    color = data["base_color_rgba"]
    texture_node = None
    if data.get("base_color_texture"):
        texture_node = node(u.MaterialExpressionTextureSample)
        texture_node.set_editor_property("texture", textures[data["base_color_texture"]])
        connect(texture_node, "RGB", u.MaterialProperty.MP_BASE_COLOR)
    else:
        color_node = node(u.MaterialExpressionConstant3Vector)
        color_node.set_editor_property("constant", u.LinearColor(*color))
        connect(color_node, "", u.MaterialProperty.MP_BASE_COLOR)
    scalar(data["roughness"], u.MaterialProperty.MP_ROUGHNESS, 160)
    scalar(data["metallic"], u.MaterialProperty.MP_METALLIC, 240)
    mode = data.get("alpha_mode", "OPAQUE")
    if mode != "OPAQUE":
        mat.set_editor_property("blend_mode", u.BlendMode.BLEND_MASKED if mode == "MASK" else u.BlendMode.BLEND_TRANSLUCENT)
        prop = u.MaterialProperty.MP_OPACITY_MASK if mode == "MASK" else u.MaterialProperty.MP_OPACITY
        if "opacity" in data:
            scalar(data["opacity"], prop, 320)
        elif texture_node:
            connect(texture_node, "A", prop)
        else:
            scalar(color[3], prop, 320)
        if mode == "MASK":
            mat.set_editor_property("opacity_mask_clip_value", float(data.get("opacity_mask_clip", 0.333)))
    mat.set_editor_property("two_sided", bool(data.get("two_sided", False)))
    if data.get("emissive_rgb"):
        emission = node(u.MaterialExpressionConstant3Vector, 400)
        emission.set_editor_property("constant", u.LinearColor(*data["emissive_rgb"], 1.0))
        connect(emission, "", u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.layout_material_expressions(mat)
    lib.recompile_material(mat)
    _save_asset(u, mat)
    return mat


def _mesh_check(mesh, asset, tolerance_cm=0.5):
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    origin = bounds.origin
    actual = [2.0 * extent.x, 2.0 * extent.y, 2.0 * extent.z]
    expected = asset["bounds_cm"]
    for got, want in zip(actual, expected):
        _require(abs(got - want) <= max(tolerance_cm, 0.01 * want),
                 f"{asset['asset_id']}: bounds mismatch {actual} vs expected {expected}; check unit/axis conversion")
    _require(abs(origin.x) <= tolerance_cm and abs(origin.y) <= tolerance_cm
             and abs(origin.z - extent.z) <= tolerance_cm,
             f"{asset['asset_id']}: imported pivot is not bottom center")
    _require(mesh.get_num_triangles(0) > 0, f"{asset['asset_id']}: mesh has no triangles")
    return {"actual_bounds_cm": actual, "expected_bounds_cm": expected,
            "triangles_lod0": mesh.get_num_triangles(0), "pivot_checked": True}


def _validate_material_slots(asset, imported_names):
    declared = set(asset["materials"])
    used = set(asset.get("used_materials", asset["materials"]))
    imported = set(imported_names)
    _require(len(imported) == len(imported_names), f"{asset['asset_id']}: duplicate imported slot names")
    _require(used.issubset(imported) and imported.issubset(declared),
             f"{asset['asset_id']}: missing used material or unknown imported slot; refusing wrong material assignment")


def _transform(u, placement):
    pitch, yaw, roll = placement["rotation_deg"]
    rotation = (u.Quat(*placement["quaternion_xyzw"]).rotator() if "quaternion_xyzw" in placement
                else u.Rotator(pitch=pitch, yaw=yaw, roll=roll))
    return u.Transform(location=u.Vector(*placement["location_cm"]),
                       rotation=rotation,
                       scale=u.Vector(*placement["scale"]))


def _new_ism(u, actor_system, group_key, mesh, asset):
    actor = actor_system.spawn_actor_from_class(u.Actor, u.Vector(0, 0, 0), transient=False)
    _require(actor is not None, f"Unable to spawn {group_key}")
    actor.set_actor_label(_asset_name("EM_", group_key))
    actor.set_editor_property("tags", ["EvergreenGenerated", "EMGroup=" + group_key])
    subsystem = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    library = u.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_instance(actor)
    parent = next((h for h in handles if library.is_actor(library.get_data(h))), None)
    _require(parent is not None, f"No actor subobject handle for {group_key}")
    handle, reason = subsystem.add_new_subobject(u.AddNewSubobjectParams(
        parent_handle=parent, new_class=u.InstancedStaticMeshComponent))
    _require(library.is_handle_valid(handle), f"ISM creation failed: {reason}")
    component = library.get_associated_object(library.get_data(handle))
    _require(isinstance(component, u.InstancedStaticMeshComponent), "Subobject is not an ISM")
    if not actor.get_editor_property("root_component"):
        actor.set_editor_property("root_component", component)
    component.set_mobility(u.ComponentMobility.STATIC)
    _require(component.set_static_mesh(mesh), f"Unable to set mesh for {group_key}")
    component.set_editor_property("component_tags", ["EvergreenGenerated", "EMGroup=" + group_key,
        "EMAsset=" + asset["asset_id"], "EMDisguiseTier=" + asset["disguise_tier"]])
    # Deliberately a visual/query staging map. Walking/physics collision must be
    # reviewed by category; default broad hulls on fixtures can block shelf props.
    component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION if asset["collision"]["strategy"] == "none"
                                    else u.CollisionEnabled.QUERY_ONLY)
    component.set_collision_response_to_all_channels(u.CollisionResponseType.IGNORE)
    component.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY, u.CollisionResponseType.BLOCK)
    component.set_editor_property("generate_overlap_events", False)
    component.set_editor_property("can_ever_affect_navigation", False)
    return actor, component


def verify_scene(u, report):
    """Verify current loaded generated map; does not load/save or change assets."""
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    groups = {}
    for actor in actors:
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            for tag in comp.get_editor_property("component_tags"):
                if str(tag).startswith("EMGroup="):
                    key = str(tag).split("=", 1)[1]
                    _require(key not in groups, f"Duplicate generated group {key}")
                    groups[key] = comp
    _require(set(groups) == set(report["groups"]), "Saved/reloaded ISM group set changed")
    for key, record in report["groups"].items():
        comp = groups[key]
        _require(comp.get_instance_count() == len(record["instances"]), f"Instance count changed: {key}")
        _require(comp.get_editor_property("static_mesh").get_path_name() == record["mesh_path"], f"Wrong mesh: {key}")
        for row in record["instances"]:
            actual = comp.get_instance_transform(row["instance_index"], world_space=True)
            _require(actual is not None and actual.is_near_equal(_transform(u, row),
                     location_tolerance=0.1, rotation_tolerance=0.001, scale3d_tolerance=0.0001),
                     f"Transform changed: {row['instance_id']}")
    return {"group_count": len(groups), "placement_count": sum(c.get_instance_count() for c in groups.values()),
            "world_transforms_checked": True}


def _write_report(path, report):
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def run(package_root, *, execute=False, phase="sample", sample_asset_ids=None,
        content_root=None, sector_size_cm=2000.0, preflight_report=None,
        visual_review_approved=False):
    """Dry-run by default. Full execution requires a successful reviewed sample report.

    execute=True imports NEW content and saves/loads a NEW staging level.
    Existing content is never overwritten or deleted. A partial failed run remains
    in its own folder for inspection; choose a new folder to retry.
    """
    contract = load_contract(package_root)
    plan = make_plan(contract, phase, sample_asset_ids, sector_size_cm)
    summary = {key: value for key, value in plan.items() if key != "groups"}
    if not execute:
        print(json.dumps(summary, indent=2))
        return summary
    if phase == "full":
        _require(preflight_report is not None and visual_review_approved is True,
                 "Inspect a sample import first; supply its report and visual_review_approved=True")
        prior = json.loads(Path(preflight_report).read_text(encoding="utf-8"))
        _require(prior.get("schema") == SCHEMA and prior.get("phase") == "sample"
                 and prior.get("status") == "verified_persistence", "Sample report is not successful")
        _require(set(select_sample(contract)).issubset(prior.get("selected_asset_ids", [])),
                 "Sample did not cover the required representative set; run default sample phase")
        _require(prior.get("package_fingerprint") == contract["fingerprint"],
                 "Package changed since sample import; run the sample phase again")
    import unreal as u  # Import only when actually executing inside the UE editor.
    level_system = u.get_editor_subsystem(u.LevelEditorSubsystem)
    _require(not level_system.is_in_play_in_editor(), "Stop PIE before importing")
    _require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
             "Save or discard your unsaved map changes yourself before importing")
    # Also protect unsaved assets from indirect map transitions and keep the run isolated.
    _require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
             "Save or discard your unsaved content changes yourself before importing")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    root = content_root or "/Game/EvergreenHandoff/" + phase.capitalize() + "_" + stamp
    _require(re.fullmatch(r"/Game/[A-Za-z0-9_/]+", root) and not root.endswith("/"), "Use a safe new /Game/... content root")
    _require(not u.EditorAssetLibrary.does_directory_exist(root)
             and not u.EditorAssetLibrary.does_asset_exist(root), f"Destination already exists: {root}")
    for name in ("SubobjectDataSubsystem", "SubobjectDataBlueprintFunctionLibrary"):
        _require(hasattr(u, name), f"Required editor API {name} unavailable; see guide/version requirements")
    for owner, method in ((u.SubobjectDataBlueprintFunctionLibrary, "get_associated_object"),
                          (u.SubobjectDataSubsystem, "add_new_subobject"),
                          (u.InstancedStaticMeshComponent, "add_instances"),
                          (u.StaticMeshEditorSubsystem, "get_simple_collision_count")):
        _require(hasattr(owner, method), f"Required editor API {owner.__name__}.{method} unavailable; use UE 5.7 or adapt explicitly")
    _require(not u.SystemLibrary.get_console_variable_bool_value("Interchange.FeatureFlags.Import.FBX"),
             "Legacy FBX options required: set Interchange.FeatureFlags.Import.FBX 0 in the editor console, then retry")
    report_folder = Path(u.Paths.project_saved_dir()).resolve() / "EvergreenHandoff" / stamp
    report_folder.mkdir(parents=True, exist_ok=False)
    report_path = report_folder / "import_report.json"
    report = dict(summary, schema=SCHEMA, status="started", engine_version=u.SystemLibrary.get_engine_version(),
                  content_root=root, map_path=root + "/Maps/L_Evergreen_" + phase,
                  material_fidelity="PBR approximation; procedural Blender nodes not transferred",
                  gameplay_implemented=False, groups={}, meshes={}, material_paths={})
    _write_report(report_path, report)
    try:
        u.EditorAssetLibrary.make_directory(root)
        used_materials = sorted({mid for aid in plan["selected_asset_ids"] for mid in contract["assets"][aid]["materials"]})
        textures = {}
        for mid in used_materials:
            data = contract["materials"][mid]
            relative = data.get("base_color_texture")
            if relative and relative not in textures:
                texture = _import_file(u, _path(contract["root"], relative), root + "/Textures",
                                       _asset_name("T_", relative), u.Texture2D)
                texture.set_editor_property("srgb", True)
                _save_asset(u, texture)
                textures[relative] = texture
        material_assets = {}
        for mid in used_materials:
            mat = _build_material(u, mid, contract["materials"][mid], root + "/Materials", textures)
            material_assets[mid] = mat
            report["material_paths"][mid] = mat.get_path_name()
        meshes = {}
        for aid in plan["selected_asset_ids"]:
            asset = contract["assets"][aid]
            mesh = _import_file(u, _path(contract["root"], asset["fbx_path"]), root + "/Meshes",
                                _asset_name("SM_", aid), u.StaticMesh, _fbx_options(u, contract))
            mesh_check = _mesh_check(mesh, asset)
            collision_count = u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_simple_collision_count(mesh)
            _require(collision_count >= 0, f"{aid}: simple collision query failed")
            _require((collision_count > 0) == (asset["collision"]["strategy"] == "box"),
                     f"{aid}: imported simple collision does not match explicit box/none strategy")
            mesh_check["simple_collision_count"] = collision_count
            slots = mesh.get_editor_property("static_materials")
            imported_names = [str(s.get_editor_property("material_slot_name")) for s in slots]
            _validate_material_slots(asset, imported_names)
            for index, mid in enumerate(imported_names):
                mesh.set_material(index, material_assets[mid])
            mesh_check["material_slot_names"] = [str(s.get_editor_property("material_slot_name")) for s in slots]
            mesh_check["path"] = mesh.get_path_name()
            report["meshes"][aid] = mesh_check
            _save_asset(u, mesh)
            meshes[aid] = mesh
            _write_report(report_path, report)
        _require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Current map became dirty; stop before map change")
        _require(level_system.new_level(report["map_path"], is_partitioned_world=False), "Could not create new staging map")
        actor_system = u.get_editor_subsystem(u.EditorActorSubsystem)
        for key, placements in plan["groups"].items():
            aid = placements[0]["asset_id"]
            actor, component = _new_ism(u, actor_system, key, meshes[aid], contract["assets"][aid])
            indices = component.add_instances([_transform(u, p) for p in placements],
                                              should_return_indices=True, world_space=True, update_navigation=False)
            _require(len(indices) == len(placements), f"Incomplete instances in {key}")
            rows = [dict(p, instance_index=int(index)) for p, index in zip(placements, indices)]
            report["groups"][key] = {"asset_id": aid, "mesh_path": meshes[aid].get_path_name(),
                                     "actor_label": actor.get_actor_label(), "instances": rows}
        report["before_save"] = verify_scene(u, report)
        _require(level_system.save_current_level(), "Could not save generated map")
        _require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Map remains dirty after saving; reload aborted")
        _require(level_system.load_level(report["map_path"]), "Could not reload generated map for persistence check")
        report["after_reload"] = verify_scene(u, report)
        lookup = report_folder / "instance_lookup.csv"
        with lookup.open("w", encoding="utf-8", newline="") as stream:
            fields = ["Name", "ComponentKey", "InstanceIndex", "StableInstanceId", "AssetId", "LocationX", "LocationY", "LocationZ"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for key, group in report["groups"].items():
                for p in group["instances"]:
                    x, y, z = p["location_cm"]
                    writer.writerow(dict(Name=p["instance_id"], ComponentKey=key, InstanceIndex=p["instance_index"],
                        StableInstanceId=p["instance_id"], AssetId=p["asset_id"], LocationX=x, LocationY=y, LocationZ=z))
        report["lookup_csv"] = str(lookup)
        report["status"] = "verified_persistence"
        report["remaining_checks"] = ["material/label visual fidelity", "asymmetric orientation/handedness",
            "gameplay collision and per-prop traces", "target-platform profiling", "multiplayer integration"]
        _write_report(report_path, report)
        u.log("Evergreen import persisted and transform-checked. Manual checks remain. Report: " + str(report_path))
        return str(report_path)
    except Exception as exc:
        report["status"] = "failed_partial_run"
        report["error"] = str(exc)
        _write_report(report_path, report)
        u.log_error("Evergreen import stopped safely; partial generated content remains at " + root + "; report: " + str(report_path))
        raise


if __name__ == "__main__":
    # Executing from the editor menu never mutates anything automatically.
    print("Loaded Evergreen helper. Read docs/UNREAL_IMPORT_AND_PROP_HUNT.md, then call run(...).")
