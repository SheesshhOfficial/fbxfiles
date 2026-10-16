import bpy
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=False
s.use_nodes=True;n=s.node_tree.nodes;l=s.node_tree.links;n.clear();r=n.new('CompositorNodeRLayers');f=n.new('CompositorNodeBilateralblur');f.iterations=2;f.sigma_color=.15;f.sigma_space=4;o=n.new('CompositorNodeComposite');l.new(r.outputs['Image'],f.inputs['Image']);l.new(r.outputs['Image'],f.inputs['Determinator']);l.new(f.outputs['Image'],o.inputs['Image'])
s.render.resolution_x=1280;s.render.resolution_y=800;s.render.resolution_percentage=100;s.camera=bpy.data.objects['CAM_Interior_Hero'];s.render.filepath='/workspace/scratch/26eeef986c30/supermarket_delivery/previews/01_Interior_Filtered_Test.png'
bpy.ops.render.render(write_still=True)
