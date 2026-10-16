"""Read-only Blender regression: mutates in memory, restores, never saves input."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import export_source_snapshot as exp
root=Path(sys.argv[-1]).resolve();m=json.loads((root/'manifest.json').read_text())
rows=[]
for a in m['assets']:
 path=root/a['fbx_path'];expected=['UBX_'+a['asset_id']+'_00'] if a['collision']['strategy']=='box' else []
 exp.verify_collision_model_names(path,expected)
for a in json.loads((root/'walking_companions.json').read_text())['assets']:
 exp.verify_collision_model_names(root/a['fbx_path'],['UBX_'+a['asset_id']+'_'+str(i).zfill(2) for i in range(a['boxes'])])
rows.append({'test':'all_342_FBX_collision_Model_names_and_Geometry_connections','passed':True})
me=bpy.data.meshes[m['assets'][0]['asset_id']]
def refused(name,change,restore):
 change()
 try:
  exp.verify(root)
 except AssertionError as e:
  rows.append({'test':name,'passed':True,'rejection':str(e)})
 else:raise AssertionError('Guard did not reject '+name)
 finally:restore()
co=me.vertices[0].co.copy()
refused('edited_vertex_rejected',lambda:setattr(me.vertices[0],'co',co+(exp.Vector((.001,0,0)))),lambda:setattr(me.vertices[0],'co',co))
n=me.attributes['EG_ExportNormal'].data[0].vector.copy()
refused('stale_normal_attribute_rejected',lambda:setattr(me.attributes['EG_ExportNormal'].data[0],'vector',n+exp.Vector((.01,0,0))),lambda:setattr(me.attributes['EG_ExportNormal'].data[0],'vector',n))
u=me.uv_layers[0].data[0].uv.copy()
refused('edited_UV_rejected',lambda:setattr(me.uv_layers[0].data[0],'uv',u+exp.Vector((.1,0))),lambda:setattr(me.uv_layers[0].data[0],'uv',u))
o=next(o for o in bpy.data.objects if o.get('instance_id'));loc=o.location.copy()
def move():o.location.x+=.001;bpy.context.view_layer.update()
def unmove():o.location=loc;bpy.context.view_layer.update()
refused('edited_placement_rejected',move,unmove)
(root/'qa/export_guard_regressions.json').write_text(json.dumps({'passed':True,'tests':rows,'input_blend_saved':False},indent=2))
print('GUARD REGRESSIONS PASSED',len(rows),flush=True)
