"""Small synthetic Blender-only export test. Does not open/export final source."""
import bpy,ast,math,json,tempfile
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
# Extract actual production mesh builder without executing the scene exporter.
tree=ast.parse((ROOT/'source/export_environment.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='mesh_object')
ns={'bpy':bpy,'scene':scene};exec(compile(ast.Module(body=[fn],type_ignores=[]),'export_environment_mesh_builder','exec'),ns)
vs=[];fs=[];uvs=[];smooth=[];normals=[];mi=[];sources=[]
for j in range(2):
 bpy.ops.mesh.primitive_cube_add(size=2,location=(j*4,0,0));o=bpy.context.object;o.name='SyntheticWeightedBevel%d'%j
 o.scale=((-1 if j else 1)*1.4,.6,1.1);o.rotation_euler=(.2,.45,.3)
 for p in o.data.polygons:p.use_smooth=True
 bevel=o.modifiers.new('Synthetic bevel','BEVEL');bevel.width=.16;bevel.segments=3
 weighted=o.modifiers.new('Synthetic weighted normals','WEIGHTED_NORMAL');weighted.keep_sharp=True
 o.data.set_sharp_from_angle(angle=math.radians(38))
 sources.append(o)
bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
for o in sources:
 ev=o.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
 linear=o.matrix_world.to_3x3();nm=linear.inverted().transposed();rev=linear.determinant()<0
 corner=[(nm@n.vector).normalized() for n in me.corner_normals];off=len(vs)
 vs.extend(tuple(o.matrix_world@v.co) for v in me.vertices)
 for p in me.polygons:
  vertices=list(p.vertices);loops=list(p.loop_indices)
  if rev:vertices.reverse();loops.reverse()
  fs.append(tuple(off+i for i in vertices));normals.append([tuple(corner[i]) for i in loops]);uvs.append([tuple(me.uv_layers.active.data[i].uv) for i in loops]);smooth.append(p.use_smooth);mi.append(0)
 ev.to_mesh_clear()
ob=ns['mesh_object']('SM_SyntheticNormals',vs,fs,[],mi,uvs,smooth,normals)
expected=[Vector((n[0],-n[1],n[2])) for face in normals for n in reversed(face)]
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,a.normalized().dot(b.normalized())))))
pre=max(angle(n.vector,e) for n,e in zip(ob.data.corner_normals,expected))
# Match geometry corners, including split normals at sharp corners, after FBX reordering.
lookup={}
for loop,n in zip(ob.data.loops,expected):
 pos=ob.data.vertices[loop.vertex_index].co;key=tuple(round(v,3) for v in pos);lookup.setdefault(key,[]).append(n)
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
path=str(ROOT/'qa/synthetic_normals_test.fbx')
bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_mesh_modifiers=False,mesh_smooth_type='FACE',use_tspace=False,bake_anim=False)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path,use_custom_normals=True)
ob=bpy.data.objects['SM_SyntheticNormals'];post=0;unmatched=0
for loop,n in zip(ob.data.loops,ob.data.corner_normals):
 pos=ob.matrix_world@ob.data.vertices[loop.vertex_index].co;key=tuple(round(v,3) for v in pos)
 if key not in lookup:unmatched+=1;continue
 post=max(post,min(angle(n.vector,e) for e in lookup[key]))
r={'test':'synthetic two weighted-bevel boxes, rotated and nonuniformly scaled; one negative scale','source_scene_opened':False,'unreal_executed':False,'corner_count':len(expected),'builder_max_normal_error_degrees':pre,'fbx_roundtrip_max_normal_error_degrees':post,'unmatched_corners':unmatched,'passed':pre<.1 and post<.1 and unmatched==0}
(ROOT/'qa/environment_normals_synthetic.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));assert r['passed']
