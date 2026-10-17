import bpy,os,json
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));vs=[];fs=[];mids=[]
for cell in json.load(open(R+'/source/pavement_cells.json')):
 k=len(vs);vs.extend([(x,y,cell['height']) for x,y in cell['polygon']]);fs.append(tuple(range(k,len(vs))));mids.append(1 if cell['rubble'] else 0)
me=bpy.data.meshes.new('Organic fractured pavement');me.from_pydata(vs,[],fs);me.materials.append(bpy.data.materials['Scanned cracked paving']);me.materials.append(bpy.data.materials['ground']);uv=me.uv_layers.new()
for p,idx in zip(me.polygons,mids):
 p.material_index=idx;tile=2 if idx else 2.5
 for li in p.loop_indices:
  v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v.x/tile,v.y/tile)
bpy.data.objects['Cracked uneven asphalt surface'].data=me
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend')
