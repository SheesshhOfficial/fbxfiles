import bpy,sys,json,time
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent
mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'AFTER'
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s
s.camera=bpy.data.objects['FULL_AISLE_EYEHEIGHT'];s.render.engine='CYCLES';s.cycles.samples=96;s.cycles.use_denoising=False;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.045;s.cycles.max_bounces=6;s.render.threads_mode='FIXED';s.render.threads=8;s.render.resolution_x=1200;s.render.resolution_y=850;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(R/(mode+'_AISLE.png'))
bpy.ops.render.render(write_still=True,scene=s.name)
print('REVIEW_READY',mode,flush=True)
