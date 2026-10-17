"""Curate matched deliverables, preserving source workspace and stale checkpoints.
Run only after final QA and the hero render. Writes delivery/ beside CarnivalMap.
"""
from pathlib import Path
import hashlib,json,zipfile,shutil
root=Path(__file__).resolve().parents[1];out=root.parent/'CarnivalMap_Delivery';out.mkdir(exist_ok=True)
sha=hashlib.sha256((root/'blender/Moonfall_Carnival_ArtPass.blend').read_bytes()).hexdigest()
e=json.loads((root/'unreal/environment_manifest.json').read_text());p=json.loads((root/'unreal/prop_placements.json').read_text());m=json.loads((root/'unreal/material_manifest.json').read_text());s=json.loads((root/'unreal/scene_metadata.json').read_text())
for name,data in [('environment',e),('props',p),('materials',m),('metadata',s)]:
 actual=data.get('source_sha256',data.get('source_blend_sha256'))
 if actual!=sha:raise SystemExit(f'{name} manifest source mismatch: {actual}')
for qa_name in ('prop_fidelity.json','prop_fbx_roundtrip.json','prop_texture_paths.json'):
 data=json.loads((root/'qa'/qa_name).read_text())
 if not data.get('all_passed') or data.get('source_blend_sha256')!=sha:raise SystemExit('Prop QA gate failed: '+qa_name)
source_qa=json.loads((root/'qa/artpass_geometry_audit.json').read_text())
# Environment release gate is supplied by the final review after any transfer fixes.
release=json.loads((root/'qa/delivery_release.json').read_text())
if release.get('source_sha256')!=sha or not release.get('ready_for_source_delivery'):raise SystemExit('Final release gate not satisfied')
hero=json.loads((root/'qa/render_maintenance_hero_manifest.json').read_text())
if hero['source_sha256']!=sha:raise SystemExit('Hero source mismatch')
fbxs={a['fbx'] for a in e['assets']}|{'unreal/'+a['fbx'] for a in p['assets']}
files=[]
for path in sorted(root.rglob('*')):
 if not path.is_file():continue
 rel=path.relative_to(root);r=rel.as_posix()
 if '__pycache__' in rel.parts or path.suffix in ('.pyc','.blend1'):continue
 if path.name in ('assemble_props_debug_backup.py','capture_precleanup_materials.py','repair_cleanup_materials_uv.py','repair_environment_exact_normals.py'):continue
 if r.startswith('blender/') and not (path.name in ('Moonfall_Carnival_ArtPass.blend','source_parts.json') or path.name.startswith('Moonfall_Carnival_ArtPass.blend.part')):continue
 if r.startswith('checkpoints/') or r.startswith('qa/checkpoints/'):continue
 if r.startswith(('unreal/environment/','unreal/props/')) and r not in fbxs:continue
 if r.startswith('textures/realistic/') and path.suffix.lower() in ('.blend','.usdc','.mtlx','.tres'):continue
 if r.startswith('textures/realistic/') and any(t in path.name for t in ('_NormalDX','_Displacement','_AmbientOcclusion')):continue
 if r.startswith('qa/'):
  if path.suffix.lower() not in ('.json','.md'):continue
  if not path.name.startswith(('artpass_geometry_', 'environment_', 'prop_', 'collision_complexity', 'reassembly_validation', 'script_syntax_validation', 'render_maintenance_hero_manifest', 'delivery_release')):continue
  if 'synthetic' in path.name or 'diagnostic' in path.name or 'mock' in path.name:continue
 if r.startswith('renders/') and not (path.name in ('Maintenance_Hero.png','Review_Gallery.html','README.md') or (r.startswith('renders/artpass/') and 'Detailed_Review' in path.name) or path.name in ('Ticket_Entrance_Detail_Review.png','Gate_Entrance_Detail_Review.png')):continue
 files.append((path,r))
selected_paths={rel for _,rel in files}
for img in source_qa['image_integrity']['images']:
 path=img['filepath'].replace('\\','/')
 if '/textures/' in path:
  rel='textures/'+path.split('/textures/',1)[1]
  if rel not in selected_paths:raise SystemExit('Used source texture excluded: '+rel)
full=[(p,r) for p,r in files if '.blend.part' not in r]
repo=[(p,r) for p,r in files if r!='blender/Moonfall_Carnival_ArtPass.blend']
for label,selection in [('Complete',full),('Repository',repo)]:
 dest=out/f'Moonfall_Carnival_{label}.zip'
 with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for path,rel in selection:z.write(path,'CarnivalMap/'+rel)
 with zipfile.ZipFile(dest) as z:
  bad=z.testzip()
  if bad:raise RuntimeError('Archive CRC failed: '+bad)
 manifest={'archive':dest.name,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'source_sha256':sha,'files':[{'path':'CarnivalMap/'+r,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,r in selection]}
 (out/f'{label}_File_Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(label,dest,manifest['bytes'],manifest['sha256'],flush=True)
 if label=='Repository':
  repo_root=out/'repository'/'CarnivalMap';repo_root.mkdir(parents=True,exist_ok=True)
  for path,rel in selection:
   dst=repo_root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)
  oversized=[r for p,r in selection if p.stat().st_size>=100_000_000]
  if oversized:raise RuntimeError('Files exceed repository per-file safe limit: '+str(oversized))
