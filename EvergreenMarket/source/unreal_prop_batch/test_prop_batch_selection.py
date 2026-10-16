import hashlib,json,unittest
from pathlib import Path
import generate_prop_batch_selection as g

class SelectionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.result=g.build();cls.rows=cls.result['selected'];cls.manifest=json.loads((g.PACKAGE/'manifest.json').read_text());cls.placements={p['instance_id']:p for p in cls.manifest['placements']};cls.assets={a['asset_id']:a for a in cls.manifest['assets']}
 def test_count_and_unique(self):
  self.assertEqual(len(self.rows),16);self.assertEqual(len({r['instance_id'] for r in self.rows}),16)
 def test_exact_original_transform(self):
  for r in self.rows:
   self.assertEqual(r['source_placement'],self.placements[r['instance_id']]);self.assertEqual(r['target_placement'],r['source_placement'])
 def test_exclude_existing_pilot(self):
  self.assertEqual(len(self.result['excluded_pilot_instance_ids']),4)
  self.assertFalse(set(self.result['excluded_pilot_instance_ids'])&set(g.IDS))
 def test_canonical_scale_and_candidate(self):
  for r in self.rows:
   self.assertEqual(r['category'],'disguise_candidate');self.assertLess(max(abs(s-1) for s in r['source_placement']['scale']),1e-6);self.assertEqual(r['canonical_bounds_cm'],self.assets[r['asset_id']]['bounds_cm'])
 def test_low_heights(self):
  for r in self.rows:
   self.assertGreaterEqual(r['bottom_top_cm'][0],22.9);self.assertLess(r['bottom_top_cm'][1],80)
 def test_distributed(self):
  ps=[r['source_placement']['location_cm'] for r in self.rows]
  self.assertGreater(max(p[0] for p in ps)-min(p[0] for p in ps),2000)
  self.assertGreater(max(p[1] for p in ps)-min(p[1] for p in ps),3000)
  self.assertEqual(len({r['asset_name'] for r in self.rows}),12)
 def test_existing_geometry_and_risk(self):
  self.assertEqual(self.result['existing_collision_box_count'],694)
  self.assertEqual(self.result['original_disguise_candidate_count'],6695)
  self.assertEqual(self.result['original_logical_placement_count'],11316)
  self.assertTrue(all(r['nearby_694_boxes_within_100cm'] for r in self.rows))
  self.assertTrue(all(r['accessibility_status']=='offline_low_height_candidate_requires_PIE_test' for r in self.rows))
 def test_fingerprint_and_reproducible(self):
  self.assertEqual(self.result['source_manifest_sha256'],hashlib.sha256((g.PACKAGE/'manifest.json').read_bytes()).hexdigest())
  self.assertEqual(self.result,json.loads(Path(__file__).with_name('prop_batch_selection_v1.json').read_text()))

if __name__=='__main__':unittest.main(verbosity=2)
