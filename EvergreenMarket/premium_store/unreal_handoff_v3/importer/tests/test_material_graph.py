"""Strict fake-API material wiring tests; no actual Unreal/shader execution."""
import copy
import sys
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import materials as b
from test_importer import material

class FakeObject:
 def __init__(self,path='',kind=''):self.path=path;self.kind=kind;self.props={}
 def set_editor_property(self,key,value):self.props[key]=value
 def get_editor_property(self,key):return self.props.get(key)
 def get_path_name(self):return self.path+'.'+self.path.rsplit('/',1)[-1]
class FakeTexture(FakeObject):
 def set_virtual_texture_streaming(self,value):self.props['virtual_texture_streaming']=value
class FakeTask(FakeObject):
 def get_objects(self):return self.objects
class FakeUE:
 def __init__(self,existing=False,asset_exists=False):
  self.created=[];self.nodes=[];self.import_tasks=[];self.connections=[];self.saved=[];self.textures=[]
  self.EditorAssetLibrary=SimpleNamespace(does_directory_exist=lambda p:existing,list_assets=lambda *a,**k:[],does_asset_exist=lambda p:asset_exists,save_loaded_asset=self.save)
  self.AssetToolsHelpers=SimpleNamespace(get_asset_tools=lambda:self)
  self.MaterialEditingLibrary=SimpleNamespace(get_material_expression_input_names=lambda n:['VectorInput'] if n.kind=='MaterialExpressionNormalize' else [],create_material_expression=self.expression,connect_material_expressions=self.connect,connect_material_property=self.property,layout_material_expressions=lambda o:None,recompile_material=lambda o:None)
  self.AssetImportTask=FakeTask;self.TextureFactory=lambda:FakeObject();self.Texture=FakeTexture;self.Texture2D=FakeTexture;self.Material=FakeObject;self.MaterialFactoryNew=lambda:FakeObject()
  for name in ['MaterialExpressionTextureCoordinate','MaterialExpressionTextureSample','MaterialExpressionConstant3Vector','MaterialExpressionConstant','MaterialExpressionLinearInterpolate','MaterialExpressionNormalize']:setattr(self,name,name)
  self.BlendMode=SimpleNamespace(BLEND_OPAQUE='BLEND_OPAQUE',BLEND_TRANSLUCENT='BLEND_TRANSLUCENT');self.MaterialShadingModel=SimpleNamespace(MSM_DEFAULT_LIT='MSM_DEFAULT_LIT',MSM_UNLIT='MSM_UNLIT');self.TranslucencyLightingMode=SimpleNamespace(TLM_SURFACE_PER_PIXEL_LIGHTING='TLM_SURFACE_PER_PIXEL_LIGHTING');self.RefractionMode=SimpleNamespace(RM_INDEX_OF_REFRACTION='RM_INDEX_OF_REFRACTION')
  self.TextureFilter=SimpleNamespace(TF_BILINEAR='TF_BILINEAR');self.TextureAddress=SimpleNamespace(TA_WRAP='TA_WRAP');self.TextureCompressionSettings=SimpleNamespace(**{k:k for k in ['TC_NORMALMAP','TC_MASKS','TC_DEFAULT']});self.MaterialSamplerType=SimpleNamespace(**{k:k for k in ['SAMPLERTYPE_NORMAL','SAMPLERTYPE_MASKS','SAMPLERTYPE_COLOR']});self.MaterialProperty=SimpleNamespace(**{k:k for k in b.PROPERTIES.values()});self.LinearColor=lambda *args:list(args)
 def import_asset_tasks(self,tasks):
  for task in tasks:
   self.import_tasks.append(task);t=FakeTexture(task.props['destination_path']+'/'+task.props['destination_name']);task.objects=[t];self.textures.append(t);self.created.append(t)
 def create_asset(self,name,path,kind,factory):o=FakeObject(path+'/'+name,'material');self.created.append(o);return o
 def expression(self,mat,kind,x,y):o=FakeObject('',kind);self.nodes.append(o);return o
 def connect(self,a,ao,b,bi):self.connections.append((a,ao,b,bi));return True
 def property(self,a,ao,p):self.connections.append((a,ao,p));return True
 def save(self,obj,**kw):self.saved.append(obj);return True


class MaterialGraphTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  (self.root/'color.png').write_bytes(b'fake color bytes');(self.root/'normal.png').write_bytes(b'fake normal bytes')
  m=material('Test textured');m['images']=[dict(name=n+'.png',node=n,projection='FLAT',extension='REPEAT',interpolation='Linear') for n in ['color','normal']]
  m['node_graph'] += [dict(name='Normal',type='NORMAL_MAP',normal_space='TANGENT',normal_strength_linked=False,normal_strength=.45,uv_map='UVMap')]
  m['links']=[dict(from_node='color',from_socket='Color',to_node='P',to_socket='Base Color'),dict(from_node='normal',from_socket='Color',to_node='Normal',to_socket='Color'),dict(from_node='Normal',from_socket='Normal',to_node='P',to_socket='Normal')]
  images=[dict(name=n+'.png',path=n+'.png',sha256=b.digest(self.root/(n+'.png')),colorspace='sRGB' if n=='color' else 'Non-Color',rgb_channels_equal=False) for n in ['color','normal']]
  b.write(self.root/'EXPORT_VALIDATION_MANIFEST.json',dict(source_sha256='fixture',assets=[dict(mesh='SM_Test',objects=[dict(materials=['Test textured'])])],images=images))
  b.write(self.root/'MATERIAL_CONTRACT.json',dict(materials=[m]))
  b.write(self.root/'TEXTURE_UV_BINDINGS.json',dict(assets=[dict(mesh='SM_Test',bindings=[dict(slot=0,image='color.png',uv_channel=1,uv_layer='ColorUV'),dict(slot=0,image='normal.png',uv_channel=0,uv_layer='UVMap',normal_tangent_uv_channel=0,normal_tangent_uv_layer='UVMap',normal_convention='OpenGL +Y')])]))
  self.plan=b.build_plan(self.root,'/Game/Test/Materials_v001')
 def tearDown(self):self.temp.cleanup()
 def test_each_image_wires_its_own_explicit_uv(self):
  self.assertFalse(self.plan['blocked_materials']);ue=FakeUE();b.apply_plan(self.plan,ue=ue)
  coords=[x for x in ue.nodes if x.kind=='MaterialExpressionTextureCoordinate'];samples=[x for x in ue.nodes if x.kind=='MaterialExpressionTextureSample']
  self.assertEqual(sorted(x.props['coordinate_index'] for x in coords),[0,1]);self.assertEqual(len(samples),len(coords))
  self.assertEqual(sum(len(c)==4 and c[-1]=='UVs' for c in ue.connections),2)
 def test_normal_flags_and_strength_graph(self):
  ue=FakeUE();b.apply_plan(self.plan,ue=ue)
  normals=[t for t in ue.textures if t.props['compression_settings']=='TC_NORMALMAP'];self.assertEqual(len(normals),1)
  self.assertFalse(normals[0].props['srgb']);self.assertTrue(normals[0].props['flip_green_channel']);self.assertFalse(normals[0].props['virtual_texture_streaming'])
  lerps=[n for n in ue.nodes if n.kind=='MaterialExpressionLinearInterpolate'];self.assertEqual(lerps[0].props['const_alpha'],.45)
  self.assertTrue(any(n.kind=='MaterialExpressionNormalize' for n in ue.nodes))
 def test_normal_nonzero_uv_blocks_before_creation(self):
  p=copy.deepcopy(self.plan);p['materials'][0]['channels']['Normal']['uv_channel']=1;ue=FakeUE()
  with self.assertRaises(ValueError):b.apply_plan(p,ue=ue)
  self.assertFalse(ue.created)
 def test_existing_destination_and_assets_block_before_creation(self):
  for ue in [FakeUE(existing=True),FakeUE(asset_exists=True)]:
   with self.assertRaises(ValueError):b.apply_plan(self.plan,ue=ue)
   self.assertFalse(ue.created)
 def test_texture_hash_mutation_blocks_before_creation(self):
  (self.root/'color.png').write_bytes(b'changed');ue=FakeUE()
  with self.assertRaises(ValueError):b.apply_plan(self.plan,ue=ue)
  self.assertFalse(ue.created)
 def test_missing_engine_api_blocks_before_creation(self):
  ue=FakeUE();del ue.TextureFactory
  with self.assertRaises(AttributeError):b.apply_plan(self.plan,ue=ue)
  self.assertFalse(ue.created)
 def test_new_material_and_texture_imports_never_replace(self):
  ue=FakeUE();b.apply_plan(self.plan,ue=ue)
  self.assertTrue(all(t.props['replace_existing'] is False and t.props['replace_existing_settings'] is False for t in ue.import_tasks))
 def test_unsupported_full_material_plan_blocks_before_creation(self):
  p=copy.deepcopy(self.plan);p['blocked_materials']=[dict(material='Unknown')];ue=FakeUE()
  with self.assertRaises(ValueError):b.apply_plan(p,ue=ue)
  self.assertFalse(ue.created)

if __name__=='__main__':unittest.main(verbosity=2)
