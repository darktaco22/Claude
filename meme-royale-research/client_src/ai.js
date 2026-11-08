// MEME ROYALE — the opponent. Thinks a few times a second: defends what crosses into its half with a fitting counter,
// builds a push behind a tank when it has the copium, spends spells on clusters or to finish a tower.
// skill 0..1 scales its reaction time, how well it places and how patient it is.
import {CARDS} from './data.js';
import {ARENA} from './sim.js';

const ROLE = {
  useless: {swarm: 1, melee: 1, antiTank: 0.8}, troll: {melee: 1, cheap: 1}, chillguy: {melee: 1, tank: 0.5}, jeanphil: {ranged: 1},
  lmao: {ranged: 1, splash: 1}, ket: {melee: 1}, zcat: {melee: 1, antiTank: 0.6, fast: 1}, cupsey: {ranged: 1, support: 1},
  cate: {melee: 1}, triplet: {melee: 1, swarm: 0.6}, baton: {win: 1, fast: 1}, chillhouse: {win: 1, tank: 1}, mensa: {antiTank: 1.2, ranged: 0.5},
  mitch: {melee: 1, antiTank: 1}, alon: {ranged: 1, splash: 0.6}, whale: {win: 1, tank: 1.5, splash: 0.6}, neet: {melee: 1, tank: 0.6, splash: 0.6},
  fud: {spell: 1, splash: 1}, pump: {buff: 1}, rug: {spell: 1, splash: 1},
  airdrop: {spell: 1, splash: 1.2}, coldwallet: {freeze: 1}, liquidation: {spell: 1, splash: 1}, godcandle: {spell: 1, splash: 0.6}, banhammer: {spell: 1, swarm: 1},
  shillturret: {building: 1, antiTank: 1.2, defense: 1}, miningrig: {econ: 1},
  firesale: {melee: 1, splash: 0.8, swarm: 0.4, cheap: 1}, uselessarmy: {melee: 1, swarm: 1.5, antiTank: 1.5},
  downvotes: {spell: 1, splash: 1.2}, margincall: {spell: 1, splash: 0.4}, gasfees: {spell: 1, splash: 1}, hopium: {heal: 1}, deadcoins: {siege: 1},
  baglauncher: {building: 1, defense: 1, antiTank: 0.5}, honeypot: {building: 1, defense: 1, antiTank: 1.2},
  mememint: {building: 1, defense: 1, antiTank: 0.6}, trollfarm: {spawner: 1},
  bonk: {melee: 1}, dope: {melee: 1, cheap: 1, antiTank: 0.4}, swordcat: {melee: 1, splash: 0.5}, popcat: {melee: 1, splash: 1},
  wojak: {melee: 1}, pnut: {melee: 0.8, splash: 0.6, antiTank: 0.4}, pepe: {ranged: 1, splash: 0.6}, moodeng: {melee: 1, tank: 1},
  giga: {melee: 1, tank: 1.2, antiTank: 0.8}, npcwojak: {win: 1, swarm: 0.4}, fart: {spell: 1, splash: 1},
  thisisfine: {melee: 1, splash: 0.6}, nyancat: {win: 1},
  floki: {melee: 1, antiTank: 0.5}, toshi: {melee: 1, antiTank: 0.6, fast: 1}, slerf: {melee: 1, tank: 1.3, splash: 0.8}, michi: {ranged: 1}, pippin: {ranged: 1, support: 1},
  pudgy: {melee: 1, tank: 0.3}, bome: {ranged: 1, splash: 0.3}, apu: {ranged: 0.6, support: 1}, walter: {melee: 1, splash: 0.4, fast: 1}, goat: {win: 1, tank: 0.6, antiTank: 0.5}, farter: {ranged: 0.5, splash: 1},
  lasereyes: {building: 1, defense: 1, antiTank: 1.6}, bubblemachine: {building: 1, defense: 1, antiTank: 0.3, splash: 1}, vestingvault: {building: 1, defense: 1, antiTank: 0.8},
  sniperbot: {building: 1, xbow: 1}, tokenburner: {spawner: 1}, backdoor: {siege: 1},
  hardfork: {buff: 1}, diamondhands: {buff: 1}, liquiditydrain: {spell: 1, splash: 0.6}, marketcrash: {spell: 1, splash: 0.8}, panicsell: {spell: 1, splash: 0.5},
};
// what an area spell is worth against a cluster (damage it deals per target, for the cluster test)
const SPELL_DMG = id => { const S = CARDS[id].spell; return (S.dmg || 0) * (S.waves || 1) || (S.dps ? S.dps * S.dur * 0.5 : 0); };

export class Bot {
  constructor(battle, team = 1, {skill = 0.5} = {}) {
    this.b = battle; this.team = team; this.skill = skill;
    this.wait = 1.5 + (1 - skill) * 1.5;           // a first beat before acting
    this.pushLane = Math.random() < 0.5 ? 0 : 1;
    this.patience = 7.5 + Math.random() * 2;       // copium it saves before opening a push
    this.lastPlay = -9;
  }
  get me() { return this.team; }
  fwd(z) { return this.team === 1 ? z : ARENA.h - z; }          // distance from my back line
  toMine(fz) { return this.team === 1 ? fz : ARENA.h - fz; }    // my-side-relative z -> world z
  hand() { return this.b.hands[this.team].map((id, slot) => ({id, slot, c: CARDS[id]})); }

  update(dt) {
    const b = this.b; if (b.over) return;
    this.wait -= dt; if (this.wait > 0) return;
    this.wait = 0.35 + (1 - this.skill) * 0.75 + Math.random() * 0.3;
    // a weaker bot sometimes just doesn't notice (early leagues should be winnable while you learn)
    if (Math.random() > 0.5 + this.skill * 0.6 && this.b.copium[this.team] < 9.5) return;
    this.think();
  }
  play(card, x, z) {
    const b = this.b, slot = b.hands[this.team].indexOf(card); if (slot < 0) return false;
    // a sloppier bot places less precisely
    const j = (1 - this.skill) * 0.9;
    x += (Math.random() - 0.5) * j; z += (Math.random() - 0.5) * j;
    x = Math.floor(Math.min(17.5, Math.max(0.5, x))) + 0.5; z = Math.floor(Math.min(31.5, Math.max(0.5, z))) + 0.5;
    if (CARDS[card].type !== 'spell') {
      // walk it back into a legal tile if needed
      for (let k = 0; k < 8 && b.canPlace(this.team, card, x, z); k++) z += this.team === 1 ? -1 : 1;
      if (b.canPlace(this.team, card, x, z)) { for (let k = 0; k < 6 && b.canPlace(this.team, card, x, z); k++) x += x < 9 ? 1 : -1; }
    }
    const ok = b.play(this.team, slot, x, z);
    if (ok) { this.lastPlay = b.t; this.wait += 0.5 + Math.random() * 0.6 * (1 - this.skill); }
    return ok;
  }

  think() {
    const b = this.b, me = this.team, cop = b.copium[me], hand = this.hand().filter(h => h.c.cost <= cop);
    const foes = b.unitsOf(1 - me).filter(u => u.state !== 'deploy' || true);
    const mine = b.unitsOf(me);
    // ---- threats: enemy units in (or about to cross into) my half, grouped by lane
    const threats = [[], []];
    for (const u of foes) { const f = this.fwd(u.z); if (f < 21) threats[u.x < 9 ? 0 : 1].push(u); }
    const value = us => us.reduce((s, u) => s + CARDS[u.card].cost / (CARDS[u.card].unit.n || 1) * (u.hp / u.max), 0);
    const tv = threats.map(value);
    const lane = tv[0] >= tv[1] ? 0 : 1, threat = threats[lane];
    const defenders = mine.filter(u => this.fwd(u.z) < 18 && (u.x < 9 ? 0 : 1) === lane);
    const defValue = value(defenders);

    // ---- finish a low tower with a spell
    for (const t of b.towers[1 - me]) if (!t.dead) for (const h of hand) if (h.c.type === 'spell' && h.c.spell.dmg && !h.c.spell.roll && h.c.spell.dmg * h.c.spell.tower >= t.hp && Math.random() < 0.5 + this.skill * 0.5) return this.play(h.id, t.x, t.z);
    // a building to pull a tank (or chargers) off my tower: dropped in the middle, a few tiles in front of my towers
    const tankIn = foes.find(u => (u.bOnly || u.hp > 1300) && this.fwd(u.z) < 20);
    const turret = hand.find(h => ROLE[h.id].defense);
    if (tankIn && turret && !b.unitsOf(me).some(u => u.card === turret.id)) return this.play(turret.id, 9, this.toMine(10.5));
    // freeze a big enemy push right at my tower, or the defenders when my own push hits theirs
    const cold = hand.find(h => h.id === 'coldwallet');
    if (cold) { const best = this.cluster(foes.filter(u => this.fwd(u.z) < 13), cold.c.spell.r); if (best && best.value >= 6) return this.play('coldwallet', best.x, best.z); }
    // the mining rig or a troop hut: when nothing is coming and I have spare copium, behind my towers (a hut on my push lane)
    const rig = hand.find(h => ROLE[h.id].econ || ROLE[h.id].spawner);
    if (rig && cop >= 8.5 && !foes.some(u => this.fwd(u.z) < 22) && ![...b.ents.values()].some(e => e.kind === 'bld' && e.team === me && e.card === rig.id))
      return this.play(rig.id, ROLE[rig.id].spawner ? (this.pushLane ? 11.5 : 6.5) : 6.5, this.toMine(ROLE[rig.id].spawner ? 4.5 : 3.5));
    // SNIPER BOT: dug in behind the river on my push lane, when nothing is coming
    const xb = hand.find(h => ROLE[h.id].xbow);
    if (xb && cop >= 7.5 && !foes.some(u => this.fwd(u.z) < 18) && ![...b.ents.values()].some(e => e.kind === 'bld' && e.team === me && e.card === xb.id)) return this.play(xb.id, ARENA.bridges[this.pushLane], this.toMine(13.5));
    // HOPIUM on my hurt troops when there are a few of them together
    const hope = hand.find(h => ROLE[h.id].heal);
    if (hope) { const hurt = mine.filter(u => u.state !== 'deploy' && u.max - u.hp > 150); const c = this.cluster(hurt, hope.c.spell.r, u => (u.max - u.hp) / 300); if (c && c.value >= 3) return this.play(hope.id, c.x, c.z); }
    // DEAD COINS on the weaker enemy tower when I can afford a push behind it
    const grave = hand.find(h => ROLE[h.id].siege);
    if (grave && cop >= 8) { const tL = b.towers[1 - me], l = tL[0].dead ? 1 : tL[1].dead ? 0 : tL[0].hp <= tL[1].hp ? 0 : 1, T = tL[l].dead ? tL[2] : tL[l]; return this.play(grave.id, T.x, T.z + (me === 1 ? -1.5 : 1.5)); }

    // ---- spells on a cluster
    for (const h of hand) {
      if (h.c.type !== 'spell' || !SPELL_DMG(h.id) || h.id === 'coldwallet') continue;
      const best = this.cluster(foes, h.c.spell.r);
      const worth = h.id === 'godcandle' || h.id === 'margincall' ? 6 : h.id === 'rug' || h.id === 'liquidation' ? 5 : h.id === 'banhammer' ? 2.5 : 3.2;
      if (best && best.value >= worth * (1.3 - this.skill * 0.4)) {
        // lead moving targets a little (rug lands after a second)
        const lead = h.c.spell.delay || 0;
        return this.play(h.id, best.x + best.vx * lead, best.z + best.vz * lead);
      }
    }

    // ---- defend
    if (threat.length && tv[lane] > defValue * 0.8) {
      const pick = this.counter(threat, hand);
      if (pick) {
        const tower = b.towers[me][lane].dead ? b.towers[me][2] : b.towers[me][lane];
        const lead = threat.reduce((a, u) => this.fwd(u.z) < this.fwd(a.z) ? u : a);
        const ranged = (pick.c.unit?.range || 0) > 2;
        let x, z;
        if (ranged) { x = tower.x + (lane === 0 ? 1.5 : -1.5); z = this.toMine(this.fwd(tower.z) - 2.5); }
        else if (pick.c.type === 'spell') { x = lead.x; z = lead.z; }
        else {
          // drop between the threat and the tower, a bit toward the middle to drag it
          x = (lead.x + tower.x) / 2 + (lane === 0 ? 1.2 : -1.2) * this.skill;
          z = this.toMine(Math.min(this.fwd(lead.z) - 1.5, this.fwd(tower.z) + 3.5));
        }
        return this.play(pick.id, x, z);
      }
    }

    // ---- support my push once its tank is over the bridge
    const tank = mine.find(u => (u.bOnly || u.hp > 1300) && this.fwd(u.z) > 12);
    if (tank) {
      const sup = hand.filter(h => h.c.type === 'unit' && !h.c.unit.bOnly).sort((a, c) => (ROLE[c.id].ranged || 0) - (ROLE[a.id].ranged || 0))[0];
      if (sup && cop >= sup.c.cost + 1 && Math.random() < 0.6) return this.play(sup.id, tank.x + (Math.random() - 0.5) * 2, this.toMine(Math.min(this.fwd(tank.z) - 2, 13.5)));
      const pump = hand.find(h => ROLE[h.id].buff);
      const near = mine.filter(u => Math.hypot(u.x - tank.x, u.z - tank.z) < 3.5).length;
      if (pump && near >= 2 && this.fwd(tank.z) > 17) return this.play(pump.id, tank.x, tank.z);
    }

    // ---- open a push when I'm full enough
    if (cop >= Math.min(10, this.patience) || cop >= 9.6) {
      const tL = b.towers[1 - me];
      // aim at the weaker (or already open) lane
      const hp = l => tL[l].dead ? -1 : tL[l].hp / tL[l].max;
      this.pushLane = hp(0) < hp(1) ? 0 : hp(1) < hp(0) ? 1 : this.pushLane;
      const lx = ARENA.bridges[this.pushLane];
      const win = hand.filter(h => ROLE[h.id].win || ROLE[h.id].tank).sort((a, c) => c.c.cost - a.c.cost)[0];
      if (win) {
        const fast = ROLE[win.id].fast;
        return this.play(win.id, lx, this.toMine(fast ? 13.5 : 1.5));
      }
      // no tank in hand: cycle the cheapest unit at the back (keeps the rotation moving)
      const cheap = hand.filter(h => h.c.type === 'unit').sort((a, c) => a.c.cost - c.c.cost)[0];
      if (cheap && cop >= 9.6) return this.play(cheap.id, lx + (this.pushLane ? -1 : 1), this.toMine(2.5));
    }
  }

  counter(threat, hand) {
    const units = threat.length, hp = threat.reduce((s, u) => s + u.hp, 0), tanky = threat.some(u => u.hp > 1100), swarm = units >= 3 && hp / units < 450;
    // a flyer (PNUT) is only reached by shooters and spells: a melee answer would walk under it
    const flying = threat.some(u => u.air);
    let best = null, bs = -1;
    for (const h of hand) {
      const r = ROLE[h.id] || {}; if (r.buff || r.econ || r.freeze || r.heal || r.siege || r.spawner || r.xbow || r.win && !r.tank) continue;
      if (h.c.type === 'spell' && !swarm) continue;
      let s = 1;
      if (swarm) s += (r.splash || 0) * 3 + (r.swarm || 0);
      if (tanky) s += (r.antiTank || 0) * 3 + (r.swarm || 0) * 1.2;
      if (!tanky && !swarm) s += (r.melee || 0) + (r.ranged || 0) * 0.8;
      s -= h.c.cost * 0.25;                          // prefer cheap answers
      if (r.tank && !tanky) s -= 1;
      if (flying && h.c.type === 'unit') s += (h.c.unit.range || 0) > 2 ? 1.5 : -2;
      if (s > bs) { bs = s; best = h; }
    }
    return best;
  }

  // the best spot for an area of radius r over these units, and what it is worth (by default: the copium of what it covers)
  cluster(foes, r, worth = u => CARDS[u.card].cost / (CARDS[u.card].unit.n || 1)) {
    let best = null;
    for (const a of foes) {
      let v = 0, x = 0, z = 0, vx = 0, vz = 0, n = 0;
      for (const u of foes) if (Math.hypot(u.x - a.x, u.z - a.z) <= r * 0.85) { v += worth(u); x += u.x; z += u.z; vx += u.x - u.px; vz += u.z - u.pz; n++; }
      if (n && (!best || v > best.value)) best = {value: v, x: x / n, z: z / n, vx: vx / n * 30, vz: vz / n * 30};
    }
    return best;
  }
}
