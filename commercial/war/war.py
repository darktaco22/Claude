"""LAST LINE (a Meme Royale war short): a battle in the game's own arena with the game's own characters.
blender -b -P war.py -- --out scene.blend [--res 1080]      Env: GAME (the game's assets), W (work folder: timeline.json).
The film is a list of SHOTS. Each shot stages its own actors (game units: the game's clips, time-warped for slow motion,
plus custom bone animation on the game's rigs), its camera and its effects, in shot-local world time u (seconds)."""
import bpy, sys, os, math, json, random
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, '..', 'useless'), os.path.join(H, '..', 'degens'), os.path.join(H, '..', 'whale')]
from mathutils import Vector, Euler, Quaternion
import rigctl, game, sets
import director as UD                      # NO UTILITY's render setup, compositor and camera
from sets import OURS, THEIRS

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return ARGS[ARGS.index(k) + 1] if k in ARGS else d
FPS = 30; PI = math.pi
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, k: a + (b - a) * k
def ramp(t, a, b): return clamp((t - a) / (b - a))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
def F(t): return int(round(t * FPS)) + 1
def V(*a): return Vector(a)
def hd(d): return math.atan2(d.x, -d.y)            # heading that faces direction d
def call(v, u): return v(u) if callable(v) else v
sn = math.sin
N, S_ = PI, 0.0                                     # headings: north (the enemy), south
LOOP = {'run', 'walk', 'idle', 'ready'}
LX = -5.0                                           # the lane: the left bridge


# ------------------------------------------------------------------ custom animation (degrees, on the game's rigs)
def flail(seed):
    def f(u):
        a = lambda w, p=0.0: sn(u * w + seed * 1.7 + p)
        return {'LeftArm': (40 * a(9), 0, 50 * a(7, 1)), 'RightArm': (40 * a(8, 2), 0, -50 * a(6.5, 3)), 'LeftUpLeg': (20 + 45 * a(7.5), 0, 10),
                'RightUpLeg': (20 + 45 * a(7.5, 3), 0, -10), 'LeftLeg': (-45 - 30 * a(9, 1), 0, 0), 'RightLeg': (-45 - 30 * a(8, 2), 0, 0),
                'Spine': (15 * a(5), 0, 0), 'Head': (12 * a(6, 1), 0, 0)}
    return f


def limp(seed):                                     # lying still where it fell
    def f(u): return {'LeftArm': (20 + 10 * sn(seed), 0, 20), 'RightArm': (35, 0, -15 * sn(seed * 2)), 'LeftUpLeg': (12, 0, 14), 'RightUpLeg': (-6, 0, -9),
                      'LeftLeg': (-25, 0, 0), 'RightLeg': (-8, 0, 0), 'Head': (14, 0, 0)}
    return f


def then(u0, a, b, blend=0.12):                     # pose a until u0, then b
    def f(u):
        k = ease(ramp(u, u0, u0 + blend)); pa, pb = a(u), b(u); out = {}
        for bn in set(pa) | set(pb):
            x, y = pa.get(bn, (0, 0, 0)), pb.get(bn, (0, 0, 0)); out[bn] = tuple(lerp(x[i], y[i], k) for i in range(3))
        return out
    return f


def prone(u, tremble=2.0, reach=1.0, push=0.0):
    """Face down in the snow, arms out ahead (reach), or planted to push up (push)."""
    tr = tremble * (sn(u * 57) + 0.6 * sn(u * 83 + 1)); ax = lerp(-72, -20, push) * reach + 60 * (1 - reach)
    return {'LeftArm': (ax + tr, 0, -26 * (1 - push) + 30 * push), 'RightArm': (ax - tr, 0, 26 * (1 - push) - 30 * push), 'LeftForeArm': (0, 0, 40 * push), 'RightForeArm': (0, 0, -40 * push),
            'LeftUpLeg': (4, 0, 8), 'RightUpLeg': (-3, 0, -8), 'LeftLeg': (-10, 0, 0), 'Head': (-18 + tr, 0, 0)}


def crawl(u_stop):
    def f(u):
        k = 1 - ease(ramp(u, u_stop, u_stop + 0.25)); w = sn(u * 9) * k
        return {'LeftArm': (lerp(40, -70 - 22 * w, k), 0, 20), 'RightArm': (lerp(55, -88 + 22 * w, k), 0, -12), 'LeftUpLeg': (10 + 22 * w, 0, 10),
                'RightUpLeg': (10 - 22 * w, 0, -10), 'LeftLeg': (-30 - 20 * w, 0, 0), 'RightLeg': (-30 + 20 * w, 0, 0), 'Head': (lerp(20, -25, k), 0, 0)}
    return f


def crouch(deg, seed=0.0):
    def f(u): b = deg / 3 + 1.2 * sn(u * 3 + seed); return {'Spine': (b, 0, 0), 'Spine1': (b, 0, 0), 'Spine2': (b, 0, 0), 'Head': (-deg * 0.5, 0, 0)}
    return f


def arm_up(u0, u1, side='Right', deg=-78):          # an arm thrown up over the clip (the order to charge)
    def f(u): k = ease(ramp(u, u0, u0 + 0.25)) * (1 - ease(ramp(u, u1, u1 + 0.3))); return {side + 'Arm': (deg * k, 0, 0), 'Spine': (-8 * k, 0, 0)}
    return f


def leap(u_hit):
    """In the air: knees tucked, right fist cocked back over the head, then driven down at u_hit."""
    def f(u):
        s = ease(ramp(u, u_hit - 0.09, u_hit)); w = ease(ramp(u, 0.0, 0.25))
        return {'RightArm': (lerp(-95 * w, 25, s), 0, lerp(35 * w, -45, s)), 'LeftArm': (lerp(-10 * w, 40, s), 0, 45 * w), 'Spine': (lerp(-16 * w, 30, s), 0, 0),
                'Spine1': (lerp(-10 * w, 14, s), 0, 0), 'LeftUpLeg': (62 * w, 0, 6), 'RightUpLeg': (lerp(24 * w, -18, s), 0, -6), 'LeftLeg': (-80 * w, 0, 0),
                'RightLeg': (lerp(-55 * w, -18, s), 0, 0), 'Head': (lerp(-10, 14, s), 0, 0)}
    return f


# ------------------------------------------------------------------ actors
def act(kind, i, pos, h=N, clips=(), z=0.0, rx=0.0, pose=None):
    return dict(kind=kind, i=i, pos=pos, h=h, clips=list(clips), z=z, rx=rx, pose=pose)


def go(p0, p1, u0=0.0, u1=1.0):
    return lambda u: p0.lerp(p1, ramp(u, u0, u1))


def thrown(kind, i, p0, p1, u0, dur=0.75, hgt=1.5, spins=1.0, pre='run', seed=1.0, h=N, pre_from=None):
    """Runs/stands until u0, then is thrown p0 -> p1 on an arc, tumbling, and lies where it lands."""
    k = lambda u: ramp(u, u0, u0 + dur)
    pos = lambda u: (pre_from.lerp(p0, ramp(u, 0, u0)) if pre_from and u < u0 else p0.lerp(p1, k(u)))
    return act(kind, i, pos, h, [(-seed, pre, 1.2), (u0, 'hit', 1.0)], z=lambda u: hgt * sn(PI * k(u)) + 0.05 * (k(u) >= 1),
               rx=lambda u: -math.radians(90 + 360 * spins) * k(u), pose=then(u0 + dur, then(u0, lambda u: {}, flail(seed), 0.05), limp(seed)))


def shot(t0, t1, cam, actors=(), fx=(), slow=1.0, pov=0.0, clock=None, name=''):
    return dict(t0=t0, t1=t1, cam=cam, actors=list(actors), fx=list(fx), slow=slow, pov=pov, clock=clock, name=name)


def tracers(n, seed, dur): return ('tracers', n, seed, dur)


# ------------------------------------------------------------------ the film
Q = V(-3.8, -7.6)                                   # where our soldier lies after the blast
B = V(-4.6, -4.6)                                   # where the blast lands
LINE = [('useless', 1, V(-5.2, -5.6)), ('useless', 2, V(-3.6, -5.9)), ('bonk', 0, V(-4.5, -5.2)), ('cate', 0, V(-5.9, -5.0)), ('walter', 0, V(-3.2, -5.0)),
        ('useless', 3, V(-6.3, -6.2)), ('bonk', 1, V(-2.7, -6.1)), ('cate', 1, V(-5.4, -4.3)), ('walter', 1, V(-3.9, -4.2))]
GIGA0 = V(-4.6, -3.6)
EN = [('goat', 0, V(LX, 3.0)), ('goat', 1, V(-5.6, 4.2)), ('goat', 2, V(-4.4, 4.4)), ('whale', 0, V(LX, 5.8)), ('goat', 3, V(-5.7, 7.0)), ('goat', 4, V(-4.3, 7.2)), ('whale', 1, V(LX, 8.6))]
BOSS = V(LX, 4.3)
TOWER = sets.ENEMY_KING.to_2d()


def pov_cam(P, yaw=0.0, roll=6.0, look_up=0.0, sway=1.0):
    """First person, lying in the snow at P facing north: its own gloves in the frame, everything soft and tilted."""
    def cam(k, u):
        y = math.radians(yaw + 6 * sn(u * 1.3) * sway); d = V(sn(y), math.cos(y), 0)
        c = P.to_3d() + V(0, 0.5, 0.3 + 0.03 * sn(u * 2.1))
        return dict(pos=c, tgt=c + d * 5 + V(0, 0, -0.35 + look_up + 0.3 * sn(u * 1.7) * sway), fov=64, fstop=1.0, focus=3.2 + 1.6 * sn(u * 2.3), roll=roll + 5 * sn(u * 1.1), shake=0.012, near=0.12)
    return cam


def me_prone(P, push=0.0):
    return act('useless', 0, P, N, [], rx=math.radians(86), pose=lambda u: prone(u, 2.5, 1.0, call(push, u)))


def film():
    SH = []
    # 1. First person. Behind the line, face down in the snow; the others wait for the order.
    line = [act(k, i, p, N, [(-0.4 * j, 'ready' if j % 2 else 'idle', 1.0)], pose=crouch(26, j)) for j, (k, i, p) in enumerate(LINE)]
    SH.append(shot(0.0, 3.6, pov_cam(V(-3.9, -8.7), 0, 4), [me_prone(V(-3.9, -8.7))] + line + [act('giga', 0, GIGA0, N, [(0, 'idle', 1.0)])],
                   [tracers(26, 1, 2.2), ('boom', 0.5, V(-2.0, 5.0, 0.4), 1.3), ('boom', 1.5, V(-7.0, 4.4, 0.4), 1.6)], slow=0.6, pov=0.7, name='pov_wait'))
    # 2. GIGA gives the order.
    SH.append(shot(3.6, 5.6, lambda k, u: dict(pos=V(-4.1 - 0.15 * k, -1.7 - 0.4 * k, 0.32), tgt=GIGA0.to_3d() + V(0, 0, 1.2), fov=36, fstop=2.8, shake=0.006),
                   [act('giga', 0, GIGA0, N, [(0, 'emote', 1.15)], pose=arm_up(0.55, 1.7))] +
                   [act(k, i, p, N, [(-0.3 * j, 'ready', 1.2)], pose=crouch(14, j)) for j, (k, i, p) in enumerate(LINE)],
                   [tracers(14, 2, 2.0), ('boom', 0.9, V(-7.6, -6.5, 0.4), 1.2)], name='order'))
    # 3. Over the top.
    run = [act(k, i, go(p, p + V((LX - p.x) * 0.35, 5.6), 0.15 + 0.05 * (j % 4), 3.6), N, [(-0.2 * j, 'ready', 1.0), (0.12 + 0.05 * (j % 4), 'run', 1.3)])
           for j, (k, i, p) in enumerate(LINE + [('useless', 0, V(-4.3, -7.2)), ('useless', 4, V(-6.6, -7.4)), ('useless', 5, V(-2.9, -7.3)), ('bonk', 2, V(-5.3, -7.6)),
                                                  ('cate', 2, V(-3.7, -7.8)), ('walter', 2, V(-6.0, -8.2))])]
    run.append(act('giga', 0, go(GIGA0, GIGA0 + V(-0.3, 5.4), 0.05, 3.6), N, [(0, 'run', 1.25)]))
    SH.append(shot(5.6, 9.0, lambda k, u: dict(pos=V(1.5, -6.9 + 4.7 * k, 0.42), tgt=V(LX, -5.2 + 4.9 * k, 0.8), fov=50, fstop=4.0, shake=0.03),
                   run, [tracers(34, 3, 3.4), ('boom', 0.9, V(-6.9, -3.6, 0.3), 1.2), ('boom', 2.3, V(-3.1, -1.9, 0.3), 1.5), ('burst', 0.6, V(-4.6, -4.4), 20, 0.7, 0.03),
                         ('burst', 1.4, V(-5.2, -3.2), 20, 0.7, 0.03), ('burst', 2.2, V(-4.4, -2.0), 20, 0.7, 0.03), ('burst', 2.9, V(-5.4, -1.0), 20, 0.7, 0.03)], clock='0:30', name='charge'))
    # 4. They come over the bridge.
    SH.append(shot(9.0, 11.4, lambda k, u: dict(pos=V(LX + 0.25, -4.4 + 0.3 * k, 0.26), tgt=V(LX, 0.6, 1.05), fov=27, fstop=4.0, shake=0.02),
                   [act(k, i, go(p, p + V(0, -4.6), 0, 2.4), S_, [(-0.13 * j, 'run', 1.2)]) for j, (k, i, p) in enumerate(EN)],
                   [tracers(18, 4, 2.4), ('boom', 1.1, V(-3.3, 5.6, 0.4), 1.5)], clock='0:27', name='enemy'))
    # 5. The lines meet. Slow motion.
    SH.append(shot(11.4, 15.0, lambda k, u: dict(pos=V(-0.7 - 0.35 * k, -3.3 + 0.2 * k, 0.3), tgt=V(LX, -2.75, 0.95), fov=33, fstop=2.8, shake=0.012 + 0.05 * (0.44 < u < 0.6)),
                   [act('giga', 0, go(V(LX, -3.9), V(LX, -3.25), 0, 0.3), N, [(-0.3, 'run', 1.2), (0.12, 'attack1', 1.0)]),
                    act('goat', 0, go(V(LX, -1.5), V(LX, -2.2), 0, 0.3), S_, [(-0.2, 'run', 1.2), (0.2, 'attack1', 1.0), (0.5, 'hit', 0.8)]),
                    act('useless', 1, lambda u: V(-6.3, -3.9).lerp(V(-6.0, -2.7), ramp(u, 0, 0.5)).lerp(V(-7.1, -4.8), ramp(u, 0.56, 1.0)), N, [(-0.2, 'run', 1.3)],
                        z=lambda u: 0.85 * sn(PI * ramp(u, 0.1, 0.5)) * (u < 0.56) + 0.9 * sn(PI * ramp(u, 0.56, 1.0)) * (u >= 0.56),
                        rx=lambda u: -math.radians(250) * ramp(u, 0.56, 1.0), pose=then(0.56, leap(0.5), flail(3), 0.05)),
                    act('goat', 1, V(-6.0, -2.0), S_, [(-0.1, 'ready', 1.0), (0.3, 'attack2', 1.0)]),
                    act('bonk', 0, go(V(-3.9, -4.1), V(-3.9, -3.3), 0, 0.35), N, [(-0.1, 'run', 1.2), (0.2, 'attack1', 1.0)]),
                    act('goat', 2, V(-4.0, -2.3), S_, [(0, 'ready', 1.0), (0.52, 'hit', 0.8)]),
                    act('whale', 0, go(V(LX, 0.9), V(LX, -0.4), 0, 1.1), S_, [(0, 'run', 1.1)]),
                    act('cate', 0, go(V(-5.6, -6.0), V(-5.5, -4.4), 0, 1.1), N, [(0, 'run', 1.3)]), act('walter', 0, go(V(-3.3, -6.3), V(-3.5, -4.7), 0, 1.1), N, [(-0.1, 'run', 1.3)]),
                    act('useless', 2, go(V(-4.5, -6.6), V(-4.6, -5.0), 0, 1.1), N, [(-0.2, 'run', 1.3)])],
                   [('flash', 0.46, V(LX, -2.75, 1.1), 9000), ('burst', 0.46, V(LX, -2.75), 40, 1.6, 0.04), ('ring', 0.46, V(LX, -2.75, 0.9), 1.6),
                    ('burst', 0.58, V(-6.0, -2.6), 24, 1.2, 0.035), ('burst', 0.54, V(-4.0, -2.8), 24, 1.2, 0.035), tracers(22, 5, 1.2)], slow=0.3, clock='0:22', name='clash'))
    # 6. The blast.
    ring = [('useless', 2, 0.3), ('useless', 3, 1.4), ('cate', 1, 2.5), ('bonk', 1, 3.6), ('walter', 1, 4.9)]
    blown = [thrown(k, i, B + V(sn(a), math.cos(a)) * 0.9, B + V(sn(a), math.cos(a)) * 3.0, 0.12, 0.62, 1.7 + 0.3 * sn(a * 3), 1.0 + 0.3 * j, seed=j + 1,
                    pre_from=B + V(sn(a), math.cos(a)) * 0.9 + V(0, -0.5)) for j, (k, i, a) in enumerate(ring)]
    blown.append(thrown('useless', 0, V(-4.2, -5.6), Q + V(0, 0.2), 0.12, 0.66, 1.3, 0.75, seed=9, pre_from=V(-4.2, -6.1)))
    SH.append(shot(15.0, 17.4, lambda k, u: dict(pos=V(-0.9, -9.6, 3.3 - 0.4 * k), tgt=B.to_3d() + V(0, 0, 0.7), fov=42, fstop=4.0, shake=0.01 + 0.09 * (0.1 < u < 0.4)),
                   blown + [act('giga', 0, V(LX, -3.2), N, [(0, 'attack2', 0.9)]), act('goat', 0, V(LX, -2.2), S_, [(0, 'attack1', 0.9)]),
                            act('goat', 1, V(-6.0, -2.4), S_, [(0, 'run', 1.0)]), act('bonk', 0, V(-3.9, -3.3), N, [(0, 'attack2', 0.9)]), act('goat', 2, V(-4.0, -2.3), S_, [(0, 'attack2', 0.9)])],
                   [('boom', 0.12, B.to_3d() + V(0, 0, 0.5), 2.6), ('ring', 0.12, B.to_3d() + V(0, 0, 0.15), 4.5), ('burst', 0.12, B, 60, 2.6, 0.05), ('flash', 0.12, B.to_3d() + V(0, 0, 1.0), 30000),
                    tracers(16, 6, 0.9)], slow=0.35, clock='0:19', name='blast'))
    # 7. First person again: deaf, the world tilted and soft. Left, right, ahead: they are going down.
    fires = [('boom', -0.4, V(-6.6, -3.8, 0.3), 1.1), ('boom', 0.3, V(-1.6, -2.2, 0.3), 1.4)]
    SH.append(shot(17.4, 19.6, pov_cam(Q, -28, 15), [me_prone(Q),
                   act('cate', 2, V(-5.5, -5.5), N, [(0, 'ready', 1.0), (0.3, 'hit', 0.7), (0.5, 'die', 1.0)]), act('goat', 3, go(V(-5.6, -3.9), V(-5.6, -4.7), 0, 0.3), S_, [(-0.2, 'run', 1.1), (0.05, 'attack1', 1.0)]),
                   act('useless', 3, V(-6.3, -6.9), N, [], rx=-PI / 2, pose=limp(2)), act('bonk', 1, V(-2.9, -6.4), N, [], rx=-PI / 2, z=0.05, pose=limp(5))],
                   fires + [tracers(14, 7, 0.9), ('burst', 0.33, V(-5.5, -5.3), 22, 1.0, 0.035)], slow=0.4, pov=1.0, name='pov_left'))
    cp0, cp1 = V(-2.3, -5.5), V(-2.9, -6.5)
    SH.append(shot(19.6, 21.8, pov_cam(Q, 30, -13), [me_prone(Q),
                   act('useless', 4, go(cp0, cp1, 0, 0.6), hd(Q - cp0), [], rx=math.radians(84), pose=crawl(0.56)),
                   act('whale', 1, V(-2.2, -3.6), S_, [(0.02, 'attack1', 1.0)]),
                   thrown('bonk', 2, V(-2.9, -4.2), V(-3.9, -5.6), 0.5, 0.5, 1.2, 0.8, 'attack1', 4), thrown('walter', 2, V(-1.7, -4.5), V(-0.9, -6.2), 0.5, 0.5, 1.4, 1.0, 'attack1', 6)],
                   [('ring', 0.5, V(-2.2, -4.2, 0.12), 3.0), ('burst', 0.5, V(-2.2, -4.2), 40, 1.8, 0.04), ('flash', 0.5, V(-2.2, -4.2, 0.8), 9000), tracers(12, 8, 0.9), ('boom', 0.1, V(-0.4, -1.0, 0.3), 1.3)],
                   slow=0.4, pov=1.0, name='pov_right'))
    SH.append(shot(21.8, 24.0, pov_cam(Q, 0, 9, 0.1), [me_prone(Q, lambda u: ease(ramp(u, 0.45, 0.85))),
                   act('giga', 0, V(-4.1, -5.3), hd(V(0.2, -1)), [(0, 'hit', 0.6), (0.2, 'die', 1.0)]),
                   act('goat', 0, go(V(-4.4, -2.6), V(-4.3, -3.6), 0, 0.9), S_, [(0, 'walk', 1.0)]), act('goat', 4, go(V(-5.6, -2.2), V(-5.5, -3.2), 0, 0.9), S_, [(-0.2, 'walk', 1.0)]),
                   act('useless', 2, V(-5.3, -6.4), N, [], rx=-PI / 2, pose=limp(7))],
                   fires + [tracers(10, 9, 0.9)], slow=0.4, pov=0.9, name='pov_front'))
    # 8. It gets up.
    up = lambda u: ease(ramp(u, 0.35, 1.7))
    SH.append(shot(24.0, 26.4, lambda k, u: dict(pos=Q.to_3d() + V(0.45 - 0.1 * k, 2.0, 0.22 + 0.25 * up(u)), tgt=Q.to_3d() + V(0, 0.55 * (1 - up(u)), 0.2 + 0.4 * up(u)), fov=34, fstop=2.0, shake=0.008),
                   [act('useless', 0, Q, N, [], rx=lambda u: math.radians(86) * (1 - up(u)),
                        pose=lambda u: {**prone(u, 3.0, 1 - up(u), ease(ramp(u, 0.2, 0.9))), 'Spine': (22 * sn(PI * up(u)), 0, 0), 'Spine1': (18 * sn(PI * up(u)), 0, 0)}),
                    act('useless', 2, V(-5.3, -6.4), N, [], rx=-PI / 2, pose=limp(7)), act('bonk', 1, V(-2.9, -6.4), N, [], rx=-PI / 2, z=0.05, pose=limp(5))],
                   [tracers(10, 10, 2.4), ('boom', 0.8, V(-6.8, -9.6, 0.3), 1.2)], clock='0:12', name='rise'))
    # 9. The Whale breaks what is left of the line.
    SH.append(shot(26.4, 29.0, lambda k, u: dict(pos=V(-4.5 + 0.2 * k, -5.9, 0.16), tgt=V(LX, -3.2, 1.35), fov=36, fstop=2.8, shake=0.01 + 0.08 * (0.55 < u < 0.8)),
                   [act('whale', 0, V(LX, -3.2), S_, [(0.03, 'attack1', 1.0)]),
                    thrown('useless', 5, V(-5.9, -4.0), V(-6.9, -6.4), 0.56, 0.5, 1.5, 1.0, 'attack1', 2), thrown('walter', 0, V(-4.0, -3.7), V(-2.6, -5.2), 0.56, 0.52, 1.7, 1.25, 'attack1', 5),
                    thrown('cate', 0, V(-6.2, -3.3), V(-7.2, -5.4), 0.58, 0.55, 1.3, 0.75, 'attack2', 8),
                    act('goat', 1, V(-6.3, -2.2), S_, [(0, 'ready', 1.0)]), act('goat', 2, V(-3.8, -2.0), S_, [(-0.3, 'ready', 1.0)])],
                   [('ring', 0.56, V(LX, -3.9, 0.12), 3.6), ('burst', 0.56, V(LX, -3.9), 60, 2.2, 0.045), ('flash', 0.56, V(LX, -3.9, 0.8), 14000), tracers(12, 11, 1.2)], slow=0.45, clock='0:10', name='slam'))
    # 10. It runs.
    r0, r1 = V(-4.4, -8.2), V(-4.9, -3.7)
    SH.append(shot(29.0, 31.2, lambda k, u: dict(pos=r0.lerp(r1, ramp(u, 0, 2.2)).to_3d() + V(0.28, 2.3, 0.28), tgt=r0.lerp(r1, ramp(u, 0, 2.2)).to_3d() + V(0, 0, 0.5), fov=36, fstop=2.0, shake=0.035),
                   [act('useless', 0, go(r0, r1, 0, 2.2), hd(r1 - r0), [(0, 'run', 1.5)], pose=lambda u: {'Spine': (10, 0, 0)}),
                    act('whale', 0, V(-6.4, -5.2), hd(V(1, -0.6)), [(0, 'attack2', 1.0), (0.9, 'idle', 1.0)]), act('goat', 2, V(-3.4, -4.6), S_, [(0.9, 'attack1', 1.0)]),
                    act('useless', 5, V(-6.9, -6.4), N, [], rx=-PI / 2, pose=limp(2))],
                   [('boom', 0.45, V(-6.4, -7.0, 0.4), 1.7), ('boom', 1.25, V(-3.1, -5.6, 0.4), 1.9), ('burst', 0.45, V(-6.4, -7.0), 30, 1.6, 0.04), ('burst', 1.25, V(-3.1, -5.6), 30, 1.6, 0.04),
                    ('flash', 1.25, V(-3.1, -5.6, 1.0), 16000), tracers(26, 12, 2.2)], clock='0:07', name='run'))
    b0, b1 = V(LX, -1.5), V(LX, 1.5)
    hp = lambda u: b0.lerp(b1, ramp(u, 0, 1.1)) + V(0.28 * sn(u * 7), 0)
    SH.append(shot(31.2, 33.4, lambda k, u: dict(pos=V(-1.5, -0.7 + 0.5 * k, 0.5), tgt=hp(u).to_3d() + V(0, 0.3, 0.55), fov=40, fstop=2.8, shake=0.02 + 0.07 * (0.36 < u < 0.6)),
                   [act('useless', 0, hp, N, [(0, 'run', 1.5)], pose=lambda u: {'Spine': (12, 0, 0)}),
                    act('goat', 1, V(-5.75, -0.2), hd(V(0.5, -1)), [(0.05, 'attack1', 1.0)]), act('goat', 2, V(-4.3, 0.95), hd(V(-0.5, -1)), [(0.45, 'attack2', 1.0)])],
                   [('boom', 0.36, V(-3.2, 0.2, 0.0), 2.0), ('burst', 0.36, V(-3.2, 0.2), 60, 2.6, 0.045), ('flash', 0.36, V(-3.2, 0.2, 0.8), 22000), ('ring', 0.36, V(-3.2, 0.2, -0.2), 2.6), tracers(18, 13, 1.1)],
                   slow=0.5, clock='0:04', name='bridge'))
    # 11. The leap: time all but stops.
    j0, j1 = V(LX, 1.9), BOSS + V(0, -0.55); UH = 0.8
    jp = lambda u: j0.lerp(j1, ramp(u, 0, UH)); jz = lambda u: 1.75 * sn(PI * 0.78 * ramp(u, 0, UH))
    def orbit(k, u):
        a = math.radians(205 + 125 * ease(k)); c = jp(u).to_3d() + V(0, 0, jz(u) + 0.45)
        return dict(pos=c + V(math.cos(a) * 1.9, sn(a) * 1.9, -0.25 + 0.3 * k), tgt=c + V(0, 0.25, 0), fov=38, fstop=2.0, shake=0.004)
    SH.append(shot(33.4, 37.4, orbit, [act('useless', 0, jp, N, [], z=jz, rx=lambda u: math.radians(lerp(-14, 26, ramp(u, 0, UH))), pose=leap(UH + 0.02)),
                   act('goat', 0, BOSS, S_, [(-0.5, 'ready', 0.8)], pose=lambda u: {'Head': (-22 * ease(ramp(u, 0.2, 0.6)), 0, 0), 'Spine2': (-10 * ease(ramp(u, 0.2, 0.6)), 0, 0)}),
                   act('goat', 3, V(-6.4, 5.4), S_, [(0, 'idle', 1.0)]), act('goat', 4, V(-6.0, 6.6), S_, [(-1, 'idle', 1.0)])],
                   [tracers(30, 14, 0.8), ('boom', 0.1, V(-8.6, 5.0, 0.4), 1.3), ('boom', 0.4, V(-0.8, 7.6, 0.4), 1.3)], slow=0.2, clock='0:02', name='leap'))
    # 12. It lands.
    fallk = lambda u: ease(ramp(u, 0.1, 0.62))
    SH.append(shot(37.4, 39.2, lambda k, u: dict(pos=V(-2.2 - 0.2 * k, 3.1, 0.3), tgt=V(LX, 4.35 + 0.3 * fallk(u), 0.6 - 0.15 * fallk(u)), fov=44, fstop=2.8, shake=0.01 + 0.1 * (0.06 < u < 0.3)),
                   [act('useless', 0, go(j1, j1 + V(0, 0.1), 0, 0.3), N, [(0.16, 'ready', 1.0)], z=lambda u: 1.0 * (1 - ramp(u, 0.0, 0.16)) ** 2 + 0.0,
                        pose=lambda u: {k_: tuple(v * (1 - ease(ramp(u, 0.1, 0.3))) for v in val) for k_, val in leap(0.06)(u).items()}),
                    act('goat', 0, go(BOSS, BOSS + V(0, 0.9), 0.08, 0.6), S_, [(0.06, 'hit', 0.8)], rx=lambda u: -math.radians(88) * fallk(u), z=lambda u: 0.25 * sn(PI * fallk(u)),
                        pose=then(0.08, lambda u: {}, flail(4), 0.05)),
                    act('goat', 3, V(-6.4, 5.4), S_, [(0.3, 'lose', 1.2)]), act('goat', 4, V(-6.0, 6.6), S_, [(0.35, 'lose', 1.2)])],
                   [('flash', 0.07, V(LX, 4.0, 1.2), 40000), ('ring', 0.07, V(LX, 4.0, 0.8), 3.4), ('burst', 0.07, V(LX, 4.0), 60, 2.4, 0.045), ('burst', 0.62, BOSS + V(0, 1.2), 40, 1.3, 0.04)],
                   slow=0.6, clock='0:01', name='strike'))
    # 13. Their tower goes.
    T3 = TOWER.to_3d()
    SH.append(shot(39.2, 42.4, lambda k, u: dict(pos=V(-3.9, 1.9, 0.55 + 0.25 * k), tgt=V(-0.9, 10.5, 2.0), fov=33, fstop=5.6, focus=14.0, shake=0.012 + 0.06 * (0.1 < u < 1.0)),
                   [act('useless', 0, j1 + V(0, 0.1), hd(TOWER - j1), [(0, 'ready', 0.7)]), act('goat', 0, BOSS + V(0, 0.9), S_, [], rx=-math.radians(88), pose=limp(4)),
                    act('goat', 3, V(-6.4, 5.4), S_, [(-0.3, 'lose', 1.2)]), act('goat', 4, V(-6.0, 6.6), S_, [(-0.25, 'lose', 1.2)])],
                   [('boom', 0.1, T3 + V(-0.8, -0.9, 1.4), 2.6), ('boom', 0.42, T3 + V(0.9, -0.6, 2.6), 3.2), ('boom', 0.75, T3 + V(0, -0.8, 1.0), 3.8), ('boom', 1.1, T3 + V(-0.5, -0.4, 3.2), 2.6),
                    ('flash', 0.42, T3 + V(0, -2.5, 2.5), 250000), ('burst', 0.42, TOWER + V(0, -1.2), 60, 3.4, 0.07), ('ring', 0.42, T3 + V(0, 0, 0.3), 9.0), ('swap', 0.45), tracers(10, 15, 1.6)],
                   slow=0.5, clock='0:00', name='tower'))
    # 14. After.
    hero = j1 + V(0, 0.1)
    SH.append(shot(42.4, 46.0, lambda k, u: dict(pos=V(-6.7 + 0.2 * k, 0.0, 0.4 + 1.1 * ease(k)), tgt=V(-1.8, 9.0, 1.7 + 0.3 * k), fov=40, fstop=4.0, focus=3.0, shake=0.004),
                   [act('useless', 0, hero, hd(TOWER - hero), [(0, 'idle', 1.0), (1.1, 'win', 1.0)]),
                    act('giga', 0, go(V(-2.4, 1.0), V(-2.5, 3.2), 0, 2.0), N, [(0, 'walk', 1.0), (2.0, 'win', 1.0)]),
                    act('bonk', 0, go(V(-3.4, 0.6), V(-3.3, 2.4), 0, 1.7), N, [(0, 'walk', 1.1), (1.7, 'win', 1.0)]),
                    act('walter', 1, go(V(-4.3, 0.0), V(-4.4, 1.9), 0.2, 2.2), N, [(0, 'walk', 1.0), (2.2, 'win', 1.0)]),
                    act('goat', 0, BOSS + V(0, 0.9), S_, [], rx=-math.radians(88), pose=limp(4))],
                   [('fire', T3 + V(0, -0.8, 1.6), 2.4), ('fire', T3 + V(1.0, -0.4, 2.8), 1.8)], name='after'))
    return SH


# ------------------------------------------------------------------ effects
MATS = {}
def fx_mats():
    def soft(name, emit):
        """A soft-edged blob: object colour = tint, object alpha = how much of it is there (fire: brightness; smoke: density)."""
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
        oi = nt.nodes.new('ShaderNodeObjectInfo'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 4
        tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(lw.outputs['Facing'], m1.inputs[0]); nt.links.new(nz.outputs['Fac'], m1.inputs[1])
        m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY_ADD'; m2.inputs[1].default_value = -2.6; m2.inputs[2].default_value = 1.0; m2.use_clamp = True
        nt.links.new(m1.outputs[0], m2.inputs[0])
        m3 = nt.nodes.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'; m3.use_clamp = True; nt.links.new(m2.outputs[0], m3.inputs[0]); nt.links.new(oi.outputs['Alpha'], m3.inputs[1])
        nt.links.new(oi.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 1.0
        if emit:
            nt.links.new(oi.outputs['Color'], b.inputs['Emission Color']); e = nt.nodes.new('ShaderNodeMath'); e.operation = 'MULTIPLY'; e.inputs[1].default_value = emit
            nt.links.new(oi.outputs['Alpha'], e.inputs[0]); nt.links.new(e.outputs[0], b.inputs['Emission Strength']); b.inputs['Alpha'].default_value = 1.0
            mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'; mn.inputs[1].default_value = 1.0; nt.links.new(m3.outputs[0], mn.inputs[0]); nt.links.new(m2.outputs[0], b.inputs['Alpha'])
        else: nt.links.new(m3.outputs[0], b.inputs['Alpha'])
        return m
    MATS['fire'] = soft('fx_fire', 14.0); MATS['smoke'] = soft('fx_smoke', 0.0)
    MATS['snow'] = sets.flat('fx_snow', (0.93, 0.96, 1.0), 0.6); MATS['dirt'] = sets.flat('fx_dirt', (0.10, 0.09, 0.09), 0.9)
    for nm, col in (('tr_ours', (0.3, 1.0, 0.5)), ('tr_theirs', (1.0, 0.25, 0.2)), ('ringm', (0.8, 0.92, 1.0))):
        MATS[nm] = sets.flat('fx_' + nm, col, 0.5, emit=(col, 30.0 if nm != 'ringm' else 3.0))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0); o = bpy.context.active_object
    for p in o.data.polygons: p.use_smooth = True
    MATS['ball'] = o.data; bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0); o = bpy.context.active_object; MATS['chunk'] = o.data; bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.018, depth=1.0); o = bpy.context.active_object; MATS['rod'] = o.data; bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.018, major_segments=64, minor_segments=8); o = bpy.context.active_object; MATS['torus'] = o.data; bpy.data.objects.remove(o)


def obj(mesh, mat, shadow=False):
    me = MATS[mesh].copy() if False else MATS[mesh]
    o = bpy.data.objects.new('fx', me); bpy.context.scene.collection.objects.link(o); o.visible_shadow = shadow
    if not me.materials: me.materials.append(None)
    o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = MATS[mat]; o.scale = (0, 0, 0); return o


def key3(K, o, path, f, v):
    for i in range(len(v)): K.add(o, path, i, f, v[i])


def build_fx(K, L, sh, frames, uof, rng):
    """One shot's effects, keyed on its frames (uof(f) = the shot's world time at film frame f)."""
    f0, f1 = frames[0], frames[-1] + 1
    def life(o):
        key3(K, o, 'scale', f0 - 1, (0, 0, 0)); key3(K, o, 'scale', f1, (0, 0, 0))
    for e in sh['fx']:
        kind = e[0]
        if kind in ('boom', 'fire'):
            if kind == 'boom': _, u0, p, size = e
            else: _, p, size = e; u0 = -9.0
            p = Vector(p)
            blobs = [(obj('ball', 'fire'), Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0, 1))) * 0.35 * size, rng.uniform(0.6, 1.0)) for _ in range(5 if kind == 'boom' else 3)]
            smoke = [(obj('ball', 'smoke'), Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.2, 1))) * 0.4 * size, rng.uniform(0.7, 1.2), rng.uniform(0, 1)) for _ in range(7)]
            lt = bpy.data.objects.new('boomL', bpy.data.lights.new('boomL', 'POINT')); bpy.context.scene.collection.objects.link(lt); lt.data.color = (1.0, 0.5, 0.18)
            lt.data.shadow_soft_size = 0.5 * size; lt.location = p + Vector((0, 0, 0.5 * size)); lt.data.energy = 0; L.append(lt)
            for o, *_ in blobs + smoke: life(o)
            K.add(lt.data, 'energy', 0, f0 - 1, 0.0); K.add(lt.data, 'energy', 0, f1, 0.0)
            for f in frames:
                a = uof(f) - u0
                if kind == 'fire':
                    for j, (o, off, s) in enumerate(blobs):
                        fl = 0.75 + 0.25 * sn(uof(f) * 13 + j * 2); key3(K, o, 'location', f, p + off * 0.6 + Vector((0, 0, 0.25 * size * sn(uof(f) * 5 + j)))); key3(K, o, 'scale', f, [size * 0.55 * s * fl] * 3)
                        key3(K, o, 'color', f, (1.0, 0.42, 0.1, 0.55 * fl))
                    for j, (o, off, s, ph) in enumerate(smoke):
                        c = (uof(f) * 0.22 + ph) % 1.0; key3(K, o, 'location', f, p + off + Vector((0.9 * c, 0.3 * c, 0.6 * size + 5.0 * c))); key3(K, o, 'scale', f, [size * (0.5 + 1.6 * c) * s] * 3)
                        key3(K, o, 'color', f, (0.07, 0.06, 0.07, 0.6 * sn(PI * c)))
                    K.add(lt.data, 'energy', 0, f, 500 * size * (0.8 + 0.2 * sn(uof(f) * 17))); continue
                if a < 0:
                    for o, *_ in blobs + smoke: key3(K, o, 'scale', f, (0, 0, 0))
                    K.add(lt.data, 'energy', 0, f, 0.0); continue
                g = 1 - math.exp(-a * 9)
                for o, off, s in blobs:
                    key3(K, o, 'location', f, p + off * (0.5 + 1.2 * g) + Vector((0, 0, 0.6 * size * g + 0.8 * a))); key3(K, o, 'scale', f, [0.55 * size * s * (0.25 + 0.75 * g) * max(0.0, 1 - a / 1.1)] * 3)
                    h = math.exp(-a * 3.2); key3(K, o, 'color', f, (1.0, 0.25 + 0.45 * h, 0.05 + 0.3 * h * h, 1.6 * h))
                for o, off, s, ph in smoke:
                    key3(K, o, 'location', f, p + off * (0.6 + 1.6 * g) + Vector((0.3 * a, 0.1 * a, 0.5 * size * g + 1.1 * a))); key3(K, o, 'scale', f, [0.5 * size * s * (0.3 + 0.8 * g + 0.35 * a)] * 3)
                    key3(K, o, 'color', f, (0.06, 0.055, 0.06, 0.5 * ramp(a, 0.04, 0.3) * max(0.0, 1 - a / 3.5)))
                K.add(lt.data, 'energy', 0, f, 3500 * size * size * math.exp(-a * 7))
        elif kind == 'flash':
            _, u0, p, en = e; lt = bpy.data.objects.new('flash', bpy.data.lights.new('flash', 'POINT')); bpy.context.scene.collection.objects.link(lt); L.append(lt)
            lt.location = p; lt.data.color = (1.0, 0.86, 0.7); lt.data.shadow_soft_size = 0.3; lt.data.energy = 0
            K.add(lt.data, 'energy', 0, f0 - 1, 0.0); K.add(lt.data, 'energy', 0, f1, 0.0)
            for f in frames: a = uof(f) - u0; K.add(lt.data, 'energy', 0, f, 0.1 * en * math.exp(-a * 16) if a >= 0 else 0.0)
        elif kind == 'ring':
            _, u0, p, size = e; o = obj('torus', 'ringm'); o.location = p; life(o)
            for f in frames:
                a = uof(f) - u0; g = 1 - math.exp(-a * 5) if a >= 0 else 0
                key3(K, o, 'scale', f, (size * g, size * g, max(0.02, 1.4 * (1 - g))) if 0 <= a < 0.9 else (0, 0, 0))
        elif kind == 'burst':
            _, u0, p, n, power, r = e
            for j in range(n):
                o = obj('chunk', 'dirt' if j % 4 == 0 else 'snow'); life(o); an = rng.uniform(0, 6.283); vr = rng.uniform(0.3, 1.0) * power * 1.6; vz = rng.uniform(0.8, 2.6) * power
                lf = rng.uniform(0.5, 1.1) * (0.8 + 0.25 * power); rr = r * rng.uniform(0.4, 1.5); off = rng.uniform(0, 0.25)
                for f in frames:
                    a = uof(f) - u0
                    if not 0 <= a <= lf: key3(K, o, 'scale', f, (0, 0, 0)); continue
                    key3(K, o, 'location', f, (p.x + math.cos(an) * (off + vr * a), p.y + sn(an) * (off + vr * a), max(0.0, 0.05 + vz * a - 2.6 * a * a))); key3(K, o, 'scale', f, [rr * (1 - a / lf) ** 0.5] * 3)
        elif kind == 'tracers':
            _, n, seed, dur = e; r2 = random.Random(seed)
            for j in range(n):
                ours = r2.random() < 0.5; o = obj('rod', 'tr_ours' if ours else 'tr_theirs'); life(o)
                x = r2.uniform(-9.5, -0.5); z = r2.uniform(1.0, 3.6); us = r2.uniform(-0.6, dur); sp = r2.uniform(26, 40) * (1 if ours else -1); y0 = -15.0 if ours else 15.0
                dx = r2.uniform(-0.12, 0.12); dz = r2.uniform(-0.03, 0.05); d = Vector((dx, 1.0, dz)).normalized()
                o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
                for f in frames:
                    a = uof(f) - us; y = y0 + sp * a
                    if a < 0 or abs(y) > 15: key3(K, o, 'scale', f, (0, 0, 0)); continue
                    key3(K, o, 'location', f, (x + dx * (y - y0), y, z + dz * abs(y - y0))); key3(K, o, 'scale', f, (1, 1, r2.choice((1.6, 2.2, 3.0))))


# ------------------------------------------------------------------ build
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    res = int(arg('--res', '1080')); sc = bpy.context.scene
    SH = film(); END = SH[-1]['t1']; NF = int(round(END * FPS))
    UD.setup_render(res); sc.frame_end = NF; sc.world.mist_settings.start = 5.0; sc.world.mist_settings.depth = 34.0
    # first person: everything soft and drained (mixed in by the 'povk' value)
    nt = sc.node_tree; cb = next(n for n in nt.nodes if n.bl_idname == 'CompositorNodeColorBalance'); ld = next(n for n in nt.nodes if n.bl_idname == 'CompositorNodeLensdist')
    pk = nt.nodes.new('CompositorNodeValue'); pk.name = 'povk'; pk.outputs[0].default_value = 0.0
    bl = nt.nodes.new('CompositorNodeBlur'); bl.filter_type = 'GAUSS'; bl.size_x = bl.size_y = max(2, res // 70); nt.links.new(cb.outputs['Image'], bl.inputs['Image'])
    mx = nt.nodes.new('CompositorNodeMixRGB'); nt.links.new(pk.outputs[0], mx.inputs[0]); nt.links.new(cb.outputs['Image'], mx.inputs[1]); nt.links.new(bl.outputs['Image'], mx.inputs[2])
    sm = nt.nodes.new('CompositorNodeMath'); sm.operation = 'MULTIPLY_ADD'; sm.inputs[1].default_value = -0.55; sm.inputs[2].default_value = 1.0; nt.links.new(pk.outputs[0], sm.inputs[0])
    hs = nt.nodes.new('CompositorNodeHueSat'); nt.links.new(mx.outputs['Image'], hs.inputs['Image']); nt.links.new(sm.outputs[0], hs.inputs['Saturation']); nt.links.new(hs.outputs['Image'], ld.inputs['Image'])
    A = sets.arena(); fx_mats()
    ruin, robjs = game.place(f'{game.G}/arena/battlestation_ruin.glb', sets.ENEMY_KING, PI, 1.2 * game.WORLD, name='en_king_ruin'); sets.team(robjs, THEIRS)
    K = rigctl.Keys(); L = []; rng = random.Random(4)
    # cast: one unit per (kind, index), hidden whenever it is not in the shot
    C = {}; vis = {}; poses = {}
    def unit(kind, i):
        if (kind, i) not in C: C[(kind, i)] = game.Unit(kind, f'{kind}{i}'); vis[(kind, i)] = set(); poses[(kind, i)] = {}
        return C[(kind, i)]
    camk = {}; cuts = set(); swap_f = None; clock = []; povf = {}
    for sh in SH:
        f0, f1 = F(sh['t0']), F(sh['t1']); frames = list(range(f0, f1)); cuts.add(f0); uof = lambda f, f0=f0, s=sh['slow']: (f - f0) / FPS * s
        if sh['clock']: clock.append((sh['t0'], sh['t1'], sh['clock']))
        for a in sh['actors']:
            key = (a['kind'], a['i']); u = unit(*key); vis[key] |= set(frames)
            for f in frames:
                w = uof(f); p = call(a['pos'], w); UD.key_ctrl(K, u, f, p, call(a['h'], w), call(a['z'], w), call(a['rx'], w))
                if a['pose']: poses[key][f] = a['pose'](w)
                else: poses[key][f] = {}
            cl = sorted(a['clips'], key=lambda c: c[0])
            for j, (u0, name, speed) in enumerate(cl):
                u1 = cl[j + 1][0] if j + 1 < len(cl) else 1e9; fs = [f for f in frames if u0 <= uof(f) < u1 + 0.1] if j else [f for f in frames if uof(f) < u1 + 0.1]
                if not fs: continue
                ac = u.clip(name); a0, a1 = ac.frame_range; ln = a1 - a0; tr = u.rig.animation_data.nla_tracks.new(); st = tr.strips.new(f'{f0}_{name}', fs[0], ac)
                st.scale = max(0.01, (fs[-1] + 1 - fs[0]) / ln); st.extrapolation = 'NOTHING'; st.use_auto_blend = False; st.blend_in = 3 if j else 0
                st.use_animated_time = True; fc = st.fcurves.find('strip_time')
                vals = []
                for f in fs:
                    x = (uof(f) - u0) * FPS * speed; x = x % ln if name in LOOP else clamp(x, 0, ln - 0.01); vals += [f, a0 + x]
                fc.keyframe_points.clear(); fc.keyframe_points.add(len(fs)); fc.keyframe_points.foreach_set('co', vals)
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
                fc.update()
        build_fx(K, L, sh, frames, uof, rng)
        for e in sh['fx']:
            if e[0] == 'swap': swap_f = f0 + int(round(e[1] / sh['slow'] * FPS))
        for f in frames:
            w = uof(f); k = (f - f0) / max(1, f1 - 1 - f0); camk[f] = sh['cam'](k, w); povf[f] = sh['pov']
    # custom bone animation: one COMBINE layer per unit over its clips
    for key, u in C.items():
        fr = sorted(poses[key]); bones = sorted({b for f in fr for b in poses[key][f]})
        if bones:
            ac = bpy.data.actions.new(f'pose_{u.name}')
            for b in bones:
                pts = [[] for _ in range(4)]
                for f in fr:
                    q = Euler([math.radians(x) for x in poses[key][f].get(b, (0, 0, 0))]).to_quaternion()
                    for i in range(4): pts[i] += [f, q[i]]
                for i in range(4):
                    fc = ac.fcurves.new(f'pose.bones["mixamorig:{b}"].rotation_quaternion', index=i, action_group=b); fc.keyframe_points.add(len(fr)); fc.keyframe_points.foreach_set('co', pts[i])
                    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            tr = u.rig.animation_data.nla_tracks.new(); st = tr.strips.new('pose', 1, ac); st.blend_type = 'COMBINE'; st.extrapolation = 'HOLD'; st.use_auto_blend = False
        for f in range(1, NF + 1): K.add(u.mesh, 'hide_render', 0, f, f not in vis[key])
    # their king tower: whole until the swap, then the game's ruin
    for o in A['towers']['en_king'][1]: K.add(o, 'hide_render', 0, 1, False); K.add(o, 'hide_render', 0, swap_f, True)
    for o in robjs: K.add(o, 'hide_render', 0, 1, True); K.add(o, 'hide_render', 0, swap_f, False)
    K.flush()
    # camera, light
    cam = UD.make_camera(); K2 = rigctl.Keys(); rs = random.Random(8)
    def light(name, kind, loc, energy, color, size=0.3, tgt=None):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); o.data.energy = energy; o.data.color = color
        if kind == 'AREA': o.data.size = size
        elif kind != 'SUN': o.data.shadow_soft_size = size
        o.location = loc; sc.collection.objects.link(o)
        if tgt: o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        L.append(o); return o
    moon = light('moon', 'SUN', (0, 0, 10), 2.3, (0.62, 0.74, 1.0)); moon.rotation_euler = Euler((math.radians(58), 0, math.radians(205))); moon.data.angle = 0.06
    light('arena_fill', 'AREA', (0, -26, 14), 1000, (0.55, 0.68, 1.0), 20, (0, 0, 0))
    light('war_glow', 'AREA', (0, 22, 5), 700, (1.0, 0.42, 0.2), 14, (0, 0, 1))                       # the horizon burns behind their lines
    rim = light('rim', 'SPOT', (0, 0, 5), 1700, (0.6, 0.95, 1.0), 0.25); rim.data.spot_size = math.radians(46); rim.data.spot_blend = 0.6; rim.rotation_mode = 'QUATERNION'
    emb = [light(f'ember{i}', 'POINT', (p.x, p.y, 0.9), 420, (1.0, 0.42, 0.12), 0.35) for i, p in enumerate(A['ruins'])]
    light('king_glow', 'POINT', (0, -12.3, 1.6), 260, OURS, 0.5); light('en_glow', 'POINT', (0, 12.3, 1.6), 260, THEIRS, 0.5)
    for f in range(1, NF + 1):
        c = camk[f]; t = (f - 1) / FPS; pos = Vector(c['pos']); tgt = Vector(c['tgt']); a = c.get('shake', 0.0)
        pos = pos + Vector((sn(t * 31.0) + 0.6 * sn(t * 47.3 + 1), sn(t * 27.1 + 2) + 0.6 * sn(t * 53.9), sn(t * 35.7 + 4) + 0.6 * sn(t * 41.1 + 3))) * a
        tgt = tgt + Vector((sn(t * 23.0 + 1), sn(t * 29.0 + 2), sn(t * 37.0))) * a * 2.5
        q = (tgt - pos).to_track_quat('-Z', 'Y') @ Quaternion((0, 0, 1), math.radians(c.get('roll', 0.0)))
        focus = c.get('focus') or (tgt - pos).length
        for i in range(3): K2.add(cam, 'location', i, f, pos[i])
        for i in range(4): K2.add(cam, 'rotation_quaternion', i, f, q[i])
        K2.add(cam.data, 'lens', 0, f, 12.0 / math.tan(math.radians(c['fov']) / 2)); K2.add(cam.data, 'dof.focus_distance', 0, f, focus)
        K2.add(cam.data, 'dof.aperture_fstop', 0, f, c['fstop']); K2.add(cam.data, 'clip_start', 0, f, c.get('near', 0.05))
        K2.add(nt, 'nodes["povk"].outputs[0].default_value', 0, f, povf[f]); K2.add(nt, 'nodes["mistk"].outputs[0].default_value', 0, f, 0.3)
        dv = Vector((tgt.x - pos.x, tgt.y - pos.y, 0)); dv = dv.normalized() if dv.length > 0.1 else Vector((0, 1, 0)); sd = Vector((-dv.y, dv.x, 0))
        ft = pos + (tgt - pos).normalized() * min(focus, 6.0); rp = ft + dv * 3.2 + sd * 1.3; rp.z = ft.z + 2.6; rq = (ft - rp).to_track_quat('-Z', 'Y')
        for i in range(3): K2.add(rim, 'location', i, f, rp[i])
        for i in range(4): K2.add(rim, 'rotation_quaternion', i, f, rq[i])
        for i, e in enumerate(emb): K2.add(e.data, 'energy', 0, f, 420 * (0.7 + 0.3 * sn(t * 11.3 + i * 2.1) * sn(t * 6.7 + i)))
    K2.flush()
    for o in L: o.visible_camera = False; o.visible_glossy = False
    for ac in bpy.data.actions:
        for fc in ac.fcurves:
            if fc.data_path == 'hide_render':
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    for idb in (cam, cam.data, nt, rim):
        for fc in idb.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cuts else 'LINEAR'
    json.dump(dict(fps=FPS, end=END, clock=clock, cuts=sorted((c - 1) / FPS for c in cuts), shots=[dict(name=s['name'], t0=s['t0'], t1=s['t1'], slow=s['slow'], pov=s['pov']) for s in SH],
                   fx=[dict(kind=e[0], t=s['t0'] + e[1] / s['slow'], size=e[3] if e[0] == 'boom' else 1.0) for s in SH for e in s['fx'] if e[0] in ('boom', 'flash', 'ring', 'swap')]),
              open(os.path.join(os.environ['W'], 'timeline.json'), 'w'), indent=1)
    sc.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False); print('SAVED', arg('--out'), NF, 'frames')


if __name__ == '__main__':
    main()
