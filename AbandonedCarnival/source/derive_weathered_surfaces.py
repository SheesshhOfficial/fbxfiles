from PIL import Image,ImageEnhance,ImageFilter,ImageDraw
import numpy as np,os,random,shutil
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));D=R+'/textures/derived';os.makedirs(D,exist_ok=True);N=2048;rng=np.random.default_rng(517);random.seed(517)
def load(asset,kind):return Image.open(R+'/textures/realistic/'+asset+'/'+asset+'_2K-JPG_'+kind+'.jpg').convert('RGB')
def noise(w,h):return np.array(Image.fromarray(rng.integers(0,255,(h,w),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC))/255
wood=load('Wood092','Color');wood=ImageEnhance.Color(wood).enhance(.18);wood=ImageEnhance.Brightness(wood).enhance(.61);wa=np.array(wood).astype(float)
dirt=.74+.26*noise(50,8);wa*=dirt[:,:,None];Image.fromarray(np.clip(wa,0,255).astype('uint8')).save(D+'/WeatheredWood_basecolor.jpg',quality=95)
for dest,src in [('normal','NormalGL'),('roughness','Roughness')]:load('Wood092',src).save(D+'/WeatheredWood_'+dest+'.jpg',quality=95)
# Vertically elongated chips and fine crackle expose real timber grain.
chip=noise(128,16)*.5+noise(512,64)*.3+noise(64,6)*.2;mask=np.clip((chip-.54)*7,0,1)
for name,col in [('PaintRed',(100,31,23)),('PaintTeal',(25,68,62)),('PaintCream',(151,137,101))]:
 lum=np.mean(wa,axis=2)/128;paint=np.array(col)[None,None,:]*(.72+.35*lum[:,:,None]);arr=paint*(1-mask[:,:,None])+wa*mask[:,:,None];Image.fromarray(np.clip(arr,0,255).astype('uint8')).save(D+'/'+name+'_basecolor.jpg',quality=95)
 shutil.copy(D+'/WeatheredWood_normal.jpg',D+'/'+name+'_normal.jpg');Image.fromarray(np.uint8(np.clip(170+mask*60,0,255))).save(D+'/'+name+'_roughness.jpg',quality=95)
# Corrosion combines scan microstructure with broad irregular oxidized regions.
metal=np.array(load('Metal063','Color')).astype(float);rustmask=np.clip((noise(24,24)*.6+noise(128,128)*.4-.38)*4,0,1);rust=np.zeros_like(metal);rust[:]=[99,49,24];rust*=.65+noise(96,96)[:,:,None]*.5;arr=metal*.34*(1-rustmask[:,:,None])+rust*rustmask[:,:,None];Image.fromarray(np.uint8(np.clip(arr,0,255))).save(D+'/CorrodedMetal_basecolor.jpg',quality=95)
load('Metal063','NormalGL').save(D+'/CorrodedMetal_normal.jpg',quality=95);Image.fromarray(np.uint8(130+rustmask*100)).save(D+'/CorrodedMetal_roughness.jpg',quality=95)
# Scanned aggregate with irregular hairline cracking layered into the albedo and height.
asphalt=ImageEnhance.Brightness(load('Asphalt033','Color')).enhance(.64);d=ImageDraw.Draw(asphalt);height=Image.new('L',(N,N),128);hd=ImageDraw.Draw(height)
for i in range(17):
 x=random.randrange(N);y=random.randrange(N);pts=[(x,y)]
 for j in range(random.randint(8,20)):
  x+=random.randint(-40,40);y+=random.randint(10,45);pts.append((x,y))
 d.line(pts,fill=(20,22,20),width=2);hd.line(pts,fill=75,width=3)
asphalt.save(D+'/CrackedAsphalt_basecolor.jpg',quality=95);load('Asphalt033','Roughness').save(D+'/CrackedAsphalt_roughness.jpg',quality=95);load('Asphalt033','NormalGL').save(D+'/CrackedAsphalt_normal.jpg',quality=95);height.save(D+'/CrackedAsphalt_height.png')
print(D)
