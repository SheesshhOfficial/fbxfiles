"""Data and rebuilding-adapter tests only; not an Unreal runtime simulation."""
import copy
import os
import unittest
import setup_prop_actor_pilot as pilot

class FakeISM:
    def __init__(self, indices=None): self.indices=indices;self.calls=[];self.count=0
    def clear_instances(self): self.calls.append('clear');self.count=0
    def add_instances(self, transforms, **kwargs):
        self.calls.append(('add',transforms,kwargs));self.count=len(transforms)
        return list(range(self.count)) if self.indices is None else self.indices

class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=pilot.em.load_contract(os.environ.get('EVERGREEN_PACKAGE','supermarket_unreal_handoff'))
        raw=pilot.em.make_plan(cls.contract,phase='full')
        cls.full=dict(raw,schema=pilot.em.SCHEMA,status='verified_persistence',
                      map_path='/Game/EvergreenHandoff/Full_test/Maps/L_Evergreen_full')
        cls.full['groups']={k:{'instances':[dict(p,instance_index=i) for i,p in enumerate(v)],'mesh_path':'/Game/Fake.'+v[0]['asset_id']}
                            for k,v in raw['groups'].items()}
        cls.collision={'status':'verified_collision_persistence','source_map':cls.full['map_path'],
                       'target_map':cls.full['map_path']+'_WalkTest_test','box_count':568}
    def plan(self): return pilot.make_plan(self.contract,self.full,self.collision)
    def test_exact_four_and_conservation(self):
        p=self.plan();self.assertEqual(len(p['promoted']),4)
        remaining=[r['instance_id'] for g in p['remaining_scene']['groups'].values() for r in g['instances']]
        chosen=[r['instance_id'] for r in p['promoted']]
        self.assertFalse(set(remaining)&set(chosen));self.assertEqual(len(remaining),11312)
        self.assertEqual(set(remaining+chosen),{r['instance_id'] for r in self.contract['placements']})
    def test_original_report_unchanged(self):
        before=copy.deepcopy(self.full);self.plan();self.assertEqual(before,self.full)
    def test_canonical_scale_and_front_walkway(self):
        p=self.plan()
        for row in p['promoted']:
            t=row['target_placement'];self.assertEqual(t['scale'],[1,1,1]);self.assertEqual(t['location_cm'][1:],[2100,0])
            self.assertTrue(-2400<t['location_cm'][0]<2400)
        self.assertEqual(p['collision_plan']['box_count'],568)
    def test_no_unchanged_group_rebuild(self):
        p=self.plan()
        for key,g in self.full['groups'].items():
            if key not in p['changed_groups']:self.assertEqual(g,p['remaining_scene']['groups'][key])
    def test_failed_collision_rejected(self):
        c=dict(self.collision,status='failed_partial_copy')
        with self.assertRaisesRegex(ValueError,'Successful'):pilot.make_plan(self.contract,self.full,c)
    def test_wrong_source_map_rejected(self):
        c=dict(self.collision,source_map='/Game/Other')
        with self.assertRaisesRegex(ValueError,'different maps'):pilot.make_plan(self.contract,self.full,c)
    def test_wrong_collision_policy_rejected(self):
        c=dict(self.collision,box_count=2)
        with self.assertRaisesRegex(ValueError,'count mismatch'):pilot.make_plan(self.contract,self.full,c)
    def test_returned_indices_not_guessed(self):
        c=FakeISM([2,0,1]);rows=[{'instance_id':str(i)} for i in range(3)]
        pilot.apply_rebuild(c,rows,lambda r:r['instance_id'])
        self.assertEqual([r['instance_index'] for r in rows],[2,0,1]);self.assertEqual(c.calls[0],'clear')
        self.assertEqual(c.calls[1][2],dict(should_return_indices=True,world_space=True,update_navigation=False))
    def test_duplicate_indices_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):pilot.apply_rebuild(FakeISM([0,0]),[{},{}],lambda r:0)
    def test_bad_index_rejected(self):
        with self.assertRaisesRegex(ValueError,'Invalid'):pilot.apply_rebuild(FakeISM([4]),[{}],lambda r:0)
    def test_empty_group_retained(self):
        c=FakeISM();pilot.apply_rebuild(c,[],lambda r:0);self.assertEqual(c.calls,['clear'])
    def test_sample_report_rejected(self):
        f=dict(self.full,phase='sample')
        with self.assertRaisesRegex(ValueError,'FULL'):pilot.make_plan(self.contract,f,self.collision)

if __name__=='__main__':unittest.main()
