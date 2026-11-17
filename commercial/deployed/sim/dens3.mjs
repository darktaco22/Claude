import fs from 'fs';
import {runMatch, rng} from './play.mjs';
const rows=[];
for (let seed=1; seed<=30000; seed++){
  const r=rng(seed*4099);
  const plan={seed, skill0:+(0.8+r()*0.2).toFixed(2), skill1:+(0.1+r()*0.35).toFixed(2)};
  const {b,log,stat,air}=runMatch(plan);
  if (b.winner!==0) continue;
  const th=log.filter(l=>l.what==='thumb'), d=log.filter(l=>l.what==='tower_down');
  rows.push({seed,plan,mean:stat.tot/stat.n,ge6:stat.ge6/stat.n,ge7:stat.ge7,maxSide:stat.maxSide,maxTot:stat.maxTot,dups:th.filter(t=>t.dup).length,plays:th.length,end:b.t,ourDown:d.filter(x=>x.team===0).length,theirDown:d.filter(x=>x.team===1).length,first:(d.find(x=>x.team===0)||{}).t});
}
rows.sort((a,b)=>a.mean-b.mean);
console.log(rows.length);
for (const r of rows.slice(0,15)) console.log(r.seed,r.plan.skill0,r.plan.skill1,'mean',r.mean.toFixed(2),'ge6',r.ge6.toFixed(2),'maxSide',r.maxSide,'maxTot',r.maxTot,'dups',r.dups,'plays',r.plays,'end',r.end.toFixed(0),'down',r.ourDown,r.theirDown,r.first);
fs.writeFileSync('/root/dep_work/wins4.json',JSON.stringify(rows));
