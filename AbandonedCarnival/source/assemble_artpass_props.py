import bpy,sys,os,re
from mathutils import Vector
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,R+'/source');from assemble_props import assemble
sets={}
for o in bpy.data.objects:
 if o.get('_assembly_source') or o.type!='MESH':continue
 match=re.match(r'(Art timber crate \d+) ',o.name)
 if match:sets.setdefault(match.group(1),[]).append(o)
centers=[(-15,-18),(-15.3,-11),(-5.2,-17),(-5.1,-8),(-14.7,-1)]
for o in bpy.data.objects:
 if o.get('_assembly_source') or o.type!='MESH':continue
 if o.name.startswith('Art cardboard') or o.name.startswith('Art bent carton flap'):
  i=min(range(len(centers)),key=lambda i:(o.location.x-centers[i][0])**2+(o.location.y-centers[i][1])**2);sets.setdefault('Art open carton %02d'%i,[]).append(o)
for name,parts in sets.items():
 points=[o.matrix_world@Vector(v) for o in parts for v in o.bound_box];origin=((min(p.x for p in points)+max(p.x for p in points))/2,(min(p.y for p in points)+max(p.y for p in points))/2,min(p.z for p in points))
 assemble(name+' Complete',parts,origin,'OpenWoodenCrate' if 'timber' in name else 'OpenCardboardCarton')
for o in bpy.data.objects:
 if o.get('_assembly_source'):o.hide_render=True;o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=R+'/blender/Moonfall_Carnival_ArtPass.blend');print('Added eligible prop assemblies',len(sets))
