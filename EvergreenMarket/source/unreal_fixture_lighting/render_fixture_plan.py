from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).resolve().parent
j=json.loads((root/'fixture_point_layout_v1.json').read_text())
fig,ax=plt.subplots(figsize=(8,9),layout='constrained')
ax.add_patch(Rectangle((-22,-30),44,48,fill=False,ec='#999999',lw=1.2,label='Approximate building footprint'))
styles={'ceiling':('#1261a0','o','Ceiling / warehouse (25)'), 'canopy':('#e39500','s','Canopy (15)'), 'exterior_wall':('#93278f','D','Exterior wall (2)')}
for role,(color,marker,label) in styles.items():
 rows=[a for a in j['lights'] if a.get('fixture_role')==role]
 if not rows:
  roles={'ceiling':'Opal LED diffuser','canopy':'Canopy linear light','exterior_wall':'Exterior wall lamp'}
  rows=[a for a in j['lights'] if roles[role].replace(' ','_') in a['source_fixture_asset_id']]
 assert len(rows)=={'ceiling':25,'canopy':15,'exterior_wall':2}[role]
 ax.scatter([a['location_cm'][0]/100 for a in rows],[a['location_cm'][1]/100 for a in rows],s=40,c=color,marker=marker,label=label,zorder=3)
ax.axhline(-20,color='#999999',ls=':',lw=.8)
ax.text(-21,-26,'Warehouse row',fontsize=9,color='#555555')
ax.text(-21,20,'Front walkway / canopy',fontsize=9,color='#555555')
ax.set(xlim=(-25,27),ylim=(-33,25),xlabel='Unreal X (meters)',ylabel='Unreal Y (meters)',aspect='equal')
ax.set_title('Evergreen: 42 source-matched point lights\nPlacement diagram only, not an Unreal lighting render',fontsize=12)
ax.grid(alpha=.15);ax.legend(loc='lower left',fontsize=8,framealpha=.95)
fig.savefig(root/'fixture_light_positions.png',dpi=150)
