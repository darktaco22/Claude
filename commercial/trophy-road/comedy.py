import sys, os, json, subprocess, numpy as np, soundfile as sf
sys.argv=sys.argv[:1]+sys.argv[1:]
only=sys.argv[1:]
from assemble import load, run, SR, MUS, FL, FI, stroke_text, CAP, R, ARENAS
from PIL import Image, ImageDraw
SEGD=R+'/seg'; V=json.load(open(R+'/vo2.json'))
SEG=5.4
def rd(p):
    a,sr=sf.read(p,dtype='float32')
    if a.ndim==1: a=np.stack([a,a],1)
    if sr!=SR:
        subprocess.run(['ffmpeg','-v','error','-y','-i',p,'-ar',str(SR),'-ac','2',R+'/tmp_v.wav'],check=True); a,_=sf.read(R+'/tmp_v.wav',dtype='float32')
    return a
def voice(p,gain=1.0):
    a=rd(p); act=a[np.abs(a).max(1)>0.02]; rms=np.sqrt((act**2).mean())+1e-6
    a=a*(0.16/rms)*gain; return np.tanh(a*1.1)/1.1*1.0
def place(buf,a,at):
    s=int(at*SR); a=a[:max(0,len(buf)-s)]; buf[s:s+len(a)]+=a
def duck_env(vo):
    env=np.abs(vo).max(1); k=int(0.12*SR); env=np.convolve(env,np.ones(k)/k,'same'); return 1-0.72*np.clip(env*7,0,1)
def wrap(d,t,font,w):
    out=[];cur=''
    for wd in t.split():
        x=(cur+' '+wd).strip()
        if d.textlength(x,font=font)>w and cur: out.append(cur);cur=wd
        else: cur=x
    out.append(cur); return out
def cap_png(text,path):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im); f=FI(42); y=1610
    for l in wrap(d,text,f,920):
        d.text((540,y),l,font=f,fill=(255,255,255,255),anchor='mm',stroke_width=7,stroke_fill=(20,8,40,255)); y+=58
    im.save(path)
def sticker_png(text,path):
    f=FL(56); t=Image.new('RGBA',(10,10)); d=ImageDraw.Draw(t); w=int(d.textlength(text,font=f))+70
    pill=Image.new('RGBA',(w,110),(0,0,0,0)); pd=ImageDraw.Draw(pill)
    pd.rounded_rectangle((0,0,w-1,109),radius=30,fill=(255,205,50,255),outline=(70,20,120,255),width=7)
    stroke_text(pd,(w//2,55),text,f,(60,16,100,255),(255,255,255,0),0,'mm')
    pill=pill.rotate(-5,expand=True,resample=Image.BICUBIC)
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); im.paste(pill,(max(20,1080-pill.width-40),330),pill); im.save(path)
def punch_png(text,path):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im)
    f=FL(118); ls=wrap(d,text.upper(),f,900); h=len(ls)*128+110; y0=760-h//2
    d.rounded_rectangle((40,y0-30,1040,y0+h),radius=40,fill=(18,6,40,205),outline=(255,205,50,255),width=6)
    y=y0+70
    for l in ls:
        stroke_text(d,(540,y),l,f,(255,255,255,255),(110,30,170,255),10,'mm'); y+=128
    d.text((540,y0+h-34),'THE ANALYST, UNIMPRESSED',font=FI(34),fill=(255,205,50,255),anchor='mm')
    im.save(path)
def enc(): return ['-c:v','libx264','-crf','12','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k']
def build(k):
    i=ARENAS.index(k)+1; v=V[k]; c=v['c']; a=v['a']
    a_start=max(SEG+0.3,0.3+c+0.25); F=a_start-SEG+a+0.6; T=SEG+F
    n=int(T*SR); out=np.zeros((n,2),dtype='float32')
    vc=np.zeros((n,2),dtype='float32'); place(vc,voice(f'{R}/v2_{k}_c.wav'),0.3)
    va=np.zeros((n,2),dtype='float32'); place(va,voice(f'{R}/v2_{k}_a.wav',1.05),a_start)
    mus=load(f'{R}/aud/{MUS[k]}.mp3'); st=int(7.0*SR); m=mus[st:st+n].copy()
    if len(m)<n: m=np.pad(m,((0,n-len(m)),(0,0)))
    m*=0.15*duck_env(vc+va)[:,None]
    fo=int(0.4*SR); m[-fo:]*=np.linspace(1,0,fo)[:,None]; fi=int(0.15*SR); m[:fi]*=np.linspace(0,1,fi)[:,None]
    out+=m
    sj=f'{CAP}/frames/{i:02d}_{k}/sfx.json'
    if os.path.exists(sj):
        j=json.load(open(sj)); first=j['first']
        if first:
            for e in j['sfx']:
                if e.get('music') or e.get('amb') or not e.get('file'): continue
                ts=(e['t']-first)/1000.0
                if ts<0 or ts>SEG-0.1: continue
                p=f"{R}/aud/sfx/{e['file']}"
                if os.path.exists(p):
                    s=load(p)[:int(1.5*SR)]; vol=float(e.get('o',{}).get('vol',1) or 1)*0.2; place(out,s*vol*duck_env(vc)[int(ts*SR):int(ts*SR)+len(s)][:len(s),None] if False else s*vol,ts)
    # comedic sting at the punchline
    sp=f'{R}/aud/sfx/surprise_hit.mp3'
    if os.path.exists(sp): place(out,load(sp)[:int(1.2*SR)]*0.55,a_start-0.12)
    out+=vc+va
    wav=f'{SEGD}/a2_{k}.wav'; sf.write(wav,out,SR)
    cap_png(v['caster'],f'{SEGD}/cap2_{k}.png'); punch_png(v['analyst'],f'{SEGD}/punch_{k}.png')
    last=f'{SEGD}/last_{k}.png'; run('ffmpeg','-v','error','-y','-sseof','-0.1','-i',f'{SEGD}/s_{k}.mp4','-frames:v','1',last)
    has_st=bool(v['sticker']);
    if has_st: sticker_png(v['sticker'],f'{SEGD}/stk_{k}.png')
    inp=['-i',f'{SEGD}/s_{k}.mp4','-loop','1','-t',str(SEG),'-i',f'{SEGD}/cap2_{k}.png','-loop','1','-t',str(F),'-framerate','30','-i',last,
         '-loop','1','-t',str(F),'-framerate','30','-i',f'{SEGD}/punch_{k}.png','-i',wav]
    if has_st: inp+=['-loop','1','-t',str(SEG),'-i',f'{SEGD}/stk_{k}.png']
    ta=a_start-SEG
    fc=["[0:v]setsar=1,fps=30[m0]"]
    cur='m0'
    if has_st:
        fc.append(f"[{cur}][5:v]overlay=x=0:y='70*pow(max(1-(t-1.0)/0.22,0),2)':enable='between(t,1.0,4.8)':format=auto[ms]"); cur='ms'
    fc.append(f"[{cur}][1:v]overlay=0:0:enable='between(t,0.3,{0.3+c+0.2:.2f})':format=auto[m2]")
    fc.append(f"[2:v]scale=w='trunc(1080*(1+0.06*t/{F:.2f})/2)*2':h=-2:eval=frame,crop=1080:1920,setsar=1,eq=brightness=-0.1:saturation=0.85[f0]")
    fc.append(f"[3:v]format=rgba,fade=t=in:st={ta:.2f}:d=0.06:alpha=1[pp]")
    fc.append(f"[f0][pp]overlay=x=0:y='-60*pow(max(1-(t-{ta:.2f})/0.18,0),2)':enable='gte(t,{ta:.2f})':format=auto,fps=30,setsar=1[f1]")
    fc.append("[m2][f1]concat=n=2:v=1:a=0[v]")
    o=f'{SEGD}/c_{k}.mp4'
    run('ffmpeg','-v','error','-y',*inp,'-filter_complex',';'.join(fc),'-map','[v]','-map','4:a','-t',f'{T:.3f}',*enc(),o)
    return o,T
def card(k,imgp,D,music,mstart,mgain,c_at,a_at,vf_extra=''):
    v=V[k]; n=int(D*SR); vc=np.zeros((n,2),dtype='float32'); va=np.zeros((n,2),dtype='float32')
    place(vc,voice(f'{R}/v2_{k}_c.wav'),c_at); place(va,voice(f'{R}/v2_{k}_a.wav',1.05),a_at)
    m=load(f'{R}/aud/{music}.mp3')[int(mstart*SR):int(mstart*SR)+n].copy()
    if len(m)<n: m=np.pad(m,((0,n-len(m)),(0,0)))
    m*=mgain*duck_env(vc+va)[:,None]; fo=int(1.0*SR); m[-fo:]*=np.linspace(1,0,fo)[:,None]
    out=m+vc+va; sp=f'{R}/aud/sfx/surprise_hit.mp3'
    if os.path.exists(sp): place(out,load(sp)[:int(1.2*SR)]*0.5,a_at-0.12)
    w=f'{SEGD}/a2_{k}.wav'; sf.write(w,out,SR); return w
def intro():
    k='intro'; v=V[k]; a_at=0.5+v['c']+0.3; D=a_at+v['a']+0.7
    w=card(k,None,D,'mus_trophy',0,0.30,0.5,a_at)
    clips=['basement','beach','casino','moon','cemetery','trench','mine','clouds']; per=0.7
    # montage background (hold last 2.5 s on dark title)
    mont=[];
    for j,cn in enumerate(clips): mont+=['-ss','0.1','-t',str(per),'-i',f'{SEGD}/s_{cn}.mp4']
    n=len(clips); fcs=[f"[{j}:v]scale=1080:1920,setsar=1,fps=30,trim=duration={per},setpts=PTS-STARTPTS[q{j}]" for j in range(n)]
    fcs.append(''.join(f'[q{j}]' for j in range(n))+f"concat=n={n}:v=1:a=0,tpad=stop_mode=clone:stop_duration={D:.2f},eq=brightness=-0.25:saturation=0.8[bg]")
    # title overlay: dark gradient bottom + text
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); px=im.load()
    for y in range(1920):
        al=255 if y>1230 else (int(60+195*(y-900)/330) if y>900 else (235 if y<340 else int(60+60*(1-y/900))))
        for x in range(0,1080,1): px[x,y]=(8,3,20,al)
    d=ImageDraw.Draw(im)
    d.text((540,800),'A MEME ROYALE',font=FI(46),fill=(255,205,50,255),anchor='mm')
    stroke_text(d,(540,930),'THE',FL(96),(255,255,255,255),(70,20,120,255),8,'mm')
    stroke_text(d,(540,1060),'TROPHY ROAD',FL(128),(255,205,50,255),(70,20,120,255),10,'mm')
    d.text((540,1200),'17 ARENAS  ·  ONE ROAD',font=FI(48),fill=(235,225,255,255),anchor='mm'); im.save(f'{SEGD}/intro2.png')
    fcs.append(f"[bg][{n}:v]overlay=0:0:format=auto,fade=t=in:d=0.3,fade=t=out:st={D-0.5:.2f}:d=0.5,format=yuv420p[v]")
    run('ffmpeg','-v','error','-y',*mont,'-loop','1','-t',f'{D:.2f}','-i',f'{SEGD}/intro2.png','-i',w,'-filter_complex',';'.join(fcs),'-map','[v]','-map',f'{n+1}:a','-t',f'{D:.2f}',*enc(),f'{SEGD}/c_intro.mp4'); return D
def outro():
    k='outro'; v=V[k]; c_at=0.8; a_at=c_at+v['c']+0.35; D=a_at+v['a']+0.9
    w=card(k,None,D,'mus_trophy',3,0.30,c_at,a_at)
    run('ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',f'{SEGD}/outro.png','-i',w,'-t',f'{D:.2f}','-vf',
        f"zoompan=z='1+0.0004*on':d=1:s=1080x1920:fps=30,fade=t=in:d=0.4,fade=t=out:st={D-0.8:.2f}:d=0.8,format=yuv420p",*enc(),f'{SEGD}/c_outro.mp4'); return D
if __name__=='__main__':
    keys=only or ARENAS
    for k in keys:
        print(k,build(k)); sys.stdout.flush()
    if not only: print('intro',intro()); print('outro',outro())
