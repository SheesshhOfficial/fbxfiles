import bpy,os,json,sys,math
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=bpy.context.scene
issues=[]; stats={'objects':len(s.objects),'mesh_objects':0,'vertices':0,'polygons':0,'missing_uv':[],'invalid_material_faces':[],'nonfinite':[],'eligible_props':[],'player_starts':[]}
for o in s.objects:
 if o.name.startswith('PlayerStart'):stats['player_starts'].append(list(o.location))
 if o.type!='MESH':continue
 stats['mesh_objects']+=1;stats['vertices']+=len(o.data.vertices);stats['polygons']+=len(o.data.polygons)
 if not o.data.uv_layers:stats['missing_uv'].append(o.name)
 if any(p.material_index>=len(o.data.materials) for p in o.data.polygons):stats['invalid_material_faces'].append(o.name)
 if any(not math.isfinite(c) for v in o.data.vertices for c in v.co):stats['nonfinite'].append(o.name)
 if o.get('PropActorTag'):stats['eligible_props'].append({'object':o.name,'family':o.get('asset_family','unspecified'),'position':list(o.location)})
stats['packed_images']=len([i for i in bpy.data.images if i.packed_file]);stats['unreal_runtime_tested']=False
open(R+'/qa/reopened_scene_audit.json','w').write(json.dumps(stats,indent=2))
print(json.dumps({k:v for k,v in stats.items() if k not in ['eligible_props','player_starts']},indent=2))
if '--render' in sys.argv:
 cams=sys.argv[sys.argv.index('--render')+1:] or ['Camera_Midway']
 s.render.resolution_percentage=75;s.cycles.samples=64;s.cycles.use_denoising=False
 for name in cams:
  s.camera=bpy.data.objects[name];s.render.filepath=R+'/renders/'+name+'.png';bpy.ops.render.render(write_still=True)
