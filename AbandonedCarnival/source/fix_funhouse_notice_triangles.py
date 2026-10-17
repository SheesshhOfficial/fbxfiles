import bpy,bmesh,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for o in bpy.data.objects:
 if o.type!='MESH' or not o.name.startswith('RF_FH_Notice_Type_'):continue
 me=o.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges));bad=[f for f in bm.faces if f.calc_area()<1e-12]
 if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
 bm.to_mesh(me);bm.free();me.update()
 for attempt in range(3):
  badidx=[p.index for p in me.polygons if p.area<=1e-12]
  if not badidx:break
  bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in badidx],context='FACES_ONLY');bm.to_mesh(me);bm.free();me.update()
 uv=me.uv_layers.active
 for p in me.polygons:
  a=max(range(3),key=lambda j:abs(p.normal[j]));ax=[j for j in range(3) if j!=a]
  for li in p.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[ax[0]],v[ax[1]])
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend',compress=True)
