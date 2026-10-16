import bpy, os
from mathutils import Vector
root=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(root,'EVERGREEN_LAYOUT_BLOCKOUT_v1.blend'))
old=[17.0,21.4,25.8,30.2,34.6,39.0,43.4,47.0]
new=[17+i*30/7 for i in range(8)]
for obj in bpy.data.objects:
 if obj.type=='MESH' and (obj.name.startswith('Shelf ') or obj.name.startswith('Oak end panel') or obj.name.startswith('Abstract package group')) and 14 <= obj.location.y <= 36 and 16 <= obj.location.x <= 48:
  idx=min(range(8),key=lambda k:abs(obj.location.x-old[k])); obj.location.x+=new[idx]-old[idx]
for obj in bpy.data.collections['06_OVERLAYS'].objects:
 if obj.type=='FONT':obj.data.extrude=0
scene=bpy.context.scene;scene['secondary_aisle_clear_m']=round(30/7-1.6,4)
cam=bpy.data.objects['Interior aisle approval'];cam.location.x=(new[2]+new[3])/2;cam.rotation_euler=(Vector((cam.location.x,39,1.7))-cam.location).to_track_quat('-Z','Y').to_euler()
for cam_name,filename in [('Aerial layout approval','EVERGREEN_BLOCKOUT_AERIAL.png'),('Interior aisle approval','EVERGREEN_BLOCKOUT_AISLE.png')]:
 cam=bpy.data.objects[cam_name];scene.camera=cam
 for obj in bpy.data.collections['06_OVERLAYS'].objects:obj.hide_render=obj.parent != cam
 scene.display.shading.show_shadows=cam_name.startswith('Aerial')
 scene.render.filepath=os.path.join(root,filename);bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Aerial layout approval'];scene.display.shading.show_shadows=True
for obj in bpy.data.collections['06_OVERLAYS'].objects:obj.hide_render=obj.parent != scene.camera
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root,'EVERGREEN_LAYOUT_BLOCKOUT_v1.blend'))
print('VALIDATED_CLEAR_AISLE',scene['secondary_aisle_clear_m'],flush=True)
