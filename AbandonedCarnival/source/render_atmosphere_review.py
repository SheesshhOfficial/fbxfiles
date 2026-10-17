import bpy,os
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));s=bpy.context.scene;s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=75;s.cycles.samples=96;s.cycles.use_denoising=False
cam=bpy.data.objects['Camera_Midway'];cam.location=(-10.4,-19.4,1.7);cam.rotation_euler=(Vector((-14.6,-1,2))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=32;s.camera=cam;s.render.filepath=R+'/renders/artpass/Midway_Atmosphere.png';bpy.ops.render.render(write_still=True)
