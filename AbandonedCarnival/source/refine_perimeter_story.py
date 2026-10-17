"""Irregular outer-fence woodland and readable natural silhouettes.

Call add_perimeter_story() in an already loaded carnival scene. This module never
opens, saves, renders, changes existing geometry/materials, or exports a scene.
It creates only its own reusable decoration meshes and original materials.

All added vertices stay outside the 52 x 52 m playable square. The complete
forecourt (x +/-6, y -31..-26) and central approach (x +/-4) are untouched.
Existing gate, circulation, gameplay actors and eligibility metadata are unchanged.
Geometry is exported as ordinary static scenery, with no collision or gameplay tag.
"""
import bpy
import bmesh
import math
import random
from mathutils import Vector
from natural_forest import Mesh

PREFIX = 'Perimeter story | foliage '
PASS = 'Outer perimeter woodland story'
GROUND_Z = -.215

# Nonperiodic groups leave deliberate dark gaps between dense woodland islands.
# Restrained cross-bank jitter keeps every leaf outside the fence footprint.
ISLANDS = (
    ('west arrival bramble', -29.9, -22.2, 'W', 1.00),
    ('west elder hollow', -30.6, -10.7, 'W', 1.20),
    ('west fern hollow', -29.8, 3.5, 'W', .86),
    ('west north hazel bank', -30.3, 20.1, 'W', 1.14),
    ('north western thicket', -20.3, 30.0, 'N', 1.15),
    ('north broken-log hollow', -6.4, 30.6, 'N', .94),
    ('north elder bank', 10.9, 30.4, 'N', 1.18),
    ('northeast wild corner', 28.9, 29.8, 'N', 1.13),
    ('east funhouse thicket', 30.6, 15.5, 'E', 1.08),
    ('east service woodland', 30.3, -.9, 'E', .92),
    ('east south saplings', 30.0, -19.9, 'E', 1.12),
    ('southwest entrance shoulder', -17.5, -34.4, 'S', 1.00),
    ('southeast entrance shoulder', 17.1, -34.7, 'S', 1.07),
)

SILHOUETTES = (
    ('west leaning hazel', -31.2, -11.0, 5.15, -1),
    ('northwest coppice', -30.7, 22.2, 6.10, 1),
    ('north forked elder', 12.2, 32.1, 5.55, -1),
    ('east bowed saplings', 32.2, 12.8, 5.05, 1),
    ('southern wind-bent elder', -19.8, -36.0, 4.70, -1),
)


def _material(name, color, roughness=.86):
    """Create a portable original Principled material; never edit an existing one."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (*color, 1)
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = roughness
    return mat


def _materials():
    # Use already-authored veined leaf UV textures where available. No dependency
    # on texture generation, file writes, external assets, or shader modifications.
    living = bpy.data.materials.get('Natural foliage • veined olive green')
    living = living or _material('Perimeter story living olive', (.105, .155, .041))
    deep = bpy.data.materials.get('Forest leaf • deep green') or living
    warm = bpy.data.materials.get('Forest leaf • warm olive') or living
    light = bpy.data.materials.get('Forest leaf • sage light') or living
    bark = bpy.data.materials.get('wood') or _material('Perimeter story bark', (.105, .068, .035))
    dry = _material('Perimeter story dry oak litter', (.135, .077, .027), .94)
    old = _material('Perimeter story grey exposed heartwood', (.205, .182, .132), .95)
    return [living, deep, warm, light], bark, dry, old


def _finish(builder, role, island):
    ob = builder.finish()
    # The helper duplicates face vertices. Weld only this new mesh, preserving
    # per-corner UVs, to avoid turning moderate foliage into large export files.
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    ob['ArtPass'] = PASS
    ob['refinement_set'] = 'PerimeterStory'
    ob['decoration_only'] = True
    ob['render_only'] = False
    ob['export_role'] = 'Static environment scenery'
    ob['collision_policy'] = 'Nonblocking foliage decoration; no UCX'
    ob['perimeter_role'] = role
    ob['woodland_island'] = island
    ob['geometry_provenance'] = 'Original folded leaves, tapered tubes and branch silhouettes'
    # Exporter's name-based decoration policy intentionally recognizes "foliage".
    # Do not set PropActorTag, eligibility, assembly or runtime Blueprint fields.
    return ob


def _direction(angle, z=0):
    return Vector((math.cos(angle), math.sin(angle), z))


def _leaf_lobe(builder, center, radii, count, rng, size=.32, dry=False):
    """Uneven connected foliage volume, never a visible sphere or billboard."""
    for index in range(count):
        angle = rng.random() * math.tau
        z = rng.uniform(-1, 1)
        q = math.sqrt(max(0, 1-z*z))
        depth = rng.random() ** .44
        offset = Vector((q*math.cos(angle)*radii[0], q*math.sin(angle)*radii[1], z*radii[2])) * depth
        direction = _direction(angle+rng.uniform(-.65, .65), rng.uniform(-.5, .35))
        length = size*rng.uniform(.72, 1.27)
        mat = 0 if dry else rng.choices((0, 1, 2, 3), (7, 5, 2, 1))[0]
        builder.leaf(center+offset, direction, length, length*rng.uniform(.48, .7), rng.uniform(-1.3, 1.3), mat)


def _briar(leaves, stems, root, height, angle, rng):
    """Rooted arching bramble with overlapping sprays instead of isolated tufts."""
    for branch in range(5):
        a = angle+branch*2.399+rng.uniform(-.25, .25)
        direct = _direction(a)
        length = rng.uniform(.6, 1.15)*height
        points = [root+direct*(length*t)+Vector((0, 0, height*math.sin(t*math.pi*.82)))
                  for t in (0, .25, .50, .75, 1)]
        stems.tube(points, (.018, .015, .010, .006, .002), 5)
        for j in range(1, 5):
            center = points[j]
            # Tri-foliate sprays maintain a visual connection to each woody cane.
            for s in (-1, 0, 1):
                d = _direction(a+s*.95, rng.uniform(-.12, .38))
                length = rng.uniform(.20, .34)*max(.8, height)
                leaves.leaf(center, d, length, length*.63, rng.uniform(-.5, .5), rng.choice((0, 0, 1, 2)))
            if j > 1:
                _leaf_lobe(leaves, center+Vector((0, 0, .06)), (.34, .32, .20), 5, rng, .34)


def _shrub(leaves, stems, root, height, rng, broad=1):
    """Five tapered leaders and dense irregular terminal sprays."""
    phase = rng.random()*math.tau
    for branch in range(5):
        angle = phase+branch*2.399
        spread = rng.uniform(.45, .85)*broad
        top = root+_direction(angle)*spread+Vector((0, 0, height*rng.uniform(.65, 1)))
        elbow = root.lerp(top, .52)+_direction(angle+.5)*.1
        stems.tube([root, elbow, top], (.040, .019, .003), 5)
        _leaf_lobe(leaves, top, (.50*broad, .44*broad, .44), 34, rng, .37)
        # One lower lobe connects each crown to its grounded stem network.
        if branch % 2 == 0:
            _leaf_lobe(leaves, elbow+Vector((0, 0, .10)), (.38, .34, .30), 18, rng, .33)


def _fern(leaves, stems, root, scale, rng):
    """Five low paired-pinna fronds. Uses the six-triangle leaf helper."""
    for frond in range(5):
        angle = frond*math.tau/5+rng.uniform(-.35, .35)
        direct = _direction(angle)
        sideways = _direction(angle+math.pi/2)
        length = rng.uniform(.62, .88)*scale
        points = [root+direct*(length*t)+Vector((0, 0, length*.58*math.sin(t*2.2)))
                  for t in (0, .25, .50, .75, 1)]
        stems.tube(points, (.006, .005, .004, .003, .001), 4)
        for j in range(1, 8):
            t = j/8
            center = root+direct*(length*t)+Vector((0, 0, length*.58*math.sin(t*2.2)))
            pinna = length*.24*math.sin(t*math.pi)**.7
            for side in (-1, 1):
                leaves.leaf(center, sideways*side+direct*.36+Vector((0, 0, -.06)), pinna, pinna*.28, .12*side, rng.choice((0, 0, 1)))


def _island(x, y, edge, scale, name, leaf_mats, bark, dry, rng):
    leaves = Mesh(PREFIX+name+' dense understory', leaf_mats)
    stems = Mesh(PREFIX+name+' rooted woody canes', [bark])
    floor = Mesh(PREFIX+name+' curled woodland litter', [dry])
    # Three off-center root groups, each with its own height and smaller plants.
    # Along-bank spacing is variable; density follows ecological shelter pockets.
    along = Vector((0, 1, 0)) if edge in ('W', 'E') else Vector((1, 0, 0))
    across = Vector((1, 0, 0)) if edge in ('W', 'E') else Vector((0, 1, 0))
    root = Vector((x, y, GROUND_Z))
    for group, shift in enumerate((-2.05, -.25, 1.65)):
        center = root+along*(shift+rng.uniform(-.4, .4))+across*rng.uniform(-.35, .35)
        height = (1.25, 2.45, 1.75)[group]*scale*rng.uniform(.90, 1.12)
        _shrub(leaves, stems, center, height, rng, broad=rng.uniform(.85, 1.12))
        # Briers braid into the shrub base, eliminating a regular lawn-like edge.
        for j in range(2 if group != 1 else 3):
            base = center+along*rng.uniform(-.85, .85)+across*rng.uniform(-.45, .45)
            _briar(leaves, stems, base, rng.uniform(.52, .88)*scale, rng.random()*math.tau, rng)
        for j in range(2):
            base = center+along*rng.uniform(-1.0, 1.0)+across*rng.uniform(-.60, .60)
            _fern(leaves, stems, base, rng.uniform(.65, 1.0)*scale, rng)
        # Litter is concentrated under these roots and fallen wood, never scattered
        # across routes. Each is a folded leaf with a natural pointed outline.
        for j in range(40):
            a = rng.random()*math.tau
            rr = rng.random()**.55
            pos = center+along*(math.cos(a)*1.55*rr)+across*(math.sin(a)*.92*rr)
            pos.z = GROUND_Z+.014+rng.uniform(0, .025)
            length = rng.uniform(.07, .16)
            floor.leaf(pos, _direction(rng.random()*math.tau, -.03), length, length*.61, rng.uniform(-.15, .15), 0)
    return [_finish(leaves, 'Dense rooted shrub, bramble and fern island', name),
            _finish(stems, 'Tapered rooted understory stems', name),
            _finish(floor, 'Localized curled forest litter', name)]


def _coppice(name, x, y, height, lean, leaf_mats, bark, rng):
    wood = Mesh(PREFIX+name+' forked trunks', [bark])
    leaves = Mesh(PREFIX+name+' uneven connected crown', leaf_mats)
    root = Vector((x, y, GROUND_Z))
    for leader in range(5):
        angle = .4+leader*2.399+rng.uniform(-.2, .2)
        h = height*rng.uniform(.68, 1.0)
        direction = _direction(angle)
        base = root+direction*rng.uniform(.06, .30)
        # Swept five-leader silhouette; the dominant leader is deliberately offset.
        end = base+direction*rng.uniform(.8, 1.35)+Vector((lean*.45, .2, h))
        points = [base, base.lerp(end, .28)-direction*.16,
                  base.lerp(end, .62)+direction*.19, end]
        wood.tube(points, (.11, .078, .043, .007), 7)
        for fork in range(3):
            a = angle+(-.9, .65, 1.9)[fork]
            start = points[1].lerp(points[2], .4+fork*.17)
            tip = start+_direction(a)*rng.uniform(.70, 1.20)+Vector((0, 0, h*rng.uniform(.24, .41)))
            wood.tube([start, start.lerp(tip, .6), tip], (.045, .023, .004), 6)
            _leaf_lobe(leaves, tip, (.66, .60, .57), 54, rng, .39)
        _leaf_lobe(leaves, end, (.74, .65, .66), 70, rng, .40)
    return [_finish(wood, 'Five-leader leaning coppice silhouette', name),
            _finish(leaves, 'Layered connected broadleaf crown', name)]


def _deadwood(name, root, axis, length, bark, heartwood, rng, standing=False):
    """Broken snag or forked nurse log, with root fan and exposed split wood."""
    wood = Mesh(PREFIX+name+' weathered root fan and limbs', [bark])
    pale = Mesh(PREFIX+name+' splintered heartwood', [heartwood])
    root = Vector(root)
    direction = Vector(axis).normalized()
    end = root+direction*length
    elbow = root.lerp(end, .54)+Vector((.09, .12, .04))
    radius = .22 if standing else .24
    wood.tube([root, elbow, end], (radius*1.30, radius*.79, radius*.31), 9)
    # Distinct asymmetric forks rather than a generic cylinder on the floor.
    for k, t in enumerate((.32, .60, .78)):
        anchor = root.lerp(end, t)
        sign = -1 if k % 2 else 1
        limb = anchor+Vector((sign*(.5+k*.2), .34-k*.18, (.60+k*.12) if standing else .18))
        wood.tube([anchor, anchor.lerp(limb, .66), limb], (.10-k*.02, .045, .008), 6)
    for k in range(7):
        angle = k*2.399
        tip = root+_direction(angle)*rng.uniform(.65, 1.05)
        tip.z = GROUND_Z+.015
        wood.tube([tip, tip.lerp(root, .6)+Vector((0, 0, .14)), root+Vector((0, 0, .12))], (.018, .075, .15), 6)
    # Jagged pale fracture planes create a readable small story under moonlight.
    u = direction.cross(Vector((0, 1, 0))).normalized()
    v = direction.cross(u).normalized()
    for k in range(7):
        angle = k*math.tau/7
        a = end+(u*math.cos(angle)+v*math.sin(angle))*radius*.32
        b = end+(u*math.cos(angle+.50)+v*math.sin(angle+.50))*radius*.30
        tip = end+direction*rng.uniform(.10, .35)+(u+v)*rng.uniform(-.02, .02)
        pale.face([a, b, tip], [(0, 0), (1, 0), (.5, 1)])
    return [_finish(wood, 'Broken rooted snag' if standing else 'Forked fallen nurse log', name),
            _finish(pale, 'Localized exposed split heartwood', name)]


def add_perimeter_story():
    """Return all new scene objects; idempotent and does not save the scene.

    Only previous objects with this module's exact prefix may be replaced.
    Existing forest, materials, actor metadata, lights and cameras stay unchanged.
    """
    for ob in list(bpy.data.objects):
        if ob.name.startswith(PREFIX):
            mesh = ob.data if ob.type == 'MESH' else None
            bpy.data.objects.remove(ob, do_unlink=True)
            if mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
    rng = random.Random(831702)
    leaves, bark, dry, pale = _materials()
    result = []
    for name, x, y, edge, scale in ISLANDS:
        result.extend(_island(x, y, edge, scale, name, leaves, bark, dry, rng))
    for name, x, y, height, lean in SILHOUETTES:
        result.extend(_coppice(name, x, y, height, lean, leaves, bark, rng))
    result.extend(_deadwood('west storm-broken snag', (-32.5, 4.6, GROUND_Z),
                            (-.19, .10, 1), 4.25, bark, pale, rng, True))
    result.extend(_deadwood('north forked nurse log', (-8.8, 30.4, GROUND_Z+.18),
                            (1, .24, .028), 4.7, bark, pale, rng))
    result.extend(_deadwood('south old rooted bough', (15.6, -35.3, GROUND_Z+.17),
                            (.90, -.40, .018), 3.4, bark, pale, rng))
    bpy.context.view_layer.update()
    # Guard at geometry level: all vertices, not just object origins or roots.
    intrusion = []
    for ob in result:
        for vertex in ob.data.vertices:
            p = ob.matrix_world @ vertex.co
            if abs(p.x) <= 26.08 and abs(p.y) <= 26.08:
                intrusion.append(ob.name)
                break
            if -31.1 <= p.y <= -25.9 and abs(p.x) <= 6.10:
                intrusion.append(ob.name+' forecourt')
                break
    if intrusion:
        # Fail before the coordinator can save a misplaced foliage pass.
        for ob in result:
            if ob.name in bpy.data.objects:
                bpy.data.objects.remove(ob, do_unlink=True)
        raise RuntimeError('Perimeter story clearance violated: '+', '.join(intrusion))
    triangles = sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in result)
    print('PERIMETER_STORY', len(result), 'static decoration meshes;', triangles,
          'triangles; 13 irregular islands, 5 coppices, 3 deadwood silhouettes;',
          '52x52 m core, gate and full forecourt clear; no gameplay flags', flush=True)
    return result
