"""Synthesised true-crime score and sound effects (no samples, no licences). 44.1 kHz stereo float32."""
import numpy as np
SR=44100
def t(d): return np.arange(int(d*SR))/SR
def env(n,a=0.01,r=0.3):
    e=np.ones(n); na=min(n,int(a*SR)); nr=min(n,int(r*SR)); e[:na]=np.linspace(0,1,na); e[-nr:]*=np.linspace(1,0,nr); return e
def lp(x,fc):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); return np.fft.irfft(X/(1+(f/fc)**4),len(x))
def hp(x,fc):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/SR); return np.fft.irfft(X*((f/fc)**4/(1+(f/fc)**4)),len(x))
def reverb(x,decay=2.2,mix=0.35,seed=1):
    rng=np.random.default_rng(seed); n=int(decay*SR); ir=rng.standard_normal(n)*np.exp(-np.arange(n)/(decay*SR/6.9)); ir=lp(ir,5000); ir/=np.abs(ir).sum()**0.5*6
    m=len(x)+n; y=np.fft.irfft(np.fft.rfft(x,m)*np.fft.rfft(ir,m),m); return x*(1-mix)+y[:len(x)]*mix*8
def st(x,w=0.0):  # mono -> stereo
    return np.stack([x,x],1).astype('float32')
def note(f,d,bright=0.5):
    tt=t(d); y=sum(np.sin(2*np.pi*f*k*tt*(1+0.0004*k*k))*np.exp(-tt*(1.6+0.9*k))/(k**(1.2+0.8*(1-bright))) for k in range(1,9)); return y*env(len(tt),0.004,0.2)
def drone(d,root=36.71,seed=3):   # D1
    tt=t(d); rng=np.random.default_rng(seed); y=np.zeros(len(tt))
    for f,a in [(root,1.0),(root*2,0.7),(root*3,0.35),(root*2*1.498,0.3),(root*4*1.189,0.18)]:
        for det in (-0.25,0.2):
            ph=rng.uniform(0,6.28); y+=a*np.sin(2*np.pi*(f+det)*tt+ph+0.6*np.sin(2*np.pi*0.07*tt+ph))
    y*=0.5+0.5*np.sin(2*np.pi*0.045*tt+1)**2*0.6+0.2
    return lp(y,420)*0.16
def heartbeat(d,bpm=50):
    y=np.zeros(int(d*SR)); per=60/bpm
    for k in range(int(d/per)):
        for off,amp in ((0,1.0),(0.22,0.6)):
            s=int((k*per+off)*SR); tt=t(0.35); b=np.sin(2*np.pi*(52*np.exp(-tt*9)+38)*tt)*np.exp(-tt*11)*amp
            e=min(len(y),s+len(b)); y[s:e]+=b[:e-s]
    return y*0.5
def piano_line(d,seq,step=2.4,start=0.6):
    y=np.zeros(int(d*SR)+SR*4); i=0; pos=start
    while pos<d-1:
        f=seq[i%len(seq)]
        if f: n=note(f,3.2); s=int(pos*SR); y[s:s+len(n)]+=n*0.5
        pos+=step; i+=1
    return reverb(y[:int(d*SR)],2.6,0.45)
def boom(d=3.0):
    tt=t(d); y=np.sin(2*np.pi*(70*np.exp(-tt*5)+30)*tt)*np.exp(-tt*2.2); rng=np.random.default_rng(5); y+=lp(rng.standard_normal(len(tt)),900)*np.exp(-tt*7)*0.6
    return reverb(y,2.5,0.4)*0.9
def riser(d=2.5):
    tt=t(d); rng=np.random.default_rng(9); k=tt/d; y=np.sin(2*np.pi*(110*tt+ (330*d)*k*k/2*2))*k**2*0.35+hp(lp(rng.standard_normal(len(tt)),6000),800)*k**3*0.5; return y
def tick():
    tt=t(0.05); rng=np.random.default_rng(2); return hp(rng.standard_normal(len(tt)),2500)*np.exp(-tt*120)*0.5
def typewriter(nchars,cps=17):
    y=np.zeros(int((nchars/cps+0.3)*SR)); rng=np.random.default_rng(11); tk=tick()
    for i in range(nchars):
        s=int((i/cps+rng.uniform(0,0.012))*SR); y[s:s+len(tk)]+=tk*rng.uniform(0.6,1.0)
    return y
def buzz(reps=2):
    one=np.concatenate([np.sign(np.sin(2*np.pi*155*t(0.38)))*env(int(0.38*SR),0.01,0.05)*0.5,np.zeros(int(0.16*SR))]); y=np.tile(one,reps); return lp(y,700)*0.8
def whoosh(d=0.5):
    tt=t(d); rng=np.random.default_rng(4); k=tt/d; n=rng.standard_normal(len(tt)); return (lp(n,900)*(1-k)+lp(n,5000)*k)*np.sin(np.pi*k)**2*0.6
def shutter():
    tt=t(0.09); rng=np.random.default_rng(6); return hp(rng.standard_normal(len(tt)),1500)*np.exp(-tt*60)*0.7
def sting_low():
    y=np.concatenate([note(73.4,0.9,0.2)*1.2,np.zeros(1)]); z=note(69.3,2.2,0.2)*1.3; out=np.zeros(int(3.4*SR)); out[:len(y)]+=y; s=int(0.75*SR); out[s:s+len(z)]+=z; return reverb(out,2.0,0.35)
MINOR=[293.66,0,349.23,0,220.0,0,261.63,246.94,0,293.66,0,174.61]     # D minor fragments
MAJOR=[293.66,369.99,440.0,0,392.0,369.99,0,293.66]                    # D major resolve
def beep(n=3,gap=0.5):
    out=np.zeros(int((n*gap+0.3)*SR))
    for i in range(n):
        tt=t(0.22); b=np.sin(2*np.pi*2300*tt)*env(len(tt),0.003,0.03)*0.45; s=int(i*gap*SR); out[s:s+len(b)]+=b
    return out
