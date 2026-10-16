import copy
import json
from pathlib import Path
import tempfile
import types
import sys
import unittest
from unittest.mock import patch
import recover_fresh_lighting as r

class Tests(unittest.TestCase):
    def failure(self):return {'schema':'evergreen-preview-v1','status':'failed_partial_preview','mode':'sample',
                              'error':'Preview transform changed','source_map':'/Sample','target_map':'/Sample','package_fingerprint':'fp'}
    def test_exact_failure_only(self):
        d=self.failure();r.validate_failure(d,'/Sample','fp')
        for key,value in [('error','Other error'),('mode','pilot'),('source_map','/Other'),('package_fingerprint','wrong')]:
            bad=dict(d);bad[key]=value
            with self.assertRaises(ValueError):r.validate_failure(bad,'/Sample','fp')

    def test_unique_discovery_not_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/'a';a.mkdir();p=a/'preview_report.json';p.write_text(json.dumps(self.failure()))
            self.assertEqual(r.discover_failure(root,'/Sample','fp'),str(p))
            b=root/'b';b.mkdir();(b/'preview_report.json').write_text(json.dumps(self.failure()))
            with self.assertRaises(ValueError):r.discover_failure(root,'/Sample','fp')

    def test_state_migration_changes_only_allowed_fields(self):
        state={'status':'stage_failed','active_stage':'sample_lighting','error':'Preview transform changed',
               'helper_hashes':{'fresh_preview_setup.py':'old','other.py':'unchanged'},'completed':['sample'],
               'reports':{'sample':'source_report'},'merged_fingerprint':'fp'}
        original=copy.deepcopy(state);new=r.ready_state(state,'success_report','new')
        self.assertEqual(state,original);self.assertEqual(new['status'],'ready')
        self.assertIsNone(new['active_stage']);self.assertNotIn('error',new)
        self.assertEqual(new['helper_hashes']['other.py'],'unchanged')
        for field in ('completed','reports','merged_fingerprint'):self.assertEqual(new[field],state[field])
        self.assertEqual(new['helper_hashes']['fresh_preview_setup.py'],'new')

    def test_state_rejects_other_stage_before_reading_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run_state.json';p.write_text(json.dumps({'schema':r.fw.SCHEMA,'status':'stage_failed','active_stage':'full','completed':['sample']}))
            with patch.object(r.em,'load_contract') as load:
                with self.assertRaises(ValueError):r.validate_state(p)
                load.assert_not_called()

    def migration_fixture(self,root):
        source=root/'CorrectedPackage'/'source';source.mkdir(parents=True)
        old=source/'fresh_preview_setup.py';old.write_text('old helper bytes')
        new=root/'approved.py';new.write_text('approved helper bytes')
        failed=root/'failed.json';failed.write_text(json.dumps(self.failure()))
        state={'schema':r.fw.SCHEMA,'status':'stage_failed','active_stage':'sample_lighting','error':'Preview transform changed',
               'completed':['sample'],'reports':{'sample':'sample_report'},'merged_package':str(source.parent),
               'helper_hashes':{'fresh_preview_setup.py':r.em._sha(old),'other.py':'unchanged'}}
        path=root/'run_state.json';path.write_text(json.dumps(state));before=path.read_bytes()
        level=types.SimpleNamespace(get_current_level=lambda:types.SimpleNamespace(get_path_name=lambda:'/Sample.Sample:PersistentLevel'),is_in_play_in_editor=lambda:False)
        u=types.SimpleNamespace(LevelEditorSubsystem=object,get_editor_subsystem=lambda cls:level,
                               EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_map_packages=lambda:[],get_dirty_content_packages=lambda:[]),
                               log=lambda value:None,log_error=lambda value:None)
        return source,old,new,failed,state,path,before,u

    def test_mock_successful_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,old,new,failed,state,path,before,u=self.migration_fixture(root)
            success=root/'success.json'
            def recover(*args,**kwargs):
                if not kwargs.get('execute'):return {'diagnostic':'Sun scale only'}
                receipt={'schema':'evergreen-preview-v1','status':'verified_preview_persistence','mode':'sample',
                         'source_map':'/Sample','target_map':'/Sample','package_fingerprint':'fp','transform_only_recovery':True,
                         'recovery_scope':'Sun factory scale 2.5 to 1 only','preserved_non_preview_actor_state':True,
                         'recovery_from':str(failed),'failed_report_sha256':r.em._sha(failed)}
                success.write_text(json.dumps(receipt));return str(success)
            helper=types.SimpleNamespace(recover_sample=recover)
            with patch.dict(sys.modules,{'unreal':u}),patch.object(r,'validate_state',return_value=(path,state,{'fingerprint':'fp'},{'map_path':'/Sample'})),patch.object(r,'approved_helper',return_value=(helper,new)),patch.object(r,'OLD_PREVIEW_SHA',r.em._sha(old)),patch.object(r,'NEW_PREVIEW_SHA',r.em._sha(new)):
                self.assertEqual(r.run(path,failed_preview_report=failed,execute=True,backup_confirmed=True),str(success))
            current=json.loads(path.read_text());self.assertEqual(current['status'],'ready')
            self.assertEqual(old.read_bytes(),new.read_bytes())
            self.assertEqual(current['helper_hashes']['other.py'],'unchanged')
            backups=list(root.glob('LightingRecovery_*'));self.assertEqual(len(backups),1)
            self.assertEqual((backups[0]/'run_state.before.json').read_bytes(),before)
            self.assertEqual(json.loads((backups[0]/'migration_report.json').read_text())['status'],'verified_migration')

    def test_mock_helper_failure_preserves_old_state_and_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,old,new,failed,state,path,before,u=self.migration_fixture(root)
            old_bytes=old.read_bytes()
            def recover(*args,**kwargs):
                if kwargs.get('execute'):raise RuntimeError('Unreal reload failed')
                return {'diagnostic':'Sun scale only'}
            helper=types.SimpleNamespace(recover_sample=recover)
            with patch.dict(sys.modules,{'unreal':u}),patch.object(r,'validate_state',return_value=(path,state,{'fingerprint':'fp'},{'map_path':'/Sample'})),patch.object(r,'approved_helper',return_value=(helper,new)),patch.object(r,'OLD_PREVIEW_SHA',r.em._sha(old)),patch.object(r,'NEW_PREVIEW_SHA',r.em._sha(new)):
                with self.assertRaises(RuntimeError):r.run(path,failed_preview_report=failed,execute=True,backup_confirmed=True)
            self.assertEqual(path.read_bytes(),before);self.assertEqual(old.read_bytes(),old_bytes)
            self.assertEqual(json.loads(next(root.glob('LightingRecovery_*/migration_report.json')).read_text())['status'],'failed_requires_inspection')

    def test_unapproved_helper_never_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'helper.py';p.write_text("raise RuntimeError('must never execute')")
            with self.assertRaises(ValueError):r.approved_helper(p)

if __name__=='__main__':unittest.main()
