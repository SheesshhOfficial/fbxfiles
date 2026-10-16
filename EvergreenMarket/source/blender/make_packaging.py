from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import random,math
OUT=Path(__file__).resolve().parents[1]/'textures'; OUT.mkdir(exist_ok=True)
FONT=str(Path(__file__).resolve().parent/'fonts'/'DejaVuSans.ttf')
BOLD=str(Path(__file__).resolve().parent/'fonts'/'DejaVuSans-Bold.ttf')
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def centered(d,y,t,n,fill,b=False):
 f=font(n,b); box=d.textbbox((0,0),t,font=f); d.text(((512-box[2])/2,y),t,font=f,fill=fill)
SKUS=[('FIELD','OATS','WHOLEGRAIN', '#e5bb78','#254d3f','oats'),('SUNRISE','CORN FLAKES','GOLDEN & CRISPY','#df704b','#fff0d1','oats'),('ORCHARD','APPLE JUICE','PRESSED DAILY','#46754e','#f6edd5','apple'),('GROVE','ORANGE JUICE','SUN-RIPENED','#e6a342','#f9f2d9','orange'),('RIVER','SPARKLING','MINERAL WATER','#64a7b7','#f4f3e7','water'),('CLOUD','OAT DRINK','ORIGINAL BLEND','#d1c9b4','#234d53','oats'),('PANTRY','TOMATOES','VINE RIPENED','#bc5546','#fff1d4','tomato'),('HARVEST','GARDEN PEAS','SWEET & TENDER','#78914b','#f5edcf','peas'),('EMBER','COFFEE','DARK ROAST','#4c332b','#d7ad69','coffee'),('MEADOW','HERBAL TEA','MINT & LEMON','#a4b59a','#263e38','leaf'),('GOLDEN','PASTA','DURUM WHEAT','#e8c058','#435044','pasta'),('PURE','CLEAN','SURFACE SPRAY','#82b7b5','#fff5dc','water'),('DAIRY','FRESH MILK','WHOLE MILK','#f1eee1','#356584','milk'),('DAIRY','YOGURT','NATURAL','#eee5d1','#686c9f','milk'),('CRISP','POTATO CHIPS','SEA SALT','#d9975b','#fff3db','chips'),('BLOOM','SOAP','CITRUS & SAGE','#c1c5a8','#40584b','leaf')]
for i,(brand,title,tag,bg,fg,icon) in enumerate(SKUS):
 im=Image.new('RGB',(512,768),bg);d=ImageDraw.Draw(im)
 d.rectangle((24,24,488,744),outline=fg,width=2)
 centered(d,50,'EVERGREEN / SELECT',20,fg,True)
 centered(d,112,brand,55,fg,True)
 centered(d,184,title,30,fg,True)
 d.line((62,242,450,242),fill=fg,width=2)
 # original simple engraved-style pack illustration
 if icon in ('apple','orange','tomato','peas','coffee','chips'):
  for j in range(3 if icon not in ('peas','coffee') else 9):
   x=256+math.sin(j*2.4)*85;y=390+math.cos(j*2.4)*55;r=58 if icon not in ('peas','coffee') else 30
   d.ellipse((x-r,y-r,x+r,y+r),fill=fg)
   d.arc((x-r+12,y-r+8,x+r-12,y+r-8),195,290,fill=bg,width=3)
   d.line((x,y-r,x+10,y-r-23),fill=fg,width=5)
 elif icon in ('oats','leaf','pasta'):
  for x in (174,256,338):
   d.line((x-28,489,x+25,310),fill=fg,width=5)
   for k in range(5):
    y=330+k*28; xx=x+20-k*8
    d.ellipse((xx-33,y-16,xx,y+2),fill=fg);d.ellipse((xx+3,y-31,xx+30,y-7),fill=fg)
 else:
  for j in range(4):
   d.arc((110,300+j*42,410,435+j*42),0,175,fill=fg,width=7)
 centered(d,562,tag,23,fg,True)
 centered(d,609,'GOOD FOOD. EVERY DAY.',15,fg)
 # printed nutritional/barcode details
 d.rounded_rectangle((52,657,140,711),radius=6,outline=fg,width=2);d.text((66,673),'500 g' if i%2==0 else '1 L',font=font(20,True),fill=fg)
 random.seed(i)
 x=326
 while x<452:
  w=random.choice([2,3,4]);d.rectangle((x,652,x+w,701),fill=fg);x+=w+random.choice([2,3,4])
 d.text((326,707),'4 918240 02716',font=font(10),fill=fg)
 im.save(OUT/f'pack_{i:02d}.png')
print('Created',len(SKUS),'original packaging textures.')
