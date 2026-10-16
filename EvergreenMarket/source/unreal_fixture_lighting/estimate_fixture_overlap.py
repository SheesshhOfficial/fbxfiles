"""Geometric attenuation-sphere overlap only; not GPU cost or photometry."""
import json, math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent
lights=json.loads((root/'fixture_point_layout_v1.json').read_text())['lights']
x,y=np.meshgrid(np.arange(-2300,2401,10),np.arange(-3100,2301,10))
rows=[]
for z in (0.,320.,398.,430.):
    for role,prefix in [('all',''),('ceiling','Fixture_'),('canopy','Canopy_'),('exterior_wall','ExteriorWall_')]:
        subset=[l for l in lights if l['key'].startswith(prefix)]
        count=np.zeros(x.shape,dtype=np.uint8)
        for l in subset:
            lx,ly,lz=l['location_cm'];r=l['attenuation_radius_cm']
            count+=((x-lx)**2+(y-ly)**2+(z-lz)**2 <=r*r)
        idx=np.unravel_index(np.argmax(count),count.shape)
        rows.append(dict(z_cm=z,role=role,max_sampled_influence_count=int(count[idx]),example_xy_cm=[int(x[idx]),int(y[idx])]))
result=dict(note='Counts attenuation spheres containing a sampled point, ignoring all occlusion and falloff. Not measured illuminance, screen cost, GPU shadow cost, or FPS. Grid maxima are sampled, not analytical guarantees.',sampling=dict(x_range_cm=[-2300,2400],y_range_cm=[-3100,2300],xy_step_cm=10),samples=rows,
canopy_floor_horizontal_reach_cm=math.sqrt(500**2-398.00001**2),canopy_at_own_height_horizontal_reach_cm=500)
(root/'fixture_overlap_estimate.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(rows,indent=2))
