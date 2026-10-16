"""Controlled original-placement prop expansion; dry-run default, no Blueprint edits."""
import copy
import importlib.util
import json
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone
TAG='EvergreenPropBatchV1'
SCHEMA='evergreen-prop-batch-v1'
APPROVED_IDS=('EGI_0f8d6343f4f54f9d', 'EGI_5451cd109bab56e9', 'EGI_01eca130f35d655e', 'EGI_7ff75102d10dd13b', 'EGI_4c0fd92658e86b28', 'EGI_3ba9a0d6328c5647', 'EGI_3013a88f914ebc03', 'EGI_869f7db65feb4ccd', 'EGI_33de12349a45541a', 'EGI_9dfa86a010edad0a', 'EGI_b74ac46863b43864', 'EGI_4c207ecbd1ac569b', 'EGI_4fb051d8175da0d7', 'EGI_18fc8f491c214f5f', 'EGI_40290a2b7eaefcbc', 'EGI_9ca5fc6b0e622d49')
DEFAULT_STATE=r'C:\Art\Evergreen_Native_Run_01\run_state.json'
DEFAULT_REPORT=r'G:\Games\SheeshhPropHuntYT\Saved\EvergreenHandoff\FixtureLights_20261016_203347_2abafb60\fixture_lights_report.json'
SOURCE='/Game/EvergreenHandoff/Full_20261016_193857_732038/Maps/L_Evergreen_full_WalkTest_20261016_194017_759391fe_PropPilot_20261016_194024_6198d196_Preview_20261016_194032_39fe2769_FixtureLights_20261016_203347_2abafb60'
def check(ok,msg):
    if not ok:raise ValueError(msg)
def support(folder):
    spec=importlib.util.spec_from_file_location('evergreen_batch_fixture_support',Path(folder)/'fixture_support.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def context(f,state_file,report_file):
    ctx=f.verified_context(state_file);report=f.read(report_file)
    check(report.get('schema')=='evergreen-fixture-patch-v1' and report.get('status')=='verified_fixture_lights_persistence','Exact successful fixture report required; no partial reports')
    check(report.get('source_map')==ctx['source_map'] and report.get('target_map')==SOURCE,'Wrong fixture source/target map')
    check(report.get('point_light_count')==42 and len(report.get('lights',[]))==42 and report.get('preserved_actor_state') is True,'Fixture completion/count mismatch')
    for path,digest in ctx['hashes'].items():check(report['protected_hashes'].get(path)==digest,'Fixture/base provenance mismatch: '+path)
    # Layout and other historical artifacts are protected as well; no latest-report search.
    f.unchanged(report['protected_hashes']);ctx['hashes'].update(report['protected_hashes'])
    ctx['hashes'][str(Path(report_file).resolve())]=f.sha(report_file)
    ctx['pilot']=f.remap_pilot(ctx['fp'],ctx['preview'],ctx['source_map'],SOURCE)
    ctx.update(source_map=SOURCE,fixture_report=report);return ctx

def make_plan(ctx,selection,f):
    check(selection.get('schema')=='evergreen-prop-batch-selection-v1','Wrong selection schema')
    check(selection.get('source_manifest_sha256')==f.sha(ctx['contract']['root']/'manifest.json'),'Selection source hash mismatch')
    chosen=selection['selected'];ids=[p['instance_id'] for p in chosen]
    check(len(ids)==16 and len(set(ids))==len(ids),'Expected 16 unique explicit IDs')
    check(set(ids)==set(APPROVED_IDS),'Selection differs from the audited 16-ID batch')
    pilot=copy.deepcopy(ctx['pilot']);scene=pilot['remaining_scene'];lookup={}
    for key,g in scene['groups'].items():
        for row in g['instances']:
            check(row['instance_id'] not in lookup,'Duplicate source ID');lookup[row['instance_id']]=(key,row)
    placements={p['instance_id']:p for p in ctx['contract']['placements']};promoted=[]
    for iid in ids:
        check(iid in lookup,'ID absent from surviving original ISMs: '+iid)
        key,row=lookup[iid];p=placements[iid];asset=ctx['contract']['assets'][p['asset_id']]
        selected=next(r for r in chosen if r['instance_id']==iid)
        check(selected['source_placement']==p and selected['target_placement']==p and selected['asset_name']==asset['name'],'Selection must preserve exact original geometry/type')
        check(asset['category']=='disguise_candidate' and max(abs(s-1) for s in p['scale'])<1e-6,'Not a canonical-scale candidate')
        check(any(word in asset['name'].lower() for word in ('can','carton','bottle','box')),'Outside approved product categories')
        for field in ('asset_id','location_cm','quaternion_xyzw','scale'):check(row[field]==p[field],'Report/source placement mismatch')
        promoted.append(dict(instance_id=iid,asset_id=p['asset_id'],label='Batch_'+asset['name']+'_'+iid,source_group=key,source_index=row['instance_index'],source_placement=copy.deepcopy(p),target_placement=copy.deepcopy(p),mesh_path=scene['groups'][key]['mesh_path'],canonical_bounds_cm=asset['bounds_cm']))
    check(len(lookup)==11312 and len(pilot['promoted'])==4,'Expected 11312 original ISMs plus four pilot actors')
    return dict(source_map=SOURCE,pilot_plan=pilot,promoted=promoted,selected_ids=ids,changed_groups=sorted({p['source_group'] for p in promoted}))

def target_map(stamp):
    check(re.fullmatch(r'[A-Za-z0-9_]+',stamp) is not None,'Invalid target suffix')
    return SOURCE.rsplit('/',1)[0]+'/L_EG_PropBatch_'+stamp

def near(a,b):return a.is_near_equal(b,location_tolerance=0.1,rotation_tolerance=0.001,scale3d_tolerance=0.0001)

def remap_survivors(component,rows,to_transform):
    """Discover actual engine survivor ordering, including remove-at-swap engines."""
    check(component.get_instance_count()==len(rows),'Survivor count mismatch')
    remaining=list(rows);mapped=[]
    for index in range(component.get_instance_count()):
        actual=component.get_instance_transform(index,world_space=True)
        matches=[p for p in remaining if actual is not None and near(actual,to_transform(p))]
        check(len(matches)==1,'Ambiguous/changed survivor transform; do not guess source identity')
        row=matches[0];remaining.remove(row);row['instance_index']=index;mapped.append(row)
    check(not remaining,'Unmapped survivors');return mapped

def remove_selected(component,rows,ids,to_transform):
    removed=sorted([p['instance_index'] for p in rows if p['instance_id'] in ids],reverse=True)
    check(len(removed)==len(set(removed)),'Duplicate removal index')
    component.modify()
    for index in removed:check(component.remove_instance(index) is True,'ISM remove failed at '+str(index))
    survivors=[p for p in rows if p['instance_id'] not in ids]
    return remap_survivors(component,survivors,to_transform),removed

def fixture_identity(u,ctx,f):
    expected={p['key']:p for p in ctx['fixture_report']['lights']};found={}
    for a in ctx['fp']._actors(u):
        tags=[str(t) for t in a.get_editor_property('tags')]
        if f.TAG not in tags:continue
        keys=[t[len(f.PREFIX):] for t in tags if t.startswith(f.PREFIX)]
        check(len(keys)==1 and keys[0] in expected and keys[0] not in found,'Fixture identity mismatch')
        p=expected[keys[0]];check(a.get_class()==u.PointLight.static_class() and 'EMSourceFixture='+p['source_fixture_instance_id'] in tags,'Fixture class/source mismatch')
        found[keys[0]]=a.get_name()
    check(len(found)==42,'Expected exactly 42 fixture points')

def mesh_snapshot(u,ctx,f):
    current=ctx['fp']._current(u);out={}
    for a in ctx['fp']._actors(u):
        if TAG in [str(t) for t in a.get_editor_property('tags')]:continue
        for c in a.get_components_by_class(u.StaticMeshComponent):
            path=f.normalized_path(c.get_path_name(),current)
            mesh=c.get_editor_property('static_mesh')
            out[path]=dict(mesh=f.scalar(mesh,current),materials=[f.scalar(c.get_material(i),current) for i in range(c.get_num_materials())],transform=ctx['fp']._transform_data(c.get_world_transform()),collision=ctx['ep']._pilot_collision_state(u,c),object_type=str(c.get_collision_object_type()),mobility=str(c.get_editor_property('mobility')),physics=c.is_simulating_physics(),overlap=c.get_editor_property('generate_overlap_events'),navigation=c.get_editor_property('can_ever_affect_navigation'))
    return out

def batch_actors(u,ctx):return [a for a in ctx['fp']._actors(u) if TAG in [str(t) for t in a.get_editor_property('tags')]]

def spawn(u,ctx,p):
    # Proven spawn/configuration, immediately replace pilot identity before verification.
    a=ctx['ep']._spawn(u,p,u.load_asset(p['mesh_path']))
    a.set_actor_label('EM_BATCH_'+p['label']);a.set_editor_property('tags',['Prop',TAG,'EMSource='+p['instance_id']]);return a

def verify(u,ctx,plan,f,before,meshes):
    pilot=plan['pilot_plan'];ctx['ep'].verify(u,pilot);ctx['ec']._check_original_collision(u,ctx['contract'])
    actors=batch_actors(u,ctx);expected={p['instance_id']:p for p in plan['promoted']};seen=set()
    for a in actors:
        tags=[str(t) for t in a.get_editor_property('tags')];ids=[t[9:] for t in tags if t.startswith('EMSource=')]
        check(len(ids)==1 and ids[0] in expected and ids[0] not in seen,'Batch source identity mismatch');iid=ids[0];seen.add(iid);p=expected[iid]
        check(a.get_class()==u.StaticMeshActor.static_class() and set(tags)=={'Prop',TAG,'EMSource='+iid} and a.get_actor_label()=='EM_BATCH_'+p['label'],'Batch class/label/tags mismatch')
        c=a.get_editor_property('static_mesh_component');ep=ctx['ep']
        check(a.get_path_name()==p['actor_path'] and c.get_editor_property('static_mesh').get_path_name()==p['mesh_path'],'Batch identity/mesh mismatch')
        check(near(c.get_world_transform(),ctx['em']._transform(u,p['target_placement'])),'Batch full-world-transform mismatch')
        ep._check_pilot_collision(u,c)
        check(c.get_collision_object_type()==u.CollisionChannel.ECC_WORLD_STATIC and c.get_editor_property('mobility')==u.ComponentMobility.STATIC and not c.is_simulating_physics(),'Batch physics/mobility mismatch')
        check(not c.get_editor_property('generate_overlap_events') and not c.get_editor_property('can_ever_affect_navigation'),'Batch overlap/navigation mismatch')
        check(not a.get_editor_property('replicates') and not a.get_editor_property('replicate_movement') and not a.get_editor_property('static_mesh_replicate_movement'),'Batch replication mismatch')
        check(ep._material_contract(c)==p['canonical_materials'],'Batch material mismatch')
    check(seen==set(expected),'Batch actor count mismatch')
    fixture_identity(u,ctx,f)
    check(f.snapshot(u,ctx,{a.get_name() for a in actors})==before,'Existing actors/lights/manual tuning changed')
    check(mesh_snapshot(u,ctx,f)==meshes,'Existing mesh/material/collision/component state changed')
    remaining=[p['instance_id'] for g in pilot['remaining_scene']['groups'].values() for p in g['instances']]
    old={p['instance_id'] for p in pilot['promoted']}
    check(len(remaining)==11312-len(expected) and not set(remaining)&(set(expected)|old) and len(remaining)+len(old)+len(expected)==11316,'Source total/duplicate visual mismatch')
    return dict(remaining_ism_instances=len(remaining),old_pilot_actors=4,new_prop_actors=len(expected),combined_original_placements=11316,fixture_points=42,collision_boxes=694)

def run(folder,state_file=DEFAULT_STATE,fixture_report=DEFAULT_REPORT,*,execute=False,backup_confirmed=False):
    folder=Path(folder).resolve();f=support(folder);ctx=context(f,state_file,fixture_report)
    selection_file=folder/'prop_batch_selection_v1.json';plan=make_plan(ctx,f.read(selection_file),f)
    for file in ('prop_batch_patch.py','fixture_support.py','prop_batch_selection_v1.json'):ctx['hashes'][str(folder/file)]=f.sha(folder/file)
    import unreal as u
    f.clean(u);check(ctx['fp']._current(u)==SOURCE,'Open exact successful FixtureLights map; never rerun a partial/batched map')
    check(not batch_actors(u,ctx),'Batch already present; stop')
    check(hasattr(u.InstancedStaticMeshComponent,'remove_instance'),'Required official remove_instance API missing')
    ctx['ep'].verify(u,ctx['pilot']);ctx['ec']._check_original_collision(u,ctx['contract']);fixture_identity(u,ctx,f)
    groups=ctx['ep']._groups(u)
    for key in plan['changed_groups']:
        c=groups[key];check(c.get_editor_property('num_custom_data_floats')==0,'Per-instance custom data is unsupported')
        ctx['ep']._material_contract(c)
        check(u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_simple_collision_count(c.get_editor_property('static_mesh'))>0,'Selected mesh lacks simple query collision')
        transforms=[ctx['em']._transform(u,p) for p in ctx['pilot']['remaining_scene']['groups'][key]['instances']]
        check(all(not near(a,b) for i,a in enumerate(transforms) for b in transforms[i+1:]),'Ambiguous duplicate source transforms in affected group')
    before=f.snapshot(u,ctx,set());meshes=mesh_snapshot(u,ctx,f)
    result=dict(schema=SCHEMA,status='dry_run',source_map=SOURCE,protected_hashes=ctx['hashes'],plan=plan,new_prop_count=len(plan['promoted']),preserved_actor_snapshot=before,preserved_mesh_snapshot=meshes,gameplay_verified=False,blueprint_modified=False,unreal_runtime_previously_tested=False)
    if not execute:
        summary=dict(status='dry_run_no_changes',source_map=SOURCE,target_prefix=target_map('UNIQUE'),new_prop_count=len(plan['promoted']),remaining_ism_instances=11312-len(plan['promoted']),total_loose_props=4+len(plan['promoted']),preserved_fixture_points=42,preserved_collision_boxes=694,selected=[dict(id=p['instance_id'],label=p['label'],xyz_cm=p['target_placement']['location_cm']) for p in plan['promoted']],caveat='Original placements retained. Shelf/pallet collision may occlude interaction; E and disguise fit require PIE testing. No Blueprint changes.')
        print(json.dumps(summary,indent=2));return result
    check(backup_confirmed is True,'Save and back up project; pass backup_confirmed=True')
    f.clean(u);f.unchanged(ctx['hashes'])
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8];target=target_map(stamp)
    check(not (Path(u.Paths.project_content_dir()).resolve()/(target[6:]+'.umap')).exists(),'Destination exists')
    output=Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff'/('PropBatch_'+stamp);output.mkdir(parents=True,exist_ok=False)
    report=output/'prop_batch_report.json';result.update(status='started',target_map=target)
    def save():report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    save();level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    try:
        check(level.new_level_from_template(target,SOURCE),'Map copy failed');check(ctx['fp']._current(u)==target,'Wrong copied map')
        wrapped=dict(source_map=SOURCE,pilot_plan=plan['pilot_plan']);plan['pilot_plan']=ctx['fp']._copy_pilot_plan(wrapped,target)['pilot_plan']
        ctx['ep'].verify(u,plan['pilot_plan']);fixture_identity(u,ctx,f)
        check(f.snapshot(u,ctx,set())==before and mesh_snapshot(u,ctx,f)==meshes,'Copy changed source actors/settings')
        groups=ctx['ep']._groups(u)
        for p in plan['promoted']:spawn(u,ctx,p)
        plan['removed_indices_descending']={}
        for key in plan['changed_groups']:
            group=plan['pilot_plan']['remaining_scene']['groups'][key]
            group['instances'],removed=remove_selected(groups[key],group['instances'],set(plan['selected_ids']),lambda p:ctx['em']._transform(u,p))
            plan['removed_indices_descending'][key]=removed
        plan['pilot_plan']['remaining_scene']['placement_count']=11312-len(plan['promoted'])
        result['before_save']=verify(u,ctx,plan,f,before,meshes);f.unchanged(ctx['hashes'])
        check(level.save_current_level(),'Map save failed');f.clean(u)
        check(level.load_level(target),'Map reload failed');check(ctx['fp']._current(u)==target,'Wrong reloaded map')
        result['after_reload']=verify(u,ctx,plan,f,before,meshes);f.unchanged(ctx['hashes'])
        lookup=copy.deepcopy(plan['pilot_plan']);lookup['promoted']+=plan['promoted'];ctx['ep']._write_lookup(output/'instance_lookup_prop_batch.csv',lookup)
        result.update(status='verified_prop_batch_persistence',lookup_csv=str(output/'instance_lookup_prop_batch.csv'));save()
        u.log('Prop batch persisted. E/Blueprint gameplay still needs user testing. Report: '+str(report));return str(report)
    except Exception as exc:
        result.update(status='failed_partial_prop_batch',error=str(exc));save()
        u.log_error('STOP. Do not rerun, edit reports, or discard changes. Inspect partial map/report: '+str(report));raise
