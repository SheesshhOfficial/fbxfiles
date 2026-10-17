"""One tracked actual Cycles zone review per invocation, -- <zone>."""
import bpy,sys,os,json,hashlib,time
from mathutils import Vector
source_hash=hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest()
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));zone='Maintenance'
views={'Carousel':((8,-.5,2.1),(0,8,2.8),28),'Funhouse':((16,-1.5,2.6),(16,9,3.1),22),'Maintenance':((16.6,-13.5,2.3),(16.6,-2,1.9),24),'Arena':((-8.8,1.7,1.9),(-18,12,2.3),30),'Gate':((0,-29.8,2),(0,-21,3),25),'Overview':((43,-55,43),(0,0,0),38)}
loc,target,lens=views[zone];s=bpy.context.scene;data=bpy.data.cameras.new('Review '+zone);cam=bpy.data.objects.new('Review '+zone,data);s.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;s.camera=cam
s.render.resolution_x=1280;s.render.resolution_y=800;s.render.resolution_percentage=100;s.cycles.samples=640;s.cycles.use_denoising=False;s.cycles.sample_clamp_indirect=2;s.cycles.sample_clamp_direct=10
nt=s.node_tree;rl=next(n for n in nt.nodes if n.type=='R_LAYERS');g=next(n for n in nt.nodes if n.type=='GLARE');blur=nt.nodes.new('CompositorNodeBlur');blur.filter_type='GAUSS';blur.size_x=1;blur.size_y=1;nt.links.new(rl.outputs['Image'],blur.inputs['Image']);nt.links.new(blur.outputs['Image'],g.inputs['Image'])
s.render.filepath=R+'/renders/Maintenance_Hero.png';bpy.ops.render.render(write_still=True)

json.dump({'source_blend':os.path.basename(bpy.data.filepath),'source_sha256':source_hash,'zone':zone,'camera_location':loc,'camera_target':target,'lens_mm':lens,'resolution':[1280,800],'cycles_samples':640,'denoising':False,'actual_blender_render':True,'render_file':s.render.filepath},open(R+'/qa/render_maintenance_hero_manifest.json','w'),indent=2)
