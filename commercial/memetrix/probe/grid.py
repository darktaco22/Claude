import sys
from PIL import Image,ImageDraw
f,eye,half,step=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])
im=Image.open(f).convert('RGB');d=ImageDraw.Draw(im);W=im.size[0]
n=int(half/step)
for k in range(-n,n+1):
  p=int(W/2+k*step/(2*half)*W)
  c=(255,0,0) if k==0 else (255,255,0)
  d.line([(p,0),(p,W)],fill=c);d.line([(0,p),(W,p)],fill=c)
  d.text((p+2,2),'%.2f'%(k*step),fill='white');d.text((2,p+2),'%.2f'%(eye-k*step),fill='white')
im.save(f.replace('.png','_grid.png'))
