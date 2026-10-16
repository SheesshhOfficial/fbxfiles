"""Run with Python 3 after downloading all five parts into this script's folder."""
from pathlib import Path
import hashlib, zipfile, shutil
ROOT=Path(__file__).resolve().parent
PARTS=[{'name': 'Evergreen_Market_Unreal_Handoff.zip.part01', 'bytes': 9437184, 'sha256': 'ffe296047dd272f1b66b238bcbc448f2b2a37c08c86e36a53775d2d45292b4cd'}, {'name': 'Evergreen_Market_Unreal_Handoff.zip.part02', 'bytes': 9437184, 'sha256': '6c695513e1ab79646f8918a7000a68a2d789d0333cc76b0f241b111cb99726ab'}, {'name': 'Evergreen_Market_Unreal_Handoff.zip.part03', 'bytes': 9437184, 'sha256': 'cc7b34c0a6278db18142da258267f3e5d9a3a82469ebb13c157d8f9479c9a51f'}, {'name': 'Evergreen_Market_Unreal_Handoff.zip.part04', 'bytes': 9437184, 'sha256': '1931735e45a716d9aaa4a06ff4211b2ed3fd07db087c9813ba747d068377ccb7'}, {'name': 'Evergreen_Market_Unreal_Handoff.zip.part05', 'bytes': 5511473, 'sha256': '368e934f7ac1c962e7356c125e289c78ded89c06af55220e401a90225a529d9c'}]
ARCHIVE='Evergreen_Market_Unreal_Handoff.zip'
EXPECTED='b87f88a38882e763d2f2a6a21957734f1eb037187bfaa6a3ae81d4000cc6149e'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for item in PARTS:
 p=ROOT/item['name']
 if not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:
  raise RuntimeError('Missing or altered part: '+item['name'])
out=ROOT/ARCHIVE
if out.exists():
 if sha(out)!=EXPECTED:raise RuntimeError('Output already exists with different contents; rename it yourself before retrying.')
else:
 temp=ROOT/(ARCHIVE+'.joining')
 with temp.open('xb') as f:
  for item in PARTS:
   with (ROOT/item['name']).open('rb') as inp:shutil.copyfileobj(inp,f)
 if sha(temp)!=EXPECTED:raise RuntimeError('Joined archive checksum failed; no existing files were overwritten.')
 temp.rename(out)
with zipfile.ZipFile(out) as z:
 bad=z.testzip()
 if bad:raise RuntimeError('Archive CRC failure: '+bad)
print('Verified:',out)
print('Unzip it, then open Evergreen_Market_Unreal_Handoff/START_HERE.txt.')
