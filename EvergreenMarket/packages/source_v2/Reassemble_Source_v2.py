"""Run with Python 3 after downloading all parts into this script's folder."""
from pathlib import Path
import hashlib, zipfile, shutil
ROOT=Path(__file__).resolve().parent
PARTS=[{'name': 'Evergreen_Market_Source_v2_Complete.zip.part01', 'bytes': 9437184, 'sha256': '9cbef229356e9e29bce3fb9c4345d74865b92b819ed71c3118f6816529c6d373'}, {'name': 'Evergreen_Market_Source_v2_Complete.zip.part02', 'bytes': 9437184, 'sha256': '5d0f0a18ef9790120bc7eded300a0a03ddad1cf3454fe684d0bf578fed935983'}, {'name': 'Evergreen_Market_Source_v2_Complete.zip.part03', 'bytes': 9437184, 'sha256': 'ae5b207f1639ba84d4b8df3db859a36f990bde177e2b90d581a52ead82284fbd'}, {'name': 'Evergreen_Market_Source_v2_Complete.zip.part04', 'bytes': 9437184, 'sha256': '649480c512040892949b9c7cbe5c8ffeb7d4db0cfec5cea5cc92175e6e911831'}, {'name': 'Evergreen_Market_Source_v2_Complete.zip.part05', 'bytes': 9437184, 'sha256': 'c586802d55b9812487a57dcf2cb24ef64f0929c4b7550b174504f35bd82d5356'}, {'name': 'Evergreen_Market_Source_v2_Complete.zip.part06', 'bytes': 6030246, 'sha256': '1db2ef26031cb938d03b2d9c440c06976e36d7fdf9995177b962124facd9ba73'}]
ARCHIVE='Evergreen_Market_Source_v2_Complete.zip'
EXPECTED='21c85917a12ca5709215783ed4e02522ad942c652ac76927525e030c920cdbab'
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
print('Unzip it, then open Evergreen_Market_Source_v2/START_HERE.md.')
