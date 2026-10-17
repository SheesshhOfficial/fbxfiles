"""Save-free evaluated decoration cleanup, copied from the checked V1 utility."""
import bpy
def apply():
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();records=[]
 for o in list(bpy.context.scene.objects):
  if o.type not in {'MESH','FONT','CURVE'} or o.get('PropActorTag') or o.hide_render or o.get('_assembly_source') or o.get('visual_replaced') or o.get('render_only'):continue
  ev=o.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
  if me is None:continue
  me.calc_loop_triangles();bad=[t for t in me.loop_triangles if t.area<=1e-12]
  if not bad:ev.to_mesh_clear();continue
  good=[t for t in me.loop_triangles if t.area>1e-12];vs=[tuple(v.co) for v in me.vertices];fs=[tuple(t.vertices) for t in good];uv=me.uv_layers.active;uvs=[[tuple(uv.data[i].uv) for i in t.loops] for t in good] if uv else None
  normals=[tuple(me.corner_normals[i].vector) for t in good for i in t.loops];mats=[m.name if m else None for m in me.materials];ids=[t.material_index for t in good];smooth=[me.polygons[t.polygon_index].use_smooth for t in good]
  name=o.name;removed=len(bad);before=len(me.loop_triangles);ev.to_mesh_clear()
  clean=bpy.data.meshes.new(name+' evaluated clean');clean.from_pydata(vs,[],fs);clean.update()
  for mat_name in mats:clean.materials.append(bpy.data.materials[mat_name] if mat_name else None)
  if uvs:
   layer=clean.uv_layers.new(name='UVMap')
   for p,coords in zip(clean.polygons,uvs):
    for li,co in zip(p.loop_indices,coords):layer.data[li].uv=co
  for p,mi,sm in zip(clean.polygons,ids,smooth):p.material_index=mi;p.use_smooth=sm
  clean.normals_split_custom_set(normals);clean.update()
  layer=clean.uv_layers.active or clean.uv_layers.new(name='UVMap')
  for p in clean.polygons:
   pts=[layer.data[i].uv.copy() for i in p.loop_indices];area=abs(sum(pts[j].x*pts[(j+1)%len(pts)].y-pts[(j+1)%len(pts)].x*pts[j].y for j in range(len(pts)))*.5)
   if area<=1e-12:
    axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis];origin=clean.vertices[p.vertices[0]].co
    for li in p.loop_indices:
     v=clean.vertices[clean.loops[li].vertex_index].co-origin;layer.data[li].uv=(v[axes[0]],v[axes[1]])
  if o.type=='MESH':o.data=clean;o.modifiers.clear()
  else:
   new=bpy.data.objects.new(name+' clean',clean);bpy.context.collection.objects.link(new);new.matrix_world=o.matrix_world.copy();o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
  records.append({'object':name,'triangles_before':before,'removed_zero_area':removed,'triangles_after':len(fs)})
 return {'objects':records,'removed_total':sum(r['removed_zero_area'] for r in records),'eligible_props_changed':0}
