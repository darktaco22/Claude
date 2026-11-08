// One match: the sim, the opponent bot, the 3D views, the HUD, sound. Runs the fixed-step loop, turns sim events into
// effects and sound, shows the intro, the banners and the results.
import * as THREE from 'three';
import {Battle} from './sim.js';
import {NetBattle} from './net/netbattle.js';
import {Bot} from './ai.js';
import {CARDS, EMOTES, arenaById} from './data.js';
import {Hud} from './ui/hud.js';
import {Overlay} from './render/overlay.js';
import {CELL} from './render/fx.js';
import {audio, buzz} from './audio.js';
import {save} from './save.js';

const pan = x => (x - 9) / 9 * 0.55;
const MELEE_SFX = {useless: 'coin_jingle', ket: 'sticky_splat'};
// a sound that may not be there yet (the abilities' own): its stand-in, or nothing
const sfx = (id, alt) => audio.has(id) ? id : alt;
// a sound hook for what has none yet: plays if it's ever in the manifest, otherwise nothing
const hook = (id, x, vol = 0.7, gap = 0.1) => { if (audio.has(id)) audio.play(id, {pan: pan(x), vol, gap}); };
const V = new THREE.Vector3(), V2 = new THREE.Vector3(), V3 = new THREE.Vector3();

export class Match {
  // offline: a local Battle and a Bot; online (`start` from the server): the server's battle, mirrored so I'm at the bottom
  constructor(app, opp, start = null) {
    this.app = app; this.opp = opp; this.online = !!start;
    if (start) {
      this.b = new NetBattle(app.net.client, start); this.bot = null;
      this.b.onDeny = () => this.hud?.deny('The server said no');
      this.b.onOpp = m => this.hud?.toast(m.gone ? 'Your opponent left' : m.away ? 'Opponent reconnecting…' : 'Opponent is back');
      this.b.onEmote = (team, id) => this.hud?.emote(1, id);
      this.b.onSync = () => this.ruins();   // (the line came back: the battle again, maybe with towers down)
    } else {
      const deck = save.deck, levels = save.levels();
      this.b = new Battle({decks: [deck, opp.deck], levels: [levels, opp.levels], towerLvl: [save.towerLvl(), opp.towerLvl], seed: Date.now() & 0xffffffff});
      this.bot = new Bot(this.b, 1, {skill: opp.skill});
    }
    this.acc = 0; this.running = false; this.done = false; this.speed = 1;
    this.stats = {played: 0, dmgTowers: 0};
  }
  // progress: the loading screen's percent (src/ui/menus.js loading), told as the arena is set up
  async start(progress = () => {}) {
    const {stage, arena, units, fx, ui} = this.app;
    units.battle = this.b;
    arena.clearTowers(); units.clear(); fx.endBattle();
    this.arenaId = this.opp.matchArena || save.arena.id;   // offline: my arena; online: the server names it (on localhost: the one the hub shows)
    const themeP = arena.themeId === this.arenaId ? null : arena.applyTheme(this.arenaId);
    await units.preload([...this.b.hands[0], ...this.b.queues[0], ...this.b.hands[1], ...this.b.queues[1]]); progress(85);
    await arena.buildTowers(this.b, (T, s) => units.commander(T, s), (T, s) => units.guard(T, s)); progress(95);
    if (themeP) await Promise.race([themeP, new Promise(r => setTimeout(r, 6000))]);
    progress(100); await new Promise(r => setTimeout(r, 260));   // (100% is seen)
    ui.innerHTML = '';
    this.hud = new Hud(ui, {stage, arena, units, battle: this.b, opp: this.opp, onPlay: (slot, x, z) => this.playerPlay(slot, x, z)});
    this.hud.onEmote = id => { if (this.online) { this.b.emote(id); return; } if (Math.random() < 0.5) setTimeout(() => !this.b.over && this.hud.emote(1, EMOTES[Math.floor(Math.random() * EMOTES.length)]), 900 + Math.random() * 1200); };
    this.overlay = new Overlay(this.app.ov, stage, this.b, units);
    stage.battle(); this.hud.layout();
    audio.preload(['deploy_drop', 'deploy_spell', 'punch_light', 'punch_heavy', 'swing', 'tower_shot', 'tower_hit', 'unit_die', 'card_pick', 'card_deny', 'countdown_tick', 'battle_start', ...this.b.hands[0].map(id => 'bark_' + id),
      'shockwave', 'spin_slash', 'charge', 'teleport', 'surprise_hit', 'acorn_boom', 'magic_hit', 'fart_cast', 'fart_cloud', 'fire_start', 'rainbow',
      'berserk', 'snared', 'shield_break', 'mend', 'dig', 'surface', 'feared', 'zone_stink', 'zone_paperstorm', 'dash_toshi', 'charge_pudgy', 'charge_goat', 'boom_bubblemachine', 'boom_bome', 'atk_bubblemachine', 'atk_sniperbot', 'spawn_tokenburner', 'spawn_backdoor', 'spell_hardfork', 'spell_liquiditydrain', 'spell_marketcrash', 'spell_panicsell', 'spell_diamondhands']);   // (the abilities': missing ones are skipped)
    const T = arena.theme; audio.music(audio.has(T?.music) ? T.music : 'mus_battle'); audio.ambience(T?.amb);
    // the opening: the arena with its name, both names on their ribbons, the HUD sliding in, then FIGHT! (online: in what
    // is left of the server's hold, the battle frozen till then anyway)
    await this.hud.intro(arenaById(this.arenaId), this.opp.name, save.p.name, this.online ? (this.hold ?? 0) - performance.now() : 2700);
    if (this.done || this.gone) return;   // (left during the opening)
    this.fight();
    this.running = true; this.t0 = performance.now();
    if (!save.p.tut) { this.hud.tutorial(); if (this.online) save.act({a: 'tutDone'}); else { save.p.tut = true; save.write(); } }
  }
  // the genre has no countdown: the opening named both sides, so the clock runs from the first FIGHT!
  fight() {
    this.hud.banner(this.opp.friendly ? 'FRIENDLY!' : 'FIGHT!', document.body.classList.contains('desk') ? 'press 1-4, then click your side' : 'drag a card onto your side', '', 1600);
    audio.play('battle_start'); audio.play(audio.has('vo_fight') ? 'vo_fight' : 'vo_rumble'); buzz(30);
  }
  // towers that fell while this page did not see it (no tower_down came): the rubble at once, guard or NEET gone, no show
  ruins() {
    const {arena, units} = this.app;
    for (const side of this.b.towers) for (const t of side) {
      const T = t?.dead && arena.towerOf(t); if (!T || T.ruined) continue;
      if (t.type === 'hq') units.dropCommander(T); else units.dropGuard(T); arena.ruin(T, true);
    }
  }
  playerPlay(slot, x, z) {
    if (!this.running) return false;
    const ok = this.b.play(0, slot, x, z);
    if (ok) { this.stats.played++; this.hud.endTutorial(); }
    return ok;
  }
  frame(dt) {
    const {stage, arena, units, fx, blds} = this.app;
    if (this.running) {
      this.acc += Math.min(dt, 0.1) * this.speed;
      while (this.acc >= Battle.DT) {
        this.bot?.update(Battle.DT);
        this.b.step();
        this.events();
        this.acc -= Battle.DT;
      }
    }
    const alpha = this.running ? this.acc / Battle.DT : 1;
    arena.update(dt); units.update(dt, alpha); fx.syncProjectiles(this.b, units, arena, alpha, dt); fx.syncSpells(this.b, alpha, dt); fx.syncWeak(this.b, units); this.app.blds.update(this.b, dt, alpha);
    // beams
    let beam = false;
    for (const e of this.b.ents.values()) if (e.beamOn && (e.kind === 'unit' || e.kind === 'bld')) {
      const t = this.b.ents.get(e.beamOn); if (!t) continue;
      const st = e.beamT < 2 ? 0 : e.beamT < 4 ? 1 : 2, to = (t.air && units.bodyOf(t.id, 0.45, V3)) || V3.set(t.x, t.kind === 'tower' ? 2.2 : t.h * 0.6, t.z);
      if (e.kind === 'bld') {   // LASER EYES: one from each eye of the idol (its ball sits between them, across its aim)
        const c = blds.coilWorld(e.id, V2) || V2.set(e.x, e.h * 1.3, e.z), sx = Math.cos(e.aim || 0) * 0.14, sz = -Math.sin(e.aim || 0) * 0.14;
        fx.beam(V.set(c.x + sx, c.y, c.z + sz), to, st, 'eyes'); fx.beam(V.set(c.x - sx, c.y, c.z - sz), to, st, 'eyes');
      } else {
        const v = units.views.get(e.id); if (!v) continue;
        fx.beam(V.set(v.root.position.x + Math.sin(e.face) * 0.25, e.h * 1.5, v.root.position.z + Math.cos(e.face) * 0.25), to, st);
      }
      beam = true;
    }
    if (beam) audio.play('beam_loop', {gap: 2.6, vol: 0.6});
    fx.update(dt);
    this.hud?.update();
    if (this.running && !this.b.over && this.warned10 !== this.b.phase && this.b.timeLeft() <= 10.05) { this.warned10 = this.b.phase; this.hud.banner('10 SECONDS!', '', 'red', 1500); }
    stage.render(dt);
    this.overlay?.draw(dt);
  }
  events() {
    const {arena, units, fx, stage, blds} = this.app, B = this.b;
    // a card that reuses a character (FIRE SALE, USELESS ARMY) speaks with that character's voice
    const voice = id => CARDS[id]?.unit?.model || id;
    for (const e of B.events) {
      units.onEvent(e);
      switch (e.type) {
        case 'play': {
          const c = CARDS[e.card];
          audio.play(c.type === 'spell' ? 'deploy_spell' : 'deploy_drop', {pan: pan(e.x)});
          if (e.team === 1) this.overlay.float(e.x, 1.5, e.z, c.name, '#ff9aac', 0.85);
          if (c.type === 'unit') setTimeout(() => audio.play('bark_' + voice(e.card), {gap: 4, vol: e.team === 0 ? 0.9 : 0.6, pan: pan(e.x), spread: 0.02}), 350);
          break;
        }
        case 'hit': {
          fx.hit({x: e.x, y: 0, z: e.z}, e.heavy, e.card);
          // each meme hits with its own sound (atk_<id>), under a punch for weight
          const vo = voice(e.card);
          if (audio.has('atk_' + vo)) audio.play('atk_' + vo, {pan: pan(e.x), gap: 0.08, vol: 0.85});
          audio.play(MELEE_SFX[vo] || (e.heavy ? 'punch_heavy' : 'punch_light'), {pan: pan(e.x), gap: 0.03, vol: audio.has('atk_' + vo) ? 0.5 : 1});
          if (e.heavy && Math.random() < 0.15) audio.play('crowd_ooh', {gap: 3, vol: 0.5});
          if ((e.card === 'cate' || e.card === 'zcat') && Math.random() < 0.25) audio.play('cat_hiss', {pan: pan(e.x), gap: 1});
          if (e.card === 'chillhouse') audio.play('house_stomp', {pan: pan(e.x), gap: 0.3});
          break;
        }
        case 'attack': { const u = B.ents.get(e.id); if (u && !u.proj && !u.beam) setTimeout(() => audio.play('swing', {pan: pan(u.x), vol: 0.5, gap: 0.05}), Math.max(0, e.hitAt * 1000 - 120)); break; }
        case 'shoot': {
          const u = B.ents.get(e.id), x = pan(u?.x ?? 9); if (audio.has('atk_' + e.card)) audio.play('atk_' + e.card, {pan: x, gap: 0.12, vol: 0.75}); else audio.play(e.proj === 'rocket' ? 'rocket_launch' : 'throw', {pan: x, vol: 0.7, gap: 0.05});
          // PNUT: the acorn drops from where he's drawn to the ground under his target (a tower's or a building's: its near side)
          if (e.proj === 'acorn' && u) { const t = B.ents.get(u.target) || u, from = units.bodyOf(e.id, 0.4, V) || V.set(u.x, 3, u.z), d = Math.hypot(u.x - t.x, u.z - t.z) || 1, k = t.kind === 'tower' || t.kind === 'bld' ? t.r * 1.1 / d : 0;
            fx.acorn(from, k ? {x: t.x + (u.x - t.x) * k, z: t.z + (u.z - t.z) * k} : t, u.team, u.splash || CARDS[e.card]?.unit?.splash); }
          break;
        }
        case 'impact': {
          const wait = fx.impact(e, B.ents.get(e.target)) || 0;
          // (Cupsey's shot lands quietly: he is a plush, his squeak is his throw, atk_cupsey; the wet splat was a cup's)
          const s = {baguette: 'bread_hit', rocket: 'rocket_explode', laugh: 'laugh_blast', cannon: 'punch_heavy', bag: 'coins', acorn: sfx('acorn_boom', 'rocket_explode'), magic: sfx('magic_hit', 'sticky_splat')}[e.proj];
          const vol = e.proj === 'acorn' && !audio.has('acorn_boom') ? 0.5 : 0.85;
          if (s) { if (wait > 0.02) setTimeout(() => audio.play(s, {pan: pan(e.x), vol, gap: 0.05}), wait * 1000); else audio.play(s, {pan: pan(e.x), vol, gap: 0.05}); }   // (the acorn: when it lands)
          break;
        }
        // the troops' abilities: each its look (src/render/fx.js) and its sound (a stand-in until its own is in the manifest)
        case 'wave': fx.wave({x: e.x, z: e.z}, e.r); audio.play(sfx('shockwave', 'emote_pop'), {pan: pan(e.x), gap: 0.08, vol: 0.75}); buzz(12); break;
        case 'spin': { const u = B.ents.get(e.id); fx.spin({x: e.x, z: e.z}, e.r, u ? Math.min(1.1, (u.h || 1) * 0.65) : 0.75); audio.play(sfx('spin_slash', 'swing'), {pan: pan(e.x), gap: 0.08, vol: 0.9}); break; }
        // (a charge's shove is a knock too: the BONK is only for a bat; the shoved troop's skid and dust are its view's)
        case 'knock': if (CARDS[B.ents.get(e.by)?.card]?.unit?.knock) { fx.knock({x: e.x, z: e.z}); this.overlay.float(e.x, 2.3, e.z, 'BONK!', '#ffd84a', 0.8); audio.play('punch_heavy', {pan: pan(e.x), gap: 0.05, vol: 0.6}); } break;
        case 'charge': { const u = B.ents.get(e.id), card = u?.card, slide = card === 'pudgy'; if (!slide) fx.snort({x: e.x, z: e.z}, u?.face ?? 0); this.overlay.float(e.x, 2.4, e.z, slide ? 'SLIDE!' : 'CHARGE!', slide ? '#bfe3ff' : '#ff9a3a', 0.75); audio.play(sfx('charge_' + card, sfx('charge', 'charge_rush')), {pan: pan(e.x), gap: 0.3, vol: 0.85}); break; }
        case 'charge_hit': fx.chargeHit({x: e.x, z: e.z}, e.card); audio.play('whale_slam', {pan: pan(e.x), gap: 0.1, vol: e.card === 'pudgy' ? 0.35 : 0.55}); buzz(e.card === 'pudgy' ? 15 : 25); break;
        case 'blink': { const u = B.ents.get(e.id); if (CARDS[e.card]?.unit?.dash) { fx.dash(units.blinkFrom(e), {x: e.x, z: e.z}, u?.h); audio.play(sfx('dash_' + e.card, 'ui_swoosh'), {pan: pan(e.x), gap: 0.1, vol: 0.8}); break; }   // (TOSHI runs it: a streak, no vanishing)
          fx.blink(units.blinkFrom(e), {x: e.x, z: e.z}, u?.h); audio.play(sfx('teleport', 'ui_swoosh'), {pan: pan(e.x), gap: 0.1, vol: 0.8}); break; }
        case 'surprise': { const cut = !!CARDS[e.card]?.unit?.dash; fx.surprise({x: e.x, z: e.z}, cut); this.overlay.float(e.x, 2.6, e.z, cut ? 'CRIT!' : '!', cut ? '#7fdcff' : '#ffe14a', cut ? 1.1 : 1.6); audio.play(sfx('surprise_hit', 'punch_heavy'), {pan: pan(e.x), gap: 0.1, vol: audio.has('surprise_hit') ? 0.85 : 0.7}); buzz(15); break; }
        // the second wave's: what comes over a troop (the state itself is worn by its view: src/render/units.js)
        case 'berserk': fx.berserk({x: e.x, z: e.z}); this.overlay.float(e.x, 2.7, e.z, 'BERSERK!', '#ff5a3a', 0.95); hook('berserk', e.x, 0.8, 0.3); buzz(12); break;
        case 'snared': fx.snare({x: e.x, z: e.z}); this.overlay.float(e.x, 2.3, e.z, 'TANGLED!', '#ff9ad0', 0.7); hook('snared', e.x, 0.6); break;
        case 'shield_break': fx.shieldBreak(units.bodyOf(e.id, 0.5, V) || V.set(e.x, 1, e.z)); hook('shield_break', e.x); break;
        case 'mend': fx.mend(units.bodyOf(e.id, 0.7, V) || V.set(e.x, 1.4, e.z), units.bodyOf(e.target, 0.55, V2) || V2.set(e.x, 1, e.z)); hook('mend', e.x, 0.55, 0.2); break;
        case 'dig': fx.dig({x: e.x, z: e.z}); hook('dig', e.x); break;
        case 'surface': fx.surface({x: e.x, z: e.z}, e.r); hook('surface', e.x, 0.8); buzz(15); break;
        case 'feared': fx.fear({x: e.x, z: e.z}); hook('feared', e.x, 0.5, 0.25); break;
        // burning ground (THIS IS FINE), NYAN CAT's rainbow, the farter's stink, BOME's pages: drawn from their entities (fx.syncSpells); here only their sound
        case 'zone': if (e.kind === 'blaze') hook('fire_start', e.x, 0.6, 1); else if (e.kind === 'rainbow') hook('rainbow', e.x, 0.3, 1.2); else hook('zone_' + e.kind, e.x, 0.5, 1); break;
        case 'tower_shot': { const t = B.ents.get(e.id); if (t?.type !== 'hq') units.guardShot(arena.towerOf(t)); audio.play('tower_shot', {pan: pan(t?.x ?? 9), vol: t?.team === 0 ? 0.55 : 0.45, gap: 0.06}); break; }
        case 'dmg':
          if (e.kind === 'tower') {
            const t = B.ents.get(e.id); audio.play('tower_hit', {pan: pan(e.x), gap: 0.12, vol: 0.6});
            if (t?.team === 1) this.stats.dmgTowers += e.amt;
            if (e.spell) this.overlay.float(e.x, 4.5, e.z, '-' + e.amt, '#ffd36a', 1.1);
            if (t && Math.random() < 0.06) units.react(t.team, 'sitangry');
          }
          break;
        case 'drain':      // the tiebreaker eats every tower at once: sparks and thuds
          audio.play('tower_hit', {pan: pan(e.x), gap: 0.11, vol: 0.45});
          if (Math.random() < 0.2) fx.burst({x: e.x + (Math.random() - 0.5) * 2, z: e.z + (Math.random() - 0.5) * 2}, {n: 5, c: [1, 0.55, 0.25], s: 0.35, sp: 2.5, up: 3, life: 0.5, cell: CELL.spark, y: 2 + Math.random() * 3});
          break;
        case 'heal': { const u = B.ents.get(e.id); if (u) fx.healTick({x: u.x, y: 0, z: u.z}); break; }
        case 'heal_pulse': { const u = B.ents.get(e.id); if (u) { fx.heal({x: u.x, z: u.z}, e.r); audio.play('heal', {gap: 0.8, vol: 0.5}); } break; }
        case 'die': audio.play(audio.has('die_' + voice(e.card)) ? 'die_' + voice(e.card) : 'unit_die', {pan: pan(e.x), gap: 0.06, vol: 0.75}); if (e.card === 'whale' || e.card === 'chillhouse') { stage.kick(0.4); audio.play('crowd_gasp', {gap: 4, vol: 0.5}); } break;
        case 'down': audio.play('unit_die', {gap: 0.05}); break;
        case 'revive': audio.play('cat_revive'); break;
        case 'landed': { const u = B.ents.get(e.id); if (u?.mass >= 15) audio.play(e.card === 'chillhouse' ? 'house_stomp' : 'whale_slam', {pan: pan(e.x), vol: 0.8});
          if (CARDS[e.card]?.unit?.weaken && audio.has('weaken')) audio.play('weaken', {pan: pan(e.x), vol: 0.5, gap: 1}); break; }   // (WOJAK's gloom: once, as he lands)
        case 'slam': if (e.card) { fx.quake({x: e.x, z: e.z}, e.r); audio.play('whale_slam', {pan: pan(e.x), vol: 0.5, gap: 0.2}); buzz(15); break; }   // (SLERF's, every few seconds: smaller than a whale landing)
          fx.slam({x: e.x, z: e.z}, e.r); audio.play('whale_slam', {pan: pan(e.x)}); buzz(40); break;
        case 'splash': fx.splash({x: e.x, z: e.z}, e.r, e.card); if (e.card === 'whale') stage.kick(0.35); break;
        case 'spell': {
          fx.spell(e);
          const cast = {pump: 'spell_pump', airdrop: 'spell_airdrop', godcandle: 'spell_godcandle', banhammer: 'spell_hammer', coldwallet: 'spell_freeze', hopium: 'heal', deadcoins: 'spell_fud', hardfork: 'spell_hardfork', liquiditydrain: 'spell_liquiditydrain', marketcrash: 'spell_marketcrash', panicsell: 'spell_panicsell', diamondhands: 'spell_diamondhands'}[e.card];
          if (cast) audio.play(cast, {pan: pan(e.x)});
          if (e.card === 'liquidation' || e.card === 'gasfees') for (let k = 0; k < (e.card === 'gasfees' ? 2 : 3); k++) setTimeout(() => audio.play('liquidation_loop', {pan: pan(e.x), vol: 0.6, gap: 0}), k * 2600);
          if (e.card === 'fart') { audio.play(sfx('fart_cast', 'sticky_splat'), {pan: pan(e.x)}); audio.play(sfx('fart_cloud', 'liquidation_loop'), {pan: pan(e.x), vol: 0.35, gap: 0}); }
          break;
        }
        case 'spawn_bld': audio.play('bld_drop', {pan: pan(e.x)}); break;
        case 'boom': if (e.card === 'bubblemachine') fx.bubblePop({x: e.x, z: e.z}, e.r, true); else if (e.card === 'bome') fx.pageBurst({x: e.x, z: e.z}, e.r); else fx.boom({x: e.x, z: e.z}, e.r);
          audio.play(sfx('boom_' + e.card, 'rocket_explode'), {pan: pan(e.x), vol: 0.55, gap: 0.05}); buzz(15); break;
        case 'bolt': fx.bolt(e.x, e.z); audio.play('spell_fud', {pan: pan(e.x), gap: 0.05}); buzz(25); break;
        case 'hut_spawn': blds.spawned(e.id);
          if (e.card === 'tokenburner') { fx.burst({x: e.x, y: 0, z: e.z}, {n: 7, c: [1, 0.55, 0.15], s: 0.5, sp: 2.2, up: 3, life: 0.45, g: 2, cell: 13, y: 0.5}); hook('spawn_tokenburner', e.x, 0.5, 0.3); break; }
          if (e.card === 'backdoor') { fx.burst({x: e.x, y: 0, z: e.z}, {n: 7, c: [0.65, 0.35, 1], s: 0.35, sp: 2, up: 1.5, life: 0.4, g: 0, cell: CELL.spark, y: 0.7}); hook('spawn_backdoor', e.x, 0.5, 0.3); break; }
          if (e.card === 'mememint') { audio.play('coin_jingle', {pan: pan(e.x), vol: 0.6, gap: 0.2}); fx.burst({x: e.x, y: 0, z: e.z}, {n: 6, c: [1, 0.82, 0.3], s: 0.4, sp: 2, up: 4, life: 0.8, g: 12, cell: 2, add: false, y: 1.2, floor: 0.05, bounce: 0.3}); } else audio.play('bld_drop', {pan: pan(e.x), vol: 0.35, gap: 0.3}); break;
        case 'popup': audio.play('ui_swoosh', {pan: pan(e.x), vol: 0.5, gap: 0.3}); fx.burst({x: e.x, y: 0, z: e.z}, {n: 10, c: [0.62, 0.6, 0.58], s: 0.7, sp: 2, up: 1, life: 0.5, g: 1, cell: 3, add: false, a0: 0.5, y: 0.1}); break;
        case 'bld_down': if (e.card !== 'bubblemachine') fx.explode({x: e.x, y: 0, z: e.z}, false);   // (the machine goes with its last bubble: the boom after this)
          audio.play('bld_destroy', {pan: pan(e.x)});
          if (e.card === 'vestingvault') { fx.burst({x: e.x, y: 0, z: e.z}, {n: 18, c: [1, 0.82, 0.3], s: 0.45, sp: 3.6, up: 6, life: 1, g: 13, cell: 2, add: false, y: 0.9, floor: 0.05, bounce: 0.3}); audio.play('coins', {pan: pan(e.x), vol: 0.7}); }   // (it pays out)
          break;
        case 'turret_shot': {
          const b = B.ents.get(e.id), t = B.ents.get(e.target); blds.shot(e.id);
          if (e.proj === 'zap') { const from = blds.coilWorld(e.id); if (from && t) fx.zap(from, new THREE.Vector3(t.x, (t.h || 1) * 1.1, t.z)); audio.play('spell_fud', {pan: pan(b?.x ?? 9), vol: 0.35, gap: 0.08}); }
          else if (e.proj === 'bubble') { audio.play(sfx('atk_' + b?.card, 'turret_shot'), {pan: pan(b?.x ?? 9), vol: 0.55, gap: 0.08}); const m = blds.coilWorld(e.id, V); if (m) fx.burst(m, {n: 3, c: [0.72, 0.93, 1], s: 0.22, sp: 1, up: 0.6, life: 0.3, g: 0, cell: CELL.spark, y: 0}); }
          else if (e.proj === 'snipe') { audio.play(sfx('atk_' + b?.card, 'turret_shot'), {pan: pan(b?.x ?? 9), vol: 0.55, gap: 0.08}); const m = blds.coilWorld(e.id, V); if (m) fx.add.emit({x: m.x, y: m.y, z: m.z, life: 0.1, s0: 1.2, s1: 0.3, c: [1, 0.85, 0.5], cell: 0}); }   // (fires fast: a flash, nothing that piles up)
          else if (e.proj === 'bag') { audio.play('rocket_launch', {pan: pan(b?.x ?? 9), vol: 0.5, gap: 0.1}); if (b) fx.burst({x: b.x, y: 0, z: b.z}, {n: 8, c: [0.62, 0.6, 0.58], s: 0.9, sp: 1.2, up: 2, life: 0.8, g: -0.5, cell: 3, add: false, a0: 0.55, y: 1.6}); }
          else audio.play('turret_shot', {pan: pan(b?.x ?? 9), vol: 0.55, gap: 0.08});
          break;
        }
        case 'mined': if (e.team === 0) { this.overlay.float(e.x, 2.6, e.z, '+1', '#d9a6ff', 1.2); audio.play('copium_gain', {vol: 0.6}); } break;
        case 'hammer_hit': fx.hit({x: e.x, y: 0, z: e.z}, true); break;
        case 'spell_hit': { if (e.card === 'panicsell') this.overlay.float(e.x, 2.6, e.z, 'SELL!', '#ff4d6d', 1.3); const s = {fud: 'spell_fud', rug: 'spell_rug', airdrop: 'coins', downvotes: 'punch_light'}[e.card]; if (s) audio.play(s, {pan: pan(e.x)}); if (e.card === 'fud') fx.scorch(e.x, e.z, e.r * 0.8); if (e.card === 'airdrop') fx.burst({x: e.x, y: 0, z: e.z}, {n: 20, c: [1, 0.82, 0.3], s: 0.45, sp: 4, up: 3, life: 0.8, g: 10, cell: 2, add: false, y: 0.3, floor: 0.05, bounce: 0.3}); buzz(25); break; }
        case 'hq_wake': {
          audio.play('hq_wake'); const T = arena.towerOf(B.ents.get(e.id)); if (T) units.react(e.team, 'sityell');
          if (e.team === 0) this.hud.toast('Your Battlestation woke up!');
          break;
        }
        case 'tower_down': {
          const T = arena.towerOf(B.ents.get(e.id));
          fx.explode({x: e.x, y: 0, z: e.z}, e.tower === 'hq');
          if (T) { if (e.tower === 'hq') units.dropCommander(T); else units.dropGuard(T); arena.ruin(T); }
          audio.play(e.tower === 'hq' ? 'hq_destroy' : 'tower_destroy', {pan: pan(e.x)}); audio.duck(0.3, 2);
          setTimeout(() => audio.play('tower_crumble', {pan: pan(e.x)}), 350); setTimeout(() => audio.play(e.team === 1 ? 'crowd_cheer' : 'crowd_boo', {vol: 0.6}), 700);
          units.react(1 - e.team, 'sitcheer'); units.react(e.team, 'sityell'); units.taunt(1 - e.team);
          buzz(e.tower === 'hq' ? [60, 40, 120] : [40, 30, 60]);
          if (e.team === 0 && Math.random() < 0.6) setTimeout(() => this.hud.emote(1, Math.random() < 0.5 ? 'lmao' : 'gg'), 1200);
          if (e.team === 1 && Math.random() < 0.5) setTimeout(() => this.hud.emote(1, Math.random() < 0.5 ? 'cope' : 'seethe'), 1500);
          break;
        }
        case 'w': {
          const down = [...B.towers[1 - e.team]].filter(t => t.dead).pop();
          if (down) setTimeout(() => this.hud.flyW(e.team, down.x, down.z), 350);
          audio.play(e.team === 0 ? (audio.has('w_fanfare') ? 'w_fanfare' : 'w_gain') : 'w_lose');
          if (!B.over) this.hud.banner(e.team === 0 ? '+1 W' : 'TAKE THE L', e.team === 0 ? 'Rig Tower down!' : 'they took a Rig Tower', e.team === 0 ? '' : 'red', 1700);
          break;
        }
        case 'phase':
          if (e.phase === 'overdose') { this.hud.banner('COPIUM OVERDOSE', 'x2 COPIUM · 60 seconds left', 'purple', 2400); audio.play('overdose'); setTimeout(() => audio.play('vo_overdose'), 400); audio.music('mus_overdose'); buzz(30); }
          if (e.phase === 'overtime') { this.hud.banner('OVERTIME', 'sudden death · next W wins · x2 COPIUM', '', 2400); audio.play('overtime'); setTimeout(() => audio.play('vo_overtime'), 300); audio.music('mus_overdose'); }
          if (e.phase === 'triple') { this.hud.banner('x3 COPIUM', '60 seconds of overtime left', 'purple', 2200); audio.play('overdose'); buzz(30); }
          if (e.phase === 'tiebreak') { this.hud.banner('TIEBREAKER', 'the weakest tower falls', 'red', 2200); audio.play('overtime'); audio.stopMusic?.(); buzz([30, 60, 30]); this.tiebreakT = 0; }
          break;
        case 'end': this.finish(e); break;
      }
    }
    B.events.length = 0;
  }
  finish(e) {
    if (this.done) return; this.done = true;
    const {units} = this.app, win = e.winner === 0 ? 1 : e.winner === -1 ? -1 : 0;
    this.hud.select(-1);
    units.celebrate(e.winner);
    // a Battlestation down: the loser's other towers come down after it, one by one
    if (e.why === 'hq' && e.winner >= 0) this.b.towers[1 - e.winner].filter(t => !t.dead).forEach((t, i) => setTimeout(() => {
      const T = this.app.arena.towerOf(t); if (!T || T.ruined) return;
      if (t.type === 'hq') this.app.units.dropCommander(T); else this.app.units.dropGuard(T);
      this.app.fx.explode({x: t.x, y: 0, z: t.z}, false); this.app.arena.ruin(T); audio.play('tower_destroy', {pan: pan(t.x)});
    }, 500 + i * 450));
    audio.stopMusic(0.6); audio.ambience(null);
    setTimeout(() => { audio.play(win === 1 ? 'victory' : win === 0 ? 'defeat' : 'draw'); audio.play(win === 1 ? 'vo_victory' : win === 0 ? 'vo_defeat' : 'vo_draw'); audio.play(win === 1 ? 'crowd_cheer' : win === 0 ? 'crowd_laugh' : 'crowd_ooh', {vol: 0.6}); }, 300);
    const sub = e.why === 'hq' ? '3 Ws: Battlestation down!' : e.why === 'tiebreak' ? (win === 1 ? 'tiebreaker: their weakest tower fell' : 'tiebreaker: your weakest tower fell') : e.why === 'draw' ? 'dead even: no Clout won or lost' : '';
    this.hud.banner(win === 1 ? 'VICTORY' : win === 0 ? 'DEFEAT' : 'DRAW', sub, win === 0 ? 'red' : win === -1 ? 'purple' : '', 2600);
    // offline the store applies the result; online the server already did and sends it
    const got = this.online ? Promise.race([this.b.done.then(r => r.res || {dc: 0, coins: 0}), new Promise(r => setTimeout(() => r({dc: 0, coins: 0}), 8000))])
      : Promise.resolve(save.result(win, this.b.ws[0], this.opp.clout));
    Promise.all([got, new Promise(r => setTimeout(r, 2400))]).then(([res]) => { this.running = false; this.app.results(this, win, res); });
  }
  destroy() { this.gone = true; this.hud?.destroy(); this.overlay?.destroy(); this.b.destroy?.(); this.running = false; this.app.fx?.endBattle(); }
}
