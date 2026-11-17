BAN = [8.9, 10.2, 6.2, 1.75, 4.0]
STAGE = dict(bowl=[7.7, 14.6, 1.5], banner=BAN)
PI = 3.14159
CROWD = [('wojak', 9.0, 17.6, PI), ('giga', 4.6, 19.6, PI), ('pepe', 6.4, 19.6, PI), ('bonk', 8.1, 19.6, PI), ('troll', 9.9, 19.6, PI), ('popcat', 11.5, 19.6, PI), ('chillguy', 13.2, 19.6, PI)]
def cu(i, side=1, dist=1.0, fz=-1, look=0.66, h0=0.95, fov=(30, 27)):
    # thighs-up framing from the person's own height; fz=-1: camera on the -z side (person faces -z), +1: +z side
    return ("(k,cam)=>{const e=(window.__show||[])[%d]; const Hh=2.15*Math.pow(e.h,0.85); const s=%s, f=%s, x=e.x, z=e.z;"
            "return __dir.dolly([x+0.42*%s*Hh*s,%s*Hh,z+f*2.0*%s*Hh],[x+0.34*%s*Hh*s,0.93*Hh,z+f*1.7*%s*Hh],[x-0.08*Hh*s,%s*Hh,z],[x-0.08*Hh*s,%s*Hh,z],%s,%s)(k,cam);}"
            % (i, side, fz, dist, h0, dist, dist, dist, look, look + 0.02, fov[0], fov[1]))
S = {
 'slip': dict(arena='parking', T=2.6, people=[('whale', 10.0, 13.6, -0.4)], props=dict(STAGE, slip=[0.55, 'WOJAK']),
              cam="D.dolly([7.7,4.0,19.8],[7.7,4.0,19.0],[7.7,3.85,14.6],[7.7,3.85,14.6],34,33)"),
 'host': dict(arena='parking', T=8.0, people=[('whale', 10.0, 13.6, -0.4)], props=STAGE,
              cam="D.dolly([8.9,4.2,26.5],[9.3,3.8,22.8],[8.9,2.9,13],[9.4,3.1,13.4],37,34)",
              gests=[(0, 'talk', 0.3, 7.5, 0.8), (0, 'present', 0.9, 1.6, 1.0), (0, 'wide', 3.6, 1.6, 0.8), (0, 'present', 5.8, 1.6, 0.9)]),
 'crowd': dict(arena='parking', T=5.0, people=CROWD, props=STAGE,
               cam="D.dolly([9,3.1,11.0],[9,3.0,11.8],[9,1.7,19],[9,1.7,19],42,40)",
               cues=[(0.25, 0, 'lose')],
               moves="".join(f"window.MOVE({i},1.7,0.45,0,1.9,0.45);" for i in range(1, 7)),
               gests=[(0, 'shake', 2.6, 1.6, 0.8)]),
 'wojak': dict(arena='parking', T=6.0, people=CROWD, props=STAGE, cam=cu(0, side=1, dist=1.0, fz=-1),
               cues=[(0.25, 0, 'lose'), (3.3, 0, 'lose')], gests=[(0, 'sob', 0.6, 2.4, 1.0), (0, 'shake', 4.2, 1.5, 0.7)]),
 'pepe': dict(arena='parking', T=6.5, people=[CROWD[0]] + [p for p in CROWD[1:]], props=STAGE, cam=cu(2, side=-1, dist=1.35, fz=-1),
              gests=[(2, 'raise', 0.6, 2.4, 1.0), (2, 'talk', 0.6, 1.4, 0.6), (2, 'point', 3.6, 2.6, 1.0)]),
 'talk': dict(arena='penthouse', T=8.0, people=[('popcat', 7.9, 16, 0.45), ('wojak', 10.1, 16, -0.45)],
              cam="D.dolly([9,2.6,23.5],[9,2.4,21.8],[9,1.5,16],[9,1.5,16],34,32)",
              gests=[(0, 'talk', 0.3, 2.2, 1.0), (0, 'present', 0.6, 1.4, 1.0), (1, 'lookdown', 2.6, 1.6, 0.8), (0, 'wide', 4.6, 1.8, 1.0), (0, 'talk', 4.6, 1.8, 1.0)], cues=[(2.9, 1, 'lose')]),
 'standoff': dict(arena='parking', T=7.0, people=[('wojak', 7.4, 16.6, PI / 2), ('giga', 10.6, 16.6, -PI / 2)],
                  cam="D.dolly([9,1.9,24.5],[9,1.9,23.4],[9,1.7,16.6],[9,1.7,16.6],32,32)",
                  cues=[(0.9, 1, 'emote'), (3.0, 1, 'walk')], moves="window.MOVE(1,3.0,3.6,7.5,0.4,0,PI_2);".replace('PI_2', str(PI / 2)),
                  gests=[(1, 'tilt', 2.2, 0.9, 0.8), (0, 'sob', 3.2, 3.2, 0.9)]),
}
S.update({
 'intro': dict(arena='parking', T=8.0, people=[], cam=None, hud=True, me_name='WOJAK', opp='EVERYONE ELSE', frames=170),
 'fightA': dict(arena='parking', T=8.0, people=[], cam="D.follow(e=>e.card==='bonk'&&e.team===0,[3.4,2.4,3.0],[0,1.0,-0.6],38)",
                js=[(0.1, "D.drop(b,0,'bonk',9,18.2); D.drop(b,1,'troll',9,13.6);")]),
 'fightB': dict(arena='parking', T=8.0, people=[], cam="D.follow(e=>e.card==='whale'&&e.team===0,[-3.8,2.8,3.4],[0,1.2,-0.8],40)",
                js=[(0.1, "D.drop(b,0,'whale',8.4,18.4); D.drop(b,1,'popcat',8.0,13.4); D.drop(b,1,'chillguy',10.2,13.0);")]),
 'victory': dict(arena='parking', T=9.0, people=[], cam=None, hud=True, me_name='WOJAK', opp='EVERYONE ELSE', frames=380,
                 js=[(0.2, "D.drop(b,0,'wojak',9,21);"), (1.0, "m.finish({winner:0, why:'hq'});")]),
})
# --- v2 battle shots: a smoothed side-on two-shot that tracks the fighters' midpoint (both in frame, eye level)
def duo(cards, side=1, dist=6.2, h=1.7, look=1.05, fov=44, lead=0.0):
    return ("(()=>{let mx=null,mz=null; return (k,cam,b)=>{const es=[...b.ents.values()].filter(e=>e.kind==='unit'&&%s.includes(e.card)&&!e.dead);"
            "if(es.length){const x=es.reduce((s,e)=>s+e.x,0)/es.length, z=es.reduce((s,e)=>s+e.z,0)/es.length; mx=mx==null?x:mx+(x-mx)*0.08; mz=mz==null?z:mz+(z-mz)*0.08;}"
            "if(mx==null) return false; cam.fov=%s; cam.position.set(mx+%s*%s, %s, mz+%s); cam.lookAt(mx, %s, mz+%s);}})()"
            % (json.dumps(cards), fov, side, dist, h, lead, look, lead))
import json
S.update({
 'clashA': dict(arena='parking', T=8.0, people=[], cam=duo(['bonk', 'troll', 'chillguy']),
                js=[(0.1, "D.drop(b,0,'bonk',8.6,19.0); D.drop(b,1,'troll',8.8,13.2); D.drop(b,0,'chillguy',9.6,19.6);")]),
 'clashB': dict(arena='parking', T=8.0, people=[], cam=duo(['whale', 'popcat', 'pepe'], side=-1),
                js=[(0.1, "D.drop(b,0,'whale',9.2,19.0); D.drop(b,1,'popcat',9.0,13.2); D.drop(b,1,'pepe',8.2,12.6);")]),
 'standoff2': dict(arena='parking', T=7.0, people=[('wojak', 8.0, 17.4, PI / 2), ('giga', 10.0, 17.4, -PI / 2)],
                   cam="D.dolly([9,1.75,24.0],[9,1.75,23.0],[9,1.25,17.4],[9,1.25,17.4],30,30)",
                   cues=[(0.9, 1, 'emote'), (3.0, 1, 'walk')], moves="window.MOVE(1,3.0,3.4,6.5,0.3,0,%s);" % (PI / 2),
                   gests=[(1, 'tilt', 2.2, 0.9, 0.8), (0, 'sob', 3.2, 3.2, 0.9)]),
})
# --- v3: 1v1 on the left lane bridge, elevated 3/4 broadcast camera (cannot collide), wider standoff
def bcast(cards, dx=3.4, h=3.3, dz=4.6, look=0.85, fov=40):
    return ("(()=>{let mx=null,mz=null; return (k,cam,b)=>{const es=[...b.ents.values()].filter(e=>e.kind==='unit'&&%s.includes(e.card));"
            "if(es.length){const x=es.reduce((s,e)=>s+e.x,0)/es.length, z=es.reduce((s,e)=>s+e.z,0)/es.length; mx=mx==null?x:mx+(x-mx)*0.06; mz=mz==null?z:mz+(z-mz)*0.06;}"
            "if(mx==null) return false; cam.fov=%s; cam.position.set(mx+%s, %s, mz+%s); cam.lookAt(mx, %s, mz);}})()" % (json.dumps(cards), fov, dx, h, dz, look))
S.update({
 'clashA': dict(arena='parking', T=8.0, people=[], cam=bcast(['bonk', 'troll']), js=[(0.1, "D.drop(b,0,'bonk',3.6,19.4); D.drop(b,1,'troll',3.6,12.8);")]),
 'clashB': dict(arena='parking', T=8.0, people=[], cam=bcast(['whale', 'popcat'], dx=-3.4), js=[(0.1, "D.drop(b,0,'whale',14.4,19.4); D.drop(b,1,'popcat',14.4,12.8);")]),
 'standoff2': dict(arena='parking', T=7.0, people=[('wojak', 8.0, 17.4, PI / 2), ('giga', 10.0, 17.4, -PI / 2)],
                   cam="D.dolly([9,1.45,23.6],[9,1.45,22.9],[9,1.15,17.4],[9,1.15,17.4],50,50)",
                   cues=[(0.9, 1, 'emote'), (3.0, 1, 'walk')], moves="window.MOVE(1,3.0,3.4,6.5,0.3,0,%s);" % (PI / 2),
                   gests=[(1, 'tilt', 2.2, 0.9, 0.8), (0, 'sob', 3.2, 3.2, 0.9)]),
})
S['clashB'] = dict(arena='parking', T=8.0, people=[], cam=bcast(['whale', 'popcat'], dx=-6.0, h=5.2, dz=7.8, look=1.2, fov=40),
                   js=[(0.1, "D.drop(b,0,'whale',14.4,19.4); D.drop(b,1,'popcat',14.4,12.8);")])
