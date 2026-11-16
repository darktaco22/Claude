import json
ARENAS=[
 ('basement', ['troll','bonk'],['chillguy','jeanphil'],'A'),
 ('backyard', ['cupsey','pudgy'],['chillhouse','dope'],'B'),
 ('parking',  ['popcat','swordcat'],['zcat','farter'],'C'),
 ('plaza',    ['pnut','apu'],['baton','npcwojak'],'A'),
 ('beach',    ['giga','floki'],['cate','triplet'],'B'),
 ('exchange', ['wojak','nyancat'],['walter','mensa'],'C'),
 ('casino',   ['pepe','michi'],['mitch','bonk'],'A'),
 ('cold',     ['moodeng','slerf'],['alon','troll'],'B'),
 ('penthouse',['whale','thisisfine'],['pippin','chillguy'],'C'),
 ('moon',     ['giga','pepe'],['troll','bonk'],'A'),
 ('factory',  ['bome','popcat'],['troll','wojak'],'B'),
 ('dump',     ['bonk','troll'],['wojak','chillguy'],'C'),
 ('cemetery', ['wojak','pnut'],['troll','giga'],'A'),
 ('trench',   ['whale','floki'],['moodeng','cate'],'B'),
 ('mine',     ['goat','swordcat'],['giga','bonk'],'C'),
 ('clouds',   ['toshi','nyancat'],['pepe','popcat'],'A'),
 ('metaverse',[],[],'E'),
]
CAMS={
 'A':"D.dolly([9,22,38],[9,12,30],[9,0,12],[9,0.8,11],42,46)",
 'B':"D.dolly([-4,9,34],[18,9,32],[9,0.8,14],[9,0.8,12],48,48)",
 'C':"D.orbit(9,0.5,15,25,11,-35,20,40)",
}
for i,(a,me,opp,c) in enumerate(ARENAS):
    pos0=[(5,20),(13,20),(9,17),(9,22)]; pos1=[(9,11),(5,12),(13,12),(9,8)]
    acts=[]
    for j,u in enumerate(me[:2]+me[:2]): acts.append(f"{{t:{0.2+0.8*j}, do:P(0,'{u}',{pos0[j][0]},{pos0[j][1]})}}")
    for j,u in enumerate(opp[:2]+opp[:2]): acts.append(f"{{t:{0.4+0.8*j}, do:P(1,'{u}',{pos1[j][0]},{pos1[j][1]})}}")
    if a=='moon': acts.append("{t:2.3, do:P(1,'godcandle',9,10)}") if False else None
    if c=='E':
        shots="[{t0:0,t1:5.4,cam:D.dolly([9,10,40],[9,4,26],[9,1,14],[9,1,10],46,50)}]"
        acts_js="[]"
    else:
        shots=f"""[{{t0:0,t1:2.3,cam:{CAMS[c]}}},{{t0:2.3,t1:6,cam:(k,cam,b)=>{{const u=[...b.ents.values()].filter(e=>e.kind==='unit'&&!e.dead);const c=u.length?[u.reduce((s,e)=>s+e.x,0)/u.length,u.reduce((s,e)=>s+e.z,0)/u.length]:[9,16];
          sm=sm?[sm[0]+(c[0]-sm[0])*0.12,sm[1]+(c[1]-sm[1])*0.12]:c; return D.orbit(sm[0],1.0,sm[1],12,7.5,30,-20,44)(k,cam);}}}}]"""
        acts_js='['+','.join(acts)+']'
    js=f"""(()=>{{const D=window.__dir;const P=(team,id,x,z)=>b=>D.play(b,team,id,x,z);let sm=null;
D.actions={acts_js};D.pre=null;D.shots={shots};}})();"""
    open(f'script_{a}.js','w').write(js)
    me8=(me+['troll','bonk','pepe','giga','wojak','popcat'])[:8]; me8=list(dict.fromkeys(me8+['troll','bonk','pepe','giga','wojak','popcat','chillguy','goat']))[:8]
    opp8=list(dict.fromkeys(opp+['troll','bonk','pepe','giga','wojak','popcat','chillguy','goat']))[:8]
    cfg={'arena':a,'me':me8,'opp':opp8,'oppName':'rugmaster','script':f'script_{a}.js','pass':'cine'}
    open(f'setup_{a}.js','w').write(open('setup2.js').read().replace('__CFG__',json.dumps(cfg)))
    out=f'frames/{i+1:02d}_{a}'
    cap=open('cap_tpl.js').read().replace('__OUT__',json.dumps(out)) if False else None
json.dump([a[0] for a in ARENAS],open('arenas.json','w'))
