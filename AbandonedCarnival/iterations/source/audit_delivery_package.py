"""Read-only package checks, then emit a reproducible SHA256 file manifest."""
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='2d4f00dbf3704895a79ea30287dfa93ac7d0ad87f6e03e0e1ea163888418ca1a'
m=json.loads((root/'blender/source_parts.json').read_text());h=hashlib.sha256();total=0
for part in m['parts']:
 p=root/part['path'];b=p.read_bytes();assert len(b)==part['bytes'] and hashlib.sha256(b).hexdigest()==part['sha256'];assert len(b)<=9*1024*1024;h.update(b);total+=len(b)
assert h.hexdigest()==m['sha256']==expected and total==m['bytes']
checks={'source_reassembled_sha256':h.hexdigest(),'source_bytes':total,'part_count':len(m['parts']),'all_part_hashes_lengths_pass':True}
cmd=(root/'source/Reassemble_Blender_Windows.cmd').read_bytes();assert cmd.count(b'\r\n')==14 and b'\\r\\n' not in cmd and b'\r' not in cmd.replace(b'\r\n',b'');assert max(map(len,cmd.splitlines()))<8191
checks['windows_cmd_actual_crlf']=True
ex=root/'export';files=[]
for name,key in [('environment_manifest','source_sha256'),('prop_placements','source_blend_sha256')]:
 d=json.loads((ex/'unreal'/f'{name}.json').read_text());assert d[key]==expected
 for asset in d['assets']:
  p=(ex/asset['fbx']) if name=='environment_manifest' else (ex/'unreal'/asset['fbx']);assert sha(p)==asset['fbx_sha256'],str(p);files.append(p)
checks['matched_fbx_count']=len(files);checks['all_fbx_hashes_pass']=True
for p in (ex/'unreal').glob('import_*.py'):
 s=p.read_text();assert '/Game/MoonfallCarnivalV2V2' not in s and '/Game/MoonfallCarnival/' not in s
checks['v2_import_namespace_pass']=True
for n in ['material_manifest','scene_metadata']:
 d=json.loads((ex/'unreal'/f'{n}.json').read_text());assert d['source_sha256']==expected
checks['matching_material_scene_hashes']=True
checks['unreal_runtime_verified']=False
(root/'qa/DELIVERY_PACKAGE_CHECKS.json').write_text(json.dumps(checks,indent=2))
rows=[]
for p in sorted(root.rglob('*')):
 if p.is_file() and p.name!='FILE_MANIFEST.json':rows.append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
out={'scope':'All staged deliverable files except this manifest itself; local staging is not publication','source_sha256':expected,'file_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'files':rows}
(root/'FILE_MANIFEST.json').write_text(json.dumps(out,indent=2));print(json.dumps(checks));print('MANIFEST',out['file_count'],out['total_bytes'])
