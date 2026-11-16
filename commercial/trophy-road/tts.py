import numpy as np, soundfile as sf, json
from kokoro_onnx import Kokoro
k=Kokoro('/root/kok/kokoro-v1.0.onnx','/root/kok/voices-v1.0.bin')
L=[("intro","Every legend starts somewhere."),
("basement","Mom's Basement. Where every degen starts. Mind the energy drink spill."),
("backyard","The Backyard. Burgers, a kiddie pool, and a lawn worth fighting for."),
("parking","The Strip Mall Lot. A pawn shop, a vape shop, and a parking lot full of beef."),
("plaza","Plaza After Dark. Neon. Sirens. A liquidity pool."),
("beach","Muscle Beach. Sun, sand, and somebody else's dumbbells."),
("exchange","The Trading Floor. Buy high. Sell low. Scream at screens."),
("casino","The Degen Casino. The house always wins. Prove it wrong."),
("cold","Cold Storage. Frozen wallets. Frostbitten bags."),
("penthouse","The Lambo Penthouse. Three Lambos. Zero chill."),
("moon","To the Moon. You made it. Now hold the line."),
("factory","The Memecoin Factory. Time to print your own."),
("dump","The Dump. Where your last twelve launches ended up."),
("cemetery","The Coin Cemetery. Here lies every coin you swore was different."),
("trench","The Whale Trench. Rock bottom. And something is still selling below you."),
("mine","The Diamond Hands Mine. Dig deeper. Never let go."),
("clouds","Copium Clouds. Breathe in. It's all still going up."),
("metaverse","The Metaverse. Nobody's here. Prices are holding."),
("outro","Seventeen arenas. One road. More memes. More arenas. More chaos.")]
out={}
for key,t in L:
    a,sr=k.create(t,voice='am_onyx',speed=1.0,lang='en-us')
    nz=np.where(np.abs(a)>0.01)[0]; a=a[max(0,nz[0]-300):nz[-1]+900]
    sf.write(f'/root/road/vo_{key}.wav',a,sr); out[key]=len(a)/sr; print(key,round(len(a)/sr,2))
json.dump(out,open('/root/road/vo.json','w'))
