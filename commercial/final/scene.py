"""MEME ROYALE CHAMPIONSHIP: "THE FINAL".  A sports-broadcast parody, about 2 min 06 s.

Two commentators call the final. Giga (44-0) sends the Whale through Pepe's towers; Pepe (3-41, down 99%) plays
nothing, then his one card: Useless, a coin that walks the length of the pitch unmarked and taps the king's tower.

Built on the clash stadium (arena, stands, crowd, units and FX code are exec'd from ../clash/scene.py).

    python3 voices.py KOKORO_DIR VO_DIR
    blender -b --factory-startup -P scene.py -- --out scene.blend --vo VO_DIR --fx FX_DIR
    (writes edl.json; render with render_edl.py; finish.py adds broadcast graphics and sound)

24 fps, 1152x648 (16:9), finished at 1920x1080.
"""
import bpy, math, json, os, sys, random
from mathutils import Vector

MYHERE = os.path.dirname(os.path.abspath(__file__))
CL = os.path.join(MYHERE, '..', 'clash', 'scene.py')
T_END = 104.0
LAST_F = int(T_END * 24) + 1

text = open(CL).read().replace('FPS = 24; LAST = 780', f'FPS = 24; LAST = {LAST_F}')
src = text.split('\n')


def line(prefix, start=0):
    return next(i for i, l in enumerate(src) if i >= start and l.startswith(prefix))


i_units = line('# ================================================================ units')
i_battle = line('# ================================================================ CLASH AT THE BRIDGE: the battle')
i_ns = line('N_, S_ = heading(0, 1)')
i_crowd = line('# ================================================================ the crowd')
i_fan = line('def fan_sched')
i_sources = line('SOURCES = ')
i_keepout = line('KEEP_OUT = []')
i_crowdcall = line('crowd()')
i_light = line('# ================================================================ dusk light')
i_edit = line('# ================================================================ the edit')

g = globals()
g['__file__'] = CL
exec(compile('\n'.join(src[:i_units]), CL, 'exec'), g)                 # helpers, arena, sky, stadium, blimp, scoreboard
exec(compile('\n'.join(src[i_units:i_battle]), CL, 'exec'), g)         # units, FX
exec(compile('\n'.join(src[i_battle:i_ns + 1]), CL, 'exec'), g)        # smooth(), fighter(), sparks(), dust(), stand(), fight()
HERE = MYHERE
VOD = arg('--vo', os.path.expanduser('~/final_work/vo'))
FXD = arg('--fx', os.path.expanduser('~/final_work/fx'))
VO = json.load(open(os.path.join(VOD, 'vo.json')))
sc.render.resolution_x, sc.render.resolution_y = 1152, 648
sc.cycles.samples = int(arg('--samples', '10'))
sc.frame_end = LAST_F
THUNDER = []                                                           # a clear evening: no lightning


def D(i):
    return VO[i]['dur']


def path_len(pts):
    return sum((Vector(b_) - Vector(a)).length for a, b_ in zip(pts, pts[1:]))


# ================================================================ the match, in animation seconds
T_KICK = 24.0
T_SWAT = 30.5                       # the Whale swats the lone defender off the left bridge
T_T1 = 39.5                         # blue's left tower: the Whale goes through it
T_T2 = 50.0                         # blue's right tower
T_EXIT = 51.0                       # blue fans leave
T_CAST = 58.0                       # Pepe plays his one card
T_USE = 59.2                        # Useless lands
T_WALK = 64.5
WALK = [(12.0, -22.5), (14.5, -19.5), (14.5, -12.5), (9.6, -7.2), (9.0, -5.3)]
WALK_SPEED = 1.25
T_ARR = T_WALK + path_len(WALK) / WALK_SPEED
T_NOTICE = T_ARR - 1.6              # Giga looks down
T_TAP = T_ARR + 0.8
T_HIT = T_TAP + 0.55
T_KFALL = T_HIT + 1.9               # the king's tower gives up
T_INT = T_KFALL + 9.0               # the interview

# ================================================================ the crowd (clash code, our own reactions)
exec(compile('\n'.join(src[i_crowd:i_fan]), CL, 'exec'), g)


def fan_sched(team, j):
    if team == 'r':
        return [(0, 'idle', 1), (2.0, 'win', 0.9 + 0.2 * j), (T_KICK - 1, 'ready', 1), (T_SWAT + 0.3, 'win', 1.0 + 0.2 * j),
                (T_SWAT + 4, 'ready', 1), (T_T1 + 0.3, 'win', 1.0 + 0.2 * j), (T_USE + 1.5, 'emote', 1.0),
                (T_WALK + 4, 'ready', 1), (T_KFALL + 0.4, 'hit', 0.5), (T_KFALL + 1.8, 'lose', 1.0 + 0.3 * j)]
    return [(0, 'idle', 1), (2.0, 'win', 0.9 + 0.2 * j), (T_KICK - 1, 'ready', 1.1), (T_SWAT + 0.3, 'hit', 0.5),
            (T_SWAT + 1.6, 'idle', 1), (T_T1 + 0.3, 'lose', 1.0 + 0.3 * j), (T_USE + 1.0, 'idle', 1),
            (T_KFALL + 0.5, 'win', 1.1 + 0.2 * j)]


exec(compile('\n'.join(src[i_sources:i_keepout]), CL, 'exec'), g)
# the commentary box, high in the west stand, and a row of blue fans who will walk out
BOOTH = Vector((-13.6, -16.0, row_z(6)))
EXIT_ROW = 4
EXIT_Y = YS - (DEPTH * (EXIT_ROW + 0.5) + 0.2)
EXIT_Z = row_z(EXIT_ROW)
KEEP_OUT = [(BOOTH, 3.6)] + [(Vector((x, EXIT_Y, EXIT_Z)), 1.45) for x in [-5 + 1.4 * i for i in range(17)]]
exec(compile('\n'.join(src[i_keepout + 1:i_crowdcall + 1]), CL, 'exec'), g)
exec(compile('\n'.join(src[i_light:i_edit]), CL, 'exec'), g)           # dusk sun, team washes, bridge lights

E_ = heading(1, 0)                                                     # facing east

# Explosions: the fire is stock footage on cards (see fx_card); the sphere "fire" of the clash code is switched off
# and its smoke and dust are thinned, because opaque spheres read as balls.
NOFIRE = bpy.data.materials.new('nofire')
NOFIRE.use_nodes = True
NOFIRE.node_tree.nodes.clear()
_o = NOFIRE.node_tree.nodes.new('ShaderNodeOutputMaterial')
_t = NOFIRE.node_tree.nodes.new('ShaderNodeBsdfTransparent')
NOFIRE.node_tree.links.new(_t.outputs[0], _o.inputs['Surface'])
SMOKE = smoke_mat('smoke_thin', (0.10, 0.095, 0.09), 0.09)
DUST = smoke_mat('dust_thin', (0.5, 0.46, 0.4), 0.09)


def fall_tower(k, t, seed, crew=()):
    kill_tower(k, t, seed, crew, NOFIRE)


# ================================================================ small helpers
def walk3(u, p0, p1, t0, speed, clipname='walk'):
    """Walk in a straight line at any height (stands, platforms). Returns the arrival time."""
    p0, p1 = Vector(p0), Vector(p1)
    hd = heading(p1.x - p0.x, p1.y - p0.y)
    t1 = t0 + (p1 - p0).length / speed
    r = u['root']
    for t, p in ((t0, p0), (t1, p1)):
        r.location = p
        r.rotation_euler = (0, 0, hd)
        key(r, 'location', F(t))
        key(r, 'rotation_euler', F(t))
    linear(r)
    clip(u, clipname, F(t0), F(t1), 1.0)
    return t1


def hero(uid, h, team=None):
    u = unit(uid, h)
    if team:
        ring(u, team)
    smooth(u, True)
    return u


def area(name, loc, target, energy, size, color):
    return keylight(name, loc, target, energy, size, color)


# ================================================================ the two managers, on their king towers
PEPE_P = Vector((9.0, -28.3, 5.45))            # on top of the king tower's cannon
PEPE_HEAD = PEPE_P + Vector((0, 0.05, 2.0))
PEPE = hero('pepe', 2.3)
place(PEPE, PEPE_P, N_)
sched(PEPE, [(0, 'idle', 1), (T_CAST - 0.1, 'attack1', 0.9), (T_CAST + 1.05, 'idle', 1)])

GIGA_P = Vector((9.0, -3.05, 4.3))
GIGA_HEAD = GIGA_P + Vector((0, -0.05, 2.3))
GIGA = hero('giga', 2.7)
place(GIGA, GIGA_P, 0.0)
sched(GIGA, [(0, 'win', 0.8), (T_KICK - 2, 'idle', 1), (T_T1 + 0.5, 'win', 1.0), (T_T1 + 5, 'idle', 1),
             (T_T2 + 0.5, 'emote', 1.0), (T_T2 + 5, 'idle', 1), (T_NOTICE, 'hit', 0.45), (T_NOTICE + 1.0, 'idle', 1)],
      end=F(T_KFALL))

# hero light: a warm rim from the low sun side and a soft key for the faces
area('pepe_key', PEPE_HEAD + Vector((-3.5, 5.0, 1.5)), PEPE_HEAD, 900, 2.5, (1.0, 0.9, 0.78))
area('pepe_rim', PEPE_HEAD + Vector((3.0, -3.5, 2.5)), PEPE_HEAD, 2600, 1.2, (0.45, 0.62, 1.0))
area('giga_key', GIGA_HEAD + Vector((3.5, -5.0, 1.0)), GIGA_HEAD, 1100, 2.5, (1.0, 0.86, 0.72))
area('giga_rim', GIGA_HEAD + Vector((-3.0, 3.5, 2.5)), GIGA_HEAD, 3200, 1.2, (1.0, 0.45, 0.25))

# ================================================================ left lane: the Whale
WH = hero('whale', 3.5, 'r')
drop(WH, 3.5, -8.5, T_KICK + 0.6, S_)
clip(WH, 'ready', F(T_KICK + 0.6) - 5, F(T_KICK + 1.0))
dust(Vector((3.5, -8.5, 0.3)), T_KICK + 0.6, 1.6, 31)
t_ = run_to(WH, [(3.5, -8.5), (3.5, -14.3)], T_KICK + 1.0, 3.2)
POP = fighter('popcat', 2.1, 'b', False)
stand(POP, 3.5, -16.4, N_, 0, t_, 'ready')
fight(WH, t_, T_SWAT + 0.5, 1.0)
fight(POP, t_, T_SWAT, 1.2, 1)
for k_, tt in enumerate((t_ + 0.9, t_ + 1.9, t_ + 2.8)):
    sparks(Vector((3.5, -15.3, 1.8)), tt, 10, 40 + k_)
fling(POP, T_SWAT, (-1.0, -0.25), up=11, dist=17, dur=1.7)
sparks(Vector((3.5, -15.6, 1.9)), T_SWAT, 22, 44, 9.0)
t_ = run_to(WH, [(3.5, -14.3), (3.5, -19.5)], T_SWAT + 0.6, 5.2 / (T_T1 - 1.5 - T_SWAT - 0.6), 'walk')
t_ = run_to(WH, [(3.5, -19.5), (3.5, -30.6)], T_T1 - 1.5, 4.0)
t_ = run_to(WH, [(3.5, -30.6), (7.4, -27.0)], t_ + 0.4, 3.0)
place(WH, (7.4, -27.0, 0), heading(1.6, -2.5), F(t_) + 4)
fight(WH, t_, T_KFALL + 0.5, 0.9)
clip(WH, 'lose', F(T_KFALL + 0.5), LAST_F, 1.0)
fall_tower('bL', T_T1, 11)

# ================================================================ right lane: the Troll and Moo Deng
TR = fighter('troll', 2.7, 'r')
MD = fighter('moodeng', 3.9, 'r', False)
NY = fighter('nyancat', 2.0, 'b', False)
stand(NY, 14.5, -20.5, N_, 0, T_T1 + 6.0, 'ready')
for u, x0, y0, x1, y1, dt in ((TR, 13.7, -8.5, 13.5, -23.1, 0.0), (MD, 15.4, -9.5, 15.5, -22.8, 0.3)):
    drop(u, x0, y0, T_T1 + 1.5 + dt, S_)
    clip(u, 'ready', F(T_T1 + 1.5 + dt) - 5, F(T_T1 + 1.9 + dt))
    dust(Vector((x0, y0, 0.3)), T_T1 + 1.5 + dt, 1.4, 50 + int(dt * 10))
    ta = run_to(u, [(x0, y0), (x1, -19.0)], T_T1 + 1.9 + dt, 3.6)
    fight(u, ta, T_T1 + 6.2, 1.1)
    tb = run_to(u, [(x1, -19.0), (x1, y1)], T_T1 + 6.2, 3.0)
    fight(u, tb, T_T2 + 0.3, 1.1, 1)
    u['t_free'] = T_T2 + 0.3
fight(NY, T_T1 + 4.6, T_T1 + 6.0, 1.2)
fling(NY, T_T1 + 6.0, (1.0, -0.2), up=10, dist=15, dur=1.6)
sparks(Vector((14.5, -20.0, 1.8)), T_T1 + 6.0, 20, 61, 9.0)
fall_tower('bR', T_T2, 12)
for u, x, y in ((TR, 10.6, -26.6), (MD, 9.0, -25.6)):
    tc = run_to(u, [(u['root'].location.x, u['root'].location.y), (x, y)], u['t_free'], 3.4)
    place(u, (x, y, 0), heading(9 - x, -29.5 - y), F(tc) + 4)
    fight(u, tc, T_KFALL + 0.5, 1.0, 1)
    clip(u, 'lose', F(T_KFALL + 0.5), LAST_F, 1.0)
# the blue king's tower takes a beating but stands
for k_ in range(int((T_KFALL - T_T2 - 4) / 0.9)):
    f = F(T_T2 + 4 + k_ * 0.9)
    for ff, dx in ((f, 0.0), (f + 2, 0.07), (f + 4, -0.05), (f + 6, 0.0)):
        TW['bK'].location.x = TPOS['bK'][0] + dx
        key(TW['bK'], 'location', ff)
    if k_ % 3 == 0:
        sparks(Vector((9.0 + rnd.uniform(-1, 1), -27.6, 2.0)), T_T2 + 4 + k_ * 0.9 + 0.1, 8, 70 + k_, 6.0)

# ================================================================ Useless
US = hero('useless', 1.55, 'b')
drop(US, WALK[0][0], WALK[0][1], T_USE, N_)
dust(Vector((WALK[0][0], WALK[0][1], 0.2)), T_USE, 0.9, 81)
clip(US, 'idle', F(T_USE) - 5, F(T_WALK))
ta = run_to(US, WALK, T_WALK, WALK_SPEED, 'walk')
assert abs(ta - T_ARR) < 0.05, (ta, T_ARR)
clip(US, 'idle', F(T_ARR), F(T_TAP))
clip(US, 'attack1', F(T_TAP), F(T_TAP + 1.03), 1.0)
clip(US, 'idle', F(T_TAP + 1.03), F(T_KFALL + 1.2))
clip(US, 'win', F(T_KFALL + 1.2), LAST_F, 1.0)
area('useless_key', (16.5, -9.0, 4.0), (14.5, -16.0, 1.0), 2200, 3.0, (1.0, 0.92, 0.8))
area('king_key', (12.5, -8.5, 3.0), (9.0, -5.3, 1.0), 1500, 3.0, (1.0, 0.9, 0.8))

# the red reserves run past him on the bridge, the other way
SQUAD = []
for k_, (uid, dx) in enumerate((('floki', -1.05), ('goat', 0.95), ('swordcat', -1.25), ('toshi', 1.2))):
    u = fighter(uid, 2.3, 'r', False)
    x = 14.5 + dx
    t0 = T_WALK + 5.55 + k_ * 0.22
    drop(u, x, -6.2, t0 - 0.5, S_)
    clip(u, 'ready', F(t0 - 0.5) - 5, F(t0))
    tb = run_to(u, [(x, -6.2), (x, -20.5), (9.0 + dx * 2.2, -24.6)], t0, 5.0)
    place(u, (9.0 + dx * 2.2, -24.6, 0), S_, F(tb) + 3)
    fight(u, tb, T_KFALL + 0.5, 1.1, k_)
    clip(u, 'lose', F(T_KFALL + 0.5), LAST_F, 1.0)
    SQUAD.append(u)

# ================================================================ the king's tower falls; Giga with it
fall_tower('rK', T_KFALL, 13, crew=(GIGA,))
for f, dx in ((F(T_HIT), 0.0), (F(T_HIT) + 2, 0.05), (F(T_HIT) + 4, -0.04), (F(T_HIT) + 6, 0.0)):
    TW['rK'].location.x = TPOS['rK'][0] + dx
    key(TW['rK'], 'location', f)
sparks(Vector((9.0, -4.55, 0.9)), T_HIT, 6, 91, 3.0)
score_timeline('r', [(1, 0), (F(T_T1) + 10, 1), (F(T_T2) + 10, 2)])
score_timeline('b', [(1, 0), (F(T_KFALL) + 14, 3)])

# confetti
CONF = [mat('conf_b', (0.1, 0.35, 1.0), 0.5, emit=(0.1, 0.35, 1.0), estr=0.6), mat('conf_g', (1.0, 0.75, 0.15), 0.4, emit=(1.0, 0.7, 0.1), estr=0.6),
        mat('conf_w', (0.95, 0.95, 0.95), 0.5, emit=(1, 1, 1), estr=0.4)]
for k_ in range(420):
    x, y = rnd.uniform(-3, 21), rnd.uniform(-34, 2)
    z0 = rnd.uniform(14, 30)
    o = box('conf', (0.16, 0.10, 0.012), (x, y, z0), CONF[k_ % 3])
    o.visible_shadow = False
    t0 = T_KFALL + 1.0 + rnd.uniform(0, 5.0)
    fall = rnd.uniform(2.2, 3.4)
    o.scale = (0.001,) * 3
    key(o, 'scale', F(t0) - 1)
    o.scale = (1, 1, 1)
    key(o, 'scale', F(t0))
    const(o)
    for t, z in ((t0, z0), (t0 + z0 / fall, 0.02), (T_END, 0.02)):
        o.location = (x + rnd.uniform(-1.5, 1.5), y + rnd.uniform(-1.5, 1.5), z)
        key(o, 'location', F(t))
        o.rotation_euler = (rnd.uniform(0, 40), rnd.uniform(0, 40), rnd.uniform(0, 12)) if z > 1 else (0, 0, rnd.uniform(0, 6))
        key(o, 'rotation_euler', F(t))
    linear(o)

# ================================================================ blue fans who have seen enough
for k_, uid in enumerate(('wojak', 'chillguy', 'cate', 'ket', 'dope', 'apu', 'lmao')):
    u = unit(uid, 2.2)
    smooth(u, False)
    x0 = 2.5 + 2.0 * k_
    t0 = T_EXIT + 0.3 * k_
    place(u, (x0, EXIT_Y, EXIT_Z), N_, 1)
    clip(u, 'lose' if k_ % 2 else 'idle', 1, F(t0), 1.0)
    walk3(u, (x0, EXIT_Y, EXIT_Z), (x0 - 26, EXIT_Y, EXIT_Z), t0, 1.9)
area('exit_key', (-3.0, EXIT_Y + 4.0, EXIT_Z + 4.0), (3.0, EXIT_Y, EXIT_Z + 1.0), 2500, 4.0, (1.0, 0.92, 0.82))

# ================================================================ the commentary box
platform = box('booth_floor', (4.4, 6.4, 0.3), BOOTH + Vector((-0.6, 0, -0.15)), DARK)
box('booth_desk', (0.9, 4.6, 1.05), BOOTH + Vector((0.9, 0, 0.52)), WOOD)
box('booth_desktop', (1.1, 4.8, 0.08), BOOTH + Vector((0.9, 0, 1.09)), DARK)
box('booth_back', (0.25, 6.4, 3.4), BOOTH + Vector((-2.9, 0, 1.7)), DARK)
box('booth_roof', (4.6, 6.6, 0.2), BOOTH + Vector((-0.7, 0, 3.5)), DARK)
for sy in (-1, 1):
    box('booth_post', (0.16, 0.16, 3.4), BOOTH + Vector((1.5, sy * 3.1, 1.7)), GOLD)
    mic = box('booth_mic', (0.05, 0.05, 0.34), BOOTH + Vector((1.0, sy * 0.95, 1.3)), DARK, rot=(0, 0.5, 0))
    sphere('booth_michead', 0.07, BOOTH + Vector((1.08, sy * 0.95, 1.47)), DARK, 12)
    scr = mat('monitor', (0.02, 0.02, 0.03), 0.3, emit=(0.25, 0.55, 1.0), estr=2.5)
    box('booth_mon', (0.05, 0.75, 0.48), BOOTH + Vector((1.25, sy * 2.0, 1.4)), scr, rot=(0, -0.25, 0))
area('booth_light', BOOTH + Vector((1.6, 0, 3.1)), BOOTH + Vector((-0.2, 0, 1.4)), 420, 2.0, (1.0, 0.93, 0.85))
CHIP = unit('baton', 2.0)
BASIL = unit('jeanphil', 2.05)
smooth(CHIP, True)
smooth(BASIL, True)
place(CHIP, BOOTH + Vector((0.0, -1.0, 0)), E_)
place(BASIL, BOOTH + Vector((0.0, 1.0, 0)), E_)
sched(CHIP, [(0, 'idle', 1), (T_T1 + 0.2, 'win', 1.0), (T_T1 + 4, 'idle', 1), (T_KFALL + 0.5, 'win', 1.1)])
sched(BASIL, [(0, 'idle', 1)])

# ================================================================ the interview microphone
MIC = bpy.data.objects.new('mic', None)
COL.objects.link(MIC)
box('mic_handle', (0.07, 0.07, 0.6), (0, 0, -0.3), DARK, parent=MIC)
sphere('mic_head', 0.13, (0, 0, 0.1), mat('mic_foam', (0.03, 0.03, 0.035), 0.95), 16).parent = MIC
box('mic_flag', (0.26, 0.26, 0.2), (0, 0, -0.16), GOLD, parent=MIC)
MIC.rotation_euler = (0.35, -0.5, 0)
for t, p in ((T_INT - 0.2, PEPE_HEAD + Vector((1.6, 1.4, -2.2))), (T_INT + 0.35, PEPE_HEAD + Vector((0.72, 0.7, -0.92))),
             (T_INT + 0.5, PEPE_HEAD + Vector((0.68, 0.64, -0.86)))):
    MIC.location = p
    key(MIC, 'location', F(t))
show(MIC, F(T_INT - 0.2))

# ================================================================ stock-footage explosions on cards (render_edl.py drives their frames)
CARDS = []


def fx_card(name, clipfile, loc, height, t0, strength=4.0, light=0.0):
    """A camera-facing card playing `clipfile` in real time from animation time t0 (see render_edl.py)."""
    img = bpy.data.images.load(os.path.join(FXD, clipfile))
    w_, h_ = img.size
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (height * w_ / h_, height, 1)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt_ = m.node_tree
    nt_.nodes.clear()
    out = nt_.nodes.new('ShaderNodeOutputMaterial')
    tex = nt_.nodes.new('ShaderNodeTexImage')
    tex.name = 'clip'
    tex.image = img
    tex.extension = 'CLIP'
    tex.image_user.frame_duration = img.frame_duration
    tex.image_user.frame_start = 1
    tex.image_user.use_auto_refresh = True
    em = nt_.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = strength
    tr = nt_.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt_.nodes.new('ShaderNodeMixShader')
    bw = nt_.nodes.new('ShaderNodeRGBToBW')
    gain = nt_.nodes.new('ShaderNodeMath')
    gain.operation = 'MULTIPLY'
    gain.inputs[1].default_value = 2.5
    gain.use_clamp = True
    nt_.links.new(tex.outputs['Color'], em.inputs['Color'])
    nt_.links.new(tex.outputs['Color'], bw.inputs[0])
    nt_.links.new(bw.outputs[0], gain.inputs[0])
    nt_.links.new(gain.outputs[0], mix.inputs['Fac'])
    nt_.links.new(tr.outputs[0], mix.inputs[1])
    nt_.links.new(em.outputs[0], mix.inputs[2])
    nt_.links.new(mix.outputs[0], out.inputs['Surface'])
    o.data.materials.append(m)
    o.visible_shadow = False
    c = o.constraints.new('TRACK_TO')
    c.target = cam
    c.track_axis = 'TRACK_Z'
    c.up_axis = 'UP_Y'
    CARDS.append(dict(name=name, t0=t0, n=img.frame_duration, fps=60.0))
    return o


# ================================================================ the edit
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
COL.objects.link(cam)
sc.camera = cam
cam.data.sensor_width = 36
cam.data.dof.use_dof = True
cam.data.clip_end = 3000
cam.data.clip_start = 0.05

EXP = 'explosion.mp4'
fx_card('fx_t1', EXP, (3.5, -25.5, 4.6), 11.0, T_T1 - 0.08, 1.7)
fx_card('fx_t2', EXP, (14.5, -25.5, 4.6), 11.0, T_T2 - 0.08, 1.7)
fx_card('fx_walk', EXP, (11.9, -24.6, 4.4), 9.0, T_WALK + 5.35, 1.8)
fx_card('fx_walk2', EXP, (9.8, -27.0, 4.0), 8.0, T_WALK + 6.3, 1.7)
fx_card('fx_king', EXP, (9.0, -2.5, 6.5), 17.0, T_KFALL - 0.08, 1.8)
boomL = bpy.data.objects.new('walk_boom', bpy.data.lights.new('walk_boom', 'POINT'))
COL.objects.link(boomL)
boomL.location = (11.9, -24.0, 4.0)
boomL.data.color = (1.0, 0.55, 0.2)
boomL.data.shadow_soft_size = 2.0
for t, e in ((T_WALK + 5.3, 0), (T_WALK + 5.5, 26000), (T_WALK + 6.0, 12000), (T_WALK + 6.4, 22000), (T_WALK + 7.6, 0)):
    boomL.data.energy = e
    boomL.data.keyframe_insert('energy', frame=F(t))

SHOTS = []
_t = [0.0]
CUES = []
LOWER = []
EV = {}
GFX = []                # broadcast graphics events for finish.py: (kind, t0, t1, data)


def SH(name, dur, a0, s, p0, p1, l0, l1, lens, fstop=4.0, shake=0.0, lens1=None, ec=0, focus=None, hand=None, live=True):
    SHOTS.append(dict(name=name, t0=round(_t[0], 4), t1=round(_t[0] + dur, 4), a0=a0, s0=s, s1=s, p0=list(p0), p1=list(p1),
                      l0=list(l0), l1=list(l1), lens=lens, lens1=lens1 or lens, fstop=fstop, shake=shake, ec=ec, focus=focus,
                      hand=hand, live=live))
    _t[0] += dur


def now():
    return _t[0]


def t0():
    return SHOTS[-1]['t0']


def say(i, t):
    CUES.append((i, round(t, 3), round(t + VO[i]['dur'], 3)))
    return t + VO[i]['dur']


def ft(a, k=-1):
    s = SHOTS[k]
    return s['t0'] + (a - s['a0']) / s['s0']


CALM = ('INVESTIGATION', 0.35)
TIGHT = ('THE_CLOSEUP', 0.3)
LOOSE = ('INVESTIGATION', 0.7)

# --- 1. opening
SH('aerial', 1.3 + D('c01') + 0.3, 1.0, 1, (52, -74, 40), (38, -58, 27), (9, -16, 7), (9, -16, 5), 24, 8.0, hand=None)
say('c01', t0() + 1.3)
GFX.append(('title', t0() + 0.3, now() - 0.2, None))
d_ = 0.3 + D('b01') + 0.45
SH('booth', d_, 8.0, 1, BOOTH + Vector((-2.35, -1.5, 2.55)), BOOTH + Vector((-2.3, -1.2, 2.5)), (6, -16, 1.0), (6, -16, 1.0), 20, 5.6,
   focus=3.2, hand=CALM)
say('b01', t0() + 0.3)
GFX.append(('names', t0() + 0.5, now() - 0.3, None))

# --- 2. tale of the tape
SH('giga hero', D('c02') + 0.5, 13.0, 1, (12.6, -11.5, 1.6), (12.2, -10.6, 1.9), GIGA_HEAD + Vector((0, 0, -0.9)), GIGA_HEAD + Vector((0, 0, -0.7)), 75,
   2.8, hand=CALM)
say('c02', t0() + 0.2)
GFX.append(('card_giga', t0() + 0.5, None, None))
SH('giga close', D('b02') + 0.5, 16.5, 1, (11.4, -9.8, 5.3), (11.0, -9.2, 5.5), GIGA_HEAD + Vector((0, 0, -0.35)), GIGA_HEAD + Vector((0, 0, -0.3)), 105, 2.8,
   hand=TIGHT)
say('b02', t0() + 0.2)
GFX[-1] = ('card_giga', GFX[-1][1], now() - 0.25, None)
SH('pepe hero', D('c03') + 0.5, 6.0, 1, (5.4, -20.0, 1.6), (5.8, -20.8, 1.9), PEPE_HEAD + Vector((0, 0, -0.9)), PEPE_HEAD + Vector((0, 0, -0.7)), 75, 2.8,
   hand=CALM)
say('c03', t0() + 0.2)
GFX.append(('card_pepe', t0() + 0.5, None, None))
SH('pepe close', D('b03') + 0.5, 9.0, 1, (7.0, -21.8, 6.6), (7.3, -22.4, 6.8), PEPE_HEAD + Vector((0, 0, -0.3)), PEPE_HEAD + Vector((0, 0, -0.25)), 105, 2.8,
   hand=TIGHT)
say('b03', t0() + 0.2)
GFX[-1] = ('card_pepe', GFX[-1][1], now() - 0.25, None)

# --- 3. kick-off: the Whale
SH('kickoff', D('c04') + 0.45, T_KICK - 0.35, 1, (-9.5, -14.0, 13.5), (-9.0, -14.5, 12.5), (4.5, -10.5, 0.5), (4.2, -13.0, 0.5), 32, 5.6, hand=CALM)
say('c04', t0() + 0.15)
EV['kick'] = ft(T_KICK)
EV['whale_land'] = ft(T_KICK + 0.6)
d_ = D('b04') + 0.6
SH('whale bridge', d_, T_SWAT - 0.78 * d_, 1, (-2.4, -18.6, 1.1), (-1.9, -18.2, 1.25), (3.5, -15.4, 2.0), (3.5, -15.6, 2.0), 40, 2.8, 0.25, hand=LOOSE)
say('b04', t0() + 0.15)
EV['swat'] = ft(T_SWAT)
SH('pepe nothing', D('c05') + 0.45, T_SWAT + 2.0, 1, (6.3, -18.9, 4.6), (6.4, -19.3, 4.7), PEPE_HEAD + Vector((0, 0, -0.7)), PEPE_HEAD + Vector((0, 0, -0.7)), 85,
   2.8, hand=CALM)
say('c05', t0() + 0.15)
SH('pepe holding', D('b05') + 0.55, T_SWAT + 6.0, 1, (8.2, -20.4, 7.2), (8.3, -21.0, 7.25), PEPE_HEAD + Vector((0, 0, -0.1)), PEPE_HEAD + Vector((0, 0, -0.1)), 180,
   2.8, hand=TIGHT)
say('b05', t0() + 0.2)

# --- 4. the first tower, and the replay
SH('tower down', 0.75 + D('c06') + 0.55, T_T1 - 0.75, 1, (8.6, -20.6, 0.9), (8.9, -20.2, 0.9), (3.5, -25.2, 2.6), (3.5, -25.6, 3.0), 26, 4.0, 0.9, hand=LOOSE)
EV['t1'] = ft(T_T1)
say('c06', ft(T_T1) + 0.12)
d_ = D('b06') + 0.5
RS = 0.45
SH('replay', d_, T_T1 - RS * (d_ - 0.75), RS, (-5.2, -26.6, 2.2), (-5.0, -26.2, 2.3), (3.5, -25.0, 2.9), (3.5, -25.0, 2.9), 38, 4.0, live=False)
say('b06', t0() + 0.15)
GFX.append(('replay', t0(), None, None))
EV['t1_replay'] = ft(T_T1)
GFX.append(('tele_tower', t0() + 1.5, ft(T_T1) - 0.2, None))
GFX.append(('tele_whale', ft(T_T1) - 1.15, ft(T_T1) + 0.2, None))
d_ = D('c07') + 0.35 + D('b07') + 0.6
SH('whale burst', d_, T_T1 + 0.02, 0.3, (3.8, -32.4, 0.8), (3.75, -32.2, 0.85), (3.5, -26.0, 2.2), (3.5, -27.5, 2.2), 35, 2.8, 0.3, live=False)
e_ = say('c07', t0() + 0.3)
say('b07', e_ + 0.35)
GFX[-3] = ('replay', GFX[-3][1], now(), None)

# --- 5. the collapse
SH('second tower', 2.25, T_T2 - 0.55, 1, (26.5, -21.0, 8.5), (26.0, -21.5, 8.0), (14.5, -25.0, 2.0), (14.5, -25.5, 2.5), 40, 4.0, 0.9, hand=LOOSE)
EV['t2'] = ft(T_T2)
say('c08', ft(T_T2) + 0.1)
d_ = D('c08') - (2.25 - 0.65) + 0.35 + D('b08') + 0.5
SH('exits', d_, T_EXIT + 0.4, 1, (-4.6, EXIT_Y + 1.5, EXIT_Z + 1.7), (-4.3, EXIT_Y + 1.4, EXIT_Z + 1.7), (6.0, EXIT_Y, EXIT_Z + 1.3), (5.0, EXIT_Y, EXIT_Z + 1.3), 50, 2.8, hand=CALM)
say('b08', CUES[-1][2] + 0.35)

# --- 6. one card
d_ = D('c09') + 0.3
SH('one card', d_, T_CAST + 0.75 - d_, 1, (6.6, -20.2, 5.0), (6.9, -20.8, 5.2), PEPE_HEAD + Vector((0, 0, -0.6)), PEPE_HEAD + Vector((0, 0, -0.55)), 85, 2.8,
   hand=CALM)
say('c09', t0() + 0.1)
EV['cast'] = ft(T_CAST + 0.5)
U0 = Vector((WALK[0][0], WALK[0][1], 0))
SH('useless lands', 0.9 + D('c10') + 0.5, T_USE - 0.45, 1, U0 + Vector((3.4, 4.6, 0.55)), U0 + Vector((3.1, 4.2, 0.6)), U0 + Vector((0, 0, 1.0)),
   U0 + Vector((0, 0, 0.85)), 35, 2.8, 0.3, hand=CALM)
EV['use'] = ft(T_USE)
say('c10', ft(T_USE) + 0.75)
SH('useless close', D('b09') + 0.5, T_USE + 2.6, 1, U0 + Vector((1.2, 6.5, 1.0)), U0 + Vector((1.0, 5.6, 1.05)), U0 + Vector((0, 0, 0.95)),
   U0 + Vector((0, 0, 0.95)), 105, 2.8, hand=TIGHT)
say('b09', t0() + 0.2)
GFX.append(('lower_useless', t0() + 0.4, now() - 0.25, None))

# --- 7. the walk
d_ = D('c11') + 0.3 + D('b10') + 0.55
SH('walk wide', d_, T_WALK + 0.3, 1, (19.6, -25.6, 2.0), (19.0, -24.6, 2.1), (12.8, -21.4, 0.9), (14.5, -17.0, 0.9), 45, 4.0, hand=CALM)
e_ = say('c11', t0() + 0.2)
say('b10', e_ + 0.3)
EV['walk'] = t0()
SH('walk hero', 5.0, T_WALK + 4.75, 0.4, (14.5, -4.9, 0.65), (14.5, -5.2, 0.7), (14.5, -16.6, 0.9), (14.5, -15.3, 0.9), 120, 2.0, hand=TIGHT, live=True)
EV['hero'] = t0()
EV['hero_boom'] = [ft(T_WALK + 5.35), ft(T_WALK + 6.3)]
SH('squad pass', 3.2, T_WALK + 6.75, 0.5, (19.6, -13.2, 1.25), (19.4, -13.6, 1.25), (14.5, -14.4, 1.15), (14.5, -13.6, 1.15), 45, 2.8, 0.2, hand=LOOSE)
EV['pass'] = ft(T_WALK + 7.35)
SH('giga notices', 2.3, T_NOTICE - 0.9, 1, (10.6, -9.6, 5.6), (10.5, -9.3, 5.65), GIGA_HEAD + Vector((0, 0, -0.3)), GIGA_HEAD + Vector((0, 0, -0.3)), 135, 2.8,
   hand=TIGHT)
EV['notice'] = ft(T_NOTICE)
d_ = D('c12') + 0.55
SH('arrive', d_, T_ARR - d_ + 0.5, 1, (10.6, -11.6, 0.5), (10.2, -10.6, 0.55), (9.0, -3.8, 2.6), (9.0, -3.8, 2.9), 20, 4.0, hand=CALM)
say('c12', t0() + 0.15)

# --- 8. the tap
SH('tap', 2.2, T_TAP - 0.55, 1, (12.6, -7.6, 0.9), (12.4, -7.3, 0.9), (9.1, -4.9, 1.0), (9.1, -4.9, 1.0), 55, 2.8, hand=TIGHT)
EV['tap'] = ft(T_HIT)
SH('beat', 1.75, T_HIT + 0.2, 1, (9.0, -15.5, 2.6), (9.0, -15.5, 2.6), (9.0, -3.5, 3.6), (9.0, -3.5, 3.6), 40, 5.6)
EV['crack'] = t0() + 0.75
d_ = 0.75 + D('c13') + 0.55
SH('collapse', d_, T_KFALL - 0.12, 0.5, (4.2, -11.2, 0.7), (4.6, -11.8, 0.8), (9.0, -2.8, 4.2), (9.0, -3.2, 3.6), 22, 4.0, 1.0, hand=LOOSE)
EV['kfall'] = ft(T_KFALL)
say('c13', ft(T_KFALL) + 0.65)
d_ = D('b11') + 0.6
SH('useless wins', d_ * 0.5, T_KFALL + 3.2, 1, (11.6, -9.4, 0.7), (11.2, -9.0, 0.8), (9.0, -5.3, 1.0), (9.0, -5.3, 1.0), 50, 2.8, hand=LOOSE)
say('b11', t0() + 0.2)
EV['party'] = t0()
SH('stadium', d_ * 0.5, T_KFALL + 5.0, 1, (30, -44, 13), (33, -50, 20), (9, -14, 5), (9, -14, 7), 24, 8.0, hand=CALM)

# --- 9. the interview
d_ = 0.35 + D('c14') + 2.3 + D('b12') + 0.6
SH('interview', d_, T_INT - 0.3, 1, (10.5, -24.0, 7.2), (10.35, -24.4, 7.25), PEPE_HEAD + Vector((0.12, 0, -0.12)), PEPE_HEAD + Vector((0.12, 0, -0.12)), 100, 2.8,
   hand=TIGHT)
e_ = say('c14', t0() + 0.35)
say('b12', e_ + 2.3)
GFX.append(('lower_pepe', t0() + 0.3, now() - 0.3, None))

T_CARD = now()
e_ = say('c15', T_CARD + 0.6)
e_ = say('b13', e_ + 0.3)
T_FILM = e_ + 1.1

for a, b_ in zip(CUES, CUES[1:]):
    if b_[1] < a[2] + 0.05:
        print('VO OVERLAP', a, b_)
N_3D = int(round(T_CARD * FPS))
print('3D ends at', round(T_CARD, 2), 's, frames', N_3D, '; film', round(T_FILM, 2), 's')
for s in SHOTS:
    print(f"  {s['name']:14s} {s['t0']:6.2f}-{s['t1']:6.2f}  frames {int(s['t0'] * FPS) + 1}-{int(round(s['t1'] * FPS))}"
          f"  anim {s['a0']:.2f}-{s['a0'] + (s['t1'] - s['t0']) * s['s0']:.2f}")
json.dump(dict(fps=FPS, first=1, last=N_3D, t_card=T_CARD, t_film=T_FILM, shots=SHOTS, cues=CUES, lower=LOWER, ev=EV, gfx=GFX, cards=CARDS,
               subs={k: v['sub'] for k, v in VO.items()}, who={k: v['who'] for k, v in VO.items()},
               times=dict(kick=T_KICK, t1=T_T1, t2=T_T2, kfall=T_KFALL)),
          open(os.path.join(MYHERE, 'edl.json'), 'w'), indent=0)
sc.frame_set(1)
sc.render.use_persistent_data = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=False)
print('SAVED', OUT)
