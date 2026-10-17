"""Additive backstage/funhouse refinement. Does not open, save, or render scenes.
Call refine_backstage_funhouse() with the art-pass scene already loaded.
"""
import bpy, bmesh, math, random, json
from mathutils import Vector

def refine_backstage_funhouse():
    from fast_geometry import make_api
    from assemble_props import assemble
    if bpy.data.objects.get('RF_Backstage_Refinement_Root'):
        return {'status':'already_applied'}
    root=bpy.data.objects.new('RF_Backstage_Refinement_Root',None);bpy.context.collection.objects.link(root)
    mats={k:bpy.data.materials[k] for k in ('wood','rust','black','gold','glass','cream','red','teal','bulb')}
    for key,base in (('paintred','red'),('paintteal','teal'),('paintcream','cream')):
        mats[key]=bpy.data.materials.get({'paintred':'PaintRed','paintteal':'PaintTeal','paintcream':'PaintCream'}[key]) or mats[base]
    cube,cyl,sphere,beam,torus=make_api(mats)
    rng=random.Random(1084);eligible=[];static=[]
    def uv_scale(o):
        # Unique mesh data prevents UV changes propagating into cached primitives.
        o.data=o.data.copy()
        for p in o.data.polygons:
            ma=o.data.materials[p.material_index] if o.data.materials else None
            if ma and ma.get('physical_tile_m'):
                for li in p.loop_indices:o.data.uv_layers.active.data[li].uv/=float(ma['physical_tile_m'])
        return o
    def C(n,p,s,ma='rust',bev=.008):return uv_scale(cube('RF_'+n,p,s,mats[ma],bevel=bev))
    def Y(n,p,r,d,ma='rust',vertices=24):return uv_scale(cyl('RF_'+n,p,r,d,mats[ma],vertices))
    def B(n,a,b,r=.015,ma='rust'):return uv_scale(beam('RF_'+n,a,b,r,mats[ma]))
    def T(n,p,R,r,ma='rust'):
        return uv_scale(torus('RF_'+n,p,R,r,mats[ma]))
    def mesh(n,vs,fs,ma):
        me=bpy.data.meshes.new('RF_'+n);me.from_pydata(vs,[],fs);me.materials.append(mats[ma]);me.update();uv=me.uv_layers.new(name='UVMap')
        for f in me.polygons:
            axis=max(range(3),key=lambda a:abs(f.normal[a]));axes=[a for a in range(3) if a!=axis]
            for li in f.loop_indices:
                v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
        ob=bpy.data.objects.new('RF_'+n,me);bpy.context.collection.objects.link(ob);return uv_scale(ob)
    def label(n,body,p,size=.06,ma='paintcream',rot=(math.pi/2,0,0)):
        cu=bpy.data.curves.new('RF_'+n,'FONT');cu.body=body;cu.align_x='CENTER';cu.size=size;cu.extrude=.0008
        ob=bpy.data.objects.new('RF_'+n,cu);bpy.context.collection.objects.link(ob);ob.location=p;ob.rotation_euler=rot;cu.materials.append(mats[ma])
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
        me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges))
        bad=[f for f in bm.faces if f.calc_area()<1e-12]
        if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
        bm.to_mesh(me);bm.free();me.update()
        for attempt in range(3):
            badidx=[p.index for p in me.polygons if p.area<=1e-12]
            if not badidx:break
            bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in badidx],context='FACES_ONLY');bm.to_mesh(me);bm.free();me.update()
        uv=me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            axis=max(range(3),key=lambda a:abs(poly.normal[a]));axes=[a for a in range(3) if a!=axis]
            for li in poly.loop_indices:
                v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
        new=bpy.data.objects.new(ob.name+'_Mesh',me);bpy.context.collection.objects.link(new);new.matrix_world=ob.matrix_world.copy();bpy.data.objects.remove(ob,do_unlink=True);return new
    def finish(name,parts,origin,family):
        # Bake every bevel before assembly; evaluated mesh carries explicit UVs.
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();baked=[]
        for ob in parts:
            me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
            if not me.uv_layers:
                uv=me.uv_layers.new(name='UVMap')
                for p in me.polygons:
                    ax=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=ax]
                    for li in p.loop_indices:
                        v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
            new=bpy.data.objects.new(ob.name+'_Source',me);bpy.context.collection.objects.link(new);new.matrix_world=ob.matrix_world.copy();bpy.data.objects.remove(ob,do_unlink=True);baked.append(new)
        ob=assemble('RF_'+name,baked,origin,family)
        ob['collision_policy']='Compound convex source components; preserve open handle and container voids'
        ob['collision_source_parts']=json.dumps([p.name for p in baked]);ob['refinement_set']='BackstageFunhouse'
        for p in baked:p.hide_render=True;p.hide_set(True);p['assembly_owner']=ob.name
        eligible.append(ob.name);return ob
    # Open toolbox: hollow compartment, rolled lip, hinged lid, handles and tools.
    def toolbox(n,x,y,z,colour='paintteal',opened=True):
        p=[C(n+'_Base',(x,y,z+.025),(.58,.32,.05),colour)]
        for sx in (-1,1):p.append(C(n+'_End',(x+sx*.276,y,z+.135),(.028,.32,.22),colour))
        for sy in (-1,1):p.append(C(n+'_Wall',(x,y+sy*.146,z+.135),(.56,.028,.22),colour))
        for sx in (-1,1):p.append(C(n+'_End_Rim',(x+sx*.279,y,z+.25),(.035,.34,.028),'rust'))
        for sy in (-1,1):p.append(C(n+'_Side_Rim',(x,y+sy*.151,z+.25),(.58,.035,.028),'rust'))
        lid=C(n+'_Lid',(x,y+.235,z+.37),(.60,.035,.32),colour) if opened else C(n+'_Lid',(x,y,z+.27),(.60,.34,.045),colour)
        if opened:lid.rotation_euler.x=-.36
        p.append(lid)
        for sx in (-1,1):
            p.append(C(n+'_Latch',(x+sx*.17,y-.173,z+.18),(.055,.025,.075),'gold'))
            p.append(B(n+'_Hinge',(x+sx*.18-.04,y+.16,z+.25),(x+sx*.18+.04,y+.16,z+.25),.014))
        if opened:
            p.append(C(n+'_Inner_Tray',(x,y,z+.085),(.50,.24,.035),'black'))
            for k in range(3):
                xx=x-.18+k*.16
                p.append(B(n+'_Tool_Shaft',(xx,y-.08,z+.13),(xx+.06,y+.1,z+.14),.012))
                p.append(B(n+'_Tool_Grip',(xx,y-.08,z+.13),(xx-.025,y-.15,z+.12),.025,'paintred'))
        else:
            for dx in (-.10,.10):p.append(B(n+'_Handle_Post',(x+dx,y,z+.29),(x+dx,y,z+.36),.014))
            p.append(B(n+'_Handle',(x-.10,y,z+.36),(x+.10,y,z+.36),.018,'black'))
        return finish(n,p,(x,y,z),'OpenToolbox' if opened else 'ClosedToolCase')
    toolbox('Service_Toolbox',15.43,-1.02,1.23)
    toolbox('Spare_Toolcase',19.8,.4,1.0,'paintred',False)
    # Each container wall is a closed convex wedge, enabling compound collision
    # without a single hull filling the usable cavity.
    def vessel(n,x,y,z,r,h,ma='paintcream',taper=.88):
        p=[Y(n+'_Bottom',(x,y,z+.012),r*taper,.024,ma)]
        for k in range(20):
            a=k*math.tau/20;b=(k+1)*math.tau/20;vs=[]
            for zz,rr in ((z+.02,r*taper),(z+h,r)):
                for rad,ang in ((rr,a),(rr,b),(rr-.012,b),(rr-.012,a)):
                    vs.append((x+rad*math.cos(ang),y+rad*math.sin(ang),zz))
            p.append(mesh(n+'_Wall_%02d'%k,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],ma))
        # Segmented bail remains genuinely open.
        pts=[(x+r*math.cos(j*math.pi/12),y,z+h+.01+r*math.sin(j*math.pi/12)) for j in range(13)]
        for a,b in zip(pts,pts[1:]):p.append(B(n+'_Bail',a,b,.008))
        return p
    x,y,z=14.8,-3.15,.0
    p=vessel('Wash_Bucket',x,y,z,.19,.31,'rust',.76)
    p.append(Y('Wash_Bucket_Dirty_Base',(x,y,z+.035),.135,.012,'black'))
    finish('Wash_Bucket',p,(x,y,z),'OpenMaintenanceBucket')
    for k,(x,y,z,r,h,col) in enumerate(((17.0,-8.5,.73,.125,.23,'paintcream'),(17.35,-8.42,.73,.10,.19,'paintred'),(14.88,-8.76,1.9,.09,.16,'paintteal'))):
        n='Paint_Can_%02d'%k;p=vessel(n,x,y,z,r,h,col,1)
        if k!=1:p.append(Y(n+'_Lid',(x,y,z+h+.007),r+.006,.014,'rust'))
        else:p.append(Y(n+'_Dried_Paint',(x,y,z+.06),r-.015,.012,'paintred'))
        p.append(C(n+'_Label',(x,y-r-.003,z+h*.52),(r*1.1,.008,h*.36),'paintcream',.002))
        finish(n,p,(x,y,z),'PaintCan_Closed' if k!=1 else 'PaintCan_Open')
    # Fuel container with protective perimeter bead and unobstructed grip slot.
    x,y,z=18.75,-8.3,.0;p=[]
    p.append(C('Fuel_Body',(x,y,z+.255),(.32,.19,.49),'paintteal',.035))
    for zz in (z+.035,z+.45):p.append(C('Fuel_Seam',(x,y,zz),(.33,.20,.025),'rust',.012))
    for sy in (-1,1):
        for sign in (-1,1):p.append(B('Fuel_Pressed_Rib',(x-.11,y+sy*.104,z+.12 if sign==1 else z+.39),(x+.11,y+sy*.104,z+.39 if sign==1 else z+.12),.009,'paintteal'))
    for dx in (-.09,.09):p.append(C('Fuel_Handle_Upright',(x+dx,y,z+.54),(.04,.055,.13),'paintteal'))
    p.append(C('Fuel_Grip',(x,y,z+.61),(.22,.055,.04),'paintteal'))
    p.append(Y('Fuel_Cap',(x-.10,y-.055,z+.51),.035,.045,'rust'))
    finish('Service_Fuel_Can',p,(x,y,z),'MetalFuelContainer')
    # Cable reel and a small oil dispenser, distinct silhouettes and sizes.
    x,y,z=16.1,1.1,.05;p=[]
    for xx in (x-.13,x+.13):
        q=Y('Cable_Reel_Cheek',(xx,y,z+.23),.22,.025,'wood');q.rotation_euler.y=math.pi/2;p.append(q)
    q=Y('Cable_Reel_Core',(x,y,z+.23),.13,.25,'black');q.rotation_euler.y=math.pi/2;p.append(q)
    for k in range(9):
        q=T('Cable_Reel_Winding',(x-.1+k*.025,y,z+.23),.145,.013,'black');q.rotation_euler.y=math.pi/2;p.append(q)
    for dx in (-.17,.17):p.append(C('Cable_Reel_Foot',(x+dx,y,z+.02),(.07,.30,.04),'rust'))
    finish('Extension_Cable_Reel',p,(x,y,z),'PortableCableReel')
    x,y,z=16.55,-3.0,1.075;p=[Y('Oiler_Tank',(x,y,z+.06),.055,.12,'paintred'),Y('Oiler_Top',(x,y,z+.127),.04,.018,'rust')]
    p.append(B('Oiler_Spout',(x,y,z+.14),(x+.11,y,z+.26),.008))
    p.append(B('Oiler_Trigger',(x-.035,y,z+.14),(x-.09,y,z+.18),.012))
    finish('Machine_Oil_Dispenser',p,(x,y,z),'MachineOilCan')
    # Repeated individually eligible copies, with distinct orientations and paint.
    # Each repeats its meaningful closed source components, never a monolithic hull.
    def copy_prop(source_name,new_name,position,yaw=0,paint=None):
        from mathutils import Matrix
        src=bpy.data.objects[source_name];origin=src.location.copy()
        transform=Matrix.Translation(Vector(position)) @ Matrix.Rotation(yaw,4,'Z') @ Matrix.Translation(-origin)
        parts=[]
        for key in json.loads(src['collision_source_parts']):
            old=bpy.data.objects[key];new=old.copy();new.data=old.data.copy();bpy.context.collection.objects.link(new)
            new.name='RF_'+new_name+'_Part';new.hide_render=False;new.hide_set(False);new.matrix_world=transform @ old.matrix_world
            for tag in ('_assembly_source','assembly_owner'):
                if tag in new:del new[tag]
            if paint:
                for idx,ma in enumerate(new.data.materials):
                    if ma and ma.name.startswith('Paint'):new.data.materials[idx]=mats[paint]
            parts.append(new)
        return finish(new_name,parts,position,src['asset_family'])
    copies=[
        ('RF_Service_Toolbox','Toolbox_North_Work', (18.3,1.1,.05),-.32,'paintred'),
        ('RF_Spare_Toolcase','Toolcase_South_Storage',(20.0,-9.5,0),.42,'paintcream'),
        ('RF_Spare_Toolcase','Toolcase_Funhouse',(12.2,8.1,.28),-.15,'paintteal'),
        ('RF_Paint_Can_00','Paint_Can_Pallet_Extra',(17.2,-8.8,.73),.6,'paintteal'),
        ('RF_Paint_Can_01','Paint_Can_Crate_Top',(15.25,-8.9,1.9),-.5,'paintcream'),
        ('RF_Paint_Can_02','Paint_Can_Repair_Box',(19.7,.65,1.0),.3,'paintred'),
        ('RF_Paint_Can_00','Paint_Can_Funhouse_Front',(11.6,8.2,.28),-.4,None),
        ('RF_Paint_Can_01','Paint_Can_Funhouse_Rear',(20.5,14.6,.28),.8,None),
        ('RF_Paint_Can_02','Paint_Can_Yard_Edge',(14.35,-8.15,0),-.3,'paintcream'),
        ('RF_Wash_Bucket','Bucket_Funhouse_Front',(20.5,8.4,.28),.3,None),
        ('RF_Wash_Bucket','Bucket_Funhouse_Side',(11.35,14.6,.28),-.9,None),
        ('RF_Wash_Bucket','Bucket_South_Storage',(18.8,-9.6,0),.7,None),
        ('RF_Service_Fuel_Can','Fuel_Can_Pallet_Side',(16.0,-9.4,0),-.6,'paintcream'),
        ('RF_Service_Fuel_Can','Fuel_Can_Van_Outer',(22.6,-6.8,0),.4,'paintred'),
        ('RF_Extension_Cable_Reel','Cable_Reel_Funhouse_West',(11.5,11.4,.28),.45,None),
        ('RF_Extension_Cable_Reel','Cable_Reel_Funhouse_Rear',(19.9,17.7,.28),-.55,None),
        ('RF_Machine_Oil_Dispenser','Oil_Can_Service_Crate',(19.5,.25,1.0),-.3,None),
        ('RF_Machine_Oil_Dispenser','Oil_Can_Pallet',(15.78,-1.1,1.23),.3,None),
        ('RF_Machine_Oil_Dispenser','Oil_Can_South_Box',(14.7,-8.55,1.9),.8,None),
    ]
    for args in copies:copy_prop(*args)
    repair_backstage_container_collision_seams()
    # Physically attached caravan gutters, joints, service panels and fasteners.
    for prefix,cx,cy,side in (('A',12.6,-4.6,1),('B',20.7,-4,-1)):
        xx=cx+side*1.43
        B('Van_'+prefix+'_Gutter',(xx,cy-3.4,3.48),(xx,cy+3.4,3.48),.035)
        B('Van_'+prefix+'_Drain',(xx,cy+3.25,3.47),(xx,cy+3.25,1.02),.026)
        for yy in (cy-2.9,cy+2.9):
            C('Van_'+prefix+'_Roof_Strapping',(cx,yy,3.67),(2.6,.06,.025),'rust',.004)
        C('Van_'+prefix+'_Service_Hatch',(cx+side*1.425,cy+2.75,1.55),(.035,.62,.58),'rust')
        for j in range(6):C('Van_'+prefix+'_Hatch_Louvre',(cx+side*1.448,cy+2.75,1.35+j*.07),(.025,.48,.025),'black',.002)
        for yy in (cy+2.48,cy+3.02):
            for zz in (1.31,1.79):
                q=Y('Van_'+prefix+'_Hatch_Screw',(cx+side*1.47,yy,zz),.014,.01,'gold',8);q.rotation_euler.y=math.pi/2
        # Layered water streaks are narrow irregular rust strips at fasteners.
        for j in range(11):
            yy=cy-3.3+j*.61
            if cy-1.45<yy<cy-.25:continue
            C('Van_'+prefix+'_Drip',(cx+side*1.425,yy,3.19-rng.uniform(.0,.10)),(.008,rng.uniform(.012,.034),rng.uniform(.16,.37)),'rust',.001)
        # Break repeated pristine rooftop silhouettes with a slanted vent hood.
        hood=C('Van_'+prefix+'_Vent_Hood',(cx+.15,cy+1.8,3.85),(.67,.60,.10),'rust',.025);hood.rotation_euler.y=.12 if side>0 else -.08
        for dx in (-.24,.24):C('Van_'+prefix+'_Vent_Mount',(cx+.15+dx,cy+1.8,3.74),(.035,.4,.20),'rust')
    # Funhouse facade: anchored poster boards and actual retaining screws.
    for i,(x,w,body) in enumerate(((12.45,1.12,'EVERY REFLECTION\nTELLS A LIE'),(19.45,1.0,'KEEP MOVING\nTHROUGH THE HALL'))):
        C('FH_Notice_Board_%d'%i,(x,6.59,2.65),(w,.08,.76),'wood')
        C('FH_Notice_Paper_%d'%i,(x,6.541,2.65),(w-.10,.014,.65),'paintcream',.001)
        label('FH_Notice_Type_%d'%i,body,(x,6.528,2.72),.087,'black')
        for dx in (-w*.41,w*.41):
            for zz in (2.36,2.94):
                q=Y('FH_Notice_Screw',(x+dx,6.52,zz),.016,.012,'rust',8);q.rotation_euler.x=math.pi/2
    for x in (11.65,20.45):
        C('FH_Lamp_Mount',(x,6.59,3.8),(.18,.12,.25),'rust')
        B('FH_Lamp_Bracket',(x,6.57,3.8),(x,6.16,3.92),.022)
        C('FH_Lamp_Cage_Top',(x,6.16,3.95),(.29,.25,.06),'rust')
        for dx in (-.11,.11):
            for dy in (-.09,.09):B('FH_Lamp_Cage',(x+dx,6.16+dy,3.62),(x+dx,6.16+dy,3.93),.009)
        C('FH_Lamp_Cage_Base',(x,6.16,3.61),(.27,.23,.04),'rust')
        Y('FH_Lamp_Glass',(x,6.16,3.78),.07,.23,'glass')
        Y('FH_Lamp_Filament',(x,6.16,3.78),.018,.16,'bulb',12)
    # Selectively exposed timber repairs; keep front opening and maze faces clear.
    for j,(x,z,w) in enumerate(((11.8,1.25,.65),(13.9,.9,.70),(18.1,1.1,.55),(20.35,1.65,.6))):
        o=C('FH_Repair_Board_%d'%j,(x,6.71,z),(w,.045,.13),'wood',.004);o.rotation_euler.y=rng.uniform(-.12,.12)
        for dx in (-w*.38,w*.38):
            q=Y('FH_Repair_Nail',(x+dx,6.68,z),.01,.015,'rust',8);q.rotation_euler.x=math.pi/2
    # Uneven mirror oxidation lies at frame margins, not across reflections.
    for o in list(bpy.context.scene.objects):
        if o.name.startswith('FH_Mirror_Silver_'):
            x,y,z=o.location
            for k in range(2):
                xx=x+rng.choice((-1,1))*.585;zz=z+rng.uniform(-.85,.85)
                C('FH_Mirror_Edge_Oxidation',(xx,y+(-.012 if '_-1' in o.name else .012),zz),(.025,.009,rng.uniform(.05,.18)),'rust',.001)
    root['eligible_props']=json.dumps(eligible);root['notes']='Edge-mounted detail; existing openings and paths unchanged; source parts retained hidden for compound collision.'
    bpy.context.view_layer.update()
    return {'status':'applied','eligible_props':eligible,'eligible_count':len(eligible),'source_parts_retained':True}

def repair_backstage_container_collision_seams():
    """In-memory repair for already-integrated RF containers; never saves.
    Separate closed component seams by sub-millimetre clearances so the exporter's
    remove_doubles cannot weld adjacent wall wedges / bail segments together.
    All source components stay closed; the cavity remains unfilled.
    """
    from assemble_props import assemble
    families={'OpenMaintenanceBucket','PaintCan_Open','PaintCan_Closed'}
    fixed=[]
    for ob in list(bpy.context.scene.objects):
        if not (ob.get('PropActorTag') and ob.name.startswith('RF_') and ob.get('asset_family') in families):continue
        if ob.get('compound_seams_separated'):continue
        keys=json.loads(ob.get('collision_source_parts','[]'));parts=[bpy.data.objects[k] for k in keys if k in bpy.data.objects]
        if not parts:continue
        for part in parts:
            if part.get('compound_seams_separated'):continue
            part.data=part.data.copy();center=sum((v.co for v in part.data.vertices),Vector())/len(part.data.vertices)
            for v in part.data.vertices:v.co=center+(v.co-center)*.999
            part.data.update();part['compound_seams_separated']=True
        name=ob.name;origin=ob.location.copy();props=dict(ob.items());family=ob['asset_family']
        bpy.data.objects.remove(ob,do_unlink=True)
        replacement=assemble(name,parts,origin,family)
        for key,value in props.items():replacement[key]=value
        replacement['compound_seams_separated']=True
        replacement['collision_policy']='Separate closed convex wall, base, label and bail components; no cavity-filling hull'
        for p in parts:p.hide_render=True;p.hide_set(True);p['assembly_owner']=name
        fixed.append(name)
    return fixed
