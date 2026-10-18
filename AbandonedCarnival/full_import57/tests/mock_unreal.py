"""Standalone Unreal-shaped test doubles; not Unreal runtime evidence.

Configure with fake_engine(contract, core). No frozen production file is edited.
"""
import copy
from pathlib import Path
import tempfile
import types

c = None


class Obj:
    def __init__(self, **properties):
        self.props = properties
        self.path = "/Transient/Mock"
    def get_editor_property(self, key):
        if key not in self.props:
            raise AttributeError(key)
        return self.props[key]
    def set_editor_property(self, key, value):
        self.props[key] = value
    def get_path_name(self):
        return self.path
    def get_class(self):
        return types.SimpleNamespace(get_name=lambda: type(self).__name__)


class Vector:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z
    def __eq__(self, other):
        return isinstance(other, Vector) and vars(self) == vars(other)


class Rotator:
    def __init__(self, roll=0, pitch=0, yaw=0):
        self.roll, self.pitch, self.yaw = roll, pitch, yaw
    def __eq__(self, other):
        return isinstance(other, Rotator) and vars(self) == vars(other)


class MaterialInterface(Obj):
    pass


class BodySetup(Obj):
    def __init__(self, hulls=0):
        super().__init__(agg_geom=Obj(**{k: [Obj() for _ in range(hulls)] if k == "convex_elems" else []
                                        for k in ("convex_elems",) + c.OTHER_SHAPES}),
                         collision_trace_flag="SIMPLE_AND_COMPLEX")


class FbxStaticMeshImportData(Obj):
    def __init__(self):
        super().__init__(**dict(c.FBX_FIELDS, normal_import_method="IMPORT_NORMALS", normal_generation_method="MIKK",
                                import_translation=Vector(), import_rotation=Rotator(),
                                coordinate_system_policy="MATCH_UP_FORWARD_AXES", using_luf_coordinate_sysem=False))
        self.filename = ""
    def extract_filenames(self):
        return [self.filename]


class FbxImportUI(Obj):
    def __init__(self):
        super().__init__(static_mesh_import_data=FbxStaticMeshImportData(),
             **{k: None for k in ("import_mesh", "import_as_skeletal", "import_animations", "import_materials",
                "import_textures", "automated_import_should_detect_type", "mesh_type_to_import", "original_import_type", "override_full_name")})


class FbxFactory(Obj):
    pass


class AssetImportTask(Obj):
    def __init__(self):
        super().__init__(**{k: None for k in ("filename", "destination_path", "destination_name", "automated", "async_", "save",
                  "replace_existing", "replace_existing_settings", "factory", "options", "imported_object_paths")})
        self.objects = []
    def get_objects(self):
        return self.objects


class StaticMesh(Obj):
    def __init__(self, item, data):
        super().__init__(asset_import_data=data, body_setup=BodySetup(item["collision_hulls"]),
             static_materials=[Obj(imported_material_slot_name=name) for name in item["materials"]])
        self.item = item
        self.path = c.MESH_FOLDER + "/" + item["asset_name"] + "." + item["asset_name"]
        self.build = Obj(**c.BUILD_FIELDS)
        self.materials = [None] * len(item["materials"])
        self.material_set_calls = []
        self.uv = 1
    def get_bounds(self):
        lo, hi = self.item["bounds_cm"]["min"], self.item["bounds_cm"]["max"]
        return types.SimpleNamespace(origin=Vector(*[(a+b)/2 for a,b in zip(lo,hi)]),
                                     box_extent=Vector(*[(b-a)/2 for a,b in zip(lo,hi)]))
    def set_material(self, index, material):
        if hasattr(self, 'events'): self.events.append('assign_material')
        self.material_set_calls.append((index, material))
        self.materials[index] = material
    def get_material(self, index):
        return self.materials[index]


class StaticMeshComponent(Obj):
    def __init__(self):
        super().__init__(static_mesh=None, override_materials=[])
    def set_static_mesh(self, mesh):
        self.props["static_mesh"] = mesh
        return True
    def set_simulate_physics(self, value):
        self.props["simulate_physics"] = value


class StaticMeshActor(Obj):
    def __init__(self, location=None):
        super().__init__(tags=[], static_mesh_component=StaticMeshComponent())
        self.location = location or Vector()
        self.scale = Vector(1, 1, 1)
    def set_actor_label(self, value):
        self.label = value
    def set_actor_scale3d(self, value):
        self.scale = value
    def get_actor_location(self):
        return self.location
    def get_actor_scale3d(self):
        return self.scale


class World(Obj):
    pass


def fake_engine(contract, core):
    global c
    c = core
    u = types.ModuleType("unreal")
    u.events, u.assets, u.actors = [], {}, []
    u.dirty_maps, u.dirty_content = [], []
    u.version = "5.7.4-12345+++UE5+Release-5.7"
    u.existing_namespace = False
    u.import_mutator = None
    u.default_material = MaterialInterface()
    u.default_material.path = "/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial"
    u.world_grid_material = MaterialInterface()
    u.world_grid_material.path = "/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial"
    u.engine_materials = {material.path: material for material in (u.default_material, u.world_grid_material)}
    u.world = World()
    u.world.path = "/Game/Previous.Previous"
    u.game_world = None
    u.content_dir = tempfile.mkdtemp(prefix="calibration57-fake-content-")
    u.saved_dir = tempfile.mkdtemp(prefix="full57-fake-saved-")
    for cls in (Obj, Vector, Rotator, MaterialInterface, BodySetup, FbxStaticMeshImportData,
                FbxImportUI, FbxFactory, AssetImportTask, StaticMesh, StaticMeshComponent, StaticMeshActor, World):
        setattr(u, cls.__name__, cls)
    u.Name = str
    u.FBXImportType = types.SimpleNamespace(FBXIT_STATIC_MESH="STATIC")
    u.FBXNormalImportMethod = types.SimpleNamespace(FBXNIM_IMPORT_NORMALS="IMPORT_NORMALS")
    u.FBXNormalGenerationMethod = types.SimpleNamespace(MIKK_T_SPACE="MIKK")
    u.CollisionTraceFlag = types.SimpleNamespace(CTF_USE_SIMPLE_AND_COMPLEX="SIMPLE_AND_COMPLEX",
            CTF_USE_DEFAULT="DEFAULT", CTF_USE_SIMPLE_AS_COMPLEX="SIMPLE_AS_COMPLEX", CTF_USE_COMPLEX_AS_SIMPLE="COMPLEX_AS_SIMPLE")
    class SystemLibrary:
        @staticmethod
        def get_engine_version(): return u.version
    class Paths:
        @staticmethod
        def project_content_dir(): return u.content_dir
        @staticmethod
        def project_saved_dir(): return u.saved_dir
        @staticmethod
        def convert_relative_path_to_full(path): return str(Path(path).resolve())
    class Loading:
        @staticmethod
        def get_dirty_map_packages(): return u.dirty_maps
        @staticmethod
        def get_dirty_content_packages(): return u.dirty_content
        @staticmethod
        def new_blank_map(save_existing_map):
            assert save_existing_map is False
            u.events.append("new_blank_map")
            u.world = World()
            u.world.path = "/Temp/Untitled.Untitled"
            u.actors = []
            return u.world
    class Library:
        @staticmethod
        def does_directory_exist(path): return u.existing_namespace
        @staticmethod
        def does_asset_exist(path): return path in u.assets
        @staticmethod
        def list_assets(path, **kwargs): return list(u.assets)
    class EditorActorSubsystem:
        def get_all_level_actors(self): return list(u.actors)
        def spawn_actor_from_class(self, cls, location, rotation, transient=False):
            u.events.append("spawn_actor")
            actor = cls(location)
            actor.path = u.world.path + ":Actor" + str(len(u.actors))
            u.actors.append(actor)
            return actor
    class UnrealEditorSubsystem:
        def get_editor_world(self): return u.world
        def get_game_world(self): return u.game_world
    class StaticMeshEditorSubsystem:
        def get_num_uv_channels(self, mesh, index): return mesh.uv
        def get_simple_collision_count(self, mesh): return 0
        def get_convex_collision_count(self, mesh): return len(mesh.props["body_setup"].props["agg_geom"].props["convex_elems"])
        def get_lod_build_settings(self, mesh, index): return mesh.build
        def set_lod_build_settings(self, mesh, index, build):
            u.events.append("set_build")
            mesh.build = build
    class AssetTools:
        def import_asset_tasks(self, tasks):
            assert len(tasks) == 1
            task = tasks[0]
            u.events.append("import_asset")
            assert task.props["save"] is False
            assert task.props["replace_existing"] is False
            assert task.props["replace_existing_settings"] is False
            assert isinstance(task.props["factory"], FbxFactory)
            opts = task.props["options"]
            assert opts.props["automated_import_should_detect_type"] is False
            assert opts.props["import_materials"] is False and opts.props["import_textures"] is False
            item = next(i for i in contract["selected"] if i["asset_name"] == task.props["destination_name"])
            data = copy.deepcopy(opts.props["static_mesh_import_data"])
            data.filename = task.props["filename"]
            mesh = StaticMesh(copy.deepcopy(item), data)
            mesh.path = task.props["destination_path"] + "/" + item["asset_name"] + "." + item["asset_name"]
            if u.import_mutator:
                u.import_mutator(mesh)
            task.objects = [mesh]
            task.props["imported_object_paths"] = [mesh.path]
            u.assets[mesh.path.split(".")[0]] = mesh
    tool = AssetTools()
    class Helpers:
        @staticmethod
        def get_asset_tools(): return tool
    for name, cls in dict(SystemLibrary=SystemLibrary, Paths=Paths, EditorLoadingAndSavingUtils=Loading,
         EditorAssetLibrary=Library, EditorActorSubsystem=EditorActorSubsystem, UnrealEditorSubsystem=UnrealEditorSubsystem,
         StaticMeshEditorSubsystem=StaticMeshEditorSubsystem, AssetToolsHelpers=Helpers).items():
        setattr(u, name, cls)
    u.get_default_object = lambda cls: cls()
    u.get_editor_subsystem = lambda cls: cls()
    u.load_asset = lambda path: u.engine_materials.get(path)
    return u


class AssetImportData(Obj):
    def __init__(self, filename=''):
        super().__init__()
        self.filename = filename
    def extract_filenames(self): return [self.filename]

class InterchangeAssetImportData(AssetImportData): pass

class TextureFactory(Obj):
    def __init__(self):
        super().__init__(create_material=False, edit_after_new=False, defer_compression=False,
                         compression_settings='DEFAULT', flip_normal_map_green_channel=False)

class Texture2D(Obj):
    def __init__(self):
        super().__init__(asset_import_data=AssetImportData(), srgb=True, compression_settings='DEFAULT',
                         flip_green_channel=False, virtual_texture_streaming=False)
        self.ignore_virtual_setter = False
    def set_virtual_texture_streaming(self, value):
        if not self.ignore_virtual_setter: self.props['virtual_texture_streaming'] = value

class Material(MaterialInterface):
    def __init__(self):
        super().__init__(two_sided=False, blend_mode='OPAQUE', shading_model='LIT', translucency_lighting_mode='PER_PIXEL', refraction_method='IOR')
        self.expressions = []
        self.property_inputs = {}

class MaterialFactoryNew(Obj): pass
class MaterialExpressionTextureSample(Obj): pass
class MaterialExpressionTextureCoordinate(Obj): pass
class MaterialExpressionConstant(Obj): pass
class MaterialExpressionConstant3Vector(Obj): pass
class MaterialExpressionMultiply(Obj): pass

class LinearColor:
    def __init__(self, r=0, g=0, b=0, a=1): self.r,self.g,self.b,self.a=r,g,b,a
    def __eq__(self, other): return isinstance(other, LinearColor) and vars(self)==vars(other)

class PointLightComponent(Obj):
    def __init__(self):
        super().__init__(intensity_units='LUMENS', attenuation_radius=1000., cast_shadows=True,
                         use_temperature=False, specular_scale=1., intensity=0.,
                         use_inverse_squared_falloff=True, light_color=LinearColor(1,1,1), mobility='MOVABLE', source_radius=0., light_source_angle=0.)
    def set_use_inverse_squared_falloff(self, value): self.props['use_inverse_squared_falloff']=value
    def set_intensity(self, value): self.props['intensity']=value
    def set_light_color(self, value, srgb): self.props['light_color']=value
    def set_mobility(self, value): self.props['mobility']=value

class DirectionalLightComponent(PointLightComponent): pass

class DirectionalLight(StaticMeshActor):
    component_class=DirectionalLightComponent
    def __init__(self, location=None):
        super().__init__(location)
        self.light_component=self.component_class()
    def get_component_by_class(self, cls): return self.light_component if isinstance(self.light_component,cls) else None

class PointLight(DirectionalLight): component_class=PointLightComponent


# Full-map additions. All state changes are confined to the fake engine.
class RectLightComponent(PointLightComponent):
    def __init__(self):
        super().__init__(); self.props.update(source_width=0.,source_height=0.,source_radius=0.)
    def set_source_width(self,value): self.props['source_width']=value
    def set_source_height(self,value): self.props['source_height']=value
class SpotLightComponent(PointLightComponent):
    def __init__(self):
        super().__init__(); self.props.update(inner_cone_angle=0.,outer_cone_angle=0.,source_radius=0.)
    def set_inner_cone_angle(self,value): self.props['inner_cone_angle']=value
    def set_outer_cone_angle(self,value): self.props['outer_cone_angle']=value
class RectLight(DirectionalLight): component_class=RectLightComponent
class SpotLight(DirectionalLight): component_class=SpotLightComponent
class PlayerStart(StaticMeshActor):
    def __init__(self, location=None):
        super().__init__(location);self.props['player_start_tag']=''
class Transform:
    def __init__(self,location=None,rotation=None,scale=None):
        self.translation=location or Vector();self.rotation=rotation or Rotator();self.scale3d=scale or Vector(1,1,1)

def _component_set_mobility(self,value): self.props['mobility']=value
def _component_set_profile(self,value,update_overlaps=True): self.props['collision_profile_name']=value
def _component_set_enabled(self,value): self.props['collision_enabled']=value
def _component_set_all_responses(self,value): self.props['responses']={'all':value}
def _component_set_response(self,channel,value): self.props.setdefault('responses',{})[channel]=value
def _component_get_response(self,channel): return self.props.get('responses',{}).get(channel,self.props.get('responses',{}).get('all'))
def _component_set_object(self,value): self.props['collision_object_type']=value
def _component_get_enabled(self): return self.props.get('collision_enabled')
StaticMeshComponent.set_mobility=_component_set_mobility
StaticMeshComponent.set_collision_profile_name=_component_set_profile
StaticMeshComponent.set_collision_enabled=_component_set_enabled
StaticMeshComponent.set_collision_response_to_all_channels=_component_set_all_responses
StaticMeshComponent.set_collision_response_to_channel=_component_set_response
StaticMeshComponent.set_collision_object_type=_component_set_object
StaticMeshComponent.get_collision_enabled=_component_get_enabled
StaticMeshComponent.get_collision_response_to_channel=_component_get_response
Obj.get_name=lambda self:self.get_path_name().split('.')[-1]
StaticMeshActor.get_actor_label=lambda self:getattr(self,'label','')
StaticMeshActor.get_actor_rotation=lambda self:getattr(self,'rotation',Rotator())
StaticMeshActor.set_actor_rotation=lambda self,rotation,teleport_physics=False:setattr(self,'rotation',rotation) or True
StaticMeshActor.get_actor_transform=lambda self:Transform(location=self.location,rotation=self.get_actor_rotation(),scale=self.scale)
StaticMeshActor.get_component_by_class=lambda self,cls:self.props['static_mesh_component'] if isinstance(self.props['static_mesh_component'],cls) else None
def _actor_components_by_class(self, cls):
    components = self.props.get('components', [self.props['static_mesh_component']])
    return [component for component in components if isinstance(component, cls)]
StaticMeshActor.get_components_by_class = _actor_components_by_class
PointLightComponent.get_light_color=lambda self:self.props['light_color']
PointLightComponent.set_attenuation_radius=lambda self,value:self.props.__setitem__('attenuation_radius',value)
PointLightComponent.set_source_radius=lambda self,value:self.props.__setitem__('source_radius',value)

def _direction(self,up=False):
    import math
    r=self.get_actor_rotation();p,y,roll=[math.radians(v) for v in (r.pitch,r.yaw,r.roll)]
    cp,sp,cy,sy,cr,sr=math.cos(p),math.sin(p),math.cos(y),math.sin(y),math.cos(roll),math.sin(roll)
    return Vector(-(cr*sp*cy+sr*sy),cy*sr-cr*sp*sy,cr*cp) if up else Vector(cp*cy,cp*sy,sp)
StaticMeshActor.get_actor_forward_vector=lambda self:_direction(self)
StaticMeshActor.get_actor_up_vector=lambda self:_direction(self,True)


def full_engine(plan, core):
    u=fake_engine({'selected':plan['assets']},core)
    u.import_mutator=None;u.texture_mutator=None;u.spawn_mutator=None;u.raise_after_import=False
    u.spawn_records=[];u.import_tasks=[];u.logs=[];u.log=lambda message:u.logs.append(message)
    u.Actor=StaticMeshActor;u.forward_renderer=0
    u.SystemLibrary.get_console_variable_int_value=lambda name:u.forward_renderer
    for cls in (AssetImportData,TextureFactory,Texture2D,Material,MaterialFactoryNew,
                MaterialExpressionTextureSample,MaterialExpressionTextureCoordinate,
                MaterialExpressionConstant,MaterialExpressionConstant3Vector,MaterialExpressionMultiply,
                PointLightComponent,DirectionalLightComponent,RectLightComponent,SpotLightComponent,
                DirectionalLight,PointLight,RectLight,SpotLight,PlayerStart,LinearColor,Transform):
        setattr(u,cls.__name__,cls)
    enums={
        'TextureCompressionSettings':{'TC_DEFAULT':'DEFAULT','TC_NORMALMAP':'NORMAL','TC_MASKS':'MASKS'},
        'MaterialSamplerType':{'SAMPLERTYPE_COLOR':'COLOR','SAMPLERTYPE_NORMAL':'NORMAL','SAMPLERTYPE_MASKS':'MASKS'},
        'MaterialProperty':{key:key for key in ('MP_BASE_COLOR','MP_ROUGHNESS','MP_NORMAL','MP_METALLIC','MP_EMISSIVE_COLOR','MP_OPACITY','MP_REFRACTION')},
        'BlendMode':{'BLEND_OPAQUE':'OPAQUE','BLEND_TRANSLUCENT':'TRANSLUCENT'},
        'MaterialShadingModel':{'MSM_DEFAULT_LIT':'LIT'},
        'ComponentMobility':{'MOVABLE':'MOVABLE','STATIC':'STATIC'},
        'LightUnits':{'LUMENS':'LUMENS','CANDELAS':'CANDELAS'},
        'CollisionEnabled':{'NO_COLLISION':'NONE','QUERY_AND_PHYSICS':'QUERY_AND_PHYSICS'},
        'CollisionChannel':{'ECC_WORLD_STATIC':'WORLD_STATIC','ECC_PAWN':'PAWN','ECC_VISIBILITY':'VISIBILITY'},
        'CollisionResponseType':{'ECR_BLOCK':'BLOCK','ECR_IGNORE':'IGNORE'},
        'TranslucencyLightingMode':{'TLM_SURFACE':'SURFACE','TLM_SURFACE_PER_PIXEL_LIGHTING':'PER_PIXEL'},
        'RefractionMode':{'RM_INDEX_OF_REFRACTION':'IOR'},
    }
    for kind,values in enums.items():setattr(u,kind,types.SimpleNamespace(**values))
    class Library:
        @staticmethod
        def does_directory_exist(path):return u.existing_namespace
        @staticmethod
        def does_asset_exist(path):return path.split('.')[0] in u.assets
        @staticmethod
        def list_assets(path,**kwargs):return [asset.get_path_name() for key,asset in u.assets.items() if key.startswith(path+'/')]
    u.EditorAssetLibrary=Library
    u.load_asset=lambda path:u.engine_materials.get(path) if path.startswith('/Engine/') else u.assets.get(path.split('.')[0])
    class Tools:
        def import_asset_tasks(self,tasks):
            assert len(tasks)==1,'Imports must be sequential'
            task=tasks[0];v=task.props;u.import_tasks.append(task)
            assert v['save'] is False and v['async_'] is False
            assert v['replace_existing'] is False and v['replace_existing_settings'] is False
            if isinstance(v['factory'],TextureFactory):
                u.events.append('import_texture');obj=Texture2D();obj.props['asset_import_data']=AssetImportData(v['filename'])
                mutate=u.texture_mutator
            else:
                assert isinstance(v['factory'],FbxFactory)
                u.events.append('import_mesh')
                item=next(row for row in plan['assets'] if row['asset_name']==v['destination_name'])
                data=copy.deepcopy(v['options'].props['static_mesh_import_data']);data.filename=v['filename']
                obj=StaticMesh(copy.deepcopy(item),data);obj.events=u.events;mutate=u.import_mutator
            obj.path=v['destination_path']+'/'+v['destination_name']+'.'+v['destination_name']
            if mutate:mutate(obj)
            task.objects=[obj];task.props['imported_object_paths']=[obj.path];u.assets[obj.path.split('.')[0]]=obj
            if u.raise_after_import:raise RuntimeError('injected import failure after creation')
        def create_asset(self,name,folder,cls,factory):
            assert cls is Material and isinstance(factory,MaterialFactoryNew)
            obj=Material();obj.path=folder+'/'+name+'.'+name
            u.events.append('create_material');u.assets[obj.path.split('.')[0]]=obj;return obj
    tool=Tools();u.AssetToolsHelpers=types.SimpleNamespace(get_asset_tools=lambda:tool)
    class MaterialEditingLibrary:
        @staticmethod
        def create_material_expression(material,cls,x,y):
            node=cls();node.material=material;node.inputs={}
            node.path=material.path+':Expression'+str(len(material.expressions))
            material.expressions.append(node)
            u.events.append('create_material_expression')
            return node
        @staticmethod
        def connect_material_property(expression,output,prop):
            expression.material.property_inputs[prop]=(expression,output)
            u.events.append('connect_material_property')
            return True
        @staticmethod
        def connect_material_expressions(source,output,target,input_name):
            assert source.material is target.material
            target.inputs[input_name]=(source,output)
            u.events.append('connect_material_expressions')
            return True
        @staticmethod
        def recompile_material(material):u.events.append('request_shader_compile')
        @staticmethod
        def get_num_material_expressions(material):return len(material.expressions)
        @staticmethod
        def get_used_textures(material):
            # A deterministic construction graph double; not compiled UE evidence.
            return list(dict.fromkeys(node.props['texture'] for node in material.expressions
                                      if isinstance(node,MaterialExpressionTextureSample) and node.props.get('texture') is not None))
    u.MaterialEditingLibrary=MaterialEditingLibrary
    class Actors:
        def get_all_level_actors(self):return list(u.actors)
        def spawn_actor_from_class(self,cls,location,rotation=None,transient=False):
            actor=cls(location);actor.rotation=rotation or Rotator();actor.path=u.world.path+':Actor'+str(len(u.actors))
            u.events.append('spawn_actor');u.actors.append(actor)
            u.spawn_records.append(dict(actor=actor,cls=cls,location=location,rotation=actor.rotation,transient=transient))
            if u.spawn_mutator:u.spawn_mutator(actor)
            return actor
        def set_actor_transform(self,actor,transform):
            actor.location=transform.translation;actor.rotation=transform.rotation;actor.scale=transform.scale3d;return True
    u.EditorActorSubsystem=Actors;u.get_editor_subsystem=lambda cls:cls()
    return u

PointLightComponent.set_intensity_units=lambda self,value:self.props.__setitem__('intensity_units',value)
PointLightComponent.set_cast_shadows=lambda self,value:self.props.__setitem__('cast_shadows',value)
DirectionalLightComponent.set_light_source_angle=lambda self,value:self.props.__setitem__('light_source_angle',value)

StaticMeshComponent.is_simulating_physics=lambda self:bool(self.props.get('simulate_physics',False))
