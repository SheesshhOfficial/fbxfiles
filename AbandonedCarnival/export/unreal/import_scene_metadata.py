"""Place prepared starts/lights into the explicit Moonfall map; Unreal untested.
No deletion, reset or automatic map save. Light conversion is approximate.
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/LocalLightComponent
"""
import unreal,json,os
DEFAULT_LEVEL='/Game/MoonfallCarnivalV2/Maps/MoonfallCarnival'

def import_scene_metadata(root=None,level_path=DEFAULT_LEVEL,local_lumens_per_blender_watt=100.0,directional_lux_per_blender_unit=1.0,attenuation_radius_cm=1200.0):
 root=os.path.abspath(root or os.path.dirname(__file__))
 with open(os.path.join(root,'scene_metadata.json'),encoding='utf-8') as f:data=json.load(f)
 world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
 if not world or world.get_path_name().split('.')[0]!=level_path:raise RuntimeError('Refusing placement outside explicit Moonfall target map: '+level_path)
 actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
 if any('MoonfallSceneMetadata' in [str(t) for t in a.tags] for a in actors.get_all_level_actors()):raise RuntimeError('Metadata actors already exist; no actors will be deleted or duplicated.')
 if data['player_start_count']!=10:raise RuntimeError('Expected exactly ten source PlayerStarts; review metadata before placement.')
 count=0
 classes={'PlayerStart':unreal.PlayerStart,'PointLight':unreal.PointLight,'SpotLight':unreal.SpotLight,'RectLight':unreal.RectLight,'DirectionalLight':unreal.DirectionalLight}
 for r in data['actors']:
  actor=actors.spawn_actor_from_class(classes[r['class']],unreal.Vector(*r['location_cm']),unreal.Rotator(*r['rotation_pitch_yaw_roll_deg']))
  actor.set_actor_label(r['source_object'])
  tags=r['tags']+['BlenderSource:'+r['source_object'],'SourceBlend:'+r['source_blend']]
  if r['class']=='PlayerStart':actor.set_editor_property('player_start_tag',unreal.Name(r['source_object']))
  else:
   comp=actor.get_component_by_class(unreal.LightComponent)
   comp.set_mobility(unreal.ComponentMobility.MOVABLE)
   comp.set_light_color(unreal.LinearColor(*r['color_linear_rgb'],1.0),False)
   comp.set_cast_shadows(r['use_shadow'])
   if r['class']=='DirectionalLight':
    comp.set_intensity(r['source_energy']*directional_lux_per_blender_unit)
    comp.set_editor_property('light_source_angle',r['source_angle_degrees'])
   else:
    comp.set_intensity_units(unreal.LightUnits.LUMENS)
    comp.set_intensity(r['source_energy']*local_lumens_per_blender_watt)
    comp.set_attenuation_radius(attenuation_radius_cm)
    if r['class']=='RectLight':
     comp.set_source_width(max(1,r['area_width_cm']))
     height=r['area_height_cm'] if r['area_shape'] in ['RECTANGLE','ELLIPSE'] else r['area_width_cm']
     comp.set_source_height(max(1,height))
    else:comp.set_source_radius(r['source_radius_cm'])
    if r['class']=='SpotLight':
     outer=min(89.0,max(.1,r['spot_outer_half_angle_degrees']))
     comp.set_outer_cone_angle(outer);comp.set_inner_cone_angle(outer*(1-r['spot_blend']))
   tags+=['BlenderLightType:'+r['source_light_type'],'SourceEnergy:'+str(r['source_energy'])+r['source_energy_unit'],'ApproximateUEPhotometry']
  actor.tags=[unreal.Name(t) for t in tags];count+=1
 unreal.log_warning('Placed source starts/lights with approximate photometry. Tune exposure, intensity, falloff and shadows in Unreal; no runtime validation performed.')
 return {'placed':count,'player_starts':data['player_start_count'],'lights':data['light_count'],'runtime_verified':False}
