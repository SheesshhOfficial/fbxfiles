"""Conservative corrected-FBX replacement on a NEW copy of a successful pilot map.
Dry-run default. UE 5.7 APIs; actual Unreal execution is not validated here.
Original maps/assets/Blueprints are never edited. Save manual changes first.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import math
import re
import uuid
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep

SCHEMA = 'evergreen-normals-patch-report-v1'
PATCH_SCHEMA = 'evergreen-closed-shell-winding-v1'
SAMPLE_NAMES = {'ShippingCarton_Floor', 'Checkout base'}
check = em._require


def load_patch(contract, patch_root):
    root = Path(patch_root).expanduser().resolve()
    path = em._path(root, 'patch_manifest.json', '.json')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    check(manifest.get('schema') == PATCH_SCHEMA, 'Unsupported normals patch schema')
    check(manifest.get('original_manifest_sha256') == em._sha(contract['root'] / 'manifest.json'),
          'Patch targets a different original manifest')
    records = manifest.get('assets', [])
    check(isinstance(records, list) and records, 'Empty patch')
    assets, hashes = {}, {'patch_manifest.json': em._sha(path)}
    for row in records:
        aid = row['asset_id']
        check(aid in contract['assets'] and aid not in assets, 'Unknown/duplicate patched asset: ' + aid)
        old = contract['assets'][aid]
        check(row.get('name') == old['name'], 'Patch name mismatch: ' + aid)
        check(row.get('original_file_sha256') == old['file_sha256'], 'Original FBX hash mismatch: ' + aid)
        check(row.get('materials') == old['materials'], 'Patch material order changed: ' + aid)
        em._numbers(row.get('bounds_cm'), 3, aid + '.bounds_cm', positive=True)
        check(all(abs(a-b) <= 0.01 for a,b in zip(row['bounds_cm'],old['bounds_cm'])), 'Patch bounds changed: ' + aid)
        fbx = em._path(root,row['fbx_path'],'.fbx')
        digest = em._sha(fbx)
        check(digest == row.get('file_sha256'), 'Corrected FBX hash mismatch: ' + aid)
        hashes[row['fbx_path']] = digest
        assets[aid] = dict(row, resolved_path=str(fbx))
    fingerprint = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    return {'root':str(root),'assets':assets,'fingerprint':fingerprint}


def make_plan(contract, patch, full, pilot, phase, sample_report=None, visual_review_approved=False):
    check(phase in ('sample','full'), 'phase must be sample or full')
    original = ec.validate_report(contract,full)
    check(pilot.get('schema') == 'evergreen-prop-actor-pilot-v1'
          and pilot.get('status') == 'verified_pilot_persistence', 'Successful prop pilot report required')
    check(pilot.get('package_fingerprint') == contract['fingerprint'], 'Pilot package mismatch')
    source = pilot.get('target_map','')
    check(re.fullmatch(re.escape(original) + r'_WalkTest_[A-Za-z0-9_]+_PropPilot_[A-Za-z0-9_]+',source),
          'Expected successful original pilot/recovery map')
    sample = sorted(aid for aid,a in patch['assets'].items() if a['name'] in SAMPLE_NAMES)
    check(len(sample)==2 and {patch['assets'][a]['name'] for a in sample}==SAMPLE_NAMES,
          'Patch must contain both diagnostic sample meshes')
    if phase == 'full':
        prior = sample_report or {}
        check(visual_review_approved is True, 'Review the sample in Lit mode first; visual_review_approved=True required')
        check(prior.get('schema')==SCHEMA and prior.get('phase')=='sample'
              and prior.get('status')=='verified_persistence', 'Successful sample patch report required')
        check(prior.get('patch_fingerprint')==patch['fingerprint']
              and prior.get('package_fingerprint')==contract['fingerprint']
              and prior.get('source_map')==source
              and prior.get('selected_asset_ids')==sample, 'Sample report does not match this patch/source')
    selected = sample if phase=='sample' else sorted(patch['assets'])
    paths = {aid:full['meshes'][aid]['path'] for aid in selected}
    check(len(set(paths.values()))==len(paths),'Duplicate original mesh paths')
    return {'source_map':source,'phase':phase,'selected_asset_ids':selected,'original_mesh_paths':paths,
            'patch_fingerprint':patch['fingerprint'],'package_fingerprint':contract['fingerprint']}


def _path(obj):
    return obj.get_path_name() if obj is not None else None


def _transform_data(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]


def _channels(u):
    names = ['ECC_WORLD_STATIC','ECC_WORLD_DYNAMIC','ECC_PAWN','ECC_VISIBILITY','ECC_CAMERA',
             'ECC_PHYSICS_BODY','ECC_VEHICLE','ECC_DESTRUCTIBLE']
    names += ['ECC_ENGINE_TRACE_CHANNEL'+str(i) for i in range(1,7)]
    names += ['ECC_GAME_TRACE_CHANNEL'+str(i) for i in range(1,19)]
    return [(n,getattr(u.CollisionChannel,n)) for n in names if hasattr(u.CollisionChannel,n)]


def snapshot(u):
    """Track all actor identities/poses, all SMCs and every ISM instance, no mutation."""
    actors = {}
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        name=actor.get_name()
        check(name not in actors,'Duplicate actor name')
        row={'class':_path(actor.get_class()),'label':actor.get_actor_label(),
             'transform':_transform_data(actor.get_actor_transform()),
             'tags':[str(t) for t in actor.get_editor_property('tags')],'components':{}}
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            record={'class':_path(c.get_class()),'mesh':_path(c.get_editor_property('static_mesh')),
                    'transform':_transform_data(c.get_world_transform()),
                    'materials':[_path(c.get_material(i)) for i in range(c.get_num_materials())],
                    'overrides':[_path(m) for m in c.get_editor_property('override_materials')],
                    'tags':[str(t) for t in c.get_editor_property('component_tags')],
                    'collision_enabled':str(c.get_collision_enabled()),
                    'object_type':str(c.get_collision_object_type()),
                    'responses':{n:str(c.get_collision_response_to_channel(v)) for n,v in _channels(u)},
                    'mobility':str(c.get_editor_property('mobility')),
                    'physics':c.is_simulating_physics(),
                    'overlaps':c.get_editor_property('generate_overlap_events'),
                    'navigation':c.get_editor_property('can_ever_affect_navigation')}
            if isinstance(c,u.InstancedStaticMeshComponent):
                record['instances']=[_transform_data(c.get_instance_transform(i,world_space=True))
                                     for i in range(c.get_instance_count())]
                record['custom_data_floats']=c.get_editor_property('num_custom_data_floats')
            row['components'][c.get_name()]=record
        actors[name]=row
    return actors


def compare(expected, actual, path='scene'):
    if isinstance(expected,dict):
        check(isinstance(actual,dict) and set(actual)==set(expected),'Membership mismatch: '+path)
        for k in expected: compare(expected[k],actual[k],path+'.'+str(k))
    elif isinstance(expected,list):
        check(isinstance(actual,list) and len(actual)==len(expected),'Length mismatch: '+path)
        for i,(a,b) in enumerate(zip(expected,actual)): compare(a,b,path+'['+str(i)+']')
    elif isinstance(expected,float):
        check(isinstance(actual,(int,float)) and math.isclose(expected,actual,rel_tol=1e-7,abs_tol=0.001),
              'Numeric mismatch: '+path)
    else: check(expected==actual,'Value mismatch: '+path)


def remap_snapshot(before, replacements):
    result=copy.deepcopy(before)
    for a in result.values():
        for c in a['components'].values():
            c['mesh']=replacements.get(c['mesh'],c['mesh'])
    return result


def _source_identity(u,pilot,contract):
    """Allow manually moved actors/instances; reject changed membership or source meshes."""
    prior=pilot['plan']; groups=ep._groups(u)
    expected=prior['remaining_scene']['groups']
    check(set(groups)==set(expected),'Original ISM group membership changed')
    for key,record in expected.items():
        c=groups[key]
        check(c.get_instance_count()==len(record['instances']) and _path(c.get_editor_property('static_mesh'))==record['mesh_path'],
              'Original ISM count/mesh changed: '+key)
    pilots=ep._pilot_actors(u); wanted={p['instance_id']:p for p in prior['promoted']}; found=set()
    for a in pilots:
        tags=[str(t) for t in a.get_editor_property('tags')]
        ids=[t[len('EMSource='):] for t in tags if t.startswith('EMSource=')]
        check(isinstance(a,u.StaticMeshActor) and 'Prop' in tags and len(ids)==1 and ids[0] in wanted and ids[0] not in found,
              'Pilot identity changed')
        found.add(ids[0]); c=a.get_editor_property('static_mesh_component')
        check(_path(c.get_editor_property('static_mesh'))==wanted[ids[0]]['mesh_path'],'Pilot mesh changed')
    check(found==set(wanted),'Pilot actor membership changed')
    ec.verify(u,ec.make_plan(contract))


def _materials(mesh):
    slots=mesh.get_editor_property('static_materials')
    names=[str(s.get_editor_property('material_slot_name')) for s in slots]
    mats=[mesh.get_material(i) for i in range(len(slots))]
    check(len(names)==len(set(names)) and all(m is not None for m in mats),'Invalid source material slots')
    return names,mats


def _api(u):
    ec._api(u)
    for owner,methods in ((u.StaticMeshComponent,('set_static_mesh','get_num_materials','get_material','is_simulating_physics','modify')),
                          (u.Actor,('get_actor_transform','get_actor_label','get_name')),
                          (u.InstancedStaticMeshComponent,('get_instance_count','get_instance_transform'))):
        for method in methods: check(hasattr(owner,method),'Missing API: '+owner.__name__+'.'+method)
    check(not u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX'),
          'Legacy FBX options required: set Interchange.FeatureFlags.Import.FBX 0, then retry')


def run(package_root, patch_root, full_import_report, prop_pilot_report, *, phase='sample', execute=False,
        backup_confirmed=False, sample_report=None, visual_review_approved=False):
    contract=em.load_contract(package_root); patch=load_patch(contract,patch_root)
    full=json.loads(Path(full_import_report).read_text(encoding='utf-8'))
    pilot=json.loads(Path(prop_pilot_report).read_text(encoding='utf-8'))
    prior=json.loads(Path(sample_report).read_text(encoding='utf-8')) if sample_report else None
    plan=make_plan(contract,patch,full,pilot,phase,prior,visual_review_approved)
    if not execute:
        print(json.dumps(plan,indent=2)); return plan
    check(backup_confirmed is True,'Back up/checkpoint first; backup_confirmed=True required')
    import unreal as u
    _api(u); level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(not level.is_in_play_in_editor(),'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
          'SAVE all manual map/asset changes before continuing; unsaved changes cannot be copied')
    check(level.get_current_level().get_path_name().split('.')[0]==plan['source_map'],
          'Open the original successful pilot/recovery map, never the sample patch copy: '+plan['source_map'])
    _source_identity(u,pilot,contract)
    before=snapshot(u)
    mesh_system=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    originals={}
    for aid,path in plan['original_mesh_paths'].items():
        mesh=u.load_asset(path); check(isinstance(mesh,u.StaticMesh),'Original mesh unavailable: '+path)
        names,mats=_materials(mesh); em._validate_material_slots(contract['assets'][aid],names)
        originals[aid]=(mesh,names,mats,mesh_system.get_simple_collision_count(mesh))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    root='/Game/EvergreenHandoff/Normals_'+phase.capitalize()+'_'+stamp
    target=root+'/Maps/L_Evergreen_Normals_'+phase
    check(not u.EditorAssetLibrary.does_directory_exist(root),'Destination folder exists')
    output=Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff'/('Normals_'+stamp)
    output.mkdir(parents=True,exist_ok=False); report_path=output/'normals_patch_report.json'
    result=dict(plan,schema=SCHEMA,status='started',target_map=target,new_content_root=root,
                visual_verified=False,gameplay_verified=False,replacements={})
    def write(): report_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    write()
    try:
        check(level.new_level_from_template(target,plan['source_map']),'Could not copy saved pilot map')
        check(level.get_current_level().get_path_name().split('.')[0]==target,'Wrong target map')
        compare(before,snapshot(u))
        replacements={}
        for aid in plan['selected_asset_ids']:
            old,names,mats,count=originals[aid]
            new=em._import_file(u,patch['assets'][aid]['resolved_path'],root+'/Meshes',
                               em._asset_name('SMN_',aid),u.StaticMesh,em._fbx_options(u,contract))
            em._mesh_check(new,contract['assets'][aid])
            newnames,_unused=_materials_allow_empty(new)
            check(newnames==names,'Corrected FBX material slot order differs: '+aid)
            check(new.get_num_triangles(0)==old.get_num_triangles(0),'Triangle count changed: '+aid)
            check(mesh_system.get_simple_collision_count(new)==count,'Simple collision count changed: '+aid)
            for i,mat in enumerate(mats): new.set_material(i,mat)
            em._save_asset(u,new)
            replacements[_path(old)]=_path(new)
        result['replacements']=replacements
        changed=0
        with u.ScopedEditorTransaction('Evergreen corrected mesh references'):
            for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
                for c in actor.get_components_by_class(u.StaticMeshComponent):
                    oldpath=_path(c.get_editor_property('static_mesh'))
                    if oldpath in replacements:
                        c.modify()
                        check(c.set_static_mesh(u.load_asset(replacements[oldpath])),'Mesh replacement failed: '+c.get_name())
                        changed+=1
        check(changed>0,'No affected components in current map')
        expected=remap_snapshot(before,replacements)
        compare(expected,snapshot(u)); ec.verify(u,ec.make_plan(contract))
        check(level.save_current_level(),'Could not save corrected copy')
        check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Map remains dirty; reload stopped')
        check(level.load_level(target),'Could not reload corrected map')
        compare(expected,snapshot(u)); ec.verify(u,ec.make_plan(contract))
        result.update(status='verified_persistence',changed_components=changed,
                      actor_count=len(before),snapshot_preserved=True)
        write(); u.log('Normals patch persisted in new map. Visual Lit review required. Report: '+str(report_path))
        return str(report_path)
    except Exception as exc:
        result.update(status='failed_partial_copy',error=str(exc)); write()
        u.log_error('Stopped; original pilot/map/assets unchanged. Partial new content: '+root)
        raise


def _materials_allow_empty(mesh):
    slots=mesh.get_editor_property('static_materials')
    return [str(s.get_editor_property('material_slot_name')) for s in slots],None


def discover_reports(saved_root, current_map):
    """Exact map matches only. Never select a report by timestamp or filename order."""
    records=[]
    for path in Path(saved_root).glob('**/*.json'):
        if path.name not in ('prop_pilot_report.json','import_report.json'):
            continue
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            continue
        if isinstance(data,dict): records.append((path,data))
    pilots=[(p,d) for p,d in records if d.get('schema')=='evergreen-prop-actor-pilot-v1'
            and d.get('status')=='verified_pilot_persistence' and d.get('target_map')==current_map]
    check(len(pilots)==1,'Expected exactly one successful pilot report for the currently open map; found '+str(len(pilots)))
    pilot_path,pilot=pilots[0]
    matches=[(p,d) for p,d in records if d.get('schema')==em.SCHEMA and d.get('phase')=='full'
             and d.get('status')=='verified_persistence' and d.get('package_fingerprint')==pilot.get('package_fingerprint')
             and isinstance(d.get('map_path'),str)
             and re.fullmatch(re.escape(d['map_path'])+r'_WalkTest_[A-Za-z0-9_]+',pilot.get('source_map',''))]
    check(len(matches)==1,'Expected exactly one matching successful Full import report; found '+str(len(matches)))
    return {'full_import_report':str(matches[0][0]),'prop_pilot_report':str(pilot_path)}


def run_current(package_root, patch_root, *, phase='sample', execute=False, backup_confirmed=False,
                sample_report=None, visual_review_approved=False):
    """Convenience entry point inside Unreal; discover reports for current source map."""
    import unreal as u
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    current=level.get_current_level().get_path_name().split('.')[0]
    reports=discover_reports(Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff',current)
    return run(package_root,patch_root,**reports,phase=phase,execute=execute,backup_confirmed=backup_confirmed,
               sample_report=sample_report,visual_review_approved=visual_review_approved)
