"""Read-only loaded source to explicit UE-coordinate FBX props.
V2 only: approved Cycle_10.blend, after environment export. Code preparation only until scheduled.
Does not save or alter the source blend. Import with Convert Scene OFF and units OFF.
"""
import bpy,bmesh,json,hashlib,os,re,collections,math
from mathutils import Matrix,Vector
from pathlib import Path
import sys
PROJECT=Path(__file__).resolve().parents[2]
ROOT=str(PROJECT/'iterations/export')
SOURCE=str(PROJECT/'iterations/Cycle_10.blend')
sha=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest()
approved_hash=os.environ.get('CARNIVAL_V2_SOURCE_SHA256','')
if Path(bpy.data.filepath).resolve()!=Path(SOURCE).resolve():raise RuntimeError('V2 requires loaded iterations/Cycle_10.blend')
if len(approved_hash)!=64 or sha(SOURCE)!=approved_hash:raise RuntimeError('CARNIVAL_V2_SOURCE_SHA256 must match the coordinator-approved frozen Cycle 10 source')
if int(bpy.context.scene.get('refinement_cycle_completed',0))!=10:raise RuntimeError('Cycle 10 scene marker missing')
# Reload only the same approved source; never inherit incidental unsaved edits.
bpy.ops.wm.open_mainfile(filepath=SOURCE)
if sha(SOURCE)!=approved_hash:raise RuntimeError('Source changed during reload')
source_hash=approved_hash
for filename,key in [('environment_manifest.json','source_sha256'),('material_manifest.json','source_sha256')]:
 path=Path(ROOT)/'unreal'/filename
 if not path.is_file():raise RuntimeError('Run V2 environment export first: missing '+filename)
 if json.loads(path.read_text()).get(key)!=source_hash:raise RuntimeError('V2 package source hash mismatch: '+filename)
OUT=ROOT+'/unreal/props'
if os.path.exists(OUT) and os.listdir(OUT):raise RuntimeError('V2 props output is nonempty; archive the partial prop output explicitly before retry')
if os.path.exists(ROOT+'/unreal/prop_placements.json'):raise RuntimeError('V2 prop manifest already exists; archive explicitly before retry')
# Environment owns texture copying. Exact packed bytes support portable .blend files
# when their original disk paths are unavailable; this branch never writes textures.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v2_texture_staging import texture_payload, staged_texture_path
texture_verification=[]
for image in bpy.data.images:
 if image.source!='FILE' or not image.filepath:continue
 path=Path(bpy.path.abspath(image.filepath)).resolve()
 payload=texture_payload(path,lambda image=image: bytes(image.packed_file.data) if image.packed_file else None)
 copied=staged_texture_path(Path(ROOT)/'textures',payload,write=False)
 texture_verification.append({'image':image.name,'payload_origin':payload[2],'sha256':payload[3],'staged_relative_path':str(copied.relative_to(Path(ROOT)))})
 image.filepath=str(copied)
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(PROJECT/'source'))
from fbx_exact_normals import replace_corner_normals
from prepare_refined_prop_collision_v2 import prepare_collision_recipes
recipe_bundle=prepare_collision_recipes()
if recipe_bundle['actor_count']!=19 or recipe_bundle['placed_hull_budget']!=160:raise RuntimeError('Refined collision recipe contract differs from approved 19 actors /160 hulls')
recipes={a['source_object']:a for a in recipe_bundle['actors']}
os.makedirs(OUT,exist_ok=True)
Path(ROOT+'/qa').mkdir(exist_ok=True)
prior_manifest=None
source_scene=bpy.context.scene
def excluded_reasons(o):
 return [key for key in ('_assembly_source','visual_replaced','render_only') if o.get(key)] + (['hidden'] if o.hide_render or o.hide_viewport or o.hide_get() else [])
props=[o for o in source_scene.objects if o.type=='MESH' and o.get('PropActorTag') and not excluded_reasons(o)]
if len(props)!=153:raise RuntimeError('Expected exactly153 eligible Cycle10 placements; found '+str(len(props)))
material_manifest=json.load(open(ROOT+'/unreal/material_manifest.json'))
material_names={r['source_name'] for r in material_manifest['materials']}
missing_materials=sorted({m.name for o in props for m in o.data.materials if m and m.name not in material_names})
if missing_materials:raise RuntimeError('V2 shared material manifest lacks prop slots: '+str(missing_materials))
excluded=[o.name for o in source_scene.objects if o.get('PropActorTag') and excluded_reasons(o)]
excluded_details=[{'object':o.name,'reasons':excluded_reasons(o)} for o in source_scene.objects if o.get('PropActorTag') and excluded_reasons(o)]
dg=bpy.context.evaluated_depsgraph_get()
# Explicit UE handedness and centimetres; FBX importer must NOT convert coordinates again.
C=Matrix.Diagonal((100.,-100.,100.))
scene=bpy.data.scenes.new('PROP_EXPORT_ONLY');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
assets={};placements=[];reports=[];material_report={}
def transform_mesh_preserving_corner_normals(me,linear):
 """Transform positions and evaluated corner normals, retaining sharp/custom splits.
 Capture by face and vertex before reflection reverses face-loop order.
 """
 normal_matrix=linear.inverted().transposed()
 corner_normals={}
 for poly in me.polygons:
  for loop_index in poly.loop_indices:
   loop=me.loops[loop_index]
   corner_normals[(poly.index,loop.vertex_index)]=(normal_matrix@me.corner_normals[loop_index].vector).normalized()
 me.transform(linear.to_4x4())
 if linear.determinant()<0:me.flip_normals()
 me.update()
 transformed=[None]*len(me.loops)
 for poly in me.polygons:
  for loop_index in poly.loop_indices:
   transformed[loop_index]=corner_normals[(poly.index,me.loops[loop_index].vertex_index)]
 me.normals_split_custom_set(transformed)
 me.update()
 return [tuple(v) for v in transformed]

def key(me,exact_normals):
 payload={'vertices':[[round(x,4) for x in v.co] for v in me.vertices], 'faces':[(list(p.vertices),p.material_index,p.use_smooth) for p in me.polygons], 'materials':[m.name if m else None for m in me.materials], 'corner_normals':[[round(x,9) for x in n] for n in exact_normals], 'uvs':[[[round(x,6) for x in d.uv] for d in l.data] for l in me.uv_layers]}
 return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()
def collision_parts(me,name):
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
 bm.verts.ensure_lookup_table();left=set(bm.verts);parts=[];notes=[]
 while left:
  seed=left.pop();part={seed};stack=[seed]
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in left:left.remove(w);part.add(w);stack.append(w)
  faces={f for v in part for f in v.link_faces};edges={e for v in part for e in v.link_edges}
  idx=len(notes);n={'component':idx,'vertices':len(part),'faces':len(faces)}
  if len(part)<4 or not faces or any(not e.is_manifold for e in edges):
   n.update(status='skipped',reason='open/nonmanifold/degenerate component');notes.append(n);continue
  vol=abs(sum(f.verts[0].co.dot(f.verts[i].co.cross(f.verts[i+1].co))/6 for f in faces for i in range(1,len(f.verts)-1)))
  hull=bmesh.new()
  for v in part:hull.verts.new(v.co)
  try:
   result=bmesh.ops.convex_hull(hull,input=list(hull.verts),use_existing_faces=False)
   unused=[g for g in result.get('geom_unused',[])+result.get('geom_interior',[]) if isinstance(g,bmesh.types.BMVert) and g.is_valid]
   if unused:bmesh.ops.delete(hull,geom=list(set(unused)),context='VERTS')
   bmesh.ops.recalc_face_normals(hull,faces=list(hull.faces))
   hv=abs(hull.calc_volume());ratio=hv/vol if vol>1e-8 else float('inf')
   n.update(source_volume_cm3=vol,hull_volume_cm3=hv,hull_volume_ratio=ratio if math.isfinite(ratio) else None)
   if vol<=1e-8 or ratio>1.02 or ratio<.98:
    n.update(status='skipped',reason='concave or invalid solid; convex hull would fill intentional space')
   else:
    hme=bpy.data.meshes.new('UCX_geometry');hull.to_mesh(hme)
    ob=bpy.data.objects.new('UCX_'+name+'_'+str(len(parts)).zfill(3),hme);scene.collection.objects.link(ob);parts.append(ob)
    n.update(status='exported',collision_object=ob.name)
  except Exception as e:n.update(status='skipped',reason=str(e))
  finally:hull.free()
  notes.append(n)
 bm.free();return parts,notes
# Explicit approved small-prop exceptions. Dimensions are centimetres after all scaling.
# Large/traversable geometry is never permitted through this branch.
SMALL_PROXY_LIMITS={'TicketRoll':(25.,25.,25.),'CoiledAirHose':(125.,125.,15.),'PaintCan_Open':(50.,50.,50.),'PaintCan_Closed':(50.,50.,50.),'OpenMaintenanceBucket':(65.,65.,65.)}
proxy_reports=[]
def bounds_of(points):
 return {'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
def family_collision(me,name,family):
 parts,notes=collision_parts(me,name)
 if family not in SMALL_PROXY_LIMITS:return parts,notes,None
 points=[v.co.copy() for v in me.vertices];bounds=bounds_of(points)
 dims=[bounds['max'][i]-bounds['min'][i] for i in range(3)]
 limits=SMALL_PROXY_LIMITS[family]
 if any(dims[i]>limits[i]+1e-4 for i in range(3)):
  raise RuntimeError('Approved small-prop proxy exceeds dimension guard: '+name+' '+str(dims))
 oldpoints=[v.co for ob in parts for v in ob.data.vertices];oldbounds=bounds_of(oldpoints)
 baseline=len(parts)
 # Double-precision QHull avoids nonplanar face merging in Blender's hull solver.
 from scipy.spatial import ConvexHull
 import numpy as np
 xyz=np.asarray([tuple(v) for v in points],dtype=np.float64);ch=ConvexHull(xyz)
 hull=bmesh.new();mapping={int(i):hull.verts.new(xyz[i]) for i in ch.vertices}
 for tri,equation in zip(ch.simplices,ch.equations):
  ids=[int(i) for i in tri];a,b,c=[xyz[i] for i in ids]
  if np.dot(np.cross(b-a,c-a),equation[:3])<0:ids.reverse()
  hull.faces.new([mapping[i] for i in ids])
 bmesh.ops.recalc_face_normals(hull,faces=list(hull.faces));hull.normal_update()
 hb=bounds_of([v.co for v in hull.verts]);be=max(abs(hb[k][i]-bounds[k][i]) for k in ('min','max') for i in range(3))
 violation=max((v-f.verts[0].co).dot(f.normal) for v in points for f in hull.faces)
 convex_violation=max((v.co-f.verts[0].co).dot(f.normal) for v in hull.verts for f in hull.faces)
 volume=abs(hull.calc_volume());closed=all(e.is_manifold for e in hull.edges)
 if be>.001 or violation>.02 or convex_violation>.02 or volume<=1e-8 or not closed or len(hull.verts)>255:
  raise RuntimeError('Small-prop proxy geometric validation failed: '+name+' '+str({'bounds_error':be,'containment_error':violation,'convexity_error':convex_violation,'volume':volume,'closed':closed}))
 for ob in parts:bpy.data.objects.remove(ob,do_unlink=True)
 hme=bpy.data.meshes.new('UCX_small_prop_proxy');hull.to_mesh(hme)
 ob=bpy.data.objects.new('UCX_'+name+'_000',hme);scene.collection.objects.link(ob)
 r={'asset':name,'family':family,'mode':'approved_small_prop_outer_convex_proxy','dimensions_cm':dims,'dimension_limits_cm':limits,'source_render_bounds_cm':bounds,'previous_collision_bounds_cm':oldbounds,'proxy_bounds_cm':hb,'previous_hulls':baseline,'proxy_hulls':1,'proxy_vertices':len(hull.verts),'proxy_faces':len(hull.faces),'proxy_volume_cm3':volume,'hull_plane_tolerance_cm':.02,'max_bounds_error_cm':be,'max_render_vertex_outside_proxy_cm':max(0.,violation),'max_convexity_violation_cm':max(0.,convex_violation),'closed_manifold':closed,'within_asset_hull_overlap_pairs':0,'intentional_filled_space':'Tiny roll winding/core, can/bucket mouth and handle gaps; shallow coiled hose centre. Not suitable for player hiding or traversal.','passed':True}
 hull.free();proxy_reports.append(r)
 for n in notes:
  if n['status']=='exported':n['status']='replaced_by_approved_small_proxy'
 notes.append({'component':'small_prop_proxy','status':'exported','collision_object':ob.name,'policy_exception':r['mode']})
 return [ob],notes,r

def make_refined_collision(recipe,name,linear):
 parts=[];notes=[]
 for index,hull in enumerate(recipe['hulls']):
  vertices=[linear@Vector(v) for v in hull['vertices_local_m']]
  faces=[tuple(reversed(f)) if linear.determinant()<0 else tuple(f) for f in hull['faces']]
  me=bpy.data.meshes.new('UCX_refined_recipe');me.from_pydata(vertices,[],faces);me.update()
  obj=bpy.data.objects.new('UCX_'+name+'_'+str(index).zfill(3),me);scene.collection.objects.link(obj);parts.append(obj)
  notes.append({'status':'exported','component':hull['part'],'collision_object':obj.name,'recipe_version':recipe_bundle['recipe_version'],'source_face_ranges':hull.get('source_face_ranges',[]),'vertices':len(vertices)})
 return parts,notes

for source in sorted(props,key=lambda o:o.name):
 ev=source.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
 linear=C@source.matrix_world.to_3x3()
 exact_normals=transform_mesh_preserving_corner_normals(me,linear)
 render_digest=key(me,exact_normals)
 recipe=recipes.get(source.name)
 recipe_digest=hashlib.sha256(json.dumps(recipe['hulls'],sort_keys=True).encode()).hexdigest() if recipe else None
 digest=hashlib.sha256((render_digest+(recipe_digest or '')).encode()).hexdigest()
 if digest not in assets:
  family=re.sub('[^A-Za-z0-9_]+','_',str(source.get('asset_family','TicketBin')))
  name='SM_'+family+'_'+digest[:10]
  me.name=name
  obj=bpy.data.objects.new(name,me);scene.collection.objects.link(obj)
  obj['PropActorTag']=True;obj['asset_family']=str(source.get('asset_family','TicketBin'));obj['source_object']=source.name
  for m in me.materials:
   if m and m.name not in material_report:
    nodes=m.node_tree.nodes if m.use_nodes else []
    p=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    material_report[m.name]={'base_color':list(p.inputs['Base Color'].default_value) if p else list(m.diffuse_color),'roughness':float(p.inputs['Roughness'].default_value) if p else m.roughness,'metallic':float(p.inputs['Metallic'].default_value) if p else m.metallic,'images':[{'node':n.name,'image':n.image.name,'path':os.path.relpath(bpy.path.abspath(n.image.filepath),ROOT)} for n in nodes if n.type=='TEX_IMAGE' and n.image]}
  if recipe:
   parts,notes=make_refined_collision(recipe,name,linear);proxy=None
  else:parts,notes,proxy=family_collision(me,name,str(source.get('asset_family','TicketBin')))
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
  for p in parts:p.select_set(True)
  bpy.context.view_layer.objects.active=obj
  path=OUT+'/'+name+'.fbx'
  bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH'},global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_mesh_modifiers=False,mesh_smooth_type='FACE',use_custom_props=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
  replace_corner_normals(path,name,exact_normals,force_smooth=True)
  entry={'asset_name':name,'fbx':'props/'+name+'.fbx','geometry_material_uv_sha256':render_digest,'collision_recipe_sha256':recipe_digest,'asset_signature_sha256':digest,'normal_payload':'Exact numeric source corner normals; packed-normal bypass','fbx_sha256':sha(path),'source_exemplar':source.name,'family':str(source.get('asset_family','TicketBin')),'vertices':len(me.vertices),'polygons':len(me.polygons),'materials':[m.name if m else None for m in me.materials],'collision_hulls':len(parts),'collision_mode':'refined_structural_recipe' if recipe else ('approved_small_prop_outer_convex_proxy' if proxy else 'component_convex_preserve_openings'),'previous_collision_hulls':proxy['previous_hulls'] if proxy else len(parts),'collision_skipped_components':sum(n['status']=='skipped' for n in notes),'bounds_cm':{'min':[min(v.co[i] for v in me.vertices) for i in range(3)],'max':[max(v.co[i] for v in me.vertices) for i in range(3)]}}
  assets[digest]=entry;reports.append({'asset':name,'components':notes})
  for ob in parts+[obj]:bpy.data.objects.remove(ob,do_unlink=True)
 else:bpy.data.meshes.remove(me)
 entry=assets[digest];position=C@source.matrix_world.translation
 placements.append({'source_object':source.name,'asset_name':entry['asset_name'],'actor_class':'StaticMeshActor','actor_tags':['PropActor'],'location_cm':list(position),'rotation_deg_pitch_yaw_roll':[0.,0.,0.],'scale':[1.,1.,1.],'source_world_matrix_blender_m':[list(r) for r in source.matrix_world],'collision_profile':'Custom','visibility_response':'Block','collision_enabled':'QueryAndPhysics','simulate_physics':False})
manifest={'schema_version':2,'export_revision':'V2 Cycle10 isolated','source_blend':os.path.relpath(SOURCE,PROJECT),'source_blend_sha256':source_hash,'coordinate_system':'UE centimetres, (x,y,z)=(100*BlenderX,-100*BlenderY,100*BlenderZ). Source linear transforms baked into mesh; placement is translation only. Disable FBX Convert Scene and Convert Scene Unit.','canonicalization':'Conservative geometry+topology+materials+UV+corner-normals+smooth-face SHA256; coordinate tolerance 0.0001 cm and UV 0.000001. Rotated geometry may remain distinct assets, intentionally.','assets':list(assets.values()),'placements':placements,'material_reference':material_report,'verified_staged_textures':texture_verification,'unreal_runtime_verified':False}
open(ROOT+'/unreal/prop_placements.json','w').write(json.dumps(manifest,indent=2))
report={'source_blend':os.path.relpath(SOURCE,PROJECT),'source_untouched':sha(SOURCE)==source_hash,'source_blend_sha256':source_hash,'eligible_placed_props':len(props),'canonical_assets':len(assets),'excluded_tagged_objects':excluded,'excluded_tagged_object_details':excluded_details,'collision_hulls':sum(a['collision_hulls'] for a in assets.values()),'collision_skipped_components':sum(a['collision_skipped_components'] for a in assets.values()),'assets_without_collision':[a['asset_name'] for a in assets.values() if not a['collision_hulls']],'collision_policy':'Cycle10 nineteen refined actors use reviewed 160-hull recipe budget. Other closed component hulls preserve useful openings. Explicit size-guarded outer convex exceptions only for TicketRoll, CoiledAirHose, PaintCan_Open, PaintCan_Closed, OpenMaintenanceBucket; no auto collision.','collision_detail':reports,'unreal_runtime_verified':False}
open(ROOT+'/qa/prop_export_report.json','w').write(json.dumps(report,indent=2));print('PROP_EXPORT_DONE',json.dumps({k:v for k,v in report.items() if k!='collision_detail'}))

# Broadphase neighbor-overlap audit: compare modified actor collision bounds against
# the previous component-collision bounds; report new candidate overlaps explicitly.
byasset={a['asset_name']:a for a in assets.values()};pr={r['asset']:r for r in proxy_reports}
def world_bounds(p,old=False):
 a=byasset[p['asset_name']];r=pr.get(p['asset_name'])
 b=(r['previous_collision_bounds_cm'] if old else r['proxy_bounds_cm']) if r else a['bounds_cm']
 return {k:[b[k][i]+p['location_cm'][i] for i in range(3)] for k in ('min','max')}
def overlaps(a,b):return all(min(a['max'][i],b['max'][i])-max(a['min'][i],b['min'][i])>1e-4 for i in range(3))
oldpairs=[];newpairs=[]
for i,p in enumerate(placements):
 for q in placements[i+1:]:
  if p['asset_name'] not in pr and q['asset_name'] not in pr:continue
  pair=[p['source_object'],q['source_object']]
  if overlaps(world_bounds(p,True),world_bounds(q,True)):oldpairs.append(pair)
  if overlaps(world_bounds(p),world_bounds(q)):newpairs.append(pair)
introduced=[p for p in newpairs if p not in oldpairs]
modified={'source_blend_sha256':source_hash,'all_passed':all(r['passed'] for r in proxy_reports) and not introduced,'modified_canonical_assets':len(proxy_reports),'modified_placed_actors':sum(p['asset_name'] in pr for p in placements),'previous_canonical_hulls':sum(a['previous_collision_hulls'] for a in assets.values()),'canonical_hulls':sum(a['collision_hulls'] for a in assets.values()),'placed_actor_hulls':sum(byasset[p['asset_name']]['collision_hulls'] for p in placements),'previous_placed_actor_hulls':sum(byasset[p['asset_name']]['previous_collision_hulls'] for p in placements),'new_broadphase_neighbor_overlap_pairs':introduced,'previous_broadphase_neighbor_overlap_pairs':oldpairs,'current_broadphase_neighbor_overlap_pairs':newpairs,'overlap_scope':'Positive-volume axis-aligned actor-bound overlap candidates, not narrowphase contacts. No new outside-bounds expansion. Internal cavity filling is deliberate only for listed small props; in-engine capsule and trace validation remains required.','assets':proxy_reports,'unreal_runtime_verified':False}
if prior_manifest and prior_manifest.get('source_blend_sha256')==source_hash:
 modified['visual_assets_unchanged']={a['asset_name']:a['geometry_material_uv_sha256'] for a in prior_manifest['assets']}=={a['asset_name']:a['geometry_material_uv_sha256'] for a in assets.values()}
 modified['placements_unchanged']=prior_manifest['placements']==placements
 modified['source_unchanged']=sha(SOURCE)==source_hash
 modified['all_passed']=modified['all_passed'] and modified['visual_assets_unchanged'] and modified['placements_unchanged'] and modified['source_unchanged']
open(ROOT+'/qa/prop_collision_optimization.json','w').write(json.dumps(modified,indent=2));print('PROXY_OPTIMIZATION',modified['all_passed'],modified['previous_canonical_hulls'],modified['canonical_hulls'])

refined_placed=[p for p in placements if p['source_object'] in recipes]
refined_report={'source_blend_sha256':source_hash,'all_passed':len(refined_placed)==19 and sum(byasset[p['asset_name']]['collision_hulls'] for p in refined_placed)==160,'recipe_version':recipe_bundle['recipe_version'],'placed_actors':len(refined_placed),'placed_hulls':sum(byasset[p['asset_name']]['collision_hulls'] for p in refined_placed),'actors':[{'source_object':p['source_object'],'asset_name':p['asset_name'],'hull_count':byasset[p['asset_name']]['collision_hulls'],'qa':recipes[p['source_object']]['qa']} for p in refined_placed],'source_untouched':sha(SOURCE)==source_hash,'unreal_runtime_verified':False}
open(ROOT+'/qa/prop_refined_collision.json','w').write(json.dumps(refined_report,indent=2))
for name in ['import_props','import_carnival']:
 template=Path(__file__).resolve().parent/(name+'_v2_template.py')
 (Path(ROOT)/'unreal'/(name+'.py')).write_text(template.read_text())
if sha(SOURCE)!=source_hash:raise RuntimeError('Source hash changed during prop export')
