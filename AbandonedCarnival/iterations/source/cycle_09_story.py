"""Cycle 9: localized paused-repair story clusters, outside circulation lanes."""
import bpy,math,random,os,sys
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path.insert(0,R+'/source')
from fast_geometry import make_api

def apply():
 m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m);rng=random.Random(9009);created=[]
 def mesh(name,vs,fs,mat):
  me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(m[mat]);me.update();uv=me.uv_layers.new(name='UVMap')
  for p in me.polygons:
   ax=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=ax]
   for li in p.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
   p.use_smooth=True
  o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o['decorative_no_collision']=True;o['refinement_cycle']=9;created.append(name);return o
 for k,(x,y) in enumerate([(11.4,-23.0),(23.7,-9.7)]):
  # The folded cloth is visibly supported by stacked repair timbers.
  for j in range(6):
   o=cube('Cycle09 salvaged repair planks',(x,y+(j%3-.9)*.19,.09+(j//3)*.11),(1.42,.16,.09),'wood',.009);o.rotation_euler.z=rng.uniform(-.035,.035);o['decorative_no_collision']=True
  nx,ny=24,20;vs=[];fs=[]
  for j in range(ny+1):
   yy=-.69+1.38*j/ny
   for i in range(nx+1):
    xx=-.91+1.82*i/nx;drop=max(0,(abs(xx)-.67)*1.1,(abs(yy)-.42)*.75)
    z=.35-drop+.022*math.sin(xx*24+yy*3)+.012*math.sin(yy*28);vs.append((x+xx,y+yy,max(.045,z)))
  for j in range(ny):
   for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
  cloth=mesh('Cycle09 weathered canvas over repair stock %02d'%k,vs,fs,'CanvasCream' if k==0 else 'CanvasRed')
  sol=cloth.modifiers.new('Thin fabric edge','SOLIDIFY');sol.thickness=.002;sol.offset=0
  for xx in (-.70,.70):
   o=beam('Cycle09 tarp retaining cord',(x+xx,y-.5,.3),(x+xx,y-.64,.04),.006,'black');o['decorative_no_collision']=True
 # A small leaning maintenance ladder rests against the outside ticket-wall.
 for yy in (-20.10,-19.70):
  o=beam('Cycle09 maintenance ladder stile',(10.93,yy,.04),(10.06,yy,1.82),.026,'wood');o['decorative_no_collision']=True
 for j in range(6):
  t=.12+j*.14;x=10.93-.87*t;z=.04+1.78*t;o=beam('Cycle09 ladder rung',(x,-20.10,z),(x,-19.70,z),.019,'wood');o['decorative_no_collision']=True
 # Coiled cable is hung on two metal hooks on the exterior wall, not loose across a route.
 for off in range(4):
  center=(10.12,-20.5,1.4);vs=[];fs=[];n=64;cross=8
  for i in range(n):
   a=math.tau*i/n;rad=.30+off*.017
   for j in range(cross):
    b=math.tau*j/cross;vs.append((center[0]+.012*math.sin(b)+off*.015,center[1]+(rad+.012*math.cos(b))*math.cos(a),center[2]+(rad+.012*math.cos(b))*math.sin(a)))
  for i in range(n):
   for j in range(cross):fs.append((i*cross+j,((i+1)%n)*cross+j,((i+1)%n)*cross+(j+1)%cross,i*cross+(j+1)%cross))
  mesh('Cycle09 wall-hung service cable %02d'%off,vs,fs,'black')
 for yy in (-20.72,-20.28):
  o=beam('Cycle09 service cable mounting hook',(10.045,yy,1.65),(10.19,yy,1.65),.013,'rust');o['decorative_no_collision']=True
 return {'change':'Two cloth-covered supported timber-repair piles, a leaning ladder and physically hooked coiled service cable establish a paused maintenance story near the ticket kiosk and outer backstage edge.','primary_meshes':created,'eligible_props_changed':0,'clearance_note':'Gate x±4 approach, stall aisles, funhouse mouth and central backstage passage receive no new obstacles. Dressing is placed outside those circulation areas.'}
