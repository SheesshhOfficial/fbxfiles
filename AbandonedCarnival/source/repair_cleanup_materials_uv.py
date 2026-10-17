import bpy,json,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));original=json.load(open(R+'/qa/precleanup_material_slots.json'));records=json.load(open(R+'/qa/evaluated_decor_cleanup.json'))['objects'];fixed=0
for rec in records:
 name=rec['object'];o=bpy.data.objects.get(name)
 if not o or o.type!='MESH':o=bpy.data.objects.get(name+' clean')
 if not o or o.type!='MESH':raise RuntimeError('Missing cleaned object '+name)
 names=original[name]
 if any(n is None or n not in bpy.data.materials for n in names):raise RuntimeError('Unrecoverable original material '+name+repr(names))
 o.data.materials.clear()
 for n in names:o.data.materials.append(bpy.data.materials[n])
 me=o.data;layer=me.uv_layers.active or me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  pts=[layer.data[i].uv.copy() for i in p.loop_indices];a=abs(sum(pts[j].x*pts[(j+1)%len(pts)].y-pts[(j+1)%len(pts)].x*pts[j].y for j in range(len(pts)))*.5)
  if a>1e-12:continue
  axis=max(range(3),key=lambda j:abs(p.normal[j]));axes=[j for j in range(3) if j!=axis];origin=me.vertices[p.vertices[0]].co
  for li in p.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co-origin;layer.data[li].uv=(v[axes[0]],v[axes[1]])
  fixed+=1
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True);print('Recovered exact source material slots on',len(records),'objects; UV faces fixed',fixed)
