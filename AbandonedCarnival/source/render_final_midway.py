import bpy,os
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));s=bpy.context.scene;s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100;s.cycles.samples=256;s.cycles.use_denoising=False
s.cycles.sample_clamp_indirect=2;s.cycles.sample_clamp_direct=10
# Small native compositor reconstruction filter for high-frequency sample noise.
nt=s.node_tree;rl=next(n for n in nt.nodes if n.type=='R_LAYERS');g=next(n for n in nt.nodes if n.type=='GLARE');blur=nt.nodes.new('CompositorNodeBlur');blur.filter_type='GAUSS';blur.size_x=1;blur.size_y=1;nt.links.new(rl.outputs['Image'],blur.inputs['Image']);nt.links.new(blur.outputs['Image'],g.inputs['Image'])
cam=bpy.data.objects['Camera_Midway'];cam.location=(-10.4,-19.4,1.7);cam.rotation_euler=(Vector((-14.6,-1,2))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=32;s.camera=cam;s.render.filepath=R+'/renders/artpass/Midway_Detailed_Review.png';bpy.ops.render.render(write_still=True)
