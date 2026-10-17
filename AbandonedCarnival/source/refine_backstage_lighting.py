import bpy,os,sys,math
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source')
from fast_geometry import make_api
m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m)
for name,x,y,side,power in [('A',14.02,-5.45,1,65),('B',19.28,-4.85,-1,45)]:
 cube('Backstage porch lamp '+name+' mounting plate',(x,y,3.18),(.06,.28,.4),'rust',.015)
 cube('Backstage porch lamp '+name+' luminous pane',(x+side*.08,y,3.18),(.09,.20,.28),'bulb',.015)
 for yy in [y-.13,y+.13]:beam('Backstage porch lamp guard',(x+side*.15,yy,3.0),(x+side*.15,yy,3.37),.012,'rust')
 for zz in [3,3.37]:beam('Backstage porch lamp guard',(x+side*.15,y-.13,zz),(x+side*.15,y+.13,zz),.012,'rust')
 ld=bpy.data.lights.new('Backstage porch practical '+name,'POINT');ld.energy=power;ld.color=(1,.52,.23);ld.shadow_soft_size=.22;ob=bpy.data.objects.new(ld.name,ld);bpy.context.collection.objects.link(ob);ob.location=(x+side*.3,y,3.08)
from refine_backstage_funhouse import repair_backstage_container_collision_seams
print(repair_backstage_container_collision_seams())
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
