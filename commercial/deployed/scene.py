"""DEPLOYED: a drop ship carries a deck of eight cards over the game's own Backyard BBQ arena.

    blender -b --factory-startup -P scene.py -- --out scene.blend [--pack PACK] [--lib chars.blend] [--assets DIR] [--mon monitor.mp4]

Everything that happens on the ground is a replay of a REAL match: `pack/match.json` was recorded by `sim/record.mjs` from the
game's own rules (hand of 4, queue of 4, Copium, placement rules) with the game's own opponent AI. The ship carries the Thumb's
deck: the four cards in the hand wait at the ramp, the four in the queue wait behind them. When the Thumb plays a card its
character jumps and lands where he tapped; the next card steps up; a copy joins the back of the queue.

Animation time A is match time + 46 s (the film opens with a 46 s briefing before the match starts). `edl.json` lists the
shots (film time, animation time, camera), the dialogue cues and the events for sound and graphics.
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import assets
import fxcard
import sets

ARGS = sys.argv[sys.argv.index('--') + 1:]


def arg(key, default=None):
    return ARGS[ARGS.index(key) + 1] if key in ARGS else default


WORK = os.path.expanduser('~/dep_work')
OUT = arg('--out', WORK + '/scene.blend')
PACK = os.path.abspath(arg('--pack', os.path.join(HERE, 'pack')))
LIB = os.path.abspath(arg('--lib', os.path.expanduser('~/tools/chars.blend')))
ASSETS = os.path.abspath(arg('--assets', os.path.expanduser('~/tools/assets')))
MON = os.path.abspath(arg('--mon', os.path.join(PACK, 'monitor.mp4')))
FX_DIR = os.path.abspath(arg('--fx', os.path.join(HERE, '..', 'final', 'pack', 'fx')))
FPS = 24
PRE = 46.0
DRY = bool(os.environ.get('DRY'))                  # DRY=1: skip loading the characters and saving the .blend; only edl.json is written (seconds, for editing shots)
MATCH = json.load(open(os.path.join(PACK, 'match.json')))
VO = json.load(open(os.path.join(PACK, 'vo', 'vo.json')))
random.seed(11)


def M(t):
    """Match time to animation time."""
    return t + PRE


def F(a):
    return a * FPS + 1


# ---------------------------------------------------------------- coordinates
SHIP = Vector((0.0, 0.0, 20.0))                     # the ship hovers over the river; its ramp faces our side (y < 0)


def H(x, y, z=0.0):
    """Ship-local (x right, y toward the ramp, z up) to world."""
    return (SHIP.x - x, SHIP.y - y, SHIP.z + z)


def hh(dx, dy):
    """Heading (rotation about Z) of a character that looks along the ship-local direction (dx, dy). Characters face -Y at 0."""
    return math.atan2(-dx, dy)


def heading(dx, dy):
    """Heading for a world direction (dx, dy)."""
    return math.atan2(dx, -dy)


def gp(x, z, h=0.0):
    return sets.gp(x, z, h)


# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 6
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.volume_bounces = 0
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.fps = FPS
sc.render.use_motion_blur = False
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
sc.render.image_settings.file_format = 'PNG'
sc.render.threads_mode = 'FIXED'
sc.render.threads = 4

sets.world(os.path.join(ASSETS, 'kloppenheim_06_puresky', 'kloppenheim_06_puresky_2k.exr'), strength=0.7, rotation_deg=84.4)
SUN = sets.sun(heading_deg=25.0, elevation_deg=30.0, energy=3.4, color=(1.0, 0.82, 0.6))
ship = sets.build_ship(os.path.join(PACK, 'tex'))
ship['root'].location = SHIP
ship['root'].rotation_euler = (0, 0, math.pi)
sets.build_exterior(ship)
arena = sets.build_game_arena(os.path.join(PACK, 'game'))

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.dof.use_dof = True
cam.data.dof.aperture_ratio = 1.4
cam.data.clip_start = 0.05
cam.data.clip_end = 700
fill = sets.light('camfill', 'AREA', (0.5, 0.5, 0.1), 0.0, (1.0, 0.9, 0.8), sc.collection, cam, size=0.8)


# ---------------------------------------------------------------- animation helpers (bulk: hundreds of keys per actor)
def animate(obj, path, samples, interp='LINEAR'):
    """samples: [(frame, value)], value a number or a tuple. Writes the F-curves directly (fast)."""
    samples = sorted({frame: value for frame, value in samples}.items())
    if not samples:
        return
    obj.animation_data_create()
    action = obj.animation_data.action or bpy.data.actions.new(obj.name + 'Action')
    obj.animation_data.action = action
    dims = len(samples[0][1]) if isinstance(samples[0][1], (tuple, list, Vector)) else 0
    for index in range(max(dims, 1)):
        curve = action.fcurves.find(path, index=index) or action.fcurves.new(path, index=index)
        curve.keyframe_points.add(len(samples))
        flat = []
        for frame, value in samples:
            flat += [frame, value[index] if dims else value]
        curve.keyframe_points.foreach_set('co', flat)
        for point in curve.keyframe_points:
            point.interpolation = interp
        curve.update()


def unwrap(previous, wanted):
    while wanted - previous > math.pi:
        wanted -= math.tau
    while wanted - previous < -math.pi:
        wanted += math.tau
    return wanted


class Actor:
    """A character (or a plain prop) on a rig empty; positions and headings are keyed in animation time."""

    def __init__(self, label, char=None, team=None):
        self.label = label
        self.rig = bpy.data.objects.new('RIG-' + label, None)
        self.bob = bpy.data.objects.new('BOB-' + label, None)
        for obj in (self.rig, self.bob):
            sc.collection.objects.link(obj)
            obj.rotation_mode = 'XYZ'
        self.bob.parent = self.rig
        self.char = char
        self.arm = None
        self.clips = {}
        if char:
            for root in char['roots']:
                root.parent = self.bob
                root.rotation_mode = 'XYZ'
                root.location = (0, 0, 0)
                root.rotation_euler = (0, 0, 0)
            self.arm = char['armature']
            if self.arm:
                self.arm.animation_data_create()
            self.clips = char['clips']
        self.loc, self.rot, self.vis, self.items = [], [], [], []
        self.pos, self.head, self.tilt = Vector((0, 0, 0)), 0.0, 0.0
        self.sched = []
        self.ring = None
        if team is not None:
            self.add_ring(team)

    def add_ring(self, team):
        glow = sets.TEAM_RED if team == 1 else sets.TEAM_GREEN
        mat = sets.material(f'ring{team}', glow, rough=0.5, emit=glow, strength=1.0)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.62, minor_radius=0.045, major_segments=32, minor_segments=8)
        ring = bpy.context.active_object
        ring.name = 'ring-' + self.label
        for old in list(ring.users_collection):
            old.objects.unlink(ring)
        sc.collection.objects.link(ring)
        ring.data.materials.append(mat)
        ring.parent = self.rig
        ring.location = (0, 0, 0.04)
        ring.visible_shadow = False
        self.ring = ring

    # -- keys
    def put(self, a, pos=None, head=None, tilt=None):
        if pos is not None:
            self.pos = Vector(pos)
        if head is not None:
            self.head = unwrap(self.head, head)
        if tilt is not None:
            self.tilt = tilt
        self.loc.append((F(a), tuple(self.pos)))
        self.rot.append((F(a), (self.tilt, 0.0, self.head)))

    def hold(self, a):
        self.put(a)

    def go(self, a, target, speed=1.4, clip='walk', then='idle'):
        """Walk to `target` (world coordinates) from the current position; returns the arrival time."""
        target = Vector(target)
        dist = (target - self.pos).length
        self.hold(a)
        self.put(a + 0.2, head=heading(target.x - self.pos.x, target.y - self.pos.y))
        arrive = a + 0.2 + dist / speed
        self.play(a, clip)
        self.put(arrive, pos=target)
        if then:
            self.play(arrive, then)
        return arrive

    def play(self, a, name, speed=1.0, offset=0.0):
        self.items.append((a, name if name in self.clips else 'idle', speed, offset))

    def show(self, a_on, a_off=None):
        self.vis.append((a_on, 1, a_off))

    def finish(self, end):
        """Write all keys: rig transform, visibility and the clip strips."""
        if self.loc:
            animate(self.rig, 'location', self.loc)
            animate(self.rig, 'rotation_euler', self.rot)
        steps = []
        for a_on, _, a_off in self.vis:
            steps += [(F(a_on) - 1, 0), (F(a_on), 1)]
            if a_off is not None:
                steps += [(F(a_off), 1), (F(a_off) + 1, 0)]
        if not steps:
            steps = [(1, 1)]
        elif steps[0][1] != 0:
            steps.insert(0, (steps[0][0] - 1, 0))
        else:
            pass
        animate(self.rig, 'scale', [(frame, (v, v, v) if v else (0.0001, 0.0001, 0.0001)) for frame, v in self._flatten(steps)], 'CONSTANT')
        if self.arm:
            self.items.sort(key=lambda item: item[0])
            for index, (a, name, speed, offset) in enumerate(self.items):
                f0 = F(a)
                f1 = F(self.items[index + 1][0]) if index + 1 < len(self.items) else F(end)
                if f1 - f0 < 1:
                    continue
                action = self.clips[name]
                a0, a1 = action.frame_range
                track = self.arm.animation_data.nla_tracks.new()
                strip = track.strips.new(f'{name}_{index}', int(f0), action)
                strip.action_frame_start = a0 + offset * (a1 - a0)
                strip.action_frame_end = a1
                strip.scale = (FPS / 30.0) / speed
                strip.repeat = max(0.01, (f1 - f0) / ((a1 - strip.action_frame_start) * strip.scale))
                strip.extrapolation = 'NOTHING'
                strip.blend_type = 'REPLACE'
                strip.use_auto_blend = False
                strip.blend_in = 3 if index else 0

    @staticmethod
    def _flatten(steps):
        """Keep the last value for each frame, in frame order."""
        return sorted({frame: v for frame, v in steps}.items())


def talk_bob(actor, a0, a1):
    """A small nod and bounce while a character speaks."""
    samples, rots = [], []
    t = a0
    while t < a1:
        u = (t - a0) * 9.0
        samples.append((F(t), (0, 0, 0.022 * abs(math.sin(u)))))
        rots.append((F(t), (math.radians(3.5) * math.sin(u * 0.7), 0, math.radians(3) * math.sin(u * 0.5))))
        t += 0.09
    samples.append((F(a1 + 0.1), (0, 0, 0)))
    rots.append((F(a1 + 0.1), (0, 0, 0)))
    actor.bob_loc = getattr(actor, 'bob_loc', []) + samples
    actor.bob_rot = getattr(actor, 'bob_rot', []) + rots


def write_bobs(actors):
    for actor in actors:
        if getattr(actor, 'bob_loc', None):
            animate(actor.bob, 'location', actor.bob_loc, 'BEZIER')
            animate(actor.bob, 'rotation_euler', actor.bob_rot, 'BEZIER')


# ================================================================ the replay
FR = MATCH['frames']
LOG = MATCH['log']
EVENTS_SIM = MATCH['events']
PLAYS = [item for item in LOG if item['what'] == 'thumb']
DOWNS = [item for item in LOG if item['what'] == 'tower_down']
SPAWN = {e['id']: e for e in EVENTS_SIM if e['type'] == 'spawn'}
LANDED = {e['id']: e['t'] for e in EVENTS_SIM if e['type'] == 'landed'}
for e in EVENTS_SIM:
    if e['type'] == 'spawn':
        LANDED.setdefault(e['id'], e['t'] + 1.03)             # (a unit deployed in the last second never lands in the recording)
UID = {'firesale': 'useless', 'uselessarmy': 'useless'}
# no two characters may overlap on screen: the game lets units touch, the film pushes them apart (a few frames, at most a few tenths of a tile)
RADIUS = json.load(open(os.path.join(PACK, 'radii.json')))
SEPARATED = 0
for frame in FR:
    live = [e for e in frame['e'] if e[1] == 'u' and not e[9]]
    for _pass in range(5):
        moved = False
        for i in range(len(live)):
            for j in range(i + 1, len(live)):
                a, b = live[i], live[j]
                lim = 0.95 * (RADIUS.get(a[2], 0.4) + RADIUS.get(b[2], 0.4)) + 0.08
                dx, dz = b[4] - a[4], b[5] - a[5]
                d = math.hypot(dx, dz)
                if d < lim:
                    if d < 1e-4:
                        dx, dz, d = 1.0, 0.3 * ((a[0] + b[0]) % 3 - 1), 1.0
                    push = (lim - d) / 2.0
                    a[4], a[5] = a[4] - dx / d * push, a[5] - dz / d * push
                    b[4], b[5] = b[4] + dx / d * push, b[5] + dz / d * push
                    moved = True
        if not moved:
            break
        SEPARATED += 1
print('SEPARATION passes', SEPARATED)
ENT = {}
for frame in FR:
    for e in frame['e']:
        if e[1] != 'u':
            continue
        ENT.setdefault(e[0], {'card': e[2], 'team': e[3], 'samples': []})['samples'].append((frame['t'], e[4], e[5], e[6], e[7], e[8], e[9], e[10]))


def ent_at(eid, t):
    """Position (game x, z) of a simulated unit at match time t (clamped to its life)."""
    samples = ENT[eid]['samples']
    for s0, s1 in zip(samples, samples[1:]):
        if s0[0] <= t <= s1[0]:
            u = (t - s0[0]) / max(1e-6, s1[0] - s0[0])
            return (s0[1] + (s1[1] - s0[1]) * u, s0[2] + (s1[2] - s0[2]) * u)
    return (samples[0][1], samples[0][2]) if t < samples[0][0] else (samples[-1][1], samples[-1][2])


# the cast: every unit that ever exists, plus the clones that join the queue
thumb_spawns = []
for play in PLAYS:
    if play['card'] == 'airdrop':
        continue
    match_spawn = next((e for e in EVENTS_SIM if e['type'] == 'spawn' and e['team'] == 0 and e['card'] == play['card'] and abs(e['t'] - play['t']) < 0.2), None)
    thumb_spawns.append((play, match_spawn))
ORDER0 = MATCH['plan']['order0']
need = [UID.get(card, card) for card in ORDER0 if card != 'airdrop']                       # the first eight (without the crate)
need += [UID.get(play['card'], play['card']) for play, _ in thumb_spawns]                   # one clone per play
enemy_ids = [eid for eid, info in ENT.items() if info['team'] == 1]
need += [UID.get(ENT[eid]['card'], ENT[eid]['card']) for eid in enemy_ids]
need.append('walter')
if DRY:
    chars = [{'id': uid, 'roots': [], 'armature': None, 'clips': {}, 'collection': None, 'height': 1.7} for uid in need]
else:
    chars = assets.load_many(LIB, need, sc.collection)


def dedupe_data():
    """Every library pass appends its own copy of the textures and materials (339 images for 43 distinct ones). Different
    characters reuse names like `base_0`, so copies are matched by content (the packed file) and never by name."""
    import hashlib
    first = {}
    for img in list(bpy.data.images):
        if img.packed_file:
            key = hashlib.md5(bytes(img.packed_file.data)).hexdigest()
        else:
            key = (img.filepath, tuple(img.size))
        first.setdefault(key, img)
        img['_canon'] = first[key].name
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and node.image.get('_canon') in bpy.data.images:
                    node.image = bpy.data.images[node.image['_canon']]
    # materials: a copy is the same when it has the same name stem and uses the same images
    import re
    pattern = re.compile(r'^(.*)\.\d{3}$')
    def signature(mat):
        if not mat.use_nodes:
            return None
        return tuple(sorted(node.image.name for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image))
    canon = {}
    for mat in sorted(bpy.data.materials, key=lambda m: m.name):
        stem = pattern.sub(r'\1', mat.name)
        key = (stem, signature(mat))
        if key[1] is not None and key not in canon:
            canon[key] = mat
    for obj in bpy.data.objects:
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            key = (pattern.sub(r'\1', mat.name), signature(mat))
            if key in canon and canon[key] is not mat:
                slot.material = canon[key]
    bpy.data.orphans_purge(do_recursive=True)


if not DRY:
    dedupe_data()
def smooth_hero(actor):
    """Subdivide at render time (only the eight cards waiting on the ship and Sarge: every subdivided mesh costs ~130 MB."""
    for obj in (actor.char['collection'].all_objects if actor.char['collection'] else []):
        if obj.type == 'MESH' and len(obj.data.vertices) > 500:
            mod = obj.modifiers.new('subd', 'SUBSURF')
            mod.levels = 0
            mod.render_levels = 1
            mod.uv_smooth = 'PRESERVE_BOUNDARIES'


pool = list(chars)


def take(uid):
    for index, char in enumerate(pool):
        if char['id'] == uid:
            return pool.pop(index)
    raise KeyError(uid)


ALL = []


def new_actor(label, uid, team=None):
    actor = Actor(label, take(uid) if uid else None, team)
    ALL.append(actor)
    return actor


# ---------------------------------------------------------------- the ship: hand slots (near the ramp), queue slots (behind)
HS = [(-1.65, 3.4), (-0.55, 3.4), (0.55, 3.4), (1.65, 3.4)]         # the hand: a row across the ship, facing the ramp
QS = [(-1.7, 1.6), (-1.7, 0.3), (-1.7, -1.0), (-1.7, -2.3)]         # the bench: a line along the left wall
RAMP_TOP = (0.0, 5.9)
RAMP_END = H(0.0, 8.5, -0.6)
FALL = 1.0                                              # seconds from the end of the ramp to the ground (20 m)
GRAV = 2 * 20.6 / FALL ** 2


def crate_actor(label):
    actor = Actor(label)
    wood = sets.add_bump(sets.material('crate' + label, (0.42, 0.29, 0.16), rough=0.8), 14.0, 0.5)
    box = sets.box('crate', (0.8, 0.8, 0.8), (0, 0, 0.4), wood, sc.collection, actor.bob, bevel=0.03)
    label_mat = sets.image_material('airdrop_label' + label, os.path.join(PACK, 'tex', 'airdrop.png'))
    for dx, dy, rot in ((0, -0.41, (math.pi / 2, 0, 0)), (0, 0.41, (math.pi / 2, 0, math.pi)), (-0.41, 0, (math.pi / 2, 0, -math.pi / 2)),
                        (0.41, 0, (math.pi / 2, 0, math.pi / 2))):
        sets.plane('airdrop_label', 0.8, 0.8, (dx, dy, 0.4), label_mat, sc.collection, actor.bob, rot=rot)
    ALL.append(actor)
    return actor


hand, queue = [], []
for index, card in enumerate(ORDER0[:4]):
    actor = crate_actor(f'crate{index}') if card == 'airdrop' else new_actor(f'{card}-h{index}', UID.get(card, card))
    actor.card = card
    if actor.char:
        smooth_hero(actor)
    actor.put(0, H(*HS[index]), hh(0, 1))
    actor.show(0)
    actor.play(0, 'idle', 0.8 + 0.3 * random.random())
    hand.append(actor)
for index, card in enumerate(ORDER0[4:]):
    actor = crate_actor(f'crate-q{index}') if card == 'airdrop' else new_actor(f'{card}-q{index}', UID.get(card, card))
    actor.card = card
    if actor.char:
        smooth_hero(actor)
    actor.put(0, H(*QS[index]), hh(0, 1))
    actor.show(0)
    actor.play(0, 'idle', 0.8 + 0.3 * random.random())
    queue.append(actor)
sarge = new_actor('sarge', 'walter')
smooth_hero(sarge)
SARGE_AT = (2.15, 5.45)                              # beside the ramp: the jumpers run down the middle
sarge.put(0, H(*SARGE_AT), hh(-2.15, -2.05))
sarge.show(0)
sarge.play(0, 'idle')

SHOTS, CUES, EVENTS = [], [], []
CUT = 0.0
FILM = 0.0


def event(kind, a, **extra):
    EVENTS.append(dict(kind=kind, a=round(a, 3), **extra))


def free_fall(actor, a_jump, a_land, start, end, spin=1.0):
    """The cartoon jump: horizontal at constant speed, vertical under gravity, one tumble."""
    start, end = Vector(start), Vector(end)
    steps = max(4, int((a_land - a_jump) * FPS / 2))
    actor.put(a_jump, start, heading(end.x - start.x, end.y - start.y), 0.0)
    for index in range(1, steps + 1):
        u = index / steps
        pos = start.lerp(end, u)
        pos.z = start.z + (end.z - start.z) * u * u
        actor.put(a_jump + (a_land - a_jump) * u, pos, tilt=math.tau * spin * u if index < steps else 0.0)


JUMPS = []                                              # (play, actor, a_jump, a_land, target)
ship_events = []
for play, spawn in thumb_spawns + [(p, None) for p in PLAYS if p['card'] == 'airdrop']:
    pass


def process_play(play, spawn):
    """The ship's side of one real play: slot, jump, step up, a copy joins the queue."""
    global hand, queue
    t = M(play['t'])
    slot = play['slot']
    jumper = hand[slot]
    stepper = queue.pop(0)
    hand[slot] = stepper
    # the jumper: to the ramp, a jump that lands where the Thumb tapped
    if spawn is not None:
        a_land = M(LANDED[spawn['id']])
    else:
        a_land = t + 1.0
    target = gp(play['x'], play['z'], 0.0)
    a_jump = a_land - FALL
    run = jumper.go(a_jump - 0.9, H(*RAMP_TOP), speed=3.4, clip='run', then=None) if jumper.char else None
    if not jumper.char:                                 # the crate slides to the ramp and is kicked off
        jumper.put(a_jump - 0.9)
        jumper.put(a_jump - 0.2, H(*RAMP_TOP))
    jumper.put(a_jump - 0.05, H(*RAMP_TOP))
    jumper.put(a_jump, RAMP_END)
    jumper.play(a_jump - 0.05, 'run' if jumper.char else 'idle')
    start = Vector(RAMP_END)
    land_pos = Vector(target) if spawn is not None else Vector(target) + Vector((0, 0, 0.4))
    free_fall(jumper, a_jump, a_land, start, land_pos, spin=1.0 if jumper.char else 2.0)
    if jumper.char:
        jumper.play(a_jump + 0.2, 'emote', 1.4)
    event('klaxon', a_jump - 1.0)
    event('jump', a_jump - 0.05, card=play['card'], slot=slot)
    event('land', a_land, card=play['card'], x=play['x'], z=play['z'], spell=spawn is None)
    if not jumper.char:
        jumper.vis[-1] = (jumper.vis[-1][0], 1, a_land + 0.15)
    jumper.land_a = a_land
    jumper.land_target = (play['x'], play['z'])
    jumper.spawn = spawn
    # the next card steps up into the vacant hand slot, the others shuffle forward, a copy pops in at the back
    a_step = a_jump - 0.6
    waypoint = stepper.go(a_step, H(HS[slot][0], 2.2), speed=1.7, then=None)       # along the aisle behind the row, never through it
    stepper.go(waypoint, H(*HS[slot]), speed=1.7, then='idle')
    stepper.put(a_step + 2.4, head=hh(0, 1))
    for index, other in enumerate(queue):
        other.go(a_step + 0.3, H(*QS[index]), speed=1.4, then='idle')
        other.put(a_step + 1.6, head=hh(0, 1))
    clone = crate_actor(f'crate-c{len(ALL)}') if play['card'] == 'airdrop' else new_actor(f"{play['card']}-c{len(ALL)}", UID.get(play['card'], play['card']))
    clone.card = play['card']
    clone.put(a_step + 1.45, H(*QS[3]), hh(0, 1))
    clone.show(a_step + 1.45)
    clone.play(a_step + 1.45, 'idle', 0.8 + 0.3 * random.random())
    event('card_pop', a_step + 1.45, card=play['card'])
    queue.append(clone)
    JUMPS.append((play, jumper, a_jump, a_land, target))
    return jumper


JUMPER_BY_PLAY = {}
for play in PLAYS:
    spawn = next((s for p, s in thumb_spawns if p is play), None)
    JUMPER_BY_PLAY[play['t']] = process_play(play, spawn)


# ---------------------------------------------------------------- the ground: Thumb units continue from their landing, the enemy drops in
def clip_for(info, previous, current, dt):
    moving = current[4]
    if not moving:
        return 'idle'
    speed = math.hypot(current[1] - previous[1], current[2] - previous[2]) / max(dt, 1e-3)
    return 'run' if speed > 2.6 else 'walk'


HIT_TIMES = {}
for e in EVENTS_SIM:
    if e['type'] == 'hit':
        HIT_TIMES.setdefault(e['id'], []).append(e['t'])
    if e['type'] == 'shoot':
        HIT_TIMES.setdefault(e['id'], []).append(e['t'])


def animate_unit(actor, eid, from_t=None, drop=False):
    """Drive an actor along a simulated unit's track (game coordinates -> world)."""
    info = ENT[eid]
    samples = info['samples']
    prev = None
    first = True
    death_a = None
    for s in samples:
        t = s[0]
        if from_t is not None and t < from_t:
            continue
        a = M(t)
        x, z, face, moving, hp, dead, state = s[1], s[2], s[3], s[4], s[5], s[6], s[7]
        pos = gp(x, z, 0.0)
        if drop and state == 'deploy':
            u = (t - samples[0][0]) / 1.03
            pos = gp(x, z, 12.0 * max(0.0, 1.0 - u * u))
        actor.put(a, pos, face)
        if first:
            actor.show(a)
            first = False
        if prev is not None and not dead:
            name = clip_for(info, prev, s, t - prev[0])
            if not actor.items or actor.items[-1][1] != name:
                actor.play(a, name, 1.0)
        elif prev is None:
            actor.play(a, 'idle')
        if dead and death_a is None:
            death_a = a
            actor.play(a, 'die', 1.0)
        prev = s
    end = M(samples[-1][0])
    off = None if death_a is None else death_a + 2.4
    if actor.vis:                                                    # a jumper: already visible since the ship
        actor.vis[-1] = (actor.vis[-1][0], 1, off)
    else:
        actor.vis.append((M(samples[0][0]), 1, off))
    for t in HIT_TIMES.get(eid, []):
        if (from_t is None or t >= from_t) and t < samples[-1][0] - 0.1 and (death_a is None or M(t) < death_a - 0.3):
            actor.play(M(t) - 0.15, 'attack1', 1.3)
            actor.play(M(t) + 0.55, clip_for(info, samples[0], samples[min(1, len(samples) - 1)], 0.1) if False else 'idle')


# the Thumb's own: continue the jumper's track from the landing (the track is the unit that was deployed)
for play, spawn in thumb_spawns:
    jumper = JUMPER_BY_PLAY[play['t']]
    if spawn is not None:
        animate_unit(jumper, spawn['id'], from_t=LANDED[spawn['id']])
for eid in enemy_ids:
    card = ENT[eid]['card']
    actor = new_actor(f'e{eid}-{card}', UID.get(card, card), 1)
    actor.vis = []
    animate_unit(actor, eid, drop=True)
for play, jumper, a_jump, a_land, target in JUMPS:                 # rings under the Thumb's units show their team
    if jumper.char:
        jumper.add_ring(0)

# ---------------------------------------------------------------- towers: HP in the recording, ruins after tower_down
TOWER_KEY = {}
for (team, kind, lane), info in arena['towers'].items():
    TOWER_KEY[(team, kind, 0 if lane < 0 else lane)] = info
for down in DOWNS:
    lane = 0 if down['x'] < 9 else 1
    info = TOWER_KEY[(down['team'], down['tower'], 0 if down['tower'] == 'hq' else lane)]
    a_down = M(down['t'])
    for holder, visible in ((info['alive'], False), (info['ruin'], True)):
        for obj in [holder] + list(holder.children_recursive):
            obj.hide_render = False
        animate(holder, 'scale', [(1, (1, 1, 1) if not visible else (0.0001,) * 3), (F(a_down), (0.0001,) * 3 if not visible else (1, 1, 1))], 'CONSTANT')
    event('tower_down', a_down, team=down['team'], tower=down['tower'], x=down['x'], z=down['z'])
CARDS = []
for index, down in enumerate(DOWNS):
    card = fxcard.card(os.path.join(FX_DIR, 'explosion.mp4'), location=gp(down['x'], down['z'], 3.2), height=9.0, cam=cam, strength=1.8, name=f'fx_boom{index}')
    card.data.materials[0].node_tree.nodes['Image Texture'].name = 'clip'
    CARDS.append(dict(name=f'fx_boom{index}', t0=round(M(down['t']), 3), fps=59.94, n=120))
    light = sets.light(f'boom_light{index}', 'POINT', gp(down['x'], down['z'], 3.0), 0.0, (1.0, 0.5, 0.15), sc.collection, size=1.5)
    for a, energy in ((M(down['t']) - 0.05, 0.0), (M(down['t']) + 0.08, 60000.0), (M(down['t']) + 0.8, 9000.0), (M(down['t']) + 2.2, 0.0)):
        light.data.energy = energy
        light.data.keyframe_insert('energy', frame=F(a))

# the ship's monitor shows the Thumb's screen (the HUD from the recording as a video)
mon_img = bpy.data.images.load(MON)
mon_mat = bpy.data.materials.new('monitor')
mon_mat.use_nodes = True
tree = mon_mat.node_tree
bsdf = tree.nodes['Principled BSDF']
tex = tree.nodes.new('ShaderNodeTexImage')
tex.image = mon_img
tex.name = 'clip'
tex.image_user.frame_duration = mon_img.frame_duration
tex.image_user.use_auto_refresh = True
tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
tree.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 1.2
sx, sy, sz = ship['screen_at']
screen_obj = sets.plane('fx_screen', ship['screen_size'][0], ship['screen_size'][1], (sx, sy, sz), mon_mat, ship['col'], ship['root'], rot=(math.pi / 2, 0, math.pi))
CARDS.append(dict(name='fx_screen', t0=0.0, fps=10, n=mon_img.frame_duration, always=True))
sets.light('screen_light', 'AREA', (sx, sy + 0.3, sz), 60.0, (0.6, 0.4, 1.0), ship['col'], ship['root'], size=1.2, rot=(-math.pi / 2, 0, 0))

# ---------------------------------------------------------------- the ship: ramp and jump lights
hinge = ship['hinge']
hinge.rotation_euler = (math.radians(90), 0, 0)
animate(hinge, 'rotation_euler', [(1, (math.radians(90), 0, 0)), (F(M(PLAYS[0]['t']) - 3.4), (math.radians(90), 0, 0)),
                                  (F(M(PLAYS[0]['t']) - 2.2), (math.radians(-14), 0, 0))], 'LINEAR')


def lamp(name, a, on):
    mat, light = ship['lenses'][name]
    socket = mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    socket.default_value = 8.0 if on else 0.0
    socket.keyframe_insert('default_value', frame=F(a))
    light.data.energy = (70.0 if name == 'green' else 110.0) if on else 0.0
    light.data.keyframe_insert('energy', frame=F(a))


lamp('red', 0, True)
lamp('green', 0, False)
for play, jumper, a_jump, a_land, target in JUMPS:
    lamp('red', a_jump - 1.5, False)
    lamp('green', a_jump - 1.5, True)
    lamp('green', a_jump + 0.4, False)
    lamp('red', a_jump + 0.4, True)
for name in ('red', 'green'):
    mat, light = ship['lenses'][name]
    for owner in (mat.node_tree, light.data):
        for curve in owner.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = 'CONSTANT'
for lamp_obj in ship['ceiling']:
    lamp_obj.data.energy = 55.0

# ---------------------------------------------------------------- airdrop coins (the one real airdrop spell of the Thumb that hits ground)
gold = sets.material('coin', (1.0, 0.72, 0.15), rough=0.25, metal=1.0)
for play in PLAYS:
    if play['card'] != 'airdrop':
        continue
    a_hit = M(play['t']) + 0.6
    random.seed(int(play['t'] * 10))
    for index in range(26):
        coin = sets.cylinder('coin', 0.2, 0.05, (0, 0, 0), gold, sc.collection, verts=16)
        angle, radius = random.uniform(0, math.tau), math.sqrt(random.random()) * 3.4
        x, z = play['x'] + math.cos(angle) * radius, play['z'] + math.sin(angle) * radius
        a0 = a_hit + random.uniform(0.0, 0.9)
        samples = []
        for step in range(7):
            u = step / 6
            samples.append((F(a0 + 0.9 * u), (*gp(x, z, 0.25 + 18.0 * (1 - u ** 1.6))[:2], 0.25 + 18.0 * (1 - u ** 1.6))))
        animate(coin, 'location', samples)
        animate(coin, 'rotation_euler', [(F(a0 + 0.9 * u / 6), (u * 9.0 + index, u * 5.0, index)) for u in range(7)])
        animate(coin, 'scale', [(1, (0.0001,) * 3), (F(a0) - 1, (0.0001,) * 3), (F(a0), (1, 1, 1)), (F(a0 + 2.6), (1, 1, 1)), (F(a0 + 2.7), (0.0001,) * 3)], 'CONSTANT')
    event('coins', a_hit, x=play['x'], z=play['z'])

# ---------------------------------------------------------------- tracers: tower shots and ranged shots
tracer_mat = sets.material('tracer', (1.0, 0.9, 0.5), rough=0.3, emit=(1.0, 0.8, 0.3), strength=6.0)
impacts = [e for e in EVENTS_SIM if e['type'] == 'impact']
count = 0
for e in EVENTS_SIM:
    if e['type'] not in ('tower_shot', 'shoot') or count > 260:
        continue
    if e['type'] == 'tower_shot':
        pos = {1: (3.5, 25.5), 2: (14.5, 25.5), 3: (9, 29.5), 4: (3.5, 6.5), 5: (14.5, 6.5), 6: (9, 2.5)}.get(e['id'])
        if pos is None or e.get('target') not in ENT:
            continue
        a = M(e['t'])
        tx, tz = ent_at(e['target'], e['t'] + 0.25)
        start = gp(pos[0], pos[1], 4.6 if e['id'] not in (3, 6) else 5.4)
        end = gp(tx, tz, 1.0)
    else:
        if e['id'] not in ENT:
            continue
        impact = next((i for i in impacts if i['proj'] == e['proj'] and 0 <= i['t'] - e['t'] < 1.2), None)
        if impact is None:
            continue
        a = M(e['t'])
        sx_, sz_ = ent_at(e['id'], e['t'])
        start = gp(sx_, sz_, 1.2)
        end = gp(impact['x'], impact['z'], 1.0)
        e = dict(e, t=e['t'])
        travel = max(0.12, impact['t'] - e['t'])
    travel = 0.25 if e['type'] == 'tower_shot' else travel
    ball = sets.sphere('shot', 0.13, (0, 0, 0), tracer_mat, sc.collection)
    animate(ball, 'location', [(F(a), start), (F(a + travel), end)])
    animate(ball, 'scale', [(1, (0.0001,) * 3), (F(a) - 1, (0.0001,) * 3), (F(a), (1, 1, 1)), (F(a + travel), (1, 1, 1)), (F(a + travel) + 1, (0.0001,) * 3)], 'CONSTANT')
    count += 1

# ================================================================ shots
CLOSED = ['ARENA', 'NOSE']                                      # nothing outside is visible through a shut ramp
HAZE_SHOTS = {'hold_wide'}
BLUR_SHOTS = set()


def shot(name, end, p0, l0, lens, p1=None, l1=None, space='ship', speed=1.0, fstop=2.8, hand=('INVESTIGATION', 0.35), shake=0.0, fill_power=0.0,
         hide=None, ec=0, lens1=None, a_start=None, phone=False, res=None, keep=None):
    """A shot from the cursor to animation time `end` (a_start jumps the cursor first)."""
    global CUT, FILM
    if a_start is not None:
        CUT = a_start
    if space == 'ship':
        convert = lambda p: list(H(*p))
    elif space == 'game':
        convert = lambda p: list(gp(*p))
    else:
        convert = lambda p: list(p)
    duration = (end - CUT) / speed
    assert duration > 0.01, (name, CUT, end)
    hide = list(hide) if hide is not None else ['NOSE', 'haze']
    if name not in HAZE_SHOTS and 'haze' not in hide:
        hide.append('haze')
    SHOTS.append(dict(name=name, t0=round(FILM, 4), t1=round(FILM + duration, 4), a0=round(CUT, 4), s0=speed, p0=convert(p0), p1=convert(p1 or p0),
                      l0=convert(l0), l1=convert(l1 or l0), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake, ec=ec, focus=None,
                      hand=list(hand) if hand else None, fill=fill_power, hide=hide, mb=name in BLUR_SHOTS, game=(space == 'game'), phone=phone, res=res, keep=keep))
    CUT = end
    FILM += duration


CUE_LIST = []


def say(line_id, a, actor=None):
    """Place a recorded line at animation time `a`; returns its end."""
    end = a + VO[line_id]['dur']
    CUE_LIST.append((line_id, a))
    if actor is not None:
        talk_bob(actor, a, end)
    return end


def character(label):
    return next(actor for actor in ALL if actor.label == label)


def cast_of(card, which=0):
    """The ship actor for a card: the one standing in the hand or queue at the start."""
    return next(actor for actor in ALL if getattr(actor, 'card', None) == card and actor.label.startswith(card))


cupsey_a, ket_a, chill_a, house_a, dope_a, lmao_a, pudgy_a = (cast_of(c) for c in ('cupsey', 'ket', 'chillguy', 'chillhouse', 'dope', 'lmao', 'pudgy'))
EYE = 1.35


def cu(name, end, actor_pos, side, lens=42, dist=1.9, up=0.0, shake=0.3, fill_power=40, **kw):
    """Close-up of a ship actor at a ship-local position, from the front-left (side -1) or front-right (+1)."""
    x, y = actor_pos
    shot(name, end, (x + side * 0.55, y - dist * 0.9, EYE + 0.05 + up), (x, y, EYE + up - 0.02), lens, hide=CLOSED + kw.pop('also', []), fill_power=fill_power,
         shake=shake, **kw)


def ship_two(name, end, lens=32, **kw):
    shot(name, end, (0.0, -1.2, 1.55), (0.0, 3.8, 1.3), lens, p1=(0.0, -0.6, 1.5), hide=kw.pop('hide', CLOSED), fill_power=25, **kw)


# ---------------------------------------------------------------- scene plan: dialogue anchors (match time) and shots
def beat(line_id, actor, cams, a_at=None, lead=0.12, pad=0.3):
    """A line with its shot(s): starts `lead` after the cursor (or at `a_at`) and the shots end `pad` after the line."""
    start = (CUT + lead) if a_at is None else a_at
    end = say(line_id, start, actor)
    stop = end + pad
    first = CUT
    for index, cam_fn in enumerate(cams):
        cam_fn(first + (stop - first) * (index + 1) / len(cams))
    return stop


RAMP_OPEN_A = M(PLAYS[0]['t']) - 3.4


def hides():
    """Shut ramp: the arena below is invisible (saves render time); open ramp: it is the view through the door."""
    return ['NOSE'] if CUT >= RAMP_OPEN_A else CLOSED


def face(actor_pos, side, lens, dist=1.9, up=0.0, name='cu', shake=0.3, fill_power=40, hide=None, ship_side=1.0, keep=None):
    """Close-up of a ship character. The hand stands in a row facing the ramp: shoot it from the front. The bench is a line
    along the left wall: shoot it from the aisle, three-quarter view."""
    x, y = actor_pos
    if (x, y) in QS or x < -1.6 and y < 2.0:
        cam_pos = (x + 1.9, y + 0.55 * side, EYE + 0.15 + up)
        distance = 1.9
    else:
        cam_y = min(y + dist, 5.3)
        cam_pos = (x + side * 0.3, cam_y, EYE + 0.1 + up)
        distance = cam_y - y
    scale = distance / dist if dist else 1.0
    def fn(end):
        shot(f'{name}', end, cam_pos, (x, y, EYE + up), lens * scale * 0.78, hide=hides() if hide is None else hide, fill_power=fill_power, shake=shake, keep=keep)
    return fn


def sarge_face(side, lens=55, dist=4.0, up=0.15, name='sarge'):
    """Sarge stands at the ramp facing the crew: the camera shoots him from the aisle."""
    def fn(end):
        shot(name, end, (SARGE_AT[0] - 0.9 + side * 0.12, SARGE_AT[1] - dist, EYE + 0.45 + up), (SARGE_AT[0], SARGE_AT[1], EYE + up), lens, hide=hides(), fill_power=60, shake=0.3, fstop=2.4, keep=['sarge'])
    return fn


def view(name, p0, l0, lens, p1=None, l1=None, hide=None, **kw):
    def fn(end):
        shot(name, end, p0, l0, lens, p1=p1, l1=l1, hide=hides() if hide is None else hide, **kw)
    return fn


import monitor
MATCH_STATE = monitor.State(MATCH)


def seat(card, a):
    """Ship-local position of a card's character at match animation time a (hand slot or queue slot)."""
    hand_now, queue_now = list(MATCH_STATE.hand0), list(MATCH_STATE.queue0)
    for play in PLAYS:
        if M(play['t']) <= a:
            hand_now, queue_now = play['hand'], play['queue']
    if card in hand_now:
        return HS[hand_now.index(card)]
    if card in queue_now:
        return QS[queue_now.index(card)]
    return QS[0]


def lface(card, a_hint, side, lens, dist=2.3, up=0.0, name=None, **kw):
    """Front close-up of whoever stands in `card`'s seat at animation time a_hint."""
    return face(seat(card, a_hint), side, lens, dist, up, name or f'{card}_cu', keep=[card], **kw)


# ---- A. the briefing (before the match; the sim has not started)
a_start = M(-45.9)
CUT = a_start
p01_end = say('p01', a_start + 0.4)
shot('ext_ship', p01_end + 0.2, (-30.0, -27.0, 23.0), (0, 0, 20.5), 38, p1=(-24.0, -21.0, 24.5), space='world', fstop=5.6, hand=('INVESTIGATION', 0.5), hide=['haze'])
event('title', a_start + 0.5, text='SOMEWHERE ABOVE ARENA 2')
shot('hold_wide', CUT + 3.2, (0.0, -5.2, 1.95), (0.0, 3.5, 1.2), 24, p1=(0.0, -3.9, 1.7), hide=CLOSED, fstop=4.0, fill_power=20)
event('title_card', CUT - 2.9)
beat('s01', sarge, [sarge_face(-1, 50, 4.2, name='sarge_1')])
beat('e01', cupsey_a, [lface('cupsey', CUT, 1, 40, name='egg_1')])
beat('s02', sarge, [sarge_face(1, 58, 4.2, name='sarge_2a'), view('crew_row', (-1.9, 5.2, 1.5), (0.0, 2.4, 1.3), 30, p1=(-1.6, 5.1, 1.5), fill_power=40, name='crew_row') if False else sarge_face(-1, 46, 3.4, name='sarge_2b')])
beat('e02', cupsey_a, [lface('cupsey', CUT, -1, 44, name='egg_2')])
beat('s03', sarge, [sarge_face(1, 60, 4.2, name='sarge_3')])
beat('k01', ket_a, [lface('ket', CUT, -1, 40, name='ket_1')], pad=0.1)
beat('c01', chill_a, [lface('chillguy', CUT, 1, 44, name='chill_1')], pad=0.3)
beat('s04', sarge, [sarge_face(-1, 50, 4.0, name='sarge_4'), view('monitor_tray', (0.7, -3.2, 1.8), (0.75, -6.0, 1.85), 50, p1=(0.8, -3.7, 1.82), fstop=4.0)])
beat('e03', cupsey_a, [lface('cupsey', CUT, 1, 44, name='egg_3')])
beat('k02', ket_a, [lface('ket', CUT, 1, 44, name='ket_2')], pad=0.2)
beat('s05', sarge, [sarge_face(1, 52, 4.0, name='sarge_5')])
beat('c02', chill_a, [lface('chillguy', CUT, -1, 44, name='chill_2')], pad=0.2)
PROLOGUE_END = CUT
print('PROLOGUE ENDS AT match time', round(PROLOGUE_END - PRE, 2))
assert PROLOGUE_END <= M(-0.4), 'briefing too long for the 46 s before the match'
# ---------------------------------------------------------------- shot macros built on the real plays
SPAWN_ID = {}
for play, spawn in thumb_spawns:
    SPAWN_ID[play['t']] = spawn['id'] if spawn else None


def jump_of(i):
    return JUMPS[i]


def filler(end, name='hold_wide2'):
    shot(name, end, (0.0, -4.4, 1.7), (0.0, 4.0, 1.2), 26, p1=(0.0, -3.7, 1.6), hide=hides(), fill_power=25, fstop=4.0)


def ship_run(i, name=None, lead=2.2, hold=0.15):
    """The ship side of play i: the character runs to the ramp and jumps."""
    play, jumper, a_jump, a_land, target = jump_of(i)
    start = max(CUT, a_jump - lead)
    if start - CUT > 0.3:
        filler(start)
    end = a_jump + hold
    if end - CUT < 0.4:
        return
    shot(name or f'run_{i}', end, (0.0, 0.8, 2.3), (0.0, 6.6, 0.8), 26, p1=(0.0, 1.4, 2.25), hide=hides(), fill_power=15, fstop=4.0)


def fall_pos(entry, a):
    play, jumper, a_jump, a_land, target = entry
    u = max(0.0, min(1.0, (a - a_jump) / (a_land - a_jump)))
    start, end = Vector(RAMP_END), Vector(target) + (Vector((0, 0, 0.4)) if play['card'] == 'airdrop' else Vector((0, 0, 0)))
    pos = start.lerp(end, u)
    pos.z = start.z + (end.z - start.z) * u * u
    return pos


def fall_cam(i, end, off=(2.6, -3.0, -0.3), lens=30, look_up=0.6, name=None, pieces=None):
    """The camera drops beside the jumper (world offset `off`) until `end`; cut into short linear pieces because a fall accelerates."""
    entry = jump_of(i)
    first = CUT
    end = min(end, entry[3])
    if end - first < 0.15:
        return
    pieces = pieces or max(2, int((end - first) / 0.3))
    for k in range(pieces):
        ta = first + (end - first) * k / pieces
        tb = first + (end - first) * (k + 1) / pieces
        pa, pb = fall_pos(entry, ta), fall_pos(entry, tb)
        ca, cb = pa + Vector(off) * (1 + 0.2 * k / pieces), pb + Vector(off) * (1 + 0.2 * (k + 1) / pieces)
        ga, gb = clear(ca.x + 9.0, 16.0 - ca.y, ca.z), clear(cb.x + 9.0, 16.0 - cb.y, cb.z)
        ca.x, ca.y, cb.x, cb.y = ga[0] - 9.0, 16.0 - ga[1], gb[0] - 9.0, 16.0 - gb[1]
        shot(name or f'fall_{i}', tb, tuple(ca), tuple(pa + Vector((0, 0, look_up))), lens, p1=tuple(cb), l1=tuple(pb + Vector((0, 0, look_up))),
             space='world', hand=None, ec=3, fstop=4.0)


TOWER_BOXES = [(3.5, 25.5, 4.2), (14.5, 25.5, 4.2), (9.0, 29.5, 5.0), (3.5, 6.5, 4.2), (14.5, 6.5, 4.2), (9.0, 2.5, 5.0)]


def clear(x, z, h):
    """Push a camera position (game coordinates) out of the towers' footprints."""
    for cx, cz, half in TOWER_BOXES:
        if abs(x - cx) < half and abs(z - cz) < half and h < 9.0:
            dx, dz = x - cx, z - cz
            if abs(dx) / half > abs(dz) / half:
                x = cx + math.copysign(half + 0.2, dx or 1.0)
            else:
                z = cz + math.copysign(half + 0.2, dz or 1.0)
    return x, z


def chase(name, end, eid, off=(-3.4, 4.5, 1.9), lens=32, look_up=0.9, pieces=None, off1=None, shake=0.3):
    """Follow a simulated unit from a behind-and-above offset (game units)."""
    first = CUT
    pieces = pieces or max(1, int((end - first) / 0.6))
    for k in range(pieces):
        ta = first + (end - first) * k / pieces
        tb = first + (end - first) * (k + 1) / pieces
        xa, za = ent_at(eid, ta - PRE)
        xb, zb = ent_at(eid, tb - PRE)
        o0 = off
        o1 = off1 or off
        offa = tuple(o0[n] + (o1[n] - o0[n]) * k / pieces for n in range(3))
        offb = tuple(o0[n] + (o1[n] - o0[n]) * (k + 1) / pieces for n in range(3))
        ca, cb = clear(xa + offa[0], za + offa[1], offa[2]), clear(xb + offb[0], zb + offb[1], offb[2])
        shot(name, tb, (ca[0], ca[1], offa[2]), (xa, za, look_up), lens, p1=(cb[0], cb[1], offb[2]), l1=(xb, zb, look_up),
             space='game', fstop=4.0, shake=shake, hand=('INVESTIGATION', 0.3))


def seq(i, chase_for=2.2, **kw):
    """One real play: the run to the ramp, the fall, and the walk that follows."""
    entry = jump_of(i)
    ship_run(i, **kw)
    if CUT < entry[3] - 0.15:
        fall_cam(i, entry[3])
    spawn_id = SPAWN_ID[entry[0]['t']]
    if spawn_id is not None:
        chase(f'chase_{i}', max(CUT + 0.5, entry[3] + chase_for), spawn_id)


# ---- the Thumb's phone: the game's own top-down view with its HUD (finish.py draws the HUD; here only the 3D picture)
PHONE_CAM = dict(p=(0.0, -30.0, 44.0), l=(0.0, -5.0, 0.0), lens=37)
PHONE_RES = [806, 1746]


def at(match_seconds):
    global CUT
    CUT = M(match_seconds)


def phone(name, end, a_start=None, **kw):
    """The game's camera: static, steep, the whole board in a portrait frame. The ship is hidden (it hovers over the river)."""
    shot(name, end, PHONE_CAM['p'], PHONE_CAM['l'], PHONE_CAM['lens'], space='world', fstop=11.0, hand=None, hide=['SHIP', 'NOSE', 'haze'],
         phone=True, res=PHONE_RES, a_start=a_start, **kw)


def ramp_shot(i, hold=0.4, tail=0.15):
    """The jumper stands at the ramp edge and goes (a_jump is the release of the drag)."""
    entry = jump_of(i)
    shot(f'ramp_{i}', entry[2] + tail, (0.0, 1.2, 2.3), (0.0, 6.6, 0.8), 26, p1=(0.0, 1.6, 2.25), hide=hides(), fill_power=15, fstop=4.0, a_start=entry[2] - hold)


def play_seq(i, chase_for=0.8, drag=0.85, hold=0.4):
    """One real play: the drag on the phone, the jump off the ramp, the fall, and a short follow of the new unit."""
    entry = jump_of(i)
    T = M(entry[0]['t'])
    phone(f'phone_{i}', T + 0.1, a_start=T - drag)
    ramp_shot(i, hold)
    fall_cam(i, entry[3])
    spawn_id = SPAWN_ID.get(entry[0]['t'])
    if spawn_id is not None and chase_for > 0.3:
        chase(f'chase_{i}', max(CUT + 0.5, entry[3] + chase_for), spawn_id)


# ---- B. the first twenty seconds, the illegal drag (17.97) and the first jumps: LMAO 19.67, Ket 22.2, Chill Guy 25.53
event('match_start', M(0.0))
say('a_fight', M(0.15))
phone('phone_fight', M(3.0), a_start=M(0.0))
beat('s06', sarge, [sarge_face(-1, 46, 3.4, name='sarge_go')], a_at=M(3.1), pad=0.05)
phone('phone_illegal', M(18.95), a_start=M(16.6))
say('e04', M(16.7))
play_seq(0, chase_for=1.0)                                          # LMAO
say('s08', M(19.4))
play_seq(1, chase_for=0.6)                                          # Ket
say('k04', M(23.2))
play_seq(2, chase_for=1.0)                                          # Chill Guy
say('c04', M(25.2))
print('B ENDS', round(CUT - PRE, 2))

# ---- C. Dope (37.3) and our left tower falls (43.1)
at(36.3)
say('k03', M(36.9))
play_seq(4, chase_for=0.8)                                          # Dope: "Two Copium. The cheap one."
shot('tower_front', M(43.0), (2.6, 32.6, 3.8), (3.5, 25.2, 2.4), 30, p1=(4.6, 31.4, 3.4), space='game', shake=0.8, hand=('HANDYCAM_RUN', 0.25), a_start=M(41.6), fstop=4.0)
say('s10', M(42.3))
phone('phone_down1', M(45.6), a_start=M(43.0))
say('c03', M(44.3))
print('C ENDS', round(CUT - PRE, 2))

# ---- D. Cupsey, the healer (54.43); their right tower (83.4) and left tower (91.17)
at(51.6)
beat('e05', cupsey_a, [lface('cupsey', CUT, 1, 44, name='egg_healer')], a_at=M(51.8), pad=0.1)
say('s09', M(53.5))
play_seq(6, chase_for=1.2)                                          # Cupsey
shot('enemy_tower', M(84.8), (8.5, 17.8, 3.0), (14.5, 6.5, 2.3), 34, p1=(9.5, 17.0, 2.8), space='game', hand=('INVESTIGATION', 0.4), shake=0.5, fstop=4.0, a_start=M(82.4))
say('s12', M(82.9))
beat('e06', cupsey_a, [lface('cupsey', CUT, -1, 44, name='egg_who')], a_at=M(85.0), pad=0.1)
say('k07', M(86.3))
play_seq(10, chase_for=0.6)                                         # LMAO (86.73)
beat('s13', sarge, [sarge_face(-1, 50, 3.6, name='sarge_rotate')], a_at=M(89.2), pad=0.1)
phone('phone_down2', M(93.4), a_start=M(90.7))
say('s20', M(91.3))
print('D ENDS', round(CUT - PRE, 2))

# ---- E. COPIUM OVERDOSE (120.0), the rotation (Cupsey 141.1, Chillhouse 144.8), the airdrop on our own side (149.8)
at(118.9)
say('a_overdose', M(119.7))
event('overdose', M(120.0))
phone('phone_overdose', M(123.0), a_start=M(118.9))
say('s14', M(120.9))
beat('e07', cupsey_a, [lface('cupsey', CUT, 1, 44, name='egg_good')], a_at=M(123.1), pad=0.1)
beat('k08', ket_a, [lface('ket', CUT, -1, 46, name='ket_dragger')], pad=0.15)
at(138.5)
beat('e08', cupsey_a, [lface('cupsey', CUT, 1, 44, name='egg_three')], a_at=M(138.6), pad=0.1)
play_seq(16, chase_for=0.8)                                         # Cupsey's third jump (141.13)
beat('c05', chill_a, [lface('chillguy', CUT, 1, 44, name='chill_rot')], a_at=M(142.7), pad=0.1)
say('s07', M(143.8))
play_seq(17, chase_for=0.6)                                         # Chillhouse (144.83)
say('h01', M(145.6))
beat('e09', cupsey_a, [lface('cupsey', CUT, -1, 44, name='egg_still')], a_at=M(146.7), pad=0.1)
play_seq(19, chase_for=0.0, drag=0.9)                               # the airdrop crate (149.8), dropped on our own side
say('s11', M(150.0))
shot('coins_on_us', M(155.4), (9.5, 23.0, 3.2), (2.9, 19.3, 1.5), 28, p1=(8.0, 22.0, 3.0), space='game', hand=('INVESTIGATION', 0.3), fstop=4.0, a_start=M(150.8))
say('k06', M(153.6))
beat('s15', sarge, [sarge_face(1, 50, 3.6, name='sarge_stop')], a_at=M(155.5), pad=0.1)
print('E ENDS', round(CUT - PRE, 2))

# ---- F. twenty seconds left, the last jump (Pudgy 175.7), time out and the victory
at(158.9)
say('s16', M(159.2))
phone('phone_twenty', M(162.3), a_start=M(159.2))
play_seq(25, chase_for=1.0)                                         # Pudgy
print('F ENDS', round(CUT - PRE, 2))

# ---- G. time out and victory, back on the ship
shot('timeout_wide', M(180.4), (9.0, 38.0, 14.0), (9.0, 14.0, 0.0), 26, p1=(9.0, 35.0, 11.0), space='game', hand=('INVESTIGATION', 0.3), a_start=M(177.4), fstop=6.0)
say('a_victory', M(180.2))
say('s17', M(180.7))
event('victory', M(180.2), until=M(184.0))
event('cheer', M(180.6))
phone('phone_win', M(183.2), a_start=M(180.2))
beat('k09', ket_a, [lface('ket', CUT, 1, 46, name='ket_won')], a_at=M(183.4), pad=0.1)
beat('e10', cupsey_a, [lface('cupsey', CUT, -1, 44, name='egg_strategy')], pad=0.1)
beat('s18', sarge, [sarge_face(1, 50, 3.6, name='sarge_rhythm')], pad=0.15)
beat('c06', chill_a, [lface('chillguy', CUT, -1, 44, name='chill_next')], pad=0.2)
beat('s19', sarge, [sarge_face(-1, 46, 3.4, name='sarge_end'), view('ship_end', (0.0, -4.4, 1.7), (0.0, 4.0, 1.2), 24, p1=(0.0, -3.0, 1.6), fill_power=25, fstop=4.0)], pad=0.5)
print('FILM ENDS', round(CUT - PRE, 2), 'film seconds', round(FILM, 1))

# ---------------------------------------------------------------- events for sound and graphics from the recording
for item in LOG:
    if item['what'] == 'illegal':
        event('illegal', M(item['t']))
game_ranges = [(sh['a0'], sh['a0'] + (sh['t1'] - sh['t0']) * sh['s0']) for sh in SHOTS if sh['game']]
rng_hits = random.Random(5)
for e in EVENTS_SIM:
    if e['type'] == 'hit' and any(a0 <= M(e['t']) < a1 for a0, a1 in game_ranges) and rng_hits.random() < 0.7:
        event('hit', M(e['t']), heavy=bool(e.get('heavy')))
    if e['type'] in ('boom',) and any(a0 <= M(e['t']) < a1 for a0, a1 in game_ranges):
        event('boom', M(e['t']))
    if e['type'] == 'tower_shot' and any(a0 <= M(e['t']) < a1 for a0, a1 in game_ranges) and rng_hits.random() < 0.5:
        event('tshot', M(e['t']))


# ==== CLIP CHECK: no two characters in the ship may overlap, at any time
def _pos_at(actor, frame):
    keys = actor.loc
    if not keys:
        return None
    if frame <= keys[0][0]:
        return keys[0][1]
    for (f0, p0), (f1, p1) in zip(keys, keys[1:]):
        if f0 <= frame <= f1:
            u = 0.0 if f1 == f0 else (frame - f0) / (f1 - f0)
            return tuple(p0[n] + (p1[n] - p0[n]) * u for n in range(3))
    return keys[-1][1]


def _visible(actor, a):
    return any(on <= a and (off is None or a < off) for on, flag, off in actor.vis)


_crew = [actor for actor in ALL if getattr(actor, 'card', None) or actor is sarge]
_worst = {}
for _k in range(int(M(0.0) * 10) - 460, int(M(184.0) * 10)):
    _a = _k / 10.0
    _in = []
    for actor in _crew:
        if not _visible(actor, _a):
            continue
        p = _pos_at(actor, F(_a))
        if p is not None and p[2] > 15.0 and p[1] > -8.3 and abs(p[0]) < 3.6:
            _in.append((actor, p))
    for _i in range(len(_in)):
        for _j in range(_i + 1, len(_in)):
            d = math.hypot(_in[_i][1][0] - _in[_j][1][0], _in[_i][1][1] - _in[_j][1][1])
            if d < 0.85:
                key = (_in[_i][0].label, _in[_j][0].label)
                if key not in _worst or d < _worst[key][0]:
                    _worst[key] = (round(d, 2), round(_a - PRE, 1))
for key, (d, at_) in sorted(_worst.items(), key=lambda kv: kv[1][0]):
    print('CLIP', key, 'min distance', d, 'at match time', at_)
print('CLIP CHECK done:', len(_worst), 'pairs closer than 0.85 m')

# ==== FINALIZE
for actor in ALL:
    key = 'sarge' if actor is sarge else getattr(actor, 'card', None)
    if key:
        actor.rig['hold'] = key
END_A = M(192.0)
for actor in ALL:
    actor.finish(END_A)
write_bobs(ALL)
sc.frame_start = 1
sc.frame_end = int(F(END_A))
N_FILM = int(round(FILM * FPS))


def film_time(a_time):
    for item in SHOTS:
        a1 = item['a0'] + (item['t1'] - item['t0']) * item['s0']
        if item['a0'] - 1e-6 <= a_time < a1:
            return item['t0'] + (a_time - item['a0']) / item['s0']
    nxt = next((item for item in SHOTS if item['a0'] > a_time), None)
    return nxt['t0'] if nxt else SHOTS[-1]['t1']


for line_id, at in CUE_LIST:
    CUES.append(dict(id=line_id, a=round(at, 3), f=round(film_time(at), 3), dur=VO[line_id]['dur'], who=VO[line_id]['who'], sub=VO[line_id]['sub']))
CUES.sort(key=lambda c: c['f'])
for previous, cue in zip(CUES, CUES[1:]):
    gap = previous['f'] + previous['dur'] + 0.18
    if cue['f'] < gap:
        print('VOICE PUSH', cue['id'], round(cue['f'], 2), '->', round(gap, 2))
        cue['f'] = round(gap, 3)
for item in EVENTS:
    item['f'] = round(film_time(item['a']), 3)
    if 'until' in item:
        item['f1'] = round(film_time(item['until']), 3)
T_CARD = FILM
END_CARD = 6.0
json.dump(dict(fps=FPS, last=N_FILM, t_card=round(T_CARD, 3), t_film=round(T_CARD + END_CARD, 3), pre=PRE, shots=SHOTS, cues=CUES, events=EVENTS, cards=CARDS),
          open(os.path.join(HERE, 'edl.json'), 'w'), indent=1)
if not DRY:
    bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=False)
print('BUILT', OUT, 'shots', len(SHOTS), 'film', round(T_CARD, 2), 'actors', len(ALL), 'frames', N_FILM)
