"""Final QA-driven attachment corrections and calibrated floor image. Run after build_refinement.py."""
import bpy,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent;m=json.load(open(R/'REFINEMENT_MANIFEST.json'))
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s;col=bpy.data.collections['13_INTERIOR_REFINEMENT_v3']
# Header paint face was coplanar with original text, so offset complete plaques forward.
for rec in m['sign_attachments']:
 if rec.get('body') in ['COLD STORE','STAFF OFFICE','BREAK ROOM']:
  for name in [rec['text'],rec['backing']]+rec['supports']:bpy.data.objects[name].location.y-=.035
  rec['header_clearance_correction_m']=.035;rec['header_embed_m']=.003
# Calibrate image pixels in scene-linear values: warm greige, not almost-white.
im=bpy.data.images['V3_Stone_BaseColor'];n=1024;xx,yy=np.meshgrid(np.arange(n)/n,np.arange(n)/n);rng=np.random.default_rng(318);noise=np.zeros((n,n))
for k,f in enumerate([2,4,9,19,41]):noise+=np.sin(2*np.pi*(xx*f+yy*(f//2+1))+k)*np.cos(2*np.pi*(yy*(f+1)-xx*(f//3+1)))*(.012/(k+1))
noise+=rng.normal(0,.0035,(n,n));rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(np.array([.34,.295,.235])+noise[:,:,None],0,1);im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(R/'textures/V3_Stone_BaseColor.png');im.save();im.pack();im.filepath='//textures/V3_Stone_BaseColor.png'
# Add a true continuous carrier behind the retained exterior v2 wordmark.
c=(31.99848,-.744,5.19192);dims=(8.47,.126,1.00);x,y,z=[v/2 for v in dims];vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)];fs=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];me=bpy.data.meshes.new('V3_Exterior_wordmark_carrier');me.from_pydata(vs,[],fs);me.materials.append(bpy.data.materials['V3_Charcoal_hardware']);me.update();o=bpy.data.objects.new('V3_Exterior_wordmark_carrier',me);col.objects.link(o);o.location=c;o['Prop']=False;o['refinement_v3']=True;o['collision_category']='decorative_nonblocking_attached_trim';o['collision']='None; exterior facade above 4.69 m, existing boundary unchanged';o['export_scope']='V3 visual overlay';m['added_objects'].append(o.name)
m['exterior_wordmark_mount']={'text':'EXT2_Brand_name','carrier':o.name,'method':'Continuous carrier spans retained oak fins and contacts backing; original text and facade untouched','letter_overlap_m':.006,'backing_overlap_m':.009}
# Raised letters physically intersect their boards by 0.3 mm.
for rec in m['sign_attachments']:
 if not rec.get('unchanged'):
  bpy.data.objects[rec['text']].data.extrude=.003
  rec['glyph_backing_embed_m']=.0003
# Keep physical counter glazing unchanged after user confirmed correct rendered view.
m['counter_status']='Original physical glass, 6 counter meshes, products and open staff-side access unchanged; user confirmed visible in render.'
m['floor_basecolor_scene_linear']=[.34,.295,.235]
json.dump(m,open(R/'REFINEMENT_MANIFEST.json','w'),indent=2)
bpy.context.view_layer.update();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'YOU_WANT_IT_YOU_GET_IT_REFINED_v3.blend'),compress=True)
print('FINALIZED_REFINEMENT',flush=True)
