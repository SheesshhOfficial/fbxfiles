"""Read-only FBX roundtrip into disposable Blender scene; not Unreal validation."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
r=json.loads((ROOT/'qa/environment_export.json').read_text());results=[]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for a in r['assets']:
 bpy.ops.import_scene.fbx(filepath=str(ROOT/a['fbx']),use_custom_normals=True)
 ob=bpy.data.objects.get(a['asset_name'])
 result={'asset':a['asset_name'],'mesh_found':ob is not None}
 if ob:
  pts=[ob.matrix_world@v.co for v in ob.data.vertices]
  bounds=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]]
  err=max(abs(bounds[j][i]-a['bounds_local_cm'][j][i]) for j in range(2) for i in range(3))
  hulls=[o for o in bpy.context.scene.objects if o.name.startswith('UCX_'+a['asset_name']+'_')]
  result.update({'bounds_max_error_cm':err,'bounds_pass':err<.01,'uv_layers':len(ob.data.uv_layers),'materials':len(ob.data.materials),'hulls_imported':len(hulls),'hulls_match':len(hulls)==a['ucx_hulls'],'source_triangles':a['triangles'],'imported_triangles':sum(len(p.vertices)-2 for p in ob.data.polygons)})
 results.append(result)
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 for m in list(bpy.data.meshes):
  if m.users==0:bpy.data.meshes.remove(m)
 print('ROUNDTRIP',a['asset_name'],result,flush=True)
out={'tool':'Blender FBX export/import roundtrip','runtime_verified':False,'asset_count':len(results),'all_passed':all(x.get('bounds_pass') and x.get('hulls_match') and x.get('uv_layers',0)>0 and x.get('source_triangles')==x.get('imported_triangles') for x in results),'results':results,'limitation':'Checks FBX geometry, local bounds, UV existence and UCX count in Blender. Does not prove Unreal axis conversion, collision import or gameplay.'}
(ROOT/'qa/environment_roundtrip.json').write_text(json.dumps(out,indent=2));print('ALL_PASS',out['all_passed'])
