"""Generate setup + scene script for a REAPING shot. usage: python3 mk.py key  (reads shots.py S[key])"""
import json, sys
sys.path.insert(0, '.'); from shots import S
k = sys.argv[1]; c = S[k]
cards = list(dict.fromkeys([p[0] for p in c['people']] + ['whale','wojak','pepe','giga','bonk','troll','popcat','chillguy']))[:8]
acts = ["{t:0.03, do:()=>{const U=window.__game.units; window.__show=PPL.map(p=>U.showcase(p[0],p[1],p[2],p[3])); for(const e of window.__show){const v=e&&U.views.get(e.id); if(v&&v.ring) v.ring.visible=false;}}}"]
for t, i, name in c.get('cues', []):
    acts.append(f"{{t:{t}, do:()=>{{const U=window.__game.units; const e=window.__show[{i}]; const v=e&&U.views.get(e.id); if(v) U.play(v,'{name}',0.2);}}}}")
for t, code in c.get('js', []): acts.append(f"{{t:{t}, do:(b,m)=>{{{code}}}}}")
gj = ''.join(f"window.GEST({i},'{n}',{a},{b},{m});" for i, n, a, b, m in c.get('gests', []))
js = ("(()=>{const U=window.__game.units; if(U.__base) U.update=U.__base; else U.__base=U.update;})();" + f"window.__PROPS={json.dumps(c.get('props', {}))};" + open('props.js').read() + open('gest.js').read() + open('move.js').read() +
      f"(()=>{{const D=window.__dir;const PPL={json.dumps(c['people'])};D.actions=[{','.join(acts)}];D.pre=null;D.shots={'[]' if c.get('cam') is None else '[{t0:0,t1:'+str(c['T']+2)+',cam:'+c['cam']+',hud:'+json.dumps(bool(c.get('hud')))+'}]'};window.__T1={c['T']};window.__gests=[];{gj}{c.get('moves','')}}})();")
open(f'scene_{k}.js', 'w').write(js)
cfg = {'arena': c['arena'], 'me': cards, 'opp': cards, 'oppName': c.get('opp', 'rugmaster'), 'script': f'scene_{k}.js', 'pass': 'cine', 'myName': c.get('me_name')}
open(f'setup_{k}.js', 'w').write(open('setup2.js').read().replace('__CFG__', json.dumps(cfg)))
print('ok', k)
