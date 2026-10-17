"""Continuous aged asphalt with sparse branching fissures, avoiding flagstone cells."""
import bpy,math,random,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));rng=random.Random(1281)
def mesh(name,vs,fs,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  for i in p.loop_indices:
   v=me.vertices[me.loops[i].vertex_index].co;uv.data[i].uv=(v.x/2.5,v.y/2.5)
 return me
old=bpy.data.objects['Cracked uneven asphalt surface'];vs=[];fs=[]
for y in range(26):
 for x in range(9):vs.append((-14+x,-22+y,.053+.0015*math.sin(x*2.4+y*.71)))
for y in range(25):
 for x in range(8):a=y*9+x;fs.append((a,a+1,a+10,a+9))
old.data=mesh('Continuous worn asphalt',vs,fs,bpy.data.materials['Scanned cracked paving'])
vs=[];fs=[]
def fissure(x,y,angle,length,width):
 steps=max(5,int(length/.08));pts=[(x,y)];a=angle
 for k in range(steps):
  a+=rng.uniform(-.58,.58);x+=math.cos(a)*length/steps;y+=math.sin(a)*length/steps
  if not(-13.9<x<-6.1 and -21.9<y<2.9):break
  pts.append((x,y))
 for j,(p,q) in enumerate(zip(pts,pts[1:])):
  dx,dy=q[0]-p[0],q[1]-p[1];d=math.hypot(dx,dy);w=width*rng.uniform(.4,1);ox,oy=-dy/d*w/2,dx/d*w/2;k=len(vs)
  vs.extend([(p[0]-ox,p[1]-oy,.056),(q[0]-ox,q[1]-oy,.056),(q[0]+ox,q[1]+oy,.056),(p[0]+ox,p[1]+oy,.056)]);fs.append((k,k+1,k+2,k+3))
 return pts
for i in range(28):
 pts=fissure(rng.uniform(-13.5,-6.5),rng.uniform(-21,2),rng.random()*math.tau,rng.uniform(.45,2.5),rng.uniform(.003,.009))
 if len(pts)>5 and rng.random()<.65:
  x,y=pts[len(pts)//2];fissure(x,y,rng.random()*math.tau,rng.uniform(.25,.7),.003)
ob=bpy.data.objects.new('Sparse branching asphalt fissures',mesh('Fine branching cracks',vs,fs,bpy.data.materials['Pavement dark crack interiors']));bpy.context.collection.objects.link(ob);ob['decorative_no_collision']=True
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
