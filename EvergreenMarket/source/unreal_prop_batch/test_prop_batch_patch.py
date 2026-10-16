"""Offline tests; fake UE adapter checks are not engine/PIE verification."""
import copy,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'evergreen_source_v2/source/unreal'))
import prop_batch_patch as b
import fixture_support as f
import test_prop_actor_pilot as pilot_tests
import setup_prop_actor_pilot as ep

class T:
 def __init__(self,n):self.n=n
 def is_near_equal(self,other,**kwargs):return self.n==other.n
class ISM:
 def __init__(self,values,swap=False,fail=False):self.values=list(values);self.swap=swap;self.removed=[];self.fail=fail
 def modify(self):pass
 def get_instance_count(self):return len(self.values)
 def get_instance_transform(self,i,**kwargs):return T(self.values[i])
 def remove_instance(self,i):
  self.removed.append(i)
  if self.fail:return False
  if self.swap:self.values[i]=self.values[-1];self.values.pop()
  else:self.values.pop(i)
  return True
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  pilot_tests.PilotTests.setUpClass();p=pilot_tests.PilotTests();cls.ctx=dict(contract=p.contract,pilot=p.plan());cls.sel=f.read(HERE/'prop_batch_selection_v1.json')
 def test_exact_source_and_counts(self):
  p=b.make_plan(self.ctx,self.sel,f);self.assertEqual(len(p['promoted']),16)
  for row in p['promoted']:self.assertEqual(row['target_placement'],row['source_placement'])
  self.assertEqual(len({r['instance_id'] for r in p['promoted']}),16)
 def test_reject_manifest_and_duplicate(self):
  s=copy.deepcopy(self.sel);s['source_manifest_sha256']='bad'
  with self.assertRaisesRegex(ValueError,'hash mismatch'):b.make_plan(self.ctx,s,f)
  s=copy.deepcopy(self.sel);s['selected'][1]=s['selected'][0]
  with self.assertRaisesRegex(ValueError,'unique'):b.make_plan(self.ctx,s,f)
 def test_no_pilot_reuse(self):
  s=copy.deepcopy(self.sel);s['selected'][0]['instance_id']=self.ctx['pilot']['promoted'][0]['instance_id']
  with self.assertRaisesRegex(ValueError,'audited'):b.make_plan(self.ctx,s,f)
 def test_descending_multiple_same_group_shift_and_swap(self):
  for swap in (False,True):
   rows=[dict(instance_id=str(i),instance_index=i) for i in range(9)];c=ISM(range(9),swap)
   out,removed=b.remove_selected(c,rows,{'1','4','6'},lambda p:T(int(p['instance_id'])))
   self.assertEqual(removed,[6,4,1]);self.assertEqual(c.removed,[6,4,1]);self.assertEqual({r['instance_id'] for r in out},{'0','2','3','5','7','8'})
   for row in out:self.assertEqual(c.values[row['instance_index']],int(row['instance_id']))
 def test_failed_remove_and_ambiguous_mapping(self):
  rows=[dict(instance_id=str(i),instance_index=i) for i in range(3)]
  with self.assertRaisesRegex(ValueError,'remove failed'):b.remove_selected(ISM(range(3),fail=True),rows,{'1'},lambda p:T(int(p['instance_id'])))
  with self.assertRaisesRegex(ValueError,'Ambiguous'):b.remap_survivors(ISM([0,0]),rows[:2],lambda p:T(0))
 def test_edited_selection_transform_rejected(self):
  s=copy.deepcopy(self.sel);s['selected'][0]['target_placement']['scale']=[2,2,2]
  with self.assertRaisesRegex(ValueError,'exact original'):b.make_plan(self.ctx,s,f)
 def test_dirty_editor_and_pie_rejected(self):
  for pie,dirty_map,dirty_asset in ((True,False,False),(False,True,False),(False,False,True)):
   u=types.SimpleNamespace(LevelEditorSubsystem=object(),get_editor_subsystem=lambda cls:types.SimpleNamespace(is_in_play_in_editor=lambda:pie),EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_map_packages=lambda:dirty_map,get_dirty_content_packages=lambda:dirty_asset))
   with self.assertRaises(ValueError):f.clean(u)
 def test_short_target_and_remap(self):
  target=b.target_map('20261016_210000_1234abcd');self.assertLess(len(target),120);self.assertLess(len('G:/Games/SheeshhPropHuntYT/Content/'+target[6:]+'.umap'),180)
  import fresh_preview_setup as fp
  old=b.SOURCE+'.'+b.SOURCE.rsplit('/',1)[-1]+':PersistentLevel.Pilot_0'
  p=dict(source_map=b.SOURCE,pilot_plan=dict(remaining_scene={},promoted=[dict(actor_path=old)]))
  result=fp._copy_pilot_plan(p,target);self.assertEqual(result['pilot_plan']['promoted'][0]['actor_path'],target+'.'+target.rsplit('/',1)[-1]+':PersistentLevel.Pilot_0')
 def test_bootstrap_plain_exec(self):
  mod=types.SimpleNamespace(run=MagicMock(return_value={}));spec=types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m:None))
  with patch('importlib.util.spec_from_file_location',return_value=spec),patch('importlib.util.module_from_spec',return_value=mod):
   ns={};exec((HERE/'Start_Prop_Batch.py').read_text(),ns)
  self.assertNotIn('__file__',ns);self.assertEqual(mod.run.call_count,1);self.assertEqual(mod.run.call_args.kwargs,{})
 def test_fixture_report_reject_partial_wrong_map_hash(self):
  ctx=dict(source_map='preview',hashes={'state':'digest'})
  report=dict(schema='evergreen-fixture-patch-v1',status='failed_partial_fixture_patch')
  fake=types.SimpleNamespace(verified_context=lambda p:copy.deepcopy(ctx),read=lambda p:report)
  with self.assertRaisesRegex(ValueError,'successful'):b.context(fake,'state','report')
  report.update(status='verified_fixture_lights_persistence',source_map='preview',target_map='wrong')
  with self.assertRaisesRegex(ValueError,'source/target'):b.context(fake,'state','report')
  report.update(target_map=b.SOURCE,point_light_count=42,lights=[{}]*42,preserved_actor_state=True,protected_hashes={'state':'bad'})
  with self.assertRaisesRegex(ValueError,'provenance'):b.context(fake,'state','report')
 def test_spawn_replaces_pilot_identity(self):
  actor=MagicMock();p={'label':'Batch_X','instance_id':'X','mesh_path':'/Game/M'};u=types.SimpleNamespace(load_asset=lambda x:x)
  ctx={'ep':types.SimpleNamespace(_spawn=MagicMock(return_value=actor))};self.assertIs(b.spawn(u,ctx,p),actor)
  actor.set_actor_label.assert_called_once_with('EM_BATCH_Batch_X');actor.set_editor_property.assert_called_once_with('tags',['Prop',b.TAG,'EMSource=X'])
 def test_orchestration_save_reload_failure_and_backup_guards(self):
  for mode in ('ok','fail_verify','fail_reload','no_backup','dry'):
   with tempfile.TemporaryDirectory() as tmp:
    current=[b.SOURCE];calls=[]
    def create(target,source):current[0]=target;calls.append('copy');return True
    def save():calls.append('save');return True
    def reload(target):current[0]=target;calls.append('reload');return True
    level=types.SimpleNamespace(new_level_from_template=create,save_current_level=save,load_level=reload)
    u=types.SimpleNamespace(InstancedStaticMeshComponent=types.SimpleNamespace(remove_instance=lambda:None),LevelEditorSubsystem=object(),get_editor_subsystem=lambda cls:level,Paths=types.SimpleNamespace(project_content_dir=lambda:tmp,project_saved_dir=lambda:tmp),log=lambda s:None,log_error=lambda s:None)
    pilot=dict(remaining_scene=dict(groups={},placement_count=11312),promoted=[])
    ctx=dict(hashes={},pilot=pilot,contract={},fp=types.SimpleNamespace(_current=lambda u:current[0],_copy_pilot_plan=lambda p,t:p),ep=types.SimpleNamespace(verify=lambda *a:None,_groups=lambda u:{},_write_lookup=lambda *a:None),ec=types.SimpleNamespace(_check_original_collision=lambda *a:None))
    plan=dict(pilot_plan=copy.deepcopy(pilot),changed_groups=[],promoted=[],selected_ids=[])
    fake=types.SimpleNamespace(read=lambda p:{},sha=lambda p:'hash',clean=lambda u:calls.append('clean'),unchanged=lambda h:None,snapshot=lambda *a:{'lights':'saved custom tuning'})
    with patch.object(b,'support',return_value=fake),patch.object(b,'context',return_value=ctx),patch.object(b,'make_plan',return_value=plan),patch.object(b,'batch_actors',return_value=[]),patch.object(b,'fixture_identity'),patch.object(b,'mesh_snapshot',return_value={}),patch.object(b,'verify',side_effect=([{'counts':'checked'},ValueError('persistence mismatch')] if mode=='fail_reload' else ValueError('persistence mismatch') if mode=='fail_verify' else None),return_value={'counts':'checked'}) as verify,patch.dict(sys.modules,unreal=u):
     if mode in ('no_backup','fail_verify','fail_reload'):
      with self.assertRaisesRegex(ValueError,'back up|persistence mismatch'):b.run(tmp,execute=True,backup_confirmed=mode!='no_backup')
     else:b.run(tmp,execute=mode!='dry',backup_confirmed=True)
    reports=list(Path(tmp).glob('EvergreenHandoff/PropBatch_*/prop_batch_report.json'))
    if mode=='ok':
     self.assertEqual(verify.call_count,2);self.assertEqual(calls.count('save'),1);self.assertEqual(calls.count('reload'),1);self.assertEqual(json.loads(reports[0].read_text())['status'],'verified_prop_batch_persistence')
    elif mode in ('fail_verify','fail_reload'):
     self.assertEqual(calls.count('save'),1 if mode=='fail_reload' else 0);self.assertEqual(json.loads(reports[0].read_text())['status'],'failed_partial_prop_batch')
    else:self.assertNotIn('copy',calls);self.assertFalse(reports)
 def test_collision_helpers_are_exact_proven_policy(self):
  from test_pilot_collision_profile import ProfileTests
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProfileTests);result=unittest.TestResult();suite.run(result)
  self.assertTrue(result.wasSuccessful(),str(result.errors)+str(result.failures))

if __name__=='__main__':unittest.main(verbosity=2)
