import sys,re,json,os,subprocess
from PIL import Image,ImageDraw,ImageFont
R='/root/road'; SEGD=R+'/seg'
ARENAS=json.load(open(R+'/cap/arenas.json'))
src=open(R+'/tts.py').read()
LINES=dict(re.findall(r'\("(\w+)","((?:[^"\\]|\\.)*)"\)',src))
VO=json.load(open(R+'/vo.json'))
F=0.25
FI=lambda s: ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Bold.otf',s)
def wrap(d,t,font,w):
    out=[];cur=''
    for wd in t.split():
        x=(cur+' '+wd).strip()
        if d.textlength(x,font=font)>w and cur: out.append(cur);cur=wd
        else: cur=x
    out.append(cur); return out
def cap_png(key,path):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im); f=FI(44)
    ls=wrap(d,LINES[key].replace('\\"','"'),f,900); y=1600
    for l in ls:
        d.text((540,y),l,font=f,fill=(255,255,255,255),anchor='mm',stroke_width=7,stroke_fill=(20,8,40,255)); y+=60
    im.save(path)
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]).decode())
only=sys.argv[1:]
keys=['intro']+[a for a in ARENAS if (not only or a in only)]+['outro']
keys=[k for k in keys if os.path.exists(f'{SEGD}/s_{k}.mp4')]
def sh(cmd): subprocess.run(cmd,check=True)
E='-c:v libx264 -crf 12 -preset fast -pix_fmt yuv420p -c:a aac -b:a 256k'.split()
# 1 captions
files=[]
for k in keys:
    o=f'{SEGD}/c_{k}.mp4'; files.append(o)
    if k in ('intro','outro'): sh(['ffmpeg','-v','error','-y','-i',f'{SEGD}/s_{k}.mp4','-c','copy',o]); continue
    p=f'{SEGD}/cap_{k}.png'; cap_png(k,p); a=0.35; b=0.35+VO[k]+0.2
    sh(['ffmpeg','-v','error','-y','-i',f'{SEGD}/s_{k}.mp4','-loop','1','-i',p,'-filter_complex',f"[0:v][1:v]overlay=0:0:enable='between(t,{a},{b})':format=auto:shortest=1[v]",'-map','[v]','-map','0:a']+E+[o])
def join(fl,out,last=False):
    inp=[];fc=[];ds=[dur(f) for f in fl]
    for f in fl: inp+=['-i',f]
    L=ds[0];cur='0:v';ac='0:a'
    for i in range(1,len(fl)):
        fc.append(f'[{cur}][{i}:v]xfade=transition=fade:duration={F}:offset={L-F:.3f}[x{i}]'); cur=f'x{i}'
        fc.append(f'[{ac}][{i}:a]acrossfade=d={F}[a{i}]'); ac=f'a{i}'; L=L+ds[i]-F
    if last:
        fc.append(f'[{cur}]noise=alls=5:allf=t,format=yuv420p[vo]'); fc.append(f'[{ac}]loudnorm=I=-14:TP=-1.5:LRA=11[ao]'); cur,ac='vo','ao'
        enc=['-c:v','libx264','-crf','22','-maxrate','5M','-bufsize','10M','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart']
    else: enc=E
    sh(['ffmpeg','-v','error','-y']+inp+['-filter_complex',';'.join(fc),'-map',f'[{cur}]' if not cur.endswith(':v') else cur,'-map',f'[{ac}]' if not ac.endswith(':a') else ac,'-r','30']+enc+[out]); return L
parts=[]
for g in range(0,len(files),6):
    o=f'{SEGD}/part_{g//6}.mp4'; parts.append(o)
    if len(files[g:g+6])==1: sh(['ffmpeg','-v','error','-y','-i',files[g],'-c','copy',o])
    else: join(files[g:g+6],o)
out=R+'/trophy_road_final.mp4'
L=join(parts,out,True)
print(out,round(L,1),'s',os.path.getsize(out)//1000000,'MB')
