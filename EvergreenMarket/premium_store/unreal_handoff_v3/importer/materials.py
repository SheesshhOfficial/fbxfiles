"""Conservative Unreal PBR and exact-profile optical material builder. Default is host-safe dry run.

Offline: python create_materials.py --export EXPORT_DIR --destination /Game/Evergreen/Materials_v001 --plan PLAN.json
Unreal editor: import create_materials; create_materials.main([...,'--apply'])
Actual Unreal execution has NOT been tested. Wrapped by the version-guarded v3 importer.
"""
import argparse,hashlib,json,re,sys,math
from pathlib import Path

PROPERTIES={'Base Color':'MP_BASE_COLOR','Metallic':'MP_METALLIC','Roughness':'MP_ROUGHNESS','Normal':'MP_NORMAL','Specular IOR Level':'MP_SPECULAR','Opacity':'MP_OPACITY','Refraction':'MP_REFRACTION','Emissive':'MP_EMISSIVE_COLOR'}
SOURCE_PROPERTIES={k:v for k,v in PROPERTIES.items() if k not in {'Opacity','Refraction','Emissive'}}
EMISSION_PROFILES=json.loads(Path(__file__).with_name('emission_profiles.json').read_text())['profiles']
PRINCIPLED_EMISSION_PROFILES={'EXT2_Warm_LED': {'expected_source_rgb':[1,.72,.37], 'expected_source_strength':4.0, 'artistic_multiplier':4.0}}
OPTICAL_PROFILES=json.loads(Path(__file__).with_name('optical_profiles.json').read_text())['profiles']

def finite_values(value):
    if isinstance(value,(int,float)):return math.isfinite(value)
    if isinstance(value,dict):return all(finite_values(v) for v in value.values())
    if isinstance(value,(list,tuple)):return all(finite_values(v) for v in value)
    return True

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stable(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()[:10]
def safe(name):return re.sub('[^A-Za-z0-9_]+','_',name).strip('_')[:80]
def read(path):return json.loads(Path(path).read_text())
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')

def destination_guard(destination):
    if not re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+_v[0-9]+',destination):
        raise ValueError('Destination must be a NEW versioned folder such as /Game/Evergreen/Materials_v001; /Game and existing folders are forbidden')

def inspect_material(material):
    errors=[];channels={};values=material.get('channels',{});links=material.get('links',[]);nodes={n['name']:n for n in material.get('node_graph',[])};images={i['node']:i for i in material.get('images',[]) if 'node' in i};p=material.get('principled_node')
    if not finite_values(material):return {},['Nonfinite material input']
    output_name=material.get('active_output_node')
    if material.get('displacement_linked') or material.get('volume_linked') or any(l['to_socket'] in {'Volume','Displacement'} and (l['to_node']==output_name if output_name else nodes.get(l['to_node'],{}).get('type')=='OUTPUT_MATERIAL') for l in links):errors.append('Linked displacement/volume shader is unsupported')
    ep=EMISSION_PROFILES.get(material['material'])
    if ep and material.get('surface_shader_type')!='EMISSION':errors.append('Emission profile source shader type changed')
    if ep and material.get('surface_shader_type')=='EMISSION':
        inputs=material.get('surface_inputs',{});color=inputs.get('Color',{});strength=inputs.get('Strength',{})
        if color.get('linked',True) or strength.get('linked',True):errors.append('Approved emission profile requires constant color and strength')
        elif max(abs(a-b) for a,b in zip(color['value'][:3],ep['expected_source_rgb']))>1e-5 or abs(strength['value']-ep['expected_source_strength'])>1e-5:errors.append('Emission profile source signature changed')
        else:channels['Emissive']={'kind':'constant','value':[v*ep['artistic_multiplier'] for v in color['value'][:3]]+[1]}
        return channels,errors
    if material.get('surface_shader_type')!='BSDF_PRINCIPLED' or material.get('surface_shader_node')!=p:
        errors.append('Only a direct Principled BSDF surface is supported; emission-only/mixed/other shaders require a reviewed engine material')
    for key in ('Coat Weight','Subsurface Weight','Sheen Weight','Anisotropic','Anisotropic IOR Level'):
        c=values.get(key,{'value':0,'linked':False})
        if c['linked'] or abs(float(c['value']))>1e-6:errors.append(key+' is nonzero/linked; explicit engine shader policy required')
    transmission=values.get('Transmission Weight',{'value':0,'linked':False});profile=OPTICAL_PROFILES.get(material['material'])
    if profile and not transmission['linked'] and abs(float(transmission['value'])-profile['expected_source_transmission'])>1e-5:errors.append('Optical profile source transmission signature changed')
    if transmission['linked']:errors.append('Linked transmission has no approved profile')
    elif float(transmission['value'])>1e-6:
        if profile is None:errors.append('Transmission material has no exact-name approved optical profile')
        elif abs(float(transmission['value'])-profile['expected_source_transmission'])>1e-5:errors.append('Optical profile source transmission signature changed')
        else:
            ior=values.get('IOR',{})
            if ior.get('linked',True) or not 1<=float(ior.get('value',0))<=2.5:errors.append('Optical profile requires constant source IOR in [1,2.5]')
            else:channels.update(Opacity={'kind':'constant','value':profile['opacity']},Refraction={'kind':'constant','value':float(ior['value'])})
    alpha=values.get('Alpha',{'value':1,'linked':False})
    if alpha['linked'] or float(alpha['value'])<.999999:errors.append('Alpha/transparency requires a reviewed blend/shading policy')
    emission=values.get('Emission Strength',{'value':0,'linked':False});color=values.get('Emission Color',{'value':[0,0,0,1],'linked':False})
    principled_emission=PRINCIPLED_EMISSION_PROFILES.get(material['material'])
    if principled_emission:
        if emission['linked'] or color['linked'] or abs(float(emission['value'])-principled_emission['expected_source_strength'])>1e-5 or max(abs(a-b) for a,b in zip(color['value'][:3],principled_emission['expected_source_rgb']))>1e-5:
            errors.append('Exact v3 Principled emission profile source signature changed')
        else:
            channels['Emissive']={'kind':'constant','value':[v*principled_emission['artistic_multiplier'] for v in color['value'][:3]]+[1]}
    elif emission['linked'] or color['linked'] or float(emission['value'])*max(color['value'][:3])>1e-6:errors.append('Emission requires approved radiometric/artistic intensity; no Blender-to-Unreal numeric copy')
    if material.get('procedural'):errors.append('Unbaked procedural texture graph')
    surface_inputs=material.get('surface_inputs',{})
    for key in ('Diffuse Roughness','Thin Film Thickness'):
        v=surface_inputs.get(key,{'value':0,'linked':False})
        if v['linked'] or abs(float(v['value']))>1e-6:errors.append(key+' is unsupported')
    tint=surface_inputs.get('Specular Tint',{'value':[1,1,1,1],'linked':False})
    if tint['linked'] or any(abs(float(v)-1)>1e-6 for v in tint['value'][:3]):errors.append('Nonwhite/linked Specular Tint is unsupported')
    if material.get('displacement_linked') or material.get('volume_linked'):errors.append('Linked displacement/volume shader is unsupported')
    def incoming(node,socket):return [l for l in links if l['to_node']==node and l['to_socket']==socket]
    for channel in SOURCE_PROPERTIES:
        edge=incoming(p,channel)
        if not edge:
            if channel!='Normal':
                v=values.get(channel)
                if v is None:errors.append('Missing source constant '+channel)
                else:channels[channel]={'kind':'constant','value':v['value']}
            continue
        if len(edge)!=1:errors.append('Multiple links for '+channel);continue
        origin=edge[0]['from_node'];normal_strength=1
        if channel=='Normal':
            node=nodes.get(origin,{})
            if node.get('type')!='NORMAL_MAP' or node.get('normal_space')!='TANGENT' or node.get('normal_strength_linked'):
                errors.append('Normal requires image-fed tangent NormalMap with constant strength');continue
            normal_strength=node['normal_strength']
            if not 0<=normal_strength<=1:errors.append('NormalMap strength outside [0,1] requires reviewed implementation');continue
            nested=incoming(origin,'Color')
            if len(nested)!=1:errors.append('NormalMap has no single image input');continue
            origin=nested[0]['from_node']
        if origin not in images:errors.append('Unsupported linked '+channel+' graph; image-to-channel only');continue
        image_settings=images[origin]
        if image_settings.get('projection')!='FLAT' or image_settings.get('extension')!='REPEAT' or image_settings.get('interpolation')!='Linear':errors.append('Image node requires reviewed FLAT / REPEAT / Linear sampling');continue
        source_output=nested[0]['from_socket'] if channel=='Normal' else edge[0]['from_socket']
        if channel=='Normal' and source_output!='Color':errors.append('Normal map requires RGB Color, never alpha');continue
        if source_output not in {'Color','Alpha'}:errors.append('Unsupported texture output '+source_output);continue
        channels[channel]={'kind':'texture','image':images[origin]['name'],'source_output':source_output,'normal_strength':normal_strength if channel=='Normal' else None,'normal_uv_map':node.get('uv_map') if channel=='Normal' else None}
    spec=channels.get('Specular IOR Level');ior=values.get('IOR',{})
    if spec:
        if spec['kind']!='constant' or ior.get('linked',True):errors.append('Specular conversion requires constant IOR and Specular IOR Level')
        elif not 1<=float(ior.get('value',0))<=2.5:errors.append('Specular conversion requires source IOR in [1,2.5]')
        else:
            source_ior=float(ior['value']);level=float(spec['value']);f0=((source_ior-1)/(source_ior+1))**2;engine_spec=f0*2*level/.08
            if not 0<=engine_spec<=1:errors.append('Source dielectric F0 exceeds bounded Unreal Specular range')
            elif 'Opacity' in channels and abs(level-.5)>1e-6:errors.append('Optical profile requires neutral source Specular IOR Level .5')
            else:spec.update(value=engine_spec,source_ior=source_ior,source_specular_ior_level=level,conversion='(((IOR-1)/(IOR+1))^2 * 2 * source_level) / 0.08')
    return channels,errors

def build_plan(export_dir,destination):
    destination_guard(destination);root=Path(export_dir).resolve();manifest=read(root/'EXPORT_VALIDATION_MANIFEST.json');contract=read(root/'MATERIAL_CONTRACT.json');uvdoc=read(root/'TEXTURE_UV_BINDINGS.json');images={x['name']:x for x in manifest['images']};uvs={}
    for a in uvdoc['assets']:
        for b in a['bindings']:uvs[(a['mesh'],b['slot'],b['image'])]=b
    material_by_name={m['material']:m for m in contract['materials']};materials={};textures={};texture_candidates={};assignments=[];blocked={}
    for asset in manifest['assets']:
        mesh=asset['mesh'];slots=asset['objects'][0]['materials']
        for index,name in enumerate(slots):
            source=material_by_name[name];channels,errors=inspect_material(source);resolved={}
            if 'Opacity' in channels and not asset.get('optical_slot_geometry',{}).get(str(index),{}).get('all_closed_outward',False):errors.append('Closed optical profile requires independently measured closed outward shells for this exact slot')
            for channel,value in channels.items():
                value=dict(value)
                if value['kind']=='texture':
                    im=images.get(value['image']);binding=uvs.get((mesh,index,value['image']))
                    if im is None or binding is None:errors.append('Missing image/UV contract for '+value['image']);continue
                    file=(root/im['path']).resolve()
                    if not file.is_relative_to(root) or not file.is_file() or digest(file)!=im['sha256']:raise ValueError('Missing/outside-package/hash-mismatched texture: '+str(file))
                    role='normal' if channel=='Normal' else 'color' if channel=='Base Color' else 'scalar';key=im['sha256']+'_'+role;texture_name='T_'+safe(Path(im['path']).stem)+'_'+stable(key)
                    desired_srgb=role=='color'
                    if channel=='Normal' and int(binding['uv_channel'])!=0:errors.append('Tangent normal UV channel is not 0; independently verified tangent basis is required')
                    if channel=='Normal' and (binding.get('normal_tangent_uv_channel')!=0 or binding.get('normal_tangent_uv_layer')!=binding['uv_layer']):errors.append('NormalMap tangent basis contract missing or different from sampled UV0')
                    if channel=='Normal' and value.get('normal_uv_map') and value['normal_uv_map']!=binding['uv_layer']:errors.append('NormalMap tangent UV name differs from texture sampling UV name')
                    if role=='scalar' and value['source_output']=='Color' and not im.get('rgb_channels_equal',False):errors.append('Scalar channel requires a grayscale RGB image or explicit alpha channel: '+value['image'])
                    if im['colorspace']!=('sRGB' if desired_srgb else 'Non-Color'):errors.append('Texture colorspace incompatible with '+channel+': '+value['image'])
                    tex=dict(name=texture_name,asset_path=destination+'/Textures/'+texture_name,source_file=str(file),sha256=im['sha256'],role=role,srgb=desired_srgb,virtual_texture_streaming=False,filter='TF_BILINEAR',address_x='TA_WRAP',address_y='TA_WRAP',flip_green_channel=role=='normal',compression='TC_NORMALMAP' if role=='normal' else 'TC_MASKS' if role=='scalar' else 'TC_DEFAULT')
                    tex=texture_candidates.setdefault(key,tex)
                    value.update(texture_key=key,texture=tex,uv_channel=int(binding['uv_channel']),uv_layer=binding['uv_layer'])
                resolved[channel]=value
            assignment=dict(mesh=mesh,slot=index,source_material=name)
            if errors:
                blocked.setdefault(name,dict(material=name,reasons=sorted(set(errors)),uses=[]))['uses'].append(dict(mesh=mesh,slot=index));assignment.update(status='MANUAL_MATERIAL_REQUIRED',material_path=None)
            else:
                key=stable({'source_material':name,'channels':resolved});material_name='M_'+safe(name)+'_'+key;path=destination+'/Materials/'+material_name
                optical='Opacity' in resolved
                policy=dict(blend_mode='BLEND_TRANSLUCENT' if optical else 'BLEND_OPAQUE',shading_model='MSM_UNLIT' if name in EMISSION_PROFILES else 'MSM_DEFAULT_LIT',two_sided=False,tangent_space_normal=True)
                if optical:policy.update(translucency_lighting_mode='TLM_SURFACE_PER_PIXEL_LIGHTING',refraction_method='RM_INDEX_OF_REFRACTION')
                materials[key]=dict(name=material_name,asset_path=path,source_material=name,channels=resolved,engine_properties=policy,shading_policy='REVIEWED_CLOSED_OPTICAL_APPROXIMATION' if optical else 'REVIEWED_OPAQUE_UNLIT_EMISSION_APPROXIMATION' if name in EMISSION_PROFILES else 'REVIEWED_OPAQUE_DEFAULT_LIT_EMISSION_APPROXIMATION' if name in PRINCIPLED_EMISSION_PROFILES else 'OPAQUE_DEFAULT_LIT_PBR',emission_profile=EMISSION_PROFILES.get(name) or PRINCIPLED_EMISSION_PROFILES.get(name),optical_profile=OPTICAL_PROFILES.get(name) if optical else None)
                for value in resolved.values():
                    if value['kind']=='texture':textures[value['texture_key']]=value['texture']
                assignment.update(status='PLANNED',material_path=path)
            assignments.append(assignment)
    return dict(schema='evergreen-unreal-material-plan-v1',mode='DRY_RUN',destination=destination,canonical_asset_count=len(manifest['assets']),canonical_material_slot_count=len(assignments),all_slots_supported=not blocked,export_source_sha256=manifest['source_sha256'],materials=list(materials.values()),textures=list(textures.values()),slot_assignments=assignments,blocked_materials=list(blocked.values()),unreal_execution_tested=False,
        policy=['No existing folders/assets may be changed or replaced.','No FBXs, meshes, maps, actors, lighting or gameplay are imported/modified by this helper.','Every image has an explicit TexCoord node with the recorded channel index.','OpenGL tangent normals import as NormalMap with green flipped for Unreal DirectX convention.','Only exact approved optical profiles receive translucent materials. Opaque labels/wood/stone stay opaque. Artistic optical opacity is not a physical transmission conversion. Unknown transmission/alpha/emission/subsurface/coat/other unsupported graphs block full apply. --allow-supported-subset explicitly creates only supported materials; unresolved slots stay listed.', 'Tangent normal maps require UV0. Strength in [0,1] uses normalize(lerp((0,0,1), decoded normal, strength)); other strengths are blocked.','Only the exact Warm opal diffuser and Cold opal diffuser names use reviewed opaque Unlit emission profiles; each multiplier is an artistic starting value, never a photometric conversion or light-creation instruction.', 'Actual Unreal API execution, shader compilation, render parity and save/reload require engine validation.'])

def apply_plan(plan,allow_supported_subset=False,ue=None):
    # Validate before importing Unreal or creating any external state.
    destination_guard(plan['destination'])
    if not finite_values(plan):raise ValueError('Nonfinite plan values are forbidden')
    if plan['blocked_materials'] and not allow_supported_subset:raise ValueError('Unsupported materials block full apply: '+', '.join(x['material'] for x in plan['blocked_materials'])+'. Review manual policies or explicitly use --allow-supported-subset.')
    if ue is None:
        import unreal as ue
    lib=ue.EditorAssetLibrary;dest=plan['destination']
    if lib.does_directory_exist(dest) or lib.list_assets(dest,recursive=True,include_folder=True):raise ValueError('Refusing existing destination folder: '+dest)
    for item in plan['materials']+plan['textures']:
        if not item['asset_path'].startswith(dest+'/') or lib.does_asset_exist(item['asset_path']):raise ValueError('Refusing existing/out-of-scope asset '+item['asset_path'])
    for texture in plan['textures']:
        if digest(texture['source_file'])!=texture['sha256']:raise ValueError('Texture bytes changed after dry run')
    # Guard API availability before creating any assets. Unsupported engine versions fail closed.
    enum_types={'blend_mode':'BlendMode','shading_model':'MaterialShadingModel','translucency_lighting_mode':'TranslucencyLightingMode','refraction_method':'RefractionMode'}
    for texture in plan['textures']:
        getattr(ue.TextureFilter,texture['filter']);getattr(ue.TextureAddress,texture['address_x']);getattr(ue.TextureAddress,texture['address_y']);getattr(ue.TextureCompressionSettings,texture['compression']);getattr(ue.MaterialSamplerType,{'normal':'SAMPLERTYPE_NORMAL','scalar':'SAMPLERTYPE_MASKS','color':'SAMPLERTYPE_COLOR'}[texture['role']])
    for api in ['AssetImportTask','TextureFactory','Texture','Texture2D','Material','MaterialFactoryNew','LinearColor']:getattr(ue,api)
    getattr(ue.Texture,'set_virtual_texture_streaming')
    for material in plan['materials']:
        for prop,value in material['engine_properties'].items():
            if prop in enum_types:getattr(getattr(ue,enum_types[prop]),value)
        for channel,value in material['channels'].items():
            getattr(ue.MaterialProperty,PROPERTIES[channel])
            if channel=='Normal' and value['kind']=='texture' and value['uv_channel']!=0:raise ValueError('Normal UV0 tangent-basis guard failed')
    for api in ['MaterialExpressionTextureCoordinate','MaterialExpressionTextureSample','MaterialExpressionConstant','MaterialExpressionConstant3Vector','MaterialExpressionLinearInterpolate','MaterialExpressionNormalize']:getattr(ue,api)
    tools=ue.AssetToolsHelpers.get_asset_tools();mel=ue.MaterialEditingLibrary;loaded={};created=[]
    for method in ['get_material_expression_input_names','create_material_expression','connect_material_expressions','connect_material_property','layout_material_expressions','recompile_material']:getattr(mel,method)
    for method in ['import_asset_tasks','create_asset']:getattr(tools,method)
    getattr(lib,'save_loaded_asset')
    # A failing apply leaves only newly created assets in its new version folder. Never deletes/rolls back user assets.
    for texture in plan['textures']:
        task=ue.AssetImportTask();task.set_editor_property('filename',texture['source_file']);task.set_editor_property('destination_path',dest+'/Textures');task.set_editor_property('destination_name',texture['name']);task.set_editor_property('automated',True);task.set_editor_property('replace_existing',False);task.set_editor_property('replace_existing_settings',False);task.set_editor_property('save',False);task.set_editor_property('async_',False);task.set_editor_property('factory',ue.TextureFactory())
        tools.import_asset_tasks([task]);objects=list(task.get_objects())
        if len(objects)!=1 or not isinstance(objects[0],ue.Texture2D):raise RuntimeError('Expected exactly one imported Texture: '+texture['name'])
        obj=objects[0];actual=obj.get_path_name().split('.')[0]
        if actual!=texture['asset_path']:raise RuntimeError('Importer changed destination/name: '+actual+'; inspect only new folder and use a new version on retry')
        obj.set_virtual_texture_streaming(False)
        if obj.get_editor_property('virtual_texture_streaming'):raise RuntimeError('Imported texture remained virtual; nonvirtual sampler contract would be invalid')
        obj.set_editor_property('filter',getattr(ue.TextureFilter,texture['filter']));obj.set_editor_property('address_x',getattr(ue.TextureAddress,texture['address_x']));obj.set_editor_property('address_y',getattr(ue.TextureAddress,texture['address_y']))
        obj.set_editor_property('srgb',texture['srgb']);obj.set_editor_property('flip_green_channel',texture['flip_green_channel']);obj.set_editor_property('compression_settings',getattr(ue.TextureCompressionSettings,texture['compression']));loaded[texture['asset_path']]=obj;created.append(actual)
        if not lib.save_loaded_asset(obj,only_if_is_dirty=False):raise RuntimeError('Texture save failed '+actual)
    for material in plan['materials']:
        obj=tools.create_asset(material['name'],dest+'/Materials',ue.Material,ue.MaterialFactoryNew())
        if not obj:raise RuntimeError('Material creation failed '+material['name'])
        actual=obj.get_path_name().split('.')[0]
        if actual!=material['asset_path']:raise RuntimeError('Material created at unexpected destination '+actual)
        created.append(actual)
        for prop,value in material['engine_properties'].items():
            actual_value=getattr(getattr(ue,enum_types[prop]),value) if prop in enum_types else value
            obj.set_editor_property(prop,actual_value)
            if obj.get_editor_property(prop)!=actual_value:raise RuntimeError('Material property verification failed: '+prop)
        for row,(channel,value) in enumerate(material['channels'].items()):
            output=''
            if value['kind']=='texture':
                tex=value['texture'];coord=mel.create_material_expression(obj,ue.MaterialExpressionTextureCoordinate,-700,row*220);coord.set_editor_property('coordinate_index',value['uv_channel']);sample=mel.create_material_expression(obj,ue.MaterialExpressionTextureSample,-450,row*220);sample.set_editor_property('texture',loaded[tex['asset_path']]);sample.set_editor_property('sampler_type',getattr(ue.MaterialSamplerType,{'normal':'SAMPLERTYPE_NORMAL','scalar':'SAMPLERTYPE_MASKS','color':'SAMPLERTYPE_COLOR'}[tex['role']]))
                if not mel.connect_material_expressions(coord,'',sample,'UVs'):raise RuntimeError('TexCoord connection failed')
                if coord.get_editor_property('coordinate_index')!=value['uv_channel']:raise RuntimeError('TexCoord index verification failed')
                node=sample;output='A' if value.get('source_output')=='Alpha' else 'R' if channel in {'Metallic','Roughness','Specular IOR Level'} else 'RGB'
            elif isinstance(value['value'],list):
                node=mel.create_material_expression(obj,ue.MaterialExpressionConstant3Vector,-450,row*220);node.set_editor_property('constant',ue.LinearColor(*value['value'][:3],1))
            else:
                node=mel.create_material_expression(obj,ue.MaterialExpressionConstant,-450,row*220);node.set_editor_property('r',float(value['value']))
            if channel=='Normal' and value['kind']=='texture' and abs(value['normal_strength']-1)>1e-6:
                neutral=mel.create_material_expression(obj,ue.MaterialExpressionConstant3Vector,-450,row*220+80);neutral.set_editor_property('constant',ue.LinearColor(0,0,1,1))
                lerp=mel.create_material_expression(obj,ue.MaterialExpressionLinearInterpolate,-200,row*220);lerp.set_editor_property('const_alpha',value['normal_strength'])
                norm=mel.create_material_expression(obj,ue.MaterialExpressionNormalize,0,row*220)
                norm_inputs=list(mel.get_material_expression_input_names(norm))
                if len(norm_inputs)!=1:raise RuntimeError('Unexpected Normalize input signature')
                if not (mel.connect_material_expressions(neutral,'',lerp,'A') and mel.connect_material_expressions(node,output,lerp,'B') and mel.connect_material_expressions(lerp,'',norm,norm_inputs[0])):raise RuntimeError('Normal strength node connection failed')
                node=norm;output=''
            if not mel.connect_material_property(node,output,getattr(ue.MaterialProperty,PROPERTIES[channel])):raise RuntimeError('Material property connection failed: '+channel)
        mel.layout_material_expressions(obj);mel.recompile_material(obj)
        if not lib.save_loaded_asset(obj,only_if_is_dirty=False):raise RuntimeError('Material save failed '+actual)
    return dict(status='CREATED_PENDING_ENGINE_VISUAL_VALIDATION',created_assets=created,destination=dest,blocked_materials=plan['blocked_materials'],slot_assignments=plan['slot_assignments'],shader_compile_errors_checked=False,save_reload_tested=False)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--export',required=True);p.add_argument('--destination',required=True);p.add_argument('--plan',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--allow-supported-subset',action='store_true');a=p.parse_args(argv)
    plan=build_plan(a.export,a.destination);write(a.plan,plan);print('DRY RUN:',len(plan['materials']),'supported materials,',len(plan['textures']),'textures,',len(plan['blocked_materials']),'manual shader policies')
    if a.apply:
        result=apply_plan(plan,a.allow_supported_subset);write(Path(a.plan).with_suffix('.applied.json'),result);print(result['status'])
    return plan
if __name__=='__main__':main()
