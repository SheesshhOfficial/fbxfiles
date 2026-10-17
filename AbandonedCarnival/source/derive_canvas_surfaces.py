"""Original portable woven-canvas surface images, no external image source."""
from PIL import Image,ImageFilter
import numpy as np,os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));D=R+'/textures/derived';n=1024;rng=np.random.default_rng(419)
coarse=np.array(Image.fromarray(rng.integers(0,255,(20,20),dtype=np.uint8)).resize((n,n),Image.Resampling.BICUBIC))/255
fine=rng.random((n,n));y,x=np.mgrid[:n,:n];weave=(np.sin(x*np.pi)*0+np.cos(x*np.pi/2)*np.cos(y*np.pi/2))*.06
stain=.62+.3*coarse+.08*fine+weave
for name,col in [('CanvasCream',(164,150,116)),('CanvasRed',(100,35,29)),('CanvasTeal',(35,72,66))]:
 im=np.clip(np.array(col)[None,None,:]*stain[:,:,None],0,255).astype('uint8');Image.fromarray(im).save(D+'/'+name+'_basecolor.jpg',quality=95)
h=(np.cos(x*np.pi/2)+np.cos(y*np.pi/2))*.08;dy,dx=np.gradient(h);norm=np.dstack([-dx,-dy,np.ones_like(h)]);norm/=np.linalg.norm(norm,axis=2)[:,:,None];Image.fromarray(np.uint8((norm*.5+.5)*255)).save(D+'/Canvas_normal.png');Image.fromarray(np.uint8(np.clip(220+coarse*25,0,255))).save(D+'/Canvas_roughness.jpg',quality=95)
