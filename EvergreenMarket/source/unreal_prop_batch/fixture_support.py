"""Lighting-only, copied-map patch. Dry-run default. No Unreal execution claimed."""
import copy
import hashlib
import importlib
import json
import math
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

TAG = 'EvergreenFixturePointsV1'
PREFIX = 'EMFixture='
HELPERS = ('import_supermarket_unreal','setup_market_collision','setup_prop_actor_pilot','fresh_preview_setup','fresh_market_source_v2')
DEFAULT_STATE = r'C:\Art\Evergreen_Native_Run_01\run_state.json'
def check(ok, message):
    if not ok: raise ValueError(message)
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load_helpers(state_file):
    path=Path(state_file).resolve(); state=read(path)
    check(state.get('schema')=='evergreen-native-fresh-run-v2','Expected exact native source-v2 state')
    source=Path(state['merged_package']).resolve()/'source'/'unreal'
    for name in HELPERS:
        file=source/(name+'.py')
        check(sha(file)==state['helper_hashes'][name+'.py'],'Frozen helper hash mismatch: '+name)
        old=sys.modules.get(name)
        check(old is None or Path(old.__file__).resolve()==file,'Different helper already loaded: restart Unreal, then run only Start_Fixture_Lights.py')
    sys.path.insert(0,str(source))
    try: modules=[importlib.import_module(name) for name in HELPERS]
    finally: sys.path.pop(0)
    return modules

def verified_context(state_file):
    em,ec,ep,fp,fw=load_helpers(state_file)
    path,state,c=fw.load_state(state_file)
    check(state.get('completed')==list(fw.STAGES),'Complete the source-v2 lighting stage first')
    hashes={str(path):sha(path)}; reports={}
    for stage in fw.STAGES:
        p=Path(state['reports'][stage]).resolve()
        check(sha(p)==state['report_hashes'][stage],'Saved stage report hash mismatch: '+stage)
        reports[stage]=read(p);fw._check_report(stage,reports[stage],c,state);hashes[str(p)]=sha(p)
    base=fp._pilot_plan(c,reports['full'],reports['collision'],reports['pilot'])
    preview=reports['lighting']; final=preview['target_map']
    check(re.fullmatch(re.escape(base['source_map'])+r'_Preview_[A-Za-z0-9_]+',final),'Final lighting map identity mismatch')
    mapped=fp._copy_pilot_plan(base,final)
    check(preview.get('plan')==mapped,'Final preview report plan differs from verified source-v2 plan')
    check(mapped['pilot_plan']['collision_plan']['box_count']==694 and len(mapped['pilot_plan']['promoted'])==4,'Expected 694 collision boxes and four props')
    for name in HELPERS: hashes[str(Path(state['merged_package'])/'source'/'unreal'/(name+'.py'))]=state['helper_hashes'][name+'.py']
    return dict(em=em,ec=ec,ep=ep,fp=fp,contract=c,state=state,hashes=hashes,preview=mapped,source_map=final)

def unchanged(hashes):
    for p,h in hashes.items(): check(sha(p)==h,'Protected state/report/helper changed: '+p)

def layout_plan(path,c):
    data=read(path)
    check(data.get('schema')=='evergreen-fixture-point-layout-v1','Unexpected fixture layout schema')
    check(data.get('source_manifest_sha256')==sha(c['root']/'manifest.json'),'Fixture layout source manifest differs')
    placements={p['instance_id']:p for p in c['placements']}
    expected={p['instance_id'] for p in c['placements'] if c['assets'][p['asset_id']]['name'] in ('Opal LED diffuser','Canopy linear light','Exterior wall lamp')}
    result=[]; seen=set(); keys=set()
    for row in data['lights']:
        iid=row['source_fixture_instance_id'];key=row['key'];p=placements.get(iid)
        check(iid in expected and iid not in seen and key not in keys,'Unknown/duplicate fixture identity')
        seen.add(iid);keys.add(key)
        check(re.fullmatch(r'[A-Za-z0-9_]+',key),'Invalid fixture key')
        rotation=row['rotation_degrees_pitch_yaw_roll'];check(len(rotation)==3 and all(math.isfinite(x) for x in rotation),'Invalid rotation')
        check(isinstance(row['cast_shadows'],bool),'Shadow setting must be boolean')
        check(row['actor']=='PointLight' and row['component']=='PointLightComponent','Only PointLight is allowed')
        check(row['scale']==[1,1,1] and row['mobility']=='Movable' and row['intensity_unit']=='lumens','Invalid unit-scale/mobility/units')
        check(row['color_linear_rgba']==[1,1,1,1] and row['use_inverse_squared_falloff'] is True,'Expected neutral inverse-square points')
        check(row['source_fixture_asset_id']==p['asset_id'] and row['source_fixture_bottom_cm']==p['location_cm'],'Fixture provenance mismatch')
        loc=row['location_cm'];check(len(loc)==3 and all(math.isfinite(x) for x in loc),'Invalid location')
        check(sum((loc[i]-p['location_cm'][i])**2 for i in range(3))<=30**2,'Point must remain within 30 cm of its source fixture pivot')
        meters=row['fixture_point_position_m'];check(all(abs(loc[i]-meters[i]*scale)<0.01 for i,scale in enumerate((100,-100,100))),'Blender-meter to Unreal-centimeter conversion mismatch')
        for field in ('intensity','attenuation_radius_cm','source_radius_cm','soft_source_radius_cm','source_length_cm'):
            check(math.isfinite(row[field]) and row[field]>=0,'Invalid light setting: '+field)
        check(row['intensity']>0 and row['attenuation_radius_cm']>0,'Positive intensity/radius required')
        item=copy.deepcopy(row);item.update(location=loc,rotation=row['rotation_degrees_pitch_yaw_roll'],radius=row['attenuation_radius_cm']);result.append(item)
    check(seen==expected and len(result)==data['source_fixture_count'],'Expected one point for each approved source fixture')
    return result

def normalized_path(path,current):
    prefix=current+'.'+current.rsplit('/',1)[-1]
    return '@MAP@'+path[len(prefix):] if path.startswith(prefix) else path

def scalar(value,current):
    if value is None or isinstance(value,(bool,int,float,str)):return value
    if hasattr(value,'get_path_name'):return normalized_path(value.get_path_name(),current)
    if hasattr(value,'export_text'):return value.export_text()
    if hasattr(value,'r') and hasattr(value,'g'):return [value.r,value.g,value.b,getattr(value,'a',255)]
    try:return [scalar(v,current) for v in value]
    except TypeError:return str(value)

# Stable user lighting settings only: exclude GUIDs, delegates, tick state and
# copy-generated identity. Unsupported subclass settings are recorded explicitly.
def light_properties(component,current):
    names=set(('intensity','light_color','mobility','cast_shadows','visible','affects_world','indirect_lighting_intensity','volumetric_scattering_intensity'))
    required=names.copy()
    names.update('temperature use_temperature attenuation_radius intensity_units use_inverse_squared_falloff source_radius soft_source_radius source_length source_width source_height inner_cone_angle outer_cone_angle light_falloff_exponent indirect_lighting_intensity volumetric_scattering_intensity specular_scale diffuse_scale cast_dynamic_shadows cast_static_shadows cast_translucent_shadows cast_volumetric_shadow affect_translucent_lighting affect_global_illumination affect_reflection ies_texture ies_brightness_scale use_ies_brightness light_function_material light_function_scale light_function_fade_distance disabled_brightness lighting_channels shadow_bias shadow_slope_bias shadow_resolution_scale shadow_sharpen contact_shadow_length contact_shadow_length_in_ws inverse_exposure_blend max_draw_distance max_distance_fade_range lightmass_settings source_angle source_soft_angle atmosphere_sun_light atmosphere_sun_light_index dynamic_shadow_distance_movable_light dynamic_shadow_distance_stationary_light dynamic_shadow_cascades cascade_distribution_exponent cascade_transition_fraction shadow_distance_fadeout_fraction distance_field_shadow_distance lower_hemisphere_is_black lower_hemisphere_color cubemap source_type source_cubemap_angle sky_distance_threshold occlusion_max_distance contrast occlusion_exponent min_occlusion occlusion_tint real_time_capture capture_emissive_only cubemap_resolution occlusion_combine_mode cloud_ambient_occlusion cloud_ambient_occlusion_strength cloud_ambient_occlusion_extent cloud_ambient_occlusion_aperture_scale cloud_ambient_occlusion_map_resolution_scale hidden_in_game component_tags barn_door_angle barn_door_length source_texture'.split())
    out={}
    for k in sorted(names):
        if k.startswith('on_') or k.endswith('_delegate') or k=='primary_component_tick':continue
        try:out[k]=scalar(component.get_editor_property(k),current)
        except Exception:
            if k in required:raise
            out[k]={'unsupported_property':True}
    return out

def snapshot(u,ctx,excluded):
    fp=ctx['fp'];current=fp._current(u);out={}
    for a in fp._actors(u):
        if a.get_name() in excluded:continue
        row=dict(path=normalized_path(a.get_path_name(),current),actor_class=a.get_class().get_path_name(),label=a.get_actor_label(),tags=sorted(str(t) for t in a.get_editor_property('tags')),transform=fp._transform_data(a.get_actor_transform()))
        components=a.get_components_by_class(u.LightComponentBase)
        if components:
            row['light_components']={c.get_name():dict(settings=light_properties(c,current),world_transform=fp._transform_data(c.get_world_transform())) for c in components}
        out[a.get_name()]=row
    return out

def old_lights(u,ctx):
    fp=ctx['fp'];expected={i['key']:i for i in ctx['preview']['lights']};found={}
    for a in fp._actors(u):
        tags=[str(t) for t in a.get_editor_property('tags')]
        check(TAG not in tags and not any(t.startswith(PREFIX) for t in tags),'Fixture patch already present; never rerun on a patched/partial map')
        if fp.TAG not in tags:continue
        keys=[t[10:] for t in tags if t.startswith('EMPreview=')]
        check(len(keys)==1,'Ambiguous old preview identity; nothing deleted')
        key=keys[0]
        if key=='PlayerStart':
            check(isinstance(a,u.PlayerStart),'Preview PlayerStart class changed');continue
        check(key in expected and key not in found,'Unknown/duplicate old preview key; nothing deleted')
        item=expected[key]
        check(a.get_class()==getattr(u,item['actor']).static_class(),'Old preview exact class mismatch')
        check(a.get_actor_label()=='EM_PREVIEW_'+key,'Old preview label mismatch')
        check(normalized_path(a.get_path_name(),fp._current(u)).startswith('@MAP@:PersistentLevel.'),'Old preview actor outside current map')
        found[key]=a
    check(set(found)==set(expected) and len(found)==11,'Expected exactly 11 old generated preview lights')
    return found

def clean(u):
    check(not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),'Stop Play In Editor first')
    check(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Save all pending map/content edits first; patch never discards dirty changes')

def remap_pilot(fp,preview,source,target):
    p=copy.deepcopy(preview);p['source_map']=source
    return fp._copy_pilot_plan(p,target)['pilot_plan']

def preflight(u,ctx,items):
    fp=ctx['fp'];clean(u)
    check(fp._current(u)==ctx['source_map'],'Open the successful final source-v2 Preview map from this run state first')
    fp._api(u,dict(lights=items,player_start=None))
    for method in ('destroy_actor',):check(hasattr(u.EditorActorSubsystem,method),'Missing API '+method)
    for method in ('set_source_radius','set_soft_source_radius','set_source_length'):check(hasattr(u.PointLightComponent,method),'Missing point API '+method)
    check(hasattr(u,'LightComponentBase'),'Missing light snapshot API')
    fp._components(u.get_default_object(u.PointLight),u.PointLightComponent).get_editor_property('use_temperature')
    pilot=ctx['preview']['pilot_plan'];ctx['ep'].verify(u,pilot);ctx['ec']._check_original_collision(u,ctx['contract'])
    found=old_lights(u,ctx)
    before=snapshot(u,ctx,{a.get_name() for a in found.values()})
    diagnostics={k:dict(actor_path=a.get_path_name(),transform=fp._transform_data(a.get_actor_transform()),settings=light_properties(fp._components(a,getattr(u,next(i['component'] for i in ctx['preview']['lights'] if i['key']==k))),fp._current(u))) for k,a in found.items()}
    manual_directionals=[a.get_actor_label() for a in fp._actors(u) if isinstance(a,u.DirectionalLight) and a not in found.values()]
    return found,before,diagnostics,manual_directionals

def spawn(u,fp,item):
    system=u.get_editor_subsystem(u.EditorActorSubsystem)
    actor=system.spawn_actor_from_class(u.PointLight,u.Vector(*item['location']),transient=False)
    check(isinstance(actor,u.PointLight),'Fixture spawn failed: '+item['key'])
    actor.set_actor_label('EM_FIXTURE_'+item['key']);actor.set_editor_property('tags',[TAG,PREFIX+item['key'],'EMSourceFixture='+item['source_fixture_instance_id']])
    fp._configure(u,actor,item)  # Explicit full transform including unit scale.
    c=fp._components(actor,u.PointLightComponent)
    c.set_editor_property('cast_shadows',item['cast_shadows']);c.set_editor_property('use_temperature',False)
    c.set_source_radius(item['source_radius_cm']);c.set_soft_source_radius(item['soft_source_radius_cm']);c.set_source_length(item['source_length_cm'])
    return actor

def verify_points(u,ctx,items):
    fp=ctx['fp'];expected={i['key']:i for i in items};found={}
    for a in fp._actors(u):
        tags=[str(t) for t in a.get_editor_property('tags')]
        check(not (fp.TAG in tags and any(t.startswith('EMPreview=') and t!='EMPreview=PlayerStart' for t in tags)),'Old generated light remains')
        if TAG not in tags:continue
        keys=[t[len(PREFIX):] for t in tags if t.startswith(PREFIX)]
        check(len(keys)==1 and keys[0] in expected and keys[0] not in found,'Invalid/duplicate fixture light')
        key=keys[0];item=expected[key];found[key]=a
        check(a.get_class()==u.PointLight.static_class(),'Non-point fixture actor found')
        check('EMSourceFixture='+item['source_fixture_instance_id'] in tags,'Fixture source tag mismatch')
        check(fp._transform_diagnostic(a,item,fp._target_transform(u,item))['matches'],'Fixture transform mismatch')
        c=fp._components(a,u.PointLightComponent)
        for prop,value in [('intensity',item['intensity']),('attenuation_radius',item['radius']),('source_radius',item['source_radius_cm']),('soft_source_radius',item['soft_source_radius_cm']),('source_length',item['source_length_cm'])]:check(abs(c.get_editor_property(prop)-value)<.01,'Fixture setting mismatch: '+prop)
        check(c.get_editor_property('mobility')==u.ComponentMobility.MOVABLE and c.get_editor_property('intensity_units')==u.LightUnits.LUMENS and c.get_editor_property('use_inverse_squared_falloff'),'Fixture mobility/unit/falloff mismatch')
        check(c.get_editor_property('cast_shadows')==item['cast_shadows'],'Fixture shadows mismatch')
        check(c.get_editor_property('use_temperature') is False,'Fixture temperature must be disabled for neutral white')
        color=c.get_editor_property('light_color');check((color.r,color.g,color.b)==(255,255,255),'Fixture color mismatch')
    check(set(found)==set(expected),'Fixture count mismatch')
    return {a.get_name() for a in found.values()}

def run(state_file=DEFAULT_STATE,layout_file=None,*,execute=False,backup_confirmed=False):
    ctx=verified_context(state_file);fp=ctx['fp']
    layout_file=Path(layout_file or Path(__file__).with_name('fixture_point_layout_v1.json')).resolve()
    items=layout_plan(layout_file,ctx['contract']);ctx['hashes'][str(layout_file)]=sha(layout_file)
    import unreal as u
    found,before,diagnostics,warnings=preflight(u,ctx,items)
    result=dict(schema='evergreen-fixture-patch-v1',status='dry_run',source_map=ctx['source_map'],protected_hashes=ctx['hashes'],old_generated_lights=diagnostics,point_light_count=len(items),lights=items,preserved_actor_snapshot=before,preserved_manual_directional_lights=warnings,unreal_runtime_previously_tested=False)
    if warnings:u.log_warning('Manual directional lights will be preserved: '+', '.join(warnings))
    if not execute:
        print(json.dumps(result,indent=2));return result
    check(backup_confirmed is True,'Back up project/save all, then pass backup_confirmed=True')
    unchanged(ctx['hashes']);clean(u)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    target=ctx['source_map']+'_FixtureLights_'+stamp
    check(not (Path(u.Paths.project_content_dir()).resolve()/(target[6:]+'.umap')).exists(),'Destination already exists')
    output=Path(u.Paths.project_saved_dir()).resolve()/'EvergreenHandoff'/('FixtureLights_'+stamp);output.mkdir(parents=True,exist_ok=False)
    report=output/'fixture_lights_report.json';result.update(status='started',target_map=target)
    def save():report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    save();level=u.get_editor_subsystem(u.LevelEditorSubsystem);system=u.get_editor_subsystem(u.EditorActorSubsystem)
    try:
        check(level.new_level_from_template(target,ctx['source_map']),'Map copy failed')
        check(fp._current(u)==target,'Wrong copied map')
        pilot=remap_pilot(fp,ctx['preview'],ctx['source_map'],target)
        ctx['ep'].verify(u,pilot)
        copied=old_lights(u,ctx)
        check(snapshot(u,ctx,{a.get_name() for a in copied.values()})==before,'Preserved actors differ in copied map; stopping')
        for key,a in copied.items():check(system.destroy_actor(a) is True,'Could not remove exact generated light '+key)
        for item in items:spawn(u,fp,item)
        new=verify_points(u,ctx,items);check(snapshot(u,ctx,new)==before,'Preserved actor/light settings changed before save')
        result['before_save']=ctx['ep'].verify(u,pilot);ctx['ec']._check_original_collision(u,ctx['contract']);unchanged(ctx['hashes'])
        check(level.save_current_level(),'Map save failed');clean(u)
        check(level.load_level(target),'Saved map reload failed');check(fp._current(u)==target,'Wrong reloaded map')
        new=verify_points(u,ctx,items);check(snapshot(u,ctx,new)==before,'Preserved actor/light settings changed after reload')
        result['after_reload']=ctx['ep'].verify(u,pilot);ctx['ec']._check_original_collision(u,ctx['contract']);unchanged(ctx['hashes'])
        result.update(status='verified_fixture_lights_persistence',preserved_actor_state=True);save();u.log('Fixture lights saved to new map. Report: '+str(report));return str(report)
    except Exception as exc:
        result.update(status='failed_partial_fixture_patch',error=str(exc));save()
        u.log_error('STOP. Do not rerun or discard dirty changes. Inspect partial map and report: '+str(report));raise
