import bpy,math,random,os,sys
from mathutils import Vector,Matrix
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source');from fast_geometry import make_api
random.seed(471);m={n:bpy.data.materials[n] for n in ['wood','rust','cream','red','teal','gold','black','glass','bulb','concrete','leaf','paper']};cube,cyl,sphere,beam,torus=make_api(m)
def pbr(n,color,rough=1,metal=0):
 mat=bpy.data.materials.new(n);mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;m[n]=mat;return mat
pbr('cardboard',(.19,.12,.057));pbr('oldpaper',(.42,.36,.23));pbr('wetground',(.045,.055,.049),.12);pbr('chippedwood',(.22,.15,.073));pbr('moss',(.08,.105,.028));pbr('fallenleaf',(.17,.075,.02))
def mesh(n,vs,fs,mat,uvcoords=None):
 me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.materials.append(m[mat]);me.update();uv=me.uv_layers.new()
 for p in me.polygons:
  axis=max(range(3),key=lambda a:abs(p.normal[a]));ax=[a for a in range(3) if a!=axis]
  for li in p.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[ax[0]],v[ax[1]])
 ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);return ob
# Hide the awkward redundant centre poles while retaining the continuous festoon cables.
for o in bpy.data.objects:
 if o.name.startswith('String light post') and abs(o.location.x+8)<.1:o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
# Local architectural details, roof sheet damage, fasteners and irregular prizes.
for label,x,y,ang in [('RING TOSS',-18,-15,math.pi/2),('BALL TOSS',-18,-9,math.pi/2),('LUCKY STARS',-18,-3,math.pi/2),('CANDY FLOSS',-2,-15,-math.pi/2),('FORTUNE',-2,-9,-math.pi/2)]:
 T=Matrix.Translation((x,y,0))@Matrix.Rotation(ang,4,'Z')
 def pt(p):return T@Vector(p)
 def box(n,p,sc,mat,b=.015):
  o=cube('Art '+label+' '+n,pt(p),sc,mat,b);o.rotation_euler.z=ang;return o
 for o in bpy.data.objects:
  if o.name.startswith('Midway '+label+' roof strip'):o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
 for k in range(5):
  if k==3 and label=='BALL TOSS':continue
  vs=[];fs=[]
  for j in range(25):
   xx=-2.25+k*.9+j*.9/24;corr=.035*math.cos(j*math.pi)
   for yy in [-1.85,1.85]:vs.append(pt((xx,yy,3.33-yy*.08+corr+random.uniform(-.008,.008))))
  for j in range(24):fs.append((j*2,j*2+1,j*2+3,j*2+2))
  mesh('Art '+label+' wavy corrugated sheet',vs,fs,'rust')
 for yy in [-1.45,0,1.4]:box('roof joist',(0,yy,3.13),(4.25,.1,.14),'wood')
 for xx in [-1.8,1.8]:
  beam('Art '+label+' angled timber brace',pt((xx,-1.4,2.35)),pt((xx*.62,-1.4,3.02)),.055,'wood')
  for z in [1.4,2.5,3.0]:
   for dx in [-.04,.04]:
    ob=cyl('Art '+label+' iron nail',pt((xx+dx,-1.49,z)),.014,.014,'black',10);ob.rotation_euler=(math.pi/2,0,ang)
 # Plank scuffs: jagged exposed timber strips with irregular outlines.
 for i in range(34):
  xx=random.uniform(-1.95,1.95);z=random.uniform(.25,1.2);w=random.uniform(.015,.05);h=random.uniform(.05,.22)
  vs=[pt((xx-w,-1.468,z-h)),pt((xx+w*.4,-1.471,z-h*.7)),pt((xx+w,-1.469,z+h)),pt((xx-w*.5,-1.47,z+h*.6))]
  mesh('Art '+label+' exposed wood chip',vs,[(0,1,2,3)],'chippedwood')
 # Prize rows become slightly irregular, with a few tipped counter bottles.
 for o in bpy.data.objects:
  if o.get('PropActorTag') and o.name.startswith('Midway '+label):
   o.rotation_euler.z+=random.uniform(-.14,.14)
   if 'prize' in o.name:o.scale*=random.uniform(.9,1.08)
# Detailed rough-edged timber crates; tight stacks at sides, not centre walkway.
def crate(n,x,y,z,s=.65):
 for k in range(4):
  zz=z+.08+k*.16
  for side in [-1,1]:
   cube(n+' long slat',(x,y+side*s*.5,zz),(s,.055,.13),'wood',.006)
   cube(n+' end slat',(x+side*s*.5,y,zz),(.055,s,.13),'wood',.006)
 for dx in [-s*.4,s*.4]:
  for dy in [-s*.4,s*.4]:cube(n+' corner batten',(x+dx,y+dy,z+.32),(.07,.07,.65),'chippedwood',.008)
 for k in range(4):cube(n+' bottom board',(x-s*.375+k*s*.25,y,z+.03),(s*.22,s,.045),'wood',.005)
for i,(x,y,z) in enumerate([(-15.2,-16.7,.06),(-15.25,-16.7,.73),(-15.7,-16,.06),(-15.1,-10,.06),(-4.9,-13.4,.06),(-5.1,-14.15,.06),(-4.95,-13.4,.73),(-15.1,-2,.06)]):crate('Art timber crate %02d'%i,x,y,z)
# Open cardboard cartons, thin walls and bent flaps.
for i,(x,y) in enumerate([(-15,-18),(-15.3,-11),(-5.2,-17),(-5.1,-8),(-14.7,-1)]):
 w=.55;h=.37
 cube('Art cardboard bottom',(x,y,.095),(w,w,.025),'cardboard',.004)
 for sx in [-1,1]:
  cube('Art cardboard side',(x+sx*w/2,y,.1+h/2),(.02,w,h),'cardboard',.002)
  o=cube('Art bent carton flap',(x+sx*(w/2+.1),y,.12+h),(.22,w,.014),'cardboard',.001);o.rotation_euler.y=sx*.38
 for sy in [-1,1]:cube('Art cardboard front',(x,y+sy*w/2,.1+h/2),(w,.02,h),'cardboard',.002)
# Irregular puddle patches on the alley, kept shallow, glossy dark water.
for k,(x,y,rx,ry) in enumerate([(-12,-16,1.4,.48),(-9,-7,.8,.5),(-13.3,-2,.7,.6),(-7,-12,.75,.25),(-10,1,1.2,.6)]):
 vs=[(x,y,.064)]
 for j in range(24):
  a=j*math.tau/24;r=random.uniform(.8,1.16);vs.append((x+rx*r*math.cos(a),y+ry*r*math.sin(a),.064))
 mesh('Art shallow puddle %02d'%k,vs,[(0,j+1,(j+1)%24+1) for j in range(24)],'wetground')
# Small fractured paving stones edge the hardstanding.
for side in [-1,1]:
 for j in range(35):
  x=-10+side*4.0+random.uniform(-.2,.2);y=-21+j*.7+random.uniform(-.18,.18);h=random.uniform(.035,.09)
  o=cube('Art broken paving edge',(x,y,.05+h/2),(random.uniform(.2,.42),random.uniform(.25,.55),h),'concrete',.025);o.rotation_euler.z=random.uniform(-.2,.2)
# Leaf litter piles and stones concentrated close to posts.
for i in range(450):
 x=random.choice([-14.8,-5.3])+random.uniform(-.55,.55);y=random.uniform(-20,2);r=random.uniform(.025,.075)
 o=sphere('Art scattered rough stone',(x,y,.065+r*.4),(r,r*.7,r*.45),'concrete');o.rotation_euler.z=random.random()*math.tau
# Moored stacks of loose repair boards.
for k in range(10):
 o=cube('Art repair timber',(-15.35,-6.7,.1+k*.045),(random.uniform(1.1,1.8),.13,.045),'wood',.004);o.rotation_euler.z=random.uniform(-.12,.12)
# Better camera and restrained nighttime exposure. Preserve practical contrast.
s=bpy.context.scene;s.world.node_tree.nodes['Background'].inputs[1].default_value=.28;s.view_settings.exposure=.1
for o in bpy.data.objects:
 if o.type=='LIGHT' and o.name=='Midway soft practical':o.data.energy=350
 if o.type=='LIGHT' and o.name=='Carousel practical bounce':o.data.energy=800
 if o.type=='LIGHT' and 'warm spill' in o.name:o.data.energy=140
cam=bpy.data.objects['Camera_Midway'];cam.location=(-10.4,-19.4,1.7);cam.rotation_euler=(Vector((-14.6,-1,2))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=32
s['Art_pass']='Midway reference refinement in progress'
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Midway architecture artpass saved')
