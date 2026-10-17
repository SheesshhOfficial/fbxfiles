import bpy,sys,os,json,hashlib
R=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))));sys.path[:0]=[R+'/source',R+'/iterations/source']
from prepare_refined_prop_collision import prepare_collision_recipes
r=prepare_collision_recipes();r['checkpoint']=bpy.data.filepath;r['source_sha256']=hashlib.sha256(open(bpy.data.filepath,'rb').read()).hexdigest();json.dump(r,open(R+'/iterations/qa/refined_collision_recipe_validation.json','w'),indent=2);print('REFINED_COLLISION',r['actor_count'],r['placed_hull_budget'])
