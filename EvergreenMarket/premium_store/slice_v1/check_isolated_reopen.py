"""Read-only check, run with the master copied to a directory without textures/."""
import bpy,os,json,hashlib
R=os.path.dirname(os.path.abspath(__file__));records=[]
for im in bpy.data.images:
 if im.source!='FILE':continue
 external=bpy.path.abspath(im.filepath);size=list(im.size);pixel=list(im.pixels[(size[0]*(size[1]//2)+size[0]//2)*4:(size[0]*(size[1]//2)+size[0]//2)*4+4])
 records.append({'image':im.name,'packed':bool(im.packed_file),'size':size,'external_file_present':os.path.isfile(external),'centre_pixel_rgba':pixel,'loaded_from_packed_data':bool(im.packed_file) and not os.path.isfile(external) and len(pixel)==4 and pixel[3]>.99})
ok=len(records)==10 and all(x['loaded_from_packed_data'] and x['size']==[600,850] for x in records)
with open(bpy.data.filepath,'rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
with open(os.path.join(R,'PACKED_REOPEN_VALIDATION.json'),'w') as f:json.dump({'passed':ok,'isolated_blend_sha256':sha,'texture_count':len(records),'textures':records},f,indent=2)
print('ISOLATED_PACKED_REOPEN_PASS',ok,flush=True)
if not ok:raise RuntimeError('Isolated packed-texture reopen failed')
