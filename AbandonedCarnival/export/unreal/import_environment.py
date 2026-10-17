"""Unreal Editor Python helper. Import into a fresh Moonfall level by default.
Requires Python Editor Script Plugin and Editor Scripting Utilities.
API reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LevelEditorSubsystem
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/EditorLoadingAndSavingUtils
Prepared against documented UE5 Python APIs; NOT run in Unreal.
"""
import os,json
import unreal
DEFAULT_LEVEL='/Game/MoonfallCarnivalV2/Maps/MoonfallCarnival'
DEST='/Game/MoonfallCarnivalV2/Environment'

def import_environment(root=None,level_path=DEFAULT_LEVEL,create_level=True,allow_existing=False):
 root=os.path.abspath(root or os.path.dirname(__file__))
 data=json.load(open(os.path.join(root,'environment_manifest.json'),encoding='utf-8'))
 actor_subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 level_subsystem=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
 # Check all file/asset conflicts before changing the currently loaded map.
 for item in data['assets']:
  filename=os.path.normpath(os.path.join(root,'..',item['fbx']))
  if not os.path.isfile(filename):raise RuntimeError('Missing source FBX: '+filename)
  if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+item['asset_name']):
   raise RuntimeError('Environment asset already exists; choose a fresh project or review existing assets manually: '+DEST+'/'+item['asset_name'])
 if create_level:
  if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
   raise RuntimeError('Current map has unsaved changes. Save your work manually before creating the Moonfall level.')
  exists=unreal.EditorAssetLibrary.does_asset_exist(level_path)
  if exists and not allow_existing:raise RuntimeError('Level exists; refusing to overwrite or reset it: '+level_path)
  if exists:
   if not level_subsystem.load_level(level_path):raise RuntimeError('Could not load '+level_path)
  elif not level_subsystem.new_level(level_path):raise RuntimeError('Could not create '+level_path)
 else:
  # Used only by an explicit caller that already opened the requested map.
  world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
  current=world.get_path_name().split('.')[0] if world else ''
  if current!=level_path:raise RuntimeError('Current map is not the explicit target '+level_path)
 if any('MoonfallEnvironment' in [str(t) for t in a.tags] for a in actor_subsystem.get_all_level_actors()):
  raise RuntimeError('Environment actors already exist. This helper never removes or resets them.')
 materials={}
 if os.path.isfile(os.path.join(root,'material_manifest.json')):
  from import_materials import build_materials
  materials=build_materials(root)
 placed=[]
 for item in data['assets']:
  task=unreal.AssetImportTask()
  task.filename=os.path.normpath(os.path.join(root,'..',item['fbx']))
  task.destination_path=DEST;task.destination_name=item['asset_name']
  task.automated=True;task.save=True;task.replace_existing=False
  opts=unreal.FbxImportUI();opts.import_mesh=True;opts.import_as_skeletal=False
  opts.import_materials=not bool(materials);opts.import_textures=not bool(materials);opts.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
  sm=opts.static_mesh_import_data
  sm.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  sm.set_editor_property('normal_generation_method',unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
  for key,value in {'combine_meshes':True,'auto_generate_collision':False,'one_convex_hull_per_ucx':True,'convert_scene':False,'convert_scene_unit':False,'force_front_x_axis':False,'import_uniform_scale':1.0,'generate_lightmap_u_vs':True}.items():sm.set_editor_property(key,value)
  task.options=opts;unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=unreal.load_asset(DEST+'/'+item['asset_name'])
  if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('StaticMesh import failed: '+item['asset_name'])
  for index,name in enumerate(item['materials']):
   if name in materials:mesh.set_material(index,materials[name])
  if materials:unreal.EditorAssetLibrary.save_loaded_asset(mesh)
  actor=actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*item['location_cm']),unreal.Rotator(0,0,0))
  actor.set_actor_label(item['asset_name']);actor.tags=[unreal.Name('MoonfallEnvironment')]
  comp=actor.static_mesh_component;comp.set_static_mesh(mesh)
  comp.set_simulate_physics(False)
  comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS if item['ucx_hulls'] else unreal.CollisionEnabled.NO_COLLISION)
  if item['ucx_hulls']:comp.set_collision_response_to_all_channels(unreal.CollisionResponse.BLOCK)
  actor.set_actor_scale3d(unreal.Vector(1,1,1));placed.append(actor)
 unreal.log('Placed %d scenery tiles. Inspect geometry/collision/materials and save level manually.'%len(placed))
 return {'placed_environment_tiles':len(placed),'level_path':level_path,'runtime_verified':False}

if __name__=='__main__':import_environment()
