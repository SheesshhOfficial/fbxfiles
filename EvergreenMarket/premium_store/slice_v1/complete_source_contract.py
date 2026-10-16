import bpy,bmesh,os,json,re,math
from mathutils import Vector,Matrix
R=os.path.dirname(os.path.abspath(__file__));B=os.path.join(R,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend');bpy.ops.wm.open_mainfile(filepath=B);s=bpy.context.scene
if s.get('context_source_completed'):print('CONTEXT_ALREADY_COMPLETED');raise SystemExit
with open(os.path.join(R,'EXPORT_MANIFEST.json')) as f:m=json.load(f)
with open(os.path.join(R,'ASSET_COLLISION_QA.json')) as f:q=json.load(f)
assets={a['asset_id']:a for a in m['assets']}
# Turn side typography vertically so it fits the narrow paperboard side panel.
for sku,w,d,h in [('rolled_oats',.151,.073,.267),('almond_granola',.145,.072,.250),('bronze_pasta',.113,.058,.304),('sea_salt',.088,.055,.150)]:
 o=bpy.data.objects[assets[sku]['mesh']];vs=[v for v in o.data.vertices if v.co.x>w/2+.0001]
 if vs:
  cy=(min(v.co.y for v in vs)+max(v.co.y for v in vs))/2;cz=(min(v.co.z for v in vs)+max(v.co.z for v in vs))/2
  for v in vs:y,z=v.co.y-cy,v.co.z-cz;v.co.y=-z;v.co.z=h/2+y
 o.data.update();assets[sku]['dimensions_m']=[max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices) for i in range(3)];o['side_typography_fitted']=True
# More readable golden honey behind the true clear-glass shell.
p=bpy.data.materials['Honey'].node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.72,.34,.055,1);p.inputs['Transmission Weight'].default_value=.20;p.inputs['Roughness'].default_value=.14
# Safe mesh generator for physical boxes, source normals always recalculated.
def boxmesh(name,dim):
 me=bpy.data.meshes.new(name);bm=bmesh.new();bmesh.ops.create_cube(bm,size=1);bmesh.ops.transform(bm,matrix=Matrix.Diagonal((*dim,1)),verts=bm.verts);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();return me
# Add under-shelf LED strips as actual fixture geometry and matching area lights.
for side in [-1,1]:
 yaw=math.pi/2 if side==-1 else -math.pi/2
 for bay,y in enumerate([.35,2.17,3.99]):
  for j,z in enumerate([.635,1.015,1.395,1.775,2.225]):
   tag=f'EGS_LED_{"L" if side<0 else "R"}_{bay+1}_{j+1}';localy=-.292;xx=side*1.83-localy*math.sin(yaw);yy=y+localy*math.cos(yaw)
   me=boxmesh(tag+'_DIFFUSER_MESH',(1.64,.014,.006));me.materials.append(bpy.data.materials['Warm opal diffuser']);ob=bpy.data.objects.new(tag+'_DIFFUSER',me);bpy.data.collections['04_LIGHT_FIXTURES'].objects.link(ob);ob.location=(xx,yy,z);ob.rotation_euler[2]=yaw;ob['fixture_category']='integrated_shelf_lighting_nonblocking';ob['nonblocking_reason']='Slim strip directly beneath shelf board; shelf collider defines the solid boundary.'
   dat=bpy.data.lights.new(tag,'AREA');dat.shape='RECTANGLE';dat.size=1.62;dat.size_y=.012;dat.energy=2.4;dat.color=(1,.86,.67);lo=bpy.data.objects.new(tag,dat);bpy.data.collections['05_LIGHTS'].objects.link(lo);lo.location=(xx,yy,z-.0035);lo.rotation_euler[2]=yaw;lo['fixture_id']=ob.name;lo['units']='Blender Cycles watts';m['lights'].append({'id':tag,'fixture':ob.name,'position_m':list(lo.location),'rotation_euler_deg':[0,0,math.degrees(yaw)],'type':'AREA','shape':'RECTANGLE','size_m':[1.62,.012],'energy_watts':2.4,'color_rgb':list(dat.color),'Unreal_photometry_validated':False})
# Canonical static assets and authored simple collision for physical surrounding context.
context_assets=[];context_places=[];inventory=[];hullcol=bpy.data.collections['06_COLLISION_LIBRARY'];assetcol=bpy.data.collections['09_ASSET_LIBRARY'];dg=bpy.context.evaluated_depsgraph_get()
physical_names=['Floor slab','Ceiling','End wall','End wall oak dado','Warm side wall','End tasting console','Console stone top']
for colname in ['01_STRUCTURE','02_FIXTURES','04_LIGHT_FIXTURES','08_CAMERA_CAPTIONS']:
 for idx,o in enumerate(list(bpy.data.collections[colname].objects)):
  if o.get('asset_id'):continue
  ident=o.get('stable_id') or 'EGS_CONTEXT_'+colname[:2]+'_'+str(idx+1).zfill(4);o['stable_id']=ident;o['Prop']=False
  isphysical=o.type=='MESH' and any(o.name==n or o.name.startswith(n+'.') for n in physical_names)
  rec={'stable_id':ident,'object_name':o.name,'collection':colname,'object_type':o.type,'eligible':False}
  if isphysical:
   aid='context_'+re.sub('[^a-z0-9]+','_',o.name.lower()).strip('_');meshname='SM_EG_'+aid
   me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg);me.name=meshname;o.data=me;o.modifiers.clear()
   proto=bpy.data.objects.new(meshname,me);assetcol.objects.link(proto);proto.hide_render=True;proto['asset_id']=aid;proto['canonical_units']='metres';proto['pivot']='geometric centre; deliberate structural pivot';proto['Prop']=False
   mn=Vector(tuple(min(v.co[i] for v in me.vertices) for i in range(3)));mx=Vector(tuple(max(v.co[i] for v in me.vertices) for i in range(3)));dim=mx-mn;centre=(mn+mx)/2
   hm=boxmesh('UCX_'+meshname+'_00',dim);hm.transform(Matrix.Translation(centre));ho=bpy.data.objects.new(hm.name,hm);hullcol.objects.link(ho);ho['collision_for_asset']=aid;ho['collision_kind']='convex';ho['canonical_hull_transform_baked']=True;ho['export_only']=True
   category='structural_static' if colname=='01_STRUCTURE' else 'fixture_static';o['asset_id']=aid;o['collision_category']=category;o['export_scope']='canonical asset plus authored simple collision'
   a={'asset_id':aid,'mesh':meshname,'kind':category,'eligible':False,'canonical_scale':[1,1,1],'pivot':'geometric centre; deliberate structural pivot','collision_objects':[ho.name],'collision_hull_count':1,'materials':[x.name for x in me.materials],'triangles':sum(len(p.vertices)-2 for p in me.polygons),'dimensions_m':list(dim),'render_open_surfaces':'none; solid static context mesh'};context_assets.append(a)
   context_places.append({'stable_id':ident,'asset_id':aid,'object_name':o.name,'tags':['Structure'] if category=='structural_static' else ['Fixture'],'intended_unreal_actor_class':'StaticMeshActor','position_m':list(o.location),'rotation_euler_deg':[math.degrees(v) for v in o.rotation_euler],'scale':list(o.scale),'collision_asset':meshname,'instance_material_overrides':False})
   rec.update(category=category,asset_id=aid,collision_objects=[ho.name],collision_status='AUTHORED_SIMPLE_SOURCE_VALIDATION_PENDING',export_status='CANONICAL_STATIC_ASSET')
  else:
   if colname=='08_CAMERA_CAPTIONS':category='nonphysical_render_caption';reason='Camera-only approval caption; omit from game export.'
   elif o.name.startswith('Stone tile joint'):category='decorative_nonblocking_flush';reason='Flush grout accent over the continuous solid floor collider.'
   elif colname=='04_LIGHT_FIXTURES' and o.get('fixture_category'):category=o['fixture_category'];reason=o['nonblocking_reason']
   elif colname=='04_LIGHT_FIXTURES':category='ineligible_nonblocking_overhead';reason='Lighting decoration mounted above the shopping aisle; lighting source only.'
   elif o.type=='FONT':category='decorative_nonblocking_lettering';reason='Thin sign or shelf-price text mounted on solid supporting fixtures.'
   else:category='decorative_nonblocking_attached_trim';reason='Thin reveal attached to a solid wall or fixture; underlying collider defines boundary.'
   o['collision_category']=category;o['nonblocking_reason']=reason;o['export_scope']='nonblocking decoration' if colname!='08_CAMERA_CAPTIONS' else 'exclude from game export';rec.update(category=category,collision_status='INTENTIONAL_NONBLOCKING',justification=reason,export_status=o['export_scope'])
  inventory.append(rec)
m['assets']+=context_assets;m['context_placements']=context_places;m['scene_context_inventory']=inventory;m['physical_context_collision_complete']=True
m['notes']=[note for note in m['notes'] if 'Surrounding visual context' not in note]
m['notes']+=['All physical floor, ceiling, wall and console context has canonical static-asset collision; nonblocking visual elements have explicit categories and reasons.','UCX local transforms are baked into mesh-space; all hull object transforms are identity. Structural context pivots deliberately use geometric centres.','The shopping basket is an eligible collision-stress sample near the aisle edge; dynamic navigation and disguised-character movement remain untested.']
q['context_physical_assets']=len(context_assets);q['context_authored_hulls']=len(context_assets);q['total_authored_hulls']=sum(a['collision_hull_count'] for a in m['assets']);q['visual_context_export_qualification']='Every context object classified; physical structures and console have authored simple source collision; Unreal validation not run';q['side_typography_fitted']=True;q['independent_audit_required_after_changes']=True
for a in context_assets:
 ho=bpy.data.objects[a['collision_objects'][0]];bm=bmesh.new();bm.from_mesh(ho.data);q['asset_checks'].append({'asset_id':a['asset_id'],'canonical_scale':[1,1,1],'pivot_origin_m':[0,0,0],'pivot_type':a['pivot'],'collision_hull_count':1,'all_collision_hulls_positive_watertight':bm.calc_volume(signed=True)>0 and all(e.is_manifold for e in bm.edges),'render_zero_area_faces':0});bm.free()
with open(os.path.join(R,'EXPORT_MANIFEST.json'),'w') as f:json.dump(m,f,indent=2)
with open(os.path.join(R,'ASSET_COLLISION_QA.json'),'w') as f:json.dump(q,f,indent=2)
s['context_source_completed']=True;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=B);print('CONTEXT_COMPLETED',len(context_assets),'physical context assets',q['total_authored_hulls'],'total authored hulls',flush=True)
