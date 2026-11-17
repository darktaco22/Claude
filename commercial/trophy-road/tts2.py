import numpy as np, soundfile as sf, json, sys
from kokoro_onnx import Kokoro
k=Kokoro('/root/kok/kokoro-v1.0.onnx','/root/kok/voices-v1.0.bin')
CASTER=('am_puck',1.04); ANALYST=('bm_george',0.98)
# key: (caster setup line, analyst punchline, sticker text)
S={
"intro":("Ladies and gentlemen! Welcome to THE TROPHY ROAD! Seventeen arenas! Zero financial advice!","Please remain seated.",""),
"basement":("Arena one! Mom's Basement! Our hero has a dream, a hoodie, and Wi-Fi!","Dinner is at six.","VIBES: DAMP"),
"backyard":("Arena two! Backyard Barbecue! Rubber ducks! Lawn chairs! Absolutely zero fire safety!","Somebody's dad is furious.","GRILL: UNATTENDED"),
"parking":("Arena three! The Strip Mall Lot! Cheap parking, big dreams, and one very haunted shopping cart!","Park responsibly.","PARKING: FREE (LIES)"),
"plaza":("Plaza After Dark! Neon! Sirens! And a liquidity pool of questionable depth!","Do not swim.","DEPTH: UNKNOWN"),
"beach":("Muscle Beach! Sun's out! Guns are out! Gains are, honestly, theoretical!","Leg day was postponed. Indefinitely.","GAINS: PENDING"),
"exchange":("The Trading Floor! Green candles! Red candles! A guy screaming BUY at absolutely nothing!","He has no position. Just passion.","SIGNAL: LOUD"),
"casino":("Degen Casino! The house always wins! Unless you ask the house. The house says it's fine!","The house is not fine.","ODDS: VIBES"),
"cold":("Cold Storage! Frozen wallets! Frostbitten bags! Somebody lost their seed phrase in the ice!","Check the freezer. Then check it again.","WALLET: FROZEN"),
"penthouse":("Lambo Penthouse! Marble floors! Gold everything! And a Lambo that is definitely not leased!","It is leased.","LAMBO: LEASED"),
"moon":("To The Moon! Zero gravity! Infinite hype! And the chart only goes up! Allegedly!","The chart is upside down.","ATH: ANY SECOND NOW"),
"factory":("The Memecoin Factory! Fresh tokens, straight off the line! Quality control left in twenty twenty-one!","Another one every nine seconds.","OUTPUT: INFINITE"),
"dump":("The Dump! Bags go in! Regret comes out! Please, no refunds!","No refunds.","BAGS: HELD (AGAINST WILL)"),
"cemetery":("Coin Cemetery! Rest in peace, old tickers! They had a roadmap! They had a community! They had a Discord!","The Discord is also dead.","RIP: ALL OF THEM"),
"trench":("Whale Trench! Deep waters! Bigger fish! One wrong move and you are the liquidity!","You are the liquidity.","DEPTH: SUSPICIOUS"),
"mine":("Diamond Hands Mine! Hold the line! Never sell! Never blink! Never check the price!","He checked the price.","HANDS: DIAMOND (SHAKING)"),
"clouds":("Copium Clouds! Breathe in! It's all still going up! Breathe out! Still going up!","It is not still going up.","COPIUM: 100%"),
"metaverse":("The Metaverse! The final arena! Look at that crowd!","There is no crowd.","PLAYERS ONLINE: 0"),
"mA":("Then the road gets weird! The Backyard! The Strip Mall! Plaza After Dark!","",""),
"mB":("The Trading Floor! Cold Storage!","",""),
"mC":("The Factory! The Dump! The Mine!","",""),
"outro":("Seventeen arenas! One road! More memes! More arenas! More chaos! Play it now on PC and mobile!","No financial advice included.",""),
}
def say(text,voice,speed):
    a,sr=k.create(text,voice=voice,speed=speed,lang='en-us')
    nz=np.where(np.abs(a)>0.01)[0]; a=a[max(0,nz[0]-300):nz[-1]+900]
    return a,sr
out={}
for key,(c,a_,st) in S.items():
    ac,sr=say(c,*CASTER); sf.write(f'/root/road/v2_{key}_c.wav',ac,sr)
    if a_:
        aa,sr=say(a_,*ANALYST); sf.write(f'/root/road/v2_{key}_a.wav',aa,sr); al=len(aa)/sr
    else: al=0
    out[key]=dict(c=len(ac)/sr,a=al,caster=c,analyst=a_,sticker=st)
    print(key,round(len(ac)/sr,2),round(al,2))
json.dump(out,open('/root/road/vo2.json','w'),indent=1)
