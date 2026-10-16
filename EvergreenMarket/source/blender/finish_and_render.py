"""Final validation, portable save, and presentation-camera renderer.
Run after build_supermarket.py: blender -b Evergreen_Market.blend --python source/finish_and_render.py
Optional --quick or --qa-only, or --views 01_Interior_Hero,08_Topdown
"""
import bpy,sys,json,math,os,time
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];scene=bpy.context.scene
# Remove accidental exact duplicates if an earlier authoring version was used.
seen={};removed=0
for o in list(scene.objects):
 if o.type not in ('MESH','CURVE'):continue
 if o.type=='MESH':geom=(o.type,o.data.as_pointer())
 else:
  if 'Fence rails' not in o.name:continue
  geom=(o.type,tuple(tuple(round(v,5) for v in p.co) for s in o.data.splines for p in s.points),o.data.bevel_depth)
 key=(geom,tuple(round(v,5) for v in o.location),tuple(round(v,5) for v in o.rotation_euler),tuple(round(v,5) for v in o.scale))
 if key in seen:bpy.data.objects.remove(o,do_unlink=True);removed+=1
 else:seen[key]=o
if not bpy.data.objects.get('Late morning sunlight'):
 d=bpy.data.lights.new('Late morning sunlight','SUN');d.energy=1.5;d.angle=.12;o=bpy.data.objects.new('Late morning sunlight',d);bpy.data.collections['40_Lighting'].objects.link(o);o.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-28))
# Add a close human-scale detail camera; keep the full scene editable.
if not bpy.data.objects.get('CAM_Grocery_Detail'):
 d=bpy.data.cameras.new('CAM_Grocery_Detail');o=bpy.data.objects.new('CAM_Grocery_Detail',d);bpy.data.collections['50_Cameras'].objects.link(o);o.location=(-10.7,-6.2,1.7);o.rotation_euler=(Vector((-8.55,-5.3,1.05))-o.location).to_track_quat('-Z','Y').to_euler();d.lens=45
# Final file always opens with its complete roof/walls.
for c in scene.collection.children:c.hide_render=False
for o in scene.objects:o.hide_render=False if o.type!='EMPTY' else True
scene.camera=bpy.data.objects['CAM_Interior_Hero'];scene.render.engine='CYCLES';scene.cycles.samples=192;scene.cycles.use_denoising=False
scene.cycles.caustics_reflective=False;scene.cycles.caustics_refractive=False;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=3;scene.cycles.transmission_bounces=6;scene.cycles.max_bounces=8;scene.cycles.sample_clamp_indirect=3.0
for name,color in [('deep evergreen',(.015,.07,.045,1)),('sage enamel',(.18,.28,.17,1))]:
 m=bpy.data.materials[name];m.diffuse_color=color;m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=color
scene.render.resolution_x=1920;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
# Edge-aware compositor pass keeps CPU previews clean without an external denoiser.
scene.use_nodes=True
n=scene.node_tree.nodes;links=scene.node_tree.links;n.clear()
r=n.new('CompositorNodeRLayers');r.location=(-400,0)
f=n.new('CompositorNodeBilateralblur');f.name='Gentle edge-aware grain filter';f.iterations=2;f.sigma_color=.15;f.sigma_space=4;f.location=(-100,0)
c=n.new('CompositorNodeComposite');c.location=(180,0)
links.new(r.outputs['Image'],f.inputs['Image']);links.new(r.outputs['Image'],f.inputs['Determinator']);links.new(f.outputs['Image'],c.inputs['Image'])
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.shading.type='SOLID'
bpy.ops.file.pack_all()
# Remove unused staging mesh datablocks and save compressed native scene.
for mesh in list(bpy.data.meshes):
 if mesh.users==0:bpy.data.meshes.remove(mesh)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Evergreen_Market.blend'),compress=True)
qa={'blender_version':bpy.app.version_string,'object_count':len(scene.objects),'mesh_objects':sum(o.type=='MESH' for o in scene.objects),'unique_meshes':len(bpy.data.meshes),'curve_objects':sum(o.type=='CURVE' for o in scene.objects),'text_objects':sum(o.type=='FONT' for o in scene.objects),'materials':len(bpy.data.materials),'image_files':len(bpy.data.images),'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'fonts':[{'name':f.name,'packed':bool(f.packed_file)} for f in bpy.data.fonts],'removed_duplicate_objects':removed,'collections':{c.name:len(c.objects) for c in scene.collection.children},'units':'metres;1 Blender unit = 1 metre','building_dimensions_m':[44,48,5.45],'player_count_assumption':'8–12; not playtested','gameplay':'environment art only','invalid_transform_objects':[o.name for o in scene.objects if any(not math.isfinite(v) for v in (*o.location,*o.scale,*o.rotation_euler))],'empty_meshes':[m.name for m in bpy.data.meshes if len(m.vertices)==0],'unpacked_external_images':[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file],'route_design':['Shop ↔ Stockroom A at x -14','Shop ↔ Stockroom B at x 3','Shop ↔ Staff at x 15','Stock ↔ Staff at y 24','Staff ↔ Yard at y 25','Yard ↔ Shop at y 8'],'route_test_status':'Geometric design only; no capsule or gameplay test in Unreal'}
tri_unique=0
for m in bpy.data.meshes:tri_unique+=sum(len(p.vertices)-2 for p in m.polygons)
qa['unique_mesh_triangle_estimate']=tri_unique;qa['instanced_mesh_triangle_estimate']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in scene.objects if o.type=='MESH')
with open(ROOT/'qa'/'scene_validation.json','w') as f:json.dump(qa,f,indent=2)
with open(ROOT/'manifest.json','w') as f:json.dump(qa,f,indent=2)
print('QA_COMPLETE',json.dumps(qa),flush=True)
if '--qa-only' in sys.argv:sys.exit(0)
views={'01_Interior_Hero':'CAM_Interior_Hero','02_Produce_Bakery':'CAM_Produce_Bakery','03_Checkouts':'CAM_Checkouts','04_Stockroom':'CAM_Stockroom','05_Staff_Room':'CAM_Staff_Room','06_Exterior':'CAM_Exterior','07_Cutaway':'CAM_Cutaway','08_Topdown':'CAM_Topdown','09_Grocery_Detail':'CAM_Grocery_Detail'}
selected=list(views)
if '--views' in sys.argv:selected=sys.argv[sys.argv.index('--views')+1].split(',')
quick='--quick' in sys.argv
if quick:scene.render.resolution_x=1280;scene.render.resolution_y=800;scene.cycles.samples=24
if '--samples' in sys.argv:scene.cycles.samples=int(sys.argv[sys.argv.index('--samples')+1])
if '--resolution' in sys.argv:
 scene.render.resolution_x=int(sys.argv[sys.argv.index('--resolution')+1]);scene.render.resolution_y=int(scene.render.resolution_x*.625)
for name in selected:
 for c in scene.collection.children:c.hide_render=False
 for o in scene.objects:
  if o.type!='EMPTY':o.hide_render=False
 if name in ('07_Cutaway','08_Topdown'):
  bpy.data.collections['03_Roof_Ceiling'].hide_render=True
  # Keep partitions and external walls for accurate plans; remove only front glazing for perspective cutaway.
  if name=='07_Cutaway':
   bpy.data.collections['02_Front_Glazing'].hide_render=True
   for o in bpy.data.collections['01_Shell'].objects:
    if o.name.startswith(('East external wall','West external wall')):o.hide_render=True
  for o in bpy.data.collections['40_Lighting'].objects:
   o.hide_render=o.type!='LIGHT' or o.data.type!='SUN'
  # Overhead views use neutral daylight to show layout cleanly.
  scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
 else:scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
 scene.view_settings.exposure=0 if name in ('06_Exterior','07_Cutaway','08_Topdown') else -1.0
 scene.camera=bpy.data.objects[views[name]]
 scene.render.filepath=str(ROOT/'previews'/(name+('_quick' if quick else '')+'.png'))
 print('RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
print('FINISHED',flush=True)
