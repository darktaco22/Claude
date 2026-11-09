// Capture the game's own battle HUD (its DOM: opponent panel, timer, Ws, card tray with the real card faces and COPIUM bar)
// as transparent PNGs, one per video frame, driven by hud.json from build_hud.py.
// node hud_capture.js hud.json OUT_DIR [ONLY=1,2,3]
const {chromium}=require('playwright'); const fs=require('fs');
const [SPEC,OUT]=process.argv.slice(2); const S=JSON.parse(fs.readFileSync(SPEC)); fs.mkdirSync(OUT,{recursive:true});
const ONLY=(process.env.ONLY||'').split(',').filter(Boolean).map(Number);
(async()=>{
const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader']});
const ctx=await b.newContext({viewport:{width:720,height:1280},storageState:'state.json'});
await ctx.addInitScript(()=>{try{localStorage.setItem('memeroyale.gfx','low')}catch{}});
const p=await ctx.newPage(); p.on('pageerror',e=>console.log('PAGEERR',e.message.slice(0,200)));
await p.goto('https://memeroyale.imaginestudio.fun/',{waitUntil:'load',timeout:90000});
await p.waitForFunction(()=>window.__game?.arena,null,{timeout:120000}); await p.waitForTimeout(4000);
await p.mouse.click(360,1180); await p.waitForTimeout(3000);
await p.evaluate(()=>{const g=window.__game; g.stage._render=g.stage.render; g.stage.render=()=>{}; g.battleOffline();});
await p.waitForFunction(()=>window.__game.match?.hud,null,{timeout:180000});
await p.waitForTimeout(6000);   // the opening (names, FIGHT!) plays out
await p.evaluate((opp)=>{
  const g=window.__game, M=g.match; M.frame=()=>{}; M.bot=null;
  if(M.hud.opp) M.hud.opp=opp;
  const n=document.querySelector('.hud-top .opp .name'); if(n) n.textContent=opp.name;
  const tr=document.querySelector('.hud-top .opp-tr .num'); if(tr) tr.textContent=String(opp.clout);
  const st=document.createElement('style'); st.textContent='html,body{background:transparent!important} #gl,#ov{display:none!important} .toast,.emotes,.keys{display:none!important} *{transition:none!important;animation:none!important}';
  document.head.append(st);
},S.opp);
const frames=Object.keys(S.frames).map(Number).sort((a,b)=>a-b);
let n=0;
for(const f of frames){
  if(ONLY.length&&!ONLY.includes(f)) continue;
  const st=S.frames[f];
  await p.evaluate((st)=>{
    const M=window.__game.match, B=M.b;
    B.hands[0]=st.hand.slice(); B.queues[0][0]=st.next; B.copium[0]=st.cop; B.clock=st.t; B.ws=[0,0]; B.phase='play'; B.overdose=false;
    M.hud.update(); M.hud.refreshHand?.();
    for(const sl of M.hud.slots){ const c=sl.firstChild; if(c) c.classList.remove('sel','drag','poor'); }
    for(let i=0;i<4;i++){ const c=M.hud.slots[i].firstChild; if(c) c.classList.toggle('poor', st.costs[i]>st.cop); }
    M.hud.slots.forEach((sl,i)=>{ sl.style.visibility = st.gone===i ? 'hidden' : ''; });
  },st);
  await p.screenshot({path:`${OUT}/h_${String(f).padStart(4,'0')}.png`,omitBackground:true});
  if(++n%60===0) console.log('HUD',f);
}
console.log('HUD-DONE',n);
await b.close();})();
