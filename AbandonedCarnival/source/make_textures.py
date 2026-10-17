from PIL import Image, ImageDraw, ImageFilter
import numpy as np, random, os
random.seed(84); rng=np.random.default_rng(84)
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/textures'; os.makedirs(root,exist_ok=True)
N=1024
for name,base in [('wood',(73,62,44)),('rust',(91,48,28)),('cream',(165,151,112)),('red',(104,30,25)),('teal',(31,83,78)),('concrete',(65,67,64)),('ground',(42,43,35))]:
 a=rng.normal(0,7,(N,N,1)); coarse=np.array(Image.fromarray(rng.integers(0,255,(32,32),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC))/255
 a=a+(coarse[:,:,None]-.5)*45
 if name=='wood':
  grain=np.array(Image.fromarray(rng.integers(0,255,(8,512),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC))/255
  a+=(grain[:,:,None]-.5)*55
 rgb=np.clip(np.array(base)[None,None,:]+a,0,255).astype('uint8'); im=Image.fromarray(rgb); d=ImageDraw.Draw(im)
 if name in ['cream','red','teal','rust']:
  for i in range(1800):
   x,y=random.randrange(N),random.randrange(N); r=random.randrange(1,12); d.ellipse((x,y,x+r,y+r*random.uniform(.2,1.5)),fill=random.choice([(66,39,22),(102,58,30),(43,40,32)]))
 if name=='wood':
  for x in range(0,N,128): d.line((x,0,x,N),fill=(22,21,17),width=4)
  for i in range(240):
   x,y=random.randrange(N),random.randrange(N); d.line((x,y,x+random.randrange(-2,3),y+random.randrange(10,90)),fill=(33,29,20),width=1)
 if name in ['ground','concrete']:
  for i in range(35):
   x,y=random.randrange(N),random.randrange(N); p=[(x,y)]
   for j in range(8): x+=random.randint(-25,25); y+=random.randint(7,30); p.append((x,y))
   d.line(p,fill=(18,21,18),width=2)
 im.save(root+'/'+name+'_basecolor.png')
 rough=np.clip(190+(coarse-.5)*60,0,255).astype('uint8'); Image.fromarray(rough).save(root+'/'+name+'_roughness.png')
 height=np.array(im.convert('L'),dtype=float)/255; dy,dx=np.gradient(height); normals=np.stack([-dx*2,-dy*2,np.ones_like(dx)],axis=2); normals/=np.linalg.norm(normals,axis=2)[:,:,None]; Image.fromarray(((normals*.5+.5)*255).astype('uint8')).save(root+'/'+name+'_normal.png')
print(root)
