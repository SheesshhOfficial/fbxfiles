"""Save-free collision RECIPES for the later ride/maintenance refinement.
No import-time scene operations, file I/O, exports or checkpoint modifications.
Recipes are plain Python dictionaries; no Blender helper objects are created.
This module intentionally does not modify the V1 exporter or its outputs.
"""
import json, math
import bpy
from mathutils import Matrix, Vector

VERSION='refined_prop_collision_recipes_v1'
BUMPER_HEADINGS=(.3,-.3,2.1,2.8,-1.2,.9,-.4)
STRUCTURAL_BUDGETS={'wooden_pallet':9,'timber_shipping_crate':8}

def _bounds(vertices):
 return {'min':[min(v[i] for v in vertices) for i in range(3)],'max':[max(v[i] for v in vertices) for i in range(3)]}

def _convex(label,points):
 """Double-precision hull; exact convex recipe, no Blender mesh creation."""
 import numpy as np
 from scipy.spatial import ConvexHull
 xyz=np.unique(np.asarray(points,dtype=np.float64),axis=0)
 if xyz.shape[0]<4 or not np.isfinite(xyz).all():raise RuntimeError('Invalid proxy points: '+label)
 hull=ConvexHull(xyz);indices=[int(i) for i in hull.vertices];remap={i:j for j,i in enumerate(indices)};faces=[]
 for tri,plane in zip(hull.simplices,hull.equations):
  tri=[int(i) for i in tri];a,b,c=[xyz[i] for i in tri]
  if float(np.dot(np.cross(b-a,c-a),plane[:3]))<0:tri.reverse()
  faces.append([remap[i] for i in tri])
 if len(indices)>255:raise RuntimeError('Proxy exceeds 255 vertices: '+label)
 vertices=[list(map(float,xyz[i])) for i in indices]
 return {'part':label,'vertices_local_m':vertices,'faces':faces,'bounds_local_m':_bounds(vertices),'volume_m3':float(hull.volume),'vertex_count':len(vertices)}

def _box_points(center,dimensions,rotation=None):
 rotation=rotation or Matrix.Identity(3);c=Vector(center)
 return [list(c+rotation@Vector((sx*dimensions[0]/2,sy*dimensions[1]/2,sz*dimensions[2]/2))) for sx in (-1,1) for sy in (-1,1) for sz in (-1,1)]

def _bumper_parts(index):
 """Eight occupied-solid proxies, authored in the same unheaded frame as the ride builder.
 Cockpit/steering clearance is intentional. Tiny trim, steering wheel, rivets and
 electrical pickup are omitted from gameplay collision, including the tall pole.
 """
 heading=Matrix.Rotation(BUMPER_HEADINGS[index],3,'Z');parts=[]
 def add(label,points):parts.append(_convex(label,[list(heading@Vector(v)) for v in points]))
 # Elliptical low bumper/undertray mass, safely below the cockpit floor.
 add('low bumper and undertray',[(1.342*math.cos(i*math.tau/24),.858*math.sin(i*math.tau/24),z) for z in (.105,.390) for i in range(24)])
 # Front bonnet stays forward of the cockpit opening (front lip x=0.355 m).
 outline=[(.375,-.415),(.92,-.40),(1.13,-.21),(1.17,0),(1.13,.21),(.92,.40),(.375,.415)]
 add('solid front hood',[(x,y,z) for z in (.390,.707) for x,y in outline])
 # Tapered side strips, never a hull spanning the cockpit from left to right.
 for side in (-1,1):
  points=[]
  for z,outer in [(.390,[.55,.675,.695,.62]),(.710,[.515,.565,.57,.53])]:
   for x,y in zip([-.78,-.40,0.,.34],outer):points.extend([(x,side*y,z),(x,side*.485,z)])
  add('left side body' if side>0 else 'right side body',points)
 add('rear body below backrest',_box_points((-.995,0,.535),(.105,.66,.285)))
 add('foot tray',_box_points((-.30,0,.462),(.96,.74,.04)))
 add('seat cushion',_box_points((-.47,0,.612),(.61,.79,.16)))
 add('seat back and upholstery',_box_points((-.749,0,.902),(.285,.86,.56),Matrix.Rotation(-.13,3,'Y')))
 # Test representative free cockpit points above the cushion/tray. These are
 # geometry guard points, not a claim that an actual UE capsule fits inside.
 probes=[(-.35,0,.78),(-.15,0,.78),(.15,0,.78),(-.15,.25,.83),(-.15,-.25,.83),(-.15,0,1.15)]
 for p in probes:
  headed=heading@Vector(p)
  for part in parts:
   if _inside(headed,part):raise RuntimeError('Cockpit guard point blocked by '+part['part'])
 return parts,{'unheaded_free_cockpit_probe_points_m':probes,'cockpit_probe_points_clear':True,'omitted_collision':'Decorative rivets, trim, lamps, steering wheel/spokes, seat stitching, electrical pickup pole/springs.'}

def _inside(point,part,tolerance=1e-8):
 vertices=[Vector(v) for v in part['vertices_local_m']]
 return all((Vector(point)-vertices[f[0]]).dot((vertices[f[1]]-vertices[f[0]]).cross(vertices[f[2]]-vertices[f[0]]).normalized())<=tolerance for f in part['faces'])

def _structural_parts(obj):
 records=json.loads(obj.get('construction_components','[]'))
 if not records:raise RuntimeError('Missing exact construction_components face ranges: '+obj.name)
 if obj.modifiers:raise RuntimeError('Face-range contract requires baked mesh without modifiers: '+obj.name)
 covered=set();parts=[];omitted=[];structural=[]
 for record in records:
  first=int(record['first_face']);count=int(record['face_count']);indices=set(range(first,first+count))
  if first<0 or count<=0 or first+count>len(obj.data.polygons) or covered.intersection(indices):raise RuntimeError('Invalid or overlapping construction face ranges: '+obj.name)
  covered.update(indices)
  role=record.get('collision_role')
  if role=='decorative':omitted.append(record['part']);continue
  if role!='structural':raise RuntimeError('Unknown construction collision_role: '+str(role))
  vertex_ids={i for face in indices for i in obj.data.polygons[face].vertices}
  structural.append({'label':record['part'],'points':[list(obj.data.vertices[i].co) for i in vertex_ids],'face_range':[first,count]})
 if covered!=set(range(len(obj.data.polygons))):raise RuntimeError('Incomplete construction face-range coverage: '+obj.name)
 if obj.get('asset_family')=='wooden_pallet':
  if len(structural)!=9:raise RuntimeError('Expected 9 pallet structural boards: '+obj.name)
  for item in structural:
   part=_convex(item['label'],item['points']);part['source_face_ranges']=[item['face_range']];parts.append(part)
 else:
  if len(structural)!=40:raise RuntimeError('Expected 40 crate structural pieces before slab merging: '+obj.name)
  groups={};skid=0
  for item in structural:
   label=item['label'];tokens=label.split()
   if label.startswith('front back skin'):group='front/back shell '+tokens[-2]
   elif label.startswith('front edge batten'):group='front/back shell '+tokens[-1]
   elif label.startswith(('end skin','internal corner batten')):group='end shell '+tokens[-2]
   elif label.startswith('lid floor board'):group='lid' if tokens[-2]=='1' else 'floor'
   elif label=='bottom load skid':group='load skid '+str(skid);skid+=1
   else:raise RuntimeError('Unrecognized structural crate part: '+label)
   groups.setdefault(group,[]).append(item)
  for label,items in groups.items():
   part=_convex(label,[p for item in items for p in item['points']]);part['source_face_ranges']=[item['face_range'] for item in items];part['merged_parts']=[item['label'] for item in items];parts.append(part)
 expected=STRUCTURAL_BUDGETS[obj.get('asset_family')]
 if len(parts)!=expected:raise RuntimeError('Unexpected structural budget '+obj.name+': '+str(len(parts)))
 bounds=_bounds([list(v.co) for v in obj.data.vertices]);center=[(bounds['min'][i]+bounds['max'][i])/2 for i in range(3)]
 if obj.get('asset_family')=='wooden_pallet':
  z=bounds['min'][2]+(bounds['max'][2]-bounds['min'][2]-.028)*.5
  probes=[(center[0]+side*.25,center[1]+y,z) for side in (-1,1) for y in (-.35,0,.35)]
 else:probes=[tuple(center)]
 for point in probes:
  if any(_inside(point,part) for part in parts):raise RuntimeError('Usable opening guard point blocked: '+obj.name+' '+str(point))
 return parts,{'opening_guard_points_local_m':probes,'opening_guard_points_clear':True,'omitted_decorative_parts':omitted,'structural_face_ranges_verified':True,'whole_prop_hull':False,'structural_pieces_before_merge':len(structural),'crate_policy':'Four independent side slabs, lid, floor and two skids; sub-centimetre plank seams filled, central cavity never enclosed by one solid hull.' if obj.get('asset_family')=='timber_shipping_crate' else 'Separate deck boards and stringers; fork lanes unbridged.'}

def prepare_collision_recipes(objects=None):
 """Read current in-memory refined objects; return 19 recipes (7 cars/8 pallets/4 crates).
 Call after BOTH refinements and after any normal cleanup, BEFORE topology-changing
 modifiers or mesh joins invalidate construction_components. Does not mark source
 regeneration flags complete: only the later verified export may do that.
 """
 source=list(objects) if objects is not None else list(bpy.context.scene.objects)
 eligible=[o for o in source if o.type=='MESH' and o.get('PropActorTag') and not any(o.get(k) for k in ('_assembly_source','visual_replaced','render_only')) and not(o.hide_render or o.hide_viewport or o.hide_get())]
 cars=sorted([o for o in eligible if o.get('asset_family')=='BumperCar'],key=lambda o:o.name)
 if len(cars)!=7:raise RuntimeError('Expected 7 refined bumper cars, got '+str(len(cars)))
 timber=[o for o in eligible if o.name.startswith(('BY_Pallet_','BY_Crate_'))]
 if len(timber)!=12:raise RuntimeError('Expected 8 maintenance pallets and 4 crates')
 result=[]
 for index,obj in enumerate(cars):
  if obj.get('ride_realism_revision')!='cycle03_rounded_shell_seat_fittings':raise RuntimeError('Unsupported bumper revision: '+obj.name)
  parts,qa=_bumper_parts(index);result.append(_recipe(obj,parts,qa))
 for obj in sorted(timber,key=lambda o:o.name):
  if obj.get('construction_refinement')!='maintenance_construction_v1':raise RuntimeError('Unsupported construction revision: '+obj.name)
  if obj.get('asset_family') not in STRUCTURAL_BUDGETS:raise RuntimeError('Unexpected timber family: '+obj.name)
  parts,qa=_structural_parts(obj);result.append(_recipe(obj,parts,qa))
 return {'recipe_version':VERSION,'coordinate_space':'object-local Blender metres; bumper heading already baked once','actors':result,'actor_count':len(result),'placed_hull_budget':sum(len(r['hulls']) for r in result),'source_mutated':False,'source_saved':False,'exported':False,'unreal_runtime_verified':False}

def _recipe(obj,parts,qa):
 source_bounds=_bounds([list(v.co) for v in obj.data.vertices]);proxy_bounds=_bounds([v for part in parts for v in part['vertices_local_m']])
 violation=max([0.]+[source_bounds['min'][i]-proxy_bounds['min'][i] for i in range(3)]+[proxy_bounds['max'][i]-source_bounds['max'][i] for i in range(3)])
 if violation>0.005:raise RuntimeError('Proxy extends beyond render envelope by >5mm: '+obj.name+' '+str(violation))
 qa.update({'source_local_bounds_m':source_bounds,'proxy_local_bounds_m':proxy_bounds,'max_aabb_extension_m':violation,'aabb_tolerance_m':.005})
 return {'source_object':obj.name,'asset_family':obj.get('asset_family'),'actor_tags':['PropActor'],'source_world_matrix_blender_m':[list(row) for row in obj.matrix_world],'hulls':parts,'hull_count':len(parts),'qa':qa}
