import bpy, hashlib, json, datetime
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent
source=R/'YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend'
out=R/'FINAL_SIGNS_256.png'
expected='c4abf30a478051c30e00536642416c53fefb7db4911128dbb8114c0732975519'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(source)
assert before==expected, (before,expected)
assert Path(bpy.data.filepath).resolve()==source.resolve()
assert not out.exists(), 'Refusing to overwrite image'
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s
loc,target,lens=(12,10.2,2.15),(30,23,2.3),26
d=bpy.data.cameras.new('V3_Final_Proof_SIGNS');cam=bpy.data.objects.new('V3_Final_Proof_SIGNS',d);s.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=400;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=256;s.cycles.use_denoising=False;s.cycles.use_adaptive_sampling=True;s.cycles.adaptive_threshold=.025;s.cycles.max_bounces=6;s.render.threads_mode='FIXED';s.render.threads=8;s.render.resolution_x=1200;s.render.resolution_y=850;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(out)
bpy.ops.render.render(write_still=True,scene=s.name)
after=sha(source)
assert after==before, 'Source changed during render'
assert out.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
record={'source':str(source),'source_sha256_before':before,'source_sha256_after':after,'source_unchanged':before==after,'output':str(out),'output_sha256':sha(out),'output_bytes':out.stat().st_size,'blender_version':bpy.app.version_string,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'settings':{'engine':'CYCLES','samples':256,'denoising':False,'adaptive_sampling':True,'adaptive_threshold':.025,'max_bounces':6,'threads':8,'resolution':[1200,850],'camera_location':loc,'camera_target':target,'lens_mm':lens,'clip_end':400},'source_saved':False,'note':'Rendered the final exact source with temporary camera/settings in memory only. No source or existing preview image was overwritten.'}
(R/'FINAL_RENDER_PROVENANCE.json').write_text(json.dumps(record,indent=2)+'\n')
print('FINAL_SIGNS_READY',json.dumps(record),flush=True)
