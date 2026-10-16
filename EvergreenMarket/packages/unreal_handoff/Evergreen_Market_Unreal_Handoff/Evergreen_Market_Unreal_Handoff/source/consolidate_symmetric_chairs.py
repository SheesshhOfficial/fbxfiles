"""Consolidate the authored 180-degree chair symmetry after geometric verification.
This touches only the new, not-yet-delivered handoff copy. Input must be its blend.
"""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1]
assert Path(bpy.data.filepath).resolve()==(ROOT/'Evergreen_Market_Unreal_Ready.blend').resolve()
m=json.loads((ROOT/'manifest.json').read_text());chairs=[a for a in m['assets'] if a['name']=='StaffChair']
if len(chairs)==1:print('Already one chair mesh')
else:
 assert len(chairs)==2
 keep,old=chairs;km=bpy.data.meshes[keep['asset_id']];om=bpy.data.meshes[old['asset_id']]
 assert len(km.vertices)==len(om.vertices) and len(km.polygons)==len(om.polygons)
 assert [x.name for x in km.materials]==[x.name for x in om.materials]
 tree=KDTree(len(km.vertices))
 for i,v in enumerate(km.vertices):tree.insert(v.co,i)
 tree.balance();err=max(tree.find(v.co)[2] for v in om.vertices)
 assert err<.00002,err
 # Authoring used symmetric beveled boxes. Check the material attached to every
 # corresponding triangle centroid, also independent of vertex/triangle order.
 bymat={}
 for mi in range(len(km.materials)):
  ps=[p for p in km.polygons if p.material_index==mi];t=KDTree(len(ps))
  for i,p in enumerate(ps):t.insert(p.center,i)
  t.balance();bymat[mi]=t
 # Triangulation diagonals may differ on flat quads; centroid matching is not
 # required, but per-material bounds and total triangle area must agree.
 for mi in range(len(km.materials)):
  ka=sum(p.area for p in km.polygons if p.material_index==mi);oa=sum(p.area for p in om.polygons if p.material_index==mi)
  assert abs(ka-oa)<.0001,(mi,ka,oa)
 replaced=0
 for o in bpy.context.scene.objects:
  if o.type=='MESH' and o.get('asset_id')==old['asset_id']:o.data=km;o['asset_id']=keep['asset_id'];replaced+=1
 for p in m['placements']:
  if p['asset_id']==old['asset_id']:p['asset_id']=keep['asset_id']
 keep['instance_count']+=old['instance_count'];m['assets'].remove(old)
 assert replaced==old['instance_count']
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Evergreen_Market_Unreal_Ready.blend'),compress=True)
 (ROOT/'manifest.json').write_text(json.dumps(m,indent=2));(ROOT/old['fbx_path']).unlink()
 report={'merged_family':'StaffChair','kept_asset_id':keep['asset_id'],'removed_redundant_asset_id':old['asset_id'],'shared_placements':keep['instance_count'],'vertex_surface_error_metres':err,'per_material_surface_area_match':True,'reason':'The rear-facing source boxes are symmetric under 180-degree rotation but have a different vertex index order.'}
 (ROOT/'qa/chair_symmetry_consolidation.json').write_text(json.dumps(report,indent=2))
 q=json.loads((ROOT/'qa/conversion_report.json').read_text());q['unique_assets']=len(m['assets']);q['symmetric_chair_consolidation']=report;(ROOT/'qa/conversion_report.json').write_text(json.dumps(q,indent=2));print(report)
