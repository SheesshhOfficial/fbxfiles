"""Cycle 6: localized pavement repairs, drainage erosion and compressed tire wear."""
import bpy,math,random,os,sys
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path.insert(0,R+'/source')
from fast_geometry import make_api

def apply():
 rng=random.Random(6006);m={x.name:x for x in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(m)
 def material(name,col,rough):
  q=bpy.data.materials.get(name) or bpy.data.materials.new(name);q.use_nodes=True;p=q.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;return q
 tar=material('Cycle06 damp tar seams',(.019,.023,.022),.42);rubber=material('Cycle06 worn tire rub',(.027,.032,.029),.88)
 repair=m['Scanned cracked paving'].copy();repair.name='Cycle06 asphalt patch aggregate';nt=repair.node_tree;p=nt.nodes.get('Principled BSDF');link=next((l for l in nt.links if l.to_socket==p.inputs['Base Color']),None)
 if link:
  src=link.from_socket;nt.links.remove(link);mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(.66,.70,.68,1);nt.links.new(src,mix.inputs[1]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
 created=[]
 def mesh(name,vs,fs,mat,tile=2.5):
  me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();uv=me.uv_layers.new(name='UVMap')
  for f in me.polygons:
   for li in f.loop_indices:
    v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v.x/tile,v.y/tile)
  o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o['decorative_no_collision']=True;o['refinement_cycle']=6;created.append(name);return o
 # Close-range review exposed faceted paper-like puddle outlines. Replace them
 # with low-frequency smooth contours and a damp, rough edge transition.
 wet=m['wetground'];wet.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.19
 margin=material('Cycle06 damp asphalt water margins',(.035,.043,.038),.58)
 for k,o in enumerate([o for o in bpy.data.objects if o.name.startswith('Art shallow puddle')]):
  old=o.data;pts=[v.co for v in old.vertices];cx=sum(v.x for v in pts[1:])/len(pts[1:]);cy=sum(v.y for v in pts[1:])/len(pts[1:]);rx=(max(v.x for v in pts)-min(v.x for v in pts))*.43;ry=(max(v.y for v in pts)-min(v.y for v in pts))*.43
  ring=[]
  for i in range(96):
   a=math.tau*i/96;r=1+.085*math.sin(a*3+k)+.045*math.sin(a*5+.7*k);ring.append((cx+rx*r*math.cos(a),cy+ry*r*math.sin(a),.0586))
  new=mesh('Cycle06 smooth shallow water outline %02d'%k,[(cx,cy,.0586)]+ring,[(0,i+1,(i+1)%96+1) for i in range(96)],wet,1)
  o.data=new.data;bpy.data.objects.remove(new,do_unlink=True);o['decorative_no_collision']=True
  vs=[];fs=[]
  for i in range(96):
   a=ring[i];b=ring[(i+1)%96];n=len(vs);vs.extend([(a[0],a[1],.0584),(b[0],b[1],.0584),(cx+(b[0]-cx)*1.045,cy+(b[1]-cy)*1.065,.0584),(cx+(a[0]-cx)*1.045,cy+(a[1]-cy)*1.065,.0584)]);fs.append((n,n+1,n+2,n+3))
  mesh('Cycle06 damp water margin %02d'%k,vs,fs,margin)
 # Irregular utility repairs are located at route edges, not an overall flagstone pattern.
 for k,(x,y,rx,ry,z) in enumerate([(-13,-18,1.05,.50,.059),(-7.1,-10,.65,1.15,.059),(-12.5,-3,.70,.45,.059),(4.8,-24.6,.60,.80,.014),(-4.8,-27.4,.55,1.10,.014),(9.9,-22.7,.48,.75,.014)]):
  ring=[]
  for i in range(28):
   a=math.tau*i/28;radius=rng.uniform(.90,1.08);ring.append((x+rx*math.cos(a)*radius,y+ry*math.sin(a)*radius,z))
  mesh('Cycle06 patched asphalt %02d'%k,[(x,y,z)]+ring,[(0,i+1,(i+1)%28+1) for i in range(28)],repair)
  vs=[];fs=[]
  for i,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
   ix=len(vs);va=((a[0]-x)*.987+x,(a[1]-y)*.987+y,z+.001);vb=((b[0]-x)*.987+x,(b[1]-y)*.987+y,z+.001);vs.extend([(a[0],a[1],z+.001),(b[0],b[1],z+.001),vb,va]);fs.append((ix,ix+1,ix+2,ix+3))
  mesh('Cycle06 hand-sealed repair seam %02d'%k,vs,fs,tar)
 # A few broken-up tire scuffs suggest maintenance access without adding obstacles.
 for k,(x,y) in enumerate([(3.9,-25.2),(-3.7,-27.0),(10.7,-10.2)]):
  vs=[];fs=[]
  for side in (-1,1):
   for j in range(22):
    if rng.random()<.22:continue
    yy=y+j*.075;xx=x+side*.46+.035*math.sin(j*.11);w=.06+rng.random()*.025;n=len(vs);vs.extend([(xx-w,yy,.016),(xx+w,yy,.016),(xx+w,yy+.025,.016),(xx-w,yy+.025,.016)]);fs.append((n,n+1,n+2,n+3))
  mesh('Cycle06 broken tire contact scuffs %02d'%k,vs,fs,rubber)
 # Low grit and timber splinters collect under structure edges, clear of the central gate strip.
 for k,(x,y) in enumerate([(-5.2,-24.7),(5.3,-24.1),(10.2,-22.2),(10.1,-19.7),(-15.9,-17.0),(-4.2,-16.8)]):
  for j in range(16):
   xx=x+rng.uniform(-.25,.25);yy=y+rng.uniform(-.6,.6);h=rng.uniform(.012,.035)
   o=cube('Cycle06 accumulated edge aggregate',(xx,yy,.012+h/2),(rng.uniform(.025,.09),rng.uniform(.025,.07),h),'ground',0);o.rotation_euler.z=rng.random()*math.tau;o['decorative_no_collision']=True
 return {'change':'Five smoother shallow-water contours with damp margins and rougher reflections; six irregular asphalt repairs with narrow sealed seams, three interrupted tire-wear trails and six localized drainage/structure-edge aggregate banks.','custom_meshes':len(created),'eligible_props_changed':0,'route_note':'All marks are non-colliding shallow surfaces; aggregate is confined to edges outside central gate strip.','material_note':'Asphalt patch uses source scanned image with tint modulation; target-engine material equivalent needs review.'}
