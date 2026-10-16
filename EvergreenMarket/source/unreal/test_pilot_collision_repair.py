import copy
import json
from pathlib import Path
import tempfile
import unittest
import repair_pilot_collision as r

class Tests(unittest.TestCase):
    def test_actor_path_remap(self):
        a='/Game/A/Old';b='/Game/A/New'
        self.assertEqual(r.remap_actor_path(a+'.Old:PersistentLevel.Prop',a,b),b+'.New:PersistentLevel.Prop')
        with self.assertRaises(ValueError):r.remap_actor_path('/Game/X.X:PersistentLevel.Prop',a,b)
        plan={'promoted':[{'actor_path':a+'.Old:PersistentLevel.Prop'}],'remaining_scene':{'map_path':a}}
        p=r.remap_plan(plan,a,b)
        self.assertEqual(plan['remaining_scene']['map_path'],a)
        self.assertEqual(p['remaining_scene']['map_path'],b)

    def test_only_collision_expected_changes(self):
        before={str(i):{'components':{'C':{'mesh':'mesh','transform':[1.,2.], 'collision_profile':'BlockAll',
                'collision_enabled':'Both','responses':{'ECC_VISIBILITY':'Block','ECC_PAWN':'Block'},'object_type':'WorldStatic'}}} for i in range(5)}
        targets=[(str(i),'C') for i in range(4)]
        after=r.expected_snapshot(before,targets,'QueryOnly','Ignore','Block')
        self.assertEqual(after['4'],before['4'])
        self.assertEqual(before['0']['components']['C']['collision_profile'],'BlockAll')
        self.assertEqual(after['0']['components']['C']['mesh'],'mesh')
        self.assertEqual(after['0']['components']['C']['responses']['ECC_PAWN'],'Ignore')
        bad=copy.deepcopy(after);bad['4']['components']['C']['transform']=[9.,2.]
        with self.assertRaises(ValueError):r.en.compare(after,bad)
        with self.assertRaises(ValueError):r.expected_snapshot(before,targets[:3],'Q','I','B')

    def test_discovery_exact_current_known_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);d={'schema':'evergreen-prop-actor-pilot-v1','status':'failed_partial_pilot_copy',
                            'error':'Pilot collision mismatch','target_map':'/Game/Current'}
            a=root/'one';a.mkdir();p=a/'prop_pilot_report.json';p.write_text(json.dumps(d))
            self.assertEqual(r.discover_report(root,'/Game/Current'),str(p))
            with self.assertRaises(ValueError):r.discover_report(root,'/Game/Other')
            b=root/'two';b.mkdir();(b/'prop_pilot_report.json').write_text(json.dumps(d))
            with self.assertRaises(ValueError):r.discover_report(root,'/Game/Current')

    def test_wrong_failure_rejected(self):
        d={'schema':'evergreen-prop-actor-pilot-v1','status':'failed_partial_pilot_copy','error':'different failure'}
        with self.assertRaises(ValueError):r.validate_failed({'fingerprint':'fp'},d)
        d['error']='Pilot collision mismatch';d['package_fingerprint']='other'
        with self.assertRaises(ValueError):r.validate_failed({'fingerprint':'fp'},d)

if __name__=='__main__':unittest.main()
