"""Local fake-Unreal regression tests, not engine integration tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'evergreen_source_v2'/'source'/'unreal'
sys.path.insert(0,str(SOURCE))
import fixture_point_patch as f
import fresh_preview_setup as fp
import test_source_preview as fake

class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=fp.em.load_contract(HERE.parent/'evergreen_source_v2')
        cls.items=f.layout_plan(HERE/'fixture_point_layout_v1.json',cls.contract)
    def setup_fake(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        u,a,l=fake.fake(self.tmp.name,'/Game/Test/L_Preview_1')
        for cls in (fake.Dir,fake.Point,fake.Start):
            cls.static_class=classmethod(lambda c:c)
        for cls in (fake.Dir,fake.Point,fake.Start):cls.get_class=lambda self:type(self)
        # Actor classes need the same identity in exact-class validation and snapshots.
        for cls in (fake.Dir,fake.Point,fake.Start):cls.get_path_name_class='/Script/Engine.'+cls.__name__
        # Snapshots mocked in execution tests; test preservation separately with real fake class paths.
        u.LightComponentBase=fake.Component;u.log_warning=lambda text:None
        fake.Component.get_name=lambda self:'LightComponent'
        fake.Component.get_world_transform=lambda self:self.actor.get_actor_transform()
        fake.PointComp.set_source_radius=lambda self,v:self.props.update(source_radius=v)
        fake.PointComp.set_soft_source_radius=lambda self,v:self.props.update(soft_source_radius=v)
        fake.PointComp.set_source_length=lambda self,v:self.props.update(source_length=v)
        fake.Actors.destroy_actor=lambda self,actor: self.rows.remove(actor) is None
        for item in fp.LIGHTS:fp._spawn(u,item)
        start=fake.Start();start.map_path=l.path;start.set_actor_label('EM_PREVIEW_PlayerStart');start.props['tags']=[fp.TAG,'EMPreview=PlayerStart'];a.rows.append(start)
        ctx=dict(fp=fp,source_map=l.path,preview=dict(source_map='/Game/Test/L_Pilot',target_map=l.path,lights=copy.deepcopy(fp.LIGHTS),pilot_plan={'remaining_scene':{'map_path':l.path},'promoted':[]}),ep=types.SimpleNamespace(verify=lambda *x:dict(promoted_actors=4,preserved_collision_boxes=694)),ec=types.SimpleNamespace(_check_original_collision=lambda *x:None),contract=self.contract,hashes={})
        return u,a,l,ctx
    def test_bootstrap_without_dunder_file(self):
        script=(HERE/'Start_Fixture_Lights.py').read_text()
        calls=[];module=types.SimpleNamespace(run=lambda *args:calls.append(args) or {})
        spec=types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m:None))
        with patch('importlib.util.spec_from_file_location',return_value=spec),patch('importlib.util.module_from_spec',return_value=module):
            scope={};exec(compile(script,'Start_Fixture_Lights.py','exec'),scope)
        self.assertEqual(len(calls),1);self.assertIn('fixture_patch',scope);self.assertNotIn('__file__',scope)
    def test_execute_copy_verify_save_reload_and_failure_report(self):
        u,a,l,ctx=self.setup_fake()
        # Unit integration of orchestration. Detailed actor/light contracts tested above.
        fp_fake=types.SimpleNamespace(_current=lambda u:l.path)
        ctx['fp']=fp_fake;ctx['preview']={};ctx['hashes']={}
        mocked_found={'Sun':a.rows[1]}
        for fail in (False,True):
            l.path=ctx['source_map'];l.save_count=0;l.reload_count=0
            snapshot_values=[{'preserved':True},{'preserved':not fail},{'preserved':True}]
            with patch.object(f,'verified_context',return_value=ctx),patch.object(f,'preflight',return_value=(mocked_found,{'preserved':True},{},[])),patch.object(f,'old_lights',return_value={}),patch.object(f,'snapshot',side_effect=snapshot_values),patch.object(f,'spawn'),patch.object(f,'verify_points',return_value=set()),patch.object(f,'remap_pilot',return_value={}),patch.dict(sys.modules,unreal=u):
                if fail:
                    with self.assertRaisesRegex(ValueError,'before save'):f.run('fake',HERE/'fixture_point_layout_v1.json',execute=True,backup_confirmed=True)
                    self.assertEqual(l.save_count,0)
                else:
                    result=f.run('fake',HERE/'fixture_point_layout_v1.json',execute=True,backup_confirmed=True)
                    self.assertEqual(f.read(result)['status'],'verified_fixture_lights_persistence');self.assertEqual(l.save_count,1);self.assertEqual(l.reload_count,1)
            reports=[f.read(p) for p in Path(self.tmp.name).glob('EvergreenHandoff/FixtureLights_*/fixture_lights_report.json')]
            self.assertTrue(any(r['status']==('failed_partial_fixture_patch' if fail else 'verified_fixture_lights_persistence') for r in reports))
    def test_layout_all_actual_fixtures(self):
        self.assertEqual(len(self.items),42)
        self.assertTrue(all(i['actor']=='PointLight' for i in self.items))
        self.assertEqual(len({i['source_fixture_instance_id'] for i in self.items}),42)
    def test_custom_layout_intensity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'custom.json';data=f.read(HERE/'fixture_point_layout_v1.json');data['lights'][0]['intensity']=1234;p.write_text(json.dumps(data))
            self.assertEqual(f.layout_plan(p,self.contract)[0]['intensity'],1234)
    def test_reject_missing_fixture_or_directional(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'custom.json';data=f.read(HERE/'fixture_point_layout_v1.json');data['lights'].pop();p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'each approved'):f.layout_plan(p,self.contract)
            data=f.read(HERE/'fixture_point_layout_v1.json');data['lights'][0]['actor']='DirectionalLight';p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'Only PointLight'):f.layout_plan(p,self.contract)
    def test_source_manifest_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'custom.json';data=f.read(HERE/'fixture_point_layout_v1.json');data['source_manifest_sha256']='bad';p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'manifest differs'):f.layout_plan(p,self.contract)
    def test_spawn_scale_25_reset_and_settings(self):
        u,a,l,c=self.setup_fake();original=a.spawn_actor_from_class
        def spawn(*args,**kwargs):
            actor=original(*args,**kwargs);actor.scale=fake.V(2.5,2.5,2.5);return actor
        a.spawn_actor_from_class=spawn
        item=self.items[0];actor=f.spawn(u,fp,item)
        self.assertEqual(actor.scale.v,(1,1,1));self.assertEqual(actor.comp.props['intensity_units'],'LUMENS')
        self.assertTrue(actor.comp.props['cast_shadows']);self.assertEqual(actor.comp.props['source_radius'],2)
    def test_removal_scope_preserves_start_manual_and_tuned(self):
        u,a,l,c=self.setup_fake();manual=fake.Dir();manual.map_path=l.path;manual.set_actor_label('MySun');a.rows.append(manual)
        old=f.old_lights(u,c);old['Sun'].comp.props['intensity']=1
        self.assertEqual(len(f.old_lights(u,c)),11)
        for actor in old.values():a.destroy_actor(actor)
        self.assertIn(manual,a.rows);self.assertTrue(any(isinstance(x,fake.Start) for x in a.rows))
    def test_unknown_or_duplicate_old_tag_fails(self):
        u,a,l,c=self.setup_fake();old=f.old_lights(u,c);old['Sun'].props['tags']=[fp.TAG,'EMPreview=Unknown']
        with self.assertRaisesRegex(ValueError,'Unknown/duplicate'):f.old_lights(u,c)
    def test_existing_patch_blocks_rerun(self):
        u,a,l,c=self.setup_fake();f.spawn(u,fp,self.items[0])
        with self.assertRaisesRegex(ValueError,'already present'):f.old_lights(u,c)
    def test_full_point_set_verify_rejects_changed_temperature(self):
        u,a,l,c=self.setup_fake()
        for actor in f.old_lights(u,c).values():a.destroy_actor(actor)
        points=[f.spawn(u,fp,item) for item in self.items]
        self.assertEqual(len(f.verify_points(u,c,self.items)),42)
        points[0].comp.props['use_temperature']=True
        with self.assertRaisesRegex(ValueError,'temperature'):f.verify_points(u,c,self.items)
    def test_current_map_guard(self):
        u,a,l,c=self.setup_fake();l.path='/Game/Wrong'
        with self.assertRaisesRegex(ValueError,'successful final'):f.preflight(u,c,self.items)
    def test_dirty_map_guard(self):
        u,a,l,c=self.setup_fake()
        with patch.object(fake.SaveUtils,'get_dirty_map_packages',return_value=['Dirty']):
            with self.assertRaisesRegex(ValueError,'never discards'):f.preflight(u,c,self.items)
    def test_report_remap_uses_current_final_not_original_pilot(self):
        old='/Game/L_Pilot';current=old+'_Preview_1';target=current+'_FixtureLights_1'
        preview=dict(source_map=old,pilot_plan={'remaining_scene':{'map_path':current},'promoted':[{'actor_path':current+'.'+current.split('/')[-1]+':PersistentLevel.Prop'}]})
        mapped=f.remap_pilot(fp,preview,current,target)
        self.assertEqual(mapped['remaining_scene']['map_path'],target)
        self.assertEqual(mapped['promoted'][0]['actor_path'],target+'.'+target.split('/')[-1]+':PersistentLevel.Prop')
    def test_state_or_report_hash_change(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'run_state.json';p.write_text('original');hashes={str(p):f.sha(p)};p.write_text('edited')
            with self.assertRaisesRegex(ValueError,'Protected state/report/helper'):f.unchanged(hashes)
    def test_helper_hash_fails_before_import(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source'/'unreal';source.mkdir(parents=True);(source/(f.HELPERS[0]+'.py')).write_text('raise RuntimeError("must not run")')
            state=root/'run_state.json';state.write_text(json.dumps(dict(schema='evergreen-native-fresh-run-v2',merged_package=d,helper_hashes={f.HELPERS[0]+'.py':'bad'})))
            with self.assertRaisesRegex(ValueError,'Frozen helper hash'):f.load_helpers(state)
    def test_snapshot_covers_all_preserved_actors(self):
        u,a,l,c=self.setup_fake()
        # Restore snapshot-class API on these instances without changing exact removal scope.
        for actor in a.rows:actor.get_class=lambda:types.SimpleNamespace(get_path_name=lambda:'/Script/Engine.Actor')
        with patch.object(f,'light_properties',return_value={'intensity':17}):
            before=f.snapshot(u,c,set());self.assertEqual(len(before),len(a.rows));a.rows[0].scale=fake.V(2,2,2)
            self.assertNotEqual(f.snapshot(u,c,set()),before)
    def test_copy_transient_fields_ignored(self):
        class C:
            def get_editor_property(self,k):return self.props[k]
        c=C();c.props={k:1 for k in ('intensity','light_color','mobility','cast_shadows','visible','affects_world','indirect_lighting_intensity','volumetric_scattering_intensity')}
        c.props['light_guid']='before';c.props['primary_component_tick']='memory address before'
        before=f.light_properties(c,'/Game/Test');c.props['light_guid']='after';c.props['primary_component_tick']='memory address after'
        self.assertEqual(before,f.light_properties(c,'/Game/Test'))
        c.props['cast_shadows']=False;self.assertNotEqual(before,f.light_properties(c,'/Game/Test'))
        c.props['cast_shadows']=1;c.props['intensity']=999;self.assertNotEqual(before,f.light_properties(c,'/Game/Test'))
    def test_manual_light_settings_drift_detected(self):
        class C:
            def get_editor_property(self,k):return self.props[k]
        c=C();c.props={k:1 for k in ('intensity','light_color','mobility','cast_shadows','visible','affects_world','indirect_lighting_intensity','volumetric_scattering_intensity')};c.props['temperature']=2700
        before=f.light_properties(c,'/Game/Test');c.props['temperature']=6500
        self.assertNotEqual(before,f.light_properties(c,'/Game/Test'))

if __name__=='__main__':unittest.main()
