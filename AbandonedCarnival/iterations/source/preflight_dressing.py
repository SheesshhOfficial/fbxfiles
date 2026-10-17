import bpy,sys,os,json,math
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path[:0]=[R+'/iterations/source',R+'/source']
import cycle_06_ground,cycle_09_story
reports={}
for mod in (cycle_06_ground,cycle_09_story):
 before=set(bpy.data.objects);result=mod.apply();errors=[]
 for o in set(bpy.data.objects)-before:
  if o.type!='MESH':continue
  m=o.data;m.calc_loop_triangles();u=m.uv_layers.active
  zero=sum(p.area<=1e-12 for p in m.polygons);badmat=sum(p.material_index>=len(m.materials) for p in m.polygons);badUV=0
  for p in m.polygons:
   v=[u.data[i].uv for i in p.loop_indices] if u else [];a=sum(v[i].x*v[(i+1)%len(v)].y-v[(i+1)%len(v)].x*v[i].y for i in range(len(v)))*.5
   if abs(a)<=1e-12:badUV+=1
  if zero or badmat or badUV:errors.append({'object':o.name,'zero_faces':zero,'bad_material':badmat,'zero_uv':badUV})
 reports[mod.__name__]={'result':result,'errors':errors}
json.dump(reports,open(R+'/iterations/qa/dressing_preflight.json','w'),indent=2);print(reports)
