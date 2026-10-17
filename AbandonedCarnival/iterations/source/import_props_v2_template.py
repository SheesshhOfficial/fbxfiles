"""Unreal Editor Python. Review configuration, then run in a NEW empty test level.
Requires Python Editor Script Plugin / Editor Scripting Utilities. Not runtime-tested. Prepared art-pass materials are assigned by source slot order;
when material_manifest.json is absent, checkpoint FBX material import is retained.
"""
import unreal,json,os

def import_props(root=None):
 ROOT=root or os.path.dirname(os.path.abspath(__file__))
 DEST='/Game/MoonfallCarnivalV2/Props'
 data=json.load(open(os.path.join(ROOT,'prop_placements.json')))
 # Prevent accidental duplicate placement on a repeat run; this script never deletes actors.
 actor_subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 if any('MoonfallV2ImportedProp' in [str(t) for t in a.tags] for a in actor_subsystem.get_all_level_actors()):
  raise RuntimeError('Moonfall props already exist in this level. Use a new empty level or remove them explicitly before re-running.')
 for item in data['assets']:
  if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+item['asset_name']):
   raise RuntimeError('Prop asset already exists; inspect it manually before retrying: '+DEST+'/'+item['asset_name'])
 # Art-pass manifests share original Blender material-slot names with scenery.
 materials={}
 manifest_path=os.path.join(ROOT,'material_manifest.json')
 use_prepared_materials=os.path.isfile(manifest_path)
 if use_prepared_materials:
  with open(manifest_path,encoding='utf-8') as f:material_data=json.load(f)
  if data.get('source_blend_sha256') and material_data.get('source_sha256') and data['source_blend_sha256']!=material_data['source_sha256']:
   raise RuntimeError('Prop and material manifests come from different Blender sources. Export both from the same approved source.')
  records={r['source_name']:r for r in material_data['materials']}
  needed={name for item in data['assets'] for name in item['materials']}
  missing=needed-set(records)
  if missing:raise RuntimeError('Missing prepared material definitions: '+repr(sorted(str(n) for n in missing)))
  for name in needed:
   mat=unreal.load_asset('/Game/MoonfallCarnivalV2/Materials/'+records[name]['asset_name'])
   if mat is not None:
    if not isinstance(mat,unreal.MaterialInterface):raise RuntimeError('Prepared asset is not a material: '+name)
    materials[name]=mat
  if materials and set(materials)!=needed:
   raise RuntimeError('Only some prepared materials exist. Inspect the partial import before retrying; existing assets will not be overwritten.')
  if not materials and needed:
   from import_materials import build_materials
   materials=build_materials(ROOT)
  if any(name not in materials for name in needed):raise RuntimeError('Prepared materials could not be resolved for all prop slots.')
 assets={}
 for item in data['assets']:
  task=unreal.AssetImportTask();task.filename=os.path.join(ROOT,item['fbx']);task.destination_path=DEST;task.destination_name=item['asset_name'];task.automated=True;task.save=True;task.replace_existing=False
  opts=unreal.FbxImportUI();opts.import_mesh=True;opts.import_as_skeletal=False;opts.import_materials=not use_prepared_materials;opts.import_textures=not use_prepared_materials;opts.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
  sm=opts.static_mesh_import_data
  sm.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  sm.set_editor_property('normal_generation_method',unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
  sm.set_editor_property('combine_meshes',True)
  sm.set_editor_property('auto_generate_collision',False)
  sm.set_editor_property('one_convex_hull_per_ucx',True)
  sm.set_editor_property('convert_scene',False)
  sm.set_editor_property('convert_scene_unit',False)
  sm.set_editor_property('force_front_x_axis',False)
  sm.set_editor_property('import_uniform_scale',1.0)
  task.options=opts
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=unreal.load_asset(DEST+'/'+item['asset_name'])
  if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing static mesh '+item['asset_name'])
  if use_prepared_materials:
   if len(mesh.get_editor_property('static_materials'))!=len(item['materials']):raise RuntimeError('Imported material-slot count differs from source manifest: '+item['asset_name'])
   for index,name in enumerate(item['materials']):mesh.set_material(index,materials[name])
   unreal.EditorAssetLibrary.save_loaded_asset(mesh)
  assets[item['asset_name']]=mesh
 for p in data['placements']:
  actor=actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*p['location_cm']),unreal.Rotator(0,0,0))
  actor.set_actor_label(p['source_object']);actor.tags=[unreal.Name('PropActor'),unreal.Name('MoonfallV2ImportedProp')]
  comp=actor.static_mesh_component;comp.set_static_mesh(assets[p['asset_name']])
  comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
  comp.set_collision_response_to_all_channels(unreal.CollisionResponse.BLOCK)
  comp.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY,unreal.CollisionResponse.BLOCK)
  comp.set_simulate_physics(False)
  actor.set_actor_scale3d(unreal.Vector(1,1,1))
 print('Placed %d independent StaticMeshActors. Inspect and save the test level manually.' % len(data['placements']))
 return {"placed_props":len(data["placements"]),"canonical_assets":len(data["assets"])}

if __name__ == "__main__":
 import_props()
