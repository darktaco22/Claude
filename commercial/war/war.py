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
    tr = tremble * (sn(u * 57) + 0.6 * sn(u * 83 + 1)); ax = lerp(-98, -20, push) * reach + 60 * (1 - reach)
    return {'LeftArm': (ax + tr, 0, -50 * (1 - push) + 30 * push), 'RightArm': (ax - tr, 0, 50 * (1 - push) - 30 * push),
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


# ------------------------------------------------------------------ the game's units, with whatever they carry
game.H.update(floki=1.4, swordcat=1.15, toshi=1.15, slerf=1.9, alon=1.4, mitch=1.5)


class WUnit:
    """One instance of a game unit: rig + skinned mesh + its props (axe, sword: bone-parented), scaled to its in-game size."""
    _src = {}

    def __init__(self, kind, name):
        self.kind, self.name = kind, name; link = bpy.context.scene.collection.objects.link
        if kind not in WUnit._src:
            before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=f'{game.G}/units/{kind}.glb')
            for o in [o for o in bpy.data.objects if o not in before and o.name.startswith('Icosphere')]: bpy.data.objects.remove(o)
            rig = bpy.data.objects[f'{kind}_rig']; parts = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
            for a in bpy.data.actions:
                if a.name.endswith(f'_{kind}_rig'): a.use_fake_user = True
            WUnit._src[kind] = (rig, parts); self.rig, self.parts = rig, parts
        else:
            r0, p0 = WUnit._src[kind]; self.rig = r0.copy(); link(self.rig); self.parts = []
            for o in p0:
                c = o.copy(); link(c); c.parent = self.rig; c.matrix_parent_inverse = o.matrix_parent_inverse.copy(); self.parts.append(c)
                for md in c.modifiers:
                    if md.type == 'ARMATURE': md.object = self.rig
            self.rig.animation_data_clear()
        self.rig.animation_data_create(); self.rig.animation_data.action = None
        for tr in list(self.rig.animation_data.nla_tracks): self.rig.animation_data.nla_tracks.remove(tr)
        self.mesh = next(o for o in self.parts if any(md.type == 'ARMATURE' for md in o.modifiers))
        for o in self.parts: o.cycles.use_motion_blur = True; o.cycles.use_deform_motion = True
        self.rig.location = (0, 0, 0); self.rig.rotation_euler = (0, 0, 0); self.rig.scale = (1, 1, 1); self.rig.parent = None
        bpy.context.view_layer.update()
        zs = [(self.mesh.matrix_world @ Vector(c)).z for c in self.mesh.bound_box]; h = max(zs) - min(zs); s = game.vis_h(kind) / h
        self.ctrl = bpy.data.objects.new(f'{name}_ctrl', None); link(self.ctrl); self.ctrl.rotation_mode = 'XYZ'
        self.rig.parent = self.ctrl; self.rig.scale = (s, s, s); self.rig.location = (0, 0, -min(zs) * s); self.height = game.vis_h(kind)

    def clip(self, name): return bpy.data.actions[f'{name}_{self.kind}_rig']


# ------------------------------------------------------------------ the arena: THE DUMP (the game's ground and backdrop, its towers and bridges)
def arena_dump():
    A = {}; G = game.G; gd = f'{G}/arenas/dump'; rng = random.Random(23)
    ground = sets.img_mat('a_ground', f'{gd}/ground.webp', repeat=1.0, normal=f'{gd}/ground_n.webp', tint=(0.8, 0.76, 0.74), rough=0.92)
    for s in (-1, 1): sets.plane('a_ground', (60, 34), (0, s * (1.3 + 17), 0), (0, 0, 0), ground, uv_scale=0.09)
    sets.plane('a_river', (60, 2.6), (0, 0, -0.35), (0, 0, 0), sets.flat('a_sludge', (0.07, 0.12, 0.03), 0.2, emit=((0.3, 0.9, 0.1), 0.6)))
    bank = sets.flat('a_bank', (0.16, 0.1, 0.08), 0.9)
    for s in (-1, 1): sets.box('a_bankwall', (-30, s * 1.3 - 0.06, -0.36), (30, s * 1.3 + 0.06, 0.0), bank)
    for x in (-sets.BRIDGE_X, sets.BRIDGE_X):
        r, objs = game.place(f'{G}/arena/bridge.glb', (x, 0, 0.0), PI / 2, 1.0, name=f'bridge_{x}'); sets.team(objs, (0.8, 0.55, 0.4))
    A['towers'] = {}
    def tower(kind, loc, rz, col, key):
        r, objs = game.place(f'{G}/arena/{kind}.glb', loc, rz, 1.2 * game.WORLD, name=key); sets.team(objs, col); A['towers'][key] = (r, objs)
    tower('battlestation', sets.OUR_KING, 0.0, OURS, 'our_king'); tower('tower_rig_ruin', sets.OUR_PRINC[0], 0.4, OURS, 'our_left_ruin'); tower('tower_rig', sets.OUR_PRINC[1], 0.0, OURS, 'our_right')
    tower('battlestation', sets.ENEMY_KING, PI, THEIRS, 'en_king'); tower('battlestation_ruin', sets.ENEMY_KING, PI, THEIRS, 'en_king_ruin')
    for i, p in enumerate(sets.EN_PRINC): tower('tower_rig_ruin', p, PI + 0.5 * (i - 0.5), THEIRS, f'en_{i}')
    bd = sets.img_mat('a_backdrop', f'{gd}/backdrop.webp', emit=1.0, tint=(1, 1, 1), rough=1.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=46, depth=44, location=(0, 4, 14), end_fill_type='NOTHING')
    cyl = bpy.context.active_object; cyl.name = 'backdrop'; cyl.data.materials.append(bd); cyl.visible_shadow = False; uv = cyl.data.uv_layers[0]
    for p in cyl.data.polygons: p.use_smooth = True
    for poly in cyl.data.polygons:
        for li in poly.loop_indices:
            v = cyl.data.vertices[cyl.data.loops[li].vertex_index].co
            uv.data[li].uv = ((1.0 - (math.atan2(v.y, v.x) / (2 * PI)) % 1.0) * 2.0, min(0.999, 0.1 + 1.25 * (v.z + 22) / 44))
    for poly in cyl.data.polygons:
        us = [uv.data[li].uv.x for li in poly.loop_indices]
        if max(us) - min(us) > 1.0:
            for li in poly.loop_indices:
                if uv.data[li].uv.x < 1.0: uv.data[li].uv.x += 2.0
    cyl.visible_diffuse = False; cyl.visible_glossy = True; A['backdrop_mat'] = bd
    dirt = sets.flat('mound', (0.2, 0.13, 0.1), 0.95)
    for _ in range(220):                                    # churned earth at the edges of the field (never where anyone runs or the camera lies)
        x, y = rng.uniform(-11, 11), rng.uniform(-19, 19)
        if not (x > 3.8 or x < -7.9 or y > 7.6 or y < -15.2) or abs(y) < 2.0: continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.0, location=(x, y, -0.03)); o = bpy.context.active_object
        r = rng.uniform(0.35, 1.1); o.scale = (r * rng.uniform(0.8, 1.5), r * rng.uniform(0.8, 1.3), r * rng.uniform(0.14, 0.3)); o.rotation_euler.z = rng.uniform(0, 3.1); o.data.materials.append(dirt)
        for p in o.data.polygons: p.use_smooth = True
    A['ruins'] = [sets.OUR_PRINC[0]] + sets.EN_PRINC
    em = sets.flat('ember_m', (1, 0.4, 0.1), 0.5, emit=((1.0, 0.38, 0.08), 14.0))
    for i, p in enumerate(A['ruins']): sets.motes(f'embers{i}', (p.x - 0.7, p.y - 0.7, 0.3), (p.x + 0.7, p.y + 0.7, 3.4), 46, 0.008, fall=-0.55, drift=0.3, mat=em, seed=30 + i)
    sets.motes('war_embers', (-10, -11, 0.1), (0, 9, 4.5), 600, 0.011, fall=-0.45, drift=0.6, mat=em, seed=41)
    sets.motes('dust', (-14, -16, 0.0), (6, 14, 7), 2600, 0.011, fall=0.1, drift=0.5, mat=sets.flat('dust_m', (1, 0.8, 0.6), 0.5, emit=((1.0, 0.62, 0.36), 0.5)), seed=7)
    return A


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


def shot(t0, t1, cam, actors=(), fx=(), slow=1.0, pov=0.0, clock=None, name='', sub=None):
    return dict(t0=t0, t1=t1, cam=cam, actors=list(actors), fx=list(fx), slow=slow, pov=pov, clock=clock, name=name, sub=sub)


def tracers(n, seed, dur): return ('tracers', n, seed, dur)


# ------------------------------------------------------------------ the film
# The cast, all from the game: our line is SWORDCAT (a tiny knight: our soldier), FLOKI (a Viking with an axe: its brother in
# arms), TOSHI (samurai) and WALTER (the dog in the tactical vest); theirs is THE GOAT in armour and SLERF, the giant.
Q = V(-3.8, -7.6)                                   # where our soldier lies after the blast
B = V(-4.6, -4.6)                                   # where the shell lands
ME = ('swordcat', 0); BRO = ('floki', 0)
LINE = [('swordcat', 1, V(-5.2, -5.6)), ('toshi', 0, V(-3.6, -5.9)), ('walter', 0, V(-4.5, -5.2)), ('floki', 1, V(-5.9, -5.0)), ('walter', 1, V(-3.2, -5.0)),
        ('swordcat', 2, V(-6.3, -6.2)), ('toshi', 1, V(-2.7, -6.1)), ('floki', 2, V(-5.4, -4.3)), ('walter', 2, V(-3.9, -4.2)), ('swordcat', 3, V(-4.6, -6.6))]
F0 = V(-4.6, -3.6)
EN = [('goat', 0, V(LX, 3.0)), ('goat', 1, V(-5.6, 4.2)), ('goat', 2, V(-4.4, 4.4)), ('slerf', 0, V(LX, 5.8)), ('goat', 3, V(-5.7, 7.0)), ('goat', 4, V(-4.3, 7.2)), ('slerf', 1, V(LX, 8.6))]
BOSS = V(LX, 4.3)
TOWER = sets.ENEMY_KING.to_2d()


def pov_cam(P, yaw=0.0, roll=6.0, look_up=0.0, sway=1.0):
    """First person, lying in the dirt at P facing north: its own paws and sword in the frame, everything soft and tilted."""
    def cam(k, u):
        y = math.radians(yaw + 6 * sn(u * 1.3) * sway); d = V(sn(y), math.cos(y), 0)
        c = P.to_3d() + V(0, 0.55, 0.32 + 0.03 * sn(u * 2.1))
        return dict(pos=c, tgt=c + d * 5 + V(0, 0, -0.3 + look_up + 0.3 * sn(u * 1.7) * sway), fov=64, fstop=1.0, focus=3.2 + 1.6 * sn(u * 2.3), roll=roll + 5 * sn(u * 1.1), shake=0.012, near=0.12)
    return cam


def me_prone(P, push=0.0, rx=86):
    return act(*ME, P, N, [], rx=math.radians(rx), pose=lambda u: prone(u, 2.5, 1.0, call(push, u)))


def film():
    SH = []
    # 1. First person. Face down behind the line. The Viking looks back at it, nods, turns to the enemy.
    P0 = V(-3.9, -8.7); fb = V(-3.1, -7.2)
    line = [act(k, i, p, N, [(-0.4 * j, 'ready' if j % 2 else 'idle', 1.0)], pose=crouch(22, j)) for j, (k, i, p) in enumerate(LINE)]
    SH.append(shot(0.0, 3.0, pov_cam(P0, 8, 4), [me_prone(P0)] + line +
                   [act(*BRO, fb, lambda u: lerp(hd(P0 + V(0, 0.9) - fb), -PI, ease(ramp(u, 1.0, 1.5))) , [(0, 'idle', 1.0)], pose=lambda u: {'Head': (16 * sn(PI * ramp(u, 0.45, 0.85)), 0, 0)})],
                   [tracers(26, 1, 1.8), ('boom', 0.5, V(-2.0, 5.0, 0.4), 1.3), ('boom', 1.3, V(-7.0, 4.4, 0.4), 1.6)], slow=0.6, pov=0.7, name='pov_wait'))
    # 2. The order: the axe goes up.
    SH.append(shot(3.0, 4.8, lambda k, u: dict(pos=V(-4.05 - 0.15 * k, -1.9 - 0.3 * k, 0.26), tgt=F0.to_3d() + V(0, 0, 1.15), fov=36, fstop=2.8, shake=0.006),
                   [act(*BRO, F0, N, [(0, 'emote', 1.15)], pose=arm_up(0.5, 1.6))] + [act(k, i, p, N, [(-0.3 * j, 'ready', 1.2)], pose=crouch(12, j)) for j, (k, i, p) in enumerate(LINE)],
                   [tracers(14, 2, 1.8), ('boom', 0.9, V(-7.6, -6.5, 0.4), 1.2)], sub=(0.5, 1.6, 'FORWARD!'), name='order'))
    # 3. Over the top: the camera climbs out of the dirt behind them and finds the whole field.
    everyone = LINE + [(*ME, V(-4.3, -7.2)), ('swordcat', 4, V(-6.6, -7.4)), ('toshi', 2, V(-2.9, -7.3)), ('walter', 3, V(-5.3, -7.7)), ('floki', 3, V(-3.7, -7.9))]
    run = [act(k, i, go(p, p + V((LX - p.x) * 0.35, 6.0), 0.1 + 0.05 * (j % 4), 3.4), N, [(-0.2 * j, 'ready', 1.0), (0.08 + 0.05 * (j % 4), 'run', 1.3)]) for j, (k, i, p) in enumerate(everyone)]
    run.append(act(*BRO, go(F0, F0 + V(-0.3, 5.0), 0.05, 3.4), N, [(0, 'run', 1.25)]))
    run += [act(k, i, go(p + V(0, 4.5), p + V(0, -0.5), 0, 3.2), S_, [(-0.13 * j, 'run', 1.2)]) for j, (k, i, p) in enumerate(EN)]
    SH.append(shot(4.8, 8.0, lambda k, u: dict(pos=V(LX + 0.5, -10.2, 0.4).lerp(V(LX + 2.6, -9.4, 6.4), ease(k)), tgt=V(LX, -6.2, 0.9).lerp(V(LX, 0.6, 0.2), ease(k)), fov=44, fstop=5.6, shake=0.02),
                   run, [tracers(40, 3, 3.2), ('boom', 0.8, V(-6.9, -3.6, 0.3), 1.3), ('boom', 1.9, V(-3.0, -1.6, 0.3), 1.6), ('boom', 2.6, V(-6.6, 2.6, 0.3), 1.5)] +
                   [('burst', 0.5 + 0.45 * j, V(-5.6 + 1.3 * (j % 3) * 0.7, -4.6 + 0.9 * j), 18, 0.7, 0.03) for j in range(6)], clock='0:30', name='charge'))
    # 4. Underfoot: they go over the lens.
    over = [(BRO, -0.45, 0.02), (ME, 0.5, 0.1), (('toshi', 0), 0.0, 0.2), (('walter', 0), -1.0, -0.06), (('swordcat', 1), 1.05, 0.26), (('floki', 1), -0.2, 0.38)]
    SH.append(shot(8.0, 9.2, lambda k, u: dict(pos=V(LX, -1.9, 0.07), tgt=V(LX, -4.2, 1.5), fov=74, fstop=4.0, focus=1.6, shake=0.03),
                   [act(k_[0], k_[1], go(V(LX + x, -5.2), V(LX + x * 0.8, -0.6), u0, u0 + 0.62), N, [(-u0, 'run', 1.4)], z=lambda u, u0=u0: 0.95 * sn(PI * ramp(u, u0 + 0.2, u0 + 0.55))) for (k_, x, u0) in over],
                   [tracers(14, 31, 0.6), ('burst', 0.2, V(LX - 0.4, -3.2), 20, 0.9, 0.03), ('burst', 0.35, V(LX + 0.5, -3.0), 20, 0.9, 0.03)], slow=0.5, name='stampede'))
    # 5. They come over the bridge.
    SH.append(shot(9.2, 11.0, lambda k, u: dict(pos=V(LX + 0.25, -4.4 + 0.3 * k, 0.26), tgt=V(LX, 0.6, 1.05), fov=27, fstop=4.0, shake=0.02),
                   [act(k, i, go(p, p + V(0, -3.6), 0, 1.8), S_, [(-0.13 * j, 'run', 1.2)]) for j, (k, i, p) in enumerate(EN)],
                   [tracers(18, 4, 1.8), ('boom', 1.0, V(-3.3, 5.6, 0.4), 1.5)], clock='0:27', name='enemy'))
    # 6. From above, the way the game sees it: two lines close.
    top = [act(k, i, go(p + V(0, 0.4), V(p.x * 0.75 + LX * 0.25, -3.3 + 0.35 * (j % 3)), 0, 1.6), N, [(-0.2 * j, 'run', 1.3)]) for j, (k, i, p) in enumerate(LINE[:8] + [(*BRO, F0 + V(0, -1.2)), (*ME, V(-4.3, -5.9))])]
    top += [act(k, i, go(V(p.x, 0.8 + 0.5 * (j % 3)), V(LX + (p.x - LX) * 1.9, -2.2 + 0.3 * (j % 2)), 0, 1.6), S_, [(-0.13 * j, 'run', 1.2)]) for j, (k, i, p) in enumerate(EN[:5])]
    SH.append(shot(11.0, 12.6, lambda k, u: dict(pos=V(LX + 0.2, -2.6, 14.0 - 2.0 * k), tgt=V(LX + 0.2, -2.6 + 0.01, 0), fov=40, fstop=8.0, roll=-10 + 14 * k, shake=0.01),
                   top, [tracers(24, 32, 1.6), ('boom', 0.5, V(-7.6, -1.9, 0.3), 1.4), ('boom', 1.1, V(-2.2, -4.4, 0.3), 1.3)], clock='0:22', name='topdown'))
    # 7. The lines meet. Slow motion.
    SH.append(shot(12.6, 15.6, lambda k, u: dict(pos=V(-0.7 - 0.35 * k, -3.3 + 0.2 * k, 0.3), tgt=V(LX, -2.75, 0.95), fov=33, fstop=2.8, shake=0.012 + 0.05 * (0.44 < u < 0.6)),
                   [act(*BRO, go(V(LX, -3.9), V(LX, -3.25), 0, 0.3), N, [(-0.3, 'run', 1.2), (0.12, 'attack1', 1.0)]),
                    act('goat', 0, go(V(LX, -1.5), V(LX, -2.2), 0, 0.3), S_, [(-0.2, 'run', 1.2), (0.2, 'attack1', 1.0), (0.5, 'hit', 0.8)]),
                    act('toshi', 0, lambda u: V(-6.3, -3.9).lerp(V(-6.0, -2.7), ramp(u, 0, 0.5)).lerp(V(-7.1, -4.8), ramp(u, 0.56, 1.0)), N, [(-0.2, 'run', 1.3)],
                        z=lambda u: 0.85 * sn(PI * ramp(u, 0.1, 0.5)) * (u < 0.56) + 0.9 * sn(PI * ramp(u, 0.56, 1.0)) * (u >= 0.56),
                        rx=lambda u: -math.radians(250) * ramp(u, 0.56, 1.0), pose=then(0.56, leap(0.5), flail(3), 0.05)),
                    act('goat', 1, V(-6.0, -2.0), S_, [(-0.1, 'ready', 1.0), (0.3, 'attack2', 1.0)]),
                    act(*ME, go(V(-3.9, -4.1), V(-3.9, -3.3), 0, 0.35), N, [(-0.1, 'run', 1.2), (0.2, 'attack1', 1.0)]),
                    act('goat', 2, V(-4.0, -2.3), S_, [(0, 'ready', 1.0), (0.52, 'hit', 0.8)]),
                    act('slerf', 0, go(V(LX, 0.9), V(LX, -0.4), 0, 1.1), S_, [(0, 'run', 1.1)]),
                    act('floki', 1, go(V(-5.6, -6.0), V(-5.5, -4.4), 0, 1.1), N, [(0, 'run', 1.3)]), act('walter', 0, go(V(-3.3, -6.3), V(-3.5, -4.7), 0, 1.1), N, [(-0.1, 'run', 1.3)]),
                    act('swordcat', 1, go(V(-4.5, -6.6), V(-4.6, -5.0), 0, 1.1), N, [(-0.2, 'run', 1.3)])],
                   [('flash', 0.46, V(LX, -2.75, 1.1), 9000), ('burst', 0.46, V(LX, -2.75), 40, 1.6, 0.04), ('ring', 0.46, V(LX, -2.75, 0.9), 1.6),
                    ('burst', 0.58, V(-6.0, -2.6), 24, 1.2, 0.035), ('burst', 0.54, V(-4.0, -2.8), 24, 1.2, 0.035), tracers(22, 5, 1.0)], slow=0.3, clock='0:20', name='clash'))
    # 8. Riding the shell in: over the bridge, over the fight, down onto our second line.
    E0 = V(-2.6, 11.0, 2.2); B3 = B.to_3d() + V(0, 0, 0.3); UL = 1.3
    shell = lambda u: E0.lerp(B3, clamp(u / UL)) + V(0, 0, 6.0 * sn(PI * clamp(u / UL)))
    SH.append(shot(15.6, 17.4, lambda k, u: dict(pos=shell(u - 0.07) + V(0.15, 0, 0.5), tgt=shell(u + 0.1) + V(0, 0, -0.35), fov=58, fstop=4.0, focus=3.0, shake=0.035),
                   [act(*BRO, V(LX, -3.25), N, [(0, 'attack2', 1.0), (0.8, 'attack1', 1.0)]), act('goat', 0, V(LX, -2.2), S_, [(0.1, 'attack1', 1.0), (0.9, 'attack2', 1.0)]),
                    act('goat', 1, V(-6.0, -2.3), S_, [(0, 'attack1', 0.9)]), act('goat', 2, V(-4.0, -2.3), S_, [(0.3, 'attack2', 1.0)]), act('floki', 1, V(-6.0, -3.3), N, [(0.1, 'attack1', 1.0)]),
                    act('slerf', 0, V(LX, -0.4), S_, [(0, 'walk', 1.0)]), act('goat', 3, V(-5.6, 1.6), S_, [(0, 'run', 1.0)]), act('goat', 4, V(-4.4, 2.8), S_, [(-0.2, 'run', 1.0)])] +
                   [act(k, i, B + V(sn(a), math.cos(a)) * 1.0, N, [(-0.3 * j, 'ready', 1.0)], pose=lambda u, j=j: {'Head': (-24 * ease(ramp(u, 0.7 + 0.05 * j, 1.0)), 0, 0)})
                    for j, (k, i, a) in enumerate([('swordcat', 2, 0.3), ('walter', 1, 1.4), ('toshi', 1, 2.5), ('floki', 2, 3.6), ('swordcat', 3, 4.9)])] +
                   [act(*ME, V(-4.2, -5.6), N, [(0, 'ready', 1.0)])],
                   [('shell', shell, UL), tracers(20, 33, 1.3), ('boom', 0.2, V(-7.4, 3.0, 0.3), 1.4)], slow=0.7, clock='0:18', name='shell'))
    # 9. The blast.
    ring = [('swordcat', 2, 0.3), ('walter', 1, 1.4), ('toshi', 1, 2.5), ('floki', 2, 3.6), ('swordcat', 3, 4.9)]
    blown = [thrown(k, i, B + V(sn(a), math.cos(a)) * 1.0, B + V(sn(a), math.cos(a)) * 3.0, 0.12, 0.56, 1.7 + 0.3 * sn(a * 3), 1.0 + 0.3 * j, pre='ready', seed=j + 1) for j, (k, i, a) in enumerate(ring)]
    blown.append(thrown(*ME, V(-4.2, -5.6), Q + V(0, 0.2), 0.12, 0.58, 1.3, 0.75, pre='ready', seed=9))
    blown.append(thrown(*BRO, V(-4.3, -3.5), V(-2.5, -5.4), 0.13, 0.56, 1.5, 1.0, pre='attack1', seed=6))
    SH.append(shot(17.4, 19.4, lambda k, u: dict(pos=V(-0.9, -9.6, 3.3 - 0.4 * k), tgt=B.to_3d() + V(0, 0, 0.7), fov=42, fstop=4.0, shake=0.01 + 0.09 * (0.1 < u < 0.4)),
                   blown + [act('goat', 0, V(LX, -2.2), S_, [(0, 'attack1', 0.9)]), act('goat', 1, V(-6.0, -2.4), S_, [(0, 'run', 1.0)]), act('goat', 2, V(-4.0, -2.3), S_, [(0, 'attack2', 0.9)])],
                   [('boom', 0.12, B.to_3d() + V(0, 0, 0.5), 2.6), ('ring', 0.12, B.to_3d() + V(0, 0, 0.15), 4.5), ('burst', 0.12, B, 70, 2.6, 0.05), ('flash', 0.12, B.to_3d() + V(0, 0, 1.0), 30000),
                    tracers(16, 6, 0.8)], slow=0.35, clock='0:17', name='blast'))
    # 10. First person again: deaf, the world tilted and soft. Left: one goes down. Right: its brother crawls to it.
    fires = [('boom', -0.4, V(-6.6, -3.8, 0.3), 1.1), ('boom', 0.3, V(-1.6, -2.2, 0.3), 1.4)]
    SH.append(shot(19.4, 21.2, pov_cam(Q, -28, 15), [me_prone(Q),
                   act('walter', 2, V(-5.5, -5.5), N, [(0, 'ready', 1.0), (0.3, 'hit', 0.7), (0.5, 'die', 1.0)]), act('goat', 3, go(V(-5.6, -3.9), V(-5.6, -4.7), 0, 0.3), S_, [(-0.2, 'run', 1.1), (0.05, 'attack1', 1.0)]),
                   act('swordcat', 2, V(-6.3, -6.9), N, [], rx=-PI / 2, pose=limp(2)), act('toshi', 1, V(-5.0, -6.5), N, [], rx=-PI / 2, z=0.05, pose=limp(5))],
                   fires + [tracers(14, 7, 0.8), ('burst', 0.33, V(-5.5, -5.3), 22, 1.0, 0.035)], slow=0.4, pov=1.0, name='pov_left'))
    cp0, cp1 = V(-2.4, -5.5), V(-2.95, -6.5)
    SH.append(shot(21.2, 23.4, pov_cam(Q, 30, -13), [me_prone(Q),
                   act(*BRO, go(cp0, cp1, 0, 0.62), hd(Q - cp0), [], rx=math.radians(84), pose=crawl(0.58)),
                   act('slerf', 1, V(-2.2, -3.4), S_, [(0.02, 'attack1', 1.0)]),
                   thrown('walter', 0, V(-2.9, -4.2), V(-4.2, -5.4), 0.5, 0.5, 1.2, 0.8, 'attack1', 4), thrown('swordcat', 1, V(-1.7, -4.5), V(-0.9, -6.2), 0.5, 0.5, 1.4, 1.0, 'attack1', 6)],
                   [('ring', 0.5, V(-2.2, -4.1, 0.12), 3.0), ('burst', 0.5, V(-2.2, -4.1), 40, 1.8, 0.04), ('flash', 0.5, V(-2.2, -4.1, 0.8), 9000), tracers(12, 8, 0.9), ('boom', 0.1, V(-0.4, -1.0, 0.3), 1.3)],
                   slow=0.4, pov=1.0, name='pov_right'))
    # 11. Its brother. A paw held up to it; then the paw falls.
    fd = V(1.0, 0.22).normalized(); Bf = Q + V(1.95, 0.95); gone = lambda u: ease(ramp(u, 0.85, 1.08))
    hand = lambda u: Q.to_3d() + V(0.82, 0.62, 0.22 + 0.36 * (1 - gone(u)))
    def bro(u): tr = 3 * sn(u * 40) * (1 - gone(u)); return {'LeftArm': (8 * gone(u) + tr, 0, 80 * (1 - gone(u))), 'RightArm': (34, 0, -6), 'Head': (lerp(-20, 14, gone(u)), 0, 0),
                     'LeftUpLeg': (10, 0, 12), 'RightUpLeg': (-5, 0, -8), 'LeftLeg': (-22, 0, 0)}
    def bcam(k, u):
        c = Q.to_3d() + V(1.25 - 0.12 * k, 2.05, 0.26); me = Q.to_3d() + V(0, 0.75, 0.42)
        return dict(pos=c, tgt=hand(u).lerp(me, 0.3 + 0.35 * ease(ramp(u, 1.05, 1.4))), fov=30, fstop=1.4, focus=lerp((c - hand(u)).length, (c - me).length, ease(ramp(u, 1.0, 1.35))), shake=0.004)
    propped = lambda u: {**prone(u, 2.5, 1.0, 0.8), 'Head': (-34, 0, 0), 'Neck': (-12, 0, 0)}
    SH.append(shot(23.4, 26.4, bcam, [act(*ME, Q, hd(V(0.5, 1)), [], rx=math.radians(62), pose=propped),
                   act(*BRO, Bf, hd(fd), [], rx=-PI / 2, z=0.04, pose=bro), act('toshi', 1, V(-5.0, -6.5), N, [], rx=-PI / 2, z=0.05, pose=limp(5))],
                   [tracers(10, 9, 1.5), ('boom', 0.5, V(-7.4, -3.0, 0.3), 1.2)], slow=0.5, pov=0.2, sub=(1.3, 2.9, '...GO.'), name='brother'))
    # 12. Rage. Its face; then it gets up.
    up = lambda u: ease(ramp(u, 0.6, 1.35)); face = lambda u: Q.to_3d() + V(0.2 * (1 - up(u)), 0.5 * (1 - up(u)), 0.5 + 0.55 * up(u))
    SH.append(shot(26.4, 29.0, lambda k, u: dict(pos=face(u) + V(0.18, 1.25 - 0.3 * ease(ramp(u, 0, 0.6)) + 0.9 * up(u), -0.12), tgt=face(u), fov=lerp(15, 30, up(u)), fstop=2.0,
                                                 shake=0.004 + 0.03 * (1.2 < u < 1.42)),
                   [act(*ME, Q, lambda u: lerp(hd(V(0.5, 1)), N, up(u)), [], rx=lambda u: math.radians(62) * (1 - up(u)),
                        pose=lambda u: {**prone(u, 4.0 * (1 - up(u)) + 1.0, 1 - up(u), 0.8), 'Head': (-34 * (1 - up(u)), 0, 0), 'Spine': (20 * sn(PI * up(u)), 0, 0), 'Spine1': (16 * sn(PI * up(u)), 0, 0),
                                        'RightArm': (lerp(-20, 55, up(u)) if up(u) > 0 else prone(u, 0, 1.0, 0.8)['RightArm'][0], 0, 0), 'LeftArm': (lerp(-20, 62, up(u)) if up(u) > 0 else prone(u, 0, 1.0, 0.8)['LeftArm'][0], 0, 0)}),
                    act(*BRO, Bf, hd(fd), [], rx=-PI / 2, z=0.04, pose=lambda u: bro(9.0))],
                   [('aura', lambda u: face(u) + V(0.5, 0.9, 0.2), 260, 0.25), ('ring', 1.3, Q.to_3d() + V(0, 0, 0.2), 3.2), ('burst', 1.3, Q, 50, 1.6, 0.03), ('flash', 1.3, Q.to_3d() + V(0, 0.6, 0.8), 6000), tracers(8, 10, 1.6)],
                   slow=0.6, clock='0:12', name='rage'))
    # 13. SLERF breaks what is left of the line.
    SH.append(shot(29.0, 31.2, lambda k, u: dict(pos=V(-4.5 + 0.2 * k, -6.9, 0.16), tgt=V(LX, -3.2, 1.3), fov=36, fstop=2.8, shake=0.01 + 0.08 * (0.55 < u < 0.8)),
                   [act('slerf', 0, V(LX, -3.2), S_, [(0.03, 'attack1', 1.0)]),
                    thrown('swordcat', 4, V(-5.9, -4.0), V(-6.9, -6.4), 0.56, 0.5, 1.5, 1.0, 'attack1', 2), thrown('walter', 3, V(-4.0, -3.7), V(-2.6, -5.2), 0.56, 0.52, 1.7, 1.25, 'attack1', 5),
                    thrown('floki', 1, V(-6.2, -3.3), V(-7.2, -5.4), 0.58, 0.55, 1.3, 0.75, 'attack2', 8),
                    act('goat', 1, V(-6.3, -2.2), S_, [(0, 'ready', 1.0)]), act('goat', 2, V(-3.8, -2.0), S_, [(-0.3, 'ready', 1.0)])],
                   [('ring', 0.56, V(LX, -3.9, 0.12), 3.6), ('burst', 0.56, V(LX, -3.9), 60, 2.2, 0.045), ('flash', 0.56, V(LX, -3.9, 0.8), 14000), tracers(12, 11, 1.0)], slow=0.45, clock='0:10', name='slam'))
    # 14. It runs.
    r0, r1 = V(-4.4, -8.2), V(-4.9, -3.7)
    SH.append(shot(31.2, 33.4, lambda k, u: dict(pos=r0.lerp(r1, ramp(u, 0, 2.2)).to_3d() + V(0.28, 2.3, 0.28), tgt=r0.lerp(r1, ramp(u, 0, 2.2)).to_3d() + V(0, 0, 0.6), fov=36, fstop=2.0, shake=0.035),
                   [act(*ME, go(r0, r1, 0, 2.2), hd(r1 - r0), [(0, 'run', 1.5)], pose=lambda u: {'Spine': (10, 0, 0)}),
                    act('slerf', 0, V(-6.4, -5.2), hd(V(1, -0.6)), [(0, 'attack1', 1.0), (1.2, 'idle', 1.0)]), act('goat', 2, V(-3.4, -4.6), S_, [(0.9, 'attack1', 1.0)]),
                    act('swordcat', 4, V(-6.9, -6.4), N, [], rx=-PI / 2, pose=limp(2))],
                   [('aura', lambda u: r0.lerp(r1, ramp(u, 0, 2.2)).to_3d() + V(0, 0.5, 0.7), 200, -1.0), ('boom', 0.45, V(-6.4, -7.0, 0.4), 1.7), ('boom', 1.25, V(-3.1, -5.6, 0.4), 1.9),
                    ('burst', 0.45, V(-6.4, -7.0), 30, 1.6, 0.04), ('burst', 1.25, V(-3.1, -5.6), 30, 1.6, 0.04), ('flash', 1.25, V(-3.1, -5.6, 1.0), 16000), tracers(26, 12, 2.2)], clock='0:07', name='run'))
    b0, b1 = V(LX, -1.5), V(LX, 1.5)
    hp = lambda u: b0.lerp(b1, ramp(u, 0, 1.1)) + V(0.28 * sn(u * 7), 0)
    SH.append(shot(33.4, 35.6, lambda k, u: dict(pos=V(-1.5, -0.7 + 0.5 * k, 0.5), tgt=hp(u).to_3d() + V(0, 0.3, 0.6), fov=40, fstop=2.8, shake=0.02 + 0.07 * (0.36 < u < 0.6)),
                   [act(*ME, hp, N, [(0, 'run', 1.5)], pose=lambda u: {'Spine': (12, 0, 0)}),
                    act('goat', 1, V(-5.75, -0.2), hd(V(0.5, -1)), [(0.05, 'attack1', 1.0)]), act('goat', 2, V(-4.3, 0.95), hd(V(-0.5, -1)), [(0.45, 'attack2', 1.0)])],
                   [('aura', lambda u: hp(u).to_3d() + V(0.5, 0.2, 0.7), 200, -1.0), ('boom', 0.36, V(-3.2, 0.2, 0.0), 2.0), ('burst', 0.36, V(-3.2, 0.2), 60, 2.6, 0.045), ('flash', 0.36, V(-3.2, 0.2, 0.8), 22000),
                    ('ring', 0.36, V(-3.2, 0.2, -0.2), 2.6), tracers(18, 13, 1.1)], slow=0.5, clock='0:04', name='bridge'))
    # 15. The leap: time all but stops, and the camera goes round it.
    j0, j1 = V(LX, 1.9), BOSS + V(0, -0.55); UH = 0.71
    jp = lambda u: j0.lerp(j1, ramp(u, 0, UH)); jz = lambda u: 1.75 * sn(PI * 0.78 * ramp(u, 0, UH))
    def orbit(k, u):
        a = math.radians(205 + 125 * ease(k)); c = jp(u).to_3d() + V(0, 0, jz(u) + 0.55)
        return dict(pos=c + V(math.cos(a) * 1.9, sn(a) * 1.9, -0.25 + 0.3 * k), tgt=c + V(0, 0.25, 0), fov=38, fstop=2.0, shake=0.004)
    SH.append(shot(35.6, 39.2, orbit, [act(*ME, jp, N, [], z=jz, rx=lambda u: math.radians(lerp(-14, 26, ramp(u, 0, UH))), pose=leap(UH + 0.02)),
                   act('goat', 0, BOSS, S_, [(-0.5, 'ready', 0.8)], pose=lambda u: {'Head': (-22 * ease(ramp(u, 0.2, 0.6)), 0, 0), 'Spine2': (-10 * ease(ramp(u, 0.2, 0.6)), 0, 0)}),
                   act('goat', 3, V(-6.4, 5.4), S_, [(0, 'idle', 1.0)]), act('goat', 4, V(-6.0, 6.6), S_, [(-1, 'idle', 1.0)])],
                   [('aura', lambda u: jp(u).to_3d() + V(0.3, -0.5, jz(u) + 0.6), 240, -1.0), tracers(30, 14, 0.8), ('boom', 0.1, V(-8.6, 5.0, 0.4), 1.3), ('boom', 0.4, V(-0.8, 7.6, 0.4), 1.3)],
                   slow=0.2, clock='0:02', name='leap'))
    # 16. It lands.
    fallk = lambda u: ease(ramp(u, 0.1, 0.62))
    SH.append(shot(39.2, 41.0, lambda k, u: dict(pos=V(-2.2 - 0.2 * k, 3.1, 0.3), tgt=V(LX, 4.35 + 0.3 * fallk(u), 0.6 - 0.15 * fallk(u)), fov=44, fstop=2.8, shake=0.01 + 0.1 * (0.06 < u < 0.3)),
                   [act(*ME, go(j1, j1 + V(0, 0.1), 0, 0.3), N, [(0.16, 'ready', 1.0)], z=lambda u: 1.0 * (1 - ramp(u, 0.0, 0.16)) ** 2,
                        pose=lambda u: {k_: tuple(v * (1 - ease(ramp(u, 0.1, 0.3))) for v in val) for k_, val in leap(0.06)(u).items()}),
                    act('goat', 0, go(BOSS, BOSS + V(0, 0.9), 0.08, 0.6), S_, [(0.06, 'hit', 0.8)], rx=lambda u: -math.radians(88) * fallk(u), z=lambda u: 0.25 * sn(PI * fallk(u)),
                        pose=then(0.08, lambda u: {}, flail(4), 0.05)),
                    act('goat', 3, V(-6.4, 5.4), S_, [(0.3, 'lose', 1.2)]), act('goat', 4, V(-6.0, 6.6), S_, [(0.35, 'lose', 1.2)])],
                   [('flash', 0.07, V(LX, 4.0, 1.2), 40000), ('ring', 0.07, V(LX, 4.0, 0.8), 3.4), ('burst', 0.07, V(LX, 4.0), 60, 2.4, 0.045), ('burst', 0.62, BOSS + V(0, 1.2), 40, 1.3, 0.04)],
                   slow=0.6, clock='0:01', name='strike'))
    # 17. Their tower goes.
    T3 = TOWER.to_3d(); hero = j1 + V(0, 0.1)
    SH.append(shot(41.0, 44.2, lambda k, u: dict(pos=V(-3.9, 1.9, 0.55 + 0.25 * k), tgt=V(-0.9, 10.5, 2.0), fov=33, fstop=5.6, focus=14.0, shake=0.012 + 0.06 * (0.1 < u < 1.0)),
                   [act(*ME, hero, hd(TOWER - j1), [(0, 'ready', 0.7)]), act('goat', 0, BOSS + V(0, 0.9), S_, [], rx=-math.radians(88), pose=limp(4)),
                    act('goat', 3, V(-6.4, 5.4), S_, [(-0.3, 'lose', 1.2)]), act('goat', 4, V(-6.0, 6.6), S_, [(-0.25, 'lose', 1.2)])],
                   [('boom', 0.1, T3 + V(-0.8, -0.9, 1.4), 2.6), ('boom', 0.42, T3 + V(0.9, -0.6, 2.6), 3.2), ('boom', 0.75, T3 + V(0, -0.8, 1.0), 3.8), ('boom', 1.1, T3 + V(-0.5, -0.4, 3.2), 2.6),
                    ('flash', 0.42, T3 + V(0, -2.5, 2.5), 250000), ('burst', 0.42, TOWER + V(0, -1.2), 70, 3.4, 0.07), ('ring', 0.42, T3 + V(0, 0, 0.3), 9.0), ('swap', 0.45), tracers(10, 15, 1.6)],
                   slow=0.5, clock='0:00', name='tower'))
    # 18. After. The sword goes up against the burning sky.
    SH.append(shot(44.2, 48.2, lambda k, u: dict(pos=V(-6.7 + 0.2 * k, 0.0, 0.4 + 1.1 * ease(k)), tgt=V(-1.8, 9.0, 1.7 + 0.3 * k), fov=40, fstop=4.0, focus=3.2, shake=0.004),
                   [act(*ME, hero, hd(TOWER - hero), [(0, 'idle', 1.0)], pose=arm_up(1.5, 9.0)),
                    act('toshi', 2, go(V(-2.4, 1.0), V(-2.5, 3.2), 0, 2.0), N, [(0, 'walk', 1.0), (2.0, 'win', 1.0)]),
                    act('walter', 2, go(V(-3.4, 0.6), V(-3.3, 2.4), 0, 1.7), N, [(0, 'walk', 1.1), (1.7, 'win', 1.0)]),
                    act('floki', 3, go(V(-4.3, 0.0), V(-4.4, 1.9), 0.2, 2.2), N, [(0, 'walk', 1.0), (2.2, 'win', 1.0)]),
                    act('goat', 0, BOSS + V(0, 0.9), S_, [], rx=-math.radians(88), pose=limp(4))],
                   [('fire', T3 + V(0, -0.8, 1.6), 2.4), ('fire', T3 + V(1.0, -0.4, 2.8), 1.8)], name='after'))
    return SH


# ------------------------------------------------------------------ effects
MATS = {}
def fx_mats():
    def soft(name, emit):
        """A ragged blob: object colour = tint, object alpha = how much of it is left (it tears into holes as it dies)."""
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; Lk = nt.links.new
        oi = nt.nodes.new('ShaderNodeObjectInfo'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.3
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.7; nz.inputs['Detail'].default_value = 6; nz.inputs['Roughness'].default_value = 0.65
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); Lk(tc.outputs['Object'], mp.inputs[0]); Lk(oi.outputs['Random'], mp.inputs['Location']); Lk(mp.outputs[0], nz.inputs['Vector'])
        def M(op, a, b_, c=None, cl=False):
            n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = cl
            for i, v in enumerate((a, b_, c)):
                if v is None: continue
                if isinstance(v, (int, float)): n.inputs[i].default_value = v
                else: Lk(v, n.inputs[i])
            return n.outputs[0]
        body = M('MULTIPLY_ADD', M('ADD', nz.outputs['Fac'], M('MULTIPLY_ADD', oi.outputs['Alpha'], 0.75, -0.95)), 5.0, 0.0, cl=True)      # noise against a threshold that the alpha moves
        edge = M('MULTIPLY_ADD', lw.outputs['Facing'], -2.2, 1.25, cl=True); al = M('MULTIPLY', body, edge, cl=True)
        b.inputs['Roughness'].default_value = 1.0
        if emit:
            cr = nt.nodes.new('ShaderNodeValToRGB'); e = cr.color_ramp.elements; e[0].position = 0.25; e[0].color = (0.25, 0.01, 0.0, 1); e[1].position = 0.8; e[1].color = (1.0, 0.75, 0.3, 1)
            mid = cr.color_ramp.elements.new(0.52); mid.color = (1.0, 0.22, 0.02, 1)
            Lk(M('MULTIPLY', M('ADD', nz.outputs['Fac'], 0.15), M('MINIMUM', oi.outputs['Alpha'], 1.3), cl=True), cr.inputs[0])
            Lk(cr.outputs[0], b.inputs['Emission Color']); Lk(cr.outputs[0], b.inputs['Base Color']); Lk(M('MULTIPLY', oi.outputs['Alpha'], emit), b.inputs['Emission Strength']); Lk(al, b.inputs['Alpha'])
        else:
            Lk(oi.outputs['Color'], b.inputs['Base Color']); Lk(M('MULTIPLY', al, 0.8), b.inputs['Alpha'])
        return m
    MATS['fire'] = soft('fx_fire', 5.0); MATS['smoke'] = soft('fx_smoke', 0.0)
    MATS['snow'] = sets.flat('fx_dust', (0.3, 0.2, 0.15), 0.9); MATS['dirt'] = sets.flat('fx_dirt', (0.07, 0.05, 0.045), 0.9)
    for nm, col in (('tr_ours', (0.5, 0.9, 1.0)), ('tr_theirs', (1.0, 0.3, 0.12)), ('ringm', (1.0, 0.85, 0.7))):
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
            blobs = [(obj('ball', 'fire'), Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0, 1))) * 0.35 * size, rng.uniform(0.6, 1.0)) for _ in range(9 if kind == 'boom' else 5)]
            smoke = [(obj('ball', 'smoke'), Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.2, 1))) * 0.4 * size, rng.uniform(0.7, 1.2), rng.uniform(0, 1)) for _ in range(9)]
            lt = bpy.data.objects.new('boomL', bpy.data.lights.new('boomL', 'POINT')); bpy.context.scene.collection.objects.link(lt); lt.data.color = (1.0, 0.5, 0.18)
            lt.data.shadow_soft_size = 0.5 * size; lt.location = p + Vector((0, 0, 0.5 * size)); lt.data.energy = 0; L.append(lt)
            for o, *_ in blobs + smoke: life(o)
            K.add(lt.data, 'energy', 0, f0 - 1, 0.0); K.add(lt.data, 'energy', 0, f1, 0.0)
            for f in frames:
                a = uof(f) - u0
                if kind == 'fire':
                    for j, (o, off, s) in enumerate(blobs):
                        fl = 0.75 + 0.25 * sn(uof(f) * 13 + j * 2); key3(K, o, 'location', f, p + off * 0.6 + Vector((0, 0, 0.25 * size * sn(uof(f) * 5 + j)))); key3(K, o, 'scale', f, [size * 0.4 * s * fl] * 3)
                        key3(K, o, 'color', f, (1.0, 0.42, 0.1, 1.05 * fl))
                    for j, (o, off, s, ph) in enumerate(smoke):
                        c = (uof(f) * 0.22 + ph) % 1.0; key3(K, o, 'location', f, p + off + Vector((0.9 * c, 0.3 * c, 0.6 * size + 5.0 * c))); key3(K, o, 'scale', f, [size * (0.35 + 0.9 * c) * s] * 3)
                        key3(K, o, 'color', f, (0.07, 0.06, 0.07, 0.3 + 0.75 * sn(PI * c)))
                    K.add(lt.data, 'energy', 0, f, 140 * size * (0.8 + 0.2 * sn(uof(f) * 17))); continue
                if a < 0:
                    for o, *_ in blobs + smoke: key3(K, o, 'scale', f, (0, 0, 0))
                    K.add(lt.data, 'energy', 0, f, 0.0); continue
                g = 1 - math.exp(-a * 9)
                for o, off, s in blobs:
                    key3(K, o, 'location', f, p + off * (0.5 + 1.2 * g) + Vector((0, 0, 0.6 * size * g + 0.8 * a))); key3(K, o, 'scale', f, [0.42 * size * s * (0.3 + 0.7 * g + 0.25 * a)] * 3)
                    h = math.exp(-a * 2.6); key3(K, o, 'color', f, (1.0, 0.4, 0.1, 1.5 * h))
                for o, off, s, ph in smoke:
                    key3(K, o, 'location', f, p + off * (0.6 + 1.6 * g) + Vector((0.3 * a, 0.1 * a, 0.5 * size * g + 1.1 * a))); key3(K, o, 'scale', f, [0.42 * size * s * (0.3 + 0.8 * g + 0.4 * a)] * 3)
                    key3(K, o, 'color', f, (0.07, 0.065, 0.07, 1.05 * ramp(a, 0.04, 0.3) * max(0.0, 1 - a / 3.5)))
                K.add(lt.data, 'energy', 0, f, 900 * size * size * math.exp(-a * 7))
        elif kind == 'shell':
            _, fn, ul = e; head = obj('ball', 'fire'); life(head); trail = [obj('ball', 'smoke') for _ in range(14)]
            for o in trail: life(o)
            for f in frames:
                w = uof(f); on = w <= ul
                key3(K, head, 'location', f, fn(w)); key3(K, head, 'scale', f, [0.22 if on else 0] * 3); key3(K, head, 'color', f, (1, 0.5, 0.1, 1.4))
                for j, o in enumerate(trail):
                    wj = w - 0.035 * (j + 1); key3(K, o, 'location', f, fn(max(0.0, wj)) + Vector((0, 0, 0.02 * j)))
                    key3(K, o, 'scale', f, [0.16 + 0.05 * j if (on and wj > 0) else 0] * 3); key3(K, o, 'color', f, (0.08, 0.07, 0.07, 1.1 - 0.05 * j))
        elif kind == 'aura':
            _, fn, en, u_on = e; lt = bpy.data.objects.new('aura', bpy.data.lights.new('aura', 'POINT')); bpy.context.scene.collection.objects.link(lt); L.append(lt)
            lt.data.color = (1.0, 0.62, 0.16); lt.data.shadow_soft_size = 0.25; lt.data.energy = 0; K.add(lt.data, 'energy', 0, f0 - 1, 0.0); K.add(lt.data, 'energy', 0, f1, 0.0)
            for f in frames: key3(K, lt, 'location', f, fn(uof(f))); K.add(lt.data, 'energy', 0, f, en * ease(ramp(uof(f), u_on, u_on + 0.5)) * (0.85 + 0.15 * sn(uof(f) * 23)))
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
    sm = nt.nodes.new('CompositorNodeMath'); sm.operation = 'MULTIPLY_ADD'; sm.inputs[1].default_value = -0.5; sm.inputs[2].default_value = 0.92; nt.links.new(pk.outputs[0], sm.inputs[0])
    hs = nt.nodes.new('CompositorNodeHueSat'); nt.links.new(mx.outputs['Image'], hs.inputs['Image']); nt.links.new(sm.outputs[0], hs.inputs['Saturation']); nt.links.new(hs.outputs['Image'], ld.inputs['Image'])
    A = arena_dump(); fx_mats(); robjs = A['towers']['en_king_ruin'][1]
    bg = sc.world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.10, 0.035, 0.04, 1); bg.inputs[1].default_value = 1.0
    next(n for n in nt.nodes if n.bl_idname == 'CompositorNodeMixRGB' and n.inputs[2].default_value[2] > 0.8 and not n.inputs[2].links).inputs[2].default_value = (0.5, 0.26, 0.16, 1)   # dust in the low sun
    K = rigctl.Keys(); L = []; rng = random.Random(4)
    # cast: one unit per (kind, index), hidden whenever it is not in the shot
    C = {}; vis = {}; poses = {}
    def unit(kind, i):
        if (kind, i) not in C: C[(kind, i)] = WUnit(kind, f'{kind}{i}'); vis[(kind, i)] = set(); poses[(kind, i)] = {}
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
        sh['fx'] += [('fire', V(x, y, 0.25), sz) for x, y, sz in ((-7.6, -6.6, 0.9), (-1.9, -2.6, 1.0), (-7.4, 3.2, 0.9), (-2.4, 6.6, 1.1), (-1.0, -9.4, 0.8))]
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
        for f in range(1, NF + 1):
            for o in u.parts: K.add(o, 'hide_render', 0, f, f not in vis[key])
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
    sun = light('sun', 'SUN', (0, 0, 10), 4.2, (1.0, 0.5, 0.26)); sun.rotation_euler = Euler((math.radians(79), 0, math.radians(152))); sun.data.angle = 0.05     # low, behind their lines
    light('sky_fill', 'AREA', (0, -26, 14), 520, (0.55, 0.45, 0.85), 20, (0, 0, 0))
    rim = light('rim', 'SPOT', (0, 0, 5), 900, (1.0, 0.62, 0.36), 0.25); rim.data.spot_size = math.radians(46); rim.data.spot_blend = 0.6; rim.rotation_mode = 'QUATERNION'
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
        K2.add(nt, 'nodes["povk"].outputs[0].default_value', 0, f, povf[f]); K2.add(nt, 'nodes["mistk"].outputs[0].default_value', 0, f, 0.42)
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
                   fx=[dict(kind=e[0], t=s['t0'] + e[1] / s['slow'], size=e[3] if e[0] == 'boom' else 1.0) for s in SH for e in s['fx'] if e[0] in ('boom', 'flash', 'ring', 'swap')],
                   subs=[(s['t0'] + s['sub'][0], s['t0'] + s['sub'][1], s['sub'][2]) for s in SH if s['sub']]),
              open(os.path.join(os.environ['W'], 'timeline.json'), 'w'), indent=1)
    sc.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False); print('SAVED', arg('--out'), NF, 'frames')


if __name__ == '__main__':
    main()
