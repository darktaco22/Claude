"""WHO SOLD? interview / lineup / establishing shots. Characters are placed with the engine's own showcase() (idle pose)."""
import json
PAD=['troll','bonk','pepe','giga','wojak','popcat','chillguy','goat','whale']
# key: arena, T1 (seconds), people [(card,x,z,face)], cam js, cues [(t, card index, anim)]
def interview(x=9,z=21,side=1,fov=(28,25),**kw):
    # framing computed in the page from the character's own height: thighs-up, slight down-tilt, slow push-in
    return ("(k,cam)=>{const e=(window.__show||[])[0]; const Hh=e?2.15*Math.pow(e.h,0.85):2.4;"
            f"const s={side}, x={x}, z=e?e.z:14;"
            f"return D.dolly([x+0.42*Hh*s,0.95*Hh,z+2.0*Hh],[x+0.34*Hh*s,0.93*Hh,z+1.7*Hh],[x-0.08*Hh*s,0.66*Hh,z],[x-0.08*Hh*s,0.68*Hh,z],{fov[0]},{fov[1]})(k,cam);}}")
S={
 'giga':  dict(arena='beach',    T=7.5, people=[('giga',9,21,0)],  cam=interview(), cues=[(3.2,0,'emote')]),
 'wojak': dict(arena='cemetery', T=8.0, people=[('wojak',9,21,0)], cam=interview(side=-1), cues=[(0.2,0,'lose')]),
 'whale': dict(arena='penthouse',T=7.0, people=[('whale',9,21,0)], cam=interview(), cues=[]),
 'pepe':  dict(arena='casino',   T=7.5, people=[('pepe',9,21,0)],  cam=interview(side=-1), cues=[(0.6,0,'emote'),(4.6,0,'attack1')]),
 'bonk':  dict(arena='backyard', T=5.0, people=[('bonk',9,21,0)],  cam=interview(), cues=[(1.6,0,'attack1')]),
 'troll': dict(arena='parking',  T=7.0, people=[('troll',9,21,0)], cam=interview(), cues=[(0.4,0,'emote'),(3.5,0,'win')]),
 'lineup':dict(arena='parking',  T=6.0, people=[('giga',3.5,12.5,0),('wojak',5.7,12.5,0),('whale',8.3,12.5,0),('pepe',10.9,12.5,0),('bonk',12.9,12.5,0),('troll',14.9,12.5,0)],
               cam="D.dolly([5.6,2.9,23.2],[12.6,2.9,23.2],[3.6,2.3,12.5],[14.8,2.3,12.5],34,34)", cues=[(4.2,5,'emote')]),
 'mine':  dict(arena='mine',     T=5.0, people=[], cam="D.dolly([9,26,50],[9,15,40],[9,0,16],[9,1,14],34,38)", cues=[]),
 'basement2': dict(arena='basement', T=5.0, people=[], cam="D.dolly([9,7,36],[9,5,30],[9,5.5,4],[9,5.5,4],30,24)", cues=[]),
}
import sys
for k,c in S.items():
    ppl=json.dumps(c['people']); auto='true' if len(c['people'])==1 else 'false'
    acts=["{t:0.03, do:()=>{const U=window.__game.units; window.__show=PPL.map(p=>U.showcase(p[0],p[1],p[2],p[3])); for(const e of window.__show){const v=e&&U.views.get(e.id); if(v&&v.ring) v.ring.visible=false; if(AUTO&&e){const Hh=2.15*Math.pow(e.h,0.85); e.z=e.pz=26.2-2.0*Hh;}}}}"]
    for t,i,name in c['cues']:
        acts.append(f"{{t:{t}, do:()=>{{const U=window.__game.units; const e=window.__show[{i}]; const v=e&&U.views.get(e.id); if(v) U.play(v,'{name}',0.2);}}}}")
    js=f"(()=>{{const D=window.__dir;const PPL={ppl};const AUTO={auto};D.actions=[{','.join(acts)}];D.pre=null;D.shots=[{{t0:0,t1:{c['T']+2},cam:{c['cam']}}}];window.__T1={c['T']};}})();"
    open(f'script3_{k}.js','w').write(js)
    cards=list(dict.fromkeys([p[0] for p in c['people']]+PAD))[:8]
    cfg={'arena':c['arena'],'me':cards,'opp':cards,'oppName':'rugmaster','script':f'script3_{k}.js','pass':'cine'}
    open(f'setup4_{k}.js','w').write(open('setup2.js').read().replace('__CFG__',json.dumps(cfg)))
json.dump({k:dict(arena=c['arena'],T=c['T']) for k,c in S.items()},open('shots3.json','w'))
