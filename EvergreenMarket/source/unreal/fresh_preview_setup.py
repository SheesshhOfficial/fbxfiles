"""Optional neutral preview lighting and clearance-checked PlayerStart.
Dry-run by default. No geometry, material, Blueprint, GameMode or project changes.
Official UE 5.7 Python APIs; local/mock tests only, Unreal execution unverified.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
import math
import re
import uuid
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep

SCHEMA = 'evergreen-preview-v1'
TAG = 'EvergreenNeutralPreviewV1'
check = em._require
# Design clearance envelope, not a claim about the user's gameplay pawn.
RADIUS_CM = 50.0
HALF_HEIGHT_CM = 100.0
START = [-300.0, 2280.0, 103.0]
LIGHTS = [dict(key='Sun', actor='DirectionalLight', component='DirectionalLightComponent',
               location=[0,2100,800], rotation=[-45,-90,0], intensity=10000.0)]
LIGHTS += [dict(key='Interior_%s_%s' % (i,j), actor='PointLight', component='PointLightComponent',
                location=[x,y,400], rotation=[0,0,0], intensity=12000.0, radius=1500.0)
           for i,x in enumerate((-1400,0,1400)) for j,y in enumerate((-1400,0,1400))]
LIGHTS += [dict(key='PilotFill', actor='PointLight', component='PointLightComponent',
                location=[-300,2100,350], rotation=[0,0,0], intensity=6000.0,radius=900.0)]

def _read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def _fresh(contract):
    check(contract['manifest'].get('fresh_import_provenance'), 'Use this fresh run’s CorrectedPackage, not the legacy package')
    check(len(contract['assets'])==256 and sum(bool(a.get('winding_patch_applied')) for a in contract['assets'].values())==178,
          'Fresh contract must contain all 256 assets including 178 corrected FBXs')
    for a in contract['assets'].values():
        check(em._sha(em._path(contract['root'],a['fbx_path']))==a['file_sha256'],'Fresh FBX hash mismatch: '+a['asset_id'])

def box_aabb(box):
    """Conservative world AABB of a rotated/scaled box, using full quaternion."""
    x,y,z,w=box['placement']['quaternion_xyzw'];s=box['placement']['scale']
    r=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
       (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
       (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
    e=[sum(abs(r[i][j]*s[j])*box['extent'][j] for j in range(3)) for i in range(3)]
    return ([box['center'][i]-e[i] for i in range(3)], [box['center'][i]+e[i] for i in range(3)])

def clearance(boxes, location=START, radius=RADIUS_CM, half_height=HALF_HEIGHT_CM):
    check(0<radius<=half_height and all(math.isfinite(v) for v in [*location,radius,half_height]),'Invalid capsule envelope')
    lo=[location[0]-radius,location[1]-radius,location[2]-half_height]
    hi=[location[0]+radius,location[1]+radius,location[2]+half_height]
    blocked=[];supports=[]
    for box in boxes:
        a,b=box_aabb(box)
        if all(lo[i]<b[i]+0.01 and hi[i]>a[i]-0.01 for i in range(3)):
            blocked.append(box['instance_id'])
        if (box['name']=='Front walkway' and a[0]<=lo[0] and b[0]>=hi[0] and a[1]<=lo[1] and b[1]>=hi[1]
                and 0.1<=lo[2]-b[2]<=5.0):supports.append(box['instance_id'])
    check(not blocked,'PlayerStart clearance blocked by: '+', '.join(blocked[:8]))
    check(supports,'PlayerStart needs a verified Front walkway support beneath the whole envelope')
    return dict(boxes_tested=len(boxes),radius_cm=radius,half_height_cm=half_height,
                location_cm=list(location),conservative_aabb_clear=True,support_ids=supports,
                note='Clear for this envelope and planned blockers only; actual gameplay pawn and spawn selection are unverified.')

def _sample_plan(contract,report):
    _fresh(contract)
    check(report.get('schema')==em.SCHEMA and report.get('phase')=='sample'
          and report.get('status')=='verified_persistence' and report.get('package_fingerprint')==contract['fingerprint'],
          'An explicit successful sample report from this corrected package is required')
    source=report.get('map_path','')
    check(re.fullmatch(r'/Game/EvergreenHandoff/Sample_[A-Za-z0-9_]+/Maps/L_Evergreen_sample',source),'Unexpected sample map path')
    return dict(mode='sample',source_map=source,target_map=source,lights=copy.deepcopy(LIGHTS),player_start=None)

def _pilot_plan(contract,full,collision,pilot):
    _fresh(contract);expected=ep.make_plan(contract,full,collision)
    check(pilot.get('schema')=='evergreen-prop-actor-pilot-v1' and pilot.get('status')=='verified_pilot_persistence'
          and pilot.get('package_fingerprint')==contract['fingerprint'] and pilot.get('source_map')==expected['source_map'],
          'An explicit successful pilot report from this fresh run is required')
    source=pilot.get('target_map','')
    check(re.fullmatch(re.escape(expected['source_map'])+r'_PropPilot_[A-Za-z0-9_]+',source),'Unexpected pilot map path')
    actual=pilot.get('plan',{});check(actual.get('collision_plan')==expected['collision_plan'],'Pilot collision plan differs')
    check(actual.get('remaining_scene',{}).get('map_path')==source,'Pilot remaining scene refers to another map')
    check(len(actual.get('promoted',[]))==4,'Expected four pilot props')
    fields=('instance_id','asset_id','source_group','source_index','target_placement','mesh_path','canonical_bounds_cm')
    for a,b in zip(actual['promoted'],expected['promoted']):
        check(all(a.get(k)==b.get(k) for k in fields),'Pilot membership or placement differs')
        check(a.get('actor_path','').startswith(source+'.'),'Pilot actor path does not belong to reported map')
    check(expected['collision_plan']['box_count']==568,'Unexpected collision policy; re-review PlayerStart')
    clear=clearance(expected['collision_plan']['boxes'])
    return dict(mode='pilot',source_map=source,lights=copy.deepcopy(LIGHTS),
                player_start=dict(key='PlayerStart',actor='PlayerStart',component='CapsuleComponent',
                                  location=list(START),rotation=[0,-90,0]),clearance=clear,pilot_plan=copy.deepcopy(actual))

def _components(actor,cls):
    result=actor.get_components_by_class(cls)
    check(len(result)==1,'Expected exactly one '+cls.__name__+' on '+actor.get_name());return result[0]

def _api(u, plan):
    """All class, function, enum and property lookups happen before map mutation."""
    required={
        'LevelEditorSubsystem':('get_current_level','new_level_from_template','save_current_level','load_level','is_in_play_in_editor'),
        'EditorActorSubsystem':('spawn_actor_from_class','get_all_level_actors'),
        'Actor':('get_actor_transform','get_components_by_class','set_actor_label','set_actor_rotation'),
        'DirectionalLightComponent':('set_intensity','set_light_color','set_mobility'),
        'PointLightComponent':('set_intensity','set_light_color','set_mobility','set_attenuation_radius','set_intensity_units','set_use_inverse_squared_falloff'),
        'EditorLoadingAndSavingUtils':('get_dirty_map_packages','get_dirty_content_packages'),
    }
    if plan['player_start']:required['CapsuleComponent']=('get_scaled_capsule_radius','get_scaled_capsule_half_height')
    for name,methods in required.items():
        check(hasattr(u,name),'Required Unreal class missing: '+name)
        for method in methods:check(hasattr(getattr(u,name),method),'Required Unreal API missing: '+name+'.'+method)
    for owner,member in [('ComponentMobility','MOVABLE'),('LightUnits','LUMENS')]:
        check(hasattr(u,owner) and hasattr(getattr(u,owner),member),'Required Unreal enum missing: '+owner+'.'+member)
    check(hasattr(u,'get_default_object'),'Unreal get_default_object unavailable')
    for item in plan['lights']+([plan['player_start']] if plan['player_start'] else []):
        check(hasattr(u,item['actor']) and hasattr(u,item['component']),'Required preview actor/component class unavailable')
        default=u.get_default_object(getattr(u,item['actor']))
        default.get_editor_property('tags');component=_components(default,getattr(u,item['component']))
        if item['actor']=='PlayerStart':
            r=component.get_scaled_capsule_radius();h=component.get_scaled_capsule_half_height()
            check(0<r<=RADIUS_CM and r<=h<=HALF_HEIGHT_CM,'Default PlayerStart capsule exceeds approved clearance envelope')
            component.get_world_transform()
        else:
            for prop in ('intensity','light_color','mobility','cast_shadows'):component.get_editor_property(prop)
            if item['actor']=='PointLight':
                for prop in ('attenuation_radius','intensity_units','use_inverse_squared_falloff'):component.get_editor_property(prop)
    return True

def _current(u):return u.get_editor_subsystem(u.LevelEditorSubsystem).get_current_level().get_path_name().split('.')[0]

def _actors(u):return u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()

def _tagged(u):return [a for a in _actors(u) if TAG in [str(t) for t in a.get_editor_property('tags')]]

def _preflight(u,plan):
    _api(u,plan);level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(not level.is_in_play_in_editor(),'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
          'Save all pending map and content changes before preview setup')
    check(_current(u)==plan['source_map'],'Open the exact fresh map shown by this preview dry run first')
    check(not _tagged(u),'Preview actors already exist; this command never repeats or deletes them')
    if plan['player_start']:check(not any(isinstance(a,u.PlayerStart) for a in _actors(u)),'Existing PlayerStart found; refusing ambiguous extra start')

def _spawn(u,item):
    system=u.get_editor_subsystem(u.EditorActorSubsystem)
    actor=system.spawn_actor_from_class(getattr(u,item['actor']),u.Vector(*item['location']),transient=False)
    check(isinstance(actor,getattr(u,item['actor'])),'Preview actor spawn failed: '+item['key'])
    actor.set_actor_label('EM_PREVIEW_'+item['key']);actor.set_editor_property('tags',[TAG,'EMPreview='+item['key']])
    p,y,r=item['rotation'];actor.set_actor_rotation(u.Rotator(pitch=p,yaw=y,roll=r),teleport_physics=True)
    component=_components(actor,getattr(u,item['component']))
    if item['actor']!='PlayerStart':
        component.set_mobility(u.ComponentMobility.MOVABLE)
        component.set_light_color(u.LinearColor(1,1,1,1));component.set_intensity(item['intensity'])
        component.set_editor_property('cast_shadows',item['actor']=='DirectionalLight')
        if item['actor']=='PointLight':
            component.set_use_inverse_squared_falloff(True);component.set_intensity_units(u.LightUnits.LUMENS)
            component.set_attenuation_radius(item['radius']);component.set_intensity(item['intensity'])
    return actor

def _verify(u,plan):
    expected={i['key']:i for i in plan['lights']+([plan['player_start']] if plan['player_start'] else [])};seen=set()
    for actor in _tagged(u):
        keys=[str(t)[10:] for t in actor.get_editor_property('tags') if str(t).startswith('EMPreview=')]
        check(len(keys)==1 and keys[0] in expected and keys[0] not in seen,'Unexpected/duplicate preview actor')
        key=keys[0];seen.add(key);item=expected[key];check(isinstance(actor,getattr(u,item['actor'])),'Preview actor class mismatch')
        p,y,r=item['rotation'];target=u.Transform(location=u.Vector(*item['location']),rotation=u.Rotator(pitch=p,yaw=y,roll=r),scale=u.Vector(1,1,1))
        check(actor.get_actor_transform().is_near_equal(target,location_tolerance=0.1,rotation_tolerance=0.001,scale3d_tolerance=0.0001),'Preview transform changed')
        c=_components(actor,getattr(u,item['component']))
        if item['actor']=='PlayerStart':
            check(c.get_world_transform().is_near_equal(target,location_tolerance=0.1,rotation_tolerance=0.001,scale3d_tolerance=0.0001),'PlayerStart capsule not centered/upright')
            check(0<c.get_scaled_capsule_radius()<=RADIUS_CM and c.get_scaled_capsule_radius()<=c.get_scaled_capsule_half_height()<=HALF_HEIGHT_CM,'PlayerStart capsule exceeds verified envelope')
            clearance(plan['pilot_plan']['collision_plan']['boxes'])
        else:
            check(c.get_editor_property('mobility')==u.ComponentMobility.MOVABLE,'Preview light mobility changed')
            check(abs(c.get_editor_property('intensity')-item['intensity'])<0.01,'Preview light intensity changed')
            col=c.get_editor_property('light_color');check((col.r,col.g,col.b)==(255,255,255),'Preview light is not neutral white')
            check(bool(c.get_editor_property('cast_shadows'))==(item['actor']=='DirectionalLight'),'Preview shadow policy changed')
            if item['actor']=='PointLight':
                check(abs(c.get_editor_property('attenuation_radius')-item['radius'])<0.01,'Preview radius changed')
                check(c.get_editor_property('intensity_units')==u.LightUnits.LUMENS and c.get_editor_property('use_inverse_squared_falloff'),'Preview light units/falloff changed')
    check(seen==set(expected),'Preview actor count changed')
    return dict(lights=len(plan['lights']),player_starts=bool(plan['player_start']),transforms_components_and_settings_verified=True)

def _copy_pilot_plan(plan,target):
    out=copy.deepcopy(plan);source=out['source_map'];out['target_map']=target
    out['pilot_plan']['remaining_scene']['map_path']=target
    for p in out['pilot_plan']['promoted']:
        check(p['actor_path'].startswith(source+'.'),'Unexpected pilot actor identity')
        prefix=source+'.'+source.rsplit('/',1)[-1]+':PersistentLevel.'
        check(p['actor_path'].startswith(prefix),'Unexpected map-object actor path')
        p['actor_path']=target+'.'+target.rsplit('/',1)[-1]+':PersistentLevel.'+p['actor_path'][len(prefix):]
    return out

def _execute(u,contract,plan,report,*,backup_confirmed):
    check(backup_confirmed is True,'Save/backup first, then pass backup_confirmed=True')
    _preflight(u,plan)
    if plan['mode']=='sample':em.verify_scene(u,report)
    else:ep.verify(u,plan['pilot_plan']);ec._check_original_collision(u,contract)
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    if plan['mode']=='pilot':
        target=plan['source_map']+'_Preview_'+stamp
        check(not (Path(u.Paths.project_content_dir()).resolve()/(target[6:]+'.umap')).exists(),'Preview destination already exists')
        plan=_copy_pilot_plan(plan,target)
    output=Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff'/('Preview_'+stamp)
    output.mkdir(parents=True,exist_ok=False);path=output/'preview_report.json'
    result=dict(schema=SCHEMA,status='started',mode=plan['mode'],source_map=plan['source_map'],target_map=plan['target_map'],
                package_fingerprint=contract['fingerprint'],plan=plan,unreal_runtime_previously_tested=False,
                note='Preview only. Actual pawn size, GameMode spawn choice, gameplay input and exposure/lighting quality require in-editor review.')
    def save():path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    save()
    try:
        if plan['mode']=='pilot':
            check(level.new_level_from_template(plan['target_map'],plan['source_map']),'Could not copy pilot map')
            check(_current(u)==plan['target_map'],'Wrong preview map loaded');ep.verify(u,plan['pilot_plan'])
        old_names={a.get_name() for a in _actors(u)}
        for item in plan['lights']+([plan['player_start']] if plan['player_start'] else []):_spawn(u,item)
        result['before_save']=_verify(u,plan)
        check({a.get_name() for a in _actors(u) if TAG not in [str(t) for t in a.get_editor_property('tags')]}==old_names,'Existing actor membership changed')
        if plan['mode']=='sample':em.verify_scene(u,report)
        else:ep.verify(u,plan['pilot_plan'])
        check(level.save_current_level(),'Preview map save failed')
        check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Preview map remains dirty; refusing reload')
        check(level.load_level(plan['target_map']),'Preview map reload failed')
        check(_current(u)==plan['target_map'],'Wrong map after reload')
        result['after_reload']=_verify(u,plan)
        check({a.get_name() for a in _actors(u) if TAG not in [str(t) for t in a.get_editor_property('tags')]}==old_names,'Existing actors changed after reload')
        if plan['mode']=='sample':em.verify_scene(u,report)
        else:ep.verify(u,plan['pilot_plan']);ec._check_original_collision(u,contract)
        result['status']='verified_preview_persistence';save()
        u.log('Optional preview persisted. Review Lit view and test actual gameplay pawn separately. Report: '+str(path));return str(path)
    except Exception as exc:
        result.update(status='failed_partial_preview',error=str(exc));save()
        u.log_error('Preview stopped; do not rerun blindly. Inspect this report and the partial map: '+str(path));raise

def editor_preflight(plan,contract,report=None):
    """Read-only editor checks, also used automatically by dry-run when Unreal is available."""
    try:
        import unreal as u
    except ModuleNotFoundError as exc:
        if exc.name!='unreal':raise
        return {'editor_available':False,'editor_checks_run':False}
    _preflight(u,plan)
    if plan['mode']=='sample':em.verify_scene(u,report)
    else:ep.verify(u,plan['pilot_plan']);ec._check_original_collision(u,contract)
    return {'editor_available':True,'editor_checks_run':True}

def light_sample(package_root,sample_import_report,*,execute=False,backup_confirmed=False):
    contract=em.load_contract(package_root);report=_read(sample_import_report);plan=_sample_plan(contract,report)
    if not execute:
        plan['preflight']=editor_preflight(plan,contract,report);print(json.dumps(plan,indent=2));return plan
    import unreal as u
    return _execute(u,contract,plan,report,backup_confirmed=backup_confirmed)

def run(package_root,full_import_report,collision_report,pilot_report,*,execute=False,backup_confirmed=False):
    contract=em.load_contract(package_root);full=_read(full_import_report);collision=_read(collision_report);pilot=_read(pilot_report)
    plan=_pilot_plan(contract,full,collision,pilot)
    if not execute:
        plan['preflight']=editor_preflight(plan,contract,pilot)
        summary={k:v for k,v in plan.items() if k!='pilot_plan'};print(json.dumps(summary,indent=2));return summary
    import unreal as u
    return _execute(u,contract,plan,pilot,backup_confirmed=backup_confirmed)
