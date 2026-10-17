"""Natural, UV-mapped midway edge vegetation. Invoke add_natural_vegetation(); does not save.
Coverage: left edge x -16.3..-14.1, right edge -5.9..-3.8, y -21..2;
additional stall-post ivy and boundary understory x -24.7. Aisle -13..-7 clear.
"""
import bpy, math, random, os
from mathutils import Vector
from math import sin, cos, pi
R=random.Random(4721)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def leaf_material():
    name='Natural foliage • veined olive green'
    m=bpy.data.materials.get(name)
    if m:return m
    # Portable image map: folded lamina, central vein, secondary veins, mottled chlorophyll.
    size=256; pixels=[]; rr=random.Random(46)
    for y in range(size):
        v=y/(size-1)
        for x in range(size):
            u=x/(size-1); mid=abs(u-.5)
            vein=math.exp(-mid*150)*.16
            side=math.exp(-abs(((v-mid*.63)*12)%1-.5)*60)*.045
            mott=.018*sin(u*76+sin(v*33)*2)+.012*sin(v*69+u*21)+rr.uniform(-.009,.009)
            tone=.07+vein+side+mott+.035*(1-mid*2)
            pixels.extend((tone*.72,tone*1.12,tone*.38,1))
    im=bpy.data.images.new('Natural_leaf_veins_basecolor',width=size,height=size)
    im.pixels.foreach_set(pixels); im.filepath_raw=ROOT+'/textures/natural_leaf_veins.png'; im.file_format='PNG'; im.save()
    m=bpy.data.materials.new(name); m.use_nodes=True
    nt=m.node_tree; p=nt.nodes.get('Principled BSDF'); p.inputs['Roughness'].default_value=.79
    tx=nt.nodes.new('ShaderNodeTexImage'); tx.image=im; nt.links.new(tx.outputs['Color'],p.inputs['Base Color'])
    # Image-driven relief, retained in Blender; UV diffuse map remains export portable.
    bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.18; bump.inputs['Distance'].default_value=.012
    nt.links.new(tx.outputs['Color'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m

class Patch:
    def __init__(self,name,materials):self.name=name;self.v=[];self.f=[];self.uv=[];self.mi=[];self.materials=materials
    def face(self,coords,uv,mat=0):
        n=len(self.v);self.v.extend(tuple(p) for p in coords);self.f.append(tuple(range(n,n+len(coords))));self.uv.extend(uv);self.mi.append(mat)
    def tube(self,points,r=.008,mat=2,sides=4):
        for a,b in zip(points,points[1:]):
            a,b=Vector(a),Vector(b); d=(b-a).normalized(); u=d.cross(Vector((0,0,1)))
            if u.length<.01:u=d.cross(Vector((0,1,0)))
            u.normalize();w=d.cross(u)
            for k in range(sides):
                q=2*pi*k/sides;q2=2*pi*(k+1)/sides
                da=(u*cos(q)+w*sin(q))*r; db=(u*cos(q2)+w*sin(q2))*r
                self.face([a+da,b+da,b+db,a+db],[(0,0),(0,1),(1,1),(1,0)],mat)
    def leaf(self,base,direction,length,width,roll=0,mat=0,sections=5):
        a=Vector(base); d=Vector(direction).normalized(); side=d.cross(Vector((0,0,1)))
        if side.length<.02:side=Vector((1,0,0))
        side.normalize(); normal=side.cross(d).normalized(); side=side*cos(roll)+normal*sin(roll); normal=side.cross(d).normalized()
        rows=[]
        for i in range(sections+1):
            t=i/sections; w=width*(sin(pi*t)**.75)*(.94+.06*sin(t*31))
            c=a+d*(t*length)+normal*(sin(t*pi)*length*.085)-Vector((0,0,t*t*length*.14))
            rows.append([c-side*w/2-normal*w*.11,c+normal*w*.06,c+side*w/2-normal*w*.11])
        for i in range(sections):
            for j in range(2):
                self.face([rows[i][j],rows[i+1][j],rows[i+1][j+1],rows[i][j+1]],[(j/2,i/sections),(j/2,(i+1)/sections),((j+1)/2,(i+1)/sections),((j+1)/2,i/sections)],mat)
    def finish(self):
        mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.v,[],self.f);mesh.update()
        obj=bpy.data.objects.new(self.name,mesh);bpy.context.collection.objects.link(obj)
        for m in self.materials:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='LeafUV')
        for i,co in enumerate(self.uv):uv.data[i].uv=co
        for poly,mi in zip(mesh.polygons,self.mi):poly.material_index=mi;poly.use_smooth=True
        obj['VegetationType']='Grounded natural foliage';obj['Geometry']='Curved UV leaves, paired fern pinnae, arching grass, woody stems'
        return obj

def fern(p,x,y,scale=1):
    z=.07
    for fr in range(R.randint(5,7)):
        theta=fr*2*pi/7+R.uniform(-.25,.25); dr=Vector((cos(theta),sin(theta),0)); side=Vector((-sin(theta),cos(theta),0))
        length=R.uniform(.55,.95)*scale; rise=R.uniform(.35,.56)*scale
        def at(t):return Vector((x,y,z))+dr*(length*t)+Vector((0,0,rise*sin(t*pi*.78)))
        p.tube([at(i/9) for i in range(10)],.006*scale)
        for j in range(1,11):
            t=j/11; pos=at(t); ln=(sin(t*pi)**.7)*length*.24
            for s in [-1,1]:
                direction=(side*s+dr*.32+Vector((0,0,.12-t*.3))).normalized()
                p.leaf(pos,direction,ln,ln*.25,R.uniform(-.2,.2),R.choice([0,0,1]),4)

def grass(p,x,y,scale=1):
    for k in range(R.randint(15,25)):
        theta=R.random()*2*pi;dr=Vector((cos(theta),sin(theta),0));side=Vector((-sin(theta),cos(theta),0));h=R.uniform(.2,.68)*scale
        a=Vector((x+R.uniform(-.1,.1),y+R.uniform(-.1,.1),.065)); rows=[]
        for i in range(7):
            t=i/6;c=a+dr*(h*.65*t*t)+Vector((0,0,h*(t-.35*t*t)))
            w=.016*scale*(1-t)**.6;rows.append((c-side*w,c+side*w))
        for i in range(6):p.face([rows[i][0],rows[i+1][0],rows[i+1][1],rows[i][1]],[(0,i/6),(0,(i+1)/6),(1,(i+1)/6),(1,i/6)],R.choice([0,1,1]))

def bramble(p,x,y,scale=1):
    for branch in range(4):
        theta=R.random()*2*pi;dr=Vector((cos(theta),sin(theta),0));length=R.uniform(.4,.8)*scale
        pts=[Vector((x,y,.06))+dr*length*t+Vector((0,0,scale*(.12+.42*sin(t*pi*.8)))) for t in [0,.2,.4,.6,.8,1]]
        pts[0].z=.06;p.tube(pts,.009*scale)
        for j in range(1,6):
            for s in [-1,1]:
                side=Vector((-dr.y*s,dr.x*s,.2)); pos=pts[j]
                p.leaf(pos,side+dr*.23,R.uniform(.13,.24)*scale,R.uniform(.07,.12)*scale,R.uniform(-.45,.45),R.choice([0,0,1]),6)

def ivy(p,x,y,height,side=1):
    # Roots at ground, stems clinging to front corner post. Foliage never floats.
    for n in range(3):
        pts=[]
        for i in range(15):
            t=i/14;pts.append(Vector((x+side*(.025+.07*sin(t*13+n)),y+.11*sin(t*9+n),.06+t*height)))
        p.tube(pts,.011)
        for j,pos in enumerate(pts[1:]):
            dr=Vector((side*.45,(-1 if j%2 else 1),-.25))
            ln=R.uniform(.15,.25);end=pos+dr*.09;p.tube([pos,end],.004)
            p.leaf(end,dr,ln,ln*.67,R.uniform(-.4,.4),0,6)

def add_natural_vegetation():
    # Idempotent only for this pass; leave earlier landscape available to caller cleanup.
    for o in list(bpy.data.objects):
        if o.name.startswith('Natural foliage |'):bpy.data.objects.remove(o,do_unlink=True)
    R.seed(4721); mat=leaf_material(); dry=mat.copy();dry.name='Natural foliage • tired ochre olive'
    # Color variation is a UV offset into detailed veined map, plus a restrained olive tint.
    nt=dry.node_tree;p=nt.nodes.get('Principled BSDF');tx=next(n for n in nt.nodes if n.type=='TEX_IMAGE')
    mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.65;mix.inputs[2].default_value=(1.3,.95,.54,1);nt.links.new(tx.outputs['Color'],mix.inputs[1]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
    wood=bpy.data.materials.get('wood') or mat; mats=[mat,dry,wood];result=[]
    for bank,xlim in [('left',(-16.1,-14.3)),('right',(-5.7,-4.1))]:
        for segment in range(5):
            p=Patch('Natural foliage | '+bank+' edge '+str(segment+1),mats);yc=-19+segment*4.4
            for j in range(5):
                x=R.uniform(*xlim);y=yc+R.uniform(-1.8,1.8);fern(p,x,y,R.uniform(.65,1.05))
            for j in range(12):grass(p,R.uniform(*xlim),yc+R.uniform(-2,2),R.uniform(.6,1.1))
            for j in range(4):bramble(p,R.uniform(*xlim),yc+R.uniform(-1.8,1.8),R.uniform(.55,1))
            result.append(p.finish())
    # Front corner posts on inward-facing stalls (counter line at x +-1.4 from center).
    for bank,x,side,ys in [('left',-16.6,1,[-17,-13,-11,-7,-5,-1]),('right',-3.4,-1,[-17,-13,-11,-7])]:
        p=Patch('Natural foliage | '+bank+' grounded post ivy',mats)
        for y in ys:
            ivy(p,x,y,R.uniform(1.8,3.1),side);bramble(p,x,y,.85)
        result.append(p.finish())
    for seg in range(4):
        p=Patch('Natural foliage | boundary understory '+str(seg+1),mats)
        for j in range(4):
            y=-20+seg*6+R.uniform(-2,2);x=R.uniform(-24.9,-23.7)
            bramble(p,x,y,1.65);fern(p,x,y,1.1);grass(p,x,y,1.1)
        result.append(p.finish())
    tri=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in result)
    print('NATURAL_VEGETATION',len(result),'mesh patches;',tri,'triangles; aisle x[-13,-7] kept clear',flush=True)
    return result

if __name__=='__main__':add_natural_vegetation()
