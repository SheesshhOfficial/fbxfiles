"""Portable Python alternative to the no-install Windows .cmd helper."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile,zipfile
ROOT=Path(__file__).resolve().parent
spec=json.loads((ROOT/'ARCHIVE_SHA256.json').read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def check(p,size,digest):
    if not p.is_file() or p.stat().st_size!=size or sha(p)!=digest:raise RuntimeError('Missing or altered file: '+p.name)
def local(name):
    if Path(name).name!=name or name in ('','.', '..'):raise ValueError('Invalid manifest filename')
    return ROOT/name
for part in spec['parts']:check(local(part['name']),part['bytes'],part['sha256'])
out=local(spec['archive'])
if out.exists():check(out,spec['bytes'],spec['sha256'])
else:
    fd,name=tempfile.mkstemp(prefix=out.name+'.joining.',dir=ROOT);tmp=Path(name)
    try:
        with os.fdopen(fd,'wb') as f:
            for part in spec['parts']:
                with local(part['name']).open('rb') as inp:shutil.copyfileobj(inp,f)
        check(tmp,spec['bytes'],spec['sha256'])
        # Exclusive destination avoids overwriting a concurrently created output.
        with out.open('xb') as dest,tmp.open('rb') as src:shutil.copyfileobj(src,dest)
    finally:tmp.unlink(missing_ok=True)
with zipfile.ZipFile(out) as z:
    bad=z.testzip()
    if bad:raise RuntimeError('Archive CRC failed: '+bad)
print('Verified ZIP:',out.name)
print('Extract the ZIP and read its README.md.')
