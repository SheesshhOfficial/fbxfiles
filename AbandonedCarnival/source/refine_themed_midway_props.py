"""Differentiate candy and fortune booths with individual themed hiding props."""
import bpy,os,sys,math,random
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source')
from fast_geometry import make_api
from assemble_props import assemble
paper=bpy.data.materials.get('oldpaper') or bpy.data.materials.new('oldpaper');paper.use_nodes=True;paper.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.42,.36,.23,1);paper.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9
m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m)
def finish(name,parts,origin,family):
 for part in parts:
  me=part.data
  if not me.get('physical_uv_applied'):
   tile=me.materials[0].get('physical_tile_m',1)
   for uv in me.uv_layers.active.data:uv.uv/=tile
   me['physical_uv_applied']=True
 ob=assemble(name,parts,origin,family)
 for p in parts:p.hide_render=True;p.hide_set(True)
 return ob
for zone in ['CANDY FLOSS','FORTUNE']:
 old=sorted([o for o in bpy.data.objects if o.get('PropActorTag') and o.name.startswith('Midway '+zone) and o.get('asset_family') in ['Bottle','TeddyPrize']],key=lambda o:o.name)
 for o in old:
  o.hide_render=True;o.hide_set(True);o['visual_replaced']=True;del o['PropActorTag']
  if o.get('asset_family')=='TeddyPrize':continue
  index=int(o.name.rsplit('bottle',1)[-1]);origin=tuple(o.location);x,y,z=origin;parts=[]
  if zone=='CANDY FLOSS':
   if index%2==0:
    parts=[cyl('Candy jar body',(x,y,z+.15),.095,.30,'glass',32),cyl('Candy jar lid',(x,y,z+.315),.099,.03,'rust',32),cube('Candy jar paper label',(x-.096,y,z+.15),(.006,.125,.105),'oldpaper',.001)]
    for a in range(5):parts.append(cyl('Wrapped candy inside jar',(x+.032*math.cos(a*1.25),y+.032*math.sin(a*1.25),z+.04+a*.038),.025,.05,'PaintRed' if a%2 else 'PaintCream',12))
    family='ConfectioneryJar'
   else:
    parts=[cyl('Sealed toffee tin',(x,y,z+.075),.11,.15,'PaintTeal',32),cyl('Toffee tin upper rim',(x,y,z+.155),.114,.018,'rust',32),cyl('Toffee tin lid',(x,y,z+.168),.106,.008,'PaintCream',32)];family='ToffeeTin'
  elif index%2==0:
   parts=[cube('Fortune card deck sleeve',(x,y,z+.025),(.12,.18,.05),'PaintRed',.004),cube('Fortune card deck paper edge',(x-.002,y,z+.028),(.116,.174,.035),'oldpaper',.001),cube('Fortune card deck cover',(x,y,z+.048),(.12,.18,.006),'PaintTeal',.001)];family='FortuneCardDeck'
  else:
   parts=[cube('Fortune keepsake box',(x,y,z+.085),(.22,.17,.17),'wood',.012),cube('Keepsake box lid',(x,y,z+.179),(.23,.18,.025),'PaintRed',.006),cube('Keepsake box latch',(x-.116,y,z+.14),(.012,.035,.06),'gold',.003)];family='KeepsakeBox'
  finish('Themed '+zone+' '+family+' %02d'%index,parts,origin,family)
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
