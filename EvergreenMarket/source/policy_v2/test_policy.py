import json,unittest
from pathlib import Path
from build_policy import build,lights,inverse_point,ec
class PolicyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=json.loads((Path(__file__).resolve().parents[1]/'supermarket_unreal_handoff/manifest.json').read_text());cls.p=build(cls.m)
 def test_coverage(self):
  self.assertEqual(self.p['invariants'],dict(asset_count=256,placement_count=11316,legacy_box_assets=111,legacy_none_assets=145,candidate_assets=51,candidate_placements=6695,walking_boxes_reconstructed=568,canonical_blocker_assets=55,canonical_blocker_boxes=66))
 def test_all_have_explicit_reason(self):
  for r in self.p['assets'].values():self.assertTrue(r['reason']);self.assertTrue(r['export_action'])
 def test_separate_bodies(self):
  for r in self.p['assets'].values():
   self.assertEqual(r['runtime']['Pawn'],'Ignore')
   if r['local_boxes_cm']:self.assertTrue(r['export_roles']['walking_companion_body']['enabled'])
 def test_doors_open(self):
  for r in self.p['assets'].values():
   if r['name'] in ec.EXCLUDED_DOORS:self.assertFalse(r['local_boxes_cm']);self.assertEqual(r['runtime']['Pawn'],'Ignore')
 def test_prop_review_not_falsely_validated(self):
  for r in self.p['assets'].values():
   if r['category']=='disguise_candidate':self.assertFalse(r['shape_tightness_verified'])
 def test_inverse_scaled_rotated(self):
  p=dict(location_cm=[1,2,3],scale=[2,3,4],quaternion_xyzw=[0,0,2**-.5,2**-.5]);v=[6,-7,8]
  for a,b in zip(v,inverse_point(p,ec.world_offset(p,v))):self.assertAlmostEqual(a,b)
 def test_lights(self):
  l=lights()['lights'];self.assertEqual(len(l),11)
  self.assertEqual(sum(r['intensity_unit']=='lumens' for r in l),10)
  for r in l:self.assertEqual(r['scale'],[1,1,1])
if __name__=='__main__':unittest.main()
