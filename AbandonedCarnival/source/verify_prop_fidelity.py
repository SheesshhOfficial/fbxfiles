"""Compare exported FBX render data to evaluated frozen source, including corner normals."""
import bpy,ast,os,json,math,hashlib
from mathutils import Matrix,Vector
from io_scene_fbx import parse_fbx
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d=json.load(open(ROOT+'/unreal/prop_placements.json'));source=ROOT+'/'+d['source_blend']
assert hashlib.sha256(open(source,'rb').read()).hexdigest()==d['source_blend_sha256']
bpy.ops.wm.open_mainfile(filepath=source);dg=bpy.context.evaluated_depsgraph_get()
module=ast.parse(open(ROOT+'/source/export_props.py').read());node=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='transform_mesh_preserving_corner_normals');exec(compile(ast.Module(body=[node],type_ignores=[]),'<export transform>','exec'))
C=Matrix.Diagonal((100.,-100.,100.));results=[]
def child(e,name):return next((c for c in e.elems if c.id==name),None)
def vector_error(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
for a in d['assets']:
 o=bpy.data.objects[a['source_exemplar']];me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
 linear=C@o.matrix_world.to_3x3();nm=linear.inverted().transposed()
 reference={(p.index,me.loops[i].vertex_index):(nm@me.corner_normals[i].vector).normalized() for p in me.polygons for i in p.loop_indices}
 transform_mesh_preserving_corner_normals(me,linear)
 tree,_=parse_fbx.parse(ROOT+'/unreal/'+a['fbx']);objects=child(tree,b'Objects');connections=child(tree,b'Connections')
 model=next(e for e in objects.elems if e.id==b'Model' and e.props[1].split(b'\x00')[0].decode()==a['asset_name'])
 ids=[e.props[1] for e in connections.elems if e.props[0]==b'OO' and e.props[2]==model.props[0]]
 geo=next(e for e in objects.elems if e.id==b'Geometry' and e.props[0] in ids)
 verts=child(geo,b'Vertices').props[0];ve=max(abs(verts[i*3+j]-v.co[j]) for i,v in enumerate(me.vertices) for j in range(3))
 polys=child(geo,b'PolygonVertexIndex').props[0];indices=[-x-1 if x<0 else x for x in polys];topology=indices==[l.vertex_index for l in me.loops]
 nlayer=child(geo,b'LayerElementNormal');ns=child(nlayer,b'Normals').props[0];ni=child(nlayer,b'NormalsIndex');ni=ni.props[0] if ni else range(len(ns)//3)
 normals=[ns[i*3:i*3+3] for i in ni];ne=max(vector_error(n,me.corner_normals[i].vector) for i,n in enumerate(normals)) if len(normals)==len(me.loops) else None
 source_ne=max(vector_error(normals[i],reference[(p.index,me.loops[i].vertex_index)]) for p in me.polygons for i in p.loop_indices) if len(normals)==len(me.loops) else None
 layers=[e for e in geo.elems if e.id==b'LayerElementUV'];uv_errors=[]
 for layer,expected in zip(layers,me.uv_layers):
  uv=child(layer,b'UV').props[0];ui=child(layer,b'UVIndex').props[0];uv_errors.append(max(abs(uv[index*2+j]-expected.data[i].uv[j]) for i,index in enumerate(ui) for j in range(2)))
 ml=child(geo,b'LayerElementMaterial');mat=child(ml,b'Materials').props[0] if ml else []
 expected_mat=[p.material_index for p in me.polygons];matok=list(mat)==expected_mat or (len(mat)==1 and all(m==mat[0] for m in expected_mat))
 result={'asset':a['asset_name'],'vertices':len(me.vertices),'corners':len(me.loops),'max_vertex_error_cm':ve,'topology_exact':topology,'max_corner_normal_vector_error':ne,'max_original_source_normal_vector_error':source_ne,'uv_layer_count':len(layers),'max_uv_error':max(uv_errors,default=0),'polygon_material_assignment_exact':matok,'passed':source_ne is not None and source_ne<.001 and ve<1e-4 and topology and ne is not None and ne<1e-5 and len(layers)==len(me.uv_layers) and max(uv_errors,default=0)<1e-6 and matok}
 results.append(result);bpy.data.meshes.remove(me)
report={'source_blend_sha256':d['source_blend_sha256'],'method':'Raw FBX geometry/topology/per-corner normal/UV/per-face material comparison against evaluated source with identical explicit UE transformation. No Unreal execution.','all_passed':all(x['passed'] for x in results),'assets':results}
open(ROOT+'/qa/prop_fidelity.json','w').write(json.dumps(report,indent=2));print('PROP_FIDELITY',report['all_passed'],len(results))
