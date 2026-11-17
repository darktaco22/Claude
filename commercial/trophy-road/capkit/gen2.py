import json
HERO=[ # arena, me, opp
 ('basement',['troll','bonk'],['chillguy','jeanphil']),
 ('beach',['giga','floki'],['cate','triplet']),
 ('casino',['pepe','michi'],['mitch','bonk']),
 ('penthouse',['whale','thisisfine'],['pippin','chillguy']),
 ('moon',['giga','pepe'],['troll','bonk']),
 ('cemetery',['wojak','pnut'],['troll','giga']),
 ('trench',['whale','floki'],['moodeng','cate']),
 ('clouds',['toshi','nyancat'],['pepe','popcat']),
]
PAD=['troll','bonk','pepe','giga','wojak','popcat','chillguy','goat']
TEND=9.8
for a,me,opp in HERO:
    WHALE=a in ('penthouse','trench'); FOLLOW='[-4.8,2.8,-10]' if WHALE else '[-2.6,1.7,-5.5]'; FOV=36 if WHALE else 34
    acts=[("0.9","0",me[0],9,22),("1.1","1",opp[0],9,10),("3.2","0",me[1],6,22),("3.4","1",opp[1],12,10)]
    acts_js='['+','.join(f"{{t:{t}, do:P({tm},'{u}',{x},{z})}}" for t,tm,u,x,z in acts)+']'
    cen="const u=[...b.ents.values()].filter(e=>e.kind==='unit'&&!e.dead);const c=u.length?[u.reduce((s,e)=>s+e.x,0)/u.length,u.reduce((s,e)=>s+e.z,0)/u.length]:[9,16];sm=sm?[sm[0]+(c[0]-sm[0])*0.10,sm[1]+(c[1]-sm[1])*0.10]:c;"
    shots=("[{t0:0,t1:2.8,cam:D.dolly([9,24,48],[9,16,40],[9,0,16],[9,1,14],34,38)},"
      f"{{t0:2.8,t1:4.8,cam:D.follow(e=>e.kind==='unit'&&e.team===0,{FOLLOW},[0,1.4,0],{FOV})}},"
      f"{{t0:4.8,t1:8.0,cam:(k,cam,b)=>{{{cen} return D.orbit(sm[0],1.0,sm[1],10.5,7.2,40,-15,38)(k,cam);}}}},"
      f"{{t0:8.0,t1:{TEND+1},cam:(k,cam,b)=>{{{cen} return D.orbit(sm[0],1.0,sm[1],15,9.5,-15,-45,40)(k,cam);}}}}]")
    js=f"(()=>{{const D=window.__dir;const P=(team,id,x,z)=>b=>D.play(b,team,id,x,z);let sm=null;D.actions={acts_js};D.pre=null;D.shots={shots};}})();"
    open(f'script2_{a}.js','w').write(js)
    me8=list(dict.fromkeys(me+PAD))[:8]; opp8=list(dict.fromkeys(opp+PAD))[:8]
    cfg={'arena':a,'me':me8,'opp':opp8,'oppName':'rugmaster','script':f'script2_{a}.js','pass':'cine'}
    open(f'setup3_{a}.js','w').write(open('setup2.js').read().replace('__CFG__',json.dumps(cfg)))
json.dump([h[0] for h in HERO],open('hero.json','w'))
