"""Graphics for WHO SOLD? All 1080x1920 RGBA PNGs unless noted."""
import os, random, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1920; FD='/root/road/who/fonts/'; G='/root/road/who/g/'
def F(name,size):
    p={'bebas':FD+'BebasNeue-Regular.ttf','type':FD+'SpecialElite-Regular.ttf','marker':FD+'PermanentMarker-Regular.ttf','serif':FD+'PlayfairDisplay.ttf',
       'bold':'/usr/share/fonts/opentype/inter/Inter-Bold.otf','med':'/usr/share/fonts/opentype/inter/Inter-Medium.otf','black':'/usr/share/fonts/opentype/inter/Inter-Black.otf',
       'mono':'/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'}[name]
    if not os.path.exists(p) and name=='mono': p='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
    return ImageFont.truetype(p,size)
def new(bg=(0,0,0,0)): return Image.new('RGBA',(W,H),bg)
def wrap(d,t,font,w):
    out=[];cur=''
    for wd in t.split():
        x=(cur+' '+wd).strip()
        if d.textlength(x,font=font)>w and cur: out.append(cur);cur=wd
        else: cur=x
    out.append(cur); return out
RED=(214,30,38,255)
def lower_third(name,role,path):
    im=new(); d=ImageDraw.Draw(im); y=1215
    fn=F('bebas',112); fr=F('med',38)
    wn=d.textlength(name,font=fn); rl=wrap(d,role,fr,820); wr=max(d.textlength(l,font=fr) for l in rl)
    w=int(max(wn,wr))+96; h=150+len(rl)*50
    d.rectangle((60,y,60+w,y+h),fill=(8,8,10,225)); d.rectangle((60,y,72,y+h),fill=RED)
    d.text((104,y+18),name,font=fn,fill=(255,255,255,255))
    for i,l in enumerate(rl): d.text((106,y+128+i*50),l,font=fr,fill=(215,215,220,255))
    im.save(path); return path
def caption(text,path,y=1560,size=46,italic_tag=None):
    im=new(); d=ImageDraw.Draw(im); f=F('bold',size); ls=wrap(d,text,f,940)
    for i,l in enumerate(ls):
        d.text((540,y+i*(size+14)),l,font=f,fill=(255,255,255,255),anchor='mm',stroke_width=6,stroke_fill=(0,0,0,255))
    im.save(path); return path
def card(lines,path,bg=(0,0,0,255),font='type',size=58,color=(235,235,235,255),y0=None,gap=1.5,align='c'):
    im=new(bg); d=ImageDraw.Draw(im); f=F(font,size); rows=[]
    for t in lines: rows+= wrap(d,t,f,900) + ['']
    rows=rows[:-1]; lh=int(size*gap); y=y0 if y0 is not None else (H-len(rows)*lh)//2
    for r in rows:
        if r: d.text((540,y),r,font=f,fill=color,anchor='ma')
        y+=lh
    im.save(path); return path
def title(path):
    im=new((0,0,0,255)); d=ImageDraw.Draw(im)
    d.text((540,760),'A MEME ROYALE ORIGINAL DOCUMENTARY',font=F('med',34),fill=(190,190,195,255),anchor='mm')
    d.text((540,960),'WHO SOLD?',font=F('bebas',262),fill=(255,255,255,255),anchor='mm')
    d.rectangle((250,1108,830,1118),fill=RED)
    d.text((540,1180),'ONE RULE.  ONE THROWN MATCH.  ONE SUSPECT TOO MANY.',font=F('med',32),fill=(190,190,195,255),anchor='mm')
    im.save(path); return path
def slam(text,path,size=260,color=(255,255,255,255),y=960):
    im=new(); d=ImageDraw.Draw(im)
    d.multiline_text((540,y),text,font=F('bebas',size),fill=color,anchor='mm',align='center',spacing=int(size*0.02),stroke_width=10,stroke_fill=(0,0,0,255)); im.save(path); return path
def tag(text,path,xy=(60,150)):
    im=new(); d=ImageDraw.Draw(im); f=F('bold',34); w=d.textlength(text,font=f)
    d.rectangle((xy[0],xy[1],xy[0]+w+44,xy[1]+62),fill=(0,0,0,170)); d.text((xy[0]+22,xy[1]+31),text,font=f,fill=(255,255,255,235),anchor='lm'); im.save(path); return path
def phone_banner(count,path):
    im=new(); d=ImageDraw.Draw(im); x0,y0,x1,y1=70,250,1010,440
    sh=new(); ImageDraw.Draw(sh).rounded_rectangle((x0,y0+10,x1,y1+10),radius=46,fill=(0,0,0,140)); im=Image.alpha_composite(im,sh.filter(ImageFilter.GaussianBlur(14))); d=ImageDraw.Draw(im)
    d.rounded_rectangle((x0,y0,x1,y1),radius=46,fill=(242,242,247,245))
    d.rounded_rectangle((x0+30,y0+38,x0+144,y0+152),radius=28,fill=(52,199,89,255)); d.text((x0+87,y0+95),'☎',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',70),fill=(255,255,255,255),anchor='mm')
    d.text((x0+176,y0+62),'MOM',font=F('black',52),fill=(20,20,22,255),anchor='lm')
    d.text((x0+176,y0+128),f'Missed call ({count})',font=F('med',42),fill=(90,90,96,255),anchor='lm')
    d.text((x1-34,y0+58),'now',font=F('med',32),fill=(130,130,136,255),anchor='rm'); im.save(path); return path
def phone_full(path,count=47):
    im=new((6,6,10,255)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((150,260,930,1700),radius=90,fill=(18,18,24,255),outline=(70,70,80,255),width=6)
    d.rounded_rectangle((180,300,900,1660),radius=64,fill=(10,22,48,255))
    d.text((540,480),'3:14',font=F('med',170),fill=(255,255,255,255),anchor='mm'); d.text((540,600),'Friday, the fourteenth',font=F('med',36),fill=(200,205,220,255),anchor='mm')
    y=760
    for i,(t,s) in enumerate([('MOM',f'Missed call ({count})'),('MOM','Voicemail: "call me back sweetie"'),('MOM','Voicemail: "it is about the button"')]):
        d.rounded_rectangle((210,y,870,y+170),radius=36,fill=(242,242,247,240)); d.rounded_rectangle((232,y+34,334,y+136),radius=24,fill=(52,199,89,255))
        d.text((283,y+85),'☎',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',60),fill=(255,255,255,255),anchor='mm')
        d.text((360,y+58),t,font=F('black',40),fill=(20,20,22,255),anchor='lm'); d.text((360,y+114),s,font=F('med',30),fill=(90,90,96,255),anchor='lm'); y+=196
    im.save(path); return path
def order_ticket(path):
    im=new((10,10,12,255)); t=Image.new('RGBA',(820,1040),(238,232,214,255)); d=ImageDraw.Draw(t)
    d.rectangle((0,0,819,150),fill=(30,30,34,255)); d.text((410,78),'DIAMOND HANDS MINE',font=F('bebas',92),fill=(238,232,214,255),anchor='mm')
    rows=[('ORDER No.','000001'),('DATE','FRI. THE 14TH'),('TIME','3:14 AM'),('TYPE','SELL'),('QUANTITY','ALL OF IT'),('REASON','(left blank)')]
    y=230
    for k,v in rows:
        d.text((70,y),k,font=F('type',44),fill=(60,60,64,255)); d.text((750,y),v,font=F('type',48),fill=(20,20,22,255),anchor='ra'); d.line((70,y+70,750,y+70),fill=(150,145,130,255),width=2); y+=112
    d.text((410,960),'this has never happened before',font=F('type',34),fill=(120,115,100,255),anchor='mm')
    st=Image.new('RGBA',(620,240),(0,0,0,0)); sd=ImageDraw.Draw(st); sd.rounded_rectangle((8,8,611,231),radius=18,outline=(200,24,30,235),width=14); sd.text((310,124),'SOLD',font=F('bebas',210),fill=(200,24,30,235),anchor='mm')
    st=st.rotate(-14,expand=True,resample=Image.BICUBIC); t.alpha_composite(st,(150,640))
    t=t.rotate(3,expand=True,resample=Image.BICUBIC); im.alpha_composite(t,((W-t.width)//2,410)); im.save(path); return path
def newspaper(path):
    im=new((14,14,16,255)); p=Image.new('RGBA',(900,1250),(232,226,208,255)); d=ImageDraw.Draw(p)
    d.text((450,80),'THE DAILY DEGEN',font=F('serif',92),fill=(20,20,22,255),anchor='mm'); d.line((40,140,860,140),fill=(20,20,22,255),width=6); d.line((40,152,860,152),fill=(20,20,22,255),width=2)
    d.text((450,182),'FRIDAY THE 14TH   ·   PRICE: UP ONLY   ·   WEATHER: COPIUM',font=F('med',22),fill=(60,60,64,255),anchor='mm')
    y=240
    for l in ['WHALE BUYS','POLICE STATION']: d.text((450,y),l,font=F('bebas',170),fill=(15,15,18,255),anchor='ma'); y+=160
    d.text((450,y+30),'"It was on sale," says whale',font=F('serif',50),fill=(40,40,44,255),anchor='ma')
    random.seed(4); y+=140
    for col in range(3):
        yy=y
        for r in range(22):
            wl=random.randint(170,250); d.rectangle((50+col*275,yy,50+col*275+wl,yy+9),fill=(120,116,104,255)); yy+=24
    p=p.rotate(-2.5,expand=True,resample=Image.BICUBIC); im.alpha_composite(p,((W-p.width)//2,330)); im.save(path); return path
def evidence_board(photos,path):
    """photos: list of (image path, label) - polaroids pinned to a cork board with red string."""
    random.seed(7); im=Image.new('RGBA',(W,H),(150,104,62,255)); px=im.load()
    noise=Image.effect_noise((W,H),38).convert('L'); im=Image.composite(Image.new('RGBA',(W,H),(176,128,80,255)),im,noise); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W-1,H-1),outline=(70,44,24,255),width=36)
    pos=[(110,170,-6),(590,130,5),(90,760,4),(600,720,-5),(140,1330,-3),(610,1290,6)]; centers=[]
    for (ph,lab),(x,y,rot) in zip(photos,pos):
        pol=Image.new('RGBA',(400,480),(246,244,238,255)); 
        try:
            src=Image.open(ph).convert('RGB'); s=min(src.size); src=src.crop(((src.width-s)//2,int(src.height*0.12),(src.width-s)//2+s,int(src.height*0.12)+s)).resize((360,360))
        except Exception: src=Image.new('RGB',(360,360),(60,60,70))
        pol.paste(src,(20,20)); pd=ImageDraw.Draw(pol); pd.text((200,430),lab,font=F('marker',40),fill=(30,30,34,255),anchor='mm')
        pol=pol.rotate(rot,expand=True,resample=Image.BICUBIC)
        sh=Image.new('RGBA',pol.size,(0,0,0,0)); sh.paste((0,0,0,110),(0,0),pol.split()[3]); im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)),(x+10,y+14)); im.alpha_composite(pol,(x,y)); centers.append((x+pol.width//2,y+34))
    d=ImageDraw.Draw(im)
    for a,b in [(0,1),(1,3),(3,2),(2,4),(4,5),(5,1),(0,3),(2,5)]:
        d.line((centers[a],centers[b]),fill=(190,20,26,255),width=7)
    for c in centers: d.ellipse((c[0]-16,c[1]-16,c[0]+16,c[1]+16),fill=(200,24,30,255),outline=(90,10,12,255),width=3)
    for (x,y,t,rot) in [(442,640,'IT IS ALL\nCONNECTED',-7),(442,1230,'WHOSE\nALARM?',6),(442,1690,'WAKE UP',-4)]:
        n=Image.new('RGBA',(196,120),(250,226,90,255)); nd=ImageDraw.Draw(n); nd.multiline_text((98,60),t,font=F('marker',30 if '\n' in t else 36),fill=(30,30,34,255),anchor='mm',align='center')
        n=n.rotate(rot,expand=True,resample=Image.BICUBIC); im.alpha_composite(n,(x,y-90))
    im.save(path); return path
def cctv_overlay(path):
    im=new(); d=ImageDraw.Draw(im)
    for y in range(0,H,6): d.line((0,y,W,y),fill=(0,0,0,46),width=2)
    d.text((60,150),'MATCH REPLAY   GRAND FINAL',font=F('mono',38),fill=(255,255,255,235)); d.text((60,206),'ROUND 3   0:03 LEFT',font=F('mono',38),fill=(255,255,255,235))
    d.ellipse((930,150,966,186),fill=(230,30,30,255)); d.text((1010,168),'REC',font=F('mono',34),fill=(255,255,255,235),anchor='rm') if False else None
    d.text((916,168),'REC',font=F('mono',34),fill=(255,255,255,235),anchor='rm')
    d.ellipse((330,820,750,1240),outline=(235,30,30,255),width=10); d.line((760,820,900,700),fill=(235,30,30,255),width=10)
    d.text((905,655),'NOTHING',font=F('bold',50),fill=(235,30,30,255),anchor='mm',stroke_width=5,stroke_fill=(0,0,0,255)); im.save(path); return path
def epilogue(name,lines,path):
    im=new((0,0,0,150)); d=ImageDraw.Draw(im); d.text((540,700),name,font=F('bebas',150),fill=(255,255,255,255),anchor='mm'); d.rectangle((440,792,640,800),fill=RED)
    f=F('type',50); y=880
    for t in lines:
        for r in wrap(d,t,f,860): d.text((540,y),r,font=f,fill=(238,238,238,255),anchor='ma'); y+=74
        y+=26
    im.save(path); return path
def endcard(path,logo='/home/user/Claude/commercial/kid/logo.png'):
    im=new((6,6,10,255)); lg=Image.open(logo).convert('RGBA'); lg=lg.resize((640,int(640*lg.height/lg.width))); im.alpha_composite(lg,(220,300)); d=ImageDraw.Draw(im)
    d.text((540,1060),'PLAY THE GAME',font=F('bebas',150),fill=(255,255,255,255),anchor='mm')
    d.text((540,1180),'THIS DOCUMENTARY IS BARELY ABOUT',font=F('bebas',74),fill=(255,205,50,255),anchor='mm'); d.rectangle((390,1250,690,1258),fill=RED)
    d.text((540,1350),'PC + MOBILE',font=F('bold',46),fill=(235,235,240,255),anchor='mm')
    d.text((540,1440),'memeroyale.imaginestudio.fun',font=F('med',44),fill=(235,235,240,255),anchor='mm'); d.text((540,1510),'@MemeRoyaleGames',font=F('med',42),fill=(255,205,50,255),anchor='mm')
    d.text((540,1720),'No pasta was wasted in the making of this film.',font=F('type',30),fill=(150,150,156,255),anchor='mm'); im.save(path); return path
if __name__=='__main__':
    lower_third('GIGACHAD','Witness. Did not skip arm day.',G+'t_lt.png'); title(G+'t_title.png'); phone_banner(12,G+'t_ph.png'); phone_full(G+'t_phone.png'); order_ticket(G+'t_order.png'); newspaper(G+'t_news.png')
    evidence_board([('/root/road/cap/t3/f_0001.png',n) for n in ['GIGA','DUCKS','CART','THE MOON','WOJAK','???']],G+'t_board.png'); cctv_overlay(G+'t_cctv.png'); epilogue('WOJAK',['was cleared of all charges.','He is still crying.','Doctors say it is unrelated.'],G+'t_epi.png'); endcard(G+'t_end.png')
    S=Image.new('RGB',(5*270,2*480),(40,40,40))
    for i,n in enumerate(['t_title','t_order','t_news','t_board','t_phone','t_cctv','t_epi','t_end','t_lt','t_ph']):
        a=Image.open(G+n+'.png'); bg=Image.new('RGBA',a.size,(70,90,110,255)); bg.alpha_composite(a); S.paste(bg.convert('RGB').resize((270,480)),((i%5)*270,(i//5)*480))
    S.save('/tmp/props.png')

def microwave(path):
    im=new((14,12,12,255)); d=ImageDraw.Draw(im)
    body=Image.new('RGBA',(900,640),(0,0,0,0)); b=ImageDraw.Draw(body)
    b.rounded_rectangle((0,0,899,639),radius=34,fill=(222,216,200,255),outline=(120,114,100,255),width=6)
    b.rounded_rectangle((40,50,620,590),radius=22,fill=(24,26,30,255),outline=(90,86,78,255),width=8)
    b.ellipse((150,330,510,540),fill=(236,236,230,255)); b.ellipse((190,355,470,505),fill=(240,226,150,255))
    for i in range(14): b.ellipse((205+i*18+(i%3)*4,385+(i%4)*14,224+i*18+(i%3)*4,404+(i%4)*14),fill=(86,168,70,255))
    b.rounded_rectangle((660,60,860,170),radius=14,fill=(10,10,12,255)); b.text((760,115),'3:14',font=F('mono',70),fill=(60,255,120,255),anchor='mm')
    for k,(lab,col) in enumerate([('REHEAT',(120,120,120,255)),('POPCORN',(120,120,120,255)),('SELL',(205,24,30,255))]):
        y=210+k*118; b.rounded_rectangle((680,y,840,y+84),radius=16,fill=col,outline=(60,58,52,255),width=4); b.text((760,y+42),lab,font=F('bold',32),fill=(255,255,255,255),anchor='mm')
    sh=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle((90,520,990,1260),radius=40,fill=(0,0,0,160)); im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)))
    im.alpha_composite(body,(90,500)); d=ImageDraw.Draw(im)
    d.text((540,1330),'MICROWAVE',font=F('bebas',120),fill=(255,255,255,255),anchor='mm'); d.text((540,1420),'(not a financial instrument)',font=F('type',38),fill=(190,190,196,255),anchor='mm')
    im.save(path); return path


# ---------------- v2 props: the match was thrown, not the money ----------------
DJ='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def phone_banner(count,path):
    """lock-screen alarm notification (the running gag): Dinner alarm, snoozed N times"""
    im=new(); x0,y0,x1,y1=70,250,1010,440
    sh=new(); ImageDraw.Draw(sh).rounded_rectangle((x0,y0+10,x1,y1+10),radius=46,fill=(0,0,0,140)); im=Image.alpha_composite(im,sh.filter(ImageFilter.GaussianBlur(14))); d=ImageDraw.Draw(im)
    d.rounded_rectangle((x0,y0,x1,y1),radius=46,fill=(242,242,247,245))
    d.rounded_rectangle((x0+30,y0+38,x0+144,y0+152),radius=28,fill=(255,149,0,255))
    cx,cy=x0+87,y0+97; d.ellipse((cx-34,cy-30,cx+34,cy+38),outline=(255,255,255,255),width=8); d.line((cx,cy+4,cx,cy-16),fill=(255,255,255,255),width=7); d.line((cx,cy+4,cx+14,cy+12),fill=(255,255,255,255),width=7)
    d.ellipse((cx-44,cy-42,cx-16,cy-14),fill=(255,255,255,255)); d.ellipse((cx+16,cy-42,cx+44,cy-14),fill=(255,255,255,255))
    d.text((x0+176,y0+62),'ALARM  -  DINNER 6:00 PM',font=F('black',44),fill=(20,20,22,255),anchor='lm')
    d.text((x0+176,y0+128),f'Snoozed ({count})',font=F('med',42),fill=(90,90,96,255),anchor='lm')
    d.text((x1-34,y0+150),'now',font=F('med',32),fill=(130,130,136,255),anchor='rm'); im.save(path); return path
def phone_full(path,count=47):
    im=new((6,6,10,255)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((150,260,930,1700),radius=90,fill=(18,18,24,255),outline=(70,70,80,255),width=6)
    d.rounded_rectangle((180,300,900,1660),radius=64,fill=(10,22,48,255))
    d.text((540,480),'5:58',font=F('med',170),fill=(255,255,255,255),anchor='mm'); d.text((540,600),'Friday, the fourteenth',font=F('med',36),fill=(200,205,220,255),anchor='mm')
    y=760
    for t,s2,col in [('ALARM  -  DINNER 6:00 PM',f'Snoozed ({count})',(255,149,0,255)),('RESERVATION','Table for one. Do not be late.',(52,120,246,255)),('RESERVATION','Your table is getting cold.',(52,120,246,255))]:
        d.rounded_rectangle((210,y,870,y+170),radius=36,fill=(242,242,247,240)); d.rounded_rectangle((232,y+34,334,y+136),radius=24,fill=col)
        d.ellipse((260,y+62,306,y+108),outline=(255,255,255,255),width=7); d.line((283,y+85,283,y+72),fill=(255,255,255,255),width=6); d.line((283,y+85,293,y+92),fill=(255,255,255,255),width=6)
        d.text((360,y+58),t,font=F('black',34),fill=(20,20,22,255),anchor='lm'); d.text((360,y+114),s2,font=F('med',28),fill=(90,90,96,255),anchor='lm'); y+=196
    im.save(path); return path
def order_ticket(path):
    """the scoreboard: a lead thrown away"""
    im=new((8,10,16,255)); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,170),fill=(22,26,40,255)); d.text((540,92),'GRAND FINAL',font=F('bebas',120),fill=(255,205,50,255),anchor='mm')
    d.text((540,380),'DEFEAT',font=F('bebas',300),fill=(214,30,38,255),anchor='mm',stroke_width=6,stroke_fill=(60,6,8,255))
    y=560
    for nm,sc,col,res in [('DIAMOND HANDS MINE','0',(60,140,255,255),'(was winning by a mile)'),('TEAM MID','1',(150,150,160,255),'(did nothing)')]:
        d.rounded_rectangle((90,y,990,y+210),radius=26,fill=(20,24,36,255),outline=col,width=6); d.text((140,y+78),nm,font=F('bebas',92),fill=(255,255,255,255),anchor='lm')
        d.text((140,y+155),res,font=F('type',40),fill=(170,174,190,255),anchor='lm'); d.text((930,y+105),sc,font=F('bebas',190),fill=col,anchor='rm'); y+=250
    d.text((540,1090),'ROUND 3    0:03 REMAINING',font=F('mono',44),fill=(200,205,220,255),anchor='mm')
    d.text((540,1170),'MVP:   nobody',font=F('type',52),fill=(200,205,220,255),anchor='mm')
    st=Image.new('RGBA',(700,260),(0,0,0,0)); sd=ImageDraw.Draw(st); sd.rounded_rectangle((8,8,691,251),radius=18,outline=(214,30,38,235),width=16); sd.text((350,134),'SOLD',font=F('bebas',230),fill=(214,30,38,235),anchor='mm')
    st=st.rotate(-12,expand=True,resample=Image.BICUBIC); st=st.resize((int(st.width*0.72),int(st.height*0.72)),Image.LANCZOS); im.alpha_composite(st,(300,1250)); im.save(path); return path
def pause_menu(path):
    """match-stats panel in the game's purple/gold style: the thrower did nothing (cards played 0)"""
    im=new((10,8,22,255)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((70,150,1010,330),radius=34,fill=(36,20,84,255),outline=(120,86,200,255),width=5)
    d.text((540,240),'TheNarrator',font=F('bebas',120),fill=(255,255,255,255),anchor='mm')
    P=(44,24,104,255); GOLD=(244,196,60,255)
    d.rounded_rectangle((70,500,1010,1330),radius=40,fill=P,outline=GOLD,width=6)
    d.text((540,580),'MATCH STATS',font=F('bebas',96),fill=GOLD,anchor='mm')
    y=700
    for k,v,hot in [('CARDS PLAYED','0',True),('COPIUM SPENT','0',True),('TOWER DMG','0',True),('TIME SPENT AFK','4:57',True)]:
        d.rounded_rectangle((130,y,950,y+140),radius=24,fill=(24,12,66,255),outline=(100,74,180,255),width=3)
        d.text((180,y+70),k,font=F('bebas',70),fill=(210,206,235,255),anchor='lm'); d.text((900,y+70),v,font=F('bebas',110),fill=(255,90,90,255) if hot else (255,255,255,255),anchor='rm'); y+=160
    d.text((540,1440),'COPIUM',font=F('bebas',70),fill=(210,206,235,255),anchor='mm')
    for i in range(10):
        x=110+i*86; d.rounded_rectangle((x,1480,x+74,1550),radius=14,fill=(168,92,255,255),outline=(220,190,255,255),width=3)
    d.text((540,1600),'10 / 10  (UNSPENT)',font=F('mono',46),fill=(255,255,255,255),anchor='mm')
    d.text((540,1700),'TIME LEFT 0:03',font=F('mono',40),fill=(160,166,184,255),anchor='mm'); im.save(path); return path
def reservation(path):
    im=new((14,12,12,255)); c=Image.new('RGBA',(840,1060),(242,236,218,255)); d=ImageDraw.Draw(c)
    d.rectangle((24,24,815,1035),outline=(120,36,36,255),width=6)
    d.text((420,150),'BELLA NOTTE',font=F('serif',96),fill=(110,28,28,255),anchor='mm'); d.text((420,236),'T R A T T O R I A',font=F('med',34),fill=(110,28,28,255),anchor='mm'); d.line((120,290,720,290),fill=(110,28,28,255),width=3)
    d.text((420,370),'RESERVATION CONFIRMED',font=F('bold',40),fill=(40,40,44,255),anchor='mm')
    y=470
    for k,v in [('NAME','The Narrator'),('PARTY','1'),('DATE','Fri. the 14th'),('TIME','6:00 PM')]:
        d.text((110,y),k,font=F('type',40),fill=(100,96,88,255)); d.text((730,y),v,font=F('type',46),fill=(20,20,22,255),anchor='ra'); d.line((110,y+66,730,y+66),fill=(190,184,166,255),width=2); y+=104
    d.text((420,930),'Late tables are given away.',font=F('type',32),fill=(120,115,100,255),anchor='mm')
    d.text((420,985),'(Spaghetti is non-refundable.)',font=F('type',30),fill=(120,115,100,255),anchor='mm')
    c=c.rotate(-3,expand=True,resample=Image.BICUBIC); sh=new(); sh.paste((0,0,0,170),(0,0),Image.new('L',(1,1),0)) if False else None
    shd=Image.new('RGBA',c.size,(0,0,0,0)); shd.paste((0,0,0,150),(0,0),c.split()[3]); im.alpha_composite(shd.filter(ImageFilter.GaussianBlur(22)),((W-c.width)//2+14,330+22)); im.alpha_composite(c,((W-c.width)//2,330))
    d=ImageDraw.Draw(im); d.text((540,1560),'EXHIBIT Z',font=F('bebas',150),fill=(255,255,255,255),anchor='mm'); d.text((540,1660),'(it was the reservation)',font=F('type',40),fill=(190,190,196,255),anchor='mm'); im.save(path); return path
