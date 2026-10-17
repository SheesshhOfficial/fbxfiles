"""Exact byte staging shared by V2 environment and prop exporters; no bpy dependency."""
from pathlib import Path
import hashlib

def texture_payload(source_path,packed_data=None):
 """Prefer existing source disk file; otherwise use original packed file bytes.
 packed_data may be a lazy callable so large Blender buffers are only read on fallback.
 Returns (payload bytes, original basename, origin label, full SHA256).
 """
 path=Path(source_path)
 name=path.name
 if not name or name in {'.','..'}:raise RuntimeError('Texture has no safe original basename')
 if path.is_file():payload=path.read_bytes();origin='disk'
 else:
  payload=packed_data() if callable(packed_data) else packed_data
  if payload is None:raise RuntimeError('Unresolved texture with no packed bytes: '+str(path))
  payload=bytes(payload);origin='packed_file'
 if not payload:raise RuntimeError('Empty texture payload: '+str(path))
 return payload,name,origin,hashlib.sha256(payload).hexdigest()

def staged_texture_path(texture_dir,payload_record,write=False):
 payload,name,origin,digest=payload_record
 dest=Path(texture_dir)/(digest[:16]+'_'+name)
 if dest.exists():
  if not dest.is_file() or hashlib.sha256(dest.read_bytes()).hexdigest()!=digest:
   raise RuntimeError('Staged texture content mismatch: '+str(dest))
 elif write:
  # Exclusive creation prevents overwriting a concurrently staged different file.
  with dest.open('xb') as f:f.write(payload)
 else:raise RuntimeError('Environment texture has not been staged: '+str(dest))
 return dest
