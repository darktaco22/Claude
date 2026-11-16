const {chromium}=require('playwright');
(async()=>{
const b=await chromium.launch();
const c=await b.newContext({viewport:{width:430,height:932},deviceScaleFactor:1,isMobile:true,hasTouch:true,storageState:'state.json',recordVideo:{dir:'vid1',size:{width:430,height:932}}});
const p=await c.newPage();
let started=false,done=false;
p.on('websocket',w=>w.on('framereceived',f=>{const s=String(f.payload);if(s.startsWith('{"t":"start"')){started=true;console.log('START',s.slice(0,200));}if(s.startsWith('{"t":"result"')){done=true;console.log('RESULT',s.slice(0,200));}}));
await p.goto('https://memeroyale.imaginestudio.fun/',{waitUntil:'networkidle',timeout:60000});
await p.waitForTimeout(2500);
await p.touchscreen.tap(215,845);await p.waitForTimeout(2500);
await p.touchscreen.tap(215,781);
const cards=[137,219,298,374];
while(!started)await p.waitForTimeout(500);
await p.waitForTimeout(9000);
let n=0;const t0=Date.now();
while(!done&&Date.now()-t0<230000){
  const x=cards[n%4],tx=80+Math.floor(Math.random()*270),ty=500+Math.floor(Math.random()*190);
  await p.mouse.move(x,840);await p.mouse.down();await p.mouse.move((x+tx)/2,(840+ty)/2,{steps:4});await p.mouse.move(tx,ty,{steps:4});await p.mouse.up();
  console.log('drag',n,Math.round((Date.now()-t0)/1000),tx,ty);n++;
  await p.waitForTimeout(5000+Math.random()*3000);
}
await p.waitForTimeout(6000);
await c.storageState({path:'state.json'});
await c.close();await b.close();console.log('END');})();
