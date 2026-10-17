import bpy, math, random, os, sys, json
from mathutils import Vector
from math import pi, sin, cos
random.seed(17)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,ROOT+'/source')
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for d in bpy.data.materials: bpy.data.materials.remove(d)
mats={}
def material(name,color,metal=0,rough=.6,emit=0):
 m=bpy.data.materials.new(name); m.use_nodes=True; p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
 if emit: p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emit
 path=ROOT+'/textures/'+name+'_basecolor.png'
 if os.path.exists(path):
  for kind,input,color_space in [('basecolor','Base Color','sRGB'),('roughness','Roughness','Non-Color'),('normal','Normal','Non-Color')]:
   n=m.node_tree.nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(ROOT+'/textures/'+name+'_'+kind+'.png'); n.image.colorspace_settings.name=color_space
   if kind=='normal':
    b=m.node_tree.nodes.new('ShaderNodeNormalMap'); b.inputs['Strength'].default_value=.35; m.node_tree.links.new(n.outputs['Color'],b.inputs['Color']); m.node_tree.links.new(b.outputs['Normal'],p.inputs[input])
   else: m.node_tree.links.new(n.outputs['Color'],p.inputs[input])
 mats[name]=m; return m
for n,c,me,ro in [('wood',(.14,.10,.055),0,.85),('rust',(.25,.1,.035),.65,.7),('cream',(.6,.5,.32),.15,.7),('red',(.4,.03,.02),.35,.4),('teal',(.03,.2,.18),.4,.45),('concrete',(.2,.21,.18),0,.85),('ground',(.08,.09,.065),0,.86),('gold',(.5,.29,.065),.7,.37),('black',(.015,.018,.019),.1,.52),('leaf',(.045,.12,.032),0,.72),('glass',(.15,.24,.28),.7,.13)]: material(n,c,me,ro)
material('bulb',(1,.45,.12),0,.3,5); material('neon',(.1,.7,1),0,.3,4); material('paper',(.55,.44,.27),0,.9); material('pink',(.55,.11,.27),0,.7)
def finish(o,n,mat):
 o.name=n
 if mat: o.data.materials.append(mats.get(mat,mat) if isinstance(mat,str) else mat)
 return o
def cube(n,loc,scale,mat,bevel=.03):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=finish(bpy.context.object,n,mat); o.dimensions=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel: mod=o.modifiers.new('Edge wear bevel','BEVEL'); mod.width=bevel; mod.segments=2; mod=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def cyl(n,loc,radius,depth,mat,vertices=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc); o=finish(bpy.context.object,n,mat)
 b=o.modifiers.new('Edge bevel','BEVEL'); b.width=min(.02,radius*.08); b.segments=2
 return o
def sphere(n,loc,scale,mat):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=loc); o=finish(bpy.context.object,n,mat); o.scale=scale
 for p in o.data.polygons: p.use_smooth=True
 return o
def beam(n,a,b,r,mat):
 a,b=Vector(a),Vector(b); o=cyl(n,(a+b)/2,r,(b-a).length,mat,12); o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); return o
def torus(n,loc,major,minor,mat):
 bpy.ops.mesh.primitive_torus_add(major_segments=24,minor_segments=8,location=loc,major_radius=major,minor_radius=minor); return finish(bpy.context.object,n,mat)
from fast_geometry import make_api
cube,cyl,sphere,beam,torus=make_api(mats)
def text(n,body,loc,size,mat,rotation=(pi/2,0,0)):
 cu=bpy.data.curves.new(n,'FONT'); cu.body=body; cu.align_x='CENTER'; cu.size=size; cu.extrude=.009; cu.bevel_depth=.002; o=bpy.data.objects.new(n,cu); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler=rotation; finish(o,n,mat); return o
def light(n,loc,power,color,size=1,kind='POINT'):
 d=bpy.data.lights.new(n,kind); d.energy=power; d.color=color
 if kind=='AREA': d.shape='DISK'; d.size=size
 else: d.shadow_soft_size=size
 o=bpy.data.objects.new(n,d); bpy.context.collection.objects.link(o); o.location=loc; return o
def wire(n,pts,r,mat):
 c=bpy.data.curves.new(n,'CURVE'); c.dimensions='3D'; c.bevel_depth=r; c.bevel_resolution=1; s=c.splines.new('POLY'); s.points.add(len(pts)-1)
 for p,co in zip(s.points,pts):p.co=(*co,1)
 o=bpy.data.objects.new(n,c); bpy.context.collection.objects.link(o); finish(o,n,mat); return o
def sign(n,body,loc,w,h,size):
 x,y,z=loc; cube(n+' backing',loc,(w,.14,h),'cream');
 for dx in [-w/2,w/2]:cube(n+' frame',(x+dx,y-.1,z),(.08,.08,h+.14),'rust')
 for dz in [-h/2,h/2]:cube(n+' frame',(x,y-.1,z+dz),(w,.08,.08),'rust')
 text(n+' lettering',body,(x,y-.085,z-size*.36),size,'red')
 for dx in [-w*.35,w*.35]:cube(n+' mounting',(x+dx,y+.12,z-.7),(.08,.12,1.5),'rust')
def barrel(n,x,y,z=0):
 o=cyl(n+' shell',(x,y,z+.48),.34,.96,'rust');
 for zz in [.12,.82]:torus(n+' hoop',(x,y,z+zz),.345,.025,'black')
 cyl(n+' lid',(x,y,z+.97),.32,.025,'rust'); o['PropActorTag']=True; return o
def bottle(n,x,y,z):
 cyl(n+' body',(x,y,z+.14),.065,.27,'glass',16); cyl(n+' neck',(x,y,z+.32),.028,.12,'glass',12); cyl(n+' cap',(x,y,z+.39),.03,.025,'rust',12)
def teddy(n,x,y,z):
 for suf,loc,sc in [('body',(x,y,z+.23),(.16,.11,.21)),('head',(x,y,z+.5),(.145,.12,.14)),('earL',(x-.11,y,z+.61),(.06,.05,.06)),('earR',(x+.11,y,z+.61),(.06,.05,.06)),('armL',(x-.2,y,z+.26),(.08,.08,.16)),('armR',(x+.2,y,z+.26),(.08,.08,.16)),('legL',(x-.1,y-.07,z+.07),(.09,.12,.09)),('legR',(x+.1,y-.07,z+.07),(.09,.12,.09))]:sphere(n+' '+suf,loc,sc,'cream')
 for xx in [x-.05,x+.05]:sphere(n+' eye',(xx,y-.116,z+.52),(.018,.015,.018),'black')
 sphere(n+' snout',(x,y-.125,z+.47),(.05,.035,.033),'wood')
def booth(n,x,y,label,clr):
 # South-facing, 4m frontage, open counter with generous rear side access.
 cube(n+' foundation',(x,y,.12),(4.3,3.3,.24),'concrete')
 for ix in range(21):
  xx=x-2+ix*.2; cube(n+' back plank',(xx,y+1.45,1.6),(.185,.1,3),'wood',.008)
  cube(n+' front skirt',(xx,y-1.4,.7),(.185,.12,1.1),clr if ix%2 else 'cream',.006)
 for sx in [-1,1]:
  for iy in range(9):cube(n+' side board',(x+sx*2,y-.1+iy*.18,1.6),(.1,.17,3),'wood',.005)
  for yy in [-1.4,1.4]:cube(n+' corner post',(x+sx*2,y+yy,1.65),(.16,.16,3.2),'wood')
 cube(n+' counter',(x,y-1.45,1.3),(4.25,.6,.13),'wood')
 for z in [1.3,2.05]:cube(n+' shelf',(x,y+1.15,z),(3.85,.55,.1),'wood')
 for xx in [-1.75,1.75]:beam(n+' brace',(x+xx,y-1.4,2.25),(x+xx*.65,y-1.4,3.0),.055,'wood')
 for ix in range(22):
  o=cube(n+' roof strip',(x-2.2+ix*.21,y,3.25),(.22,3.6,.06),'rust',.006); o.rotation_euler.x=.08
 sign(n,label,(x,y-1.58,3.2),3.7,.65,.43)
 for i in range(11):sphere(n+' marquee bulb',(x-1.9+i*.38,y-1.73,3.65),(.045,.045,.065),'bulb')
 light(n+' warm spill',(x,y-1.7,2.65),110,(1,.5,.19),.65)
 for j in range(7):
  bottle(n+' bottle'+str(j),x-1.4+j*.35,y-1.47,1.37)
  teddy(n+' prize'+str(j),x-1.45+j*.48,y+1,2.1)
 for j in range(2):
  xx=x-1+j*2; cyl(n+' stool seat',(xx,y-2.2,.73),.24,.09,'wood')
  for a in range(3):beam(n+' stool leg',(xx+cos(a*2*pi/3)*.15,y-2.2+sin(a*2*pi/3)*.15,.7),(xx+cos(a*2*pi/3)*.22,y-2.2+sin(a*2*pi/3)*.22,.15),.025,'rust')
 barrel(n+' bin',x+2.45,y-1.25)
print('PHASE ground and midway',flush=True)
# Physical ground and perimeter
cube('Ground playable base',(0,0,-.18),(52,52,.35),'ground',.02)
for x in [-26,26]:
 for y in range(-26,27):cube('Boundary plank',(x,y,1.25),(.15,.94,2.5),'wood',.01)
for y in [-26,26]:
 for x in range(-26,27):
  if y==-26 and -6<x<6:continue
  cube('Boundary plank',(x,y,1.25),(.94,.15,2.5),'wood',.01)
# Bounded arrival forecourt beyond the main entrance.
cube('Entrance forecourt ground',(0,-28.5,-.18),(12,5,.35),'ground')
for x in [-6,6]:
 for yy in range(-31,-25):cube('Forecourt fence',(x,yy,1.25),(.14,.95,2.5),'wood')
for x in range(-6,7):cube('Outer closed arrival fence',(x,-31,1.25),(.95,.14,2.5),'wood')
# main walkways
cube('Midway paved route',(-10,-7,.015),(8,30,.06),'concrete',.01)
cube('Central crosswalk',(-2.5,-2,.02),(23,5,.06),'concrete',.01)
cube('Backstage approach north',(13,2,.02),(12,3,.06),'concrete',.01)
cube('Backstage clear central aisle',(16.5,-3,.02),(3,10,.06),'concrete',.01)
for x,y,label,c in [(-18,-15,'RING TOSS','red'),(-18,-9,'BALL TOSS','teal'),(-18,-3,'LUCKY STARS','red')]:booth('Midway '+label,x,y,label,c)
# mirrored facing row (booths rotated as whole group)
for x,y,label,c in [(-2,-15,'CANDY FLOSS','teal'),(-2,-9,'FORTUNE','red')]:
 before=set(bpy.data.objects); booth('Midway '+label,x,y,label,c)
 # existing orientation still south creates aisle connections and varied sight lines
# strings anchored to poles
for x in [-23,-8,5]:
 for y in [-22,-6,10]:
  cube('String light post',(x,y,2.6),(.14,.14,5.2),'wood')
for y in [-21,-6,4]:
 pts=[]
 for i in range(61):
  t=i/60; pts.append((-23+29*t,y,5.15-.85*sin(pi*t)))
 wire('Suspended festoon cable',pts,.018,'black')
 for i in range(24):
  t=i/23; x=-23+29*t; z=5.15-.85*sin(pi*t); cyl('Bulb socket',(x,y,z-.055),.035,.11,'black',12); sphere('Festoon filament bulb',(x,y,z-.16),(.055,.055,.085),'bulb')
  if i%4==0:light('Festoon pool',(x,y,z-.25),36,(1,.5,.21),.32)
# Entrance arch with actual open gap
for x in [-5,5]:
 cube('Gate masonry pier',(x,-23,1.35),(.8,.8,2.7),'concrete'); beam('Gate upright',(x,-23,2.6),(x,-23,5.5),.085,'rust')
wire('Gate arch',[(-5+10*i/32,-23,5.1+.9*sin(pi*i/32)) for i in range(33)],.12,'rust')
sign('Entrance name','MOONFALL CARNIVAL',(0,-23,4.85),9,.85,.64)
for x in [-5.7,5.7]:
 for j in range(11):beam('Entrance fence bar',(x+(j-5)*.18,-23,.15),(x+(j-5)*.18,-23,2.7),.025,'rust')
booth('Ticket booth',8,-21,'TICKETS','red')
# litter and grass; keep central routes traversable
for i in range(400):
 x=random.uniform(-25,25); y=random.uniform(-25,25)
 o=cube('Ground leaf litter',(x,y,.065),(random.uniform(.04,.15),random.uniform(.08,.22),.008),'paper' if i%7==0 else 'wood',0); o.rotation_euler.z=random.random()*6.28
# low grass tuft mesh reusable, clusters at boundaries & architecture edges
verts=[]; faces=[]
for i in range(18):
 a=random.random()*pi*2; x=random.uniform(-.2,.2); y=random.uniform(-.2,.2); h=random.uniform(.15,.48); w=.025; k=len(verts); verts.extend([(x-w*cos(a),y-w*sin(a),0),(x+w*cos(a),y+w*sin(a),0),(x+.12*cos(a),y+.12*sin(a),h)]); faces.append((k,k+1,k+2))
me=bpy.data.meshes.new('Grass tuft mesh'); me.from_pydata(verts,[],faces); me.materials.append(mats['leaf']); me.uv_layers.new()
for i in range(800):
 x=random.uniform(-25,25); y=random.uniform(-25,25)
 if (-14<x<-6 and -23<y<6) or (-6<x<7 and -7<y<15):continue
 o=bpy.data.objects.new('Overgrowth grass tuft',me); bpy.context.collection.objects.link(o); o.location=(x,y,.04); o.rotation_euler.z=random.random()*6.28
def foliage(name,center,scale,count):
 vs=[]; fs=[]
 for q in range(count):
  a=random.random()*2*pi; b=random.uniform(-1,1); rr=random.random()**.33
  xx=center[0]+scale[0]*rr*math.sqrt(1-b*b)*cos(a); yy=center[1]+scale[1]*rr*math.sqrt(1-b*b)*sin(a); zz=center[2]+scale[2]*rr*b
  w=random.uniform(.08,.2); k=len(vs); vs.extend([(xx-w,yy,zz),(xx,yy-w,zz+.06),(xx+w,yy,zz),(xx,yy+w,zz-.03)]); fs.append((k,k+1,k+2,k+3))
 me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.materials.append(mats['leaf']); uv=me.uv_layers.new()
 for poly in me.polygons:
  for j,li in enumerate(poly.loop_indices):uv.data[li].uv=[(0,.5),(.5,0),(1,.5),(.5,1)][j]
 ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
# trees outside playable fence, trunk branches and loose foliage clusters
for i in range(40):
 a=i*2*pi/40; x=40*cos(a); y=40*sin(a); h=random.uniform(7,12); beam('Boundary tree trunk',(x,y,0),(x+.3,y,h),.32,'wood')
 for j in range(7):
  aa=random.random()*6.28; r=random.uniform(.5,2.5); z=random.uniform(h*.6,h); beam('Tree branch',(x,y,z-2),(x+r*cos(aa),y+r*sin(aa),z),.09,'wood'); foliage('Tree canopy',(x+r*cos(aa),y+r*sin(aa),z),(2.1,1.8,1.7),240)
print('PHASE rides and backstage',flush=True)
# Zone modules
api=dict(cube=cube,cyl=cyl,sphere=sphere,beam=beam,torus=torus,text=text,mats=mats)
for mod,fn in [('rides','build_rides'),('backstage','build_backstage')]:
 try:
  print('Building '+mod,flush=True);getattr(__import__(mod),fn)(api);print('Done '+mod,flush=True)
 except ImportError: print('Module not present yet:',mod)
from assemble_props import consolidate_midway
consolidate_midway()
for o in bpy.data.objects:
 if o.get("_assembly_source"):
  o.hide_render=True;o.hide_set(True)
# Ten explicit spawn markers
for i in range(10):
 o=bpy.data.objects.new('PlayerStart_%02d'%i,None); bpy.context.collection.objects.link(o); o.location=(-11+(i%5)*1.2,-20+(i//5)*2,1); o['UE_Class']='PlayerStart'
# cameras and twilight lighting
world=bpy.data.worlds.new('Moonlit dusk'); world.use_nodes=True; world.node_tree.nodes['Background'].inputs[0].default_value=(.10,.17,.29,1); world.node_tree.nodes['Background'].inputs[1].default_value=.35; bpy.context.scene.world=world
sun=light('Moon key',(0,0,20),2.0,(.48,.65,1),1,'SUN'); sun.rotation_euler=(.45,-.5,-.3)
area=light('Dusk fill',(-10,-10,20),1700,(.32,.48,.75),25,'AREA')
def camera(n,loc,target,lens):
 d=bpy.data.cameras.new(n); o=bpy.data.objects.new(n,d); bpy.context.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); d.lens=lens; return o
camera('Camera_Midway',(-11,-24,2.1),(-15,-3,2.4),28)
camera('Camera_Overview',(47,-59,46),(0,1,0),45)
camera('Camera_Arena',(-13,2,2.1),(-17,13,1.9),24)
camera('Camera_Gate',(0,-29.8,2.2),(0,-21,3),25)
camera('Camera_Backstage',(11,-14,2.1),(17,-3,1.7),26)
scene=bpy.context.scene; scene.camera=bpy.data.objects['Camera_Midway']; scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=False; scene.render.resolution_x=1600; scene.render.resolution_y=1000; scene.render.resolution_percentage=70
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.render.image_settings.file_format='PNG'
# gentle optical glare, actual geometry remains untouched
scene.use_nodes=True; nt=scene.node_tree; nt.nodes.clear(); r=nt.nodes.new('CompositorNodeRLayers'); g=nt.nodes.new('CompositorNodeGlare'); g.glare_type='FOG_GLOW'; g.quality='MEDIUM'; g.threshold=2; out=nt.nodes.new('CompositorNodeComposite'); nt.links.new(r.outputs['Image'],g.inputs['Image']); nt.links.new(g.outputs['Image'],out.inputs['Image'])
for im in bpy.data.images:
 if im.source=='FILE':im.pack()
scene['Map']='Moonfall Carnival / second PropHunt map'; scene['Units']='meters'; scene.unit_settings.system='METRIC'; scene['Unreal_runtime_verified']=False
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/blender/Moonfall_Carnival.blend')
summary={'objects':len(bpy.data.objects),'mesh_objects':sum(o.type=='MESH' for o in bpy.data.objects),'materials':len(bpy.data.materials),'images_packed':sum(bool(i.packed_file) for i in bpy.data.images),'bounds_m':[52,57],'player_starts':10}
open(ROOT+'/qa/build_summary.json','w').write(json.dumps(summary,indent=2)); print(summary)
if '--render' in sys.argv:
 for cam in ['Camera_Midway','Camera_Overview','Camera_Arena','Camera_Backstage']:
  scene.camera=bpy.data.objects[cam]; scene.render.filepath=ROOT+'/renders/'+cam+'.png'; bpy.ops.render.render(write_still=True)
