import bpy,os,math,json
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def surface(name,base,normal,rough,tile=1,metal=0,normal_strength=.7):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');p=nt.nodes.new('ShaderNodeBsdfPrincipled');nt.links.new(p.outputs['BSDF'],out.inputs['Surface']);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.85
 uv=nt.nodes.new('ShaderNodeTexCoord');sc=nt.nodes.new('ShaderNodeVectorMath');sc.operation='SCALE';sc.inputs[3].default_value=1.0;nt.links.new(uv.outputs['UV'],sc.inputs[0])
 for kind,path in [('Base Color',base),('Roughness',rough),('Normal',normal)]:
  tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(path,check_existing=True);tex.image.colorspace_settings.name='sRGB' if kind=='Base Color' else 'Non-Color';nt.links.new(sc.outputs['Vector'],tex.inputs['Vector'])
  if kind=='Normal':
   nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=normal_strength;nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
  else:nt.links.new(tex.outputs['Color'],p.inputs[kind])
 m['source']='ambientCG CC0, derived weathering where specified';m['physical_tile_m']=tile;return m
D=R+'/textures/derived/'
def derived(mat,key,tile=1,metal=0):return surface(mat,D+key+'_basecolor.jpg',D+key+'_normal.jpg',D+key+'_roughness.jpg',tile,metal)
derived('wood','WeatheredWood',.8);derived('rust','CorrodedMetal',.8,.1)
for key in ['PaintRed','PaintTeal','PaintCream']:derived(key,key,.8)
paving=derived('Scanned cracked paving','CrackedAsphalt',2.5)
A=R+'/textures/realistic/Ground112/Ground112_2K-JPG_';surface('ground',A+'Color.jpg',A+'NormalGL.jpg',A+'Roughness.jpg',2.0,0,.85)
# Material slot substitution only in painted timber, not horses, toys or metal cars.
for o in bpy.data.objects:
 if o.type!='MESH':continue
 if o.name.startswith('Midway ') and 'front skirt' in o.name:
  for slot in o.material_slots:
   if slot.material and slot.material.name in ['red','teal','cream']:slot.material=bpy.data.materials[{'red':'PaintRed','teal':'PaintTeal','cream':'PaintCream'}[slot.material.name]]
 if any(t in o.name for t in ['paved route','Central crosswalk','Backstage approach','Backstage clear central aisle']):
  o.data.materials.clear();o.data.materials.append(paving)
# Plank grain follows the longest projected direction on each wood face.
seen=set()
for o in bpy.data.objects:
 if o.type!='MESH' or o.data.name in seen:continue
 me=o.data;seen.add(me.name)
 if not me.uv_layers:continue
 uv=me.uv_layers.active
 for p in me.polygons:
  if p.material_index>=len(me.materials) or not me.materials[p.material_index] or me.materials[p.material_index].name!='wood':continue
  axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis];spans={a:max(me.vertices[i].co[a] for i in p.vertices)-min(me.vertices[i].co[a] for i in p.vertices) for a in axes};v=max(axes,key=lambda a:spans[a]);u=[a for a in axes if a!=v][0]
  for li in p.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co[u],co[v])
# Bake physical tile scaling into UV loops for portable FBX materials.
seen=set()
for o in bpy.data.objects:
 if o.type!='MESH' or o.data.name in seen:continue
 me=o.data;seen.add(me.name)
 if not me.uv_layers:continue
 for p in me.polygons:
  mat=me.materials[p.material_index] if p.material_index<len(me.materials) else None
  if mat and mat.get('physical_tile_m'):
   for li in p.loop_indices:me.uv_layers.active.data[li].uv/=float(mat['physical_tile_m'])
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Scanned surfaces applied')
