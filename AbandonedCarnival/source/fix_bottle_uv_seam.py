"""Repair each lathed quad crossing the cylindrical UV seam; no geometry change."""
import bpy,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seen=set();fixed=0
for o in bpy.data.objects:
 if not o.get('PropActorTag') or o.get('asset_family')!='Bottle' or o.data.name in seen:continue
 seen.add(o.data.name);uv=o.data.uv_layers.active
 for p in o.data.polygons:
  if len(p.vertices)!=4:continue
  values=[uv.data[i].uv.x for i in p.loop_indices]
  if max(values)-min(values)>.5:
   for i in p.loop_indices:
    if uv.data[i].uv.x<.5:uv.data[i].uv.x+=1
   fixed+=1
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
print('Bottle seam quads repaired:',fixed)
