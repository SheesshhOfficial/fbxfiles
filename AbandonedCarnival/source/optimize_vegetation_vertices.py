"""Weld duplicate decorative vegetation vertices, preserving per-loop UVs/material IDs.
Never touches gameplay props, architecture or collision-source solids.
"""
import bpy,bmesh,os,json
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));seen=set();records=[]
for o in bpy.data.objects:
 if o.type!='MESH' or o.get('PropActorTag') or not o.name.startswith(('Natural forest |','Natural foliage |','Overgrowth grass tuft','Entrance verge natural patch')):continue
 me=o.data
 if me.name in seen:continue
 seen.add(me.name);before=[len(me.vertices),len(me.polygons)];bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bm.to_mesh(me);bm.free();me.update()
 for attempt in range(2):
  ids=[p.index for p in me.polygons if p.area<=1e-12]
  if not ids:break
  bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in ids],context='FACES_ONLY');bm.to_mesh(me);bm.free();me.update()
 records.append({'mesh':me.name,'before_vertices_faces':before,'after_vertices_faces':[len(me.vertices),len(me.polygons)]})
json.dump({'scope':'Decorative vegetation only; loop UVs/material IDs preserved, no gameplay prop geometry touched','meshes':records,'vertices_before':sum(r['before_vertices_faces'][0] for r in records),'vertices_after':sum(r['after_vertices_faces'][0] for r in records)},open(R+'/qa/vegetation_vertex_cleanup.json','w'),indent=2)
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
