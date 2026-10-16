"""Pure-data tests, no Unreal required. Add the existing Unreal helper folder to PYTHONPATH."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import setup_market_normals as n


class Tests(unittest.TestCase):
    def test_compare_remap_preserves_original(self):
        before={'A':{'transform':[1.0,2.0], 'components':{'C':{'mesh':'old','materials':['m'],'instances':[[0.,1.]]}}}}
        expected=n.remap_snapshot(before,{'old':'new'})
        self.assertEqual(before['A']['components']['C']['mesh'],'old')
        self.assertEqual(expected['A']['components']['C']['mesh'],'new')
        n.compare(expected,copy.deepcopy(expected))
        bad=copy.deepcopy(expected);bad['A']['components']['C']['materials']=['changed']
        with self.assertRaises(ValueError):n.compare(expected,bad)
        bad=copy.deepcopy(expected);bad['A']['components']['C']['instances'][0][0]=2.
        with self.assertRaises(ValueError):n.compare(expected,bad)
        with self.assertRaises(ValueError):n.compare(expected,{})

    def test_patch_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=root/'old';patch=root/'patch';old.mkdir();patch.mkdir();(patch/'assets').mkdir()
            (old/'manifest.json').write_text('original')
            (patch/'assets/a.fbx').write_bytes(b'corrected')
            asset={'name':'Checkout base','file_sha256':'oldhash','materials':['M'],'bounds_cm':[1,2,3]}
            c={'root':old,'assets':{'A':asset}}
            row={'asset_id':'A','name':'Checkout base','original_file_sha256':'oldhash',
                 'file_sha256':n.em._sha(patch/'assets/a.fbx'),'fbx_path':'assets/a.fbx','materials':['M'],'bounds_cm':[1,2,3]}
            doc={'schema':n.PATCH_SCHEMA,'original_manifest_sha256':n.em._sha(old/'manifest.json'),'assets':[row]}
            p=patch/'patch_manifest.json';p.write_text(json.dumps(doc))
            result=n.load_patch(c,patch);self.assertEqual(set(result['assets']),{'A'})
            doc['assets'][0]['materials']=['wrong'];p.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):n.load_patch(c,patch)
            doc['assets'][0]['materials']=['M'];doc['assets'][0]['fbx_path']='../old/manifest.json';p.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):n.load_patch(c,patch)

    def test_discovery_exact_not_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); f='/Game/EvergreenHandoff/Full_x/Maps/L_Evergreen_full';walk=f+'_WalkTest_x';target=walk+'_PropPilot_x_Recovered_x'
            records=[('f/import_report.json',{'schema':n.em.SCHEMA,'phase':'full','status':'verified_persistence','map_path':f,'package_fingerprint':'fp'}),
                     ('p/prop_pilot_report.json',{'schema':'evergreen-prop-actor-pilot-v1','status':'verified_pilot_persistence','target_map':target,'source_map':walk,'package_fingerprint':'fp'})]
            for rel,data in records:
                p=root/rel;p.parent.mkdir();p.write_text(json.dumps(data))
            self.assertEqual(n.discover_reports(root,target)['prop_pilot_report'],str(root/'p/prop_pilot_report.json'))
            with self.assertRaises(ValueError):n.discover_reports(root,target+'_Normals_sample')
            (root/'dup').mkdir();(root/'dup/prop_pilot_report.json').write_text(json.dumps(records[1][1]))
            with self.assertRaises(ValueError):n.discover_reports(root,target)

    def test_full_gate(self):
        f='/Game/EvergreenHandoff/Full_x/Maps/L_Evergreen_full'; walk=f+'_WalkTest_x';target=walk+'_PropPilot_x_Recovered_x'
        c={'fingerprint':'fp','placements':[{'instance_id':'I'}]}
        full={'schema':n.em.SCHEMA,'phase':'full','status':'verified_persistence','package_fingerprint':'fp','map_path':f,
              'placement_count':1,'groups':{'G':{'instances':[{'instance_id':'I'}]}},'meshes':{'A':{'path':'/A'},'B':{'path':'/B'}}}
        patch={'fingerprint':'patch','assets':{'A':{'name':'ShippingCarton_Floor'},'B':{'name':'Checkout base'}}}
        pilot={'schema':'evergreen-prop-actor-pilot-v1','status':'verified_pilot_persistence','package_fingerprint':'fp','target_map':target}
        plan=n.make_plan(c,patch,full,pilot,'sample')
        report=dict(plan,schema=n.SCHEMA,status='verified_persistence')
        with self.assertRaises(ValueError):n.make_plan(c,patch,full,pilot,'full',report,False)
        n.make_plan(c,patch,full,pilot,'full',report,True)
        report['patch_fingerprint']='wrong'
        with self.assertRaises(ValueError):n.make_plan(c,patch,full,pilot,'full',report,True)

if __name__=='__main__':unittest.main()
