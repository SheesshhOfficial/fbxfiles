"""Prepared UE5 portable PBR material builder; NOT executed in Unreal.
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialEditingLibrary
https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture2D
Glass API reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Material?application_version=5.6
Existing assets are never overwritten. Shader approximations are in material_manifest.json.
"""
import unreal,os,json,hashlib,re
DEST='/Game/MoonfallCarnivalV2/Materials'
TEX='/Game/MoonfallCarnivalV2/Textures'

def build_materials(root=None):
 root=os.path.abspath(root or os.path.dirname(__file__))
 with open(os.path.join(root,'material_manifest.json'),encoding='utf-8') as f:data=json.load(f)
 tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
 textures={};materials={}
 def texture_name(path,usage):
  stem=re.sub('[^A-Za-z0-9_]','_',os.path.splitext(os.path.basename(path))[0])[:45]
  return 'T_'+stem+'_'+hashlib.sha1((path+usage).encode()).hexdigest()[:8]
 # Fail closed before writing when expected maps are missing or assets exist.
 for r in data['materials']:
  if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+r['asset_name']):raise RuntimeError('Material already exists: '+r['asset_name'])
  for usage,m in r['maps'].items():
   if not m.get('available') or not m.get('path') or not os.path.isfile(os.path.join(root,'..',m['path'])):raise RuntimeError('Missing material texture: '+str(m))
   if unreal.EditorAssetLibrary.does_asset_exist(TEX+'/'+texture_name(m['path'],usage)):raise RuntimeError('Texture already exists; inspect manually: '+m['path'])
 def load_texture(m,usage,flip):
  key=(m['path'],usage)
  if key in textures:return textures[key]
  name=texture_name(*key);task=unreal.AssetImportTask()
  task.filename=os.path.normpath(os.path.join(root,'..',m['path']));task.destination_path=TEX;task.destination_name=name
  task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task])
  tex=unreal.load_asset(TEX+'/'+name)
  if not isinstance(tex,unreal.Texture2D):raise RuntimeError('Texture import failed: '+m['path'])
  tex.set_editor_property('srgb',usage=='base_color')
  if usage=='normal':
   tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
   tex.set_editor_property('flip_green_channel',flip)
  elif usage=='roughness':tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
  unreal.EditorAssetLibrary.save_loaded_asset(tex);textures[key]=tex;return tex
 for r in data['materials']:
  mat=tools.create_asset(r['asset_name'],DEST,unreal.Material,unreal.MaterialFactoryNew())
  if mat is None:raise RuntimeError('Material creation failed: '+r['asset_name'])
  mat.set_editor_property('two_sided',r['two_sided'])
  if r.get('glass_approximation'):
   mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
   mat.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
   try:mat.set_editor_property('refraction_method',unreal.RefractionMode.RM_INDEX_OF_REFRACTION)
   except Exception:mat.set_editor_property('refraction_mode',unreal.RefractionMode.RM_INDEX_OF_REFRACTION)
   for y,value,prop in [(1100,r['opacity_approximation'],unreal.MaterialProperty.MP_OPACITY),(1300,r['ior'],unreal.MaterialProperty.MP_REFRACTION)]:
    node=lib.create_material_expression(mat,unreal.MaterialExpressionConstant,-400,y)
    node.set_editor_property('r',float(value))
    if not lib.connect_material_property(node,'',prop):raise RuntimeError('Glass opacity/refraction connection failed: '+r['source_name'])
  for idx,(usage,prop) in enumerate([('base_color',unreal.MaterialProperty.MP_BASE_COLOR),('roughness',unreal.MaterialProperty.MP_ROUGHNESS),('normal',unreal.MaterialProperty.MP_NORMAL),('metallic',unreal.MaterialProperty.MP_METALLIC),('emission_color',unreal.MaterialProperty.MP_EMISSIVE_COLOR)]):
   if usage in r['maps']:
    node=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample,-400,idx*200)
    node.set_editor_property('texture',load_texture(r['maps'][usage],usage,r['normal_flip_green']))
    sample={'base_color':unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,'roughness':unreal.MaterialSamplerType.SAMPLERTYPE_MASKS,'normal':unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL}[usage]
    node.set_editor_property('sampler_type',sample);output='R' if usage=='roughness' else 'RGB'
   elif usage=='normal':continue
   elif usage in ['base_color','emission_color']:
    values=r.get(usage,[0,0,0]);node=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-400,idx*200)
    node.set_editor_property('constant',unreal.LinearColor(*values[:3],1.0));output=''
   else:
    node=lib.create_material_expression(mat,unreal.MaterialExpressionConstant,-400,idx*200)
    node.set_editor_property('r',float(r[usage]));output=''
   if usage=='base_color' and 'base_color_multiply_linear' in r:
    if usage not in r['maps']:raise RuntimeError('Tint requires a source basecolor texture')
    tint=lib.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-400,-200)
    tint.set_editor_property('constant',unreal.LinearColor(*r['base_color_multiply_linear'],1.0))
    multiply=lib.create_material_expression(mat,unreal.MaterialExpressionMultiply,-150,0)
    if not lib.connect_material_expressions(node,output,multiply,'A'):raise RuntimeError('Texture to tint multiply connection failed')
    if not lib.connect_material_expressions(tint,'',multiply,'B'):raise RuntimeError('Tint constant connection failed')
    node=multiply;output=''
   if not lib.connect_material_property(node,output,prop):raise RuntimeError('Material connection failed: '+r['source_name']+' '+usage)
  lib.recompile_material(mat);unreal.EditorAssetLibrary.save_loaded_asset(mat);materials[r['source_name']]=mat
  for warning in r['approximations']:unreal.log_warning(r['source_name']+': '+warning)
 return materials
