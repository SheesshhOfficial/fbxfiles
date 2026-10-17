import bpy,sys,os,json,hashlib,importlib,time
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path[:0]=[R+'/iterations/source',R+'/source']
args=sys.argv[sys.argv.index('--')+1:];number=int(args[0]);module=args[1];function=args[2];zone=args[3]
parent=bpy.data.filepath;parent_sha=hashlib.sha256(open(parent,'rb').read()).hexdigest();before={o.name for o in bpy.data.objects};result=getattr(importlib.import_module(module),function)()
s=bpy.context.scene;s['refinement_cycle_completed']=number
views={'Ground':((-10,-21,1.7),(-12,-17,.3),34),'Ticket':((14.5,-24.6,2.1),(9.7,-20.9,1.5),28),'Maintenance':((16.6,-13.5,2.3),(16.6,-2,1.9),24),'Midway':((-10,-24,2.3),(-10,-7,2.0),25),'Arena':((-8.8,1.7,1.9),(-18,12,2.3),30),'Carousel':((8,-.5,2.1),(0,8,2.8),28),'Funhouse':((16,-1.5,2.6),(16,9,3.1),22),'Gate':((0,-29.8,2),(0,-21,3),25),'Overview':((43,-55,43),(0,0,0),38)}
loc,target,lens=views[zone];d=bpy.data.cameras.new('Cycle %02d review'%number);cam=bpy.data.objects.new(d.name,d);s.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;s.camera=cam
s.render.resolution_x=1100;s.render.resolution_y=700;s.render.resolution_percentage=100;s.cycles.samples=128;s.cycles.use_denoising=False;s.cycles.sample_clamp_indirect=2;s.cycles.sample_clamp_direct=10
out=R+'/iterations/Cycle_%02d.blend'%number;s.render.filepath=R+'/iterations/renders/Cycle_%02d_%s.png'%(number,zone)
bpy.ops.wm.save_as_mainfile(filepath=out,compress=True)
report={'cycle':number,'zone':zone,'parent_source':parent,'parent_sha256':parent_sha,'checkpoint':out,'checkpoint_sha256':hashlib.sha256(open(out,'rb').read()).hexdigest(),'improvement':result,'added_objects':len({o.name for o in bpy.data.objects}-before),'actual_render':s.render.filepath,'samples':128,'review_status':'rendering','unreal_runtime_verified':False}
report['scene_lighting']={'exposure':s.view_settings.exposure,'world_strength':s.world.node_tree.nodes.get('Background').inputs[1].default_value if s.world and s.world.use_nodes and s.world.node_tree.nodes.get('Background') else None,'lights':[{'name':o.name,'kind':o.data.type,'energy':o.data.energy,'color':list(o.data.color),'position':list(o.location)} for o in s.objects if o.type=='LIGHT']};path=R+'/iterations/qa/Cycle_%02d.json'%number;json.dump(report,open(path,'w'),indent=2)
bpy.ops.render.render(write_still=True);report['review_status']='awaiting visual inspection';json.dump(report,open(path,'w'),indent=2);print('CYCLE_COMPLETE',number)
