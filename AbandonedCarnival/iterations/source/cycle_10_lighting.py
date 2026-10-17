"""Final lighting response to inspected carousel, arena and funhouse views."""
import bpy

def apply():
 from refine_funhouse_practical_lighting import add_funhouse_practical_lighting
 from cleanup_iteration_decorations import apply as cleanup
 fixtures=add_funhouse_practical_lighting(power_w=120,color=(1.0,.91,.80))
 # Cycle9 review found the wall-mounted service gear illegible in deep shade.
 # Add a real guarded work lamp on that wall, with a visible cable to the roof.
 from fast_geometry import make_api
 from refine_ride_realism import _Geometry
 mats={m.name:m for m in bpy.data.materials};cube,cyl,sphere,beam,torus=make_api(mats)
 work=[]
 work.append(cube('Cycle10 ticket worklight mounting plate',(10.065,-20.3,2.43),(.035,.24,.40),'rust',0))
 work.append(cyl('Cycle10 ticket worklight top',(10.22,-20.3,2.64),.15,.055,'rust'))
 work.append(cyl('Cycle10 ticket worklight lower ring',(10.22,-20.3,2.22),.14,.04,'rust'))
 for xx in (10.10,10.34):
  for yy in (-20.40,-20.20):work.append(beam('Cycle10 ticket worklight cage',(xx,yy,2.24),(xx,yy,2.62),.008,'rust'))
 work.append(beam('Cycle10 ticket worklight fixed supply cable',(10.075,-20.3,2.64),(10.075,-20.3,3.23),.008,'black'))
 g=_Geometry();g.ellipsoid((10.22,-20.3,2.43),(.09,.09,.15),'bulb',24,12);work.append(g.make_object('Cycle10 ticket worklight opal bulb'))
 for ob in work:ob['decorative_no_collision']=True
 ld=bpy.data.lights.new('Cycle10 ticket worklight practical','POINT');ld.energy=35;ld.color=(1.0,.80,.56);ld.shadow_soft_size=.15
 ob=bpy.data.objects.new(ld.name,ld);bpy.context.scene.collection.objects.link(ob);ob.location=(10.38,-20.3,2.43)
 changes=[]
 # Existing area lights represent the visible ride fixture banks. Reduce the
 # overly orange arena wash and bring out carved carousel forms without raising
 # the whole exposure or adding floating arbitrary point sources.
 for name,energy,color in [('Arena practical bounce',1000,(1.0,.68,.40)),('Carousel practical bounce',900,(1.0,.62,.32))]:
  o=bpy.data.objects.get(name)
  if o and o.type=='LIGHT':
   changes.append({'light':name,'before_energy':o.data.energy,'before_color':list(o.data.color),'after_energy':energy,'after_color':list(color)})
   o.data.energy=energy;o.data.color=color
 return {'funhouse_supported_fixtures':fixtures,'ticket_supported_worklight':[o.name for o in work],'existing_fixture_bank_balance':changes,'evaluated_decoration_cleanup':cleanup(),'exposure_unchanged':bpy.context.scene.view_settings.exposure,'reason':'Cycle4 horses were overly dark/orange, cycle3 rust floor overly orange, cycle5 face/sign underlit. Existing warm/cool night hierarchy retained.','unreal_lighting_verified':False}
