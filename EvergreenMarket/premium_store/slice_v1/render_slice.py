import bpy,os,sys
R=os.path.dirname(os.path.abspath(__file__));bpy.ops.wm.open_mainfile(filepath=os.path.join(R,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend'))
s=bpy.context.scene;s.cycles.use_denoising=False;s.cycles.samples=512;s.cycles.adaptive_threshold=.015;s.render.resolution_percentage=100;s.render.resolution_x=1500;s.render.resolution_y=1100;s.render.threads_mode='FIXED';s.render.threads=8
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
preview=any(a.startswith('preview') for a in args)
if preview:s.cycles.samples=40;s.cycles.adaptive_threshold=.05;s.render.resolution_percentage=70
jobs=[('03_Pantry_product_study','SLICE_02_PRODUCT_DETAIL_CYCLES.png'),('01_Aisle_eyeheight','SLICE_01_AISLE_CYCLES.png')]
if 'all' in args:jobs.append(('02_Product_closeup','SLICE_03_SHELF_DETAIL_CYCLES.png'))
if preview:
 if 'preview_products' in args:jobs=[('02_Product_closeup','PREVIEW_PRODUCTS.png')]
 elif 'preview_still' in args:jobs=[('03_Pantry_product_study','PREVIEW_STILL.png')]
 else:jobs=[('01_Aisle_eyeheight','PREVIEW_AISLE.png')]
for camname,filename in jobs:
 s.camera=bpy.data.objects[camname]
 for o in bpy.data.collections['08_CAMERA_CAPTIONS'].objects:o.hide_render=o.parent!=s.camera
 s.render.filepath=os.path.join(R,filename);bpy.ops.render.render(write_still=True);print('RENDER_COMPLETE',filename,flush=True)
if not preview:
 s.camera=bpy.data.objects['01_Aisle_eyeheight']
 for o in bpy.data.collections['08_CAMERA_CAPTIONS'].objects:o.hide_render=o.parent!=s.camera
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=os.path.join(R,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend'))
