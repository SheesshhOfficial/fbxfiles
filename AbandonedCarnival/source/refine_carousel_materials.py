import bpy,os,sys,math
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def material(name):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree;p=n.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.86;p.inputs['Sheen Weight'].default_value=.16
 for slot,f in [('Base Color',name+'_basecolor.jpg'),('Normal','Canvas_normal.png'),('Roughness','Canvas_roughness.jpg')]:
  t=n.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(R+'/textures/derived/'+f,check_existing=True);t.image.colorspace_settings.name='sRGB' if slot=='Base Color' else 'Non-Color'
  if slot=='Normal':q=n.nodes.new('ShaderNodeNormalMap');q.inputs['Strength'].default_value=.25;n.links.new(t.outputs['Color'],q.inputs['Color']);n.links.new(q.outputs['Normal'],p.inputs[slot])
  else:n.links.new(t.outputs['Color'],p.inputs[slot])
 return m
can={k:material(k) for k in ['CanvasCream','CanvasRed','CanvasTeal']}
for o in bpy.data.objects:
 if o.type!='MESH':continue
 if o.name.startswith('Carousel | weathered canvas gore'):
  for slot in o.material_slots:
   if slot.material:slot.material=can['CanvasRed' if slot.material.name=='red' else 'CanvasCream']
 elif o.name.startswith('Carousel horse') or o.name.startswith('Carousel | scalloped painted valance') or o.name.startswith('Carousel | central drum'):
  o.data=o.data.copy()
  for slot in o.material_slots:
   if slot.material and slot.material.name in ['cream','red','teal']:slot.material=bpy.data.materials[{'cream':'PaintCream','red':'PaintRed','teal':'PaintTeal'}[slot.material.name]]
  if o.data.uv_layers.active:
   for p in o.data.polygons:
    if o.data.materials[p.material_index].name.startswith('Paint'):
     for li in p.loop_indices:o.data.uv_layers.active.data[li].uv/= .8
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
