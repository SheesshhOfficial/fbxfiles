"""Close-view architectural/maintenance pass. Import and call; never opens or saves files."""
import bpy,bmesh,math,random
from mathutils import Vector
from math import sin,cos,pi

def refine_bumper_arena():
    from assemble_props import assemble
    if bpy.data.objects.get('Arena detail | operator counter'):return {'status':'already applied'}
    rng=random.Random(5317);M=bpy.data.materials;created=[];props=[]
    def mat(key):return M[key]
    def mesh(name,vs,fs,material,smooth=False):
        me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat(material) if isinstance(material,str) else material)
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
        uv=me.uv_layers.new(name='UVMap');tile=float(me.materials[0].get('physical_tile_m',1))
        for p in me.polygons:
            p.use_smooth=smooth and len(p.vertices)==4
            axis=max(range(3),key=lambda a:abs(p.normal[a]));ax=[a for a in range(3) if a!=axis]
            for li in p.loop_indices:
                v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[ax[0]]/tile,v[ax[1]]/tile)
        o=bpy.data.objects.new('Arena detail | '+name,me);bpy.context.collection.objects.link(o);created.append(o);return o
    def box(n,c,d,m,bevel=0):
        x,y,z=[v/2 for v in d];o=mesh(n,[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m);o.location=c
        if bevel:
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=2,profile=.5,affect='EDGES');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
            # Fresh UVs on real beveled topology.
            uv=o.data.uv_layers.active;tile=float(o.data.materials[0].get('physical_tile_m',1))
            for p in o.data.polygons:
                axis=max(range(3),key=lambda a:abs(p.normal[a]));ax=[a for a in range(3) if a!=axis]
                for li in p.loop_indices:
                    v=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[ax[0]]/tile,v[ax[1]]/tile)
        return o
    def frustum(n,c,r1,r2,h,m,N=24):
        vs=[(r*cos(2*pi*i/N),r*sin(2*pi*i/N),z) for r,z in [(r1,-h/2),(r2,h/2)] for i in range(N)]
        fs=[tuple(reversed(range(N))),tuple(range(N,N*2))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
        o=mesh(n,vs,fs,m,True);o.location=c;return o
    def beam(n,a,b,r,m,N=12):
        a,b=Vector(a),Vector(b);o=frustum(n,(a+b)*.5,r,r,max(.001,(b-a).length-.0004),m,N);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
    def cable(n,pts,r,m,segments=8):
        # Individual capped convex pieces retain true hollow coiling spaces in collision export.
        return [beam(n+' segment %02d'%i,a,b,r,m,segments) for i,(a,b) in enumerate(zip(pts[:-1],pts[1:]))]
    def label(n,body,loc,size,material='PaintCream'):
        cu=bpy.data.curves.new(n,'FONT');cu.body=body;cu.size=size;cu.align_x='CENTER';cu.extrude=.0008
        o=bpy.data.objects.new('Arena detail | '+n,cu);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(pi/2,0,0);cu.materials.append(mat(material));created.append(o);return o
    def finish_prop(n,parts,origin,family):
        o=assemble('Arena prop | '+n,parts,origin,family)
        o['collision_policy']='Compound closed convex components; preserve all handle and coil openings. No whole-assembly hull.'
        o['placement_role']='Accessible maintenance dressing outside marked north/south through-route'
        for p in parts:p.hide_render=True;p.hide_set(True);p['_assembly_source']=True
        props.append(o);return o
    # Steel frames gain real plates, seam overlaps and exposed fasteners, not decorative floating bolts.
    for x in [-24.35,-9.65]:
        for y in [6.25,12,17.75]:
            side=1 if x<-17 else -1
            box('rafter cleat',(x,y,4.85),(.34,.29,.07),'rust',.008)
            plate=mesh('bolted knee gusset',[(x,y-.15,4.14),(x,y-.15,4.9),(x+side*.73,y-.15,4.9)],[(0,1,2)],'rust')
            # Small visible steel washers and hex heads on the broad gusset face.
            for xx,zz in [(x+side*.08,4.4),(x+side*.08,4.78),(x+side*.43,4.79)]:
                beam('gusset bolt washer',(xx,y-.174,zz),(xx,y-.162,zz),.034,'rust',16)
                beam('hex bolt head',(xx,y-.194,zz),(xx,y-.175,zz),.022,'PaintCream',6)
    roofs=sorted([o for o in bpy.data.objects if o.name.startswith('Dodgems | corrugated roof sheet')],key=lambda o:o.name)
    for i,o in enumerate(roofs):
        if i%7==2:
            o.data=o.data.copy();ys=[v.co.y for v in o.data.vertices];ymax=max(ys)
            for v in o.data.vertices:
                # Small wind-peel at sheet end; existing open holes remain visibly open.
                t=max(0,(v.co.y-(ymax-.45))/.45);v.co.z+=t*t*(.14+.09*sin(v.co.x*7))
            o.data.update()
        # A pair of fasteners at actual sheet/purlin bearing line.
        if i%3==0 and len(o.data.vertices):
            for j in [2,13]:
                v=o.matrix_world@o.data.vertices[min(j,len(o.data.vertices)-1)].co
                frustum('roof screw and washer',(v.x,v.y,v.z+.016),.032,.027,.024,'rust',12)
    # Tattered front fascia has sensible mounting brackets and a supported hanging closure notice.
    for x in [-19.65,-14.35]:
        beam('sign hanging bracket',(x,5.88,4.77),(x,5.88,4.98),.018,'rust')
        box('sign back cleat',(x,5.98,4.53),(.09,.24,.55),'rust',.008)
    for x in [-18,-16]:beam('closure notice chain',(x,6.05,1.31),(x,6.05,1.02),.011,'rust',8)
    box('closure notice board',(-17,6.05,.9),(2.2,.035,.32),'PaintCream',.01)
    label('closure notice text','RIDE CLOSED',(-17,6.026,.84),.155,'PaintRed')
    # Closure board is above an existing entrance rail gap, suspended high enough to step under only if desired;
    # relocate it onto left rail bay so primary gateway is wholly unobstructed.
    for o in created[-4:]:o.location.x-=3.7
    # North-west operator shelter, open front/east access, human-scale counter and service hatch.
    bx,by=-23.1,16.6
    box('operator booth plinth',(bx,by,.49),(2.05,1.8,.18),'concrete',.025)
    for xx in [bx-.94,bx+.94]:
        for yy in [by-.8,by+.8]:box('booth painted steel mullion',(xx,yy,1.8),(.07,.07,2.5),'PaintTeal',.009)
    for i in range(10):
        x=bx-.89+i*.196
        box('booth rear tongue and groove',(x,by+.8,1.55),(.185,.045,2.0),'wood',.005)
        box('booth front kick panel',(x,by-.8,.89),(.185,.045,.62),'PaintTeal',.004)
    for i in range(8):box('booth west wall plank',(bx-.94,by-.72+i*.196,1.55),(.045,.185,2.0),'wood',.005)
    box('operator counter',(bx,by-.7,1.26),(2.13,.54,.09),'wood',.025)
    box('booth rear shelf',(bx,by+.6,1.35),(1.8,.35,.06),'wood',.012)
    box('booth overhanging roof',(bx,by,3.08),(2.3,2.05,.085),'rust',.012)
    for x in [bx-.96,bx+.96]:box('booth roof trim',(x,by,3.03),(.07,2.05,.13),'PaintTeal',.01)
    box('operator fascia',(bx,by-.83,2.78),(1.83,.05,.33),'PaintCream',.01)
    label('operator booth sign','OPERATOR', (bx,by-.865,2.70),.19,'PaintRed')
    # Distinct electrical cabinet: door reveal, lock, conduit, bracketed ceramic insulators and isolator.
    ex,ey=-24.22,16.23
    box('control enclosure',(ex,ey,1.88),(.12,.54,.72),'rust',.03)
    box('control cabinet door',(ex+.075,ey,1.88),(.035,.49,.66),'PaintTeal',.015)
    box('cabinet hinge top',(ex+.10,ey+.20,2.07),(.035,.045,.11),'rust',.006)
    box('cabinet hinge bottom',(ex+.10,ey+.20,1.68),(.035,.045,.11),'rust',.006)
    beam('door latch spindle',(ex+.10,ey-.17,1.89),(ex+.16,ey-.17,1.89),.018,'rust')
    box('isolator red paddle',(ex+.18,ey-.17,1.86),(.04,.06,.15),'PaintRed',.01)
    cable('rigid metal conduit',[(ex,ey,2.26),(ex,ey,2.7),(ex,ey+.6,3.2),(ex,ey+.6,4.75),(-17,ey+.6,4.75)],.018,'rust')
    for z in [2.5,3.3,4.0]:box('conduit saddle clamp',(ex,ey+.6,z),(.08,.07,.025),'rust',.004)
    box('control desk angled panel',(bx,by-.64,1.36),(.72,.3,.11),'rust',.018)
    for x,c in [(bx-.22,'PaintRed'),(bx-.07,'PaintTeal'),(bx+.19,'PaintCream')]:
        frustum('control button bezel',(x,by-.65,1.426),.045,.045,.018,'rust')
        frustum('control pushbutton',(x,by-.65,1.445),.03,.03,.025,c)
    box('service instruction plate',(bx-.47,by-.985,1.08),(.58,.012,.17),'PaintCream',.003)
    label('service panel text','POWER OFF', (bx-.47,by-.995,1.035),.067,'PaintRed')
    # Material variants retain the existing scanned PBR maps, including roughness/normal.
    def tinted_material(name,base,factor,roughness=None):
        m=M.get(name)
        if m:return m
        m=M[base].copy();m.name=name;nt=m.node_tree;p=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');inp=p.inputs['Base Color']
        if inp.is_linked:
            old=inp.links[0].from_socket;mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*factor,1);nt.links.new(old,mix.inputs[1]);nt.links.new(mix.outputs[0],inp)
        else:inp.default_value=(*factor,1)
        if roughness is not None:
            for l in list(p.inputs['Roughness'].links):nt.links.remove(l)
            p.inputs['Roughness'].default_value=roughness
        return m
    oil=tinted_material('Arena dark aged oil on scanned metal','rust',(.06,.07,.08),.29)
    wear=tinted_material('Arena burnished steel wear','rust',(.52,.61,.65),.46)
    # Isolated real-size stain patches and elliptical wheel scuffs. No pavement covering grid.
    for j,(x,y,rx,ry) in enumerate([(-22.7,14.4,.57,.27),(-11,16.5,.29,.19),(-20,8.5,.73,.36)]):
        vs=[(x,y,.389+j*.0003)]+[(x+rx*(1+.17*sin(i*2.1))*cos(i*2*pi/25),y+ry*(1+.16*sin(i*1.7))*sin(i*2*pi/25),.389+j*.0003) for i in range(25)]
        mesh('old oil splash %02d'%j,vs,[(0,i+1,(i+1)%25+1) for i in range(25)],oil)
    for j,(x,y,a) in enumerate([(-18.9,13.8,.3),(-13,10.4,1.1),(-20.3,10.1,2.4)]):
        vs=[]
        for i in range(32):
            t=a+i*.075
            for r in [1.28,1.30+.017*sin(i*.8)]:vs.append((x+r*cos(t),y+.76*r*sin(t),.3898))
        mesh('interrupted tire scuff arc %02d'%j,vs,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(31) if i%7!=0],wear)
    # Closed toolbox with actual seam, clasps, protected corners and a genuinely open hand grip.
    p0=len(created);x,y,z=-22.9,15.98,1.31
    box('tool case lower shell',(x,y,z+.12),(.64,.33,.24),'PaintRed',.025)
    box('tool case lid',(x,y,z+.27),(.655,.345,.065),'PaintRed',.018)
    for xx in [x-.22,x+.22]:box('toolcase front clasp',(xx,y-.18,z+.23),(.045,.025,.12),'rust',.006)
    for xx in [x-.12,x+.12]:box('toolcase handle upright',(xx,y,z+.35),(.033,.055,.12),'rust',.01)
    box('toolcase carrying grip',(x,y,z+.407),(.27,.064,.045),'black',.015)
    for xx in [x-.29,x+.29]:box('toolcase reinforced corner',(xx,y-.15,z+.11),(.052,.03,.18),'rust',.009)
    finish_prop('Mechanic tool case',created[p0:],(x,y,z),'MechanicToolCase')
    # Two distinct small oil cans, supported and reachable at the counter/booth foot.
    for j,(x,y,z) in enumerate([(-23.7,16.05,1.31),(-23.9,16.6,.59)]):
        k=len(created)
        frustum('oiler reservoir',(x,y,z+.12),.105,.092,.23,'PaintTeal',32)
        frustum('oiler rolled foot',(x,y,z+.014),.112,.112,.028,'rust',32)
        frustum('oiler shoulder',(x,y,z+.26),.094,.044,.05,'PaintTeal',32)
        frustum('oiler screw cap',(x,y,z+.30),.047,.047,.028,'rust',24)
        beam('oiler tapered spout',(x,y,z+.31),(x+.14,y,z+.48),.012,'rust')
        beam('oiler final nozzle',(x+.14,y,z+.48),(x+.20,y,z+.47),.008,'rust')
        for a,b in [((x-.09,y,z+.23),(x-.17,y,z+.22)),((x-.17,y,z+.22),(x-.17,y,z+.11)),((x-.17,y,z+.11),(x-.09,y,z+.10))]:beam('oiler handle',a,b,.012,'rust')
        finish_prop('Pump oil can %02d'%j,created[k:],(x,y,z),'PumpOilCan')
    # Two cones: a real rubber foot, differently colored tapered bands, convex geometry per band.
    for j,(x,y) in enumerate([(-21.65,16.85),(-10.6,16.9)]):
        z=.39;k=len(created);box('cone weighted rubber foot',(x,y,z+.035),(.42,.42,.07),'black',.025)
        rings=[.07,.22,.32,.45,.51,.56];N=32
        vs=[(x+.17*(1-h/.61)*cos(i*2*pi/N),y+.17*(1-h/.61)*sin(i*2*pi/N),z+h) for h in rings for i in range(N)]
        fs=[tuple(reversed(range(N))),tuple((len(rings)-1)*N+i for i in range(N))]
        for row in range(len(rings)-1):
            for i in range(N):fs.append((row*N+i,row*N+(i+1)%N,(row+1)*N+(i+1)%N,(row+1)*N+i))
        cone=mesh('continuous convex striped cone',vs,fs,'PaintRed',True);cone.data.materials.append(mat('PaintCream'))
        for poly in cone.data.polygons:
            if poly.index>=2:poly.material_index=1 if (poly.index-2)//N in [1,3] else 0
        finish_prop('Service safety cone %02d'%j,created[k:],(x,y,z),'SafetyCone')
    # Coiled air hose: a modest 1.6-turn service coil, convex capped pieces preserve empty middle.
    x,y,z=-23.2,14.8,.42;k=len(created)
    pts=[(x+(.36+.035*t/(2*pi))*cos(t),y+(.36+.035*t/(2*pi))*sin(t),z+.006*t) for t in [i*3.2*pi/42 for i in range(43)]]
    cable('coiled service air hose',pts,.023,'black',10)
    cable('hose loose lead',[pts[-1],(x-.2,y-.55,z+.035),(x+.27,y-.66,z+.035)],.023,'black',10)
    beam('hose brass connector',(x+.27,y-.66,z+.035),(x+.37,y-.66,z+.035),.035,'rust',12)
    finish_prop('Coiled service air hose',created[k:],(x,y,.39),'CoiledAirHose')
    # Additional separately placeable copies belong to real maintenance stations.
    originals={o['asset_family']:o for o in props}
    for family,loc,name in [
        ('MechanicToolCase',(-22.5,16.95,.59),'spare case on booth floor'),
        ('PumpOilCan',(-23.7,17.17,1.39),'rear-shelf oiler'),
        ('PumpOilCan',(-23.4,17.17,1.39),'second rear-shelf oiler'),
        ('SafetyCone',(-10.7,7.05,.39),'south-east service cone'),
        ('CoiledAirHose',(-10.8,13.5,.39),'east wall spare air hose')]:
        o=originals[family].copy();o.data=originals[family].data;o.name='Arena prop | '+name;bpy.context.collection.objects.link(o);o.location=loc;props.append(o)
    # Portable inspection lanterns have hollow steel carrying frames and separate glass fronts.
    for j,(x,y,z) in enumerate([(-22.45,17.17,1.39),(-23.85,13.6,.39),(-10.45,11.15,.39)]):
        k=len(created)
        box('worklamp battery foot',(x,y,z+.035),(.25,.19,.07),'PaintTeal',.012)
        box('worklamp metal housing',(x,y,z+.19),(.23,.12,.23),'rust',.025)
        box('worklamp protective rim',(x,y-.067,z+.19),(.23,.025,.23),'PaintCream',.012)
        box('worklamp glass face',(x,y-.084,z+.19),(.187,.012,.18),'glass',.002)
        for xx in [x-.145,x+.145]:beam('worklamp carrying frame',(xx,y,z+.08),(xx,y,z+.36),.014,'rust')
        beam('worklamp handle grip',(x-.145,y,z+.36),(x+.145,y,z+.36),.021,'black')
        for zz in [z+.135,z+.24]:beam('worklamp guard bar',(x-.1,y-.10,zz),(x+.1,y-.10,zz),.008,'rust',8)
        finish_prop('Portable inspection lamp %02d'%j,created[k:],(x,y,z),'PortableWorkLamp')
    # Four modest solid wheel chocks, two beside the service cart and two on the rear shelf.
    for j,(x,y,z) in enumerate([(-23.95,13.0,.39),(-23.55,13.0,.39),(-23.05,17.17,1.39),(-22.85,17.17,1.39)]):
        k=len(created);w=.12;d=.20;h=.13
        mesh('solid timber wheel chock',[(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x+w/2,y+d/2,z),(x-w/2,y+d/2,z),(x-w/2,y+d/2,z+h),(x+w/2,y+d/2,z+h)],[(0,3,2,1),(3,4,5,2),(0,1,5,4),(0,4,3),(1,2,5)],'wood')
        finish_prop('Timber wheel chock %02d'%j,created[k:],(x,y,z),'WheelChock')
    # Restrained edge litter: two discarded packing pieces and three individual fastener clusters.
    for j,(x,y,a) in enumerate([(-24,14.6,.4),(-10.1,17.5,-.5),(-23.8,7.1,.9)]):
        o=box('folded maintenance carton',(x,y,.425),(.29,.18,.035),'wood',.004);o.rotation_euler.z=a
        box('carton lifting flap',(x-.10,y,.47),(.06,.18,.085),'wood',.002).rotation_euler.y=-.55
    for j in range(5):
        x=-23.8+rng.uniform(-.15,.15);y=15+rng.uniform(-.25,.25)
        beam('dropped maintenance bolt',(x,y,.41),(x+.075,y+.02,.41),.011,'rust',6)
    bpy.context.view_layer.update()
    return {'new_detail_objects':len(created),'eligible_props':len(props),'families':sorted({o['asset_family'] for o in props}),'arena_center':[-17,12],'routes':'North/south main entrance gaps and all car cockpits preserved','booth_center':[bx,by]}
