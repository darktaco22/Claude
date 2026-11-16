import {CARDS} from '/home/user/Claude/meme-royale-research/client_src/data.js';
const o={};for(const [k,c] of Object.entries(CARDS)){ if(c.unit) o[k]=c.unit.r; }
console.log(JSON.stringify(o));
