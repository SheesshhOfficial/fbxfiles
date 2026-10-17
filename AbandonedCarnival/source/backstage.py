"""Original, metre-scale carnival funhouse and backstage set dressing.
Entrances and maze gaps are geometry openings. No runtime/collision claims.
"""
import bpy, math, random
from mathutils import Vector

def build_backstage(api):
    get=lambda k: api[k] if isinstance(api,dict) else getattr(api,k)
    cube,cyl,sphere,beam,torus,txt=[get(k) for k in ('cube','cyl','sphere','beam','torus','text')]
    m=get('mats'); rng=random.Random(825)
    def C(n,p,s,mat='wood',b=.025): return cube(n,p,s,m[mat] if isinstance(mat,str) else mat,bevel=b)
    def S(n,p,s,mat): return sphere(n,p,s,m[mat])
    def B(n,a,b,r,mat): return beam(n,a,b,r,m[mat])
    def curve(n,pts,r,mat):
        cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.resolution_u=12;cu.bevel_depth=r;cu.bevel_resolution=3
        sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
        for p,co in zip(sp.points,pts): p.co=(*co,1)
        ob=bpy.data.objects.new(n,cu);bpy.context.collection.objects.link(ob);ob.data.materials.append(m[mat]);return ob
    def plate(n,body,p,size=.3,mat='cream',rot=(math.pi/2,0,0)):
        return txt(n,body,p,size,m[mat],rotation=rot)
    mirror=bpy.data.materials.new('FH_Aged_Silver_Mirror');mirror.use_nodes=True
    bs=mirror.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.44,.53,.55,1);bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.115
    # Concrete raft and timber stage; genuine, central, flush threshold.
    C('FH_Foundation',(16,13,.09),(10.5,12.5,.18),'concrete')
    for ix in range(25):
        C('FH_Floorboard_%02d'%ix,(11.2+ix*.4,13,.22),(.39,12,.12),'wood',.008)
    # The low-cutaway outer shell preserves the sightline into the playable interior.
    for x in (11,21):
        C('FH_Perimeter_Side',(x,13,1.9),(.18,12,3.25),'teal')
        for y in range(7,20): C('FH_Side_Frame',(x,y,1.9),(.23,.10,3.3),'wood')
    C('FH_Back_Wall_Left',(14.9,19,2.2),(7.8,.18,3.9),'teal')
    C('FH_Back_Wall_Right',(20.6,19,2.2),(.8,.18,3.9),'teal')
    C('FH_Rear_Exit_Header',(19.5,19,3.57),(1.4,.18,1.15),'teal')
    for x in (11,12,13,14,15,16,17,18,21): C('FH_Back_Frame',(x,18.88,2.2),(.1,.1,3.9),'wood')
    # Alternating partitions leave 2.6 m clear around their ends; front/back circulation stays open.
    for i,y in enumerate((10.3,13.3,16.3)):
        x=14.55 if i%2==0 else 17.45
        C('FH_Maze_Partition_%d'%i,(x,y,1.65),(6.85,.16,2.75),'red' if i%2 else 'teal')
        C('FH_Maze_Cap_%d'%i,(x,y,3.05),(6.98,.24,.1),'gold')
        for j in range(3):
            mx=x-2.35+j*2.3
            for side in (-1,1):
                yy=y+side*.101
                C('FH_Mirror_Backing_%d_%d_%d'%(i,j,side),(mx,yy,1.75),(1.45,.07,2.22),'black')
                C('FH_Mirror_Silver_%d_%d_%d'%(i,j,side),(mx,yy+side*.045,1.75),(1.23,.018,1.98),mirror,.006)
                for dx in (-.69,.69):C('FH_Mirror_Frame_V',(mx+dx,yy+side*.06,1.75),(.1,.09,2.24),'gold')
                for z in (.65,2.85):C('FH_Mirror_Frame_H',(mx,yy+side*.06,z),(1.47,.09,.1),'gold')
        for xend in (x-3.4,x+3.4):C('FH_Maze_End_Post',(xend,y,1.7),(.18,.25,2.85),'wood')
    # Back roof only: open overhead maze is deliberate cutaway presentation.
    roof=C('FH_Back_Roof_Cutaway',(16,18.2,4.35),(10.5,2.1,.16),'rust');roof.rotation_euler.x=.08
    for x in (11,16,21):B('FH_Roof_Beam',(x,17.1,4.15),(x,19.3,4.4),.07,'wood')
    # Front facade has opening x14.75..17.25. No solid wall behind the clown mouth.
    for x in (12.9,19.1):
        C('FH_Facade_Wing',(x,6.95,2.35),(3.7,.24,4.3),'teal')
        for dx in (-1.4,-.7,0,.7,1.4):C('FH_Facade_Batten',(x+dx,6.78,2.35),(.065,.06,4.25),'cream')
        C('FH_Facade_Base',(x,6.72,.52),(3.7,.14,.38),'rust')
        C('FH_Facade_Cornice',(x,6.75,4.5),(3.8,.2,.18),'gold')
    C('FH_Mounted_Sign_Back',(16,6.72,6.18),(9.7,.28,1.05),'wood')
    C('FH_Mounted_Sign_Face',(16,6.54,6.18),(9.35,.07,.8),'black')
    plate('FH_Hall_Of_Mirrors_Title','HALL OF MIRRORS',(16.0,6.48,6.0),.56,'gold')
    for x in (11.4,20.6):C('FH_Sign_Support',(x,7.02,4.7),(.18,.2,3.1),'rust')
    for k in range(30):S('FH_Marquee_Bulb',(11.37+k*.32,6.49,6.61),(.052,.052,.052),'bulb')
    # Sculptural original jester face built around a real 2.5 m-wide opening.
    S('FH_Clown_Forehead',(16,6.68,4.6),(1.7,.58,1.28),'cream')
    for s in (-1,1):
        S('FH_Clown_Cheek',(16+s*1.56,6.48,3.12),(.55,.51,1.55),'cream')
        S('FH_Clown_Cheek_Rouge',(16+s*1.66,5.98,3.68),(.29,.10,.31),'red')
        S('FH_Clown_Eye_Socket',(16+s*.75,6.12,4.67),(.43,.16,.51),'black')
        S('FH_Clown_Eyelid',(16+s*.75,5.99,4.67),(.32,.08,.36),'cream')
        S('FH_Clown_Pupil',(16+s*.70,5.90,4.65),(.12,.06,.23),'black')
        brow=[(16+s*(.34+t*.83),6.00,5.03+.27*math.sin(t*math.pi)) for t in [j/12 for j in range(13)]]
        curve('FH_Clown_Raised_Brow',brow,.075,'teal')
        for j in range(5):
            a=(16+s*(1.5+j*.08),6.7,4.0+j*.28); b=(16+s*(2.2+.2*math.sin(j)),6.65,4.2+j*.4)
            B('FH_Clown_Hair_Lock',a,b,.19,'rust')
    S('FH_Clown_Nose',(16,5.84,4.12),(.38,.38,.37),'red')
    # Mouth top / descending sides only, with no lower crossbar trip hazard.
    lips=[(14.63,6.13,.32),(14.60,6.10,1.3),(14.58,6.08,2.4),(14.65,6.08,3.4),(15.15,6.03,3.38),(16,6.0,3.05),(16.85,6.03,3.38),(17.35,6.08,3.4),(17.42,6.08,2.4),(17.40,6.10,1.3),(17.37,6.13,.32)]
    curve('FH_Clown_Open_Mouth_Lip',lips,.115,'red')
    for k in range(7):
        x=15.13+k*.29;z=3.12+.2*abs(x-16)
        C('FH_Clown_Upper_Tooth',(x,6.17,z),(.24,.21,.22),'cream',.045)
    # Exit signage and a leaning spare mirror, outside main opening.
    plate('FH_Exit_Label','EXIT',(19.5,18.86,3.55),.28,'bulb')
    spare=C('FH_Spare_Mirror_Frame',(20.3,6.0,1.25),(1.1,.14,2.2),'gold');spare.rotation_euler.x=-.16
    ob=C('FH_Spare_Mirror_Glass',(20.3,5.90,1.25),(.91,.025,1.96),mirror);ob.rotation_euler.x=-.16
    # Maintenance yard: opposing caravans retain open door cuts.
    def caravan(prefix,cx,cy,inward,paint):
        C(prefix+'_Chassis',(cx,cy,.53),(2.65,6.9,.22),'rust')
        C(prefix+'_Floor',(cx,cy,.78),(2.75,7,.20),'wood')
        C(prefix+'_Roof',(cx,cy,3.56),(2.88,7.1,.18),'cream',.15)
        for xx in (cx-1.36,cx+1.36):
            inside=(xx>cx)==(inward>0)
            if inside:
                # Door hole centered at cy-.85, 0.95 m wide, clear to 2.80m.
                for ya,yb in ((cy-3.5,cy-1.35),(cy-.35,cy+3.5)):
                    C(prefix+'_Side_Panel',(xx,(ya+yb)/2,2.2),(.10,yb-ya,2.65),paint)
                C(prefix+'_Door_Header',(xx,cy-.85,3.19),(.10,1,.65),paint)
            else:C(prefix+'_Outer_Side',(xx,cy,2.2),(.10,7,2.65),paint)
            if inside:
                for ya,yb in ((cy-3.5,cy-1.35),(cy-.35,cy+3.5)):
                    C(prefix+'_Lower_Trim',(xx,(ya+yb)/2,1.01),(.14,yb-ya,.12),'rust')
            else:C(prefix+'_Lower_Trim',(xx,cy,1.01),(.14,7,.12),'rust')
            C(prefix+'_Upper_Trim',(xx,cy,3.38),(.14,7,.09),'rust')
            # Horizontal sheet seams suggest aged aluminum skins.
            for z in (1.15,1.4,1.65,1.9,2.15,2.4,2.65,2.9,3.15):
                for ya,yb in ((cy-3.48,cy-1.4),(cy-.3,cy+3.48)):
                    C(prefix+'_Corrugation',(xx+(.055 if xx>cx else -.055),(ya+yb)/2,z),(.025,yb-ya,.025),'cream',.003)
            for wy in (cy-2.35,cy+1.55):
                C(prefix+'_Window_Gasket',(xx+(.08 if xx>cx else -.08),wy,2.45),(.08,1.3,.95),'black',.04)
                C(prefix+'_Window_Glass',(xx+(.13 if xx>cx else -.13),wy,2.45),(.025,1.12,.77),'glass',.02)
                for dy in (-.66,.66):C(prefix+'_Window_Frame',(xx+(.16 if xx>cx else -.16),wy+dy,2.45),(.05,.05,1.0),'rust')
                for zz in (1.98,2.92):C(prefix+'_Window_Frame',(xx+(.16 if xx>cx else -.16),wy,zz),(.05,1.34,.05),'rust')
                C(prefix+'_Window_Mullion',(xx+(.16 if xx>cx else -.16),wy,2.45),(.05,.05,.9),'cream')
            for j in range(17):
                yy=rng.uniform(cy-3.4,cy+3.4)
                if inside and cy-1.4<yy<cy-.3:continue
                C(prefix+'_Paint_Loss',(xx+(.06 if xx>cx else -.06),yy,rng.uniform(1.1,1.8)),(.012,rng.uniform(.09,.3),rng.uniform(.07,.33)),'rust',.005)
        for yy in (cy-3.5,cy+3.5):C(prefix+'_End_Cap',(cx,yy,2.2),(2.72,.10,2.65),paint)
        # Ajar door is a distinct leaf swung clear of doorway.
        dx=cx+inward*1.8
        door=C(prefix+'_Open_Door',(dx,cy,1.82),(.10,.94,1.98),paint);door.rotation_euler.z=inward*.95
        # Three treads give four equal 0.22 m rises to the 0.88 m floor.
        C(prefix+'_Entry_Step_Upper',(cx+inward*1.68,cy-.85,.61),(.66,1.10,.10),'rust')
        C(prefix+'_Entry_Step_Middle',(cx+inward*2.18,cy-.85,.39),(.35,1.10,.10),'rust')
        C(prefix+'_Entry_Step_Lower',(cx+inward*2.53,cy-.85,.17),(.35,1.10,.10),'wood')
        for off,z in ((1.68,.56),(2.18,.34),(2.53,.12)):
            for dy in (-.45,.45):
                C(prefix+'_Step_Support',(cx+inward*off,cy-.85+dy,z/2),(.07,.07,z),'rust')
        for yy in (cy-2.15,cy+2.15):
            B(prefix+'_Axle',(cx-1.52,yy,.5),(cx+1.52,yy,.5),.09,'rust')
            for xx in (cx-1.48,cx+1.48):
                wheel=torus(prefix+'_Tire',(xx,yy,.51),.35,.13,m['black']);wheel.rotation_euler.y=math.pi/2
                hub=cyl(prefix+'_Wheel_Hub',(xx,yy,.51),.25,.12,m['rust']);hub.rotation_euler.y=math.pi/2
        for x in (cx-.9,cx+.9):B(prefix+'_Tow_A_Frame',(x,cy-3.3,.52),(cx,cy-4.3,.48),.065,'rust')
        cyl(prefix+'_Hitch_Jack',(cx,cy-4,.29),.045,.45,m['rust'])
        for yy in (cy-1.8,cy+1.8):
            cyl(prefix+'_Roof_Vent',(cx,yy,3.72),.30,.14,m['rust'])
        C(prefix+'_Interior_Bench',(cx-inward*.7,cy+1.3,1.12),(.65,2.3,.46),'red')
    caravan('BY_Caravan_A',12.6,-4.6,1,'cream')
    caravan('BY_Caravan_B',20.7,-4.0,-1,'teal')
    def pallet(n,x,y,z):
        for xx in (-.5,0,.5):C(n+'_Runner',(x+xx,y,z+.08),(.12,1.1,.15),'wood')
        for j in range(6):C(n+'_Deck',(x,y-.5+j*.2,z+.19),(1.2,.15,.08),'wood',.01)
    for k in range(5):pallet('BY_Pallet_Stack_%d'%k,15.4,-1.0,k*.25)
    for k in range(3):pallet('BY_Pallet_Low_%d'%k,17.1,-8.5,k*.25)
    for j,(x,y,z) in enumerate(((14.7,-8.7,.5),(15,-8.8,1.45),(18.8,.2,.65),(19.8,.4,.55))):
        C('BY_Crate_%d_Core'%j,(x,y,z),(1.05,1.0,.9),'wood')
        for dx in (-.45,.45):
            for yy in (y-.52,y+.52):C('BY_Crate_%d_Straps'%j,(x+dx,yy,z),(.09,.05,.95),'rust')
        for xx in (x-.53,x+.53):
            for k in range(5):C('BY_Crate_%d_Slat'%j,(xx,y,z-.4+k*.2),(.04,1,.04),'cream',.004)
    # Service generator, protective roll cage, radiator fins, and hose runs.
    C('BY_Generator_Block',(17.0,-3.0,.65),(1.35,.85,.85),'gold')
    C('BY_Generator_Engine',(17.15,-3.0,.76),(.55,.94,.6),'black')
    for i in range(10):C('BY_Generator_Radiator_Fin',(16.43,-3.39+i*.085,.7),(.055,.028,.63),'rust')
    for x in (16.28,17.72):
        curve('BY_Generator_Cage',[(x,-3.53,.2),(x,-3.53,1.2),(x,-2.47,1.2),(x,-2.47,.2)],.045,'rust')
    B('BY_Generator_Exhaust',(17.3,-2.65,.9),(17.3,-2.65,1.45),.045,'rust')
    for k in range(2):
        pts=[]
        for j in range(90):
            t=j/89;pts.append((17.1+1.5*math.sin(t*9+k)*t,-3.5-t*3,.07))
        curve('BY_Loose_Rubber_Hose',pts,.024,'black')
    for k in range(3):
        tr=torus('BY_Coiled_Service_Hose',(18.15,-4.2,.10+k*.035),.37+k*.045,.025,m['black'])
    # Retired passenger bench shells, structural legs and lap bars.
    for row,(x,y) in enumerate(((17.5,-.4),(18.2,-7.0))):
        C(('BY_Retired_Seat_%d_Chassis' % row),(x,y,.45),(1.7,.80,.15),'rust')
        for dx in (-.44,.44):
            C(('BY_Retired_Seat_%d_Cushion' % row),(x+dx,y,.65),(.70,.65,.18),'red',.10)
            back=C(('BY_Retired_Seat_%d_Back' % row),(x+dx,y+.29,1.02),(.70,.16,.68),'teal',.09);back.rotation_euler.x=.12
        for dx in (-.68,.68):
            B(('BY_Retired_Seat_%d_Leg' % row),(x+dx,y,.15),(x+dx,y,.53),.055,'rust')
            curve(('BY_Retired_Seat_%d_Rail' % row),[(x+dx,y+.37,.6),(x+dx,y+.40,1.5),(x+dx,y-.3,1.45),(x+dx,y-.4,.8)],.035,'rust')
        B(('BY_Retired_Seat_%d_Lapbar' % row),(x-.68,y-.37,.85),(x+.68,y-.37,.85),.035,'rust')
    for x,y in ((14.5,-6.5),(18.7,-9),(15.4,1)):
        cyl('BY_Service_Drum',(x,y,.48),.36,.95,m['rust'])
        for z in (.13,.8):torus('BY_Drum_Rib',(x,y,z),.36,.025,m['black'])
    for x,y in ((14.5,-9.6),(18.5,-8.9),(15.2,-7.1)):
        torus('BY_Discarded_Tire',(x,y,.18),.35,.13,m['black'])
    # Light vegetation concentrated at prop bases; preserve center aisle clearance.
    for j in range(75):
        x=rng.choice((11.1,14.15,19.2,22.2))+rng.uniform(-.35,.35);y=rng.uniform(-9.5,1)
        for k in range(3):
            a=(x+rng.uniform(-.15,.15),y+rng.uniform(-.15,.15),.08)
            b=(a[0]+rng.uniform(-.16,.16),a[1]+rng.uniform(-.16,.16),rng.uniform(.27,.70))
            B('BY_Grass_Stem',a,b,.014,'leaf')
    # Bake coherent movable assemblies as one mesh per placed prop.
    # Evaluated meshes include bevels, and preserve material slots / winding.
    def consolidate(prefix,family):
        parts=[o for o in list(bpy.context.scene.objects) if o.name.startswith(prefix+'_') and o.type in {'MESH','CURVE'}]
        if not parts:return
        baked=[];dg=bpy.context.evaluated_depsgraph_get()
        for ob in parts:
            mesh=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),depsgraph=dg)
            new=bpy.data.objects.new(ob.name+'_Baked',mesh);bpy.context.collection.objects.link(new);new.matrix_world=ob.matrix_world.copy()
            bpy.data.objects.remove(ob,do_unlink=True);baked.append(new)
        bpy.ops.object.select_all(action='DESELECT')
        for ob in baked:ob.select_set(True)
        bpy.context.view_layer.objects.active=baked[0];bpy.ops.object.join()
        ob=bpy.context.object;ob.name=prefix;ob['PropActorTag']=True;ob['asset_family']=family
        # Explicit joined UVs also cover any converted curve rail/cage tubes.
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.015)
        bpy.ops.object.mode_set(mode='OBJECT')
    for k in range(5):consolidate('BY_Pallet_Stack_%d'%k,'wooden_pallet')
    for k in range(3):consolidate('BY_Pallet_Low_%d'%k,'wooden_pallet')
    for k in range(4):consolidate('BY_Crate_%d'%k,'timber_shipping_crate')
    for k in range(2):consolidate('BY_Retired_Seat_%d'%k,'retired_ride_bench')
    consolidate('BY_Generator','portable_generator')
    return {'funhouse_entry':(16,6.2,.3),'funhouse_mirror_material':mirror.name,'backstage_aisle':(16.7,-5,.1)}
