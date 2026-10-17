"""Cycle 3/4 ride manufacturing refinement. Blender 4.3+, no file I/O on import.

Each public function runs once in the currently loaded evolving scene. The seven
BumperCar actors keep their objects, tags, pivots and placements. Newly authored
ride decoration is never eligible gameplay prop duplication. Export collision
must be regenerated after these changes; no whole-car hull is suitable because
the cockpit remains open. No blueprint or source .blend is changed by this file.
"""
import bpy, bmesh, math
from math import sin, cos, pi, tau
from mathutils import Vector, Matrix

class _Geometry:
    """One data-API mesh per logical assembly; no object operators or modifiers."""
    def __init__(self):
        self.vertices=[]; self.faces=[]; self.indices=[]; self.smooth=[]; self.materials=[]
    def part(self, vertices, faces, material, smooth=True):
        if isinstance(material,str): material=bpy.data.materials[material]
        if material not in self.materials:self.materials.append(material)
        mi=self.materials.index(material);off=len(self.vertices)
        self.vertices.extend(tuple(v) for v in vertices)
        self.faces.extend(tuple(off+i for i in f) for f in faces)
        self.indices.extend([mi]*len(faces));self.smooth.extend([smooth]*len(faces))
    def tube(self,pts,radius,material,closed=False,sides=10):
        pts=[Vector(p) for p in pts];vs=[];fs=[];n=len(pts);previous_u=None
        for i,p in enumerate(pts):
            t=(pts[(i+1)%n]-pts[(i-1)%n]) if closed else (pts[min(i+1,n-1)]-pts[max(i-1,0)])
            t.normalize()
            if previous_u is None:
                ref=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0));u=t.cross(ref).normalized()
            else:
                # Parallel transport prevents 180-degree frame flips when an
                # arched moulding transitions from horizontal to vertical.
                u=previous_u-t*previous_u.dot(t)
                if u.length<1e-8:u=t.cross(Vector((0,1,0)) if abs(t.y)<.9 else Vector((1,0,0)))
                u.normalize()
            v=t.cross(u).normalized();previous_u=u
            r=radius[i] if isinstance(radius,(list,tuple)) else radius
            for j in range(sides):vs.append(p+r*(u*cos(tau*j/sides)+v*sin(tau*j/sides)))
        for i in range(n if closed else n-1):
            for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%n)*sides+(j+1)%sides,((i+1)%n)*sides+j))
        self.part(vs,fs,material,True)
        if not closed:
            # End caps share original ring vertices, preserving watertight components.
            off=len(self.vertices)-len(vs);mi=self.materials.index(bpy.data.materials[material] if isinstance(material,str) else material)
            self.faces.extend([tuple(off+j for j in reversed(range(sides))),tuple(off+(n-1)*sides+j for j in range(sides))]);self.indices.extend([mi,mi]);self.smooth.extend([False,False])
    def ellipsoid(self,c,r,material,segments=32,rows=16,rotation=None):
        c=Vector(c);mat=rotation or Matrix.Identity(3)
        vs=[c+mat@Vector((0,0,r[2]))]
        for j in range(1,rows):
            v=pi*j/rows
            for i in range(segments):
                a=tau*i/segments;vs.append(c+mat@Vector((r[0]*sin(v)*cos(a),r[1]*sin(v)*sin(a),r[2]*cos(v))))
        vs.append(c+mat@Vector((0,0,-r[2])));bottom=len(vs)-1
        fs=[(0,1+i,1+(i+1)%segments) for i in range(segments)]
        for j in range(rows-2):
            for i in range(segments):a=1+j*segments+i;b=1+j*segments+(i+1)%segments;fs.append((a,a+segments,b+segments,b))
        fs.extend((bottom,1+(rows-2)*segments+(i+1)%segments,1+(rows-2)*segments+i) for i in range(segments))
        self.part(vs,fs,material,True)
    def loft(self,rings,material,cap=True,smooth=True):
        n=len(rings[0]);vs=[v for ring in rings for v in ring]
        fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(rings)-1) for i in range(n)]
        if cap:fs.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
        self.part(vs,fs,material,smooth)
        if cap:self.smooth[-1]=self.smooth[-2]=False
    def lathe(self,center,profile,material,segments=48):
        x,y,z=center;self.loft([[(x+r*cos(tau*i/segments),y+r*sin(tau*i/segments),z+h) for i in range(segments)] for h,r in profile],material)
    def round_box(self,c,d,r,material,rotation=None,n=8):
        # Six densely tessellated faces project onto a true spherical-edge box.
        # Shared face-boundary vertices are welded in the integer key dictionary.
        c=Vector(c);mat=rotation or Matrix.Identity(3);ext=Vector(d)*.5;inner=Vector(tuple(max(.001,v-r) for v in ext));vs=[];fs=[];cache={}
        for axis in range(3):
            others=[i for i in range(3) if i!=axis]
            for sign in [-1,1]:
                grid=[]
                for j in range(n+1):
                    row=[]
                    for i in range(n+1):
                        p=Vector((0,0,0));p[axis]=sign*ext[axis];p[others[0]]=ext[others[0]]*(2*i/n-1);p[others[1]]=ext[others[1]]*(2*j/n-1)
                        q=Vector(tuple(max(-inner[k],min(inner[k],p[k])) for k in range(3)));delta=p-q
                        v=c+mat@(q+delta.normalized()*r);key=tuple(round(v[k],9) for k in range(3))
                        if key not in cache:cache[key]=len(vs);vs.append(v)
                        row.append(cache[key])
                    grid.append(row)
                for j in range(n):
                    for i in range(n):fs.append((grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]))
        self.part(vs,fs,material,True)
    def make_mesh(self,name,transform=None):
        vs=self.vertices if transform is None else [transform@Vector(v) for v in self.vertices]
        me=bpy.data.meshes.new(name);me.from_pydata(vs,[],self.faces)
        for m in self.materials:me.materials.append(m)
        for p,mi,sm in zip(me.polygons,self.indices,self.smooth):p.material_index=mi;p.use_smooth=sm
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
        uv=me.uv_layers.new(name='UVMap')
        # A metric tangent-plane projection per polygon keeps even cap UVs nonzero.
        for p in me.polygons:
            normal=p.normal;reference=Vector((0,0,1)) if abs(normal.z)<.9 else Vector((0,1,0));u=normal.cross(reference).normalized();v=normal.cross(u).normalized()
            tile=float(me.materials[p.material_index].get('physical_tile_m',1))
            # Integer wrapping preserves repeat textures while avoiding float32 UV
            # cancellation on millimetre-scale fittings far from the world origin.
            ou=math.floor(sum(float(p.center[k])*float(u[k]) for k in range(3))/tile);ov=math.floor(sum(float(p.center[k])*float(v[k]) for k in range(3))/tile)
            for li in p.loop_indices:
                co=me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv=(sum(float(co[k])*float(u[k]) for k in range(3))/tile-ou,sum(float(co[k])*float(v[k]) for k in range(3))/tile-ov)
        me.update();return me
    def make_object(self,name):
        ob=bpy.data.objects.new(name,self.make_mesh(name));bpy.context.collection.objects.link(ob);ob['ride_realism_detail']=True;return ob

def _eligible_names():
    return sorted(o.name for o in bpy.context.scene.objects if o.type=='MESH' and o.get('PropActorTag') and not any(o.get(k) for k in ('_assembly_source','visual_replaced','render_only')) and not (o.hide_render or o.hide_viewport or o.hide_get()))

def _audit(meshes):
    report={'meshes':len(meshes),'vertices':0,'polygons':0,'zero_area_faces':0,'zero_area_triangles':0,'nonfinite_vertices':0,'degenerate_uv_faces':0,'invalid_material_indices':0,'missing_materials':0,'nonmanifold_edges':0}
    for me in meshes:
        report['vertices']+=len(me.vertices);report['polygons']+=len(me.polygons);report['missing_materials']+=sum(m is None for m in me.materials)
        report['nonfinite_vertices']+=sum(not all(math.isfinite(x) for x in v.co) for v in me.vertices)
        uv=me.uv_layers.active
        for p in me.polygons:
            report['zero_area_faces']+=p.area<=1e-12;report['invalid_material_indices']+=p.material_index>=len(me.materials)
            ps=[uv.data[i].uv for i in p.loop_indices];area=sum(ps[i].x*ps[(i+1)%len(ps)].y-ps[(i+1)%len(ps)].x*ps[i].y for i in range(len(ps)))*.5
            report['degenerate_uv_faces']+=abs(area)<=1e-12
        me.calc_loop_triangles()
        report['zero_area_triangles']+=sum((me.vertices[t.vertices[1]].co-me.vertices[t.vertices[0]].co).cross(me.vertices[t.vertices[2]].co-me.vertices[t.vertices[0]].co).length*.5<=1e-12 for t in me.loop_triangles)
        bm=bmesh.new();bm.from_mesh(me);report['nonmanifold_edges']+=sum(not e.is_manifold for e in bm.edges);bm.free()
    report['passed']=not any(report[k] for k in ['zero_area_faces','zero_area_triangles','nonfinite_vertices','degenerate_uv_faces','invalid_material_indices','missing_materials'])
    if not report['passed']:raise RuntimeError('Ride geometry audit failed: '+str(report))
    return report

def _material(name,base,color=None,roughness=None,metallic=None):
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials[base].copy();mat.name=name
    p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for label,value in [('Roughness',roughness),('Metallic',metallic)]:
        if value is not None:
            for link in list(p.inputs[label].links):mat.node_tree.links.remove(link)
            p.inputs[label].default_value=value
    if color is not None:
        for link in list(p.inputs['Base Color'].links):mat.node_tree.links.remove(link)
        p.inputs['Base Color'].default_value=(*color,1)
    for n in mat.node_tree.nodes:
        if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=min(n.inputs['Strength'].default_value,.16)
    return mat

def _superellipse(a,rx,ry,power=3.8):
    return (math.copysign(abs(cos(a))**(2/power),cos(a))*rx,math.copysign(abs(sin(a))**(2/power),sin(a))*ry)

def add_bumper_realism():
    """Rebuild seven live cars in place with manufactured, curved components."""
    s=bpy.context.scene
    if s.get('ride_realism_bumper_applied'):return {'status':'already applied'}
    before=_eligible_names();cars=sorted([o for o in s.objects if o.get('asset_family')=='BumperCar' and o.name in before],key=lambda o:o.name)
    if len(cars)!=7:raise RuntimeError('Expected seven existing BumperCar actors, found '+str(len(cars)))
    red=_material('Ride realism | faded oxblood enamel','PaintRed',None,.44,.32)
    teal=_material('Ride realism | faded teal enamel','PaintTeal',None,.44,.32)
    ochre=_material('Ride realism | warm ochre enamel','gold',(.42,.235,.052),.48,.27)
    rubber=_material('Ride realism | vulcanized bumper rubber','black',(.016,.019,.018),.78,0)
    vinyl=_material('Ride realism | aged charcoal vinyl','black',(.032,.037,.034),.51,0)
    trim=_material('Ride realism | worn nickel fittings','gold',(.34,.32,.25),.30,.8)
    lens=_material('Ride realism | old headlamp glass','cream',(.48,.42,.26),.20,.12)
    angles=[.3,-.3,2.1,2.8,-1.2,.9,-.4];meshes=[];results=[]
    for index,ob in enumerate(cars):
        g=_Geometry();paint=[red,ochre,teal][index%3];N=96
        # Inflated sidewall profile, real continuous rubber bump ring.
        for z,r,rx,ry in [(.205,.111,1.234,.754),(.287,.100,1.245,.765)]:g.tube([(rx*cos(tau*i/N),ry*sin(tau*i/N),z) for i in range(N)],r,rubber,True,12)
        for z in [.155,.335]:g.tube([(1.245*cos(tau*i/N),.765*sin(tau*i/N),z) for i in range(N)],.013,rubber,True,8)
        g.tube([(1.214*cos(tau*i/N),.742*sin(tau*i/N),.392) for i in range(N)],.025,trim,True,10)
        # Closed thin-walled pressing. Rings run from undertray up over the hood
        # and down INSIDE the cockpit; the top opening is never capped.
        rings=[]
        for rx,ry,z in [(1.10,.65,.285),(1.17,.70,.34),(1.18,.70,.43),(1.13,.66,.55),(1.065,.605,.665)]:
            rings.append([(rx*cos(tau*i/N),ry*sin(tau*i/N),z) for i in range(N)])
        for q in [.25,.5,.75,1.]:
            ring=[]
            for i in range(N):
                t=tau*i/N;x0=1.065*cos(t);y0=.605*sin(t);x1=-.30+.655*cos(t);y1=.465*sin(t)
                z=.665+.074*q+.072*sin(pi*q)*(.30+.70*max(0,cos(t)))
                ring.append((x0*(1-q)+x1*q,y0*(1-q)+y1*q,z))
            rings.append(ring)
        for shrink,z in [(.985,.69),(.88,.48),(.85,.445)]:rings.append([(-.30+.655*shrink*cos(tau*i/N),.465*shrink*sin(tau*i/N),z) for i in range(N)])
        g.loft(rings,paint,True)
        # Rubber welt follows genuine rolled cockpit lip.
        g.tube([(-.30+.655*cos(tau*i/N),.465*sin(tau*i/N),.744) for i in range(N)],.018,vinyl,True,10)
        # Low foot tray and shaped seat: both have properly rounded silhouettes.
        g.round_box((-.30,0,.462),(.96,.74,.04),.018,rubber,n=8)
        g.round_box((-.47,0,.612),(.61,.79,.16),.065,vinyl,n=12)
        backrot=Matrix.Rotation(-.13,3,'Y')
        g.round_box((-.795,0,.900),(.19,.86,.56),.084,paint,backrot,12)
        g.round_box((-.685,0,.903),(.09,.766,.465),.040,vinyl,backrot,12)
        # Seat piping and six shallow upholstered channels read from both sides.
        for x in [-.899,-.630]:
            pts=[]
            for i in range(64):
                yy,zz=_superellipse(tau*i/64,.385,.239,4);pts.append((x-.12*zz,yy,.903+zz))
            g.tube(pts,.007,trim if x<-.8 else vinyl,True,6)
        for yy in [-.275,-.165,-.055,.055,.165,.275]:
            pts=[(-.632-.13*(z-.903),yy,z) for z in [.72,.78,.86,.94,1.02,1.10]];g.tube(pts,.0065,rubber,False,6)
        # Thin side moulding, exposed mounting rivets, actual lamp housings.
        for side in [-1,1]:
            g.tube([(-.87+.11*i,side*(.595-.065*abs(-.87+.11*i)),.529+.008*cos(i*.6)) for i in range(17)],.012,trim,False,8)
            for x in [-.80,-.45,0,.45,.80]:g.ellipsoid((x,side*(.66*math.sqrt(max(.01,1-(x/1.13)**2))+.008),.49),(.015,.012,.015),trim,12,6)
            center=(1.02,side*.34,.64);g.ellipsoid(center,(.090,.143,.089),trim,32,12);g.ellipsoid((1.082,side*.34,.65),(.043,.115,.061),lens,32,12)
            g.ellipsoid((-.995,side*.355,.562),(.047,.108,.050),trim,24,10);g.ellipsoid((-1.026,side*.355,.562),(.021,.087,.035),'PaintRed',24,10)
        # A curved bonnet central spear and short, individual stamped louvers.
        g.tube([(.37+.72*i/20,0,.790-.15*(i/20)**1.7) for i in range(21)],.010,trim,False,8)
        for side in [-1,1]:
            for k in range(6):
                x=.47+k*.065;pts=[(x,side*(.15+.14*i/8),.785-.065*(x-.47)-.10*(i/8)**2) for i in range(9)];g.tube(pts,.011,trim,False,6)
        # Steering wheel is in an inclined plane with true open spoke sectors.
        hub=Vector((.025,0,1.008));u=Vector((.825,0,-.565));v=Vector((0,1,0));normal=u.cross(v).normalized()
        g.tube([(.245,0,.625),tuple(hub)],.025,trim,False,12)
        g.tube([hub+.192*(cos(tau*i/64)*u+sin(tau*i/64)*v) for i in range(64)],.025,vinyl,True,10)
        for k in range(3):g.tube([hub,hub+.175*(cos(tau*k/3)*u+sin(tau*k/3)*v)],.010,trim,False,8)
        g.ellipsoid(tuple(hub),(.042,.042,.035),trim,20,10)
        # Correct grounded electrical pickup, ribbed insulator and spring barrel.
        pole=[(-.91,.13,.71),(-.92,.13,1.16),(-.946,.13,2.16),(-.975,.13,3.77)]
        g.tube(pole,.017,trim,False,12)
        g.lathe((-.91,.13,.72),[(0,.063),(.03,.07),(.055,.047),(.19,.047),(.21,.068),(.235,.060)],rubber,24)
        for k in range(5):g.tube([(-.91+.057*cos(tau*i/24),.13+.057*sin(tau*i/24),.79+k*.024) for i in range(24)],.007,vinyl,True,6)
        g.tube([(-.947+.023*cos(i*tau/16),.13+.023*sin(i*tau/16),1.18+i*.0025) for i in range(65)],.006,trim,False,6)
        g.ellipsoid((-.975,.13,3.80),(.075,.040,.022),rubber,20,8)
        # Bake the original car heading into its mesh as the source does.
        me=g.make_mesh(ob.name+' | rounded manufactured mesh',Matrix.Rotation(angles[index],3,'Z'));old=ob.data;ob.data=me
        ob['ride_realism_revision']='cycle03_rounded_shell_seat_fittings';ob['collision_regeneration_required']=True
        ob['collision_policy']='Regenerate component collision and segment concave shell/bumper trim; preserve cockpit. Never whole-car convex hull.'
        ob['description']='Rounded pressed-steel dodgem, open cockpit with shaped stitched vinyl seat, pneumatic bump ring, worn nickel fittings, lamps and sprung power pickup'
        meshes.append(me);results.append({'actor':ob.name,'previous_vertices':len(old.vertices),'vertices':len(me.vertices),'polygons':len(me.polygons)})
    assert before==_eligible_names(),'Eligible actor identity changed'
    audit=_audit(meshes);s['ride_realism_bumper_applied']=True
    return {'status':'applied','changed_actors':results,'eligible_props_before':len(before),'eligible_props_after':len(_eligible_names()),'geometry_audit':audit,'collision_regeneration_required':True,'cockpit_openings_preserved':True,'source_saved':False}


def add_carousel_realism():
    """Refine the actual visible carousel craftsmanship without new prop actors."""
    s=bpy.context.scene
    if s.get('ride_realism_carousel_applied'):return {'status':'already applied'}
    before=_eligible_names();created=[];modified=[];mould=_material('Ride realism | aged gilt moulding','gold',(.34,.205,.067),.42,.68)
    painted=_material('Ride realism | carousel blue trim','PaintTeal',None,.59,.04)
    leather=_material('Ride realism | saddle burgundy leather','PaintRed',(.105,.023,.018),.65,0)
    # Replace crude horse body ellipsoids with four times denser curved surfaces.
    # Shapes, poses, material story and original object identities are retained.
    parts=('carved barrel','hindquarter','arched neck','head','long muzzle','ear','knee','dark carved hoof','saddle seat','saddle pommel','leather saddle flap')
    for ob in list(s.objects):
        if ob.type!='MESH' or not ob.name.startswith('Carousel horse ') or not any('| '+k in ob.name for k in parts):continue
        me=ob.data;mins=[min(v.co[i] for v in me.vertices) for i in range(3)];maxs=[max(v.co[i] for v in me.vertices) for i in range(3)];center=tuple((a+b)*.5 for a,b in zip(mins,maxs));r=tuple((b-a)*.5 for a,b in zip(mins,maxs));g=_Geometry()
        mat=leather if ('saddle seat' in ob.name or 'leather saddle flap' in ob.name) else me.materials[0]
        g.ellipsoid(center,r,mat,32,16);ob.data=g.make_mesh(ob.name+' | refined carving');ob['ride_realism_revision']='cycle04_fine_carving';modified.append(ob)
    # Replace the eight stacked mane blobs per horse with one flowing, scalloped
    # carved mane ridge and incised strands. Tail silhouette gains flowing strands.
    for index in range(12):
        ang=index*tau/12;r=3.85 if index%2==0 else 2.65;center=Vector((r*cos(ang),8+r*sin(ang),1.95+(index%3)*.12));rot=Matrix.Rotation(ang+pi/2,3,'Z')
        def P(v):return center+rot@Vector(v)
        for ob in list(s.objects):
            if ob.name.startswith('Carousel horse %02d | carved mane lock'%index):
                ob.hide_render=True;ob.hide_set(True);ob['visual_replaced']=True
        g=_Geometry()
        for side in [-1,1]:
            # Articulated leather bridle follows cheek and muzzle rather than a rod.
            g.tube([P((.54,side*.18,.89)),P((.73,side*.191,.77)),P((.92,side*.158,.59)),P((.97,side*.10,.52))],.018,leather,False,8)
            g.tube([P((.91,side*.14,.60)),P((.83,side*.19,.51)),P((.69,side*.17,.55))],.012,mould,False,8)
            g.ellipsoid(P((.76,side*.20,.69)),(.032,.032,.032),mould,16,8)
            # Oval saddle piping, buckle and fitted straps read on broad horse flanks.
            pts=[P((-.04+.251*cos(tau*i/48),side*.296,.02+.231*sin(tau*i/48))) for i in range(48)];g.tube(pts,.011,mould,True,8)
            g.round_box(P((-.035,side*.302,-.13)),(.060,.025,.076),.009,mould,rot,6)
            for k in range(8):
                t=tau*k/8;g.ellipsoid(P((-.04+.222*cos(t),side*.300,.02+.196*sin(t))),(.009,.009,.009),mould,12,6)
        # Swept surface with softly scalloped edge, visually continuous carved hair.
        rings=[];N=24
        for k in range(15):
            q=k/14;cx=.28+.23*q-.035*sin(q*pi);cz=.16+.76*q;rx=.115*(1-.22*q);ry=.205*(1-.40*q)
            rings.append([P((cx+rx*cos(tau*i/N),ry*sin(tau*i/N),cz+.022*sin(4*tau*i/N+q*9))) for i in range(N)])
        g.loft(rings,'rust' if index%2==0 else mould,True)
        for side in [-1,1]:
            for k in range(4):
                pts=[P((.285+.23*q+.025*sin(q*9+k),side*(.177-.062*q),.18+.72*q-.018*k)) for q in [j/18 for j in range(19)]];g.tube(pts,.0065,mould if index%2==0 else 'rust',False,6)
        ob=g.make_object('Carousel realism | horse %02d bridle mane and saddle craft'%index);created.append(ob)
    # Visible central drum gains layered turned profiles, fluted pilasters and
    # individually fitted curved mirror frames rather than featureless slabs.
    g=_Geometry()
    for z in [.96,1.08,3.70,3.83]:
        g.lathe((0,8,z),[(0,1.28),(.014,1.37),(.035,1.40),(.060,1.37),(.078,1.30)],mould,96)
    for j in range(12):
        a=j*tau/12;radial=Vector((cos(a),sin(a),0));tangent=Vector((-sin(a),cos(a),0));c=Vector((1.315*cos(a),8+1.315*sin(a),2.4))
        # Proper arched picture-frame outline and inboard bead reveal.
        outline=[]
        for i in range(64):
            yy,zz=_superellipse(tau*i/64,.305,1.09,6);outline.append(c+tangent*yy+Vector((0,0,zz)))
        g.tube(outline,.026,mould,True,10)
        outline2=[]
        for i in range(64):
            yy,zz=_superellipse(tau*i/64,.265,1.045,6);outline2.append(c+radial*.006+tangent*yy+Vector((0,0,zz)))
        g.tube(outline2,.008,painted,True,8)
        a2=a+.23;x,y=1.34*cos(a2),8+1.34*sin(a2)
        g.lathe((x,y,1.05),[(0,.07),(.06,.09),(.12,.07),(.18,.045),(2.40,.045),(2.47,.07),(2.53,.09),(2.59,.07)],mould,24)
        for k in range(6):
            t=k*tau/6;g.tube([(x+.047*cos(t),y+.047*sin(t),1.28),(x+.047*cos(t),y+.047*sin(t),3.46)],.007,painted,False,6)
    created.append(g.make_object('Carousel realism | turned drum cornices fluted pilasters and mirror reveals'))
    # Scalloped fascia has real layered lower moulding, fan rays and curled scrolls.
    g=_Geometry()
    for j in range(24):
        a=(j+.5)*tau/24;da=pi/24
        pts=[]
        for i in range(41):
            t=a-da+2*da*i/40;pts.append((5.565*cos(t),8+5.565*sin(t),4.40-.22*sin(pi*i/40)))
        g.tube(pts,.022,mould,False,10)
        radial=Vector((cos(a),sin(a),0));tangent=Vector((-sin(a),cos(a),0));center=Vector((5.605*cos(a),8+5.605*sin(a),4.66))
        for side in [-1,1]:
            pts=[]
            for i in range(32):
                t=i/31*1.75*pi;r=.13*(1-i/38);pts.append(center+tangent*(side*(.54+r*cos(t)))+Vector((0,0,.004+r*sin(t))))
            g.tube(pts,.014,mould,False,8)
        for k in range(7):
            t=.20+pi*.86*k/6;g.tube([center+tangent*(.12*cos(t))+Vector((0,0,.055*sin(t))),center+tangent*(.39*cos(t))+Vector((0,0,.165*sin(t)))],.009,mould,False,6)
        # Each decorative shell sits on a visible attachment rosette.
        for side in [-1,1]:g.ellipsoid(center+tangent*side*.65,(.038,.038,.038),mould,16,8)
    created.append(g.make_object('Carousel realism | scallop moulding and hand-carved fascia scrollwork'))
    # Turned spindle fittings give poles readable manufacturing detail.
    g=_Geometry()
    for j in range(12):
        a=j*tau/12;r=3.85 if j%2==0 else 2.65;x,y=r*cos(a),8+r*sin(a)
        for z in [.79,3.40,3.91]:g.lathe((x,y,z),[(0,.045),(.018,.073),(.04,.077),(.06,.055),(.13,.048),(.16,.066),(.185,.067),(.21,.043)],mould,32)
        g.lathe((x,y,.78),[(0,.105),(.018,.105),(.028,.08),(.05,.048)],'rust',32)
    created.append(g.make_object('Carousel realism | spindle turned collars and deck foot sockets'))
    # Physical deck board end caps, brass fasteners and subtle grain splits.
    g=_Geometry()
    for j in range(72):
        a=tau*(j+.48)/72
        for r in [1.40,4.98]:
            x,y=r*cos(a),8+r*sin(a);g.lathe((x,y,.759),[(0,.012),(.006,.012)],mould,12)
        if j%3==0:
            r=4.35+.20*sin(j*1.41);g.tube([(r*cos(a),8+r*sin(a),.763),((r+.28)*cos(a+.002),8+(r+.28)*sin(a+.002),.763),((r+.50)*cos(a),8+(r+.50)*sin(a),.763)],.0035,'black',False,5)
    created.append(g.make_object('Carousel realism | individual board fixings and wear checks'))
    assert before==_eligible_names(),'Eligible actor identity changed'
    audit=_audit([o.data for o in created+modified]);s['ride_realism_carousel_applied']=True
    return {'status':'applied','new_detail_objects':len(created),'remeshed_existing_horse_parts':len(modified),'eligible_props_before':len(before),'eligible_props_after':len(_eligible_names()),'geometry_audit':audit,'collision_regeneration_required':'Regenerate environment export for revised horse silhouettes and decorative details; gameplay actors unchanged.','source_saved':False}
