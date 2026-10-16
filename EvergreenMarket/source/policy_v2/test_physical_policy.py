import unittest,json,tempfile,shutil,importlib.util
from pathlib import Path
from build_policy import ROOT,ec
from expand_physical_policy import run
class PhysicalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.p=run(cls.root)
  cls.m=json.loads((ROOT/'supermarket_unreal_handoff/manifest.json').read_text());cls.assets={a['asset_id']:a for a in cls.m['assets']}
  cls.contract=dict(root=cls.root,assets=cls.assets,placements=cls.m['placements'])
  spec=importlib.util.spec_from_file_location('collision_v2_under_test',ROOT/'source_consolidation_delivery/unreal/setup_market_collision.py');cls.v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.v2)
  cls.plan=cls.v2.make_plan(cls.contract)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_original568_exact(self):self.assertEqual(self.plan['boxes'][:568],ec.make_plan(self.contract)['boxes'])
 def test_totals(self):self.assertEqual(self.plan['box_count'],694);self.assertEqual(len(self.p['additions']),31)
 def test_impulse_world_dimensions(self):
  boxes=[b for b in self.plan['boxes'] if b['name']=='Impulse display'];self.assertEqual(len(boxes),4)
  for b in boxes:
   self.assertEqual([v*2 for v in b['extent']],[62,145,126]);self.assertAlmostEqual(b['center'][2],63)
 def test_lockers_actual_body_not_handle(self):
  boxes=[b for b in self.plan['boxes'] if b['name'].startswith('StaffLocker')];self.assertEqual(len(boxes),6)
  for b in boxes:self.assertAlmostEqual(b['center'][1],-2935);self.assertEqual(b['extent'],[85,50,105])
 def test_bakery_cavities(self):
  boxes=[b for b in self.plan['boxes'] if b['name']=='BakeryWallCabinet'];self.assertEqual(len(boxes),18)
  self.assertEqual(sum(b['extent']==[110,140,52] for b in boxes),3)
  self.assertEqual(sum(b['extent']==[100,132.5,3.5] for b in boxes),9)
  self.assertEqual(sum(b['extent']==[110,3,145] for b in boxes),6)
 def test_no_doors_or_fence_plane(self):
  self.assertFalse(any(b['name'] in ec.EXCLUDED_DOORS for b in self.plan['boxes']))
  for b in self.plan['boxes']:
   if b['name']=='Fence rails':
    self.assertEqual(len(b['placement']['source_names']),1)
    self.assertLess(2*b['extent'][0],3);self.assertLess(2*b['extent'][2],3)
   if b['name']=='SafetyBollard':
    self.assertEqual(len(b['placement']['source_names']),2);self.assertEqual(b['extent'],[10.5,10.5,47.5])
 def test_shared_role_masks(self):
  for name,prefix in [('Promotional feature sign','Promotional island plinth'),('Planter soil','Promotional island timber box')]:
   boxes=[b for b in self.plan['boxes'] if b['name']==name];self.assertEqual(len(boxes),3)
   for b in boxes:self.assertTrue(b['placement']['source_names'][0].startswith(prefix))
 def test_scaled_planters(self):
  boxes=[b for b in self.plan['boxes'] if b['name']=='Entrance planter'];self.assertEqual(len(boxes),2)
  for b in boxes:
   for got,want in zip([2*e*s for e,s in zip(b['extent'],b['placement']['scale'])],[300,110,70]):self.assertAlmostEqual(got,want,3)
 def test_hash_reject(self):
  path=self.root/'collision_policy_v2.json';old=path.read_bytes();path.write_bytes(old+b' ')
  try:
   with self.assertRaisesRegex(ValueError,'hash mismatch'):self.v2.make_plan(self.contract)
  finally:path.write_bytes(old)
if __name__=='__main__':unittest.main()
