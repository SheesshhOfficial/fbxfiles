"""Full frozen carnival UE5.7.4 import into a new unsaved world/namespace.

No module-import side effects. preflight/validate are read-only. import_full is
explicit mutation. resume_full and resume_after_restart are explicit,
single-checkpoint recoveries only.
No saving, deletion, replacement, fallback or automatic resume.
"""
from __future__ import annotations
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re

DEST = "/Game/AbandonedCarnivalFull57_Corrected"
MAP_PATH = DEST + "/Maps/AbandonedCarnivalFull57"
TAG = "AbandonedCarnivalFull57_Corrected"
AXIS_ADAPTER = "counter_y_fbx7400_v1"
SENTINELS = ("SM_Env_Tile_m3_m4", "SM_OpenToolbox_20d6fff596")
# This descriptor is derived from the supplied native failure ledger. No host
# filesystem paths or log content are published. It is not a graph fingerprint.
# Projection uses compact sorted-key JSON: schema/status/namespace/world_path/
# stage/axis_sentinels_passed; created_materials(actual,source_name,status),
# created_textures(actual_objects,status,sha256), created_meshes(name,status,actual),
# inventory(namespace_assets_on_failure) and actors. No live-log authentication.
RESUME_WORLD = "/Temp/Untitled_3.Untitled"
RESUME_FAILED_MESH = "SM_TeddyPrize_7adfe5d511"
RESUME_CHECKPOINT = dict(id="native_teddy_slot_failure_20261017_220639",
    creation_ledger_projection_sha256="bd57a669a3bb5e06a0bdbd5f4b07a04d79842c03d3d326584ab333b02862565f",
    textures=41,materials=59,meshes=68,assigned_meshes=65,unassigned_meshes=3,authored_actors=0,
    source_error="Aged tan plush fabric_001 != Aged tan plush fabric.001")
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
    for asset in assets: asset["material_name_universe"]=sorted(names)
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
                namespace=DEST,suggested_manual_save_path=MAP_PATH,counts=dict(COUNTS),derived_files=[],textures=[],materials=[],meshes=[],actors=[],errors=[],
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
        "SystemLibrary":("get_console_variable_int_value",),"Paths":("project_saved_dir",),"StaticMeshComponent":("set_collision_enabled","set_collision_response_to_all_channels","set_collision_response_to_channel","get_collision_enabled","get_collision_response_to_channel","is_simulating_physics")}.items():
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
    _cache_root(u)  # Read-only path/symlink check; never creates directories.
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


# Pure, frozen-source FBX7400 adapter. No file or Unreal operations here.
"""Frozen-Carnival FBX7400 Y-reflection fallback CANDIDATE; standard library only.

No operation occurs on import. reflect_bytes() returns a derived FBX in memory.
It does not read/write assets, change original files, or claim Unreal validation.
Unknown geometry/layer schemas and nonidentity Model transforms fail closed.
All original unmodified property encodings and the entire footer are preserved.
Compression choices keep the footer at its original modulo-16 alignment.
"""
import array
from dataclasses import dataclass, field
import hashlib
import math
import struct
import sys
import zlib

_fbx_MAGIC = b'Kaydara FBX Binary  \x00\x1a\x00'
_fbx_NULL = b'\x00' * 13
_fbx_SCALARS = {'Z': ('b', 1), 'Y': ('h', 2), 'B': ('?', 1), 'C': ('c', 1),
           'I': ('i', 4), 'F': ('f', 4), 'D': ('d', 8), 'L': ('q', 8)}
_fbx_ARRAYS = {'b': ('B', 1), 'c': ('B', 1), 'i': ('i', 4), 'l': ('q', 8),
          'f': ('f', 4), 'd': ('d', 8)}
_fbx_IDENTITY = {'Lcl Translation': (0.,0.,0.), 'Lcl Rotation': (0.,0.,0.),
            'Lcl Scaling': (1.,1.,1.), 'GeometricTranslation': (0.,0.,0.),
            'GeometricRotation': (0.,0.,0.), 'GeometricScaling': (1.,1.,1.),
            'PreRotation': (0.,0.,0.), 'PostRotation': (0.,0.,0.),
            'RotationOffset': (0.,0.,0.), 'RotationPivot': (0.,0.,0.),
            'ScalingOffset': (0.,0.,0.), 'ScalingPivot': (0.,0.,0.)}


def _fbx_require(ok, message):
    if not ok:
        raise ValueError(message)


@dataclass
class _fbx_Property:
    kind: str
    encoded: bytes  # original whole property, including type byte
    payload: bytes  # uncompressed array payload, string bytes, or scalar bytes
    count: int | None = None
    encoding: int | None = None
    changed: bool = False

    def value(self):
        if self.kind in ('S', 'R'):
            return self.payload
        if self.kind in _fbx_SCALARS:
            return struct.unpack('<' + _fbx_SCALARS[self.kind][0], self.payload)[0]
        _fbx_require(self.kind in _fbx_ARRAYS, 'Unsupported property kind')
        a = array.array(_fbx_ARRAYS[self.kind][0]); a.frombytes(self.payload)
        if sys.byteorder != 'little' and a.itemsize > 1:
            a.byteswap()
        return a

    def set_array(self, values):
        _fbx_require(self.kind in _fbx_ARRAYS, 'Only arrays may be changed')
        a = array.array(_fbx_ARRAYS[self.kind][0], values)
        _fbx_require(len(a) == self.count, 'Array length change forbidden')
        if sys.byteorder != 'little' and a.itemsize > 1:
            a.byteswap()
        payload = a.tobytes()
        if payload != self.payload:
            self.payload = payload; self.changed = True
            self.encoded = self.compressed(1)

    def compressed(self, level):
        _fbx_require(self.kind in _fbx_ARRAYS, 'Compression requires array')
        data = zlib.compress(self.payload, level) if self.encoding == 1 else self.payload
        return self.kind.encode() + struct.pack('<III', self.count, self.encoding, len(data)) + data


@dataclass
class _fbx_Node:
    name: bytes
    props: list[_fbx_Property]
    children: list['Node']
    sentinel: bool


@dataclass
class _fbx_Document:
    header: bytes
    nodes: list[_fbx_Node]
    footer: bytes
    footer_offset: int


def _fbx_parse(data: bytes) -> _fbx_Document:
    _fbx_require(data[:23] == _fbx_MAGIC and len(data) >= 40, 'Not binary FBX')
    _fbx_require(struct.unpack_from('<I', data, 23)[0] == 7400, 'Only FBX7400 is supported')
    limit = len(data)
    def node_at(pos):
        _fbx_require(pos + 13 <= limit, 'Truncated FBX record')
        end, count, plen, nlen = struct.unpack_from('<IIIB', data, pos)
        _fbx_require(end and pos + 13 + nlen <= end <= limit, 'Invalid FBX record end')
        name = data[pos+13:pos+13+nlen]; cur = pos+13+nlen; pend = cur+plen
        _fbx_require(pend <= end, 'Invalid property byte count')
        props=[]
        for _ in range(count):
            start=cur; _fbx_require(cur < pend, 'Missing property type'); k=chr(data[cur]);cur+=1
            n=enc=None
            if k in _fbx_SCALARS:
                size=_fbx_SCALARS[k][1]; _fbx_require(cur+size<=pend, 'Truncated scalar')
                payload=data[cur:cur+size];cur+=size
            elif k in ('S','R'):
                _fbx_require(cur+4<=pend, 'Truncated string header');size=struct.unpack_from('<I',data,cur)[0];cur+=4
                _fbx_require(cur+size<=pend, 'Truncated string');payload=data[cur:cur+size];cur+=size
            elif k in _fbx_ARRAYS:
                _fbx_require(cur+12<=pend, 'Truncated array header');n,enc,size=struct.unpack_from('<III',data,cur);cur+=12
                _fbx_require(enc in (0,1) and cur+size<=pend, 'Unsupported/truncated array')
                packed=data[cur:cur+size];cur+=size
                if enc:
                    dec=zlib.decompressobj();payload=dec.decompress(packed);payload+=dec.flush()
                    _fbx_require(dec.eof and not dec.unused_data and not dec.unconsumed_tail, 'Invalid zlib array stream')
                else:payload=packed
                _fbx_require(len(payload)==n*_fbx_ARRAYS[k][1], 'Array payload length mismatch')
            else:raise ValueError('Unsupported FBX property type: '+repr(k))
            props.append(_fbx_Property(k,data[start:cur],payload,n,enc))
        _fbx_require(cur==pend, 'Property list length mismatch')
        children=[];sentinel=False
        while cur<end:
            if data[cur:cur+13]==_fbx_NULL:
                _fbx_require(cur+13==end, 'Misplaced nested null record');sentinel=True;cur+=13;break
            _fbx_child,cur=node_at(cur);children.append(_fbx_child)
        _fbx_require(cur==end, 'Node offset mismatch')
        _fbx_require(not children or sentinel, 'Missing child-list terminator')
        return _fbx_Node(name,props,children,sentinel),cur
    nodes=[];pos=27
    while True:
        _fbx_require(pos+13<=limit, 'Missing root terminator')
        if data[pos:pos+13]==_fbx_NULL:pos+=13;break
        n,pos=node_at(pos);nodes.append(n)
    footer=data[pos:]
    _fbx_require(len(footer)>=160, 'Missing binary footer')
    _fbx_require(footer[:16]==bytes.fromhex('fabcab09d0c8d466b176fb831cf7267e'), 'Unrecognized frozen-source footer ID')
    _fbx_require(footer[-16:]==bytes.fromhex('f85a8c6adef5d97eece90ce3758f290b'), 'Invalid footer trailer')
    _fbx_require(footer[-140:-136]==struct.pack('<I',7400) and footer[-136:-16]==b'\0'*120, 'Invalid footer version/reserved block')
    _fbx_require(footer[16:-140] and not any(footer[16:-140]), 'Nonzero footer padding')
    _fbx_require((pos+len(footer)-140)%16==0, 'Footer version alignment mismatch')
    return _fbx_Document(data[:27],nodes,footer,pos)


def _fbx_walk(nodes):
    for node in nodes:
        yield node
        yield from _fbx_walk(node.children)


def _fbx_child(node, name, optional=False):
    found=[n for n in node.children if n.name==name]
    _fbx_require(len(found)==1 or (optional and not found), 'Missing/duplicate child '+repr(name))
    return found[0] if found else None


def _fbx_single(node):
    _fbx_require(node is not None and len(node.props)==1, 'Expected single property')
    return node.props[0]


def _fbx_text_child(node,name):
    p=_fbx_single(_fbx_child(node,name));_fbx_require(p.kind=='S','Expected string property');return p.value()


def _fbx_identity_models(doc):
    objects=next((n for n in doc.nodes if n.name==b'Objects'),None)
    _fbx_require(objects is not None,'Missing Objects')
    def inspect(props_node):
        if props_node is None:return
        for p in props_node.children:
            _fbx_require(p.name==b'P' and len(p.props)>=4,'Invalid Properties70')
            key=p.props[0].value().decode('utf-8')
            if key in _fbx_IDENTITY:
                vals=tuple(x.value() for x in p.props[4:])
                _fbx_require(vals==_fbx_IDENTITY[key], 'Nonidentity Model transform '+key+': '+repr(vals))
    for n in _fbx_walk(doc.nodes):
        if n.name==b'PropertyTemplate' and n.props and n.props[0].value()==b'FbxNode':
            inspect(_fbx_child(n,b'Properties70',True))
    models={}
    for n in objects.children:
        if n.name==b'Model':
            _fbx_require(len(n.props)==3 and n.props[2].value()==b'Mesh', 'Only Mesh Models are supported')
            inspect(_fbx_child(n,b'Properties70',True));models[n.props[0].value()]=n
    connections=next((n for n in doc.nodes if n.name==b'Connections'),None)
    _fbx_require(connections is not None, 'Missing Connections')
    model_parent={}
    for c in connections.children:
        vals=[p.value() for p in c.props]
        if len(vals)==3 and vals[0]==b'OO' and vals[1] in models:
            _fbx_require(vals[1] not in model_parent,'Multiple Model parents')
            model_parent[vals[1]]=vals[2]
    _fbx_require(set(model_parent)==set(models) and all(v==0 for v in model_parent.values()),'Only root-parented identity Models are supported')
    return objects


def _fbx_reorder(prop, permutation, stride=1):
    _fbx_require(prop.kind in _fbx_ARRAYS,'Expected array')
    vals=prop.value();_fbx_require(len(vals)==len(permutation)*stride,'Corner payload cardinality mismatch')
    prop.set_array(v for old in permutation for v in vals[old*stride:(old+1)*stride])


def _fbx_reflect_vectors(prop):
    _fbx_require(prop.kind in ('d','f') and prop.count%3==0,'Expected 3D floating vectors')
    vals=prop.value();_fbx_require(all(math.isfinite(x) for x in vals),'Nonfinite vectors')
    for i in range(1,len(vals),3):vals[i]=-vals[i]
    prop.set_array(vals)


def _fbx_reflect_geometry(g):
    _fbx_require(len(g.props)==3 and g.props[2].value()==b'Mesh','Only Mesh Geometry is supported')
    allowed={b'Properties70',b'GeometryVersion',b'Vertices',b'PolygonVertexIndex',b'Edges',b'Layer',
             b'LayerElementNormal',b'LayerElementUV',b'LayerElementSmoothing',b'LayerElementColor',b'LayerElementMaterial'}
    _fbx_require(all(c.name in allowed for c in g.children),'Unsupported geometry element (including tangent/binormal)')
    pv=_fbx_single(_fbx_child(g,b'Vertices'));_fbx_reflect_vectors(pv);nverts=pv.count//3
    pp=_fbx_single(_fbx_child(g,b'PolygonVertexIndex'));_fbx_require(pp.kind=='i','Polygon indices must be int32')
    old=pp.value();_fbx_require(old and old[-1]<0,'Unterminated/empty polygon stream')
    decoded=array.array('i',(-v-1 if v<0 else v for v in old));_fbx_require(all(0<=v<nverts for v in decoded),'Vertex index outside mesh')
    perm=array.array('i');face_count=0;start=0;new=array.array('i');next_corner=array.array('i',[0])*len(old)
    for end,v in enumerate(old):
        if v<0:
            stop=end+1;_fbx_require(stop-start>=3,'Degenerate polygon schema')
            face_count+=1;reverse=range(stop-1,start-1,-1);perm.extend(reverse)
            for i in range(start,stop):next_corner[i]=i+1 if i+1<stop else start
            new.extend(decoded[i] for i in reverse);new[-1]=-new[-1]-1;start=stop
    _fbx_require(start==len(old),'Invalid final polygon')
    pp.set_array(new);inverse=array.array('i',[0])*len(old)
    for new_index,old_index in enumerate(perm):inverse[old_index]=new_index
    edges=_fbx_child(g,b'Edges',True);edge_count=0
    if edges:
        ep=_fbx_single(edges);_fbx_require(ep.kind=='i','Edges must be int32');ev=ep.value();edge_count=len(ev)
        _fbx_require(all(0<=v<len(old) for v in ev),'Invalid edge corner reference')
        ep.set_array(inverse[next_corner[v]] for v in ev)
    layer_specs={b'LayerElementNormal':(b'Normals',b'NormalsIndex',3),
                 b'LayerElementUV':(b'UV',b'UVIndex',2),
                 b'LayerElementSmoothing':(b'Smoothing',b'SmoothingIndex',1),
                 b'LayerElementColor':(b'Colors',b'ColorIndex',4)}
    mappings={b'ByPolygonVertex':len(old),b'ByVertice':nverts,b'ByVertex':nverts,
              b'ByPolygon':face_count,b'AllSame':1,b'ByEdge':edge_count}
    layer_ids=set()
    for l in [x for x in g.children if x.name.startswith(b'LayerElement')]:
        _fbx_require(len(l.props)==1 and l.props[0].kind=='I','Invalid layer identifier')
        lid=(l.name,l.props[0].value());_fbx_require(lid not in layer_ids,'Duplicate layer');layer_ids.add(lid)
        mapping=_fbx_text_child(l,b'MappingInformationType');reference=_fbx_text_child(l,b'ReferenceInformationType')
        _fbx_require(mapping in mappings,'Unsupported mapping '+repr(mapping));_fbx_require(reference in (b'Direct',b'IndexToDirect'),'Unsupported reference '+repr(reference))
        count=mappings[mapping];base={b'Version',b'Name',b'MappingInformationType',b'ReferenceInformationType'}
        if l.name==b'LayerElementMaterial':
            _fbx_require(reference==b'IndexToDirect' and mapping in (b'ByPolygon',b'AllSame'),'Unsupported material schema')
            _fbx_require(all(x.name in base|{b'Materials'} for x in l.children),'Unknown material property')
            mp=_fbx_single(_fbx_child(l,b'Materials'));_fbx_require(mp.kind=='i' and mp.count==count,'Material cardinality mismatch')
            continue
        data_name,index_name,stride=layer_specs[l.name]
        _fbx_require(all(x.name in base|{data_name,index_name} for x in l.children),'Unknown layer property')
        dp=_fbx_single(_fbx_child(l,data_name));_fbx_require(dp.kind in _fbx_ARRAYS and dp.count%stride==0,'Malformed layer data')
        if l.name in (b'LayerElementNormal',b'LayerElementUV',b'LayerElementColor'):
            _fbx_require(dp.kind in ('d','f'),'Expected floating layer data')
        ip_node=_fbx_child(l,index_name,True)
        if reference==b'Direct':
            _fbx_require(ip_node is None and dp.count==count*stride,'Direct layer cardinality/index mismatch')
            if mapping==b'ByPolygonVertex':_fbx_reorder(dp,perm,stride)
        else:
            _fbx_require(ip_node is not None,'Missing layer index array');ip=_fbx_single(ip_node)
            _fbx_require(ip.kind=='i' and ip.count==count,'Indexed layer cardinality mismatch')
            _fbx_require(all(0<=i<dp.count//stride for i in ip.value()),'Layer index outside data array')
            if mapping==b'ByPolygonVertex':_fbx_reorder(ip,perm)
        if l.name==b'LayerElementNormal':_fbx_reflect_vectors(dp)
    for layer in [x for x in g.children if x.name==b'Layer']:
        _fbx_require(all(x.name in (b'Version',b'LayerElement') for x in layer.children),'Unknown Layer child')
        for ref in [x for x in layer.children if x.name==b'LayerElement']:
            pair=(_fbx_text_child(ref,b'Type'),_fbx_single(_fbx_child(ref,b'TypedIndex')).value())
            _fbx_require(pair in layer_ids,'Layer reference to unsupported/missing element')
    return {'vertices':nverts,'polygons':face_count,'corners':len(old),'edges':edge_count}


def _fbx_node_size(node):
    return 13+len(node.name)+sum(len(p.encoded) for p in node.props)+sum(_fbx_node_size(c) for c in node.children)+(13 if node.sentinel else 0)


def _fbx_footer_alignment(doc):
    """Use valid deterministic zlib levels, never padding inside compressed streams.

    The original footer includes alignment padding. Choose equivalent compressed
    encodings whose combined lengths preserve its original absolute alignment.
    Fail rather than alter any footer byte if no choice can achieve that.
    """
    offset=27+sum(_fbx_node_size(n) for n in doc.nodes)+13
    needed=(doc.footer_offset-offset)%16
    if needed==0:return 0
    candidates=[p for n in _fbx_walk(doc.nodes) for p in n.props if p.changed and p.encoding==1]
    candidates.sort(key=lambda p:len(p.payload))  # stable traversal breaks ties
    states={0:[]};options=[]
    for p in candidates:
        base_len=len(p.encoded);variants={0:p.encoded}
        for level in range(10):
            encoded=p.compressed(level);variants.setdefault((len(encoded)-base_len)%16,encoded)
        options.append((p,variants));index=len(options)-1;new=dict(states)
        for residue,choices in states.items():
            for delta in sorted(variants):new.setdefault((residue+delta)%16,choices+[(index,delta)])
        states=new
        if needed in states:
            for index,delta in states[needed]:
                prop,variants=options[index];prop.encoded=variants[delta]
            _fbx_require((27+sum(_fbx_node_size(n) for n in doc.nodes)+13-doc.footer_offset)%16==0,'Internal footer alignment failure')
            return len(states[needed])
    raise ValueError('Cannot preserve exact footer alignment with valid compressed-array encodings')


def _fbx_encode(doc):
    _fbx_footer_alignment(doc)
    out=bytearray(doc.header)
    def emit(n):
        start=len(out);pbytes=b''.join(p.encoded for p in n.props);out.extend(b'\0'*13);out.extend(n.name);out.extend(pbytes)
        for c in n.children:emit(c)
        if n.sentinel:out.extend(_fbx_NULL)
        _fbx_require(len(out)<2**32,'FBX7400 offset overflow')
        struct.pack_into('<IIIB',out,start,len(out),len(n.props),len(pbytes),len(n.name))
    for n in doc.nodes:emit(n)
    out.extend(_fbx_NULL);_fbx_require((len(out)-doc.footer_offset)%16==0,'Footer alignment moved');out.extend(doc.footer)
    return bytes(out)


def _fbx_decoded_digest(doc):
    """Bit-exact decoded semantic digest, including types, order and footer.

    Excludes only node byte offsets and compressed representations of arrays.
    Signed zero is distinguished; every original scalar/string byte is included.
    """
    h=hashlib.sha256();h.update(doc.header)
    def piece(b):h.update(struct.pack('<Q',len(b)));h.update(b)
    def emit(n):
        piece(n.name);h.update(bytes([n.sentinel]));h.update(struct.pack('<II',len(n.props),len(n.children)))
        for p in n.props:
            piece(p.kind.encode());piece(p.payload)
            if p.kind in _fbx_ARRAYS:h.update(struct.pack('<II',p.count,p.encoding))
        for c in n.children:emit(c)
    for n in doc.nodes:emit(n)
    piece(doc.footer);return h.hexdigest()


def _fbx_reflect_bytes(data):
    doc=_fbx_parse(data);objects=_fbx_identity_models(doc);stats=[]
    for g in objects.children:
        if g.name==b'Geometry':stats.append(_fbx_reflect_geometry(g))
    _fbx_require(stats,'No geometry')
    result=_fbx_encode(doc)
    check=_fbx_parse(result);_fbx_require(check.footer==doc.footer,'Footer changed')
    _fbx_require(_fbx_decoded_digest(check)==_fbx_decoded_digest(doc),'Encoder decoded-payload mismatch')
    return result,{'geometry_count':len(stats),'vertices':sum(x['vertices'] for x in stats),
                   'polygons':sum(x['polygons'] for x in stats),'corners':sum(x['corners'] for x in stats),
                   'source_sha256':hashlib.sha256(data).hexdigest(),'derived_sha256':hashlib.sha256(result).hexdigest(),
                   'source_bytes':len(data),'derived_bytes':len(result),'footer_preserved_exact':True,
                   'unreal_import_tested':False}


def _counterreflect_fbx(raw):
    return _fbx_reflect_bytes(raw)


def _cache_root(u):
    saved=Path(str(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir())))
    require(saved.is_absolute() and saved.is_dir() and not saved.is_symlink(),"Cannot verify project Saved directory")
    path=saved/"CarnivalFull57Derived"/AXIS_ADAPTER
    for part in (saved/"CarnivalFull57Derived",path):
        require(not part.is_symlink() and (not part.exists() or part.is_dir()),"Unsafe derived FBX cache directory")
    return path


def _derived_source(u,c,item,report=None,write=False):
    """Verify original bytes; derive reproducibly. Only explicit import may write new cache files."""
    source=Path(item["source_path"]);raw=source.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==item["fbx_sha256"],"Original FBX changed before counter-conversion")
    derived,proof=_counterreflect_fbx(raw)
    digest=hashlib.sha256(derived).hexdigest()
    directory=_cache_root(u)/item["fbx_sha256"]
    require(not directory.is_symlink() and (not directory.exists() or directory.is_dir()),"Unsafe derived source directory")
    path=directory/(item["asset_name"]+".fbx");meta=directory/(item["asset_name"]+".json")
    metadata=dict(adapter=AXIS_ADAPTER,asset_name=item["asset_name"],original_sha256=item["fbx_sha256"],
                  derived_sha256=digest,derived_bytes=len(derived),proof=proof)
    encoded=(json.dumps(metadata,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf-8")
    row=dict(original_source_path=str(source),original_fbx_sha256=item["fbx_sha256"],source_path=str(path),
             derived_fbx_sha256=digest,metadata_path=str(meta),status="VERIFIED_EXISTING" if path.exists() else "PENDING",files_written=[])
    if report is not None:report["derived_files"].append(row)
    for dest,expected in ((path,derived),(meta,encoded)):
        require(not dest.is_symlink(),"Refusing symlink in derived source cache")
        if dest.exists():
            require(dest.is_file() and dest.read_bytes()==expected,"Existing derived cache differs; no overwrite: "+str(dest))
        else:
            require(write,"Derived import source missing; read-only validation will not recreate it: "+str(dest))
            directory.mkdir(parents=True,exist_ok=True)
            row["status"]="WRITING_NEW_CACHE"
            with dest.open("xb") as stream:
                row["files_written"].append(str(dest));stream.write(expected)
            require(dest.read_bytes()==expected,"Derived source write verification failed")
    row["status"]="DERIVED_SOURCE_VERIFIED"
    result=dict(item,source_path=str(path),fbx_sha256=digest,original_source_path=str(source),
                original_fbx_sha256=item["fbx_sha256"],derived_fbx_sha256=digest)
    return result


def _slot_aliases(source):
    """Only source text and two explicit, source-derived legacy FBX spellings."""
    return {source,source.replace(".","_"),re.sub(r"[^A-Za-z0-9_]","_",source)}


def _check_slot_names(actual,sources,universe=None):
    require(len(actual)==len(sources),"Material-slot count mismatch")
    owners={}
    for source in set(sources)|set(universe or ()):
        for alias in _slot_aliases(source): owners.setdefault(alias,set()).add(source)
    for got,want in zip(actual,sources):
        require(got in _slot_aliases(want),"Imported material-slot name/order mismatch: "+got+" != "+want)
        require(owners[got]=={want},"Ambiguous imported material-slot alias collision: "+got)


def _validate_mesh(u,c,mesh,item):
    """Extend only slot-name compatibility; retain every frozen geometry validator."""
    require(isinstance(mesh,u.StaticMesh),"Expected StaticMesh: "+item["asset_name"])
    slots=mesh.get_editor_property("static_materials")
    names=[str(slot.get_editor_property("imported_material_slot_name")) for slot in slots]
    _check_slot_names(names,item["materials"],item.get("material_name_universe"))
    # The original vendor now sees the already strictly verified actual spelling.
    # No mesh/slot/source metadata is changed, and all its other gates still run.
    result=c._validate_mesh(u,mesh,dict(item,materials=names))
    result["source_materials"]=list(item["materials"])
    result["slot_name_policy"]="ORDERED_UNAMBIGUOUS_SOURCE_DOT_OR_LEGACY_ASCII"
    return result


def _import_mesh(u,c,item,report):
    target=DEST+"/"+("Props" if item["kind"]=="props" else "Environment")+"/"+item["asset_name"]
    require(not u.EditorAssetLibrary.does_asset_exist(target),"Mesh target already exists: "+target)
    item=_derived_source(u,c,item,report,write=True)
    require(c._sha(Path(item["source_path"]))==item["fbx_sha256"],"Derived FBX changed after verification")
    task=u.AssetImportTask()
    c._set_readback(task,dict(filename=item["source_path"],destination_path=target.rsplit("/",1)[0],destination_name=item["asset_name"],factory=u.FbxFactory(),options=c._options(u),automated=True,async_=False,save=False,replace_existing=False,replace_existing_settings=False))
    row=dict(name=item["asset_name"],requested=target,status="ATTEMPTED",actual=[],task_paths=[],original_source_path=item["original_source_path"],original_fbx_sha256=item["original_fbx_sha256"],derived_source_path=item["source_path"],derived_fbx_sha256=item["derived_fbx_sha256"]);report["meshes"].append(row);objects=[]
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
    row.update(_validate_mesh(u,c,mesh,item))
    if item["asset_name"] in SENTINELS:row["signed_geometry_probe"]=_signed_landmark_probe(u,c,mesh,item)
    row["status"]="GEOMETRY_COLLISION_CHECKED_UNSAVED";return mesh


def _signed_landmark_probe(u,c,mesh,item):
    """Optional read-only MeshDescription evidence; unsupported bindings are reported.

    Bounds/UV/UCX validation remains mandatory. If these documented getters are
    available, a signed-position mismatch is a hard failure, never normalized.
    """
    if not callable(getattr(mesh,"get_static_mesh_description",None)) or not hasattr(u,"VertexID"):
        return dict(status="UNAVAILABLE",reason="MeshDescription/VertexID Python binding absent")
    try:
        desc=mesh.get_static_mesh_description(0)
        require(desc is not None,"No LOD0 MeshDescription")
        for name in ("get_vertex_count","is_vertex_valid","get_vertex_position"):
            require(callable(getattr(desc,name,None)),"Missing MeshDescription getter: "+name)
        count=desc.get_vertex_count();require(0<count<=10000000,"Invalid MeshDescription vertex count")
        # Freshly imported MeshDescriptions normally have dense IDs. Do not guess across holes.
        ids=[u.VertexID(id_value=i) for i in range(count)]
        require(all(desc.is_vertex_valid(i) for i in ids),"Non-dense vertex IDs; optional probe cannot enumerate safely")
    except Exception as exc:return dict(status="UNAVAILABLE",reason=str(exc))
    doc=_fbx_parse(Path(item["original_source_path"]).read_bytes())
    objects=next(n for n in doc.nodes if n.name==b"Objects")
    geo=next(n for n in objects.children if n.name==b"Geometry" and n.props[1].value().split(b"\x00")[0].decode()==item["asset_name"])
    verts=_fbx_single(_fbx_child(geo,b"Vertices")).value()
    indices=_fbx_single(_fbx_child(geo,b"PolygonVertexIndex")).value()
    used=sorted({-v-1 if v<0 else v for v in indices})
    chosen={used[0]}
    for axis in range(3):
        chosen.add(min(used,key=lambda i:verts[i*3+axis]));chosen.add(max(used,key=lambda i:verts[i*3+axis]))
    landmarks=[[float(v) for v in verts[i*3:i*3+3]] for i in sorted(chosen)]
    best=[float("inf")]*len(landmarks)
    for vid in ids:
        position=c._vec(desc.get_vertex_position(vid))
        for k,want in enumerate(landmarks):best[k]=min(best[k],max(abs(a-b) for a,b in zip(position,want)))
    require(max(best)<=.05,"Signed MeshDescription landmark mismatch: "+item["asset_name"]+": "+repr(best))
    return dict(status="SIGNED_LANDMARKS_PASS",source_landmarks_cm=landmarks,max_error_cm=max(best),mesh_description_vertices=count)


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
        meshes={};assets={a["asset_name"]:a for a in p["assets"]}
        for i,name in enumerate(SENTINELS,1):
            progress("axis sentinel",i,len(SENTINELS),name)
            meshes[name]=_import_mesh(u,c,assets[name],r)
        r["axis_sentinels_passed"]=list(SENTINELS)
        textures={}
        for i,t in enumerate(p["textures"],1):
            progress("texture",i,41,t["asset_name"]);textures[(t["path"],t["usage"])]=m.import_texture(u,c,t,r)
        materials={}
        for i,a in enumerate(p["materials"],1):
            progress("material",i,59,a["source_name"]);materials[a["source_name"]]=_material(u,m,a,textures,r)
        for i,a in enumerate(p["assets"],1):
            progress("mesh",i,181,a["asset_name"])
            mesh=meshes.get(a["asset_name"])
            if mesh is None:mesh=_import_mesh(u,c,a,r)
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


def _asset_path(item):
    return DEST+("/Props/" if item["kind"]=="props" else "/Environment/")+item["asset_name"]


def _object_path(path):
    return path+"."+path.rsplit("/",1)[1]


def _check_reused_material(u,m,record):
    path=m.MATS+"/"+record["asset_name"];mat=u.load_asset(path)
    require(isinstance(mat,u.Material) and mat.get_path_name()==_object_path(path),"Reused material identity/type differs: "+path)
    expected=dict(two_sided=record["two_sided"],shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,
                  blend_mode=u.BlendMode.BLEND_TRANSLUCENT if record["glass_approximation"] else u.BlendMode.BLEND_OPAQUE)
    if record["glass_approximation"]:
        expected.update(refraction_method=u.RefractionMode.RM_INDEX_OF_REFRACTION,
                        translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    for key,value in expected.items():require(mat.get_editor_property(key)==value,"Reused material setting differs: "+path+": "+key)
    return mat


def _check_reused_texture(u,c,m,record):
    path=m.TEX+"/"+record["asset_name"];tex=u.load_asset(path)
    require(isinstance(tex,u.Texture2D) and tex.get_path_name()==_object_path(path),"Reused texture identity/type differs: "+path)
    require(c._sha(Path(record["filename"]))==record["sha256"],"Reused texture source hash differs")
    data=tex.get_editor_property("asset_import_data")
    require(isinstance(data,u.AssetImportData) and str(data.get_class().get_name())=="AssetImportData","Reused texture importer provenance differs")
    files=list(data.extract_filenames())
    require(len(files)==1 and Path(str(files[0])).resolve()==Path(record["filename"]).resolve(),"Reused texture source path differs")
    compression={"base_color":u.TextureCompressionSettings.TC_DEFAULT,"normal":u.TextureCompressionSettings.TC_NORMALMAP,"roughness":u.TextureCompressionSettings.TC_MASKS}[record["usage"]]
    for key,value in dict(srgb=record["usage"]=="base_color",compression_settings=compression,
                          flip_green_channel=record["flip_green"],virtual_texture_streaming=False).items():
        require(tex.get_editor_property(key)==value,"Reused texture setting differs: "+path+": "+key)
    return tex


def _resume_inventory(p,m):
    failed=[i for i,a in enumerate(p["assets"]) if a["asset_name"]==RESUME_FAILED_MESH]
    require(failed==[65],"Pinned recovery mesh order differs")
    assigned={a["asset_name"] for a in p["assets"][:65]}
    pending=set(SENTINELS)|{RESUME_FAILED_MESH}
    names=assigned|pending;require(len(assigned)==65 and len(names)==68,"Recovery checkpoint mesh count differs")
    meshes={a["asset_name"]:a for a in p["assets"] if a["asset_name"] in names}
    require(len(meshes)==68,"Recovery checkpoint mesh missing from source")
    paths={_asset_path(a) for a in meshes.values()}
    paths.update(m.TEX+"/"+t["asset_name"] for t in p["textures"])
    paths.update(m.MATS+"/"+a["asset_name"] for a in p["materials"])
    require(len(paths)==168,"Recovery checkpoint asset count differs")
    return meshes,assigned,pending,paths


def _resume_physical_guard(u,paths,require_saved=False):
    """Reject unregistered on-disk targets and every owned-namespace symlink."""
    content=Path(str(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())))
    require(content.is_absolute() and content.is_dir() and not content.is_symlink(),"Cannot verify physical Content directory for resume")
    name=DEST.removeprefix("/Game/")
    roots=[x for x in content.iterdir() if x.name.casefold()==name.casefold()]
    require(len(roots)<=1,"Ambiguous physical namespace case variants")
    if not roots:
        require(not require_saved,"Saved checkpoint .uasset files are missing")
        return dict(files_checked=0,saved_packages_checked=0)
    root=roots[0];require(not root.is_symlink() and root.is_dir(),"Unsafe physical resume namespace")
    allowed={x.casefold() for x in paths};pending=[root];count=0;saved=set()
    while pending:
        directory=pending.pop()
        for child in directory.iterdir():
            require(not child.is_symlink(),"Symlink in physical resume namespace: "+str(child))
            if child.is_dir():pending.append(child);continue
            require(child.is_file(),"Unexpected non-file in physical resume namespace")
            package=DEST+"/"+child.relative_to(root).with_suffix("").as_posix()
            require(child.suffix.casefold() in (".uasset",".uexp",".ubulk") and package.casefold() in allowed,
                    "Unregistered or unexpected physical asset target blocks resume: "+str(child))
            if child.suffix.casefold()==".uasset":
                require(package.casefold() not in saved,"Duplicate physical checkpoint package case variants")
                require(child.stat().st_size>0,"Empty physical checkpoint .uasset file")
                saved.add(package.casefold())
            count+=1
    require(not require_saved or saved==allowed,"Saved checkpoint .uasset files are missing")
    return dict(files_checked=count,saved_packages_checked=len(saved))


def _checkpoint_state(u,c,m,p,require_saved=False):
    """Read-only validation common to both explicit checkpoint recoveries."""
    items,assigned,pending,paths=_resume_inventory(p,m)
    actual=[str(x) for x in u.EditorAssetLibrary.list_assets(DEST,recursive=True,include_folder=False)]
    require(len(actual)==168 and set(actual)=={_object_path(x) for x in paths},
            "Resume namespace inventory differs from the exact 168-asset checkpoint")
    _cache_root(u);physical=_resume_physical_guard(u,paths,require_saved=require_saved)
    materials={a["source_name"]:_check_reused_material(u,m,a) for a in p["materials"]}
    textures={(t["path"],t["usage"]):_check_reused_texture(u,c,m,t) for t in p["textures"]}
    default=u.load_asset("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial")
    require(isinstance(default,u.MaterialInterface),"Cannot verify native default material")
    meshes={};checks=[]
    for name,item in items.items():
        u.log("[CarnivalFull57] Verify reused mesh %d/68: %s"%(len(meshes)+1,name))
        path=_asset_path(item);mesh=u.load_asset(path)
        require(isinstance(mesh,u.StaticMesh) and mesh.get_path_name()==_object_path(path),"Reused mesh identity/type differs: "+name)
        derived=_derived_source(u,c,item,write=False);checked=_validate_mesh(u,c,mesh,derived)
        if name in SENTINELS:checked["signed_geometry_probe"]=_signed_landmark_probe(u,c,mesh,derived)
        for slot,source in enumerate(item["materials"]):
            current=mesh.get_material(slot)
            if name in assigned:require(current==materials[source],"Completed mesh material assignment differs: "+name)
            else:require(current is None or current==default,"Unexpected material on unassigned checkpoint mesh: "+name)
        checked["assignment_state"]="VERIFIED_COMPLETED" if name in assigned else "VERIFIED_NATIVE_DEFAULTS"
        checks.append(checked);meshes[name]=mesh
    return dict(meshes=meshes,materials=materials,textures=textures,assigned=assigned,pending=pending,
                checks=checks,default=default,physical=physical)


def _resume_guard(u,c,m,p):
    """Read-only, single known checkpoint. No generic resume/repair/replacement."""
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    require(editor.get_game_world() is None,"Stop Play/Simulate before resume")
    world=editor.get_editor_world()
    require(world is not None and isinstance(world,u.World) and world.get_path_name()==RESUME_WORLD,
            "Resume requires the same empty failure world "+RESUME_WORLD)
    actors=list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
    require(all(str(a.get_class().get_name()) in ("WorldSettings","Brush") for a in actors),
            "Resume requires zero authored actors; no actor-stage resume is supported")
    items,assigned,pending,paths=_resume_inventory(p,m)
    actual=[str(x) for x in u.EditorAssetLibrary.list_assets(DEST,recursive=True,include_folder=False)]
    require(len(actual)==168 and set(actual)=={_object_path(x) for x in paths},
            "Resume namespace inventory differs from the exact 168-asset checkpoint")
    dirty_maps=[str(x.get_path_name()) for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    dirty_content=[str(x.get_path_name()) for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    require(all(x==RESUME_WORLD.split(".")[0] for x in dirty_maps),"Unrelated dirty map blocks resume")
    require(all(x in paths for x in dirty_content),"Unrelated dirty content blocks resume")
    state=_checkpoint_state(u,c,m,p)
    state.update(world=world,dirty_maps=dirty_maps,dirty_content=dirty_content)
    return state


def _restart_editor_guard(u):
    """Require a clean editor before leaving its current map; never save it."""
    require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),"Save/discard dirty maps yourself before restart recovery")
    require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),"Save/discard dirty content yourself before restart recovery")
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    require(editor.get_game_world() is None,"Stop Play/Simulate before restart recovery")
    world=editor.get_editor_world()
    require(world is not None and isinstance(world,u.World),"No valid current editor world for restart recovery")
    require(not world.get_path_name().split(".")[0].startswith(DEST+"/"),"Current map belongs to the full-import namespace; inspect it before restart recovery")
    require(callable(getattr(u.Actor,"get_components_by_class",None)),"Missing Actor.get_components_by_class for restart checkpoint guard")
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        tags=[str(t) for t in actor.get_editor_property("tags")]
        require(TAG not in tags and not any(t.startswith("Full57Id=") for t in tags),"Existing full-import actor blocks restart recovery")
        for component in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=component.get_editor_property("static_mesh")
            require(mesh is None or not mesh.get_path_name().startswith(DEST+"/"),"Current map contains a checkpoint mesh actor; inspect it before restart recovery")
    return world


def _restart_guard(u,c,m,p):
    world=_restart_editor_guard(u)
    state=_checkpoint_state(u,c,m,p,require_saved=True)
    state.update(world=world,dirty_maps=[],dirty_content=[])
    return state


def resume_full(package_root):
    """EXPLICIT recovery only for the unchanged, empty, 168-asset Teddy checkpoint.

    Rechecks every reusable asset before mutation. Preserves existing material
    graphs without claiming graph retraversal or a visual/shader pass. Never
    creates a new map, recreates existing assets, saves, deletes or overwrites.
    A different/advanced partial checkpoint is blocked and requires review.
    """
    return _run_resume(package_root,restart=False)


def resume_after_restart(package_root):
    """EXPLICIT recovery of the exact saved 168-asset checkpoint after restart.

    All existing assets, sources, caches, settings and assignments are checked
    before creating a fresh unsaved blank map. The previous clean map is not
    modified or saved by this helper. Existing material graphs are preserved.
    Dirty work, missing saved assets, differing inventory or any unsafe target
    blocks recovery before map/asset mutation. No saving/deletion/overwrite.
    """
    return _run_resume(package_root,restart=True)


def _run_resume(package_root,restart):
    mode="resume_after_restart" if restart else "resume_full"
    status_prefix="FULL_RESTART_RESUME" if restart else "FULL_RESUME"
    r=_report(mode);r["resume_checkpoint"]=dict(RESUME_CHECKPOINT)
    r["material_graph_retraversal"]="NOT_PERFORMED_EXISTING_GRAPHS_PRESERVED"
    r["material_graph_evidence"]="Original native construction ledger completed 59 graphs; current graph contents are not independently fingerprinted."
    r["reused_assets"]=[];r["completed_assignment_changes"]=[]
    try:
        c,m,p=plan(package_root);u=importlib.import_module("unreal");r["engine_version"]=_api(u,c,m)
        r.update(source_sha256=p["source_sha256"],verified_file_count=len(p["verified_files"]),normalized_json_files=p["normalized_json_files"])
        c._options(u);state=(_restart_guard if restart else _resume_guard)(u,c,m,p);world=state["world"]
        if restart:
            r["previous_world"]=world.get_path_name()
            # Validation may load/compile assets. Recheck clean work and world
            # identity immediately before the only map switch in this recovery.
            require(_restart_editor_guard(u)==world,"Editor world changed during restart checkpoint validation")
            r.update(mutation_started=True,stage="new_blank_map")
            fresh=u.EditorLoadingAndSavingUtils.new_blank_map(False)
            require(fresh is not None and isinstance(fresh,u.World) and fresh!=world and
                    not fresh.get_path_name().startswith("/Game/") and
                    u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()==fresh,
                    "Fresh unsaved restart-recovery map creation failed")
            world=fresh
            require(all(str(a.get_class().get_name()) in ("WorldSettings","Brush")
                        for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()),
                    "Fresh restart-recovery map contains unexpected authored actors")
        r.update(world_path=world.get_path_name(),reused_mesh_checks=state["checks"],dirty_maps=state["dirty_maps"],dirty_content=state["dirty_content"],physical_namespace_check=state["physical"])
        r["reused_assets"]=[x.get_path_name() for group in (state["meshes"],state["materials"],state["textures"]) for x in group.values()]
        meshes=state["meshes"];materials=state["materials"];assets={a["asset_name"]:a for a in p["assets"]}
        def progress(kind,index,total,name):
            require(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()==world,"Editor world changed during resume; stopping without cleanup")
            r["stage"]=kind+":"+name;u.log("[CarnivalFull57] %s %d/%d: %s"%(kind,index,total,name))
        missing=[a for a in p["assets"] if a["asset_name"] not in meshes]
        require(len(missing)==113,"Recovery missing-mesh count differs")
        # All reusable assets and assignments passed before the first mutation.
        for i,a in enumerate(missing,1):
            progress("resume missing mesh",i,113,a["asset_name"]);r["mutation_started"]=True
            mesh=_import_mesh(u,c,a,r)
            for slot,source in enumerate(a["materials"]):
                mesh.set_material(slot,materials[source]);require(mesh.get_material(slot)==materials[source],"New mesh material assignment failed")
            meshes[a["asset_name"]]=mesh
        for i,name in enumerate(sorted(state["pending"]),1):
            progress("complete pending assignments",i,3,name);mesh=meshes[name]
            entry=dict(name=name,status="ATTEMPTED",slots=[]);r["completed_assignment_changes"].append(entry)
            for slot,source in enumerate(assets[name]["materials"]):
                before=mesh.get_material(slot)
                require(before is None or before==state["default"],"Pending mesh material changed during resume: "+name)
                entry["slots"].append(dict(slot=slot,previous=before.get_path_name() if before else None,target=materials[source].get_path_name()))
                mesh.set_material(slot,materials[source]);require(mesh.get_material(slot)==materials[source],"Pending mesh material assignment failed")
            entry["status"]="ASSIGNED_UNSAVED"
        for i,pmt in enumerate(p["placements"],1):
            progress("mesh actor",i,196,pmt["source_object"]);_spawn_mesh(u,c,assets[pmt["asset_name"]],meshes[pmt["asset_name"]],pmt,r)
        for i,row in enumerate(p["metadata"],1):progress("metadata actor",i,51,row["source_object"]);_spawn_metadata(u,c,row,r)
        r["stage"]="read_only_validation";r["validation"]=_validate_current(u,c,m,p)
        require(r["validation"]["passed"],"Post-resume structural validation failed: "+repr(r["validation"]["errors"]))
        r.update(status=status_prefix+"_CREATED_UNSAVED",partial=False,stage="complete")
        u.log("[CarnivalFull57] Resume complete: reused 168 assets, created 113 meshes and 247 actors. No save performed.")
        return r
    except Exception as exc:
        if r["mutation_started"]:
            try:
                r["namespace_assets_on_failure"]=[str(x) for x in u.EditorAssetLibrary.list_assets(DEST,recursive=True,include_folder=False)]
                r["current_actor_paths_on_failure"]=[x.get_path_name() for x in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()]
            except Exception as snapshot:r["snapshot_error"]=str(snapshot)
        r.update(status=status_prefix+"_FAILED_PARTIAL" if r["mutation_started"] else status_prefix+"_BLOCKED",partial=r["mutation_started"],errors=[str(exc)],
                 recovery="No save, deletion, replacement or cleanup was attempted. Preserve this state and report the ledger; do not retry a different partial checkpoint.")
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
            mesh=u.load_asset(path);derived=_derived_source(u,c,a,write=False);_validate_mesh(u,c,mesh,derived)
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
