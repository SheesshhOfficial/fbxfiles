"""Metadata preparation for source PlayerStart empties and non-render-only lights.
Called by approved environment export; never saves/modifies the source scene.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector

def ue_rotation(forward,up):
 """UE pitch/yaw/roll for reflected forward/up unit vectors; degrees."""
 fx,fy,fz=forward;pitch=math.atan2(fz,math.hypot(fx,fy));yaw=math.atan2(fy,fx)
 right0=(-math.sin(yaw),math.cos(yaw),0)
 up0=(-math.sin(pitch)*math.cos(yaw),-math.sin(pitch)*math.sin(yaw),math.cos(pitch))
 roll=math.atan2(sum(up[i]*right0[i] for i in range(3)),sum(up[i]*up0[i] for i in range(3)))
 return [math.degrees(v) for v in (pitch,yaw,roll)]

def export_scene_metadata(root,source_path,source_hash,source_scene):
 records=[];excluded=[]
 for o in source_scene.objects:
  spawn=o.type=='EMPTY' and (o.get('UE_Class')=='PlayerStart' or o.name.startswith('PlayerStart_'))
  if not spawn and o.type!='LIGHT':continue
  if o.get('render_only') or o.get('_assembly_source') or o.get('visual_replaced') or o.hide_render or o.hide_get(view_layer=source_scene.view_layers[0]):
   excluded.append(o.name);continue
  p=o.matrix_world.translation;q=o.matrix_world.to_quaternion()
  f=q@Vector((1,0,0) if spawn else (0,0,-1));u=q@Vector((0,0,1) if spawn else (0,1,0))
  forward=[f.x,-f.y,f.z];up=[u.x,-u.y,u.z]
  r={'source_object':o.name,'source_blend':source_path.name,'location_cm':[p.x*100,-p.y*100,p.z*100],'rotation_pitch_yaw_roll_deg':ue_rotation(forward,up),'forward_ue':forward,'up_ue':up,'source_matrix_world':[list(row) for row in o.matrix_world],'class':'PlayerStart' if spawn else {'POINT':'PointLight','SPOT':'SpotLight','AREA':'RectLight','SUN':'DirectionalLight'}[o.data.type],'tags':['MoonfallSceneMetadata','MoonfallPlayerStart' if spawn else 'MoonfallSourceLight']}
  if not spawn:
   light=o.data;r.update({'source_light_type':light.type,'source_energy':light.energy,'source_energy_unit':'W/m2' if light.type=='SUN' else 'W','color_linear_rgb':list(light.color),'use_shadow':light.use_shadow,'source_radius_cm':float(getattr(light,'shadow_soft_size',0))*100,'source_angle_degrees':math.degrees(float(getattr(light,'angle',0))),'area_shape':getattr(light,'shape',None),'area_width_cm':float(getattr(light,'size',0))*100,'area_height_cm':float(getattr(light,'size_y',getattr(light,'size',0)))*100,'spot_outer_half_angle_degrees':math.degrees(float(getattr(light,'spot_size',0)))/2,'spot_blend':float(getattr(light,'spot_blend',0))})
  records.append(r)
 report={'source_blend':source_path.name,'source_sha256':source_hash,'runtime_verified':False,'actors':records,'player_start_count':sum(r['class']=='PlayerStart' for r in records),'light_count':sum(r['class']!='PlayerStart' for r in records),'excluded_source_objects':excluded,'coordinate_convention':'Position (100x,-100y,100z). Lights use reflected Blender local -Z forward/+Y up; PlayerStart uses reflected local +X forward/+Z up.','limitations':['Source energy/color/type retained exactly in metadata. Unreal photometry and exposure differ; importer numeric conversions are only adjustable starting estimates.','Area disk/ellipse converted to rectangular light approximation; spot blend mapped approximately.','Blender world, fog/volume, camera, render-only moon/haze and compositing effects excluded.','Spawn clearance, player orientation, light mobility/performance/shadows and gameplay require Unreal testing.']}
 (Path(root)/'unreal/scene_metadata.json').write_text(json.dumps(report,indent=2));return 'unreal/scene_metadata.json'
