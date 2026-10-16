"""Narrow recovery for a failed fresh-run sample-lighting transform check.
Delegates light repair to a separately hash-approved preview helper. No respawn,
delete, reimport, Blueprint edits, or generic run-state reset is allowed.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import importlib.util
import json
import shutil
import sys
import uuid
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import setup_market_normals as en
import fresh_market_start as fw

OLD_PREVIEW_SHA='af21fb468f9901fbc489e3c25f3cd033ac20fb08131842ad4851f672fcc7c456'
NEW_PREVIEW_SHA='31e03cca11a5f4b9def4039d77e66a92d0191040105e624a0b77bd8a079c8aae'
check=em._require


def _read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def _write(path,data):
    path=Path(path);temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(path)


def validate_state(state_file):
    path=Path(state_file).expanduser().resolve();state=_read(path)
    check(state.get('schema')==fw.SCHEMA and state.get('status')=='stage_failed'
          and state.get('active_stage')=='sample_lighting' and state.get('completed')==['sample'],
          'Recovery supports only the failed sample_lighting step immediately after a successful sample')
    check(state.get('error')=='Preview transform changed','Unexpected original lighting failure; inspect before recovery')
    check(Path(state.get('state_file','')).resolve()==path,'Use the original exact run-state path')
    check(set(state.get('reports',{}))=={'sample'} and not state.get('optional_reports',{}),
          'Unexpected completed-stage or optional reports; no generic state reset allowed')
    merged=Path(state['merged_package']).resolve()
    check(merged==path.parent/'CorrectedPackage','Unexpected prepared package location')
    contract=em.load_contract(merged)
    check(contract['fingerprint']==state.get('merged_fingerprint'),'Prepared package changed')
    source=merged/'source';hashes=state.get('helper_hashes',{})
    check(hashes.get('fresh_preview_setup.py')==OLD_PREVIEW_SHA,'Unsupported original preview helper version')
    modules={'import_supermarket_unreal.py':em,'setup_market_collision.py':ec,
             'setup_prop_actor_pilot.py':ep,'setup_market_normals.py':en,'fresh_market_start.py':fw}
    check(set(hashes)==set(modules)|{'fresh_preview_setup.py'},'Unexpected helper snapshot membership')
    for name,digest in hashes.items():
        check(em._sha(source/name)==digest,'Prepared helper snapshot changed: '+name)
        if name in modules:
            check(em._sha(Path(modules[name].__file__).resolve())==digest,'Loaded helper differs from run snapshot: '+name)
    sample_path=Path(state['reports']['sample']).resolve();sample=_read(sample_path)
    check(sample.get('schema')==em.SCHEMA and sample.get('status')=='verified_persistence'
          and sample.get('phase')=='sample' and sample.get('package_fingerprint')==contract['fingerprint'],
          'Successful sample report does not match immutable prepared package')
    check(fw.SAMPLE_NAMES <= {contract['assets'][aid]['name'] for aid in sample.get('selected_asset_ids',[])},
          'Successful sample report lacks required diagnostic assets')
    return path,state,contract,sample


def validate_failure(report,source,fingerprint):
    check(report.get('schema')=='evergreen-preview-v1' and report.get('status')=='failed_partial_preview'
          and report.get('mode')=='sample' and report.get('error')=='Preview transform changed',
          'Only the original sample-lighting transform failure is supported')
    check(report.get('source_map')==source and report.get('target_map')==source
          and report.get('package_fingerprint')==fingerprint,'Failed preview report refers to another map/package')


def discover_failure(saved_root,source,fingerprint):
    found=[]
    for path in Path(saved_root).glob('**/preview_report.json'):
        try:
            report=_read(path)
            if not isinstance(report,dict):continue
            validate_failure(report,source,fingerprint)
        except (OSError,ValueError):continue
        found.append(path)
    check(len(found)==1,'Expected one exact failed sample-preview report; found '+str(len(found))+'. Never select newest by timestamp.')
    return str(found[0])


def approved_helper(helper_file):
    path=Path(helper_file).expanduser().resolve()
    check(NEW_PREVIEW_SHA!='WAIT_FOR_APPROVED_HELPER_SHA','Recovery helper approval is not finalized; do not execute this draft')
    check(em._sha(path)==NEW_PREVIEW_SHA,'Corrected preview helper does not match the approved recovery version')
    spec=importlib.util.spec_from_file_location('_evergreen_approved_preview_recovery',path)
    check(spec is not None and spec.loader is not None,'Cannot load corrected preview helper')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    check(callable(getattr(module,'recover_sample',None)),'Approved helper lacks scoped recovery API')
    return module,path


def ready_state(state,report_path,new_hash):
    result=copy.deepcopy(state)
    result['helper_hashes']['fresh_preview_setup.py']=new_hash
    result.setdefault('optional_reports',{})['sample_lighting']=str(Path(report_path).resolve())
    result.update(status='ready',active_stage=None)
    result.pop('error',None)
    return result


def run(state_file,*,failed_preview_report=None,helper_file=None,execute=False,backup_confirmed=False):
    path,state,contract,sample=validate_state(state_file)
    helper,helper_path=approved_helper(helper_file or Path(__file__).resolve().with_name('fresh_preview_setup.py'))
    import unreal as u
    source=sample['map_path'];level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(level.get_current_level().get_path_name().split('.')[0]==source,'Open this run\'s exact failed sample map: '+source)
    if failed_preview_report is None:
        failed_preview_report=discover_failure(Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff',source,contract['fingerprint'])
    failed_preview_report=str(Path(failed_preview_report).resolve())
    validate_failure(_read(failed_preview_report),source,contract['fingerprint'])
    failed_report_hash=em._sha(failed_preview_report)
    # This is read-only and must prove exact eleven-light membership/settings,
    # sample geometry and actual-vs-target transforms before any file/state write.
    diagnostic=helper.recover_sample(state['merged_package'],state['reports']['sample'],failed_preview_report,execute=False)
    if not execute:return diagnostic
    check(backup_confirmed is True,'Save and back up the project first; backup_confirmed=True required')
    check(not level.is_in_play_in_editor(),'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
          'SAVE the failed sample map with its existing eleven lights and all manual changes first')
    original_state_hash=em._sha(path);old_helper=Path(state['merged_package'])/'source'/'fresh_preview_setup.py'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    backup=path.parent/('LightingRecovery_'+stamp);backup.mkdir(exist_ok=False)
    shutil.copy2(path,backup/'run_state.before.json');shutil.copy2(old_helper,backup/'fresh_preview_setup.before.py')
    check(em._sha(backup/'run_state.before.json')==original_state_hash
          and em._sha(backup/'fresh_preview_setup.before.py')==OLD_PREVIEW_SHA,'Backup verification failed')
    receipt={'schema':'evergreen-lighting-recovery-migration-v1','status':'started','state_file':str(path),
             'failed_preview_report':failed_preview_report,'old_state_sha256':original_state_hash,
             'old_preview_sha256':OLD_PREVIEW_SHA,'new_preview_sha256':NEW_PREVIEW_SHA}
    receipt_path=backup/'migration_report.json';_write(receipt_path,receipt)
    try:
        new_report=helper.recover_sample(state['merged_package'],state['reports']['sample'],failed_preview_report,
                                         execute=True,backup_confirmed=True)
        verified=_read(new_report)
        check(verified.get('schema')=='evergreen-preview-v1' and verified.get('status')=='verified_preview_persistence'
              and verified.get('mode')=='sample' and verified.get('source_map')==source
              and verified.get('target_map')==source and verified.get('package_fingerprint')==contract['fingerprint']
              and verified.get('transform_only_recovery') is True
              and verified.get('recovery_scope')=='Sun factory scale 2.5 to 1 only'
              and verified.get('preserved_non_preview_actor_state') is True
              and Path(verified.get('recovery_from','')).resolve()==Path(failed_preview_report)
              and verified.get('failed_report_sha256')==failed_report_hash,
              'Light recovery did not return a matching verified success report')
        receipt.update(status='lights_verified',successful_preview_report=str(new_report));_write(receipt_path,receipt)
        # Recheck originals immediately before narrow migration. Other state/helper
        # fields must remain byte-for-byte untouched throughout the operation.
        check(em._sha(path)==original_state_hash and em._sha(old_helper)==OLD_PREVIEW_SHA,
              'State/helper changed during recovery; stop before migration')
        validate_state(path)
        staged=old_helper.with_suffix('.recovery.tmp');shutil.copy2(helper_path,staged)
        check(em._sha(staged)==NEW_PREVIEW_SHA,'Staged helper hash mismatch')
        staged.replace(old_helper)
        receipt['status']='helper_installed';_write(receipt_path,receipt)
        _write(path,ready_state(state,new_report,NEW_PREVIEW_SHA))
        receipt['status']='verified_migration';_write(receipt_path,receipt)
        # Make subsequent fw.preview imports use the already-verified helper in this session.
        sys.modules['fresh_preview_setup']=helper
        u.log('Existing sample lights repaired and reloaded; run ready. State and original helper backups: '+str(backup))
        return str(new_report)
    except Exception as exc:
        receipt.update(status='failed_requires_inspection',error=str(exc));_write(receipt_path,receipt)
        u.log_error('Recovery stopped. Keep original failed report and backup folder: '+str(backup))
        raise
