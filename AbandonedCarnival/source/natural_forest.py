"""Irregular temperate broadleaf woodland. add_natural_forest() edits only, never saves.
30 rooted trees with UV bark, bent tapered limbs and folded, veined leaf meshes.
Hero west/north crowns use 600 small leaves per lobe, background crowns 180.
Leaf subsurface weight 0.08 is a Blender source-only light-transport refinement;
portable exports retain the diffuse veined texture and folded leaf geometry.
Existing boundary trees are preserved, hidden and marked visual_replaced.
"""
import bpy, math, random, os, sys
from mathutils import Vector
from math import sin, cos, pi
sys.path.insert(0,os.path.dirname(__file__))
from natural_vegetation import leaf_material

class Mesh:
    def __init__(self,name,mats): self.name=name; self.v=[]; self.f=[]; self.uv=[]; self.mi=[]; self.mats=mats
    def face(self,vs,uv,mat=0):
        n=len(self.v); self.v.extend(tuple(v) for v in vs);self.f.append(tuple(range(n,n+len(vs))));self.uv.extend(uv);self.mi.append(mat)
    def tube(self,pts,radii,sides=8):
        rings=[]
        for i,(p,r) in enumerate(zip(pts,radii)):
            d=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized();u=d.cross(Vector((0,1,0))).normalized();w=d.cross(u)
            rings.append([p+r*(u*cos(2*pi*k/sides)+w*sin(2*pi*k/sides))*(1+.08*sin(k*7+i)) for k in range(sides)])
        for j in range(len(rings)-1):
            for k in range(sides): self.face([rings[j][k],rings[j][(k+1)%sides],rings[j+1][(k+1)%sides],rings[j+1][k]],[(k/sides,j*.4),((k+1)/sides,j*.4),((k+1)/sides,(j+1)*.4),(k/sides,(j+1)*.4)])
    def leaf(self,p,d,L,W,roll,mat):
        d=d.normalized();s=d.cross(Vector((0,0,1)))
        if s.length<.01:s=Vector((1,0,0))
        s.normalize();n=s.cross(d).normalized();s=s*cos(roll)+n*sin(roll);n=s.cross(d).normalized()
        # Six-triangle pointed lamina: small botanical scale, curved raised midrib.
        verts=[p,p+d*L*.34-s*W*.45,p+d*L*.68-s*W*.46,p+d*L,p+d*L*.68+s*W*.46,p+d*L*.34+s*W*.45]
        uv=[(.5,0),(.05,.34),(.04,.68),(.5,1),(.96,.68),(.95,.34)]
        c=p+d*L*.52+n*L*.085
        for k in range(6): self.face([verts[k],verts[(k+1)%6],c],[uv[k],uv[(k+1)%6],(.5,.52)],mat)
    def finish(self):
        me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update();ob=bpy.data.objects.new(self.name,me);bpy.context.collection.objects.link(ob)
        for m in self.mats:me.materials.append(m)
        uv=me.uv_layers.new(name='NaturalUV');uv.data.foreach_set('uv',[c for pair in self.uv for c in pair])
        for p,m in zip(me.polygons,self.mi):p.material_index=m;p.use_smooth=True
        ob['ArtPass']='Natural boundary woodland';return ob

def add_natural_forest():
    rng=random.Random(17389)
    for ob in list(bpy.data.objects):
        if ob.name.startswith(('Boundary tree trunk','Tree branch','Tree canopy','Dense forest crown')):
            ob.hide_render=True;ob.hide_set(True);ob['visual_replaced']=True
        if ob.name.startswith('Natural forest |'):bpy.data.objects.remove(ob,do_unlink=True)
    base=leaf_material();mats=[base]
    for name,tint in [('Forest leaf • deep green',(.48,.68,.38,1)),('Forest leaf • warm olive',(.9,.83,.45,1)),('Forest leaf • sage light',(.75,.96,.66,1))]:
        m=bpy.data.materials.get(name)
        if not m:
            m=base.copy();m.name=name;nt=m.node_tree;p=nt.nodes.get('Principled BSDF');tx=next(n for n in nt.nodes if n.type=='TEX_IMAGE');mul=nt.nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=tint;nt.links.new(tx.outputs['Color'],mul.inputs[1]);nt.links.new(mul.outputs[0],p.inputs['Base Color'])
        mats.append(m)
    # Thin lamina response under sun / festoon lights, source renderer refinement.
    for material in mats:
        shader=material.node_tree.nodes.get('Principled BSDF')
        if shader and 'Subsurface Weight' in shader.inputs:
            shader.inputs['Subsurface Weight'].default_value=.08
            shader.inputs['Subsurface Radius'].default_value=(.25,.45,.15)
    bark=bpy.data.materials.get('wood')
    if bark is None:
        bark=bpy.data.materials.new('Forest bark');bark.diffuse_color=(.13,.09,.055,1)
    positions=[]
    for side in [-1,1]:
        for i in range(8):positions.append((side*rng.uniform(29.2,33.2),-23+i*6.8+rng.uniform(-1.2,1.2)))
    for i in range(7):positions.append((-25+i*8.2+rng.uniform(-1,1),rng.uniform(30,35.5)))
    for i in range(7):positions.append((-25+i*8.2+rng.uniform(-1,1),rng.uniform(-39,-35)))
    out=[]
    for ti,(x,y) in enumerate(positions):
        wood=Mesh('Natural forest | %02d bent trunk and branches'%ti,[bark]);leaves=Mesh('Natural forest | %02d dense broadleaf crown'%ti,mats)
        h=rng.uniform(8.4,14.8);r=rng.uniform(.28,.51);bend=Vector((rng.uniform(-.85,.85),rng.uniform(-.85,.85),0));root=Vector((x,y,-.19))
        pts=[root+Vector((0,0,h*t))+bend*t*t+Vector((.18*sin(t*8),.15*sin(t*7),0)) for t in [0,.1,.26,.43,.6,.77,.92,1]]
        wood.tube(pts,[r*1.65,r,r*.83,r*.68,r*.53,r*.35,r*.18,.025],10)
        for j in range(5):
            a=rng.random()*2*pi;end=root+Vector((cos(a)*r*3,sin(a)*r*3,.03));wood.tube([end,root+Vector((0,0,.6))],[.04,r*.55],6)
        hero=(x < -28 or y > 28)
        leaves_per_lobe=600 if hero else 180
        for bi in range(14):
            angle=bi*2.399+rng.uniform(-.4,.4);start=pts[3+bi%4];spread=rng.uniform(1.8,3.8);rise=rng.uniform(.7,2.5);d=Vector((cos(angle),sin(angle),0));end=start+d*spread+Vector((0,0,rise))
            elbow=start+d*spread*.42+Vector((0,0,rise*.7));wood.tube([start,elbow,end],[r*.4,r*.18,.018],7)
            for twig in range(3):
                a=angle+rng.uniform(-1,1);tip=end+Vector((cos(a)*rng.uniform(.5,1.2),sin(a)*rng.uniform(.5,1.2),rng.uniform(.15,.8)));wood.tube([elbow.lerp(end,.6),end,tip],[.065,.035,.007],5)
            # Overlapping, uneven ellipsoidal clusters obscure branch tips without spherical shells.
            scale=rng.uniform(.85,1.25);center=end+Vector((0,0,.35));rad=Vector((1.25*scale,1.14*scale,1.05*scale))
            for li in range(leaves_per_lobe):
                a=rng.random()*2*pi;z=rng.uniform(-1,1);q=math.sqrt(1-z*z);rr=rng.random()**.38
                offset=Vector((q*cos(a)*rad.x,q*sin(a)*rad.y,z*rad.z))*rr;pos=center+offset
                direct=Vector((cos(a+rng.uniform(-1,1)),sin(a+rng.uniform(-1,1)),rng.uniform(-.7,.6)))
                L=rng.uniform(.10,.22);leaves.leaf(pos,direct,L,L*rng.uniform(.4,.64),rng.uniform(-pi,pi),rng.choices([0,1,2,3],[5,3,1,1])[0])
        a=wood.finish();a['RootPosition']=(x,y,-.19);a['TreeHeight']=h;a['CrownLOD']='Hero 600 leaves per lobe' if hero else 'Background 180 leaves per lobe';out.extend([a,leaves.finish()])
        # Small rooted elder/bramble plants break the fence-base line and forest floor.
        shrubs=Mesh('Natural forest | %02d rooted understory'%ti,mats);stems=Mesh('Natural forest | %02d understory stems'%ti,[bark])
        for sh in range(3):
            sx=x+rng.uniform(-2,2);sy=y+rng.uniform(-2,2);basep=Vector((sx,sy,-.18));height=rng.uniform(.9,2.0)
            for bi in range(5):
                ang=bi*2.4;top=basep+Vector((cos(ang)*.7,sin(ang)*.7,height*rng.uniform(.65,1)));stems.tube([basep,basep.lerp(top,.5),top],[.035,.019,.004],5)
                for li in range(10):
                    pos=basep.lerp(top,rng.uniform(.4,1))+Vector((rng.uniform(-.3,.3),rng.uniform(-.3,.3),rng.uniform(-.1,.2)));L=rng.uniform(.18,.34);shrubs.leaf(pos,Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-.2,.6))),L,L*.58,rng.uniform(-1,1),rng.randrange(4))
        out.extend([shrubs.finish(),stems.finish()])
    return out
