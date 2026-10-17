"""Mock all-material manifest integration; no Blender or Unreal."""
import sys,json,tempfile
from pathlib import Path
from types import SimpleNamespace as N
from export_material_manifest_v2 import export_material_manifest
warning='Base Color graph modulation not baked; direct source image is an approximation.'
names={'Cycle06 asphalt patch aggregate':(.66,.70,.68),'Forest leaf deep':(.48,.68,.38),'Forest leaf olive':(.9,.83,.45),'Forest leaf sage':(.75,.96,.66),'Unsupported tint':(.2,.3,.4)}
materials={}
for name,color in names.items():
 image=N(type='TEX_IMAGE',image=N(colorspace_settings=N(name='sRGB')))
 mix=N(type='MIX_RGB',blend_type='ADD' if name=='Unsupported tint' else 'MULTIPLY',use_clamp=False,inputs=[N(is_linked=False,default_value=1),N(links=[N(from_node=image,from_socket=N(name='Color'))]),N(is_linked=False,default_value=(*color,1))])
 principled=N(type='BSDF_PRINCIPLED',inputs={'Base Color':N(is_linked=True,links=[N(from_node=mix)])})
 materials[name]=N(use_nodes=True,node_tree=N(nodes=[principled]))
def original(root,source,sha):
 data={'materials':[{'source_name':name,'base_color':[1,1,1,1],'roughness':.5,'maps':{'base_color':{'available':True,'path':'textures/test.png'}},'approximations':[warning]} for name in names]}
 (Path(root)/'unreal/material_manifest.json').write_text(json.dumps(data));return 'unreal/material_manifest.json'
sys.modules['bpy']=N(data=N(materials=materials));sys.modules['export_material_manifest']=N(export_material_manifest=original)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);(root/'unreal').mkdir();(root/'qa').mkdir()
 export_material_manifest(root,Path('Cycle_10.blend'),'mock')
 data=json.loads((root/'unreal/material_manifest.json').read_text())
 for record in data['materials']:
  if record['source_name']=='Unsupported tint':assert warning in record['approximations'] and 'base_color_multiply_linear' not in record
  else:assert record['base_color_multiply_linear']==list(names[record['source_name']]) and warning not in record['approximations']
report={'scope':'Mock all-material manifest integration only; no source load or engine execution','passed':True,'supported_tints':4,'unsupported_warning_retained':True}
(Path(__file__).resolve().parents[1]/'qa/v2_all_material_tints_preparation.json').write_text(json.dumps(report,indent=2));print('PASS all four supported tints and unsupported warning retention')
