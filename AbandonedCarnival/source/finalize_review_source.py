import bpy,os,sys,runpy
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source')
# Light participating haze: retain depth while avoiding a milky foreground.
m=bpy.data.materials.get('Thin blue dusk atmosphere')
if m:
 for n in m.node_tree.nodes:
  if n.type=='PRINCIPLED_VOLUME':n.inputs['Density'].default_value=.002
# Newly added practical meshes follow the same transport policy as festoon bulbs.
for o in bpy.data.objects:
 if o.type!='MESH':continue
 emissive=False
 for m in o.data.materials:
  if m and m.use_nodes:
   for n in m.node_tree.nodes:
    if n.type=='BSDF_PRINCIPLED' and n.inputs['Emission Strength'].default_value>0:
     col=n.inputs['Emission Color'].default_value
     if max(col[:3])>0:emissive=True
 if emissive:o.visible_diffuse=False;o.visible_volume_scatter=False
runpy.run_path(R+'/source/fix_refinement_uvs.py',run_name='__main__')
