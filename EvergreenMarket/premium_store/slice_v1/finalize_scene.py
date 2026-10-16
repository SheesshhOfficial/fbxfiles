import bpy,os,json,math
from mathutils import Vector,Matrix
R=os.path.dirname(os.path.abspath(__file__));fn=os.path.join(R,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend');bpy.ops.wm.open_mainfile(filepath=fn);s=bpy.context.scene
s.cycles.use_denoising=False;s.cycles.samples=512;s.cycles.adaptive_threshold=.008;s.cycles.caustics_reflective=False;s.cycles.caustics_refractive=False;s.cycles.sample_clamp_indirect=3;s.cycles.blur_glossy=.5;s.view_settings.exposure=-.50
# Bake collision local transforms into their mesh coordinates: all UCX origins now canonical zero.
for o in bpy.data.collections['06_COLLISION_LIBRARY'].objects:
 o.data.transform(o.matrix_basis);o.matrix_basis=Matrix.Identity(4);o.data.update();o['canonical_hull_transform_baked']=True
# Keep the stress-test basket in camera view, near the aisle edge.
o=bpy.data.objects['EGS_SHOPPING_BASKET_0001'];o.location=(1.05,1.35,.003)
changes={'02_Product_closeup':((-.55,-.16,1.24),(-1.64,.25,1.14),60),'03_Pantry_product_study':((1.10,3.05,1.54),(-.05,5.23,1.17),56)}
for o in bpy.data.collections['07_CAMERAS'].objects:
 oldlens=o.data.lens;o.data.dof.use_dof=False
 if o.name in changes:
  pos,target,lens=changes[o.name];o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens
  ratio=oldlens/lens
  for child in o.children:
   child.location.x*=ratio;child.location.y*=ratio
   if child.type=='FONT':child.data.size*=ratio
   else:child.scale.x*=ratio;child.scale.y*=ratio
# Supporting scene inventory is explicit even though only canonical asset sets are export-qualified.
scene_inventory=[]
for collection in ['01_STRUCTURE','02_FIXTURES','04_LIGHT_FIXTURES']:
 for i,o in enumerate(bpy.data.collections[collection].objects):
  if o.get('stable_id'):continue
  ident='EGS_CONTEXT_'+collection[:2]+'_'+str(i+1).zfill(4);o['stable_id']=ident;o['Prop']=False;o['export_scope']='visual context; collision inventory pending';scene_inventory.append({'stable_id':ident,'object_name':o.name,'collection':collection,'type':o.type,'eligible':False,'export_status':'VISUAL_CONTEXT_ONLY','collision_status':'Not export-qualified in this slice'})
with open(os.path.join(R,'EXPORT_MANIFEST.json')) as f:m=json.load(f)
for p in m['eligible_placements']:
 if p['asset_id']=='shopping_basket':p['position_m']=[1.05,1.35,.003]
m['display_store_name']='You want it You get it';m['scene_context_inventory']=scene_inventory;m['notes'].append('All UCX hull object transforms are baked into canonical mesh-space coordinates; hull objects are identity-transform. Surrounding visual context is inventoried but not collision/export-qualified.')
with open(os.path.join(R,'EXPORT_MANIFEST.json'),'w') as f:json.dump(m,f,indent=2)
with open(os.path.join(R,'ASSET_COLLISION_QA.json')) as f:q=json.load(f)
q['collision_object_transforms_baked']=True;q['display_store_name']='You want it You get it';q['visual_context_export_qualification']='PENDING; separately inventoried in export manifest';q['rendering']='Cycles CPU; no denoiser available, high-sample render'
with open(os.path.join(R,'ASSET_COLLISION_QA.json'),'w') as f:json.dump(q,f,indent=2)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=fn);print('FINAL_SCENE_PATCHED',flush=True)
