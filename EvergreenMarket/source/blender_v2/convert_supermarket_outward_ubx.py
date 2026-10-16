"""Create a NEW logical-mesh scene and Unreal handoff. Never saves the input file.
blender -b ORIGINAL.blend --python source/convert_supermarket.py
Requires adjacent logical_groups.py. Blender 4.3 tested.
"""
import bpy, math, json, hashlib, re, sys, shutil, time
from pathlib import Path
from mathutils import Vector, Matrix
from collections import Counter, defaultdict
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
import logical_groups
SOURCE=Path(bpy.data.filepath).resolve()
assert SOURCE != (ROOT/'Evergreen_Market_Unreal_Ready.blend').resolve()
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
scene=bpy.context.scene
objects=sorted([o for o in scene.objects if o.type in {'MESH','CURVE','FONT'}],key=lambda o:o.name)
dg=bpy.context.evaluated_depsgraph_get()
centers={o.name:sum((o.matrix_world@Vector(c) for c in o.bound_box),Vector())/8 for o in objects}
print('GROUPING',len(objects),flush=True)
groups=logical_groups.build_groups(objects,centers)
if isinstance(groups,tuple):groups=groups[0]
errors=getattr(logical_groups,'ERRORS',[])
if errors:raise RuntimeError('Group validation errors: '+str(errors))
used=set()
for g in groups:
 for o in g['members']:
  assert o.name not in used, 'Duplicate membership '+o.name
  used.add(o.name)
print('COMPOSITES',len(groups),'members',len(used),flush=True)
# Exact exported material slot IDs, consistent across FBX, JSON and Blender.
material_records=[]; mat_ids={}
for m in sorted(bpy.data.materials,key=lambda m:m.name):
 old=m.name; mid='M_EG_'+re.sub('[^A-Za-z0-9]+','_',old).strip('_');mat_ids[old]=mid;m.name=mid
 bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.use_nodes else None
 rec={'material_id':mid,'source_name':old,'base_color_rgba':list(bs.inputs['Base Color'].default_value) if bs else list(m.diffuse_color),'roughness':float(bs.inputs['Roughness'].default_value) if bs else .5,'metallic':float(bs.inputs['Metallic'].default_value) if bs else 0.,'two_sided':False,'alpha_mode':'OPAQUE'}
 if bs:
  rec['emissive_rgb']=[float(c)*float(bs.inputs['Emission Strength'].default_value) for c in bs.inputs['Emission Color'].default_value[:3]]
  rec['transmission']=float(bs.inputs['Transmission Weight'].default_value)
  if rec['transmission']>.1:rec.update(alpha_mode='BLEND',opacity=.16,two_sided=True)
  imgs=[n.image for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
  if imgs:
   im=imgs[0];name=Path(im.filepath).name;dest=ROOT/'textures'/name
   im.filepath_raw=str(dest);im.file_format='PNG';im.save();rec['base_color_texture']='textures/'+name
  rec['procedural_approximation']=any(n.type in {'TEX_NOISE','BUMP','VALTORGB'} for n in m.node_tree.nodes)
 material_records.append(rec)
(ROOT/'materials.json').write_text(json.dumps({'schema_version':1,'materials':material_records,'note':'Uniform PBR and original packaging textures. Blender procedural noise/bump are approximated, not baked. Original nodes remain in the .blend.'},indent=2))
# Cache source evaluated mesh data. Curves with identical text geometry share conversion.
cache={}; eval_counts=Counter()
def geometry(o):
 if o.type=='FONT':
  d=o.data;k=('FONT',d.body,round(d.size,6),d.align_x,d.align_y,round(d.extrude,6),round(d.bevel_depth,6),tuple(m.name for m in d.materials))
 else:k=(o.type,o.data.as_pointer())
 if k in cache:return cache[k]
 eo=None
 if o.type=='MESH' and not o.modifiers:me=o.data
 else:eo=o.evaluated_get(dg);me=eo.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
 me.calc_loop_triangles()
 verts=[tuple(v.co) for v in me.vertices];tris=[];uv=[];norm=[];mats=[mat_ids.get(m.name,m.name) for m in me.materials]
 u=me.uv_layers.active
 for t in me.loop_triangles:
  tris.append((tuple(t.vertices),int(t.material_index),me.polygons[t.polygon_index].use_smooth))
  for li in t.loops:
   uv.append(tuple(u.data[li].uv) if u else (0.,0.));norm.append(tuple(me.corner_normals[li].vector))
 result=(verts,tris,uv,norm,mats);cache[k]=result;eval_counts[o.type]+=1
 if eo:eo.to_mesh_clear()
 return result
# Snapshot before adding logical objects, avoiding dependency-graph invalidation per part.
for i,o in enumerate(objects):
 geometry(o)
 if i%1500==0:print('SNAPSHOT',i,'/',len(objects),'cache',len(cache),flush=True)
# Single objects retain original linked data, local rotation and scale.
for o in objects:
 if o.name in used:continue
 if o.data.name.startswith('SKU_'):
  family=o.data.name;tier='conditional_small';category='disguise_candidate'
 elif o.name.startswith('PROP bread roll') or o.name.startswith('Bread roll'):
  family='Bread_Roll';tier='conditional_tiny';category='disguise_candidate'
 else:family=re.sub(r'\.\d+$','',o.name);tier='fixed';category='scenery'
 groups.append({'family':family,'tier':tier,'category':category,'members':[o],'single':True})
logical_collection=bpy.data.collections.new('UNREAL_Logical_Instances');scene.collection.children.link(logical_collection)
collections={};assets={};placements=[];mesh_for={};asset_hash={};family_shapes=defaultdict(list);source_coverage=[];max_reconstruction_error=0
FIXED_BLOCKING=('wall','floor','slab','walkway','kerb','gondola','shelf','rack upright','chilled','freezer','checkout','counter','table','locker','door','plinth','island timber','canopy','roof panel','paving','threshold')

def safe(s):return re.sub('[^A-Za-z0-9]+','_',s).strip('_')[:48]
def serialize_matrix(m):return [[round(float(v),9) for v in row] for row in m]
def make_asset(g):
 global max_reconstruction_error
 members=g['members'];single=g.get('single',False)
 if single:base=members[0].matrix_world.copy(); inv=base.inverted()
 else:
  base=Matrix.Translation(Vector(g['anchor']))@Matrix.Rotation(float(g.get('rotation_z',0)),4,'Z');inv=base.inverted()
 allv=[];allf=[];alluv=[];allnorm=[];mnames=[];matmap={};count=0
 for o in sorted(members,key=lambda o:(re.sub(r'\.\d+$','',o.name),tuple(round(v,4) for v in (inv@centers[o.name])))):
  v,tri,uv,norm,ms=geometry(o);tr=inv@o.matrix_world;nm=tr.to_3x3().inverted().transposed();offset=len(allv)
  allv.extend(tr@Vector(p) for p in v)
  for name in ms:
   if name not in matmap:matmap[name]=len(mnames);mnames.append(name)
  allf.extend((tuple(offset+i for i in t),matmap[ms[mi]],smooth) for t,mi,smooth in tri)
  alluv.extend(uv);allnorm.extend(tuple((nm@Vector(n)).normalized()) for n in norm)
  count+=len(v)
 assert allv and allf, g['family']
 used_slots=sorted(set(mi for _,mi,_ in allf));slot_remap={old:new for new,old in enumerate(used_slots)}
 mnames=[mnames[i] for i in used_slots];allf=[(t,slot_remap[mi],sm) for t,mi,sm in allf]
 lo=Vector(tuple(min(v[i] for v in allv) for i in range(3)));hi=Vector(tuple(max(v[i] for v in allv) for i in range(3)))
 pivot=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));base=base@Matrix.Translation(pivot)
 # Round to 0.01 mm to deduplicate harmless float32 world-position noise.
 vv=[tuple(round(float(v[i]-pivot[i]),5) for i in range(3)) for v in allv]
 uvround=[tuple(round(float(q),6) for q in u) for u in alluv]
 fingerprint=hashlib.sha256(json.dumps([[tuple(round(v,4) for v in p) for p in vv],allf,uvround,mnames],separators=(',',':')).encode()).hexdigest()
 aid='SM_EG_'+safe(g['family'])+'_'+fingerprint[:10]
 shape_key=(g['family'],len(vv),len(allf),tuple(mnames));structure=hashlib.sha256(json.dumps([allf,uvround],separators=(',',':')).encode()).hexdigest()
 match=next((other for other,coords,st in family_shapes[shape_key] if st==structure and max(abs(a-b) for v,w in zip(vv,coords) for a,b in zip(v,w))<.0001),None)
 if fingerprint in asset_hash:aid=asset_hash[fingerprint]
 elif match:aid=match
 else:
  mesh=bpy.data.meshes.new(aid);mesh.from_pydata(vv,[],[t for t,mi,sm in allf]);mesh.update()
  for name in mnames:mesh.materials.append(bpy.data.materials[name])
  uv=mesh.uv_layers.new(name='UV0')
  uv.data.foreach_set('uv',[v for pair in uvround for v in pair])
  for p,(_,mi,sm) in zip(mesh.polygons,allf):p.material_index=mi;p.use_smooth=sm
  mesh.normals_split_custom_set(allnorm)
  category=g.get('category','scenery' if g['tier'].startswith('fixed') else 'disguise_candidate')
  blocking=category=='disguise_candidate' or any(w in g['family'].lower() for w in FIXED_BLOCKING)
  rec={'asset_id':aid,'name':g['family'],'fbx_path':'assets/'+aid+'.fbx','category':category,'disguise_tier':g['tier'],'materials':mnames,'used_materials':mnames,'bounds_cm':[round(float(hi[i]-lo[i])*100,5) for i in range(3)],'default_pivot':'bottom_center','collision':{'strategy':'box' if blocking else 'none','note':'Conservative gameplay proxy; validate clearance and trace channels in Unreal.'},'vertices':len(vv),'triangles':len(allf),'source_component_count':len(members),'instance_count':0,'mesh_sha256':fingerprint}
  assets[aid]=rec;mesh_for[aid]=mesh;asset_hash[fingerprint]=aid;family_shapes[shape_key].append((aid,vv,structure))
 # Source geometry roundtrip including deduplication: use the actually shared mesh.
 vv=[tuple(v.co) for v in mesh_for[aid].vertices]
 err=max(((base@Vector(vv[i]))-(base@Vector(tuple(float(allv[i][j]-pivot[j]) for j in range(3))))).length for i in range(len(vv)))
 max_reconstruction_error=max(max_reconstruction_error,err)
 loc,quat,scale=base.decompose();e=quat.to_euler('XYZ');iid='EGI_'+hashlib.sha256('|'.join(sorted(o.name for o in members)).encode()).hexdigest()[:16]
 placement={'instance_id':iid,'asset_id':aid,'location_cm':[round(loc.x*100,6),round(-loc.y*100,6),round(loc.z*100,6)],'rotation_deg':[math.degrees(-e.y),math.degrees(-e.z),math.degrees(e.x)],'quaternion_xyzw':[-quat.x,quat.y,-quat.z,quat.w],'scale':list(scale),'source_names':[o.name for o in members],'source_collection':members[0].users_collection[0].name,'blender_matrix':serialize_matrix(base)}
 placements.append(placement);assets[aid]['instance_count']+=1
 cname=placement['source_collection']
 if cname not in collections:collections[cname]=bpy.data.collections.new(cname+'_Logical');logical_collection.children.link(collections[cname])
 ob=bpy.data.objects.new(iid+'__'+safe(g['family']),mesh_for[aid]);collections[cname].objects.link(ob);ob.matrix_world=base;ob['asset_id']=aid;ob['instance_id']=iid;ob['disguise_tier']=assets[aid]['disguise_tier']
 source_coverage.extend(placement['source_names'])
 return aid
# Cache exact single-object data results to avoid repeated heavy assembly, while retaining transforms.
single_cache={}
for index,g in enumerate(groups):
 if g.get('single'):
  o=g['members'][0];key=(o.data.as_pointer(),g['tier'])
  if key in single_cache:
   aid,shift=single_cache[key];base=o.matrix_world@shift;loc,q,scale=base.decompose();e=q.to_euler('XYZ');iid='EGI_'+hashlib.sha256(o.name.encode()).hexdigest()[:16]
   p={'instance_id':iid,'asset_id':aid,'location_cm':[round(loc.x*100,6),round(-loc.y*100,6),round(loc.z*100,6)],'rotation_deg':[math.degrees(-e.y),math.degrees(-e.z),math.degrees(e.x)],'quaternion_xyzw':[-q.x,q.y,-q.z,q.w],'scale':list(scale),'source_names':[o.name],'source_collection':o.users_collection[0].name,'blender_matrix':serialize_matrix(base)}
   placements.append(p);assets[aid]['instance_count']+=1;source_coverage.append(o.name);cname=p['source_collection']
   if cname not in collections:collections[cname]=bpy.data.collections.new(cname+'_Logical');logical_collection.children.link(collections[cname])
   ob=bpy.data.objects.new(iid+'__'+safe(g['family']),mesh_for[aid]);collections[cname].objects.link(ob);ob.matrix_world=base;ob['asset_id']=aid;ob['instance_id']=iid;ob['disguise_tier']=assets[aid]['disguise_tier']
   continue
  aid=make_asset(g);base=Matrix(placements[-1]['blender_matrix']);single_cache[key]=(aid,o.matrix_world.inverted()@base)
 else:make_asset(g)
 if index%100==0:print('ASSEMBLY',index,'/',len(groups),'assets',len(assets),flush=True)
assert len(source_coverage)==len(objects)==len(set(source_coverage))
assert set(source_coverage)=={o.name for o in objects}
assert len(placements)==len({p['instance_id'] for p in placements})
# Keep original cameras/lights and authoring materials in the new Blender copy; remove source renderable components.
for o in objects:bpy.data.objects.remove(o,do_unlink=True)
for c in list(bpy.data.collections):
 if not c.objects and not c.children and c!=logical_collection:bpy.data.collections.remove(c)
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.shading.type='SOLID'
scene['Unreal handoff']='Logical shared meshes; full geometry placements. Read START_HERE.txt. UE import has not been executed in this environment.'
scene['Source SHA256']=source_hash
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Evergreen_Market_Unreal_Ready.blend'),compress=True)
print('NEW BLEND SAVED',len(assets),len(placements),flush=True)
# Export each asset once from isolated scene, so no placement transforms leak into FBX.
exportscene=bpy.data.scenes.new('FBX_Export_Workspace');exportscene.unit_settings.system='METRIC';exportscene.unit_settings.scale_length=1;bpy.context.window.scene=exportscene
for i,(aid,rec) in enumerate(sorted(assets.items())):
 for o in list(exportscene.objects):bpy.data.objects.remove(o,do_unlink=True)
 ob=bpy.data.objects.new(aid,mesh_for[aid]);exportscene.collection.objects.link(ob);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if rec['collision']['strategy']=='box':
  mesh=mesh_for[aid];mins=[min(v.co[j] for v in mesh.vertices) for j in range(3)];maxs=[max(v.co[j] for v in mesh.vertices) for j in range(3)]
  verts=[(x,y,z) for x in (mins[0],maxs[0]) for y in (mins[1],maxs[1]) for z in (mins[2],maxs[2])]
  faces=[(2,6,4,0),(5,7,3,1),(4,5,1,0),(3,7,6,2),(1,3,2,0),(6,7,5,4)]
  cm=bpy.data.meshes.new('Collision');cm.from_pydata(verts,[],faces);co=bpy.data.objects.new('UBX_'+aid+'_00',cm);exportscene.collection.objects.link(co);co.select_set(True)
 bpy.ops.export_scene.fbx(filepath=str(ROOT/rec['fbx_path']),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='Y',axis_up='Z',use_space_transform=True,bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False,use_custom_props=False)
 rec['file_sha256']=hashlib.sha256((ROOT/rec['fbx_path']).read_bytes()).hexdigest()
 if i%50==0:print('EXPORTED',i,'/',len(assets),flush=True)
manifest={'schema_version':1,'title':'Evergreen Market Unreal logical-mesh handoff','source_blend_sha256':source_hash,'coordinate_system':'UE_X_FORWARD_Y_RIGHT_Z_UP_CM','rotation_order':'pitch_yaw_roll','coordinate_note':'Blender metres [x,y,z] -> Unreal centimetres [100x,-100y,100z]. Quaternion preferred. Epic Send2UE-style FBX settings; verify axis probe in target Unreal version.','fbx_import':{'convert_scene':False,'convert_scene_unit':False,'force_front_x_axis':False,'import_uniform_scale':1.0,'transform_vertex_to_absolute':True},'assets':list(assets.values()),'placements':placements,'materials_file':'materials.json','original_renderable_components':len(objects),'logical_placements':len(placements),'lighting':'Original Blender lights are retained in blend only. Re-light in Unreal; no unsupported watts-to-lumens assumption.','unreal_tested':False}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
qa={'source_sha256_before':source_hash,'source_sha256_after':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_unchanged':source_hash==hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_components':len(objects),'covered_source_components':len(source_coverage),'duplicate_source_memberships':len(source_coverage)-len(set(source_coverage)),'logical_placements':len(placements),'unique_assets':len(assets),'material_count':len(material_records),'max_geometry_quantization_error_metres':max_reconstruction_error,'evaluated_geometry_cache_counts':dict(eval_counts),'family_counts':dict(Counter(g['family'] for g in groups)),'unreal_runtime_tested':False}
(ROOT/'qa/conversion_report.json').write_text(json.dumps(qa,indent=2))
print('CONVERSION COMPLETE',json.dumps({k:v for k,v in qa.items() if k!='family_counts'}),flush=True)
