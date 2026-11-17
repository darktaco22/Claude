import {runMatch, rng} from './play.mjs';
import {CARDS} from '/home/user/Claude/meme-royale-research/client_src/data.js';
const single=Object.entries(CARDS).filter(([k,c])=>c.type==='unit'&&!(c.unit.n>1)&&!c.unit.deathSpawn).map(([k,c])=>[k,c.cost,c.unit.hp||c.unit.max,c.unit.dps||c.unit.dmg]);
console.log(single.map(x=>x.join(':')).join(' '));
const decks={
 base:['troll','dope','bonk','neet','zcat','apu','farter','popcat'],
 squishy:['troll','dope','bonk','zcat','apu','farter','popcat','pudgy'],
};
for (const [name,deck1] of Object.entries(decks)){
  const rows=[];
  for (let seed=1; seed<=400; seed++){
    const r=rng(seed*4099);
    const plan={seed, deck1, skill0:+(0.8+r()*0.2).toFixed(2), skill1:+(0.1+r()*0.35).toFixed(2)};
    const {b,stat}=runMatch(plan);
    rows.push({win:b.winner===0,mean:stat.tot/stat.n,ge6:stat.ge6/stat.n,max:stat.maxTot});
  }
  const m=a=>a.reduce((x,y)=>x+y,0)/a.length;
  console.log(name,'win',rows.filter(r=>r.win).length,'mean',m(rows.map(r=>r.mean)).toFixed(2),'ge6',m(rows.map(r=>r.ge6)).toFixed(3),'max',m(rows.map(r=>r.max)).toFixed(1));
}
