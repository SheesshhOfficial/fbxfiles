"""Native-source v2 fresh import. Dry-run default; no original package, patch or old reports.
Local/mock verified only. Execute each stage explicitly inside Unreal after saving/backup.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import uuid
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
import fresh_preview_setup as fp

SCHEMA='evergreen-native-fresh-run-v2'
STAGES=('sample','sample_lighting','full','collision','pilot','lighting')
SAMPLE_NAMES={'ShippingCarton_Floor','Checkout base','PaperShoppingBag','Impulse display'}
check=em._require
MODULES={'import_supermarket_unreal.py':em,'setup_market_collision.py':ec,
         'setup_prop_actor_pilot.py':ep,'fresh_preview_setup.py':fp}

def _read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def _write(path,data):
    path=Path(path);tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)

def validate_source(package_root):
    c=em.load_contract(package_root);root=c['root']
    source=_read(root/'source_manifest.json')
    check(source.get('schema')=='evergreen-consolidated-native-v2','Expected complete native v2 export')
    check(len(c['assets'])==256 and len(c['placements'])==11316,'Expected complete 256 asset / 11,316 placement source')
    check(set(source.get('assets',{}))==set(c['assets']),'Native source asset membership differs')
    files=dict(c['file_hashes'])
    for aid,a in c['assets'].items():
        b=source['assets'][aid]
        check(a['fbx_path']==b['fbx_path'] and a['file_sha256']==b['file_sha256']
              and em._sha(em._path(root,a['fbx_path'],'.fbx'))==a['file_sha256'],'Native FBX mismatch: '+aid)
    blend=em._path(root,source['blend_file'],'.blend')
    check(em._sha(blend)==source['blend_sha256'],'Native blend checkpoint differs')
    check(c['manifest'].get('source_checkpoint_schema')==source['schema']
          and c['manifest'].get('source_blend_sha256')==source['blend_sha256'],'Import manifest refers to another native checkpoint')
    companions=_read(root/'walking_companions.json')
    check(companions.get('schema')=='evergreen-walking-companions-v1','Missing native walking companions')
    seen=set();source_seen=set()
    for a in companions['assets']:
        check(a['source_asset_id'] in c['assets'] and a['source_asset_id'] not in source_seen and a['asset_id'] not in seen,'Invalid companion membership')
        seen.add(a['asset_id']);source_seen.add(a['source_asset_id'])
        file=em._path(root,a['fbx_path'],'.fbx')
        check(em._sha(file)==a['file_sha256'],'Companion FBX mismatch')
        files[a['fbx_path']]=em._sha(file)
    policy=_read(root/'collision_policy_v2.json')
    check(policy.get('schema')=='evergreen-source-collision-policy-v1' and policy.get('revision')=='physical-coverage-v2' and set(policy['assets'])==set(c['assets']),'Collision policy membership differs')
    collision_plan=ec.make_plan(c)
    fp.clearance(collision_plan['boxes'])  # Fail before importing if preview spawn loses its clear support.
    check(collision_plan['box_count']==policy['invariants']['total_world_boxes'],'Expanded source policy count mismatch')
    expected={aid:row for aid,row in policy['assets'].items() if row['local_boxes_cm']}
    check({a['source_asset_id'] for a in companions['assets']}==set(expected),'Companion coverage differs from policy')
    check(sum(a['boxes'] for a in companions['assets'])==policy['invariants']['canonical_blocker_boxes'],'Canonical companion total differs')
    check(sum(a['boxes']*len(a['instance_ids']) for a in companions['assets'])==policy['invariants']['total_world_boxes'],'World companion total differs')
    for a in companions['assets']:
        row=expected[a['source_asset_id']];role=row['export_roles']['walking_companion_body']
        check(a['asset_id']==role['asset_id'] and a['boxes']==len(row['local_boxes_cm'])
              and a['runtime']==role['runtime'] and a['instance_ids']==row['walking_instance_ids']
              and a['render_hidden_required'] is True and a['attach_same_transform_as_source_instance'] is True,
              'Companion metadata differs from source-reviewed policy')
    lights=_read(root/'neutral_light_layout_v1.json')
    check(lights.get('schema')=='evergreen-neutral-light-layout-v1' and len(lights['lights'])==11,'Expected neutral 11-light layout')
    fp._lights(c)  # Validate runtime-supported light settings before any import.
    for light in lights['lights']:
        check(light['scale']==[1,1,1],'Light scale must be unit')
    for name in ('manifest.json','source_manifest.json','walking_companions.json','collision_policy_v2.json','neutral_light_layout_v1.json',source['blend_file']):
        files[name]=em._sha(em._path(root,name))
    fingerprint=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    return c,files,fingerprint

def start(package_root,work_folder,*,execute=False):
    c,files,fingerprint=validate_source(package_root)
    work=Path(work_folder).expanduser().resolve()
    check(not work.exists(),'Use a new nonexistent work folder; never overwrite an earlier run')
    check(work!=c['root'] and c['root'] not in work.parents,'Work folder must be outside native source package')
    helpers=Path(__file__).resolve().parent
    for module in MODULES.values():
        check(Path(module.__file__).resolve().parent==helpers,'Mixed helper folders loaded; restart Unreal with one v2 folder')
    summary=dict(package_root=str(c['root']),work_folder=str(work),source_fingerprint=fingerprint,
                 total_assets=len(c['assets']),placement_count=len(c['placements']),state_file=str(work/'run_state.json'))
    if not execute:
        print(json.dumps(summary,indent=2));return summary
    work.mkdir(parents=True,exist_ok=False);merged=work/'NativePackage';merged.mkdir()
    state=dict(summary,schema=SCHEMA,run_id=uuid.uuid4().hex,created_utc=datetime.now(timezone.utc).isoformat(),
               status='preparing',completed=[],reports={},merged_package=str(merged))
    path=work/'run_state.json';_write(path,state)
    try:
        for rel in files:
            dst=merged/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(em._path(c['root'],rel),dst)
        source=merged/'source'/'unreal';source.mkdir(parents=True)
        for pattern in ('*.py','*.md'):
            for file in helpers.glob(pattern):shutil.copy2(file,source/file.name)
        native,_,native_fingerprint=validate_source(merged)
        check(native_fingerprint==fingerprint,'Prepared native copy differs')
        state.update(status='ready',merged_fingerprint=native['fingerprint'],
                     helper_hashes={name:em._sha(source/name) for name in (*MODULES,'fresh_market_source_v2.py')})
        _write(path,state);return str(path)
    except Exception as exc:
        state.update(status='prepare_failed',error=str(exc));_write(path,state);raise

def load_state(state_file):
    path=Path(state_file).expanduser().resolve();state=_read(path)
    check(state.get('schema')==SCHEMA,'Expected native v2 run state')
    check(path==Path(state['state_file']).resolve(),'State file was moved')
    check(state.get('status') in ('ready','complete'),'Run incomplete/failed; inspect first error. Never edit state or retry blindly.')
    check(state.get('completed')==list(STAGES[:len(state.get('completed',[]))]),'Invalid stage order')
    c,_,fingerprint=validate_source(state['merged_package'])
    check(fingerprint==state['source_fingerprint'] and c['fingerprint']==state['merged_fingerprint'],'Prepared native package changed')
    for name,module in MODULES.items():
        check(em._sha(Path(module.__file__).resolve())==state['helper_hashes'][name],'Loaded helper changed/stale: '+name)
    check(em._sha(Path(__file__).resolve())==state['helper_hashes']['fresh_market_source_v2.py'],'Fresh v2 wrapper changed')
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
    elif stage=='pilot':
        collision=_read(state['reports']['collision'])
        check(report.get('schema')=='evergreen-prop-actor-pilot-v1'
              and report.get('status')=='verified_pilot_persistence'
              and report.get('package_fingerprint')==contract['fingerprint']
              and report.get('source_map')==collision['target_map'],'Pilot stage did not verify this run\'s map')

    elif stage=='sample_lighting':
        sample=_read(state['reports']['sample'])
        check(report.get('schema')=='evergreen-preview-v1' and report.get('status')=='verified_preview_persistence'
              and report.get('mode')=='sample' and report.get('source_map')==sample['map_path']
              and report.get('target_map')==sample['map_path']
              and report.get('package_fingerprint')==contract['fingerprint'],'Sample lighting report mismatch')
    elif stage=='lighting':
        pilot=_read(state['reports']['pilot'])
        check(report.get('schema')=='evergreen-preview-v1' and report.get('status')=='verified_preview_persistence'
              and report.get('mode')=='pilot' and report.get('source_map')==pilot['target_map']
              and report.get('package_fingerprint')==contract['fingerprint'],'Lighting report mismatch')


def step(state_file,*,stage='status',execute=False,backup_confirmed=False,visual_review_approved=False):
    """Perform one requested stage; never auto-advance across the sample review gate."""
    path,state,c=load_state(state_file)
    for previous in state['completed']:
        check(em._sha(Path(state['reports'][previous]))==state['report_hashes'][previous],'Saved stage report changed')
        _check_report(previous,_read(state['reports'][previous]),c,state)
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
    elif stage=='sample_lighting':
        call=lambda run:fp.light_sample(package,state['reports']['sample'],execute=run,backup_confirmed=backup_confirmed)
    elif stage=='full':
        check(visual_review_approved is True,'Inspect the corrected sample first, then pass visual_review_approved=True')
        call=lambda run:em.run(package,execute=run,phase='full',preflight_report=state['reports']['sample'],visual_review_approved=True)
    elif stage=='collision':
        call=lambda run:ec.run(package,state['reports']['full'],execute=run,backup_confirmed=backup_confirmed)
    elif stage=='pilot':
        call=lambda run:ep.run(package,state['reports']['full'],state['reports']['collision'],execute=run,backup_confirmed=backup_confirmed)
    else:
        call=lambda run:fp.run(package,state['reports']['full'],state['reports']['collision'],state['reports']['pilot'],execute=run,backup_confirmed=backup_confirmed)
    if not execute:return call(False)
    check(backup_confirmed is True,'Save/backup the project first, then pass backup_confirmed=True')
    _editor_preflight(stage,state)
    state.update(status='running',active_stage=stage,stage_started_utc=datetime.now(timezone.utc).isoformat())
    _write(path,state)
    try:
        report_path=call(True)
        check(isinstance(report_path,str) and Path(report_path).is_file(),'Stage did not return its report path')
        report=_read(report_path);_check_report(stage,report,c,state)
        state['reports'][stage]=str(Path(report_path).resolve())
        state.setdefault('report_hashes',{})[stage]=em._sha(Path(report_path))
        state['completed'].append(stage)
        state.update(status='complete' if stage=='lighting' else 'ready',active_stage=None)
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
    if stage in ('full','sample_lighting'):expected=_read(state['reports']['sample'])['map_path']
    elif stage=='collision':expected=_read(state['reports']['full'])['map_path']
    elif stage=='pilot':expected=_read(state['reports']['collision'])['target_map']
    elif stage=='lighting':expected=_read(state['reports']['pilot'])['target_map']
    if expected:
        check(level.get_current_level().get_path_name().split('.')[0]==expected,
              'Open this run\'s exact stage source map first: '+expected)


def finish(state_file,*,execute=False,backup_confirmed=False,visual_review_approved=False):
    """After sample review, run remaining stages with a checkpoint after every success."""
    path,state,c=load_state(state_file)
    for stage in state['completed']:
        check(em._sha(Path(state['reports'][stage]))==state['report_hashes'][stage],'Saved stage report changed')
        _check_report(stage,_read(state['reports'][stage]),c,state)
    check('sample_lighting' in state['completed'],'Run sample and sample_lighting, then inspect the lit sample first')
    remaining=list(STAGES[len(state['completed']):])
    result={'state_file':str(path),'remaining_stages':remaining,'reports':state['reports']}
    if not execute or not remaining:
        print(json.dumps(result,indent=2));return result
    check(backup_confirmed is True,'Save/backup the project first')
    if 'full' in remaining:check(visual_review_approved is True,'Explicit corrected-sample visual approval required')
    for stage in remaining:
        step(path,stage=stage,execute=True,backup_confirmed=True,visual_review_approved=visual_review_approved)
    return step(path)


