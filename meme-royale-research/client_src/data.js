// MEME ROYALE — every table: cards, units, towers, leagues, the match clock. Numbers are level 1; each level adds LVL_STEP.
// Units: hp, dmg per hit, hs (seconds per hit), speed (tiles/s), range (tiles past both radii), sight (tiles), r (body radius),
// mass (pushing), h (height in game, tiles), bOnly (targets buildings only), splash (tiles), proj (projectile kind), n (count),
// heal ([hp a second to allies around, radius], in 4 pulses a second), healLand (hp given to allies around when it lands),
// model (another card's character it reuses: the genre's trick of the same troop in several cards), kamikaze (bursts on its
// first hit, splash around the target, and is gone), fire (drawn burning), tint (a colour over the reused character),
// knock (tiles each hit pushes the target back), frenzy ([attack speed added per hit on the same target, the most]),
// spin ([every Nth swing, radius, damage x]: hits everything around), wave (every hit is a shockwave of this radius around it),
// weaken ([damage x, radius]: enemies near it hit softer), air (flies at this height: only shooters, towers and spells reach it;
// it drops proj on the ground below), charge ([tiles walked before it charges, charge speed, damage x of the charge hit, tiles it shoves all around the hit, slow x, slow s]),
// towerK (damage x on towers and buildings), blink ([reach, cooldown s, damage x]: teleports behind its target, then a surprise hit),
// burn ([radius, dps, s]: each hit sets the ground under the target on fire), trail ([s between drops, radius, dps, s]: a flyer
// leaves a burning trail on the ground under its path). The burning ground is a zone (sim.js zone()): ground troops and buildings only.
// berserk ([health share, speed x, damage x]: below that share it goes mad for good), dash (its blink is a dash, drawn as a streak),
// quake ([radius, s]: every hit is a ground slam, troops around it stunned), trap ([every s, radius, s, s it lies]: a yarn trap at its target,
// what walks on it can't move for that long), pulse ([hp, radius, every s]: a big wave of healing around it), mend ([hp, shield, s the shield
// lasts, every s, radius]: the worst hurt ally in reach gets both), burrow ([reach, tiles a second, stun s, stun radius, cooldown s]: tunnels at its
// target, untouchable, and comes up beside it; also when it's being hit), cloud ([radius, dps, s]: each hit leaves a gas cloud where the target stands),
// deathBoom ([damage, radius]: bursts when it falls), deathZone ([zone kind, radius, dps, s, slow x]: hurting ground left when it falls).
// Buildings: spawn ([unit card, count, every s]: a hut), deathSpawn (troops left when it falls), minRange + lob (a mortar: lobs
// at a spot, can't hit what is too close), hide (stays underground, untargetable by troops, until something is in range),
// beam ([damage per hit at each stage]: a stare that ramps on one target), siege (also shoots towers and buildings, troops first),
// setup (s before it works, instead of the usual drop), deathBoom ([damage, radius]: bursts when it falls), anywhere (can go on
// the enemy's half too).
// Spells: summon ([unit card, count]: spread over dur, anywhere in the area), waves + gap (the area hit repeats), bolts (hits
// only the N toughest things in the area), ramp (dps grows by this every tick), heal (hp a second to allies in the area),
// drift (tiles a second the area moves toward the enemy's side), ground (flyers are out of it), pull (tiles a second towards the
// middle), bldK (dps x on buildings), fear (s enemy troops run home), guard ([damage x, s]: my troops in the area), clone (a copy of
// each of my troops in the area, one hit point).

export const LVL_STEP = 0.08;
export const MAX_LVL = 9;

export const MATCH = {
  // seconds. 3:00, COPIUM OVERDOSE (x2) in the last 60 s; tied: 2:00 of sudden-death overtime (x2, then x3 in its last 60 s);
  // still tied: the TIEBREAKER drains every tower by the same amount until the weakest one falls (equal: a draw)
  time: 180, overtime: 120, overdoseAt: 60, tripleAt: 60, tiebreakS: 2.4,
  regen: 2.8, maxCopium: 10, startCopium: 5,
  // the opening rush: COPIUM fills a little faster (x1.3) for the first 30 s, so the first plays come sooner
  rushS: 30, rush: 1.3,
  deployTime: 1.0,
};
// how fast COPIUM fills now (sim.js, and the online client's own guess between snapshots): the opening rush, x2 in
// COPIUM OVERDOSE and overtime, x3 in overtime's last minute
export const regenMult = (phase, clock, overdose) => phase === 'overtime' ? (clock <= MATCH.tripleAt ? 3 : 2) : overdose ? 2
  : phase === 'play' && clock > MATCH.time - MATCH.rushS ? MATCH.rush : 1;

export const TOWERS = {
  rig: {name: 'Rig Tower', hp: 2600, dmg: 88, hs: 0.8, range: 7.5, r: 1.45, h: 4.2},
  hq: {name: 'Battlestation', hp: 4400, dmg: 104, hs: 1.0, range: 7.0, r: 1.95, h: 5.0},
};

export const RARITY = {
  common: {name: 'Common', color: '#AEB6C2', glow: '#e9eef5'},
  rare: {name: 'Rare', color: '#4CC9F0', glow: '#a9ecff'},
  epic: {name: 'Epic', color: '#C77DFF', glow: '#ecd2ff'},
  legendary: {name: 'Legendary', color: '#FFC84A', glow: '#fff0b8'},
};

// type: 'unit' | 'spell' | 'building'
export const CARDS = {
  useless: {name: 'USELESS', rarity: 'common', cost: 2, type: 'unit', blurb: 'Four gold coins with no utility. Proudly swarm anything.',
    unit: {hp: 135, dmg: 56, hs: 1.0, speed: 1.8, range: 0.5, sight: 5.5, r: 0.3, mass: 1, h: 0.8, n: 4, hitSfx: 'coin_jingle'}},
  troll: {name: 'Trollface', rarity: 'rare', cost: 2, type: 'unit', blurb: 'Problem? Teleports behind his target and hits it twice as hard. Then does it again.',
    unit: {hp: 500, dmg: 108, hs: 1.1, speed: 1.8, range: 0.6, sight: 5.5, r: 0.42, mass: 4, h: 1.3, blink: [5.5, 7, 2.0]}},
  chillguy: {name: 'Chill Guy', rarity: 'common', cost: 3, type: 'unit', blurb: 'Soaks hits. Never panic sells: cannot be stunned or knocked back.',
    unit: {hp: 1380, dmg: 150, hs: 1.2, speed: 1.25, range: 0.7, sight: 5.5, r: 0.5, mass: 7, h: 1.4, noStun: true}},
  jeanphil: {name: 'Jean Phil', rarity: 'common', cost: 3, type: 'unit', blurb: 'Two Jean Phils lob baguettes from range. Bonjour, exit liquidity.',
    unit: {hp: 300, dmg: 94, hs: 1.0, speed: 1.25, range: 5.0, sight: 6.0, r: 0.4, mass: 3, h: 1.35, n: 2, proj: 'baguette'}},
  lmao: {name: 'LMAO!', rarity: 'common', cost: 4, type: 'unit', blurb: 'Laughs so hard it hurts everyone near the target.',
    unit: {hp: 640, dmg: 170, hs: 1.5, speed: 1.25, range: 5.5, sight: 6.0, r: 0.45, mass: 4, h: 1.35, splash: 1.4, proj: 'laugh'}},
  ket: {name: 'KET', rarity: 'rare', cost: 3, type: 'unit', blurb: 'Sweet and sticky. Every hit slows the target down.',
    unit: {hp: 820, dmg: 124, hs: 1.2, speed: 1.25, range: 0.6, sight: 5.5, r: 0.45, mass: 5, h: 1.3, slow: [0.65, 2.0]}},
  zcat: {name: 'ZCAT', rarity: 'rare', cost: 3, type: 'unit', blurb: 'Very fast, hits like a margin call. Paper hands: folds quickly.',
    unit: {hp: 420, dmg: 265, hs: 1.3, speed: 2.3, range: 0.6, sight: 6.0, r: 0.4, mass: 3, h: 1.25, pounce: 1.8}},
  cupsey: {name: 'Cupsey', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Patches up allies the moment he lands, then keeps healing everyone near him. Throws a little matcha too.',
    unit: {hp: 700, dmg: 62, hs: 1.2, speed: 1.25, range: 4.5, sight: 5.5, r: 0.45, mass: 4, h: 1.3, proj: 'matcha', heal: [65, 3.0], healLand: 130}},
  cate: {name: 'CATE', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Nine lives, all leveraged: gets back up once at half health.',
    unit: {hp: 740, dmg: 158, hs: 1.0, speed: 1.7, range: 0.6, sight: 5.5, r: 0.42, mass: 4, h: 1.3, revive: 0.5}},
  triplet: {name: 'Triple T', rarity: 'rare', cost: 5, type: 'unit', blurb: 'Three times the tree. Three times the bags.',
    unit: {hp: 560, dmg: 120, hs: 1.2, speed: 1.25, range: 0.6, sight: 5.5, r: 0.45, mass: 5, h: 1.35, n: 3}},
  baton: {name: 'BATON', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Suit on. Jumps the Liquidity Pool and charges straight for towers.',
    unit: {hp: 1450, dmg: 228, hs: 1.5, speed: 2.1, range: 0.6, sight: 9, r: 0.5, mass: 6, h: 1.4, bOnly: true, jumper: true}},
  chillhouse: {name: 'CHILLHOUSE', rarity: 'common', cost: 5, type: 'unit', blurb: 'A whole house walking to your towers. Rent is due: two USELESS move out when it falls.',
    unit: {hp: 3250, dmg: 190, hs: 1.6, speed: 0.85, range: 0.8, sight: 9, r: 0.85, mass: 18, h: 2.0, bOnly: true, deathSpawn: ['useless', 2]}},
  mensa: {name: 'MENSA', rarity: 'common', cost: 5, type: 'unit', blurb: 'Big-brain beam. The longer it stares, the harder it burns.',
    unit: {hp: 1150, dmg: 30, hs: 0.35, speed: 0.95, range: 4.5, sight: 5.5, r: 0.6, mass: 8, h: 1.45, beam: [30, 100, 330]}},
  mitch: {name: 'MITCH', rarity: 'epic', cost: 5, type: 'unit', blurb: 'Chains, crosses, and one very heavy right hand.',
    unit: {hp: 2150, dmg: 440, hs: 1.8, speed: 1.05, range: 0.8, sight: 5.5, r: 0.55, mass: 10, h: 1.5}},
  alon: {name: 'Alon', rarity: 'epic', cost: 5, type: 'unit', blurb: 'Ships rockets faster than products. Long range, small blast.',
    unit: {hp: 760, dmg: 215, hs: 1.6, speed: 1.25, range: 6.2, sight: 6.5, r: 0.45, mass: 4, h: 1.4, splash: 0.9, proj: 'rocket'}},
  whale: {name: 'The Whale', rarity: 'legendary', cost: 7, type: 'unit', blurb: 'Moves the market by sitting down. Slams on landing and on every hit.',
    unit: {hp: 4700, dmg: 285, hs: 1.8, speed: 0.8, range: 0.9, sight: 9, r: 1.0, mass: 30, h: 2.3, bOnly: true, splash: 1.6, slam: [230, 2.6]}},
  neet: {name: 'NEET', rarity: 'legendary', cost: 5, type: 'unit', blurb: 'Left the basement for this. Every punch is a keyboard smash: it hits everything around the target.',
    unit: {hp: 2050, dmg: 240, hs: 1.4, speed: 1.0, range: 0.7, sight: 5.5, r: 0.55, mass: 9, h: 1.45, splash: 1.1}},
  bonk: {name: 'BONK', rarity: 'common', cost: 3, type: 'unit', blurb: 'One dog, one bat. Every swing knocks the target back.',
    unit: {hp: 1160, dmg: 185, hs: 1.4, speed: 1.5, range: 0.9, sight: 5.5, r: 0.45, mass: 5, h: 1.4, knock: 1.4}},
  dope: {name: 'DOPE', rarity: 'common', cost: 2, type: 'unit', blurb: 'A very good boy with a very sad face. Bites faster the longer it hangs on.',
    unit: {hp: 430, dmg: 88, hs: 0.75, speed: 2.3, range: 0.5, sight: 6.0, r: 0.42, mass: 3, h: 0.95, frenzy: [0.2, 1.8]}},
  swordcat: {name: 'SWORDCAT', rarity: 'rare', cost: 3, type: 'unit', blurb: 'Tiny knight, real sword. Every third swing is a spin that cuts everything around it.',
    unit: {hp: 840, dmg: 160, hs: 1.0, speed: 1.6, range: 0.7, sight: 5.5, r: 0.4, mass: 4, h: 1.15, spin: [3, 1.4, 1.6]}},
  popcat: {name: 'POPCAT', rarity: 'rare', cost: 4, type: 'unit', blurb: 'POP! Every pop is a shockwave that hits everything around it.',
    unit: {hp: 1120, dmg: 158, hs: 1.5, speed: 1.25, range: 1.2, sight: 5.5, r: 0.45, mass: 5, h: 1.0, wave: 2.2}},
  wojak: {name: 'WOJAK', rarity: 'rare', cost: 3, type: 'unit', blurb: 'It\'s over. Enemies near him lose the will to fight: they deal 35% less damage.',
    unit: {hp: 900, dmg: 90, hs: 1.2, speed: 1.25, range: 0.6, sight: 5.5, r: 0.42, mass: 4, h: 1.4, weaken: [0.65, 3.5]}},
  pnut: {name: 'PNUT', rarity: 'epic', cost: 4, type: 'unit', blurb: 'A flying squirrel with a hat and a grudge. Drops explosive acorns. Only shooters, towers and spells can reach him.',
    unit: {hp: 720, dmg: 230, hs: 1.7, speed: 1.5, range: 0.4, sight: 6.0, r: 0.4, mass: 3, h: 1.1, air: 2.2, splash: 1.3, proj: 'acorn'}},
  pepe: {name: 'PEPE', rarity: 'legendary', cost: 4, type: 'unit', blurb: 'Feels good, man. His magic bolts hit a small area and slow everything they touch.',
    unit: {hp: 600, dmg: 100, hs: 1.3, speed: 1.25, range: 5.5, sight: 6.5, r: 0.42, mass: 4, h: 1.4, proj: 'magic', splash: 1.0, slow: [0.65, 2.2]}},
  moodeng: {name: 'MOO DENG', rarity: 'epic', cost: 5, type: 'unit', blurb: 'Tiny, angry, unstoppable. Charges after a short run: the charge hits twice as hard, and she wrecks towers.',
    unit: {hp: 2100, dmg: 185, hs: 1.5, speed: 1.0, range: 0.8, sight: 5.5, r: 0.7, mass: 14, h: 1.15, charge: [2.5, 2.2, 1.8], towerK: 1.35}},
  giga: {name: 'GIGA', rarity: 'legendary', cost: 6, type: 'unit', blurb: 'Heavy, calm, perfectly sculpted. Punches like a truck and can\'t be stunned or pushed.',
    unit: {hp: 2750, dmg: 285, hs: 1.6, speed: 1.05, range: 0.8, sight: 5.5, r: 0.62, mass: 16, h: 1.75, noStun: true}},
  npcwojak: {name: 'NPC WOJAK', rarity: 'common', cost: 4, type: 'unit', blurb: 'Five NPCs, one script: walk to the tower, hit the tower. They ignore everything else.',
    unit: {hp: 300, dmg: 70, hs: 1.1, speed: 1.25, range: 0.6, sight: 9, r: 0.38, mass: 2.5, h: 1.15, n: 5, bOnly: true, model: 'wojak', tint: '#a9b4c2'}},
  thisisfine: {name: 'THIS IS FINE', rarity: 'epic', cost: 4, type: 'unit', blurb: 'Everything is on fire and he is fine with it. Every hit sets the ground ablaze.',
    unit: {hp: 980, dmg: 92, hs: 1.3, speed: 1.25, range: 0.8, sight: 5.5, r: 0.42, mass: 4, h: 1.35, burn: [1.4, 55, 4]}},
  nyancat: {name: 'NYAN CAT', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Flies straight at buildings, leaving a rainbow that burns whatever walks under it.',
    unit: {hp: 820, dmg: 130, hs: 1.2, speed: 1.8, range: 0.5, sight: 7, r: 0.42, mass: 3, h: 0.9, air: 2.0, bOnly: true, trail: [0.3, 0.9, 55, 2.5]}},
  // the second wave of characters
  floki: {name: 'FLOKI', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Viking shiba, axe the size of a door. Below 30% health he goes berserk: much faster, and he hits harder.',
    unit: {hp: 1300, dmg: 175, hs: 1.3, speed: 1.25, range: 0.7, sight: 5.5, r: 0.48, mass: 6, h: 1.4, berserk: [0.3, 1.6, 1.35]}},
  toshi: {name: 'TOSHI', rarity: 'epic', cost: 3, type: 'unit', blurb: 'Blue cat assassin. Dashes behind his target and lands a critical hit, then needs 5 s before he can do it again.',
    unit: {hp: 640, dmg: 150, hs: 1.1, speed: 1.8, range: 0.6, sight: 6.0, r: 0.4, mass: 3, h: 1.15, blink: [5.5, 5, 2.4], dash: true}},
  slerf: {name: 'SLERF', rarity: 'epic', cost: 6, type: 'unit', blurb: 'Half asleep and very slow. Every punch is a ground slam that hits and stuns everything around him.',
    unit: {hp: 2850, dmg: 230, hs: 2.6, speed: 0.55, range: 0.8, sight: 5.5, r: 0.8, mass: 20, h: 1.9, noStun: true, quake: [2.4, 0.7]}},
  michi: {name: 'MICHI', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Throws yarn balls, and every 4 s a yarn trap: the next enemies to walk on it are tangled and can\'t move for 1.5 s.',
    unit: {hp: 640, dmg: 105, hs: 1.2, speed: 1.25, range: 5.5, sight: 6.0, r: 0.4, mass: 4, h: 1.25, proj: 'yarn', trap: [4, 1.2, 1.5, 7]}},
  pippin: {name: 'PIPPIN', rarity: 'epic', cost: 4, type: 'unit', blurb: 'A magical unicorn. Every 3 s a wave of light heals every ally nearby.',
    unit: {hp: 640, dmg: 90, hs: 1.3, speed: 1.25, range: 5.0, sight: 6.0, r: 0.42, mass: 4, h: 1.35, proj: 'star', pulse: [125, 4.5, 3]}},
  pudgy: {name: 'PUDGY', rarity: 'common', cost: 3, type: 'unit', blurb: 'After a short run he slides in belly first: enemies at the point of impact are knocked back and slowed.',
    unit: {hp: 1000, dmg: 120, hs: 1.1, speed: 1.25, range: 0.6, sight: 5.5, r: 0.45, mass: 6, h: 1.15, charge: [1.8, 3.2, 1.3, 1.3, 0.6, 2.5]}},
  bome: {name: 'BOME', rarity: 'epic', cost: 4, type: 'unit', blurb: 'A floating spellbook that shoots pages. When it falls it explodes into a paper storm that hurts and slows all inside.',
    unit: {hp: 680, dmg: 105, hs: 1.4, speed: 1.25, range: 5.0, sight: 6.0, r: 0.45, mass: 3, h: 1.05, air: 1.8, proj: 'page', deathBoom: [150, 2.2], deathZone: ['paperstorm', 2.4, 55, 3.5, 0.7]}},
  apu: {name: 'APU', rarity: 'rare', cost: 3, type: 'unit', blurb: 'Frog healer. Every 3 s the most hurt ally nearby gets health back and a shield that lasts 4 s.',
    unit: {hp: 560, dmg: 60, hs: 1.2, speed: 1.25, range: 4.0, sight: 5.5, r: 0.38, mass: 3, h: 1.05, proj: 'holy', mend: [120, 90, 4, 3, 5.5]}},
  walter: {name: 'WALTER', rarity: 'rare', cost: 4, type: 'unit', blurb: 'Digs underground where nothing can touch him, comes up beside his target and stuns all around him. Ready again after 6 s.',
    unit: {hp: 1200, dmg: 125, hs: 1.2, speed: 1.25, range: 0.7, sight: 5.5, r: 0.45, mass: 5, h: 1.35, burrow: [6, 4.5, 1, 1.6, 6]}},
  goat: {name: 'THE GOAT', rarity: 'legendary', cost: 5, type: 'unit', blurb: 'Greatest of all time. After a short run he charges, knocking enemies back, and he hits towers extra hard.',
    unit: {hp: 1850, dmg: 190, hs: 1.25, speed: 1.25, range: 0.7, sight: 5.5, r: 0.55, mass: 9, h: 1.5, charge: [2.5, 2.8, 1.7, 1.6], towerK: 1.6}},
  farter: {name: 'FARTER', rarity: 'common', cost: 3, type: 'unit', blurb: 'Releases toxic gas clouds where his target stands. Whatever stays inside keeps taking damage.',
    unit: {hp: 560, dmg: 40, hs: 2.2, speed: 1.25, range: 3.0, sight: 5.5, r: 0.42, mass: 3, h: 1.35, proj: 'gas', cloud: [1.9, 95, 5]}},
  // the same characters, other cards
  firesale: {name: 'FIRE SALE', rarity: 'common', cost: 2, type: 'unit', blurb: 'Three USELESS set on fire. They sprint at the first thing they see and burst, burning everything around it.',
    unit: {hp: 120, dmg: 110, hs: 0.5, speed: 2.6, range: 1.8, sight: 6.0, r: 0.3, mass: 1, h: 0.8, n: 3, splash: 1.5, kamikaze: true, fire: true, model: 'useless'}},
  uselessarmy: {name: 'USELESS ARMY', rarity: 'epic', cost: 3, type: 'unit', blurb: 'Fifteen USELESS at once. One is nothing; fifteen bury anything big.',
    unit: {hp: 70, dmg: 56, hs: 1.0, speed: 1.8, range: 0.5, sight: 5.5, r: 0.27, mass: 0.8, h: 0.68, n: 15, model: 'useless', hitSfx: 'coin_jingle'}},
  fud: {name: 'FUD', rarity: 'common', cost: 2, type: 'spell', blurb: 'A storm of bad headlines: zaps an area and stuns briefly.',
    spell: {r: 2.5, dmg: 175, tower: 0.3, stun: 0.6, delay: 0.25}},
  pump: {name: 'PUMP IT', rarity: 'rare', cost: 2, type: 'spell', blurb: 'Allies in the green candle move and hit 40% faster for 6 s.',
    spell: {r: 3.5, dur: 6, boost: 1.4, delay: 0}},
  rug: {name: 'RUG PULL', rarity: 'epic', cost: 4, type: 'spell', blurb: 'Yanks the rug: heavy damage and knockback after a short delay.',
    spell: {r: 2.6, dmg: 560, tower: 0.35, knock: 1.3, delay: 1.0}},
  airdrop: {name: 'AIRDROP', rarity: 'rare', cost: 3, type: 'spell', blurb: 'A rain of gold coins over a wide area: hits everything under it.',
    spell: {r: 4, dmg: 150, tower: 0.25, delay: 0.7}},
  coldwallet: {name: 'COLD WALLET', rarity: 'epic', cost: 4, type: 'spell', blurb: 'Freezes everything in the area, towers too, for 3.5 s.',
    spell: {r: 3, dmg: 90, tower: 0.3, freeze: 3.5, delay: 0.15}},
  liquidation: {name: 'LIQUIDATION', rarity: 'rare', cost: 4, type: 'spell', blurb: 'A pool of melting red candles: burns and slows everything in it for 8 s.',
    spell: {r: 3.5, dps: 75, tower: 0.3, dur: 8, slow: 0.8, delay: 0}},
  godcandle: {name: 'GOD CANDLE', rarity: 'legendary', cost: 6, type: 'spell', blurb: 'One colossal green candle from the sky. Small area, enormous damage.',
    spell: {r: 2, dmg: 1050, tower: 0.32, delay: 1.3}},
  banhammer: {name: 'BAN HAMMER', rarity: 'common', cost: 2, type: 'spell', blurb: 'Rolls 10 tiles forward, hitting and knocking back everything on the ground.',
    spell: {r: 1.8, dmg: 230, tower: 0.15, roll: 10, speed: 7, knock: 1.0, delay: 0}},
  downvotes: {name: 'DOWNVOTES', rarity: 'common', cost: 3, type: 'spell', blurb: 'Three waves of downvotes over a huge area. Swarms get ratioed.',
    spell: {r: 4.6, dmg: 60, waves: 3, gap: 0.3, tower: 0.25, delay: 0.45}},
  margincall: {name: 'MARGIN CALL', rarity: 'epic', cost: 6, type: 'spell', blurb: 'Three red bolts strike the three toughest things in the area and stun them.',
    spell: {r: 3.5, dmg: 640, tower: 0.3, bolts: 3, stun: 0.5, delay: 0.35}},
  gasfees: {name: 'GAS FEES', rarity: 'rare', cost: 3, type: 'spell', blurb: 'A cloud of network fees: every second inside costs more than the last.',
    spell: {r: 3.2, dps: 40, ramp: 20, tower: 0.3, dur: 6, delay: 0}},
  fart: {name: 'FART', rarity: 'common', cost: 3, type: 'spell', blurb: 'A toxic green cloud that drifts toward the enemy, hurting everything it passes for 6 s.',
    spell: {r: 2.8, dps: 90, tower: 0.3, dur: 6, drift: 0.55, delay: 0}},
  hopium: {name: 'HOPIUM', rarity: 'rare', cost: 3, type: 'spell', blurb: 'A cloud of pure hope: your troops inside heal fast for 2.5 s.',
    spell: {r: 3.2, heal: 160, dur: 2.5, delay: 0}},
  deadcoins: {name: 'DEAD COINS', rarity: 'legendary', cost: 5, type: 'spell', blurb: 'Dead projects never die: 13 USELESS crawl out of the ground over 9 s, anywhere in the area.',
    spell: {r: 4, dur: 9, summon: ['useless', 13], delay: 0.5}},
  hardfork: {name: 'HARD FORK', rarity: 'epic', cost: 3, type: 'spell', blurb: 'Every troop of yours in the area gets a copy beside it. Same hits, one hit point.',
    spell: {r: 3, clone: true, delay: 0.2}},
  liquiditydrain: {name: 'LIQUIDITY DRAIN', rarity: 'epic', cost: 3, type: 'spell', blurb: 'A whirlpool of coins: pulls every enemy troop in the area to its middle for 2.5 s.',
    spell: {r: 4.5, pull: 3, dps: 70, tower: 0.25, dur: 2.5, delay: 0}},
  marketcrash: {name: 'MARKET CRASH', rarity: 'rare', cost: 3, type: 'spell', blurb: 'The floor gives way: 3 s of quakes that slow troops and shake buildings to pieces. Flyers just watch.',
    spell: {r: 3.5, dps: 75, bldK: 3.5, tower: 0.35, slow: 0.5, ground: true, dur: 3, delay: 0}},
  panicsell: {name: 'PANIC SELL', rarity: 'common', cost: 2, type: 'spell', blurb: 'Everybody out! Enemy troops in the area drop everything and run home for 2.5 s. The big ones don\'t scare.',
    spell: {r: 2.8, dmg: 90, tower: 0.2, fear: 2.5, delay: 0.2}},
  diamondhands: {name: 'DIAMOND HANDS', rarity: 'rare', cost: 3, type: 'spell', blurb: 'Never let go. Your troops in the area take half damage for 5 s.',
    spell: {r: 3.2, guard: [0.5, 5], delay: 0}},
  // buildings: stand where you drop them, lose health over their life, block the way; giants and chargers go for them
  shillturret: {name: 'SHILL TURRET', rarity: 'common', cost: 3, type: 'building', blurb: 'Spams anything that walks by. Lasts 30 s. Tanks love to chase it.',
    bld: {hp: 850, life: 30, r: 0.9, h: 1.6, range: 5.5, dmg: 115, hs: 0.9, proj: 'spam'}},
  miningrig: {name: 'MINING RIG', rarity: 'epic', cost: 6, type: 'building', blurb: 'Mines 1 COPIUM every 9 s for 80 s. Protect your investment.',
    bld: {hp: 900, life: 80, r: 1.0, h: 2.2, mine: 9}},
  baglauncher: {name: 'BAG LAUNCHER', rarity: 'common', cost: 4, type: 'building', blurb: 'Lobs heavy bags halfway across the arena. Big splash, slow reload, and it can\'t hit anything right next to it.',
    bld: {hp: 1100, life: 30, r: 0.9, h: 1.5, range: 11.5, minRange: 3.5, dmg: 150, hs: 5.0, splash: 1.5, proj: 'bag', lob: true}},
  honeypot: {name: 'HONEYPOT', rarity: 'rare', cost: 4, type: 'building', blurb: 'Hides underground, so troops walk right past it. Then it pops up and zaps them.',
    bld: {hp: 900, life: 30, r: 0.8, h: 1.3, range: 5.5, dmg: 170, hs: 1.1, proj: 'zap', hide: true}},
  mememint: {name: 'MEME MINT', rarity: 'common', cost: 3, type: 'building', blurb: 'A coin press: mints a USELESS every 3.5 s for 30 s, and spills three more when it breaks.',
    bld: {hp: 500, life: 30, r: 0.8, h: 1.5, spawn: ['useless', 1, 3.5], deathSpawn: ['useless', 3]}},
  trollfarm: {name: 'TROLL FARM', rarity: 'rare', cost: 6, type: 'building', blurb: 'A server rack full of trolls: sends out a Trollface every 8 s for 40 s.',
    bld: {hp: 1100, life: 40, r: 1.0, h: 1.9, spawn: ['troll', 1, 8.0]}},
  lasereyes: {name: 'LASER EYES', rarity: 'rare', cost: 5, type: 'building', blurb: 'A stone idol with laser eyes. The longer it stares at one target, the hotter it burns. Tanks hate it.',
    bld: {hp: 1100, life: 35, r: 0.9, h: 1.9, range: 5.5, hs: 0.35, beam: [25, 90, 300]}},
  bubblemachine: {name: 'BUBBLE MACHINE', rarity: 'rare', cost: 4, type: 'building', blurb: 'Every bubble bursts over a small area. And when the machine breaks, the biggest one goes too.',
    bld: {hp: 1150, life: 35, r: 0.9, h: 1.6, range: 6, dmg: 110, hs: 1.6, splash: 1.4, proj: 'bubble', deathBoom: [200, 2.2]}},
  sniperbot: {name: 'SNIPER BOT', rarity: 'epic', cost: 6, type: 'building', blurb: 'Takes 3.5 s to set up. Then it fires non-stop at anything within 11.5 tiles, towers too.',
    bld: {hp: 1000, life: 30, r: 0.9, h: 1.7, range: 11.5, dmg: 22, hs: 0.3, proj: 'snipe', siege: true, setup: 3.5}},
  tokenburner: {name: 'TOKEN BURNER', rarity: 'rare', cost: 4, type: 'building', blurb: 'A furnace with a mean streak: spits out a flaming USELESS every 5 s for 40 s, and two more when it breaks.',
    bld: {hp: 700, life: 40, r: 0.9, h: 1.6, spawn: ['firesale', 1, 5.0], deathSpawn: ['firesale', 2]}},
  vestingvault: {name: 'VESTING VAULT', rarity: 'rare', cost: 4, type: 'building', blurb: 'A locked vault that soaks hits and pulls tanks. When it breaks, or the lock-up ends, a Chill Guy walks out.',
    bld: {hp: 1200, life: 20, r: 0.9, h: 1.5, deathSpawn: ['chillguy', 1]}},
  backdoor: {name: 'BACKDOOR', rarity: 'epic', cost: 4, type: 'building', blurb: 'Goes anywhere on the map, even next to their tower. Lets a USELESS through every 2 s until someone shuts it.',
    bld: {hp: 450, life: 10, r: 0.8, h: 1.0, spawn: ['useless', 1, 2.0], deathSpawn: ['useless', 2], anywhere: true}},
};

export const CARD_IDS = Object.keys(CARDS);
export const UNIT_IDS = CARD_IDS.filter(id => CARDS[id].type === 'unit');

// THE TROPHY ROAD: seventeen arenas, each a place with its own look (src/render/themes.js), reached with Clout (trophies). You
// battle in the arena of your Clout; reaching one unlocks its cards. The league titles ride along (Lurker -> Gigachad).
export const ARENAS = [
  {id: 'basement', n: 1, name: "MOM'S BASEMENT", at: 0, title: 'LURKER', unlock: ['useless', 'troll', 'chillguy', 'jeanphil', 'lmao', 'ket', 'neet', 'fud', 'rug', 'downvotes', 'mememint', 'bonk'],
    blurb: 'Where every degen starts. Mind the energy drink spill.'},
  {id: 'backyard', n: 2, name: 'BACKYARD BBQ', at: 300, title: 'NORMIE', unlock: ['cupsey', 'chillhouse', 'airdrop', 'firesale', 'hopium', 'dope', 'fart', 'pudgy', 'vestingvault'], blurb: 'Burgers, a kiddie pool and a lawn worth fighting for.'},
  {id: 'parking', n: 3, name: 'STRIP MALL LOT', at: 600, title: 'NORMIE', unlock: ['zcat', 'pump', 'shillturret', 'baglauncher', 'popcat', 'swordcat', 'farter'], blurb: 'Pawn shop, vape shop, and a parking lot full of beef.'},
  {id: 'plaza', n: 4, name: 'PLAZA AFTER DARK', at: 1000, title: 'DEGEN', unlock: ['baton', 'banhammer', 'uselessarmy', 'gasfees', 'pnut', 'npcwojak', 'apu', 'panicsell'], blurb: 'Neon, sirens and the Liquidity Pool.'},
  {id: 'beach', n: 5, name: 'MUSCLE BEACH', at: 1300, title: 'DEGEN', unlock: ['cate', 'triplet', 'trollfarm', 'giga', 'floki', 'bubblemachine'], blurb: 'Sun, sand and somebody else\'s dumbbells.'},
  {id: 'exchange', n: 6, name: 'THE TRADING FLOOR', at: 1700, title: 'DEGEN', unlock: ['mensa', 'liquidation', 'honeypot', 'wojak', 'nyancat', 'walter', 'marketcrash'], blurb: 'Buy high, sell low, scream at screens.'},
  {id: 'casino', n: 7, name: 'DEGEN CASINO', at: 2100, title: 'CHAD', unlock: ['mitch', 'miningrig', 'margincall', 'pepe', 'michi', 'diamondhands'], blurb: 'The house always wins. Prove it wrong.'},
  {id: 'cold', n: 8, name: 'COLD STORAGE', at: 2500, title: 'CHAD', unlock: ['alon', 'coldwallet', 'moodeng', 'slerf', 'lasereyes'], blurb: 'Frozen wallets and frostbitten bags.'},
  {id: 'penthouse', n: 9, name: 'LAMBO PENTHOUSE', at: 3000, title: 'GIGACHAD', unlock: ['whale', 'deadcoins', 'thisisfine', 'pippin'], blurb: 'Infinity pool, three Lambos, zero chill.'},
  {id: 'moon', n: 10, name: 'TO THE MOON', at: 3500, title: 'GIGACHAD', unlock: ['godcandle', 'sniperbot'], blurb: 'You made it. Now hold the line up here.'},
  {id: 'factory', n: 11, name: 'MEMECOIN FACTORY', at: 5000, title: 'GIGACHAD', unlock: ['bome'], blurb: 'You got to the moon. Time to print your own.'},
  {id: 'dump', n: 12, name: 'THE DUMP', at: 7500, title: 'GIGACHAD', unlock: ['tokenburner'], blurb: 'Where your last twelve launches ended up.'},
  {id: 'cemetery', n: 13, name: 'COIN CEMETERY', at: 11000, title: 'GIGACHAD', unlock: ['backdoor'], blurb: 'Here lies every coin you swore was different.'},
  {id: 'trench', n: 14, name: 'WHALE TRENCH', at: 16000, title: 'GIGACHAD', unlock: ['liquiditydrain'], blurb: 'Rock bottom, and something is still selling below you.'},
  {id: 'mine', n: 15, name: 'DIAMOND HANDS MINE', at: 23000, title: 'GIGACHAD', unlock: ['goat'], blurb: 'Dig deeper. Never let go.'},
  {id: 'clouds', n: 16, name: 'COPIUM CLOUDS', at: 34000, title: 'GIGACHAD', unlock: ['toshi'], blurb: "Breathe in. It's all still going up."},
  {id: 'metaverse', n: 17, name: 'THE METAVERSE', at: 50000, title: 'GIGACHAD', unlock: ['hardfork'], blurb: "Nobody's here. Prices are holding."},
];
export const arenaOf = clout => { let A = ARENAS[0]; for (const a of ARENAS) if (clout >= a.at) A = a; return A; };
export const arenaById = id => ARENAS.find(a => a.id === id) || ARENAS[0];
// (the old names, kept for the code that still says league)
export const LEAGUES = ARENAS, leagueOf = arenaOf;

// THE SHOP. COINS: soft currency (battles, bags, daily gift). GEMS: premium, bought with real money (a Solana wallet pays in
// USD-priced USDC, server/pay.mjs) and found in small amounts in bags. Prices in usd are charged by the server only.
export const GEM_PACKS = [
  {id: 'gems_s', gems: 80, usd: 0.99, label: 'Pocket of Gems'}, {id: 'gems_m', gems: 500, usd: 4.99, label: 'Bag of Gems'},
  {id: 'gems_l', gems: 1200, usd: 9.99, label: 'Box of Gems', tag: 'POPULAR'}, {id: 'gems_xl', gems: 2600, usd: 19.99, label: 'Chest of Gems'},
  {id: 'gems_whale', gems: 7000, usd: 49.99, label: 'Whale Vault', tag: 'BEST VALUE'},
];
export const OFFERS = [
  {id: 'starter', label: 'STARTER PACK', usd: 2.99, once: true, gives: {gems: 250, coins: 2000, bag: 'epic'}},
  {id: 'legend_whale', label: 'THE WHALE', usd: 4.99, gives: {card: ['whale', 1], gems: 100}, rarity: 'legendary'},
];
export const GEM_PRICES = {bag: {rare: 60, epic: 180, legendary: 500}, legendaryCopy: 500, epicCopy: 120, coinsPer100Gems: 1000, skipPerHour: 6};

// The shop's sections, top to bottom: FREE (one gift a day), DAILY DEALS (6 card offers, refreshed 00:00 UTC, seeded per
// player per day from the cards they own), SPECIAL OFFERS (OFFERS + an arena pack the day you reach an arena), BAGS (gems),
// GEMS (real money), COINS (gems), COSMETICS (emote packs, tower skins: gems).
export const SHOP = {
  free: [{coins: 50}, {coins: 100}, {gems: 5}, {cards: 'common', n: 10}],            // the free gift rotates by weekday
  dailySlots: 6,
  copyCoins: {common: 10, rare: 100, epic: 1000, legendary: 40000},                // coins per copy in daily deals
  dealQty: {common: [10, 20, 40], rare: [2, 5, 10], epic: [1, 2], legendary: [1]},
  dealOdds: {common: 0.5, rare: 0.32, epic: 0.15, legendary: 0.03},
  bags: [{tier: 'rare', gems: 60}, {tier: 'epic', gems: 180}, {tier: 'legendary', gems: 500}],
  coinPacks: [{id: 'coins_s', coins: 1000, gems: 60}, {id: 'coins_m', coins: 10000, gems: 500}, {id: 'coins_l', coins: 100000, gems: 4500}],
  arenaPack: {usd: 1.99, gives: {gems: 120, coins: 3000, bag: 'rare'}},             // offered for 24 h after reaching an arena
  cosmetics: [{id: 'emotes_degen', kind: 'emotes', gems: 250, label: 'Degen emote pack'}, {id: 'skin_gold', kind: 'tower', gems: 1500, label: 'Gold tower skin'}],
};

// ACCOUNT LEVEL: XP from upgrading cards (by the level reached) and a little per battle; the level sets my towers' level.
export const XP = {upgrade: [0, 0, 4, 5, 6, 10, 25, 50, 100, 200], win: 4, loss: 1,
  need: [0, 0, 20, 50, 100, 200, 400, 800, 1600, 3000]};                           // need[L] = XP to reach level L (max 9)
// THE DAILY W BAG: 10 Ws in a day (towers taken) -> a free rare bag, resets 00:00 UTC.
export const W_BAG = {need: 10, tier: 'rare'};
// THE TROPHY ROAD between arenas, claimed once from the hub's road: a reward every 100 Clout up to 4000, then five between one
// arena and the next, as the arenas grow apart. A player's claims are these Clout marks: the ones already out there must stay.
export const ROAD = (() => { const ats = []; for (let c = 100; c <= 4000; c += 100) ats.push(c);
  for (let i = 10; i < ARENAS.length; i++) { const a = Math.max(ARENAS[i - 1].at, 4000), b = ARENAS[i].at; for (let j = 1; j <= 5; j++) ats.push(a + (b - a) * j / 5); }
  return ats.map((at, i) => { const k = i + 1; return {at, gives: k % 5 === 0 ? {bag: k % 10 === 0 ? 'epic' : 'rare'} : k % 3 === 0 ? {gems: 10 + k * 2} : {coins: 100 + k * 50}}; }); })();

export const STARTER_DECK = ['useless', 'troll', 'chillguy', 'jeanphil', 'lmao', 'ket', 'fud', 'rug'];   // = the Basement's cards

// copies needed to reach the next level, and its coin price
export const UPGRADE = [null, [2, 20], [4, 50], [10, 150], [20, 400], [50, 1000], [100, 2000], [200, 4000], [400, 8000]];

export const EMOTES = ['cope', 'gg', 'lmao', 'wagmi', 'ngmi', 'seethe'];

// PROFILE PICTURES: a portrait of each character, painted as a player icon (assets/ui/avatars/<id>.webp, small copies in sm/),
// picked in the profile once I own that character's card. The ids are the characters' cards, so a saved pick stays valid.
export const AVATARS = ['troll', 'chillguy', 'jeanphil', 'lmao', 'ket', 'zcat', 'cupsey', 'cate', 'triplet', 'baton', 'chillhouse', 'mensa', 'mitch', 'alon', 'whale', 'useless'];

export const BOT_NAMES = ['xX_DegenKing_Xx', 'paperhands420', 'rugmaster', 'ngmi_andy', 'copelord', 'bagholder_99', 'moonboi', 'exitliquidity',
  'chartwizard', 'wenlambo', 'basementceo', 'gmgn', 'fudbuster', 'apeszn', 'diamondhandz', 'liquidated_larry', 'seedphrase_sam', 'pumpfun_pete'];
