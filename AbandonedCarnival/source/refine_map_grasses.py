"""Replace coarse triangular weed tufts with folded arching grass blades."""
import bpy,random,math,os
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));rng=random.Random(559)
mat=bpy.data.materials.new('Natural arching grass blades');mat.use_nodes=True;n=mat.node_tree;p=n.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.8;p.inputs['Base Color'].default_value=(.075,.105,.025,1)
t=n.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(R+'/textures/natural_leaf_veins_living.png',check_existing=True);n.links.new(t.outputs['Color'],p.inputs['Base Color'])
vs=[];fs=[];uvs=[]
def face(points,uv):
 k=len(vs);vs.extend(points);fs.append(tuple(range(k,k+len(points))));uvs.extend(uv)
for b in range(23):
 a=rng.random()*math.tau;d=Vector((math.cos(a),math.sin(a),0));s=Vector((-d.y,d.x,0));root=Vector((rng.uniform(-.11,.11),rng.uniform(-.11,.11),0));h=rng.uniform(.14,.38);w=rng.uniform(.008,.019);bend=rng.uniform(.05,.19)
 rows=[]
 for k in range(5):
  t0=k/4;c=root+d*(bend*t0*t0)+Vector((0,0,h*math.sin(t0*1.65)));ww=w*(1-t0*.88)/2
  rows.append((c-s*ww,c+Vector((0,0,w*.2)),c+s*ww))
 for k in range(4):
  for side in range(2):face([rows[k][side],rows[k][side+1],rows[k+1][side+1],rows[k+1][side]],[(side*.5,k/4),((side+1)*.5,k/4),((side+1)*.5,(k+1)/4),(side*.5,(k+1)/4)])
me=bpy.data.meshes.new('Folded arching grass clump');me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();uv=me.uv_layers.new();uv.data.foreach_set('uv',[c for p in uvs for c in p])
count=0
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('Overgrowth grass tuft'):
  o.data=me;count+=1
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True);print('Grass tufts refined:',count)
