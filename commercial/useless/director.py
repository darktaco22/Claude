"""NO UTILITY (a Meme Royale short): builds the scene and keys every frame.
blender -b -P director.py -- --out scene.blend [--res 1080]
Env: PH (Poly Haven folder), GAME (the game's assets: units/, arena/, arenas/), W (work folder: timeline.json goes here).
Every character is the game's own model with its own clips (game.Unit); nothing is modified."""
import bpy, sys, os, math, json, random
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'degens'), os.path.join(H, '..', 'whale')]
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view
import rigctl, game, sets
from sets import TX, GATE_Y, TH

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return ARGS[ARGS.index(k) + 1] if k in ARGS else d
FPS = 30; END = 36.0; NF = int(END * FPS)
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
lerp = lambda a, b, k: a + (b - a) * k
def ramp(t, a, b): return clamp((t - a) / (b - a))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
def F(t): return int(round(t * FPS)) + 1
def T(f): return (f - 1) / FPS
def V(*a): return Vector(a)

# ------------------------------------------------------------------ the edit (seconds)
CUTS = [3.0, 4.0, 5.0, 6.0, 7.0, 7.66, 8.33, 9.0, 11.0, 13.0, 14.6, 16.4, 18.0, 19.4, 21.0, 21.8, 22.75, 23.95, 24.85, 26.0, 27.2, 28.0, 32.0]
PICKS = [('giga', 3.0), ('whale', 5.0), ('bonk', 7.0), ('cate', 7.66), ('walter', 8.33)]
NIGHT = 9.0              # the gate light goes cold: nobody is coming back for them
ARENA = (11.0, 14.6)     # the final match, part 1 (14.6-16.4 is the hand: arena out of focus behind the UI)
CHOSEN = 16.4            # the light finds the coins
DEPLOY = 18.0
CHARGE = 19.4; IMPACT = 20.1
STAND = 21.8
HORN = 26.0
VICTORY = (28.0, 32.0)   # UI over the blurred arena
MORNING = 32.0
# Gameplay cutaways: where each picked card goes (kind, the story time the cutaway comes in at, frames). They are extra
# frames after the film (scene time >= END), so the film's own frames stay as they are; edit.py splices them in.
INS = [('giga', 5.0, 45), ('whale', 7.0, 45), ('bonk', 7.66, 17), ('cate', 8.33, 17), ('walter', 9.0, 17)]
INS_T = [END + sum(n for _, _, n in INS[:i]) / FPS for i in range(len(INS))]
NFX = NF + sum(n for _, _, n in INS)
I_LAND = V(1.9, -5.4); I_GOAT = V(2.25, -2.7); I_QUICK = V(1.4, -6.4)


def ins_at(t):
    """(index, kind, seconds into it) when scene time t is inside a cutaway."""
    j = int(round(t * FPS)) - NF
    if j < 0: return None
    for i, (k, at, n) in enumerate(INS):
        if j < n: return i, k, j / FPS
        j -= n
    return None

# tunnel line-up (x offset from TX, y); heading pi = facing the gate (+Y)
LINE = dict(giga=(-0.85, 5.4), whale=(0.1, 8.3), bonk=(1.2, 4.4), cate=(-1.3, 2.3), walter=(1.05, 1.2))
COINS_T = [(0.75, -2.5), (1.4, -2.15), (0.2, -3.05), (1.2, -3.2)]           # coin 0 is our hero
COINS_M = [(0.35, 7.4), (1.0, 7.75), (-0.2, 6.85), (0.8, 6.7)]               # the next morning: at the front of the line
# arena
GOAT_PATH = [(11.6, V(-5.0, 4.5)), (14.6, V(-4.6, -1.6)), (18.0, V(-3.6, -4.4))]
COINS_A = [V(-2.25, -7.95), V(-2.95, -6.75), V(-3.4, -7.25), V(-2.45, -6.95)]
SIB_FLY = [None, V(-5.0, -6.2), V(-4.9, -8.6), V(-0.9, -6.3)]
HERO_KNOCK = V(-1.95, -9.1)
HIT2 = HERO_KNOCK + V(-0.2, -0.15); HIT3 = HERO_KNOCK + V(0.15, -0.35)
GOAT_STOP = V(-2.85, -7.1)


FALL0, FALL1 = 27.0, 27.85      # after the horn: it sways, and falls back into the snow


def fall_rx(t):
    k = ramp(t, FALL0, FALL1); a = -90.0 * k * k                       # gravity: slow, then all at once
    if t > FALL1: a = -90.0 + 5.0 * math.sin((t - FALL1) * 18) * math.exp(-(t - FALL1) * 7)   # a small bounce
    return math.radians(a)


def heading(d): return math.atan2(d.x, -d.y)       # facing(h) = (sin h, -cos h): heading 0 faces -Y


def setup_render(res):
    sc = bpy.context.scene; sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 12; sc.cycles.transmission_bounces = 2; sc.cycles.volume_bounces = 0
    sc.cycles.light_tree = True; sc.cycles.adaptive_threshold = 0.03
    sc.render.resolution_x = res * 9 // 16 if res != 1080 else 1080; sc.render.resolution_y = res * 16 // 9 if res != 1080 else 1920
    if res != 1080: sc.render.resolution_x, sc.render.resolution_y = res, res * 16 // 9
    sc.render.resolution_percentage = 100
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'START'   # no smear across cuts
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
    finish(sc)
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.0033, 0.074, 0.216, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    w.mist_settings.start = 9.0; w.mist_settings.depth = 42.0; w.mist_settings.falloff = 'QUADRATIC'


def finish(sc):
    """Compositor: soft bloom on the highlights, a hint of lens dispersion, a gentle vignette."""
    bpy.context.view_layer.use_pass_mist = True
    sc.use_nodes = True; nt = sc.node_tree; nt.nodes.clear()
    rl = nt.nodes.new('CompositorNodeRLayers'); out = nt.nodes.new('CompositorNodeComposite')
    gl = nt.nodes.new('CompositorNodeGlare'); gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'; gl.threshold = 0.85; gl.size = 8; gl.mix = -0.82
    ld = nt.nodes.new('CompositorNodeLensdist'); ld.inputs[1].default_value = 0.0; ld.inputs[2].default_value = 0.012
    em = nt.nodes.new('CompositorNodeEllipseMask'); em.width = 1.05; em.height = 0.92
    bl = nt.nodes.new('CompositorNodeBlur'); bl.use_relative = True; bl.factor_x = 0.35; bl.factor_y = 0.35; bl.filter_type = 'GAUSS'
    mr = nt.nodes.new('CompositorNodeMapRange'); mr.inputs['To Min'].default_value = 0.68; mr.inputs['To Max'].default_value = 1.0
    mx = nt.nodes.new('CompositorNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    L = nt.links.new
    # aerial haze in the arena (keyed off in the tunnel), then a gentle split-tone grade
    mk = nt.nodes.new('CompositorNodeValue'); mk.name = 'mistk'; mk.outputs[0].default_value = 0.0
    mm = nt.nodes.new('CompositorNodeMath'); mm.operation = 'MULTIPLY'; L(rl.outputs['Mist'], mm.inputs[0]); L(mk.outputs[0], mm.inputs[1])
    hz = nt.nodes.new('CompositorNodeMixRGB'); hz.inputs[2].default_value = (0.30, 0.50, 0.82, 1)
    L(mm.outputs[0], hz.inputs[0]); L(rl.outputs['Image'], hz.inputs[1])
    cb = nt.nodes.new('CompositorNodeColorBalance'); cb.correction_method = 'LIFT_GAMMA_GAIN'
    cb.lift = (0.97, 1.0, 1.04); cb.gamma = (1.0, 1.0, 1.0); cb.gain = (1.04, 1.0, 0.95)
    L(hz.outputs['Image'], gl.inputs['Image']); L(gl.outputs['Image'], cb.inputs['Image']); L(cb.outputs['Image'], ld.inputs['Image'])
    L(em.outputs['Mask'], bl.inputs['Image']); L(bl.outputs['Image'], mr.inputs['Value'])
    L(ld.outputs['Image'], mx.inputs[1]); L(mr.outputs['Value'], mx.inputs[2]); L(mx.outputs['Image'], out.inputs['Image'])


# ------------------------------------------------------------------ cast
def cast():
    C = {}
    for k in ('giga', 'whale', 'bonk', 'cate', 'walter'):
        C['t_' + k] = game.Unit(k, 't_' + k)
    for i in range(4): C[f't_coin{i}'] = game.Unit('useless', f't_coin{i}')
    C['goat'] = game.Unit('goat', 'goat')
    C['a_giga'] = game.Unit('giga', 'a_giga'); C['a_whale'] = game.Unit('whale', 'a_whale')
    for i in range(4): C[f'a_coin{i}'] = game.Unit('useless', f'a_coin{i}')
    for k, _, _ in INS: C['i_' + k] = game.Unit(k, 'i_' + k)
    C['i_goat'] = game.Unit('goat', 'i_goat')
    return C


def key_ctrl(K, u, f, loc, h, z=0.0, rx=0.0):
    K.add(u.ctrl, 'location', 0, f, loc.x); K.add(u.ctrl, 'location', 1, f, loc.y); K.add(u.ctrl, 'location', 2, f, z)
    K.add(u.ctrl, 'rotation_euler', 2, f, h); K.add(u.ctrl, 'rotation_euler', 0, f, rx)


def path_at(path, t):
    if t <= path[0][0]: return path[0][1]
    for (t0, p0), (t1, p1) in zip(path, path[1:]):
        if t <= t1: return p0.lerp(p1, (t - t0) / (t1 - t0))
    return path[-1][1]


def act(C, K):
    """Clip schedules (NLA) and per-frame positions for everyone."""
    # --- tunnel: the line-up. Each pick: the light lands, a beat, it walks out through the gate.
    for k, (x, y) in LINE.items():
        u = C['t_' + k]; tp = dict(PICKS)[k]
        walk_at = tp + 0.55
        ws = 1.25 if k in ('whale', 'giga') else 1.4
        u.play([(0, 'idle', 1.0, 20), (tp + 0.05, 'ready', 1.4, 1), (walk_at, 'walk', ws, 40, 0.15)])
        start = V(TX + x, y); gate = V(TX + x * 0.3, GATE_Y + 3.0)
        dist = (gate - start).length; speed = 2.0 if k == 'whale' else 2.3
        for f in range(1, NF + 1):
            t = T(f)
            if t < walk_at: p = start
            else: p = start.lerp(gate, clamp((t - walk_at) * speed / dist))
            key_ctrl(K, u, f, p, math.pi)
            gone = min([c for c in CUTS if c >= walk_at + 0.8] + [NIGHT])
            u.mesh.hide_render = t >= min(gone, walk_at + dist / speed); K.add(u.mesh, 'hide_render', 0, f, u.mesh.hide_render)
    # the coins: they bounce hopefully at every pick (less each time), slump at night, rise in the chosen light,
    # run for the gate; the next morning they stand first in line and the light finds them at once.
    hope = [(3.05, 1.5), (5.05, 1.3), (7.05, 1.1), (7.7, 1.0), (8.4, 0.9)]
    for i in range(4):
        u = C[f't_coin{i}']; d = 0.06 * i
        sch = [(0, 'idle', 1.0, 20)]
        for (tt, sp) in hope: sch += [(tt + d, 'ready', sp, 1, 0.1), (tt + d + 52 / 30 / sp * 0.6, 'idle', 1.0, 10, 0.25)]
        sch += [(NIGHT + 0.6 + d * 2, 'lose', 0.8, 1, 0.4)]
        sch += [(CHOSEN + 0.45 + d, 'ready', 1.0, 1, 0.3), (CHOSEN + 1.0 + d, 'run', 1.0, 10, 0.15)]
        sch += [(MORNING - 0.01, 'idle', 1.0, 3, 0.0), (MORNING + 1.0 + d, 'win', 1.0, 1, 0.15), (MORNING + 1.0 + d + 4.4, 'idle', 1.0, 3, 0.3)]
        u.play(sch)
        x, y = COINS_T[i]; start = V(TX + x, y); out = V(TX + x * 0.4, GATE_Y + 2.5)
        mx, my = COINS_M[i]; morning = V(TX + mx, my)
        for f in range(1, NF + 1):
            t = T(f)
            if t >= MORNING: p = morning; h = math.pi
            elif t >= CHOSEN + 1.0 + d: p = start.lerp(out, clamp((t - CHOSEN - 1.0 - d) * 3.2 / (out - start).length)); h = math.pi
            else:
                p = start; h = math.pi
                if CHOSEN <= t: h = math.pi                              # looking up into the light (the clip)
            key_ctrl(K, u, f, p, h)
    # --- arena: GIGA and The Whale fall; THE GOAT crosses the bridge and comes for our king.
    g = C['a_giga']; g.play([(0, 'hit', 1.0, 3), (11.6, 'die', 0.9, 1, 0.1)])
    w = C['a_whale']; w.play([(0, 'attack1', 0.8, 10), (12.25, 'hit', 1.0, 1, 0.05), (12.55, 'die', 0.85, 1, 0.1)])
    for f in range(1, NF + 1):
        key_ctrl(K, g, f, V(0.8, -4.6), heading(V(-0.3, 1))); key_ctrl(K, w, f, V(-2.6, -3.0), heading(V(-0.5, 1)))
    goat = C['goat']
    goat.play([(0, 'walk', 1.3, 60), (18.0, 'ready', 1.3, 1, 0.2), (CHARGE, 'run', 1.4, 6, 0.1), (IMPACT + 0.25, 'attack1', 1.0, 1, 0.1),
               (IMPACT + 1.0, 'idle', 1.0, 3, 0.3),
               (22.45, 'attack1', 1.15, 1, 0.08), (23.3, 'idle', 1.0, 3, 0.3), (24.55, 'attack2', 1.15, 1, 0.08), (25.4, 'idle', 1.0, 3, 0.3),
               (25.75, 'attack1', 0.9, 1, 0.08), (HORN + 0.5, 'lose', 1.0, 1, 0.5)])
    goat_stop_dir = GOAT_STOP - GOAT_PATH[-1][1]
    for f in range(1, NF + 1):
        t = T(f)
        if t < 18.0: p = path_at(GOAT_PATH, t); h = heading(GOAT_PATH[-1][1] - GOAT_PATH[0][1])
        elif t < CHARGE: p = GOAT_PATH[-1][1]; h = heading(goat_stop_dir)
        else: p = GOAT_PATH[-1][1].lerp(GOAT_STOP, ease(ramp(t, CHARGE, IMPACT + 0.1))); h = heading(goat_stop_dir)
        if t > HORN: p = GOAT_STOP                       # frozen by the horn
        key_ctrl(K, goat, f, p, h)
    # --- the coins in the arena. Deploy (they drop from the sky), the charge scatters three, the hero stands.
    for i in range(4):
        u = C[f'a_coin{i}']; d = 0.05 * i
        if i == 0:
            sch = [(0, 'ready', 1.0, 1), (DEPLOY + 0.35, 'ready', 1.0, 1, 0.05), (IMPACT, 'hit', 0.7, 1, 0.03),
                   (IMPACT + 0.75, 'ready', 0.8, 1, 0.2),
                   (STAND, 'run', 1.2, 4, 0.1), (22.3, 'attack1', 1.0, 1, 0.05), (22.75, 'hit', 0.8, 1, 0.03),
                   (23.35, 'ready', 0.9, 1, 0.2), (23.95, 'run', 1.2, 3, 0.1), (24.35, 'attack2', 1.0, 1, 0.05),
                   (24.85, 'hit', 0.7, 1, 0.03), (25.45, 'ready', 0.8, 1, 0.3), (25.75, 'idle', 0.6, 3, 0.35)]
        else:
            sch = [(0, 'ready', 1.0, 1), (DEPLOY + 0.35 + d, 'ready', 1.0, 1, 0.05), (IMPACT - 0.02 + d * 0.3, 'hit', 0.9, 1, 0.03),
                   (IMPACT + 0.45 + d, 'die', 2.4, 1, 0.08)]
        u.play(sch)
        for f in range(1, NF + 1):
            t = T(f); base = COINS_A[i]; z = 0.0
            if t < DEPLOY: hidden = True; p = base
            else:
                hidden = False
                z = max(0.0, 6.0 * (1 - ramp(t, DEPLOY + d, DEPLOY + 0.32 + d)) ** 2)        # the drop
                p = base; h = heading(V(-0.6, 1.0))
            h = heading(GOAT_PATH[-1][1] - base)
            if i > 0 and t >= IMPACT - 0.02:
                k = ease(ramp(t, IMPACT, IMPACT + 0.55)); p = base.lerp(SIB_FLY[i], k); z = 1.6 * math.sin(math.pi * k)
                h = heading(GOAT_PATH[-1][1] - base) + 6.0 * k
            if i == 0:
                knocks = [(IMPACT, base, HERO_KNOCK, 1.0)]
                if t >= IMPACT:
                    p = HERO_KNOCK
                    k = ease(ramp(t, IMPACT, IMPACT + 0.4)); p = base.lerp(HERO_KNOCK, k); z = 0.7 * math.sin(math.pi * k)
                if 21.0 <= t < STAND:                            # it looks at its brothers lying in the snow, then at the goat
                    h = lerp(heading(SIB_FLY[2] - HERO_KNOCK), heading(SIB_FLY[1] - HERO_KNOCK), ease(ramp(t, 21.0, 21.5)))
                if t >= STAND - 0.15: h = heading(GOAT_STOP - HERO_KNOCK)
                front = GOAT_STOP + V(0.25, -0.95)
                if t >= STAND: p = HERO_KNOCK.lerp(front, ease(ramp(t, STAND, 22.3))); z = 0
                hit2 = HERO_KNOCK + V(-0.2, -0.15)
                if t >= 22.75: k = ease(ramp(t, 22.75, 23.1)); p = front.lerp(hit2, k); z = 0.6 * math.sin(math.pi * k)
                if t >= 23.95: p = hit2.lerp(front, ease(ramp(t, 23.95, 24.35))); z = 0
                hit3 = HERO_KNOCK + V(0.15, -0.35)
                if t >= 24.85: k = ease(ramp(t, 24.85, 25.2)); p = front.lerp(hit3, k); z = 0.5 * math.sin(math.pi * k)
                rx = fall_rx(t); z += 0.06 * ramp(t, FALL0, FALL1)
            else: rx = 0.0
            key_ctrl(K, u, f, p, h, z, rx)
            K.add(u.mesh, 'hide_render', 0, f, hidden)
    # --- custom animation over the clips (the game has no clip for these moments)
    def trem(t, a): return a * (math.sin(t * 57.0) + 0.6 * math.sin(t * 83.0 + 1.0))
    def hero_pose(t):
        bend = 0.0; lean = 0.0; tr = 0.0
        bend += 35 * (1 - ease(ramp(t, IMPACT + 0.45, IMPACT + 1.25))) * (t >= IMPACT + 0.4)       # struggling up
        bend += 20 * ease(ramp(t, 21.0, 21.3)) * (1 - ease(ramp(t, 21.55, 21.8)))                   # bowed over its brothers
        tr += 2.0 * (21.0 <= t < 21.8)
        bend += 30 * (1 - ease(ramp(t, 23.2, 23.95))) * (23.1 <= t < 23.95); tr += 3.0 * (23.1 <= t < 23.95)
        if t >= 25.2:                                                                               # up again; then the brace
            bend += 34 * (1 - ease(ramp(t, 25.3, 25.9))) + 8 * ease(ramp(t, 25.6, 25.9)); tr += 2.5 * (t < FALL0)
            lean += 6 * math.sin(math.pi * 2 * ramp(t, FALL0 - 0.55, FALL0)) * (FALL0 - 0.55 <= t < FALL0)   # it sways
            bend *= 1 - ease(ramp(t, FALL0, FALL0 + 0.3))
        sp = (bend / 3 + trem(t, tr), trem(t + 0.3, tr) * 0.5, lean / 3)
        return {'Spine': sp, 'Spine1': sp, 'Spine2': sp, 'Head': (trem(t + 0.7, tr) * 0.6, 0, 0)}
    def hero_arms(t):
        return ease(ramp(t, 25.55, 25.85)) * (1 - 0.35 * ease(ramp(t, FALL0, FALL1)))
    game.layer(C['a_coin0'], NF, hero_pose, hero_arms)
    for i in range(4):
        d = 0.08 * i
        def tun_pose(t, d=d):
            look = -24 * ease(ramp(t, CHOSEN + 0.25 + d, CHOSEN + 0.6 + d)) * (1 - ease(ramp(t, CHOSEN + 0.95 + d, CHOSEN + 1.1 + d)))
            slump = 10 * ease(ramp(t, NIGHT + 1.2, NIGHT + 2.2)) * (1 - ease(ramp(t, CHOSEN + 0.2, CHOSEN + 0.45)))
            sp = ((look + slump) / 3, 0, 0)
            return {'Spine': sp, 'Spine1': sp, 'Spine2': sp, 'Head': (look * 0.3, 0, 0)}
        game.layer(C[f't_coin{i}'], NF, tun_pose)


def puffs(K, extra=()):
    """Snow kicked up by every landing, blow and footfall: small clumps on ballistic arcs."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0); src = bpy.context.active_object; me = src.data
    for p in me.polygons: p.use_smooth = True
    me.materials.append(sets.flat('puff', (0.93, 0.96, 1.0), 0.6)); bpy.data.objects.remove(src)
    rng = random.Random(9); sc = bpy.context.scene
    def burst(t0, p, n, power, r, ring=0.0):
        for _ in range(n):
            o = bpy.data.objects.new('puff', me); sc.collection.objects.link(o); o.visible_shadow = False
            a = rng.uniform(0, 6.283); vr = rng.uniform(0.25, 1.0) * power; vz = rng.uniform(0.7, 2.3) * power
            life = rng.uniform(0.4, 0.9); rr = r * rng.uniform(0.3, 1.3); f0 = F(t0); off = ring + rng.uniform(0, 0.12)
            for i in range(3): K.add(o, 'scale', i, f0 - 1, 0.0)
            for j in range(int(life * FPS) + 1):
                tt = j / FPS; s = rr * (1 - tt / life) ** 0.6
                pos = (p.x + math.cos(a) * (off + vr * tt), p.y + math.sin(a) * (off + vr * tt), max(0.0, 0.03 + vz * tt - 2.6 * tt * tt))
                for i in range(3): K.add(o, 'location', i, f0 + j, pos[i]); K.add(o, 'scale', i, f0 + j, s)
            for i in range(3): K.add(o, 'scale', i, f0 + int(life * FPS) + 1, 0.0)
    for i in range(4): burst(DEPLOY + 0.32 + 0.05 * i, COINS_A[i], 14, 0.8, 0.034)
    ctr = sum(COINS_A, V(0, 0)) / 4; burst(IMPACT, ctr, 60, 1.5, 0.045)
    for i in (1, 2, 3): burst(IMPACT + 0.55, SIB_FLY[i], 18, 0.8, 0.034)
    for tt, p in ((IMPACT + 0.4, HERO_KNOCK), (23.1, HIT2), (25.2, HIT3)): burst(tt, p, 18, 0.75, 0.032)
    dg = (GOAT_STOP - HIT3).normalized(); burst(FALL1, HIT3 - dg * 0.42, 44, 0.6, 0.02, ring=0.36)      # thrown out from under its rim, not through its face
    t = CHARGE + 0.1
    while t < IMPACT: burst(t, GOAT_PATH[-1][1].lerp(GOAT_STOP, ease(ramp(t, CHARGE, IMPACT + 0.1))), 7, 0.55, 0.03); t += 0.12
    front = GOAT_STOP + V(0.25, -0.95)
    for (a, b, pa, pb) in ((STAND, 22.3, HERO_KNOCK, front), (23.95, 24.35, HIT2, front)):
        t = a + 0.08
        while t < b: burst(t, pa.lerp(pb, ease(ramp(t, a, b))), 4, 0.4, 0.022); t += 0.1
    for tt in (22.62, 24.72): burst(tt, front, 16, 0.9, 0.034)
    for b in extra: burst(*b)


def cutaways(C, K):
    """The gameplay cutaways: the card drops into the match (and the two stars hit THE GOAT). Returns their snow bursts."""
    bursts = []
    for k in ('a_giga', 'a_whale', 'goat'):
        K.add(C[k].mesh, 'hide_render', 0, 1, False); K.add(C[k].mesh, 'hide_render', 0, NF + 1, True)
    for i in range(4): K.add(C[f'a_coin{i}'].mesh, 'hide_render', 0, NF + 1, True)
    gsch = [(0, 'idle', 1.0, 60)]
    adv = (I_GOAT - I_LAND).normalized() * 1.0
    for i, (k, at, n) in enumerate(INS):
        s0 = INS_T[i]; u = C['i_' + k]; big = n > 30
        land = I_LAND if big else I_QUICK; face = heading(I_GOAT - I_LAND) if big else math.pi
        sch = [(0, 'idle', 1.0, 60), (s0 + 0.22, 'ready', 1.4, 1, 0.04)]
        if big:
            sch += [(s0 + 0.42, 'run', 1.3, 3, 0.1), (s0 + 0.7, 'attack1', 1.0, 1, 0.08)]
            gsch += [(s0 - 0.05, 'idle', 1.0, 10, 0.0), (s0 + 0.95, 'hit', 1.0, 1, 0.04)]
            bursts.append((s0 + 0.95, I_GOAT, 14, 0.8, 0.034))
        u.play(sch); bursts.append((s0 + 0.23, land, 22 if big else 16, 0.9, 0.036))
        for f in range(1, NFX + 1):
            t = T(f); on = F(s0) <= f < F(s0) + n
            K.add(u.mesh, 'hide_render', 0, f, not on)
            if on or f == 1:
                p = land + adv * ease(ramp(t, s0 + 0.42, s0 + 0.72)) if big else land
                key_ctrl(K, u, f, p, face, 6.0 * (1 - ramp(t, s0, s0 + 0.22)) ** 2)
    g = C['i_goat']; g.play(gsch)
    for f in range(1, NFX + 1):
        ia = ins_at(T(f)); K.add(g.mesh, 'hide_render', 0, f, not (ia and INS[ia[0]][2] > 30))
    key_ctrl(K, g, 1, I_GOAT, heading(I_LAND - I_GOAT))
    return bursts


POS = {}


# ------------------------------------------------------------------ camera
def make_camera():
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam; cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24; cd.dof.use_dof = True
    cd.clip_start = 0.05; cd.clip_end = 200
    cam.rotation_mode = 'QUATERNION'; return cam


def world_pos(u, f, up=0.5):
    bpy.context.scene.frame_set(f); return u.ctrl.matrix_world.translation + Vector((0, 0, u.height * up))


def camera(cam, C, f, K, cache):
    t = T(f)
    def shot(pos, tgt, fov, fstop=2.8, focus=None):
        pos = Vector(pos); tgt = Vector(tgt); return pos, (tgt - pos).to_track_quat('-Z', 'Y'), fov, focus or (tgt - pos).length, fstop
    hand = Vector((math.sin(t * 1.1) * 0.012 + math.sin(t * 2.7) * 0.006, math.sin(t * 0.8) * 0.01, math.sin(t * 1.6 + 1) * 0.008))
    hero_t = cache['t_coin0'][f]; hero_a = cache['a_coin0'][f]; goat = cache['goat'][f]
    dg = (GOAT_STOP - HIT3).to_3d().normalized()
    def rot(v, a): return V(v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a), 0)
    ia = ins_at(t)
    if ia:                            # gameplay cutaway: the picked card lands in the match (framed above the hand UI)
        i, k, u = ia; ku = ease(u / (INS[i][2] / FPS)); la = I_LAND.to_3d(); qq = I_QUICK.to_3d()
        if k == 'giga': c = V(3.45 - 0.25 * ku, -8.1 + 0.3 * ku, 0.5); r = shot(c, V(2.1, -3.9, 0.55), 46, 4.0, focus=(c - la).length)      # behind him (clear of the snow drifts at x > 3.8)
        elif k == 'whale': c = I_GOAT.to_3d() + V(-1.1 + 0.15 * ku, 2.1, 0.95); r = shot(c, la + V(0.1, 0.6, 0.5), 46, 4.0, focus=(c - la).length)      # over THE GOAT's shoulder
        else:
            c = qq + dict(bonk=V(0.5, 2.9, 0.35), cate=V(2.6, 1.5, 0.45), walter=V(-1.8, 2.4, 1.2))[k]
            r = shot(c, qq + V(0, 0, 0.35), 42, 2.8, focus=(c - qq).length)
    elif t < 3.0:                     # behind the line-up: silhouettes against the gate; slow push in
        k = ease(ramp(t, 0, 3.0)); r = shot(V(TX - 0.2, -9.6 + 1.6 * k, 0.55 + 0.1 * k), V(TX + 0.4, 3.0, 1.3), 34, 4.0, focus=7.5)
    elif t < 4.0:                     # GIGA is chosen: over the coins' heads, the light on him
        g_ = cache['t_giga'][f]; c = V(TX + 0.35, -4.7, 1.3); r = shot(c, g_ + V(0, 0, 0.25), 24, 2.8, focus=(c - g_).length)
    elif t < 5.0:                     # the hero's face: hope (it bounces)
        c = V(TX + 0.55, -0.6, 0.55); r = shot(c, hero_t + V(0, 0, 0.05), 32, 2.0)
    elif t < 6.0:                     # The Whale is chosen
        w_ = cache['t_whale'][f]; c = V(TX + 0.6, -4.7, 1.3); r = shot(c, w_ + V(0, 0, 0.5), 22, 2.8, focus=(c - w_).length)
    elif t < 7.0:                     # he walks away past them; they watch him go
        c = V(TX + 1.55, -0.9, 0.5); r = shot(c, hero_t + V(0, 0, 0.1), 34, 2.0)
    elif t < NIGHT:                   # the montage: the light lands on someone else, again, and again; closer each time
        z = min(2, int((t - 7.0) / 0.667)); c = [V(TX + 1.6, -0.5, 0.6), V(TX - 0.2, -0.9, 0.5), V(TX + 0.95, -0.7, 0.5)][z]
        r = shot(c, hero_t + V(0, 0, 0.05), [34, 30, 26][z], 2.0)
    elif t < ARENA[0]:                # alone: a wide, high view down the empty tunnel, the gate gone cold
        k = ease(ramp(t, NIGHT, ARENA[0])); r = shot(V(TX - 0.9, 8.2 - 0.6 * k, 3.1), V(TX + 0.7, -2.6, 0.3), 46 - 6 * k, 5.6)
    elif t < 13.0:                    # the final match, from the snow itself: GIGA falls close by, The Whale beyond
        k = ease(ramp(t, 11.0, 13.0)); c = V(2.25 - 0.5 * k, -7.3 + 0.2 * k, 0.26); gg = cache['a_giga'][f]
        r = shot(c, V(-1.0, -2.6, 0.95), 40, 2.8, focus=(c - gg).length)
    elif t < 14.6:                    # THE GOAT comes off the bridge: low, looking up at him
        c = V(-5.7, -4.6, 0.22); r = shot(c, goat + V(0, 0, 0.75), 32, 2.8)
    elif t < CHOSEN:                  # the hand (UI): the arena out of focus behind it
        r = shot(V(-0.5, -16.5, 3.0), V(-2.5, -4.0, 1.0), 40, 0.6, focus=1.0)
    elif t < DEPLOY:                  # back in the dark tunnel: the light finds the coins
        k = ease(ramp(t, CHOSEN, DEPLOY)); c = V(TX - 0.9, -0.7 - 0.1 * k, 0.28); r = shot(c, hero_t + V(0, 0, 0.12), 34 - 4 * k, 2.0)
    elif t < CHARGE:                  # deploy: the coins drop in front of our king; THE GOAT stops, sees them
        r = shot(V(-0.9, -11.2, 0.55), V(-3.1, -5.6, 1.1), 40, 4.0, focus=(V(-0.9, -11.2, 0.55) - COINS_A[0].to_3d()).length)
    elif t < 21.0:                    # the charge: from the side, low
        r = shot(V(0.9, -6.3, 0.6), V(-2.9, -7.2, 0.8), 42, 4.0)
    elif t < STAND:                   # the hero, alone now, looks at its brothers
        sb = SIB_FLY[3].to_3d(); away = (sb - HERO_KNOCK.to_3d()).normalized(); pp = V(-away.y, away.x, 0); c = sb + away * 0.8 + pp * 0.75 + V(0, 0, 0.5)
        r = shot(c, hero_a + V(0, 0, 0.0), 30, 2.4, focus=(c - hero_a).length)
    elif t < 22.75:                   # the stand: low behind the hero as it runs at THE GOAT
        k = ease(ramp(t, STAND, 22.75)); c = V(-1.35, -10.4 + 0.5 * k, 0.32)
        r = shot(c, lerp(V(-2.6, -7.6, 0.8), goat + V(0, 0, 0.4), 0.5), 34, 2.8, focus=(c - hero_a).length)
    elif t < 23.95:                   # knocked down: ground-level profile, the hero getting up, THE GOAT towering out of focus
        c = HIT2.to_3d() + rot(dg, 0.9) * 1.9 + V(0, 0, 0.22)
        r = shot(c, hero_a, 38, 2.0, focus=(c - hero_a).length)
    elif t < 24.85:                   # worm's eye: from the snow behind the hero, up at THE GOAT as it strikes again
        side = V(-dg.y, dg.x, 0); c = hero_a + side * 0.7 - dg * 0.6; c.z = 0.12; r = shot(c, goat + V(0, 0, 0.45), 46, 4.0, focus=(c - goat).length)
    elif t < HORN:                    # arms spread in front of our king: from the goat's side, low, the tower behind it
        c = HIT3.to_3d() + rot(dg, 0.75) * 2.3 + V(0, 0, 0.3); k = ease(ramp(t, 24.85, HORN))
        c = c.lerp(HIT3.to_3d() + rot(dg, 0.75) * 1.9 + V(0, 0, 0.32), k)
        r = shot(c, HIT3.to_3d() + V(0, 0, 0.4), 40, 2.4)
    elif t < 27.2:                    # the horn. Its face, trembling, slowly closer
        k = ease(ramp(t, HORN, 27.2)); c = HIT3.to_3d() + rot(dg, 0.45) * (1.6 - 0.35 * k) + V(0, 0, 0.42)
        r = shot(c, HIT3.to_3d() + V(0, 0, 0.45), 30, 2.0)
    elif t < VICTORY[0]:              # it falls back into the snow: from the side, at ground level
        side = V(-dg.y, dg.x, 0); c = HIT3.to_3d() - dg * 0.3 + side * 2.6 + V(0, 0, 0.28)
        r = shot(c, HIT3.to_3d() - dg * 0.35 + V(0, 0, 0.3), 36, 2.8)
    elif t < MORNING:                 # straight down on it lying in the snow, arms out, rising away (victory + deck UI over it)
        k = ease(ramp(t, VICTORY[0], MORNING)); ctr = HIT3.to_3d() - dg * 0.42 + V(0, 0, 0.05)
        c = ctr + V(0.0, 0.0, 1.7 + 1.6 * k); up = -dg; zx = V(0, 0, 1); xx = up.cross(zx).normalized()
        from mathutils import Matrix
        q = Matrix((xx, up, zx)).transposed().to_quaternion(); r = (c, q, 40, (c - ctr).length, 1.6)
    else:                             # the next morning: from the gate side, warm; the light finds them first
        k = ease(ramp(t, MORNING, END)); c = V(TX - 1.35, 9.3 - 0.3 * k, 0.62); r = shot(c, V(TX + 0.5, 7.15, 0.5), 40 - 4 * k, 2.8)
    pos, q, fov, focus, fstop = r; pos = pos + hand
    cache.setdefault('cam', {})[f] = (pos.copy(), pos + q @ Vector((0, 0, -1)) * focus)
    for i in range(3): K.add(cam, 'location', i, f, pos[i])
    for i in range(4): K.add(cam, 'rotation_quaternion', i, f, q[i])
    K.add(cam.data, 'lens', 0, f, 12.0 / math.tan(math.radians(fov) / 2))
    K.add(cam.data, 'dof.focus_distance', 0, f, focus); K.add(cam.data, 'dof.aperture_fstop', 0, f, fstop)


# ------------------------------------------------------------------ light
def lights(S, Ar, C, K, cache):
    sc = bpy.context.scene; L = {}
    def light(name, kind, loc, energy, color, size=0.3, tgt=None):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); o.data.energy = energy; o.data.color = color
        if kind == 'AREA': o.data.size = size
        elif kind != 'SUN': o.data.shadow_soft_size = size
        o.location = loc; sc.collection.objects.link(o)
        if tgt: o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        L[name] = o; return o
    light('moon', 'SUN', (0, 0, 10), 0.0, (0.62, 0.74, 1.0)); L['moon'].rotation_euler = Euler((math.radians(58), 0, math.radians(205))); L['moon'].data.angle = 0.06
    light('arena_fill', 'AREA', (0, -26, 14), 0.0, (0.55, 0.68, 1.0), 20, (0, 0, 0))
    light('hero_warm', 'SPOT', (0, 0, 6), 0.0, (1.0, 0.75, 0.45), 0.4); L['hero_warm'].data.spot_size = math.radians(14); L['hero_warm'].data.spot_blend = 0.8
    light('tunnel_fill', 'AREA', (TX, -6, TH - 0.2), 0.0, (1.0, 0.8, 0.6), 3.0, (TX, -6, 0))
    light('rim', 'SPOT', (0, 0, 5), 0.0, (0.6, 0.95, 1.0), 0.25); L['rim'].data.spot_size = math.radians(46); L['rim'].data.spot_blend = 0.6
    L['rim'].rotation_mode = 'QUATERNION'
    for i, p in enumerate(Ar['ruins']): light(f'ember{i}', 'POINT', (p.x, p.y, 0.9), 0.0, (1.0, 0.42, 0.12), 0.35)
    light('king_glow', 'POINT', (0, -12.3, 1.6), 260, sets.OURS, 0.5); light('en_glow', 'POINT', (0, 12.3, 1.6), 260, sets.THEIRS, 0.5)
    sc_nt = sc.node_tree
    rng = random.Random(5)
    bm = S['beam_mat'].node_tree.nodes['strength'].inputs[1]
    blaze = S['blaze_mat'].node_tree.nodes['Principled BSDF'].inputs
    for f in range(1, NFX + 1):
        t = T(f)
        in_arena = (ARENA[0] <= t < CHOSEN) or (DEPLOY <= t < MORNING) or t >= END
        # gate light: gold by day, cold at night, gold again in the morning
        night = ease(ramp(t, NIGHT, NIGHT + 1.6)) * (1 - (t >= MORNING))
        gold, cold = Vector((1.0, 0.84, 0.6)), Vector((0.45, 0.6, 1.0))
        col = gold.lerp(cold, night)
        for i in range(3): K.add(S['gate_sun'].data, 'color', i, f, col[i])
        K.add(S['gate_sun'].data, 'energy', 0, f, lerp(900, 330, night) * (0.3 if t >= MORNING else 1.0))
        for i in range(3): K.add(S['blaze_mat'].node_tree, 'nodes["Principled BSDF"].inputs["Emission Color"].default_value', i, f, col[i])
        K.add(S['blaze_mat'].node_tree, 'nodes["Principled BSDF"].inputs["Emission Strength"].default_value', 0, f, lerp(6.0, 1.2, night) * (0.35 if t >= MORNING else 1.0))
        for j, ln in enumerate(S['lanterns']):
            fl = 0.82 + 0.18 * math.sin(t * 9.1 + j * 1.7) * math.sin(t * 5.3 + j)
            K.add(ln.data, 'energy', 0, f, 40 * fl * lerp(1.0, 0.5, night))
        K.add(L['tunnel_fill'].data, 'energy', 0, f, lerp(18, 11, night))
        # the light that chooses
        target, on = None, 0.0
        for k, tp in PICKS:
            if tp <= t < min(tp + 1.6, NIGHT): target = cache['t_' + k][F(tp)]; on = ease(ramp(t, tp, tp + 0.2)) * (1 - ease(ramp(t, tp + 1.2, tp + 1.6)))
        if CHOSEN + 0.2 <= t < CHOSEN + 1.6:  # (brighter: this is the moment)
            target = cache['t_coin0'][F(CHOSEN)] + V(0.25, 0.25, 0); on = ease(ramp(t, CHOSEN + 0.2, CHOSEN + 0.5))
        if t >= MORNING + 0.6:
            target = V(TX + 0.55, 7.2, 0); on = ease(ramp(t, MORNING + 0.6, MORNING + 0.9))
        if target is None: target = V(TX, -20, 0)
        tl = V(target.x, target.y, TH - 0.05)
        sl = tl + V(-1.3, 1.5, 0) if CHOSEN <= t < DEPLOY else tl          # the chosen light leans in from the gate side: it lights their faces
        se = (V(target.x, target.y, 0.3) - sl).to_track_quat('-Z', 'Y').to_euler()
        for i in range(3): K.add(S['choose'], 'location', i, f, sl[i]); K.add(S['choose'], 'rotation_euler', i, f, se[i])
        K.add(S['choose'].data, 'energy', 0, f, (3500 if CHOSEN <= t < DEPLOY else 900) * on)
        for i in range(2): K.add(S['beam'], 'location', i, f, tl[i])
        K.add(S['beam_mat'].node_tree, 'nodes["strength"].inputs[1].default_value', 0, f, (0.16 if CHOSEN <= t < DEPLOY else 0.2 if t >= MORNING else 0.5) * on)
        # arena: cold moonlight; a warm spot on the hero after the horn
        K.add(L['moon'].data, 'energy', 0, f, 2.5); K.add(L['arena_fill'].data, 'energy', 0, f, 1150)
        K.add(sc_nt, 'nodes["mistk"].outputs[0].default_value', 0, f, 0.24 if in_arena else 0.0)
        for i in range(len(Ar['ruins'])):
            fl = 0.7 + 0.3 * math.sin(t * 11.3 + i * 2.1) * math.sin(t * 6.7 + i) + 0.12 * math.sin(t * 23.0 + i)
            K.add(L[f'ember{i}'].data, 'energy', 0, f, 420 * fl)
        # a rim light that always sits behind whoever the lens is on: aurora-cold in the arena, lantern-warm in the tunnel
        cp, ct = cache['cam'][f]; dv = Vector((ct.x - cp.x, ct.y - cp.y, 0))
        dv = dv.normalized() if dv.length > 0.1 else Vector((0, 1, 0)); sd = Vector((-dv.y, dv.x, 0))
        rp = ct + dv * 3.2 + sd * 1.3; rp.z = ct.z + 2.6
        if in_arena: rcol = Vector((0.55, 0.95, 1.0)); ren = 500.0 if VICTORY[0] <= t < MORNING else 1700.0
        else:
            rp.x = clamp(rp.x, TX - 1.9, TX + 1.9); rp.y = clamp(rp.y, -10.5, GATE_Y - 0.8); rp.z = min(rp.z, TH - 0.3)
            rcol = Vector((1.0, 0.62, 0.32)).lerp(Vector((0.5, 0.66, 1.0)), night); ren = lerp(420.0, 750.0, night)
        rq = (Vector((ct.x, ct.y, ct.z)) - rp).to_track_quat('-Z', 'Y')
        for i in range(3): K.add(L['rim'], 'location', i, f, rp[i]); K.add(L['rim'].data, 'color', i, f, rcol[i])
        for i in range(4): K.add(L['rim'], 'rotation_quaternion', i, f, rq[i])
        K.add(L['rim'].data, 'energy', 0, f, ren)
        hw = ease(ramp(t, HORN + 0.6, HORN + 2.0)) * (t < MORNING)
        hp = cache['a_coin0'][f]
        for i, v in enumerate((hp.x + 0.4, hp.y - 1.0, 6.0)): K.add(L['hero_warm'], 'location', i, f, v)
        K.add(L['hero_warm'].data, 'energy', 0, f, 900 * hw)
    q = (V(0, 0, 0) - V(0, 0, 1)).to_track_quat('-Z', 'Y')
    L['hero_warm'].rotation_euler = Euler((0.17, 0, 0))
    for o in L.values(): o.visible_camera = False; o.visible_glossy = False
    return L


# ------------------------------------------------------------------ overlay events (screen positions)
def overlay_events(cam, C):
    sc = bpy.context.scene; ev = []
    def scr(p, f):
        sc.frame_set(f); v = world_to_camera_view(sc, cam, p); return [round(v.x, 4), round(1 - v.y, 4)]
    for (tt, who) in ((22.5, 'goat'), (24.55, 'goat')):
        f = F(tt); p = C['goat'].ctrl.matrix_world.translation + V(0, 0, C['goat'].height * 0.85)
        ev.append(dict(kind='dmg', t=tt, text='-56', at=scr(p, f)))
    for i, (k, at, n) in enumerate(INS):
        if n > 30:
            g = C['i_goat']; p = g.ctrl.matrix_world.translation + V(0, 0, g.height * 0.85)
            ev.append(dict(kind='idmg', ins=i, u=0.97, text=dict(giga='-212', whale='-340')[k], at=scr(p, F(INS_T[i] + 0.97))))
    return ev


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    res = int(arg('--res', '1080'))
    setup_render(res)
    S = sets.tunnel(); Ar = sets.arena()
    C = cast()
    K = rigctl.Keys()
    act(C, K); puffs(K, cutaways(C, K)); K.flush()
    for u in C.values():               # hide toggles must not interpolate
        ad = u.mesh.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    sc = bpy.context.scene
    cache = {k: {} for k in ('t_coin0', 'a_coin0', 'goat', 't_giga', 't_whale', 't_bonk', 't_cate', 't_walter', 'a_giga')}
    for f in range(1, NFX + 1):
        sc.frame_set(f)
        for k in cache: cache[k][f] = C[k].ctrl.matrix_world.translation.copy() + V(0, 0, C[k].height * 0.45)
    cam = make_camera(); K2 = rigctl.Keys()
    for f in range(1, NFX + 1): camera(cam, C, f, K2, cache)
    L = lights(S, Ar, C, K2, cache)
    K2.flush()
    cut_frames = {F(c) for c in CUTS} | {F(END)} | {F(x) for x in INS_T}; sc.frame_end = NFX
    for idb in (cam, cam.data):
        for fc in idb.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if int(round(kp.co.x)) + 1 in cut_frames else 'LINEAR'
    ev = overlay_events(cam, C)
    json.dump(dict(fps=FPS, end=END, cuts=CUTS, picks=PICKS, night=NIGHT, arena=ARENA, chosen=CHOSEN, deploy=DEPLOY,
                   charge=CHARGE, impact=IMPACT, stand=STAND, horn=HORN, victory=VICTORY, morning=MORNING, events=ev,
                   inserts=[dict(kind=k, at=at, n=n) for k, at, n in INS]),
              open(os.path.join(os.environ['W'], 'timeline.json'), 'w'), indent=1)
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=arg('--out'), compress=False)
    print('SAVED', arg('--out'), NFX, 'frames')


if __name__ == '__main__':
    main()
