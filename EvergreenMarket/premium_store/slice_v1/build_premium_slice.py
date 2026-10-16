"""You want it You get it pantry vertical slice. Metres, Z-up, canonical bottom-centre pivots.
Run Blender --background --python build_premium_slice.py. No Unreal validation implied.
"""
import bpy, bmesh, math, os, json, random
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__)); TEX=os.path.join(ROOT,'textures'); random.seed(71)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
COL={}
for name in ['01_STRUCTURE','02_FIXTURES','03_ELIGIBLE_PROP_PLACEMENTS','04_LIGHT_FIXTURES','05_LIGHTS','06_COLLISION_LIBRARY','07_CAMERAS','08_CAMERA_CAPTIONS','09_ASSET_LIBRARY']:
 c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);COL[name]=c
COL['06_COLLISION_LIBRARY'].hide_render=True;COL['06_COLLISION_LIBRARY'].hide_viewport=True
COL['09_ASSET_LIBRARY'].hide_render=True;COL['09_ASSET_LIBRARY'].hide_viewport=False
M={};assets={};placements=[];fixture_places=[];light_manifest=[];uid=0

def material(name,color,rough=.45,metal=0,transmission=0,ior=1.45):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;p.inputs['Transmission Weight'].default_value=transmission;p.inputs['IOR'].default_value=ior;M[name]=m;return m
material('Oak quarter-sawn',(.27,.125,.042),.38)
m=M['Oak quarter-sawn'];n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=7;tex.inputs['Detail'].default_value=3;tex.inputs['Roughness'].default_value=.7
coord=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(2,45,3);l.new(coord.outputs['Generated'],mapping.inputs[0]);l.new(mapping.outputs[0],tex.inputs['Vector']);r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.19;r.color_ramp.elements[0].color=(.12,.045,.012,1);r.color_ramp.elements[1].position=.82;r.color_ramp.elements[1].color=(.39,.22,.09,1);l.new(tex.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],p.inputs['Base Color']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.13;b.inputs['Distance'].default_value=.0012;l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
material('Walnut endgrain',(.115,.053,.021),.39)
material('Powder-coated graphite',(.022,.028,.025),.32,.65)
material('Brushed champagne brass',(.48,.31,.105),.26,.83)
material('Brushed tin',(.46,.49,.47),.24,.92)
material('Cream stone',(.72,.69,.59),.36)
m=M['Cream stone'];n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=90;t.inputs['Detail'].default_value=2;r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(.58,.56,.49,1);r.color_ramp.elements[1].color=(.79,.76,.67,1);l.new(t.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],p.inputs['Base Color']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.001;l.new(t.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
material('Warm plaster',(.75,.73,.67),.80);material('Grout',(.42,.41,.37),.65);material('Evergreen enamel',(.035,.105,.071),.30,.12);material('Paper ivory',(.83,.80,.67),.63);material('Label side navy',(.035,.078,.085),.57);material('Glass clear',(.94,.98,.97),.075,0,1,1.46);material('Glass olive',(.31,.40,.16),.11,0,1,1.46);material('Olive oil',(.31,.34,.065),.14,0,.5,1.47);material('Honey',(.56,.23,.025),.18,0,.48,1.48);material('Strawberry preserve',(.25,.022,.018),.28,0,.08,1.45);material('Black cap',(.018,.020,.016),.32,.35);material('Copper cap',(.38,.12,.055),.28,.77);material('Basket coated wire',(.045,.085,.062),.29,.65)

def emit(name,color,power):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();o=n.new('ShaderNodeOutputMaterial');e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);e.inputs['Strength'].default_value=power;m.node_tree.links.new(e.outputs[0],o.inputs['Surface']);M[name]=m;return m
emit('Warm opal diffuser',(1,.77,.47),3.2);emit('Caption green',(.025,.065,.046),1);emit('Caption white',(.92,.92,.84),1)

def link_obj(o,col):
 for c in list(o.users_collection):c.objects.unlink(o)
 COL[col].objects.link(o)
def mesh_obj(name,verts,faces,mat,col='09_ASSET_LIBRARY',uv=None,smooth=False):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(M[mat]);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();o=bpy.data.objects.new(name,me);COL[col].objects.link(o)
 if uv:
  layer=me.uv_layers.new(name='UVMap')
  for poly in me.polygons:
   for li in poly.loop_indices:layer.data[li].uv=uv[me.loops[li].vertex_index]
 for p in me.polygons:p.use_smooth=smooth
 return o

def box(name,loc,dim,mat,col='09_ASSET_LIBRARY',bevel=0):
 x,y,z=[s/2 for s in dim];v=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)];f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];o=mesh_obj(name,v,f,mat,col);o.location=loc
 if bevel:
  b=o.modifiers.new('Manufactured edge radius','BEVEL');b.width=bevel;b.segments=3;b.affect='EDGES';w=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
 return o

def lathe(name,profile,mat,col='09_ASSET_LIBRARY',n=64):
 verts=[];rings=[]
 for rad,z in profile:
  if rad==0:rings.append([len(verts)]);verts.append((0,0,z))
  else:
   rr=[]
   for i in range(n):a=2*math.pi*i/n;rr.append(len(verts));verts.append((rad*math.cos(a),rad*math.sin(a),z))
   rings.append(rr)
 faces=[]
 for aa,bb in zip(rings,rings[1:]):
  for i in range(n):j=(i+1)%n
  if len(aa)==1 and len(bb)>1:faces.extend((aa[0],bb[(i+1)%n],bb[i]) for i in range(n))
  elif len(bb)==1 and len(aa)>1:faces.extend((aa[i],aa[(i+1)%n],bb[0]) for i in range(n))
  elif len(aa)>1 and len(bb)>1:faces.extend((aa[i],aa[(i+1)%n],bb[(i+1)%n],bb[i]) for i in range(n))
 return mesh_obj(name,verts,faces,mat,col,smooth=True)

def cylinder(name,r,h,z,mat,col='09_ASSET_LIBRARY',n=48):return lathe(name,[(0,z),(r,z),(r,z+h),(0,z+h)],mat,col,n)
def torus(name,r,t,z,mat,col='09_ASSET_LIBRARY',n=48,k=10):
 v=[];f=[]
 for i in range(n):
  a=2*math.pi*i/n
  for j in range(k):b=2*math.pi*j/k;v.append(((r+t*math.cos(b))*math.cos(a),(r+t*math.cos(b))*math.sin(a),z+t*math.sin(b)))
 for i in range(n):
  for j in range(k):f.append((i*k+j,((i+1)%n)*k+j,((i+1)%n)*k+(j+1)%k,i*k+(j+1)%k))
 return mesh_obj(name,v,f,mat,col,smooth=True)

def curved_label(sku,r,z,h,halfangle=1.08):
 v=[];uv=[];f=[]
 for zz,tt in [(z,0),(z+h,1)]:
  for i in range(33):a=-halfangle+2*halfangle*i/32;v.append((r*math.sin(a),-r*math.cos(a),zz));uv.append((i/32,tt))
 for i in range(32):f.append((i,i+1,i+34,i+33))
 return mesh_obj('Printed curved label '+sku,v,f,'Label '+sku,uv=uv,smooth=True)
def panel_label(sku,w,h,d,z=0):
 return mesh_obj('Printed front '+sku,[(-w/2,-d/2-.00025,z),(w/2,-d/2-.00025,z),(w/2,-d/2-.00025,z+h),(-w/2,-d/2-.00025,z+h)],[(0,1,2,3)],'Label '+sku,uv=[(0,0),(1,0),(1,1),(0,1)])
def text_obj(name,body,loc,size,mat='Paper ivory',col='02_FIXTURES',rotation=(math.pi/2,0,0),align='CENTER'):
 curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.align_x=align;curve.size=size;curve.extrude=.00015;curve.bevel_depth=0;o=bpy.data.objects.new(name,curve);COL[col].objects.link(o);o.location=loc;o.rotation_euler=rotation;curve.materials.append(M[mat]);return o

def merge_parts(name,parts):
 # Baking modifiers and joining once per asset preserves materials and one object per placement.
 for o in bpy.context.selected_objects:o.select_set(False)
 for o in parts:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.convert(target='MESH');bpy.ops.object.join();o=bpy.context.object;o.name=name;o.data.name=name;bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 # Recalculate every disconnected solid component consistently.
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free();o.data.update();o.select_set(False);return o

def hull_box(asset,index,loc,dim):
 o=box('UCX_'+asset+'_'+str(index).zfill(2),loc,dim,'Black cap','06_COLLISION_LIBRARY');o.data.transform(o.matrix_basis);o.location=(0,0,0);return o

def hull_cyl(asset,index,r,h,z):
 o=cylinder('UCX_'+asset+'_'+str(index).zfill(2),r,h,z,'Black cap','06_COLLISION_LIBRARY',16);return o

def register(sku,obj,hulls,eligible=True,kind='product'):
 obj['asset_id']=sku;obj['canonical_units']='metres';obj['pivot']='bottom centre';obj['gameplay_validated']=False;obj.data['asset_id']=sku
 assets[sku]={'asset_id':sku,'mesh':obj.name,'kind':kind,'eligible':eligible,'canonical_scale':[1,1,1],'pivot':'bottom centre','render_open_surfaces':'Printed label panels, price cards, lettering; intentional non-colliding surface geometry','collision_objects':[h.name for h in hulls],'collision_hull_count':len(hulls),'materials':[m.name for m in obj.data.materials],'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'dimensions_m':list(obj.dimensions),'template':obj}
 for h in hulls:h['collision_for_asset']=sku;h['collision_kind']='convex';h['export_only']=True

def place(sku,loc,yaw=0,prefix='EGS'):
 a=assets[sku];base=a['template'];o=bpy.data.objects.new(base.name,base.data);COL['03_ELIGIBLE_PROP_PLACEMENTS' if a['eligible'] else '02_FIXTURES'].objects.link(o);o.location=loc;o.rotation_euler[2]=yaw;num=1+sum(x['asset_id']==sku for x in placements+fixture_places);ident=f'{prefix}_{sku.upper()}_{num:04d}';o.name=ident;o['stable_id']=ident;o['asset_id']=sku;o['Prop']=bool(a['eligible']);o['tags']='Prop' if a['eligible'] else 'Fixture';o['collision_profile']='Authored simple; Unreal untested';o['disguise_profile']='UNTESTED';o['canonical_scale_verified']=True
 rec={'stable_id':ident,'asset_id':sku,'object_name':o.name,'tags':['Prop'] if a['eligible'] else ['Fixture'],'intended_unreal_actor_class':'StaticMeshActor','position_m':list(loc),'rotation_euler_deg':[0,0,math.degrees(yaw)],'scale':[1,1,1],'collision_asset':a['mesh'],'instance_material_overrides':False}
 (placements if a['eligible'] else fixture_places).append(rec);return o

# Read externally generated bespoke labels.
for sku in ['crushed_tomatoes','chickpeas','coffee','olive_oil','wildflower_honey','strawberry_preserve','rolled_oats','almond_granola','bronze_pasta','sea_salt']:
 fn=os.path.join(TEX,sku+'.png')
 if not os.path.exists(fn):raise RuntimeError('Missing label texture: '+fn)
 m=material('Label '+sku,(.8,.75,.65),.52);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');im=bpy.data.images.load(fn);im.pack();im.colorspace_settings.name='sRGB';tx=n.new('ShaderNodeTexImage');tx.image=im;tx.interpolation='Linear';l.new(tx.outputs['Color'],p.inputs['Base Color']);p.inputs['Specular IOR Level'].default_value=.26
# Tin products with rolled rims, stamped lids, recessed rings and pull tab.
for sku,r,h in [('crushed_tomatoes',.043,.145),('chickpeas',.043,.145),('coffee',.052,.195)]:
 parts=[cylinder('Can body',r,h-.008,.004,'Paper ivory'),cylinder('Tin base',r-.002,.003,.002,'Brushed tin'),cylinder('Recessed lid',r-.001,.003,h-.004,'Brushed tin'),torus('Bottom rolled seam',r-.0005,.0018,.003,'Brushed tin'),torus('Upper rolled seam',r-.0005,.0018,h-.002,'Brushed tin'),torus('Lid stamp',r*.72,.0007,h-.0005,'Brushed tin'),curved_label(sku,r+.0003,.015,h-.031)]
 tab=torus('Pull tab',.009,.002,h+.001,'Brushed tin',n=24,k=8);tab.scale=(.65,1,1);parts.append(tab)
 if sku=='coffee':parts.append(cylinder('Coffee overcap',r+.0008,.008,h-.003,'Black cap'))
 obj=merge_parts('SM_MV_'+sku,parts);register(sku,obj,[hull_cyl(obj.name,0,r+.0018,h+.005,0)])
# Glass oil bottle, hollow shell, liquid body, shoulders, cap and neck band.
sku='olive_oil';parts=[]
profile=[(0,0),(.033,0),(.039,.007),(.041,.02),(.041,.191),(.038,.215),(.019,.243),(.016,.283),(.012,.283),(.014,.243),(.034,.211),(.037,.188),(.037,.020),(.030,.008),(0,.008)]
parts.append(lathe('Olive glass shell',profile,'Glass olive'))
parts.append(lathe('Olive oil fill',[(0,.012),(.034,.012),(.036,.02),(.036,.19),(.032,.211),(.024,.222),(0,.222)],'Olive oil'))
parts+=[cylinder('Bottle cap',.0178,.029,.274,'Black cap'),torus('Bottle neck band',.0178,.0013,.276,'Brushed champagne brass'),curved_label(sku,.0414,.043,.136)]
for z in [.28,.284,.288,.292,.296]:parts.append(torus('Cap knurl ring',.0179,.0004,z,'Black cap',n=32,k=6))
obj=merge_parts('SM_MV_'+sku,parts);register(sku,obj,[hull_cyl(obj.name,0,.0415,.218,0),hull_cyl(obj.name,1,.021,.086,.218)])
# Preserve and honey jars with true glass shells and contents.
for sku,fill,h in [('wildflower_honey','Honey',.151),('strawberry_preserve','Strawberry preserve',.134)]:
 r=.049;parts=[lathe('Jar glass shell',[(0,0),(.040,0),(.047,.006),(.049,.017),(.049,h-.027),(.046,h-.016),(.044,h-.010),(.040,h-.010),(.043,h-.029),(.045,.018),(.038,.007),(0,.007)],'Glass clear'),cylinder('Jar contents',.044,h-.035,.010,fill),cylinder('Metal jar cap',.048,.016,h-.013,'Copper cap' if sku=='strawberry_preserve' else 'Brushed champagne brass'),torus('Cap lip',.047,.0016,h-.011,'Brushed tin'),curved_label(sku,.0494,.025,h-.055)]
 for z in [h-.009,h-.005]:parts.append(torus('Jar lid detail',.048,.0006,z,'Copper cap' if sku=='strawberry_preserve' else 'Brushed champagne brass',n=48,k=6))
 obj=merge_parts('SM_MV_'+sku,parts);register(sku,obj,[hull_cyl(obj.name,0,.050,h+.003,0)])
# Paperboard boxes with printed front, side brand and fold seams.
for sku,w,d,h in [('rolled_oats',.151,.073,.267),('almond_granola',.145,.072,.250),('bronze_pasta',.113,.058,.304),('sea_salt',.088,.055,.150)]:
 parts=[box('Paperboard carton',(0,0,h/2),(w,d,h),'Label side navy',bevel=.0008),panel_label(sku,w-.001,h-.001,d,.0005),box('Folded top panel',(0,0,h+.0003),(w-.002,d-.002,.0006),'Paper ivory'),box('Carton top fold',(0,0,h+.0007),(.001,d-.002,.0004),'Walnut endgrain')]
 t=text_obj('Side print','MORROW & VALE',(w/2+.0005,0,h*.20),h*.045,'Paper ivory','09_ASSET_LIBRARY',rotation=(math.pi/2,0,math.pi/2));parts.append(t)
 obj=merge_parts('SM_MV_'+sku,parts);register(sku,obj,[hull_box(obj.name,0,(0,0,h/2),(w,d,h+.001))])
# Shopping basket: individually selectable solid asset with open cavity and compound hulls.
parts=[];w=.43;d=.29;h=.245
for x in [-w/2,w/2]:
 for y in [-d/2,d/2]:parts.append(box('Basket corner',(x,y,h/2),(.009,.009,h),'Basket coated wire',bevel=.003))
for z in [.012,.08,.15,.225]:
 for y in [-d/2,d/2]:parts.append(box('Basket horizontal rail',(0,y,z),(w,.008,.008),'Basket coated wire',bevel=.003))
 for x in [-w/2,w/2]:parts.append(box('Basket horizontal rail',(x,0,z),(.008,d,.008),'Basket coated wire',bevel=.003))
for x in [-.18,-.12,-.06,0,.06,.12,.18]:
 parts.append(box('Basket base wire',(x,0,.009),(.006,d,.006),'Basket coated wire',bevel=.002))
 for y in [-d/2,d/2]:parts.append(box('Basket upright wire',(x,y,.118),(.005,.005,.214),'Basket coated wire',bevel=.002))
for y in [-.10,-.05,0,.05,.10]:
 parts.append(box('Basket base wire',(0,y,.009),(w,.006,.006),'Basket coated wire',bevel=.002))
 for x in [-w/2,w/2]:parts.append(box('Basket end wire',(x,y,.118),(.005,.005,.214),'Basket coated wire',bevel=.002))
# Handles folded upright as U sections; preserve hand opening.
for y in [-.095,.095]:
 for x in [-.12,.12]:parts.append(box('Basket handle riser',(x,y,.30),(.010,.010,.16),'Basket coated wire',bevel=.003))
 parts.append(box('Basket oak grip',(0,y,.38),(.26,.020,.021),'Oak quarter-sawn',bevel=.009))
obj=merge_parts('SM_EG_Basket',parts);hulls=[hull_box(obj.name,0,(0,0,.009),(w,d,.018))]
for i,(loc,dim) in enumerate([((0,-d/2,.12),(w,.012,.24)),((0,d/2,.12),(w,.012,.24)),((-w/2,0,.12),(.012,d,.24)),((w/2,0,.12),(.012,d,.24))],1):hulls.append(hull_box(obj.name,i,loc,dim))
for y in [-.095,.095]:
 for x in [-.12,.12]:hulls.append(hull_box(obj.name,len(hulls),(x,y,.30),(.012,.012,.16)))
 hulls.append(hull_box(obj.name,len(hulls),(0,y,.38),(.26,.020,.021)))
register('shopping_basket',obj,hulls,True,'movable basket')
# Reusable premium bay: compound collision retains open shopping face and shelf gaps.
parts=[];hulls=[];asset='SM_EG_PremiumShelfBay';levels=[.28,.66,1.04,1.42,1.80]
parts.append(box('Oak plinth',(0,0,.105),(1.8,.68,.21),'Oak quarter-sawn',bevel=.006));hulls.append(hull_box(asset,len(hulls),(0,0,.105),(1.8,.68,.21)))
parts.append(box('Recessed toe kick',(0,-.025,.04),(1.70,.60,.08),'Powder-coated graphite',bevel=.002))
parts.append(box('Oak back panel',(0,.321,1.21),(1.76,.028,2.04),'Oak quarter-sawn',bevel=.003));hulls.append(hull_box(asset,len(hulls),(0,.321,1.21),(1.76,.028,2.04)))
for x in [-.884,.884]:
 for y in [-.308,.308]:
  parts.append(box('Black steel upright',(x,y,1.15),(.032,.032,2.30),'Powder-coated graphite',bevel=.002));hulls.append(hull_box(asset,len(hulls),(x,y,1.15),(.032,.032,2.30)))
for z in levels:
 parts.append(box('Oak shelf',(0,0,z),(1.75,.635,.030),'Oak quarter-sawn',bevel=.0025));hulls.append(hull_box(asset,len(hulls),(0,0,z),(1.75,.635,.030)))
 parts.append(box('Shelf rounded edge',(0,-.318,z+.002),(1.75,.018,.040),'Walnut endgrain',bevel=.004))
 parts.append(box('Champagne price rail',(0,-.329,z-.001),(1.74,.006,.026),'Brushed champagne brass',bevel=.001))
 for x in [-.72,-.24,.24,.72]:parts.append(box('Price label card',(x,-.333,z),(.23,.0015,.020),'Paper ivory',bevel=.0005))
parts+=[box('Crown moulding',(0,0,2.29),(1.84,.71,.10),'Oak quarter-sawn',bevel=.008),box('Cornice reveal',(0,-.355,2.25),(1.83,.008,.010),'Brushed champagne brass',bevel=.001)]
hulls.append(hull_box(asset,len(hulls),(0,0,2.29),(1.84,.71,.10)))
obj=merge_parts(asset,parts);register('premium_shelf_bay',obj,hulls,False,'fixture')
# World structure, tile joints and repeated fixture placement.
box('Floor slab',(0,1.75,-.08),(9,11,.16),'Cream stone','01_STRUCTURE')
for x in [i*.90 for i in range(-5,6)]:box('Stone tile joint X',(x,1.75,.0005),(.0025,11,.001),'Grout','01_STRUCTURE')
for y in [i*.90 for i in range(-4,9)]:box('Stone tile joint Y',(0,y,.0005),(9,.0025,.001),'Grout','01_STRUCTURE')
box('Ceiling',(0,1.75,3.43),(9,11,.12),'Warm plaster','01_STRUCTURE')
box('End wall',(0,6.10,1.7),(9,.18,3.4),'Warm plaster','01_STRUCTURE')
box('End wall oak dado',(0,5.99,.61),(9,.04,1.22),'Oak quarter-sawn','01_STRUCTURE')
box('End wall brass reveal',(0,5.95,1.24),(9,.014,.018),'Brushed champagne brass','01_STRUCTURE')
text_obj('Evergreen wall branding','You want it You get it',(0,5.89,2.45),.29,'Evergreen enamel')
text_obj('Slice wall label','THE PANTRY  /  VERTICAL SLICE',(0,5.88,2.13),.085,'Walnut endgrain')
# Side boundary backwalls outside shelves frame the short segment.
for x in [-2.35,2.35]:box('Warm side wall',(x,2.5,1.7),(.10,7,3.4),'Warm plaster','01_STRUCTURE')
# Stock all copies as independent Prop objects with shared meshes, no material overrides.
left_patterns=[['sea_salt','crushed_tomatoes','wildflower_honey','olive_oil','coffee'],['chickpeas','crushed_tomatoes','strawberry_preserve','olive_oil','coffee'],['rolled_oats','almond_granola','wildflower_honey','bronze_pasta','sea_salt']]
right_patterns=[['rolled_oats','almond_granola','bronze_pasta','chickpeas','strawberry_preserve'],['rolled_oats','coffee','almond_granola','olive_oil','bronze_pasta'],['chickpeas','strawberry_preserve','sea_salt','wildflower_honey','coffee']]
for side in [-1,1]:
 yaw=math.pi/2 if side==-1 else -math.pi/2
 for bay,y in enumerate([.35,2.17,3.99]):
  place('premium_shelf_bay',(side*1.83,y,0),yaw,'EGS_FIX')
  skus=(left_patterns if side==-1 else right_patterns)[bay]
  for zi,(z,sku) in enumerate(zip(levels,skus)):
   # Eight visible facings, two depths; deliberate subtle placement variation.
   for j in range(8):
    localx=-.72+j*(1.44/7)
    for depth in [0,1]:
     localy=-.19+depth*.18;xx=side*1.83+localx*math.cos(yaw)-localy*math.sin(yaw);yy=y+localx*math.sin(yaw)+localy*math.cos(yaw)
     place(sku,(xx,yy,z+.016),yaw+random.uniform(-.016,.016))
  # Price type belongs to fixture decoration, not separate interactive geometry.
  for zi,(z,sku) in enumerate(zip(levels,skus)):
   price={'sea_salt':'3.80','crushed_tomatoes':'2.90','wildflower_honey':'8.50','olive_oil':'16.00','coffee':'12.50','chickpeas':'2.60','strawberry_preserve':'6.40','rolled_oats':'4.80','almond_granola':'7.20','bronze_pasta':'4.20'}[sku]
   for localx in [-.72,-.24,.24,.72]:
    localy=-.334;xx=side*1.83-localy*math.sin(yaw);yy=y+localx*math.sin(yaw)
    text_obj('Shelf price '+sku,'M&V   '+price,(xx,yy,z-.005),.012,'Label side navy',rotation=(math.pi/2,0,yaw))
# Modest end display, intentionally only this aisle slice.
box('End tasting console',(0,5.33,.46),(1.95,.68,.92),'Walnut endgrain','02_FIXTURES',.009)
box('Console stone top',(0,5.33,.945),(2.02,.74,.06),'Cream stone','02_FIXTURES',.008)
for sku,x,yy in [('olive_oil',-.66,5.22),('wildflower_honey',-.43,5.11),('strawberry_preserve',-.20,5.12),('crushed_tomatoes',.05,5.15),('coffee',.29,5.23),('rolled_oats',.55,5.34),('bronze_pasta',.76,5.32)]:place(sku,(x,yy,.976),0)
place('shopping_basket',(1.05,1.35,.003),-.20)
# Actual fixture geometry and matching area lights beneath each diffuser.
for i,y in enumerate([.20,2.15,4.10]):
 for x in [-.64,.64]:box('Pendant suspension',(x,y,3.23),(.008,.008,.28),'Powder-coated graphite','04_LIGHT_FIXTURES',.002)
 box('Linear pendant housing',(0,y,3.08),(1.62,.14,.11),'Powder-coated graphite','04_LIGHT_FIXTURES',.015)
 box('Pendant brass edge',(0,y,3.023),(1.55,.122,.008),'Brushed champagne brass','04_LIGHT_FIXTURES',.002)
 box('Opal diffuser',(0,y,3.015),(1.50,.105,.009),'Warm opal diffuser','04_LIGHT_FIXTURES',.002)
 data=bpy.data.lights.new('EGS_LIGHT_PENDANT_'+str(i+1),'AREA');data.energy=115;data.shape='RECTANGLE';data.size=1.50;data.size_y=.105;data.color=(1,.84,.65);o=bpy.data.objects.new(data.name,data);COL['05_LIGHTS'].objects.link(o);o.location=(0,y,3.003);o['fixture_id']='Pendant '+str(i+1);o['units']='Blender Cycles watts';light_manifest.append({'id':o.name,'fixture':'Linear pendant '+str(i+1),'position_m':list(o.location),'type':'AREA','shape':'RECTANGLE','size_m':[1.5,.105],'energy_watts':115,'color_rgb':list(data.color),'orientation_euler_deg':[0,0,0],'Unreal_photometry_validated':False})
# Daylight entering from implied storefront opening, explicitly named fill source.
data=bpy.data.lights.new('EGS_LIGHT_STOREFRONT_DAYLIGHT','AREA');data.energy=420;data.shape='RECTANGLE';data.size=5;data.size_y=2.6;data.color=(.78,.87,1);o=bpy.data.objects.new(data.name,data);COL['05_LIGHTS'].objects.link(o);o.location=(0,-3.6,2.15);o.rotation_euler=(Vector((0,2,1.2))-o.location).to_track_quat('-Z','Y').to_euler();light_manifest.append({'id':o.name,'fixture':'Implied front glazing daylight','position_m':list(o.location),'type':'AREA','energy_watts':420,'size_m':[5,2.6],'Unreal_photometry_validated':False})
# Gentle wallwash from an actual top-mounted fixture.
box('End wallwash housing',(0,5.6,3.12),(1.8,.10,.08),'Powder-coated graphite','04_LIGHT_FIXTURES',.008)
data=bpy.data.lights.new('EGS_LIGHT_END_WALLWASH','AREA');data.energy=80;data.shape='RECTANGLE';data.size=1.7;data.size_y=.10;data.color=(1,.83,.60);o=bpy.data.objects.new(data.name,data);COL['05_LIGHTS'].objects.link(o);o.location=(0,5.52,3.06);o.rotation_euler=(Vector((0,5.8,1.6))-o.location).to_track_quat('-Z','Y').to_euler();light_manifest.append({'id':o.name,'fixture':'End wallwash housing','position_m':list(o.location),'type':'AREA','energy_watts':80,'Unreal_photometry_validated':False})
# Render scene, cameras and captions.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=64;scene.cycles.use_denoising=False;scene.cycles.adaptive_threshold=.025;scene.cycles.max_bounces=8;scene.cycles.transmission_bounces=6;scene.cycles.transparent_max_bounces=8;scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=1500;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.45,.52,.60,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.12;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.50
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene['stage']='PANTRY VERTICAL SLICE / VISUAL APPROVAL';scene['gameplay_tested']=False

def camera(name,loc,target,lens,focus,aperture):
 data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);COL['07_CAMERAS'].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;data.clip_start=.05;data.clip_end=100;data.dof.use_dof=False;data.dof.focus_distance=(Vector(focus)-o.location).length;data.dof.aperture_fstop=aperture;return o
cams=[camera('01_Aisle_eyeheight',(0,-3.40,1.65),(0,3.3,1.46),30,(0,1.4,1.5),7.1),camera('02_Product_closeup',(-.55,-.16,1.24),(-1.64,.25,1.14),60,(-1.64,.25,1.14),8),camera('03_Pantry_product_study',(1.10,3.05,1.54),(-.05,5.23,1.17),56,(-.05,5.23,1.17),8)]
# Caption meshes are camera-only ray-visible and never cast shadows or pollute reflections.
for cam in cams:
 w=2*math.tan(cam.data.angle_x/2);h=w*1100/1500
 panel=box('Vertical slice caption',(0,0,0),(w,h*.075,.001),'Caption green','08_CAMERA_CAPTIONS');panel.parent=cam;panel.location=(0,h*.4625,-1.005)
 title=text_obj('Vertical slice title','You want it You get it  /  PANTRY VERTICAL SLICE',(0,0,0),w*.013,'Caption white','08_CAMERA_CAPTIONS',rotation=(0,0,0),align='LEFT');title.data.extrude=0;title.parent=cam;title.location=(-w*.477,h*.468,-1)
 sub=text_obj('Vertical slice status','VISUAL APPROVAL  |  Genuine Blender Cycles render  |  Gameplay and Unreal import untested',(0,0,0),w*.0066,'Caption white','08_CAMERA_CAPTIONS',rotation=(0,0,0),align='LEFT');sub.data.extrude=0;sub.parent=cam;sub.location=(-w*.477,h*.439,-1)
 for ob in [panel,title,sub]:
  ob.visible_shadow=False;ob.visible_diffuse=False;ob.visible_glossy=False;ob.visible_transmission=False;ob.visible_volume_scatter=False;ob.hide_render=cam!=cams[0]
# Geometry QA uses actual mesh topology, not assumptions about primitive winding.
qa={'units':'metres; Unreal import must use metre-to-centimetre conversion 100','scope':'One pantry aisle vertical slice only','all_gameplay_checks':'NOT RUN','asset_checks':[],'placement_count':len(placements),'unique_eligible_assets':sum(a['eligible'] for a in assets.values()),'fixture_placements':len(fixture_places),'fixture_bay_aisle_clear_m':2*(1.83-.355),'warnings':[]}
for sku,a in assets.items():
 obj=a['template'];me=obj.data;bm=bmesh.new();bm.from_mesh(me);zero=sum(f.calc_area()<1e-12 for f in bm.faces);vol=bm.calc_volume(signed=True);bm.free();hchecks=[]
 for hn in a['collision_objects']:
  ho=bpy.data.objects[hn];bm=bmesh.new();bm.from_mesh(ho.data);nonmanifold=sum(not e.is_manifold for e in bm.edges);hv=bm.calc_volume(signed=True);zfaces=sum(f.calc_area()<1e-12 for f in bm.faces);bm.free();hchecks.append({'object':hn,'positive_volume':hv>0,'watertight':nonmanifold==0,'zero_area_faces':zfaces,'scale':list(ho.scale)})
 check={'asset_id':sku,'render_zero_area_faces':zero,'render_signed_volume_m3':vol,'canonical_scale':list(obj.scale),'pivot_origin_m':list(obj.location),'all_collision_hulls_positive_watertight':all(h['positive_volume'] and h['watertight'] and h['zero_area_faces']==0 for h in hchecks),'collision_hull_count':len(hchecks),'collision_details':hchecks}
 qa['asset_checks'].append(check)
 if zero or not check['all_collision_hulls_positive_watertight']:qa['warnings'].append(sku+' needs mesh review')
qa['all_placement_scales_unit']=all(tuple(o.scale)==(1,1,1) for o in COL['03_ELIGIBLE_PROP_PLACEMENTS'].objects)
qa['unique_stable_ids']=len({p['stable_id'] for p in placements})==len(placements)
qa['eligible_placement_material_overrides']=0
manifest={'version':'premium_store_slice_v1','status':'Visual approval candidate; NOT Unreal tested','coordinate_system':{'linear_unit':'metres','up_axis':'Z','unreal_translation_multiplier':100},'every_physical_eligible_placement_is_separate_object':True,'shared_mesh_assets':True,'assets':[{k:v for k,v in a.items() if k!='template'} for a in assets.values()],'eligible_placements':placements,'fixture_placements':fixture_places,'lights':light_manifest,'notes':['Collision library objects are asset-local export hulls; pair by UCX names. They are hidden in render.','Individual placement objects carry Prop=true and tags=Prop. No ISM grouping or representative-only eligibility.','Asset meshes contain canonical material slots; placements have no instance-level material overrides.','Authored collision does not verify Character capsule fitting, selection traces or network behavior.']}
with open(os.path.join(ROOT,'EXPORT_MANIFEST.json'),'w') as f:json.dump(manifest,f,indent=2)
with open(os.path.join(ROOT,'ASSET_COLLISION_QA.json'),'w') as f:json.dump(qa,f,indent=2)
# Asset masters kept exportable but hidden; images packed into blend.
for a in assets.values():a['template'].hide_render=True
COL['09_ASSET_LIBRARY'].hide_viewport=True
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:im.pack()
scene.camera=cams[0];bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend'))
print('SCENE_BUILT',len(placements),'eligible placements;',len(assets),'assets;',len(qa['warnings']),'QA warnings',flush=True)
# Low-cost first look; final render script chooses camera resolution and samples.
scene.cycles.samples=24;scene.render.resolution_percentage=70;scene.render.filepath=os.path.join(ROOT,'PREVIEW_AISLE.png');bpy.ops.render.render(write_still=True)
print('PREVIEW_COMPLETE',flush=True)
