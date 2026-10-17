"""Read-only independent audit. Run blender -b -t 2 --python this_file.py."""
import bpy,bmesh,math,json,os,collections,hashlib
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
assert bpy.data.filepath, 'Load an iteration checkpoint before auditing'
scene=bpy.context.scene
finite=lambda seq:all(math.isfinite(float(v)) for v in seq)
issues={k:[] for k in ['nonfinite_transforms','nonfinite_vertices','nonfinite_uvs','missing_uv','degenerate_uv_faces','zero_area_faces','invalid_material_indices','empty_material_slots','empty_meshes']}
cache={}; props=[]; all_bounds=[]; visible_bounds=[]; families=collections.Counter()
for o in scene.objects:
 if not finite(v for row in o.matrix_world for v in row):issues['nonfinite_transforms'].append(o.name)
 if o.type!='MESH':continue
 me=o.data
 if me.name not in cache:
  r={'vertices':len(me.vertices),'polygons':len(me.polygons),'zero_area_faces':[],'nonfinite_vertices':[],'nonfinite_uvs':[],'degenerate_uv_faces':[],'invalid_material_indices':[],'empty_material_slots':[i for i,m in enumerate(me.materials) if m is None],'uv_layers':len(me.uv_layers)}
  r['nonfinite_vertices']=[v.index for v in me.vertices if not finite(v.co)]
  for p in me.polygons:
   if p.area<=1e-12:r['zero_area_faces'].append(p.index)
   if p.material_index>=len(me.materials):r['invalid_material_indices'].append(p.index)
  uv=me.uv_layers.active
  if uv:
   r['nonfinite_uvs']=[i for i,d in enumerate(uv.data) if not finite(d.uv)]
   for p in me.polygons:
    pts=[uv.data[i].uv for i in p.loop_indices]
    a=sum(pts[i].x*pts[(i+1)%len(pts)].y-pts[(i+1)%len(pts)].x*pts[i].y for i in range(len(pts)))*.5 if len(pts)>=3 else 0
    if abs(a)<=1e-12:r['degenerate_uv_faces'].append(p.index)
  cache[me.name]=r
 r=cache[me.name]
 for k in ['nonfinite_vertices','nonfinite_uvs','degenerate_uv_faces','zero_area_faces','invalid_material_indices','empty_material_slots']:
  if r[k]:issues[k].append({'object':o.name,'mesh':me.name,'count':len(r[k]),'face_or_slot_samples':r[k][:12],'assembly_source':bool(o.get('_assembly_source'))})
 if not r['uv_layers']:issues['missing_uv'].append(o.name)
 if not r['vertices'] or not r['polygons']:issues['empty_meshes'].append(o.name)
 bounds=[o.matrix_world@Vector(co) for co in o.bound_box];all_bounds.extend(bounds)
 if not o.hide_render and not o.get('_assembly_source'):visible_bounds.extend(bounds)
 if o.get('PropActorTag') and not any(o.get(k) for k in ('_assembly_source','visual_replaced','render_only')) and not o.hide_render and not o.hide_viewport and not o.hide_get():
  bm=bmesh.new();bm.from_mesh(me)
  boundary=sum(e.is_boundary for e in bm.edges); nonmanifold=sum(not e.is_manifold for e in bm.edges)
  winding=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
  signed=bm.calc_volume(signed=True)*o.matrix_world.determinant() if bm.faces else 0
  components=[];left=set(bm.faces)
  while left:
   seed=left.pop();part={seed};stack=[seed]
   while stack:
    f=stack.pop()
    for e in f.edges:
     for n in e.link_faces:
      if n in left:left.remove(n);part.add(n);stack.append(n)
   edges={e for f in part for e in f.edges};closed=all(len(e.link_faces)==2 for e in edges)
   # Signed triangle-fan volume of this disconnected component; original meshes untouched.
   v=0.0
   if closed:
    for f in part:
     a=f.verts[0].co
     for i in range(1,len(f.verts)-1):v+=a.dot(f.verts[i].co.cross(f.verts[i+1].co))/6
   components.append({'faces':len(part),'closed':closed,'signed_volume_m3':v*o.matrix_world.determinant() if closed else None})
  bm.free();family=o.get('asset_family','unspecified');families[family]+=1
  props.append({'object':o.name,'family':family,'hidden_render':o.hide_render,'vertices':r['vertices'],'polygons':r['polygons'],'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'inconsistent_winding_edges':winding,'closed_manifold':nonmanifold==0,'signed_volume_m3':signed if nonmanifold==0 else None,'components':len(components),'closed_components':sum(c['closed'] for c in components),'negative_closed_components':[c for c in components if c['closed'] and c['signed_volume_m3']<-1e-9],'near_zero_closed_components':sum(c['closed'] and abs(c['signed_volume_m3'])<1e-9 for c in components)})
def bbox(points):return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]} if points else None
report={'scope':'Saved Blender source read-only audit; no scene writes, runtime collision, or Unreal validation. Base mesh UV and finite checks; prop component closed-volume/winding checks. Open surfaces can be intentional. Degenerate UV faces are warnings, not automatically invalid geometry.','file':bpy.data.filepath,'objects':len(scene.objects),'mesh_objects':sum(o.type=='MESH' for o in scene.objects),'unique_meshes':len(cache),'unique_mesh_vertices':sum(r['vertices'] for r in cache.values()),'unique_mesh_polygons':sum(r['polygons'] for r in cache.values()),'assembly_source_objects':sum(bool(o.get('_assembly_source')) for o in scene.objects),'gameplay_prop_count':len(props),'gameplay_prop_families':dict(families),'player_starts':sum(o.name.startswith('PlayerStart') for o in scene.objects),'all_mesh_bounds':bbox(all_bounds),'visible_mesh_bounds_including_scenery':bbox(visible_bounds),'issues':issues,'eligible_prop_topology':props,'unreal_runtime_verified':False}

images=[]
for im in bpy.data.images:
 if im.source!='FILE':continue
 path=bpy.path.abspath(im.filepath)
 images.append({'name':im.name,'filepath':im.filepath,'resolved_exists':os.path.isfile(path),'packed':bool(im.packed_file),'size':list(im.size),'colorspace':im.colorspace_settings.name})
materials=[]
for mat in bpy.data.materials:
 if not mat.get('physical_tile_m'):continue
 nt=mat.node_tree
 materials.append({'name':mat.name,'physical_tile_m':mat['physical_tile_m'],'image_nodes':sum(n.type=='TEX_IMAGE' for n in nt.nodes),'uv_coordinate_links':sum(l.from_node.type=='TEX_COORD' and l.from_socket.name=='UV' for l in nt.links),'vector_scales':[n.inputs[3].default_value for n in nt.nodes if n.type=='VECT_MATH' and n.operation=='SCALE']})
scales=collections.defaultdict(list)
for o in scene.objects:
 if o.type!='MESH' or o.get('_assembly_source') or o.hide_render:continue
 me=o.data;uv=me.uv_layers.active
 if not uv:continue
 for p in me.polygons:
  if p.material_index>=len(me.materials):continue
  mat=me.materials[p.material_index]
  if not mat or not mat.get('physical_tile_m'):continue
  pts=[uv.data[i].uv for i in p.loop_indices]
  area=abs(sum(pts[i].x*pts[(i+1)%len(pts)].y-pts[(i+1)%len(pts)].x*pts[i].y for i in range(len(pts)))*.5)
  if area>1e-10 and p.area>1e-10:scales[mat.name].append(math.sqrt(p.area/area))
report['image_integrity']={'file_images':len(images),'packed_images':sum(i['packed'] for i in images),'unresolved_unpacked':[i for i in images if not i['packed'] and not i['resolved_exists']],'zero_size':[i for i in images if min(i['size'])<=0],'images':images}
report['physical_uv_materials']=materials
report['physical_uv_scale_samples']={k:{'faces':len(v),'median_local_m_per_uv_unit':sorted(v)[len(v)//2],'expected_tile_m':bpy.data.materials[k]['physical_tile_m'],'within_2pct_faces':sum(abs(q/bpy.data.materials[k]['physical_tile_m']-1)<.02 for q in v)} for k,v in scales.items()}
report['physical_uv_scale_note']='Local geometric face area vs UV area is a diagnostic, not a guarantee for rotated or curved planar projections. Node scale must remain1 because physical tiling is baked into loops. Object nonunit scale may further alter world texel density.'


# Distinguish real exportable instances from staging and render-only objects.
visibility={k:{'objects':0,'mesh_objects':0,'base_triangles':0} for k in ['_assembly_source','visual_replaced','render_only','hidden','visible_exportable']}
triangle_cache={};evaluated_triangles=0;visible_meshes=0;loop_triangle_issues=[];dg=bpy.context.evaluated_depsgraph_get()
for o in scene.objects:
 flags=[k for k in ('_assembly_source','visual_replaced','render_only') if o.get(k)]
 hidden=o.hide_render or o.hide_viewport or o.hide_get()
 if hidden:flags.append('hidden')
 if not flags:flags=['visible_exportable']
 tri=0
 if o.type=='MESH':
  if o.data.name not in triangle_cache:
   o.data.calc_loop_triangles();triangle_cache[o.data.name]=len(o.data.loop_triangles)
  tri=triangle_cache[o.data.name]
 for flag in flags:
  visibility[flag]['objects']+=1;visibility[flag]['mesh_objects']+=int(o.type=='MESH');visibility[flag]['base_triangles']+=tri
 if flags==['visible_exportable'] and o.type=='MESH':
  visible_meshes+=1
  if len(o.modifiers):
   ev=o.evaluated_get(dg);em=ev.to_mesh();em.calc_loop_triangles();evaluated_triangles+=len(em.loop_triangles)
   bad=[t.index for t in em.loop_triangles if t.area<=1e-12]
   if bad:loop_triangle_issues.append({'object':o.name,'count':len(bad),'samples':bad[:12],'evaluated':True})
   ev.to_mesh_clear()
  else:
   evaluated_triangles+=tri
   bad=[t.index for t in o.data.loop_triangles if t.area<=1e-12]
   if bad:loop_triangle_issues.append({'object':o.name,'count':len(bad),'samples':bad[:12],'evaluated':False})
report['visible_evaluated_zero_area_loop_triangles']=loop_triangle_issues
report['visibility_categories']=visibility
report['visible_exportable_evaluated_mesh_triangles']=evaluated_triangles
report['visible_exportable_mesh_instances']=visible_meshes
report['visibility_note']='Categories overlap: an assembly source can also be hidden. Visible exportable excludes all three flags plus render/viewport/local hidden objects. Evaluated triangles include modifiers, count instances, and exclude curves/fonts/lights.'
report['excluded_tagged_objects']=[{'object':o.name,'flags':[k for k in ('_assembly_source','visual_replaced','render_only') if o.get(k)],'hidden':bool(o.hide_render or o.hide_viewport or o.hide_get())} for o in scene.objects if o.get('PropActorTag') and (any(o.get(k) for k in ('_assembly_source','visual_replaced','render_only')) or o.hide_render or o.hide_viewport or o.hide_get())]
report['source_file_stat']={'bytes':os.stat(report['file']).st_size,'mtime':os.stat(report['file']).st_mtime}
with open(report['file'],'rb') as source:report['source_sha256']=hashlib.file_digest(source,'sha256').hexdigest()
for key,entries in report['issues'].items():
 for item in entries:
  if isinstance(item,dict) and item.get('object'):
   ob=scene.objects.get(item['object']);item['exclusion_flags']=[k for k in ('_assembly_source','visual_replaced','render_only') if ob.get(k)];item['hidden']=bool(ob.hide_render or ob.hide_viewport or ob.hide_get())

open(ROOT+'/iterations/qa/current_geometry_audit.json','w').write(json.dumps(report,indent=2))
print('AUDIT_SUMMARY',json.dumps({'objects':report['objects'],'props':len(props),'families':dict(families),'issues':{k:len(v) for k,v in issues.items()},'props_negative_closed_components':[p['object'] for p in props if p['negative_closed_components']],'props_inconsistent_winding':[p['object'] for p in props if p['inconsistent_winding_edges']],'props_open':[p['object'] for p in props if not p['closed_manifold']]}))
