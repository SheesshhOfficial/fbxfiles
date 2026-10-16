"""Local data/regression tests; not a simulation of Unreal execution."""
import copy
import json
import math
from pathlib import Path
import unittest
from unittest import mock
import setup_market_collision as collision

class CollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set EVERGREEN_PACKAGE when running from another checkout.
        import os
        root = Path(os.environ.get('EVERGREEN_PACKAGE', 'supermarket_unreal_handoff'))
        cls.contract = collision.em.load_contract(root)
        cls.plan = collision.make_plan(cls.contract)
        planned = collision.em.make_plan(cls.contract, phase='full')
        cls.report = dict(planned, schema=collision.em.SCHEMA, status='verified_persistence',
                         map_path='/Game/EvergreenHandoff/Full_test/Maps/L_Evergreen_full')
        cls.report['groups'] = {k: {'instances': v} for k,v in planned['groups'].items()}

    def test_actual_package_count(self):
        self.assertEqual(self.plan['box_count'], 568)
        self.assertEqual(self.plan['by_name']['Sales floor'], 1)
        self.assertEqual(self.plan['by_name']['Service floor'], 1)

    def test_compound_and_small_props_excluded(self):
        names = set(self.plan['by_name'])
        self.assertTrue(names.isdisjoint(collision.EXCLUDED_DOORS))
        self.assertTrue(names.isdisjoint({'ShoppingCart','ShoppingBasket','StaffChair'}))
        self.assertFalse(any(n.startswith('SKU_') for n in names))
        self.assertFalse(any('Fence' in n for n in names))

    def test_compound_boxes_are_granular(self):
        self.assertEqual(self.plan['by_name']['StaffTable'], 5)
        self.assertEqual(self.plan['by_name']['ProduceIsland'], 30)
        self.assertEqual(self.plan['by_name']['BakeryIsland'], 2)
        self.assertEqual(self.plan['by_name']['StaffKitchenette'], 2)
        table = [b for b in self.plan['boxes'] if b['name']=='StaffTable']
        self.assertEqual(sorted(b['extent'][2] for b in table), [6,39,39,39,39])

    def test_bottom_pivot_center(self):
        p = {'location_cm':[10,20,30], 'scale':[1,1,2], 'quaternion_xyzw':[0,0,0,1]}
        self.assertEqual(collision.world_center(p, 20), [10,20,50])

    def test_rotated_center(self):
        s = math.sqrt(0.5)
        p = {'location_cm':[10,20,30], 'scale':[1,1,2], 'quaternion_xyzw':[0,s,0,s]}
        for actual, expected in zip(collision.world_center(p,20),[30,20,30]):
            self.assertAlmostEqual(actual,expected)

    def test_full_report_valid(self):
        collision.validate_report(self.contract,self.report)

    def test_sample_rejected(self):
        r=copy.deepcopy(self.report);r['phase']='sample'
        with self.assertRaisesRegex(ValueError,'FULL'): collision.validate_report(self.contract,r)

    def test_failed_rejected(self):
        r=copy.deepcopy(self.report);r['status']='failed_partial_run'
        with self.assertRaisesRegex(ValueError,'FULL'): collision.validate_report(self.contract,r)

    def test_wrong_package_rejected(self):
        r=copy.deepcopy(self.report);r['package_fingerprint']='wrong'
        with self.assertRaisesRegex(ValueError,'differs'): collision.validate_report(self.contract,r)

    def test_unrelated_map_rejected(self):
        r=copy.deepcopy(self.report);r['map_path']='/Game/MainMap'
        with self.assertRaisesRegex(ValueError,'original generated'): collision.validate_report(self.contract,r)

    def test_missing_placement_rejected(self):
        r=copy.deepcopy(self.report);next(iter(r['groups'].values()))['instances'].pop()
        with self.assertRaisesRegex(ValueError,'coverage'): collision.validate_report(self.contract,r)

    def test_door_clearances(self):
        # Structural OBB point tests at walking height, at centers and 42cm sides.
        # Not a capsule sweep or runtime movement test.
        points=[(-1400,-1800,100),(300,-1800,100),(1500,-1800,100),
                (800,-2400,100),(2200,-800,100),(2200,-2500,100),(0,2400,100)]
        for point in points:
            for dx,dy in ((0,0),(42,0),(-42,0),(0,42),(0,-42)):
                v=[point[0]+dx,point[1]+dy,point[2]]
                for b in self.plan['boxes']:
                    if b['name'] not in collision.STRUCTURE: continue
                    x,y,z,w=b['placement']['quaternion_xyzw']
                    # Transpose rotation transforms world delta into local.
                    R=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
                       (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
                       (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
                    delta=[a-c for a,c in zip(v,b['center'])]
                    local=[sum(R[j][i]*delta[j] for j in range(3))/b['placement']['scale'][i] for i in range(3)]
                    inside=all(abs(a)<e-0.01 for a,e in zip(local,b['extent']))
                    self.assertFalse(inside, (v,b['name']))

    def test_default_dry_run_has_no_unreal_import(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json';path.write_text(json.dumps(self.report))
            with mock.patch.object(collision.em,'load_contract',return_value=self.contract), mock.patch('builtins.print'):
                result=collision.run('unused',path)
            self.assertEqual(result['box_count'],568)

if __name__=='__main__': unittest.main()
