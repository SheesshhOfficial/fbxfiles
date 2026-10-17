"""Pure file/byte tests; no Blender, no writes to generated export directory."""
from pathlib import Path
import tempfile,hashlib,json
from v2_texture_staging import texture_payload,staged_texture_path
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);out=root/'textures';out.mkdir();source=root/'original.png'
 packed=b'\x89PNG\r\n\x1a\nexact packed payload\x00\xff'
 record=texture_payload(source,lambda:packed)
 assert record[0]==packed and record[1]=='original.png' and record[2]=='packed_file'
 dest=staged_texture_path(out,record,write=True)
 assert dest.name==hashlib.sha256(packed).hexdigest()[:16]+'_original.png' and dest.read_bytes()==packed
 assert staged_texture_path(out,record,write=False)==dest
 source.write_bytes(b'existing disk payload')
 disk=texture_payload(source,lambda:(_ for _ in ()).throw(AssertionError('Packed fallback unnecessarily read')))
 assert disk[0]==b'existing disk payload' and disk[2]=='disk'
 rejected=0
 for fn in [lambda:texture_payload(root/'missing.png'),lambda:texture_payload(root/'empty.png',b''),lambda:staged_texture_path(out,disk,write=False)]:
  try:fn()
  except RuntimeError:rejected+=1
 assert rejected==3
 dest.write_bytes(b'wrong')
 try:staged_texture_path(out,record,write=True)
 except RuntimeError:pass
 else:raise AssertionError('Corrupt stage must not be overwritten')
 assert dest.read_bytes()==b'wrong'
report={'scope':'Pure Python tempfile tests only; no Blender loaded or existing export artifacts changed','passed':True,'checks':['packed byte identity and original basename','SHA256 naming','read-only prop lookup','disk preferred with lazy packed fallback','missing and empty fail','missing staged file fails','corruption fails without overwrite'],'current_export_regenerated':False}
(Path(__file__).resolve().parents[1]/'qa/v2_texture_staging_preparation.json').write_text(json.dumps(report,indent=2));print('PASS packed fallback and disk precedence; fail-closed staging')
