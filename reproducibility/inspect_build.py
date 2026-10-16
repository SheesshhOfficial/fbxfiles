import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent;O=R/'output';O.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.unit_settings.system='METRIC';s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=False
s.world=bpy.data.worlds.new('Sky');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.38,.5,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.6
masters=bpy.data.collections.new('SOURCE_MASTERS');s.collection.children.link(masters)
inv=[]
for idx,p in enumerate(sorted((R/'assets_repo').rglob('*'))):
 if p.suffix.lower() not in ['.fbx','.glb']:continue
 old=set(bpy.data.objects)
 if p.suffix.lower()=='.fbx':bpy.ops.import_scene.fbx(filepath=str(p))
 else:bpy.ops.import_scene.gltf(filepath=str(p))
 bpy.context.view_layer.update();new=set(bpy.data.objects)-old;meshes=[o for o in new if o.type=='MESH']
 pts=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box];lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)]);center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));height=hi.z-lo.z
 bpy.ops.object.select_all(action='DESELECT')
 for o in meshes:o.select_set(True)
 bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();o=bpy.context.object
 world=o.matrix_world.copy();o.data.transform(Matrix.Scale(1/height,4)@Matrix.Translation(-center)@world);o.matrix_world=Matrix.Identity(4);o.name=p.stem
 if len(o.data.polygons)>120000:
  m=o.modifiers.new('Working mesh optimization','DECIMATE');m.ratio=100000/len(o.data.polygons);bpy.ops.object.modifier_apply(modifier=m.name)
 for c in list(o.users_collection):c.objects.unlink(o)
 masters.objects.link(o);o['source_asset']=p.name
 for ob in list(bpy.data.objects):
  if ob not in old and ob!=o:bpy.data.objects.remove(ob,do_unlink=True)
 for im in bpy.data.images:
  if im.size[0]>1024:im.scale(1024,1024);im.pack()
 bpy.context.view_layer.update()
 inv.append({'name':p.stem,'file':str(p.relative_to(R)),'original_dimensions':list(hi-lo),'normalized_dimensions':list(o.dimensions),'triangles':len(o.data.polygons),'images':len(bpy.data.images)})
 print('IMPORTED',p.name,flush=True)
# Contact sheet using copies and numeric labels.
contact=bpy.data.collections.new('CONTACT_SHEET');s.collection.children.link(contact)
for i,r in enumerate(inv):
 src=bpy.data.objects[r['name']];o=src.copy();o.data=src.data;contact.objects.link(o);o.scale=(4,4,4);o.location=((i%5)*8,(i//5)*9,0)
 bpy.ops.object.text_add(location=(o.location.x-3,o.location.y-3,.05));txt=bpy.context.object;txt.data.body=str(i+1)+' '+r['name'];txt.data.size=.35;txt.data.extrude=0
 for c in list(txt.users_collection):c.objects.unlink(txt)
 contact.objects.link(txt)
masters.hide_render=True;masters.hide_viewport=True
bpy.ops.object.light_add(type='SUN',location=(0,0,20));bpy.context.object.rotation_euler=(.4,-.5,-.4);bpy.context.object.data.energy=3
bpy.ops.object.camera_add(location=(33,-27,40));cam=bpy.context.object;cam.rotation_euler=(Vector((16,9,1.5))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=51;s.camera=cam
s.render.resolution_x=1800;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.render.filepath=str(O/'Asset_Inspection.png');bpy.ops.render.render(write_still=True)
(O/'Asset_Inventory.json').write_text(json.dumps(inv,indent=2))
for ob in list(contact.objects):bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.collections.remove(contact)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Asset_Library.blend'),compress=True)
