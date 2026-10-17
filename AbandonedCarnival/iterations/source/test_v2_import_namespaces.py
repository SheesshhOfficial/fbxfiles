"""Check actual helper-copy replacement and resulting destination constants without imports."""
import ast,json
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
tree=ast.parse((PROJECT/'iterations/source/export_environment_v2.py').read_text())
assign=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
records=[]
for name in ['import_environment.py','import_materials.py','import_scene_metadata.py']:
 template=PROJECT/'iterations/source/import_materials_v2.py' if name=='import_materials.py' else PROJECT/'unreal'/name
 context={'template':template};exec(compile(ast.fix_missing_locations(ast.Module(body=[assign],type_ignores=[])),'actual_copy_expression','exec'),context)
 result=ast.parse(context['code']);destinations=[]
 for n in ast.walk(result):
  if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('/Game/'):
   destinations.append(n.value)
   assert n.value.startswith('/Game/MoonfallCarnivalV2/'),(name,n.value)
   assert 'V2V2' not in n.value,(name,n.value)
 assert destinations
 records.append({'helper':name,'destination_literals':destinations})
out={'scope':'Static actual template-copy expression and Unreal path literals only; no engine execution or generated export writes','passed':True,'helpers':records}
(PROJECT/'iterations/qa/v2_import_namespace_preparation.json').write_text(json.dumps(out,indent=2));print('PASS all three prepared helpers target single V2 root')
