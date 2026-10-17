import bpy,os
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));s=bpy.context.scene;s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=85;s.cycles.samples=160;s.cycles.use_denoising=False;s.render.image_settings.file_format='PNG'
os.makedirs(R+'/renders/artpass',exist_ok=True)
for name,loc,target,lens in [('Midway_Refined',(-10.4,-19.4,1.7),(-14.6,-1,2),32),('Stall_Closeup',(-12.4,-18.1,1.65),(-16.45,-13.8,1.8),35)]:
 o=bpy.data.objects.get(name)
 if o is None:
  d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o)
 o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens;s.camera=o;s.render.filepath=R+'/renders/artpass/'+name+'.png';bpy.ops.render.render(write_still=True)
