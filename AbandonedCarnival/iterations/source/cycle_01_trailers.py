"""Cycle 1: curved sheet-metal trailer roofs and rolled-edge construction."""
import bpy,math,sys,os
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path.insert(0,R+'/source')
from fast_geometry import make_api

def apply():
 mats={m.name:m for m in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(mats);made=[]
 def mesh(name,vs,fs,mat):
  me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();uv=me.uv_layers.new(name='UVMap')
  for p in me.polygons:
   ax=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=ax]
   for li in p.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
   p.use_smooth=len(p.vertices)==4
  me.set_sharp_from_angle(angle=math.radians(35));o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o['refinement_cycle']=1;o['geometry_provenance']='Original project geometry';made.append(o.name);return o
 for letter,cx,cy in [('A',12.6,-4.6),('B',20.7,-4.0)]:
  roof=bpy.data.objects.get('BY_Caravan_'+letter+'_Roof');mat=roof.data.materials[0]
  roof.hide_render=True;roof.hide_set(True);roof['visual_replaced']=True
  n=48;vs=[]
  for y in (cy-3.55,cy+3.55):
   for inner in (False,True):
    for i in range(n+1):
     x=-1.44+2.88*i/n;z=3.48+.30*math.sqrt(max(0,1-(x/1.48)**2))-(.035 if inner else 0)
     vs.append((cx+x,y,z))
  a=n+1;fs=[]
  for i in range(n):
   fs.extend([(i,i+1,2*a+i+1,2*a+i),(a+i,3*a+i,3*a+i+1,a+i+1),(i,a+i,a+i+1,i+1),(2*a+i,2*a+i+1,3*a+i+1,3*a+i)])
  fs.extend([(0,2*a,3*a,a),(n,a+n,3*a+n,2*a+n)])
  mesh('Cycle01 caravan '+letter+' formed barrel roof',vs,fs,mat)
  # Thin rolled seams follow the roof curvature, replacing flat straps.
  for o in list(bpy.data.objects):
   if o.name.startswith('RF_Van_'+letter+'_Roof_Strapping'):
    o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
  for y in (cy-2.9,cy,cy+2.9):
   for i in range(24):
    x=-1.44+2.88*i/24;xx=-1.44+2.88*(i+1)/24
    z=lambda t:3.493+.30*math.sqrt(max(0,1-(t/1.48)**2))
    o=beam('Cycle01 '+letter+' rolled roof seam',(cx+x,y,z(x)),(cx+xx,y,z(xx)),.009,'rust');o['decorative_no_collision']=True
  # Curved roof-edge perimeter conceals exposed sheet seams and reads as metal trim.
  for side in (-1,1):
   o=beam('Cycle01 '+letter+' drip edge',(cx+side*1.445,cy-3.55,3.55),(cx+side*1.445,cy+3.55,3.55),.022,'Entrance dull galvanized metal');o['decorative_no_collision']=True
  for o in bpy.data.objects:
   if o.name.startswith('BY_Caravan_'+letter+'_Roof_Vent'):
    o.location.z+=.15
  # Roof end infills sit above walls, not across a door or window.
  for y in (cy-3.49,cy+3.49):
   v=[(cx-1.4,y,3.47),(cx+1.4,y,3.47)]+[(cx+1.4-2.8*i/32,y,3.48+.30*math.sqrt(max(0,1-((1.4-2.8*i/32)/1.48)**2))) for i in range(33)]
   o=mesh('Cycle01 '+letter+' curved end cap',v,[tuple(range(len(v)))],mat);o['decorative_no_collision']=True
 return {'change':'Replaced two flat slab roofs with 48-segment formed sheet-metal roofs, curved seams, drip edges and matching end caps; raised vents onto new roof.','created_primary_meshes':made,'eligible_props_changed':0,'route_geometry_changed':False,'collision_note':'New curved roof shells require dedicated roof collision review on export; no door/window openings changed.'}
