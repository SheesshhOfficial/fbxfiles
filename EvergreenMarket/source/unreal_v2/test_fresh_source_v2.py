"""Pure-data/mock orchestration tests. No Unreal runtime validation implied."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fresh_market_source_v2 as fw

class Tests(unittest.TestCase):
    def state(self,root,completed=()):
        reports={};hashes={}
        for stage in completed:
            p=root/(stage+'.json');p.write_text('{}');reports[stage]=str(p);hashes[stage]=fw.em._sha(p)
        return dict(completed=list(completed),reports=reports,report_hashes=hashes,merged_package='/merged',status='ready')
    def test_order_and_visual_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=self.state(root,['sample','sample_lighting'])
            with patch.object(fw,'load_state',return_value=(root/'state',s,{})),patch.object(fw,'_check_report'):
                with self.assertRaisesRegex(ValueError,'Next permitted'):fw.step('x',stage='pilot')
                with self.assertRaisesRegex(ValueError,'Inspect'):fw.step('x',stage='full')
    def test_lighting_required_before_full(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=self.state(root,['sample'])
            with patch.object(fw,'load_state',return_value=(root/'state',s,{})),patch.object(fw,'_check_report'),patch.object(fw.fp,'light_sample',return_value='dry') as run:
                with self.assertRaisesRegex(ValueError,'sample_lighting'):fw.step('x',stage='full',visual_review_approved=True)
                self.assertEqual(fw.step('x',stage='sample_lighting'),'dry')
                self.assertFalse(run.call_args.kwargs['execute'])
                with self.assertRaisesRegex(ValueError,'sample_lighting'):fw.finish('x',execute=True,backup_confirmed=True,visual_review_approved=True)
    def test_actual_native_light_metadata(self):
        root=Path(__file__).resolve().parents[2]/'evergreen_source_v2'
        if not (root/'neutral_light_layout_v1.json').is_file():self.skipTest('Native layout fixture missing')
        lights=fw.fp._lights({'root':root})
        self.assertEqual(len(lights),11)
        self.assertEqual(sum(x['actor']=='DirectionalLight' for x in lights),1)
        self.assertEqual(sum(x['actor']=='PointLight' for x in lights),10)
    def test_dry_sample_union(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);c={'assets':{str(i):{'name':n} for i,n in enumerate(fw.SAMPLE_NAMES)}}
            with patch.object(fw,'load_state',return_value=(root/'state',self.state(root),c)),patch.object(fw.em,'select_sample',return_value=[]),patch.object(fw.em,'run',return_value='dry') as run:
                self.assertEqual(fw.step('x',stage='sample'),'dry');self.assertFalse(run.call_args.kwargs['execute'])
                self.assertEqual(set(run.call_args.kwargs['sample_asset_ids']),set(c['assets']))
    def test_lighting_final_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=self.state(root,fw.STAGES[:-1]);report=root/'lighting.json';report.write_text('{}');path=root/'state.json'
            with patch.object(fw,'load_state',return_value=(path,s,{})),patch.object(fw,'_check_report'),patch.object(fw,'_editor_preflight'),patch.object(fw.fp,'run',return_value=str(report)):
                fw.step(path,stage='lighting',execute=True,backup_confirmed=True)
            saved=json.loads(path.read_text());self.assertEqual(saved['completed'],list(fw.STAGES));self.assertEqual(saved['status'],'complete')
            self.assertEqual(saved['report_hashes']['lighting'],fw.em._sha(report))
    def test_report_tamper_stops_before_call(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=self.state(root,['sample','sample_lighting']);Path(s['reports']['sample']).write_text('{"changed":true}')
            with patch.object(fw,'load_state',return_value=(root/'state',s,{})),patch.object(fw.em,'run') as run:
                with self.assertRaisesRegex(ValueError,'report changed'):fw.step('x',stage='full',visual_review_approved=True)
                run.assert_not_called()
    def test_failure_is_terminal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=self.state(root,['sample','sample_lighting','full']);p=root/'state.json'
            with patch.object(fw,'load_state',return_value=(p,s,{})),patch.object(fw,'_check_report'),patch.object(fw,'_editor_preflight'),patch.object(fw.ec,'run',side_effect=RuntimeError('first error')):
                with self.assertRaisesRegex(RuntimeError,'first error'):fw.step(p,stage='collision',execute=True,backup_confirmed=True)
            self.assertEqual(json.loads(p.read_text())['status'],'stage_failed')
    def test_running_state_refuses_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';p.write_text(json.dumps(dict(schema=fw.SCHEMA,state_file=str(p),status='running')))
            with self.assertRaisesRegex(ValueError,'incomplete'):fw.load_state(p)
    def test_backup_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=self.state(root,['sample','sample_lighting','full'])
            with patch.object(fw,'load_state',return_value=(root/'state',s,{})),patch.object(fw,'_check_report'),patch.object(fw.ec,'run') as run:
                with self.assertRaisesRegex(ValueError,'backup'):fw.step('x',stage='collision',execute=True)
                run.assert_not_called()

if __name__=='__main__':unittest.main()
