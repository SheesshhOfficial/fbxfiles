"""Small synthetic test only; does not load or export the carnival scene."""
import bpy,ast,os,json,math,tempfile
from mathutils import Matrix,Vector
from io_scene_fbx import parse_fbx
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
module=ast.parse(open(ROOT+'/source/export_props.py').read())
node=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='transform_mesh_preserving_corner_normals')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<exporter function>','exec'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.ops.mesh.primitive_cube_add();obj=bpy.context.object;me=obj.data
for p in me.polygons:p.use_smooth=True
for e in me.edges:e.use_edge_sharp=True
normals=[]
for p in me.polygons:
 for i in p.loop_indices:normals.append((p.normal*.83+me.vertices[me.loops[i].vertex_index].co.normalized()*.17).normalized())
me.normals_split_custom_set(normals);me.update()
linear=Matrix.Rotation(.37,3,'Z')@Matrix.Diagonal((130.,-80.,175.));nm=linear.inverted().transposed()
expected={(p.index,me.loops[i].vertex_index):(nm@me.corner_normals[i].vector).normalized() for p in me.polygons for i in p.loop_indices}
transform_mesh_preserving_corner_normals(me,linear)
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,a.normalized().dot(b.normalized())))))
angles=[angle(me.corner_normals[i].vector,expected[(p.index,me.loops[i].vertex_index)]) for p in me.polygons for i in p.loop_indices]
path='/tmp/prop_normals_synthetic.fbx'
bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH'},global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_mesh_modifiers=False,mesh_smooth_type='FACE',use_custom_props=True,bake_anim=False,path_mode='RELATIVE',embed_textures=False)
tree,version=parse_fbx.parse(path);fbxnormals=[]
def walk(e):
 if e.id==b'LayerElementNormal':
  a=next(c for c in e.elems if c.id==b'Normals').props[0]
  fbxnormals.extend(Vector(a[i:i+3]) for i in range(0,len(a),3))
 for c in e.elems:walk(c)
walk(tree)
fbx_error=max(min(angle(n,e) for e in expected.values()) for n in fbxnormals)
result={'scope':'Synthetic smooth cube with custom split corner normals, sharp edges, nonuniform scale, rotation and reflected Y. No carnival source opened.','custom_corner_normals':len(normals),'fbx_corner_normals':len(fbxnormals),'max_transform_angle_error_deg':max(angles),'max_fbx_angle_error_deg':fbx_error,'all_sharp_edges_preserved':all(e.use_edge_sharp for e in me.edges),'passed':max(angles)<.1 and fbx_error<.1 and len(fbxnormals)==len(normals) and all(e.use_edge_sharp for e in me.edges)}
open(ROOT+'/qa/prop_corner_normals_synthetic.json','w').write(json.dumps(result,indent=2));print('NORMAL_TEST',json.dumps(result))
