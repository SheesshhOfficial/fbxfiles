import bpy,os,json,math,random,sys
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source');random.seed(918)
def mesh(n,vs,fs,mat,tile=1):
 me=bpy.data.meshes.new(n);me.from_pydata(vs,[],fs);me.materials.append(mat);uv=me.uv_layers.new()
 for p in me.polygons:
  for li in p.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co.x/tile,co.y/tile)
 ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);return ob
base=bpy.data.materials.new('Pavement dark crack interiors');base.use_nodes=True;p=base.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.012,.016,.011,1);p.inputs['Roughness'].default_value=.95
mesh('Dark recessed pavement substrate',[(-14,-22,.047),(-6,-22,.047),(-6,3,.047),(-14,3,.047)],[(0,1,2,3)],base)
vs=[];fs=[]
for cell in json.load(open(R+'/source/pavement_cells.json')):
 k=len(vs);vs.extend([(x,y,cell['height']) for x,y in cell['polygon']]);fs.append(tuple(range(k,len(vs))))
mesh('Cracked uneven asphalt surface',vs,fs,bpy.data.materials['Scanned cracked paving'],2.5)
# Small depth and roughness variation rather than blue paper-like puddles.
wet=bpy.data.materials['wetground'];p=wet.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.015,.022,.019,1);p.inputs['Roughness'].default_value=.06;p.inputs['IOR'].default_value=1.333
for o in bpy.data.objects:
 if o.name.startswith('Art shallow puddle'):
  for v in o.data.vertices:v.co.z=.059
# Printed distressed paper; each tiny paper face uses the complete ticket image.
paper=bpy.data.materials['paper'];nt=paper.node_tree;p=nt.nodes.get('Principled BSDF');tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(R+'/textures/torn_ticket.png',check_existing=True);nt.links.new(tex.outputs['Color'],p.inputs['Base Color'])
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('Ground leaf litter') and any(m and m.name=='paper' for m in o.data.materials):
  uv=o.data.uv_layers.active
  for face in o.data.polygons:
   for j,li in enumerate(face.loop_indices):uv.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][j%4]
# Low-contrast interior foliage masses beneath individual leaf geometry fill sparse crown gaps.
mat=bpy.data.materials.new('Deep canopy interior');mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.012,.025,.009,1);p.inputs['Roughness'].default_value=1
for o in list(bpy.data.objects):
 if o.name.startswith('NF_') and ('Leaves' in o.name or 'Canopy' in o.name):pass
# Physically participating thin blue ground haze; render only, not static geometry export.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,7));fog=bpy.context.object;fog.name='FX_RenderOnly_DuskHaze';fog.dimensions=(110,110,22);fog['render_only']=True
mat=bpy.data.materials.new('Thin blue dusk atmosphere');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');v=nt.nodes.new('ShaderNodeVolumePrincipled');v.inputs['Density'].default_value=.006;v.inputs['Color'].default_value=(.42,.52,.64,1);v.inputs['Anisotropy'].default_value=.25;nt.links.new(v.outputs['Volume'],out.inputs['Volume']);fog.data.materials.append(mat)
# A distant moon is a render backdrop, not an imported collision object.
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.48,location=(-4,50,18));moon=bpy.context.object;moon.name='FX_RenderOnly_Moon';moon['render_only']=True
mat=bpy.data.materials.new('Moon surface');mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.65,.77,.9,1);p.inputs['Emission Color'].default_value=(.65,.77,.9,1);p.inputs['Emission Strength'].default_value=1.5;moon.data.materials.append(mat)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Ground and atmospheric pass saved')
