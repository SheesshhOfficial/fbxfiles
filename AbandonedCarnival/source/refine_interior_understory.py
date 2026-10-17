"""Optional localized structure-base/fence understory, additive and save-free.

Call add_interior_understory() in the coordinator's loaded refinement scene.
No scene is opened, saved, rendered, or exported by this module. Existing scene
objects/materials are never changed. There are no spheres, particle systems,
images, downloads, Blueprint changes, or gameplay-eligibility tags.

Design review: see source/backstage.py for the solid funhouse side walls at
x=11/21, rear wall y=19 with exit x=18.8..20.2, and outward caravan sides at
x=11.24/22.06. Core circulation comes from source/build_carnival.py.
Every new vertex is fitted inside one conservative strip below; the final
geometry cannot spread past its declared strip even if helper foliage changes.
"""
import math
import random
import bpy
import bmesh
from mathutils import Vector
from natural_forest import Mesh
from refine_perimeter_story import _materials, _shrub, _briar, _fern, _direction

PREFIX = 'Interior understory | foliage '
VERSION = 'LocalizedInteriorUnderstory_v1'
GROUND_Z = .005

# Rectangles are xmin, xmax, ymin, ymax. All are outside building footprints,
# doorway/step approaches and published circulation. No scatter over open ground.
# The caravan strips sit between wheel locations, on sides opposite the doors.
STRIPS = (
    ('funhouse west solid wall', (10.18, 10.69, 10.75, 14.15), 'Y', 1.22),
    ('funhouse east solid wall', (21.33, 21.96, 10.20, 13.60), 'Y', 1.12),
    ('funhouse rear left wall', (12.05, 15.55, 19.35, 19.92), 'X', .92),
    ('left caravan outward side', (10.56, 11.09, -5.87, -3.58), 'Y', .83),
    ('right caravan outward side', (22.36, 23.00, -5.40, -3.10), 'Y', .91),
    ('west fence sheltered pocket', (-25.78, -25.08, -18.60, -15.30), 'Y', 1.30),
    ('east fence sheltered pocket', (25.05, 25.76, -17.30, -13.80), 'Y', 1.25),
    ('north fence sheltered pocket', (-6.40, -2.30, 25.04, 25.75), 'X', 1.34),
)

# Conservative no-plant rectangles, including routes a walking capsule needs.
KEEP_CLEAR = (
    ('arrival and gate', (-6.2, 6.2, -31.2, -18.0)),
    ('midway and spawns', (-14.2, -5.8, -22.2, 8.2)),
    ('central crosswalk', (-14.2, 9.2, -4.7, .7)),
    ('backstage north approach', (6.8, 19.2, .3, 3.7)),
    ('backstage central aisle', (14.8, 18.2, -8.2, 2.2)),
    ('funhouse front approach', (10.5, 21.5, 4.0, 8.1)),
    ('funhouse rear exit approach', (18.55, 20.65, 18.7, 24.9)),
    ('left caravan door and steps', (13.75, 16.1, -6.55, -4.25)),
    ('right caravan door and steps', (17.15, 19.55, -5.95, -3.65)),
)


def _overlap(a, b, margin=0):
    return (a[0] < b[1]+margin and a[1] > b[0]-margin and
            a[2] < b[3]+margin and a[3] > b[2]-margin)


def _validate_layout():
    for name, bounds, axis, height in STRIPS:
        if not (-26 < bounds[0] < bounds[1] < 26 and
                -26 < bounds[2] < bounds[3] < 26):
            raise RuntimeError('Interior understory strip escapes core: '+name)
        for route, excluded in KEEP_CLEAR:
            if _overlap(bounds, excluded):
                raise RuntimeError('Interior understory overlaps '+route+': '+name)
        if axis not in ('X', 'Y') or not (.3 < height < 1.5):
            raise RuntimeError('Invalid understory strip: '+name)


def _actor_bounds():
    """Protect any later-added gameplay props too; skip rather than move them."""
    result = []
    for ob in bpy.context.scene.objects:
        if not ob.get('PropActorTag') or ob.get('_assembly_source') or ob.hide_render:
            continue
        points = [ob.matrix_world @ Vector(p) for p in ob.bound_box]
        if not points:
            continue
        if min(p.z for p in points) > 1.65 or max(p.z for p in points) < -.05:
            continue
        result.append((ob.name, (min(p.x for p in points), max(p.x for p in points),
                                 min(p.y for p in points), max(p.y for p in points))))
    return result


def _fit_builders(builders, bounds, along_axis):
    """One positive affine fit shared by stems/leaves preserves connectivity.

    Positive, nonzero factors preserve triangle area and UV orientation. The
    original six-triangle pointed leaves and tapered tube quads need no spheres
    or collapsed poles. UVs remain authored per face by natural_forest.Mesh.
    """
    points = [v for builder in builders for v in builder.v]
    xmin = min(p[0] for p in points)
    xmax = max(p[0] for p in points)
    ymin = min(p[1] for p in points)
    ymax = max(p[1] for p in points)
    if xmax-xmin < .01 or ymax-ymin < .01:
        raise RuntimeError('Understory source has a degenerate footprint')
    inset = .012
    x0, x1, y0, y1 = bounds
    x0 += inset; x1 -= inset; y0 += inset; y1 -= inset
    for builder in builders:
        transformed = []
        for x, y, z in builder.v:
            # Local X is cross-strip and local Y is along-strip.
            u = (x-xmin)/(xmax-xmin)
            v = (y-ymin)/(ymax-ymin)
            if along_axis == 'Y':
                point = (x0+u*(x1-x0), y0+v*(y1-y0), z)
            else:
                # Rotation has determinant +1, so face winding remains unchanged.
                point = (x0+v*(x1-x0), y1-u*(y1-y0), z)
            if not (bounds[0] <= point[0] <= bounds[1] and bounds[2] <= point[1] <= bounds[3]):
                raise RuntimeError('Understory geometry escaped fitted strip')
            transformed.append(point)
        builder.v = transformed


def _finish(builder, name, bounds):
    ob = builder.finish()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    ob['ArtPass'] = 'Localized structure-base and fence understory'
    ob['refinement_set'] = VERSION
    ob['decoration_only'] = True
    ob['render_only'] = False
    ob['export_role'] = 'Static environment scenery'
    ob['collision_policy'] = 'Nonblocking foliage decoration; no UCX'
    ob['placement_strip'] = name
    ob['placement_bounds_xy'] = list(bounds)
    ob['geometry_provenance'] = 'Original UV-mapped folded leaves and tapered stems'
    return ob


def add_interior_understory():
    """Return created meshes (up to 24), leaving any existing scene untouched.

    Repeated calls return this module's existing objects; they do not replace
    them or accumulate duplicate geometry. Collision/name exclusion matches the
    existing environment exporter. Runtime walkability remains untested.
    """
    _validate_layout()
    existing = [ob for ob in bpy.context.scene.objects if ob.name.startswith(PREFIX)]
    if existing:
        return existing
    bpy.context.view_layer.update()
    occupied = _actor_bounds()
    leaf_mats, bark, dry, unused_pale = _materials()
    created = []
    skipped = []
    # Each strip uses its own deterministic stream, so skipped occupied strips
    # cannot change the appearance or bounds of later clusters.
    for index, (name, bounds, axis, height) in enumerate(STRIPS):
        blocking = [actor for actor, bbox in occupied if _overlap(bounds, bbox, .15)]
        if blocking:
            skipped.append((name, blocking))
            continue
        rng = random.Random(20973+index*2311)
        leaves = Mesh(PREFIX+name+' shrub and fern cluster', leaf_mats)
        stems = Mesh(PREFIX+name+' grounded branching stems', [bark])
        litter = Mesh(PREFIX+name+' localized curled leaves', [dry])
        # One offset elder seedling, arching bramble from its shelter, and uneven
        # lower fern rosettes. Variation follows a root group, never a lawn grid.
        root = Vector((rng.uniform(-.10, .10), rng.uniform(-.4, .4), GROUND_Z))
        _shrub(leaves, stems, root, height, rng, broad=.61)
        for j in range(2+index % 2):
            root = Vector((rng.uniform(-.13, .13), -.95+j*.84+rng.uniform(-.18, .18), GROUND_Z))
            _briar(leaves, stems, root, rng.uniform(.32, .51), rng.random()*math.tau, rng)
        for j in range(4+index % 2):
            root = Vector((rng.uniform(-.22, .22), rng.uniform(-1.25, 1.2), GROUND_Z))
            _fern(leaves, stems, root, rng.uniform(.46, .70), rng)
        for j in range(25):
            root = Vector((rng.uniform(-.28, .28), rng.uniform(-1.4, 1.4), GROUND_Z+.012))
            length = rng.uniform(.07, .13)
            litter.leaf(root, _direction(rng.random()*math.tau), length, length*.6,
                        rng.uniform(-.1, .1), 0)
        builders = [leaves, stems, litter]
        _fit_builders(builders, bounds, axis)
        # Validate explicit UV arrays and geometric primitives before linking.
        for builder in builders:
            if len(builder.uv) != sum(len(f) for f in builder.f):
                raise RuntimeError('Understory corner UV mismatch: '+builder.name)
            for face in builder.f:
                a, b, c = [Vector(builder.v[i]) for i in face[:3]]
                if (b-a).cross(c-a).length <= 1e-12:
                    raise RuntimeError('Degenerate understory face: '+builder.name)
                if not all(math.isfinite(value) for i in face for value in builder.v[i]):
                    raise RuntimeError('Nonfinite understory vertex: '+builder.name)
        created.extend(_finish(builder, name, bounds) for builder in builders)
    triangles = sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in created)
    print('INTERIOR_UNDERSTORY', len(created)//3, 'localized clusters;', len(created),
          'decoration meshes;', triangles, 'triangles; skipped occupied strips:', skipped,
          '; entrances, exits, caravan steps, routes and spawns unchanged', flush=True)
    return created
