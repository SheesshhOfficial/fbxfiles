"""Replace presentation-style open roof with a damaged, supported roof structure."""
import bpy,os,sys,math,random
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source');from fast_geometry import make_api
m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m);rng=random.Random(116)
for y in [7.5,11.3,15.1,18.9]:
 for x in [11,21]:beam('Funhouse roof structural post',(x,y,3.35),(x,y,4.28),.08,'wood')
 beam('Funhouse roof tie beam',(11,y,4.24),(21,y,4.24),.08,'wood')
 for side in [-1,1]:
  beam('Funhouse roof main rafter',(16,y,5.3),(16+5.15*side,y,4.25),.08,'wood')
  beam('Funhouse roof diagonal brace',(16+side*4.8,y,4.24),(16+side*2.4,y,4.8),.045,'wood')
for x in [10.9,13.4,16,18.6,21.1]:beam('Funhouse roof longitudinal purlin',(x,7.3,5.31-abs(x-16)*.204),(x,19.1,5.31-abs(x-16)*.204),.055,'rust')
for side in [-1,1]:
 for row in range(3):
  for col in range(9):
   if (row+col*2+(side>0))%7 in [0,1,4]:continue
   xa=16+side*row*1.72;ya=7.2+col*1.34;vs=[];fs=[]
   for i in range(2):
    x=xa+side*i*1.75
    for j in range(17):
     y=ya+j*1.37/16;z=5.34-abs(x-16)*.204+(.022 if j%2 else -.022)
     if row==2 and col in [1,7]:z-=.18*i*(j/16)**2
     vs.append((x,y,z))
   for j in range(16):fs.append((j,j+1,18+j,17+j) if side<0 else (17+j,18+j,j+1,j))
   me=bpy.data.meshes.new('Damaged funhouse roof sheet');me.from_pydata(vs,[],fs);me.materials.append(m['rust']);me.update();uv=me.uv_layers.new()
   for f in me.polygons:
    for li in f.loop_indices:
     co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co.x/.8,co.y/.8)
   ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
# Small fixed wall lights provide readable paths without a bright ceiling fill.
for i,(x,y) in enumerate([(11.25,9.1),(20.75,12.2),(11.25,15.3),(20.75,18.1)]):
 cube('Funhouse interior fixture back',(x,y,2.9),(.13,.25,.35),'rust',.015);cube('Funhouse interior fixture lens',(x+(.08 if x<16 else -.08),y,2.9),(.10,.18,.24),'bulb',.01)
 ld=bpy.data.lights.new('Funhouse interior practical %d'%i,'POINT');ld.energy=22;ld.color=(1,.4,.16);ld.shadow_soft_size=.18;ob=bpy.data.objects.new(ld.name,ld);bpy.context.collection.objects.link(ob);ob.location=(x+(.25 if x<16 else -.25),y,2.85)
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
