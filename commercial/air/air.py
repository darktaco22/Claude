"""DAWN PATROL (a Meme Royale war short, the air-raid sequel to LAST LINE): the game's own characters fly bombers over the same battlefield.
blender -b -P air.py -- --out scene.blend [--res 1080]      Env: GAME (the game's assets), W (work folder: timeline.json).
It reuses LAST LINE's engine (war.py: shots, units, arena, fire/smoke/blast effects) and adds aircraft (built from primitives, with the game's
characters in the cockpits), falling bombs, anti-aircraft fire, a burning plane and a parachute."""
import bpy, sys, os, math, json, random
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'war'))
import war
from war import *                                    # V, ramp, ease, lerp, act, go, thrown, shot, tracers, poses, WUnit, MATS, obj, key3, K helpers ...
from mathutils import Vector, Euler

game.H.update(pepe=1.3, chillguy=1.45, troll=1.4, wojak=1.4)
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
ME = ('pepe', 0); WING = ('cate', 0); HEAVY = ('bonk', 0)
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


def cockpit(kind, i, fn, dy=0.0, dz=-0.2, clips=(), pose=None, rx=0.0, roll=None):
    """A character sitting in a plane's cockpit: dy along the nose axis toward the tail, dz relative to the fuselage axis."""
    def pos(u):
        h, _ = heading_of(fn, u); c = fn(u); n = head_dir(h); return V(c.x, c.y) - n * dy
    def z(u): return fn(u).z + dz
    def hh(u): return heading_of(fn, u)[0]
    def pr(u): return rx + heading_of(fn, u)[1] * -1.0 * 0.9
    a = act(kind, i, pos, hh, clips, z=z, rx=lambda u: -heading_of(fn, u)[1] + rx, pose=pose)
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
                   [tracers(14, 22, 1.8), ('boom', 0.9, V(-7.6, -6.5, 0.4), 1.2)], name='looks_up', sub=(0.7, 1.7, 'AIR SUPPORT.')))
    # 3. The flyover: three planes pass over the line, low, toward the enemy. The line cheers.
    lead = fly(V(-3.0, -24.0, 5.2), V(-3.0, 6.0, 5.8), 0.0, 2.4, 0.15); lft = fly(V(-6.6, -27.0, 5.6), V(-6.6, 3.0, 6.1), 0.0, 2.4, 0.2, 1.0); rgt = fly(V(0.6, -26.0, 5.4), V(0.6, 4.0, 5.9), 0.0, 2.4, 0.2, 2.0)
    SH.append(shot(5.0, 7.6, lambda k, u: dict(pos=V(-4.0, -3.6, 0.3), tgt=V(-3.4, -9.0 + 5.0 * ease(k), 2.2 + 3.6 * ease(k)), fov=72, fstop=5.6, shake=0.012, roll=-3 + 6 * k),
                   [cockpit(*ME, lead, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*WING, rgt, -0.05, 0.0, [(0, 'idle', 1.0)]), cockpit(*HEAVY, lft, 0.1, 0.35, [(0, 'attack1', 0.6)])] +
                   [act(k, i, p, N, [(-0.2 * j, 'idle', 1.0), (0.9 + 0.08 * j, 'win', 1.0)], pose=lambda u, j=j: cheer(j)(u) if u > 1.0 + 0.08 * j else crouch(10, j)(u)) for j, (k, i, p) in enumerate(OUR)],
                   [plane_fx('lead', lead), plane_fx('right', rgt, col=(0.55, 0.4, 0.2)), plane_fx('left', lft, True, (0.3, 0.36, 0.25)), tracers(10, 23, 2.4), ('boom', 1.2, V(-7.0, 5.0, 0.4), 1.4)],
                   slow=0.8, name='flyover'))
    # 4. The cockpit: the lead plane's pilot, scarf streaming.
    lead2 = fly(V(-3.0, -6.0, 5.4), V(-3.0, 26.0, 5.4), 0.0, 2.6, 0.12)
    SH.append(shot(7.6, 9.8, lambda k, u: dict(pos=lead2(u) + V(-2.8 + 0.5 * k, 3.2 - 0.3 * k, 2.2 + 0.2 * k), tgt=lead2(u) + V(0, -0.05, 1.15), fov=26, fstop=2.0, focus=4.4, shake=0.007, roll=3 - 5 * k),
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
    SH.append(shot(19.8, 22.8, lambda k, u: dict(pos=h9(u) + V(-2.8 + 0.5 * k, 3.2 - 0.3 * k, 2.2 + 0.2 * k), tgt=h9(u) + V(0, -0.05, 0.95), fov=28, fstop=2.2, focus=4.4, shake=0.012 + 0.07 * (0.15 < u < 0.5), roll=6 * sn(u * 3)),
                   [cockpit(*WING, h9, -0.05, 0.0, [(0, 'idle', 1.0), (0.45, 'hit', 0.8), (1.1, 'idle', 1.0)], pose=lambda u: {'Head': (16 * sn(u * 11), 0, 0)})],
                   [plane_fx('right', h9, col=(0.55, 0.4, 0.2), smoke=(0.0, 0.5), fire=(0.35, 1.0)), ('boom', 0.35, h9(0.35) + V(0.0, 1.5, 0.3), 1.2), ('flash', 0.35, h9(0.35) + V(0, 1.6, 0.6), 9000),
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
                   [act(*WING, lambda u: V(c10(u).x, c10(u).y), lambda u: heading_of(dv, u)[0] if u < jmp else N, [(0, 'idle', 1.0)], z=lambda u: c10(u).z, rx=lambda u: -heading_of(dv, u)[1] if u < jmp else 0.0,
                        pose=lambda u: {} if u < jmp else ARM_UP(u))],
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
    return SH


# ------------------------------------------------------------------ extra effects (planes, bombs, anti-aircraft fire, the parachute)
_build_fx_war = war.build_fx; _fx_mats_war = war.fx_mats


def air_mats():
    _fx_mats_war()
    m = bpy.data.materials.new('propdisc'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1); b.inputs['Alpha'].default_value = 0.16; b.inputs['Roughness'].default_value = 1.0
    sc = bpy.context.scene; wn = sc.world.node_tree; bgn = wn.nodes['Background']; nl = wn.links.new
    tc = wn.nodes.new('ShaderNodeTexCoord'); sp = wn.nodes.new('ShaderNodeSeparateXYZ'); nl(tc.outputs['Object'], sp.inputs[0])
    cr = wn.nodes.new('ShaderNodeValToRGB'); nl(sp.outputs['Z'], cr.inputs[0]); e = cr.color_ramp.elements
    e[0].position = 0.35; e[0].color = (0.50, 0.24, 0.26, 1); e[1].position = 0.95; e[1].color = (0.045, 0.03, 0.11, 1)
    mid = cr.color_ramp.elements.new(0.62); mid.color = (0.34, 0.15, 0.24, 1); nl(cr.outputs['Color'], bgn.inputs['Color'])
    MATS['propdisc'] = m; MATS['bombmat'] = sets.flat('bomb_olive', (0.16, 0.18, 0.1), 0.45, metal=0.4); MATS['cloth'] = sets.flat('chute_cloth', (0.95, 0.55, 0.14), 0.7)
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
            _, key, fn, heavy, col, roll, scarf, drop, smoke, fire, dive = e; P = build_plane(f'{key}_{f0}', heavy, col); root = P['root']; life(root)
            for f in frames:
                u = uof(f)
                pos = fn(u); h_, p_ = heading_of(fn, u)
                rl = (0.18 * sn(u * 1.3 + (3 if heavy else 0)) if roll is None else call(roll, u))
                if dive: rl = 0.9 * sn(u * 6) * ramp(u, 0, dive[0])
                eu = (-p_, rl, h_); gone_ = bool(dive) and u > dive[0]
                key3(K, root, 'location', f, pos); key3(K, root, 'rotation_euler', f, eu); key3(K, root, 'scale', f, (0, 0, 0) if gone_ else (1, 1, 1))
                for j, (b, x, y, z) in enumerate(P['blades']): K.add(b, 'rotation_euler', 1, f, (u * 140 + j * 1.5 + rng.uniform(0, 3)) % 6.283)
                if P['scarf'] is not None:
                    s = P['scarf']; key3(K, s, 'location', f, (0.0, 0.9 + 0.06 * sn(u * 40), 0.9)); K.add(s, 'rotation_euler', 2, f, 0.18 * sn(u * 31 + 1)); K.add(s, 'rotation_euler', 0, f, 0.1 * sn(u * 23))
                for j, b in enumerate(P['bombs']): K.add(b, 'hide_render', 0, f, bool(j < len(drop) and u >= drop[j]))
            if smoke or fire:
                us, ue = (smoke or fire)[0], 99.0; trail = [obj('ball', 'smoke') for _ in range(18)]; head = [obj('ball', 'fire') for _ in range(4)]
                for o in trail + head: life(o)
                for f in frames:
                    u = uof(f)
                    for j, o in enumerate(trail):
                        uj = u - 0.06 * (j + 1)
                        if smoke and uj > us:
                            key3(K, o, 'location', f, fn(uj) + V(0.0, 0.0, 0.05 * j) + V(rng.uniform(-0.04, 0.04), 0, 0)); key3(K, o, 'scale', f, [0.18 + 0.075 * j] * 3); key3(K, o, 'color', f, (0.06, 0.055, 0.06, max(0.0, 1.0 - 0.04 * j)))
                        else: key3(K, o, 'scale', f, (0, 0, 0))
                    for j, o in enumerate(head):
                        if fire and u > fire[0]:
                            key3(K, o, 'location', f, fn(u) + head_dir(heading_of(fn, u)[0]).to_3d() * (1.7 - 0.5 * j) + V(0.0, 0.0, 0.15 + 0.2 * sn(u * 20 + j))); key3(K, o, 'scale', f, [(0.42 - 0.07 * j) * (0.8 + 0.2 * sn(u * 25 + j))] * 3); key3(K, o, 'color', f, (1.0, 0.4, 0.1, 1.1))
                        else: key3(K, o, 'scale', f, (0, 0, 0))
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


war.build_fx = build_fx_air; war.fx_mats = air_mats; war.film = film


if __name__ == '__main__':
    war.main()
