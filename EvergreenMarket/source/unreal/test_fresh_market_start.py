import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fresh_market_start as fw

class Tests(unittest.TestCase):
    def test_stage_order_and_visual_gate(self):
        state={'completed':[],'reports':{},'merged_package':'/merged','status':'ready'}
        with patch.object(fw,'load_state',return_value=(Path('/state'),state,{})):
            with self.assertRaises(ValueError):fw.step('/state',stage='pilot')
            state['completed']=['sample'];state['reports']['sample']='sample'
            with patch.object(fw,'_read',return_value={}),patch.object(fw,'_check_report'):
                with self.assertRaises(ValueError):fw.step('/state',stage='full',visual_review_approved=False)

    def test_sample_union_no_automatic_execute(self):
        names=sorted(fw.SAMPLE_NAMES);c={'assets':{str(i):{'name':n} for i,n in enumerate(names)}}
        c['assets']['required']={'name':'required'}
        state={'completed':[],'reports':{},'merged_package':'/merged'}
        with patch.object(fw,'load_state',return_value=(Path('/state'),state,c)),patch.object(fw.em,'select_sample',return_value=['required']),patch.object(fw.em,'run',return_value='dry') as run:
            self.assertEqual(fw.step('/state',stage='sample'),'dry')
            self.assertFalse(run.call_args.kwargs['execute'])
            self.assertEqual(set(run.call_args.kwargs['sample_asset_ids']),set(c['assets']))

    def test_success_checkpoint_exact_returned_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=root/'returned_report.json';report.write_text('{}');statepath=root/'run_state.json'
            state={'completed':['sample','full'],'reports':{'sample':'s','full':'f'},'merged_package':'/merged','status':'ready'}
            with patch.object(fw,'load_state',return_value=(statepath,state,{})),patch.object(fw,'_read',return_value={}),patch.object(fw,'_check_report'),patch.object(fw,'_editor_preflight'),patch.object(fw.ec,'run',return_value=str(report)):
                fw.step(statepath,stage='collision',execute=True,backup_confirmed=True)
            saved=json.loads(statepath.read_text());self.assertEqual(saved['completed'],['sample','full','collision'])
            self.assertEqual(saved['reports']['collision'],str(report));self.assertEqual(saved['status'],'ready')

    def test_failure_stops_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run_state.json';state={'completed':['sample','full'],'reports':{'sample':'s','full':'f'},'merged_package':'/merged'}
            with patch.object(fw,'load_state',return_value=(path,state,{})),patch.object(fw,'_read',return_value={}),patch.object(fw,'_check_report'),patch.object(fw,'_editor_preflight'),patch.object(fw.ec,'run',side_effect=RuntimeError('first failure')):
                with self.assertRaises(RuntimeError):fw.step(path,stage='collision',execute=True,backup_confirmed=True)
            saved=json.loads(path.read_text());self.assertEqual(saved['status'],'stage_failed');self.assertNotIn('collision',saved['reports'])

    def test_finish_completed_is_read_only(self):
        state={'completed':list(fw.STAGES),'reports':{s:s for s in fw.STAGES}}
        with patch.object(fw,'load_state',return_value=(Path('/state'),state,{})),patch.object(fw,'_read',return_value={}),patch.object(fw,'_check_report'),patch.object(fw,'step') as step:
            result=fw.finish('/state',execute=True)
            self.assertEqual(result['remaining_stages'],[]);step.assert_not_called()

    def test_finish_requires_review_before_full(self):
        state={'completed':['sample'],'reports':{'sample':'s'}}
        with patch.object(fw,'load_state',return_value=(Path('/state'),state,{})),patch.object(fw,'_read',return_value={}),patch.object(fw,'_check_report'),patch.object(fw,'step') as step:
            with self.assertRaises(ValueError):fw.finish('/state',execute=True,backup_confirmed=True)
            step.assert_not_called()

    def test_optional_completed_report_is_read_only(self):
        state={'completed':list(fw.STAGES),'reports':{s:s for s in fw.STAGES},'optional_reports':{'pilot_preview':'preview'}}
        receipt={'schema':'evergreen-preview-v1','status':'verified_preview_persistence','mode':'pilot'}
        with patch.object(fw,'load_state',return_value=(Path('/state'),state,{})),patch.object(fw,'_read',return_value=receipt),patch.object(fw,'_check_report'),patch.object(fw,'_write') as write:
            self.assertEqual(fw.preview('/state',execute=True),'preview')
            write.assert_not_called()

    def test_running_state_refuses_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'state.json';p.write_text(json.dumps({'schema':fw.SCHEMA,'state_file':str(p),'status':'running'}))
            with self.assertRaises(ValueError):fw.load_state(p)

if __name__=='__main__':unittest.main()
