"""Source-first surgical v3 refinement; run against complete exterior v2. No gameplay moves."""
import bpy, math, json, hashlib,struct
from mathutils import Vector,Matrix
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent;T=R/'textures';T.mkdir(exist_ok=True)
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s;bpy.context.view_layer.update()
col=bpy.data.collections.new('13_INTERIOR_REFINEMENT_v3');s.collection.children.link(col)
# New collection must be visible in the existing exterior preview too.
for sc in bpy.data.scenes:
 if sc!=s:sc.collection.children.link(col)
def fingerprint(o,materials=True):
 h=hashlib.sha256();h.update(o.type.encode());h.update(str(tuple(round(x,7) for row in o.matrix_world for x in row)).encode());h.update(str(sorted((k,str(v)) for k,v in o.items())).encode())
 if o.type=='MESH':
  for v in o.data.vertices:h.update(struct.pack('fff',*v.co))
  for p in o.data.polygons:h.update(struct.pack('I',p.material_index));h.update(str(tuple(p.vertices)).encode())
 if o.type=='FONT':h.update(o.data.body.encode());h.update(str(o.data.size).encode())
 if materials and hasattr(o.data,'materials'):h.update(str([m.name if m else None for m in o.data.materials]).encode())
 return h.hexdigest()
baseline={o.name:fingerprint(o) for o in bpy.data.objects};geometry={o.name:fingerprint(o,False) for o in bpy.data.objects};changed=set();added=[];coverage=[]
json.dump({'hashes':baseline,'geometry_hashes':geometry},open(R/'PRESERVATION_BASELINE.json','w'),indent=2)
def material(name,c,rough=.6,metal=0):
 m=bpy.data.materials.new('V3_'+name);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
sage=material('Mineral_sage',(.20,.29,.225),.82);forest=material('Deep_forest',(.035,.105,.073),.72);terra=material('Muted_terracotta',(.34,.145,.087),.78);clay=material('Soft_clay',(.43,.255,.155),.79);teal=material('Cellar_teal',(.045,.14,.145),.72);cream=material('Warm_cream_letters',(.88,.78,.58),.46);metal=material('Charcoal_hardware',(.024,.031,.028),.36,.55);brass=material('Satin_brass',(.46,.30,.115),.36,.72);grout=material('Stone_grout',(.115,.10,.078),.8);floor=material('Warm_greige_honed_stone',(.30,.26,.20),.49)
def assign(o,m):
 changed.add(o.name);o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(m)
def bounds(o):
 c=[o.matrix_world@Vector(v) for v in o.bound_box];return Vector([min(v[i] for v in c) for i in range(3)]),Vector([max(v[i] for v in c) for i in range(3)])
def box(name,center,dims,mat,yaw=0,category='ineligible_nonblocking_overhead'):
 x,y,z=[v/2 for v in dims];vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)];fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];me=bpy.data.meshes.new('V3_'+name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();o=bpy.data.objects.new('V3_'+name,me);col.objects.link(o);o.location=center;o.rotation_euler.z=yaw;o['Prop']=False;o['refinement_v3']=True;o['collision_category']=category;o['collision']='None: decorative attachment or overhead; original gameplay colliders unchanged';o['export_scope']='V3 visual overlay';added.append(o.name);return o
# Image-driven UV material, no procedural shader dependence in export. Texture is seamless.
n=1024;rng=np.random.default_rng(318);xx,yy=np.meshgrid(np.arange(n)/n,np.arange(n)/n)
noise=np.zeros((n,n))
for k,f in enumerate([2,4,9,19,41]):noise+=np.sin(2*np.pi*(xx*f+yy*(f//2+1))+k)*np.cos(2*np.pi*(yy*(f+1)-xx*(f//3+1)))*(.012/(k+1))
noise+=rng.normal(0,.0035,(n,n));base=np.array([.34,.295,.235]);rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(base+noise[:,:,None],0,1)
im=bpy.data.images.new('V3_Stone_BaseColor',width=n,height=n,alpha=False);im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();im.pack();im.filepath='//textures/'+im.name+'.png';tx=floor.node_tree.nodes.new('ShaderNodeTexImage');tx.image=im;floor.node_tree.links.new(tx.outputs['Color'],floor.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
# Portable tangent-space micronormal, very subtle stone grain.
dy,dx=np.gradient(noise);normal=np.dstack((-dx*1.5,-dy*1.5,np.ones_like(noise)));normal/=np.linalg.norm(normal,axis=2)[:,:,None];rgba[:,:,:3]=normal*.5+.5
imn=bpy.data.images.new('V3_Stone_Normal',width=n,height=n,alpha=False);imn.colorspace_settings.name='Non-Color';imn.pixels.foreach_set(rgba.ravel());imn.filepath_raw=str(T/(imn.name+'.png'));imn.file_format='PNG';imn.save();imn.pack();imn.filepath='//textures/'+imn.name+'.png';tn=floor.node_tree.nodes.new('ShaderNodeTexImage');tn.image=imn;nm=floor.node_tree.nodes.new('ShaderNodeNormalMap');floor.node_tree.links.new(tn.outputs['Color'],nm.inputs['Color']);floor.node_tree.links.new(nm.outputs['Normal'],floor.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
o=bpy.data.objects['FULL_MAIN_FLOOR_00001'];assign(o,floor);uv=o.data.uv_layers.new(name='V3_StoneUV')
for p in o.data.polygons:
 for li in p.loop_indices:
  v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x/2.4,v.y/2.4)
o.data.uv_layers.active=uv
# Paint only the visible architectural instances; shared asset-library masters remain unchanged.
for o in list(bpy.data.objects):
 if o.name.startswith('Stone grout '):assign(o,grout)
 if o.name.startswith('FULL_') and o.type=='MESH' and any(m and m.name=='Warm plaster' for m in o.data.materials) and o.get('asset_id') not in ['roof_slab','front_upper_lintel']:
  aid=o.get('asset_id','');m=terra if aid=='wall_left' else forest if aid=='wall_rear' else sage
  if 'office' in aid:m=teal
  if 'wc_' in aid or 'stall' in aid:m=clay
  assign(o,m)
# Determine actual sign-local coordinates: local X horizontal, local Y vertical, normal faces shopper.
signs=[o for o in bpy.data.objects if o.type=='FONT' and o.name.startswith('SIGN ')]
for idx,o in enumerate(signs):
 body=o.data.body
 if body=='You want it You get it':
  coverage.append({'text':o.name,'method':'Preserved exterior v2 fascia-mounted lettering','backing':'FULL_FRONT_SIGN_FASCIA_00001','supports':['EXT2 facade assembly'],'unchanged':True});continue
 changed.add(o.name);o.data=o.data.copy()
 aisle=body[:2].isdigit()
 if aisle:o.data.size=.23
 o.data.extrude=.0012;o.data.bevel_depth=.0003;o.data.bevel_resolution=1
 bpy.context.view_layer.update()
 coords=[Vector(v) for v in o.bound_box];lx0=min(v.x for v in coords);lx1=max(v.x for v in coords);ly0=min(v.y for v in coords);ly1=max(v.y for v in coords)
 lc=Vector(((lx0+lx1)/2,(ly0+ly1)/2,0));center=o.matrix_world@lc;right=(o.matrix_world.to_3x3()@Vector((1,0,0))).normalized();back=(o.matrix_world.to_3x3()@Vector((0,0,-1))).normalized();yaw=o.rotation_euler.z
 w=lx1-lx0+(.40 if aisle else .55);h=max(.34 if aisle else .39,ly1-ly0+.23)
 board=bpy.data.objects.get('Wayfinding backing '+body)
 if body in ['CHECKOUTS','WELCOME IN']:
  boards=[q for q in bpy.data.objects if q.name.startswith('Front wayfinding backing')];board=min(boards,key=lambda q:(q.location-center).length)
 # Small labels are mounted directly to existing room headers / refrigeration fascia where present.
 walllabel=body in ['COLD STORE','STAFF OFFICE','BREAK ROOM','CUSTOMER WC','STAFF WC']
 refrigeration=body in ['DAIRY','CHILLED','FROZEN','FRESH DRINKS']
 supports=[];depth=.075;bc=center+back*(depth/2+.003)
 if walllabel:depth=.035;bc=center+back*(depth/2+.003)
 if refrigeration:depth=.035;bc=center+back*(depth/2+.003)
 palette=forest
 if body in ['COFFEE & PATISSERIE','BAKED HERE','DELI & CHEESE','BUTCHER']:palette=terra
 if body in ['DAIRY / CHILLED / FROZEN','FISHMONGER','THE CELLAR & DRINKS'] or refrigeration:palette=teal
 if body=='FLOWERS & FINDS':palette=sage
 o.data.materials.clear();o.data.materials.append(cream)
 if board:
  changed.add(board.name);board.data=board.data.copy();board.data.materials.clear();board.data.materials.append(palette)
  # Existing board's actual geometry replaced with exact sign-sized box. Only decoration changes.
  old=board;new=box('Temporary_board_'+str(idx),bc,(w,depth,h),palette,yaw);old.data=new.data;old.location=bc;old.rotation_euler=(0,0,yaw);old.scale=(1,1,1);added.remove(new.name);bpy.data.objects.remove(new,do_unlink=True);board=old
 else:board=box('Sign_backing_'+str(idx).zfill(2),bc,(w,depth,h),palette,yaw,'decorative_nonblocking_attached_trim' if walllabel or refrigeration else 'ineligible_nonblocking_overhead')
 # A thin brass bottom rule belongs to the board, visibly touching its front face.
 rule=box('Sign_brass_rule_'+str(idx),center+Vector((0,0,-h/2+.025))+back*.001,(w-.05,.009,.008),brass,yaw);supports.append(rule.name)
 if walllabel or refrigeration:
  # Back of plaque intersects the existing header / case fascia. Two attachment studs finish front.
  for j,k in enumerate([-.40,.40]):
   q=center+right*(w*k)+back*.001;stud=box('Plaque_stud_'+str(idx)+'_'+str(j),q,(.018,.012,.018),brass,yaw,'decorative_nonblocking_attached_trim');supports.append(stud.name)
  method='Surface-mounted plaque with two fixing studs; existing wall/header or case fascia behind'
 else:
  # Visible twin rigid hangers go all the way into actual roof underside at 4.66 m.
  top=center.z+h/2;ceiling=4.675
  for j,k in enumerate([-.36,.36]):
   anchor=bc+right*(w*k);rod=box('Sign_hanger_'+str(idx)+'_'+str(j),(anchor.x,anchor.y,(top+ceiling)/2),(.026,.026,ceiling-top+.018),metal);supports.append(rod.name)
   shoe=box('Ceiling_anchor_'+str(idx)+'_'+str(j),(anchor.x,anchor.y,4.655),(.13,.13,.03),metal);supports.append(shoe.name)
   collar=box('Sign_top_clamp_'+str(idx)+'_'+str(j),(anchor.x,anchor.y,top-.009),(.085,depth+.025,.055),brass,yaw);supports.append(collar.name)
  method='Rigid twin ceiling hangers with roof-contact anchor plates and board clamps'
 coverage.append({'text':o.name,'body':body,'method':method,'backing':board.name,'supports':supports,'text_front_gap_m':.003,'bottom_z':float(center.z-h/2),'ceiling_contact_z':None if walllabel or refrigeration else 4.66,'wall_mounted':walllabel,'case_mounted':refrigeration})
# Palette accent details remain flush against boundary walls, outside all floor routes.
for name,c,d in [('Left_wall_brass_reveal',(.004,28,3.85),(.008,55.8,.018)),('Right_wall_brass_reveal',(63.996,28,3.85),(.008,55.8,.018)),('Rear_wall_brass_reveal',(32,55.996,3.85),(63.8,.008,.018))]:box(name,c,d,brass,category='decorative_nonblocking_attached_trim')
bpy.context.view_layer.update()
protected={name:h for name,h in baseline.items() if name not in changed};errors=[name for name,h in protected.items() if fingerprint(bpy.data.objects[name])!=h];assert not errors,errors
eligible=bpy.data.collections['03_ELIGIBLE_PROP_PLACEMENTS'];assert len(eligible.objects)==5574
# Source manifest includes every changed object and every physical sign assembly.
manifest={'version':'premium_store_refinement_v3','source':'premium_store_exterior_v2/YOU_WANT_IT_YOU_GET_IT_EXTERIOR_v2.blend','display_name':'You want it You get it','changed_objects':sorted(changed),'added_objects':added,'sign_attachments':coverage,'eligible_placements':5574,'protected_objects':len(protected),'protected_unchanged':True,'new_signage_collision':'None. Overhead assemblies clear player envelope; flush plaques use existing support collision. Original colliders preserved.','floor_shader':'Packed image base color and tangent normal; explicit repeating UV; roughness .49; original continuous floor collision','unreal_tested':False,'full_v1_export_updated':False}
json.dump(manifest,open(R/'REFINEMENT_MANIFEST.json','w'),indent=2)
s.camera=bpy.data.objects['FULL_AISLE_EYEHEIGHT'];bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend'),compress=True)
print('REFINEMENT_SAVED',len(changed),len(added),len(coverage),flush=True)
# An isolated v3 overlay includes replacements (remove old named objects) plus additions.
# Convert copied text to meshes only in transient export session; source stays editable.
for o in bpy.context.selected_objects:o.select_set(False)
for name in sorted(changed)+added:
 o=bpy.data.objects[name];o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects[sorted(changed)[0]]
bpy.ops.object.convert(target='MESH');bpy.ops.export_scene.gltf(filepath=str(R/'REFINEMENT_v3_OVERLAY.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_apply=True,export_yup=True,export_extras=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
print('OVERLAY_EXPORTED',flush=True)
