"""Independent raw FBX versus evaluated frozen-source fidelity, no Blender re-encoding."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from io_scene_fbx import parse_fbx
ROOT=Path(__file__).resolve().parents[1]/'export';m=json.loads((ROOT/'unreal/environment_manifest.json').read_text())
sourcehash=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest();assert sourcehash==m['source_sha256']
dg=bpy.context.evaluated_depsgraph_get();results=[]
def child(e,k):return next((c for c in e.elems if c.id==k),None)
for a in m['assets']:
 points=[];indices=[];uvs=[];normals=[];materials=[];origin=Vector(a['pivot_source_m'])
 for name in a['source_objects']:
  o=bpy.data.objects[name]
  assert not any(o.get(k) for k in ['PropActorTag','render_only','visual_replaced','_assembly_source'])
  ev=o.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
  linear=o.matrix_world.to_3x3();normal_matrix=linear.inverted().transposed();corner=[(normal_matrix@n.vector).normalized() for n in me.corner_normals]
  offset=len(points)
  for v in me.vertices:
   p=o.matrix_world@v.co-origin;points.append((100*p.x,-100*p.y,100*p.z))
  uv=me.uv_layers.active
  for p in me.polygons:
   loops=list(p.loop_indices)
   if linear.determinant()>0:loops.reverse()
   axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=[i for i in range(3) if i!=axis]
   for li in loops:
    vi=me.loops[li].vertex_index;indices.append(offset+vi)
    uvs.append(tuple(uv.data[li].uv) if uv else tuple(me.vertices[vi].co[i] for i in axes))
    n=corner[li];normals.append((n.x,-n.y,n.z))
   indices[-1]=-indices[-1]-1
   materials.append(a['materials'].index(me.materials[p.material_index].name) if me.materials else 0)
  ev.to_mesh_clear()
 tree,_=parse_fbx.parse(str(ROOT/a['fbx']));objects=child(tree,b'Objects')
 geo=next(g for g in objects.elems if g.id==b'Geometry' and g.props[1].split(b'\x00')[0].decode()==a['asset_name'])
 vertices=child(geo,b'Vertices').props[0];polys=child(geo,b'PolygonVertexIndex').props[0]
 nlayer=child(geo,b'LayerElementNormal');nv=child(nlayer,b'Normals').props[0];ni=child(nlayer,b'NormalsIndex');ni=ni.props[0] if ni else range(len(nv)//3)
 ulayers=[e for e in geo.elems if e.id==b'LayerElementUV'];uv=child(ulayers[0],b'UV').props[0];ui=child(ulayers[0],b'UVIndex').props[0]
 ml=child(geo,b'LayerElementMaterial');mv=child(ml,b'Materials').props[0]
 ve=max(abs(vertices[i*3+j]-p[j]) for i,p in enumerate(points) for j in range(3))
 ne=max(math.sqrt(sum((nv[k*3+j]-normals[i][j])**2 for j in range(3))) for i,k in enumerate(ni))
 ue=max(abs(uv[k*2+j]-uvs[i][j]) for i,k in enumerate(ui) for j in range(2))
 matok=list(mv)==materials or len(mv)==1 and all(x==mv[0] for x in materials)
 result={'asset':a['asset_name'],'vertices':len(points),'corners':len(normals),'raw_vertex_count_match':len(vertices)==len(points)*3,'raw_corner_count_match':len(ni)==len(normals),'topology_exact':list(polys)==indices,'max_vertex_error_cm':ve,'max_corner_normal_vector_error':ne,'uv_layer_count':len(ulayers),'max_uv_error':ue,'polygon_material_assignment_exact':matok,'fbx_sha256':hashlib.sha256((ROOT/a['fbx']).read_bytes()).hexdigest()}
 result['passed']=result['raw_vertex_count_match'] and result['raw_corner_count_match'] and result['topology_exact'] and ve<.001 and ne<1e-7 and ue<1e-6 and matok and len(ulayers)==1
 results.append(result);print('RAW_FIDELITY',a['asset_name'],result['passed'],ve,ne,ue,flush=True)
report={'source_sha256':sourcehash,'method':'Raw FBX arrays compared to evaluated frozen source; numerical inverse-transpose normal references captured before Blender output custom-normal encoding. Geometry/topology unchanged.','all_passed':all(r['passed'] for r in results),'asset_count':len(results),'unreal_runtime_verified':False,'results':results}
(ROOT/'qa/environment_raw_fidelity.json').write_text(json.dumps(report,indent=2));print('ALL_PASS',report['all_passed'])
