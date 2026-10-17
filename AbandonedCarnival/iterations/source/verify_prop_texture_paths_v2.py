import os,json
from io_scene_fbx import parse_fbx
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
ROOT=str(PROJECT/'iterations/export')
d=json.load(open(ROOT+'/unreal/prop_placements.json'))
import hashlib
_approved=os.environ.get('CARNIVAL_V2_SOURCE_SHA256','')
if len(_approved)!=64 or d.get('source_blend_sha256')!=_approved or hashlib.sha256((PROJECT/'iterations/Cycle_10.blend').read_bytes()).hexdigest()!=_approved:raise RuntimeError('V2 validator requires matching approved Cycle10 source and manifest hash')
checks=[]
for asset in d['assets']:
 path=ROOT+'/unreal/'+asset['fbx'];tree,version=parse_fbx.parse(path)
 def walk(e):
  if e.id==b'Video':
   children={c.id:c for c in e.elems};rel=children.get(b'RelativeFilename');content=children.get(b'Content')
   if rel:
    value=rel.props[0].decode() if isinstance(rel.props[0],bytes) else rel.props[0]
    target=os.path.normpath(os.path.join(os.path.dirname(path),value.replace('\\','/')))
    checks.append({'asset':asset['asset_name'],'relative_texture_path':value,'exists':os.path.isfile(target),'inside_package_textures':os.path.commonpath([ROOT+'/textures',target])==ROOT+'/textures','embedded_payload_bytes':sum(len(p) for p in content.props if isinstance(p,bytes)) if content else 0})
  for c in e.elems:walk(c)
 walk(tree)
report={'source_blend_sha256':d['source_blend_sha256'],'all_passed':bool(checks) and all(c['exists'] and c['inside_package_textures'] and c['embedded_payload_bytes']==0 for c in checks),'fbx_assets':len(d['assets']),'texture_references':len(checks),'checks':checks}
open(ROOT+'/qa/prop_texture_paths.json','w').write(json.dumps(report,indent=2));print('TEXTURE_PATH_CHECK',report['all_passed'],len(checks))
