import bpy,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;args=sys.argv[sys.argv.index('--')+1:];mode=args[0];view=args[1] if len(args)>1 else 'SIGNS'
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s
loc,target,lens=((12,10.2,2.15),(30,23,2.3),26) if view=='SIGNS' else ((12,17,2.0),(2,25,2.05),25)
d=bpy.data.cameras.new('V3_Review_'+view);cam=bpy.data.objects.new('V3_Review_'+view,d);s.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=400;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=False;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.035;s.cycles.max_bounces=6;s.render.threads_mode='FIXED';s.render.threads=8;s.render.resolution_x=1200;s.render.resolution_y=850;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(R/(mode+'_'+view+'.png'));bpy.ops.render.render(write_still=True,scene=s.name);print('DETAIL_READY',mode,view,flush=True)
