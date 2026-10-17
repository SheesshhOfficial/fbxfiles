import bpy,re
from mathutils import Vector

def assemble(name,parts,origin,family):
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();vs=[];fs=[];mi=[];uvs=[];materials=[]
 for o in parts:
  if o.type not in {'MESH','CURVE','FONT'}:continue
  ev=None
  if o.type=='MESH':me=o.data
  else:ev=o.evaluated_get(dg);me=ev.to_mesh()
  off=len(vs);vs.extend([o.matrix_world@v.co-Vector(origin) for v in me.vertices]);remap=[]
  for m in me.materials:
   if m not in materials:materials.append(m)
   remap.append(materials.index(m))
  layer=me.uv_layers.active
  for p in me.polygons:
   fs.append(tuple(off+i for i in p.vertices));mi.append(remap[p.material_index] if remap else 0)
   uvs.append([tuple(layer.data[i].uv) for i in p.loop_indices] if layer else [(0,0)]*len(p.vertices))
  if ev:ev.to_mesh_clear()
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
 for m in materials:me.materials.append(m)
 layer=me.uv_layers.new()
 for p,mat,uv in zip(me.polygons,mi,uvs):
  p.material_index=mat
  for li,co in zip(p.loop_indices,uv):layer.data[li].uv=co
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.location=origin;ob['PropActorTag']=True;ob['asset_family']=family
 for o in parts:
  o['_assembly_source']=True
  if 'PropActorTag' in o:del o['PropActorTag']
 return ob

def consolidate_midway():
 groups={}
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH':continue
  match=re.match(r'(Midway .+? (bottle\d+|prize\d+|bin)) ',o.name)
  if match:groups.setdefault(match.group(1),[]).append(o)
 for name,parts in groups.items():
  points=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box];origin=((min(p.x for p in points)+max(p.x for p in points))/2,(min(p.y for p in points)+max(p.y for p in points))/2,min(p.z for p in points))
  assemble(name,parts,origin,'Bottle' if 'bottle' in name else 'TeddyPrize' if 'prize' in name else 'Barrel')
