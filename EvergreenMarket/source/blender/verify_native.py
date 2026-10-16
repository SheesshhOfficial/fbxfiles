import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];s=bpy.context.scene
view_modes=[a.spaces.active.shading.type for scr in bpy.data.screens for a in scr.areas if a.type=='VIEW_3D']
for scr in bpy.data.screens:
 for a in scr.areas:
  if a.type=='VIEW_3D':a.spaces.active.shading.type='SOLID'
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file]
result={'native_reopen':'PASS','blender_version':bpy.app.version_string,'scene_objects':len(s.objects),'missing_external_images':missing,'font_packed':bool(bpy.data.fonts['DejaVu Sans Bold'].packed_file),'view_modes_before':view_modes,'saved_default':'SOLID','roof_visible':not bpy.data.collections['03_Roof_Ceiling'].hide_render,'scene_units':s.unit_settings.system,'scale_length':s.unit_settings.scale_length,'polish_layer_present':bool(s.get('polish_layer_v1')),'viewport_note':'Detailed ~15,000-object authoring scene. Solid mode recommended initially; no runtime performance guarantee.'}
assert not missing;assert result['font_packed'];assert result['polish_layer_present'];assert result['roof_visible'];assert s.unit_settings.scale_length==1
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Evergreen_Market.blend'),compress=True)
(R/'qa'/'native_reopen.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
