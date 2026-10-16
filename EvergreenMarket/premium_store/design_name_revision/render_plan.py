from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent
fig,ax=plt.subplots(figsize=(13,11));fig.patch.set_facecolor('#f6f2e9');ax.set_facecolor('#f6f2e9')
zones=[(0,0,12,16,'Coffee / patisserie\nseating','#d9c1a0'),(0,16,12,16,'Produce / fresh','#b6c79e'),(0,32,12,8,'Bakery','#d9c1a0'),(52,0,12,12,'Florist /\nseasonal','#c3c99d'),(52,12,12,12,'Beverages /\nwine','#cab6a2'),(52,24,12,16,'Deli / cheese\nmeat / fish','#c4d5cd'),(12,0,28,10,'Checkout islands + bypass\ncustomer service','#d3c8b5'),(40,0,12,10,'Entry / baskets\ncart parking','#e7d8b8'),(16,14,32,10,'PANTRY / SNACKS / CEREAL','#c4b29a'),(16,28,32,8,'HOUSEHOLD / PERSONAL CARE','#c4b29a'),(16,36,32,4,'DAIRY / CHILLED / FROZEN — gaps for through-routes','#b9cfce'),(0,47,40,9,'WAREHOUSE / RECEIVING / COLD STORAGE','#bbb8b1'),(40,47,24,9,'STAFF / OFFICE / TOILETS\nUTILITIES','#c7c3ba')]
for x,y,w,h,label,c in zones:
 ax.add_patch(Rectangle((x,y),w,h,facecolor=c,edgecolor='#564d40',lw=1.2));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=9 if h>4 else 8,color='#292a27')
for x,y,w,h,l in [(12,10,40,4,'FRONT CROSS-AISLE'),(16,24,32,4,'CENTRAL CROSS-AISLE'),(0,40,64,4,'REAR SHOPPING LOOP • TWO OR MORE STAFF CONNECTIONS'),(0,44,64,3,'CONNECTED STAFF / STOCK CIRCULATION')]:
 ax.add_patch(Rectangle((x,y),w,h,facecolor='#eee7d8',edgecolor='none'));ax.text(x+w/2,y+h/2,l,ha='center',va='center',fontsize=8,color='#726245')
for x in (12,48):
 ax.add_patch(Rectangle((x,14),4,26,facecolor='#eee7d8'));ax.text(x+2,25,'4 m MAIN LOOP',rotation=90,ha='center',va='center',fontsize=8,color='#726245')
ax.add_patch(Rectangle((0,0),64,56,fill=False,edgecolor='#282b27',lw=3))
ax.annotate('MAIN ENTRANCE',xy=(46,0),xytext=(46,-4),ha='center',arrowprops=dict(arrowstyle='->',lw=1.7,color='#585548'),fontsize=10)
ax.text(5,-4,'ROAD / FOREST BACKDROP\nExterior scenery only',fontsize=9,color='#53604b')
ax.set_xlim(-2,66);ax.set_ylim(59,-7);ax.set_aspect('equal');ax.set_xticks(range(0,65,8));ax.set_yticks(range(0,57,8));ax.set_xlabel('Metres from front-left corner');ax.set_ylabel('Metres toward rear');ax.grid(alpha=.12)
fig.suptitle('You want it You get it • PREMIUM LAYOUT',fontsize=20,fontweight='bold',x=.51,y=.97)
ax.set_title('64 × 56 m • 3,584 m² • 10 players • single floor • approved layout, updated name',fontsize=11,pad=15)
fig.text(.10,.035,'Department blocks are space reservations, not final walls. Shelf rows, doors and exact collision clearances follow in greybox.\nAll eligible placements become individual tagged actors; shared meshes are allowed. No existing project changes.',fontsize=10,color='#4a4b42')
plt.subplots_adjust(top=.89,bottom=.12,left=.09,right=.96)
fig.savefig(p/'PREMIUM_FLOOR_PLAN_OPTION_A.png',dpi=160);fig.savefig(p/'PREMIUM_FLOOR_PLAN_OPTION_A.svg')
