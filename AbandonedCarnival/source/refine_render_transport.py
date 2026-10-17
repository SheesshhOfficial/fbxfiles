import bpy,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
count=0
for o in bpy.data.objects:
 if o.type!='MESH':continue
 emissive=False
 for m in o.data.materials:
  if m and m.use_nodes:
   p=m.node_tree.nodes.get('Principled BSDF')
   if p and p.inputs['Emission Strength'].default_value>0:emissive=True
 if emissive and not o.get('render_only'):
  # Visible filament geometry is paired with explicit practical lights; avoid double-counting tiny mesh emitters.
  o.visible_diffuse=False;o.visible_volume_scatter=False;count+=1
s=bpy.context.scene;s.cycles.sample_clamp_indirect=2;s.cycles.sample_clamp_direct=10;s.cycles.max_bounces=8;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=4;s.cycles.volume_bounces=1;s.cycles.use_denoising=False;s.cycles.samples=512
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Practical emitter transport refined',count)
