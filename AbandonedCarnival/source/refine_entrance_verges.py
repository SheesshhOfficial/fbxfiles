"""Localized entrance verge clusters; keep broad central arrival strip clear."""
import bpy,os,sys,random,math
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source')
from natural_vegetation import Patch,fern,grass,bramble
from fast_geometry import make_api
m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m);rng=random.Random(616)
for o in bpy.data.objects:
 if o.name.startswith('Overgrowth grass tuft') and -26<o.location.y<-14 and abs(o.location.x)<4:
  o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
leaf=bpy.data.materials['Natural foliage • veined olive green'];dry=bpy.data.materials.get('Natural foliage • tired ochre olive') or leaf
for i,(x,y) in enumerate([(-5.3,-24.2),(5.25,-24.15),(-5.4,-27.8),(5.35,-28.6),(-5.1,-20.8),(6.0,-18.7),(10.4,-22.7)]):
 p=Patch('Entrance verge natural patch %02d'%i,[leaf,dry,m['wood']])
 for j in range(5):
  xx=x+rng.uniform(-.33,.33);yy=y+rng.uniform(-.65,.65);fern(p,xx,yy,.55+rng.random()*.25)
 for j in range(7):grass(p,x+rng.uniform(-.42,.42),y+rng.uniform(-.8,.8),.6+rng.random()*.3)
 bramble(p,x,y,.6);p.finish()
 for j in range(4):
  xx=x+rng.uniform(-.4,.4);yy=y+rng.uniform(-.7,.7);o=cube('Entrance verge weathered timber fragment',(xx,yy,.055),(.035,rng.uniform(.12,.3),.018),'wood',.002);o.rotation_euler.z=rng.random()*math.tau
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
