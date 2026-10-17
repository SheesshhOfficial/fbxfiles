"""Pure Python mocked control-flow checks; not Unreal integration/runtime tests."""
import importlib.util,sys,types,tempfile,json
from pathlib import Path
from unittest.mock import MagicMock
ROOT=Path(__file__).resolve().parents[1]
class Mesh:
 def __init__(self):self.assigned=[]
 def get_editor_property(self,key):return [None,None]
 def set_material(self,index,mat):self.assigned.append((index,mat))
class Material:pass
results=[]

def run_case(prepared=True,wrong_hash=False,partial=False):
 mesh=Mesh();mats={'M_Glass':Material(),'M_Wood':Material()};tasks=[]
 ue=types.ModuleType('unreal');ue.StaticMesh=Mesh;ue.MaterialInterface=Material
 for n in ['EditorActorSubsystem','StaticMeshActor','CollisionEnabled','CollisionResponse','CollisionChannel','FBXImportType','FBXNormalImportMethod','FBXNormalGenerationMethod','Name','Vector','Rotator','EditorAssetLibrary']:setattr(ue,n,MagicMock())
 ue.EditorAssetLibrary.does_asset_exist.return_value=False
 actors=MagicMock();actors.get_all_level_actors.return_value=[];ue.get_editor_subsystem=lambda _:actors
 ue.AssetImportTask=lambda:types.SimpleNamespace()
 ue.FbxImportUI=lambda:types.SimpleNamespace(static_mesh_import_data=MagicMock())
 assettools=types.SimpleNamespace(import_asset_tasks=lambda ts:tasks.extend(ts))
 ue.AssetToolsHelpers=types.SimpleNamespace(get_asset_tools=lambda:assettools)
 def load(path):
  key=path.rsplit('/',1)[-1]
  if key=='SM_Test':return mesh
  if partial and key=='M_Wood':return None
  return mats.get(key)
 ue.load_asset=load;sys.modules['unreal']=ue
 spec=importlib.util.spec_from_file_location('prop_import_test',ROOT/'unreal/import_props.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)
  (root/'prop_placements.json').write_text(json.dumps({'source_blend_sha256':'same','assets':[{'asset_name':'SM_Test','fbx':'props/test.fbx','materials':['glass','wood']}],'placements':[{'asset_name':'SM_Test','source_object':'TestProp','location_cm':[1,2,3]}]}))
  if prepared:(root/'material_manifest.json').write_text(json.dumps({'source_sha256':'different' if wrong_hash else 'same','materials':[{'source_name':'glass','asset_name':'M_Glass'},{'source_name':'wood','asset_name':'M_Wood'}]}))
  try:mod.import_props(str(root))
  except RuntimeError:
   assert wrong_hash or partial
   assert not tasks
   return 'blocked before import'
  assert not wrong_hash and not partial
  assert tasks[0].options.import_materials is (not prepared)
  assert tasks[0].options.import_textures is (not prepared)
  assert mesh.assigned==([(0,mats['M_Glass']),(1,mats['M_Wood'])] if prepared else [])
  assert actors.spawn_actor_from_class.call_count==1
  return 'passed'
for name,kwargs in [('prepared materials',{}),('checkpoint fallback',{'prepared':False}),('source hash mismatch',{'wrong_hash':True}),('partial material import',{'partial':True})]:results.append({'case':name,'result':run_case(**kwargs)})
report={'test_type':'Mocked Python control flow only','unreal_executed':False,'tests':results}
(ROOT/'qa/prop_material_import_mock_tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
