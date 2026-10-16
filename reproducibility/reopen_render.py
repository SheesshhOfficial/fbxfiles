import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'));s=bpy.context.scene;s.camera=bpy.data.objects['CAM_SNIPER_POV'];s.render.resolution_x=1500;s.render.resolution_y=850;s.render.filepath=str(O/'Sniper_POV.png');bpy.ops.render.render(write_still=True)
masters=bpy.data.collections['SOURCE_MASTERS'];bpy.context.view_layer.update();inv=json.loads((O/'Asset_Inventory.json').read_text())
for r in inv:r['normalized_dimensions']=list(bpy.data.objects[r['name']].dimensions)
(O/'Asset_Inventory.json').write_text(json.dumps(inv,indent=2));r={'file_bytes':(O/'SnipersAim_Dense_Canyon_v2.blend').stat().st_size,'packed_images':len([im for im in bpy.data.images if im.packed_file]),'missing_images':[im.name for im in bpy.data.images if im.source=='FILE' and not im.size[0]],'source_mesh_count':len([o for o in masters.objects if o.type=='MESH']),'named_cameras':[o.name for o in bpy.data.objects if o.type=='CAMERA'],'eye':list(bpy.data.objects['SNIPER_EYE'].location)};(O/'Reopen_QA.json').write_text(json.dumps(r,indent=2));print('REOPEN_QA',json.dumps(r),flush=True)
