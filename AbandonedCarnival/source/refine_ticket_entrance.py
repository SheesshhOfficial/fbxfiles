"""Grounded ticket-kiosk and entrance detail pass.

The coordinator calls refine_ticket_entrance() in the loaded art-pass scene.
This module never opens, saves, or exports a .blend. Geometry is original.
New props use separate closed, convex solid components for the UCX exporter.
The central opening and the bounded arrival forecourt receive no new obstacles.
"""
import math
import random
import bpy
import bmesh
from mathutils import Vector
from assemble_props import assemble


PREFIX = "Entrance detail "
VERSION = "ticket_entrance_refinement_v1"


def refine_ticket_entrance():
    scene = bpy.context.scene
    if scene.get(VERSION):
        return {"already_applied": True, "version": VERSION}
    rng = random.Random(7419)
    created, replaced, props = [], [], []
    mats = {m.name: m for m in bpy.data.materials}

    def plain(name, color, rough=.8, metal=0., emission=0.):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1)
        p.inputs['Roughness'].default_value = rough
        p.inputs['Metallic'].default_value = metal
        if emission:
            p.inputs['Emission Color'].default_value = (*color, 1)
            p.inputs['Emission Strength'].default_value = emission
        m['provenance'] = 'Original material; no external geometry or artwork'
        mats[name] = m
        return m

    plain('Entrance recessed lime mortar', (.105, .11, .095), .98)
    plain('Entrance aged ticket stock', (.43, .35, .20), .96)
    plain('Entrance recycled carton', (.16, .104, .055), .95)
    plain('Entrance faded ink', (.08, .034, .016), .98)
    plain('Entrance dull galvanized metal', (.16, .18, .17), .73, .45)
    plain('Entrance dusty lamp glass', (.36, .21, .085), .38, 0., .65)
    plain('Entrance charcoal enamel', (.025, .031, .029), .67, .2)
    paint_cream = mats.get('PaintCream', mats['cream'])
    paint_red = mats.get('PaintRed', mats['red'])

    def uv_project(me, offset=(0., 0.)):
        uv = me.uv_layers.active or me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            axis = max(range(3), key=lambda a: abs(p.normal[a]))
            axes = [a for a in range(3) if a != axis]
            m = me.materials[p.material_index]
            # Long grain follows the longer physical face dimension.
            if m.name == 'wood':
                spans = {a: max(me.vertices[i].co[a] for i in p.vertices) -
                         min(me.vertices[i].co[a] for i in p.vertices) for a in axes}
                long_axis = max(axes, key=lambda a: spans[a])
                axes = [next(a for a in axes if a != long_axis), long_axis]
            tile = float(m.get('physical_tile_m', 1.))
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (co[axes[0]] / tile + offset[0],
                                  co[axes[1]] / tile + offset[1])

    def mesh(name, vertices, faces, mat, location=(0, 0, 0), bevel=0., smooth=False):
        me = bpy.data.meshes.new(PREFIX + name)
        me.from_pydata(vertices, [], faces)
        me.materials.append(mats[mat] if isinstance(mat, str) else mat)
        me.update()
        bm = bmesh.new()
        bm.from_mesh(me)
        if bevel:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2,
                            affect='EDGES', clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(me)
        bm.free()
        me.update()
        uv_project(me, (rng.random() * 2, rng.random() * 2))
        for p in me.polygons:
            p.use_smooth = smooth and len(p.vertices) == 4
        ob = bpy.data.objects.new(PREFIX + name, me)
        bpy.context.collection.objects.link(ob)
        ob.location = location
        ob['detail_pass'] = VERSION
        ob['geometry_provenance'] = 'Original project geometry'
        created.append(ob)
        return ob

    def box(name, loc, size, mat, bevel=.004):
        x, y, z = (s / 2 for s in size)
        vs = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
              (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
        fs = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        return mesh(name, vs, fs, mat, loc, min(bevel, min(size) * .2))

    def cylinder(name, loc, radius, height, mat, n=20, top_radius=None):
        rt = radius if top_radius is None else top_radius
        vs = [(r * math.cos(i * math.tau / n), r * math.sin(i * math.tau / n), z)
              for r, z in [(radius, -height / 2), (rt, height / 2)] for i in range(n)]
        fs = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
        fs += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        ob = mesh(name, vs, fs, mat, loc)
        uv = ob.data.uv_layers.active
        # Explicit seam-safe cylindrical UVs. Planar cap UVs stay nondegenerate.
        tile = float(ob.data.materials[0].get('physical_tile_m', 1.))
        for p in ob.data.polygons:
            if len(p.vertices) != 4:
                continue
            angles = [math.atan2(ob.data.vertices[v].co.y, ob.data.vertices[v].co.x)
                      % math.tau for v in p.vertices]
            if max(angles) - min(angles) > math.pi:
                angles = [a + math.tau if a < math.pi else a for a in angles]
            for li, a in zip(p.loop_indices, angles):
                co = ob.data.vertices[ob.data.loops[li].vertex_index].co
                uv.data[li].uv = (a * max(radius, rt) / tile, co.z / tile)
            p.use_smooth = n > 12
        return ob

    def rod(name, a, b, radius, mat='rust', n=12):
        a, b = Vector(a), Vector(b)
        ob = cylinder(name, (a+b)/2, radius, (b-a).length, mat, n)
        ob.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
        return ob

    def bolt(name, x, y, z, radius=.014):
        ob = cylinder(name, (x,y,z), radius, .012, 'rust', 6)
        ob.rotation_euler.x = math.pi/2
        return ob

    def replace(ob):
        ob.hide_render = True
        ob.hide_set(True)
        ob['visual_replaced'] = True
        if 'PropActorTag' in ob:
            del ob['PropActorTag']
        replaced.append(ob.name)

    def prop(name, parts, origin, family):
        smooth = [p.use_smooth for part in parts if part.type == 'MESH'
                  for p in part.data.polygons]
        ob = assemble(PREFIX + name, parts, origin, family)
        for face, shading in zip(ob.data.polygons, smooth):
            face.use_smooth = shading
        ob['detail_pass'] = VERSION
        ob['geometry_provenance'] = 'Original project geometry'
        ob['collision_strategy'] = 'Separate closed convex component hulls; no assembly hull'
        for part in parts:
            part.hide_render = True
            part.hide_set(True)
        props.append(ob)
        created.append(ob)
        return ob

    def lettering(name, body, pos, size, mat='Entrance faded ink'):
        cu = bpy.data.curves.new(PREFIX + name, 'FONT')
        cu.body = body
        cu.align_x = 'CENTER'
        cu.align_y = 'CENTER'
        cu.size = size
        cu.extrude = .0006
        original = bpy.data.objects.get('Entrance name lettering')
        if original and original.type == 'FONT':
            cu.font = original.data.font
        cu.materials.append(mats[mat] if isinstance(mat, str) else mat)
        ob = bpy.data.objects.new(PREFIX + name, cu)
        bpy.context.collection.objects.link(ob)
        ob.location = pos
        ob.rotation_euler.x = math.pi/2
        bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        world = ob.matrix_world.copy()
        bpy.data.objects.remove(ob, do_unlink=True)
        ob = bpy.data.objects.new(PREFIX + name, me)
        bpy.context.collection.objects.link(ob)
        ob.matrix_world = world
        bpy.data.curves.remove(cu)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-8, edges=list(bm.edges))
        degenerate = [f for f in bm.faces if f.calc_area() <= 1e-12]
        if degenerate:
            bmesh.ops.delete(bm, geom=degenerate, context='FACES')
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(me)
        bm.free()
        me.update()
        # The font tessellator can retain collapsed cap polygons after an edge
        # dissolve. Rebuild from Blender's final face areas, before making UVs.
        if any(p.area <= 1e-12 for p in me.polygons):
            cleaned = bpy.data.meshes.new(PREFIX + name + ' cleaned')
            cleaned.from_pydata([tuple(v.co) for v in me.vertices], [],
                                [tuple(p.vertices) for p in me.polygons if p.area > 1e-12])
            for m in me.materials:
                cleaned.materials.append(m)
            cleaned.update()
            ob.data = cleaned
            bpy.data.meshes.remove(me)
            me = cleaned
        uv_project(me)
        ob['detail_pass'] = VERSION
        created.append(ob)
        return ob

    # Dressed masonry with visible, recessed lime joints and staggered courses.
    for ob in list(scene.objects):
        if ob.name.startswith('Gate masonry pier'):
            replace(ob)
    for x in (-5., 5.):
        box('recessed pier mortar core', (x,-23,1.35), (.746,.746,2.7),
            'Entrance recessed lime mortar', 0.)
        for course in range(9):
            z = .15 + course * .3
            # Four individual blocks per course, alternating joint direction.
            if course % 2 == 0:
                for dx in (-.205,.205):
                    for dy in (-.205,.205):
                        box('staggered pier ashlar', (x+dx,-23+dy,z),
                            (.394,.394,.284), 'concrete', .009)
            else:
                for dy in (-.205,.205):
                    box('long pier ashlar', (x,-23+dy,z),
                        (.804,.394,.284), 'concrete', .009)
        box('pier plinth course', (x,-23,.11), (.92,.92,.21), 'concrete', .016)
        box('pier upper cornice', (x,-23,2.73), (.89,.89,.11), 'concrete', .014)
        box('pier weathered coping', (x,-23,2.825), (1.01,1.01,.09), 'concrete', .014)
        box('upright foot plate', (x,-23,2.89), (.29,.29,.035), 'rust', .006)
        for dx in (-.105,.105):
            for dy in (-.105,.105):
                cylinder('upright anchor nut', (x+dx,-23+dy,2.917), .023,.025,'rust',6)
        cylinder('upright slip collar', (x,-23,3.01), .112,.19,'rust',24)

    # Thin metal rails close the existing fence panels only, outside the gate opening.
    for x in (-5.7,5.7):
        for z in (.53,2.2):
            box('wrought fence horizontal rail', (x,-23,z), (1.88,.055,.065), 'rust', .004)
        for xx in (x-.73,x+.73):
            box('fence bolted splice plate', (xx,-23.046,2.2), (.13,.027,.14), 'rust', .003)
            bolt('fence splice bolt', xx,-23.066,2.2)

    # Sign supports visibly terminate at the arch. Remove the original loose posts.
    for ob in list(scene.objects):
        if ob.name.startswith('Entrance name mounting'):
            replace(ob)
    for x in (-3.15,3.15):
        top = 5.1 + .9 * math.sin(math.pi * (x+5.)/10.)
        box('sign arch hanger strap', (x,-22.94,(5.04+top)/2),
            (.10,.075,top-5.04+.16), 'rust', .006)
        box('sign arch hanger shoe', (x,-22.94,top), (.25,.16,.11), 'rust', .004)
        for z in (5.08,5.24):
            bolt('entrance sign hanger bolt', x,-23.076,z,.021)
    for x in (-4.38,4.38):
        for z in (4.51,5.19):
            bolt('entrance sign edge rivet', x,-23.076,z,.016)

    # Pier-mounted maintenance lanterns: real arms, cage, caps, and restrained spill.
    for side in (-1,1):
        px = side*5.
        lx = side*5.45
        box('lantern wall fixing plate',(px,-23.018,3.55),(.12,.12,.32),'rust',.008)
        rod('lantern cantilever arm',(px,-23,3.65),(lx,-23,3.65),.027)
        rod('lantern diagonal arm brace',(px,-23,3.40),(lx,-23,3.65),.018)
        rod('lantern suspension stem',(lx,-23,3.65),(lx,-23,3.47),.016)
        cylinder('lantern weather cap',(lx,-23,3.45),.17,.10,'rust',24,top_radius=.065)
        cylinder('lantern glass cylinder',(lx,-23,3.23),.095,.35,
                 'Entrance dusty lamp glass',24)
        cylinder('lantern bottom metal cup',(lx,-23,3.035),.135,.045,'rust',24)
        for a in range(6):
            q = math.tau*a/6
            xx, yy = lx+.115*math.cos(q), -23+.115*math.sin(q)
            rod('lantern cage upright',(xx,yy,3.045),(xx,yy,3.43),.009)
        d=bpy.data.lights.new(PREFIX+'pier practical','POINT')
        d.energy=42
        d.color=(1.,.55,.24)
        d.shadow_soft_size=.13
        ob=bpy.data.objects.new(PREFIX+'pier practical',d)
        bpy.context.collection.objects.link(ob)
        ob.location=(lx,-23.17,3.23)
        ob['detail_pass']=VERSION
        created.append(ob)

    # The ticket booth is a cashier kiosk, so remove the generic prize-game display.
    for ob in list(scene.objects):
        if not ob.name.startswith('Ticket booth'):
            continue
        # Stand the fascia in front of the roof drainage, rather than letting a
        # gutter cut across the lettering. The new outrigger brackets carry it.
        if any(ob.name.startswith('Ticket booth '+k) for k in
               ('backing','frame','lettering','marquee bulb')):
            ob.location.y -= .48
        if ob.type=='LIGHT' and 'warm spill' in ob.name:
            ob.location.y = -23.28
        if any(k in ob.name for k in (' bottle',' prize',' roof strip',' bin',' mounting')):
            replace(ob)
        elif ob.type=='FONT' and 'lettering' in ob.name:
            original=bpy.data.objects.get('Entrance name lettering')
            if original and original.type=='FONT':
                ob.data.font=original.data.font
            ob.data.materials.clear()
            ob.data.materials.append(mats['Entrance faded ink'])
        elif ob.type=='MESH' and 'backing' in ob.name:
            ob.data=ob.data.copy()
            ob.data.materials.clear()
            ob.data.materials.append(paint_cream)
            uv_project(ob.data)
        elif ob.type=='MESH' and 'front skirt' in ob.name:
            ob.data = ob.data.copy()
            for i, m in enumerate(ob.data.materials):
                if m and m.name in ('red','cream'):
                    ob.data.materials[i] = paint_red if m.name=='red' else paint_cream
            uv_project(ob.data)

    # Subtly dented, solid corrugated roof sheets, proper supporting purlins and laps.
    # The plain solid deck is also a recognized box for the environment UCX exporter;
    # do not derive a convex hull from corrugations or from the whole kiosk.
    deck=box('solid weathered roof deck',(8,-21.,3.28),(4.50,3.63,.065),'wood',0.)
    deck.rotation_euler.x=.08
    for panel in range(5):
        width=.93
        x0=5.70+panel*.91
        steps=28
        top=[]
        for j in range(steps+1):
            x=x0+width*j/steps
            wav=.026*math.cos(j*math.pi)
            dent=-.018*math.exp(-((j-11)/5)**2) if panel==3 else 0.
            for y in (-22.84,-19.16):
                top.append((x,y,3.36+.08*(y+21)+wav+dent))
        vs=top+[(x,y,z-.014) for x,y,z in top]
        n=len(top)
        fs=[]
        for j in range(steps):
            a=2*j
            fs += [(a,a+2,a+3,a+1),(a+n,a+1+n,a+3+n,a+2+n),
                   (a,a+n,a+2+n,a+2),(a+1,a+3,a+3+n,a+1+n)]
        fs += [(0,1,n+1,n),(2*steps,2*steps+n,2*steps+n+1,2*steps+1)]
        mesh('corrugated kiosk roof sheet',vs,fs,'rust')
        for y in (-22.47,-21.,-19.55):
            for xx in (x0+.08,x0+.81):
                j=(xx-x0)/width*steps
                lo=int(j)
                hi=min(steps,lo+1)
                wave=(1-(j-lo))*.026*math.cos(lo*math.pi)+(j-lo)*.026*math.cos(hi*math.pi)
                dent=-.018*math.exp(-((j-11)/5)**2) if panel==3 else 0.
                cylinder('roof washer screw',(xx,y,3.36+.08*(y+21)+wave+dent+.007),
                         .018,.016,'Entrance dull galvanized metal',10)
    for y in (-22.43,-21.,-19.57):
        box('roof timber purlin',(8,y,3.25+.08*(y+21)),(4.37,.11,.14),'wood',.009)
    for x in (5.84,10.18):
        ob=box('roof side flashing',(x,-21.,3.37),(.075,3.8,.045),'rust',.004)
        ob.rotation_euler.x=.08
    # Downpipe stays beyond the kiosk edge, far outside the entrance opening.
    box('eaves gutter bottom',(8,-22.91,3.14),(4.62,.15,.025),'rust',.003)
    box('eaves gutter outer lip',(8,-22.98,3.19),(4.62,.022,.12),'rust',.003)
    box('eaves gutter rear lip',(8,-22.84,3.19),(4.62,.022,.12),'rust',.003)
    for x in (5.96,7.,8.,9.,10.12):
        box('gutter support strap',(x,-22.88,3.08),(.04,.24,.035),'rust',.003)
    rod('kiosk rainwater downpipe',(10.25,-22.91,.30),(10.25,-22.91,3.16),.045)
    rod('downpipe drain elbow',(10.25,-22.91,.30),(10.49,-23.06,.13),.045)
    for z in (.55,1.75,2.8):
        box('downpipe anchor strap',(10.25,-22.88,z),(.15,.15,.035),'rust',.003)

    # Cashier window with solid timber jambs and a useful hand-through opening.
    for x in (6.30,9.70):
        box('ticket window jamb',(x,-22.405,2.12),(.14,.16,1.49),'wood',.009)
    for z in (1.47,2.82):
        box('ticket window cross rail',(8,-22.405,z),(3.52,.16,.13),'wood',.009)
    for x in (6.61,6.95,7.29,7.63,7.97,8.31,8.65,8.99,9.33):
        bottom=1.77 if 7.60<x<8.34 else 1.53
        rod('ticket security grille',(x,-22.43,bottom),(x,-22.43,2.77),.013,
            'Entrance charcoal enamel')
    box('cashier slot upper rail',(7.97,-22.43,1.77),(.85,.045,.045),
        'Entrance charcoal enamel',.003)
    for x in (6.30,9.70):
        for z in (1.47,2.82):
            bolt('window frame fixing bolt',x,-22.491,z,.018)
    # The original sign bulb row now has lamp bases and a metal cable raceway.
    box('ticket marquee metal raceway',(8,-23.08,3.56),(3.92,.11,.07),'rust',.005)
    for i in range(11):
        x=6.1+i*.38
        rod('ticket marquee lamp stem',(x,-23.08,3.56),(x,-23.21,3.65),.022,
            'Entrance charcoal enamel')
    for x in (6.4,9.6):
        box('kiosk sign rear strap',(x,-22.98,3.08),(.09,.10,.60),'rust',.005)
        box('kiosk sign outrigger bracket',(x,-22.67,3.08),(.08,.62,.08),'rust',.004)
        for z in (2.97,3.39):
            bolt('kiosk sign bolt',x,-23.136,z,.015)

    # A fixed plate attached to the timber skirt, with lettering on its surface.
    box('admission price plate',(6.82,-22.482,.83),(.78,.026,.50),paint_cream,.007)
    lettering('admission plate text','ADMISSION\nONE TICKET',(6.82,-22.499,.83),.077)
    for dx in (-.34,.34):
        for dz in (-.20,.20):
            bolt('admission plate corner screw',6.82+dx,-22.501,.83+dz,.011)

    # Bring existing loose stools into the same prop identity/collision convention.
    seats=[o for o in scene.objects if o.name.startswith('Ticket booth stool seat')
           and not o.get('_assembly_source')]
    legs=[o for o in scene.objects if o.name.startswith('Ticket booth stool leg')
          and not o.get('_assembly_source')]
    for idx, seat in enumerate(seats):
        stoolparts=[seat]+[leg for leg in legs if abs(leg.location.x-seat.location.x)<.4]
        prop('cashier stool %02d'%idx,stoolparts,(seat.location.x,seat.location.y,.15),
             'TicketStool')

    # Open supply carton: each thin wall is a separate sealed box component.
    x,y,z=8.73,-22.40,1.368
    parts=[box('ticket carton bottom',(x,y,z+.012),(.51,.32,.024),
               'Entrance recycled carton',.002)]
    for sx in (-1,1):
        parts.append(box('ticket carton end',(x+sx*.247,y,z+.105),(.016,.32,.19),
                         'Entrance recycled carton',.002))
    for sy in (-1,1):
        parts.append(box('ticket carton wall',(x,y+sy*.152,z+.105),(.49,.016,.19),
                         'Entrance recycled carton',.002))
    prop('ticket supply carton',parts,(x,y,z),'TicketCarton')

    def ticket_roll(index,x,y,z):
        # End-on wound paper roll, with a shallow printed cardboard core disk.
        p=[cylinder('ticket roll wound stock',(x,y,z+.092),.092,.084,
                    'Entrance aged ticket stock',32)]
        p[0].rotation_euler.x=math.pi/2
        core=cylinder('ticket roll core shadow',(x,y-.045,z+.092),.022,.004,
                      'Entrance faded ink',24)
        core.rotation_euler.x=math.pi/2
        p.append(core)
        for radius in (.041,.059,.077):
            # Segmented, sealed thin rods imply visible paper winding at close range.
            for q in range(18):
                a,b=math.tau*q/18,math.tau*(q+.82)/18
                p.append(rod('ticket roll winding',
                             (x+radius*math.cos(a),y-.0435,z+.092+radius*math.sin(a)),
                             (x+radius*math.cos(b),y-.0435,z+.092+radius*math.sin(b)),
                             .0007,'Entrance faded ink',6))
        return prop('ticket roll %02d'%index,p,(x,y,z),'TicketRoll')
    ticket_roll(0,8.59,-22.40,1.392)
    ticket_roll(1,8.84,-22.40,1.392)
    ticket_roll(2,7.48,-22.52,1.368)

    # Lidded cashier cash tin, with a handle assembled from solid bent strips.
    x,y,z=7.86,-22.41,1.368
    p=[box('cash tin body',(x,y,z+.065),(.36,.25,.13),'Entrance charcoal enamel',.012),
       box('cash tin overhanging lid',(x,y,z+.139),(.38,.27,.026),
           'Entrance charcoal enamel',.006)]
    for dx in (-.07,.07):
        p.append(box('cash tin handle mounting',(x+dx,y,z+.17),(.022,.023,.05),
                     'Entrance dull galvanized metal',.003))
    p.append(box('cash tin handle grip',(x,y,z+.198),(.16,.026,.022),
                 'Entrance dull galvanized metal',.004))
    p.append(box('cash tin latch',(x,y-.145,z+.102),(.042,.018,.053),'rust',.003))
    prop('cashier locking tin',p,(x,y,z),'CashTin')

    def cup(index,x,y,z):
        p=[cylinder('discarded paper cup',(x,y,z+.067),.038,.134,
                    'Entrance aged ticket stock',24,top_radius=.052),
           cylinder('paper cup rolled rim',(x,y,z+.136),.055,.012,
                    'Entrance aged ticket stock',24),
           cylinder('paper cup fitted lid',(x,y,z+.146),.053,.012,
                    'Entrance charcoal enamel',24,top_radius=.049)]
        return prop('lidded paper cup %02d'%index,p,(x,y,z),'LiddedPaperCup')
    cup(0,9.28,-22.51,1.368)
    cup(1,10.82,-22.66,.055)

    # Closed lidded bin with lid, grab handle, rolled rim and stamped vertical flutes.
    x,y,z=10.64,-22.06,.055
    p=[cylinder('waste bin tapered body',(x,y,z+.42),.27,.84,
                'Entrance dull galvanized metal',32,top_radius=.31),
       cylinder('waste bin bottom chime',(x,y,z+.035),.282,.055,'rust',32),
       cylinder('waste bin lid rim',(x,y,z+.858),.33,.045,
                'Entrance dull galvanized metal',32),
       cylinder('waste bin crowned lid',(x,y,z+.908),.316,.07,
                'Entrance dull galvanized metal',32,top_radius=.24)]
    for q in range(16):
        a=math.tau*q/16
        p.append(rod('waste bin stamped flute',
                     (x+.279*math.cos(a),y+.279*math.sin(a),z+.10),
                     (x+.311*math.cos(a),y+.311*math.sin(a),z+.78),.009,
                     'Entrance dull galvanized metal',8))
    for dx in (-.075,.075):
        p.append(box('waste bin lid handle foot',(x+dx,y,z+.977),(.025,.033,.065),
                     'rust',.004))
    p.append(box('waste bin lid handle',(x,y,z+1.012),(.178,.033,.027),'rust',.005))
    prop('galvanized lidded waste bin',p,(x,y,z),'GalvanizedWasteBin')

    bpy.context.view_layer.update()
    scene[VERSION] = True
    report = {
        'version': VERSION,
        'created_objects': len(created),
        'eligible_props': len(props),
        'prop_names': [o.name for o in props],
        'prop_families': sorted(set(o['asset_family'] for o in props)),
        'visually_replaced_objects': len(replaced),
        'geometry_provenance': 'Original project geometry; existing project materials/fonts reused',
        'route_scope': '8.99 m clear width between pier coping edges; no new obstacles in the central arrival route',
        'unreal_runtime_verified': False,
    }
    print('TICKET_ENTRANCE_REFINED', report, flush=True)
    return report

