import bpy,math,json,random
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent;O=R/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'Asset_Library.blend'));s=bpy.context.scene;random.seed(31)
for o in list(s.objects):
 if o.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(o,do_unlink=True)
def col(name):
 c=bpy.data.collections.new(name);s.collection.children.link(c);return c
terrain=col('00_TERRAIN');walls=col('01_CANYON');towercol=col('02_TOWER');covers=col('03_DENSE_COVER');anchors=col('04_GAMEPLAY_ANCHORS');guides=col('05_LAYOUT_GUIDES');cams=col('06_PRESENTATION')
manifest=[]
def place(asset,name,x,y,h,angle=0,collection=covers,sx=1,sy=1):
 src=bpy.data.objects[asset];o=src.copy();o.data=src.data;collection.objects.link(o);o.name=name;o.hide_render=False;o.hide_viewport=False;o.location=(x,y,0);o.scale=(h*sx,h*sy,h);o.rotation_euler=(0,0,math.radians(angle));o['source_asset']=asset
 manifest.append({'object':name,'asset':asset,'position':[x,y,0],'height':h,'rotation_z':angle,'scale_xy':[sx,sy],'collection':collection.name});return o
def mat(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85;return m
sand=mat('Warm canyon sand',(.46,.29,.13));teal=mat('Runner marker',(.03,.65,.55));gold=mat('Route lines',(.9,.65,.15))
def cube(name,loc,scale,material,collection):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 for c in list(o.users_collection):c.objects.unlink(o)
 collection.objects.link(o);return o
cube('Sand ground',(0,0,-.4),(64,224,.8),sand,terrain)
# Sand grain stays procedural in Blender; interchange uses base colour.
nt=sand.node_tree;n=nt.nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=95;b=nt.nodes.new('ShaderNodeBump');b.inputs['Strength'].default_value=.18;b.inputs['Distance'].default_value=.07;nt.links.new(n.outputs['Fac'],b.inputs['Height']);nt.links.new(b.outputs['Normal'],nt.nodes['Principled BSDF'].inputs['Normal'])
# Actual canyon panels overlap along the perimeter; inner gameplay width about 36m.
for side in [-1,1]:
 for i,y in enumerate(range(-90,94,14)):
  asset='Straight canyon wall' if i%3 else 'Canyon bend and variation';o=place(asset,f'Canyon {side:+d} segment {i:02d}',side*24,y,12.5+(i%3)*.6,-90 if side==1 else 90,walls)
# End walls leave the tower centre passage open.
for x in [-13.8,13.8]:place('Straight canyon wall',f'End wall {x}',x,94,12,0,walls,sx=.55)
tow=place('Tower','Tower gate and sniper deck',0,89,26,0,towercol)
# Three interleaved lanes: roughly 8m advance between cover stations, varied diagonals.
patterns=['Large sandstone cover boulder','baricade2','Angular sandstone cover slab','L-shaped barricade','Baricade3','Abandoned Water Station','Overturned Mining Cart']
for lane,xbase in enumerate([-11,0,11]):
 for j in range(19):
  y=-78+j*8.35+(lane-1)*2.4;x=xbase+random.uniform(-2.7,2.7)
  if lane==0 and j==12:continue # reserve open landmark footprint
  asset=patterns[(j*2+lane*3)%len(patterns)];height=random.uniform(2.8,3.6)
  if asset=='L-shaped barricade':height=2.6
  if asset=='Abandoned Water Station':height=2.7
  if y>48:height+=.7
  angle=random.choice([-42,-25,-12,15,28,43])+random.uniform(-6,6)
  place(asset,f'Cover L{lane+1} S{j+1:02d} | {asset}',x,y,height,angle)
  # Occasional complementary cargo clusters, offset sideways rather than closing lanes.
  if j%5==lane:
   for k in range(2):place(['CrateA','CrateB','CrateC'][(j+k+lane)%3],f'Cargo L{lane+1} S{j+1:02d} P{k+1}',x+(-1 if lane==2 else 1)*(2.7+k*1.4),y+(-1)**k*.8,1.8+k*.5,angle+k*23)
# Landmark remains visually open, placed beside, rather than across, the centre route.
place('Collapsed Sandstone Arc','Open collapsed arch landmark',-11,20,5.0,0)
# Final approach keeps some protective cover near the high sniper angle.
place('Large sandstone cover boulder','Final west cover',-5,79,4.3,-30)
place('Angular sandstone cover slab','Final east peek',5,81,4.4,25)
# Rifle is display only.
rifle=place('Sniper','Sniper display rifle',0,88,.6,0,towercol);rifle.location.z=22.2;manifest[-1]['position']=[0,88,22.2]
for name,loc in [('RUNNER_SPAWN',(0,-87,0)),('EXIT_GATE',(0,89,0)),('SNIPER_EYE',(0,88,23.55))]:
 o=bpy.data.objects.new(name,None);anchors.objects.link(o);o.location=loc;o.empty_display_type='ARROWS';o.empty_display_size=1
# Human scale marks are annotations, not exported gameplay geometry.
for x in [-1.5,0,1.5]:
 cube('Runner scale 1.8m',(x,-86,.9),(.45,.35,1.8),teal,guides)
def label(text,loc,size=1):
 cu=bpy.data.curves.new(text,'FONT');cu.body=text;cu.size=size;cu.align_x='CENTER';ob=bpy.data.objects.new(text,cu);guides.objects.link(ob);ob.location=loc;cu.materials.append(gold)
label('RUNNERS  /  1.8m reference',(0,-94,.05),1.2);label('TOWER / EXIT',(0,97,.05),1.4)
def camera(name,loc,target,lens=45,ortho=None):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);cams.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens
 if ortho:d.type='ORTHO';d.ortho_scale=ortho
 return o
camera('CAM_OVERVIEW',(145,-195,155),(0,4,3),42)
camera('CAM_TOPDOWN',(0,0,210),(0,0,0),ortho=233)
camera('CAM_SNIPER_POV',(0,88,23.55),(0,-30,1.4),35)
camera('CAM_RUNNER_APPROACH',(0,-88,1.65),(0,-45,2),25)
d=bpy.data.lights.new('Warm sun','SUN');d.energy=3;ob=bpy.data.objects.new('Warm sun',d);cams.objects.link(ob);ob.rotation_euler=(.3,-.35,-.45)
s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_percentage=100;s.world.node_tree.nodes['Background'].inputs[1].default_value=.7
s['source_commit']='5ae8afdb0ae6519261049e15dc388da1cf7f99b1';s['design']='Dense staggered cover revision; geometric checking only, no gameplay balance claim.'
bpy.context.view_layer.update()
for r in manifest:
 r['source_id']=r['asset'];r['blender_scale']=[r['height']*r['scale_xy'][0],r['height']*r['scale_xy'][1],r['height']]
 r['unity_position_xyz']=[r['position'][0],r['position'][2],r['position'][1]];r['unity_yaw_degrees']=-r['rotation_z'];r['unity_scale_xyz']=[r['blender_scale'][0],r['blender_scale'][2],r['blender_scale'][1]]
(O/'Layout_Manifest.json').write_text(json.dumps(manifest,indent=2))
bpy.ops.file.pack_all();s.camera=bpy.data.objects['CAM_OVERVIEW'];bpy.ops.wm.save_as_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'),compress=True)
for name,cam,res in [('Topdown','CAM_TOPDOWN',(1000,1800)),('Sniper_POV','CAM_SNIPER_POV',(1500,850)),('Runner_Approach','CAM_RUNNER_APPROACH',(1500,850)),('Overview','CAM_OVERVIEW',(1500,1050))]:
 guides.hide_render=name!='Topdown';s.camera=bpy.data.objects[cam];s.render.resolution_x,s.render.resolution_y=res;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True);print('PREVIEW_READY',name,flush=True)
