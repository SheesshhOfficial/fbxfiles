"""Independent stdlib safety/rollback mocks. These are NOT Unreal runtime tests."""
import ast
import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path
import shutil
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
PATCH = HERE.parents[2]
ROOT = Path(os.environ.get('CARNIVAL_PACKAGE_ROOT', str(PATCH.parent / 'CarnivalMap_Refined_Delivery/repository/AbandonedCarnival')))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module

m = load('material_stage_review', HERE.parents[1] / 'carnival_material_stage57.py')
t = load('calibration_test_support', PATCH / 'tests/test_calibration57.py')

class AssetImportData(t.Obj):
    def __init__(self, filename=''):
        super().__init__()
        self.filename = filename
    def extract_filenames(self): return [self.filename]

class InterchangeAssetImportData(AssetImportData): pass

class TextureFactory(t.Obj):
    def __init__(self):
        super().__init__(create_material=False, edit_after_new=False, defer_compression=False,
                         compression_settings='DEFAULT', flip_normal_map_green_channel=False)

class Texture2D(t.Obj):
    def __init__(self):
        super().__init__(asset_import_data=AssetImportData(), srgb=True, compression_settings='DEFAULT',
                         flip_green_channel=False, virtual_texture_streaming=False)
        self.ignore_virtual_setter = False
    def set_virtual_texture_streaming(self, value):
        if not self.ignore_virtual_setter: self.props['virtual_texture_streaming'] = value

class Material(t.MaterialInterface):
    def __init__(self): super().__init__(two_sided=False, blend_mode='OPAQUE', shading_model='LIT')

class MaterialFactoryNew(t.Obj): pass
class MaterialExpressionTextureSample(t.Obj): pass
class MaterialExpressionTextureCoordinate(t.Obj): pass
class MaterialExpressionConstant(t.Obj): pass
class MaterialExpressionConstant3Vector(t.Obj): pass
class MaterialExpressionMultiply(t.Obj): pass

class LinearColor:
    def __init__(self, r=0, g=0, b=0, a=1): self.r,self.g,self.b,self.a=r,g,b,a
    def __eq__(self, other): return isinstance(other, LinearColor) and vars(self)==vars(other)

class PointLightComponent(t.Obj):
    def __init__(self):
        super().__init__(intensity_units='LUMENS', attenuation_radius=1000., cast_shadows=True,
                         use_temperature=False, specular_scale=1., intensity=0.,
                         use_inverse_squared_falloff=True, light_color=LinearColor(1,1,1), mobility='MOVABLE')
    def set_use_inverse_squared_falloff(self, value): self.props['use_inverse_squared_falloff']=value
    def set_intensity(self, value): self.props['intensity']=value
    def set_light_color(self, value, srgb): self.props['light_color']=value
    def set_mobility(self, value): self.props['mobility']=value

class DirectionalLightComponent(PointLightComponent): pass

class DirectionalLight(t.StaticMeshActor):
    component_class=DirectionalLightComponent
    def __init__(self, location=None):
        super().__init__(location)
        self.light_component=self.component_class()
    def get_component_by_class(self, cls): return self.light_component if isinstance(self.light_component,cls) else None

class PointLight(DirectionalLight): component_class=PointLightComponent


def engine(c,p):
    u=t.fake_engine(p['contract'])
    u.world.path=m.MAP
    u.assets[m.MAP.split('.')[0]]=u.world
    u.texture_mutator=None
    u.light_mutator=None
    u.material_mutator=None
    u.import_raises_after_create=False
    u.created_texture_order=[]
    for cls in (AssetImportData, TextureFactory, Texture2D, Material, MaterialFactoryNew,
                MaterialExpressionTextureSample, MaterialExpressionTextureCoordinate,
                MaterialExpressionConstant, MaterialExpressionConstant3Vector,
                MaterialExpressionMultiply, PointLightComponent, DirectionalLightComponent,
                DirectionalLight, PointLight, LinearColor): setattr(u,cls.__name__,cls)
    for enum,values in {
        'TextureCompressionSettings': {'TC_DEFAULT':'DEFAULT','TC_NORMALMAP':'NORMAL','TC_MASKS':'MASKS'},
        'MaterialSamplerType': {'SAMPLERTYPE_COLOR':'COLOR','SAMPLERTYPE_NORMAL':'NORMAL','SAMPLERTYPE_MASKS':'MASKS'},
        'MaterialProperty': {key:key for key in ('MP_BASE_COLOR','MP_ROUGHNESS','MP_NORMAL','MP_METALLIC','MP_EMISSIVE_COLOR')},
        'BlendMode': {'BLEND_OPAQUE':'OPAQUE'}, 'MaterialShadingModel': {'MSM_DEFAULT_LIT':'LIT'},
        'ComponentMobility': {'MOVABLE':'MOVABLE'}, 'LightUnits': {'LUMENS':'LUMENS'}
    }.items(): setattr(u,enum,types.SimpleNamespace(**values))
    meshes=[]
    for item in p['contract']['selected']:
        data=t.FbxStaticMeshImportData(); data.filename=item['source_path']
        mesh=t.StaticMesh(copy.deepcopy(item),data)
        mesh.materials=[]
        for index in range(len(item['materials'])):
            old=t.MaterialInterface(); old.path='/Game/Originals/Original_%s_%d.Original' % (item['asset_name'],index)
            mesh.materials.append(old)
        u.assets[mesh.path.split('.')[0]]=mesh
        meshes.append(mesh)
    for index,mesh in enumerate(meshes+[meshes[-1]]):
        actor=t.StaticMeshActor(t.Vector(index*500.,0.,0.)); actor.path=m.MAP+':Actor'+str(index)
        actor.props['tags']=['PropActor','CarnivalCalibration57']
        actor.props['static_mesh_component'].props.update(static_mesh=mesh,override_materials=[])
        u.actors.append(actor)
    class Library:
        @staticmethod
        def does_asset_exist(path): return path.split('.')[0] in u.assets
        @staticmethod
        def does_directory_exist(path): return u.existing_namespace if path==m.DEST else False
        @staticmethod
        def list_assets(path,**kwargs): return [obj.get_path_name() for key,obj in u.assets.items() if key.startswith(path+'/')]
    u.EditorAssetLibrary=Library
    u.load_asset=lambda path:u.assets.get(path.split('.')[0])
    class Tools:
        def import_asset_tasks(self,tasks):
            assert len(tasks)==1,'Texture tasks must be submitted sequentially'
            task=tasks[0]; values=task.props
            assert values['save'] is False and values['async_'] is False
            assert values['replace_existing'] is False and values['replace_existing_settings'] is False
            assert isinstance(values['factory'],TextureFactory)
            assert values['factory'].props['create_material'] is False
            assert values['factory'].props['edit_after_new'] is False
            u.events.append('import_texture')
            u.created_texture_order.append(values['destination_name'])
            tex=Texture2D(); tex.path=values['destination_path']+'/'+values['destination_name']+'.'+values['destination_name']
            tex.props['asset_import_data']=AssetImportData(values['filename'])
            if u.texture_mutator: u.texture_mutator(tex)
            task.objects=[tex]; task.props['imported_object_paths']=[tex.path]
            u.assets[tex.path.split('.')[0]]=tex
            if u.import_raises_after_create: raise RuntimeError('injected import failure after asset creation')
        def create_asset(self,name,folder,cls,factory):
            assert cls is Material and isinstance(factory,MaterialFactoryNew)
            mat=Material(); mat.path=folder+'/'+name+'.'+name
            u.events.append('create_material'); u.assets[mat.path.split('.')[0]]=mat
            if u.material_mutator: u.material_mutator(mat)
            return mat
    tool=Tools(); u.AssetToolsHelpers=types.SimpleNamespace(get_asset_tools=lambda:tool)
    class MaterialEditingLibrary:
        @staticmethod
        def create_material_expression(material,cls,x,y): u.events.append('create_expression'); return cls()
        @staticmethod
        def connect_material_property(*args): return True
        @staticmethod
        def connect_material_expressions(*args): return True
        @staticmethod
        def recompile_material(mat): u.events.append('request_shader_compile')
    u.MaterialEditingLibrary=MaterialEditingLibrary
    class Actors:
        def get_all_level_actors(self): return list(u.actors)
        def spawn_actor_from_class(self,cls,location,rotation,transient=False):
            assert cls in (DirectionalLight,PointLight) and transient is False
            u.events.append('spawn_light')
            actor=cls(location); actor.path=m.MAP+':Light'+str(len(u.actors)); u.actors.append(actor)
            if u.light_mutator: u.light_mutator(actor)
            return actor
    u.EditorActorSubsystem=Actors
    u.get_editor_subsystem=lambda cls:cls()
    return u,meshes


class StageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=m.core()
        cls.plan=json.loads((HERE.parent/'material_plan_fixture.json').read_text())
    def setUp(self):
        self.p=copy.deepcopy(self.plan)
        sources=tempfile.TemporaryDirectory(prefix='material-stage57-mock-source-')
        self.addCleanup(sources.cleanup)
        for item in self.p['contract']['selected']:
            file=Path(sources.name)/(item['asset_name']+'.fbx')
            file.write_bytes(b'MOCK FBX, not renderable geometry')
            item['source_path']=str(file); item['fbx_sha256']=self.c._sha(file)
        for record in self.p['textures']:
            file=Path(sources.name)/(record['asset_name']+'.mocktexture')
            file.write_bytes(('MOCK texture bytes '+record['path']).encode())
            record['filename']=str(file); record['sha256']=self.c._sha(file)
        self.u,self.meshes=engine(self.c,self.p)
        self.originals=[list(mesh.materials) for mesh in self.meshes]
        self.addCleanup(shutil.rmtree,self.u.content_dir)
        self.mods=patch.dict(sys.modules,{'unreal':self.u}); self.mods.start(); self.addCleanup(self.mods.stop)
        self.planner=patch.object(m,'plan',return_value=(self.c,self.p)); self.planner.start(); self.addCleanup(self.planner.stop)
    def assert_unchanged(self):
        self.assertEqual(self.u.events,[])
        self.assertEqual([mesh.materials for mesh in self.meshes],self.originals)
        self.assertEqual(len(self.u.assets),4)
    def assert_blocked(self):
        with self.assertRaises(m.MaterialStageError) as found: m.apply(ROOT)
        self.assertEqual(found.exception.report['status'],'MATERIAL_STAGE_BLOCKED')
        self.assert_unchanged()
    def test_preflight_read_only(self):
        result=m.preflight(ROOT)
        self.assertEqual(result['status'],'MATERIAL_PREFLIGHT_PASS',result)
        self.assertTrue(result['ready']); self.assert_unchanged()
    def test_wrong_saved_map_blocked(self): self.u.world.path='/Game/Other.Other'; self.assert_blocked()
    def test_unsaved_map_asset_blocked(self): del self.u.assets[m.MAP.split('.')[0]]; self.assertRaises(m.MaterialStageError,m.apply,ROOT); self.assertEqual(self.u.events,[])
    def test_dirty_map_blocked(self): self.u.dirty_maps=['dirty']; self.assert_blocked()
    def test_dirty_content_blocked(self): self.u.dirty_content=['dirty']; self.assert_blocked()
    def test_pie_blocked(self): self.u.game_world=t.World(); self.assert_blocked()
    def test_namespace_blocked(self): self.u.existing_namespace=True; self.assert_blocked()
    def test_empty_physical_namespace_blocked(self):
        (Path(self.u.content_dir)/m.DEST.removeprefix('/Game/')).mkdir(parents=True); self.assert_blocked()
    def test_missing_actor_blocked(self): self.u.actors.pop(); self.assert_blocked()
    def test_duplicate_actor_identity_blocked(self): self.u.actors[-1].path=self.u.actors[-2].path; self.assert_blocked()
    def test_extra_actor_blocked(self): self.u.actors.append(t.StaticMeshActor()); self.assert_blocked()
    def test_missing_tag_blocked(self): self.u.actors[0].props['tags']=['CarnivalCalibration57']; self.assert_blocked()
    def test_wrong_mesh_blocked(self): self.u.actors[0].props['static_mesh_component'].props['static_mesh']=None; self.assert_blocked()
    def test_existing_actor_override_blocked(self): self.u.actors[0].props['static_mesh_component'].props['override_materials']=[t.MaterialInterface()]; self.assert_blocked()
    def test_exact_success_counts_no_save_delete(self):
        result=m.apply(ROOT)
        self.assertEqual(result['status'],'MATERIAL_STAGE_CREATED_UNSAVED')
        self.assertEqual(self.u.events.count('import_texture'),10)
        self.assertEqual(self.u.events.count('create_material'),9)
        self.assertEqual(self.u.events.count('spawn_light'),3)
        self.assertEqual(self.u.created_texture_order,[r['asset_name'] for r in self.p['textures']])
        self.assertEqual(len(self.u.assets),23); self.assertEqual(len(self.u.actors),7)
        self.assertEqual(len(result['assignments']),10)
        self.assertEqual(result['saves_performed'],0)
        self.assertEqual(result['shader_compilation'],'NOT_VERIFIED')
        self.assertEqual(result['visual_review'],'NOT_RUN')
        self.assertTrue(all('PropActor' in a.props['tags'] for a in self.u.actors[:4]))
        self.assertEqual([a.props['static_mesh_component'].props['override_materials'] for a in self.u.actors[:4]],[[],[],[],[]])
    def test_wrong_texture_actual_name_stops_sequential_import(self):
        self.u.texture_mutator=lambda tex:setattr(tex,'path',tex.path+'_Wrong')
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        self.assertEqual(self.u.events.count('import_texture'),1)
        self.assertEqual(self.u.events.count('create_material'),0)
        self.assertTrue(found.exception.report['textures'][0]['actual_paths'])
        self.assertEqual([mesh.materials for mesh in self.meshes],self.originals)
    def test_interchange_provenance_rejected(self):
        def mutate(tex): tex.props['asset_import_data']=InterchangeAssetImportData(tex.props['asset_import_data'].filename)
        self.u.texture_mutator=mutate
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        self.assertIn('Unexpected texture importer provenance',found.exception.report['error'])
        self.assertEqual(self.u.events.count('import_texture'),1)
    def test_virtual_texture_failed_readback_rejected(self):
        def mutate(tex): tex.props['virtual_texture_streaming']=True; tex.ignore_virtual_setter=True
        self.u.texture_mutator=mutate
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        self.assertIn('Virtual texture disable readback',found.exception.report['error'])
        self.assertEqual(self.u.events.count('import_texture'),1)
    def test_changed_texture_rejected_before_submission(self):
        self.p['textures'][0]['sha256']='0'*64
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        self.assertIn('changed after preflight',found.exception.report['error'])
        self.assertEqual(self.u.events,[])
    def test_light_failure_restores_originals_keeps_assets_and_actor(self):
        def fail(actor): raise RuntimeError('injected post-spawn light failure')
        self.u.light_mutator=fail
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        result=found.exception.report
        self.assertEqual(result['status'],'MATERIAL_STAGE_FAILED_PARTIAL')
        self.assertEqual([mesh.materials for mesh in self.meshes],self.originals)
        self.assertEqual(len(result['rollback']),10)
        self.assertTrue(all(row['status']=='ORIGINAL_RESTORED' for row in result['rollback']))
        self.assertEqual(len(self.u.assets),23); self.assertEqual(len(self.u.actors),5)
        self.assertEqual(len(result['new_actor_paths_on_failure']),1)
        self.assertEqual(len(result['namespace_assets_on_failure']),19)
        self.assertEqual(result['saves_performed'],0)
    def test_assignment_failure_restores_original_nondefault_materials(self):
        mesh=self.meshes[0]; setter=mesh.set_material; fired=[False]
        def fail(index,material):
            setter(index,material)
            if isinstance(material,Material) and index==1 and not fired[0]:
                fired[0]=True; raise RuntimeError('injected assignment failure after write')
        mesh.set_material=fail
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        self.assertTrue(fired[0]); self.assertEqual(found.exception.report['status'],'MATERIAL_STAGE_FAILED_PARTIAL')
        self.assertIn('injected assignment failure',found.exception.report['error'])
        self.assertEqual([item.materials for item in self.meshes],self.originals)
        self.assertEqual(self.u.events.count('spawn_light'),0)
        self.assertTrue(all(row['status']=='ORIGINAL_RESTORED' for row in found.exception.report['rollback']))
    def test_partial_texture_import_retains_result_paths(self):
        self.u.import_raises_after_create=True
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        result=found.exception.report
        self.assertEqual(result['status'],'MATERIAL_STAGE_FAILED_PARTIAL')
        self.assertEqual(len(result['textures'][0]['actual_paths']),1)
        self.assertEqual(len(result['textures'][0]['actual_objects']),1)
        self.assertEqual(len(result['namespace_assets_on_failure']),1)
        self.assertEqual(len(self.u.assets),5)
        self.assertEqual([mesh.materials for mesh in self.meshes],self.originals)
    def test_failed_rollback_is_reported_without_deleting(self):
        mesh=self.meshes[0]; setter=mesh.set_material
        def reject_restore(index,material):
            if not isinstance(material,Material): raise RuntimeError('injected restoration denial')
            setter(index,material)
        mesh.set_material=reject_restore
        self.u.light_mutator=lambda actor: (_ for _ in ()).throw(RuntimeError('injected light failure'))
        with self.assertRaises(m.MaterialStageError) as found:m.apply(ROOT)
        result=found.exception.report
        self.assertEqual(result['status'],'MATERIAL_STAGE_FAILED_PARTIAL')
        self.assertTrue(any(row['status']=='FAILED' for row in result['rollback']))
        self.assertEqual(len(self.u.assets),23); self.assertEqual(len(self.u.actors),5)
        self.assertEqual(result['saves_performed'],0)
    @unittest.skipUnless(ROOT.is_dir(),'Set CARNIVAL_PACKAGE_ROOT for real-package hash integration test')
    def test_plan_has_exact_materials_textures_and_hashes(self):
        self.planner.stop()
        c,p=m.plan(ROOT)
        self.assertEqual(len(p['materials']),9);self.assertEqual(len(p['textures']),10)
        self.assertEqual(len({r['asset_name'] for r in p['textures']}),10)
        self.assertEqual(len({r['filename'] for r in p['textures']}),10)
        self.assertTrue(all(c._sha(Path(r['filename']))==r['sha256'] for r in p['textures']))
        self.assertFalse(next(x for x in p['materials'] if 'headlamp glass' in x['source_name'])['glass_approximation'])
    def test_offline_preflight_does_not_claim_runtime(self):
        with patch.dict(sys.modules,{'unreal':None}): result=m.preflight(ROOT)
        self.assertEqual(result['status'],'FILES_VERIFIED_ENGINE_NOT_CHECKED');self.assertFalse(result['ready'])
    def test_no_save_delete_calls_in_helper(self):
        tree=ast.parse(Path(m.__file__).read_text())
        calls=[node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)]
        self.assertFalse([name for name in calls if name.startswith(('save','delete','destroy')) or name in ('unlink','rmdir','rmtree')])

if __name__=='__main__': unittest.main(verbosity=2)
