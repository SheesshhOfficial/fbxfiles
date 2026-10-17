import bpy,json,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
j={o.name:[s.material.name if s.material else None for s in o.material_slots] for o in bpy.context.scene.objects if o.type in {'MESH','FONT','CURVE'}}
json.dump(j,open(R+'/qa/precleanup_material_slots.json','w'),indent=2)
