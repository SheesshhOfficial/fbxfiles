import bpy,math
from math import sin,cos,pi
from mathutils import Vector
CACHE={}
def make_api(mats):
 def mat(m):return mats[m] if isinstance(m,str) else m
 def mesh(n,verts,faces,loc,material,smooth=False,key=None):
  if key and key in CACHE:me=CACHE[key]
  else:
   me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.materials.append(mat(material));me.update();uv=me.uv_layers.new(name='UVMap')
   for p in me.polygons:
    axis=max(range(3),key=lambda a:abs(p.normal[a])); axes=[a for a in range(3) if a!=axis]
    for li in p.loop_indices:
     v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
    p.use_smooth=smooth
   if key:CACHE[key]=me
  o=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(o);o.location=loc;return o
 def cube(n,loc,scale,material,bevel=.03):
  x,y,z=[v/2 for v in scale];vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)];fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
  o=mesh(n,vs,fs,loc,material,key=('cube',tuple(scale),mat(material).name))
  if bevel:
   b=o.modifiers.new('Edge wear bevel','BEVEL');b.width=bevel;b.segments=2;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
  return o
 def cyl(n,loc,radius,depth,material,vertices=32):
  vs=[(radius*cos(2*pi*i/vertices),radius*sin(2*pi*i/vertices),z) for z in [-depth/2,depth/2] for i in range(vertices)];fs=[tuple(reversed(range(vertices))),tuple(range(vertices,2*vertices))]+[(i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices)]
  return mesh(n,vs,fs,loc,material,key=('cyl',radius,depth,vertices,mat(material).name))
 def sphere(n,loc,scale,material):
  seg=16;rows=8;vs=[(scale[0]*sin(pi*j/rows)*cos(2*pi*i/seg),scale[1]*sin(pi*j/rows)*sin(2*pi*i/seg),scale[2]*cos(pi*j/rows)) for j in range(rows+1) for i in range(seg)];fs=[]
  for j in range(rows):
   for i in range(seg):fs.append(((j+1)*seg+i,(j+1)*seg+(i+1)%seg,j*seg+(i+1)%seg,j*seg+i))
  return mesh(n,vs,fs,loc,material,True,key=('sphere',tuple(scale),mat(material).name))
 def beam(n,a,b,r,material):
  a,b=Vector(a),Vector(b);o=cyl(n,(a+b)/2,r,(b-a).length,material,12);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
 def torus(n,loc,major,minor,material):
  vs=[((major+minor*cos(2*pi*j/8))*cos(2*pi*i/24),(major+minor*cos(2*pi*j/8))*sin(2*pi*i/24),minor*sin(2*pi*j/8)) for i in range(24) for j in range(8)];fs=[(i*8+j,((i+1)%24)*8+j,((i+1)%24)*8+(j+1)%8,i*8+(j+1)%8) for i in range(24) for j in range(8)]
  return mesh(n,vs,fs,loc,material,True,key=('torus',major,minor,mat(material).name))
 return cube,cyl,sphere,beam,torus
