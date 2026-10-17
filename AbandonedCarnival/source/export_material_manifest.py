"""Extract portable PBR intent from loaded Blender materials; does not save source."""
import bpy,json,hashlib,re
from pathlib import Path

def export_material_manifest(root,source_path,source_hash):
 root=Path(root);records=[]
 def image_record(image):
  path=Path(bpy.path.abspath(image.filepath)).resolve()
  try:relative=path.relative_to(root.resolve()).as_posix()
  except ValueError:return {'path':None,'available':False,'warning':'Image outside package: '+image.name}
  return {'path':relative,'available':path.is_file(),'color_space':image.colorspace_settings.name}
 def upstream(socket,seen=None):
  seen=seen or set();found=[]
  for link in socket.links:
   node=link.from_node
   if node.as_pointer() in seen:continue
   seen.add(node.as_pointer())
   if node.type=='TEX_IMAGE' and node.image:found.append(node)
   else:
    for inp in node.inputs:
     if inp.is_linked:found+=upstream(inp,seen)
  return found
 for mat in sorted(bpy.data.materials,key=lambda m:m.name):
  if mat.users==0:continue
  ps=[n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'] if mat.use_nodes else []
  if not ps:continue
  p=ps[0];safe=re.sub('[^A-Za-z0-9_]','_',mat.name).strip('_')[:45]
  r={'source_name':mat.name,'asset_name':'M_'+safe+'_'+hashlib.sha1(mat.name.encode()).hexdigest()[:8], 'maps':{},'base_color':list(p.inputs['Base Color'].default_value),'roughness':p.inputs['Roughness'].default_value,'metallic':p.inputs['Metallic'].default_value,'two_sided':any(x in mat.name.lower() for x in ['foliage','leaf','leaves','grass','fern']),'normal_flip_green':True,'approximations':[]}
  r['transmission']=float(p.inputs['Transmission Weight'].default_value) if 'Transmission Weight' in p.inputs else 0.0
  r['ior']=float(p.inputs['IOR'].default_value)
  r['glass_approximation']=r['transmission']>.01 and not r['two_sided']
  if r['glass_approximation']:
   r['opacity_approximation']=min(.95,max(.05,1-r['transmission']))
   r['approximations'].append('Blender transmission approximated by translucent opacity 1-transmission and constant IOR refraction; no matched absorption, thickness or path-traced transmission.')
  for name,slot in [('base_color','Base Color'),('roughness','Roughness'),('normal','Normal')]:
   nodes=upstream(p.inputs[slot])
   # Only tangent-space Normal Map nodes transfer; image-driven Bump is not a normal map.
   if name=='normal':
    normal_nodes=[n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP']
    nodes=[t for n in normal_nodes for t in upstream(n.inputs['Color'])]
    if p.inputs[slot].is_linked and not nodes:r['approximations'].append('Blender bump/procedural normal omitted; requires baking or manual recreation.')
   if len(nodes)==1:r['maps'][name]=image_record(nodes[0].image)
   elif len(nodes)>1:r['approximations'].append(slot+' has multiple textures; requires baking/manual graph recreation.')
   if p.inputs[slot].is_linked and name!='normal':
    first=p.inputs[slot].links[0].from_node
    if first.type!='TEX_IMAGE':r['approximations'].append(slot+' graph modulation not baked; direct source image is an approximation.')
  if 'Emission Color' in p.inputs:
   strength=p.inputs['Emission Strength'].default_value
   r['emission_color']=[float(v)*strength for v in p.inputs['Emission Color'].default_value[:3]]
  r['physical_tile_m']=mat.get('physical_tile_m')
  r['uv_policy']='Preserve exported UV channel 0; physical tiling is already baked in scene UVs. No second scale applied.'
  records.append(r)
 report={'source_blend':str(source_path.name),'source_sha256':source_hash,'runtime_verified':False,'materials':records,'provenance':'ambientCG CC0 scanned Wood092/Asphalt033/Ground112/Metal063 and derived surfaces; source/realistic_asset_sources.json; docs/ASSET_PROVENANCE.md','limitations':['Portable BaseColor/Roughness/tangent Normal maps, constant metallic and emission only.','Procedural noise, dirt, bump, color mixing, transmission and specialized Blender shader behavior are not automatically baked.','Normal GL textures use Unreal Flip Green Channel; validate lighting in target engine.','Two-sided foliage enabled by source material name; full subsurface/transmission requires review.']}
 (root/'unreal/material_manifest.json').write_text(json.dumps(report,indent=2));return 'unreal/material_manifest.json'
