"""One-time final detail layer, safely repeatable on the authored scene."""
import bpy,math,random
from pathlib import Path
from mathutils import Vector
random.seed(23)
ROOT=Path(__file__).resolve().parents[1];s=bpy.context.scene
if not s.get('polish_layer_v1'):
 c=bpy.data.collections.new('17_Promotional_Displays');s.collection.children.link(c)
 # Reuse the beveled authored mesh shapes, with unique material slots where needed.
 btemplate=next(o for o in s.objects if o.name.startswith('Produce island plinth')).data
 ctemplate=next(o for o in s.objects if o.name.startswith('Safety bollard')).data
 stemplate=next(o for o in s.objects if o.name.startswith('Herb foliage')).data
 cache={}
 def shaped(name,loc,dims,ma,typ='box',collection=c):
  key=(typ,ma)
  if key not in cache:
   cache[key]={'box':btemplate,'cyl':ctemplate,'sphere':stemplate}[typ].copy();cache[key].materials.clear();cache[key].materials.append(bpy.data.materials[ma])
  o=bpy.data.objects.new(name,cache[key]);collection.objects.link(o);o.location=loc
  bounds=[max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices) for i in range(3)];o.scale=[dims[i]/bounds[i] for i in range(3)];return o
 def txt(name,body,loc,size=.2,ma='cream paper',rot=(math.pi/2,0,0)):
  d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size;d.align_x='CENTER';d.align_y='CENTER';d.font=bpy.data.fonts['DejaVu Sans Bold'];d.extrude=.001;d.materials.append(bpy.data.materials[ma]);o=bpy.data.objects.new(name,d);c.objects.link(o);o.location=loc;o.rotation_euler=rot;return o
 def rod(name,x,y,z1,z2,r=.008):return shaped(name,(x,y,(z1+z2)/2),(2*r,2*r,z2-z1),'steel','cyl')
 # The produce board is a real suspended sign.
 for x in (-17.45,-13.55):rod('Produce sign suspension',x,-9.9,3.5,4.9)
 # Landmarks intentionally sit outside the uninterrupted shelf cross-aisles.
 for i,(x,y,caption,sku) in enumerate([(-5,15,'PANTRY PICKS',0),(7,15,'WEEKEND FAVORITES',14),(15,-6,'DRINKS TO GO',3)]):
  shaped('Promotional island plinth',(x,y,.18),(2.25,2.1,.36),'deep evergreen')
  shaped('Promotional island timber box',(x,y,.57),(2.18,2.03,.55),'oak')
  shaped('Promotional island top',(x,y,.88),(2.35,2.2,.09),'oak light')
  shaped('Stepped merchandise riser',(x,y+.48,1.04),(2.15,.9,.24),'oak light')
  template=next(o for o in s.objects if o.name.startswith(f'PROP_SKU_{sku:02d}_'))
  for row in range(5):
   for col in range(8):
    o=bpy.data.objects.new('PROMO_'+template.name,template.data);c.objects.link(o);o.location=(x-.92+col*.26,y-.82+row*.37,.94 if row<3 else 1.19);o.rotation_euler.z=random.uniform(-.05,.05)
  for xx in (x-.9,x+.9):rod('Promo header post',xx,y+.95,.92,1.95,.012)
  shaped('Promotional feature sign',(x,y+.95,1.93),(2.35,.07,.48),'deep evergreen');txt('Promo headline',caption,(x,y+.905,1.97),.14);txt('Promo supporting line','EVERGREEN  /  EVERYDAY VALUE',(x,y+.904,1.81),.065)
  shaped('Promotional offer card',(x,y-1.12,.68),(.9,.03,.32),'cream paper');txt('Promotional price','THIS WEEK  $ 3.49',(x,y-1.14,.68),.082,'ink')
 # Department posters, bolted to the west wall, add graphic hierarchy.
 for y,title,small in [(-13,'GROWN WITH CARE','FRESH PRODUCE / EVERY MORNING'),(2,'LOCAL. SEASONAL.','GOOD FOOD BRINGS US TOGETHER')]:
  shaped('West wall framed poster',(-21.79,y,2.75),(.075,3.0,1.45),'oak')
  shaped('Poster cream face',(-21.74,y,2.75),(.025,2.83,1.28),'cream paper')
  txt('Poster headline',title,(-21.72,y,2.94),.22,'deep evergreen',(math.pi/2,0,math.pi/2));txt('Poster caption',small,(-21.71,y,2.52),.087,'ink',(math.pi/2,0,math.pi/2))
 # Roof mechanical equipment remains in roof collection, hidden by cutaway views.
 roof=bpy.data.collections['03_Roof_Ceiling']
 for x in (-12,0,12):
  y=23
  shaped('Rooftop AHU curb',(x,y,5.51),(3.9,2.8,.2),'charcoal',collection=roof)
  shaped('Rooftop air handling unit',(x,y,6.13),(3.6,2.5,1.05),'brushed steel',collection=roof)
  for xx in (x-.88,x+.88):
   shaped('Condenser fan recess',(xx,y,6.69),(1.3,1.3,.07),'charcoal','cyl',roof)
   shaped('Fan centre motor',(xx,y,6.76),(.21,.21,.16),'steel','cyl',roof)
   for k in range(6):
    a=k*math.tau/6;o=shaped('Condenser fan blade',(xx+math.cos(a)*.32,y+math.sin(a)*.32,6.74),(.5,.13,.025),'steel',collection=roof);o.rotation_euler.z=a+.5
   for q in range(9):shaped('Fan protective grille',(xx-.52+q*.13,y,6.8),(.012,1.07,.015),'steel',collection=roof)
  for q in range(11):shaped('AHU front louvre',(x,y-1.262,5.8+q*.065),(3.35,.035,.035),'charcoal',collection=roof)
 # Planters and simple mature foliage near entrance, leaving doors/circulation open.
 site=bpy.data.collections['00_Site']
 for x in (-15,15):
  shaped('Entrance planter',(x,-20.6,.35),(3,1.1,.7),'concrete',collection=site);shaped('Planter soil',(x,-20.6,.72),(2.86,.97,.04),'oak',collection=site)
  for j in range(15):
   xx=x-1.25+j*.18;shaped('Entrance planting',(xx,-20.6+random.uniform(-.18,.18),.99+random.uniform(0,.16)),(.5,.5,.65),'leaf','sphere',site)
 s['polish_layer_v1']=True
# Better human-height presentation, less ceiling, and balanced luminance.
o=bpy.data.objects['CAM_Interior_Hero'];o.location=(-18.5,-15.8,2.1);o.rotation_euler=(Vector((-1,5,1.55))-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=22
s.view_settings.exposure=-1.0
s['Review notes']='Visual QA: lower eye-level camera, supported produce header, added promo landmarks and rooftop mechanical detail.'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Evergreen_Market.blend'),compress=True)
print('POLISH SAVED',flush=True)
