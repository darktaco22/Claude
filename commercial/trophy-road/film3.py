import sys, os, json, subprocess, numpy as np, soundfile as sf
args=sys.argv[1:]
from assemble import load, run, SR, MUS, FL, FI, stroke_text, CAP, R, ARENAS, overlay_png, road_png, META
import comedy as C
from comedy import voice, place, duck_env, wrap, cap_png, enc, rd
from PIL import Image, ImageDraw
SEGD=R+'/seg'; HD=R+'/hero'; V=json.load(open(R+'/vo2.json'))
HEROES=json.load(open(CAP+'/hero.json'))
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]).decode())
def sfx_path(f): return f'{R}/aud/sfx/{f}'
def punch_top(text,path,cy=520):
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(im)
    f=FL(104); ls=wrap(d,text.upper(),f,880); h=len(ls)*112+96; y0=cy-h//2
    d.rounded_rectangle((50,y0-26,1030,y0+h),radius=36,fill=(18,6,40,210),outline=(255,205,50,255),width=6)
    y=y0+62
    for l in ls: stroke_text(d,(540,y),l,f,(255,255,255,255),(110,30,170,255),9,'mm'); y+=112
    d.text((540,y0+h-30),'THE ANALYST, UNIMPRESSED',font=FI(32),fill=(255,205,50,255),anchor='mm'); im.save(path)
def hero(a):
    i=ARENAS.index(a)+1; v=V[a]; info=json.load(open(f'{HD}/{a}.json')); times=np.array(info['times'],dtype=float)
    vid=f'{HD}/{a}.mp4'; T=len(times)/30.0+0.8
    bt=(times-times[0])/1000.0                       # battle time per frame
    fidx=lambda t: int(np.searchsorted(bt,t))/30.0   # video time of battle time t
    slow=[x for x in info['info'] if x[0]=='slow']; s0=(slow[0][1]/30.0) if slow else fidx(6.0)
    c_at=0.9; a_at=max(s0+0.5,c_at+v['c']+0.4)
    n=int(T*SR); vc=np.zeros((n,2),dtype='float32'); va=np.zeros((n,2),dtype='float32')
    place(vc,voice(f'{R}/v2_{a}_c.wav'),c_at); place(va,voice(f'{R}/v2_{a}_a.wav',1.05),a_at)
    m=load(f'{R}/aud/{MUS[a]}.mp3'); st=int(7.0*SR); mm=m[st:st+n].copy()
    if len(mm)<n: mm=np.pad(mm,((0,n-len(mm)),(0,0)))
    mm*=0.17*duck_env(vc+va)[:,None]; fo=int(0.6*SR); mm[-fo:]*=np.linspace(1,0,fo)[:,None]; fi=int(0.5*SR); mm[:fi]*=np.linspace(0,1,fi)[:,None]
    out=mm.copy()
    for e in info['sfx']:
        if e.get('music') or e.get('amb') or not e.get('file'): continue
        k=int(np.searchsorted(times,e['t']));
        if k<=0 or k>=len(times): continue
        p=sfx_path(e['file'])
        if os.path.exists(p): s=load(p)[:int(1.5*SR)]; place(out,s*float(e.get('o',{}).get('vol',1) or 1)*0.22,k/30.0)
    sw=sfx_path('ui_swoosh.mp3') if os.path.exists(sfx_path('ui_swoosh.mp3')) else f'{R}/aud/ui_swoosh.mp3'
    for tb in (2.8,4.8,8.0):
        if os.path.exists(sw): place(out,load(sw)[:int(1.0*SR)]*0.35,max(0,fidx(tb)-0.05))
    sp=sfx_path('surprise_hit.mp3')
    if os.path.exists(sp): place(out,load(sp)[:int(1.2*SR)]*0.5,a_at-0.12)
    out+=vc+va; wav=f'{SEGD}/a3_{a}.wav'; sf.write(wav,out,SR)
    ov=f'{SEGD}/ov3_{a}.png'; overlay_png(a,ov); rd_=f'{SEGD}/road3_{a}.png'; road_png(i-1 if False else ARENAS.index(a),rd_)
    cap_png(v['caster'],f'{SEGD}/cap3_{a}.png'); punch_top(v['analyst'],f'{SEGD}/pt3_{a}.png')
    ta=a_at; te=a_at+v['a']+0.9
    fc=("[0:v]setsar=1,fps=30,eq=contrast=1.07:saturation=1.1:gamma=0.98,vignette=PI/6,format=yuva420p[b];"
        "[b][1:v]overlay=x='-1080*pow(1-min(max(t-0.6,0)/0.45,1),3)-1080*pow(min(max(t-4.0,0)/0.45,1),3)':y=0:format=auto[c];"
        "[c][2:v]overlay=0:0:format=auto[d];"
        f"[d][3:v]overlay=0:0:enable='between(t,{c_at:.2f},{c_at+v['c']+0.2:.2f})':format=auto[e];"
        f"[4:v]format=rgba,fade=t=in:st={ta:.2f}:d=0.06:alpha=1[pp];"
        f"[e][pp]overlay=x=0:y='-70*pow(max(1-(t-{ta:.2f})/0.18,0),2)':enable='between(t,{ta:.2f},{te:.2f})':format=auto,"
        f"tpad=stop_mode=clone:stop_duration=1,fade=t=in:d=0.4,fade=t=out:st={T-0.5:.2f}:d=0.5,format=yuv420p[v]")
    o=f'{SEGD}/h_{a}.mp4'
    run('ffmpeg','-v','error','-y','-i',vid,'-loop','1','-i',ov,'-loop','1','-i',rd_,'-loop','1','-i',f'{SEGD}/cap3_{a}.png','-loop','1','-i',f'{SEGD}/pt3_{a}.png','-i',wav,
        '-filter_complex',fc,'-map','[v]','-map','5:a','-t',f'{T:.3f}',*enc(),o); return o
def montage(key,arenas,mkey):
    v=V[mkey]; per=1.5; T=per*len(arenas)+1.2
    n=int(T*SR); vc=np.zeros((n,2),dtype='float32'); place(vc,voice(f'{R}/v2_{mkey}_c.wav'),0.25)
    m=load(f'{R}/aud/mus_trophy.mp3'); mm=m[int(14*SR):int(14*SR)+n].copy()
    if len(mm)<n: mm=np.pad(mm,((0,n-len(mm)),(0,0)))
    mm*=0.26*duck_env(vc)[:,None]; fo=int(0.5*SR); mm[-fo:]*=np.linspace(1,0,fo)[:,None]; fi=int(0.2*SR); mm[:fi]*=np.linspace(0,1,fi)[:,None]
    out=mm.copy(); sw=f'{R}/aud/ui_swoosh.mp3'
    for j in range(len(arenas)):
        if os.path.exists(sw): place(out,load(sw)[:int(1.0*SR)]*0.45,j*per)
    out+=vc; wav=f'{SEGD}/a3_{key}.wav'; sf.write(wav,out,SR)
    inp=[];fc=[]
    for j,a in enumerate(arenas):
        inp+=['-ss','0.9','-t',str(per+0.05),'-i',f'{SEGD}/s_{a}.mp4']
        fc.append(f"[{j}:v]setsar=1,fps=30,trim=duration={per},setpts=PTS-STARTPTS,scale=w='1080*(1+0.05*t/{per})':h=-2:eval=frame,crop=1080:1920[q{j}]")
    fc.append(''.join(f'[q{j}]' for j in range(len(arenas)))+f"concat=n={len(arenas)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=1,eq=contrast=1.07:saturation=1.1,fade=t=in:d=0.3,fade=t=out:st={T-0.5:.2f}:d=0.5,format=yuv420p[v]")
    run('ffmpeg','-v','error','-y',*inp,'-filter_complex',';'.join(fc),'-map','[v]','-map',f'{len(arenas)}:a','-t',f'{T:.3f}',*enc(),f'{SEGD}/h_{key}.mp4') if False else None
    run('ffmpeg','-v','error','-y',*inp,'-i',wav,'-filter_complex',';'.join(fc),'-map','[v]','-map',f'{len(arenas)}:a','-t',f'{T:.3f}',*enc(),f'{SEGD}/h_{key}.mp4'); return f'{SEGD}/h_{key}.mp4'
def intro3(bg='moon'):
    v=V['intro']; a_at=0.7+v['c']+0.3; D=a_at+v['a']+0.9
    w=C.card('intro',None,D,'mus_trophy',0,0.30,0.7,a_at)
    im=Image.new('RGBA',(1080,1920),(0,0,0,0)); px=im.load()
    for y in range(1920):
        al=255 if y>1230 else (int(60+195*(y-900)/330) if y>900 else (235 if y<340 else int(60+60*(1-y/900))))
        for x in range(1080): px[x,y]=(8,3,20,al)
    d=ImageDraw.Draw(im); d.text((540,800),'A MEME ROYALE',font=FI(46),fill=(255,205,50,255),anchor='mm')
    stroke_text(d,(540,930),'THE',FL(96),(255,255,255,255),(70,20,120,255),8,'mm'); stroke_text(d,(540,1060),'TROPHY ROAD',FL(128),(255,205,50,255),(70,20,120,255),10,'mm')
    d.text((540,1200),'17 ARENAS  ·  ONE ROAD',font=FI(48),fill=(235,225,255,255),anchor='mm'); im.save(f'{SEGD}/intro3.png')
    fc=(f"[0:v]setsar=1,fps=30,trim=duration={D:.2f},setpts=PTS-STARTPTS,eq=brightness=-0.15:saturation=0.9[bg];[bg][1:v]overlay=0:0:format=auto,fade=t=in:d=0.6,fade=t=out:st={D-0.6:.2f}:d=0.6,format=yuv420p[v]")
    run('ffmpeg','-v','error','-y','-i',f'{HD}/{bg}.mp4','-loop','1','-i',f'{SEGD}/intro3.png','-i',w,'-filter_complex',fc,'-map','[v]','-map','2:a','-t',f'{D:.2f}',*enc(),f'{SEGD}/h_intro.mp4'); return D
def join(fl,out,last=False,F=0.4):
    inp=[];fc=[];ds=[dur(f) for f in fl]
    for f in fl: inp+=['-i',f]
    L=ds[0];cur='0:v';ac='0:a'
    for i in range(1,len(fl)):
        fc.append(f'[{cur}][{i}:v]xfade=transition=fade:duration={F}:offset={L-F:.3f}[x{i}]'); cur=f'x{i}'
        fc.append(f'[{ac}][{i}:a]acrossfade=d={F}[a{i}]'); ac=f'a{i}'; L=L+ds[i]-F
    if last:
        fc.append(f'[{cur}]eq=contrast=1.05,format=gbrp,split=2[o1][o2];[o2]lut3d=file=/root/road/fx/cine_srgb.cube[lg];[o1][lg]blend=all_expr=A*0.25+B*0.75[gr];'
            '[gr]split=2[b1][b2];[b2]curves=all=\'0/0 0.65/0 1/1\',gblur=sigma=20[bl];[b1][bl]blend=all_mode=screen:all_opacity=0.22,rgbashift=rh=-1:bh=1,noise=alls=6:allf=t,format=yuv420p[vo]'); fc.append(f'[{ac}]loudnorm=I=-14:TP=-1.5:LRA=11[ao]'); cur,ac='vo','ao'
        e=['-c:v','libx264','-crf','22','-maxrate','4M','-bufsize','8M','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart']
    else: e=enc()
    run('ffmpeg','-v','error','-y',*inp,'-filter_complex',';'.join(fc),'-map',f'[{cur}]' if not cur.endswith(':v') else cur,'-map',f'[{ac}]' if not ac.endswith(':a') else ac,'-r','30',*e,out); return L
ORDER=[('h','intro'),('h','basement'),('m',('backyard','parking','plaza'),'mA'),('h','beach'),('m',('exchange','cold'),'mB'),('h','casino'),('h','penthouse'),('h','moon'),
       ('m',('factory','dump','mine'),'mC'),('h','cemetery'),('h','trench'),('h','clouds'),('c','metaverse'),('c','outro')]
if __name__=='__main__':
    mode=args[0] if args else 'all'
    files=[]
    for it in ORDER:
        if it[0]=='h' and it[1]=='intro':
            if os.path.exists(f'{HD}/moon.ok') or True:
                if not os.path.exists(f'{HD}/moon.mp4'): continue
                intro3('moon'); files.append(f'{SEGD}/h_intro.mp4')
        elif it[0]=='h':
            if not os.path.exists(f'{HD}/{it[1]}.ok'): print('missing hero',it[1]); continue
            if mode in ('all',it[1]) or mode=='final':
                if mode!='final': print(hero(it[1]))
            files.append(f'{SEGD}/h_{it[1]}.mp4')
        elif it[0]=='m':
            if mode in ('all',it[2]) and mode!='final': print(montage(it[2],it[1],it[2]))
            files.append(f'{SEGD}/h_{it[2]}.mp4')
        else:
            files.append(f'{SEGD}/c_{it[1]}.mp4')
    files=[f for f in files if os.path.exists(f)]
    if mode in ('all','final'):
        parts=[]
        for g in range(0,len(files),5):
            o=f'{SEGD}/p3_{g//5}.mp4'; parts.append(o)
            if len(files[g:g+5])==1: run('ffmpeg','-v','error','-y','-i',files[g],'-c','copy',o)
            else: join(files[g:g+5],o)
        out=R+'/trophy_road_v3.mp4'; L=join(parts,out,True); print(out,round(L,1),'s',os.path.getsize(out)//1000000,'MB')
