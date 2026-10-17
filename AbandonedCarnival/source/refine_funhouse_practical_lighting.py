"""Cycle 10: two bracket-mounted reflector floods for the funhouse facade.

Call add_funhouse_practical_lighting() with the sequential carnival scene open.
This module does not open, save, render or export a scene, does not edit existing
objects/materials, and does not change collision or Blueprint data.  It reuses
the validated batch mesh/physical-UV helper from refine_funhouse_realism.

The light sources coincide with visible 430 mm reflector apertures. Each lamp
has a curved double-skin bell, glass pane, rolled lip, pivoting yoke, hex bolts,
cable, two post mounting plates, a bent arm and a diagonal support brace.
Power and color can be tuned by the coordinator through the optional arguments;
the default is a restrained warm-neutral wash, not an orange ambient fill.
"""
import json
import math

import bpy
import bmesh
from mathutils import Vector
from refine_funhouse_realism import _Mesh, _smooth_path

PREFIX = 'FHPL_'
ROOT_NAME = PREFIX+'Reflector_Floods_Root'
PASS_NAME = 'Funhouse supported practical reflector lighting'
DEFAULT_POWER_W = 120.0
DEFAULT_COLOR = (1.0, .91, .80)


class _PracticalMesh(_Mesh):
    def tube(self, points, radius, material=0, sides=10, depth_radius=None, closed=False):
        """Parallel-transport tube frames prevent twists in mirrored bent arms."""
        points=[Vector(point) for point in points]
        if len(points)<2:
            return
        depth_radius=radius if depth_radius is None else depth_radius
        verts=[];faces=[];normal=None
        if closed:
            normal=(points[1]-points[0]).cross(points[2]-points[1]).normalized()
        for i,center in enumerate(points):
            tangent=((points[(i+1)%len(points)]-points[(i-1)%len(points)]) if closed else
                     (points[min(i+1,len(points)-1)]-points[max(0,i-1)])).normalized()
            if normal is None or abs(normal.dot(tangent))>.999:
                axes=(Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
                normal=min(axes,key=lambda axis:abs(axis.dot(tangent)))
            normal=(normal-tangent*normal.dot(tangent)).normalized()
            across=tangent.cross(normal).normalized()
            for k in range(sides):
                a=math.tau*k/sides
                verts.append(center+across*(radius*math.cos(a))+normal*(depth_radius*math.sin(a)))
        for i in range(len(points) if closed else len(points)-1):
            j=(i+1)%len(points)
            for k in range(sides):
                faces.append((i*sides+k,i*sides+(k+1)%sides,j*sides+(k+1)%sides,j*sides+k))
        if not closed:
            faces.extend((tuple(reversed(range(sides))),tuple((len(points)-1)*sides+k for k in range(sides))))
        self.add(verts,faces,material,True)
        if not closed:
            self.smooth[-1]=self.smooth[-2]=False


def _builder(name, materials):
    mesh = _PracticalMesh(name, materials)
    mesh.name = PREFIX+name
    return mesh


def _lamp_basis(center, target):
    origin, aim = Vector(center), (Vector(target)-Vector(center)).normalized()
    right = Vector((0,0,1)).cross(aim).normalized()
    up = aim.cross(right).normalized()
    def world(point):
        return origin+right*point[0]+up*point[1]+aim*point[2]
    return world, aim


def _lathed_bell(builder, world, rust_index, reflector_index, segments=32):
    """Closed thin sheet-metal shell, never a solid cone or collapsed pole."""
    profile = ((.100,.000),(.158,.036),(.224,.125),(.228,.160),
               (.215,.160),(.211,.125),(.147,.043),(.092,.014))
    verts = [world((radius*math.cos(math.tau*k/segments),
                    radius*math.sin(math.tau*k/segments),z))
             for radius,z in profile for k in range(segments)]
    faces = [(j*segments+k,j*segments+(k+1)%segments,
              ((j+1)%len(profile))*segments+(k+1)%segments,
              ((j+1)%len(profile))*segments+k)
             for j in range(len(profile)) for k in range(segments)]
    first = len(builder.faces)
    builder.add(verts,faces,rust_index,True)
    for j in (4,5,6):
        for k in range(segments):
            builder.indices[first+j*segments+k]=reflector_index
    for j in (3,7):
        for k in range(segments):
            builder.smooth[first+j*segments+k]=False


def _ring(builder, world, radius, z, thickness, material, segments=32):
    points=[world((radius*math.cos(math.tau*k/segments),
                   radius*math.sin(math.tau*k/segments),z)) for k in range(segments)]
    builder.tube(points,thickness,material,sides=8,closed=True)


def _validate(mesh_objects):
    """Run in the coordinator's serialized Blender invocation, before lights."""
    problems=[]
    triangle_count=0
    for obj in mesh_objects:
        mesh=obj.data
        uv=mesh.uv_layers.active
        if not uv:
            problems.append(obj.name+': missing UVMap')
            continue
        mesh.calc_loop_triangles()
        triangle_count+=len(mesh.loop_triangles)
        if any(tri.area<=1e-12 for tri in mesh.loop_triangles):
            problems.append(obj.name+': zero-area triangle')
        if any(not math.isfinite(q) for vert in mesh.vertices for q in vert.co):
            problems.append(obj.name+': nonfinite vertex')
        # All hardware is high on the existing sign supports, entirely clear of
        # the walkable doorway and the maze even before any runtime collision.
        if any(vert.co.z<4.45 for vert in mesh.vertices):
            problems.append(obj.name+': low hardware outside planned mount envelope')
        for face in mesh.polygons:
            if face.material_index>=len(mesh.materials) or not mesh.materials[face.material_index]:
                problems.append(obj.name+': missing material slot')
                break
            points=[uv.data[i].uv for i in face.loop_indices]
            if any(not math.isfinite(q) for point in points for q in point):
                problems.append(obj.name+': nonfinite UV')
                break
            area=abs(sum(points[k].x*points[(k+1)%len(points)].y-
                         points[(k+1)%len(points)].x*points[k].y for k in range(len(points))))*.5
            if area<=1e-12:
                problems.append(obj.name+': zero-area UV face')
                break
        bm=bmesh.new()
        bm.from_mesh(mesh)
        if any(not edge.is_manifold for edge in bm.edges):
            problems.append(obj.name+': nonmanifold edge')
        if any(edge.is_manifold and not edge.is_contiguous for edge in bm.edges):
            problems.append(obj.name+': inconsistent winding')
        bm.free()
    if problems:
        raise RuntimeError('Funhouse practical geometry validation failed: '+'; '.join(problems))
    return triangle_count


def add_funhouse_practical_lighting(power_w=DEFAULT_POWER_W, color=DEFAULT_COLOR):
    """Add two visible, supported, directed floods exactly once; never save.

    power_w is the Blender AREA energy per fixture, not an electrical rating.
    To tune an existing application, edit the two FHPL_*_Area light data blocks;
    this function intentionally does not mutate an already applied pass.
    """
    existing=bpy.data.objects.get(ROOT_NAME)
    if existing:
        return {'status':'already_applied','root':ROOT_NAME}
    power_w=float(power_w)
    color=tuple(float(channel) for channel in color)
    if not math.isfinite(power_w) or not 0<power_w<=1000:
        raise ValueError('Use a positive practical-flood energy no greater than 1000 W per fixture.')
    if len(color)!=3 or any(not math.isfinite(q) or q<0 or q>1 for q in color):
        raise ValueError('color must contain three finite RGB channels in the range 0..1.')
    required=('rust','black','FH_Aged_Silver_Mirror','glass','cream','bulb','gold')
    missing=[name for name in required if bpy.data.materials.get(name) is None]
    if missing:
        raise RuntimeError('Required existing carnival materials missing: '+', '.join(missing))
    for name in ('FH_Sign_Support','FH_Sign_Support.001'):
        if bpy.data.objects.get(name) is None:
            raise RuntimeError('Expected the existing funhouse sign support: '+name)
    mats=[bpy.data.materials[name] for name in required]
    RUST,BLACK,REFLECTOR,GLASS,CREAM,BULB,GOLD=range(len(mats))
    collection=bpy.data.collections.get('Funhouse practical reflector lights')
    if collection is None:
        collection=bpy.data.collections.new('Funhouse practical reflector lights')
        bpy.context.scene.collection.children.link(collection)
    root=bpy.data.objects.new(ROOT_NAME,None)
    collection.objects.link(root)
    root['ArtPass']=PASS_NAME
    root['preserved']='Sign text, sculpted face, 2.5 m entry, rear exit, mirrors, maze and eligible props'
    created=[]
    planned_lights=[]
    try:
        for side,post_x,center,target in (
            ('West',11.4,(12.12,5.10,5.60),(15.40,6.14,5.05)),
            ('East',20.6,(19.88,5.10,5.60),(16.60,6.14,5.05))):
            world,aim=_lamp_basis(center,target)
            builder=_builder(side+'_Bracket_Mounted_Reflector',mats)
            # Mounting plates overlap the front face of the retained steel post.
            # The two attachment heights and brace carry the cantilever load.
            for z in (4.84,5.34):
                builder.box((post_x,6.915,z),(.24,.045,.23),RUST)
                for dx in (-.073,.073):
                    for dz in (-.065,.065):
                        builder.tube([(post_x+dx,6.889,z+dz),(post_x+dx,6.874,z+dz)],.019,GOLD,sides=6)
            joint=world((0,-.266,.042))
            arm=_smooth_path([(post_x,6.90,5.34),(post_x,6.56,5.34),
                              (post_x,5.58,5.34),(post_x,5.31,5.34),
                              tuple(joint)],5)
            builder.tube(arm,.025,RUST,sides=12)
            builder.tube([(post_x,6.90,4.84),(post_x,5.53,5.34)],.018,RUST,sides=10)
            # Under-arm cable returns to the post; it never falls into a route.
            cable=_smooth_path([(post_x,6.93,4.60),(post_x,6.88,5.28),
                                (post_x,5.52,5.28),tuple(joint-Vector((0,0,.035))),
                                tuple(world((0,-.08,-.035)))],5)
            builder.tube(cable,.007,BLACK,sides=8)
            builder.tube([world((0,0,-.048)),world((0,0,.010))],.098,RUST,sides=24)
            # The U-shaped steel yoke contacts the support arm and side pivots.
            yoke=_smooth_path([world((-.258,.005,.045)),world((-.258,-.20,.045)),
                               world((-.22,-.266,.045)),world((.22,-.266,.045)),
                               world((.258,-.20,.045)),world((.258,.005,.045))],5)
            builder.tube(yoke,.014,RUST,sides=10)
            for direction in (-1,1):
                builder.tube([world((direction*.144,0,.045)),world((direction*.284,0,.045))],.031,BLACK,sides=16)
                builder.tube([world((direction*.279,0,.045)),world((direction*.300,0,.045))],.025,GOLD,sides=6)
            _lathed_bell(builder,world,RUST,REFLECTOR)
            # Replaceable glass disk and real rolled metal gasket/lip.
            builder.tube([world((0,0,.145)),world((0,0,.149))],.210,GLASS,sides=32)
            _ring(builder,world,.213,.154,.006,BLACK)
            _ring(builder,world,.226,.161,.007,RUST)
            # Compact luminous ceramic-centred source inside the reflector.
            builder.tube([world((0,0,.027)),world((0,0,.070))],.031,CREAM,sides=16)
            builder.tube([world((0,0,.071)),world((0,0,.091))],.023,BULB,sides=16)
            # Three faceplate screws keep the lens retention physically legible.
            for k in range(3):
                a=math.tau*k/3+.3
                q=(.226*math.cos(a),.226*math.sin(a))
                builder.tube([world((q[0],q[1],.161)),world((q[0],q[1],.176))],.011,GOLD,sides=6)
            obj=builder.finish(collection,root)
            obj['ArtPass']=PASS_NAME
            obj['refinement_set']='FunhousePracticalLighting'
            obj['fixture_role']='430 mm aged reflector flood with double-skin bell and braced mounting arm'
            obj['physical_mount']='Existing '+('west' if side=='West' else 'east')+' funhouse sign support'
            obj['collision_policy']='Small overhead fixture; no automatic collider or building hull'
            created.append(obj)
            planned_lights.append((side,world((0,0,.172)),aim,tuple(target),obj.name))
        triangles=_validate(created)
        lights=[]
        for side,position,aim,target,fixture_name in planned_lights:
            data=bpy.data.lights.new(PREFIX+side+'_Area','AREA')
            data.energy=power_w
            data.color=color
            data.shape='DISK'
            data.size=.380
            if hasattr(data,'spread'):
                data.spread=math.radians(120)
            lamp=bpy.data.objects.new(data.name,data)
            collection.objects.link(lamp)
            lamp.parent=root
            lamp.location=position
            lamp.rotation_euler=aim.to_track_quat('-Z','Y').to_euler()
            lamp['ArtPass']=PASS_NAME
            lamp['refinement_set']='FunhousePracticalLighting'
            lamp['fixture_object']=fixture_name
            lamp['physical_source']='Visible reflector aperture, 11 mm in front of the rolled lip'
            lamp['aim_target_m']=target
            lights.append(lamp.name)
            created.append(lamp)
        report={'status':'applied','root':ROOT_NAME,'mesh_objects_added':2,'directed_area_lights_added':2,
                'triangles_added':triangles,'geometry_uv_validation':'passed','power_w_each':power_w,
                'color_rgb':color,'aperture_diameter_m':.380,'beam_spread_degrees':120,
                'light_objects':lights,'geometry_support':'Two physically connected braced sign-post mounts',
                'existing_materials_modified':0,'existing_objects_modified':0,'save_performed':False,
                'mouth_clear_width_m':2.5,'rear_exit_maze_and_props_unchanged':True}
        root['report_json']=json.dumps(report,sort_keys=True)
        return report
    except Exception:
        for obj in created:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj,do_unlink=True)
        if root.name in bpy.data.objects:
            bpy.data.objects.remove(root,do_unlink=True)
        raise
