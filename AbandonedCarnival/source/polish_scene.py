import bpy,os,random,math,json
from mathutils import Vector,Matrix
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));random.seed(172)
s=bpy.context.scene
# Turn the prize counters toward the aisle, including source components, assembled copies and local lights.
for label,x,y,a in [('RING TOSS',-18,-15,math.pi/2),('BALL TOSS',-18,-9,math.pi/2),('LUCKY STARS',-18,-3,math.pi/2),('CANDY FLOSS',-2,-15,-math.pi/2),('FORTUNE',-2,-9,-math.pi/2)]:
 T=Matrix.Translation((x,y,0))@Matrix.Rotation(a,4,'Z')@Matrix.Translation((-x,-y,0))
 for o in bpy.data.objects:
  if o.name.startswith('Midway '+label):o.matrix_world=T@o.matrix_world
# Extend visible landscape beneath forest.
me=bpy.data.meshes.new('Forest ground mesh');me.from_pydata([(-65,-65,-.22),(65,-65,-.22),(65,65,-.22),(-65,65,-.22)],[],[(0,1,2,3)]);me.materials.append(bpy.data.materials['ground']);uv=me.uv_layers.new()
for i,p in enumerate([(-65,-65),(65,-65),(65,65),(-65,65)]):uv.data[i].uv=p
ob=bpy.data.objects.new('Surrounding forest terrain',me);bpy.context.collection.objects.link(ob)
# Real leaf geometry, various leaf tilts and sizes, dense branching clusters.
def leaves(name,centers,count,radius):
 vs=[];fs=[]
 for center in centers:
  for i in range(count):
   a=random.random()*math.tau;b=random.uniform(-1,1);rr=random.random()**.333
   p=Vector(center)+Vector((radius*rr*math.sqrt(1-b*b)*math.cos(a),radius*rr*math.sqrt(1-b*b)*math.sin(a),radius*.7*rr*b))
   w=random.uniform(.08,.18);u=Vector((math.cos(a)*w,math.sin(a)*w,random.uniform(-.08,.08)));v=Vector((-math.sin(a)*w*.6,math.cos(a)*w*.6,random.uniform(-.08,.08)));k=len(vs);vs.extend([p-u,p+v,p+u,p-v]);fs.append((k,k+1,k+2,k+3))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(bpy.data.materials['leaf']);uv=me.uv_layers.new()
 for p in me.polygons:
  for j,li in enumerate(p.loop_indices):uv.data[li].uv=[(0,.5),(.5,0),(1,.5),(.5,1)][j]
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
for i in range(40):
 a=i*math.tau/40;x,y=40*math.cos(a),40*math.sin(a);centers=[(x+random.uniform(-2,2),y+random.uniform(-2,2),random.uniform(5,11)) for j in range(9)];leaves('Dense forest crown %02d'%i,centers,600,2.3)
# Ivy on prize booths, fence corners and caravan edges, not blocking walk routes.
for label,x,y in [('RING TOSS',-18,-15),('BALL TOSS',-18,-9),('LUCKY STARS',-18,-3),('CANDY FLOSS',-2,-15),('FORTUNE',-2,-9)]:
 centers=[]
 for side in [-1,1]:
  for j in range(11):centers.append((x+random.uniform(-.2,.2),y+side*2.05,.3+j*.29))
 leaves('Booth creeping ivy '+label,centers,14,.32)
# Irregular paper and fallen leaves concentrated near scenery edges.
vs=[];fs=[]
for i in range(1400):
 x=random.choice([-18,-2])+random.uniform(-3.2,3.2);y=random.uniform(-19,0);z=.07;a=random.random()*math.tau;w=random.uniform(.035,.11);p=Vector((x,y,z));u=Vector((math.cos(a)*w,math.sin(a)*w,0));v=Vector((-math.sin(a)*w*.6,math.cos(a)*w*.6,.015));k=len(vs);vs.extend([p-u,p-v,p+u,p+v]);fs.append((k,k+1,k+2,k+3))
me=bpy.data.meshes.new('Accumulated fallen leaves');me.from_pydata(vs,[],fs);me.materials.append(bpy.data.materials['wood']);uv=me.uv_layers.new()
for p in me.polygons:
 for j,li in enumerate(p.loop_indices):uv.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][j]
o=bpy.data.objects.new('Accumulated fallen leaves',me);bpy.context.collection.objects.link(o)
# Warm area spill gives broad readable practical illumination.
def area(n,p,power,color,size):
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.location=p
area('Carousel practical bounce',(0,8,4.7),1100,(1,.46,.15),8)
area('Arena practical bounce',(-17,12,4.6),1100,(1,.55,.25),8)
area('Midway soft practical',(-10,-9,5.5),900,(1,.55,.29),14)
area('Backstage moon fill',(16,-4,6),700,(.45,.63,1),9)
for o in bpy.data.objects:
 if o.type=='LIGHT' and 'warm spill' in o.name:o.data.energy=170
s.world.node_tree.nodes['Background'].inputs[1].default_value=.5;s.view_settings.exposure=1.0
# Camera framing emphasizes the facing stall row.
s.camera=bpy.data.objects['Camera_Midway'];s.camera.location=(-10.4,-22.5,1.85);s.camera.rotation_euler=(Vector((-11,3,2.5))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=30
s.cycles.use_denoising=False;s.cycles.samples=128
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival.blend');print('Polished scene saved',len(bpy.data.objects))
