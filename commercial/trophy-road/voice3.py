"""Swap the Chatterbox narration (from the repo) into the film pipeline. Keeps the Kokoro files as v2k_*."""
import json, os, shutil, subprocess, numpy as np, soundfile as sf
R='/root/road'; SRC='/home/user/Claude/commercial/trophy-road/tts3/out'
V=json.load(open(R+'/vo2.json'))
n=0
for key,v in V.items():
    for role in ('c','a'):
        src=f'{SRC}/v3_{key}_{role}.wav'; dst=f'{R}/v2_{key}_{role}.wav'
        if role=='a' and not v['analyst']: continue
        if not os.path.exists(src): print('missing',src); continue
        if os.path.exists(dst) and not os.path.exists(f'{R}/v2k_{key}_{role}.wav'): shutil.copy(dst,f'{R}/v2k_{key}_{role}.wav')
        a,sr=sf.read(src,dtype='float32')
        if a.ndim>1: a=a.mean(1)
        nz=np.where(np.abs(a)>0.012)[0]
        a=a[max(0,nz[0]-int(0.05*sr)):nz[-1]+int(0.25*sr)]
        sf.write(dst,a,sr); V[key]['c' if role=='c' else 'a']=len(a)/sr; n+=1
json.dump(V,open(R+'/vo2.json','w'),indent=1); print('swapped',n,'files')
for k,v in V.items(): print(k,round(v['c'],2),round(v['a'],2))
