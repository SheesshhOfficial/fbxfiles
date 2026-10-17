"""Additive UE5.7.4 material/neutral-light sample stage. Import does no work.

preflight(root) is read-only; apply(root) is explicit mutation. No save/delete.
Requires the earlier geometry calibration and its 3 mesh assets saved by the user.
"""
from __future__ import annotations
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re

DEST = "/Game/AbandonedCarnivalCalibration57/MaterialStage"
MATS, TEX = DEST + "/Materials", DEST + "/Textures"
MAP = "/Game/AbandonedCarnivalCalibration57/Maps/Calibration57.Calibration57"
MATERIAL_MANIFEST_SHA = "7b4624bf35618733783f8b13b9d7a376890a4dbed795b0177f4ff574739caaa2"
CORE_SHA = "5575273cce7f485930e73f363821d9294b62e374919639b7169cead28af74171"
LIGHT_TAG = "CarnivalMaterialStage57"


class MaterialStageError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(json.dumps(report, indent=2, allow_nan=False))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def core():
    path = Path(__file__).resolve().parents[1] / "carnival_calibration57.py"
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == CORE_SHA or
            hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == CORE_SHA,
            "Original geometry helper changed or is missing; use the matching first patch")
    spec = importlib.util.spec_from_file_location("_carnival_geometry_core57", path)
    module = importlib.util.module_from_spec(spec)
    # compile/exec avoids writing a Python cache when loading this dependency.
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def texture_name(relative, usage):
    stem = re.sub(r"[^A-Za-z0-9_]", "_", Path(relative).stem)[:45]
    return "T_" + stem + "_" + hashlib.sha256((relative + "|" + usage).encode()).hexdigest()[:8]


def plan(root):
    c = core()
    contract = c._contract(root)
    base = Path(contract["root"])
    rel = "export/unreal/material_manifest.json"
    path = c._safe_file(base, rel)
    actual, normalized = c._pinned_json_sha(path, MATERIAL_MANIFEST_SHA)
    data = c._read(path)
    inventory = c._read(c._safe_file(base, "FILE_MANIFEST.json"))
    require(data["source_sha256"] == c.SOURCE_SHA256, "Material/source lineage mismatch")
    rows = {row["path"]: row for row in inventory["files"]}
    require(rows[rel]["sha256"] == MATERIAL_MANIFEST_SHA, "Frozen material inventory mismatch")
    needed = {name for a in contract["selected"] for name in a["materials"]}
    selected = [r for r in data["materials"] if r["source_name"] in needed]
    require(len(selected) == len(needed) == 9 and len({r["source_name"] for r in selected}) == 9,
            "Expected exactly the nine source sample materials")
    textures = {}
    for r in selected:
        require(not r["glass_approximation"] and r["transmission"] == 0, "Unexpected translucent source recipe")
        require(re.fullmatch(r"M_[A-Za-z0-9_]+", r["asset_name"]), "Unsafe material name")
        for usage, entry in r["maps"].items():
            require(usage in ("base_color", "roughness", "normal") and entry["available"], "Unsupported/missing source texture")
            relative = "export/" + entry["path"]
            file = c._safe_file(base, relative)
            require(relative in rows and c._sha(file) == rows[relative]["sha256"] and file.stat().st_size == rows[relative]["bytes"],
                    "Whole texture SHA256/size mismatch: " + relative)
            key = (entry["path"], usage)
            record = dict(path=entry["path"], usage=usage, filename=str(file), sha256=rows[relative]["sha256"],
                          asset_name=texture_name(*key), flip_green=bool(r["normal_flip_green"]) if usage == "normal" else False)
            require(key not in textures or textures[key] == record, "Conflicting shared texture settings")
            textures[key] = record
    require(len(textures) == 10, "Expected exactly ten texture-role inputs")
    return c, dict(contract=contract, materials=selected, textures=list(textures.values()),
                   material_manifest_actual_sha256=actual, material_manifest_crlf_normalized=normalized)


def report_base(mode):
    return dict(schema="carnival-material-stage57-v1", mode=mode, status="PENDING", ready=False,
                mutation_started=False, partial=False, saves_performed=0, textures=[], materials=[], assignments=[],
                lights=[], rollback=[], shader_compilation="NOT_VERIFIED", visual_review="NOT_RUN",
                namespace=DEST, required_saved_map=MAP,
                limitations=["Nine source materials/ten textures only; not the full carnival.",
                    "Sequential synchronous texture submissions can still trigger background engine compilation; no memory-use guarantee.",
                    "Neutral diagnostic lights do not reproduce Blender lighting. Exposure/project settings are unchanged.",
                    "No shader compilation success, visual fidelity, final reflections, gameplay or multiplayer claim.",
                    "Nothing is saved or deleted. Failed assignments are restored where possible; generated assets/lights remain for inspection."])


def api(u, c):
    version = c._guard_api(u)
    required = {
        "TextureFactory": (), "Texture2D": ("set_virtual_texture_streaming",), "AssetImportData": ("extract_filenames",),
        "Material": (), "MaterialFactoryNew": (), "MaterialExpressionTextureSample": (),
        "MaterialExpressionTextureCoordinate": (), "MaterialExpressionConstant": (),
        "MaterialExpressionConstant3Vector": (), "MaterialExpressionMultiply": (),
        "MaterialEditingLibrary": ("create_material_expression", "connect_material_property", "connect_material_expressions", "recompile_material"),
        "DirectionalLight": (), "PointLight": (), "DirectionalLightComponent": (),
        "PointLightComponent": ("set_intensity", "set_light_color", "set_mobility", "set_use_inverse_squared_falloff"), "LinearColor": (),
    }
    for cls, methods in required.items():
        target = getattr(u, cls, None)
        require(target is not None, "Missing Unreal class: " + cls)
        for name in methods:
            require(callable(getattr(target, name, None)), "Missing Unreal API: " + cls + "." + name)
    enums = {"TextureCompressionSettings": ("TC_DEFAULT", "TC_NORMALMAP", "TC_MASKS"),
             "MaterialSamplerType": ("SAMPLERTYPE_COLOR", "SAMPLERTYPE_NORMAL", "SAMPLERTYPE_MASKS"),
             "MaterialProperty": ("MP_BASE_COLOR", "MP_ROUGHNESS", "MP_NORMAL", "MP_METALLIC", "MP_EMISSIVE_COLOR"),
             "BlendMode": ("BLEND_OPAQUE",), "MaterialShadingModel": ("MSM_DEFAULT_LIT",),
             "ComponentMobility": ("MOVABLE",), "LightUnits": ("LUMENS",)}
    for kind, names in enums.items():
        for name in names: c._enum(u, kind, name)
    for cls, fields in ((u.TextureFactory, ("create_material", "edit_after_new", "compression_settings", "flip_normal_map_green_channel")),
                        (u.Texture2D, ("asset_import_data", "srgb", "compression_settings", "flip_green_channel", "virtual_texture_streaming")),
                        (u.Material, ("two_sided", "blend_mode", "shading_model")),
                        (u.PointLightComponent, ("intensity_units", "attenuation_radius", "cast_shadows", "use_temperature", "specular_scale"))):
        default = u.get_default_object(cls)
        for key in fields: default.get_editor_property(key)
    require(callable(getattr(u.AssetToolsHelpers.get_asset_tools(), "create_asset", None)), "Missing AssetTools.create_asset")
    return version


def guard(u, c, p):
    require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Save the sample map yourself before this stage; dirty map(s) found")
    require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), "Save the three sample meshes/other wanted work yourself; dirty content found")
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    require(editor.get_game_world() is None, "Stop Play/Simulate before this stage")
    world = editor.get_editor_world()
    require(world and world.get_path_name() == MAP, "Open the saved calibration map: " + MAP)
    library = u.EditorAssetLibrary
    require(library.does_asset_exist(MAP.split(".")[0]), "Calibration map is not a saved asset")
    require(not library.does_directory_exist(DEST) and not library.list_assets(DEST, recursive=True, include_folder=True),
            "MaterialStage namespace already exists; inspect previous attempt, do not rerun")
    content = Path(str(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())))
    require(content.is_absolute() and content.is_dir(), "Cannot verify Content directory")
    physical = content / DEST.removeprefix("/Game/")
    require(not physical.exists() and not physical.is_symlink(), "MaterialStage physical directory already exists")
    expected = {c.MESH_FOLDER + "/" + a["asset_name"] + "." + a["asset_name"]: a for a in p["contract"]["selected"]}
    meshes = {}
    for path, item in expected.items():
        require(library.does_asset_exist(path.split(".")[0]), "Expected saved sample mesh missing: " + path)
        mesh = u.load_asset(path)
        require(mesh and mesh.get_path_name() == path, "Wrong sample mesh identity")
        c._validate_mesh(u, mesh, item)
        meshes[item["asset_name"]] = mesh
    actors = list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
    placed = []
    counts = {path: 0 for path in expected}
    for actor in actors:
        cls = str(actor.get_class().get_name())
        if cls in ("WorldSettings", "Brush"):
            continue
        require(cls == "StaticMeshActor" and isinstance(actor, u.StaticMeshActor), "Unexpected actor in calibration map: " + cls)
        tags = [str(t) for t in actor.get_editor_property("tags")]
        require("PropActor" in tags and "CarnivalCalibration57" in tags, "Unexpected sample actor tags")
        component = actor.get_editor_property("static_mesh_component")
        mesh = component.get_editor_property("static_mesh")
        require(mesh and mesh.get_path_name() in expected, "Actor uses unexpected mesh")
        require(not any(component.get_editor_property("override_materials")), "Sample actor has material overrides; inspect before applying mesh materials")
        counts[mesh.get_path_name()] += 1
        placed.append(actor)
    require(len(placed) == 4 and len({a.get_path_name() for a in placed}) == 4 and sorted(counts.values()) == [1, 1, 2] and counts[c.MESH_FOLDER + "/" + c.SAMPLES[2][0] + "." + c.SAMPLES[2][0]] == 2,
            "Expected exactly car/pallet/bucket/bucket: four native sample actors")
    return meshes, actors


def preflight(package_root):
    r = report_base("preflight")
    try:
        c, p = plan(package_root)
        r.update(material_count=9, texture_count=10, material_manifest_crlf_normalized=p["material_manifest_crlf_normalized"],
                 source_sha256=c.SOURCE_SHA256)
        try: u = importlib.import_module("unreal")
        except ModuleNotFoundError as exc:
            if exc.name != "unreal": raise
            r["status"] = "FILES_VERIFIED_ENGINE_NOT_CHECKED"
            return r
        r["engine_version"] = api(u, c)
        guard(u, c, p)
        r.update(status="MATERIAL_PREFLIGHT_PASS", ready=True)
    except Exception as exc: r.update(status="MATERIAL_PREFLIGHT_BLOCKED", error=str(exc))
    return r


def set_checked(obj, key, value):
    obj.set_editor_property(key, value)
    require(obj.get_editor_property(key) == value, "Property readback mismatch: " + key)


def import_texture(u, c, record, report):
    name = record["asset_name"]
    expected = TEX + "/" + name + "." + name
    require(not u.EditorAssetLibrary.does_asset_exist(expected), "Texture target exists")
    require(c._sha(Path(record["filename"])) == record["sha256"], "Texture changed after preflight")
    usage = record["usage"]
    compression = {"base_color": u.TextureCompressionSettings.TC_DEFAULT,
                   "normal": u.TextureCompressionSettings.TC_NORMALMAP,
                   "roughness": u.TextureCompressionSettings.TC_MASKS}[usage]
    factory = u.TextureFactory()
    for key, value in dict(create_material=False, edit_after_new=False, compression_settings=compression,
                           flip_normal_map_green_channel=record["flip_green"]).items(): set_checked(factory, key, value)
    task = u.AssetImportTask()
    for key, value in dict(filename=record["filename"], destination_path=TEX, destination_name=name,
            factory=factory, automated=True, async_=False, save=False,
            replace_existing=False, replace_existing_settings=False).items(): set_checked(task, key, value)
    row = dict(requested=expected, status="ATTEMPTED", actual_paths=[], source=record["filename"])
    report["textures"].append(row)
    objects = []
    try:
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    finally:
        try: row["actual_paths"] = [str(v) for v in task.get_editor_property("imported_object_paths")]
        except Exception as exc: row["path_readback_error"] = str(exc)
        try:
            objects = list(task.get_objects())
            row["actual_objects"] = [o.get_path_name() for o in objects]
        except Exception as exc: row["object_readback_error"] = str(exc)
    require(len(objects) == 1 and isinstance(objects[0], u.Texture2D) and objects[0].get_path_name() == expected
            and row["actual_paths"] == [expected], "Texture result identity mismatch; possible Interchange routing: " + name)
    tex = objects[0]
    data = tex.get_editor_property("asset_import_data")
    require(isinstance(data, u.AssetImportData), "Missing native texture AssetImportData")
    row["import_data_class"] = str(data.get_class().get_name())
    require(row["import_data_class"] == "AssetImportData", "Unexpected texture importer provenance: " + row["import_data_class"])
    files = list(data.extract_filenames())
    require(len(files) == 1 and Path(str(files[0])).resolve() == Path(record["filename"]).resolve(), "Texture source filename mismatch")
    tex.set_virtual_texture_streaming(False)
    require(tex.get_editor_property("virtual_texture_streaming") is False, "Virtual texture disable readback failed")
    for key, value in dict(srgb=usage == "base_color", compression_settings=compression,
                           flip_green_channel=record["flip_green"]).items(): set_checked(tex, key, value)
    row.update(status="SETTINGS_VERIFIED", usage=usage, srgb=usage == "base_color", compression=str(compression),
               flip_green=record["flip_green"], virtual_texture_streaming=False, sha256=record["sha256"])
    return tex


def material(u, record, textures, report):
    name = record["asset_name"]
    target = MATS + "/" + name
    require(not u.EditorAssetLibrary.does_asset_exist(target), "Material target exists")
    row = dict(source_name=record["source_name"], requested=target, status="ATTEMPTED")
    report["materials"].append(row)
    mat = u.AssetToolsHelpers.get_asset_tools().create_asset(name, MATS, u.Material, u.MaterialFactoryNew())
    require(isinstance(mat, u.Material) and mat.get_path_name() == target + "." + name, "Material creation identity mismatch")
    row["actual"] = mat.get_path_name()
    for key, value in dict(two_sided=record["two_sided"], blend_mode=u.BlendMode.BLEND_OPAQUE,
                           shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT).items(): set_checked(mat, key, value)
    lib = u.MaterialEditingLibrary
    def node(cls, y):
        result = lib.create_material_expression(mat, cls, -400, y)
        require(result is not None, "Material expression creation failed")
        return result
    uv = None
    if record["maps"]:
        uv = node(u.MaterialExpressionTextureCoordinate, -200)
        for key, value in dict(coordinate_index=0, u_tiling=1., v_tiling=1.).items(): set_checked(uv, key, value)
    props = {"base_color": u.MaterialProperty.MP_BASE_COLOR, "roughness": u.MaterialProperty.MP_ROUGHNESS,
             "normal": u.MaterialProperty.MP_NORMAL, "metallic": u.MaterialProperty.MP_METALLIC,
             "emission_color": u.MaterialProperty.MP_EMISSIVE_COLOR}
    samplers = {"base_color": u.MaterialSamplerType.SAMPLERTYPE_COLOR, "roughness": u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                "normal": u.MaterialSamplerType.SAMPLERTYPE_NORMAL}
    for index, (usage, prop) in enumerate(props.items()):
        if usage in record["maps"]:
            expression = node(u.MaterialExpressionTextureSample, index * 200)
            key = (record["maps"][usage]["path"], usage)
            set_checked(expression, "texture", textures[key])
            set_checked(expression, "sampler_type", samplers[usage])
            set_checked(expression, "const_coordinate", 0)
            require(lib.connect_material_expressions(uv, "", expression, "UVs"), "UV0 connection failed")
            output = "R" if usage == "roughness" else "RGB"
        elif usage == "normal":
            continue
        elif usage in ("base_color", "emission_color"):
            expression = node(u.MaterialExpressionConstant3Vector, index * 200)
            set_checked(expression, "constant", u.LinearColor(*record.get(usage, [0., 0., 0.])[:3], 1.))
            output = ""
        else:
            expression = node(u.MaterialExpressionConstant, index * 200)
            set_checked(expression, "r", float(record[usage]))
            output = ""
        if usage == "base_color" and "base_color_multiply_linear" in record:
            tint = node(u.MaterialExpressionConstant3Vector, -400)
            set_checked(tint, "constant", u.LinearColor(*record["base_color_multiply_linear"], 1.))
            mul = node(u.MaterialExpressionMultiply, 0)
            require(lib.connect_material_expressions(expression, output, mul, "A") and
                    lib.connect_material_expressions(tint, "", mul, "B"), "Source basecolor tint connection failed")
            expression, output = mul, ""
        require(lib.connect_material_property(expression, output, prop), "Material property connection failed: " + usage)
    lib.recompile_material(mat)
    row.update(status="GRAPH_CREATED_COMPILATION_REQUESTED", source_approximations=record["approximations"])
    return mat


def add_lights(u, report):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    configs = [(u.DirectionalLight, u.DirectionalLightComponent, "NeutralKey", (500., -600., 600.),
                dict(pitch=-45., yaw=45., roll=0.), 1000., True),
               (u.PointLight, u.PointLightComponent, "NeutralFillFront", (500., -400., 350.),
                dict(pitch=0., yaw=0., roll=0.), 8000., False),
               (u.PointLight, u.PointLightComponent, "NeutralFillBack", (500., 400., 250.),
                dict(pitch=0., yaw=0., roll=0.), 8000., False)]
    for cls, component_cls, label, location, rotation, intensity, shadows in configs:
        row = dict(label=label, status="ATTEMPTED", intensity=intensity, units="lux" if cls == u.DirectionalLight else "lumens")
        report["lights"].append(row)
        actor = actors.spawn_actor_from_class(cls, u.Vector(*location), u.Rotator(**rotation), transient=False)
        require(actor is not None and str(actor.get_class().get_name()) == cls.__name__, "Light spawn failed")
        row["path"] = actor.get_path_name()
        actor.set_actor_label("Calibration57_" + label)
        actor.set_editor_property("tags", [u.Name(LIGHT_TAG)])
        component = actor.get_component_by_class(component_cls)
        require(component is not None, "Light component missing")
        component.set_mobility(u.ComponentMobility.MOVABLE)
        for key, value in dict(cast_shadows=shadows, use_temperature=False, specular_scale=1.).items(): set_checked(component, key, value)
        if cls == u.PointLight:
            component.set_use_inverse_squared_falloff(True)
            require(component.get_editor_property("use_inverse_squared_falloff") is True, "Point fill falloff readback failed")
            set_checked(component, "intensity_units", u.LightUnits.LUMENS)
            set_checked(component, "attenuation_radius", 2000.)
        component.set_light_color(u.LinearColor(1., 1., 1., 1.), False)
        component.set_intensity(intensity)
        require(abs(float(component.get_editor_property("intensity")) - intensity) < 0.01, "Light intensity readback failed")
        row.update(status="CREATED_UNSAVED", location_cm=list(location), rotation=rotation, shadows=shadows)


def apply(package_root):
    """Explicitly create 10 textures/9 materials, assign only 3 saved sample meshes, add 3 lights.

    Nothing is saved. On failure, restore changed mesh assignments, leaving generated
    assets and any lights untouched for user inspection. Raises MaterialStageError(report).
    """
    r = report_base("apply")
    original = []
    baseline_actor_paths = set()
    try:
        c, p = plan(package_root)
        u = importlib.import_module("unreal")
        r["engine_version"] = api(u, c)
        meshes, baseline_actors = guard(u, c, p)
        baseline_actor_paths = {a.get_path_name() for a in baseline_actors}
        for name, mesh in meshes.items():
            for index in range(len(mesh.get_editor_property("static_materials"))):
                original.append((mesh, index, mesh.get_material(index)))
        # Final clean-state boundary. No pending preflight result is treated as permission.
        guard(u, c, p)
        r["mutation_started"] = True
        textures = {}
        for record in p["textures"]:
            r["stage"] = "texture:" + record["asset_name"]
            textures[(record["path"], record["usage"])] = import_texture(u, c, record, r)
        materials = {}
        for record in p["materials"]:
            r["stage"] = "material:" + record["source_name"]
            materials[record["source_name"]] = material(u, record, textures, r)
        for item in p["contract"]["selected"]:
            mesh = meshes[item["asset_name"]]
            for index, name in enumerate(item["materials"]):
                r["stage"] = "assignment:" + item["asset_name"]
                previous = mesh.get_material(index)
                row = dict(mesh=mesh.get_path_name(), slot=index, source_material=name,
                           before=previous.get_path_name() if previous else None, after=materials[name].get_path_name(), status="ATTEMPTED")
                r["assignments"].append(row)
                mesh.set_material(index, materials[name])
                require(mesh.get_material(index) == materials[name], "Sample assignment readback failed")
                row["status"] = "ASSIGNED_UNSAVED"
        r["stage"] = "neutral_lighting"
        add_lights(u, r)
        r.update(status="MATERIAL_STAGE_CREATED_UNSAVED", stage="complete", canonical_meshes=3, material_count=9,
                 texture_count=10, actor_placements=4, added_lights=3, partial=False,
                 next_step="Wait for editor texture/shader work to finish, then inspect in Lit mode. Do not treat this result as shader/visual validation. Nothing was saved.")
        return r
    except Exception as exc:
        if r["assignments"]:
            for mesh, index, previous in original:
                try:
                    if mesh.get_material(index) != previous:
                        mesh.set_material(index, previous)
                    require(mesh.get_material(index) == previous, "Rollback readback failed")
                    r["rollback"].append(dict(mesh=mesh.get_path_name(), slot=index, status="ORIGINAL_RESTORED"))
                except Exception as rollback_error:
                    r["rollback"].append(dict(mesh=mesh.get_path_name(), slot=index, status="FAILED", error=str(rollback_error)))
        if r["mutation_started"]:
            try:
                r["new_actor_paths_on_failure"] = [a.get_path_name() for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
                                                    if a.get_path_name() not in baseline_actor_paths]
                r["namespace_assets_on_failure"] = [str(a) for a in u.EditorAssetLibrary.list_assets(DEST, recursive=True, include_folder=False)]
            except Exception as snapshot_error: r["snapshot_error"] = str(snapshot_error)
        r.update(status="MATERIAL_STAGE_FAILED_PARTIAL" if r["mutation_started"] else "MATERIAL_STAGE_BLOCKED",
                 partial=r["mutation_started"], error=str(exc),
                 recovery="No assets/lights were deleted or saved. Inspect rollback entries; even restored mesh packages may remain dirty. Inspect partial generated objects before deciding what to keep/discard.")
        raise MaterialStageError(r) from exc
