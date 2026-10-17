"""Cycle 5: manufacture-scale funhouse facade refinement.

Usage, with the evolving carnival scene already open::

    from refine_funhouse_realism import add_funhouse_realism
    report = add_funhouse_realism()

This module never opens, saves, renders or exports a .blend, never changes a
material, and never modifies gameplay/Blueprint/collider data.  It replaces only
named static facade decoration.  Existing meshes are retained, marked as visual
replacements, and hidden rather than deleted.  The doorway, floor, maze, mirrors,
rear exit and eligible movable props are untouched.  Every new part is original,
closed mesh geometry, with explicit finite physical-scale UVs and material slots.
"""
import json
import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

PREFIX = 'FHR_'
ROOT = PREFIX + 'Manufactured_Facade_Root'
PASS_NAME = 'Funhouse manufactured facade realism'


def _smooth_path(points, subdivisions=8):
    """Interpolating cubic path with tangent-matched rounded corners."""
    p = [Vector(q) for q in points]
    out = []
    for i in range(len(p)-1):
        p0, p1, p2, p3 = p[max(0, i-1)], p[i], p[i+1], p[min(len(p)-1, i+2)]
        for k in range(subdivisions):
            t = k/subdivisions
            out.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    out.append(p[-1])
    return out


class _Mesh:
    """Batch construction; no per-part operators or dependency graph updates."""
    def __init__(self, name, materials):
        self.name = PREFIX+name
        self.materials = materials
        self.vertices, self.faces, self.indices, self.smooth = [], [], [], []

    def add(self, vertices, faces, material=0, smooth=False):
        offset = len(self.vertices)
        self.vertices.extend(tuple(v) for v in vertices)
        self.faces.extend(tuple(offset+i for i in f) for f in faces)
        self.indices.extend([material]*len(faces))
        self.smooth.extend([smooth]*len(faces))

    def box(self, center, size, material=0):
        x, y, z = center
        a, b, c = (s/2 for s in size)
        vs = [(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
              (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        self.add(vs, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], material)

    def plate(self, outline, front, depth, material=0):
        """Thin closed sheet, including explicitly tessellated concave cap faces."""
        outline = [tuple(p) for p in outline]
        n = len(outline)
        vs = [(x,front,z) for x,z in outline]+[(x,front+depth,z) for x,z in outline]
        flat = [Vector((x,z,0)) for x,z in outline]
        lookup = {(round(p.x,8),round(p.y,8)):i for i,p in enumerate(flat)}
        tris = [[v if isinstance(v,int) else lookup[(round(v.x,8),round(v.y,8))] for v in tri]
                for tri in tessellate_polygon([flat])]
        fs = [tuple(t) for t in tris]+[tuple(n+i for i in reversed(t)) for t in tris]
        fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        self.add(vs,fs,material)

    def tube(self, points, radius, material=0, sides=10, depth_radius=None, closed=False):
        p = [Vector(q) for q in points]
        if len(p)<2:
            return
        depth_radius = radius if depth_radius is None else depth_radius
        vs, fs = [], []
        for i, center in enumerate(p):
            if closed:
                tangent = (p[(i+1)%len(p)]-p[(i-1)%len(p)]).normalized()
            else:
                tangent = (p[min(i+1,len(p)-1)]-p[max(0,i-1)]).normalized()
            normal = Vector((0,1,0)) if abs(tangent.y)<.95 else Vector((1,0,0))
            normal = (normal-tangent*tangent.dot(normal)).normalized()
            across = tangent.cross(normal).normalized()
            for k in range(sides):
                angle = math.tau*k/sides
                vs.append(center+across*(radius*math.cos(angle))+normal*(depth_radius*math.sin(angle)))
        for i in range(len(p) if closed else len(p)-1):
            j = (i+1)%len(p)
            for k in range(sides):
                fs.append((i*sides+k,i*sides+(k+1)%sides,j*sides+(k+1)%sides,j*sides+k))
        if not closed:
            fs.extend([tuple(reversed(range(sides))),tuple((len(p)-1)*sides+k for k in range(sides))])
        self.add(vs,fs,material,True)
        if not closed:
            self.smooth[-1] = self.smooth[-2] = False

    def lens(self, center, radius, material=0, segments=12, rows=6):
        """Small rounded lamp or rivet, with single poles and no collapsed quads."""
        c = Vector(center)
        scale = Vector(radius if hasattr(radius,'__len__') else (radius,radius,radius))
        vs = [c+Vector((0,0,scale.z))]
        for row in range(1,rows):
            theta = math.pi*row/rows
            for k in range(segments):
                a = math.tau*k/segments
                vs.append(c+Vector((scale.x*math.sin(theta)*math.cos(a),scale.y*math.sin(theta)*math.sin(a),scale.z*math.cos(theta))))
        bottom = len(vs)
        vs.append(c-Vector((0,0,scale.z)))
        fs = [(0,1+k,1+(k+1)%segments) for k in range(segments)]
        for row in range(rows-2):
            base = 1+row*segments
            fs.extend((base+k,base+segments+k,base+segments+(k+1)%segments,base+(k+1)%segments) for k in range(segments))
        base = 1+(rows-2)*segments
        fs.extend((base+k,bottom,base+(k+1)%segments) for k in range(segments))
        self.add(vs,fs,material,True)

    def finish(self, collection, root):
        if not self.faces:
            return None
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices,[],self.faces)
        for material in self.materials:
            mesh.materials.append(material)
        mesh.update()
        for face, material, smooth in zip(mesh.polygons,self.indices,self.smooth):
            face.material_index = material
            face.use_smooth = smooth
        # Single batch winding pass.  All components are deliberately closed.
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        uv = mesh.uv_layers.new(name='UVMap')
        for face in mesh.polygons:
            axis = max(range(3),key=lambda a:abs(face.normal[a]))
            axes = [a for a in range(3) if a!=axis]
            tile = float(mesh.materials[face.material_index].get('physical_tile_m') or .8)
            for li in face.loop_indices:
                p = mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv = (p[axes[0]]/tile,p[axes[1]]/tile)
        obj = bpy.data.objects.new(self.name,mesh)
        collection.objects.link(obj)
        obj.parent = root
        obj['ArtPass'] = PASS_NAME
        obj['refinement_set'] = 'FunhouseRealism'
        obj['decoration_only'] = True
        obj['export_role'] = 'Static manufactured facade detail'
        obj['collision_policy'] = 'Facade decoration only; no automatic UCX or full-building hull'
        obj['geometry_provenance'] = 'Original authored sheet metal, moulding, panels and hardware'
        return obj


def _sign_outline(cx=16, cz=6.23, sx=1, sz=1):
    """Soft shoulders and a shallow crown; recognizably a built carnival sign."""
    # Clockwise from lower left. Cubic sampling preserves the handmade profile.
    control = [(11.11,6.00),(11.20,5.78),(11.56,5.70),(13.20,5.72),
               (16.00,5.76),(18.80,5.72),(20.44,5.70),(20.80,5.78),
               (20.89,6.00),(20.86,6.47),(20.64,6.68),(19.00,6.74),
               (17.30,6.81),(16.00,6.95),(14.70,6.81),(13.00,6.74),
               (11.36,6.68),(11.14,6.47)]
    # Cyclic Catmull path, with endpoints removed rather than duplicated.
    p = [Vector((x,0,z)) for x,z in control]
    out = []
    for i in range(len(p)):
        p0,p1,p2,p3 = p[(i-1)%len(p)],p[i],p[(i+1)%len(p)],p[(i+2)%len(p)]
        for k in range(5):
            t=k/5
            q=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
            out.append((cx+(q.x-cx)*sx,cz+(q.z-cz)*sz))
    return out


def add_funhouse_realism():
    """Apply once and return an audit-friendly report; caller owns scene saving."""
    if bpy.data.objects.get(ROOT):
        return {'status':'already_applied','root':ROOT}
    required = ('wood','rust','black','gold','cream','red','teal','bulb')
    missing = [name for name in required if bpy.data.materials.get(name) is None]
    if missing:
        raise RuntimeError('Funhouse refinement requires the existing scene materials: '+', '.join(missing))
    # Exact prefix matching does not include movable props or assembly sources.
    targets = ('FH_Facade_Wing','FH_Facade_Cornice','FH_Mounted_Sign_Back',
               'FH_Mounted_Sign_Face','FH_Marquee_Bulb','FH_Clown_Open_Mouth_Lip',
               'FH_Clown_Hair_Lock')
    originals = [o for o in bpy.context.scene.objects
                 if any(o.name==t or o.name.startswith(t+'.') for t in targets)]
    if not any(o.name=='FH_Facade_Wing' for o in originals):
        raise RuntimeError('Expected the original carnival funhouse facade in the loaded scene.')
    if any(o.get('PropActorTag') or o.get('_assembly_source') for o in originals):
        raise RuntimeError('Refusing to replace an eligible prop or an assembly source.')
    collection = bpy.data.collections.get('Funhouse manufactured facade details')
    if collection is None:
        collection = bpy.data.collections.new('Funhouse manufactured facade details')
        bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(ROOT,None)
    collection.objects.link(root)
    root['ArtPass'] = PASS_NAME
    root['mouth_clear_zone_m'] = 'x 14.75..17.25; y 5.8..7.2; below z 2.85 remains free of all new detail'
    root['preserved'] = 'Floor, original entry opening, rear exit, maze, mirrors, practical lights and eligible props'
    materials = [bpy.data.materials[name] for name in required]
    WOOD,RUST,BLACK,GOLD,CREAM,RED,TEAL,BULB = range(len(required))
    builders = {n:_Mesh(n,materials) for n in (
        'Wing_Sheet_Panels','Fascia_Moulding','Scalloped_Valance','Panel_Hardware',
        'Manufactured_Sign_Case','Sign_Rolled_Edges','Marquee_Sockets','Marquee_Lenses',
        'Mouth_Shadow_Rebate','Mouth_Rounded_Moulding','Mouth_Fine_Inlay',
        'Pressed_Hair_Fans','Hair_Edge_Beading','Return_Corner_Fittings')}
    b = builders

    # Manufacture-scale skin over retained wall positions. Fine genuine joins,
    # hemmed edges and occasional short lower-edge damage replace two giant slabs.
    for wing, edges in enumerate(((11.05,11.5,12.2,12.9,13.6,14.3,14.75),
                                  (17.25,17.7,18.4,19.1,19.8,20.5,20.95))):
        for i,(left,right) in enumerate(zip(edges,edges[1:])):
            left += .0035
            right -= .0035
            bottom = .205
            notch = .055 if (wing,i) in ((0,1),(1,3)) else .012
            outline = [(left,bottom+.016),(left+.13*(right-left),bottom),
                       (left+.29*(right-left),bottom+notch),
                       (left+.36*(right-left),bottom+.009),(right,bottom+.02),
                       (right,4.49),(left,4.49)]
            b['Wing_Sheet_Panels'].plate(outline,6.828,.065,TEAL)
        # Horizontal retaining rail behind the skins and upper folded flashing.
        lo,hi=edges[0],edges[-1]
        b['Return_Corner_Fittings'].box(((lo+hi)/2,7.006,4.38),(hi-lo,.075,.09),WOOD)
        b['Return_Corner_Fittings'].box(((lo+hi)/2,6.863,.34),(hi-lo,.028,.07),RUST)
        top=[(lo+(hi-lo)*k/40,6.65,4.52+.16*math.sin(math.pi*k/40)) for k in range(41)]
        b['Fascia_Moulding'].tube(top,.032,GOLD,sides=10,depth_radius=.045)
        b['Fascia_Moulding'].tube([(x,y+.045,z-.062) for x,y,z in top],.018,RED,sides=8)
        cap_outline=[(x,z) for x,y,z in top]+[(hi,4.385),(lo,4.385)]
        b['Scalloped_Valance'].plate(cap_outline,6.72,.032,TEAL)
        # Sheet-metal scallops have a 32 mm hem, not blocks suspended in space.
        count=6
        for k in range(count):
            xa=lo+(hi-lo)*k/count
            xb=lo+(hi-lo)*(k+1)/count
            edge=[(xa+(xb-xa)*j/10,6.655,4.40-.11*math.sin(math.pi*j/10)) for j in range(11)]
            shape=[(xa,4.44),(xb,4.44)]+[(p[0],p[2]) for p in reversed(edge)]
            b['Scalloped_Valance'].plate(shape,6.684,.025,CREAM)
            b['Fascia_Moulding'].tube(edge,.013,GOLD,sides=8)
        # Existing cream battens remain; fasteners sit on them at structural rails.
        for x in edges[1:-1]:
            for z in (.79,2.12,4.22):
                b['Panel_Hardware'].lens((x,6.744,z),(.013,.007,.013),RUST,8,4)
        # One visible sheet-metal overlap seam per wing with a narrow shadow line.
        for xa,xb in ((lo+.08,lo+.40),(hi-.40,hi-.08)):
            b['Panel_Hardware'].box(((xa+xb)/2,6.814,1.11),(xb-xa,.012,.014),RUST)

    # New light sign case: thin rounded/scrolled sheet silhouette, layered borders,
    # rolled return, wiring raceway, separately seated replaceable bulb lenses.
    outline=_sign_outline()
    b['Manufactured_Sign_Case'].plate(outline,6.572,.105,RUST)
    inset=_sign_outline(sx=.989,sz=.875)
    b['Manufactured_Sign_Case'].plate(inset,6.531,.040,RED)
    inset2=_sign_outline(sx=.975,sz=.748)
    b['Manufactured_Sign_Case'].plate(inset2,6.509,.022,BLACK)
    b['Sign_Rolled_Edges'].tube([(x,6.537,z) for x,z in outline],.024,GOLD,sides=10,closed=True)
    b['Sign_Rolled_Edges'].tube([(x,6.483,z) for x,z in inset2],.012,GOLD,sides=8,closed=True)
    # Shallow crown retains the existing title's exact position and readability.
    crowns=[]
    for k in range(31):
        x=11.38+k*(9.24/30)
        z=6.67+.225*max(0.0,1-abs((x-16)/4.62))**1.4
        crowns.append((x,6.55,z))
        b['Marquee_Sockets'].tube([(x,6.551,z),(x,6.464,z)],.035,RUST,sides=10)
        b['Marquee_Lenses'].lens((x,6.424,z),(.046,.048,.046),BULB,12,6)
    b['Marquee_Sockets'].tube([(x,y+.078,z) for x,y,z in crowns],.018,BLACK,sides=8)
    for x in (11.4,20.6):
        b['Return_Corner_Fittings'].box((x,6.706,5.94),(.28,.033,.31),RUST)
        # Two folded stand-offs physically bridge the shallow sign case to the
        # retained support post at y=7.02; the front plate does not float.
        for z in (5.845,6.035):
            b['Return_Corner_Fittings'].box((x,6.810,z),(.19,.290,.030),RUST)
        for dx in (-.085,.085):
            for z in (5.84,6.04):
                b['Panel_Hardware'].lens((x+dx,6.678,z),(.020,.010,.020),GOLD,10,4)

    # Rounded cast moulding follows the original open-bottom mouth. Every new
    # vertex below head height remains outside the 2.5 m central clear zone.
    mouth=_smooth_path([(14.56,6.08,.32),(14.54,6.07,1.25),(14.53,6.06,2.65),
                        (14.61,6.06,3.34),(15.02,6.03,3.40),(16,6.00,3.09),
                        (16.98,6.03,3.40),(17.39,6.06,3.34),(17.47,6.06,2.65),
                        (17.46,6.07,1.25),(17.44,6.08,.32)],8)
    b['Mouth_Shadow_Rebate'].tube([(p.x,p.y+.08,p.z) for p in mouth],.121,RUST,12,depth_radius=.045)
    b['Mouth_Rounded_Moulding'].tube(mouth,.091,RED,16,depth_radius=.073)
    b['Mouth_Fine_Inlay'].tube([(p.x+(16-p.x)*.024,p.y-.073,p.z) for p in mouth],.014,GOLD,8,depth_radius=.010)
    for x in (14.54,17.46):
        for z in (.60,2.55):
            b['Panel_Hardware'].lens((x,5.992,z),(.012,.006,.012),GOLD,8,4)

    # The ten old chunky radial sticks become thin rounded pressed fan ornaments.
    for side in (-1,1):
        for j in range(5):
            # A six-sample bowed centreline and taper create curved, stamped fins.
            root_x=16+side*(1.49+.018*j)
            root_z=4.00+j*.265
            end_x=16+side*(2.21+.11*math.sin(j*.8))
            end_z=4.19+j*.365
            center=[]
            for k in range(11):
                t=k/10
                center.append((root_x+(end_x-root_x)*t+side*.08*math.sin(math.pi*t),
                               root_z+(end_z-root_z)*t+.12*math.sin(math.pi*t)))
            top=[];bottom=[]
            for k,(x,z) in enumerate(center):
                t=k/10
                width=.090+.045*math.sin(math.pi*t)-.050*t
                top.append((x,z+width));bottom.append((x,z-width))
            outline=top+list(reversed(bottom))
            b['Pressed_Hair_Fans'].plate(outline,6.51+j*.006,.055,RED if j%2 else RUST)
            b['Hair_Edge_Beading'].tube([(x,6.49+j*.006,z) for x,z in top],.012,GOLD,8)

    # Wall corners have folded protective angles and three normal fastener rows.
    # Nothing projects into either the front mouth or the rear exit.
    for x,direction in ((11.025,-1),(20.975,1)):
        b['Return_Corner_Fittings'].box((x,6.822,2.38),(.055,.034,3.94),RUST)
        b['Return_Corner_Fittings'].box((x+direction*.035,6.914,2.38),(.026,.17,3.94),RUST)
        for z in (.62,2.35,4.25):
            b['Panel_Hardware'].lens((x,6.798,z),(.015,.008,.015),GOLD,8,4)

    added=[]
    for builder in builders.values():
        obj=builder.finish(collection,root)
        if obj:
            added.append(obj)
    # Hard guard before original visibility changes, independent of their source
    # geometry. New moulding must never narrow the central standing route.
    violations=[]
    for obj in added:
        for v in obj.data.vertices:
            x,y,z=v.co
            if 14.75+1e-5<x<17.25-1e-5 and 5.8<y<7.2 and .20<z<2.85:
                violations.append(obj.name)
                break
    if violations:
        for obj in added:
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.objects.remove(root,do_unlink=True)
        raise RuntimeError('New facade geometry entered the preserved mouth clearance: '+str(violations))
    for original in originals:
        original['visual_replaced']=True
        original['replacement_refinement']='FunhouseRealism'
        original.hide_render=True
        original.hide_set(True)
    report={'status':'applied','root':ROOT,'objects_added':len(added),'originals_replaced':len(originals),
            'vertices_added':sum(len(o.data.vertices) for o in added),
            'polygons_added':sum(len(o.data.polygons) for o in added),
            'mouth_clear_width_m':2.5,'new_clear_zone_intrusions':violations,
            'rear_exit_and_maze_unchanged':True,'materials_created_or_modified':0,
            'save_performed':False,'existing_props_unchanged':True}
    root['report_json']=json.dumps(report,sort_keys=True)
    return report
