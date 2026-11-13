"""DAWN PATROL (a Meme Royale war short, the air-raid sequel to LAST LINE): the game's own characters fly bombers over the same battlefield.
blender -b -P air.py -- --out scene.blend [--res 1080]      Env: GAME (the game's assets), W (work folder: timeline.json).
It reuses LAST LINE's engine (war.py: shots, units, arena, fire/smoke/blast effects) and adds aircraft (built from primitives, with the game's
characters in the cockpits), falling bombs, anti-aircraft fire, a burning plane and a parachute."""
import bpy, sys, os, math, json, random
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'war'))
import war
from war import *                                    # V, ramp, ease, lerp, act, go, thrown, shot, tracers, poses, WUnit, MATS, obj, key3, K helpers ...
from mathutils import Vector, Euler

game.H.update(pepe=1.3, chillguy=1.45, troll=1.4, wojak=1.4, pnut=1.9)
OUR_COL = (0.25, 0.85, 0.45)
GIGA_FLIP = PI                                       # GIGA's model faces the other way from the rest of the cast


# ------------------------------------------------------------------ aircraft
def _part(root, mesh, loc, scale, mat, rot=(0, 0, 0)):
    if mesh == 'sphere': bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0)
    elif mesh == 'cyl': bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=1.0, depth=1.0)
    elif mesh == 'torus': bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.14, major_segments=32, minor_segments=8)
    else: bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object; o.scale = scale; o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; o.data.materials.append(mat)
    if mesh in ('sphere', 'cyl'):
        for p in o.data.polygons: p.use_smooth = True
    o.parent = root; o.visible_shadow = True; return o


def build_plane(name, heavy, col):
    """A WWI-style biplane (heavy=False) or a twin-engined bomber (heavy=True). The nose points to -Y (like the game's units), up is +Z.
    Returns the root empty, the propeller discs (spun per frame), the scarf and the bombs hanging under it."""
    root = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(root); root.rotation_mode = 'XYZ'
    body = sets.flat(name + '_body', col, 0.5); dark = sets.flat(name + '_dark', (0.07, 0.07, 0.08), 0.45, metal=0.5); wood = sets.flat(name + '_wood', (0.45, 0.28, 0.14), 0.6)
    white = sets.flat(name + '_white', (0.92, 0.92, 0.9), 0.5); ring = sets.flat(name + '_ring', OUR_COL, 0.5); red = sets.flat(name + '_red', (0.85, 0.12, 0.1), 0.5)
    S = 1.55 if heavy else 1.0
    P = []; bombs = []; scarf = None
    _part(root, 'sphere', (0, 0, 0), (0.42 * S, 2.0 * S, 0.40 * S), body)                                   # fuselage
    _part(root, 'sphere', (0, 1.75 * S, 0.06), (0.22 * S, 1.2 * S, 0.2 * S), body)                           # tail boom
    _part(root, 'box', (0, 2.75 * S, 0.5 * S), (0.07, 0.75 * S, 0.9 * S), body)                              # fin
    _part(root, 'box', (0, 2.7 * S, 0.12 * S), (2.0 * S, 0.6 * S, 0.07), body)                               # tailplane
    _part(root, 'cyl', (0, -1.95 * S, 0.0), (0.44 * S, 0.44 * S, 0.5), dark, (90, 0, 0))                    # cowling
    _part(root, 'sphere', (0, -2.28 * S, 0.0), (0.12 * S, 0.12 * S, 0.12 * S), dark)
    if not heavy: _part(root, 'sphere', (0, -0.05, 0.32), (0.4, 0.56, 0.44), body)                           # the hump that hides the pilot's legs
    _part(root, 'torus', (0, -0.05 * S, (0.36 if heavy else 0.62) * S), (0.36 * S, 0.36 * S, 0.36 * S), dark)   # the cockpit rim
    if heavy:
        _part(root, 'box', (0, -0.3 * S, 0.12), (7.6, 1.25, 0.12), body)                                       # one broad wing
        _part(root, 'box', (0, -0.3 * S, 0.12), (7.6, 0.4, 0.14), white)
        for sx in (-1, 1):
            _part(root, 'cyl', (sx * 1.9, -0.9, 0.05), (0.38, 0.38, 1.5), dark, (90, 0, 0)); _part(root, 'sphere', (sx * 1.9, -1.72, 0.05), (0.14, 0.14, 0.14), dark)
            d = _part(root, 'cyl', (sx * 1.9, -1.8, 0.05), (0.95, 0.95, 0.012), dark, (90, 0, 0)); d.data.materials.clear(); d.data.materials.append(MATS['propdisc']); P.append((d, sx * 1.9, -1.8, 0.05))
            _part(root, 'cyl', (sx * 3.2, -0.3 * S, 0.19), (0.34, 0.34, 0.015), ring, (0, 0, 0)); _part(root, 'cyl', (sx * 3.2, -0.3 * S, 0.2), (0.17, 0.17, 0.015), white)
        for i in range(4): bombs.append(_part(root, 'sphere', (-0.36 + 0.24 * i, 0.2 + 0.3 * (i % 2), -0.44), (0.1, 0.34, 0.1), MATS['bombmat']))
    else:
        for z, w in ((0.74, 5.2), (-0.12, 4.6)):
            _part(root, 'box', (0, -0.55, z), (w, 0.95, 0.075), body); _part(root, 'box', (0, -0.55, z + 0.005), (w, 0.24, 0.08), white)
            for sx in (-1, 1): _part(root, 'cyl', (sx * (w / 2 - 0.45), -0.55, z + 0.045), (0.3, 0.3, 0.012), ring); _part(root, 'cyl', (sx * (w / 2 - 0.45), -0.55, z + 0.055), (0.15, 0.15, 0.012), red)
        for sx in (-1, 1):
            for yy in (-0.2, -0.9): _part(root, 'box', (sx * 1.35, yy, 0.31), (0.05, 0.05, 0.86), wood); _part(root, 'box', (sx * 0.5, yy, 0.38), (0.05, 0.05, 0.62), wood, (0, 25 * sx, 0))
            _part(root, 'cyl', (sx * 0.5, -0.8, -0.62), (0.05, 0.05, 0.62), dark, (0, 14 * sx, 0)); _part(root, 'cyl', (sx * 0.62, -0.84, -0.9), (0.24, 0.24, 0.1), dark, (0, 90, 0))
        d = _part(root, 'cyl', (0, -2.27, 0), (1.05, 1.05, 0.012), dark, (90, 0, 0)); d.data.materials.clear(); d.data.materials.append(MATS['propdisc']); P.append((d, 0, -2.27, 0))
        for i in range(2): bombs.append(_part(root, 'sphere', (-0.2 + 0.4 * i, 0.1, -0.5), (0.1, 0.3, 0.1), MATS['bombmat']))
        scarf = _part(root, 'box', (0, 0.9 * S, 0.9), (0.14, 1.25, 0.03), red)                                  # the pilot's scarf, streaming back
    blades = []
    for d, x, y, z in P:                                                                                         # two blades per propeller, spun by hand
        b = _part(root, 'box', (x, y - 0.02, z), (d.scale.x * 2, 0.04, 0.09), dark); blades.append((b, x, y, z))
    return dict(root=root, blades=blades, scarf=scarf, bombs=bombs, heavy=heavy)


def heading_of(fn, u, dt=0.06):
    a, b = fn(u - dt), fn(u + dt); d = b - a; return hd(Vector((d.x, d.y))), math.atan2(d.z, max(0.05, math.hypot(d.x, d.y)))


def plane_pose(fn, u, roll=0.0):
    """Euler for a plane flying along fn: yaw to the heading, nose to the climb angle (nose up = -x rotation), bank (roll about the nose axis)."""
    h, pitch = heading_of(fn, u); return (-pitch, roll, h)


# ------------------------------------------------------------------ the film
ME = ('pnut', 0); WING = ('pnut', 1); HEAVY = ('pnut', 2)
CH = ('chillguy', 0)
OUR = [('chillguy', 1, V(-5.4, -6.4)), ('wojak', 0, V(-3.7, -6.1)), ('wojak', 1, V(-4.6, -5.4)), ('chillguy', 2, V(-6.2, -5.5)), ('wojak', 2, V(-3.1, -5.2)),
       ('chillguy', 3, V(-5.0, -7.4)), ('wojak', 3, V(-3.6, -7.2)), ('wojak', 4, V(-6.0, -7.9))]
TROLLS = [('troll', 0, V(-5.0, 5.2)), ('troll', 1, V(-6.4, 6.4)), ('troll', 2, V(-3.8, 6.0)), ('troll', 3, V(-5.6, 8.0)), ('troll', 4, V(-4.2, 8.2)), ('troll', 5, V(-7.0, 4.6)), ('troll', 6, V(-3.0, 4.4))]
TOWER = sets.ENEMY_KING.to_2d(); T3 = TOWER.to_3d()


def fly(p0, p1, u0, u1, bob=0.0, ph=0.0):
    """Straight and level from p0 (x, y, z) to p1 between u0 and u1 (before and after it keeps going at the same speed), with a lazy bob."""
    d = (p1 - p0) / (u1 - u0)
    return lambda u: p0 + d * (u - u0) + V(0.0, 0.0, bob * sn(u * 1.7 + ph))


def head_dir(h): return V(sn(h), -math.cos(h))                      # the direction a unit with heading h faces (hd(d) = atan2(d.x, -d.y))


FLY_RX = math.radians(50)
FLY = lambda u: {'LeftArm': (-10, 0, -62 + 6 * sn(u * 5)), 'RightArm': (-10, 0, 62 - 6 * sn(u * 5.4)), 'Spine2': (-14, 0, 0), 'Head': (-28, 0, 0)}


def cockpit(kind, i, fn, dy=0.0, dz=-0.2, clips=(), pose=None, rx=0.0, roll=None):
    """A character sitting in a plane's cockpit: dy along the nose axis toward the tail, dz relative to the fuselage axis."""
    dy, dz = 0.45, -0.75                                           # PNUT lies along his flight path, arms out, head forward
    def pos(u):
        h, _ = heading_of(fn, u); c = fn(u); n = head_dir(h); return V(c.x, c.y) - n * dy
    def z(u): return fn(u).z + dz
    def hh(u): return heading_of(fn, u)[0]
    def pr(u): return rx + heading_of(fn, u)[1] * -1.0 * 0.9
    ps = (lambda u: {**FLY(u), **pose(u)}) if pose else FLY
    a = act(kind, i, pos, hh, clips, z=z, rx=lambda u: FLY_RX - heading_of(fn, u)[1] + rx, pose=ps)
    return a


def plane_fx(key, fn, heavy=False, col=(0.35, 0.42, 0.22), roll=None, scarf=True, drop=(), smoke=None, fire=None, dive=None):
    """('plane', ...) effect: the aircraft itself, keyed on every frame of the shot. drop = shot times at which the bombs hanging under it go."""
    return ('plane', key, fn, heavy, col, roll, scarf, tuple(drop), smoke, fire, dive)


def bomb_fx(u0, src, dst, fall, size=2.0, extra=()):
    """A bomb dropped at u0 from src to dst; it hits at u0 + fall with the whole bang."""
    t = u0 + fall; d2 = V(dst.x, dst.y)
    return [('bomb', u0, src, dst, fall), ('boom', t, dst + V(0, 0, 0.3), size), ('ring', t, dst + V(0, 0, 0.15), size * 1.8), ('burst', t, d2, int(22 * size), size * 1.05, 0.035),
            ('flash', t, dst + V(0, 0, 1.0), 9000 * size)] + list(extra)


def aa(n, seed, u0, dur, aim, base_x=(-4.0, 4.0), y0=9.5):
    """Anti-aircraft tracers: from the enemy lines up to where the planes will be."""
    return ('aa', n, seed, u0, dur, aim, base_x, y0)


def flak(u0, p, size=0.9): return ('boom', u0, p, size)


ARM_UP = lambda u: {'LeftArm': (-160, 0, 16), 'RightArm': (-160, 0, -16)}
def cheer(seed): return lambda u: {'LeftArm': (-150 + 25 * sn(u * 9 + seed), 0, 14), 'RightArm': (-150 + 25 * sn(u * 8.3 + seed * 1.7), 0, -14), 'Head': (-14, 0, 0)}
def look_up(deg=-30, u0=0.0, d=0.6): return lambda u: {'Head': (deg * ease(ramp(u, u0, u0 + d)), 0, 0), 'Spine2': (deg * 0.3 * ease(ramp(u, u0, u0 + d)), 0, 0)}


_shot_war = shot


def shot(t0, t1, cam, *rest, **kw):
    """Every camera move is steadier than the first cut: handheld shake and roll cut to about a third."""
    def cam2(k, u):
        d = dict(cam(k, u)); d['shake'] = d.get('shake', 0.0) * 0.3; d['roll'] = d.get('roll', 0.0) * 0.45; return d
    return _shot_war(t0, t1, cam2, *rest, **kw)


# ------------------------------------------------------------------ the battlefield: troops spread over the whole field, each busy with something
OURK = ['swordcat', 'floki', 'toshi', 'walter', 'pepe', 'bonk', 'cate', 'chillguy', 'wojak']
THEIRK = ['troll', 'goat', 'troll', 'slerf', 'troll', 'giga']
KEEPOUT = [(p.x, p.y) for _, _, p in OUR] + [(p.x, p.y) for _, _, p in TROLLS] + [(LX, 6.2), (-3.2, -8.0), (-3.2, -10.2), (-4.0, -9.4)]


KEEPOUT += [(-5.2, 2.4), (-2.8, 2.4), (-4.6, 2.6), (-4.6, 3.8), (-3.6, 4.2), (-3.6, 9.4), (-3.6, 5.0)] + [(-9.4 + 1.55 * j, -4.6) for j in range(9)]


def crowd(seed, zones, dur=3.4):
    """zones: (x0, x1, y0, y1, n, mode) with mode duel | march | cheer | guard. Returns acts, each with a (kind, index) of its own (indices from 20 up, reused shot to shot)."""
    r = random.Random(seed); out = []; cnt = {}
    def key(kind):
        cnt[kind] = cnt.get(kind, 20 - 1) + 1; return (kind, cnt[kind])
    def free(x0, x1, y0, y1, taken):
        for _ in range(60):
            p = (r.uniform(x0, x1), r.uniform(y0, y1))
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) > 1.5 for q in KEEPOUT + taken): return p
        return None
    taken = []
    for (x0, x1, y0, y1, n, mode) in zones:
        for j in range(n):
            p = free(x0, x1, y0, y1, taken)
            if p is None: continue
            taken.append(p); ph = r.uniform(0, 1.2)
            if mode == 'duel':                                                # one of ours and one of theirs, locked together
                ko, kt = key(r.choice(OURK)), key(r.choice(THEIRK)); a_ = V(p[0], p[1]); b_ = V(p[0] + r.uniform(-0.25, 0.25), p[1] + 1.05)
                def seqs(first, kind, ph=ph, wob=r.uniform(0.7, 1.0)):
                    t = -ph; L_ = []; k = first
                    while t < dur + 1: L_.append((t, 'attack1' if (k % 2 or kind == 'slerf') else 'attack2', wob)); t += 0.95 / wob; k += 1
                    return L_
                die_t = r.uniform(1.0, dur - 0.5) if r.random() < 0.45 else None
                ca = seqs(0, ko[0]); cb = seqs(1, kt[0])
                if die_t is not None: cb = [c for c in cb if c[0] < die_t] + [(die_t, 'die', 1.0)]; ca = [c for c in ca if c[0] < die_t + 0.6] + [(die_t + 0.6, 'ready', 1.0)]
                gh = N if ko[0] != 'giga' else N + GIGA_FLIP; th = S_ + (GIGA_FLIP if kt[0] == 'giga' else 0.0)
                out.append(act(ko[0], ko[1], a_, gh, ca)); out.append(act(kt[0], kt[1], b_, th, cb))
            elif mode == 'march':                                              # a few of theirs charging our line
                kt = key(r.choice(THEIRK)); y1 = p[1] - r.uniform(5.0, 8.0); th = S_ + (GIGA_FLIP if kt[0] == 'giga' else 0.0)
                out.append(act(kt[0], kt[1], go(V(p[0], p[1]), V(p[0] + r.uniform(-1.2, 1.2), y1), 0, dur), th, [(-ph, 'run', 1.15)]))
            elif mode == 'advance':                                            # ours charging the river
                ko = key(r.choice(OURK)); y1 = p[1] + r.uniform(5.0, 8.0)
                out.append(act(ko[0], ko[1], go(V(p[0], p[1]), V(p[0] + r.uniform(-1.0, 1.0), y1), 0, dur), N + (GIGA_FLIP if ko[0] == 'giga' else 0.0), [(-ph, 'run', 1.15)]))
            elif mode == 'cheer':
                ko = key(r.choice(OURK)); out.append(act(ko[0], ko[1], V(p[0], p[1]), N + r.uniform(-0.35, 0.35), [(-ph, 'idle', 1.0), (0.3 + ph, 'win', 1.0)], pose=(lambda u, s=ph * 7: cheer(s)(u) if u > 0.3 + s / 7 else {})))
            else:                                                              # guard: ours holding the line, ready
                ko = key(r.choice(OURK)); out.append(act(ko[0], ko[1], V(p[0], p[1]), N + r.uniform(-0.3, 0.3), [(-ph, 'ready', 1.0)], pose=crouch(14, ph * 5)))
    return out


# per shot: where the fighting is (x0, x1, y0, y1, count, mode); every camera keeps its own foreground clear
CROWD = {
    'pinned': [(-9, 3, 0.5, 5.5, 3, 'duel'), (-9, 3, 7.0, 13.0, 5, 'march')],
    'looks_up': [(0.5, 5, -4, 4, 2, 'duel')],
    'flyover': [(-10, 4, -3.0, 3.0, 4, 'duel'), (-10, 4, 6, 13, 6, 'march'), (-10, 4, -16, -9, 6, 'guard')],
    'flak': [(-10, 4, -6, 5, 5, 'duel'), (-10, 4, 8, 15, 6, 'march'), (-10, 4, -16, -11, 4, 'guard')],
    'bombrun': [(-10, 4, -4, 6, 4, 'duel'), (-10, 4, 9, 18, 6, 'march'), (-10, 4, -16, -10, 6, 'guard')],
    'lane': [(-9, -4.5, 5, 12, 3, 'duel'), (1.5, 5, 5, 12, 3, 'duel')],
    'giga': [(-9, -5, 9, 15, 3, 'duel'), (0, 4, 8, 15, 3, 'duel'), (-9, 4, -3, 2, 3, 'guard')],
    'hit': [(1.5, 7, -3, 9, 5, 'duel')],
    'dive': [(-9, 4, 0, 13, 6, 'duel'), (-9, 4, -14, -4, 5, 'guard')],
    'chute': [(-10, 4, 2, 13, 6, 'duel'), (-10, 4, -12, 0, 4, 'cheer')],
    'home': [(-10, 4, -3, 8, 6, 'cheer'), (-10, 4, 10, 16, 3, 'duel')],
    'crane_dawn': [(-10, 4, -15, -8, 10, 'guard'), (-10, 4, 6, 15, 10, 'guard'), (-10, 4, -3, 3, 4, 'duel')],
    'wing_pass': [(-10, -7, -10, 10, 5, 'duel'), (-2, 4, -10, 10, 5, 'duel')],
    'barrel_roll': [(-10, 4, -6, 8, 5, 'duel'), (-10, 4, 10, 18, 5, 'march')],
    'charge_wide': [(-10, 4, -10, -3, 9, 'advance'), (-10, 4, 5, 13, 9, 'march'), (-10, 4, -2, 3, 7, 'duel')],
    'duel': [(-10, -7.5, 0, 9, 3, 'duel'), (-2.5, 3, 0, 9, 3, 'duel')],
    'slam': [(-10, -7.5, -2, 9, 3, 'duel'), (-1.5, 4, -2, 12, 5, 'duel')],
    'titan': [(-10, -7.5, 0, 14, 3, 'duel'), (0.5, 4, 0, 14, 3, 'duel'), (-10, 4, -10, -3, 5, 'advance')],
    'aerial_support': [(-10, 3, -4, 5, 5, 'duel'), (-10, 3, 12, 18, 4, 'march')],
}


ORDER = ['crane_dawn', 'pinned', 'looks_up', 'flyover', 'muster', 'cockpit', 'wing_pass', 'flak', 'barrel_roll', 'bombrun', 'carpet', 'lane', 'giga',
         'charge_wide', 'duel', 'slam', 'titan', 'aerial_support', 'hit', 'dive', 'chute', 'home']


def new_shots():
    """The second half of the film: ten new set pieces between the original shots. Durations are multiples of 0.1 s so every shot is a whole number of frames."""
    NS = {}
    # a slow crane up over both armies in the moonlight
    NS['crane_dawn'] = shot(0, 3.6, lambda k, u: dict(pos=V(-15.0 + 2.5 * ease(k), -19.0 + 1.5 * k, 1.1 + 8.0 * ease(k)), tgt=V(-3.0, 1.0, 1.4 + 0.5 * k), fov=52, fstop=5.6, focus=22.0, shake=0.002),
                            [], [tracers(10, 31, 2.6), ('boom', 1.1, V(-6.5, 6.0, 0.4), 1.4), ('boom', 2.2, V(-1.5, 3.0, 0.4), 1.2)], name='crane_dawn')
    # the line, dollying past: every kind of fighter we have, readying
    kinds = ['swordcat', 'floki', 'toshi', 'walter', 'pepe', 'bonk', 'cate', 'chillguy', 'wojak']; xs = [-9.4 + 1.55 * j for j in range(9)]
    line = [act(kd, 30, V(xs[j], -4.6 + 0.35 * sn(j * 2.3)), N, [(-0.3 * j, 'ready', 1.0), (0.5 + 0.2 * j, 'attack1', 0.7), (1.6 + 0.1 * j, 'ready', 1.0)], pose=crouch(16, j)) for j, kd in enumerate(kinds)]
    NS['muster'] = shot(0, 2.8, lambda k, u: dict(pos=V(lerp(5.2, -10.6, ease(k)), -8.6, 1.1), tgt=V(lerp(5.2, -10.6, ease(k)) - 1.2, -4.2, 1.25), fov=40, fstop=2.8, focus=4.6, shake=0.002), line, [tracers(8, 32, 1.8)], name='muster')
    # a PNUT skims the ground; acorns walk through the trolls ahead of him
    fw = fly(V(-4.6, -26.0, 2.1), V(-4.6, 16.0, 2.3), 0.0, 2.6, 0.1, 0.5)
    BM3 = []; TH3 = []
    for j, u0 in enumerate((0.9, 1.2, 1.5, 1.8)):
        dst = V(-4.6 + 1.1 * sn(j * 2.0), fw(u0).y + 8.0, 0.0); BM3 += bomb_fx(u0, fw(u0) + V(0, 0, -0.5), dst, 0.55, 2.0)
        TH3.append(thrown('troll', 41 + j, V(dst.x, dst.y), V(dst.x + sn(j * 3.1) * 2.2, dst.y + 2.4), u0 + 0.55, 0.6, 1.8, 1.1 + 0.2 * j, pre='run', seed=j + 1, h=S_, pre_from=V(dst.x, dst.y + 3.0)))
    NS['wing_pass'] = shot(0, 2.6, lambda k, u: dict(pos=fw(u) + V(2.0, -4.2, 1.3 - 0.4 * k), tgt=fw(u) + V(0, 3.0, -0.2), fov=64, fstop=6.0, focus=7.0, shake=0.004),
                           [cockpit('pnut', 0, fw, 0.0, 0.0, [(0, 'idle', 1.0)])] + TH3, [plane_fx('lead', fw, drop=(0.9, 1.2, 1.5, 1.8))] + BM3 + [tracers(8, 33, 1.6)], slow=0.8, name='wing_pass')
    # weaving through the flak
    wv = lambda u: V(-3.0 + 2.4 * sn(u * 3.4), -8.0 + 11.5 * u, 5.4 + 0.8 * sn(u * 4.3))
    NS['barrel_roll'] = shot(0, 2.4, lambda k, u: dict(pos=wv(u) + V(5.2 - 1.2 * k, -0.8, 0.4), tgt=wv(u) + V(0, 0.9, -0.2), fov=46, fstop=3.6, focus=5.6, shake=0.004),
                             [cockpit('pnut', 0, wv, 0.0, 0.0, [(0, 'idle', 1.0)])],
                             [plane_fx('lead', wv), aa(26, 77, 0.0, 1.8, lambda u: wv(u + 0.4), (-4.5, 4.5)), flak(0.3, wv(0.6) + V(2.2, 2.0, 1.6), 1.1), flak(0.9, wv(1.2) + V(-2.0, 2.2, -1.0), 1.0), flak(1.4, wv(1.6) + V(1.8, 1.5, 1.2), 1.2)],
                             slow=0.7, name='barrel_roll')
    # a stick of acorns marches toward the camera under a long lens
    CM = []; TH5 = []; RUN5 = []
    for j in range(6):
        y0 = 10.5 - 1.9 * j; x0 = -5.0 + 0.9 * sn(j * 1.7); u0 = 0.05 + 0.24 * j
        CM += bomb_fx(u0, V(x0, y0 + 1.0, 9.5), V(x0, y0, 0.0), 0.5, 2.2)
        TH5.append(thrown('troll', 50 + j, V(x0, y0), V(x0 + sn(j * 2.6) * 2.4, y0 - 2.4), u0 + 0.5, 0.6, 1.9, 1.0 + 0.2 * j, pre='run', seed=j + 2, h=S_, pre_from=V(x0, y0 + 3.5)))
    for j in range(4): RUN5.append(act('troll', 60 + j, go(V(-6.5 + 1.6 * j, 15.0 + 1.2 * j), V(-6.5 + 1.6 * j, 5.0 + 1.2 * j), 0, 1.65), S_, [(-0.1 * j, 'run', 1.25)]))
    NS['carpet'] = shot(0, 3.0, lambda k, u: dict(pos=V(-5.0, -14.0, 0.9), tgt=V(-4.8, 10.0, 1.6 + 0.3 * k), fov=24, fstop=4.0, focus=22.0, shake=0.003), TH5 + RUN5, CM + [tracers(10, 34, 2.0)], slow=0.55, name='carpet')
    # both armies collide: an aerial track along the river
    NS['charge_wide'] = shot(0, 3.4, lambda k, u: dict(pos=V(lerp(-14.0, -0.5, ease(k)), -7.0, 5.8), tgt=V(lerp(-14.0, -0.5, ease(k)) + 5.0, 2.0, 1.0), fov=58, fstop=5.6, focus=14.0, shake=0.003), [],
                             [tracers(14, 35, 2.4), ('boom', 0.9, V(-5.0, 1.0, 0.4), 1.3), ('boom', 1.7, V(-2.0, 2.0, 0.4), 1.4), ('boom', 2.4, V(-8.0, 3.0, 0.4), 1.2)], name='charge_wide')
    # FLOKI against the goat, orbiting, slow
    C = V(-5.2, 2.4)
    NS['duel'] = shot(0, 2.6, lambda k, u: dict(pos=V(C.x + 3.4 * math.cos(3.1 + 1.5 * k), C.y + 3.4 * sn(3.1 + 1.5 * k), 1.2 - 0.3 * k), tgt=V(C.x, C.y, 1.0), fov=38, fstop=2.8, focus=3.4, shake=0.002),
                      [act('floki', 30, V(C.x, C.y - 0.55), N, [(0, 'ready', 1.0), (0.2, 'attack1', 0.8), (1.1, 'attack2', 0.8)]),
                       act('goat', 30, V(C.x, C.y + 0.55), S_, [(0, 'ready', 1.0), (0.2, 'attack1', 0.7), (0.9, 'hit', 1.0), (1.5, 'die', 1.0)]),
                       act('toshi', 30, V(C.x + 2.4, C.y - 0.3), N, [(0, 'ready', 1.0), (0.4, 'attack2', 0.8), (1.3, 'attack1', 0.8)]), act('troll', 70, V(C.x + 2.4, C.y + 0.7), S_, [(0, 'ready', 1.0), (0.4, 'attack1', 0.8), (1.2, 'die', 1.0)])],
                      [('flash', 0.9, V(C.x, C.y, 1.2), 4000), ('burst', 0.9, C, 16, 0.8, 0.03), ('boom', 0.95, V(C.x, C.y + 0.4, 0.6), 0.8), ('burst', 1.3, V(C.x + 2.4, C.y + 0.4), 12, 0.7, 0.03)], slow=0.5, name='duel')
    # BONK's bat: a troll flies
    NS['slam'] = shot(0, 2.4, lambda k, u: dict(pos=V(-9.0 + 1.0 * k, 3.0, 0.7), tgt=V(-4.6, 3.0, 1.3).lerp(V(-3.8, 8.0, 2.6), ease(ramp(u, 0.8, 1.8))), fov=44, fstop=3.2, focus=4.6, shake=0.003),
                      [act('bonk', 30, V(-4.6, 2.6), N, [(0, 'ready', 1.0), (0.25, 'attack3', 0.8), (1.4, 'ready', 1.0)]),
                       thrown('troll', 71, V(-4.6, 3.8), V(-3.6, 11.0), 0.85, 0.8, 3.0, 1.4, pre='idle', seed=3, h=S_)],
                      [('flash', 0.85, V(-4.6, 3.4, 1.3), 6000), ('burst', 0.85, V(-4.6, 3.4), 20, 1.0, 0.04), ('ring', 0.85, V(-4.6, 3.4, 0.2), 3.0), ('boom', 0.9, V(-4.6, 3.4, 0.4), 1.2)], slow=0.45, name='slam')
    # GIGA against the giant SLERF
    M = V(-3.6, 6.8)
    NS['titan'] = shot(0, 3.8, lambda k, u: dict(pos=V(M.x + (7.5 - k) * math.cos(2.5 + 1.4 * ease(k)), M.y + (7.5 - k) * sn(2.5 + 1.4 * ease(k)), 0.5 + 0.9 * k), tgt=V(M.x, M.y, 2.0), fov=42, fstop=3.6, focus=7.0, shake=0.003),
                       [act('giga', 30, V(-3.6, 4.2), N + GIGA_FLIP, [(0, 'ready', 1.0), (1.0, 'attack1', 0.8), (2.2, 'attack2', 0.8)]),
                        act('slerf', 30, V(-3.6, 9.4), S_, [(0, 'ready', 1.0), (1.3, 'attack1', 0.7), (2.4, 'hit', 1.0), (2.9, 'ready', 1.0)])],
                       [('ring', 1.6, V(-3.6, 6.9, 0.2), 5.0), ('boom', 1.6, V(-3.6, 6.8, 1.6), 2.4), ('burst', 1.6, V(-3.6, 6.9), 30, 2.0, 0.05), ('flash', 1.6, V(-3.6, 6.8, 2.0), 30000), ('ring', 2.6, V(-3.6, 7.5, 0.2), 4.0), ('boom', 2.6, V(-3.6, 7.5, 1.4), 1.9)],
                       slow=0.6, name='titan')
    # two PNUTs bomb the giant
    f1 = fly(V(-8.0, -4.0, 8.5), V(-2.0, 16.0, 3.4), 0.0, 2.4, 0.1, 0.5); f2 = fly(V(0.0, -6.0, 9.5), V(-5.0, 15.0, 4.2), 0.0, 2.4, 0.1, 1.5)
    AB = bomb_fx(0.6, f1(0.6) + V(0, 0, -0.5), V(-4.2, 9.0, 0.0), 0.55, 2.6) + bomb_fx(0.9, f2(0.9) + V(0, 0, -0.5), V(-2.8, 9.8, 0.0), 0.55, 2.4) + bomb_fx(1.25, f1(1.25) + V(0, 0, -0.5), V(-3.6, 10.5, 0.0), 0.55, 2.8)
    NS['aerial_support'] = shot(0, 2.6, lambda k, u: dict(pos=V(-12.0, 2.0 + 3.0 * k, 4.2), tgt=V(-3.6, 9.2, 2.0), fov=50, fstop=4.0, focus=14.0, shake=0.003),
                                [cockpit('pnut', 0, f1, 0.0, 0.0, [(0, 'idle', 1.0)]), cockpit('pnut', 1, f2, 0.0, 0.0, [(0, 'idle', 1.0)]),
                                 act('slerf', 30, V(-3.6, 9.4), S_, [(0, 'ready', 1.0), (0.8, 'hit', 0.8), (1.6, 'ready', 1.0)]), act('giga', 30, V(-3.6, 5.0), N + GIGA_FLIP, [(0, 'ready', 1.0), (0.8, 'attack1', 0.8)])],
                                [plane_fx('lead', f1), plane_fx('right', f2)] + AB + [tracers(8, 36, 1.8)], slow=0.8, name='aerial_support')
    return NS


def film():
    SH = []
    FIELD = [act(k, i, p, N, [(-0.4 * j, 'ready' if j % 2 else 'idle', 1.0)], pose=crouch(20, j)) for j, (k, i, p) in enumerate(OUR)]
    P0 = V(-4.0, -9.4)
    # 1. First person, face down behind the line. Distant shells. Somewhere above, a hum.
    SH.append(shot(0.0, 3.2, pov_cam(P0, 6, 4), [act('wojak', 9, P0, N, [], rx=math.radians(86), pose=lambda u: prone(u, 2.5, 1.0, 0.0))] + FIELD +
                   [act('chillguy', 0, V(-3.2, -8.0), N, [(0, 'idle', 1.0)], pose=lambda u: {'Head': (-34 * ease(ramp(u, 1.3, 2.0)), 0, 0)})],
                   [tracers(26, 21, 2.0), ('boom', 0.5, V(-2.0, 5.0, 0.4), 1.3), ('boom', 1.3, V(-7.0, 4.4, 0.4), 1.6), ('boom', 2.0, V(-5.5, 2.5, 0.4), 1.2)], slow=0.6, pov=0.7, name='pinned'))
    # 2. CHILLGUY looks up. Low angle, the sun behind him.
    SH.append(shot(3.2, 5.0, lambda k, u: dict(pos=V(-3.15, -8.8 + 0.1 * k, 0.28), tgt=V(-3.2, -10.2, 1.2 + 0.5 * k), fov=46, fstop=2.4, shake=0.004),
                   [act('chillguy', 0, V(-3.2, -10.2), N, [(0, 'idle', 1.0)], pose=lambda u: {'Head': (-38 * ease(ramp(u, 0.3, 0.9)), 0, 0), 'Spine2': (-8 * ease(ramp(u, 0.3, 0.9)), 0, 0)})],
                   [tracers(14, 22, 1.8), ('boom', 0.9, V(-7.6, -6.5, 0.4), 1.2)], name='looks_up', sub=(0.7, 1.7, 'PNUT. INBOUND.')))
    # 3. The flyover: three planes pass over the line, low, toward the enemy. The line cheers.
    lead = fly(V(-3.0, -24.0, 5.2), V(-3.0, 6.0, 5.8), 0.0, 2.4, 0.15); lft = fly(V(-6.6, -27.0, 5.6), V(-6.6, 3.0, 6.1), 0.0, 2.4, 0.2, 1.0); rgt = fly(V(0.6, -26.0, 5.4), V(0.6, 4.0, 5.9), 0.0, 2.4, 0.2, 2.0)
    SH.append(shot(5.0, 7.6, lambda k, u: dict(pos=V(-4.0, -3.6, 0.3), tgt=V(-3.4, -9.0 + 5.0 * ease(k), 2.2 + 3.6 * ease(k)), fov=72, fstop=5.6, shake=0.012, roll=-3 + 6 * k),
                   [cockpit(*ME, lead, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*WING, rgt, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*HEAVY, lft, 0.1, 0.35, [(0, 'attack1', 0.6)])] +
                   [act(k, i, p, N, [(-0.2 * j, 'idle', 1.0), (0.9 + 0.08 * j, 'win', 1.0)], pose=lambda u, j=j: cheer(j)(u) if u > 1.0 + 0.08 * j else crouch(10, j)(u)) for j, (k, i, p) in enumerate(OUR)],
                   [plane_fx('lead', lead), plane_fx('right', rgt, col=(0.55, 0.4, 0.2)), plane_fx('left', lft, True, (0.3, 0.36, 0.25)), tracers(10, 23, 2.4), ('boom', 1.2, V(-7.0, 5.0, 0.4), 1.4)],
                   slow=0.8, name='flyover'))
    # 4. The cockpit: the lead plane's pilot, scarf streaming.
    lead2 = fly(V(-3.0, -6.0, 5.4), V(-3.0, 26.0, 5.4), 0.0, 2.6, 0.12)
    SH.append(shot(7.6, 9.8, lambda k, u: dict(pos=lead2(u) + V(-1.2 + 0.4 * k, 4.4 - 0.3 * k, -2.7 + 0.2 * k), tgt=lead2(u) + V(0, 0.9, -0.5), fov=36, fstop=2.6, focus=5.0, shake=0.007, roll=3 - 5 * k),
                   [cockpit(*ME, lead2, -0.05, 0.0, [(0, 'idle', 1.0)], pose=lambda u: {'Head': (-6, 20 * ease(ramp(u, 0.2, 0.9)) - 25 * ease(ramp(u, 1.3, 1.9)), 0)})],
                   [plane_fx('lead', lead2), ('boom', 1.1, V(-5.0, 11.0, 0.4), 1.3)], slow=0.8, name='cockpit'))
    # 5. Flak. The enemy opens up; Bonk swats shells off the big bomber's roof with his bat; Cate's engine is hit and starts to smoke.
    L5 = fly(V(-3.0, -2.0, 5.6), V(-3.0, 20.0, 5.8), 0.0, 2.6, 0.2); l5 = fly(V(-6.6, -4.0, 6.0), V(-6.6, 18.0, 6.2), 0.0, 2.6, 0.25, 1.0); r5 = fly(V(0.6, -3.0, 5.8), V(0.6, 19.0, 6.0), 0.0, 2.6, 0.25, 2.0)
    FL = [flak(0.15, V(-1.0, 3.0, 7.2), 0.9), flak(0.45, V(-6.0, 4.4, 8.0), 1.0), flak(0.8, V(-3.8, 5.8, 6.4), 1.1), flak(1.15, V(-8.2, 7.0, 7.4), 0.9), flak(1.5, V(1.6, 7.6, 6.8), 1.0),
          flak(1.85, V(-4.6, 9.2, 8.0), 1.2), flak(2.1, V(-0.6, 10.5, 6.2), 0.9)]
    SH.append(shot(9.8, 12.4, lambda k, u: dict(pos=V(-1.5 - 3 * k, -9.5 + 2 * k, 1.4 + 1.0 * k), tgt=L5(u) + V(0, 0, 0.2), fov=52, fstop=4.0, focus=14.0, shake=0.012 + 0.03 * (0.9 < u < 1.5)),
                   [cockpit(*ME, L5, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*WING, r5, -0.05, 0.0, [(0, 'idle', 1.0)], pose=lambda u: {'Head': (14 * sn(u * 9), 0, 0)}), cockpit(*HEAVY, l5, 0.1, 0.35, [(0, 'attack1', 0.9)])],
                   [plane_fx('lead', L5), plane_fx('right', r5, col=(0.55, 0.4, 0.2), smoke=(1.2, 0.45)), plane_fx('left', l5, True, (0.3, 0.36, 0.25)),
                    aa(24, 24, 0.0, 2.6, lambda u: L5(u + 0.5), (-4.5, 4.5)), aa(18, 25, 0.3, 2.3, lambda u: r5(u + 0.5), (-4.5, 4.5))] + FL, slow=0.7, name='flak'))
    # 6. Over the enemy lane, looking straight down: the planes cross the frame, the bombs fall, and each blast throws a troll.
    L6 = fly(V(-3.0, -6.0, 6.4), V(-3.0, 18.0, 6.4), 0.0, 2.4); l6 = fly(V(-6.6, -7.5, 6.8), V(-6.6, 16.5, 6.8), 0.0, 2.4); r6 = fly(V(0.6, -6.8, 6.6), V(0.6, 17.2, 6.6), 0.0, 2.4)
    FALL = 0.62
    drops = [(0.30, L6, 0), (0.64, L6, 1), (0.98, L6, 3), (0.30, r6, 6), (0.64, r6, 2), (0.30, l6, 5), (0.55, l6, 4), (0.80, l6, None), (1.05, l6, None)]
    BM = []; thrownT = []; seen = set()
    for u0, fn, ti in drops:
        dst = TROLLS[ti][2].to_3d() if ti is not None else V(-5.6 + 1.8 * (u0 > 1.0), 10.6 + 0.9 * (u0 > 1.0), 0.0)
        BM += bomb_fx(u0, fn(u0) + V(0, 0, -0.5), dst, FALL, 2.1 + 0.2 * (ti is None))
        if ti is not None: thrownT.append(thrown('troll', ti, TROLLS[ti][2], TROLLS[ti][2] + V(sn(ti * 2.1) * 2.0, 2.4), u0 + FALL, 0.6, 1.8, 1.0 + 0.3 * ti, pre='run', seed=ti + 1, h=S_, pre_from=TROLLS[ti][2] + V(0, 2.5)))
    SH.append(shot(12.4, 15.0, lambda k, u: dict(pos=V(-3.0, L6(u).y - 8.5, 10.5 - 1.5 * k), tgt=V(-4.2, L6(u).y + 5.5, 0.6), fov=58, fstop=8.0, roll=-5 + 8 * k, shake=0.009),
                   thrownT + [cockpit(*ME, L6, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*WING, r6, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*HEAVY, l6, 0.1, 0.35, [(0, 'attack1', 0.8)])],
                   [plane_fx('lead', L6, drop=(0.30, 0.64, 0.98)), plane_fx('right', r6, col=(0.55, 0.4, 0.2), drop=(0.30, 0.64)), plane_fx('left', l6, True, (0.3, 0.36, 0.25), drop=(0.30, 0.55, 0.80, 1.05))] + BM + [tracers(10, 26, 1.6)],
                   slow=0.45, name='bombrun'))
    # 7. Ground level among the trolls: they charge the camera; the stick of bombs walks through them.
    run7 = [act(k, i, go(V(p.x, 3.5 + 0.7 * j), V(p.x, 0.8 + 0.7 * j), 0, 1.0), S_, [(-0.13 * j, 'run', 1.25)]) for j, (k, i, p) in enumerate(TROLLS)]
    BM7 = []
    for j in range(4): BM7 += bomb_fx(0.0 + 0.08 * j, V(LX + (j % 2) * 0.8, 6.0 - 1.6 * j, 9.0), V(LX + 0.7 * (j % 2) - 0.4, 4.2 - 1.5 * j, 0.0), 0.5, 2.0 + 0.2 * (j % 2))
    SH.append(shot(15.0, 17.4, lambda k, u: dict(pos=V(LX + 0.6, -2.8 + 0.3 * k, 0.8), tgt=V(LX - 0.2, 2.2, 1.0), fov=50, fstop=6.0, shake=0.02 + 0.04 * (0.45 < u < 0.9)),
                   run7, BM7 + [tracers(14, 27, 1.6), ('boom', 0.9, V(-1.5, -1.8, 0.3), 1.2)], slow=0.4, name='lane'))
    # 8. GIGA stands in it all and roars at the sky.
    SH.append(shot(17.4, 19.8, lambda k, u: dict(pos=V(-2.1 - 0.5 * k, 4.4, 0.18), tgt=V(LX, 6.0, 1.6 + 0.5 * ease(k)), fov=46, fstop=2.8, shake=0.01 + 0.03 * (0.5 < u < 0.9)),
                   [act('giga', 0, V(LX, 6.2), S_ + GIGA_FLIP, [(0, 'ready', 1.0), (0.4, 'attack1', 0.8)], pose=lambda u: {'Head': (-28 * ease(ramp(u, 0.1, 0.5)), 0, 0)}),
                    act('troll', 5, V(-6.0, 7.2), S_, [(0, 'idle', 1.0)]), act('troll', 6, V(-3.4, 7.6), S_, [(-0.3, 'idle', 1.0)])],
                   [aa(14, 28, 0.0, 1.6, lambda u: V(-3.0, 8.0 + 8.0 * u, 7.0)), ('boom', 0.5, V(-1.6, 9.0, 6.0), 1.0), ('boom', 1.1, V(-6.4, 8.0, 6.0), 1.2), ('burst', 0.5, V(-4.0, 8.4), 20, 1.0, 0.03)], slow=0.55, name='giga'))
    # 9. CATE's plane takes the hit: fire in the engine; she holds the stick, then pulls the lever.
    h9 = lambda u: V(-1.8, 2.0 + 3.85 * u, 5.8 - 0.4 * u * u)
    SH.append(shot(19.8, 22.8, lambda k, u: dict(pos=h9(u) + V(-5.4 + 0.6 * k, 0.9 - 0.4 * k, -0.2 + 0.3 * k), tgt=h9(u) + V(0, 0.8, -0.2), fov=44, fstop=2.6, focus=5.0, shake=0.008 + 0.03 * (0.15 < u < 0.5), roll=4 * sn(u * 3)),
                   [cockpit(*WING, h9, -0.05, 0.0, [(0, 'idle', 1.0)], pose=lambda u: {'Head': (12 * sn(u * 11) + 12, 0, 0), 'LeftArm': (-30 + 25 * sn(u * 13), 0, -62), 'RightArm': (-30 - 25 * sn(u * 12), 0, 62)})],
                   [plane_fx('right', h9, col=(0.55, 0.4, 0.2), smoke=(0.0, 0.5), fire=(0.35, 1.0)), ('boom', 0.35, h9(0.35) + V(1.4, -1.4, 0.9), 0.9), ('flash', 0.35, h9(0.35) + V(1.4, -1.4, 1.0), 6000),
                    ('burst', 0.35, V(-1.8, 3.0), 12, 1.0, 0.03), aa(10, 29, 0.0, 1.0, lambda u: h9(u))], slow=0.35, name='hit'))
    # 10. The dive: the burning plane screams at their king tower; Cate jumps at the last second; the tower goes.
    d0, d1 = V(-2.6, 0.0, 11.0), V(0.0, 11.4, 1.4); DT = 1.35; jmp = 0.8
    dv = lambda u: d0.lerp(d1, ease(clamp(u / DT))) + V(0.4 * sn(u * 4) * (1 - clamp(u / DT)), 0, 0)
    def cate_path(a):                                      # a = seconds since she jumped: a short fall, then the canopy holds her up
        b = dv(jmp); z = b.z + 1.2 * min(a, 0.55) - 3.0 * min(a, 0.55) ** 2 - 0.9 * max(0.0, a - 0.55)
        return V(b.x - 0.9 * a, b.y + 1.0 * a, z)
    CP = cate_path
    c10 = lambda u: dv(u) + V(0, 0, 0.0) if u < jmp else CP(u - jmp)
    SH.append(shot(22.8, 26.0, lambda k, u: dict(pos=V(-11.0 + 1.0 * k, -2.0, 4.5 + 1.0 * k), tgt=dv(u).lerp(V(0, 9.5, 2.0), 0.35), fov=52, fstop=8.0, focus=14.0, shake=0.012 + 0.09 * (u > DT - 0.1)),
                   [act(*WING, lambda u: (V(c10(u).x, c10(u).y) - head_dir(heading_of(dv, u)[0]) * 0.3) if u < jmp else V(c10(u).x, c10(u).y), lambda u: heading_of(dv, u)[0] if u < jmp else N, [(0, 'idle', 1.0)],
                        z=lambda u: c10(u).z - 0.45 if u < jmp else c10(u).z, rx=lambda u: FLY_RX - heading_of(dv, u)[1] if u < jmp else 0.0,
                        pose=lambda u: FLY(u) if u < jmp else ARM_UP(u))],
                   [plane_fx('right', dv, col=(0.55, 0.4, 0.2), smoke=(0.0, 0.6), fire=(0.0, 1.1), dive=(DT, d1)), ('canopy', lambda u: c10(u), 1.0, jmp + 0.55),
                    ('boom', DT, d1 + V(0, 0.6, 0.4), 3.6), ('flash', DT, d1 + V(0, -1.0, 1.0), 220000), ('ring', DT, d1 + V(0, 0, 0.3), 9.0), ('burst', DT, V(0.0, 12.0), 70, 3.2, 0.07), ('swap', DT + 0.04),
                    ('boom', DT + 0.3, T3 + V(0.9, -0.6, 2.6), 3.2), tracers(8, 30, 2.4)], slow=0.5, name='dive'))
    # 11. The parachute: Cate drifts down through the smoke; below, the burning tower.
    cp = lambda u: CP(0.8 + u)
    SH.append(shot(26.0, 29.0, lambda k, u: dict(pos=cp(u) + V(-3.6 + 0.8 * k, -4.4, -0.9 + 0.5 * k), tgt=cp(u) + V(0, 1.5, 1.4), fov=58, fstop=4.0, focus=6.0, shake=0.004),
                   [act(*WING, lambda u: V(cp(u).x, cp(u).y), N, [(0, 'idle', 0.7)], z=lambda u: cp(u).z, pose=ARM_UP)],
                   [('canopy', cp, 1.0, -9.0), ('fire', T3 + V(0, -0.8, 1.6), 2.4), ('fire', T3 + V(1.0, -0.4, 2.8), 1.8), ('fire', V(-6.0, 7.0, 0.2), 1.0)], slow=0.6, name='chute'))
    # 12. The squadron goes home over the burning tower; the line cheers; the sun is down.
    a12 = fly(V(-3.0, 15.0, 5.6), V(-3.0, -27.0, 7.4), 0.0, 4.4, 0.2); b12 = fly(V(-6.2, 17.0, 5.8), V(-6.2, -25.0, 7.6), 0.0, 4.4, 0.2, 1.0)
    SH.append(shot(29.0, 33.2, lambda k, u: dict(pos=V(-4.6 + 0.3 * k, -5.2, 0.6 + 0.9 * ease(k)), tgt=V(-3.8, 8.0, 2.4 + 1.8 * ease(k)), fov=52, fstop=6.0, focus=12.0, shake=0.004),
                   [cockpit(*ME, a12, -0.05, 0.0, [(0, 'idle', 1.0)], pose=lambda u: {'LeftArm': (-120 + 20 * sn(u * 6), 0, 20)}), cockpit(*HEAVY, b12, 0.1, 0.35, [(0, 'idle', 1.0), (1.0, 'win', 1.0)])] +
                   [act('chillguy', 0, V(-4.4, 0.4), N, [(0, 'idle', 1.0), (0.4, 'win', 1.0)]), act('wojak', 0, V(-3.0, 0.9), N, [(0, 'idle', 1.1), (0.2, 'win', 1.0)]), act('wojak', 1, V(-5.4, 1.3), N, [(0, 'idle', 1.0), (0.6, 'win', 1.0)])],
                   [plane_fx('lead', a12), plane_fx('left', b12, True, (0.3, 0.36, 0.25)), ('fire', T3 + V(0, -0.8, 1.6), 2.4), ('fire', T3 + V(1.0, -0.4, 2.8), 1.8), ('fire', V(-6.4, 5.2, 0.2), 1.0)], name='home'))
    NS = new_shots()
    for sh in SH + list(NS.values()):
        zs = CROWD.get(sh['name'])
        if zs: sh['actors'] += crowd(sum(ord(c) * (i + 3) for i, c in enumerate(sh['name'])), zs, dur=(sh['t1'] - sh['t0']) * sh['slow'] + 0.6)
    byname = {sh['name']: sh for sh in SH + list(NS.values())}; out = []; t = 0.0
    for n in ORDER:                                                       # the final running order; every shot keeps its own duration (a whole number of frames)
        sh = byname[n]; d = round(sh['t1'] - sh['t0'], 4); sh['t0'] = round(t, 4); sh['t1'] = round(t + d, 4); t += d; out.append(sh)
    return out


# ------------------------------------------------------------------ extra effects (planes, bombs, anti-aircraft fire, the parachute)
_build_fx_war = war.build_fx; _fx_mats_war = war.fx_mats


def air_mats():
    _fx_mats_war()
    m = bpy.data.materials.new('propdisc'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1); b.inputs['Alpha'].default_value = 0.16; b.inputs['Roughness'].default_value = 1.0
    sc = bpy.context.scene; wn = sc.world.node_tree; bgn = wn.nodes['Background']; nl = wn.links.new
    tc = wn.nodes.new('ShaderNodeTexCoord'); sp = wn.nodes.new('ShaderNodeSeparateXYZ'); nl(tc.outputs['Object'], sp.inputs[0])
    cr = wn.nodes.new('ShaderNodeValToRGB'); nl(sp.outputs['Z'], cr.inputs[0]); e = cr.color_ramp.elements
    e[0].position = 0.35; e[0].color = (0.07, 0.13, 0.22, 1); e[1].position = 0.95; e[1].color = (0.02, 0.02, 0.07, 1)
    mid = cr.color_ramp.elements.new(0.62); mid.color = (0.025, 0.045, 0.12, 1); nl(cr.outputs['Color'], bgn.inputs['Color'])
    vr = wn.nodes.new('ShaderNodeTexVoronoi'); vr.feature = 'F1'; vr.inputs['Scale'].default_value = 140.0; nl(tc.outputs['Object'], vr.inputs['Vector'])
    sr = wn.nodes.new('ShaderNodeValToRGB'); nl(vr.outputs['Distance'], sr.inputs[0]); se = sr.color_ramp.elements; se[0].position = 0.0; se[0].color = (9, 9, 11, 1); se[1].position = 0.05; se[1].color = (0, 0, 0, 1)
    def addmix(a_, b_):
        m_ = wn.nodes.new('ShaderNodeMix'); m_.data_type = 'RGBA'; m_.blend_type = 'ADD'; m_.inputs[0].default_value = 1.0; nl(a_, m_.inputs[6]); nl(b_, m_.inputs[7]); return m_.outputs[2]
    nm = wn.nodes.new('ShaderNodeVectorMath'); nm.operation = 'NORMALIZE'; nl(tc.outputs['Object'], nm.inputs[0])
    dt = wn.nodes.new('ShaderNodeVectorMath'); dt.operation = 'DOT_PRODUCT'; dt.inputs[1].default_value = (-0.08, 0.906, 0.41); nl(nm.outputs[0], dt.inputs[0])
    mr = wn.nodes.new('ShaderNodeValToRGB'); nl(dt.outputs['Value'], mr.inputs[0]); me_ = mr.color_ramp.elements; me_[0].position = 0.9987; me_[0].color = (0, 0, 0, 1); me_[1].position = 0.9991; me_[1].color = (0, 0, 0, 1)
    hr = wn.nodes.new('ShaderNodeValToRGB'); nl(dt.outputs['Value'], hr.inputs[0]); he_ = hr.color_ramp.elements; he_[0].position = 0.88; he_[0].color = (0, 0, 0, 1); he_[1].position = 0.9986; he_[1].color = (0.0, 0.0, 0.0, 1)
    cn = wn.nodes.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 2.2; cn.inputs['Detail'].default_value = 7; nl(tc.outputs['Object'], cn.inputs['Vector'])
    cc = wn.nodes.new('ShaderNodeValToRGB'); nl(cn.outputs['Fac'], cc.inputs[0]); ce = cc.color_ramp.elements; ce[0].position = 0.45; ce[0].color = (0, 0, 0, 1); ce[1].position = 0.72; ce[1].color = (0.05, 0.075, 0.14, 1)
    sky = addmix(addmix(addmix(cr.outputs['Color'], cc.outputs['Color']), sr.outputs['Color']), hr.outputs['Color']); nl(addmix(sky, mr.outputs['Color']), bgn.inputs['Color'])
    vo = wn.nodes.new('ShaderNodeVolumePrincipled'); vo.inputs['Density'].default_value = 0.0035; vo.inputs['Color'].default_value = (0.45, 0.65, 1.0, 1); vo.inputs['Anisotropy'].default_value = 0.35
    nl(vo.outputs['Volume'], wn.nodes['World Output'].inputs['Volume'])
    MATS['propdisc'] = m; MATS['bombmat'] = sets.flat('bomb_olive', (0.42, 0.24, 0.09), 0.5, metal=0.1); MATS['cloth'] = sets.flat('chute_cloth', (0.95, 0.55, 0.14), 0.7)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1.0); o = bpy.context.active_object
    for p in o.data.polygons: p.use_smooth = True
    MATS['bombmesh'] = o.data; bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=10, radius=1.0); o = bpy.context.active_object
    for p in o.data.polygons: p.use_smooth = True
    MATS['dome'] = o.data; bpy.data.objects.remove(o)


def build_fx_air(K, L, sh, frames, uof, rng):
    f0, f1 = frames[0], frames[-1] + 1
    mine = [e for e in sh['fx'] if e[0] in ('plane', 'bomb', 'aa', 'canopy')]
    sh2 = dict(sh); sh2['fx'] = [e for e in sh['fx'] if e not in mine]
    _build_fx_war(K, L, sh2, frames, uof, rng)
    def life(o): key3(K, o, 'scale', f0 - 1, (0, 0, 0)); key3(K, o, 'scale', f1, (0, 0, 0))
    for e in mine:
        kind = e[0]
        if kind == 'plane':
            _, key, fn, heavy, col, roll, scarf, drop, smoke, fire, dive = e; root = bpy.data.objects.new(f'{key}_{f0}', None); bpy.context.scene.collection.objects.link(root); root.rotation_mode = 'XYZ'; P = dict(root=root, blades=[], scarf=None, bombs=[]); life(root)
            ld = bpy.data.lights.new(f'plight_{key}_{f0}', 'POINT'); ld.energy = 2600; ld.color = (1.0, 0.72, 0.45); ld.shadow_soft_size = 0.8
            lo = bpy.data.objects.new(f'plight_{key}_{f0}', ld); bpy.context.scene.collection.objects.link(lo); K.add(lo, 'hide_render', 0, f0 - 1, True); K.add(lo, 'hide_render', 0, f1, True)
            ld2 = bpy.data.lights.new(f'prim_{key}_{f0}', 'POINT'); ld2.energy = 1800; ld2.color = (0.45, 0.85, 1.0); ld2.shadow_soft_size = 0.8
            lo2 = bpy.data.objects.new(f'prim_{key}_{f0}', ld2); bpy.context.scene.collection.objects.link(lo2); K.add(lo2, 'hide_render', 0, f0 - 1, True); K.add(lo2, 'hide_render', 0, f1, True)
            for f in frames:
                u = uof(f)
                pos = fn(u); h_, p_ = heading_of(fn, u)
                key3(K, lo, 'location', f, pos + V(0.0, 0.0, 0.0) + head_dir(h_).to_3d() * 2.2 + V(1.4, 0, 1.6)); K.add(lo, 'hide_render', 0, f, False)
                key3(K, lo2, 'location', f, pos - head_dir(h_).to_3d() * 1.8 + V(-1.6, 0, 1.2)); K.add(lo2, 'hide_render', 0, f, False)
                rl = (0.18 * sn(u * 1.3 + (3 if heavy else 0)) if roll is None else call(roll, u))
                if dive: rl = 0.9 * sn(u * 6) * ramp(u, 0, dive[0])
                eu = (-p_, rl, h_); gone_ = bool(dive) and u > dive[0]
                key3(K, root, 'location', f, pos); key3(K, root, 'rotation_euler', f, eu); key3(K, root, 'scale', f, (0, 0, 0) if gone_ else (1, 1, 1))
                for j, (b, x, y, z) in enumerate(P['blades']): K.add(b, 'rotation_euler', 1, f, (u * 140 + j * 1.5 + rng.uniform(0, 3)) % 6.283)
                if P['scarf'] is not None:
                    s = P['scarf']; key3(K, s, 'location', f, (0.0, 0.9 + 0.06 * sn(u * 40), 0.9)); K.add(s, 'rotation_euler', 2, f, 0.18 * sn(u * 31 + 1)); K.add(s, 'rotation_euler', 0, f, 0.1 * sn(u * 23))
                for j, b in enumerate(P['bombs']): K.add(b, 'hide_render', 0, f, bool(j < len(drop) and u >= drop[j]))
            if smoke or fire:
                us = (smoke or fire)[0]; uf = fire[0] if fire else 1e9; ue = dive[0] if dive else 1e9
                def body(u, which):
                    """Where the flames leave PNUT: the torso, the tail and the shoulder (he lies along his path with his head forward)."""
                    h_, p_ = heading_of(fn, u); n3 = head_dir(h_).to_3d(); c = fn(u)
                    return (c + n3 * (0.35 + (0.35 if which == 2 else 0.0)) + V(0, 0, -0.1)) if which != 1 else (c - n3 * 0.45 + V(0, 0, 0.35))
                NF, NS, NE = 34, 22, 26
                fl = [obj('ball', 'fire') for _ in range(NF)]; sm = [obj('ball', 'smoke') for _ in range(NS)]; em = [obj('ball', 'fire') for _ in range(NE)]
                for o in fl + sm + em: life(o)
                lt = bpy.data.objects.new(f'pfire_light_{key}_{f0}', bpy.data.lights.new(f'pfl_{key}_{f0}', 'POINT')); bpy.context.scene.collection.objects.link(lt); lt.data.color = (1.0, 0.5, 0.16); lt.data.shadow_soft_size = 0.5; lt.data.energy = 0.0
                K.add(lt.data, 'energy', 0, f0 - 1, 0.0); K.add(lt.data, 'energy', 0, f1, 0.0)
                pr = random.Random(hash(key) % 1000 if False else sum(map(ord, key)) + 5)
                par = [(pr.uniform(0, 1), pr.randrange(3), V(pr.uniform(-0.25, 0.25), pr.uniform(-0.2, 0.2), pr.uniform(0.0, 0.2)), pr.uniform(0.7, 1.3)) for _ in range(NF + NS + NE)]
                for f in frames:
                    u = uof(f); on = ue > u and u > us
                    big = 0.0 if not on else min(1.0, (u - us) / 0.35)
                    if on and u > uf: big = 1.0 + min(1.0, (u - uf) / 0.5)
                    c0 = fn(u)
                    for j, o in enumerate(fl):                                                   # flame tongues: born on the body, left behind on the path, lick upward
                        off, wh, jit, sz = par[j]; life_ = 0.42; a = ((u / life_) + off) % 1.0; tb = u - a * life_
                        if not on or tb < max(us, uf) - 0.05 or big < 0.01: key3(K, o, 'scale', f, (0, 0, 0)); continue
                        p = body(tb, wh) + jit + V(0, 0, 0.9 * a * a * big) - head_dir(heading_of(fn, u)[0]).to_3d() * 0.0
                        s_ = sz * (0.5 + 0.45 * big) * (1.0 - a) ** 0.55 * (0.8 + 0.2 * sn(u * 31 + j * 2.1)) * 0.5
                        key3(K, o, 'location', f, p); key3(K, o, 'scale', f, (s_ * 0.8, s_ * 0.8, s_ * 2.6)); key3(K, o, 'color', f, (1.0, 0.34 - 0.2 * a, 0.03, 0.95 * (1.0 - a) ** 0.8))
                    for j, o in enumerate(sm):                                                  # black smoke, thick, rising and drifting back
                        off, wh, jit, sz = par[NF + j]; life_ = 1.5; a = ((u / life_) + off) % 1.0; tb = u - a * life_
                        if not on or tb < us or big < 0.01: key3(K, o, 'scale', f, (0, 0, 0)); continue
                        p = body(tb, wh) + jit * 2 + V(0.25 * sn(j), 0.0, 1.2 * a * big + 0.2)
                        s_ = (0.2 + 0.8 * a) * sz * (0.55 + 0.5 * big)
                        key3(K, o, 'location', f, p); key3(K, o, 'scale', f, (s_, s_, s_)); key3(K, o, 'color', f, (0.045, 0.04, 0.05, 0.55 * sn(PI * a) + 0.05))
                    for j, o in enumerate(em):                                                  # sparks thrown off, falling in a curve
                        off, wh, jit, sz = par[NF + NS + j]; life_ = 0.9; a = ((u / life_) + off) % 1.0; tb = u - a * life_; t_ = a * life_
                        if not on or tb < uf or big < 0.01 or not fire: key3(K, o, 'scale', f, (0, 0, 0)); continue
                        v = V(pr.uniform(-1, 1) * 0.0 + sn(j * 7.3) * 1.3, sn(j * 3.1) * 1.3, 1.1 + 0.8 * sn(j * 5.7)); p = body(tb, wh) + v * t_ + V(0, 0, -2.2 * t_ * t_)
                        key3(K, o, 'location', f, p); key3(K, o, 'scale', f, [0.035 + 0.02 * sz] * 3); key3(K, o, 'color', f, (1.0, 0.7, 0.25, 2.0 * (1.0 - a)))
                    lt.location = body(u, 0); lt.keyframe_insert('location', frame=f); K.add(lt.data, 'energy', 0, f, 0.0 if not on else (900 + 500 * sn(u * 23)) * (0.3 + 0.7 * min(1.0, big)))
        elif kind == 'bomb':
            _, u0, src, dst, fall = e; o = obj('bombmesh', 'bombmat', shadow=True); life(o)
            for f in frames:
                a = (uof(f) - u0) / fall
                if 0 <= a < 1: key3(K, o, 'location', f, V(lerp(src.x, dst.x, a), lerp(src.y, dst.y, a), lerp(src.z, dst.z, a * a))); key3(K, o, 'scale', f, (0.11, 0.11, 0.32)); K.add(o, 'rotation_euler', 0, f, 0.35 * (1 - a))
                else: key3(K, o, 'scale', f, (0, 0, 0))
        elif kind == 'aa':
            _, n, seed, u0, dur, aim, bx, y0 = e; r2 = random.Random(seed)
            for j in range(n):
                o = obj('rod', 'tr_theirs'); life(o); us = u0 + r2.uniform(0, dur); x0 = r2.uniform(*bx); yy = y0 + r2.uniform(-1.5, 3.0); tt = r2.uniform(0.5, 0.9); sp = tt
                tgt = Vector(aim(us + tt)) + V(r2.uniform(-1.2, 1.2), r2.uniform(-1.2, 1.2), r2.uniform(-0.6, 0.8)); src = V(x0, yy, 0.2); d = (tgt - src).normalized(); o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
                for f in frames:
                    a = (uof(f) - us) / tt
                    if 0 <= a < 1.15: key3(K, o, 'location', f, src.lerp(tgt, min(1.0, a) + max(0.0, a - 1.0) * 0.6)); key3(K, o, 'scale', f, (1, 1, 2.6))
                    else: key3(K, o, 'scale', f, (0, 0, 0))
        elif kind == 'canopy':
            _, fn, size, uo = e; dome = obj('dome', 'cloth'); life(dome); lines = [obj('rod', 'tr_ours') for _ in range(6)]
            for o in lines: life(o)
            for f in frames:
                u = uof(f); op = ease(ramp(u, uo, uo + 0.3)); c = fn(u) + V(0, 0, 0.6 + 1.9 * op); key3(K, dome, 'location', f, c); key3(K, dome, 'scale', f, (1.5 * size * op, 1.5 * size * op, 0.8 * size * op))
                for j, o in enumerate(lines):
                    a = j * PI / 3; top = c + V(math.cos(a) * 1.45 * size, sn(a) * 1.45 * size, -0.12); bot = fn(u) + V(0, 0, 1.15); mid = (top + bot) / 2; d = top - bot
                    key3(K, o, 'location', f, mid); o.rotation_euler = d.normalized().to_track_quat('Z', 'Y').to_euler(); key3(K, o, 'scale', f, (0.4, 0.4, d.length) if op > 0.5 else (0, 0, 0))


sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import env as _env
war.SUNK = (2.6, (0.55, 0.68, 1.0), 66, 185)       # the moon, behind the enemy lines and a little to the left
war.FILLK = (700, (0.35, 0.5, 0.95))
war.HAZEK = (0.02, 0.05, 0.1, 1)                  # the aerial haze: deep night blue, not a grey wash
_arena_war = war.arena_dump


def arena_night():
    A = _arena_war()
    bd = bpy.data.objects['backdrop']; bd.scale = (1.6, 1.6, 1.0)                              # the game's painted horizon, pushed far back and dimmed: a distant layer, not the whole set
    for n in bd.data.materials[0].node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED': n.inputs['Emission Strength'].default_value = 0.55
    _env.build_env(A); return A


war.arena_dump = arena_night
_finish_war = war.UD.finish


def finish_night(sc):
    _finish_war(sc)
    for n in sc.node_tree.nodes:
        if n.type == 'COLORBALANCE': n.lift = (0.98, 1.0, 1.05); n.gain = (0.97, 1.0, 1.05)


war.UD.finish = finish_night
war.build_fx = build_fx_air; war.fx_mats = air_mats; war.film = film


if __name__ == '__main__':
    war.main()
