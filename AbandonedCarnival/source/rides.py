"""Original, meter-scale abandoned carnival rides. Blender 4.x compatible."""
import bpy, bmesh, math, random
from mathutils import Vector
from math import sin, cos, pi

def build_rides(api):
    random.seed(341)
    cube,cyl,sphere,beam,torus = [api[k] for k in ('cube','cyl','sphere','beam','torus')]
    text=api['text']; m=api['mats']
    def mesh(name,verts,faces,mat,smooth=False):
        me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.materials.append(mat); me.update()
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();me.update()
        uv=me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            axis=max(range(3),key=lambda a:abs(poly.normal[a]));axes=[a for a in range(3) if a!=axis]
            for li in poly.loop_indices:
                co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]*.5,co[axes[1]]*.5)
        ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob)
        if smooth:
            for p in me.polygons:p.use_smooth=True
        return ob
    def curve(name,points,r,mat,cyclic=False):
        # Explicit swept mesh avoids evaluated-curve dependency graph conversion.
        pts=[Vector(p) for p in points];verts=[];faces=[];sides=8;n=len(pts)
        for i,p in enumerate(pts):
            tangent=(pts[(i+1)%n]-pts[(i-1)%n]) if cyclic else (pts[min(i+1,n-1)]-pts[max(0,i-1)])
            tangent.normalize();ref=Vector((0,0,1)) if abs(tangent.z)<.95 else Vector((0,1,0))
            u=tangent.cross(ref).normalized();v=tangent.cross(u).normalized()
            for j in range(sides):verts.append(tuple(p+r*(cos(j*2*pi/sides)*u+sin(j*2*pi/sides)*v)))
        for i in range(n if cyclic else n-1):
            for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%n)*sides+(j+1)%sides,((i+1)%n)*sides+j))
        if not cyclic:faces.extend([tuple(reversed(range(sides))),tuple((n-1)*sides+j for j in range(sides))])
        return mesh(name,verts,faces,mat,True)
    def ring(name,c,r,z,thick,mat,n=96):
        return curve(name,[(c[0]+r*cos(i*2*pi/n),c[1]+r*sin(i*2*pi/n),z) for i in range(n)],thick,mat,True)
    def ell(name,loc,scale,mat,rot=0):
        o=sphere(name,loc,scale,mat);o.rotation_euler[2]=rot;return o
    # Carousel foundation and radial boarded deck.
    cx,cy=0,8
    cyl('Carousel | cracked concrete footing',(cx,cy,.12),6.12,.24,m['concrete'],96)
    cyl('Carousel | lower steel step',(cx,cy,.30),5.98,.18,m['rust'],96)
    cyl('Carousel | upper step',(cx,cy,.46),5.68,.18,m['wood'],96)
    cyl('Carousel | turntable rim',(cx,cy,.62),5.35,.25,m['rust'],96)
    for j in range(72):
        a=2*pi*j/72;b=2*pi*(j+.96)/72
        mesh('Carousel | radial oak floor board',[(cx+r*cos(t),cy+r*sin(t),.76) for r,t in [(1.18,a),(5.3,a),(5.3,b),(1.18,b)]],[(0,1,2,3)],m['wood'])
    for r,z in [(5.97,.39),(5.67,.55),(5.33,.77),(5.30,.62)]:ring('Carousel | edge brass molding',(cx,cy),r,z,.035,m['gold'])
    cyl('Carousel | central drum',(cx,cy,2.44),1.28,3.38,m['cream'],24)
    for j in range(12):
        a=j*2*pi/12; x=cx+1.29*cos(a);y=cy+1.29*sin(a)
        o=cube('Carousel | antique mirrored drum panel',(x,y,2.4),(.59,.045,2.15),m['glass'],.035);o.rotation_euler[2]=a-pi/2
        for z in [1.23,3.55]:
            o=cube('Carousel | panel gilded border',(x*1.01,cy+(y-cy)*1.01,z),(.68,.065,.09),m['gold']);o.rotation_euler[2]=a-pi/2
        beam('Carousel | decorative drum stile',(1.32*cos(a+.23),cy+1.32*sin(a+.23),1.1),(1.32*cos(a+.23),cy+1.32*sin(a+.23),3.7),.042,m['red'])
    for z,r in [(1,1.36),(3.8,1.36),(4.2,1.48)]:cyl('Carousel | drum cornice',(cx,cy,z),r,.12,m['gold'],48)
    # Swept canopy fabric, radial seams, worn alternating canvas panels.
    count=24
    for j in range(count):
        a=j*2*pi/count;b=(j+1)*2*pi/count
        verts=[];radial=[(.28,7.12),(1.4,6.6),(3.0,5.9),(4.3,5.28),(5.55,4.92)]
        for r,z in radial:
            for t in [a,(a+b)/2,b]:verts.append((cx+r*cos(t),cy+r*sin(t),z-(.10 if t==(a+b)/2 and r>1 else 0)))
        faces=[]
        for k in range(4):
            for q in range(2):
                if j in (5,14) and k==3 and q==0:continue
                faces.append((k*3+q,k*3+q+1,(k+1)*3+q+1,(k+1)*3+q))
        mesh('Carousel | weathered canvas gore %02d'%j,verts,faces,m['cream'] if j%2 else m['red'])
        curve('Carousel | canopy stitched seam',[(cx+r*cos(a),cy+r*sin(a),z+.02) for r,z in radial],.019,m['rust'])
        beam('Carousel | radial canopy rib',(cx,cy,4.65),(cx+5.5*cos(a),cy+5.5*sin(a),4.86),.045,m['rust'])
    cyl('Carousel | crown collar',(cx,cy,7.15),.30,.26,m['gold'])
    sphere('Carousel | finial',(cx,cy,7.5),(.18,.18,.37),m['gold'])
    ring('Carousel | upper fascia frame',(cx,cy),5.52,4.91,.085,m['gold'])
    ring('Carousel | lower fascia frame',(cx,cy),5.52,4.35,.075,m['gold'])
    # Scalloped painted fascia with oval crest medallions and perimeter incandescent bulbs.
    for j in range(24):
        a=(j+.5)*2*pi/24;da=pi/24
        verts=[]
        for k in range(9):
            t=a-da+2*da*k/8
            verts.extend([(5.53*cos(t),cy+5.53*sin(t),4.91),(5.53*cos(t),cy+5.53*sin(t),4.40-.22*sin(pi*k/8))])
        mesh('Carousel | scalloped painted valance',verts,[(2*k,2*k+1,2*k+3,2*k+2) for k in range(8)],m['teal'] if j%2 else m['cream'])
        tangent=Vector((-sin(a),cos(a),0));n=Vector((cos(a),sin(a),0));c=Vector((5.58*cos(a),cy+5.58*sin(a),4.66))
        pts=[tuple(c+tangent*(.48*cos(t))+Vector((0,0,.21*sin(t)))) for t in [i*2*pi/32 for i in range(32)]]
        curve('Carousel | oval gilt medallion',pts,.042,m['gold'],True)
        sphere('Carousel | medallion jewel',tuple(c+n*.025),(.075,.075,.11),m['red'])
        for q in [-.39,-.2,0,.2,.39]:
            t=a+q/5.6;sphere('Carousel | marquee globe',(5.61*cos(t),cy+5.61*sin(t),4.32),(.055,.055,.055),m['bulb'])
    # Twelve richly assembled, posed carved wooden carousel horses.
    def horse(index,ang,r):
        center=Vector((cx+r*cos(ang),cy+r*sin(ang),1.95+(index%3)*.12));rot=ang+pi/2
        def p(v):return tuple(center+Vector((v[0]*cos(rot)-v[1]*sin(rot),v[0]*sin(rot)+v[1]*cos(rot),v[2])))
        def e(n,v,s,mat):return ell('Carousel horse %02d | '%index+n,p(v),s,mat,rot)
        def b(n,a,c,rad,mat):return beam('Carousel horse %02d | '%index+n,p(a),p(c),rad,mat)
        coat=m['cream'] if index%3 else m['wood']
        e('carved barrel',(0,0,0),(.68,.25,.32),coat)
        e('hindquarter',(-.46,0,.02),(.31,.28,.35),coat)
        neck=e('arched neck',(.47,0,.35),(.22,.21,.48),coat);neck.rotation_euler[1]=-.36
        e('head',(.68,0,.70),(.28,.18,.22),coat)
        e('long muzzle',(.88,0,.58),(.25,.16,.13),coat)
        for s in [-1,1]:
            e('ear',(.62,s*.12,.96),(.07,.045,.18),coat)
            e('glass eye',(.77,s*.17,.75),(.038,.023,.039),m['black'])
            e('nostril',(1.02,s*.13,.59),(.028,.025,.034),m['black'])
            # flexed knees and fetlocks in two distinct galloping poses
            for x,dx in [(-.43,-.25),(.45,.30)]:
                k=(x+dx,s*.20,-.43);foot=(x+dx+(.22 if x<0 else -.08),s*.20,-.78+(index%2)*.12)
                b('upper leg',(x,s*.17,-.12),k,.075,coat);e('knee',k,(.09,.085,.10),coat)
                b('shin',k,foot,.052,coat);e('dark carved hoof',(foot[0]+.03,foot[1],foot[2]-.055),(.13,.083,.08),m['black'])
            # Saddle flaps, stirrups, reins along cheeks
            e('leather saddle flap',(-.03,s*.26,.015),(.26,.035,.24),m['red'])
            b('stirrup leather',(-.05,s*.30,.05),(-.05,s*.33,-.34),.018,m['gold'])
            curve('Carousel horse | stirrup iron',[p((-.15,s*.33,-.32)),p((-.14,s*.33,-.47)),p((.06,s*.33,-.47)),p((.06,s*.33,-.32))],.016,m['rust'],True)
            curve('Carousel horse | leather rein',[p((.93,s*.17,.60)),p((.55,s*.28,.38)),p((.17,s*.29,.21))],.019,m['gold'])
        e('saddle seat',(-.05,0,.31),(.32,.27,.07),m['red']);e('saddle pommel',(.18,0,.37),(.09,.25,.10),m['gold'])
        for k in range(8):e('carved mane lock',(.33+k*.028,0,.20+k*.09),(.14,.23,.09),m['gold'] if index%2 else m['rust'])
        curve('Carousel horse | flowing tail',[p((-.62,0,.13)),p((-.85,0,.08)),p((-.96,0,-.23)),p((-.82,0,-.47))],.105,m['rust'])
        pole=(cx+r*cos(ang),cy+r*sin(ang))
        beam('Carousel | horse brass spindle',(*pole,.8),(*pole,4.75),.035,m['gold'])
        for z in [.98,3.48,4.0]:cyl('Carousel | spindle turned collar',(*pole,z),.065,.11,m['gold'],12)
    for j in range(12):horse(j,j*2*pi/12,3.85 if j%2==0 else 2.65)
    # Bumper arena, open north and south with structural steel and a fractured roof.
    print('Carousel built; beginning arena',flush=True)
    ax,ay=-17,12
    cube('Dodgems | foundation',(ax,ay,.17),(15.8,12.8,.34),m['concrete'],.1)
    for ix in range(5):
        for iy in range(4):cube('Dodgems | conductive steel floor panel',(ax-6+ix*3,ay-4.5+iy*3,.36),(2.97,2.97,.055),m['rust'],.008)
    for x in [-7.35,7.35]:
        for y in [-5.75,0,5.75]:
            cube('Dodgems | riveted steel column',(ax+x,ay+y,2.73),(.19,.24,4.78),m['rust'])
            cube('Dodgems | column base plate',(ax+x,ay+y,.48),(.48,.48,.08),m['rust'])
            for dx in [-.16,.16]:
                for dy in [-.16,.16]:cyl('Dodgems | anchor bolt',(ax+x+dx,ay+y+dy,.56),.036,.09,m['black'],6)
    # Gable trusses run along x at front, center and back. Roof pitch only .9m.
    for yy in [-6,0,6]:
        y=ay+yy
        beam('Dodgems | transverse lower truss',(ax-7.7,y,4.95),(ax+7.7,y,4.95),.085,m['rust'])
        for side in [-1,1]:
            beam('Dodgems | roof rafter',(ax,y,5.9),(ax+side*7.9,y,5.0),.095,m['rust'])
            for i in range(5):
                x0=ax+side*i*1.5;x1=ax+side*(i+1)*1.5
                beam('Dodgems | lattice diagonal',(x0,y,4.95),(x1,y,5.9-(i+1)*1.5*.9/7.9),.04,m['rust'])
    for xx in [-7.8,-4,0,4,7.8]:beam('Dodgems | longitudinal purlin',(ax+xx,ay-6.3,5.9-abs(xx)*.9/7.9),(ax+xx,ay+6.3,5.9-abs(xx)*.9/7.9),.06,m['rust'])
    # Individually corrugated metal sheets, deliberately missing patches preserve sightlines.
    for side in [-1,1]:
        for row in range(3):
            for col in range(10):
                if (side,row,col) in [(-1,1,3),(-1,1,4),(1,2,6),(1,0,4),(-1,0,8)]:continue
                verts=[];xstart=row*2.65;ya=ay-6.35+col*1.27
                for ix in range(2):
                    x=side*(xstart+ix*2.67)
                    for iy in range(17):
                        y=ya+iy*1.27/16;z=5.93-abs(x)*.9/7.9+(.027 if iy%2 else -.027)
                        if row==2 and col in [2,8]:z-=.13*(ix)*(iy/16)
                        verts.append((ax+x,y,z))
                mesh('Dodgems | corrugated roof sheet',verts,[(j,j+1,18+j,17+j) for j in range(16)],m['rust'] if (row+col)%3 else m['teal'])
    # Perimeter tubular guard rails with two generous walk-through gaps.
    for y in [ay-5.95,ay+5.95]:
        for x0,x1 in [(ax-7.1,ax-1.9),(ax+1.9,ax+7.1)]:
            for z in [.7,1.3]:beam('Dodgems | arena horizontal rail',(x0,y,z),(x1,y,z),.04,m['rust'])
            for i in range(5):beam('Dodgems | arena rail upright',(x0+(x1-x0)*i/4,y,.42),(x0+(x1-x0)*i/4,y,1.3),.035,m['rust'])
    for x in [ax-7.3,ax+7.3]:
        for z in [.7,1.3]:beam('Dodgems | side safety rail',(x,ay-5.9,z),(x,ay+5.9,z),.04,m['rust'])
        for i in range(9):beam('Dodgems | side rail upright',(x,ay-5.8+i*1.45,.42),(x,ay-5.8+i*1.45,1.3),.035,m['rust'])
    # Original oval bumper cars: lofted shell, separate rubber bumper, cockpit, seat, wheel, pole.
    car_groups=[]
    def car(index,x,y,angle,col):
        previous=set(bpy.data.objects)
        c=Vector((x,y,.42));ca,sa=cos(angle),sin(angle)
        def p(v):return tuple(c+Vector((v[0]*ca-v[1]*sa,v[0]*sa+v[1]*ca,v[2])))
        def e(n,v,s,mat):return ell('Dodgem %02d | '%index+n,p(v),s,mat,angle)
        def cb(n,v,s,mat,bevel=.03):
            o=cube('Dodgem %02d | '%index+n,p(v),s,mat,bevel);o.rotation_euler[2]=angle;return o
        def cr(n,pts,r,mat,cyclic=False):return curve('Dodgem %02d | '%index+n,[p(q) for q in pts],r,mat,cyclic)
        # Oval rubber belts form realistic inflated tire bumper profile.
        for z in [.19,.28]:cr('continuous rubber impact belt',[(1.24*cos(t),.76*sin(t),z) for t in [i*2*pi/64 for i in range(64)]],.105,m['black'],True)
        cr('chrome rub strip',[(1.20*cos(t),.74*sin(t),.39) for t in [i*2*pi/64 for i in range(64)]],.026,m['gold'],True)
        # Curved closed lower shell loft.
        verts=[]
        for rx,ry,z in [(1.13,.68,.28),(1.17,.69,.43),(1.02,.59,.61),(.89,.50,.68)]:
            for i in range(48):
                t=i*2*pi/48;verts.append(p((rx*cos(t),ry*sin(t),z)))
        faces=[tuple(range(47,-1,-1))]
        for j in range(3):
            for i in range(48):faces.append((j*48+i,j*48+(i+1)%48,(j+1)*48+(i+1)%48,(j+1)*48+i))
        mesh('Dodgem %02d | pressed steel body shell'%index,verts,faces,col,True)
        # Sculpted tapered hood at forward end; cockpit is visibly open at rear.
        e('rounded bonnet',(.59,0,.62),(.57,.55,.24),col)
        cb('black cockpit footwell',(-.34,0,.48),(1.08,.91,.11),m['black'],.12)
        e('rear cowl',(-.88,0,.65),(.22,.57,.23),col)
        for s in [-1,1]:
            cr('raised cockpit coaming',[(-.87,s*.46,.73),(-.48,s*.57,.72),(.07,s*.5,.67),(.30,s*.39,.72)],.065,col)
            e('inset headlamp',(1.02,s*.32,.62),(.065,.135,.075),m['cream'])
            cb('rear red lamp',(-1.075,s*.37,.53),(.04,.13,.07),m['red'])
        cb('bench seat cushion',(-.46,0,.64),(.60,.80,.15),m['black'],.12)
        o=cb('padded seat back',(-.78,0,.91),(.17,.84,.51),m['black'],.12);o.rotation_euler[1]=-.13
        for yy in [-.27,-.09,.09,.27]:cr('upholstery seam',[(-.67,yy,.74),(-.67,yy,1.09)],.009,m['wood'])
        beam('Dodgem | steering column',p((.25,0,.65)),p((.02,0,1.01)),.029,m['rust'])
        wheel=torus('Dodgem | steering wheel',p((.02,0,1.01)),.19,.024,m['black']);wheel.rotation_euler=(0,.6,angle)
        for j in range(3):
            t=j*2*pi/3;beam('Dodgem | steering wheel spoke',p((.02,0,1.01)),p((.02+.16*cos(t),.16*sin(t),1.01)),.012,m['rust'])
        beam('Dodgem | spring electric pickup pole',p((-.85,.13,.75)),p((-.93,.13,3.82)),.018,m['rust'])
        e('pickup pole insulated socket',(-.85,.13,.85),(.065,.065,.20),m['black'])
        cr('white bonnet pinstripe',[(1.1,0,.71),(.81,0,.85),(.51,0,.86),(.27,0,.76)],.015,m['cream'])
        for k in range(9):
            q=k/8;cr('bonnet cooling louvre',[(.45+q*.3,-.31,.80),(.45+q*.3,-.16,.85)],.012,m['rust'])
        # Each bumper car is a separately placed reusable gameplay prop.
        parts=[o for o in bpy.data.objects if o not in previous]
        car_groups.append((index,parts,c.copy()))

    placements=[(-4.5,-3.1,.3),(-1.3,-3.7,-.3),(2.2,-3.1,2.1),(4.6,-.3,2.8),(.5,.1,-1.2),(-3.9,1.3,.9),(1.9,3.4,-.4)]
    for j,(x,y,a) in enumerate(placements):car(j,ax+x,ay+y,a,[m['red'],m['gold'],m['teal']][j%3])
    from assemble_props import assemble
    for index,parts,origin in car_groups:
        print('Assembling bumper car',index,len(parts),flush=True)
        car_obj=assemble('BumperCar_%02d_Complete'%index,parts,origin,'BumperCar')
        car_obj['description']='Weathered oval dodgem with rubber bumper, open cockpit, seat, steering wheel and electrical pickup pole'
    # Hanging electric contact grid, sagged feeds, bulbs and south-facing sign.
    for i in range(9):beam('Dodgems | overhead power grid',(ax-6.8+i*1.7,ay-5.5,4.2),(ax-6.8+i*1.7,ay+5.5,4.2),.008,m['black'])
    for i in range(8):beam('Dodgems | cross power grid',(ax-7,ay-5.2+i*1.5,4.2),(ax+7,ay-5.2+i*1.5,4.2),.008,m['black'])
    for y in [ay-3,ay+3]:
        pts=[(ax-7+14*i/24,y,4.75-.55*sin(pi*i/24)) for i in range(25)]
        curve('Dodgems | sagged festoon cable',pts,.018,m['black'])
        for i in range(7):
            x=ax-6+i*2;z=4.75-.55*sin(pi*(x-ax+7)/14)
            beam('Dodgems | lamp drop',(x,y,z),(x,y,z-.17),.014,m['black']);sphere('Dodgems | surviving filament globe',(x,y,z-.24),(.07,.07,.10),m['bulb'])
    cube('Dodgems | faded sign board',(ax,ay-6.12,4.52),(5.8,.13,.67),m['teal'])
    text('Dodgems | front sign','BUMPER ARENA',(ax,ay-6.20,4.32),.48,m['cream'])
    for x in [-6.8,6.8]:
        cube('Dodgems | safety notice',(ax+x,ay-5.92,2.05),(.72,.07,.52),m['cream'])
        text('Dodgems | safety lettering','NO\nBUMPING',(ax+x,ay-5.98,2.12),.12,m['black'])
    # Tires and broken roof sheet lie at the edges, not in the pedestrian gateways.
    for j in range(14):
        x=ax-random.uniform(7.5,8.2);y=ay+random.uniform(-5.8,5.8)
        o=torus('Dodgems | discarded perimeter tire',(x,y,.30),.35,.11,m['black']);o.rotation_euler[0]=random.choice([0,.4,1.3])
    return {'carousel_center':(cx,cy),'arena_center':(ax,ay),'horse_count':12,'bumper_car_count':7}
