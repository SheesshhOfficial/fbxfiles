"""Repair only the four completed pilot actors' collision in a NEW saved map copy.
Dry-run default. Requires the exact known failed report; no actors/instances rebuilt.
Unreal execution must be tested in the user's editor, not available in local tests.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import inspect
import json
import re
import uuid
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import setup_market_normals as en

check=em._require


def discover_report(saved_root,current_map):
    matches=[]
    for p in Path(saved_root).glob('**/prop_pilot_report.json'):
        try: d=json.loads(p.read_text(encoding='utf-8'))
        except (OSError,ValueError): continue
        if (isinstance(d,dict) and d.get('schema')=='evergreen-prop-actor-pilot-v1'
            and d.get('status')=='failed_partial_pilot_copy' and d.get('error')=='Pilot collision mismatch'
            and d.get('target_map')==current_map): matches.append(p)
    check(len(matches)==1,'Expected exactly one known collision-failure report for the current map; found '+str(len(matches)))
    return str(matches[0])


def validate_failed(contract,failed):
    check(failed.get('schema')=='evergreen-prop-actor-pilot-v1'
          and failed.get('status')=='failed_partial_pilot_copy'
          and failed.get('error')=='Pilot collision mismatch','Only the known completed-pilot collision failure is supported')
    check(failed.get('package_fingerprint')==contract['fingerprint'],'Original package/report fingerprint differs')
    source=failed.get('source_map',''); current=failed.get('target_map','')
    check(re.fullmatch(r'/Game/EvergreenHandoff/Full_[A-Za-z0-9_]+/Maps/L_Evergreen_full_WalkTest_[A-Za-z0-9_]+',source),
          'Unexpected original WalkTest path')
    check(re.fullmatch(re.escape(source)+r'_PropPilot_[A-Za-z0-9_]+',current),'Unexpected failed pilot map path')
    plan=copy.deepcopy(failed['plan'])
    check(plan.get('source_map')==source,'Plan/source map mismatch')
    promoted=plan.get('promoted',[])
    ids=[p['instance_id'] for p in promoted]
    check(len(ids)==4 and len(set(ids))==4,'Exactly four completed pilot records required')
    known={p['instance_id'] for p in contract['placements']}
    remaining=[p['instance_id'] for g in plan['remaining_scene']['groups'].values() for p in g['instances']]
    check(len(set(remaining))==len(remaining) and not set(remaining)&set(ids)
          and set(remaining)|set(ids)==known,'Remaining/promoted placement coverage differs')
    check(plan['remaining_scene']['map_path']==current,'Failed report did not reach completed-actor stage')
    check(plan['remaining_scene']['placement_count']==len(remaining),'Remaining placement count differs')
    en.compare(ec.make_plan(contract),plan['collision_plan'],'collision_plan')
    for p in promoted:
        remap_actor_path(p['actor_path'],current,current)
    return plan


def remap_actor_path(path,source,target):
    prefix=source+'.'+source.rsplit('/',1)[-1]+':PersistentLevel.'
    check(isinstance(path,str) and path.startswith(prefix) and len(path)>len(prefix),'Pilot actor path does not belong to source map')
    return target+'.'+target.rsplit('/',1)[-1]+':PersistentLevel.'+path[len(prefix):]


def remap_plan(plan,source,target):
    result=copy.deepcopy(plan)
    for p in result['promoted']:p['actor_path']=remap_actor_path(p['actor_path'],source,target)
    result['remaining_scene']['map_path']=target
    return result


def snapshot(u):
    result=en.snapshot(u)
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        for c in a.get_components_by_class(u.StaticMeshComponent):
            result[a.get_name()]['components'][c.get_name()]['collision_profile']=str(c.get_collision_profile_name())
    return result


def expected_snapshot(before,targets,query_only,ignore,block):
    result=copy.deepcopy(before)
    check(len(targets)==4 and len(set(targets))==4,'Exactly four distinct component targets required')
    for actor,component in targets:
        c=result[actor]['components'][component]
        c['collision_profile']='Custom';c['collision_enabled']=query_only
        c['responses']={name:block if name=='ECC_VISIBILITY' else ignore for name in c['responses']}
    return result


def run(package_root,failed_pilot_report,*,execute=False,backup_confirmed=False):
    contract=em.load_contract(package_root)
    failed=json.loads(Path(failed_pilot_report).read_text(encoding='utf-8'))
    plan=validate_failed(contract,failed);source=failed['target_map']
    summary={'source_map':source,'failed_report':str(failed_pilot_report),'pilot_actor_count':4,
             'collision_proxy_count':plan['collision_plan']['box_count'],
             'operation':'Copy saved map; change only four pilot collision settings; save and reload-verify'}
    import unreal as u
    ec._api(u)
    check('verify_collision' in inspect.signature(ep.verify).parameters and hasattr(ep,'_apply_pilot_collision'),
          'Updated setup_prop_actor_pilot.py required; restart/reload the current helper files')
    for method in ('get_collision_profile_name','set_collision_profile_name','modify'):
        check(hasattr(u.StaticMeshComponent,method),'Missing collision API: '+method)
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(not level.is_in_play_in_editor(),'Stop Play In Editor first')
    check(level.get_current_level().get_path_name().split('.')[0]==source,'Open the exact failed pilot map: '+source)
    ep.verify(u,plan,verify_collision=False);ec._check_original_collision(u,contract)
    before=snapshot(u)
    targets=[(a.get_name(),a.get_editor_property('static_mesh_component').get_name()) for a in ep._pilot_actors(u)]
    summary['collision_before']={a+'.'+c:{k:before[a]['components'][c][k] for k in ('collision_profile','collision_enabled','responses')}
                                 for a,c in targets}
    if not execute:
        print(json.dumps(summary,indent=2));return summary
    check(backup_confirmed is True,'Back up/checkpoint first; backup_confirmed=True required')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
          'SAVE current map and all manual changes before continuing. Unsaved work cannot be copied.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    target=source+'_CollisionVerified_'+stamp
    file=Path(u.Paths.project_content_dir()).resolve()/(target[len('/Game/'):]+'.umap')
    check(not file.exists(),'New map destination already exists')
    out=Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff'/('PilotCollision_'+stamp)
    out.mkdir(parents=True,exist_ok=False);path=out/'prop_pilot_report.json'
    newplan=remap_plan(plan,source,target)
    result=copy.deepcopy(failed)
    result.update(status='collision_repair_started',target_map=target,plan=newplan,
                  collision_repair_from=source,collision_repair_source_report=str(failed_pilot_report),
                  gameplay_verified=False,blueprint_modified=False)
    result.pop('error',None);result.pop('lookup_csv',None)
    def write():path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    write()
    try:
        check(level.new_level_from_template(target,source),'Could not copy saved failed map')
        check(level.get_current_level().get_path_name().split('.')[0]==target,'Wrong copied map loaded')
        en.compare(before,snapshot(u));ep.verify(u,newplan,verify_collision=False)
        expected=expected_snapshot(before,targets,str(u.CollisionEnabled.QUERY_ONLY),
                                   str(u.CollisionResponseType.ECR_IGNORE),str(u.CollisionResponseType.ECR_BLOCK))
        with u.ScopedEditorTransaction('Repair four pilot collision profiles'):
            for a in ep._pilot_actors(u):ep._apply_pilot_collision(u,a.get_editor_property('static_mesh_component'))
        result['before_save']=ep.verify(u,newplan)
        en.compare(expected,snapshot(u));ec._check_original_collision(u,contract)
        check(level.save_current_level(),'Could not save repaired map copy')
        check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Map remains dirty; reload stopped')
        check(level.load_level(target),'Could not reload repaired map')
        result['after_reload']=ep.verify(u,newplan)
        en.compare(expected,snapshot(u));ec._check_original_collision(u,contract)
        newplan['remaining_scene']['status']='verified_persistence'
        ep._write_lookup(out/'instance_lookup_pilot.csv',newplan)
        result.update(status='verified_pilot_persistence',lookup_csv=str(out/'instance_lookup_pilot.csv'),
                      manual_actor_snapshot_preserved=True)
        write();u.log('Four pilot collision profiles saved and reload-verified. Report: '+str(path))
        return str(path)
    except Exception as exc:
        result.update(status='failed_pilot_collision_repair',error=str(exc));write()
        u.log_error('Repair stopped. Original saved failed map unchanged; partial COPY may remain: '+target)
        raise


def run_current(package_root,*,execute=False,backup_confirmed=False):
    import unreal as u
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    current=level.get_current_level().get_path_name().split('.')[0]
    report=discover_report(Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff',current)
    return run(package_root,report,execute=execute,backup_confirmed=backup_confirmed)
