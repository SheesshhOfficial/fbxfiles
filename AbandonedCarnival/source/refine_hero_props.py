import bpy,os,math,random
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));random.seed(947)
# Proper rotational bottle shoulder and sealed cap.
profile=[(.004,.049),(.008,.058),(.018,.064),(.205,.064),(.238,.061),(.262,.053),(.282,.038),(.297,.027),(.355,.027),(.364,.032),(.38,.032)]
N=32;vs=[];fs=[];mids=[]
for z,r in profile:
 for i in range(N):a=i*math.tau/N;vs.append((r*math.cos(a),r*math.sin(a),z))
for j in range(len(profile)-1):
 for i in range(N):fs.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i));mids.append(0)
fs.append(tuple(reversed(range(N))));mids.append(0)
# A sealed weathered cap is part of the same prop; no glass opening is implied.
k=len(vs)
for z,r in [(.38,.033),(.392,.033),(.398,.03)]:
 for i in range(N):a=i*math.tau/N;vs.append((r*math.cos(a),r*math.sin(a),z))
for j in range(2):
 for i in range(N):fs.append((k+j*N+i,k+j*N+(i+1)%N,k+(j+1)*N+(i+1)%N,k+(j+1)*N+i));mids.append(1)
fs.append(tuple(k+2*N+i for i in range(N)));mids.append(1)
# close body top below cap
fs.append(tuple((len(profile)-1)*N+i for i in range(N)));mids.append(0)
fs.append(tuple(k+i for i in reversed(range(N))));mids.append(1)
me=bpy.data.meshes.new('HeroBottle_RoundedShoulders');me.from_pydata(vs,[],fs);me.materials.append(bpy.data.materials['glass']);me.materials.append(bpy.data.materials['rust']);me.update();uv=me.uv_layers.new()
for p,idx in zip(me.polygons,mids):
 p.material_index=idx;p.use_smooth=len(p.vertices)==4
 for li in p.loop_indices:
  v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(math.atan2(v.y,v.x)/math.tau+.5,v.z/.398) if len(p.vertices)==4 else (v.x/.13+.5,v.y/.13+.5)
for o in bpy.data.objects:
 if o.get('PropActorTag') and o.get('asset_family')=='Bottle':o.data=me
# Matte woven plush, no corroded-metal cream texture on teddy prizes.
mat=bpy.data.materials.new('Aged tan plush fabric');mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.28,.15,.055,1);p.inputs['Roughness'].default_value=.92;p.inputs['Sheen Weight'].default_value=.3
nt=mat.node_tree
for kind,path in [('Base Color','plush_fabric_basecolor.png'),('Normal','plush_fabric_normal.png')]:
 tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(R+'/textures/'+path,check_existing=True);tex.image.colorspace_settings.name='Non-Color' if kind=='Normal' else 'sRGB'
 if kind=='Normal':
  nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.45;nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
 else:nt.links.new(tex.outputs['Color'],p.inputs[kind])
snout=bpy.data.materials.new('Dark plush muzzle');snout.use_nodes=True;p=snout.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.075,.038,.014,1);p.inputs['Roughness'].default_value=.95
for o in bpy.data.objects:
 if o.get('PropActorTag') and o.get('asset_family')=='TeddyPrize':
  for slot in o.material_slots:
   if slot.material and (slot.material.name=='cream' or slot.material.name.startswith('Aged tan plush fabric')):slot.material=mat
   elif slot.material and (slot.material.name=='wood' or slot.material.name.startswith('Dark plush muzzle')):slot.material=snout
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Rounded hero bottles and plush shading saved')
