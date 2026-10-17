"""V2 manifest extension for exact linear-space texture × constant tint intent.
No source writes. The corresponding V2 importer builds a Multiply shader node.
"""
import json,math
from pathlib import Path

def extract_direct_multiply(principled):
 socket=principled.inputs['Base Color']
 if len(socket.links)!=1:raise ValueError('Expected one Base Color input link')
 mix=socket.links[0].from_node
 if mix.type!='MIX_RGB' or mix.blend_type!='MULTIPLY':raise ValueError('Expected MixRGB MULTIPLY')
 if mix.use_clamp:raise ValueError('Clamped multiply needs separate shader handling')
 if mix.inputs[0].is_linked or abs(float(mix.inputs[0].default_value)-1)>1e-7:raise ValueError('Expected constant factor 1')
 if mix.inputs[2].is_linked:raise ValueError('Expected constant tint')
 if len(mix.inputs[1].links)!=1:raise ValueError('Expected one texture color input')
 link=mix.inputs[1].links[0];image=link.from_node
 if image.type!='TEX_IMAGE' or not image.image or link.from_socket.name!='Color':raise ValueError('Multiply input must be direct image Color')
 tint=[float(v) for v in mix.inputs[2].default_value[:3]]
 if not all(math.isfinite(v) and 0<=v<=1 for v in tint):raise ValueError('Tint out of supported range')
 if image.image.colorspace_settings.name!='sRGB':raise ValueError('Expected sRGB source image with linear shader multiplication')
 return tint

def export_material_manifest(root,source_path,source_hash):
 import bpy
 from export_material_manifest import export_material_manifest as original
 target='Cycle06 asphalt patch aggregate'
 material=bpy.data.materials.get(target)
 if material is None:raise RuntimeError('Expected Cycle 6 asphalt patch material is missing')
 principled=[n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
 if len(principled)!=1:raise RuntimeError('Expected a single patch Principled shader')
 try:tint=extract_direct_multiply(principled[0])
 except ValueError as e:raise RuntimeError('Cannot export patch tint faithfully: '+str(e)) from e
 path=original(root,source_path,source_hash)
 out=Path(root)/path;data=json.loads(out.read_text())
 supported=[];unsupported=[]
 for record in data['materials']:
  mat=bpy.data.materials.get(record['source_name'])
  ps=[n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'] if mat and mat.use_nodes else []
  if len(ps)!=1:
   unsupported.append({'material':record['source_name'],'reason':'Requires a single Principled shader'})
   continue
  try:color=extract_direct_multiply(ps[0])
  except ValueError as e:
   # Ordinary constants/direct image graphs and unsupported modulation retain
   # all original extraction warnings; never claim support from image discovery.
   if ps[0].inputs['Base Color'].is_linked:
    first=ps[0].inputs['Base Color'].links[0].from_node
    if first.type!='TEX_IMAGE':unsupported.append({'material':record['source_name'],'reason':str(e)})
   continue
  if not record['maps'].get('base_color',{}).get('available'):
   if record['source_name']==target:raise RuntimeError('Patch tint source image unavailable')
   unsupported.append({'material':record['source_name'],'reason':'Source image unavailable'})
   continue
  record['base_color_multiply_linear']=color
  record['base_color_graph_equivalent']='sRGB image decoded to linear RGB, multiplied by linear constant tint; MixRGB MULTIPLY factor 1, clamp off; alpha unused by opaque BaseColor.'
  record['approximations']=[v for v in record['approximations'] if v!='Base Color graph modulation not baked; direct source image is an approximation.']
  supported.append({'material':record['source_name'],'tint_linear':color,'texture':record['maps']['base_color']['path']})
 if target not in {r['material'] for r in supported}:raise RuntimeError('Mandatory asphalt tint was not represented')
 out.write_text(json.dumps(data,indent=2))
 names={target,'wetground','Cycle06 damp asphalt water margins','Cycle06 damp tar seams','Cycle06 worn tire rub'}|{r['material'] for r in supported}
 records=[r for r in data['materials'] if r['source_name'] in names]
 qa={'source_sha256':source_hash,'scope':'Source graph structure and exported numeric material intent; Unreal shader execution unverified','runtime_verified':False,'patch_tint_supported':True,'patch_tint_linear':tint,'supported_multiply_materials':supported,'unsupported_modulation_materials':unsupported,'method':'Explicit Multiply expression in prepared V2 Unreal material importer; no lossy texture rebake','materials':[{k:r[k] for k in ['source_name','base_color','roughness','maps','approximations']} for r in records]}
 (Path(root)/'qa/environment_material_compatibility.json').write_text(json.dumps(qa,indent=2))
 return path
