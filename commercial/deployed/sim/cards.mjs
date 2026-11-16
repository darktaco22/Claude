import {CARDS} from '/home/user/Claude/meme-royale-research/client_src/data.js';
const out=[];
for(const [k,c] of Object.entries(CARDS)){ if(c.type==='unit'&&!(c.unit.n>1)&&!c.unit.deathSpawn) out.push(k+':'+c.cost); }
console.log(out.join(' '));
