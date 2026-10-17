import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;m=json.load(open(R/'REFINEMENT_MANIFEST.json'));s=bpy.data.scenes['Scene'];bpy.context.window.scene=s
for o in bpy.context.selected_objects:o.select_set(False)
names=sorted(set(m['changed_objects']+m['added_objects']))
for name in names:bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects[names[0]]
bpy.ops.object.convert(target='MESH')
cleanup={}
for o in bpy.context.selected_objects:
 bm=bmesh.new();bm.from_mesh(o.data);bad=[f for f in bm.faces if f.calc_area()<1e-12]
 if bad:bmesh.ops.delete(bm,geom=bad,context='FACES');bm.to_mesh(o.data);cleanup[o.name]=len(bad)
 bm.free()
bpy.context.view_layer.update();expected={}
for name in names:
 o=bpy.data.objects[name];co=[o.matrix_world@v.co for v in o.data.vertices];expected[name]={'min':[min(v[i] for v in co) for i in range(3)],'max':[max(v[i] for v in co) for i in range(3)],'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':[x.name for x in o.data.materials]}
json.dump({'objects':expected,'zero_area_faces_removed':cleanup},open(R/'OVERLAY_GEOMETRY.json','w'),indent=2)
bpy.ops.export_scene.gltf(filepath=str(R/'REFINEMENT_v3_OVERLAY.glb'),export_format='GLB',use_selection=True,use_active_scene=True,export_apply=True,export_yup=True,export_extras=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'REFINEMENT_v3_OVERLAY.glb'));actual={o.name:o for o in bpy.data.objects if o.type=='MESH'};errors=[];maxerr=0
for name,e in expected.items():
 o=actual.get(name)
 if not o:errors.append(name+': missing');continue
 co=[o.matrix_world@v.co for v in o.data.vertices];mn=[min(v[i] for v in co) for i in range(3)];mx=[max(v[i] for v in co) for i in range(3)];err=max(abs(a-b) for a,b in zip(mn+mx,e['min']+e['max']));maxerr=max(maxerr,err)
 if err>1e-4:errors.append(name+': bounds '+str(err))
 if sum(len(p.vertices)-2 for p in o.data.polygons)!=e['triangles']:errors.append(name+': triangle count')
extras=set(actual)-set(expected)
if extras:errors.append('Extras: '+str(extras))
r={'objects_expected':len(expected),'objects_imported':len(actual),'max_world_bounds_error_m':maxerr,'geometry_match':not errors,'all_images_packed':all(i.packed_file for i in bpy.data.images if i.source=='FILE'),'images':len(bpy.data.images),'errors':errors,'full_store_export':False,'Unreal_tested':False}
json.dump(r,open(R/'OVERLAY_ROUNDTRIP_QA.json','w'),indent=2);print(r,flush=True);assert not errors
