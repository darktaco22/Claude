// One match of Meme Royale with the game's own rules and its own Bot on BOTH sides (the Thumb plays like a competent
// player: defends a push with a counter, builds a push behind a tank). Each bot and the sim have their own random stream,
// so the match is repeatable. Injected on top: one illegal tap (the gag) and one airdrop dropped on our own side.
import {Battle} from '/home/user/Claude/meme-royale-research/client_src/sim.js';
import {Bot} from '/home/user/Claude/meme-royale-research/client_src/ai.js';

export function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
export const DECK0 = ['lmao', 'chillguy', 'cupsey', 'chillhouse', 'airdrop', 'ket', 'dope', 'pudgy'];
export const ORDER0 = ['lmao', 'ket', 'cupsey', 'dope', 'chillhouse', 'chillguy', 'pudgy', 'airdrop'];
export const DECK1 = ['troll', 'dope', 'bonk', 'neet', 'zcat', 'apu', 'farter', 'popcat'];

export function runMatch(plan, {record = false, stride = 3} = {}) {
  const rA = rng(plan.seed * 7 + 1), rB = rng(plan.seed * 13 + 2), rS = rng(plan.seed * 31 + 5), rG = rng(plan.seed * 17 + 3);
  Math.random = rS;
  const b = new Battle({decks: [plan.deck0 || DECK0, plan.deck1 || DECK1], seed: plan.seed});
  const order = plan.order0 || ORDER0; b.hands[0] = order.slice(0, 4); b.queues[0] = order.slice(4);
  Math.random = rA; const botA = new Bot(b, 0, {skill: plan.skill0});
  Math.random = rB; const botB = new Bot(b, 1, {skill: plan.skill1});
  const gagT = plan.gagT ?? 17 + rG() * 3, airT = plan.airT ?? 95 + rG() * 50, airX = +(2 + rG() * 14).toFixed(1), airZ = +(19 + rG() * 10).toFixed(1);
  let gag = false, air = false;
  const log = [], frames = [], seen = new Map(), stat = {n: 0, tot: 0, ge6: 0, ge7: 0, maxSide: 0, maxTot: 0};
  const origPlay = b.play.bind(b); let lastDup = false; const hq = [];
  b.play = (team, slot, x, z) => { if (team === 0) { const id = b.hands[0][slot]; lastDup = b.unitsOf(0).some(u => u.card === id); } const ok = origPlay(team, slot, x, z); if (team === 0 && ok) hq.push([b.hands[0].slice(), b.queues[0].slice()]); return ok; };
  let pendingGag = false;
  for (let i = 0; i < 30 * 200 && !b.over; i++) {
    const ev0 = b.events.length;
    Math.random = rA; botA.update(1 / 30);
    Math.random = rB; botB.update(1 / 30);
    Math.random = rS;
    if (!gag && b.t >= gagT) {                                     // the gag: a drag onto the enemy side
      const slot = Math.floor(rG() * 4); gag = true;
      log.push({t: +b.t.toFixed(2), what: 'illegal', card: b.hands[0][slot], x: 9, z: 8, why: 'enemy side', copium: +b.copium[0].toFixed(1)});
    }
    if (!air && b.t >= airT) {
      const slot = b.hands[0].indexOf('airdrop');
      if (slot >= 0 && !b.canPlay(0, slot, airX, airZ)) {
        air = true; pendingGag = true;
        b.play(0, slot, airX, airZ);
      }
    }
    b.step();
    for (const e of b.events.slice(ev0)) {
      if (['tower_down', 'phase'].includes(e.type)) log.push({t: +b.t.toFixed(2), what: e.type, ...Object.fromEntries(Object.entries(e).filter(([k, v]) => typeof v !== 'object' && k !== 't' && k !== 'type'))});
      if (e.type === 'play' && e.team === 0) {                      // the Thumb's plays (the bot's, and the gag): hand and queue as they were right after it
        const gagPlay = pendingGag && e.card === 'airdrop'; if (gagPlay) pendingGag = false;
        log.push({t: +e.t.toFixed(2), what: 'thumb', card: e.card, x: +e.x.toFixed(1), z: +e.z.toFixed(1), slot: e.slot, gag: gagPlay || undefined, dup: lastDup || undefined, copium: +b.copium[0].toFixed(1), ...(() => { const h = hq.shift() || [b.hands[0].slice(), b.queues[0].slice()]; return {hand: h[0], queue: h[1]}; })()});
      }
    }
    const u0 = b.unitsOf(0).length, u1 = b.unitsOf(1).length;
    if (i % 3 === 0 && b.t > 8) { stat.n++; stat.tot += u0 + u1; if (u0 + u1 >= 6) stat.ge6++; if (u0 + u1 >= 7) stat.ge7++; stat.maxSide = Math.max(stat.maxSide, u0, u1); stat.maxTot = Math.max(stat.maxTot, u0 + u1); }
    if (record && i % stride === 0) {
      const ents = [];
      for (const e of b.all) {
        if (e.kind === 'unit' || e.kind === 'tower' || e.kind === 'bld') ents.push([e.id, e.kind === 'unit' ? 'u' : e.kind === 'tower' ? 't' : 'b', e.card || e.type, e.team, +e.x.toFixed(2), +e.z.toFixed(2), +(e.face || 0).toFixed(2), e.moving ? 1 : 0, Math.round(e.hp), e.dead ? 1 : 0, e.state || '', +(e.y || 0).toFixed(2)]);
        if (!seen.has(e.id)) seen.set(e.id, {t0: b.t, kind: e.kind, card: e.card || e.type, team: e.team});
        const s = seen.get(e.id); s.t1 = b.t; s.hp = e.hp;
      }
      frames.push({t: +b.t.toFixed(2), cop: +b.copium[0].toFixed(1), cop1: +b.copium[1].toFixed(1), clock: +b.clock.toFixed(1), ws: b.ws.slice(), e: ents});
    }
  }
  return {b, log, frames, stat, air, gag};
}
