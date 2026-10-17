import bpy,os
from PIL import Image, ImageEnhance
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ImageEnhance.Brightness(Image.open(R+'/textures/natural_leaf_veins.png').convert('RGB')).enhance(2.4).save(R+'/textures/natural_leaf_veins_living.png')
im=bpy.data.images.load(R+'/textures/natural_leaf_veins_living.png',check_existing=True)
for m in bpy.data.materials:
 if not m.use_nodes:continue
 if 'foliage' in m.name.lower() or 'Forest leaf' in m.name:
  for n in m.node_tree.nodes:
   if n.type=='TEX_IMAGE' and n.image and ('leaf_veins' in n.image.name.lower() or 'natural_leaf' in n.image.name.lower()):n.image=im
   if n.type=='BUMP':n.inputs['Distance'].default_value=.0005;n.inputs['Strength'].default_value=.15
  p=m.node_tree.nodes.get('Principled BSDF')
  if p:p.inputs['Roughness'].default_value=.65;p.inputs['Sheen Weight'].default_value=.1
im.pack();bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend')
