import bpy,bmesh,os,json,sys
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source')
from assemble_props import assemble
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Ticket booth bin ') and not o.get('_assembly_source')]
if len(parts)>1:
 origin=(10.45,-22.25,0);assemble('Ticket booth complete barrel',parts,origin,'Barrel')
 for o in parts:o.hide_render=True;o.hide_set(True)
seen=set();report=[]
for o in bpy.data.objects:
 if o.type!='MESH' or o.data.name in seen:continue
 seen.add(o.data.name);me=o.data;before=(len(me.vertices),len(me.polygons));bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
 bmesh.ops.dissolve_degenerate(bm,dist=.0000001,edges=list(bm.edges))
 bad=[f for f in bm.faces if f.calc_area()<1e-12]
 if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
 if not me.uv_layers:me.uv_layers.new()
 # Repair only degenerate UV faces by local dominant-axis projection.
 uv=me.uv_layers.active
 for p in me.polygons:
  co=[uv.data[i].uv for i in p.loop_indices];area=abs(sum(co[i].x*co[(i+1)%len(co)].y-co[(i+1)%len(co)].x*co[i].y for i in range(len(co))))*.5
  if area<1e-12 and p.area>1e-12:
   axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis]
   for li in p.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
 after=(len(me.vertices),len(me.polygons))
 if before!=after:report.append({'mesh':me.name,'before':before,'after':after})
bpy.context.scene.cycles.use_denoising=False
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival.blend')
open(R+'/qa/cleanup_report.json','w').write(json.dumps(report,indent=2));print('Cleaned unique meshes',len(report))
