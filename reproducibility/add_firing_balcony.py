import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'output';bpy.ops.wm.open_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'));s=bpy.context.scene;c=bpy.data.collections['02_TOWER']
m=bpy.data.materials.get('Balcony dark steel') or bpy.data.materials.new('Balcony dark steel');m.use_nodes=True;m.diffuse_color=(.14,.17,.18,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Metallic'].default_value=.65;bs.inputs['Roughness'].default_value=.65
for name,loc,dims in [('Sniper firing balcony',(0,86,21.8536),(3.2,4,.22)),('Balcony left stringer',(-1.35,86.1,21.65),(.18,4.5,.25)),('Balcony right stringer',(1.35,86.1,21.65),(.18,4.5,.25))]:
 if name in bpy.data.objects:continue
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 for cl in list(o.users_collection):cl.objects.unlink(o)
 c.objects.link(o);o['purpose']='Original added firing balcony supporting unobstructed sniper stance at tower deck height'
for name in ['SNIPER_EYE','CAM_SNIPER_POV']:bpy.data.objects[name].location=(0,85.8,23.55)
cam=bpy.data.objects['CAM_SNIPER_POV'];cam.rotation_euler=(Vector((0,-30,1.4))-cam.location).to_track_quat('-Z','Y').to_euler();bpy.data.objects['Sniper display rifle'].location.y=86.5
mp=O/'Layout_Manifest.json';rows=json.loads(mp.read_text());rows=[r for r in rows if not r.get('generated_geometry')]
for r in rows:
 if r['object']=='Sniper display rifle':r['position']=[0,86.5,22.2];r['unity_position_xyz']=[0,22.2,86.5]
for ob in c.objects:
 if ob.name.startswith(('Sniper firing balcony','Balcony ')):
  rows.append({'object':ob.name,'source_id':None,'generated_geometry':'cube','position':list(ob.location),'dimensions_xyz':list(ob.dimensions),'unity_position_xyz':[ob.location.x,ob.location.z,ob.location.y],'unity_dimensions_xyz':[ob.dimensions.x,ob.dimensions.z,ob.dimensions.y],'material':'Balcony dark steel'})
mp.write_text(json.dumps(rows,indent=2))
s.camera=bpy.data.objects['CAM_OVERVIEW'];bpy.ops.wm.save_as_mainfile(filepath=str(O/'SnipersAim_Dense_Canyon_v2.blend'),compress=True)
for name,camera,res in [('Sniper_POV','CAM_SNIPER_POV',(1500,850)),('Topdown','CAM_TOPDOWN',(1000,1800)),('Overview','CAM_OVERVIEW',(1500,1050)),('Runner_Approach','CAM_RUNNER_APPROACH',(1500,850))]:
 bpy.data.collections['05_LAYOUT_GUIDES'].hide_render=name!='Topdown';s.camera=bpy.data.objects[camera];s.render.resolution_x,s.render.resolution_y=res;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
