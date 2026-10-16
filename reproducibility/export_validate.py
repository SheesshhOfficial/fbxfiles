import bpy,json,re,math,sys
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'));s=bpy.context.scene;bpy.context.view_layer.update();U=O/'Unity';U.mkdir(exist_ok=True);T=O/'textures';T.mkdir(exist_ok=True)
meshes=[o for c in s.collection.children if c.name.startswith(('00_','01_','02_','03_')) for o in c.objects if o.type=='MESH']
def cast(objects,a,b):
 a=Vector(a);b=Vector(b);hits=[]
 for o in objects:
  inv=o.matrix_world.inverted();la=inv@a;lb=inv@b;d=lb-la;hit,p,n,f=o.ray_cast(la,d.normalized())
  if hit and (p-la).length<d.length:
   w=o.matrix_world@p;hits.append(((w-a).length,o.name,list(w)))
 return min(hits) if hits else None
qa={'source_models':15,'visible_mesh_objects':len(meshes),'unique_meshes':len({o.data for o in meshes}),'missing_images':[im.name for im in bpy.data.images if im.source=='FILE' and not im.size[0]],'packed_images':len([im for im in bpy.data.images if im.packed_file]),'gate_rays':{},'deck_probes':{}}
for x in [-.75,0,.75]:
 for z in [.2,1,1.8]:qa['gate_rays'][f'{x},{z}']=cast(meshes,(x,83,z),(x,105,z))
tower=[bpy.data.objects['Tower gate and sniper deck']]+[o for o in bpy.data.objects if o.name.startswith(('Sniper firing balcony','Balcony '))]
for y in [85.8,88,89]:qa['deck_probes'][str(y)]=cast(tower,(0,y,24),(0,y,19))
for im in bpy.data.images:
 if im.source=='FILE' and im.size[0]:
  name=re.sub('[^A-Za-z0-9_.-]','_',im.name)+'.png';im.filepath_raw=str(T/name);im.file_format='PNG';im.save();im.pack()
# Final scene opens on overview, with guides hidden in beauty renders.
bpy.data.collections['05_LAYOUT_GUIDES'].hide_render=True;s.camera=bpy.data.objects['CAM_OVERVIEW'];bpy.ops.wm.save_as_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'),compress=True)
if '--skip-export' in sys.argv:
 (O/'Final_QA.json').write_text(json.dumps(qa,indent=2));print('FINAL_QA',json.dumps(qa),flush=True);sys.exit(0)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
for o in bpy.data.collections['04_GAMEPLAY_ANCHORS'].objects:o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(U/'SnipersAim_Dense_Canyon_v2.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Z',axis_up='Y',bake_anim=False,path_mode='COPY',embed_textures=False,use_custom_props=True)
qa['fbx_bytes']=(U/'SnipersAim_Dense_Canyon_v2.fbx').stat().st_size
(O/'Final_QA.json').write_text(json.dumps(qa,indent=2));print('FINAL_QA',json.dumps(qa),flush=True)
# Reimport external FBX and verify geometry and referenced texture buffers.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(U/'SnipersAim_Dense_Canyon_v2.fbx'),use_image_search=False);bpy.context.view_layer.update();obs=[o for o in bpy.data.objects if o.type=='MESH'];pts=[o.matrix_world@Vector(v) for o in obs for v in o.bound_box]
r={'mesh_count':len(obs),'bounds_m':[max(p[i] for p in pts)-min(p[i] for p in pts) for i in range(3)],'images':len(bpy.data.images),'missing_images':[im.name for im in bpy.data.images if not im.size[0]],'test':'Blender FBX reimport only; Unity not available/tested.'};(O/'FBX_Roundtrip_QA.json').write_text(json.dumps(r,indent=2));print('FBX_ROUNDTRIP',json.dumps(r),flush=True)
