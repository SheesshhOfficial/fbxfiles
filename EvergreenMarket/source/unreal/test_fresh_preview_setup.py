"""Pure geometry and fake-Unreal tests. Not an Unreal integration test."""
import copy
import json
import math
import os
import sys
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import fresh_preview_setup as f

class V:
    def __init__(self,*v):self.v=v;self.x,self.y,self.z=v[:3]
class T:
    def __init__(self,**v):
        self.v=v;self.translation=v['location'];self.scale3d=v['scale']
        rr=v['rotation'].v;p,y,r=(math.radians(rr[k])/2 for k in ('pitch','yaw','roll'))
        self.rotation=types.SimpleNamespace(x=math.sin(r)*math.cos(p)*math.cos(y)-math.cos(r)*math.sin(p)*math.sin(y),y=math.cos(r)*math.sin(p)*math.cos(y)+math.sin(r)*math.cos(p)*math.sin(y),z=math.cos(r)*math.cos(p)*math.sin(y)-math.sin(r)*math.sin(p)*math.cos(y),w=math.cos(r)*math.cos(p)*math.cos(y)+math.sin(r)*math.sin(p)*math.sin(y))
    def is_near_equal(self,other,**kw):return repr(self.v)==repr(other.v)
class Rot:
    def __init__(self,**v):self.v=v
    def __repr__(self):return repr(self.v)
V.__repr__=lambda self:repr(self.v)

class Component:
    def __init__(self):self.props={'intensity':0,'light_color':types.SimpleNamespace(r=255,g=255,b=255),'mobility':'STATIC','cast_shadows':True,'attenuation_radius':0,'intensity_units':'UNITLESS','use_inverse_squared_falloff':True}
    def get_editor_property(self,k):return self.props[k]
    def set_editor_property(self,k,v):self.props[k]=v
    def set_mobility(self,v):self.props['mobility']=v
    def set_light_color(self,c):self.props['light_color']=types.SimpleNamespace(r=255,g=255,b=255)
    def set_intensity(self,v):self.props['intensity']=v
    def set_attenuation_radius(self,v):self.props['attenuation_radius']=v
    def set_intensity_units(self,v):self.props['intensity_units']=v
    def set_use_inverse_squared_falloff(self,v):self.props['use_inverse_squared_falloff']=v
class DirComp(Component):pass
class PointComp(Component):pass
class Capsule(Component):
    def get_scaled_capsule_radius(self):return 40
    def get_scaled_capsule_half_height(self):return 92
    def get_world_transform(self):return self.actor.get_actor_transform()
class Actor:
    comp_type=None
    def __init__(self,location=None):
        self.props={'tags':[]};self.name=self.__class__.__name__;self.location=location or V(0,0,0);self.rot=Rot(pitch=0,yaw=0,roll=0);self.scale=V(1,1,1);self.moves=[]
        self.comp=self.comp_type() if self.comp_type else None
        if self.comp:self.comp.actor=self
    def get_name(self):return self.name
    def get_editor_property(self,k):return self.props[k]
    def set_editor_property(self,k,v):self.props[k]=v
    def set_actor_label(self,v):self.name=v
    def get_actor_label(self):return self.name
    def get_path_name(self):return self.map_path+'.'+self.map_path.rsplit('/',1)[-1]+':PersistentLevel.'+self.name
    def get_class(self):return types.SimpleNamespace(get_path_name=lambda:'/Script/Engine.'+self.__class__.__name__)
    def get_components_by_class(self,cls):return [self.comp] if isinstance(self.comp,cls) else []
    def set_actor_rotation(self,r,**kw):self.rot=r
    def set_actor_transform(self,t,**kw):
        self.moves.append(self.comp.props.get('mobility') if self.comp else None)
        self.location=t.v['location'];self.rot=t.v['rotation'];self.scale=t.v['scale'];return True
    def get_actor_transform(self):return T(location=self.location,rotation=self.rot,scale=self.scale)
class Dir(Actor):comp_type=DirComp
class Point(Actor):comp_type=PointComp
class Start(Actor):comp_type=Capsule
class Actors:
    def __init__(self):self.rows=[Actor()]
    def get_all_level_actors(self):return self.rows
    def set_actor_transform(self,actor,target):return actor.set_actor_transform(target)
    def spawn_actor_from_class(self,cls,loc,**kw):a=cls(loc);a.map_path=self.map_path;self.rows.append(a);return a
class Level:
    def __init__(self,actors,path):self.actors=actors;self.path=path;self.save_count=0;self.reload_count=0
    def get_current_level(self):return types.SimpleNamespace(get_path_name=lambda:self.path+'.'+self.path.rsplit('/',1)[-1])
    def is_in_play_in_editor(self):return False
    def save_current_level(self):self.save_count+=1;return True
    def load_level(self,path):self.path=path;self.reload_count+=1;self.actors.rows=copy.deepcopy(self.actors.rows);return True
    def new_level_from_template(self,target,source):self.path=target;return True
class SaveUtils:
    @staticmethod
    def get_dirty_map_packages():return []
    @staticmethod
    def get_dirty_content_packages():return []

def fake(root,source):
    a=Actors();a.map_path=source;a.rows[0].map_path=source;l=Level(a,source)
    u=types.SimpleNamespace(Actor=Actor,DirectionalLight=Dir,PointLight=Point,PlayerStart=Start,
        DirectionalLightComponent=DirComp,PointLightComponent=PointComp,CapsuleComponent=Capsule,
        EditorActorSubsystem=Actors,LevelEditorSubsystem=Level,EditorLoadingAndSavingUtils=SaveUtils,
        ComponentMobility=types.SimpleNamespace(MOVABLE='MOVABLE'),LightUnits=types.SimpleNamespace(LUMENS='LUMENS'),
        Vector=V,Rotator=Rot,Transform=T,LinearColor=V,get_default_object=lambda cls:cls(),
        get_editor_subsystem=lambda cls:a if cls is Actors else l,
        Paths=types.SimpleNamespace(project_saved_dir=lambda:root,project_content_dir=lambda:root),
        log=lambda s:None,log_error=lambda s:None)
    return u,a,l

def support():return {'instance_id':'ground','name':'Front walkway','center':[0,2100,-8],'extent':[2400,300,8],
                       'placement':{'quaternion_xyzw':[0,0,0,1],'scale':[1,1,1]}}
class PreviewTests(unittest.TestCase):
    def test_actual_568_box_clearance(self):
        root=Path(os.environ.get('EVERGREEN_PACKAGE','supermarket_unreal_handoff')).resolve()
        if not root.exists():self.skipTest('Original geometry fixture not available')
        c=f.em.load_contract(root);boxes=f.ec.make_plan(c)['boxes'];r=f.clearance(boxes)
        self.assertEqual(r['boxes_tested'],568);self.assertTrue(r['conservative_aabb_clear'])
    def test_clearance_support(self):self.assertEqual(f.clearance([support()])['support_ids'],['ground'])
    def test_clearance_rejects_blocker(self):
        b=support();b.update(instance_id='wall',name='Wall',center=list(f.START),extent=[1,1,1])
        with self.assertRaisesRegex(ValueError,'blocked'):f.clearance([support(),b])
    def test_clearance_rejects_missing_support(self):
        with self.assertRaisesRegex(ValueError,'support'):f.clearance([])
    def test_yaw_rotated_scaled_aabb(self):
        b=support();b.update(center=[0,0,0],extent=[10,20,30]);b['placement']={'quaternion_xyzw':[0,0,math.sin(math.pi/4),math.cos(math.pi/4)],'scale':[2,1,1]}
        lo,hi=f.box_aabb(b);self.assertTrue(all(abs(a-b)<1e-8 for a,b in zip(hi,[20,20,30])))
    def test_invalid_capsule(self):
        with self.assertRaises(ValueError):f.clearance([support()],radius=101,half_height=100)
    def test_copy_path_remaps_package_and_object(self):
        src='/Game/X/L_A';target=src+'_Preview_1';p={'source_map':src,'pilot_plan':{'remaining_scene':{'map_path':src},'promoted':[{'actor_path':src+'.L_A:PersistentLevel.Prop_0'}]}}
        q=f._copy_pilot_plan(p,target)
        self.assertEqual(q['pilot_plan']['promoted'][0]['actor_path'],target+'.L_A_Preview_1:PersistentLevel.Prop_0')
        self.assertEqual(p['pilot_plan']['remaining_scene']['map_path'],src)
    def test_copy_path_rejects_wrong_map_object(self):
        p={'source_map':'/Game/X/L_A','pilot_plan':{'remaining_scene':{},'promoted':[{'actor_path':'/Game/X/L_A.Wrong:PersistentLevel.X'}]}}
        with self.assertRaises(ValueError):f._copy_pilot_plan(p,'/Game/X/L_B')
    def test_sample_report_rejects_failed_before_mutation(self):
        with patch.object(f,'_fresh'):
            with self.assertRaises(ValueError):f._sample_plan({'fingerprint':'x'},{'status':'failed'})
    def test_sample_plan_accepts_only_exact_fresh_report(self):
        r={'schema':f.em.SCHEMA,'phase':'sample','status':'verified_persistence','package_fingerprint':'x','map_path':'/Game/EvergreenHandoff/Sample_123/Maps/L_Evergreen_sample'}
        with patch.object(f,'_fresh'):
            p=f._sample_plan({'fingerprint':'x'},r);self.assertIsNone(p['player_start']);self.assertEqual(p['target_map'],r['map_path'])
    def test_api_missing_preflight(self):
        with self.assertRaisesRegex(ValueError,'class missing'):f._api(types.SimpleNamespace(),{'player_start':None})
    def test_mock_spawn_and_save_reload(self):
        with tempfile.TemporaryDirectory() as root:
            source='/Game/EvergreenHandoff/Sample_1/Maps/L_Evergreen_sample';u,a,l=fake(root,source)
            plan=dict(mode='sample',source_map=source,target_map=source,lights=copy.deepcopy(f.LIGHTS),player_start=None)
            with patch.object(f.em,'verify_scene',return_value={'ok':True}):out=f._execute(u,{'fingerprint':'x'},plan,{},backup_confirmed=True)
            report=json.loads(Path(out).read_text());self.assertEqual(report['status'],'verified_preview_persistence');self.assertEqual(report['mode'],'sample')
            self.assertEqual(l.save_count,1);self.assertEqual(l.reload_count,1);self.assertEqual(len(a.rows),1+len(f.LIGHTS))
            self.assertTrue(report['after_reload']['transforms_components_and_settings_verified'])
    def test_missing_backup_refuses(self):
        with self.assertRaisesRegex(ValueError,'backup'):f._execute(None,{},None,None,backup_confirmed=False)
    def test_repeated_preview_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');a.rows[0].props['tags']=[f.TAG]
            with self.assertRaisesRegex(ValueError,'already exist'):f._preflight(u,{'source_map':'/Game/S','player_start':None,'lights':copy.deepcopy(f.LIGHTS)})
            self.assertEqual(len(a.rows),1)
    def test_wrong_current_map_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/Other')
            with self.assertRaisesRegex(ValueError,'exact fresh map'):f._preflight(u,{'source_map':'/Game/S','player_start':None,'lights':copy.deepcopy(f.LIGHTS)})
    def test_unsaved_changes_refuse(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');u.EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_map_packages=lambda:['dirty'],get_dirty_content_packages=lambda:[])
            with self.assertRaisesRegex(ValueError,'pending'):f._preflight(u,{'source_map':'/Game/S','player_start':None,'lights':copy.deepcopy(f.LIGHTS)})
    def test_light_state_change_detected(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');i=copy.deepcopy(f.LIGHTS[0]);f._spawn(u,i);a.rows[-1].comp.props['intensity']=2
            with self.assertRaisesRegex(ValueError,'intensity'):f._verify(u,dict(lights=[i],player_start=None))
    def test_editor_dry_preflight_checks_api_before_mutation(self):
        with patch.dict(sys.modules,{'unreal':types.SimpleNamespace()}):
            with self.assertRaisesRegex(ValueError,'class missing'):
                f.editor_preflight({'player_start':None},{})
    def test_editor_dry_preflight_verifies_sample(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');p=dict(mode='sample',source_map='/Game/S',lights=copy.deepcopy(f.LIGHTS),player_start=None)
            with patch.dict(sys.modules,{'unreal':u}),patch.object(f.em,'verify_scene') as v:
                result=f.editor_preflight(p,{},{});self.assertTrue(result['editor_checks_run']);v.assert_called_once()
            self.assertEqual(len(a.rows),1)
    def test_player_start_component_and_transform_verify(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');item=dict(key='PlayerStart',actor='PlayerStart',component='CapsuleComponent',location=list(f.START),rotation=[0,-90,0])
            f._spawn(u,item);p=dict(lights=[],player_start=item,pilot_plan={'collision_plan':{'boxes':[support()]}})
            self.assertTrue(f._verify(u,p)['player_starts'])
    def test_factory_nonunit_scale_is_explicitly_repaired(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');actor=Dir(V(5,5,5));actor.scale=V(2.5,2.5,2.5)
            f._configure(u,actor,f.LIGHTS[0]);self.assertEqual(actor.scale.v,(1,1,1));self.assertEqual(actor.moves,['MOVABLE'])
    def test_none_transform_result_fails_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');actor=Dir()
            with patch.object(actor,'set_actor_transform',return_value=None):
                with self.assertRaisesRegex(ValueError,'setter failed'):f._configure(u,actor,f.LIGHTS[0])
    def test_false_transform_result_fails_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');actor=Dir()
            with patch.object(actor,'set_actor_transform',return_value=False):
                with self.assertRaisesRegex(ValueError,'setter failed'):f._configure(u,actor,f.LIGHTS[0])
    def test_success_return_wrong_rotation_is_detected(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');actor=Dir()
            with patch.object(actor,'set_actor_transform',return_value=True):
                with self.assertRaisesRegex(ValueError,'quaternion_xyzw'):f._configure(u,actor,f.LIGHTS[0])
    def test_verify_transform_error_names_actor_and_expected_actual(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l=fake(root,'/Game/S');f._spawn(u,f.LIGHTS[0]);a.rows[-1].scale=V(2,2,2)
            with self.assertRaises(ValueError) as exc:f._verify(u,dict(lights=[f.LIGHTS[0]],player_start=None))
            self.assertIn('EM_PREVIEW_Sun',str(exc.exception));self.assertIn('actual',str(exc.exception));self.assertIn('expected',str(exc.exception))
    def _recovery_fixture(self,root):
        source='/Game/EvergreenHandoff/Sample_123/Maps/L_Evergreen_sample';u,a,l=fake(root,source)
        plan=dict(mode='sample',source_map=source,target_map=source,lights=copy.deepcopy(f.LIGHTS),player_start=None)
        for item in plan['lights']:f._spawn(u,item)
        a.rows[1].scale=V(2.5,2.5,2.5)
        contract={'fingerprint':'x'}
        report={'schema':f.em.SCHEMA,'phase':'sample','status':'verified_persistence','package_fingerprint':'x','map_path':source}
        failed={'schema':f.SCHEMA,'status':'failed_partial_preview','mode':'sample','source_map':source,'target_map':source,'package_fingerprint':'x','plan':plan,'error':'Preview transform changed'}
        return u,a,l,plan,contract,report,failed
    def test_recovery_sun_factory_scale_only_save_reload(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);rp=Path(root)/'sample.json';fp=Path(root)/'failed.json'
            rp.write_text(json.dumps(report));fp.write_text(json.dumps(failed));original=fp.read_bytes()
            with patch.dict(sys.modules,{'unreal':u}),patch.object(f.em,'load_contract',return_value=c),patch.object(f,'_fresh'),patch.object(f.em,'verify_scene'):
                result=f.recover_sample(root,rp,fp,execute=True,backup_confirmed=True)
            out=json.loads(Path(result).read_text());self.assertEqual(out['status'],'verified_preview_persistence');self.assertEqual(out['changed_light_keys'],['Sun'])
            self.assertEqual(len(a.rows),12);self.assertEqual(l.reload_count,1);self.assertEqual(fp.read_bytes(),original);self.assertEqual(a.rows[1].scale.v,(1,1,1))
    def test_recovery_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root)
            with patch.object(f.em,'verify_scene'):
                actors,summary=f._recovery_preflight(u,c,plan,report,require_clean=False)
            self.assertEqual(summary['mismatched_lights'],['Sun']);self.assertEqual(a.rows[1].scale.v,(2.5,2.5,2.5));self.assertEqual(l.save_count,0)
    def test_recovery_already_correct_sun_allowed_without_respawn(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);a.rows[1].scale=V(1,1,1)
            with patch.object(f.em,'verify_scene'):actors,summary=f._recovery_preflight(u,c,plan,report,require_clean=False)
            self.assertEqual(summary['mismatched_lights'],[])
    def test_recovery_rejects_changed_point_transform(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);a.rows[2].scale=V(2,2,2)
            with patch.object(f.em,'verify_scene'):
                with self.assertRaisesRegex(ValueError,'point-light'):f._recovery_preflight(u,c,plan,report,require_clean=False)
    def test_recovery_rejects_changed_sun_rotation(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);a.rows[1].rot=Rot(pitch=0,yaw=0,roll=0)
            with patch.object(f.em,'verify_scene'):
                with self.assertRaisesRegex(ValueError,'unexpected location'):f._recovery_preflight(u,c,plan,report,require_clean=False)
    def test_recovery_rejects_changed_light_intensity(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);a.rows[2].comp.props['intensity']=1
            with self.assertRaisesRegex(ValueError,'intensity'):f._recovery_preflight(u,c,plan,report,require_clean=False)
    def test_recovery_rejects_missing_light(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);a.rows.pop()
            with self.assertRaisesRegex(ValueError,'all 11'):f._recovery_preflight(u,c,plan,report,require_clean=False)
    def test_recovery_rejects_wrong_failure_map(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);failed['target_map']='/Game/Wrong'
            with patch.object(f,'_fresh'):
                with self.assertRaisesRegex(ValueError,'another package/map'):f._recovery_plan(c,report,failed)
    def test_recovery_requires_clean_editor_for_execution(self):
        with tempfile.TemporaryDirectory() as root:
            u,a,l,plan,c,report,failed=self._recovery_fixture(root);u.EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_map_packages=lambda:['dirty'],get_dirty_content_packages=lambda:[])
            with self.assertRaisesRegex(ValueError,'Save all pending'):f._recovery_preflight(u,c,plan,report,require_clean=True)
if __name__=='__main__':unittest.main()
