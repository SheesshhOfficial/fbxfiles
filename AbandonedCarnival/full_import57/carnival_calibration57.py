"""Fail-closed, geometry-only UE 5.7.4 calibration. Importing this module does nothing.

preflight(root) only reads. import_sample(root) is the sole explicit mutating entry.
There is no full import, save, overwrite, delete, cleanup, material builder, or bpy.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
from pathlib import Path, PurePosixPath
import re

SCHEMA = "carnival-calibration57-v1"
DESTINATION = "/Game/AbandonedCarnivalCalibration57"
MESH_FOLDER = DESTINATION + "/Props"
SUGGESTED_MAP_PATH = DESTINATION + "/Maps/Calibration57"
SOURCE_SHA256 = "2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a"
SOURCE_BYTES = 136393382
PINNED_FILES = {
    "FILE_MANIFEST.json": "a4257f232c1c2f5cb334a823095b25893ac608bf639456b924d4bf81a29d16eb",
    "export/unreal/prop_placements.json": "715847bfceb05802d9157311b68ab862949ee4a96017925c2efda45de7214523",
    "blender/source_parts.json": "07a257a4d5926df70ec69000a96797150475ece10e6694fd28bd9c38604199a2",
    "qa/Frozen_Source.json": "67df90c11217baddc95241052f764ec5e29052e46dd30d553b8cffabed0b742b",
    "export/qa/prop_fidelity.json": "e987801cf1f05a290328ed478f377e66bc9d7bebecaf5bc4ba81273a8e0c5f01",
}
SAMPLES = (
    ("SM_BumperCar_566477cf32", 8, "c2cec0066bb3639fb79f1f90ed42ca056844e838d7e1365cda5779041a86531e"),
    ("SM_wooden_pallet_244700516e", 9, "3a75274214328a035f8d708dc32f875bf35711f483b9853698dbc24857e10644"),
    ("SM_OpenMaintenanceBucket_aeb36301a9", 1, "2281d9973d1e01f32e9794d9d45b733674aa34c369c0d4a9ed74b44edfd58306"),
)
OTHER_SHAPES = ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems",
                "level_set_elems", "ml_level_set_elems", "skinned_level_set_elems",
                "skinned_triangle_mesh_elems")
FBX_FIELDS = dict(convert_scene=False, convert_scene_unit=False, force_front_x_axis=False,
                  import_uniform_scale=1.0, transform_vertex_to_absolute=True,
                  bake_pivot_in_vertex=False, combine_meshes=False, auto_generate_collision=False,
                  one_convex_hull_per_ucx=True, generate_lightmap_u_vs=False,
                  reorder_material_to_fbx_order=True, remove_degenerates=False,
                  build_nanite=False, import_mesh_lods=False, compute_weighted_normals=False)
BUILD_FIELDS = dict(recompute_normals=False, recompute_tangents=True, use_mikk_t_space=True,
                    generate_lightmap_u_vs=False, use_full_precision_u_vs=True,
                    remove_degenerates=False)
LIMITATIONS = [
    "Geometry/collision calibration only; materials, textures and shading are NOT validated.",
    "Source normals are imported; these FBXs have no explicit tangent payload. MikkTSpace tangents are generated.",
    "No floor, lighting, player start, gameplay, traces, multiplayer or full-scene import.",
    "No save or cleanup is performed. Imported assets and the fresh map remain unsaved.",
    "An importer failure may leave partial assets/actors. Inspect them manually; do not rerun over them.",
    "Bounds and UV-channel checks do not prove visual fidelity or collision clearance.",
]


class CalibrationError(RuntimeError):
    """Carries a JSON-serializable report, including any partial mutation."""
    def __init__(self, report):
        self.report = report
        super().__init__(json.dumps(report, indent=2, allow_nan=False))


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _safe_file(root, relative):
    _require(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative,
             "Invalid package-relative file path")
    rel = PurePosixPath(relative)
    _require(not rel.is_absolute() and ".." not in rel.parts, "Unsafe package path: " + relative)
    path = (root / relative).resolve()
    _require(root in path.parents and path.is_file(), "Missing or outside-package file: " + relative)
    return path


def _pinned_json_sha(path, expected):
    # Git autocrlf may change only text line endings on Windows. Binary checks never normalize.
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    normalized = actual != expected and hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == expected
    _require(actual == expected or normalized, "Pinned file SHA256 mismatch: " + path.name)
    return actual, normalized


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _vector(value):
    _require(isinstance(value, (list, tuple)) and len(value) == 3 and
             all(type(x) in (int, float) and math.isfinite(x) for x in value), "Invalid finite 3-vector")
    return list(value)


def _contract(package_root):
    root = Path(package_root).expanduser().resolve()
    verified = {}
    normalized_json_files = []
    docs = {}
    for relative, expected in PINNED_FILES.items():
        path = _safe_file(root, relative)
        actual, normalized = _pinned_json_sha(path, expected)
        if normalized:
            normalized_json_files.append(relative)
        verified[relative] = actual
        docs[relative] = _read(path)
    manifest = docs["export/unreal/prop_placements.json"]
    parts = docs["blender/source_parts.json"]
    inventory = docs["FILE_MANIFEST.json"]
    frozen = docs["qa/Frozen_Source.json"]
    fidelity = docs["export/qa/prop_fidelity.json"]
    _require(manifest.get("schema_version") == 2, "Unsupported prop manifest schema")
    _require(manifest.get("source_blend_sha256") == parts.get("sha256") == inventory.get("source_sha256")
             == frozen.get("sha256") == fidelity.get("source_blend_sha256") == SOURCE_SHA256,
             "Frozen source hash lineage mismatch")
    # Hash the entire source stream without extracting/assembling/writing the .blend.
    whole = hashlib.sha256()
    total = 0
    seen = set()
    for part in parts["parts"]:
        relative = part["path"]
        _require(relative not in seen, "Duplicate source part")
        seen.add(relative)
        path = _safe_file(root, relative)
        digest = hashlib.sha256()
        count = 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                count += len(block)
                total += len(block)
                digest.update(block)
                whole.update(block)
        _require(count == part["bytes"] and digest.hexdigest() == part["sha256"],
                 "Source part hash/size mismatch: " + relative)
        verified[relative] = digest.hexdigest()
    _require(total == parts["bytes"] == frozen["bytes"] == SOURCE_BYTES and whole.hexdigest() == SOURCE_SHA256,
             "Complete source SHA256/size mismatch")
    assets = {}
    for item in manifest["assets"]:
        _require(item["asset_name"] not in assets, "Duplicate canonical mesh name")
        assets[item["asset_name"]] = item
    fidelity_rows = {item["asset"]: item for item in fidelity["assets"]}
    file_rows = {item["path"]: item for item in inventory["files"]}
    selected = []
    for name, hulls, digest in SAMPLES:
        _require(name in assets, "Required sample missing: " + name)
        item = assets[name]
        relative = "export/unreal/props/" + name + ".fbx"
        _require(item["fbx"] == "props/" + name + ".fbx" and item["fbx_sha256"] == digest,
                 "Canonical sample path/hash mismatch: " + name)
        path = _safe_file(root, relative)
        _require(_sha(path) == digest, "Whole sample FBX SHA256 mismatch: " + name)
        _require(file_rows[relative]["sha256"] == digest and file_rows[relative]["bytes"] == path.stat().st_size,
                 "File inventory mismatch: " + name)
        verified[relative] = digest
        _require(item["collision_hulls"] == hulls, "Sample hull contract mismatch: " + name)
        lo, hi = [_vector(item["bounds_cm"][key]) for key in ("min", "max")]
        _require(all(hi[i] > lo[i] for i in range(3)), "Invalid source bounds")
        evidence = fidelity_rows[name]
        _require(evidence["passed"] is True and evidence["uv_layer_count"] == 1,
                 "Sample source fidelity evidence failed: " + name)
        placements = [p for p in manifest["placements"] if p["asset_name"] == name]
        _require(placements and all(p["actor_class"] == "StaticMeshActor" and "PropActor" in p["actor_tags"]
                                   for p in placements), "Sample actor/tag contract missing: " + name)
        selected.append(dict(item, source_path=str(path), source_tags=list(placements[0]["actor_tags"]),
                             expected_uv_channels=1))
    return dict(root=str(root), selected=selected, verified_files=verified,
                source_sha256=whole.hexdigest(), source_bytes=total, normalized_json_files=normalized_json_files)


def _base_report(mode):
    return dict(schema=SCHEMA, mode=mode, status="PENDING", ready_to_import=False,
                destination=DESTINATION, suggested_manual_save_path=SUGGESTED_MAP_PATH,
                material_validation="NOT_RUN", gameplay_validation="NOT_RUN", saves_performed=0,
                mutation_started=False, partial_import=False, imported_objects=[], spawned_actors=[],
                limitations=list(LIMITATIONS))


def _enum(u, kind, name):
    obj = getattr(u, kind, None)
    _require(obj is not None and hasattr(obj, name), "Missing Unreal enum: " + kind + "." + name)
    return getattr(obj, name)


def _guard_api(u):
    required = {
        "SystemLibrary": ("get_engine_version",),
        "Paths": ("project_content_dir", "convert_relative_path_to_full"),
        "EditorLoadingAndSavingUtils": ("get_dirty_map_packages", "get_dirty_content_packages", "new_blank_map"),
        "EditorAssetLibrary": ("does_directory_exist", "does_asset_exist", "list_assets"),
        "AssetImportTask": ("get_objects", "get_editor_property", "set_editor_property"),
        "AssetToolsHelpers": ("get_asset_tools",),
        "EditorActorSubsystem": ("get_all_level_actors", "spawn_actor_from_class"),
        "UnrealEditorSubsystem": ("get_editor_world", "get_game_world"),
        "StaticMeshEditorSubsystem": ("get_num_uv_channels", "get_simple_collision_count",
            "get_convex_collision_count", "get_lod_build_settings", "set_lod_build_settings"),
        "StaticMesh": ("get_bounds", "set_material", "get_material"),
        "StaticMeshActor": ("set_actor_label", "set_actor_scale3d", "get_actor_location", "get_actor_scale3d"),
        "StaticMeshComponent": ("set_static_mesh", "set_simulate_physics"),
        "FbxStaticMeshImportData": ("extract_filenames",),
        "FbxFactory": (), "FbxImportUI": (), "BodySetup": (), "World": (), "Name": (),
        "MaterialInterface": (), "Vector": (), "Rotator": (),
    }
    for cls, methods in required.items():
        target = getattr(u, cls, None)
        _require(target is not None, "Missing Unreal API class: " + cls)
        for method in methods:
            _require(callable(getattr(target, method, None)), "Missing Unreal API: " + cls + "." + method)
    for name in ("get_editor_subsystem", "get_default_object", "load_asset"):
        _require(callable(getattr(u, name, None)), "Missing Unreal API: " + name)
    version = str(u.SystemLibrary.get_engine_version())
    _require(re.match(r"^5\.7\.4(?:[-+]|$)", version) is not None,
             "This patch is restricted to Unreal 5.7.4; found: " + version)
    for cls, name in (("FBXImportType", "FBXIT_STATIC_MESH"),
                      ("FBXNormalImportMethod", "FBXNIM_IMPORT_NORMALS"),
                      ("FBXNormalGenerationMethod", "MIKK_T_SPACE"),
                      ("CollisionTraceFlag", "CTF_USE_SIMPLE_AND_COMPLEX")):
        _enum(u, cls, name)
    # CDO property READS only. No object/asset/map creation and no property setters in preflight.
    for cls, properties in (
        (u.FbxImportUI, ("import_mesh", "import_as_skeletal", "import_animations", "import_materials",
                         "import_textures", "automated_import_should_detect_type", "mesh_type_to_import",
                         "original_import_type", "override_full_name", "static_mesh_import_data")),
        (u.FbxStaticMeshImportData, tuple(FBX_FIELDS) + ("normal_import_method", "normal_generation_method",
                  "import_translation", "import_rotation", "coordinate_system_policy", "using_luf_coordinate_sysem")),
        (u.AssetImportTask, ("filename", "destination_path", "destination_name", "automated", "async_", "save",
                            "replace_existing", "replace_existing_settings", "factory", "options", "imported_object_paths")),
    ):
        default = u.get_default_object(cls)
        for prop in properties:
            default.get_editor_property(prop)
    # A different coordinate-conversion mode is deliberately not guessed around.
    _require(not u.get_default_object(u.FbxStaticMeshImportData).get_editor_property("using_luf_coordinate_sysem"),
             "LUF coordinate mode is unsupported for this already-converted XYZ source; stop for review")
    body_default = u.get_default_object(u.BodySetup)
    body_default.get_editor_property("collision_trace_flag")
    aggregate = body_default.get_editor_property("agg_geom")
    for prop in ("convex_elems",) + OTHER_SHAPES:
        aggregate.get_editor_property(prop)
    _require(callable(getattr(u.AssetToolsHelpers.get_asset_tools(), "import_asset_tasks", None)),
             "Missing AssetTools.import_asset_tasks")
    for cls in (u.EditorActorSubsystem, u.UnrealEditorSubsystem, u.StaticMeshEditorSubsystem):
        _require(u.get_editor_subsystem(cls) is not None, "Editor subsystem unavailable")
    return version


def _guard_editor(u):
    loading = u.EditorLoadingAndSavingUtils
    _require(not loading.get_dirty_map_packages(), "Dirty map(s): save or discard them yourself before importing")
    _require(not loading.get_dirty_content_packages(), "Dirty content: save or discard it yourself before importing")
    _require(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is None,
             "Stop Play/Simulate before calibration")
    library = u.EditorAssetLibrary
    _require(not library.does_directory_exist(DESTINATION) and
             not library.list_assets(DESTINATION, recursive=True, include_folder=True),
             "Existing calibration namespace rejected: " + DESTINATION)
    # The Asset Registry need not retain an empty folder. Check the real Content
    # path too, using Unreal's BaseDir-aware conversion rather than Python's cwd.
    content = Path(str(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())))
    _require(content.is_absolute() and content.is_dir(), "Cannot verify physical project Content directory")
    physical_destination = content / DESTINATION.removeprefix("/Game/")
    _require(not physical_destination.exists() and not physical_destination.is_symlink(),
             "Existing physical calibration namespace rejected: " + str(physical_destination))
    for target in [SUGGESTED_MAP_PATH] + [MESH_FOLDER + "/" + row[0] for row in SAMPLES]:
        _require(not library.does_asset_exist(target), "Existing sample target rejected: " + target)
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        _require("CarnivalCalibration57" not in [str(t) for t in actor.get_editor_property("tags")],
                 "Calibration actors already exist; inspect previous run instead of repeating")


def preflight(package_root):
    """Read/hash only. Returns a report; never creates maps/assets/reports or saves.

    Offline Python can verify source bytes but cannot return ready_to_import=True.
    A successful preflight is not permission and is never cached for import_sample.
    """
    report = _base_report("preflight")
    try:
        contract = _contract(package_root)
        report.update(package_root=contract["root"], source_sha256=contract["source_sha256"],
                      source_bytes=contract["source_bytes"], verified_files=contract["verified_files"], normalized_json_files=contract["normalized_json_files"],
                      sample_assets=[dict(name=a["asset_name"], hulls=a["collision_hulls"],
                                          material_slots=len(a["materials"]), uv_channels=1,
                                          bounds_cm=a["bounds_cm"]) for a in contract["selected"]])
        try:
            u = importlib.import_module("unreal")
        except ModuleNotFoundError as exc:
            if exc.name != "unreal":
                raise
            report.update(status="FILES_VERIFIED_ENGINE_NOT_CHECKED", editor_available=False)
            return report
        report["editor_available"] = True
        report["engine_version"] = _guard_api(u)
        _guard_editor(u)
        report.update(status="PREFLIGHT_PASS", ready_to_import=True)
    except Exception as exc:
        report.update(status="PREFLIGHT_BLOCKED", error=str(exc))
    return report


def _set_readback(obj, values):
    for key, value in values.items():
        obj.set_editor_property(key, value)
        _require(obj.get_editor_property(key) == value, "Option readback mismatch: " + key)


def _options(u):
    options = u.FbxImportUI()
    _set_readback(options, dict(import_mesh=True, import_as_skeletal=False, import_animations=False,
        import_materials=False, import_textures=False, automated_import_should_detect_type=False,
        mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH,
        original_import_type=u.FBXImportType.FBXIT_STATIC_MESH, override_full_name=True))
    data = options.get_editor_property("static_mesh_import_data")
    _require(isinstance(data, u.FbxStaticMeshImportData), "Unexpected options import-data class")
    _set_readback(data, FBX_FIELDS)
    _set_readback(data, dict(normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                            normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE,
                            import_translation=u.Vector(0, 0, 0),
                            import_rotation=u.Rotator(roll=0, pitch=0, yaw=0)))
    _require(not data.get_editor_property("using_luf_coordinate_sysem"), "Unsupported LUF coordinate mode")
    return options


def _path(obj):
    return str(obj.get_path_name())


def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _validate_mesh(u, mesh, item):
    name = item["asset_name"]
    _require(isinstance(mesh, u.StaticMesh), "Expected StaticMesh: " + name)
    data = mesh.get_editor_property("asset_import_data")
    _require(isinstance(data, u.FbxStaticMeshImportData) and str(data.get_class().get_name()) == "FbxStaticMeshImportData",
             "Wrong importer provenance (possibly Interchange); expected legacy FbxStaticMeshImportData: " + name)
    files = list(data.extract_filenames())
    _require(len(files) == 1 and Path(str(files[0])).resolve() == Path(item["source_path"]).resolve(),
             "Actual import-data source path mismatch: " + name)
    for key, expected in dict(FBX_FIELDS, normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                             normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE).items():
        _require(data.get_editor_property(key) == expected, "Imported setting mismatch: " + name + ": " + key)
    _require(_vec(data.get_editor_property("import_translation")) == [0., 0., 0.], "Unexpected import translation")
    rotation = data.get_editor_property("import_rotation")
    _require(all(float(getattr(rotation, k)) == 0 for k in ("roll", "pitch", "yaw")), "Unexpected import rotation")
    _require(not data.get_editor_property("using_luf_coordinate_sysem"), "Imported LUF mode unsupported")
    bounds = mesh.get_bounds()
    origin, extent = _vec(bounds.origin), _vec(bounds.box_extent)
    actual = {"min": [origin[i] - extent[i] for i in range(3)], "max": [origin[i] + extent[i] for i in range(3)]}
    expected = item["bounds_cm"]
    errors = []
    for key in ("min", "max"):
        for axis in range(3):
            tolerance = max(0.05, (expected["max"][axis] - expected["min"][axis]) * 0.001)
            error = abs(actual[key][axis] - expected[key][axis])
            _require(math.isfinite(error) and error <= tolerance,
                     "Centimetre bounds/pivot/axis mismatch: " + name + ": " + repr(actual))
            errors.append(error)
    ss = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    convex = ss.get_convex_collision_count(mesh)
    simple = ss.get_simple_collision_count(mesh)
    _require(convex == item["collision_hulls"] and simple >= 0, "UCX collision count mismatch: " + name)
    body = mesh.get_editor_property("body_setup")
    _require(body is not None, "Missing BodySetup: " + name)
    trace_flag = body.get_editor_property("collision_trace_flag")
    _require(trace_flag == u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX,
             "Collision must explicitly use authored simple collision, not a project default or ComplexAsSimple: " + name)
    agg = body.get_editor_property("agg_geom")
    counts = {kind: len(agg.get_editor_property(kind)) for kind in ("convex_elems",) + OTHER_SHAPES}
    _require(counts["convex_elems"] == item["collision_hulls"] and not any(counts[k] for k in OTHER_SHAPES),
             "BodySetup must contain exactly authored UCX hulls and no additional primitive/level-set shapes: " + name)
    uv = ss.get_num_uv_channels(mesh, 0)
    _require(uv == item["expected_uv_channels"], "UV channel count mismatch: " + name)
    slots = mesh.get_editor_property("static_materials")
    _require(len(slots) == len(item["materials"]), "Material-slot count mismatch: " + name)
    slot_names = [str(slot.get_editor_property("imported_material_slot_name")) for slot in slots]
    for actual_name, source_name in zip(slot_names, item["materials"]):
        # FBX names may be sanitized by the legacy importer. Accept only the
        # original or this exact source-derived form, preserving slot order.
        sanitized = re.sub(r"[^A-Za-z0-9_]", "_", source_name)
        _require(actual_name in (source_name, sanitized),
                 "Imported material-slot name/order mismatch: " + name + ": " + actual_name + " != " + source_name)
    build = ss.get_lod_build_settings(mesh, 0)
    for key, value in BUILD_FIELDS.items():
        _require(build.get_editor_property(key) == value, "Mesh build setting mismatch: " + key)
    return dict(name=name, mesh_path=_path(mesh), importer_class="FbxStaticMeshImportData",
                bounds_cm=actual, expected_bounds_cm=expected, max_bounds_error_cm=max(errors),
                convex_count=convex, simple_count_diagnostic_only=simple, bodysetup_shapes=counts,
                collision_trace_flag=str(trace_flag),
                uv_channels=uv, material_slot_count=len(slots), source_materials=item["materials"],
                imported_material_slot_names=slot_names,
                build_settings=dict(BUILD_FIELDS), coordinate_system_policy=str(data.get_editor_property("coordinate_system_policy")),
                material_validation="NOT_RUN", geometry_collision_checks="PASS")


def import_sample(package_root):
    """EXPLICIT MUTATION: 3 unsaved meshes, 4 actors, fresh unsaved blank map.

    Raises CalibrationError(report) on failure. No saving or rollback/cleanup.
    The bucket is placed twice using the SAME StaticMesh; only three assets import.
    """
    report = _base_report("import_sample")
    try:
        # Every byte check is repeated here. Preflight results cannot authorize/bypass checks.
        contract = _contract(package_root)
        report.update(package_root=contract["root"], source_sha256=contract["source_sha256"],
                      source_bytes=contract["source_bytes"], verified_files=contract["verified_files"],
                      normalized_json_files=contract["normalized_json_files"])
        u = importlib.import_module("unreal")
        report["engine_version"] = _guard_api(u)
        _guard_editor(u)
        tasks = []
        for item in contract["selected"]:
            task = u.AssetImportTask()
            _set_readback(task, dict(filename=item["source_path"], destination_path=MESH_FOLDER,
                destination_name=item["asset_name"], automated=True, async_=False, save=False,
                replace_existing=False, replace_existing_settings=False,
                factory=u.FbxFactory(), options=_options(u)))
            tasks.append((item, task))
        # Reading the engine default material creates no new material asset.
        default_material = u.load_asset("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial")
        _require(isinstance(default_material, u.MaterialInterface), "Engine default material unavailable")
        _guard_editor(u)  # Immediately before first mutating operation / level switch.
        old_world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        report["previous_world"] = _path(old_world) if old_world else None
        report["mutation_started"] = True
        report["stage"] = "new_blank_map"
        world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
        _require(world is not None and isinstance(world, u.World) and world != old_world,
                 "Fresh unsaved blank map creation failed")
        report["world_path"] = _path(world)
        _require(not _path(world).startswith("/Game/"), "New map unexpectedly has a saved content path; stop")
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        # Blank engine-owned WorldSettings/Brush are permitted, authored actors are not.
        existing = list(actors.get_all_level_actors())
        _require(all(str(a.get_class().get_name()) in ("WorldSettings", "Brush") for a in existing),
                 "Fresh map unexpectedly contains authored actors; stop without deleting anything")
        meshes = {}
        report["mesh_checks"] = []
        for item, task in tasks:
            name = item["asset_name"]
            target = MESH_FOLDER + "/" + name
            _require(not u.EditorAssetLibrary.does_asset_exist(target), "Existing asset target rejected: " + target)
            _require(_sha(Path(item["source_path"])) == item["fbx_sha256"], "Sample changed after verification: " + name)
            report["stage"] = "import:" + name
            entry = dict(requested=target, actual=[], task_paths=[], status="ATTEMPTED", readback_errors=[])
            report["imported_objects"].append(entry)
            objects = []
            try:
                u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                entry["status"] = "IMPORT_CALL_RETURNED"
            finally:
                # Keep partial identities even when the importer throws. Each
                # read is isolated so one failed query cannot hide the other.
                try:
                    entry["task_paths"] = [str(p) for p in task.get_editor_property("imported_object_paths")]
                except Exception as read_error:
                    entry["readback_errors"].append("imported_object_paths: " + str(read_error))
                try:
                    objects = list(task.get_objects())
                    entry["actual"] = [_path(o) for o in objects]
                except Exception as read_error:
                    entry["readback_errors"].append("get_objects: " + str(read_error))
            paths = entry["task_paths"]
            _require(not entry["readback_errors"], "Unable to verify actual import results: " + repr(entry))
            expected_object = target + "." + name
            _require(len(objects) == 1 and _path(objects[0]) == expected_object and paths == [expected_object],
                     "Task result count/name/path mismatch; no guessed load or rename is allowed: " + name)
            mesh = objects[0]
            # Reject non-legacy provenance BEFORE changing this newly imported object.
            data = mesh.get_editor_property("asset_import_data")
            _require(isinstance(mesh, u.StaticMesh) and isinstance(data, u.FbxStaticMeshImportData) and
                     str(data.get_class().get_name()) == "FbxStaticMeshImportData", "Expected legacy FBX static mesh import")
            ss = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
            build = ss.get_lod_build_settings(mesh, 0)
            _set_readback(build, BUILD_FIELDS)
            ss.set_lod_build_settings(mesh, 0, build)
            body = mesh.get_editor_property("body_setup")
            _require(body is not None, "Missing BodySetup: " + name)
            # Only this new unsaved asset changes. Do not inherit a project
            # ComplexAsSimple default, which could hide missing UCX behaviour.
            _set_readback(body, {"collision_trace_flag": u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX})
            for index in range(len(mesh.get_editor_property("static_materials"))):
                mesh.set_material(index, default_material)
                _require(mesh.get_material(index) == default_material, "Default material assignment failed")
            report["mesh_checks"].append(_validate_mesh(u, mesh, item))
            meshes[name] = mesh
        placements = [(contract["selected"][i], i * 500.0, 0.0) for i in range(3)]
        placements.append((contract["selected"][2], 1000.0, 350.0))
        spawned = []
        for index, (item, x, y) in enumerate(placements):
            report["stage"] = "spawn:" + str(index + 1)
            # All bottoms sit at z=0 for inspection; there is no actual floor.
            location = [x, y, -item["bounds_cm"]["min"][2]]
            actor = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(*location),
                                                  u.Rotator(roll=0, pitch=0, yaw=0), transient=False)
            _require(actor is not None and isinstance(actor, u.StaticMeshActor), "StaticMeshActor spawn failed")
            report["spawned_actors"].append(dict(path=_path(actor), mesh=item["asset_name"], location_cm=location))
            _require(str(actor.get_class().get_name()) == "StaticMeshActor", "Blueprint actor is forbidden")
            actor.set_actor_label("Calibration57_%02d_%s" % (index + 1, item["asset_name"]))
            tags = list(dict.fromkeys(item["source_tags"] + ["CarnivalCalibration57"]))
            actor.set_editor_property("tags", [u.Name(t) for t in tags])
            actor.set_actor_scale3d(u.Vector(1, 1, 1))
            comp = actor.get_editor_property("static_mesh_component")
            _require(comp.set_static_mesh(meshes[item["asset_name"]]), "Actor mesh assignment failed")
            comp.set_simulate_physics(False)
            _require(comp.get_editor_property("static_mesh") == meshes[item["asset_name"]], "Wrong actor mesh")
            _require("PropActor" in [str(t) for t in actor.get_editor_property("tags")], "PropActor tag lost")
            _require(_vec(actor.get_actor_scale3d()) == [1., 1., 1.] and
                     max(abs(a-b) for a,b in zip(_vec(actor.get_actor_location()), location)) < 0.001,
                     "Actor transform mismatch")
            spawned.append(actor)
        _require(len({_path(a) for a in spawned}) == 4, "Actors are not four independent placements")
        _require(len(actors.get_all_level_actors()) == len(existing) + 4, "Unexpected actor count")
        report.update(status="SAMPLE_GEOMETRY_COLLISION_PASS_UNSAVED", stage="complete", partial_import=False,
                      canonical_assets=3, actor_placements=4, map_saved=False, assets_saved=False,
                      ready_to_import=False, next_step="Inspect the four actors and authored collision manually. Nothing has been saved.")
        return report
    except Exception as exc:
        if report["mutation_started"]:
            try:
                report["namespace_assets_on_failure"] = [str(p) for p in
                    u.EditorAssetLibrary.list_assets(DESTINATION, recursive=True, include_folder=False)]
            except Exception as snapshot_error:
                report["failure_snapshot_error"] = str(snapshot_error)
        report.update(status="SAMPLE_FAILED_PARTIAL" if report["mutation_started"] else "SAMPLE_BLOCKED",
                      partial_import=report["mutation_started"], error=str(exc),
                      recovery="No automatic cleanup was attempted. Inspect partial assets/actors and preserve any wanted work before manually deciding what to discard.")
        raise CalibrationError(report) from exc


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Read-only calibration preflight; never imports assets.")
    parser.add_argument("package_root", help="Unmodified AbandonedCarnival package root")
    args = parser.parse_args()
    result = preflight(args.package_root)
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(1 if result["status"] == "PREFLIGHT_BLOCKED" else 0)
