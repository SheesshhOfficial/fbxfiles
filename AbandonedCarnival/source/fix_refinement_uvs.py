"""Repair degenerate per-face UVs without welding solids or changing geometry."""
import bpy,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));seen=set();fixed=0
for o in bpy.data.objects:
 if o.type!='MESH' or o.data.name in seen:continue
 me=o.data;seen.add(me.name);uv=me.uv_layers.active
 if not uv:continue
 for p in me.polygons:
  pts=[uv.data[i].uv.copy() for i in p.loop_indices];a=sum(pts[i].x*pts[(i+1)%len(pts)].y-pts[(i+1)%len(pts)].x*pts[i].y for i in range(len(pts)))*.5
  if abs(a)>1e-12:continue
  axis=max(range(3),key=lambda j:abs(p.normal[j]));axes=[j for j in range(3) if j!=axis];mat=me.materials[p.material_index] if me.materials else None;tile=mat.get('physical_tile_m',1) if mat else 1
  for li in p.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/tile,v[axes[1]]/tile)
  fixed+=1
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True);print('Reprojected UV faces:',fixed)
