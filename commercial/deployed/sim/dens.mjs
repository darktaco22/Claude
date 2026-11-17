import {runMatch, rng} from './play.mjs';
const rows=[];
for (let seed=1; seed<=1500; seed++){
  const r=rng(seed*4099);
  const plan={seed, skill0:+(0.8+r()*0.2).toFixed(2), skill1:+(0.1+r()*0.35).toFixed(2)};
  const {b,log,stat}=runMatch(plan);
  rows.push({seed,win:b.winner===0,end:b.t,mean:stat.tot/stat.n,maxSide:stat.maxSide,maxTot:stat.maxTot,ge6:stat.ge6/stat.n,plays:log.filter(l=>l.what==='thumb').length});
}
const w=rows.filter(r=>r.win);
const q=(a,p)=>a.sort((x,y)=>x-y)[Math.floor(a.length*p)];
for (const [n,s] of [['all',rows],['wins',w]]) console.log(n,s.length,'mean',q(s.map(r=>r.mean),0.1).toFixed(2),q(s.map(r=>r.mean),0.5).toFixed(2),'maxSide',q(s.map(r=>r.maxSide),0.1),q(s.map(r=>r.maxSide),0.5),'maxTot',q(s.map(r=>r.maxTot),0.1),q(s.map(r=>r.maxTot),0.5),'ge6',q(s.map(r=>r.ge6),0.1).toFixed(3),q(s.map(r=>r.ge6),0.5).toFixed(3),'plays',q(s.map(r=>r.plays),0.1),q(s.map(r=>r.plays),0.5),'end',q(s.map(r=>r.end),0.5).toFixed(0));
