import os,json,numpy as np,math
from scipy.spatial import Voronoi
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));rng=np.random.default_rng(811)
points=rng.uniform([-14,-22],[-6,3],(85,2));points=np.vstack([points,[[-100,-100],[100,-100],[100,100],[-100,100]]]);v=Voronoi(points);out=[]
def clip(poly,axis,bound,greater):
 ret=[]
 for i,a in enumerate(poly):
  b=poly[(i+1)%len(poly)];ai=a[axis]>=bound if greater else a[axis]<=bound;bi=b[axis]>=bound if greater else b[axis]<=bound
  if ai:ret.append(a)
  if ai!=bi:
   t=(bound-a[axis])/(b[axis]-a[axis]);ret.append(a+(b-a)*t)
 return ret
for i in range(85):
 reg=v.regions[v.point_region[i]]
 if -1 in reg:continue
 poly=[v.vertices[j] for j in reg]
 for axis,bound,greater in [(0,-14,True),(0,-6,False),(1,-22,True),(1,3,False)]:
  poly=clip(poly,axis,bound,greater) if poly else []
 if len(poly)<3:continue
 center=np.mean(poly,axis=0);dense=[]
 for j,a in enumerate(poly):
  b=poly[(j+1)%len(poly)];steps=max(1,int(np.linalg.norm(b-a)/.17))
  for q in range(steps):
   p=a+(b-a)*(q/steps);x,y=p
   p=p+np.array([.015*math.sin(x*19+y*11),.015*math.sin(x*7-y*21)])
   dense.append(center+(p-center)*.988)
 out.append({'polygon':[list(p) for p in dense],'height':float(rng.uniform(.052,.057)),'rubble':bool(center[0]<-12.8 and rng.random()<.45)})
json.dump(out,open(R+'/source/pavement_cells.json','w'))
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import random
random.seed(18);im=Image.new('RGB',(512,256),(178,156,112));d=ImageDraw.Draw(im)
for i in range(24000):
 x,y=random.randrange(512),random.randrange(256);c=random.randrange(100,210);d.point((x,y),fill=(c,int(c*.86),int(c*.63)))
font=ImageFont.truetype(R+'/assets/fonts/DejaVuSerif-Bold.ttf',38);sm=ImageFont.truetype(R+'/assets/fonts/DejaVuSerif-Bold.ttf',22)
d.rectangle((18,18,494,238),outline=(66,42,25),width=4);d.text((256,63),'MOONFALL',anchor='mm',font=font,fill=(75,35,22));d.text((256,119),'ADMIT ONE',anchor='mm',font=sm,fill=(47,44,33));d.text((256,179),'CARNIVAL  •  01489',anchor='mm',font=sm,fill=(74,40,25));im.save(R+'/textures/torn_ticket.png')
