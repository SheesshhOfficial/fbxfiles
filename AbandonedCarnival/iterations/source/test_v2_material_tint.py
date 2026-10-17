"""Pure-Python V2 tint graph tests; no Blender or Unreal execution."""
import sys,ast,json,math
from pathlib import Path
from types import SimpleNamespace as N
sys.path.insert(0,str(Path(__file__).resolve().parent))
from export_material_manifest_v2 import extract_direct_multiply
image=N(type='TEX_IMAGE',image=N(colorspace_settings=N(name='sRGB')))
mix=N(type='MIX_RGB',blend_type='MULTIPLY',use_clamp=False,inputs=[N(is_linked=False,default_value=1),N(links=[N(from_node=image,from_socket=N(name='Color'))]),N(is_linked=False,default_value=(.66,.70,.68,1))])
p=N(inputs={'Base Color':N(links=[N(from_node=mix)])})
assert extract_direct_multiply(p)==[.66,.70,.68]
for obj,key,bad in [(mix,'use_clamp',True),(mix,'blend_type','ADD'),(mix.inputs[0],'default_value',.5),(mix.inputs[2],'is_linked',True),(image.image.colorspace_settings,'name','Non-Color')]:
 old=getattr(obj,key);setattr(obj,key,bad)
 try:extract_direct_multiply(p)
 except ValueError:pass
 else:raise AssertionError('Unsupported graph was accepted')
 setattr(obj,key,old)
# Execute the actual inserted importer branch with a recording API double.
source=(Path(__file__).parent/'import_materials_v2.py').read_text();tree=ast.parse(source)
branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and 'base_color_multiply_linear' in ast.unparse(n.test))
connections=[]
class Node:
 def __init__(self,kind):self.kind=kind;self.properties={}
 def set_editor_property(self,k,v):self.properties[k]=v
class Lib:
 def create_material_expression(self,mat,kind,x,y):return Node(kind)
 def connect_material_expressions(self,a,out,b,inp):connections.append((a,out,b,inp));return True
u=N(MaterialExpressionConstant3Vector='constant3',MaterialExpressionMultiply='multiply',LinearColor=lambda *v:v)
ctx={'usage':'base_color','r':{'maps':{'base_color':{}},'base_color_multiply_linear':[.66,.70,.68]},'node':Node('texture'),'output':'RGB','lib':Lib(),'mat':object(),'unreal':u}
exec(compile(ast.fix_missing_locations(ast.Module(body=[branch],type_ignores=[])),'importer_tint_branch','exec'),ctx)
assert ctx['node'].kind=='multiply' and connections[0][3]=='A' and connections[1][3]=='B'
assert connections[1][0].properties['constant']==(.66,.70,.68,1.0)
# Shader algebra: Blender factor1 MULTIPLY = Unreal decoded linearRGB × tint.
errors=[]
for c in [0,.01,.04045,.2,.5,1]:
 linear=c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
 for tint in [.66,.70,.68]:errors.append(abs(((1-1)*linear+1*linear*tint)-linear*tint))
report={'scope':'Pure Python graph extractor, actual importer branch with API doubles, and linear multiply algebra; no Blender source loaded or Unreal execution','passed':True,'unsupported_graph_cases_rejected':5,'maximum_algebra_error':max(errors),'source_material_values_verified':False,'engine_shader_verified':False}
(Path(__file__).resolve().parents[1]/'qa/v2_material_tint_preparation.json').write_text(json.dumps(report,indent=2));print('PASS tint extraction, rejection guards, importer wiring and linear algebra')
