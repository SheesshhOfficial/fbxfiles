"""Integration of the final native package, pure planners and fresh run snapshot.
Requires complete export. No Unreal runtime used or claimed.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import fresh_market_source_v2 as fw

class NativePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ.get('EVERGREEN_PACKAGE','evergreen_source_v2')).resolve()
        if not (cls.root/'walking_companions.json').is_file():raise unittest.SkipTest('Final native export not ready')
        cls.c,cls.files,cls.fingerprint=fw.validate_source(cls.root)
    def test_complete_contract_and_plans(self):
        c=self.c;collision=fw.ec.make_plan(c)
        self.assertEqual(collision['box_count'],694)
        self.assertEqual(fw.fp.clearance(collision['boxes'])['boxes_tested'],694)
        raw=fw.em.make_plan(c,phase='full')
        full=dict(raw,schema=fw.em.SCHEMA,status='verified_persistence',map_path='/Game/EvergreenHandoff/Full_test/Maps/L_Evergreen_full')
        full['groups']={k:dict(instances=[dict(p,instance_index=i) for i,p in enumerate(v)],mesh_path='/Game/Fake.'+v[0]['asset_id']) for k,v in raw['groups'].items()}
        receipt=dict(status='verified_collision_persistence',source_map=full['map_path'],target_map=full['map_path']+'_WalkTest_test',box_count=collision['box_count'])
        pilot=fw.ep.make_plan(c,full,receipt)
        target=receipt['target_map']+'_PropPilot_test';pilot['remaining_scene']['map_path']=target
        for row in pilot['promoted']:row['actor_path']=target+'.L_Evergreen_full:PersistentLevel.'+row['label']
        pilot_report=dict(schema='evergreen-prop-actor-pilot-v1',status='verified_pilot_persistence',package_fingerprint=c['fingerprint'],source_map=receipt['target_map'],target_map=target,plan=pilot)
        preview=fw.fp._pilot_plan(c,full,receipt,pilot_report)
        self.assertEqual(len(preview['lights']),11);self.assertEqual(len(pilot['promoted']),4)
        self.assertEqual(pilot['remaining_scene']['placement_count'],11312)
    def test_prepare_snapshot_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/'newrun'
            fw.start(self.root,work);self.assertFalse(work.exists())
            state=fw.start(self.root,work,execute=True)
            _,saved,c=fw.load_state(state)
            self.assertEqual(saved['source_fingerprint'],self.fingerprint)
            self.assertEqual(fw.step(state)['next_stage'],'sample')
            with self.assertRaisesRegex(ValueError,'nonexistent'):fw.start(self.root,work,execute=True)
            target=Path(saved['merged_package'])/'neutral_light_layout_v1.json'
            target.write_text(target.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'package changed'):fw.load_state(state)

if __name__=='__main__':unittest.main()
