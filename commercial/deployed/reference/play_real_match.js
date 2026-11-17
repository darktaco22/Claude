// Plays a real Meme Royale match against the real server bot: defence first (counter what crosses, near our towers so they help),
// then a push behind a tank when copium allows. Sends the same websocket 'play' messages the client sends.
const {chromium}=require('playwright');const fs=require('fs');
const COST={fud:2,lmao:4,jeanphil:3,rug:4,chillguy:3,ket:3,useless:2,troll:2};
const SPELL=new Set(['fud','rug']);
(async()=>{
const b=await chromium.launch();
const c=await b.newContext({viewport:{width:360,height:640},deviceScaleFactor:1,isMobile:true,hasTouch:true,storageState:'state.json'});
await c.addInitScript(()=>{const W=window.WebSocket;window.__socks=[];window.WebSocket=function(...a){const s=new W(...a);window.__socks.push(s);return s;};window.WebSocket.prototype=W.prototype;Object.assign(window.WebSocket,W);});
const p=await c.newPage();
const log=[];const L=(...a)=>{const s=a.join(' ');console.log(s);log.push(s);};
const ents=new Map();let hand=[],queue=[],cop=5,t=0,started=false,done=false,result=null,n=2,lastPlay=-9,ws=[0,0],towers={};
const stats={n:0,tot:0,max:0,ge6:0};
function onSnap(s){
  if(s.t==='start'){started=true;hand=s.mine.hand.slice();queue=s.mine.queue.slice();cop=s.mine.cop;for(const e of s.ents)towers[e.id]={team:e.team,x:e.x,z:e.z,type:e.type,hp:e.max,lane:e.lane};return;}
  if(s.t==='result'){done=true;result=s;return;}
  if(s.t!=='snap')return;
  t=s.bt??t;if(s.ws)ws=s.ws;
  if(s.me&&s.me.cop!==undefined)cop=s.me.cop;
  if(s.mine&&s.mine.hand){hand=s.mine.hand.slice();queue=s.mine.queue.slice();}
  for(const a of s.add||[]){if(a.kind==='unit')ents.set(a.id,{card:a.card,team:a.team,x:null,z:null,hp:a.max,max:a.max,state:'',r:a.r,range:a.range});}
  if(s.d&&s.d.unit)for(const row of s.d.unit){const e=ents.get(row[0]);if(!e)continue;let mask=row[1],k=2;for(let bit=0;bit<26;bit++){if(mask&(1<<bit)){const v=row[k++];if(bit===0)e.x=v;else if(bit===1)e.z=v;else if(bit===3)e.state=v;else if(bit===5)e.hp=v;}}}
  if(s.d&&s.d.tower)for(const row of s.d.tower){if(towers[row[0]])towers[row[0]].hp=row[1];}
  for(const ev of s.ev||[]){if(['tower_down','phase','end','w'].includes(ev.type))L('EV',JSON.stringify(ev).slice(0,160));if(ev.type==='die'||ev.type==='dead'){ents.delete(ev.id);} }
  for(const [id,e] of ents)if(e.hp<=0)ents.delete(id);
}
p.on('websocket',w=>{w.on('framereceived',f=>{let s;try{s=JSON.parse(String(f.payload));}catch{return;}onSnap(s);});});
await p.goto('https://memeroyale.imaginestudio.fun/',{waitUntil:'networkidle',timeout:60000});
await p.waitForTimeout(2500);await p.touchscreen.tap(180,590);await p.waitForTimeout(2500);await p.touchscreen.tap(180,540);
const w0=Date.now();while(!started&&Date.now()-w0<150000)await p.waitForTimeout(300);
L('started',started);
const send=async(slot,x,z)=>{const card=hand[slot];const msg=JSON.stringify({t:'play',slot,x,z,card,n:n++});await p.evaluate(m=>window.__socks[window.__socks.length-1].send(m),msg);
  L('PLAY',t.toFixed(1),card,x.toFixed(1),z.toFixed(1),'cop',cop.toFixed(1));hand[slot]=queue.shift();queue.push(card);cop-=COST[card];lastPlay=t;};
const lanes=()=>{const out=[[],[]];for(const e of ents.values())if(e.team===1&&e.z!=null&&e.z>12)out[e.x<9?0:1].push(e);return out;};
const mine=()=>[...ents.values()].filter(e=>e.team===0&&e.z!=null);
const enemy=()=>[...ents.values()].filter(e=>e.team===1&&e.z!=null);
await p.waitForTimeout(5500); // intro
const m0=Date.now();
while(!done&&Date.now()-m0<290000){
  await p.waitForTimeout(350);
  const us=[...ents.values()].filter(e=>e.z!=null&&e.hp>0&&e.state!=='dead');
  const a=us.filter(e=>e.team===0).length,bn=us.filter(e=>e.team===1).length;stats.n++;stats.tot+=a+bn;stats.max=Math.max(stats.max,a+bn);if(a+bn>=6)stats.ge6++;
  if(t-lastPlay<1.0)continue;
  const th=lanes();const tv=th.map(l=>l.reduce((s,e)=>s+e.hp,0));
  const lane=tv[0]>=tv[1]?0:1,threat=th[lane];
  const afford=hand.map((card,slot)=>({card,slot,cost:COST[card]})).filter(h=>h.cost<=cop);
  const defenders=mine().filter(e=>e.z>14&&(e.x<9?0:1)===lane);
  const dv=defenders.reduce((s,e)=>s+e.hp,0);
  const twr=lane===0?3.5:14.5;
  if(threat.length&&tv[lane]>dv*0.8){
    const lead=threat.reduce((x,y)=>y.z>x.z?y:x);
    const near=threat.filter(e=>Math.hypot(e.x-lead.x,e.z-lead.z)<2.6);
    const sp=afford.find(h=>h.card==='fud');
    if(near.length>=2&&sp){await send(sp.slot,lead.x,lead.z+0.8);continue;}
    const rg=afford.find(h=>h.card==='rug');
    if(near.length>=3&&rg){await send(rg.slot,lead.x,lead.z+1.5);continue;}
    const order=tv[lane]>1800?['chillguy','ket','troll','jeanphil','lmao','useless']:['ket','troll','chillguy','jeanphil','useless','lmao'];
    let pick=null;for(const o of order){pick=afford.find(h=>h.card===o&&!SPELL.has(o));if(pick)break;}
    if(pick){const ranged=['lmao','jeanphil'].includes(pick.card);
      let x=Math.min(16.5,Math.max(1.5,ranged?twr+(lane?-1.2:1.2):lead.x)),z=ranged?27.0:Math.min(24.5,Math.max(19.5,lead.z+1.8));
      if(lead.z>22)z=Math.min(27,lead.z+1.2);
      await send(pick.slot,x,z);continue;}
  }
  // counter-push: our survivors are across and nothing is coming: support them, spend before copium overflows
  if(!threat.length){
    const adv=mine().filter(e=>e.z<20&&e.z>6&&e.hp>250);
    const sup=afford.find(h=>h.card==='lmao')||afford.find(h=>h.card==='jeanphil');
    if(adv.length&&sup&&cop>=4.5){const tk0=adv.reduce((x,y)=>y.z<x.z?y:x);await send(sup.slot,Math.min(16.5,Math.max(1.5,tk0.x)),Math.min(27,tk0.z+4.5));continue;}
  }
  // push: a tank in the lane of the weaker enemy tower, then support behind it
  if(!threat.length&&cop>=7.5){
    const tk=afford.find(h=>h.card==='chillguy')||afford.find(h=>h.card==='ket');
    const sup=afford.find(h=>h.card==='lmao');
    const tanks=mine().filter(e=>(e.card==='chillguy'||e.card==='ket')&&e.z<22&&e.z>8);
    if(tanks.length&&sup){const tk0=tanks[0];await send(sup.slot,Math.min(16.5,Math.max(1.5,tk0.x)),Math.min(27,tk0.z+4));continue;}
    if(tk){const e4=towers[4]?.hp??2600,e5=towers[5]?.hp??2600;const px=e4<=e5?3.5:14.5;await send(tk.slot,px,20.5);continue;}
  }
}
await p.waitForTimeout(3000);
L('RESULT',JSON.stringify(result&&{win:result.win,ws:result.ws,why:result.why}),'units mean',(stats.tot/Math.max(1,stats.n)).toFixed(2),'max',stats.max,'ge6',(stats.ge6/Math.max(1,stats.n)).toFixed(2));
fs.writeFileSync('ai_match.log',log.join('\n'));
await b.close();})();
