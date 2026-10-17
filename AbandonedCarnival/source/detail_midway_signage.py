import bpy,os,math,sys
from mathutils import Vector,Matrix
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source');from fast_geometry import make_api
m={mat.name:mat for mat in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m)
font=bpy.data.fonts.load(R+'/assets/fonts/DejaVuSerif-Bold.ttf')
for o in bpy.data.objects:
 if o.type=='FONT' and ('Midway' in o.name or 'Entrance name lettering' in o.name):o.data.font=font
font.pack()
def txt(n,body,p,size,mat,angle):
 cu=bpy.data.curves.new(n,'FONT');cu.body=body;cu.align_x='CENTER';cu.align_y='CENTER';cu.size=size;cu.space_line=1.15;cu.extrude=.0005;cu.font=font;o=bpy.data.objects.new(n,cu);bpy.context.collection.objects.link(o);o.location=p;o.rotation_euler=(math.pi/2,0,angle);cu.materials.append(m[mat]);return o
for label,x,y,a,body in [('RING TOSS',-18,-15,math.pi/2,'3 THROWS\n1 TICKET'),('BALL TOSS',-18,-9,math.pi/2,'KNOCK THEM\nALL DOWN'),('CANDY FLOSS',-2,-15,-math.pi/2,'FRESH\nCANDY FLOSS')]:
 T=Matrix.Translation((x,y,0))@Matrix.Rotation(a,4,'Z')
 def p(co):return T@Vector(co)
 # Counter-mounted distressed instruction plate, attached with four rivets.
 o=cube('Instruction plate '+label,p((1.4,-1.49,.78)),(.72,.035,.58),'paper',.008);o.rotation_euler.z=a
 txt('Instruction lettering '+label,body,p((1.4,-1.515,.78)),.105,'black',a)
 for dx in [-.31,.31]:
  for dz in [-.25,.25]:sphere('Instruction plate rivet',p((1.4+dx,-1.525,.78+dz)),(.012,.012,.012),'rust')
 # A-frame chalk sign on service edge; true braced support.
 pos=p((-1.3,-2.1,.67));o=cube('Chalkboard '+label,pos,(.62,.045,.88),'black',.02);o.rotation_euler=(0,0,a)
 for dx in [-.34,.34]:
  beam('Chalk sign front timber',p((-1.3+dx,-2.1,.08)),p((-1.3+dx,-2.1,1.18)),.025,'wood')
  beam('Chalk sign rear prop',p((-1.3+dx,-1.75,.08)),p((-1.3+dx,-2.1,1.08)),.025,'wood')
 txt('Chalk sign letters '+label,'TRY\nYOUR\nLUCK',p((-1.3,-2.132,.72)),.115,'cream',a)
# Correct bottle optical material.
p=bpy.data.materials['glass'].node_tree.nodes.get('Principled BSDF');p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.21;p.inputs['Transmission Weight'].default_value=.55;p.inputs['IOR'].default_value=1.45
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Fine signage saved')
