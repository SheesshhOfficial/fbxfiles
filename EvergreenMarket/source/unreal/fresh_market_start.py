"""Restart-safe fresh Evergreen import from corrected FBXs. No old reports used.
Preflight/dry-run by default; each stage requires an explicit execute=True call.
Local/mock tests only: Unreal runtime remains unverified in the build environment.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import uuid
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import setup_market_normals as en

SCHEMA='evergreen-fresh-run-v1'
STAGES=('sample','full','collision','pilot')
SAMPLE_NAMES={'ShippingCarton_Floor','Checkout base','PaperShoppingBag','Impulse display'}
ORIGINAL_MANIFEST_SHA='a8da455b0402ccce0f22eb6451b92eee0d9fb6d4cda2d3c183136a051021939e'
ORIGINAL_FINGERPRINT='886da0f702f82b76742b49023a268ac8a2e76e63214e45202ca4d19c27f14157'
PATCH_MANIFEST_SHA='483bd3743899f589a4e71f0468034946ee73cee4a38fb3085367a8092c389749'
check=em._require


def _read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def _write(path,data):
    path=Path(path);tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)


def _validate_sources(package_root,patch_root):
    c=em.load_contract(package_root);p=en.load_patch(c,patch_root)
    check(em._sha(c['root']/'manifest.json')==ORIGINAL_MANIFEST_SHA and c['fingerprint']==ORIGINAL_FINGERPRINT,
          'This fresh-start helper requires the verified original Evergreen package')
    check(em._sha(Path(patch_root).expanduser().resolve()/'patch_manifest.json')==PATCH_MANIFEST_SHA,
          'This helper requires the complete verified normals patch; altered/incomplete patches are rejected')
    check(len(c['assets'])==256 and len(c['placements'])==11316 and len(p['assets'])==178,
          'Expected 256 total assets, 11,316 placements and 178 corrected FBXs')
    for a in c['assets'].values():
        check(em._sha(em._path(c['root'],a['fbx_path'],'.fbx'))==a['file_sha256'],
              'Original asset differs from manifest: '+a['asset_id'])
    return c,p


def start(package_root,patch_root,work_folder,*,execute=False):
    """Validate originals; optionally create a NEW local merged package and state file."""
    c,p=_validate_sources(package_root,patch_root)
    work=Path(work_folder).expanduser().resolve()
    check(not work.exists(),'Use a new empty/nonexistent work folder; never overwrite a previous run')
    patch=Path(patch_root).expanduser().resolve()
    check(work!=c['root'] and work!=patch and c['root'] not in work.parents and patch not in work.parents,
          'Work folder must be outside both input packages')
    summary={'original_package':str(c['root']),'patch_root':str(patch),'work_folder':str(work),
             'total_assets':len(c['assets']),'corrected_assets':len(p['assets']),
             'unchanged_assets':len(c['assets'])-len(p['assets']),
             'source_fingerprint':c['fingerprint'],'patch_fingerprint':p['fingerprint'],
             'state_file':str(work/'run_state.json')}
    if not execute:
        print(json.dumps(summary,indent=2));return summary
    work.mkdir(parents=True,exist_ok=False)
    merged=work/'CorrectedPackage';merged.mkdir()
    state=dict(summary,schema=SCHEMA,run_id=uuid.uuid4().hex,
               created_utc=datetime.now(timezone.utc).isoformat(),status='preparing',completed=[],reports={},
               merged_package=str(merged))
    statepath=work/'run_state.json';_write(statepath,state)
    try:
        # Only package files referenced by the validated importer contract.
        for rel in c['file_hashes']:
            src=em._path(c['root'],rel);dest=merged/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dest)
        manifest=_read(merged/'manifest.json')
        for a in manifest['assets']:
            if a['asset_id'] in p['assets']:
                repair=p['assets'][a['asset_id']]
                shutil.copy2(repair['resolved_path'],merged/a['fbx_path'])
                a['original_file_sha256']=a['file_sha256'];a['file_sha256']=repair['file_sha256']
                a['winding_patch_applied']=True
        manifest['fresh_import_provenance']={'original_manifest_sha256':em._sha(c['root']/'manifest.json'),
                                            'patch_fingerprint':p['fingerprint'],
                                            'note':'Same logical asset IDs and placements; corrected FBX bytes and hashes.'}
        _write(merged/'manifest.json',manifest)
        source=merged/'source';source.mkdir()
        helper_dir=Path(em.__file__).resolve().parent
        for module in (ec,ep,en):
            check(Path(module.__file__).resolve().parent==helper_dir,'Mixed helper folders loaded; restart with one current source folder')
        for file in helper_dir.glob('*.py'):shutil.copy2(file,source/file.name)
        shutil.copy2(Path(__file__).resolve(),source/Path(__file__).name)
        # Preserve bootstrap and user guide if shipped beside this wrapper.
        for name in ('Start_Fresh_Market.py','FRESH_START.md'):
            file=Path(__file__).resolve().parent/name
            if file.is_file():shutil.copy2(file,source/name)
        merged_contract=em.load_contract(merged)
        for a in merged_contract['assets'].values():
            check(em._sha(em._path(merged,a['fbx_path'],'.fbx'))==a['file_sha256'],'Merged FBX hash differs')
        state.update(status='ready',merged_fingerprint=merged_contract['fingerprint'],
                     helper_hashes={name:em._sha(source/name) for name in
                                    ('import_supermarket_unreal.py','setup_market_collision.py',
                                     'setup_prop_actor_pilot.py','setup_market_normals.py','fresh_market_start.py')})
        if (source/'fresh_preview_setup.py').is_file():
            state['helper_hashes']['fresh_preview_setup.py']=em._sha(source/'fresh_preview_setup.py')
        _write(statepath,state)
        print('Prepared corrected package. Keep this exact state path: '+str(statepath))
        return str(statepath)
    except Exception as exc:
        state.update(status='prepare_failed',error=str(exc));_write(statepath,state);raise


def load_state(state_file):
    path=Path(state_file).expanduser().resolve();state=_read(path)
    check(state.get('schema')==SCHEMA,'Unsupported run state')
    check(path==Path(state['state_file']).resolve(),'State file was moved; use its original explicit path')
    check(state.get('status') in ('ready','complete'),
          'Previous stage is incomplete/failed. Keep its report/error for inspection; do not rerun or edit state to bypass it.')
    check(state.get('completed')==list(STAGES[:len(state.get('completed',[]))]),'Invalid completed-stage order')
    c=em.load_contract(state['merged_package'])
    check(c['fingerprint']==state.get('merged_fingerprint'),'Prepared package changed since this run began')
    modules={'import_supermarket_unreal.py':em,'setup_market_collision.py':ec,
             'setup_prop_actor_pilot.py':ep,'setup_market_normals.py':en}
    for name,module in modules.items():
        check(em._sha(Path(module.__file__).resolve())==state['helper_hashes'][name],
              'Loaded helper changed or is stale: '+name+'; use this run\'s CorrectedPackage/source snapshot')
    check(em._sha(Path(__file__).resolve())==state['helper_hashes']['fresh_market_start.py'],'Fresh wrapper differs from prepared run')
    return path,state,c


def _check_report(stage,report,contract,state):
    if stage in ('sample','full'):
        check(report.get('schema')==em.SCHEMA and report.get('phase')==stage
              and report.get('status')=='verified_persistence'
              and report.get('package_fingerprint')==contract['fingerprint'],'Import stage did not verify persistence')
    elif stage=='collision':
        full=_read(state['reports']['full'])
        check(report.get('status')=='verified_collision_persistence' and report.get('source_map')==full['map_path'],
              'Collision report does not match this run\'s full map')
        check(report.get('box_count')==ec.make_plan(contract)['box_count'],'Collision count mismatch')
    else:
        collision=_read(state['reports']['collision'])
        check(report.get('schema')=='evergreen-prop-actor-pilot-v1'
              and report.get('status')=='verified_pilot_persistence'
              and report.get('package_fingerprint')==contract['fingerprint']
              and report.get('source_map')==collision['target_map'],'Pilot stage did not verify this run\'s map')


def step(state_file,*,stage='status',execute=False,backup_confirmed=False,visual_review_approved=False):
    """Perform one requested stage; never auto-advance across the sample review gate."""
    path,state,c=load_state(state_file)
    for previous in state['completed']:_check_report(previous,_read(state['reports'][previous]),c,state)
    next_stage=STAGES[len(state['completed'])] if len(state['completed'])<len(STAGES) else None
    if stage=='status':
        result={'state_file':str(path),'next_stage':next_stage,'completed':state['completed'],'reports':state['reports']}
        print(json.dumps(result,indent=2));return result
    check(stage in STAGES and stage==next_stage,'Next permitted stage is '+str(next_stage)+'; completed stages never rerun')
    package=state['merged_package']
    if stage=='sample':
        selected=set(em.select_sample(c))
        selected.update(aid for aid,a in c['assets'].items() if a['name'] in SAMPLE_NAMES)
        check(SAMPLE_NAMES.issubset({c['assets'][aid]['name'] for aid in selected}),'Diagnostic sample meshes missing')
        kwargs={'phase':'sample','sample_asset_ids':sorted(selected)}
        call=lambda run:em.run(package,execute=run,**kwargs)
    elif stage=='full':
        check(visual_review_approved is True,'Inspect the corrected sample first, then pass visual_review_approved=True')
        call=lambda run:em.run(package,execute=run,phase='full',preflight_report=state['reports']['sample'],visual_review_approved=True)
    elif stage=='collision':
        call=lambda run:ec.run(package,state['reports']['full'],execute=run,backup_confirmed=backup_confirmed)
    else:
        call=lambda run:ep.run(package,state['reports']['full'],state['reports']['collision'],execute=run,backup_confirmed=backup_confirmed)
    if not execute:return call(False)
    check(backup_confirmed is True,'Save/backup the project first, then pass backup_confirmed=True')
    _editor_preflight(stage,state)
    state.update(status='running',active_stage=stage,stage_started_utc=datetime.now(timezone.utc).isoformat())
    _write(path,state)
    try:
        report_path=call(True)
        check(isinstance(report_path,str) and Path(report_path).is_file(),'Stage did not return its report path')
        report=_read(report_path);_check_report(stage,report,c,state)
        state['reports'][stage]=str(Path(report_path).resolve());state['completed'].append(stage)
        state.update(status='complete' if stage=='pilot' else 'ready',active_stage=None)
        _write(path,state)
        print('Stage verified: '+stage+'. State: '+str(path))
        return str(report_path)
    except Exception as exc:
        state.update(status='stage_failed',error=str(exc));_write(path,state)
        print('Stage stopped. Keep the FIRST error/report and this state file. No automatic retry or old-report lookup.')
        raise


def _editor_preflight(stage,state):
    import unreal as u
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(not level.is_in_play_in_editor(),'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
          and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
          'SAVE the current map and all changed assets first; do not discard manual work')
    check(not u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX'),
          'Legacy FBX options required: set Interchange.FeatureFlags.Import.FBX 0 in the editor console')
    expected=None
    if stage=='full':expected=_read(state['reports']['sample'])['map_path']
    elif stage=='collision':expected=_read(state['reports']['full'])['map_path']
    elif stage=='pilot':expected=_read(state['reports']['collision'])['target_map']
    if expected:
        check(level.get_current_level().get_path_name().split('.')[0]==expected,
              'Open this run\'s exact stage source map first: '+expected)


def finish(state_file,*,execute=False,backup_confirmed=False,visual_review_approved=False):
    """After sample review, run remaining stages with a checkpoint after every success."""
    path,state,c=load_state(state_file)
    for stage in state['completed']:_check_report(stage,_read(state['reports'][stage]),c,state)
    check('sample' in state['completed'],'Run and inspect the corrected sample first')
    remaining=list(STAGES[len(state['completed']):])
    result={'state_file':str(path),'remaining_stages':remaining,'reports':state['reports']}
    if not execute or not remaining:
        print(json.dumps(result,indent=2));return result
    check(backup_confirmed is True,'Save/backup the project first')
    if 'full' in remaining:check(visual_review_approved is True,'Explicit corrected-sample visual approval required')
    for stage in remaining:
        step(path,stage=stage,execute=True,backup_confirmed=True,visual_review_approved=visual_review_approved)
    return step(path)


def _preview_stage(state_file,mode,execute,backup_confirmed):
    path,state,c=load_state(state_file)
    for stage in state['completed']:_check_report(stage,_read(state['reports'][stage]),c,state)
    key='sample_lighting' if mode=='sample' else 'pilot_preview'
    if key in state.get('optional_reports',{}):
        old=state['optional_reports'][key];report=_read(old)
        check(report.get('schema')=='evergreen-preview-v1' and report.get('status')=='verified_preview_persistence'
              and report.get('mode')==mode,'Stored optional report is invalid')
        print('Already completed; no duplicate actors/maps created. Report: '+old);return old
    check(state['completed']==(['sample'] if mode=='sample' else list(STAGES)),
          'Sample lighting is available just after sample; final preview requires all four pipeline stages')
    import fresh_preview_setup as fp
    check('fresh_preview_setup.py' in state['helper_hashes']
          and em._sha(Path(fp.__file__).resolve())==state['helper_hashes']['fresh_preview_setup.py'],
          'Preview helper was not included in this prepared run or has changed')
    if mode=='sample':
        source=_read(state['reports']['sample'])['map_path']
        call=lambda run:fp.light_sample(state['merged_package'],state['reports']['sample'],execute=run,backup_confirmed=backup_confirmed)
    else:
        source=_read(state['reports']['pilot'])['target_map']
        call=lambda run:fp.run(state['merged_package'],state['reports']['full'],state['reports']['collision'],
                              state['reports']['pilot'],execute=run,backup_confirmed=backup_confirmed)
    if not execute:return call(False)
    check(backup_confirmed is True,'Save/backup first; backup_confirmed=True required')
    # Catch ordinary setup mistakes before recording an in-progress mutation.
    _editor_preflight('sample',state)
    import unreal as u
    current=u.get_editor_subsystem(u.LevelEditorSubsystem).get_current_level().get_path_name().split('.')[0]
    check(current==source,'Open this run\'s exact preview source map first: '+source)
    call(False)
    state.update(status='running',active_stage=key);_write(path,state)
    try:
        report_path=call(True);report=_read(report_path)
        check(report.get('schema')=='evergreen-preview-v1' and report.get('status')=='verified_preview_persistence'
              and report.get('mode')==mode and report.get('source_map')==source,'Preview did not verify this run\'s source map')
        state.setdefault('optional_reports',{})[key]=str(Path(report_path).resolve())
        state.update(status='complete' if mode=='pilot' else 'ready',active_stage=None);_write(path,state)
        return str(report_path)
    except Exception as exc:
        state.update(status='stage_failed',error=str(exc));_write(path,state);raise


def light_sample(state_file,*,execute=False,backup_confirmed=False):
    """Optional neutral lights on this run's exact sample map, with a saved receipt."""
    return _preview_stage(state_file,'sample',execute,backup_confirmed)


def preview(state_file,*,execute=False,backup_confirmed=False):
    """Optional final-map preview copy with lights/PlayerStart, no Blueprint edits."""
    return _preview_stage(state_file,'pilot',execute,backup_confirmed)
