import json, os, re, subprocess, sys, numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
R='/root/road'; CAP=R+'/cap'; OUTD=R+'/seg'; os.makedirs(OUTD,exist_ok=True)
SR=44100
ARENAS=json.load(open(CAP+'/arenas.json'))
t=open('/root/xacct/data.js').read()
META={}
for a in re.findall(r"\{id: '(\w+)', n: (\d+), name: (\"[^\"]*\"|'[^']*'), at: (\d+), title: '(\w+)'",t):
    META[a[0]]=dict(n=int(a[1]),name=a[2][1:-1],at=int(a[3]),title=a[4])
MUS={'basement':'mus_battle','backyard':'mus_battle_backyard','parking':'mus_battle_parking','plaza':'mus_battle_lofi','beach':'mus_battle_summer','exchange':'mus_battle_exchange','casino':'mus_battle_casino','cold':'mus_battle_cold','penthouse':'mus_battle_penthouse','moon':'mus_battle_space','factory':'mus_battle_factory','dump':'mus_battle_dump','cemetery':'mus_battle_cemetery','trench':'mus_battle_trench','mine':'mus_battle_mine','clouds':'mus_battle_clouds','metaverse':'mus_battle_metaverse'}
VO=json.load(open(R+'/vo.json'))
FL=lambda s: ImageFont.truetype(R+'/lilita.ttf',s)
FI=lambda s: ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Bold.otf',s)
SEG=5.4; NF=162
def run(*a): subprocess.run(list(map(str,a)),check=True)
_cache={}
def load(path):
    if path in _cache: return _cache[path]
    tmp=R+'/tmp_dec.wav'; run('ffmpeg','-v','error','-y','-i',path,'-ar',SR,'-ac',2,tmp)
    a,_=sf.read(tmp,dtype='float32'); _cache[path]=a; return a
def stroke_text(d,xy,text,font,fill,stroke,sw,anchor='la'):
    d.text(xy,text,font=font,fill=fill,stroke_width=sw,stroke_fill=stroke,anchor=anchor)
def overlay_png(arena,path):
    m=META[arena]; im=Image.new('RGBA',(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im)
    # lower third
    y0=1290; panel=Image.new('RGBA',(1080,1920),(0,0,0,0)); pd=ImageDraw.Draw(panel)
    pd.rounded_rectangle((48,y0,1032,y0+250),radius=34,fill=(24,10,52,215),outline=(255,196,40,255),width=5)
    im=Image.alpha_composite(im,panel); d=ImageDraw.Draw(im)
    stroke_text(d,(112,y0+125),f"{m['n']:02d}",FL(160),(255,205,50,255),(70,20,120,255),8,'lm')
    d.line((300,y0+40,300,y0+210),fill=(255,205,50,255),width=5)
    nm=m['name']; fs=84
    while d.textlength(nm,font=FL(fs))>690: fs-=4
    stroke_text(d,(332,y0+98),nm,FL(fs),(255,255,255,255),(70,20,120,255),7,'lm')
    d.text((336,y0+178),f"{m['title']}  ·  {m['at']:,} CLOUT",font=FI(40),fill=(255,205,50,255),anchor='lm')
    im.save(path)
def road_png(idx,path):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im)
    x0,x1,y=96,984,236; d.line((x0,y,x1,y),fill=(255,255,255,90),width=8)
    xi=x0+(x1-x0)*idx/16; d.line((x0,y,xi,y),fill=(255,205,50,255),width=8)
    for i in range(17):
        x=x0+(x1-x0)*i/16; r=17 if i==idx else 8
        d.ellipse((x-r,y-r,x+r,y+r),fill=(255,205,50,255) if i<=idx else (255,255,255,140),outline=(70,20,120,255),width=3 if i==idx else 0)
    stroke_text(d,(540,170),"THE TROPHY ROAD",FL(46),(255,255,255,255),(70,20,120,255),5,'mm')
    im.save(path)
def mix_segment(arena,i):
    n=int(SEG*SR); out=np.zeros((n,2),dtype='float32')
    mus=load(f'{R}/aud/{MUS[arena]}.mp3'); st=int(7.0*SR); seg=mus[st:st+n].copy()
    if len(seg)<n: seg=np.pad(seg,((0,n-len(seg)),(0,0)))
    vo=load(f'{R}/vo_{arena}.wav') if False else None
    vw,vsr=sf.read(f'{R}/vo_{arena}.wav',dtype='float32'); 
    if vw.ndim==1: vw=np.stack([vw,vw],1)
    if vsr!=SR:
        run('ffmpeg','-v','error','-y','-i',f'{R}/vo_{arena}.wav','-ar',SR,'-ac',2,R+'/tmp_vo.wav'); vw,_=sf.read(R+'/tmp_vo.wav',dtype='float32')
    vpk=np.abs(vw).max(); vw=vw/vpk*0.8
    voch=np.zeros((n,2),dtype='float32'); s0=int(0.35*SR); voch[s0:s0+len(vw)]=vw[:n-s0]
    env=np.abs(voch).max(1); k=int(0.15*SR); env=np.convolve(env,np.ones(k)/k,'same'); duck=1-0.62*np.clip(env*6,0,1)
    seg*= (0.42*duck)[:,None]
    fi=int(0.12*SR); fo=int(0.35*SR); seg[:fi]*=np.linspace(0,1,fi)[:,None]; seg[-fo:]*=np.linspace(1,0,fo)[:,None]
    out+=seg+voch
    # game sfx
    sj=f'{CAP}/frames/{i:02d}_{arena}/sfx.json'
    if os.path.exists(sj):
        j=json.load(open(sj)); first=j['first']
        for e in j['sfx']:
            if e.get('music') or e.get('amb') or not e.get('file'): continue
            ts=(e['t']-first)/1000.0
            if ts<0 or ts>SEG-0.1: continue
            p=f"{R}/aud/sfx/{e['file']}"
            if not os.path.exists(p): continue
            a=load(p); vol=float(e.get('o',{}).get('vol',1) or 1)*0.5
            s=int(ts*SR); a=a[:n-s]; out[s:s+len(a)]+=a*vol
    return out
def build_segment(arena,i):
    d=f'{CAP}/frames/{i:02d}_{arena}'
    ov=f'{OUTD}/ov_{arena}.png'; rd=f'{OUTD}/road_{arena}.png'; overlay_png(arena,ov); road_png(i-1,rd)
    au=mix_segment(arena,i); wav=f'{OUTD}/a_{arena}.wav'; sf.write(wav,au,SR)
    out=f'{OUTD}/s_{arena}.mp4'
    fc=("[0:v]tpad=stop_mode=clone:stop_duration=2,scale=1080:1920,eq=contrast=1.07:saturation=1.12:gamma=0.98,vignette=PI/6,format=yuva420p[b];"
        "[b][1:v]overlay=x='-1080*pow(1-min(max(t-0.25,0)/0.4,1),3)':y=0:format=auto[c];"
        "[c][2:v]overlay=0:0:format=auto,fade=t=in:d=0.1,format=yuv420p[v]")
    run('ffmpeg','-v','error','-y','-framerate','30','-i',d+'/f_%04d.png','-loop','1','-i',ov,'-loop','1','-i',rd,'-i',wav,
        '-filter_complex',fc,'-map','[v]','-map','3:a','-frames:v',NF,'-r','30','-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',out)
    return out
def card_video():
    pass
if __name__=='__main__':
    which=sys.argv[1:] or ARENAS
    for a in which:
        i=ARENAS.index(a)+1
        if not os.path.exists(f'{CAP}/frames/{i:02d}_{a}/DONE'): print('skip',a); continue
        print(build_segment(a,i))
