"""Cycle 8: bounded irregular perimeter and sheltered interior-base understory."""
def apply():
 import refine_perimeter_story as perimeter
 from refine_perimeter_story import add_perimeter_story
 # Overview review found that five low coppices still left the tall tree rhythm
 # too regular. A second irregular mid-height layer breaks those silhouette gaps.
 perimeter.SILHOUETTES=perimeter.SILHOUETTES+(
  ('west arrival intermediate crown',-33.4,-23.2,7.4,1),
  ('west winding intermediate crown',-34.0,-3.2,8.3,-1),
  ('west old fork crown',-33.1,12.4,6.9,1),
  ('northwest double crown',-24.0,34.2,8.7,-1),
  ('north sheltered crown',-13.2,33.8,7.3,1),
  ('north uneven crown',1.4,34.4,8.9,-1),
  ('north east shoulder crown',22.3,34.0,7.8,1),
  ('east high fork crown',34.4,24.0,8.3,-1),
  ('east service crown',33.7,1.8,7.6,1),
  ('east arrival leaning crown',34.0,-16.2,8.6,-1))
 from refine_interior_understory import add_interior_understory
 return {'outer_growth':[o.name for o in add_perimeter_story()],'sheltered_structure_growth':[o.name for o in add_interior_understory()],'route_policy':'Every cluster is bounded outside declared entrances, circulation and spawn strips.'}
