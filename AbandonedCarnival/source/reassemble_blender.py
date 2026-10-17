"""Reassemble repository-sized Blender chunks with SHA256 verification.
Run: python CarnivalMap/source/reassemble_blender.py
The normal downloadable archive already contains the complete .blend file.
"""
from pathlib import Path
import hashlib
import json
import os

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'blender/source_parts.json').read_text())
target = root / manifest['output']
if target.exists():
    if (target.stat().st_size == manifest['bytes']
            and hashlib.sha256(target.read_bytes()).hexdigest() == manifest['sha256']):
        print('Existing Blender source is already verified:', target)
        raise SystemExit(0)
    raise SystemExit('Refusing to overwrite a different existing Blender file: ' + str(target))

temporary = Path(str(target) + '.assembling')
h = hashlib.sha256()
created_temporary = False
try:
    # Exclusive creation preserves any temporary file from an earlier attempt.
    with temporary.open('xb') as out:
        created_temporary = True
        for item in manifest['parts']:
            data = (root / item['path']).read_bytes()
            if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('Chunk verification failed: ' + item['path'])
            out.write(data)
            h.update(data)
    if temporary.stat().st_size != manifest['bytes']:
        raise ValueError('Complete source length mismatch')
    if h.hexdigest() != manifest['sha256']:
        raise ValueError('Complete source checksum mismatch')
    # Both operations fail if another process created the destination meanwhile.
    # Windows rename is no-clobber; POSIX rename is not, so use a same-volume link.
    if os.name == 'nt':
        os.rename(temporary, target)
    else:
        os.link(temporary, target)
        temporary.unlink()
    print('Verified Blender source:', target)
finally:
    if created_temporary and temporary.exists():
        temporary.unlink()
