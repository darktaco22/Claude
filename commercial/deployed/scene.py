"""DEPLOYED: a drop ship full of cards waits for "the Thumb" (a hopeless player) to play them.

    blender -b --factory-startup -P scene.py -- --out scene.blend --vo VO_DIR --tex TEX_DIR --fx FX_DIR --lib chars.blend

Writes scene.blend and edl.json (shots, dialogue cues, events for sound and graphics). Times are animation
seconds; a shot may run slower than real time (speed < 1), so film time comes from the shot list (see `film_time`).
The hold is in ship coordinates (front bulkhead y = -6, ramp y = +6); `H()` converts them to world coordinates.
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
VO_DIR = arg('--vo', os.path.join(HERE, 'pack', 'vo'))
TEX_DIR = arg('--tex', os.path.join(HERE, 'pack', 'tex'))
FX_DIR = arg('--fx', os.path.join(HERE, '..', 'final', 'pack', 'fx'))
LIB = arg('--lib', os.path.expanduser('~/tools/chars.blend'))
ASSETS = arg('--assets', os.path.expanduser('~/tools/assets'))
FPS = 24
SHIP = Vector((0.0, -8.0, 46.0))
VO = json.load(open(os.path.join(VO_DIR, 'vo.json')))
random.seed(11)


def F(t):
    return t * FPS + 1


def H(x, y, z=0.0):
    """Ship (hold) coordinates to world."""
    return (SHIP.x + x, SHIP.y + y, SHIP.z + z)


def heading(dx, dy):
    """Rotation about Z that makes a character (which faces -Y at 0) look along (dx, dy)."""
    return math.atan2(dx, -dy)


# ================================================================ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 8
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.volume_bounces = 0
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.fps = FPS
sc.render.use_motion_blur = True
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
sc.render.image_settings.file_format = 'PNG'
sc.render.threads_mode = 'FIXED'
sc.render.threads = 4

sets.world(os.path.join(ASSETS, 'kloppenheim_06_puresky', 'kloppenheim_06_puresky_2k.exr'), strength=0.6, rotation_deg=84.4)
SUN = sets.sun(heading_deg=215.0, elevation_deg=9.0, energy=5.0)    # the sun sits 35 degrees off the ramp axis
ship = sets.build_ship(TEX_DIR)
ship['root'].location = SHIP
sets.build_exterior(ship)
yard = sets.build_yard(TEX_DIR, ASSETS, grass=True)

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.dof.use_dof = True
cam.data.dof.aperture_ratio = 1.4
cam.data.clip_start = 0.05
cam.data.clip_end = 600
fill = sets.light('camfill', 'AREA', (0.5, 0.5, 0.1), 0.0, (1.0, 0.9, 0.8), sc.collection, cam, size=0.8)


def key(obj, path, t, interp='LINEAR'):
    obj.keyframe_insert(path, frame=F(t))
    for curve in obj.animation_data.action.fcurves:
        if curve.data_path == path:
            curve.keyframe_points[-1].interpolation = interp
            for point in curve.keyframe_points:
                if abs(point.co.x - F(t)) < 0.01:
                    point.interpolation = interp


def key_value(owner, path, value, t, interp='CONSTANT', index=-1):
    """Key a property (light energy, socket value ...)."""
    if index >= 0:
        getattr(owner, path)[index] = value
    else:
        setattr(owner, path, value)
    owner.keyframe_insert(path, frame=F(t), index=index)
    action = owner.id_data.animation_data.action
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            if abs(point.co.x - F(t)) < 0.01:
                point.interpolation = interp


def show(obj, t_on, t_off=None):
    """Visible only between t_on and t_off, by keyed scale (keeps motion blur and persistent data happy)."""
    full = obj.scale.copy()
    steps = [(t_on - 1 / FPS, 0), (t_on, 1)]
    if t_off is not None:
        steps += [(t_off, 1), (t_off + 1 / FPS, 0)]
    for t, on in steps:
        obj.scale = full if on else full * 0.0001
        key(obj, 'scale', t, 'CONSTANT')
    obj.scale = full


# ================================================================ actors
class Actor:
    """A character on a rig empty (position, heading, tilt) with a child empty for the talking bob."""

    def __init__(self, name, char, scale=1.0):
        self.name = name
        self.rig = bpy.data.objects.new('RIG-' + name, None)
        self.bob = bpy.data.objects.new('BOB-' + name, None)
        for obj in (self.rig, self.bob):
            sc.collection.objects.link(obj)
            obj.rotation_mode = 'XYZ'
        self.bob.parent = self.rig
        for root in char['roots']:
            root.parent = self.bob
            root.rotation_mode = 'XYZ'
            root.location = (0, 0, 0)
            root.rotation_euler = (0, 0, 0)
            root.scale = root.scale * scale
        self.arm = char['armature']
        self.arm.animation_data_create()
        self.clips = char['clips']
        self.height = char['height'] * scale
        self.items = []
        self.pos = Vector((0, 0, 0))
        self.head = 0.0
        self.tilt = 0.0

    def at(self, t, pos=None, head=None, tilt=None, interp='LINEAR'):
        if pos is not None:
            self.pos = Vector(pos)
        if head is not None:
            self.head = head
        if tilt is not None:
            self.tilt = tilt
        self.rig.location = self.pos
        self.rig.rotation_euler = (self.tilt, 0, self.head)
        key(self.rig, 'location', t, interp)
        key(self.rig, 'rotation_euler', t, interp)

    def face(self, t, target, dur=0.3):
        self.at(t)
        self.at(t + dur, head=_near(self.head, heading(target[0] - self.pos.x, target[1] - self.pos.y)))

    def go(self, t, target, speed=1.2, clip='walk', then='idle', clip_speed=1.0):
        """Walk in a straight line from the current position; returns the arrival time."""
        target = Vector(target)
        distance = (target - self.pos).length
        new_head = _near(self.head, heading(target.x - self.pos.x, target.y - self.pos.y))
        self.at(t)
        self.at(t + 0.2, head=new_head)
        arrive = t + 0.2 + distance / speed
        self.clip(t, clip, clip_speed)
        self.at(arrive, pos=target)
        if then:
            self.clip(arrive, then)
        return arrive

    def clip(self, t, name, speed=1.0, offset=0.0):
        self.items.append((t, name if name in self.clips else 'idle', speed, offset))

    def talk(self, t0, t1):
        t = t0
        while t < t1:
            u = (t - t0) * 9.0
            self.bob.location = (0, 0, 0.022 * abs(math.sin(u)))
            self.bob.rotation_euler = (math.radians(3.5) * math.sin(u * 0.7), 0, math.radians(3) * math.sin(u * 0.5))
            key(self.bob, 'location', t, 'BEZIER')
            key(self.bob, 'rotation_euler', t, 'BEZIER')
            t += 0.09
        self.bob.location = (0, 0, 0)
        self.bob.rotation_euler = (0, 0, 0)
        key(self.bob, 'location', t1 + 0.1, 'BEZIER')
        key(self.bob, 'rotation_euler', t1 + 0.1, 'BEZIER')

    def build(self, end):
        """Turn the clip list into NLA strips: each clip loops until the next one starts."""
        self.items.sort(key=lambda item: item[0])
        for index, (t, name, speed, offset) in enumerate(self.items):
            f0 = F(t)
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


def _near(current, wanted):
    """The equivalent of `wanted` closest to `current`, so turns take the short way round."""
    while wanted - current > math.pi:
        wanted -= math.tau
    while wanted - current < -math.pi:
        wanted += math.tau
    return wanted


CAST = [('sarge', 'walter', 1.0), ('egg', 'cupsey', 0.92), ('ket', 'ket', 1.0), ('chill', 'chillguy', 1.0), ('lmao', 'lmao', 1.0),
        ('house', 'chillhouse', 1.62), ('dope', 'dope', 0.8), ('pudgy', 'pudgy', 0.95),
        ('b1', 'bonk', 1.0), ('b2', 'bonk', 1.0), ('b3', 'bonk', 1.0), ('j1', 'jeanphil', 1.0), ('j2', 'jeanphil', 1.0)]
loaded = assets.load_many(LIB, [uid for _, uid, _ in CAST], sc.collection)
A = {name: Actor(name, char, scale) for (name, uid, scale), char in zip(CAST, loaded)}
for char in loaded:                                               # smooth shading at render time for the close-ups
    for obj in char['collection'].all_objects:
        if obj.type == 'MESH' and len(obj.data.vertices) > 500:
            mod = obj.modifiers.new('subd', 'SUBSURF')
            mod.levels = 0
            mod.render_levels = 1
            mod.uv_smooth = 'PRESERVE_BOUNDARIES'
sarge, egg, ket, chill, lmao, house, dope, pudgy = (A[n] for n in ('sarge', 'egg', 'ket', 'chill', 'lmao', 'house', 'dope', 'pudgy'))
ENEMY = [A[n] for n in ('b1', 'b2', 'b3', 'j1', 'j2')]
ENEMY_OFFSET = [(-0.9, 0.0), (0.9, 0.25), (0.0, -1.1), (-0.7, 2.3), (0.8, 2.6)]       # relative to the group centre, facing -y

LEFT, RIGHT = heading(1, 0), heading(-1, 0)                        # facing +x (left row), facing -x (right row)
SEAT = {'pudgy': (-1.3, -2.2), 'house': (-1.2, -0.3), 'egg': (-1.3, 1.7), 'lmao': (-1.3, 3.5),
        'dope': (1.25, -1.6), 'ket': (1.3, 0.6), 'chill': (1.3, 2.4)}
for name, (x, y) in SEAT.items():
    A[name].at(0, H(x, y), LEFT if x < 0 else RIGHT)
    A[name].clip(0, 'idle', 0.8 + random.random() * 0.3)
sarge.at(0, H(0, 5.3), heading(0, -1))
sarge.clip(0, 'idle')

# ================================================================ timeline
SHOTS, CUES, EVENTS, SCREENS = [], [], [], []
CUT = 0.0                                                          # animation time where the next shot starts
FILM = 0.0                                                         # film time where the next shot starts
T = 0.0                                                            # animation-time cursor for the story


def say(line_id, at=None, gap=0.3, actor=None):
    """Place a recorded line at the cursor (or `at`). Returns (start, end) in animation time."""
    global T
    start = T if at is None else at
    end = start + VO[line_id]['dur']
    CUES.append({'id': line_id, 'a': round(start, 3)})
    if actor:
        actor.talk(start, end)
    T = end + gap
    return start, end


def event(kind, t, **extra):
    EVENTS.append(dict(kind=kind, a=round(t, 3), **extra))


def shot(name, end, p0, l0, lens, p1=None, l1=None, space='hold', speed=1.0, fstop=2.8, hand=('INVESTIGATION', 0.35), shake=0.0,
         fill_power=0.0, hide=None, focus=None, ec=0, lens1=None):
    """A shot from the previous cut to animation time `end`."""
    global CUT, FILM
    convert = (lambda p: list(H(*p))) if space == 'hold' else (lambda p: list(p))
    duration = (end - CUT) / speed
    if hide is None:
        hide = ['grass_field', 'NOSE'] if space == 'hold' else ['haze']
    SHOTS.append(dict(name=name, t0=round(FILM, 4), t1=round(FILM + duration, 4), a0=round(CUT, 4), s0=speed,
                      p0=convert(p0), p1=convert(p1 or p0), l0=convert(l0), l1=convert(l1 or l0), lens=lens, lens1=lens1 or lens,
                      fstop=fstop, shake=shake, ec=ec, focus=focus, hand=list(hand) if hand else None, fill=fill_power, hide=list(hide)))
    CUT = end
    FILM += duration


def screen(state, t):
    SCREENS.append((t, state))


LANE = -sets.LANE                                                 # the opponent pushes down our left lane
CLOSED = ['YARD', 'grass_field', 'NOSE']                                    # ramp shut: nothing outside is visible
EYE = 1.32                                                          # eye height of most characters

# ---------------------------------------------------------------- A. opening
screen('idle', 0.0)
event('title', 0.4, text='SOMEWHERE ABOVE ARENA 2')
say('p01', at=0.9)
shot('ext_ship', 5.6, (-34, -40, 36.0), (0, -8, 47.5), 40, p1=(-25, -31, 39.0), space='world', fstop=5.6, hand=('INVESTIGATION', 0.5),
     hide=['haze'])
shot('hold_wide', 9.2, (0.0, -5.3, 1.95), (0.0, 3.0, 1.25), 24, p1=(0.0, -3.9, 1.6), hide=CLOSED, fstop=4.0, fill_power=20)

# ---------------------------------------------------------------- B. briefing
T = 9.3
s01 = say('s01', actor=sarge)
sarge.clip(s01[0] - 0.2, 'walk', 0.8)
sarge.at(s01[0] - 0.2)
sarge.at(s01[1] - 0.3, pos=H(0, 3.0))
sarge.clip(s01[1] - 0.3, 'idle')
shot('sarge_walk', s01[1] + 0.15, (0.3, 0.3, 1.0), (0.0, 4.3, 1.3), 40, l1=(0.0, 3.0, 1.36), hide=CLOSED, fill_power=60)
e01 = say('e01', actor=egg)
shot('egg_1', e01[1] + 0.2, (0.5, 1.1, 1.05), (-1.3, 1.7, 0.98), 50, hide=CLOSED, fill_power=40)
sarge.face(e01[0], H(-1.3, 1.7))
s02 = say('s02', actor=sarge)
shot('sarge_cu', s02[0] + 1.25, (-0.95, 1.5, 1.2), (0.0, 3.0, 1.38), 50, hide=CLOSED, fill_power=50)
shot('monitor_thumb', s02[0] + 2.45, (0.5, -3.3, 1.8), (0.75, -6.0, 1.85), 55, p1=(0.55, -3.7, 1.82), hide=CLOSED, fstop=4.0)
shot('sarge_cu2', s02[1] + 0.15, (-0.95, 1.5, 1.2), (0.0, 3.0, 1.4), 62, hide=CLOSED, fill_power=50)
e02 = say('e02', actor=egg, gap=0.45)
shot('egg_2', e02[1] + 0.3, (0.4, 1.2, 1.05), (-1.3, 1.7, 1.0), 62, hide=CLOSED, fill_power=40)
k01 = say('k01', actor=ket, gap=0.4)
shot('ket_1', k01[1] + 0.3, (-0.5, 1.35, 1.25), (1.3, 0.6, 1.2), 50, hide=CLOSED, fill_power=40)
sarge.face(k01[1], H(0, -6))
s03 = say('s03', actor=sarge, gap=0.35)
shot('sarge_rows', s03[1] + 0.15, (0.75, 0.1, 1.15), (0.0, 3.0, 1.35), 35, p1=(0.6, 0.5, 1.2), hide=CLOSED, fill_power=60)
c01 = say('c01', actor=chill, gap=0.5)
shot('chill_1', c01[1] + 0.4, (-0.5, 1.6, 1.3), (1.3, 2.4, 1.25), 50, hide=CLOSED, fill_power=40)

# ---------------------------------------------------------------- C. first drop: LMAO
screen('lmao', T - 0.1)
y01 = say('y01', gap=0.35)
shot('monitor_lmao', y01[1] + 0.2, (0.6, -3.2, 1.8), (0.75, -6.0, 1.85), 60, hide=CLOSED, fstop=4.0)
T_GREEN1 = T
event('klaxon', T_GREEN1)
event('ramp', T_GREEN1 + 0.2)
sarge.go(T_GREEN1 - 1.6, H(-0.95, 5.0), speed=2.2, clip='run', then='idle')
sarge.face(T_GREEN1, H(-1.3, 3.5))
s04 = say('s04', at=T_GREEN1 + 0.3, actor=sarge)
shot('ramp_opens', s04[1] - 0.2, (0.0, -4.9, 1.5), (0.0, 5.0, 1.3), 28, p1=(0.0, -4.3, 1.45), fstop=4.0, shake=0.4, fill_power=15)
T_RUN1 = s04[1] - 0.5
event('laugh', T_RUN1)
lmao.clip(T_RUN1, 'run', 1.2)
lmao.at(T_RUN1)
lmao.at(T_RUN1 + 0.25, head=heading(1.2, 1.2))
lmao.at(T_RUN1 + 0.7, pos=H(-0.2, 4.7), head=heading(0, 1))
T_JUMP1 = T_RUN1 + 1.75
lmao.at(T_JUMP1, pos=H(0.0, 8.4, -0.55))
LAND1 = Vector((LANE, 4.6, 0.0))
T_LAND1 = T_JUMP1 + 2.6


def fall(actor, t0, t1, start, end, spin=1.0, clip='run'):
    """Cartoon fall: accelerating drop with a tumble, upright again on landing."""
    start, end = Vector(start), Vector(end)
    actor.clip(t0, clip, 1.4)
    steps = max(2, int((t1 - t0) * FPS / 2))
    for index in range(steps + 1):
        u = index / steps
        pos = start.lerp(end, u)
        pos.z = start.z + (end.z - start.z) * u ** 1.9
        actor.at(t0 + (t1 - t0) * u, pos=pos, tilt=math.tau * spin * u if index < steps else 0.0)


def fall_point(t, t0, t1, start, end):
    start, end = Vector(start), Vector(end)
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    pos = start.lerp(end, u)
    pos.z = start.z + (end.z - start.z) * u ** 1.9
    return pos


def fall_shot(name, end, t0, t1, start, land, offset, lens, speed):
    """The camera drops beside a falling character and keeps it framed."""
    a, b = fall_point(CUT, t0, t1, start, land), fall_point(end, t0, t1, start, land)
    offset = Vector(offset)
    shot(name, end, tuple(a + offset), tuple(a + Vector((0, 0, 0.8))), lens, p1=tuple(b + offset * 1.25), l1=tuple(b + Vector((0, 0, 0.8))),
         space='world', speed=speed, fstop=4.0, hand=('HANDYCAM_RUN', 0.4), ec=3)


fall(lmao, T_JUMP1, T_LAND1, H(0.0, 8.4, -0.55), LAND1, spin=1.0)
shot('lmao_leaps', T_JUMP1 + 0.45, (1.9, 10.6, 0.1), (0.0, 7.2, 0.9), 32, fstop=4.0, hand=('HANDYCAM_RUN', 0.3))
fall_shot('lmao_falls', T_JUMP1 + 1.5, T_JUMP1, T_LAND1, H(0.0, 8.4, -0.55), LAND1, (2.6, 3.4, -1.6), 35, 0.55)
shot('thumb_view_1', T_LAND1 + 0.35, (-5.5, -1.0, 40.0), (-5.5, 5.4, 0.0), 75, space='world', fstop=8.0, hand=None)
event('hud', T_JUMP1 + 1.5, until=T_LAND1 + 0.35, card='lmao')
event('land', T_LAND1)
lmao.clip(T_LAND1, 'emote')
lmao.at(T_LAND1 + 0.05, head=heading(0, 1))
T_BONK = T_LAND1 + 1.9
shot('lmao_lands', T_BONK - 0.1, (-2.2, 5.3, 0.8), (-5.5, 5.7, 1.1), 35, p1=(-2.4, 5.5, 0.75), space='world', fstop=2.8)
event('bonk', T_BONK)
event('bonk', T_BONK + 0.28)
event('bonk', T_BONK + 0.55)
event('unit_die', T_BONK + 0.6)
lmao.clip(T_BONK + 0.1, 'die')
show(lmao.rig, 0.0, T_BONK + 1.6)
screen('lmao_dead', T_BONK + 0.7)
T = T_BONK + 0.9
y02 = say('y02', gap=0.3)
shot('sarge_looks_down', T_BONK + 0.85, (-0.2, 3.3, 1.5), (-0.95, 5.0, 1.35), 50, fill_power=30, shake=0.2)
shot('monitor_dead', y02[1] + 0.1, (0.6, -3.2, 1.8), (0.75, -6.0, 1.85), 60, fstop=4.0)
e03 = say('e03', actor=egg, gap=0.35)
shot('egg_3', e03[1] + 0.2, (0.5, 1.1, 1.05), (-1.3, 1.7, 0.98), 55, fill_power=40)
k02 = say('k02', actor=ket, gap=0.7)
shot('ket_2', k02[1] + 0.45, (-0.5, 1.35, 1.25), (1.3, 0.6, 1.2), 58, fill_power=40)

# ---------------------------------------------------------------- D. the airdrop
CRATE_AT = (0.55, 5.1)
sarge.go(k02[0] - 0.5, H(0.55, 4.15), speed=1.6, then='idle')
sarge.face(T - 0.3, H(0.55, 9.0))
screen('airdrop', T)
s05 = say('s05', actor=sarge, gap=0.2)
shot('sarge_crate', s05[0] + 1.75, (-1.0, 3.1, 0.95), (0.5, 4.6, 1.05), 40, p1=(-0.8, 3.2, 1.0), fill_power=40)
shot('thumb_view_bridge', s05[0] + 3.3, (-5.5, -6.0, 40.0), (-5.5, 0.6, 0.0), 80, space='world', fstop=8.0, hand=None)
event('hud', s05[0] + 1.75, until=s05[0] + 3.3, card='airdrop', target=True)
T_KICK = s05[1] + 0.25
sarge.clip(T_KICK - 0.35, 'attack1')
sarge.clip(T_KICK + 0.6, 'idle')
event('kick', T_KICK)
crate = ship['airdrop']
crate.parent = None
crate.location = H(*CRATE_AT, 0.4)
key(crate, 'location', 0)
key(crate, 'location', T_KICK)
crate.location = H(0.55, 8.4, -0.2)
key(crate, 'location', T_KICK + 0.55)
crate.location = H(0.55, 10.5, -6.0)
key(crate, 'location', T_KICK + 1.1)
key(crate, 'rotation_euler', T_KICK + 0.5)
crate.rotation_euler = (2.2, 0.4, 0.3)
key(crate, 'rotation_euler', T_KICK + 1.1)
show(crate, 0.0, T_KICK + 1.15)
shot('crate_out', T_KICK + 1.0, (-0.7, 3.0, 1.0), (0.5, 4.6, 1.0), 35, l1=(0.5, 7.0, 0.6), fill_power=40)
T_COINS = T_KICK + 1.3
event('coins', T_COINS)
DUCK = Vector((9.3, 0.1, 0.72))
gold = sets.material('coin', (1.0, 0.72, 0.15), rough=0.25, metal=1.0)
random.seed(5)
for index in range(34):
    coin = sets.cylinder('coin', 0.24, 0.06, (0, 0, 0), gold, yard['col'], verts=16)
    lucky = index == 0
    angle, radius = random.uniform(0, math.tau), random.uniform(0.9, 3.4)
    target = Vector((DUCK.x - 0.53, DUCK.y - 0.14, DUCK.z + 1.5)) if lucky else Vector((DUCK.x + math.cos(angle) * radius,
                                                                                DUCK.y + math.sin(angle) * radius * 0.45, 0.9))
    t0 = T_COINS + (1.9 if lucky else random.uniform(0.0, 1.6))
    t1 = t0 + 1.1
    for step in range(7):
        u = step / 6
        coin.location = (target.x, target.y, target.z + 26.0 * (1 - u ** 1.6))
        coin.rotation_euler = (u * 9.0 + index, u * 5.0, index)
        key(coin, 'location', t0 + (t1 - t0) * u)
        key(coin, 'rotation_euler', t0 + (t1 - t0) * u)
    if lucky:
        coin.rotation_euler = (0, 0, 0.4)
        key(coin, 'rotation_euler', t1 + 0.05)
        show(coin, t0)
    else:
        coin.location = (target.x, target.y, 0.3)
        key(coin, 'location', t1 + 0.5)
        show(coin, t0, t1 + 0.5)
    event('plop', t1, quiet=not lucky)
shot('thumb_view_duck', T_COINS + 1.5, (9.3, -6.0, 40.0), (9.3, 0.3, 0.0), 90, space='world', fstop=8.0, hand=None)
event('hud', T_COINS - 0.3, until=T_COINS + 1.5, card='airdrop', target=True)
shot('duck', T_COINS + 3.9, (5.2, -3.4, 1.7), (9.2, 0.1, 1.5), 50, p1=(5.5, -3.1, 1.7), space='world', fstop=2.8)
T_STARE = T_COINS + 3.9
shot('enemy_stares', T_STARE + 1.3, (-1.6, -1.2, 3.1), (-5.5, 0.3, 2.5), 40, space='world', fstop=4.0)
T = T_STARE + 1.3
sarge.face(T - 2.0, H(0.55, 12))
shot('sarge_silent', T + 1.2, (1.0, 7.6, 1.2), (0.55, 4.15, 1.38), 50, p1=(0.95, 7.3, 1.25), fill_power=25)
T += 1.2
c02 = say('c02', actor=chill, gap=0.55)
shot('chill_2', c02[1] + 0.3, (-0.5, 1.6, 1.3), (1.3, 2.4, 1.25), 55, fill_power=40)
s06 = say('s06', actor=sarge, gap=0.5)
shot('sarge_duck', s06[1] + 0.4, (0.1, 6.9, 1.3), (0.55, 4.15, 1.4), 62, fill_power=30)

# ---------------------------------------------------------------- E. tower down, emote
T_BOOM = T + 1.5
shot('tower_attack', T_BOOM + 1.7, (-10.2, -4.2, 0.9), (-5.5, -8.6, 2.2), 30, p1=(-10.6, -3.8, 1.1), space='world', fstop=4.0, shake=0.8,
     hand=('HANDYCAM_RUN', 0.3))
event('boom', T_BOOM)
T = T_BOOM + 1.7
screen('tower', T_BOOM + 0.3)
y04 = say('y04', at=T_BOOM + 1.9, gap=0.3)
shot('hold_shakes', y04[1] + 0.2, (0.3, -4.4, 1.5), (0.0, 3.0, 1.3), 26, shake=1.6, fill_power=15, fstop=4.0, hand=('HANDYCAM_RUN', 0.5))
e04 = say('e04', actor=egg, gap=0.35)
shot('egg_4', e04[1] + 0.15, (0.5, 1.1, 1.05), (-1.3, 1.7, 0.98), 58, fill_power=40, shake=0.3)
screen('wagmi', e04[1])
k03 = say('k03', actor=ket, gap=0.3)
shot('ket_3', k03[1] + 0.35, (-0.5, 1.35, 1.25), (1.3, 0.6, 1.2), 58, fill_power=40)
T_EMOTE = T + 0.3
event('emote', T_EMOTE)
shot('wagmi', T_EMOTE + 2.4, (7.5, -24.0, 1.8), (0.0, -13.5, 6.6), 28, p1=(7.0, -23.2, 2.0), space='world', fstop=4.0)
T = T_EMOTE + 2.5
sarge.go(k03[0], H(0.0, 3.0), speed=1.5, then='idle')
sarge.face(T - 1.0, H(0, -6))
s07 = say('s07', actor=sarge, gap=0.45)
shot('sarge_burn', s07[1] + 0.25, (0.25, 0.9, 1.3), (0.0, 3.0, 1.42), 60, p1=(0.2, 1.25, 1.32), lens1=70, fill_power=50)
c03 = say('c03', actor=chill, gap=0.5)
shot('chill_3', c03[1] + 0.35, (-0.5, 1.6, 1.3), (1.3, 2.4, 1.25), 58, fill_power=40)

# ---------------------------------------------------------------- F. Chillhouse
T_FULL = T
event('alarm', T_FULL, until=T_FULL + 5.0)
flash = T_FULL
while flash < T_FULL + 16:
    screen('full_a', flash)
    screen('full_b', flash + 0.3)
    flash += 0.6
y05 = say('y05', gap=0.2)
shot('monitor_full', y05[1] + 0.1, (0.55, -3.0, 1.75), (0.75, -6.0, 1.85), 50, p1=(0.6, -3.5, 1.8), fstop=4.0, shake=0.3)
s08 = say('s08', actor=sarge, gap=0.2)
sarge.face(s08[0] + 0.6, H(-1.2, -0.3))
T_HOUSE_RUN = s08[0] + 1.5
house.clip(T_HOUSE_RUN, 'run', 0.9)
house.at(T_HOUSE_RUN)
house.at(T_HOUSE_RUN + 0.25, head=heading(1, 0.6))
house.at(T_HOUSE_RUN + 0.7, pos=H(0.0, 0.9), head=heading(0, 1))
T_STUCK = T_HOUSE_RUN + 2.4
house.at(T_STUCK, pos=H(0.0, 5.55))
event('thud', T_STUCK)
sarge.go(s08[0] + 1.3, H(-1.35, 3.6), speed=2.4, clip='run', then='idle')
sarge.face(T_STUCK - 0.6, H(0, 5.5))
shot('sarge_yells', T_HOUSE_RUN + 0.5, (0.9, 4.6, 1.2), (0.0, 3.0, 1.4), 40, fill_power=60, shake=0.4, hand=('HANDYCAM_RUN', 0.3))
shot('house_runs', T_STUCK + 0.5, (0.5, -4.6, 1.1), (0.0, 1.5, 1.6), 26, l1=(0.0, 5.0, 1.6), fill_power=20, shake=0.5,
     hand=('HANDYCAM_RUN', 0.4), fstop=4.0)
T = T_STUCK + 0.9
h01 = say('h01', actor=house, gap=0.3)
shot('house_stuck', h01[0] - 0.1, (0.6, 13.0, 0.6), (0.0, 6.0, 1.5), 45, p1=(0.5, 12.4, 0.7), fstop=4.0)
shot('house_sorry', h01[1] + 0.35, (0.5, 10.2, 1.7), (0.0, 6.0, 1.9), 85, fstop=4.0)
s09 = say('s09', actor=sarge, gap=0.2)
T_PUSH = s09[0] + 0.5
pushers = [(sarge, (-0.55, 4.5)), (ket, (0.55, 4.5)), (chill, (0.6, 3.5)), (egg, (-0.6, 3.5)), (pudgy, (0.0, 2.7)), (dope, (0.0, 1.5))]
for actor, (x, y) in pushers:
    arrive = actor.go(T_PUSH + random.uniform(0.0, 0.3), H(x, y), speed=3.0, clip='run', then='walk')
    actor.at(arrive + 0.15, head=heading(0, 1))
shot('push_call', s09[1] + 0.2, (-0.9, 0.9, 1.4), (-0.4, 4.3, 1.3), 32, fill_power=40, shake=0.3)
k04 = say('k04', at=T_PUSH + 1.7, actor=ket, gap=0.3)
T_POP = k04[1] + 0.55
shot('push_side', k04[0] + 0.1, (-1.85, 2.2, 0.8), (0.0, 4.6, 1.2), 26, p1=(-1.8, 2.6, 0.85), fill_power=30, shake=0.5, fstop=4.0)
shot('ket_push', T_POP - 0.15, (1.8, 5.5, 1.3), (0.55, 4.5, 1.25), 40, fill_power=50, shake=0.4)
event('pop', T_POP)
for actor, (x, y) in pushers:                                       # everyone stumbles forward as the house lets go
    actor.at(T_POP)
    actor.at(T_POP + 0.3, pos=H(x, y + 0.5))
    actor.clip(T_POP, 'hit')
    actor.clip(T_POP + 0.7, 'idle')
TRAMP = Vector((9.5, -5.0, 1.35))
T_TRAMP = T_POP + 2.3
house.at(T_POP)
fall(house, T_POP + 0.02, T_TRAMP, H(0.0, 7.6, 0.0), TRAMP, spin=1.0, clip='run')
shot('house_pops', T_POP + 0.8, (2.4, 12.5, -0.8), (0.0, 6.5, 1.0), 30, l1=(0.3, 8.0, -1.5), fstop=4.0, shake=0.5, hand=('HANDYCAM_RUN', 0.4))
shot('thumb_view_tramp', T_TRAMP + 0.4, (9.5, -11.0, 40.0), (9.5, -5.0, 0.0), 85, space='world', fstop=8.0, hand=None)
event('boing', T_TRAMP)
APEX = Vector(H(0.4, 11.0, 0.6))
T_APEX = T_TRAMP + 2.3
steps = 16
for index in range(steps + 1):                                      # up to the ramp, hang, and down again
    u = index / steps
    pos = TRAMP.lerp(APEX, u)
    pos.z = TRAMP.z + (APEX.z - TRAMP.z) * (1 - (1 - u) ** 2.2)
    house.at(T_TRAMP + (T_APEX - T_TRAMP) * u, pos=pos, tilt=0.0, head=heading(0, -1))
house.clip(T_TRAMP, 'idle')
house.clip(T_APEX - 0.5, 'emote')
house.at(T_APEX + 0.9)
T_SPLASH = T_APEX + 2.6
for index in range(1, 9):
    u = index / 8
    house.at(T_APEX + 0.9 + (T_SPLASH - T_APEX - 0.9) * u, pos=(APEX.x + 2.0 * u, APEX.y + 1.0 * u, APEX.z - 46.0 * u ** 2), tilt=-1.5 * u)
show(house.rig, 0.0, T_SPLASH)
event('splash', T_SPLASH)
event('squeak', T_SPLASH + 0.15)
for actor, (x, y) in pushers:
    actor.face(T_TRAMP + 0.3, H(0.3, 12))
shot('house_returns', T_APEX + 1.9, (0.2, 1.4, 1.5), (0.2, 9.0, 1.3), 30, p1=(0.2, 1.9, 1.5), fill_power=15, fstop=5.6)
shot('duck_rocks', T_SPLASH + 1.3, (5.2, -3.4, 1.7), (9.2, 0.1, 1.5), 60, space='world', fstop=2.8)
T = T_SPLASH + 1.3

# ---------------------------------------------------------------- G. the egg
screen('last', T - 0.2)
y06 = say('y06', gap=0.3)
shot('monitor_last', y06[1] + 0.1, (0.6, -3.2, 1.8), (0.75, -6.0, 1.85), 60, fstop=4.0)
sarge.go(T_APEX + 2.2, H(0.55, 5.1), speed=1.4, then='idle')
egg.go(T_APEX + 2.4, H(-0.45, 4.9), speed=1.2, then='idle')
for actor, spot in ((ket, (1.3, 2.9)), (chill, (1.35, 3.9)), (pudgy, (-1.3, 2.6)), (dope, (-1.2, 1.2))):
    arrive = actor.go(T_APEX + 2.0 + random.uniform(0, 0.6), H(*spot), speed=1.3, then='idle')
    actor.face(arrive, H(0, 5.2))
egg.face(T - 0.4, H(0.55, 5.1))
sarge.face(T - 0.4, H(-0.45, 4.9))
e05 = say('e05', actor=egg, gap=0.6)
shot('egg_5', e05[1] + 0.4, (1.3, 3.2, 1.1), (-0.45, 4.9, 1.0), 48, p1=(1.2, 3.3, 1.1), fill_power=45)
event('music_swell', T)
s10 = say('s10', actor=sarge, gap=0.5)
shot('speech', s10[1] + 0.3, (-0.2, 2.2, 1.15), (0.05, 5.0, 1.3), 50, p1=(-0.15, 2.7, 1.2), lens1=58, fill_power=35)
e06 = say('e06', actor=egg, gap=0.3)
shot('egg_6', e06[1] + 0.2, (1.3, 3.2, 1.1), (-0.45, 4.9, 1.0), 55, fill_power=45)
s11 = say('s11', actor=sarge, gap=0.0)
T_SHOVE = s11[1] - 0.35
sarge.clip(T_SHOVE - 0.3, 'attack1')
sarge.clip(T_SHOVE + 0.7, 'idle')
event('shove', T_SHOVE)
shot('sarge_go', T_SHOVE + 0.1, (1.7, 9.6, 0.5), (0.0, 5.0, 1.2), 35, fill_power=20, fstop=4.0)
EGG_LAND = Vector((0.0, -9.6, 0.0))
T_EGG_OUT = T_SHOVE + 0.5
T_EGG_LAND = T_EGG_OUT + 2.6
egg.at(T_SHOVE)
egg.at(T_EGG_OUT, pos=H(-0.2, 8.3, 0.0), tilt=0.6)
fall(egg, T_EGG_OUT, T_EGG_LAND, H(-0.2, 8.3, 0.0), EGG_LAND, spin=2.0, clip='hit')
event('scream', T_EGG_OUT)
shot('egg_out', T_EGG_OUT + 0.3, (1.6, 10.8, 0.4), (-0.2, 7.0, 1.0), 32, fstop=4.0, hand=('HANDYCAM_RUN', 0.4))
fall_shot('egg_falls', T_EGG_OUT + 1.45, T_EGG_OUT, T_EGG_LAND, H(-0.2, 8.3, 0.0), EGG_LAND, (1.8, -2.8, -1.2), 40, 0.4)
shot('thumb_view_egg', T_EGG_LAND + 0.2, (0.0, -14.0, 40.0), (0.0, -8.0, 0.0), 70, space='world', fstop=8.0, hand=None)
event('hud', T_EGG_OUT + 1.45, until=T_EGG_LAND + 0.2, card='cupsey')
event('land', T_EGG_LAND)
egg.clip(T_EGG_LAND, 'hit', 0.8)
egg.at(T_EGG_LAND + 0.05, head=heading(0, 1))
T_RAISE = T_EGG_LAND + 2.3
T_FREEZE = T_RAISE + 1.3
shot('egg_lands', T_EGG_LAND + 2.2, (0.9, -11.6, 0.45), (0.0, -7.2, 1.4), 24, p1=(0.8, -11.3, 0.5), space='world', fstop=4.0)
shot('egg_cowers', T_FREEZE + 0.9, (-1.4, -5.6, 2.1), (0.0, -9.6, 0.9), 50, p1=(-1.2, -6.0, 2.0), space='world', fstop=2.8)
event('freeze', T_FREEZE)
T = T_FREEZE + 1.0
T_ICONS = T
shot('frozen', T_ICONS + 1.5, (4.0, -5.6, 1.2), (0.0, -7.4, 1.5), 35, p1=(3.7, -5.7, 1.2), space='world', fstop=4.0, hand=('INVESTIGATION', 0.2))
T = T_ICONS + 0.9
y07 = say('y07', gap=0.3)
T_TOPPLE = y07[0] + 1.2
shot('topple', y07[1] + 0.9, (1.6, -11.0, 0.5), (0.0, -7.2, 1.2), 28, space='world', fstop=4.0)
event('banner', y07[0], text='OPPONENT paperhands420 HAS LEFT THE MATCH', until=y07[1] + 0.8)
T = y07[1] + 1.0
T_WIN = T
egg.clip(T_WIN - 0.6, 'idle')
egg.clip(T_WIN + 0.2, 'win')
screen('victory', T_WIN)
y08 = say('y08', at=T_WIN + 0.3, gap=0.2)
event('victory', T_WIN + 0.2, until=T_WIN + 3.2)
shot('egg_wins', T_WIN + 3.2, (1.6, -6.4, 0.7), (0.0, -9.6, 1.0), 40, p1=(1.2, -6.9, 0.9), space='world', fstop=2.8)
T = T_WIN + 3.2

# ---------------------------------------------------------------- H. tag
T_CHEER = T
for actor in (ket, chill, pudgy, dope):
    actor.clip(T_CHEER - 1.0, 'win')
event('cheer', T_CHEER)
sarge.face(T_CHEER - 2.0, H(0.55, 12))
shot('hold_cheers', T_CHEER + 1.7, (0.0, -1.2, 1.5), (0.0, 4.0, 1.3), 28, fill_power=30, fstop=4.0, hand=('HANDYCAM_RUN', 0.25))
T = T_CHEER + 1.8
s12 = say('s12', actor=sarge, gap=0.4)
shot('sarge_proud', s12[1] + 0.25, (-0.9, 3.2, 1.4), (0.55, 5.1, 1.4), 60, p1=(-0.8, 3.4, 1.42), fill_power=50)
for actor in (ket, chill, pudgy, dope):
    actor.clip(s12[0] + 0.5, 'idle')
c04 = say('c04', actor=chill, gap=0.5)
shot('chill_4', c04[1] + 0.35, (-0.4, 3.0, 1.3), (1.35, 3.9, 1.25), 55, fill_power=40)
screen('clout', T - 0.1)
y09 = say('y09', gap=0.3)
shot('monitor_clout', y09[1] + 0.1, (0.6, -3.2, 1.8), (0.75, -6.0, 1.85), 60, fstop=4.0)
k05 = say('k05', actor=ket, gap=0.35)
shot('ket_5', k05[1] + 0.25, (-0.4, 2.0, 1.25), (1.3, 2.9, 1.2), 55, fill_power=40)
T_NEXT = T
screen('next', T_NEXT)
event('klaxon', T_NEXT)
event('red', T_NEXT)
y10 = say('y10', at=T_NEXT + 0.3, gap=0.0)
for actor in (ket, chill, pudgy, dope, sarge):
    actor.clip(T_NEXT + 0.5 + random.uniform(0, 0.3), 'lose')
event('groan', T_NEXT + 0.9)
T_END = y10[1] + 0.15
shot('next_match', T_END, (0.0, -3.4, 1.6), (0.0, 3.5, 1.3), 26, p1=(0.0, -3.9, 1.65), fill_power=20, fstop=4.0)
T_CARD = FILM
END_CARD = 6.0
CUES.append({'id': 's13', 'f': round(T_CARD + 1.2, 3)})

# ================================================================ the opponent's push (timed against the beats above)
def group_at(t, centre, face=(0, -1), interp='LINEAR'):
    angle = heading(*face)
    cos, sin = math.cos(angle), math.sin(angle)
    for actor, (ox, oy) in zip(ENEMY, ENEMY_OFFSET):
        actor.at(t, pos=(centre[0] + ox * cos - oy * sin, centre[1] + ox * sin + oy * cos, 0), head=angle, interp=interp)


def bridge_z(y):
    y = abs(y)
    if y > 4.4:
        return 0.0
    if y > 2.5:
        return 1.45 * (4.4 - y) / 1.9
    return 1.45 + 0.12 * (1 - (y / 2.5) ** 2)


def group_walk(t0, t1, y0, y1, x=None):
    """Walk the group down the lane from y0 to y1, following the bridge profile."""
    steps = max(2, int(abs(y1 - y0) / 0.45))
    for index in range(steps + 1):
        u = index / steps
        cy = y0 + (y1 - y0) * u
        for actor, (ox, oy) in zip(ENEMY, ENEMY_OFFSET):
            py = cy + oy
            actor.at(t0 + (t1 - t0) * u, pos=((LANE if x is None else x) + ox, py, bridge_z(py)), head=heading(0, -1))


def group_clip(t, name, speed=1.0, spread=0.25):
    for actor in ENEMY:
        actor.clip(t + random.uniform(0, spread), name, speed)


group_at(0, (LANE, 14.0))
group_clip(0, 'idle')
group_at(T_GREEN1 - 4.0, (LANE, 14.0))
group_clip(T_GREEN1 - 4.0, 'walk')
group_at(T_LAND1 - 0.3, (LANE, 6.9))                                # they arrive as LMAO lands in front of them
group_clip(T_LAND1 - 0.3, 'idle')
for actor in ENEMY[:3]:
    actor.clip(T_BONK - 0.45, 'attack1')
    actor.clip(T_BONK + 0.9, 'idle')
group_at(T_BONK + 2.0, (LANE, 6.9))
group_clip(T_BONK + 2.0, 'walk')
T_BRIDGE = s05[0] + 1.6
group_walk(T_BONK + 2.0, T_BRIDGE, 6.9, 1.4)
group_walk(T_BRIDGE, T_STARE - 0.6, 1.4, 0.4)
group_clip(T_STARE - 0.6, 'idle')
for actor in ENEMY:                                                # they all look at the duck
    actor.at(T_STARE - 0.2, head=heading(1, -0.1))
    actor.at(T_STARE + 1.6)
    actor.at(T_STARE + 2.0, head=heading(0, -1))
group_clip(T_STARE + 2.0, 'walk')
group_walk(T_STARE + 2.0, T_BOOM - 3.2, 0.4, -5.6)
for actor in ENEMY:
    actor.clip(T_BOOM - 3.2, 'attack1' if actor in ENEMY[:3] else 'attack2')
group_at(T_BOOM + 2.5, (LANE, -5.6))
group_clip(T_BOOM + 2.5, 'walk')
group_at(T_BOOM + 9.0, (0.0, -3.4))
group_clip(T_BOOM + 9.0, 'idle')
group_at(T_EGG_LAND + 0.4, (0.0, -3.4))
group_clip(T_EGG_LAND + 0.4, 'run')
group_at(T_EGG_LAND + 1.9, (0.0, -6.9))
group_clip(T_EGG_LAND + 1.9, 'idle', spread=0.1)
for actor in ENEMY:
    actor.clip(T_RAISE + random.uniform(0, 0.3), 'attack1', 0.8)
    actor.clip(T_FREEZE, 'attack1', 0.0005, offset=0.3)             # frozen mid-swing
for index, actor in enumerate(ENEMY):                              # they tip over like statues, one after another
    t = T_TOPPLE + index * 0.28
    actor.at(t)
    actor.at(t + 0.45, tilt=-math.pi / 2 * 0.97, interp='BEZIER')
    event('clunk', t + 0.45)

# disconnect icons over the frozen opponents
icon_mat = sets.image_material('disconnect', os.path.join(TEX_DIR, 'disconnect.png'), emit=1.0, alpha=True)
for index, actor in enumerate(ENEMY):
    icon = sets.plane('icon', 0.75, 0.75, (0, 0, 0), icon_mat, yard['col'])
    icon.location = (actor.pos.x, actor.pos.y, 2.55)
    track = icon.constraints.new('TRACK_TO')
    track.target = cam
    track.track_axis = 'TRACK_Z'
    track.up_axis = 'UP_Y'
    t_on = T_ICONS + 0.25 + index * 0.16
    show(icon, t_on, T_TOPPLE + index * 0.28 + 0.1)
    event('blip', t_on)

# ================================================================ set animation
# ramp: shut, opens at the first green light
hinge = ship['hinge']
key(hinge, 'rotation_euler', 0)
key(hinge, 'rotation_euler', T_GREEN1 + 0.2, 'BEZIER')
hinge.rotation_euler = (math.radians(-14), 0, 0)
key(hinge, 'rotation_euler', T_GREEN1 + 2.3, 'BEZIER')

# jump lights
GREEN_TIMES = [(T_GREEN1, T_BONK + 0.6), (T_KICK - 0.6, T_COINS + 0.5), (s08[0] + 0.4, T_TRAMP), (s11[0], T_NEXT)]


def lamp_state(name, t, on):
    mat, lamp = ship['lenses'][name]
    socket = mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    socket.default_value = 8.0 if on else 0.0
    socket.keyframe_insert('default_value', frame=F(t))
    lamp.data.energy = (70.0 if name == 'green' else 110.0) if on else 0.0
    lamp.data.keyframe_insert('energy', frame=F(t))


lamp_state('red', 0, True)
lamp_state('green', 0, False)
for t_on, t_off in GREEN_TIMES:
    lamp_state('red', t_on, False)
    lamp_state('green', t_on, True)
    lamp_state('green', t_off, False)
    lamp_state('red', t_off, True)
for name in ('red', 'green'):
    mat, lamp = ship['lenses'][name]
    for owner in (mat.node_tree, lamp.data):
        for curve in owner.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = 'CONSTANT'

# ceiling lamps flicker when the tower goes and during the alarm
for lamp in ship['ceiling']:
    lamp.data.keyframe_insert('energy', frame=F(0))
    t = T_BOOM
    while t < T_BOOM + 2.2:
        lamp.data.energy = random.choice((4.0, 55.0, 20.0))
        lamp.data.keyframe_insert('energy', frame=F(t))
        t += random.uniform(0.06, 0.2)
    lamp.data.energy = 55.0
    lamp.data.keyframe_insert('energy', frame=F(T_BOOM + 2.3))

# monitor states: stacked planes, one visible at a time
x, y, z = ship['screen_at']
width, height = ship['screen_size']
SCREENS.sort()
planes = {}
for index, (t, state) in enumerate(SCREENS):
    if state not in planes:
        mat = sets.image_material('screen_' + state, os.path.join(TEX_DIR, f'screen_{state}.png'), emit=1.3)
        planes[state] = sets.plane('screen_' + state, width, height, H(x, y, z), mat, ship['col'], rot=(math.pi / 2, 0, math.pi))
        planes[state]['times'] = []
    end = SCREENS[index + 1][0] if index + 1 < len(SCREENS) else None
    planes[state]['times'] = list(planes[state]['times']) + [t, end if end is not None else -1.0]
for state, obj in planes.items():
    full = obj.scale.copy()
    times = list(obj['times'])
    obj.scale = full * 0.0001
    key(obj, 'scale', 0, 'CONSTANT')
    for t_on, t_off in zip(times[::2], times[1::2]):
        obj.scale = full
        key(obj, 'scale', max(t_on, 0.001), 'CONSTANT')
        if t_off >= 0:
            obj.scale = full * 0.0001
            key(obj, 'scale', t_off, 'CONSTANT')
screen_light = sets.light('screen_light', 'AREA', H(x, y + 0.3, z), 60.0, (0.6, 0.4, 1.0), ship['col'], size=1.2,
                          rot=(math.pi / 2, 0, 0))

# our left tower: destroyed at T_BOOM (parts fly, an explosion card, rubble and a fire light stay)
tower = yard['towers']['our_left']
random.seed(9)
for part in tower['parts']:
    key(part, 'location', T_BOOM)
    key(part, 'rotation_euler', T_BOOM)
    start = part.location.copy()
    out = Vector((random.uniform(-1, 1), random.uniform(-1, 1), 0)) * random.uniform(1.0, 3.2)
    for step in range(1, 7):
        u = step / 6
        part.location = (start.x + out.x * u, start.y + out.y * u, max(0.25, start.z + 3.0 * u - 9.0 * u * u))
        part.rotation_euler = (random.uniform(-2, 2) * u, random.uniform(-2, 2) * u, part.rotation_euler.z)
        key(part, 'location', T_BOOM + 0.9 * u)
        key(part, 'rotation_euler', T_BOOM + 0.9 * u)
boom_card = fxcard.card(os.path.join(FX_DIR, 'explosion.mp4'), location=(-5.5, -9.0, 3.4), height=9.0, cam=cam, strength=1.8, name='fx_boom',
                        light=0.0)
boom_card.data.materials[0].node_tree.nodes['Image Texture'].name = 'clip'
CARDS = [dict(name='fx_boom', t0=round(T_BOOM, 3), fps=59.94, n=120)]
boom_light = sets.light('boom_light', 'POINT', (-5.5, -9.0, 3.0), 0.0, (1.0, 0.5, 0.15), sc.collection, size=1.5)
for t, energy in ((T_BOOM - 0.05, 0.0), (T_BOOM + 0.08, 60000.0), (T_BOOM + 0.8, 9000.0), (T_BOOM + 2.0, 2500.0)):
    boom_light.data.energy = energy
    boom_light.data.keyframe_insert('energy', frame=F(t))

# the WAGMI bubble pops up over our king tower
bubble_mat = sets.image_material('bubble', os.path.join(TEX_DIR, 'bubble_wagmi.png'), emit=0.9, alpha=True)
bubble = sets.plane('bubble', 6.4, 4.0, (0.0, -13.5, 8.4), bubble_mat, yard['col'])
track = bubble.constraints.new('TRACK_TO')
track.target = cam
track.track_axis = 'TRACK_Z'
track.up_axis = 'UP_Y'
full = bubble.scale.copy()
for t, factor in ((0, 0.0001), (T_EMOTE, 0.0001), (T_EMOTE + 0.12, 1.25), (T_EMOTE + 0.25, 0.95), (T_EMOTE + 0.35, 1.0), (T_EMOTE + 4.0, 1.0),
                  (T_EMOTE + 4.1, 0.0001)):
    bubble.scale = full * factor
    key(bubble, 'scale', t, 'LINEAR')

# trampoline dips when the house lands; the duck rocks after the splash
mat_obj = next(obj for obj in yard['trampoline'].children if obj.name.startswith('tramp_mat'))
for t, dz in ((T_TRAMP - 0.05, 0.0), (T_TRAMP + 0.12, -0.75), (T_TRAMP + 0.3, 0.25), (T_TRAMP + 0.45, 0.0)):
    mat_obj.location.z = 1.3 + dz
    key(mat_obj, 'location', t, 'BEZIER')
duck = yard['duck']
duck.rotation_mode = 'XYZ'
duck.rotation_euler = (0, 0, math.radians(105))
key(duck, 'rotation_euler', 0)
for index in range(40):
    t = T_SPLASH + 0.1 + index * 0.12
    amount = math.exp(-index * 0.09) * 0.32
    duck.rotation_euler = (amount * math.sin(index * 1.3), amount * 0.6 * math.cos(index * 1.1), math.radians(105))
    key(duck, 'rotation_euler', t, 'BEZIER')

# copium drips from the pipe during the alarm
drip_mat = sets.material('drip', (0.6, 0.2, 1.0), rough=0.1, emit=(0.7, 0.3, 1.0), strength=2.5)
for index in range(26):
    drop = sets.sphere('drip', 0.035, (0, 0, 0), drip_mat, ship['col'], scale=(1, 1, 1.8))
    y = random.uniform(-4.5, 4.0)
    t0 = T_FULL + random.uniform(0.0, 9.0)
    drop.location = H(-1.55, y, 2.8)
    key(drop, 'location', t0)
    drop.location = H(-1.55, y, 0.05)
    key(drop, 'location', t0 + 0.55)
    show(drop, t0, t0 + 0.55)

# ================================================================ finish
N_FILM = int(round(FILM * FPS))
for actor in A.values():
    actor.build(T_END + 2)
sc.frame_start = 1
sc.frame_end = int(F(T_END)) + 2


def film_time(a):
    for item in SHOTS:
        a1 = item['a0'] + (item['t1'] - item['t0']) * item['s0']
        if item['a0'] <= a < a1 + 1e-6:
            return item['t0'] + (a - item['a0']) / item['s0']
    return SHOTS[-1]['t1']


for cue in CUES:
    if 'f' not in cue:
        cue['f'] = round(film_time(cue['a']), 3)
    cue.update(dur=VO[cue['id']]['dur'], who=VO[cue['id']]['who'], sub=VO[cue['id']]['sub'])
for item in EVENTS:
    item['f'] = round(film_time(item['a']), 3)
    if 'until' in item:
        item['f1'] = round(film_time(item['until']), 3)
json.dump(dict(fps=FPS, last=N_FILM, t_card=round(T_CARD, 3), t_film=round(T_CARD + END_CARD, 3), shots=SHOTS, cues=CUES, events=EVENTS,
               cards=CARDS), open(os.path.join(HERE, 'edl.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=False)
print('BUILT', OUT, 'shots', len(SHOTS), 'film', round(T_CARD, 2), '+', END_CARD, 'frames', N_FILM)
