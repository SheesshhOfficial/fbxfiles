import bpy,os,json
from mathutils import Vector
R=os.path.dirname(os.path.abspath(__file__));p=os.path.join(R,'EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend');bpy.ops.wm.open_mainfile(filepath=p)
pos={'olive_oil':(-.40,5.38),'wildflower_honey':(-.30,5.08),'strawberry_preserve':(-.10,5.08),'crushed_tomatoes':(.10,5.09),'coffee':(.31,5.17),'rolled_oats':(.10,5.43),'bronze_pasta':(.33,5.43)}
with open(os.path.join(R,'EXPORT_MANIFEST.json')) as f:m=json.load(f)
for rec in m['eligible_placements']:
 if abs(rec['position_m'][2]-.976)<1e-5:
  x,y=pos[rec['asset_id']];bpy.data.objects[rec['object_name']].location=(x,y,.976);rec['position_m']=[x,y,.976]
o=bpy.data.objects['03_Pantry_product_study'];old=o.data.lens;o.data.lens=67;o.location=(.43,3.66,1.39);o.rotation_euler=(Vector((-.02,5.22,1.14))-o.location).to_track_quat('-Z','Y').to_euler()
ratio=old/o.data.lens
for c in o.children:
 c.location.x*=ratio;c.location.y*=ratio
 if c.type=='FONT':c.data.size*=ratio
 else:c.scale.x*=ratio;c.scale.y*=ratio
with open(os.path.join(R,'EXPORT_MANIFEST.json'),'w') as f:json.dump(m,f,indent=2)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=p)
