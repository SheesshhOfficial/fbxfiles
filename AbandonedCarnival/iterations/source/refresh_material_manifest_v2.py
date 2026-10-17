"""Save-free refresh of material manifest, compatibility QA and source portability QA.
Caller loads frozen Cycle_10.blend. All textures must already be staged.
No FBX export, new texture creation, import-helper write, or blend save.
"""
import bpy,sys,os,json,hashlib
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(PROJECT/'iterations/source'),str(PROJECT/'source')]
from v2_texture_staging import texture_payload,staged_texture_path
from export_material_manifest_v2 import export_material_manifest
ROOT=PROJECT/'iterations/export'
source=Path(bpy.data.filepath).resolve()
if source!=(PROJECT/'iterations/Cycle_10.blend').resolve():raise RuntimeError('Load frozen Cycle_10.blend')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source_hash=sha(source)
if source_hash!=os.environ.get('CARNIVAL_V2_SOURCE_SHA256'):raise RuntimeError('Approved source hash missing/mismatch')
manifest=json.loads((ROOT/'unreal/environment_manifest.json').read_text())
if manifest['source_sha256']!=source_hash:raise RuntimeError('Environment source hash mismatch')
prop=ROOT/'unreal/prop_placements.json'
if prop.exists() and json.loads(prop.read_text())['source_blend_sha256']!=source_hash:raise RuntimeError('Prop source hash mismatch')
# Verification of existing texture staging only; paths changed in memory.
image_checks=[]
for image in bpy.data.images:
 if image.source!='FILE' or not image.filepath:continue
 path=Path(bpy.path.abspath(image.filepath)).resolve()
 payload=texture_payload(path,lambda image=image:bytes(image.packed_file.data) if image.packed_file else None)
 staged=staged_texture_path(ROOT/'textures',payload,write=False)
 packed_bytes=bytes(image.packed_file.data) if image.packed_file else None
 packed_hash=hashlib.sha256(packed_bytes).hexdigest() if packed_bytes is not None else None
 image_checks.append({'image':image.name,'original_basename':path.name,'packed':packed_bytes is not None,'packed_bytes':len(packed_bytes) if packed_bytes is not None else 0,'packed_sha256':packed_hash,'staged_path':staged.relative_to(ROOT).as_posix(),'staged_sha256':sha(staged),'packed_matches_staged':packed_hash==sha(staged) if packed_hash else False})
 image.filepath=str(staged)
export_material_manifest(ROOT,source,source_hash)
if sha(source)!=source_hash:raise RuntimeError('Source changed during refresh')
font_checks=[]
for font in bpy.data.fonts:
 builtin=font.filepath=='<builtin>' or font.name=='Bfont'
 packed=font.packed_file
 font_checks.append({'font':font.name,'builtin':builtin,'packed':bool(packed),'packed_bytes':len(packed.data) if packed else 0,'packed_sha256':hashlib.sha256(bytes(packed.data)).hexdigest() if packed else None,'available_without_original_path':builtin or bool(packed)})
portability={'source_sha256':source_hash,'source_sha256_after':sha(source),'source_unchanged':sha(source)==source_hash,'scope':'Read-only packed image/font availability and exact byte comparison to existing staged files; no unpacking/source save','expected_file_images':41,'file_image_count':len(image_checks),'expected_image_count_matches':len(image_checks)==41,'all_images_packed_and_match_staged':all(r['packed_matches_staged'] for r in image_checks),'all_fonts_available_without_original_path':all(r['available_without_original_path'] for r in font_checks),'images':image_checks,'fonts':font_checks,'runtime_verified':False}
(ROOT/'qa/source_portability.json').write_text(json.dumps(portability,indent=2))
print('REFRESHED_ONLY unreal/material_manifest.json qa/environment_material_compatibility.json and qa/source_portability.json; source SHA',source_hash)
