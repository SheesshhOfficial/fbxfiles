"""Full saved-source to FBX corner UV/material/normal QA. Never saves source.
Run with the approved source blend loaded; exported manifest SHA must match.
"""
import bpy,json,hashlib,math,os
from pathlib import Path
from mathutils import Vector,kdtree
ROOT=Path(__file__).resolve().parents[1];manifest=json.loads((ROOT/'unreal/environment_manifest.json').read_text())
source_scene=bpy.context.scene;source_hash=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
assert source_hash==manifest['source_sha256'],'Source/FBX manifests do not match'
source_objects={o.name:o for o in source_scene.objects};test_scene=bpy.data.scenes.new('VERIFY_TEMP_ENVIRONMENT')
test_scene.unit_settings.system='METRIC';test_scene.unit_settings.scale_length=.01
results=[]
selected=set(filter(None,os.environ.get('CARNIVAL_VERIFY_TILES','').split(',')))
for a in manifest['assets']:
 if selected and a['asset_name'] not in selected:continue
 bpy.context.window.scene=source_scene;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
 points=[];corners=[];point_sources=[];expected_loops=0;expected_triangles=0;origin=Vector(a['pivot_source_m'])
 for name in a['source_objects']:
  o=source_objects[name]
  assert not o.get('PropActorTag') and not o.get('render_only') and not o.get('visual_replaced') and not o.get('_assembly_source') and not o.hide_render
  ev=o.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
  off=len(points);nm=o.matrix_world.to_3x3().inverted().transposed()
  local_normals=[(nm@n.vector).normalized() for n in me.corner_normals]
  for v in me.vertices:
   p=o.matrix_world@v.co-origin;points.append((100*p.x,-100*p.y,100*p.z));corners.append([]);point_sources.append(o.name)
  layer=me.uv_layers.active
  for p in me.polygons:
   mat=me.materials[p.material_index].name if me.materials else None;index=a['materials'].index(mat) if mat else 0
   axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=[i for i in range(3) if i!=axis]
   expected_triangles+=len(p.vertices)-2
   for li in p.loop_indices:
    vi=me.loops[li].vertex_index;n=local_normals[li]
    uv=tuple(layer.data[li].uv) if layer else tuple(me.vertices[vi].co[i] for i in axes)
    corners[off+vi].append((uv,(n.x,-n.y,n.z),index));expected_loops+=1
  ev.to_mesh_clear()
 kd=kdtree.KDTree(len(points))
 for i,p in enumerate(points):kd.insert(p,i)
 kd.balance();bpy.context.window.scene=test_scene
 bpy.ops.import_scene.fbx(filepath=str(ROOT/a['fbx']),use_custom_normals=True,use_image_search=False)
 ob=test_scene.objects.get(a['asset_name']);r={'asset':a['asset_name'],'mesh_found':bool(ob)}
 if ob:
  me=ob.data;uv=me.uv_layers.active;actual_points=[ob.matrix_world@v.co for v in me.vertices]
  bounds=[[min(p[i] for p in actual_points) for i in range(3)],[max(p[i] for p in actual_points) for i in range(3)]]
  r['bounds_max_error_cm']=max(abs(bounds[j][i]-a['bounds_local_cm'][j][i]) for j in range(2) for i in range(3))
  actual_mats=[m.name if m else None for m in me.materials]
  def match_name(actual,expected):return actual==expected or (actual and expected and actual.startswith(expected+'.') and actual[len(expected)+1:].isdigit())
  r['material_slots_match']=len(actual_mats)==len(a['materials']) and all(match_name(x,y) for x,y in zip(actual_mats,a['materials']))
  r['actual_material_names']=actual_mats;r['expected_material_names']=a['materials']
  r['corner_count_match']=len(me.loops)==expected_loops;r['triangles_match']=sum(len(p.vertices)-2 for p in me.polygons)==expected_triangles
  r['uv_layer_present']=bool(uv);r['missing_position_vertices']=0;r['corner_mismatches']=0;r['normal_max_vector_error']=0.;r['uv_max_error']=0.;r['mismatch_examples']=[];r['mismatch_components']={}
  candidates={i:[j for _,j,_ in kd.find_range(p,.01)] for i,p in enumerate(actual_points)}
  r['missing_position_vertices']=sum(not v for v in candidates.values())
  transform=ob.matrix_world.to_3x3().inverted().transposed();actual_normals=[(transform@n.vector).normalized() for n in me.corner_normals]
  for p in me.polygons:
   for li in p.loop_indices:
    vi=me.loops[li].vertex_index;n=actual_normals[li];u=uv.data[li].uv if uv else Vector((999,999))
    best=None;best_source=None
    for j in candidates[vi]:
     for eu,en,em in corners[j]:
      if em!=p.material_index:continue
      uv_error=max(abs(eu[k]-u[k]) for k in range(2))
      if uv_error>.00002:continue
      normal_error=math.sqrt(sum((en[k]-n[k])**2 for k in range(3)))
      if best is None or normal_error<best[0]:best=(normal_error,uv_error);best_source=point_sources[j]
    if best is None or best[0]>.002:
     r['corner_mismatches']+=1
     owner=best_source or 'unresolved';r['mismatch_components'][owner]=r['mismatch_components'].get(owner,0)+1
     if len(r['mismatch_examples'])<5:r['mismatch_examples'].append({'loop':li,'vertex':vi,'best_error':best,'imported_smooth':p.use_smooth,'imported_normal':list(n),'source_candidates':[{'source':point_sources[j],'corners':corners[j]} for j in candidates[vi]][:4]})
    if best:
     r['normal_max_vector_error']=max(r['normal_max_vector_error'],best[0]);r['uv_max_error']=max(r['uv_max_error'],best[1])
  hulls=[o for o in test_scene.objects if o.name.startswith('UCX_'+a['asset_name']+'_')]
  r['hull_count_match']=len(hulls)==a['ucx_hulls']
  r['passed']=r['bounds_max_error_cm']<.01 and r['material_slots_match'] and r['corner_count_match'] and r['triangles_match'] and r['uv_layer_present'] and r['hull_count_match'] and not r['corner_mismatches'] and not r['missing_position_vertices']
 else:r['passed']=False
 results.append(r);print('SOURCE_ROUNDTRIP',a['asset_name'],r['passed'],r.get('corner_mismatches'),flush=True)
 for obj in list(test_scene.objects):
  mesh=obj.data if obj.type=='MESH' else None;bpy.data.objects.remove(obj,do_unlink=True)
  if mesh and mesh.users==0:bpy.data.meshes.remove(mesh)
 del points,corners,kd,candidates
report={'source_sha256':source_hash,'test':'Saved source evaluated corners versus Blender re-imported FBX','unreal_runtime_verified':False,'tolerances':{'position_cm':.01,'uv_absolute':.00002,'normal_vector':.002},'asset_count':len(results),'all_passed':all(x['passed'] for x in results),'results':results}
(ROOT/('qa/environment_source_roundtrip_diagnostic.json' if selected else 'qa/environment_source_roundtrip.json')).write_text(json.dumps(report,indent=2));print('ALL_PASS',report['all_passed'])
