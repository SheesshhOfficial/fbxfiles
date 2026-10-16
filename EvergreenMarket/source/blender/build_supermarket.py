"""EVERGREEN MARKET - original procedural Blender authoring source.
Run: blender -b --python source/build_supermarket.py -- [--preview-only]
Units: metres. Blender 4.3+. All assets, labels and materials original.
"""
import bpy, math, random, os, sys, json, time
from pathlib import Path
from mathutils import Vector
random.seed(19)
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT; TEX=ROOT/'textures'; PRE=ROOT/'previews'
PRE.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for d in list(bpy.data.collections):
 if d.name!='Collection':bpy.data.collections.remove(d)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.cycles.preview_samples=16
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX'
scene.render.film_transparent=False
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.65,0.75,0.85,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
# Collections are intentionally semantic for handoff and selective export.
COLS={}; CURRENT=None
for name in ['00_Site','01_Shell','02_Front_Glazing','03_Roof_Ceiling','04_Floor_Detail','10_Grocery_Fixtures','11_Grocery_Products','12_Produce','13_Bakery','14_Chilled','15_Checkouts','16_Carts_Baskets','20_Stockroom','21_Staff_Room','22_Loading_Yard','30_Signage','40_Lighting','50_Cameras','90_Gameplay_Notes']:
 c=bpy.data.collections.new(name);scene.collection.children.link(c);COLS[name]=c
CURRENT=COLS['00_Site']
base=bpy.data.collections.get('Collection')
if base:bpy.data.collections.remove(base)
def use(name):
 global CURRENT;CURRENT=COLS[name]
def link_obj(name,mesh,loc=(0,0,0),rot=(0,0,0),scale=(1,1,1)):
 o=bpy.data.objects.new(name,mesh);CURRENT.objects.link(o);o.location=loc;o.rotation_euler=rot;o.scale=scale;return o
M={}
def mat(name,color,rough=.5,metal=0,noise=0,emission=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;n=m.node_tree.nodes;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
 if noise:
  tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=noise;tex.inputs['Detail'].default_value=3
  bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.035;m.node_tree.links.new(tex.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
 M[name]=m;return m
mat('warm plaster',(.74,.75,.68),.75,noise=85);mat('deep evergreen',(.035,.15,.115),.38);mat('sage enamel',(.28,.42,.32),.4);mat('porcelain',(.8,.83,.78),.29);mat('warm stone',(.57,.59,.54),.55,noise=90);mat('tile grout',(.24,.28,.26),.85)
mat('oak',(.39,.21,.095),.47,noise=7);mat('oak light',(.62,.38,.16),.44,noise=9);mat('steel',(.32,.36,.36),.28,.8);mat('brushed steel',(.58,.63,.63),.32,.75,noise=180);mat('black rubber',(.014,.022,.021),.74);mat('charcoal',(.045,.059,.057),.45)
mat('cream paper',(.91,.83,.64),.64);mat('white label',(.93,.94,.87),.55);mat('ink',(.012,.04,.03),.55);mat('amber',(.87,.41,.08),.42);mat('yellow safety',(.92,.62,.06),.5);mat('red plastic',(.57,.06,.035),.45);mat('blue plastic',(.035,.22,.34),.32);mat('cardboard',(.45,.29,.13),.82,noise=100);mat('tape',(.61,.44,.23),.48)
mat('asphalt',(.105,.12,.12),.9,noise=65);mat('concrete',(.4,.43,.41),.85,noise=65);mat('leaf',(.12,.28,.06),.58);mat('apple',(.56,.045,.025),.3,noise=22);mat('green apple',(.38,.55,.07),.33,noise=22);mat('orange',(.9,.28,.015),.5,noise=60);mat('lemon',(.9,.7,.025),.4,noise=55);mat('eggplant',(.115,.018,.09),.26);mat('bread',(.54,.27,.065),.7,noise=60)
mat('LED',(.94,.97,1),.2,emission=5);mat('warm LED',(1,.77,.42),.2,emission=4);mat('screen',(.025,.3,.25),.25,emission=.7)
glass=mat('architectural glass',(.73,.87,.88),.08);p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.98;p.inputs['IOR'].default_value=1.45
# Floor material: slightly varied aggregate rather than a flat blockout surface.
floor=mat('terrazzo porcelain',(.66,.69,.64),.33)
n=floor.node_tree.nodes;l=floor.node_tree.links;noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=145;noise.inputs['Detail'].default_value=2
r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.31;r.color_ramp.elements[0].color=(.36,.39,.35,1);r.color_ramp.elements[1].position=.64;r.color_ramp.elements[1].color=(.72,.74,.68,1);l.new(noise.outputs['Fac'],r.inputs[0]);l.new(r.outputs['Color'],n.get('Principled BSDF').inputs['Base Color'])
b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.018;l.new(noise.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],n.get('Principled BSDF').inputs['Normal'])
# Cached meshes make thousands of products lightweight and editable.
CACHE={}
def box(name,loc,dims,ma='porcelain',bev=.03,rot=(0,0,0)):
 key=('b',tuple(round(x,4) for x in dims),ma,bev)
 if key not in CACHE:
  x,y,z=(v/2 for v in dims);verts=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)];faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
  mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.materials.append(M[ma]);mesh.update()
  if bev:
   temp=link_obj('_bevel_template',mesh);mod=temp.modifiers.new('Machined edge radius','BEVEL');mod.width=bev;mod.segments=3;mod.affect='EDGES'
   bpy.context.view_layer.objects.active=temp;temp.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name)
   for p in temp.data.polygons:p.use_smooth=True
   mod=temp.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True
   bpy.ops.object.modifier_apply(modifier=mod.name);mesh=temp.data;bpy.data.objects.remove(temp,do_unlink=True)
  CACHE[key]=mesh
 return link_obj(name,CACHE[key],loc,rot)
def lathemesh(name,profile,mats,segments=32):
 verts=[];faces=[];mi=[]
 for radius,z,idx in profile:
  for k in range(segments):
   a=k*math.tau/segments;verts.append((radius*math.cos(a),radius*math.sin(a),z))
 for j in range(len(profile)-1):
  for k in range(segments):faces.append((j*segments+k,j*segments+(k+1)%segments,(j+1)*segments+(k+1)%segments,(j+1)*segments+k));mi.append(profile[j][2])
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces)
 for m in mats:mesh.materials.append(m)
 uv=mesh.uv_layers.new(name='UVMap')
 for pi,p in enumerate(mesh.polygons):
  p.material_index=mi[pi];p.use_smooth=True;j=pi//segments;k=pi%segments
  for li,xy in zip(p.loop_indices,[(k/segments,j/(len(profile)-1)),((k+1)/segments,j/(len(profile)-1)),((k+1)/segments,(j+1)/(len(profile)-1)),(k/segments,(j+1)/(len(profile)-1))]):uv.data[li].uv=xy
 mesh.update();return mesh
def cyl(name,loc,r,depth,ma='steel',rot=(0,0,0),segments=32):
 key=('c',r,depth,ma,segments)
 if key not in CACHE:
  e=min(.009,r*.12,depth*.08);CACHE[key]=lathemesh(name+'_Mesh',[(0,-depth/2,0),(r-e,-depth/2,0),(r,-depth/2+e,0),(r,depth/2-e,0),(r-e,depth/2,0),(0,depth/2,0)],[M[ma]],segments)
 return link_obj(name,CACHE[key],loc,rot)
def sphere(name,loc,scale,ma='apple'):
 key=('s',ma)
 if key not in CACHE:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16);o=bpy.context.object;o.data.materials.append(M[ma]);mesh=o.data
  for p in mesh.polygons:p.use_smooth=True
  CACHE[key]=mesh;bpy.data.objects.remove(o,do_unlink=True)
 return link_obj(name,CACHE[key],loc,scale=scale)
def tube(name,points,r=.015,ma='steel'):
 c=bpy.data.curves.new(name+'_Curve','CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=r;c.bevel_resolution=3;s=c.splines.new('POLY');s.points.add(len(points)-1)
 for p,co in zip(s.points,points):p.co=(*co,1)
 c.materials.append(M[ma]);return link_obj(name,c)
FONT_PATH=str(ROOT/'source'/'fonts'/'DejaVuSans-Bold.ttf')
FONT=bpy.data.fonts.load(FONT_PATH)
def text(name,body,loc,size=.3,ma='cream paper',rot=(math.pi/2,0,0),align='CENTER'):
 c=bpy.data.curves.new(name+'_Lettering','FONT');c.body=body;c.size=size;c.align_x=align;c.align_y='CENTER';c.font=FONT;c.extrude=.0015;c.bevel_depth=.0007;c.resolution_u=6;c.materials.append(M[ma]);return link_obj(name,c,loc,rot)
def area(name,loc,power,size,color=(1,.93,.82),target=None):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;o=link_obj(name,d,loc)
 if target:o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
 return o
# Original pack textures, on linked carton and can meshes.
PACK=[]
for i in range(16):
 m=bpy.data.materials.new(f'Packaging_{i:02d}_Original');m.use_nodes=True;im=bpy.data.images.load(str(TEX/f'pack_{i:02d}.png'));im.pack();tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;m.node_tree.links.new(tex.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color']);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.48;PACK.append(m)
def carton_mesh(i,w=.22,d=.12,h=.34):
 key=('carton',i,w,d,h)
 if key in CACHE:return CACHE[key]
 # Pack front faces Y- and Y+ use texture, other faces use matching paper.
 v=[(-w/2,-d/2,0),(w/2,-d/2,0),(w/2,-d/2,h),(-w/2,-d/2,h),(-w/2,d/2,0),(w/2,d/2,0),(w/2,d/2,h),(-w/2,d/2,h)]
 f=[(0,1,2,3),(5,4,7,6),(4,0,3,7),(1,5,6,2),(3,2,6,7),(4,5,1,0)]
 mesh=bpy.data.meshes.new(f'SKU_{i:02d}_Carton');mesh.from_pydata(v,[],f);mesh.materials.append(PACK[i]);mesh.materials.append(M['cream paper']);uv=mesh.uv_layers.new(name='Packaging_UV')
 for p in mesh.polygons:
  p.material_index=0 if p.index<2 else 1
  for li,xy in zip(p.loop_indices,[(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=xy
 CACHE[key]=mesh;return mesh
def product(i,loc,rot=0,kind=None,scale=1):
 if kind is None:kind='bottle' if i in (2,3,4,11) else 'can' if i in (6,7,8,13) else 'box'
 key=('product',i,kind)
 if key not in CACHE:
  if kind=='box':mesh=carton_mesh(i,.24 if i in (0,1,14) else .19,.11,.36 if i in (0,1) else .29)
  else:
   if kind=='bottle':prof=[(0,0,0),(.061,0,0),(.07,.015,0),(.07,.04,1),(.07,.21,0),(.067,.245,0),(.035,.29,0),(.028,.32,2),(.03,.322,2),(.03,.347,2),(0,.347,2)]
   else:prof=[(0,0,0),(.062,0,0),(.067,.008,0),(.067,.02,1),(.067,.17,0),(.067,.18,0),(.062,.185,0),(0,.185,0)]
   mesh=lathemesh(f'SKU_{i:02d}_{kind}',prof,[M['sage enamel'] if kind=='bottle' else M['brushed steel'],PACK[i],M['cream paper']],40)
   uv=mesh.uv_layers.active
   # Each label spans one complete repeat around the circumference.
   for p in mesh.polygons:
    if p.material_index==1:
     k=p.index%40
     for li,xy in zip(p.loop_indices,[(k/40,0),((k+1)/40,0),((k+1)/40,1),(k/40,1)]):uv.data[li].uv=xy
  CACHE[key]=mesh
 o=link_obj(f'PROP_SKU_{i:02d}_{kind}',CACHE[key],loc,(0,0,rot),(scale,scale,scale));o['prop_family']=f'SKU_{i:02d}';o['gameplay_status']='Candidate only; implement bounds, collision and min size in Unreal';return o
print('STAGE: Building shell',flush=True)
# Building shell; front at Y=-18.
use('00_Site')
box('Site terrain',(7,5,-.42),(79,74,.5),'asphalt',.05)
box('Raised building slab',(0,6,-.15),(45,49,.3),'concrete',.05)
box('Front walkway',(0,-21,-.08),(48,6,.16),'concrete',.025)
box('Front kerb',(0,-24,.015),(48,.2,.3),'porcelain',.025)
for x in range(-24,30,6):box('Parking bay stripe',(x,-29,-.155),(.1,8,.015),'white label',0)
for x in (-18,-10,10,18):
 cyl('Safety bollard',(x,-20.5,.48),.1,.95,'sage enamel');cyl('Bollard reflective band',(x,-20.5,.79),.105,.12,'cream paper')
use('04_Floor_Detail')
box('Sales floor',(0,0,-.015),(44,36,.12),'terrazzo porcelain',.015)
box('Service floor',(0,24,-.015),(44,12,.12),'concrete',.015)
# Tile joints sparse geometry, visible at human scale.
for x in range(-22,23,2):box('Tile expansion joint',(x,0,.048),(.012,36,.002),'tile grout',0)
for y in range(-18,19,2):box('Tile expansion joint',(0,y,.049),(44,.012,.002),'tile grout',0)
use('01_Shell')
def wall_y(name,y,xmin,xmax,doors=[]):
 cursor=xmin
 for center,width,height in sorted(doors):
  left=center-width/2;right=center+width/2
  if left>cursor:box(name,( (cursor+left)/2,y,2.5),(left-cursor,.24,5),'warm plaster',.025)
  box(name+'_lintel',(center,y,(height+5)/2),(width,.24,5-height),'warm plaster',.02);cursor=right
 if cursor<xmax:box(name,((cursor+xmax)/2,y,2.5),(xmax-cursor,.24,5),'warm plaster',.025)
def wall_x(name,x,ymin,ymax,doors=[]):
 cursor=ymin
 for center,width,height in sorted(doors):
  left=center-width/2;right=center+width/2
  if left>cursor:box(name,(x,(cursor+left)/2,2.5),(.24,left-cursor,5),'warm plaster',.025)
  box(name+'_lintel',(x,center,(height+5)/2),(.24,width,5-height),'warm plaster',.02);cursor=right
 if cursor<ymax:box(name,(x,(cursor+ymax)/2,2.5),(.24,ymax-cursor,5),'warm plaster',.025)
wall_x('West external wall',-22,-18,30)
wall_x('East external wall',22,-18,30,[(8,3,3.1),(25,3,3.1)])
wall_y('Rear external wall',30,-22,22)
wall_y('Shop service partition',18,-22,22,[(-14,3.2,3.2),(3,3.2,3.2),(15,2.4,2.8)])
wall_x('Staff stock partition',8,18,30,[(24,2.2,2.8)])
# lower protection rails and green upper bands
for x in (-21.8,21.8):
 box('Wall green frieze',(x,0,3.8),(.08,36,.62),'deep evergreen',.01)
 if x<0:box('Impact protection',(x,0,.35),(.08,36,.18),'oak',.02)
box('Rear sales frieze',(0,17.82,3.8),(44,.08,.62),'deep evergreen',.01)
for x in (-14,3,15):
 box('Door frame left',(x-1.66 if x!=15 else x-1.26,17.83,1.6),(.1,.2,3.2),'steel',.01)
 box('Door frame right',(x+1.66 if x!=15 else x+1.26,17.83,1.6),(.1,.2,3.2),'steel',.01)
# Columns define structural rhythm without blocking aisles.
for x in (-20,18):
 for y in (-10,4,17,29):
  box('Structural column',(x,y,2.5),(.34,.34,5),'porcelain',.025);box('Column scuff guard',(x,y,.55),(.39,.39,1.1),'sage enamel',.02)
use('02_Front_Glazing')
for x in (-19,-13,-7,7,13,19):
 box('Shopfront glass',(x,-18,2.1),(5.8,.035,4.1),'architectural glass',.008)
 box('Shopfront mullion',(x-2.95,-18,2.2),(.09,.16,4.4),'charcoal',.012)
box('Shopfront header',(0,-18,4.6),(44,.25,.8),'deep evergreen',.025)
for x in (-1.5,1.5):
 box('Sliding entrance glass',(x,-18.03,1.8),(2.95,.04,3.6),'architectural glass',.005)
 for xx in (x-1.47,x+1.47):box('Entrance door frame',(xx,-18.07,1.8),(.06,.1,3.6),'brushed steel',.008)
 box('Door visibility strip',(x,-18.08,1.4),(2.9,.015,.08),'cream paper',0)
box('Entrance transom',(0,-18.1,3.7),(6.1,.2,.15),'charcoal',.02)
box('Entry mat',(0,-16.6,.07),(5.3,2.4,.05),'black rubber',.02)
for x in [i*.12-2.55 for i in range(43)]:box('Entry mat rib',(x,-16.6,.1),(.035,2.25,.016),'charcoal',.005)
box('Entrance canopy',(0,-19.6,4.25),(16,3.4,.24),'charcoal',.04)
box('Canopy timber soffit',(0,-19.6,4.1),(15.8,3.2,.08),'oak',.02)
for x in range(-7,8):box('Canopy linear light',(x,-19.6,4.04),(.035,2.7,.03),'warm LED',.005)
use('03_Roof_Ceiling')
box('Roof membrane',(0,6,5.35),(44.8,48.8,.2),'charcoal',.03)
box('Ceiling acoustic deck',(0,6,5.13),(44,48,.12),'warm plaster',.01)
for y in range(-16,31,6):
 box('Steel main roof beam',(0,y,4.86),(44,.18,.34),'charcoal',.01)
for x in range(-20,23,4):box('Ceiling purlin',(x,6,5.0),(.07,48,.1),'steel',.008)
for x in (-15,15):
 cyl('HVAC spiral main',(x,0,4.53),.22,33,'brushed steel',(math.pi/2,0,0),40)
 for y in range(-15,17,2):cyl('HVAC seam ring',(x,y,4.53),.225,.035,'steel',(math.pi/2,0,0),40)
 for y in (-11,-3,5,13):
  tube('HVAC outlet neck',[(x,y,4.53),(x+(.5 if x<0 else -.5),y,4.5)],.14,'brushed steel')
  box('Diffuser grille',(x+(.55 if x<0 else -.55),y,4.47),(.08,.5,.22),'charcoal',.01)
for y in (-14,-7,0,7,14):
 tube('Sprinkler line',[(-21,y,4.72),(21,y,4.72)],.025,'red plastic')
 for x in (-18,-9,0,9,18):cyl('Sprinkler head',(x,y,4.64),.045,.08,'steel')
# Lighting fixtures included separately from roof for cutaways.
use('40_Lighting')
for x in (-18,-9,0,9,18):
 for y in (-13,-5,3,11,24):
  box('Suspended LED housing',(x,y,4.43),(2.9,.3,.12),'porcelain',.025)
  box('Opal LED diffuser',(x,y,4.355),(2.7,.24,.025),'LED',.01)
  for xx in (x-1.1,x+1.1):tube('Fixture suspension',[(xx,y,4.5),(xx,y,5.05)],.004,'steel')
  area('Retail soft light',(x,y,4.3),850,3.7,(1,.94,.82))
sun_data=bpy.data.lights.new('Late morning sunlight','SUN');sun_data.energy=1.5;sun_data.angle=.12
sun=link_obj('Late morning sunlight',sun_data);sun.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-28))
# daylight through storefront
for x in (-15,0,15):area('Window daylight',(x,-17.4,3.5),1300,5,(.72,.85,1),(x,3,1.0))
print('STAGE: Gondola shelving',flush=True)
# Gondola shelving, 12 detailed four-sided merchandising runs.
def price_strip(x,y,z,width=.7,rot=0,label='$ 3.49'):
 o=box('Shelf ticket holder',(x,y,z),(width,.018,.065),'charcoal',.004,rot=(0,0,rot))
 # lettering for main front-facing shelf endcaps only (stock SKUs retain label textures)
def shelf(cx,cy,num):
 use('10_Grocery_Fixtures');L=4.5
 box(f'Aisle {num:02d} recessed plinth',(cx,cy,.12),(1.1,L,.24),'charcoal',.025)
 box(f'Aisle {num:02d} backing',(cx,cy,1.15),(.07,L,2.15),'porcelain',.015)
 for yy in (-L/2,L/2):
  for xx in (-.5,.5):box('Shelf slotted upright',(cx+xx,cy+yy,1.15),(.065,.07,2.25),'porcelain',.012)
  box('Gondola timber end panel',(cx,cy+yy,1.06),(1.14,.07,1.95),'oak',.02)
  # endcap peg board, promotional display
  box('Endcap dark header',(cx,cy+yy,2.16),(1.18,.12,.23),'deep evergreen',.025)
  for z in (.42,1.0,1.58):
   box('Endcap shelf',(cx,cy+yy+(-.23 if yy<0 else .23),z),(1.1,.44,.035),'porcelain',.009)
   use('11_Grocery_Products')
   for k in range(4):product((num+int(z*3))%16,(cx-.4+k*.26,cy+yy+(-.24 if yy<0 else .24),z+.03),0 if yy<0 else math.pi)
   use('10_Grocery_Fixtures')
 for side in (-1,1):
  for row,z in enumerate((.3,.78,1.26,1.74)):
   box('Powder coated shelf',(cx+side*.31,cy,z),(.58,L,.035),'porcelain',.008)
   box('Shelf price rail',(cx+side*.61,cy,z+.01),(.025,L,.075),'charcoal',.006)
   for k in range(9):
    yy=cy-L/2+.23+k*.5
    box('Paper shelf-edge label',(cx+side*.626,yy,z+.015),(.004,.21,.048),'cream paper',.001)
    # uprights notches for adjustment
   use('11_Grocery_Products')
   for k in range(20):
    yy=cy-2.1+k*.215;sku=(num*3+row+(k//5))%16
    for dep in (0,1):
     if random.random()<.075:continue
     product(sku,(cx+side*(.29+dep*.17),yy+random.uniform(-.008,.008),z+.026),side*math.pi/2+random.uniform(-.03,.03),scale=random.uniform(.97,1.015))
   use('10_Grocery_Fixtures')
  for yy in [cy-2.2+i*.22 for i in range(21)]:
   for z in (.55,1.03,1.51,1.99):box('Shelf upright perforation',(cx+side*.047,yy,z),(.008,.026,.045),'charcoal',.002)
 # hanging aisle boards in parent signage collection
 use('30_Signage')
 box(f'Aisle {num:02d} overhead sign',(cx,cy-2.4,3.35),(2.9,.09,.64),'deep evergreen',.025)
 names=['PANTRY  /  GRAINS','DRINKS  /  JUICE','COFFEE  /  TEA','HOME  /  CLEAN','PASTA  /  SAUCES','BREAKFAST  /  OATS','SNACKS  /  TREATS','DAILY  /  ESSENTIALS','CANS  /  PRESERVES','NATURAL  /  ORGANIC','FAMILY  /  FAVORITES','BAKING  /  SPICES']
 text('Aisle designation',f'{num:02d}   {names[num-1]}',(cx,cy-2.455,3.35),.16)
 for xx in (cx-1.05,cx+1.05):tube('Sign hangers',[(xx,cy-2.4,3.68),(xx,cy-2.4,4.75)],.006,'steel')
for j,y in enumerate((-6,1.5,9)):
 for i,x in enumerate((-8,-2,4,10)):shelf(x,y,j*4+i+1)
print('STAGE: Produce tables',flush=True)
# Produce tables, separated slatted crates and dense produce with natural variation.
use('12_Produce')
def crate(name,x,y,z,w=1.1,d=.8):
 box(name+' base',(x,y,z+.045),(w,d,.09),'oak',.015)
 for level in range(3):
  zz=z+.13+level*.09
  for xx in (-w/2,w/2):box(name+' side slat',(x+xx,y,zz),(.045,d,.07),'oak light',.009)
  for yy in (-d/2,d/2):box(name+' end slat',(x,y+yy,zz),(w,.045,.07),'oak light',.009)
 for xx in (-w/2,w/2):
  for yy in (-d/2,d/2):box(name+' corner',(x+xx,y+yy,z+.2),(.06,.06,.4),'oak',.01)
for ti,(x,y) in enumerate([(-17,-7),(-13,-7),(-17,-1),(-13,-1),(-17,5)]):
 box('Produce island plinth',(x,y,.24),(2.6,3.4,.48),'deep evergreen',.04)
 box('Produce oak worktop',(x,y,.78),(2.85,3.65,.14),'oak light',.035)
 for xx in (-1.15,1.15):
  for yy in (-1.5,1.5):box('Island leg',(x+xx,y+yy,.53),(.13,.13,.8),'oak',.02)
 for ci,(xx,yy) in enumerate([(a,b) for a in (-.67,.67) for b in (-1.05,0,1.05)]):
  crate('Produce crate',x+xx,y+yy,.87,1.2,.95);fruit=['apple','green apple','orange','lemon','eggplant'][(ti+ci)%5]
  for a in range(5):
   for b in range(4):
    px=x+xx-.46+a*.225+random.uniform(-.02,.02);py=y+yy-.33+b*.22+random.uniform(-.02,.02);zz=1.15+random.uniform(-.01,.02)
    sc=(.098,.1,.1) if fruit!='eggplant' else (.075,.11,.16)
    sphere('PROP_'+fruit,(px,py,zz),sc,fruit)
    if (a+b)%4==0:cyl('Fruit stem',(px,py,zz+sc[2]),.009,.035,'oak',segments=12)
  if ci%2==0:
   box('Produce chalk ticket',(x+xx,y+yy-.5,1.21),(.52,.025,.21),'charcoal',.01)
   text('Produce price',f'{fruit.upper()}\n$ {1.49+ci*.5:.2f}',(x+xx,y+yy-.519,1.21),.055)
 # market sign
 box('Produce island upright sign',(x,y,1.8),(1.5,.08,.5),'deep evergreen',.02);text('Produce table sign','FRESHLY PICKED',(x,y-.05,1.8),.13)
# Herb planters and bag dispensers
for x,y in [(-20,-7),(-20,0),(-20,7)]:
 cyl('Herb pot',(x,y,.8),.25,.5,'cream paper');
 for k in range(15):
  a=k*2.4;xx=x+math.cos(a)*.18;yy=y+math.sin(a)*.18;sphere('Herb foliage',(xx,yy,1.18+random.random()*.2),(.12,.13,.22),'leaf')
print('STAGE: Bakery wall',flush=True)
# Bakery wall cases and center pastry display
use('13_Bakery')
for y in (10,13.5,16.5):
 box('Bakery cabinet base',(-20.5,y,.52),(2.2,2.8,1.04),'oak',.04)
 for z in (1.12,1.68,2.24):
  box('Bakery oak shelf',(-20.4,y,z),(2,2.65,.07),'oak light',.015)
  for a in range(3):
   for b in range(6):
    xx=-21+a*.57;yy=y-1.1+b*.43;sphere('PROP crusty loaf',(xx,yy,z+.13),(.23,.15,.12),'bread')
    for q in (-.09,.03,.14):tube('Bread scoring',[(xx+q-.05,yy-.08,z+.22),(xx+q+.04,yy+.07,z+.22)],.006,'cream paper')
 for yy in (-1.4,1.4):box('Bakery upright',(-20.45,y+yy,1.5),(2.2,.06,2.9),'oak',.015)
 box('Bakery top light',(-20.4,y,2.85),(1.7,2.6,.035),'warm LED',.01)
box('Bakery island',(-15.5,13,.5),(3.5,2.5,1),'deep evergreen',.05)
box('Bakery marble counter',(-15.5,13,1.05),(3.7,2.7,.13),'porcelain',.025)
for x in (-16.5,-15.5,-14.5):
 for y in (12.4,13.3):
  box('Baking tray',(x,y,1.14),(.8,.7,.03),'steel',.015)
  for k in range(6):sphere('PROP bakery roll',(x-.25+(k%3)*.25,y-.17+(k//3)*.3,1.24),(.11,.11,.09),'bread')
box('Bakery sneeze glass',(-15.5,13.9,1.6),(3.6,.025,.9),'architectural glass',.01)
use('30_Signage');text('Bakery wall brand','THE DAILY\nBAKE',(-21.82,13,3.7),.45,rot=(math.pi/2,0,math.pi/2))
print('STAGE: Refrigeration cabinets',flush=True)
# Refrigeration cabinets (individual doors, hinges, gaskets, shelves, lighting).
use('14_Chilled')
def fridge(x,y,length=3.2):
 box('Chilled case body',(x,y,1.55),(1.38,length,3.1),'charcoal',.04)
 box('Chilled enamel interior',(x-.12,y,1.55),(1.2,length-.14,2.8),'porcelain',.02)
 box('Chilled back',(x+.48,y,1.5),(.04,length-.1,2.7),'sage enamel',.005)
 for j in range(3):
  yy=y-length/2+.55+j*(length/3)
  for z in (.35,.9,1.45,2.0,2.55):
   box('Chilled wire shelf',(x-.15,yy,z),(1,length/3-.08,.025),'brushed steel',.004)
   for a in range(4):
    for b in range(4):product(12 if j%2==0 else 13,(x-.5+a*.22,yy-.36+b*.22,z+.02),-math.pi/2,kind='box' if j%2==0 else 'can',scale=.95)
  box('Glass refrigerator door',(x-.72,yy,1.53),(.028,length/3-.04,2.8),'architectural glass',.006)
  for z in (.12,2.94):box('Fridge door frame',(x-.75,yy,z),(.07,length/3,.06),'brushed steel',.01)
  for dy in (-length/6,length/6):box('Fridge upright gasket',(x-.75,yy+dy,1.53),(.07,.045,2.85),'charcoal',.008)
  tube('Refrigerator grab handle',[(x-.84,yy+.34,1.0),(x-.94,yy+.34,1.04),(x-.94,yy+.34,1.85),(x-.84,yy+.34,1.9)],.018,'brushed steel')
  box('Case vertical LED',(x-.57,yy-.48,1.52),(.03,.025,2.65),'LED',.004)
 box('Chilled header',(x-.76,y,3.05),(.08,length,.28),'deep evergreen',.02)
 text('Chilled section lettering','FRESH  /  CHILLED',(x-.811,y,3.05),.16,rot=(math.pi/2,0,-math.pi/2))
for y in (-11,-7,-3,1,13.5):fridge(21,y)
# Open low freezer islands create cover and cross-routing.
for y in (1,10):
 box('Freezer island',(16,y,.55),(2.1,4.2,1.1),'porcelain',.04);box('Freezer inset',(16,y,1.09),(1.85,3.95,.04),'charcoal',.015)
 for yy in (-1.05,1.05):box('Freezer sliding glass lid',(16,y+yy,1.13),(1.77,2,.025),'architectural glass',.012)
 for yy in (-1.6,-.8,0,.8,1.6):
  for x in (15.5,16,16.5):product(13,(x,y+yy,.88),kind='box')
print('STAGE: Checkout lanes',flush=True)
# Checkout lanes. Cash drawer, rollers, scanner, display, bag hooks, impulse stock.
use('15_Checkouts')
for i,x in enumerate((-5,1,7,13),1):
 y=-13
 box('Checkout base',(x,y,.5),(1.55,4.35,1),'deep evergreen',.06)
 box('Checkout stainless rim',(x,y,1.02),(1.68,4.5,.12),'brushed steel',.045)
 box('Rubber conveyor belt',(x,y+1.05,1.095),(1.34,1.95,.025),'black rubber',.025)
 for yy in [y+.18+j*.18 for j in range(11)]:box('Belt fine seam',(x,yy,1.11),(1.25,.008,.004),'charcoal',0)
 for yy in (y+.08,y+2.03):cyl('Conveyor roller',(x,yy,1.08),.05,1.33,'steel',(0,math.pi/2,0))
 box('Checkout scanner glass',(x,y-.35,1.092),(.55,.58,.025),'screen',.015)
 box('Bagging well',(x,y-1.5,1.08),(1.2,.85,.05),'charcoal',.025)
 box('POS pedestal',(x+.55,y-.75,1.34),(.08,.1,.5),'charcoal',.02)
 box('POS monitor',(x+.55,y-.75,1.63),(.55,.1,.36),'charcoal',.025,rot=(0,0,.1))
 box('POS screen',(x+.55,y-.813,1.63),(.49,.012,.3),'screen',.009,rot=(0,0,.1))
 text('Checkout interface','EVERGREEN\nTOTAL  $ 24.90',(x+.55,y-.826,1.64),.035,'cream paper')
 box('Card reader',(x-.64,y-.7,1.25),(.18,.22,.13),'charcoal',.02)
 box('Card reader screen',(x-.64,y-.72,1.323),(.13,.13,.008),'screen',.005)
 for j in range(3):box('Paper shopping bag',(x-.38+j*.3,y-1.6,1.35),(.25,.18,.5),'cream paper',.012)
 for j in range(3):tube('Paper bag handle',[(x-.45+j*.3,y-1.6,1.6),(x-.45+j*.3,y-1.6,1.72),(x-.31+j*.3,y-1.6,1.72),(x-.31+j*.3,y-1.6,1.6)],.008,'oak')
 cyl('Lane sign post',(x+.77,y+1.6,2.0),.025,2,'steel')
 box('Checkout lane sign',(x+.77,y+1.6,3.12),(.68,.13,.65),'amber',.035);text('Lane number',str(i).zfill(2),(x+.77,y+1.52,3.12),.39,'ink')
 for k in range(3):product((i*2+k)%16,(x-.42+k*.36,y+.6,1.12),random.uniform(-.15,.15))
 box('Impulse display',(x+1.65,y+.5,.63),(.62,1.45,1.26),'oak',.03)
 for z in (.5,.95,1.3):
  box('Impulse shelf',(x+1.65,y+.5,z),(.7,1.55,.04),'porcelain',.01)
  for k in range(5):product(14,(x+1.65,y-.12+k*.28,z+.025),math.pi/2,scale=.68)
print('STAGE: Shopping carts',flush=True)
# Shopping carts and baskets, actual wire structure and casters.
use('16_Carts_Baskets')
def wheel(x,y,z,r=.08):
 cyl('Rubber caster',(x,y,z),r,.045,'black rubber',(math.pi/2,0,0),24);cyl('Caster hub',(x,y-.025,z),r*.4,.052,'steel',(math.pi/2,0,0),20)
def cart(x,y,a=0):
 # cart assembled in local coordinates using a temporary transform parent
 before=set(CURRENT.objects)
 for xx in (-.27,.27):
  for yy in (-.4,.4):wheel(x+xx,y+yy,.12)
 tube('Cart lower frame',[(x-.3,y-.45,.23),(x-.3,y+.45,.23),(x+.3,y+.45,.23),(x+.3,y-.45,.23),(x-.3,y-.45,.23)],.018,'steel')
 for xx in (-.3,.3):tube('Cart handle frame',[(x+xx,y+.42,.2),(x+xx,y+.45,.98),(x+xx,y+.65,1.0)],.018,'steel')
 tube('Cart handle',[(x-.3,y+.65,1.0),(x+.3,y+.65,1.0)],.03,'deep evergreen')
 for z,w,d in [(.47,.25,.39),(.62,.28,.43),(.78,.31,.47),(.94,.34,.51)]:tube('Wire basket rim',[(x-w,y-d,z),(x+w,y-d,z),(x+w,y+d,z),(x-w,y+d,z),(x-w,y-d,z)],.009,'brushed steel')
 for j in range(13):
  yy=-.39+j*.065;tube('Wire cart basket',[(x-.34,y+yy*1.3,.94),(x-.25,y+yy,.47),(x+.25,y+yy,.47),(x+.34,y+yy*1.3,.94)],.006,'brushed steel')
 for j in range(9):
  xx=-.25+j*.0625;tube('Wire cart longitudinal',[(x+xx*1.35,y-.51,.94),(x+xx,y-.39,.47),(x+xx,y+.39,.47),(x+xx*1.35,y+.51,.94)],.006,'brushed steel')
 if a:
  for o in set(CURRENT.objects)-before:
   v=o.location-Vector((x,y,0));o.location=(x+v.x*math.cos(a)-v.y*math.sin(a),y+v.x*math.sin(a)+v.y*math.cos(a),v.z);o.rotation_euler.z+=a
for x,y in [(-16,-15),(-15.2,-15),(-14.4,-15),(-13.6,-15),(-10,-1),(18,5),(-10,13)]:cart(x,y)
for j in range(7):
 x=-11.8;y=-15;z=.15+j*.09
 box('Shopping basket base',(x,y,z),(.6,.4,.045),'sage enamel',.02)
 for yy in (-.2,.2):
  for k in range(9):box('Basket slot rib',(x-.28+k*.07,y+yy,z+.13),(.025,.035,.24),'sage enamel',.007)
 for xx in (-.3,.3):box('Basket end',(x+xx,y,z+.13),(.035,.42,.24),'sage enamel',.01)
 tube('Basket rim',[(x-.32,y-.22,z+.25),(x+.32,y-.22,z+.25),(x+.32,y+.22,z+.25),(x-.32,y+.22,z+.25),(x-.32,y-.22,z+.25)],.018,'sage enamel')
print('STAGE: Stockroom pallets',flush=True)
# Stockroom pallets/racks with labelled cartons.
use('20_Stockroom')
def pallet(x,y,z=0):
 for xx in (-.48,0,.48):box('Pallet stringer',(x+xx,y,z+.08),(.12,1.2,.16),'oak',.008)
 for yy in (-.52,-.26,0,.26,.52):box('Pallet deck board',(x,y+yy,z+.18),(1.2,.18,.065),'oak light',.008)
def carton(x,y,z,w=.55,d=.45,h=.4):
 box('PROP shipping carton',(x,y,z+h/2),(w,d,h),'cardboard',.012)
 box('Carton packing tape',(x,y,z+h+.003),(.07,d,.008),'tape',.002)
 box('Carton printed label',(x,y-d/2-.007,z+h*.6),(w*.55,.005,h*.36),'cream paper',.002)
 text('Carton handling text','EG / 014\nTHIS WAY UP',(x,y-d/2-.013,z+h*.6),min(w*.055,.04),'ink')
for x in (-20,-11,-2):
 for y in (22,27.5):
  for xx in (-1.7,1.7):
   for yy in (-.7,.7):box('Stock rack upright',(x+xx,y+yy,2),(.1,.1,4),'blue plastic',.015)
  for z in (.25,1.65,3.05):
   box('Warehouse shelf',(x,y,z),(3.5,1.6,.07),'oak',.01)
   for yy in (-.8,.8):box('Warehouse orange beam',(x,y+yy,z-.05),(3.6,.08,.17),'amber',.01)
   for xx in (-1.05,0,1.05):
    pallet(x+xx,y,z+.035)
    for zz in (0,.42):
     for dy in (-.28,.28):
      for dx in (-.25,.25):carton(x+xx+dx,y+dy,z+.3+zz,.46,.5,.39)
 # diagonal rear brace
 tube('Rack diagonal brace',[(x-1.7,y+.75,.3),(x+1.7,y+.75,3.9)],.025,'steel')
for x,y in [(-16,25),(-7,20),(3,28)]:
 pallet(x,y)
 for k in range(6):carton(x-.29+(k%2)*.58,y-.32+((k//2)%2)*.64,.23+(k//4)*.5,.55,.59,.48)
# cleaning station
box('Janitor trolley base',(4.7,21,.25),(1.2,.75,.12),'charcoal',.025)
for xx in (4.2,5.2):
 for yy in (20.75,21.25):wheel(xx,yy,.12)
for x in (4.4,5):cyl('Cleaning bucket',(x,21,.58),.23,.6,'yellow safety');cyl('Bucket dark opening',(x,21,.89),.2,.015,'charcoal')
for x in (4.2,4.5):tube('Mop handle',[(x,21.3,.3),(x+.2,21.3,1.7)],.015,'steel')
box('Folded wet floor sign',(5.6,20.9,.45),(.48,.08,.8),'yellow safety',.02,rot=(.16,0,0));text('Safety lettering','CAUTION\nWET FLOOR',(5.6,20.85,.5),.06,'ink')
# pallet jack
box('Pallet jack hydraulic body',(-7,25,.24),(.55,.55,.3),'yellow safety',.035)
for xx in (-7.35,-6.65):box('Pallet jack fork',(xx,24.25,.13),(.23,1.7,.13),'yellow safety',.025);wheel(xx,23.6,.12)
tube('Pallet jack handle',[(-7,25.1,.3),(-7,25.5,1.2),(-7.25,25.6,1.35),(-6.75,25.6,1.35),(-7,25.5,1.2)],.028,'black rubber')
print('STAGE: Staff room',flush=True)
# Staff room: kitchenette, dining, lockers, noticeboard, mugs, bins.
use('21_Staff_Room')
for x in (10,12,14,16,18,20):
 box('Staff locker',(x,29.35,1.05),(1.7,1,2.1),'sage enamel',.04)
 box('Locker recessed door',(x,28.82,1.06),(1.57,.04,1.94),'deep evergreen',.015)
 for z in (1.7,1.78,1.86):box('Locker vent',(x,28.79,z),(1.1,.015,.025),'charcoal',.002)
 box('Locker handle',(x+.57,28.75,1.05),(.035,.055,.25),'brushed steel',.009)
 text('Locker number',str(int(x-9)).zfill(2),(x,28.78,1.5),.1)
box('Staff kitchenette',(10,21.2,.45),(2.8,1.5,.9),'oak',.035)
box('Kitchen worktop',(10,21.2,.96),(3,1.65,.12),'porcelain',.025)
box('Kitchen sink',(9.3,21.2,1.025),(.8,.55,.015),'steel',.06)
tube('Kitchen tap',[(9.3,21.6,1.03),(9.3,21.6,1.4),(9.3,21.2,1.4),(9.3,21.2,1.26)],.018,'brushed steel')
box('Coffee machine',(10.8,21.3,1.32),(.5,.45,.6),'charcoal',.03)
box('Coffee front plate',(10.8,21.06,1.32),(.42,.025,.46),'brushed steel',.015)
box('Microwave',(10,21.35,1.22),(.85,.5,.42),'porcelain',.025);box('Microwave glass',(9.9,21.08,1.24),(.57,.02,.3),'charcoal',.015)
box('Staff table',(16,23.7,.79),(3.4,2,.12),'oak light',.04)
for xx in (-1.45,1.45):
 for yy in (-.75,.75):box('Table leg',(16+xx,23.7+yy,.39),(.09,.09,.78),'charcoal',.01)
for x,y,a in [(14.7,22,0),(16.9,22,0),(14.7,25.3,math.pi),(16.9,25.3,math.pi)]:
 box('Staff chair seat',(x,y,.47),(.58,.58,.08),'sage enamel',.05)
 box('Staff chair back',(x,y+(-.25 if a==0 else .25),.85),(.58,.07,.65),'sage enamel',.04)
 for xx in (-.23,.23):
  for yy in (-.23,.23):box('Chair steel leg',(x+xx,y+yy,.23),(.035,.035,.46),'steel',.007)
for x,y in [(14.9,23.5),(16.2,24),(17,23.2),(10.5,20.9)]:
 cyl('PROP ceramic mug',(x,y,.96 if x>12 else 1.14),.065,.15,'porcelain');tube('Mug handle',[(x+.06,y,.94 if x>12 else 1.12),(x+.12,y,.94 if x>12 else 1.12),(x+.12,y,1.03 if x>12 else 1.21),(x+.06,y,1.03 if x>12 else 1.21)],.012,'porcelain')
box('Notice board',(21.8,20.5,2),(.06,2.4,1.4),'oak',.02)
for j in range(7):box('Staff notice sheet',(21.76,19.6+(j%4)*.53,1.72+(j//4)*.5),(.015,.4,.4),'cream paper',.003)
for x,y in [(12,21),(20,26),(4,19)]:
 cyl('PROP utility bin',(x,y,.4),.28,.8,'charcoal');cyl('Bin lid',(x,y,.81),.3,.05,'sage enamel')
print('STAGE: Loading yard',flush=True)
# Loading yard: concrete dock, roller doors, pallets, waste, wall details and fence.
use('22_Loading_Yard')
box('Loading yard paving',(30,17,-.03),(16,26,.15),'concrete',.02)
for y in (4.5,29.5):box('Yard safety stripe',(30,y,.055),(15,.13,.01),'yellow safety',0)
# staff-yard doorway remains an open 3 m walking connection, marked by jambs
for y in (6.5,9.5,23.5,26.5):box('Yard portal steel jamb',(22.15,y,1.55),(.3,.16,3.1),'charcoal',.025)
for y in (8,25):
 box('Roller shutter housing',(22.17,y,3.35),(.4,3.4,.5),'steel',.03)
 for z in (3.14,3.24,3.34,3.44,3.54):box('Raised roller shutter slat',(22.39,y,z),(.04,3.2,.05),'brushed steel',.008)
 box('Loading threshold',(22.2,y,.06),(.8,3,.12),'brushed steel',.015)
for x in (25,28,31):
 for y in (14,18):
  for j in range(3):pallet(x,y,j*.23)
  if (x+y)%2:
   for k in range(4):carton(x-.3+(k%2)*.6,y-.3+(k//2)*.6,.7,.55,.55,.6)
for y in (21,24):
 box('Commercial refuse container',(35,y,.75),(1.8,2.1,1.4),'deep evergreen',.06)
 box('Dumpster lid',(35,y,1.5),(1.95,2.2,.13),'charcoal',.035,rot=(0,.06,0))
 for xx in (-.7,.7):
  for yy in (-.8,.8):wheel(35+xx,y+yy,.1)
 text('Recycling label','RECYCLE',(35,y-1.065,.95),.16)
for y in range(4,31,3):
 cyl('Fence post',(38,y,1.4),.035,2.8,'steel');
for z in (.35,1.4,2.5):tube('Fence rails',[(38,4,z),(38,30,z)],.013,'steel')
# Chain mesh impression from diagonal wires, real geometry.
for y in [4+i*.3 for i in range(87)]:
 tube('Fence diagonal wire',[(38,y,.2),(38,min(30,y+1.4),2.65)],.0035,'steel')
 tube('Fence cross wire',[(38,y,2.65),(38,min(30,y+1.4),.2)],.0035,'steel')
for y in (11,27):
 box('Exterior wall lamp',(22.3,y,3.2),(.2,.5,.2),'charcoal',.02);area('Dock light',(22.7,y,3.15),150,1,(1,.8,.5),(27,y,0))
print('STAGE: signage, brand',flush=True)
# signage, brand lettering and wall graphics
use('30_Signage')
text('Evergreen storefront logo','EVERGREEN',(0,-18.17,4.66),.68)
text('Front canopy tagline','MARKET   /   GOOD FOOD. EVERY DAY.',(0,-21.32,4.2),.18)
for x,y,s in [(-15.5,-9.9,'FARM FRESH'),(0,17.67,'GOOD FOOD. EVERY DAY.'),(15,17.66,'DAIRY & CHILLED')]:
 if x==-15.5:
  box('Produce overhead board',(x,y,3.1),(5,.1,.8),'deep evergreen',.03);text('Produce header',s,(x,y-.065,3.12),.37)
 else:text('Rear department heading',s,(x,y,3.8),.37)
for x,s in [(-14,'WAREHOUSE  A'),(3,'STOCK  /  SERVICE'),(15,'TEAM ROOM')]:text('Service wayfinding',s,(x,17.65,3.43),.19)
for x in (-14,3):
 box('Service swing door bumper',(x-1.25,18,1),(.2,.35,2),'sage enamel',.02)
box('Yard wayfinding',(21.65,8,3.6),(.08,2.8,.55),'deep evergreen',.02);text('Yard direction','LOADING  /  EXIT',(21.59,8,3.6),.18,rot=(math.pi/2,0,-math.pi/2))
text('Staff welcome','TAKE A BREAK',(16,29.81,3.7),.4)
for x in (-14,3,15):
 box('Emergency exit sign',(x,17.6,2.95),(.68,.13,.24),'deep evergreen',.01);text('Exit lettering','EXIT  →',(x,17.52,2.95),.12,'white label')
# Fire extinguisher details in three readable locations.
for x,y in [(-21.65,-12),(7.6,21),(21.6,15.9)]:
 cyl('Fire extinguisher',(x,y,.8),.1,.5,'red plastic');box('Extinguisher bracket',(x,y+.04,1.1),(.12,.08,.1),'charcoal',.01);tube('Extinguisher hose',[(x+.05,y,1.05),(x+.17,y,.95),(x+.15,y,.6)],.012,'black rubber')
# Navigation annotations stored as non-rendering empties, never masquerade as gameplay.
use('90_Gameplay_Notes')
for name,loc in [('SPAWN_SUGGESTION_HUNTERS',(0,-16,1)),('SPAWN_SUGGESTION_HIDERS',(-11,12,1)),('LOOP_A_SHOP_STOCK',(-14,18,1)),('LOOP_B_STOCK_SHOP',(3,18,1)),('LOOP_C_SHOP_STAFF',(15,18,1)),('LOOP_D_STAFF_YARD',(22,25,1)),('LOOP_E_YARD_SHOP',(22,8,1))]:
 o=link_obj(name,None,loc);o.empty_display_type='ARROWS';o.empty_display_size=.5;o.hide_render=True;o['status']='Layout suggestion only; no collision/navigation/gameplay authored'
scene['Project']='EVERGREEN MARKET | original detailed prop-hunt environment'
scene['Scale']='1 Blender unit = 1 metre; 44m × 48m building, 16m × 26m side yard'
scene['Design assumption']='8–12 players; requires actual playtesting and size tuning in Unreal'
scene['Gameplay']='Environment only. No game mode, replication, collision, NavMesh, shooting or disguise logic.'
scene['Art assets']='All geometry and labels procedurally authored for this deliverable; no external marketplace assets.'
scene['Preview note']='Cutaway previews hide roof and selected shell. Master saved with full roof visible.'
print('STAGE: Cameras',flush=True)
# Cameras
use('50_Cameras')
def camera(name,loc,target,lens=25,ortho=None):
 d=bpy.data.cameras.new(name);o=link_obj(name,d,loc);o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=300
 if ortho:d.type='ORTHO';d.ortho_scale=ortho
 return o
CAMS={}
CAMS['01_Interior_Hero']=camera('CAM_Interior_Hero',(-19,-15.8,4.0),(-1,5,1.8),21)
CAMS['02_Produce_Bakery']=camera('CAM_Produce_Bakery',(-20,-9.5,2.7),(-14,9,1.6),25)
CAMS['03_Checkouts']=camera('CAM_Checkouts',(-10,-17,2.5),(8,-12,1.1),24)
CAMS['04_Stockroom']=camera('CAM_Stockroom',(5,19.8,2.8),(-14,26,1.6),23)
CAMS['05_Staff_Room']=camera('CAM_Staff_Room',(20,19.4,2.7),(13,25,1.3),25)
CAMS['06_Exterior']=camera('CAM_Exterior',(43,-51,26),(3,3,1.5),38)
CAMS['07_Cutaway']=camera('CAM_Cutaway',(57,-65,66),(5,5,0),45,79)
CAMS['08_Topdown']=camera('CAM_Topdown',(5,6,82),(5,6,0),45,70)
# Nice viewport default.
scene.camera=CAMS['01_Interior_Hero']
for a in bpy.data.screens:
 for ar in a.areas:
  if ar.type=='VIEW_3D':
   ar.spaces.active.clip_end=300;ar.spaces.active.region_3d.view_distance=55;ar.spaces.active.region_3d.view_location=(0,4,1)
# Pack fonts/images and save before any expensive renders.
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Evergreen_Market.blend'),compress=True)
manifest={'project':'Evergreen Market','blender_version':bpy.app.version_string,'seed':19,'metres_per_unit':1,'building_m':[44,48,5.45],'yard_m':[16,26],'player_assumption':'8–12; untested','collections':{c.name:len(c.objects) for c in scene.collection.children},'object_count':len(scene.objects),'mesh_datablocks':len(bpy.data.meshes),'material_count':len(bpy.data.materials),'image_count':len(bpy.data.images),'cameras':list(CAMS),'gameplay_implemented':False}
with open(OUT/'manifest.json','w') as f:json.dump(manifest,f,indent=2)
print('BUILD_COMPLETE',json.dumps(manifest),flush=True)
if '--no-render' not in sys.argv:
 scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.cycles.samples=32
 for name in ['01_Interior_Hero','07_Cutaway']:
  scene.camera=CAMS[name]
  if name=='07_Cutaway':COLS['03_Roof_Ceiling'].hide_render=True;COLS['01_Shell'].hide_render=True;COLS['02_Front_Glazing'].hide_render=True
  scene.render.filepath=str(PRE/(name+'_draft.png'));bpy.ops.render.render(write_still=True);print('RENDER_COMPLETE',name,flush=True)
print('DONE',flush=True)
