"""Self-contained offline unit/mock tests. They never import or run Unreal."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import store_importer as s
import materials as b


def material(name='Mat'):
    constants={'Base Color':[.5,.6,.7,1], 'Metallic':0., 'Roughness':.4, 'Specular IOR Level':.5,
        'IOR':1.5, 'Alpha':1., 'Transmission Weight':0., 'Emission Strength':0., 'Emission Color':[0,0,0,1]}
    return dict(material=name, channels={k:dict(value=v,linked=False) for k,v in constants.items()},
        principled_node='P', surface_shader_node='P', surface_shader_type='BSDF_PRINCIPLED',
        surface_inputs={}, node_graph=[dict(name='P',type='BSDF_PRINCIPLED')], links=[], images=[], procedural=False)


def export_fixture(root, probe=False):
    root.mkdir(parents=True)
    ids=['unit_axis_probe'] if probe else ['main_floor','wall_left','premium_shelf_bay','shopping_basket','cafe_chair','shopping_cart','service_counter','shipping_carton_large','crushed_tomatoes','visual_context','sign_text','sign_backing','sign_hanger','pine_tall_v3_variant_2']
    assets=[]; places=[]
    for n,aid in enumerate(ids):
        mesh='SM_'+aid; rel='fbx/'+mesh+'.fbx'; (root/'fbx').mkdir(exist_ok=True); (root/rel).write_bytes((mesh+' fixture, not real FBX').encode())
        eligible=not probe and aid not in ['main_floor','wall_left','visual_context','sign_text','sign_backing','sign_hanger','pine_tall_v3_variant_2']
        hulls=[] if aid=='visual_context' else ['UCX_'+mesh+'_%02d'%i for i in range(3 if probe else 1)]
        assets.append(dict(asset_id=aid,mesh=mesh,eligible=eligible,fbx=rel,sha256=s.sha(root/rel),hulls=hulls,
            collision_mode='AUTHORED_SIMPLE' if hulls else 'NONE',auto_generate_collision=False,image_uv_bindings=[],optical_slot_geometry={},
            objects=[dict(bounds_min_m=[0,0,0],bounds_max_m=[1,2,3],dimensions_m=[1,2,3],triangles=12,uv_layers=['UVMap'],materials=['Mat'])]))
        if not probe:
            for j in range(3 if aid=='crushed_tomatoes' else 1):
                places.append(dict(stable_id=aid+'_'+str(j),asset_id=aid,object_name={'sign_text':'SIGN 01  BREAKFAST','sign_backing':'V3_Sign_backing_01','sign_hanger':'V3_Sign_hanger_01_0'}.get(aid,aid),intended_unreal_actor_class='StaticMeshActor',eligible=eligible,
                    tags=['Prop'] if eligible else [],position_m=[n,j,0],rotation_euler_deg=[0,0,0],scale=[1,1,1],instance_material_overrides=False))
    lights=[] if probe else [dict(id='Light_%02d'%i,type='AREA',export_to_unreal=True,render_only=False,energy_watts=220.,color_rgb=[1,.86,.68],size_m=[3.22,.18],shape='RECTANGLE',position_m=[i,0,4],rotation_euler_deg=[0,0,0]) for i in range(67)]
    doc=dict(schema='evergreen-fbx-export-v1',source_unchanged=True,source_sha256='derivative',source_lineage={'approved_source_sha256':s.APPROVED_SOURCE_SHA256},
        assets=assets,placements=places,images=[],unit_contract={k:s.FBX_SETTINGS[k] for k in ['convert_scene','convert_scene_unit','force_front_x_axis','import_uniform_scale']},
        eligible_actor_count=sum(p['eligible'] for p in places),total_actor_count=len(places),lights=lights,render_only_lights=[])
    s.write(root/'EXPORT_VALIDATION_MANIFEST.json',doc);s.write(root/'MATERIAL_CONTRACT.json',{'materials':[material()]})
    s.write(root/'FBX_ROUNDTRIP_VALIDATION.json',dict(status='PASS',source_sha256='derivative',assets_tested=len(assets),assets_passed=len(assets),collision_hulls_tested=sum(len(a['hulls']) for a in assets),total_placements_preserved=len(places),eligible_placements_preserved=doc['eligible_actor_count'],results=[dict(asset_id=a['asset_id'],passed=True,fbx_sha256=a['sha256']) for a in assets]))
    s.write(root/'PIPELINE_RUN.json',dict(status='PASS',source_unchanged=True,source_checksums_before={'source':'derivative'},source_checksums_after={'source':'derivative'},processes=[dict(stage='export',returncode=0),dict(stage='roundtrip',returncode=0)]))
    s.write(root/'TEXTURE_UV_BINDINGS.json',{'assets':[dict(mesh=a['mesh'],bindings=[]) for a in assets]})


def package_fixture(root):
    export_fixture(root/'export');export_fixture(root/'qa_axis/export',True)
    s.write(root/'export/SCENE_SUPPORT.json',dict(schema='premium-store-scene-support-v3',approved_source_sha256=s.APPROVED_SOURCE_SHA256,
        boundaries=[dict(id='LEFT',position_m=[0,0,0],centre_m=[0,0,0],dimensions_m=[.2,56,4.7],metadata_only=True,duplicate_blocker_creation=False,placement_ids=['wall_left_0'])],
        spawn_markers=[dict(id='START',kind='PlayerStart',position_m=[1,1,1],rotation_euler_deg=[0,0,0])]))
    return root


class Obj:
    def __init__(self,path='',kind=''): self.path=path;self.kind=kind;self.props={}
    def set_editor_property(self,key,value): self.props[key]=value
    def get_editor_property(self,key): return self.props.get(key)
    def get_path_name(self): return self.path+'.'+self.path.rsplit('/',1)[-1]

class Vec:
    def __init__(self,x=0,y=0,z=0):self.x=x;self.y=y;self.z=z
class Quat:
    def __init__(self,x=0,y=0,z=0,w=1):self.x=x;self.y=y;self.z=z;self.w=w
    def rotator(self):return self
class Transform:
    def __init__(self,location,rotation,scale):self.translation=location;self.rotation=rotation;self.scale3d=scale
class Component(Obj):
    def __init__(self):super().__init__();self.responses={}
    def set_mobility(self,x):self.mobility=x
    def set_visibility(self,x,**kw):self.props['visible']=x
    def set_cast_shadow(self,x):self.props['cast_shadow']=x
    def set_static_mesh(self,x):self.props['static_mesh']=x;return True
    def set_collision_profile_name(self,x,**kw):self.profile=x
    def set_collision_enabled(self,x):self.enabled=x
    def set_collision_object_type(self,x):self.object_type=x
    def set_collision_response_to_all_channels(self,x):self.all_response=x
    def set_collision_response_to_channel(self,k,v):self.responses[k]=v
    def get_collision_response_to_channel(self,k):return self.responses.get(k,self.all_response)
    def get_collision_enabled(self):return self.enabled
class Actor(Obj):
    def __init__(self):super().__init__();self.props['static_mesh_component']=Component()
    def set_actor_label(self,label):self.label=label
    def set_actor_hidden_in_game(self,x):self.props['hidden']=x
    def get_actor_transform(self):return self.transform
    def get_components_by_class(self,c):return []
class Actors:
    def __init__(self):self.actors=[]
    def spawn_actor_from_class(self,cls,*args,**kw):a=cls();self.actors.append(a);return a
    def set_actor_transform(self,a,t):a.transform=t;return True
    def get_all_level_actors(self):return self.actors

def fake_spawn_ue():
    return SimpleNamespace(StaticMeshActor=Actor,Vector=Vec,Quat=Quat,Transform=Transform,
        ComponentMobility=SimpleNamespace(STATIC='static'),CollisionEnabled=SimpleNamespace(NO_COLLISION='none',QUERY_AND_PHYSICS='both'),
        CollisionChannel=SimpleNamespace(ECC_VISIBILITY='visibility',ECC_PAWN='pawn',ECC_WORLD_STATIC='worldstatic'),
        CollisionResponseType=SimpleNamespace(ECR_BLOCK='block',ECR_IGNORE='ignore'))


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=package_fixture(Path(self.temp.name));self.contract=s.load_package(self.root)
    def tearDown(self):self.temp.cleanup()
    def modify_export(self,fn):
        p=self.root/'export/EXPORT_VALIDATION_MANIFEST.json';d=s.read(p);fn(d);s.write(p,d)
    def test_dry_run_does_not_import_unreal(self):
        p=s.build_plan(self.contract);self.assertNotIn('unreal',sys.modules);self.assertEqual(p['mode'],'DRY_RUN');self.assertFalse((self.root/'runtime_reports').exists())
    def test_full_plan_contains_every_copy(self):
        p=s.build_plan(self.contract,'full');self.assertEqual(p['expected_placement_count'],16);self.assertEqual(p['expected_eligible_count'],9)
        self.assertEqual(len({r['stable_id'] for r in p['placements']}),16)
    def test_sample_has_three_same_item_copies_and_all_required_roles(self):
        p=s.build_plan(self.contract);self.assertEqual(sum(r['asset_id']=='crushed_tomatoes' for r in p['placements']),3)
        self.assertTrue({'main_floor','wall_left','premium_shelf_bay','shopping_basket','cafe_chair','shopping_cart','service_counter','shipping_carton_large'}.issubset({r['asset_id'] for r in p['placements']}))
        self.assertEqual(p['probe_asset']['asset_id'],'unit_axis_probe')
    def test_y_reflection_and_cm_scale(self):
        p=s.transform_record({'position_m':[1,2,3]});self.assertEqual(p['location_cm'],[100,-200,300]);self.assertEqual(p['quaternion_xyzw'],[0,0,0,1])
    def test_z_yaw_reflection(self):
        p=s.transform_record({'position_m':[0,0,0],'rotation_euler_deg':[0,0,90]});self.assertAlmostEqual(p['quaternion_xyzw'][2],-math.sqrt(.5));self.assertAlmostEqual(p['quaternion_xyzw'][3],math.sqrt(.5))
    def test_light_local_positive_x_points_down(self):
        q=s.transform_record({'position_m':[0,0,0]},light=True)['quaternion_xyzw'];x,y,z,w=q
        rotated_x=[1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w)]
        self.assertTrue(all(abs(a-b)<1e-8 for a,b in zip(rotated_x,[0,0,-1])))
    def test_negative_and_sheared_matrices_rejected(self):
        for m in [[[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],[[1,.5,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]]:
            with self.assertRaises(ValueError):s.transform_record({'source_world_matrix_m':m})
    def test_nonfinite_transform_rejected(self):
        with self.assertRaises(ValueError):s.transform_record({'position_m':[0,float('nan'),0]})
    def test_bounds_preserve_offcentre_pivot(self):
        a=copy.deepcopy(self.contract['manifest']['assets'][0]);a['objects'][0].update(bounds_min_m=[1,2,3],bounds_max_m=[4,5,6])
        self.assertEqual(s.expected_bounds(a),{'min_cm':[100,-500,300],'max_cm':[400,-200,600]})
    def test_fbx_changed_bytes_rejected(self):
        a=self.contract['manifest']['assets'][0];(self.root/'export'/a['fbx']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):s.load_package(self.root)
    def test_approved_v1_lineage_rejected(self):
        self.modify_export(lambda d:d['source_lineage'].update(approved_source_sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'v3 source'):s.load_package(self.root)
    def test_path_escape_rejected(self):
        for rel in ['../escape','/tmp/file','C:/Art/file','fbx\\file']:
            with self.assertRaises(ValueError):s.safe_file(self.root,rel)
    def test_duplicate_and_missing_prop_tag_rejected(self):
        self.modify_export(lambda d:d['placements'][0].update(stable_id=d['placements'][1]['stable_id']))
        with self.assertRaisesRegex(ValueError,'Duplicate'):s.load_package(self.root)
    def test_eligible_prop_tag_required(self):
        self.modify_export(lambda d:next(p for p in d['placements'] if p['eligible']).update(tags=[]))
        with self.assertRaisesRegex(ValueError,'Prop tag'):s.load_package(self.root)
    def test_ism_placement_rejected(self):
        self.modify_export(lambda d:d['placements'][0].update(intended_unreal_actor_class='InstancedStaticMeshActor'))
        with self.assertRaisesRegex(ValueError,'StaticMeshActor'):s.load_package(self.root)
    def test_sun_and_missing_fixture_rejected(self):
        self.modify_export(lambda d:d['lights'][0].update(type='SUN'))
        with self.assertRaisesRegex(ValueError,'directional'):s.load_package(self.root)
    def test_overwrite_destination_namespace_rejected(self):
        for name in ['/Game','/Game/Existing','/Game/PremiumStoreV3/Test','/Game/PremiumStoreV3/../Test_v1']:
            with self.assertRaises(ValueError):s.destination_guard(name)
    def test_dryrun_report_cannot_overwrite(self):
        out=self.root/'plan.json';s.dry_run(self.root,output=out)
        with self.assertRaises(FileExistsError):s.dry_run(self.root,output=out)
    def test_full_requires_manual_gate_before_ue_access(self):
        with self.assertRaisesRegex(ValueError,'sample approval'):s.run(self.root,phase='full',ue=object())
    def test_version_guard_rejects_other_versions_before_mutation(self):
        for version in ['5.7.4','5.9.0','4.27.2','unknown']:
            ue=SimpleNamespace(SystemLibrary=SimpleNamespace(get_engine_version=lambda:version))
            with self.assertRaisesRegex(ValueError,'requires Unreal 5.8'):s._guard_api(ue,s.build_plan(self.contract))
    def test_missing_api_stops_before_mutation(self):
        ue=SimpleNamespace(SystemLibrary=SimpleNamespace(get_engine_version=lambda:'5.8.1'))
        with self.assertRaisesRegex(ValueError,'Required API class missing'):s._guard_api(ue,s.build_plan(self.contract))
    def test_existing_engine_destination_rejected(self):
        ue=SimpleNamespace(EditorAssetLibrary=SimpleNamespace(does_directory_exist=lambda p:True))
        with self.assertRaisesRegex(ValueError,'Existing destination'):s._fresh_destination(ue,s.build_plan(self.contract))
    def test_dirty_map_refuses_switch(self):
        lib=SimpleNamespace(does_directory_exist=lambda p:False,list_assets=lambda *a,**kw:[],does_asset_exist=lambda p:False)
        ue=SimpleNamespace(EditorAssetLibrary=lib,EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_map_packages=lambda:['dirty']))
        with self.assertRaisesRegex(ValueError,'dirty maps'):s._fresh_destination(ue,s.build_plan(self.contract))
    def test_spawn_each_copy_independently_shared_mesh(self):
        ue=fake_spawn_ue();actors=Actors();a=self.contract['assets']['crushed_tomatoes'];mesh=Obj('/Shared/Can')
        rows=[p for p in self.contract['manifest']['placements'] if p['asset_id']=='crushed_tomatoes']
        for p in rows:s._spawn_mesh(ue,actors,a,mesh,p,s.transform_record(p),'sample')
        self.assertEqual(len(actors.actors),3);self.assertEqual(len({id(x) for x in actors.actors}),3)
        for actor in actors.actors:
            self.assertIn('Prop',actor.props['tags']);self.assertIs(actor.props['static_mesh_component'].props['static_mesh'],mesh)
    def test_physical_blockers_keep_pawn_and_visibility_block(self):
        ue=fake_spawn_ue();actors=Actors();a=self.contract['assets']['main_floor'];p=self.contract['manifest']['placements'][0]
        actor=s._spawn_mesh(ue,actors,a,Obj(),p,s.transform_record(p),'sample');c=actor.props['static_mesh_component']
        self.assertEqual(c.enabled,'both');self.assertEqual(c.responses,{'visibility':'block','pawn':'block'});self.assertEqual(c.profile,'BlockAll')
    def test_declared_nonblocking_context_stays_no_collision(self):
        ue=fake_spawn_ue();actors=Actors();a=self.contract['assets']['visual_context'];p=next(p for p in self.contract['manifest']['placements'] if p['asset_id']=='visual_context')
        actor=s._spawn_mesh(ue,actors,a,Obj(),p,s.transform_record(p),'sample');c=actor.props['static_mesh_component']
        self.assertEqual(c.enabled,'none');self.assertNotIn('Prop',actor.props['tags'])
    def test_reload_transform_detects_corruption(self):
        p={'location_cm':[1,2,3],'quaternion_xyzw':[0,0,0,1],'scale':[1,1,1]};actual=s._ue_transform(fake_spawn_ue(),p)
        s._check_transform(actual,p,'test');actual.translation.y=999
        with self.assertRaisesRegex(ValueError,'location mismatch'):s._check_transform(actual,p,'test')
    def sample_report(self):
        p=self.root/'SAMPLE_REPORT.json';r=dict(schema=s.SCHEMA+'-report',status='SAVED_RELOADED_PENDING_MANUAL_REVIEW',phase='sample',
            after_reload={'status':'PASS_STRUCTURAL_CHECKS_ONLY'},package_root=str(self.root),package_fingerprint=self.contract['fingerprint'],
            actual_unreal_run=True,editor_process_id=123,engine_version='5.8.1',success_token='offline_fake_token_1234567890')
        s.write(p,r);s.write(p.with_name('COLD_REOPEN_VERIFICATION.json'),dict(schema=s.SCHEMA+'-cold-reopen',status='PASS',actual_unreal_run=True,sample_report_sha256=s.sha(p),package_fingerprint=self.contract['fingerprint'],editor_process_id=456));return p
    def test_approval_requires_all_explicit_checks(self):
        with self.assertRaisesRegex(ValueError,'Every manual check'):s.approve_sample(self.sample_report(),{},'I reviewed the v3 sample in Unreal 5.8 and approve the full import')
    def test_exact_approval_phrase_required(self):
        with self.assertRaisesRegex(ValueError,'Exact manual'):s.approve_sample(self.sample_report(),{k:True for k in s.REVIEW_CHECKS},'yes')
    def test_gate_binds_report_token_and_package(self):
        report=self.sample_report();approval=s.approve_sample(report,{k:True for k in s.REVIEW_CHECKS},'I reviewed the v3 sample in Unreal 5.8 and approve the full import')
        s._validate_approval(self.contract,approval['approval_file'],approval['success_token'])
        with self.assertRaisesRegex(ValueError,'token mismatch'):s._validate_approval(self.contract,approval['approval_file'],'bad')
        report.write_text(report.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'modified'):s._validate_approval(self.contract,approval['approval_file'],approval['success_token'])
    def test_gate_rejects_changed_package(self):
        report=self.sample_report();approval=s.approve_sample(report,{k:True for k in s.REVIEW_CHECKS},'I reviewed the v3 sample in Unreal 5.8 and approve the full import')
        c=dict(self.contract,fingerprint='new')
        with self.assertRaisesRegex(ValueError,'changed after sample'):s._validate_approval(c,approval['approval_file'],approval['success_token'])
    def test_fixture_policy_is_explicitly_uncalibrated(self):
        p=s.build_plan(self.contract);self.assertEqual(len(p['lights']),67);self.assertEqual(p['light_policy']['lumens_per_blender_watt'],10);self.assertIn('UNCALIBRATED',p['light_policy']['status'])


    def test_sign_assembly_and_tree_in_sample(self):
        p=s.build_plan(self.contract);names={r['object_name'] for r in p['placements']}
        self.assertTrue({'SIGN 01  BREAKFAST','V3_Sign_backing_01','V3_Sign_hanger_01_0'}.issubset(names))
        self.assertTrue(any('pine_tall_v3_variant_' in r['asset_id'] for r in p['placements']))
    def test_failed_roundtrip_rejected(self):
        path=self.root/'export/FBX_ROUNDTRIP_VALIDATION.json';d=s.read(path);d['status']='FAIL';s.write(path,d)
        with self.assertRaisesRegex(ValueError,'did not pass'):s.load_package(self.root)
    def test_roundtrip_row_digest_mismatch_rejected(self):
        path=self.root/'export/FBX_ROUNDTRIP_VALIDATION.json';d=s.read(path);d['results'][0]['fbx_sha256']='wrong';s.write(path,d)
        with self.assertRaisesRegex(ValueError,'FBX evidence'):s.load_package(self.root)
    def test_cold_restart_evidence_required(self):
        path=self.sample_report();path.with_name('COLD_REOPEN_VERIFICATION.json').unlink()
        with self.assertRaisesRegex(ValueError,'Restart Unreal'):s.approve_sample(path,{k:True for k in s.REVIEW_CHECKS},'I reviewed the v3 sample in Unreal 5.8 and approve the full import')
    def test_same_editor_process_cannot_claim_cold_restart(self):
        path=self.sample_report();d=s.read(path);d['editor_process_id']=s.os.getpid();s.write(path,d)
        with self.assertRaisesRegex(ValueError,'Close and restart'):s.verify_after_editor_restart(path,ue=object())


    def test_boundary_uses_full_dimensions_not_empty_halfscale(self):
        rec=dict(centre_m=[32,-.06,2.35],dimensions_m=[64,.12,4.7],source_world_matrix_m=[[32,0,0,32],[0,.06,0,-.06],[0,0,2.35,2.35],[0,0,0,1]])
        data=s._boundary_transform(rec);self.assertEqual(data['scale'],[64,.12,4.7]);self.assertEqual(data['location_cm'],[3200,6,235])
    def test_boundary_actor_is_hidden_nonprop_physical_pawn_only_for_trace(self):
        ue=fake_spawn_ue();actors=Actors();plan=s.build_plan(self.contract);cube=Obj('/Engine/BasicShapes/Cube')
        with patch.object(s,'_boundary_cube',return_value=cube):s._spawn_boundaries(ue,actors,plan)
        actor=actors.actors[0];c=actor.props['static_mesh_component'];self.assertNotIn('Prop',actor.props['tags'])
        self.assertEqual(c.enabled,'both');self.assertEqual(c.responses,{'pawn':'block','visibility':'ignore'})
        self.assertTrue(actor.props['hidden']);self.assertFalse(c.props['visible']);self.assertFalse(c.props['cast_shadow']);self.assertIs(c.props['static_mesh'],cube)
    def test_spawn_markers_become_actual_playerstarts(self):
        ue=fake_spawn_ue();ue.PlayerStart=type('PlayerStart',(Actor,),{});ue.TargetPoint=type('TargetPoint',(Actor,),{});actors=Actors()
        s._spawn_markers(ue,actors,s.build_plan(self.contract))
        self.assertEqual(sum(isinstance(a,ue.PlayerStart) for a in actors.actors),1);self.assertEqual(sum(isinstance(a,ue.TargetPoint) for a in actors.actors),1)
    def test_boundary_policy_preserves_source_metadata(self):
        plan=s.build_plan(self.contract);self.assertTrue(plan['boundary_policy']['runtime_barriers_enabled']);self.assertFalse(plan['scene_support']['boundaries'][0]['duplicate_blocker_creation'])


    def mesh_fixture(self,uv=1,simple=0,extra_shape=False):
        asset=copy.deepcopy(self.contract['assets']['main_floor'])
        class Mesh(Obj):
            def get_bounds(self):return SimpleNamespace(origin=Vec(50,-100,150),box_extent=Vec(50,100,150))
            def get_num_triangles(self,lod):return 12
        mesh=Mesh('/Game/Test/Mesh');slot=Obj();slot.props['imported_material_slot_name']='Mat';mesh.props['static_materials']=[slot]
        agg=Obj();agg.props={k:[] for k in ['box_elems','sphere_elems','sphyl_elems','tapered_capsule_elems','level_set_elems','ml_level_set_elems','skinned_level_set_elems','skinned_triangle_mesh_elems']};agg.props['convex_elems']=[object()]
        if extra_shape:agg.props['box_elems']=[object()]
        body=Obj();body.props['agg_geom']=agg;mesh.props['body_setup']=body
        ss=SimpleNamespace(get_simple_collision_count=lambda m:simple,get_convex_collision_count=lambda m:1,get_num_uv_channels=lambda m,lod:uv)
        ue=SimpleNamespace(StaticMesh=Mesh,StaticMeshEditorSubsystem=object,get_editor_subsystem=lambda cls:ss)
        return ue,mesh,asset
    def test_simple_count_not_assumed_to_include_convex(self):
        ue,mesh,asset=self.mesh_fixture(simple=0);r=s._mesh_check(ue,mesh,asset);self.assertEqual(r['convex_collision_count'],1);self.assertEqual(r['simple_collision_count'],0)
    def test_untextured_uvless_mesh_can_have_blank_uv0(self):
        ue,mesh,asset=self.mesh_fixture();asset['objects'][0]['uv_layers']=[]
        self.assertTrue(s._mesh_check(ue,mesh,asset)['untextured_blank_uv0_fallback'])
        asset['image_uv_bindings']=[{'image':'something.png'}]
        with self.assertRaisesRegex(ValueError,'UV channel count'):s._mesh_check(ue,mesh,asset)
    def test_extra_simple_collision_shape_is_rejected(self):
        ue,mesh,asset=self.mesh_fixture(extra_shape=True)
        with self.assertRaisesRegex(ValueError,'non-UCX'):s._mesh_check(ue,mesh,asset)


    def test_sign_hardware_numeric_index_matches_zero_padded_board(self):
        c=copy.deepcopy(self.contract)
        next(p for p in c['manifest']['placements'] if p.get('object_name')=='V3_Sign_hanger_01_0')['object_name']='V3_Sign_hanger_1_0'
        self.assertTrue(any(p.get('object_name')=='V3_Sign_hanger_1_0' for p in s.sample_placements(c)))


class MaterialTests(unittest.TestCase):
    def test_exact_led_policy_retains_pbr_plus_emission(self):
        m=material('EXT2_Warm_LED');m['channels']['Emission Strength']['value']=4;m['channels']['Emission Color']['value']=[1,.72,.37,1]
        channels,errors=b.inspect_material(m);self.assertFalse(errors);self.assertEqual(channels['Emissive']['value'],[4,2.88,1.48,1]);self.assertIn('Base Color',channels);self.assertIn('Roughness',channels)
    def test_unknown_led_or_changed_signature_rejected(self):
        m=material('EXT2_Warm_LED');m['channels']['Emission Strength']['value']=4;m['channels']['Emission Color']['value']=[1,.72,.37,1]
        for name,strength in [('EXT2_Warm_LED.001',4),('EXT2_Warm_LED',5)]:
            x=copy.deepcopy(m);x['material']=name;x['channels']['Emission Strength']['value']=strength;self.assertTrue(b.inspect_material(x)[1])
    def test_unknown_procedural_and_transmission_rejected(self):
        m=material();m['procedural']=True;self.assertTrue(b.inspect_material(m)[1]);m['procedural']=False;m['channels']['Transmission Weight']['value']=1;self.assertTrue(b.inspect_material(m)[1])
    def test_unsupported_alpha_rejected(self):
        m=material();m['channels']['Alpha']['value']=.5;self.assertTrue(b.inspect_material(m)[1])
    def test_normal_alpha_rejected(self):
        m=material();m['node_graph'].append(dict(name='Normal',type='NORMAL_MAP',normal_space='TANGENT',normal_strength_linked=False,normal_strength=1,uv_map='UVMap'))
        m['images']=[dict(name='normal.png',node='Image',projection='FLAT',extension='REPEAT',interpolation='Linear')]
        m['links']=[dict(from_node='Normal',from_socket='Normal',to_node='P',to_socket='Normal'),dict(from_node='Image',from_socket='Alpha',to_node='Normal',to_socket='Color')]
        self.assertTrue(any('never alpha' in e for e in b.inspect_material(m)[1]))

if __name__=='__main__':unittest.main(verbosity=2)
