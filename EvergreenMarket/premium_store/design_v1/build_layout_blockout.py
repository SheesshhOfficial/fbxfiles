import bpy, math, os, json
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection' and c.users == 0: bpy.data.collections.remove(c)
base=bpy.data.collections.get('Collection'); base.name='00_STRUCTURE_BLOCKOUT'
cols={}
for name in ['01_FIXTURES_BLOCKOUT','02_PLACEHOLDERS_NOT_GAMEPLAY','03_STOCK_STAFF','04_SIGNAGE','05_CAMERAS','06_OVERLAYS']:
 c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); cols[name]=c
cols[base.name]=base
mats={}
def mat(name, rgb):
 m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); mats[name]=m; return m
mat('Cream stone',(.75,.71,.61));mat('Ivory plaster',(.85,.82,.73));mat('Warm oak',(.44,.25,.11));mat('Walnut',(.22,.12,.055));mat('Black metal',(.055,.063,.06));mat('Evergreen',(.075,.20,.14));mat('Sage',(.38,.48,.32));mat('Chilled pale blue',(.45,.64,.64));mat('Glass proxy',(.27,.48,.48));mat('Brass',(.64,.48,.22));mat('Stock concrete',(.48,.50,.47));mat('Cafe floor',(.63,.49,.32));mat('White',(.94,.93,.87));mat('Produce green',(.33,.48,.13));mat('Produce orange',(.85,.37,.08));mat('Produce red',(.58,.17,.10));mat('Box kraft',(.57,.40,.22));mat('Package cream',(.82,.75,.52));mat('Package green',(.17,.34,.24));mat('Package red',(.58,.23,.14));mat('Package blue',(.20,.34,.40));mat('Route',(.66,.72,.60));mat('Floral',(.65,.38,.45))
count=0
def move(obj,col):
 for c in list(obj.users_collection): c.objects.unlink(obj)
 cols[col].objects.link(obj)
def cube(name,loc,scale,material,col='01_FIXTURES_BLOCKOUT',bevel=0):
 global count; count+=1
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=f'{name}_{count:04d}'; o.dimensions=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(mats[material]);move(o,col);o['stage']='LAYOUT_BLOCKOUT';o['gameplay_ready']=False
 if bevel:
  mod=o.modifiers.new('Blockout edge softening','BEVEL');mod.width=bevel;mod.segments=2
  mod=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def cyl(name,loc,r,depth,material,col='01_FIXTURES_BLOCKOUT',verts=12):
 global count; count+=1
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=f'{name}_{count:04d}';o.data.materials.append(mats[material]);move(o,col);o['stage']='LAYOUT_BLOCKOUT';return o
def text(name,body,loc,size,material='Evergreen',rotation=(0,0,0),align='CENTER',col='04_SIGNAGE'):
 curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.align_x=align;curve.size=size;curve.extrude=.001
 o=bpy.data.objects.new(name,curve);cols[col].objects.link(o);o.location=loc;o.rotation_euler=rotation;curve.materials.append(mats[material]);return o
def floor_label(body,x,y,size=.75):return text('Zone '+body,body,(x,y,.027),size)
def sign(body,x,y,width=4):
 cube('Sign backing '+body,(x,y,2.75),(width,.10,.68),'Evergreen');text('Sign '+body,body,(x,y-.06,2.53),.34,'White',(math.pi/2,0,0))
def shelf(x,y,length=9.2,height=1.9,col='01_FIXTURES_BLOCKOUT',stock=True):
 cube('Shelf plinth',(x,y,.15),(1.6,length,.30),'Walnut',col)
 cube('Shelf spine',(x,y,height/2),(.13,length,height),'Black metal',col)
 for end in [-1,1]:cube('Oak end panel',(x,y+end*(length/2-.075),height/2),(1.6,.15,height),'Warm oak',col)
 for z in [.4,.85,1.30,1.75]:
  cube('Shelf tier',(x,y,z),(1.6,length-.2,.10),'Warm oak',col)
  if stock:
   for j in range(6):
    yy=y-length/2+.65+j*(length-1.3)/5
    for s in [-1,1]:
     palette=['Package cream','Package green','Package red','Package blue'];mm=palette[(j+int(x)+int(z*5))%4]
     cube('Abstract package group',(x+s*.49,yy,z+.24),(.43,.60,.38),mm,'02_PLACEHOLDERS_NOT_GAMEPLAY')
def counter(name,x,y,w,d=1.7,m='Warm oak',glass=False):
 cube(name,(x,y,.55),(w,d,1.10),m,bevel=.04);cube(name+' worktop',(x,y,1.14),(w+.10,d+.1,.12),'Cream stone')
 if glass:
  cube(name+' display proxy',(x,y-.12,1.42),(w-.15,d-.40,.45),'Glass proxy');cube(name+' top',(x,y,1.68),(w,d,.08),'Black metal')
def chair(x,y,rot=0):
 o=cube('Cafe chair seat',(x,y,.48),(.55,.55,.12),'Warm oak');
 for dx in [-.2,.2]:
  for dy in [-.2,.2]: cube('Chair leg',(x+dx,y+dy,.23),(.055,.055,.46),'Black metal')
 cube('Cafe chair back',(x,y+.24,.82),(.55,.09,.55),'Warm oak')
# Envelope and preserved route surfaces
cube('64 x 56 m floor',(32,28,-.15),(64,56,.30),'Cream stone','00_STRUCTURE_BLOCKOUT')
cube('Cafe finish',(6,8,.008),(12,16,.016),'Cafe floor','00_STRUCTURE_BLOCKOUT')
cube('Staff floor',(32,50,.008),(64,12,.016),'Stock concrete','00_STRUCTURE_BLOCKOUT')
# Roof intentionally absent for approval; front and left facade cut low for view.
for name,loc,sc in [('Right exterior',(64,28,1.65),(.24,56,3.3)),('Rear exterior',(32,56,1.65),(64,.24,3.3)),('Left cutaway',(0,28,.42),(.24,56,.84)),('Front left cutaway',(20,0,.42),(40,.24,.84)),('Front right cutaway',(56,0,.42),(16,.24,.84))]:cube(name,loc,sc,'Ivory plaster','00_STRUCTURE_BLOCKOUT')
# Floor route stripes thin and flush, not collision objects.
for x,y,w,d in [(32,12,40,4),(32,26,32,4),(14,27,4,26),(50,27,4,26),(32,42,64,4)]:cube('4m route tint',(x,y,.012),(w,d,.008),'Route','00_STRUCTURE_BLOCKOUT')
floor_label('FRONT LOOP / 4 m',32,11,.65);floor_label('CROSS AISLE / 4 m',32,25.7,.65);floor_label('REAR LOOP / 4 m',32,41.6,.70)
floor_label('ENTRY',44,1.3,.80)
# Central two banks: ends preserve Y10-14 /24-28 /36-40 links.
for x in [17.0,21.4,25.8,30.2,34.6,39.0,43.4,47.0]:
 shelf(x,19,9.2);shelf(x,32,7.2)
for x,body in [(19.2,'PANTRY'),(28,'SNACKS'),(36.8,'CEREAL'),(45,'EVERYDAY')]:sign(body,x,14.6,3.5)
# Front checkouts leave entry/bypass and the full front cross-aisle open.
for x in [17,23,29,35]:
 counter('Checkout island',x,5.0,1.8,4.6,'Warm oak');cube('Checkout conveyor',(x,4.4,1.23),(1.35,2.0,.08),'Black metal');cube('Till',(x+.35,6.55,1.55),(.45,.25,.55),'Black metal');sign('CHECKOUT',x,7.5,3.0)
counter('Customer service',36,1.7,5,1.9,'Evergreen');floor_label('SERVICE',35,3.0,.65)
for x in [42,43.4,44.8]:
 cube('Basket station',(x,6,.35),(.9,1.3,.7),'Black metal');cube('Basket insert',(x,6,.69),(.78,1.17,.08),'Sage')
# Cafe, furniture recognizable but explicitly non-final.
counter('Cafe counter',4,2.3,6,2,'Walnut',True);sign('COFFEE + PATISSERIE',5,3.5,8.0)
for x,y in [(3,7),(8,7),(3,12),(8,12)]:
 cyl('Cafe pedestal',(x,y,.38),.14,.76,'Black metal');cyl('Cafe table',(x,y,.81),.85,.14,'Warm oak',verts=20)
 chair(x,y-1.25);chair(x,y+1.1)
floor_label('CAFE',6,15,.95)
# Produce low islands X0-12/Y16-32
for x in [3,8.5]:
 for y in [19,24,29]:
  counter('Produce island',x,y,3.6,2.6,'Warm oak')
  for dx in [-.9,0,.9]:
   for dy in [-.65,.15,.75]:
    cyl('Produce mound',(x+dx,y+dy,1.34),.35,.35,['Produce green','Produce orange','Produce red'][int((dx+1)*4+dy*3)%3],'02_PLACEHOLDERS_NOT_GAMEPLAY')
floor_label('PRODUCE + FRESH',6,16.2,.64)
# Bakery rear-left, access to rear at Y40.
counter('Bakery display',6,35,8,2,'Warm oak',True);shelf(1.3,36.3,5.0,2.3,stock=False);sign('BAKERY',6,38.1,7)
for x in [3,4.5,6,7.5,9]:cyl('Bread proxy',(x,35,1.85),.32,.24,'Package cream','02_PLACEHOLDERS_NOT_GAMEPLAY')
# Right florist / beverages
for x,y in [(55,4),(60,4),(55,8.5),(60,8.5)]:
 cyl('Flower stand',(x,y,.45),.83,.9,'Walnut');cyl('Flower foliage',(x,y,1.1),.67,.4,'Sage');cyl('Bloom proxy',(x,y,1.4),.45,.35,'Floral','02_PLACEHOLDERS_NOT_GAMEPLAY')
floor_label('FLORIST',58,10.5,.80)
for x in [55,60]:shelf(x,18,8.5,1.85,stock=True)
sign('WINE + BEVERAGES',58,22.7,9)
# Separate deli / meat-fish islands with rear prep route.
counter('Deli cheese counter',57.6,27.1,8.7,2.0,'Evergreen',True);sign('DELI + CHEESE',58,29.5,8)
counter('Butcher seafood counter',57.6,34.3,8.7,2.0,'Walnut',True);sign('BUTCHER + SEAFOOD',58,37,9)
for y in [28.5,35.8]:counter('Right prep backdrop',62.4,y,1.6,4.8,'Black metal')
# Chilled X16-48, with wide walk-throughs to rear loop; NEVER in 12-16 or48-52.
for x,w in [(19.0,6),(29.0,6),(39.0,6),(46,4)]:
 cube('Chilled island',(x,38,.88),(w,2.1,1.76),'Chilled pale blue');cube('Chilled top',(x,38,1.8),(w,2.1,.12),'Black metal')
 for xx in [x-w/2+.55+k*1.1 for k in range(int(w/1.1))]:cube('Chilled door proxy',(xx,36.93,.96),(.96,.045,1.38),'Glass proxy')
floor_label('DAIRY / CHILLED / FROZEN',32,39.4,.65)
# Rear staff boundary at44, staff spine44-47, many visible openings.
for x,w in [(5,10),(26,18),(46,10),(61,6)]:cube('Staff boundary',(x,44,1.45),(w,.16,2.9),'Ivory plaster','00_STRUCTURE_BLOCKOUT')
for x in [13.5,38,55]:floor_label('STAFF',x,44.8,.55)
# Staff storage racks: open spine and rear crossroute; clear loop around each rack.
for x in [5,12,19,26,33]:
 shelf(x,50.4,4.7,2.6,'03_STOCK_STAFF',False)
 for z in [.55,1.35,2.05]:
  for yy in [48.8,50.4,52]:cube('Stock box',(x,yy,z),(1.2,1.15,.6),'Box kraft','03_STOCK_STAFF')
floor_label('RECEIVING + STOCK',19,54.5,.75)
# Cold room proxy with dual openings to spine/rear loop, pale surfaces.
for name,loc,sc in [('Cold room side',(39.5,50.7,1.4),(.16,7.4,2.8)),('Cold room rear',(36.3,54.4,1.4),(6.4,.16,2.8)),('Cold room front stub',(37.9,47,1.4),(3.2,.16,2.8))]:cube(name,loc,sc,'Chilled pale blue','03_STOCK_STAFF')
floor_label('COLD',36.1,52,.6)
# Staff area and utilities with openings front and back.
for x in [42,53]:cube('Staff room divider',(x,50.2,1.4),(.16,6.4,2.8),'Ivory plaster','03_STOCK_STAFF')
for x in [46,49]:counter('Office desk',x,49.5,2.2,1.2,'Warm oak');chair(x,50.7)
counter('Break kitchenette',48,53.4,7,1.0,'Evergreen')
for x in [56,59,62]:cube('Utility cabinet',(x,53,1.2),(1.8,1.4,2.4),'Stock concrete','03_STOCK_STAFF')
floor_label('STAFF / OFFICE',47.5,47.3,.5);floor_label('UTILITIES',58.5,48,.60)
# Minimal scale markers, abstract silhouettes 1.8m high in clear areas.
for x,y in [(44,9),(14,25.8),(50,41.8)]:
 cyl('Scale marker torso',(x,y,1.05),.22,.8,'Evergreen','02_PLACEHOLDERS_NOT_GAMEPLAY')
 cyl('Scale marker head',(x,y,1.65),.16,.3,'Brass','02_PLACEHOLDERS_NOT_GAMEPLAY')
 for dx in [-.1,.1]:cyl('Scale marker leg',(x+dx,y,.39),.08,.75,'Black metal','02_PLACEHOLDERS_NOT_GAMEPLAY')
# Cameras and render settings.
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
s=scene.display.shading;s.light='STUDIO';s.studio_light='paint.sl';s.color_type='MATERIAL';s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.curvature_ridge_factor=1.5;s.curvature_valley_factor=1.2;s.cavity_ridge_factor=1.2;s.cavity_valley_factor=1.2;s.show_specular_highlight=True;s.background_type='WORLD';scene.world.color=(.88,.87,.83);s.show_object_outline=True;s.object_outline_color=(.12,.13,.11)
scene.display.render_aa='16';scene.view_settings.view_transform='Standard'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['status']='LAYOUT APPROVAL BLOCKOUT ONLY';scene['interior_envelope_m']='64 x 56';scene['implemented']='Single floor; department reservations; two shelf banks; 4m front/central/rear circulation; staff spine; furnishings proxies';scene['not_implemented']='Final art, detailed products/brands, UVs/textures, Unreal export, collision validation, prop transformation eligibility, gameplay/network/performance tests, production lighting'
def camera(name,loc,target,ortho=None,lens=28):
 data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);cols['05_CAMERAS'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.clip_end=400;data.lens=lens
 if ortho:data.type='ORTHO';data.ortho_scale=ortho
 return o
cam_a=camera('Aerial layout approval',(85,-67,85),(32,28,0),ortho=100)
cam_b=camera('Interior aisle approval',(28.0,9.5,2.25),(28,39,1.70),lens=19)
# Camera-facing title is geometry, so BLOCKOUT is visibly burnt into each render.
def overlay(cam,subtitle):
 if cam.data.type=='ORTHO':w=cam.data.ortho_scale;depth=1;size=.94
 else:depth=1;w=2*depth*math.tan(cam.data.angle_x/2);size=w*.0100
 h=w*scene.render.resolution_y/scene.render.resolution_x
 panel=cube('Approval banner',(0,0,0),(w,h*.090,.001),'White','06_OVERLAYS');panel.parent=cam;panel.location=(0,h*.455,-depth-.006);panel.rotation_euler=(0,0,0)
 t=text('BLOCKOUT title','EVERGREEN MARKET | LAYOUT BLOCKOUT',(-w*.475,h*.462,-depth),size,'Evergreen',align='LEFT',col='06_OVERLAYS');t.parent=cam;t.location=(-w*.475,h*.465,-depth)
 t2=text('Approval subtitle',subtitle,(-w*.475,h*.429,-depth),size*.68,'Black metal',align='LEFT',col='06_OVERLAYS');t2.parent=cam;t2.location=(-w*.475,h*.433,-depth)
 return [panel,t,t2]
ola=overlay(cam_a,'64 x 56 m | Single-floor layout approval | Placeholder fixtures and stock | No gameplay validation')
olb=overlay(cam_b,'Aisle-level layout approval | Warm wood / pale stone / dark metal palette study | Final artwork not implemented')
for ob in ola+olb:ob.hide_render=True
scene.camera=cam_a
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'EVERGREEN_LAYOUT_BLOCKOUT_v1.blend'))
for cam,ols,fn in [(cam_a,ola,'EVERGREEN_BLOCKOUT_AERIAL.png'),(cam_b,olb,'EVERGREEN_BLOCKOUT_AISLE.png')]:
 scene.camera=cam
 for ob in ola+olb:ob.hide_render=ob not in ols
 scene.render.filepath=os.path.join(ROOT,fn);bpy.ops.render.render(write_still=True)
scene.camera=cam_a
for ob in ola+olb:ob.hide_render=ob not in ola
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'EVERGREEN_LAYOUT_BLOCKOUT_v1.blend'))
print('BLOCKOUT_COMPLETE',count)
