"""Export original Moonfall scenery; never writes the source .blend.
Run: blender -b blender/Moonfall_Carnival.blend -t 2 --python source/export_environment.py
Original geometry plus ambientCG CC0 scanned/derived surfaces; see provenance ledger.
UCX is per primitive, never a convex zone/building.
"""
import bpy, json, math, os, hashlib, sys
from collections import defaultdict, Counter
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'unreal/environment';OUT.mkdir(parents=True,exist_ok=True)
QA=ROOT/'qa';QA.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'source'))
from fbx_exact_normals import replace_corner_normals
TILE=12.0
source_path=Path(bpy.data.filepath)
source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
source_scene=bpy.context.scene
source_scene.render.threads_mode='FIXED';source_scene.render.threads=2
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
sources=[o for o in source_scene.objects if o.type in {'MESH','CURVE','FONT','SURFACE'} and not o.get('PropActorTag') and not o.get('_assembly_source') and not o.get('render_only') and not o.get('visual_replaced') and not o.hide_render and not o.hide_get()]
excluded=Counter()
for o in source_scene.objects:
 if o.get('PropActorTag'):excluded['PropActorTag']+=1
 elif o.get('_assembly_source'):excluded['assembly_source']+=1
 elif o.get('render_only'):excluded['render_only']+=1
 elif o.get('visual_replaced'):excluded['visual_replaced']+=1
 elif o.hide_render or o.hide_get():excluded['hidden']+=1
 elif o.type not in {'MESH','CURVE','FONT','SURFACE'}:excluded[o.type]+=1
# Group by actual world-space bounds centre (some authored meshes have origin 0).
groups=defaultdict(list)
for o in sources:
 points=[o.matrix_world@Vector(p) for p in o.bound_box]
 centre=sum(points,Vector())/8
 key=(math.floor(centre.x/TILE),math.floor(centre.y/TILE))
 groups[key].append(o)
scene=bpy.data.scenes.new('EXPORT_TEMP_ENVIRONMENT')
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
report={'source_blend':'blender/'+source_path.name,'source_sha256':source_hash,'provenance':'Original procedural geometry with ambientCG CC0 Wood092, Asphalt033, Ground112 and Metal063 scanned surfaces, and derived weathering. See docs/ASSET_PROVENANCE.md and source/realistic_asset_sources.json. Typeface: bundled DejaVu license.', 'runtime_verified':False,'source_objects':len(sources),'excluded':dict(excluded),'tile_size_m':TILE,'assets':[], 'collision_skipped':[], 'uv_generated':[], 'coordinate_convention':{'source':'Blender X/Y/Z metres','fbx':'Preconverted UE centimetre vertices (100x,-100y,100z), reversed winding; axis_forward=Y, axis_up=Z, use_space_transform=False; scene scale_length=.01; global_scale=1; FBX_SCALE_UNITS','ue_placement':'X=source X*100, Y=-source Y*100, Z=source Z*100; zero actor rotation; unit scale','import':'Import Uniform Scale 1; Convert Scene disabled; Convert Scene Unit disabled; Force Front XAxis disabled. Confirm axis/scale in target Unreal version before playtesting.'}}

def collision_kind(o):
 if o.type!='MESH':return None,'non-mesh lettering/curve'
 low=o.name.lower()
 if any(w in low for w in ['foliage','canopy','grass','leaf','leaves','litter','bulb','filament','socket','neon','wire','cable','molding','trim','screw','rivet','bolt','festoon']):return None,'nonblocking decoration'
 d=sorted(o.dimensions)
 if d[0]<.045 or d[1]<.10:return None,'thin decoration'
 me=o.data;n=len(me.vertices);p=list(me.polygons)
 # Reject nonmanifold or concave impostors before recognizing primitive topology.
 edges=Counter()
 for face in p:
  for a,b in face.edge_keys:edges[tuple(sorted((a,b)))]+=1
 if any(count!=2 for count in edges.values()):return None,'nonmanifold primitive candidate'
 for face in p:
  normal=face.normal;anchor=me.vertices[face.vertices[0]].co
  signed=[normal.dot(v.co-anchor) for v in me.vertices]
  if min(signed)<-1e-5 and max(signed)>1e-5:return None,'nonconvex source; preserve openings'
 if n==8 and len(p)==6 and all(len(f.vertices)==4 for f in p):return 'box',''
 if n>=12 and n%2==0 and len(p)==n//2+2:
  caps=[f for f in p if len(f.vertices)==n//2]
  if len(caps)==2 and all(len(f.vertices)==4 or len(f.vertices)==n//2 for f in p):return 'cylinder',''
 return None,'not an original simple box/capped cylinder; omitted to preserve openings'

def mesh_object(name,vs,fs,mats=None,mi=None,uvs=None,smooth=None,normals=None):
 # Reflection into UE-handed coordinates requires reversed face and UV winding.
 vs=[(100*v[0],-100*v[1],100*v[2]) for v in vs]
 fs=[tuple(reversed(f)) for f in fs]
 if uvs is not None:uvs=[list(reversed(u)) for u in uvs]
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
 for m in mats or []:me.materials.append(m)
 if uvs is not None:
  uv=me.uv_layers.new(name='UVMap')
  for p,mat,coords,sm in zip(me.polygons,mi,uvs,smooth):
   p.material_index=mat;p.use_smooth=True if normals is not None else sm
   for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
 if normals is not None:
  # Each normal belongs to the corresponding face corner, not merely its vertex.
  converted=[(n[0],-n[1],n[2]) for face in normals for n in reversed(face)]
  me.normals_split_custom_set(converted)
  me.update()
 ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);return ob

for key,objects in sorted(groups.items()):
 bpy.context.window.scene=source_scene
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
 asset='SM_Env_Tile_%s_%s'%tuple(('p%d'%v if v>=0 else 'm%d'%-v) for v in key)
 origin=Vector((key[0]*TILE,key[1]*TILE,0))
 vs=[];fs=[];mats=[];mi=[];uvs=[];smooth=[];normals=[];collisions=[];source_names=[]
 for o in objects:
  source_names.append(o.name)
  ev=o.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
  if me is None:continue
  linear=o.matrix_world.to_3x3()
  if abs(linear.determinant())<1e-12:raise RuntimeError('Singular source transform: '+o.name)
  normal_matrix=linear.inverted().transposed();reverse_source=linear.determinant()<0
  corner_normals=[(normal_matrix@n.vector).normalized() for n in me.corner_normals]
  offset=len(vs);vs.extend(tuple(o.matrix_world@v.co-origin) for v in me.vertices)
  remap=[]
  for m in me.materials:
   if m not in mats:mats.append(m)
   remap.append(mats.index(m))
  uv=me.uv_layers.active
  if not uv:report['uv_generated'].append(o.name)
  for p in me.polygons:
   vertices=list(p.vertices);loops=list(p.loop_indices)
   if reverse_source:vertices.reverse();loops.reverse()
   normals.append([tuple(corner_normals[i]) for i in loops])
   fs.append(tuple(offset+i for i in vertices));mi.append(remap[p.material_index] if remap else 0);smooth.append(p.use_smooth)
   if uv:uvs.append([tuple(uv.data[i].uv) for i in loops])
   else:
    axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis]
    uvs.append([tuple(me.vertices[me.loops[li].vertex_index].co[a] for a in axes) for li in loops])
  ev.to_mesh_clear()
  kind,reason=collision_kind(o)
  if kind:
   collisions.append((o.name,kind,[tuple(o.matrix_world@v.co-origin) for v in o.data.vertices],[tuple(reversed(p.vertices)) if reverse_source else tuple(p.vertices) for p in o.data.polygons]))
  else:report['collision_skipped'].append({'source':o.name,'reason':reason,'asset':asset})
 bpy.context.window.scene=scene
 render=mesh_object(asset,vs,fs,mats,mi,uvs,smooth,normals)
 created=[render]
 for idx,(name,kind,cvs,cfs) in enumerate(collisions):created.append(mesh_object('UCX_%s_%03d'%(asset,idx),cvs,cfs))
 for o in created:o.select_set(True)
 bpy.context.view_layer.objects.active=render
 fbx=OUT/(asset+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_mesh_modifiers=False,mesh_smooth_type='FACE',use_tspace=False,use_custom_props=False,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
 exact_normals=[(n[0],-n[1],n[2]) for face in normals for n in reversed(face)]
 replace_corner_normals(fbx,asset,exact_normals)
 report['assets'].append({'asset_name':asset,'fbx':'unreal/environment/'+fbx.name,'source_objects':source_names,'pivot_source_m':list(origin),'location_cm':[origin.x*100,-origin.y*100,origin.z*100],'rotation_degrees':[0,0,0],'scale':[1,1,1],'bounds_local_cm':[[min((100*v[0],-100*v[1],100*v[2])[i] for v in vs) for i in range(3)],[max((100*v[0],-100*v[1],100*v[2])[i] for v in vs) for i in range(3)]],'normal_payload':'Exact numeric source normals written directly to FBX; Blender packed-normal bypass','fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),'custom_split_normals':True,'normal_corner_count':sum(len(n) for n in normals),'vertices':len(vs),'polygons':len(fs),'triangles':sum(max(0,len(p)-2) for p in fs),'materials':[m.name if m else None for m in mats],'ucx_hulls':len(collisions),'collision_sources':[{'source':c[0],'kind':c[1]} for c in collisions],'fbx_bytes':fbx.stat().st_size})
 print('EXPORTED',asset,len(objects),'sources',len(collisions),'hulls',flush=True)
 for o in created:
  me=o.data;bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(me)
report['asset_count']=len(report['assets']);report['ucx_hull_count']=sum(a['ucx_hulls'] for a in report['assets'])
report['limitations']=['Unreal import and gameplay collision have not been runtime-tested.','UCX is separate original solid primitives only. Complex custom shapes, rings, swept curves, foliage and small decorative parts deliberately have no generated collision.','No automatic whole-tile or whole-building hulls: doorways, gaps, arches and funhouse routes are not bridged by generation.','Inspect collision and run character traversal in Unreal. Do not enable auto-generate collision over these compound tile meshes.','FBX carries material slots and image references; Blender shader graphs, emission and mirror response require Unreal materials.','Existing active UVs preserved; converted font/curve meshes without UVs receive explicit local dominant-axis UVs. Lightmap UV generation is an Unreal import task.']
import sys
sys.path.insert(0,str(ROOT/'source'))
from export_material_manifest import export_material_manifest
report['material_manifest']=export_material_manifest(ROOT,source_path,source_hash)
from export_scene_metadata import export_scene_metadata
report['scene_metadata']=export_scene_metadata(ROOT,source_path,source_hash,source_scene)
(QA/'environment_export.json').write_text(json.dumps(report,indent=2))
(ROOT/'unreal/environment_manifest.json').write_text(json.dumps({k:report[k] for k in ['source_blend','source_sha256','provenance','coordinate_convention','assets','limitations','material_manifest','scene_metadata']},indent=2))
print('COMPLETE',report['asset_count'],'assets',report['ucx_hull_count'],'hulls',flush=True)
