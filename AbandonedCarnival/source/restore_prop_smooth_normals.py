"""Restore smooth curved surfaces lost when component meshes were assembled.
Sharp angles preserve hard box/panel edges; geometry, pivots and collision unchanged.
"""
import bpy,math,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));seen=set();count=0
for o in bpy.data.objects:
 if o.type!='MESH' or not o.get('PropActorTag') or o.hide_render or o.get('_assembly_source'):continue
 me=o.data
 if me.name in seen:continue
 seen.add(me.name)
 for p in me.polygons:p.use_smooth=True
 me.set_sharp_from_angle(angle=math.radians(38));me.update();count+=1
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True);print('Restored smooth/hard prop meshes:',count)
