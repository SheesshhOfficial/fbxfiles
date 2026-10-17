"""Cycle 2: crafted counter boards, thin canvas valances and folded roof trims."""
import bpy,math,os,sys,random
from mathutils import Vector,Matrix
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path.insert(0,R+'/source')
from fast_geometry import make_api

def apply():
 m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m);rng=random.Random(2002);created=0;replaced=[]
 def mesh(name,vs,fs,mat):
  nonlocal created
  me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(m[mat]);me.update();uv=me.uv_layers.new(name='UVMap')
  for p in me.polygons:
   axes=sorted(range(3),key=lambda a:abs(p.normal[a]))[:2]
   for li in p.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
  o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o['refinement_cycle']=2;o['decorative_no_collision']=True;created+=1;return o
 for label,x,y,angle in [('RING TOSS',-18,-15,math.pi/2),('BALL TOSS',-18,-9,math.pi/2),('LUCKY STARS',-18,-3,math.pi/2),('CANDY FLOSS',-2,-15,-math.pi/2),('FORTUNE',-2,-9,-math.pi/2)]:
  T=Matrix.Translation((x,y,0))@Matrix.Rotation(angle,4,'Z');pt=lambda p:T@Vector(p)
  # Replace the monolithic counter with individual worn boards and an edge moulding.
  for o in list(bpy.data.objects):
   if o.name=='Midway '+label+' counter':o.hide_render=True;o.hide_set(True);o['visual_replaced']=True;replaced.append(o.name)
  for j in range(4):
   o=cube('Cycle02 '+label+' counter board',pt((0,-1.68+j*.15,1.3+rng.uniform(-.003,.003))),(4.25,.143,.12),'wood',.012);o.rotation_euler.z=angle
  o=beam('Cycle02 '+label+' rounded counter nosing',pt((-2.13,-1.76,1.3)),pt((2.13,-1.76,1.3)),.028,'wood')
  # Overhanging textile valance, short enough to retain signs/prizes and head clearance.
  for k in range(18):
   x0=-2.16+k*.24;vs=[];fs=[]
   for j in range(9):
    xx=x0+.24*j/8;bottom=2.90-.095*math.sin(math.pi*j/8)
    yy=-1.81-.018*math.sin(math.pi*j/8)+rng.uniform(-.002,.002)
    vs.extend([pt((xx,yy,3.0)),pt((xx,yy,bottom))])
   for j in range(8):fs.append((j*2,j*2+1,j*2+3,j*2+2))
   mesh('Cycle02 '+label+' scalloped canvas valance',vs,fs,'CanvasCream' if k%2 else 'CanvasRed')
  # Narrow folded sheet-metal roof drip edges, not oversized blocks.
  for side in (-1,1):
   pts=[(-2.28,side*1.87,3.33-side*1.87*.08),(2.28,side*1.87,3.33-side*1.87*.08),(2.28,side*1.9,3.27-side*1.87*.08),(-2.28,side*1.9,3.27-side*1.87*.08)]
   mesh('Cycle02 '+label+' folded eave flashing',[pt(p) for p in pts],[(0,1,2,3)],'rust')
  # Individual fasteners show how the frame is held together.
  for xx in (-2,2):
   for z in (1.33,2.8):
    o=cyl('Cycle02 '+label+' post bolt',pt((xx,-1.493,z)),.018,.018,'Entrance dull galvanized metal',12);o.rotation_euler=(math.pi/2,0,angle)
 return {'change':'Five stalls receive board-built counters with rounded nosings, short scalloped woven canvas valances, thin folded eave flashing and visible join fasteners.','replaced_objects':replaced,'custom_meshes_added':created,'eligible_props_changed':0,'route_note':'No floor obstacles added; canvas bottom stays above2.8m and signs remain exposed.'}
