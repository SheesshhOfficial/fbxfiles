import bpy,os,sys,math
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source');from fast_geometry import make_api
m={q.name:q for q in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m)
for o in bpy.data.objects:
 if o.name.startswith(('Dodgems | safety notice','Dodgems | safety lettering')):o.hide_render=True;o.hide_set(True);o['visual_replaced']=True
for x in [-23.8,-10.2]:
 board=cube('Arena safety thin enamel sign',(x,6.08,2.05),(.95,.018,.52),'PaintCream',.004);board.data=board.data.copy()
 for v in board.data.uv_layers.active.data:v.uv/=.8
 for xx in [x-.32,x+.32]:
  beam('Arena safety sign steel support',(xx,6.14,.45),(xx,6.14,2.3),.02,'rust')
  for z in [1.84,2.26]:
   r=cyl('Arena safety sign bolt',(xx,6.062,z),.012,.014,'black',10);r.rotation_euler.x=math.pi/2
 cu=bpy.data.curves.new('No head-on collisions lettering','FONT');cu.body='NO HEAD-ON\nCOLLISIONS';cu.align_x='CENTER';cu.size=.093;cu.space_line=1.15;cu.extrude=0
 ob=bpy.data.objects.new('Arena safety lettering',cu);bpy.context.collection.objects.link(ob);ob.location=(x,6.065,2.13);ob.rotation_euler=(math.pi/2,0,0);cu.materials.append(m['black'])
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
