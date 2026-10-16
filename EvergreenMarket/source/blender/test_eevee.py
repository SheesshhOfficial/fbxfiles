import bpy,math
from mathutils import Vector
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64
s.view_settings.exposure=-.5
s.camera=bpy.data.objects['CAM_Interior_Hero'];s.camera.location=(-18.5,-15.8,2.6);s.camera.rotation_euler=(Vector((-1,5,1.6))-s.camera.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=1280;s.render.resolution_y=800;s.render.resolution_percentage=100
s.render.filepath='/workspace/scratch/26eeef986c30/supermarket_delivery/previews/01_Interior_Eevee_Test.png'
print('EEVEE START',flush=True);bpy.ops.render.render(write_still=True);print('EEVEE DONE',flush=True)
