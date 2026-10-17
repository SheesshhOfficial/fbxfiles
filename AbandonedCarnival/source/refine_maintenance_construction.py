"""Cycle 7: manufactured trailer ends and believable maintenance timber.

Call add_maintenance_construction() on an already loaded scene. This module never
opens, saves, exports, or renders a scene. Only the visible placed meshes are
replaced; object names, transforms, custom properties, and eligibility survive.
All geometry stays inside each object's original local and world bounding box.
"""
import bpy
import bmesh
import json
import math
from mathutils import Vector

_VERSION = 'maintenance_construction_v1'


class _Builder:
    """Closed, separately connected pieces, metre-scale UVs, no hidden masters."""
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.face_materials = []
        self.face_uvs = []
        self.materials = []
        self.components = []

    def part(self, label, vertices, faces, material, bevel=0.0,
             grain_axis=None, uv_offset=(0.0, 0.0)):
        mat = bpy.data.materials.get(material) if isinstance(material, str) else material
        if mat is None:
            raise RuntimeError('Missing construction material: ' + str(material))
        me = bpy.data.meshes.new('_MaintenanceTemporary')
        me.from_pydata(vertices, [], faces)
        me.update()
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if bevel:
            edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle() > .24]
            if edges:
                bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=3,
                                profile=.5, affect='EDGES', clamp_overlap=True)
                bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if any(f.calc_area() <= 1e-12 for f in bm.faces):
            raise RuntimeError('Degenerate construction face: ' + label)
        if any(not e.is_manifold for e in bm.edges):
            raise RuntimeError('Open construction component: ' + label)
        bm.to_mesh(me)
        bm.free()
        me.update()
        offset = len(self.vertices)
        first_face = len(self.faces)
        self.vertices.extend([tuple(v.co) for v in me.vertices])
        if mat not in self.materials:
            self.materials.append(mat)
        material_index = self.materials.index(mat)
        tile = float(mat.get('physical_tile_m', 1.0))
        for p in me.polygons:
            self.faces.append(tuple(offset+i for i in p.vertices))
            self.face_materials.append(material_index)
            normal_axis = max(range(3), key=lambda a: abs(p.normal[a]))
            axes = [a for a in range(3) if a != normal_axis]
            if grain_axis in axes:
                axes = [a for a in axes if a != grain_axis] + [grain_axis]
            self.face_uvs.append([((me.vertices[i].co[axes[0]] / tile) + uv_offset[0],
                                   (me.vertices[i].co[axes[1]] / tile) + uv_offset[1])
                                  for i in p.vertices])
        self.components.append({'part': label, 'first_face': first_face,
                                'face_count': len(self.faces)-first_face,
                                'collision_role': 'decorative' if any(word in label for word in
                                    ('nail', 'rivet', 'fixing', 'packing band', 'buckle')) else 'structural'})
        bpy.data.meshes.remove(me)

    def board(self, label, center, dimensions, material='wood', long_axis=0,
              thickness_axis=2, bevel=.0018, warp=0.0, chip=0.0, phase=0.0):
        """Board stock with a restrained bow or localized splinter loss.
        Cross sections stay full-thickness. Damage removes wood rather than
        adding jagged noise. Most boards are straight manufactured pieces.
        """
        axes = (long_axis, next(a for a in range(3)
                               if a not in (long_axis, thickness_axis)), thickness_axis)
        length, width, thickness = [dimensions[a] for a in axes]
        ts = [0.0, .07, .16, .50, .84, .94, 1.0] if (warp or chip) else [0.0, 1.0]
        vertices = []
        for t in ts:
            bow = warp*math.sin(math.pi*t)
            # Only one end/edge loses a tapered splinter. No repeated sawtooth.
            loss = chip * max(0.0, 1.0-t/.16)
            for w, h in ((-width/2+loss, -thickness/2),
                         (width/2, -thickness/2),
                         (width/2, thickness/2),
                         (-width/2+loss, thickness/2)):
                p = list(center)
                p[axes[0]] += (t-.5)*length
                p[axes[1]] += w
                p[axes[2]] += h+bow
                vertices.append(p)
        faces = [(3, 2, 1, 0), tuple(range(4*(len(ts)-1), 4*len(ts)))]
        for j in range(len(ts)-1):
            for k in range(4):
                faces.append((j*4+k, j*4+(k+1)%4, (j+1)*4+(k+1)%4, (j+1)*4+k))
        self.part(label, vertices, faces, material, min(bevel, thickness*.24, width*.24), long_axis, (phase, phase*.713))

    def box(self, label, center, dimensions, material, bevel=.001):
        long_axis = max(range(3), key=lambda a: dimensions[a])
        thickness_axis = min((a for a in range(3) if a != long_axis), key=lambda a: dimensions[a])
        self.board(label, center, dimensions, material, long_axis, thickness_axis, bevel)

    def stud(self, label, center, radius=.004, depth=.0014,
             axis=2, material='rust', sides=8):
        other = [a for a in range(3) if a != axis]
        vertices = []
        for level, scale in ((-depth/2, 1.0), (depth/2, .82)):
            for i in range(sides):
                p = list(center)
                p[axis] += level
                p[other[0]] += radius*scale*math.cos(i*math.tau/sides)
                p[other[1]] += radius*scale*math.sin(i*math.tau/sides)
                vertices.append(p)
        faces = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
        faces.extend((i, (i+1)%sides, (i+1)%sides+sides, i+sides) for i in range(sides))
        self.part(label, vertices, faces, material)

    def finish(self, obj, bounds):
        lo, hi = bounds
        # This is a constraint check, never a clamp that could flatten damage.
        tolerance = 3e-6
        for v in self.vertices:
            if any(v[a] < lo[a]-tolerance or v[a] > hi[a]+tolerance for a in range(3)):
                raise RuntimeError('Construction exceeds original bounds: '+obj.name+' '+str(v))
        me = bpy.data.meshes.new(obj.name+' | manufactured construction')
        me.from_pydata(self.vertices, [], self.faces)
        for mat in self.materials:
            me.materials.append(mat)
        me.update()
        uv = me.uv_layers.new(name='UVMap')
        for p, mi, coords in zip(me.polygons, self.face_materials, self.face_uvs):
            p.material_index = mi
            p.use_smooth = False
            for li, coord in zip(p.loop_indices, coords):
                uv.data[li].uv = coord
        me.calc_loop_triangles()
        bad_faces = sum(p.area <= 1e-12 for p in me.polygons)
        bad_triangles = sum(t.area <= 1e-12 for t in me.loop_triangles)
        if bad_faces or bad_triangles:
            raise RuntimeError('Degenerate finished mesh: '+obj.name)
        old = obj.data
        obj.data = me
        # Existing component primitives have baked bevels; the replacement does too.
        for modifier in list(obj.modifiers):
            obj.modifiers.remove(modifier)
        obj['construction_refinement'] = _VERSION
        obj['refinement_cycle'] = 7
        obj['geometry_provenance'] = 'Original project construction, no external downloads'
        obj['collision_regeneration_needed'] = True
        obj['collision_policy'] = ('Regenerate separate board/panel component hulls. '
                                   'Keep pallet fork lanes and crate cavities. '
                                   'Omit cosmetic fasteners using construction_components face ranges. '
                                   'Do not use a single whole-prop hull.')
        obj['construction_components'] = json.dumps(self.components)
        obj['original_local_bounds'] = json.dumps([list(lo), list(hi)])
        if old.users == 0:
            bpy.data.meshes.remove(old)
        return {'name': obj.name, 'components': len(self.components),
                'vertices': len(me.vertices), 'faces': len(me.polygons),
                'triangles': len(me.loop_triangles), 'degenerate_faces': bad_faces,
                'degenerate_triangles': bad_triangles, 'uv_loops': len(uv.data),
                'material_indices_valid': all(p.material_index < len(me.materials) for p in me.polygons),
                'bounds_not_expanded': True}


def _bounds(obj):
    return tuple(Vector((min(v.co[a] for v in obj.data.vertices) if k == 0 else
                         max(v.co[a] for v in obj.data.vertices)) for a in range(3))
                 for k in range(2))


def _pallet(obj, variant):
    bounds = _bounds(obj)
    lo, hi = bounds
    cx, cy = ((lo.x+hi.x)/2, (lo.y+hi.y)/2)
    top = hi.z
    bottom = lo.z
    b = _Builder(obj.name)
    # Tall, narrow solid stringers carry 28 mm deck stock. Their horizontal
    # footprints equal the original 120 mm runners, preserving both fork lanes.
    deck_bottom = top-.028
    for j, x in enumerate((cx-.5, cx, cx+.5)):
        b.board('load-bearing stringer %d'%j, (x, cy, (bottom+deck_bottom)/2),
                (.12, 1.10, deck_bottom-bottom), long_axis=1,
                thickness_axis=0, bevel=.0024, phase=.21*j+.37*variant)
    # Fixed end-board positions retain the original footprint; slight stock-width
    # differences and UV offsets break repetition without arbitrary crookedness.
    widths = (.150, .143, .153, .146, .151, .150)
    for j in range(6):
        y = cy-.5+j*.2
        warp = -.0022 if variant in (2, 7) and j == 4 else 0.0
        chip = .012 if variant in (2, 5) and j == (0 if variant == 2 else 3) else 0.0
        length = 1.2-(.006 if j in (1, 4) else 0.0)
        center = (cx, y, top-.014-.00015)
        b.board('28mm deck board %d'%j, center, (length, widths[j], .0277),
                bevel=.0017, warp=warp, chip=chip, phase=.167*j+.293*variant)
        for support, x in enumerate((cx-.5, cx, cx+.5)):
            t = (x-cx)/length+.5
            surface = top-.0003+warp*math.sin(math.pi*t)
            for side in (-1, 1):
                b.stud('deck nail %d %d %d'%(j,support,side),
                       (x, y+side*.035, surface-.00075), radius=.0037,
                       depth=.0014, material='rust')
    report = b.finish(obj, bounds)
    report['fork_gap_min_width_m'] = .38
    report['fork_lane_footprints_unchanged'] = True
    report['damaged_boards'] = int(variant in (2,7))+int(variant in (2,5))
    return report


def _crate(obj, variant):
    bounds = _bounds(obj)
    lo, hi = bounds
    c = (lo+hi)/2
    b = _Builder(obj.name)
    # Shipping cases are built from thin timber skins and battens, not a solid
    # cube with oversized bars. Dimensions stay inside the previous placed case.
    xwall = min(.520, (hi.x-lo.x)/2-.026)
    ywall = min(.510, (hi.y-lo.y)/2-.027)
    for side in (-1,1):
        for j in range(5):
            z = c.z-.344+j*.172
            width = .167 if j not in (1,3) else .165
            p = (c.x,c.y+side*ywall,z)
            # One damaged front slat per two crates; the rest remains straight.
            chip = .015 if side == -1 and j == 1 and variant in (1,3) else 0.0
            b.board('front back skin %d %d'%(side,j),p,(1.038,.022,width),
                    long_axis=0,thickness_axis=1,bevel=.0014,chip=chip,
                    phase=.19*j+.31*variant)
            p = (c.x+side*xwall,c.y,z)
            b.board('end skin %d %d'%(side,j),p,(.022,.998,width),
                    long_axis=1,thickness_axis=0,bevel=.0014,
                    phase=.27*j+.23*variant+.31)
    # Internal corner battens receive the visible nail lines. They also join
    # lid/floor and skin; no floating nail pattern away from actual supports.
    for sx in (-1,1):
        for sy in (-1,1):
            x,y = c.x+sx*.478,c.y+sy*.467
            b.board('internal corner batten %d %d'%(sx,sy),
                    (x,y,c.z),(.070,.070,.89),long_axis=2,thickness_axis=0,
                    bevel=.0018,phase=.31*variant)
            for j in range(5):
                b.stud('end join nail %d %d %d'%(sx,sy,j),
                       (c.x+sx*(xwall+.0113),y,c.z-.344+j*.172),
                       radius=.0038,depth=.0014,axis=0)
        # Thin external timber reinforcements replace thick uniform bars.
        for sy in (-1,1):
            x,y = c.x+sx*.455,c.y+sy*.530
            b.board('front edge batten %d %d'%(sx,sy),
                    (x,y,c.z),(.054,.023,.948),long_axis=2,thickness_axis=1,
                    bevel=.0022,phase=.2*variant+.4*sx)
            for j in range(5):
                z = c.z-.344+j*.172
                b.stud('front join nail %d %d %d'%(sx,sy,j),
                       (x,y+sy*.0113,z),radius=.0042,depth=.0014,axis=1)
    # Actual five-board lid and floor. The lid's top stays at the old core top,
    # so paint tins already resting there keep their contact height.
    for j in range(5):
        x=c.x-.416+j*.208
        for side in (-1,1):
            z=c.z+side*.437
            b.board('lid floor board %d %d'%(side,j),(x,c.y,z),(.203,1.018,.026),
                    long_axis=1,thickness_axis=2,bevel=.0016,
                    chip=.009 if side == 1 and j == 4 and variant == 0 else 0.0,
                    phase=.32*j+.17*variant)
            if side == 1:
                for sy in (-1,1):
                    b.stud('lid nail %d %d'%(j,sy),(x,c.y+sy*.461,c.z+.449),
                           radius=.0038,depth=.0014)
    # Skids preserve the original ground/stacking contact elevation.
    for x in (c.x-.455,c.x+.455):
        b.board('bottom load skid',(x,c.y,c.z-.462),(.070,1.03,.026),
                long_axis=1,thickness_axis=2,bevel=.0018,phase=.34*variant)
    # A narrow genuine steel packing strap on one case, with a folded buckle.
    # It is selective evidence of a different service history, not uniform dirt.
    if variant == 1:
        x=c.x-.12
        for sy in (-1,1):
            b.box('packing band face',(x,c.y+sy*.524,c.z),(.025,.004,.889),'rust',.0006)
        for sz in (-1,1):
            b.box('packing band return',(x,c.y,c.z+sz*.452),(.025,1.052,.004),'rust',.0006)
        b.box('folded steel band buckle',(x,c.y-.529,c.z+.20),(.039,.008,.048),'rust',.001)
    return b.finish(obj,bounds)


def _trailer_end(obj, letter):
    bounds = _bounds(obj)
    lo,hi = bounds
    cx,cz = (lo.x+hi.x)/2,(lo.z+hi.z)/2
    width,height = hi.x-lo.x,hi.z-lo.z
    b=_Builder(obj.name)
    paint=obj.data.materials[0]
    metal=bpy.data.materials.get('Entrance dull galvanized metal') or bpy.data.materials['rust']
    # Exterior is negative Y. The skin is brought inward a few millimetres, so
    # all seams, folded edges, rivets and repairs fit inside the old 100 mm slab.
    b.box('inner end wall',(cx,.025,cz),(width-.003,.045,height-.003),paint,.015)
    seam_x=cx+(.23 if letter=='A' else -.31)
    for side,x0,x1 in ((0,lo.x+.015,seam_x-.006),(1,seam_x+.006,hi.x-.015)):
        b.box('pressed aluminium skin %d'%side,((x0+x1)/2,-.020,cz),
              (x1-x0,.026,height-.035),paint,.007)
    b.box('vertical folded standing seam',(seam_x,-.039,cz),(.020,.018,height-.020),metal,.003)
    for x in (lo.x+.017,hi.x-.017):
        b.box('folded perimeter edge',(x,-.034,cz),(.031,.028,height-.006),metal,.006)
    for z in (lo.z+.017,hi.z-.017):
        b.box('folded upper lower edge',(cx,-.034,z),(width-.006,.028,.031),metal,.006)
    # Regular rivets follow actual sheet attachments, not random surface specks.
    for x in (lo.x+.018,seam_x,hi.x-.018):
        for j in range(8):
            z=lo.z+.11+j*(height-.22)/7
            b.stud('flush sheet rivet',(x,-.048,z),radius=.0055,depth=.0016,axis=1,
                   material=metal,sides=10)
    # Low embossed belt line continues the side's sheet-metal construction.
    for z in (cz-.73,cz+.63):
        b.box('pressed horizontal hem',(cx,-.038,z),(width-.060,.012,.017),paint,.004)
    if letter=='A':
        # One small dissimilar-metal riveted repair, with clipped corners.
        x,z=cx+.70,cz-.59
        w,h=.46,.33
        outline=[(-w/2+.025,-h/2), (w/2,-h/2), (w/2,h/2-.018),
                 (w/2-.018,h/2),(-w/2,h/2),(-w/2,-h/2+.025)]
        verts=[(x+xx,y,z+zz) for y in (-.039,-.045) for xx,zz in outline]
        n=len(outline)
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        b.part('clipped sheet-metal repair',verts,faces,metal,.0009)
        for dx in (-.195,.195):
            for dz in (-.130,.130):
                b.stud('repair fixing',(x+dx,-.047,z+dz),radius=.005,depth=.0014,axis=1,
                       material='rust')
    else:
        # Recessed service louver: dark recess, 0.7 mm folded blades and a rim.
        # The blades occupy shallow slots within the existing end-wall envelope.
        x,z=cx-.70,cz+.05
        b.box('service vent recess',(x,-.034,z),(.53,.008,.58),'black',.014)
        for dx in (-.273,.273):
            b.box('vent frame vertical',(x+dx,-.040,z),(.024,.014,.625),metal,.004)
        for dz in (-.301,.301):
            b.box('vent frame horizontal',(x,-.040,z+dz),(.57,.014,.024),metal,.004)
        for j in range(7):
            zz=z-.245+j*.078
            # Folded wedge profiles are closed, thin, and visibly separated.
            profile=[(-.038,zz-.027),(-.046,zz+.025),(-.043,zz+.027),(-.035,zz-.025)]
            vs=[(xx,yy,zzz) for xx in (x-.250,x+.250) for yy,zzz in profile]
            fs=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
            b.part('folded vent blade %d'%j,vs,fs,paint,.0005)
        for dx in (-.273,.273):
            for dz in (-.275,.275):
                b.stud('vent fixing',(x+dx,-.048,z+dz),radius=.005,depth=.0015,axis=1,
                       material='rust')
    report=b.finish(obj,bounds)
    obj['decorative_no_collision']=False
    report['preserved_end_wall_envelope']=True
    return report


def add_maintenance_construction():
    """Replace twelve placed props and two front end-cap meshes in memory."""
    root_name='Cycle07 maintenance construction record'
    if bpy.data.objects.get(root_name):
        return {'status':'already_applied','version':_VERSION}
    names=sorted(o.name for o in bpy.context.scene.objects
                 if o.type=='MESH' and o.get('PropActorTag')
                 and not o.hide_render and not o.get('_assembly_source')
                 and (o.name.startswith('BY_Pallet_') or o.name.startswith('BY_Crate_')))
    expected=[o for o in names if o.startswith('BY_Pallet_')]
    if len(expected)!=8 or len(names)!=12:
        raise RuntimeError('Expected 8 placed maintenance pallets and 4 crates; got '+str(names))
    for letter in ('A','B'):
        if not bpy.data.objects.get('BY_Caravan_'+letter+'_End_Cap'):
            raise RuntimeError('Missing original front trailer end cap '+letter)
    tags={n:dict(bpy.data.objects[n].items()) for n in names}
    reports=[]
    for variant,name in enumerate(expected):
        reports.append(_pallet(bpy.data.objects[name],variant))
    for name in names:
        if name.startswith('BY_Crate_'):
            reports.append(_crate(bpy.data.objects[name],int(name.rsplit('_',1)[1])))
    for letter in ('A','B'):
        reports.append(_trailer_end(bpy.data.objects['BY_Caravan_'+letter+'_End_Cap'],letter))
    for name,props in tags.items():
        for key in ('PropActorTag','asset_family'):
            if bpy.data.objects[name].get(key)!=props.get(key):
                raise RuntimeError('Changed eligibility: '+name)
    bpy.context.view_layer.update()
    result={'status':'applied','version':_VERSION,'eligible_props_changed':12,
            'trailer_front_caps_changed':2,'placed_object_names_preserved':True,
            'route_geometry_changed':False,'bounds_expanded':False,
            'geometry_validation':reports,
            'change':('Replaced solid maintenance crates with thin-board skins, internal joinery, '
                      'load skids and grounded nails; replaced thick pallet planks with 28 mm '
                      'deck stock and sparse localized damage; formed two trailer end skins '
                      'with shallow seams, edge folds, a selective repair and a recessed vent.'),
            'collision_note':('Collision regeneration REQUIRED for all twelve changed eligible '
                              'props and the two changed static caps. Regenerate per-component '
                              'hulls; do not bridge pallet fork lanes or hollow crate interiors. '
                              'No Blueprint changes. Unreal runtime verification remains pending.')}
    root=bpy.data.objects.new(root_name,None)
    bpy.context.collection.objects.link(root)
    root['construction_refinement']=_VERSION
    root['eligible_props_changed']=json.dumps(names)
    root['collision_regeneration_needed']=True
    root['notes']=result['collision_note']
    return result
