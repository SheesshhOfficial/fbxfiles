"""Normalize packed texture references for portable reopening of the saved master."""
import bpy,os,json,hashlib
R=os.path.dirname(os.path.abspath(__file__));p=os.path.join(R,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend');bpy.ops.wm.open_mainfile(filepath=p)
records=[]
for im in bpy.data.images:
 if im.source=='FILE':
  if not im.packed_file:im.pack()
  im.filepath='//textures/'+os.path.basename(im.filepath)
  records.append({'image':im.name,'filepath':im.filepath,'packed':bool(im.packed_file),'size':list(im.size)})
assert len(records)==10 and all(r['packed'] and r['size']==[600,850] for r in records)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=p)
with open(p,'rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
with open(os.path.join(R,'PACKED_TEXTURE_VALIDATION.json'),'w') as f:json.dump({'master_sha256':sha,'all_ten_labels_packed':True,'all_texture_paths_relative':True,'textures':records,'isolated_reopen':'See PACKED_REOPEN_VALIDATION.json'},f,indent=2)
print('PACKED_RELATIVE_TEXTURES_VERIFIED',len(records),sha,flush=True)
