import bpy,sys,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source')
from natural_vegetation import add_natural_vegetation
# Superseded simplistic ivy and near-stall grass is hidden, not layered into noise.
for o in bpy.data.objects:
 if o.name.startswith('Booth creeping ivy') or (o.name.startswith('Overgrowth grass tuft') and -22<o.location.x<2 and -22<o.location.y<3):
  o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
print(add_natural_vegetation(),flush=True)
for i in bpy.data.images:
 if i.source=='FILE' and not i.packed_file:i.pack()
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend')
