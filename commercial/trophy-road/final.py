import sys,subprocess,numpy as np,soundfile as sf,json,os
sys.argv=['x']; 
from assemble import *
def bg(path,top=(18,8,40),bot=(60,18,90)):
    a=np.zeros((1920,1080,3),dtype='uint8')
    for c in range(3): a[:,:,c]=np.linspace(top[c],bot[c],1920)[:,None]
    Image.fromarray(a).save(path)
def music(name,start,dur,gain,fi=0.5,fo=1.0):
    m=load(f'{R}/aud/{name}.mp3'); n=int(dur*SR); s=m[int(start*SR):int(start*SR)+n].copy()
    if len(s)<n: s=np.pad(s,((0,n-len(s)),(0,0)))
    s*=gain; a=int(fi*SR); b=int(fo*SR); s[:a]*=np.linspace(0,1,a)[:,None]; s[-b:]*=np.linspace(1,0,b)[:,None]; return s
def vo(key,n,at):
    run('ffmpeg','-v','error','-y','-i',f'{R}/vo_{key}.wav','-ar',SR,'-ac',2,R+'/tmp_vo.wav'); v,_=sf.read(R+'/tmp_vo.wav',dtype='float32')
    v=v/np.abs(v).max()*0.8; o=np.zeros((n,2),dtype='float32'); s=int(at*SR); o[s:s+len(v)]=v[:n-s]; return o
# ---- intro 3.2s
D=3.2; bg(R+'/seg/bg_in.png',(8,4,18),(40,12,70))
im=Image.open(R+'/seg/bg_in.png').convert('RGBA'); d=ImageDraw.Draw(im)
d.text((540,800),'A MEME ROYALE',font=FI(46),fill=(255,205,50,255),anchor='mm')
stroke_text(d,(540,930),'THE',FL(96),(255,255,255,255),(70,20,120,255),8,'mm')
stroke_text(d,(540,1070),'TROPHY ROAD',FL(128),(255,205,50,255),(70,20,120,255),10,'mm')
d.text((540,1230),'17 ARENAS  ·  ONE ROAD',font=FI(50),fill=(235,225,255,255),anchor='mm')
im.save(R+'/seg/intro.png')
au=music('mus_trophy',0,D,0.5,0.3,0.4)+vo('intro',int(D*SR),0.7); sf.write(R+'/seg/a_intro.wav',au,SR)
run('ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',R+'/seg/intro.png','-i',R+'/seg/a_intro.wav','-t',D,
 '-vf',"zoompan=z='1+0.0006*on':d=1:s=1080x1920:fps=30,fade=t=in:d=0.5,fade=t=out:st=2.8:d=0.4,format=yuv420p",'-c:v','libx264','-crf','17','-c:a','aac','-b:a','192k',R+'/seg/s_intro.mp4')
# ---- outro 8.5s
D=8.5; bg(R+'/seg/bg_out.png')
logo=Image.open('/home/user/Claude/commercial/kid/logo.png').convert('RGBA'); logo=logo.resize((700,int(700*logo.height/logo.width)))
im=Image.open(R+'/seg/bg_out.png').convert('RGBA'); d=ImageDraw.Draw(im)
im.paste(logo,(190,230),logo)
stroke_text(d,(540,1010),'MORE MEMES.',FL(104),(255,255,255,255),(70,20,120,255),8,'mm')
stroke_text(d,(540,1130),'MORE ARENAS.',FL(104),(255,205,50,255),(70,20,120,255),8,'mm')
stroke_text(d,(540,1250),'MORE CHAOS.',FL(104),(255,255,255,255),(70,20,120,255),8,'mm')
d.rounded_rectangle((120,1390,960,1480),radius=44,fill=(255,205,50,255)); d.text((540,1435),'FULLY PLAYABLE ON PC + MOBILE',font=FI(40),fill=(40,14,70,255),anchor='mm')
d.text((540,1580),'memeroyale.imaginestudio.fun',font=FI(48),fill=(255,255,255,255),anchor='mm')
d.text((540,1650),'@MemeRoyaleGames',font=FI(46),fill=(255,205,50,255),anchor='mm')
im.save(R+'/seg/outro.png')
au=music('mus_trophy',3,D,0.5,0.3,1.5)+vo('outro',int(D*SR),0.8); sf.write(R+'/seg/a_outro.wav',au,SR)
run('ffmpeg','-v','error','-y','-loop','1','-framerate','30','-i',R+'/seg/outro.png','-i',R+'/seg/a_outro.wav','-t',D,
 '-vf',"zoompan=z='1+0.0004*on':d=1:s=1080x1920:fps=30,fade=t=in:d=0.4,fade=t=out:st=7.7:d=0.8,format=yuv420p",'-c:v','libx264','-crf','17','-c:a','aac','-b:a','192k',R+'/seg/s_outro.mp4')
print('cards ok')
