"""Read-only independent audit. Run blender -b -t 2 --python this_file.py."""
import bpy,bmesh,math,json,os,collections
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=ROOT+'/blender/Moonfall_Carnival.blend')
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
 if o.get('PropActorTag') and not o.get('_assembly_source'):
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
report={'scope':'Saved Blender source read-only audit; no scene writes, runtime collision, or Unreal validation. Base mesh UV and finite checks; prop component closed-volume/winding checks. Open surfaces can be intentional. Degenerate UV faces are warnings, not automatically invalid geometry.','file':ROOT+'/blender/Moonfall_Carnival.blend','objects':len(scene.objects),'mesh_objects':sum(o.type=='MESH' for o in scene.objects),'unique_meshes':len(cache),'unique_mesh_vertices':sum(r['vertices'] for r in cache.values()),'unique_mesh_polygons':sum(r['polygons'] for r in cache.values()),'assembly_source_objects':sum(bool(o.get('_assembly_source')) for o in scene.objects),'gameplay_prop_count':len(props),'gameplay_prop_families':dict(families),'player_starts':sum(o.name.startswith('PlayerStart') for o in scene.objects),'all_mesh_bounds':bbox(all_bounds),'visible_mesh_bounds_including_scenery':bbox(visible_bounds),'issues':issues,'eligible_prop_topology':props,'unreal_runtime_verified':False}
open(ROOT+'/qa/geometry_audit.json','w').write(json.dumps(report,indent=2))
print('AUDIT_SUMMARY',json.dumps({'objects':report['objects'],'props':len(props),'families':dict(families),'issues':{k:len(v) for k,v in issues.items()},'props_negative_closed_components':[p['object'] for p in props if p['negative_closed_components']],'props_inconsistent_winding':[p['object'] for p in props if p['inconsistent_winding_edges']],'props_open':[p['object'] for p in props if not p['closed_manifold']]}))
