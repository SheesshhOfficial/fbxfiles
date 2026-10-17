"""Full frozen carnival UE5.7.4 import into a new unsaved world/namespace.

No module-import side effects. preflight/validate are read-only. import_full is
explicit mutation. No saving, deletion, replacement, fallback or automatic resume.
"""
from __future__ import annotations
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re

DEST = "/Game/AbandonedCarnivalFull57"
MAP_PATH = DEST + "/Maps/AbandonedCarnivalFull57"
TAG = "AbandonedCarnivalFull57"
COUNTS = dict(mesh_assets=181, prop_assets=138, prop_actors=153, environment_assets=43,
              environment_actors=43, materials=59, textures=41, player_starts=10, lights=41, authored_actors=247)
VENDORS = {"carnival_calibration57.py": "5575273cce7f485930e73f363821d9294b62e374919639b7169cead28af74171",
           "_support/carnival_material_stage57.py": "d06e38dcdd23dfbad3d60ebee0cb11b3d4906813211b383d17f9de8537de3783"}
LIGHT_POLICY = dict(local_lumens_per_source_watt=100., directional_lux_per_source_unit=1.,
                    attenuation_radius_min_cm=1200., source_shadows_preserved=True,
                    attenuation_rule="max(1200, 2*area_width_cm, 2*max(0, location_z_cm)); approximate source-ground Z=0 heuristic",
                    status="APPROXIMATE_PHOTOMETRY_NOT_CALIBRATED", disk_lights="square area_width by area_width")


class FullImportError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(json.dumps(report, indent=2, allow_nan=False))


def require(ok, message):
    if not ok: raise ValueError(message)


def _vendors():
    modules=[]
    for index,(relative,digest) in enumerate(VENDORS.items()):
        path=Path(__file__).resolve().parent/relative; raw=path.read_bytes()
        require(hashlib.sha256(raw).hexdigest()==digest or hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest()==digest,
                "Vendored tested helper changed: "+relative)
        spec=importlib.util.spec_from_file_location("_full57_vendor_"+str(index),path)
        module=importlib.util.module_from_spec(spec);exec(compile(raw,str(path),"exec"),module.__dict__);modules.append(module)
    c,m=modules
    m.DEST=DEST; m.MATS=DEST+"/Materials";m.TEX=DEST+"/Textures"
    return c,m


def basis(rotation):
    pitch,yaw,roll=[math.radians(v) for v in rotation]
    forward=[math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),math.sin(pitch)]
    right0=[-math.sin(yaw),math.cos(yaw),0.]
    up0=[-math.sin(pitch)*math.cos(yaw),-math.sin(pitch)*math.sin(yaw),math.cos(pitch)]
    return forward,[math.cos(roll)*up0[i]+math.sin(roll)*right0[i] for i in range(3)]


def plan(package_root):
    c,m=_vendors(); sample=c._contract(package_root);root=Path(sample["root"])
    inventory=c._read(c._safe_file(root,"FILE_MANIFEST.json"));rows={x["path"]:x for x in inventory["files"]}
    require(len(rows)==len(inventory["files"]),"Duplicate frozen inventory paths")
    verified=dict(sample["verified_files"]);normalized=list(sample["normalized_json_files"])
    def file(relative):
        path=c._safe_file(root,relative);require(relative in rows,"File absent from frozen inventory: "+relative)
        if relative.endswith(".json"):
            actual,norm=c._pinned_json_sha(path,rows[relative]["sha256"])
            if norm: normalized.append(relative)
        else:
            actual=c._sha(path);require(actual==rows[relative]["sha256"] and path.stat().st_size==rows[relative]["bytes"],"Binary hash/size mismatch: "+relative)
        verified[relative]=actual;return path
    props=c._read(file("export/unreal/prop_placements.json"));env=c._read(file("export/unreal/environment_manifest.json"))
    materials=c._read(file("export/unreal/material_manifest.json"));metadata=c._read(file("export/unreal/scene_metadata.json"))
    pq=c._read(file("export/qa/prop_fidelity.json"));eq=c._read(file("export/qa/environment_raw_fidelity.json"))
    for doc,key in ((props,"source_blend_sha256"),(env,"source_sha256"),(materials,"source_sha256"),(metadata,"source_sha256"),(pq,"source_blend_sha256"),(eq,"source_sha256")):
        require(doc.get(key)==c.SOURCE_SHA256,"Mixed source lineage")
    require(pq["all_passed"] is True and eq["all_passed"] is True,"Raw source fidelity evidence did not pass")
    propqa={a["asset"]:a for a in pq["assets"]};envqa={a["asset"]:a for a in eq["results"]}
    require(len(props["assets"])==138 and len(props["placements"])==153 and len(env["assets"])==43 and len(materials["materials"])==59,"Unexpected full export counts")
    assets=[];placements=[];seen=set()
    for kind,records,qa in (("props",props["assets"],propqa),("environment",env["assets"],envqa)):
        for a in records:
            name=a["asset_name"];require(name not in seen and re.fullmatch(r"SM_[A-Za-z0-9_]+",name),"Duplicate/unsafe mesh name");seen.add(name)
            relative=("export/unreal/" if kind=="props" else "export/")+a["fbx"]
            path=file(relative);require(rows[relative]["sha256"]==a["fbx_sha256"],"FBX metadata hash mismatch: "+name)
            q=qa[name];require(q["passed"] is True and q["uv_layer_count"]==1,"Source UV/fidelity check failed: "+name)
            bounds=a["bounds_cm"] if kind=="props" else dict(zip(("min","max"),a["bounds_local_cm"]))
            for key in ("min","max"):c._vector(bounds[key])
            require(all(bounds["max"][i]>bounds["min"][i] for i in range(3)),"Invalid bounds: "+name)
            hulls=a["collision_hulls"] if kind=="props" else a["ucx_hulls"]
            require(type(hulls)==int and hulls>=(1 if kind=="props" else 0),"Invalid authored collision count")
            assets.append(dict(asset_name=name,kind=kind,source_path=str(path),fbx_sha256=a["fbx_sha256"],bounds_cm=bounds,
                               collision_hulls=hulls,materials=a["materials"],expected_uv_channels=1))
            if kind=="environment":
                require(a["rotation_degrees"]==[0,0,0] and a["scale"]==[1,1,1],"Unexpected environment transform")
                placements.append(dict(asset_name=name,source_object=name,location_cm=c._vector(a["location_cm"]),tags=["MoonfallEnvironment"],kind=kind,id="env:"+name))
    for p in props["placements"]:
        require(p["asset_name"] in seen and p["actor_class"]=="StaticMeshActor" and "PropActor" in p["actor_tags"] and
                p["rotation_deg_pitch_yaw_roll"]==[0,0,0] and p["scale"]==[1,1,1],"Unexpected prop actor/transform")
        placements.append(dict(asset_name=p["asset_name"],source_object=p["source_object"],location_cm=c._vector(p["location_cm"]),tags=p["actor_tags"],kind="props",id="prop:"+p["source_object"]))
    matrows=materials["materials"];names={r["source_name"] for r in matrows}
    require(len(names)==59 and len({r["asset_name"] for r in matrows})==59,"Duplicate material identity")
    require(all(name in names for a in assets for name in a["materials"]),"Unresolved source material slot")
    textures={}
    for r in matrows:
        require(re.fullmatch(r"M_[A-Za-z0-9_]+",r["asset_name"]),"Unsafe material name")
        require(not r["glass_approximation"] or r["source_name"]=="glass","Unexpected glass recipe")
        for usage,entry in r["maps"].items():
            require(usage in ("base_color","roughness","normal") and entry["available"],"Unsupported/missing texture")
            path=file("export/"+entry["path"]);key=(entry["path"],usage)
            t=dict(path=entry["path"],usage=usage,filename=str(path),sha256=rows["export/"+entry["path"]]["sha256"],
                   asset_name=m.texture_name(*key),flip_green=bool(r["normal_flip_green"]) if usage=="normal" else False)
            require(key not in textures or textures[key]==t,"Conflicting shared texture policy");textures[key]=t
    require(len(textures)==41,"Unexpected full texture count")
    require(len(metadata["actors"])==51 and metadata["player_start_count"]==10 and metadata["light_count"]==41,"Unexpected metadata count")
    for row in metadata["actors"]:
        require(row["class"] in ("PlayerStart","PointLight","RectLight","DirectionalLight"),"Unsupported source actor")
        c._vector(row["location_cm"]);c._vector(row["rotation_pitch_yaw_roll_deg"])
        f,up=basis(row["rotation_pitch_yaw_roll_deg"])
        require(max(abs(a-b) for actual,want in ((f,row["forward_ue"]),(up,row["up_ue"])) for a,b in zip(actual,want))<1e-5,"Metadata orientation mismatch")
        if row["class"]!="PlayerStart":
            require(row["source_energy"]>=0 and all(0<=v<=1 for v in row["color_linear_rgb"]),"Invalid source light photometry")
            if row["class"]=="RectLight": require(row["area_width_cm"]>0 and row["area_shape"]=="DISK","Unexpected area-light recipe")
    ids=[p["id"] for p in placements]+["meta:"+p["source_object"] for p in metadata["actors"]]
    require(len(ids)==len(set(ids))==247,"Duplicate full actor identity")
    return c,m,dict(root=str(root),assets=assets,placements=placements,materials=matrows,textures=list(textures.values()),metadata=metadata["actors"],
                    counts=dict(COUNTS),verified_files=verified,normalized_json_files=sorted(set(normalized)),source_sha256=c.SOURCE_SHA256,
                    canonical_hulls=sum(a["collision_hulls"] for a in assets),source_limitations=metadata["limitations"]+materials["limitations"])


def _report(mode):
    return dict(schema="carnival-full-import57-v1",mode=mode,status="PENDING",mutation_started=False,partial=False,saves_performed=0,
                namespace=DEST,suggested_manual_save_path=MAP_PATH,counts=dict(COUNTS),textures=[],materials=[],meshes=[],actors=[],errors=[],
                light_policy=dict(LIGHT_POLICY),visual_pass=False,shader_compilation="NOT_VERIFIED",gameplay="NOT_VERIFIED",
                limitations=["Full import is untested in Unreal until executed and reviewed; sample success is narrower evidence.",
                "Source light placement/color/type/shadows are preserved; brightness/falloff and disk-to-square shape are approximations.",
                "41 source shadow lights and 181 meshes may be expensive. Sequential submissions do not bound engine background compilation or peak memory.",
                "Known Blender roundtrip normal caveats remain: 24 environment tiles (4,795 corners) and two pallets; raw FBX source fidelity passes but is not visual validation.",
                "No floor/support/sky/reflection capture/exposure additions. The source export excludes Blender world/fog/render-only effects.",
                "No saves, replacement, deletion, cleanup or automatic resume. Unreal's independent autosave is not changed."])


def _api(u,c,m):
    version=m.api(u,c)
    for cls,methods in {"RectLight":(),"PlayerStart":(),"RectLightComponent":("set_source_width","set_source_height","set_intensity_units","set_attenuation_radius"),
        "PointLightComponent":("set_source_radius","set_intensity_units","set_attenuation_radius"),
        "DirectionalLightComponent":("set_light_source_angle",),"Actor":("get_actor_forward_vector","get_actor_up_vector","get_actor_rotation"),
        "SystemLibrary":("get_console_variable_int_value",),"StaticMeshComponent":("set_collision_enabled","set_collision_response_to_all_channels","set_collision_response_to_channel","get_collision_enabled","get_collision_response_to_channel","is_simulating_physics")}.items():
        obj=getattr(u,cls,None);require(obj is not None,"Missing full-import API class: "+cls)
        for name in methods:require(callable(getattr(obj,name,None)),"Missing full-import API: "+cls+"."+name)
    for cls in (u.PointLightComponent,u.RectLightComponent,u.DirectionalLightComponent):
        for name in ("set_mobility","set_intensity","set_cast_shadows","set_light_color","get_light_color"):
            require(callable(getattr(cls,name,None)),"Missing light API: "+cls.__name__+"."+name)
        default=u.get_default_object(cls)
        for prop in ("mobility","intensity","cast_shadows","use_temperature","specular_scale"):
            default.get_editor_property(prop)
    u.get_default_object(u.PlayerStart).get_editor_property("player_start_tag")
    for kind,names in {"TranslucencyLightingMode":["TLM_SURFACE_PER_PIXEL_LIGHTING"],"RefractionMode":["RM_INDEX_OF_REFRACTION"],
        "BlendMode":["BLEND_TRANSLUCENT"],"MaterialProperty":["MP_OPACITY","MP_REFRACTION"],"CollisionEnabled":["NO_COLLISION","QUERY_AND_PHYSICS"],
        "CollisionResponseType":["ECR_BLOCK"],"CollisionChannel":["ECC_VISIBILITY","ECC_PAWN"]}.items():
        for name in names:c._enum(u,kind,name)
    default=u.get_default_object(u.Material)
    for prop in ("translucency_lighting_mode","refraction_method"):default.get_editor_property(prop)
    for cls,props in ((u.RectLightComponent,("source_width","source_height","intensity_units","attenuation_radius")),
                      (u.PointLightComponent,("source_radius",)),(u.DirectionalLightComponent,("light_source_angle",))):
        default=u.get_default_object(cls)
        for prop in props:default.get_editor_property(prop)
    require(u.SystemLibrary.get_console_variable_int_value("r.ForwardShading")==0,"Source RectLights require deferred rendering; forward renderer is unsupported, no settings changed")
    return version


def _guard(u,c):
    require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),"Save/discard current dirty maps yourself before full import")
    require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),"Save/discard current dirty assets yourself before full import")
    require(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is None,"Stop Play/Simulate first")
    lib=u.EditorAssetLibrary
    require(not lib.does_directory_exist(DEST) and not lib.list_assets(DEST,recursive=True,include_folder=True) and not lib.does_asset_exist(MAP_PATH),"Full-import namespace/map already exists; no overwrite/resume")
    content=Path(str(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())))
    require(content.is_absolute() and content.is_dir(),"Cannot verify physical Content directory")
    target=content/DEST.removeprefix("/Game/");require(not target.exists() and not target.is_symlink(),"Physical full-import namespace already exists")
    require(not any(TAG in [str(t) for t in a.get_editor_property("tags")] for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()),"Existing full-import actors found")


def preflight(package_root):
    r=_report("preflight")
    try:
        c,m,p=plan(package_root);r.update(source_sha256=p["source_sha256"],verified_file_count=len(p["verified_files"]),normalized_json_files=p["normalized_json_files"],canonical_hulls=p["canonical_hulls"])
        try:u=importlib.import_module("unreal")
        except ModuleNotFoundError as exc:
            if exc.name!="unreal":raise
            r["status"]="FILES_VERIFIED_ENGINE_NOT_CHECKED";return r
        r["engine_version"]=_api(u,c,m);_guard(u,c);r["status"]="FULL_PREFLIGHT_PASS"
    except Exception as exc:r.update(status="FULL_PREFLIGHT_BLOCKED",errors=[str(exc)])
    return r


def _material(u,m,record,textures,report):
    mat=m.material(u,record,textures,report)
    if record["glass_approximation"]:
        for key,value in dict(blend_mode=u.BlendMode.BLEND_TRANSLUCENT,
                translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
                refraction_method=u.RefractionMode.RM_INDEX_OF_REFRACTION).items():m.set_checked(mat,key,value)
        for value,prop,y in ((record["opacity_approximation"],u.MaterialProperty.MP_OPACITY,1200),(record["ior"],u.MaterialProperty.MP_REFRACTION,1400)):
            node=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant,-400,y);require(node is not None,"Glass expression creation failed")
            node.set_editor_property("r",float(value));require(abs(float(node.get_editor_property("r"))-value)<1e-6,"Glass value readback failed")
            require(u.MaterialEditingLibrary.connect_material_property(node,"",prop),"Glass property connection failed")
        u.MaterialEditingLibrary.recompile_material(mat)
    return mat


def _import_mesh(u,c,item,report):
    target=DEST+"/"+("Props" if item["kind"]=="props" else "Environment")+"/"+item["asset_name"]
    require(not u.EditorAssetLibrary.does_asset_exist(target),"Mesh target already exists: "+target)
    require(c._sha(Path(item["source_path"]))==item["fbx_sha256"],"FBX changed after preflight")
    task=u.AssetImportTask()
    c._set_readback(task,dict(filename=item["source_path"],destination_path=target.rsplit("/",1)[0],destination_name=item["asset_name"],factory=u.FbxFactory(),options=c._options(u),automated=True,async_=False,save=False,replace_existing=False,replace_existing_settings=False))
    row=dict(name=item["asset_name"],requested=target,status="ATTEMPTED",actual=[],task_paths=[]);report["meshes"].append(row);objects=[]
    try:u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    finally:
        try:row["task_paths"]=[str(x) for x in task.get_editor_property("imported_object_paths")]
        except Exception as exc:row["path_error"]=str(exc)
        try:objects=list(task.get_objects());row["actual"]=[x.get_path_name() for x in objects]
        except Exception as exc:row["object_error"]=str(exc)
    expected=target+"."+item["asset_name"]
    require(len(objects)==1 and isinstance(objects[0],u.StaticMesh) and row["actual"]==[expected] and row["task_paths"]==[expected],"Mesh import result identity/count mismatch")
    mesh=objects[0];data=mesh.get_editor_property("asset_import_data")
    require(isinstance(data,u.FbxStaticMeshImportData) and str(data.get_class().get_name())=="FbxStaticMeshImportData","Unexpected mesh import provenance")
    ss=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);build=ss.get_lod_build_settings(mesh,0);c._set_readback(build,c.BUILD_FIELDS);ss.set_lod_build_settings(mesh,0,build)
    body=mesh.get_editor_property("body_setup");require(body is not None,"Missing BodySetup")
    c._set_readback(body,dict(collision_trace_flag=u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX))
    row.update(c._validate_mesh(u,mesh,item));row["status"]="GEOMETRY_COLLISION_CHECKED_UNSAVED";return mesh


def _spawn_mesh(u,c,item,mesh,placement,report):
    row=dict(id=placement["id"],class_name="StaticMeshActor",status="ATTEMPTED");report["actors"].append(row)
    actor=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.StaticMeshActor,u.Vector(*placement["location_cm"]),u.Rotator(pitch=0.,yaw=0.,roll=0.),transient=False)
    require(actor is not None and str(actor.get_class().get_name())=="StaticMeshActor","Independent native StaticMeshActor required")
    row["path"]=actor.get_path_name();actor.set_actor_label(placement["source_object"])
    actor.set_editor_property("tags",[u.Name(t) for t in placement["tags"]+[TAG,"Full57Id="+placement["id"]]])
    actor.set_actor_scale3d(u.Vector(1,1,1));comp=actor.get_editor_property("static_mesh_component")
    require(comp.set_static_mesh(mesh),"Mesh component assignment failed");comp.set_simulate_physics(False)
    mode=u.CollisionEnabled.QUERY_AND_PHYSICS if item["collision_hulls"] else u.CollisionEnabled.NO_COLLISION
    comp.set_collision_enabled(mode)
    if item["collision_hulls"]:
        comp.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_BLOCK)
        comp.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY,u.CollisionResponseType.ECR_BLOCK)
    require(comp.get_editor_property("static_mesh")==mesh and max(abs(a-b) for a,b in zip(c._vec(actor.get_actor_location()),placement["location_cm"]))<.01,"Spawn identity/position mismatch")
    _check_collision(u,comp,item)
    row.update(status="PLACED_UNSAVED",mesh=mesh.get_path_name(),collision_enabled=str(mode));return actor


def _check_collision(u,comp,item):
    mode=u.CollisionEnabled.QUERY_AND_PHYSICS if item["collision_hulls"] else u.CollisionEnabled.NO_COLLISION
    require(comp.get_collision_enabled()==mode,"Actor collision mode differs")
    require(not comp.is_simulating_physics(),"Unexpected actor physics simulation")
    if item["collision_hulls"]:
        for channel in (u.CollisionChannel.ECC_VISIBILITY,u.CollisionChannel.ECC_PAWN):
            require(comp.get_collision_response_to_channel(channel)==u.CollisionResponseType.ECR_BLOCK,"Actor collision response differs")


def _radius(row):
    return max(LIGHT_POLICY["attenuation_radius_min_cm"],2.*row.get("area_width_cm",0.),2.*max(0.,row["location_cm"][2]))


def _check_metadata(u,c,actor,row):
    tags=[str(x) for x in actor.get_editor_property("tags")]
    require(all(t in tags for t in row["tags"]) and "BlenderSource:"+row["source_object"] in tags,"Metadata source tags differ")
    for actual,want in ((c._vec(actor.get_actor_forward_vector()),row["forward_ue"]),(c._vec(actor.get_actor_up_vector()),row["up_ue"])):
        require(max(abs(a-b) for a,b in zip(actual,want))<1e-4,"Metadata direction/up differs")
    if row["class"]=="PlayerStart":
        require(str(actor.get_editor_property("player_start_tag"))==row["source_object"],"PlayerStart tag differs")
        return
    comp=actor.get_component_by_class(getattr(u,row["class"]+"Component"));require(comp is not None,"Missing light component")
    expected=dict(mobility=u.ComponentMobility.MOVABLE,cast_shadows=row["use_shadow"],use_temperature=False,specular_scale=1.)
    if row["class"]=="DirectionalLight":
        expected.update(intensity=row["source_energy"]*LIGHT_POLICY["directional_lux_per_source_unit"],light_source_angle=row["source_angle_degrees"])
    else:
        expected.update(intensity=row["source_energy"]*LIGHT_POLICY["local_lumens_per_source_watt"],intensity_units=u.LightUnits.LUMENS,
                        attenuation_radius=_radius(row))
        if row["class"]=="RectLight":expected.update(source_width=row["area_width_cm"],source_height=row["area_width_cm"])
        else:expected.update(source_radius=row["source_radius_cm"],use_inverse_squared_falloff=True)
    for prop,want in expected.items():
        actual=comp.get_editor_property(prop)
        require(abs(float(actual)-want)<=max(.001,abs(want)*1e-6) if type(want)==float else actual==want,"Light property differs: "+prop)
    color=comp.get_light_color()
    require(max(abs(a-b) for a,b in zip((color.r,color.g,color.b),row["color_linear_rgb"]))<.015,"Source linear light color differs")


def _color(u,comp,rgb):
    comp.set_light_color(u.LinearColor(*rgb,1.),True)
    actual=comp.get_light_color();got=[float(actual.r),float(actual.g),float(actual.b)]
    require(max(abs(a-b) for a,b in zip(got,rgb))<.015,"Source linear light color roundtrip mismatch")
    return got


def _spawn_metadata(u,c,row,report):
    entry=dict(id="meta:"+row["source_object"],class_name=row["class"],status="ATTEMPTED");report["actors"].append(entry)
    pitch,yaw,roll=row["rotation_pitch_yaw_roll_deg"]
    actor=u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(getattr(u,row["class"]),u.Vector(*row["location_cm"]),u.Rotator(pitch=pitch,yaw=yaw,roll=roll),transient=False)
    require(actor is not None and str(actor.get_class().get_name())==row["class"],"Metadata actor class mismatch")
    entry["path"]=actor.get_path_name();actor.set_actor_label(row["source_object"])
    tags=row["tags"]+[TAG,"Full57Id="+entry["id"],"BlenderSource:"+row["source_object"]]
    actor.set_editor_property("tags",[u.Name(t) for t in tags])
    for actual,want in ((c._vec(actor.get_actor_forward_vector()),row["forward_ue"]),(c._vec(actor.get_actor_up_vector()),row["up_ue"])):
        require(max(abs(a-b) for a,b in zip(actual,want))<1e-4,"Metadata direction/up vector mismatch")
    if row["class"]=="PlayerStart":actor.set_editor_property("player_start_tag",u.Name(row["source_object"]))
    else:
        comp=actor.get_component_by_class(getattr(u,row["class"]+"Component"));require(comp is not None,"Light component missing")
        comp.set_mobility(u.ComponentMobility.MOVABLE);comp.set_editor_property("use_temperature",False);comp.set_editor_property("specular_scale",1.)
        entry["color_linear_rgb"]=_color(u,comp,row["color_linear_rgb"]);comp.set_cast_shadows(row["use_shadow"])
        if row["class"]=="DirectionalLight":
            intensity=row["source_energy"]*LIGHT_POLICY["directional_lux_per_source_unit"];comp.set_intensity(intensity);comp.set_light_source_angle(row["source_angle_degrees"])
        else:
            if row["class"]=="PointLight":comp.set_use_inverse_squared_falloff(True)
            comp.set_intensity_units(u.LightUnits.LUMENS);intensity=row["source_energy"]*LIGHT_POLICY["local_lumens_per_source_watt"]
            comp.set_intensity(intensity);comp.set_attenuation_radius(_radius(row));entry["attenuation_radius_cm"]=_radius(row)
            if row["class"]=="RectLight":comp.set_source_width(row["area_width_cm"]);comp.set_source_height(row["area_width_cm"])
            else:comp.set_source_radius(row["source_radius_cm"])
        require(abs(float(comp.get_editor_property("intensity"))-intensity)<=max(.01,intensity*1e-6),"Light intensity readback mismatch")
        require(bool(comp.get_editor_property("cast_shadows"))==row["use_shadow"],"Source shadow policy mismatch")
        entry.update(intensity=intensity,photometry="APPROXIMATE")
    _check_metadata(u,c,actor,row)
    entry["status"]="PLACED_UNSAVED";return actor


def import_full(package_root):
    """Explicit full import. Blocks dirty work/existing targets; never imports into current map."""
    r=_report("import_full")
    try:
        c,m,p=plan(package_root);u=importlib.import_module("unreal");r["engine_version"]=_api(u,c,m);_guard(u,c)
        r.update(source_sha256=p["source_sha256"],verified_file_count=len(p["verified_files"]),normalized_json_files=p["normalized_json_files"])
        # Test nonwhite color on an unowned transient component before map/asset mutation.
        probe=u.PointLightComponent();probe.set_editor_property("use_temperature",False)
        r["nonwhite_color_probe"]=_color(u,probe,[.17,.53,.83])
        c._options(u);_guard(u,c)
        old=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();r["previous_world"]=old.get_path_name() if old else None
        r.update(mutation_started=True,stage="new_blank_map")
        world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
        require(world is not None and isinstance(world,u.World) and world!=old and not world.get_path_name().startswith("/Game/"),"Fresh unsaved map creation failed")
        r["world_path"]=world.get_path_name()
        actor_system=u.get_editor_subsystem(u.EditorActorSubsystem)
        require(all(str(a.get_class().get_name()) in ("WorldSettings","Brush") for a in actor_system.get_all_level_actors()),"Fresh map contains unexpected authored actors")
        def progress(kind,index,total,name):
            require(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()==world,"Editor world changed during full import; stopping without cleanup")
            r["stage"]=kind+":"+name;u.log("[CarnivalFull57] %s %d/%d: %s"%(kind,index,total,name))
        textures={}
        for i,t in enumerate(p["textures"],1):
            progress("texture",i,41,t["asset_name"]);textures[(t["path"],t["usage"])]=m.import_texture(u,c,t,r)
        materials={}
        for i,a in enumerate(p["materials"],1):
            progress("material",i,59,a["source_name"]);materials[a["source_name"]]=_material(u,m,a,textures,r)
        meshes={};assets={a["asset_name"]:a for a in p["assets"]}
        # Exercise the new zero-hull environment case first, without changing source order.
        first_zero=next(a for a in p["assets"] if a["kind"]=="environment" and a["collision_hulls"]==0)
        mesh_order=[first_zero]+[a for a in p["assets"] if a is not first_zero]
        for i,a in enumerate(mesh_order,1):
            progress("mesh",i,181,a["asset_name"]);mesh=_import_mesh(u,c,a,r)
            for slot,name in enumerate(a["materials"]):mesh.set_material(slot,materials[name]);require(mesh.get_material(slot)==materials[name],"Full material assignment failed")
            meshes[a["asset_name"]]=mesh
        for i,pmt in enumerate(p["placements"],1):
            progress("mesh actor",i,196,pmt["source_object"]);_spawn_mesh(u,c,assets[pmt["asset_name"]],meshes[pmt["asset_name"]],pmt,r)
        for i,row in enumerate(p["metadata"],1):progress("metadata actor",i,51,row["source_object"]);_spawn_metadata(u,c,row,r)
        r["stage"]="read_only_validation";r["validation"]=_validate_current(u,c,m,p)
        require(r["validation"]["passed"],"Post-import structural validation failed: "+repr(r["validation"]["errors"]))
        r.update(status="FULL_IMPORT_CREATED_UNSAVED",partial=False,stage="complete")
        u.log("[CarnivalFull57] Created 281 assets and 247 authored actors. No save performed. Wait for compilation and review before manually saving.")
        return r
    except Exception as exc:
        if r["mutation_started"]:
            try:
                r["namespace_assets_on_failure"]=[str(x) for x in u.EditorAssetLibrary.list_assets(DEST,recursive=True,include_folder=False)]
                r["current_actor_paths_on_failure"]=[x.get_path_name() for x in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()]
            except Exception as snapshot:r["snapshot_error"]=str(snapshot)
        r.update(status="FULL_IMPORT_FAILED_PARTIAL" if r["mutation_started"] else "FULL_IMPORT_BLOCKED",partial=r["mutation_started"],errors=[str(exc)],
                 recovery="Do not rerun over partial assets/map. No cleanup or save was attempted; inspect the ledger and manually decide what to retain/discard.")
        raise FullImportError(r) from exc


def _validate_current(u,c,m,p):
    out=dict(passed=False,errors=[],checked_meshes=0,checked_materials=0,checked_textures=0,checked_actors=0,material_graph_retraversal="NOT_PERFORMED",shader_compilation="NOT_VERIFIED",visual_pass=False)
    def attempt(label,fn):
        try:fn()
        except Exception as exc:out["errors"].append(label+": "+str(exc))
    expected_assets=set();material_objects={}
    for a in p["materials"]:
        path=m.MATS+"/"+a["asset_name"];expected_assets.add(path)
        def check(a=a,path=path):
            mat=u.load_asset(path);require(isinstance(mat,u.Material),"Missing Material")
            require(mat.get_editor_property("two_sided")==a["two_sided"],"Two-sided policy differs")
            require(mat.get_editor_property("shading_model")==u.MaterialShadingModel.MSM_DEFAULT_LIT,"Shading model differs")
            require(mat.get_editor_property("blend_mode")== (u.BlendMode.BLEND_TRANSLUCENT if a["glass_approximation"] else u.BlendMode.BLEND_OPAQUE),"Blend mode differs")
            if a["glass_approximation"]:
                require(mat.get_editor_property("refraction_method")==u.RefractionMode.RM_INDEX_OF_REFRACTION and mat.get_editor_property("translucency_lighting_mode")==u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,"Glass mode differs")
            material_objects[a["source_name"]]=mat;out["checked_materials"]+=1
        attempt(path,check)
    for t in p["textures"]:
        path=m.TEX+"/"+t["asset_name"];expected_assets.add(path)
        def check(t=t,path=path):
            tex=u.load_asset(path);require(isinstance(tex,u.Texture2D),"Missing Texture2D")
            data=tex.get_editor_property("asset_import_data");require(isinstance(data,u.AssetImportData) and str(data.get_class().get_name())=="AssetImportData","Wrong texture provenance")
            files=list(data.extract_filenames());require(len(files)==1 and Path(str(files[0])).resolve()==Path(t["filename"]).resolve(),"Wrong texture source")
            compression={"base_color":u.TextureCompressionSettings.TC_DEFAULT,"normal":u.TextureCompressionSettings.TC_NORMALMAP,"roughness":u.TextureCompressionSettings.TC_MASKS}[t["usage"]]
            for key,value in dict(srgb=t["usage"]=="base_color",compression_settings=compression,flip_green_channel=t["flip_green"],virtual_texture_streaming=False).items():require(tex.get_editor_property(key)==value,"Texture setting differs: "+key)
            out["checked_textures"]+=1
        attempt(path,check)
    for a in p["assets"]:
        path=DEST+("/Props/" if a["kind"]=="props" else "/Environment/")+a["asset_name"];expected_assets.add(path)
        def check(a=a,path=path):
            mesh=u.load_asset(path);c._validate_mesh(u,mesh,a)
            for slot,name in enumerate(a["materials"]):require(name in material_objects and mesh.get_material(slot)==material_objects[name],"Material slot assignment differs")
            out["checked_meshes"]+=1
        attempt(path,check)
    actual={str(x).split(".")[0] for x in u.EditorAssetLibrary.list_assets(DEST,recursive=True,include_folder=False)}
    # The user may have manually saved the suggested map after a successful import.
    actual.discard(MAP_PATH)
    if actual!=expected_assets:out["errors"].append("Full namespace asset inventory differs from 281 expected assets")
    assets_by_name={a["asset_name"]:a for a in p["assets"]}
    actor_rows={pmt["id"]:pmt for pmt in p["placements"]}
    actor_rows.update({"meta:"+a["source_object"]:a for a in p["metadata"]});seen=set()
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        cls=str(actor.get_class().get_name())
        if cls in ("WorldSettings","Brush"):continue
        def check(actor=actor,cls=cls):
            tags=[str(x) for x in actor.get_editor_property("tags")];ids=[x.split("=",1)[1] for x in tags if x.startswith("Full57Id=")]
            require(TAG in tags and len(ids)==1 and ids[0] in actor_rows and ids[0] not in seen,"Unexpected/duplicate full actor identity")
            sid=ids[0];seen.add(sid);row=actor_rows[sid]
            require(max(abs(a-b) for a,b in zip(c._vec(actor.get_actor_location()),row["location_cm"]))<.02,"Actor position differs")
            if sid.startswith("meta:"):
                require(cls==row["class"],"Metadata class differs")
                _check_metadata(u,c,actor,row)
            else:
                require(cls=="StaticMeshActor" and all(t in tags for t in row["tags"]),"Mesh actor class/source tags differ")
                comp=actor.get_editor_property("static_mesh_component");mesh=comp.get_editor_property("static_mesh")
                expected=DEST+("/Props/" if row["kind"]=="props" else "/Environment/")+row["asset_name"]+"."+row["asset_name"]
                require(mesh is not None and mesh.get_path_name()==expected and not any(comp.get_editor_property("override_materials")),"Actor mesh/material override differs")
                require(c._vec(actor.get_actor_scale3d())==[1.,1.,1.],"Mesh actor scale differs")
                for actual_vec,want in ((c._vec(actor.get_actor_forward_vector()),[1.,0.,0.]),(c._vec(actor.get_actor_up_vector()),[0.,0.,1.])):
                    require(max(abs(a-b) for a,b in zip(actual_vec,want))<1e-5,"Baked mesh actor rotation differs")
                _check_collision(u,comp,assets_by_name[row["asset_name"]])
            out["checked_actors"]+=1
        attempt(actor.get_path_name(),check)
    if seen!=set(actor_rows):out["errors"].append("Missing full actor identities")
    out["passed"]=not out["errors"];return out


def validate(package_root):
    """Read-only structural check of the current full map, allowing dirty packages."""
    r=_report("validate")
    try:
        c,m,p=plan(package_root);u=importlib.import_module("unreal");r["engine_version"]=_api(u,c,m)
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);require(editor.get_game_world() is None,"Stop Play/Simulate before auditing")
        world=editor.get_editor_world();require(world is not None,"No editor world")
        r["world_path"]=world.get_path_name();require(not r["world_path"].startswith("/Game/") or r["world_path"].split(".")[0]==MAP_PATH,"Current map is not the full-import target")
        r["dirty_maps"]=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        r["dirty_content"]=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
        r["validation"]=_validate_current(u,c,m,p);r["status"]="FULL_STRUCTURE_PASS" if r["validation"]["passed"] else "FULL_STRUCTURE_MISMATCH"
    except Exception as exc:r.update(status="FULL_VALIDATE_BLOCKED",errors=[str(exc)])
    return r
