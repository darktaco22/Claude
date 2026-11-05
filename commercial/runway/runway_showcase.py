"""
Runway: every MEME ROYALE character walks the catwalk, one by one, in front of a locked-off camera.
Each one walks in from the left, stops at centre, turns to the camera and strikes a pose (the game's own emote / win
clip), turns back and walks off to the right. The next character enters as the last one leaves. Behind them the
backdrop slowly cross-fades into each character's own world, and their name pops up in the game's Lilita One font.

    blender -b --factory-startup -P runway_showcase.py -- --models DIR
        [--order giga,pepe,moodeng,popcat] [--bgdir DIR] [--font ../assets/lilita.ttf] [--fit]
        [--w 1920 --h 1080 --samples 16 --fps 30 --step 1] [--gpu]
        [--save runway.blend] [--stills 60,200 OUTDIR] [--render OUTDIR]

--models  a folder of the game's character models (.glb). Every rigged model in it walks; unrigged props are skipped.
--order   who walks first (file names without .glb). Others follow in alphabetical order.
--bgdir   optional: an image named after a character (pepe.png / pepe.jpg) replaces its procedural backdrop.
--fit     scale every character to the same height (default keeps the models' relative sizes from the game).
--step    render every Nth frame (2 or 3 makes a quick preview).
"""
import bpy, math, os, sys, glob, re
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
A = lambda k, d=None, t=str: t(argv[argv.index(k) + 1]) if k in argv else d
HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.abspath(A("--models", os.path.join(HERE, "models")))
BGDIR = os.path.abspath(A("--bgdir")) if "--bgdir" in argv else None
FONT = os.path.abspath(A("--font", os.path.join(HERE, "..", "assets", "lilita.ttf")))
FPS = A("--fps", 30, int)
W, H = A("--w", 1920, int), A("--h", 1080, int)
S = lambda sec: int(round(sec * FPS))

# timing (seconds)
LEAD, WALK_IN, TURN, WALK_OUT, TAIL = 0.5, 2.0, 0.4, 2.0, 0.8
HOLD_MIN, HOLD_MAX = 1.8, 3.2          # the pose lasts as long as its clip, within these bounds
RUNWAY_TOP = 0.06                       # feet height

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
PREF = bpy.context.preferences.edit

def key(target, path, frame, interp="BEZIER", index=-1):
    """Insert a keyframe whose segment to the next key uses `interp` (version-safe: no fcurve access needed)."""
    PREF.keyframe_new_interpolation_type = interp
    target.keyframe_insert(path, frame=frame, index=index)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1,)

def mat(name, color, rough=0.4, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc(color); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m

# ---------------------------------------------------------------- who walks, and their worlds
# pattern: rays | stars | waves | dots | stripes | spot.   accent also tints the runway lights and the name title.
THEMES = {
    "giga":    dict(name="GIGA",     top="#3A3F4D", bottom="#0B0C10", accent="#FFC52E", pattern="rays"),    # gym-statue god rays
    "pepe":    dict(name="PEPE",     top="#2A0F6E", bottom="#0C2A14", accent="#7CFF6B", pattern="stars"),   # the swamp wizard's night sky
    "moodeng": dict(name="MOO DENG", top="#26C3D6", bottom="#0A3A50", accent="#FF8FB1", pattern="waves"),   # the hippo's water, bubbles
    "popcat":  dict(name="POPCAT",   top="#FF5FA2", bottom="#FF9F1C", accent="#FFF35C", pattern="dots"),    # pop-art halftone
}
FALLBACK = [  # characters not in the table get one of these, in turn
    dict(top="#5B2BD9", bottom="#14062E", accent="#FFC52E", pattern="spot"),
    dict(top="#FF4D4D", bottom="#3A0610", accent="#FFD166", pattern="stripes"),
    dict(top="#2ED47A", bottom="#06301C", accent="#E6FF5C", pattern="rays"),
    dict(top="#3B6BFF", bottom="#0A1240", accent="#7FE7FF", pattern="stars"),
    dict(top="#FF8A3D", bottom="#3A1606", accent="#FFE29A", pattern="dots"),
    dict(top="#C03CFF", bottom="#22063A", accent="#FF9EF5", pattern="waves"),
]
KNOWN_ORDER = ["giga", "pepe", "moodeng", "popcat"]
slug = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

paths = sorted(glob.glob(os.path.join(MODELS, "*.glb")) + glob.glob(os.path.join(MODELS, "*.gltf")))
if not paths:
    sys.exit(f"no .glb models in {MODELS}")
by_slug = {slug(os.path.splitext(os.path.basename(p))[0]): p for p in paths}
wanted = [slug(x) for x in A("--order", "").split(",") if x.strip()] or [k for k in KNOWN_ORDER if k in by_slug]
order = [k for k in wanted if k in by_slug] + sorted(k for k in by_slug if k not in wanted)

def find_action(actions, words):
    for w in words:
        for a in actions:
            n = a.name.lower()
            if n == w or n.startswith(w + "_") or n.startswith(w + ".") or n.startswith(w):
                return a
    return None

# ---------------------------------------------------------------- import every character
cast = []
fb = 0
for k in order:
    before_obj, before_act = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=by_slug[k])
    objs = [o for o in bpy.data.objects if o not in before_obj]
    acts = [a for a in bpy.data.actions if a not in before_act]
    rig = next((o for o in objs if o.type == "ARMATURE"), None)
    if rig is None:
        print(f"[runway] skip {k}: no rig (a prop, not a character)")
        for o in objs: bpy.data.objects.remove(o)
        continue
    under = lambda o: o is rig or (o.parent is not None and under(o.parent))
    for o in list(objs):   # the game's selection sphere and other loose helper meshes
        if o.type == "MESH" and not under(o):
            objs.remove(o); bpy.data.objects.remove(o)
    walk = find_action(acts, ["walk", "run", "move", "idle"])
    pose = find_action(acts, ["emote", "win", "victory", "dance", "taunt", "celebrate", "attack1", "attack", "idle"])
    if walk is None or pose is None:
        print(f"[runway] skip {k}: no usable animation clips ({[a.name for a in acts]})")
        for o in objs: bpy.data.objects.remove(o)
        continue
    th = dict(THEMES.get(k) or dict(FALLBACK[fb % len(FALLBACK)], name=k.upper()))
    if k not in THEMES: fb += 1
    walker = bpy.data.objects.new(f"Walker_{k}", None); sc.collection.objects.link(walker)
    fit = bpy.data.objects.new(f"Fit_{k}", None); sc.collection.objects.link(fit); fit.parent = walker
    for o in objs:
        if o.parent is None:
            o.parent = fit
    # measure the model as imported
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.type == "MESH":
            oe = o.evaluated_get(dg)
            pts += [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    cast.append(dict(key=k, rig=rig, objs=objs, walk=walk, pose=pose, theme=th, walker=walker, fit=fit, lo=lo, hi=hi))
    print(f"[runway] {k}: walk={walk.name} pose={pose.name} size={tuple(round(v, 2) for v in hi - lo)}")
if not cast:
    sys.exit("no rigged characters found")

# sizes: keep the game's relative scale (tallest = 2.0 m, nobody under 1.1 m), or --fit everyone to 1.8 m
tallest = max(c["hi"].z - c["lo"].z for c in cast)
for c in cast:
    h = c["hi"].z - c["lo"].z
    wid = max(c["hi"].x - c["lo"].x, c["hi"].y - c["lo"].y)
    s = 1.8 / h if "--fit" in argv else max(2.0 / tallest, 1.1 / h)
    s = min(s, 2.6 / max(wid, 1e-6))
    c["fit"].scale = (s, s, s)
    c["fit"].location = (-(c["lo"].x + c["hi"].x) / 2 * s, -(c["lo"].y + c["hi"].y) / 2 * s, -c["lo"].z * s)
    c["s"], c["half_w"] = s, wid * s / 2

# ---------------------------------------------------------------- the schedule
cur = S(LEAD) + 1
for c in cast:
    clip = c["pose"].frame_range[1] - c["pose"].frame_range[0]
    hold = int(min(max(clip, S(HOLD_MIN)), S(HOLD_MAX)))
    c["t0"] = cur
    c["a"] = c["t0"] + S(WALK_IN)        # arrives at centre, starts turning to us
    c["p0"] = c["a"] + S(TURN)           # facing the camera, posing
    c["p1"] = c["p0"] + hold             # pose ends, turns back
    c["d"] = c["p1"] + S(TURN)           # walks off
    c["e"] = c["d"] + S(WALK_OUT)        # gone
    c["hold"], c["clip"] = hold, clip
    cur = c["d"]                         # the next one enters as this one leaves
END = cast[-1]["e"] + S(TAIL)
sc.frame_start, sc.frame_end = 1, END
sc.frame_step = A("--step", 1, int)

# ---------------------------------------------------------------- motion: walk in, turn, pose, turn, walk off
for c in cast:
    wk, rig = c["walker"], c["rig"]
    x_off = 2.75 + c["half_w"] + 0.3      # just out of frame
    wk.location = (-40, 0, RUNWAY_TOP); wk.rotation_euler = (0, 0, math.radians(90))
    if c["t0"] > 2: key(wk, "location", 1, "CONSTANT", 0)
    for f, x, ip in ((c["t0"], -x_off, "LINEAR"), (c["t0"] + S(WALK_IN - 0.5), -0.55, "BEZIER"), (c["a"], 0.0, "BEZIER"),
                     (c["d"], 0.0, "BEZIER"), (c["d"] + S(0.5), 0.55, "LINEAR"), (c["e"], x_off, "CONSTANT"), (c["e"] + 1, 40.0, "CONSTANT")):
        wk.location.x = x; key(wk, "location", f, ip, 0)
    for f, deg in ((c["t0"], 90), (c["a"], 90), (c["p0"], 0), (c["p1"], 0), (c["d"], 90)):
        wk.rotation_euler.z = math.radians(deg); key(wk, "rotation_euler", f, "BEZIER", 2)
    # only render each character while it's on stage
    for o in c["objs"]:
        o.hide_render = True; key(o, "hide_render", 1, "CONSTANT")
        o.hide_render = False; key(o, "hide_render", max(1, c["t0"] - 2), "CONSTANT")
        o.hide_render = True; key(o, "hide_render", c["e"] + 2, "CONSTANT")
    # the clips: walk underneath the whole time, the pose on top with soft blends
    ad = rig.animation_data or rig.animation_data_create()
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    ad.action = None
    def strip(track, name, start, action):
        st = track.strips.new(name, int(start), action)
        if hasattr(st, "action_slot") and getattr(st, "action_slot", None) is None and getattr(action, "slots", None):
            try: st.action_slot = action.slots[0]
            except Exception: pass
        return st
    tw = ad.nla_tracks.new(); tw.name = "walk"
    sw = strip(tw, "walk", c["t0"] - S(0.2), c["walk"])
    wl = max(1.0, c["walk"].frame_range[1] - c["walk"].frame_range[0])
    sw.repeat = max(1.0, (c["e"] + 2 - (c["t0"] - S(0.2))) / wl)
    tp = ad.nla_tracks.new(); tp.name = "pose"
    sp = strip(tp, "pose", c["a"] - 3, c["pose"])
    span = c["p1"] + 4 - (c["a"] - 3)
    if c["clip"] >= span:
        sp.action_frame_end = sp.action_frame_start + span
    else:
        sp.repeat = span / max(1.0, c["clip"])
    sp.extrapolation = "NOTHING"; sp.blend_in = 8; sp.blend_out = 8

# ---------------------------------------------------------------- the set
world = bpy.data.worlds.new("studio"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = hexc("#0A0612")
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 1.5, 0)); floor = bpy.context.active_object
floor.scale = (40, 12, 1); floor.data.materials.append(mat("floor", "#0E0A18", rough=0.35))
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, RUNWAY_TOP / 2)); runway = bpy.context.active_object
runway.scale = (18, 1.5, RUNWAY_TOP); runway.data.materials.append(mat("runway", "#1C1528", rough=0.16))

# runway edge lights and rim lights in the current character's accent colour
strip_m = bpy.data.materials.new("runway_lights"); strip_m.use_nodes = True
snt = strip_m.node_tree; snt.nodes.clear()
s_out = snt.nodes.new("ShaderNodeOutputMaterial"); s_em = snt.nodes.new("ShaderNodeEmission")
s_em.inputs["Strength"].default_value = 4.0; snt.links.new(s_em.outputs[0], s_out.inputs[0])
for yy in (-0.76, 0.76):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, yy, RUNWAY_TOP + 0.004))
    e = bpy.context.active_object; e.scale = (18, 0.03, 0.012); e.data.materials.append(strip_m)

def light(name, kind, loc, at, energy, color=(1, 1, 1), size=1.0):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); sc.collection.objects.link(L)
    L.location = loc; L.rotation_euler = (Vector(at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    L.data.energy = energy; L.data.color = color
    if kind == "AREA": L.data.size = size
    return L
light("key", "AREA", (-2.4, -3.4, 3.4), (0, 0, 1.0), 520, (1.0, 0.96, 0.9), 2.5)
light("fill", "AREA", (2.8, -3.0, 1.6), (0, 0, 1.0), 140, (0.85, 0.9, 1.0), 3.0)
rimL = light("rimL", "AREA", (2.4, 1.8, 2.8), (0, 0, 1.2), 420, (1, 1, 1), 1.6)
rimR = light("rimR", "AREA", (-2.4, 1.8, 2.8), (0, 0, 1.2), 380, (1, 1, 1), 1.6)

# ---------------------------------------------------------------- the backdrop: one world per character, cross-faded
# sized to fill the locked-off camera's view, so the plane's UVs are the frame (camera: see below)
asp = W / H
CAM_LOC, CAM_AT, LENS, BACK_Y = Vector((0, -7.2, 1.3)), Vector((0, 0, 1.15)), 50.0, 4.6
dist = BACK_Y - CAM_LOC.y
bw = dist * 36.0 / LENS * 1.06; bh = bw / asp
bz = CAM_LOC.z + (CAM_AT.z - CAM_LOC.z) * dist / (CAM_AT.y - CAM_LOC.y)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, BACK_Y, bz), rotation=(math.pi / 2, 0, 0))
backdrop = bpy.context.active_object; backdrop.scale = (bw, bh, 1)
bm = bpy.data.materials.new("backdrop"); bm.use_nodes = True
nt = bm.node_tree; nt.nodes.clear(); L = nt.links.new
NS = bpy.types.NodeSocket

def feed(inp, v):
    if isinstance(v, NS): L(v, inp)
    else: inp.default_value = v

def M(op, a, b=0.0):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op; feed(n.inputs[0], a); feed(n.inputs[1], b); return n.outputs[0]

def V(op, a, b=(0, 0, 0), out="Vector"):
    n = nt.nodes.new("ShaderNodeVectorMath"); n.operation = op; feed(n.inputs[0], a); feed(n.inputs[1], b); return n.outputs[out]

def MR(v, a, b, c, d):
    n = nt.nodes.new("ShaderNodeMapRange"); n.clamp = True; feed(n.inputs["Value"], v)
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = c, d
    return n.outputs[0]

def MIX(fac, c1, c2):
    """Colour mix (the Mix node in RGBA mode). Returns (factor socket, result socket)."""
    n = nt.nodes.new("ShaderNodeMix"); n.data_type = "RGBA"; n.clamp_factor = True
    ins = {s.identifier: s for s in n.inputs}; outs = {s.identifier: s for s in n.outputs}
    feed(ins["Factor_Float"], fac); feed(ins["A_Color"], c1); feed(ins["B_Color"], c2)
    return ins["Factor_Float"], outs["Result_Color"]

def XYZ(x, y, z=0.0):
    n = nt.nodes.new("ShaderNodeCombineXYZ"); feed(n.inputs["X"], x); feed(n.inputs["Y"], y); feed(n.inputs["Z"], z); return n.outputs[0]

def RAMP(v, stops):
    n = nt.nodes.new("ShaderNodeValToRGB"); cr = n.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], hexc(stops[0][1])
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], hexc(stops[-1][1])
    for p, col in stops[1:-1]:
        e = cr.elements.new(p); e.color = hexc(col)
    feed(n.inputs[0], v); return n.outputs["Color"]

tc = nt.nodes.new("ShaderNodeTexCoord")
P = V("MULTIPLY", tc.outputs["UV"], (asp, 1.0, 1.0))                     # square units across the plane
C = V("SUBTRACT", P, (asp / 2, 0.45, 0.0))                              # centred on the posing character's chest
Py = nt.nodes.new("ShaderNodeSeparateXYZ"); L(P, Py.inputs[0]); Py = Py.outputs
Cs = nt.nodes.new("ShaderNodeSeparateXYZ"); L(C, Cs.inputs[0]); Cs = Cs.outputs
R = V("LENGTH", C, out="Value")
clock = nt.nodes.new("ShaderNodeValue"); T = clock.outputs[0]               # seconds, keyed linearly over the shot
T.default_value = 0.0; key(T, "default_value", 1, "LINEAR")
T.default_value = END / FPS; key(T, "default_value", END, "LINEAR")

def world_of(c):
    th = c["theme"]
    if BGDIR:
        for ext in ("png", "jpg", "jpeg", "webp"):
            f = os.path.join(BGDIR, f"{c['key']}.{ext}")
            if os.path.exists(f):   # the artist's own background, with a slow drift
                mp = nt.nodes.new("ShaderNodeMapping"); L(tc.outputs["UV"], mp.inputs["Vector"])
                L(XYZ(M("MULTIPLY", T, 0.006), 0.0), mp.inputs["Location"]); mp.inputs["Scale"].default_value = (0.92, 0.92, 1)
                im = nt.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(f); im.extension = "EXTEND"
                L(mp.outputs[0], im.inputs["Vector"]); return im.outputs["Color"]
    acc = hexc(th["accent"]); white = (1, 1, 1, 1)
    col = RAMP(Py["Y"], [(0.0, th["bottom"]), (1.0, th["top"])])
    pat = th["pattern"]
    if pat == "rays":       # a slow-turning sunburst
        ang = M("ARCTAN2", Cs["Y"], Cs["X"])
        wav = M("SINE", M("ADD", M("MULTIPLY", ang, 14.0), M("MULTIPLY", T, 0.25)))
        col = MIX(MR(wav, 0.25, 0.5, 0.0, 0.4), col, acc)[1]
    elif pat == "stars":    # a drifting nebula and stars
        vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 70; L(P, vo.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); L(vo.outputs["Color"], sep.inputs[0])
        star = M("MULTIPLY", MR(vo.outputs["Distance"], 0.0, 0.06, 1.0, 0.0), M("GREATER_THAN", sep.outputs[0], 0.82))
        no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 2.4; no.inputs["Detail"].default_value = 6
        L(V("ADD", P, XYZ(M("MULTIPLY", T, 0.03), 0.0)), no.inputs["Vector"])
        col = MIX(MR(no.outputs["Fac"], 0.48, 0.74, 0.0, 0.5), col, acc)[1]
        col = MIX(star, col, white)[1]
    elif pat == "waves":    # rolling water and rising bubbles
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Y"
        wv.inputs["Scale"].default_value = 2.2; wv.inputs["Distortion"].default_value = 6; wv.inputs["Detail"].default_value = 3
        L(V("ADD", P, XYZ(0.0, M("MULTIPLY", T, 0.05))), wv.inputs["Vector"])
        col = MIX(MR(wv.outputs["Fac"], 0.55, 0.85, 0.0, 0.45), col, acc)[1]
        vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 9
        L(V("ADD", P, XYZ(0.0, M("MULTIPLY", T, -0.12))), vo.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); L(vo.outputs["Color"], sep.inputs[0])
        bub = M("MULTIPLY", MR(vo.outputs["Distance"], 0.0, 0.09, 0.6, 0.0), M("GREATER_THAN", sep.outputs[0], 0.7))
        col = MIX(bub, col, white)[1]
    elif pat == "dots":     # pop-art halftone, bigger dots toward the floor, sliding
        vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 16; vo.inputs["Randomness"].default_value = 0.0
        L(V("ADD", P, XYZ(M("MULTIPLY", T, 0.04), M("MULTIPLY", T, 0.02))), vo.inputs["Vector"])
        r = MR(Py["Y"], 0.0, 1.0, 0.42, 0.08)
        dot = MR(M("SUBTRACT", vo.outputs["Distance"], r), -0.03, 0.03, 0.55, 0.0)
        col = MIX(dot, col, acc)[1]
    elif pat == "stripes":  # sliding diagonal stripes
        wav = M("SINE", M("ADD", M("MULTIPLY", M("ADD", Py["X"], Py["Y"]), 10.0), M("MULTIPLY", T, 0.6)))
        col = MIX(MR(wav, 0.55, 0.8, 0.0, 0.35), col, acc)[1]
    else:                   # "spot": a soft spotlight pool
        col = MIX(MR(R, 0.0, 0.7, 0.45, 0.0), col, acc)[1]
    return col

# chain: world 0, then each next world mixed in over the previous one while its character walks in
acc_sock = s_em.inputs["Color"]
out_col = world_of(cast[0])
for i, c in enumerate(cast):
    col_acc = hexc(c["theme"]["accent"])
    f_from = (cast[i - 1]["d"] - S(0.3)) if i else 1
    f_to = c["p0"]
    if i:
        fac, mixed = MIX(0.0, out_col, world_of(c))
        fac.default_value = 0.0; key(fac, "default_value", f_from, "BEZIER")
        fac.default_value = 1.0; key(fac, "default_value", f_to, "BEZIER")
        out_col = mixed
    prev_acc = hexc(cast[i - 1]["theme"]["accent"]) if i else col_acc
    for f, ca in (((f_from, prev_acc), (f_to, col_acc)) if i else ((1, col_acc),)):   # runway lights and rims follow the fade
        acc_sock.default_value = ca; key(acc_sock, "default_value", f, "BEZIER")
        for rl, mixw in ((rimL, 0.75), (rimR, 0.45)):
            rl.data.color = tuple(1 - mixw + mixw * v for v in ca[:3]); key(rl.data, "color", f, "BEZIER")
# a soft glow behind the character, and a vignette
out_col = MIX(MR(R, 0.0, 0.65, 0.22, 0.0), out_col, (1, 1, 1, 1))[1]
out_col = MIX(MR(R, 0.55, 1.3, 0.0, 0.75), out_col, (0, 0, 0, 1))[1]
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0; L(out_col, em.inputs["Color"])
o = nt.nodes.new("ShaderNodeOutputMaterial"); L(em.outputs[0], o.inputs[0])
backdrop.data.materials.append(bm)
backdrop.visible_shadow = False

# ---------------------------------------------------------------- name titles
font = bpy.data.fonts.load(FONT) if os.path.exists(FONT) else None
for c in cast:
    cu = bpy.data.curves.new(f"title_{c['key']}", "FONT"); cu.body = c["theme"]["name"]
    if font: cu.font = font
    cu.align_x, cu.align_y = "CENTER", "CENTER"; cu.size = 0.40; cu.extrude = 0.025
    t = bpy.data.objects.new(f"Title_{c['key']}", cu); sc.collection.objects.link(t)
    t.location = (0, 0.9, 2.42); t.rotation_euler = (math.pi / 2, 0, 0)
    tm = bpy.data.materials.new(f"title_{c['key']}"); tm.use_nodes = True
    tn = tm.node_tree; tn.nodes.clear()
    to = tn.nodes.new("ShaderNodeOutputMaterial"); te = tn.nodes.new("ShaderNodeEmission"); tt = tn.nodes.new("ShaderNodeBsdfTransparent")
    tx = tn.nodes.new("ShaderNodeMixShader")
    te.inputs["Color"].default_value = hexc(c["theme"]["accent"]); te.inputs["Strength"].default_value = 2.4
    tn.links.new(tt.outputs[0], tx.inputs[1]); tn.links.new(te.outputs[0], tx.inputs[2]); tn.links.new(tx.outputs[0], to.inputs[0])
    cu.materials.append(tm); t.visible_shadow = False
    fac = tx.inputs[0]
    for f, v in ((1, 0.0), (c["p0"], 0.0), (c["p0"] + S(0.25), 1.0), (c["p1"], 1.0), (c["p1"] + S(0.25), 0.0)):
        fac.default_value = v; key(fac, "default_value", f, "BEZIER")
    for f, s in ((c["p0"], 0.7), (c["p0"] + S(0.2), 1.06), (c["p0"] + S(0.32), 1.0)):
        t.scale = (s, s, s); key(t, "scale", f, "BEZIER")
    t.hide_render = True; key(t, "hide_render", 1, "CONSTANT")
    t.hide_render = False; key(t, "hide_render", c["p0"] - 1, "CONSTANT")
    t.hide_render = True; key(t, "hide_render", c["p1"] + S(0.3), "CONSTANT")
PREF.keyframe_new_interpolation_type = "BEZIER"

# ---------------------------------------------------------------- the camera: locked off, runway at eye level
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = LENS; cam.data.sensor_fit = "HORIZONTAL"; cam.data.sensor_width = 36.0; cam.location = CAM_LOC
cam.rotation_euler = (CAM_AT - CAM_LOC).to_track_quat("-Z", "Y").to_euler()

# ---------------------------------------------------------------- render
r = sc.render
r.engine = "CYCLES"; sc.cycles.device = "CPU"
if "--gpu" in argv:
    try:
        cp = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                cp.compute_device_type = kind; cp.get_devices()
                if any(d.type == kind for d in cp.devices):
                    for d in cp.devices: d.use = True
                    sc.cycles.device = "GPU"; break
            except Exception: pass
    except Exception: pass
sc.cycles.samples = A("--samples", 16, int); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3; sc.cycles.adaptive_threshold = 0.05; r.use_persistent_data = True
r.resolution_x, r.resolution_y, r.resolution_percentage = W, H, 100
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"
r.image_settings.file_format = "PNG"
print(f"[runway] {len(cast)} characters, {END} frames ({END / FPS:.1f} s at {FPS} fps), device {sc.cycles.device}")
for c in cast:
    print(f"[runway]   {c['theme']['name']:<12} frames {c['t0']}-{c['e']}  pose {c['p0']}-{c['p1']}  scale {c['s']:.3f}")
if "--save" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(A("--save")))
if "--stills" in argv:
    fr = [int(x) for x in argv[argv.index("--stills") + 1].split(",")]; od = argv[argv.index("--stills") + 2]; os.makedirs(od, exist_ok=True)
    for f in fr:
        sc.frame_set(f); r.filepath = os.path.join(os.path.abspath(od), f"runway_{f:04d}.png"); bpy.ops.render.render(write_still=True)
if "--render" in argv:
    r.use_overwrite = False; r.use_placeholder = True
    r.filepath = os.path.join(os.path.abspath(A("--render")), "f_"); bpy.ops.render.render(animation=True)
