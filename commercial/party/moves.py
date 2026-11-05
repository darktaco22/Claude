"""
Animation for MEME ROYALE characters at the party: the game's models share Mixamo's skeleton (T-pose rest, facing -Y), so
every move here is written once and fitted to each character's own proportions.

A character is driven by IK: hands and feet go to targets (in the character's own space), the hips ride up and down on top
of planted feet, the spine and head turn. Each move is a function of time returning those targets; `bake()` keyframes it.
"""
import bpy, math
from mathutils import Vector, Quaternion, Euler

TAU = math.tau
BPM = 129.2          # the party track, measured with librosa
BEAT = 60.0 / BPM
BEAT0 = 0.07         # its first beat (s)

def tri(x):        # 0..1..0 over one period
    x = x % 1.0
    return 1 - abs(2 * x - 1)

def bounce(t, phase=0.0):   # a beat bounce: 1 on the beat, easing back up
    x = (((t - BEAT0) / BEAT) + phase) % 1.0
    return math.sin(math.pi * x) ** 2

class Char:
    """One character: its rig, a controller empty (place/turn this), and IK targets in the controller's space."""
    def __init__(self, rig, name):
        self.rig, self.name = rig, name
        sc = bpy.context.scene
        self.ctrl = bpy.data.objects.new(name + "_ctrl", None); sc.collection.objects.link(self.ctrl)
        rig.parent = self.ctrl
        rig.animation_data_create(); rig.animation_data.action = None
        B = {b.name.split(":")[-1]: b for b in rig.data.bones}
        self.B = B
        need = ("LeftArm", "LeftForeArm", "LeftHand", "RightArm", "RightForeArm", "RightHand", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot", "Head", "Spine", "Spine1", "Spine2")
        self.ik = all(n in B for n in need)
        self.clip_actions = {a.name.split("_")[0]: a for a in bpy.data.actions if a.name.endswith("_" + rig.name)}
        if not self.ik:   # a skeleton of its own (a quadruped, a book): it plays the game's clips instead
            self.T = {}
            self.hip = Vector(B["Hips"].head_local); self.headp = Vector(B["Head"].head_local) if "Head" in B else self.hip + Vector((0, 0, 0.6))
            hz = max((rig.matrix_world @ Vector(b.tail_local)).z for b in rig.data.bones)
            self.shoulderL = self.shoulderR = Vector((0, 0, hz * 0.7)); self.arm = 0.4; self.leg = self.hip.z
            self.footL = self.footR = Vector((0, 0, 0)); self.handL = self.handR = self.shoulderL
            return
        head = lambda n: Vector(B[n].head_local)
        tail = lambda n: Vector(B[n].tail_local)
        self.hip = head("Hips")
        self.shoulderL, self.shoulderR = head("LeftArm"), head("RightArm")
        self.handL, self.handR = head("LeftHand"), head("RightHand")
        self.footL, self.footR = head("LeftFoot"), head("RightFoot")
        self.headp = head("Head")
        self.neck = head("Neck")
        self.arm = (self.handL - self.shoulderL).length
        self.leg = (self.hip.z - self.footL.z)
        self.height = max(self.headp.z, self.shoulderL.z) + 0.2
        self.T = {}
        for n in ("hand_L", "hand_R", "foot_L", "foot_R", "pole_L", "pole_R", "knee_L", "knee_R", "look"):
            e = bpy.data.objects.new(f"{name}_{n}", None); sc.collection.objects.link(e); e.parent = self.ctrl
            e.empty_display_size = 0.05; self.T[n] = e
        pb = rig.pose.bones
        for side, s in (("Left", "L"), ("Right", "R")):
            c = pb[f"mixamorig:{side}ForeArm"].constraints.new("IK")
            c.target = self.T["hand_" + s]; c.chain_count = 2; c.pole_target = self.T["pole_" + s]
            c.pole_angle = math.radians(-90 if s == "L" else -90)
            c = pb[f"mixamorig:{side}Leg"].constraints.new("IK")
            c.target = self.T["foot_" + s]; c.chain_count = 2; c.pole_target = self.T["knee_" + s]; c.pole_angle = math.radians(-90)
        c = pb["mixamorig:Head"].constraints.new("DAMPED_TRACK"); c.target = self.T["look"]; c.track_axis = "TRACK_Z"; c.influence = 0.7
        for n in ("Spine", "Spine1", "Spine2", "Hips"):
            pb["mixamorig:" + n].rotation_mode = "XYZ"
        self.default()

    # rest-relative helpers (character space: x its left, -y ahead, z up)
    def default(self):
        T = self.T
        T["foot_L"].location = self.footL; T["foot_R"].location = self.footR
        T["knee_L"].location = self.footL + Vector((0.05, -0.6, self.leg * 0.6))
        T["knee_R"].location = self.footR + Vector((-0.05, -0.6, self.leg * 0.6))
        T["pole_L"].location = self.shoulderL + Vector((0.2, 0.5, -0.3))
        T["pole_R"].location = self.shoulderR + Vector((-0.2, 0.5, -0.3))
        T["look"].location = self.headp + Vector((0, -2, 0))

    def arm_at(self, side, fwd, out, up):
        """A hand placed relative to its shoulder, in arm lengths: fwd (ahead), out (away from the body), up."""
        s = self.shoulderL if side == "L" else self.shoulderR
        sign = 1 if side == "L" else -1
        return s + Vector((sign * out * self.arm, -fwd * self.arm, up * self.arm))

    def play(self, clip, f0=1, speed=1.0):
        """Non-IK characters: loop one of the game's own clips from frame f0."""
        act = self.clip_actions.get(clip) or self.clip_actions.get("idle") or next(iter(self.clip_actions.values()))
        ad = self.rig.animation_data
        for pbn in self.rig.pose.bones:   # its clip drives it now, not the IK
            for cn in pbn.constraints: cn.mute = True
        tr = ad.nla_tracks.new(); st = tr.strips.new(act.name, f0, act)
        st.repeat = 40; st.scale = 1.0 / speed
        ad.action = None

    def key(self, f, pose):
        if not self.ik or pose.get("clip_driven"):
            if "loc" in pose: self.ctrl.location = pose["loc"]; self.ctrl.keyframe_insert("location", frame=f)
            if "rot" in pose: self.ctrl.rotation_euler = (pose.get("rx", 0.0), 0, pose["rot"]); self.ctrl.keyframe_insert("rotation_euler", frame=f)
            return
        """pose: dict with any of hand_L/hand_R/foot_L/foot_R/look (Vectors), hips (Vector offset), spine (forward bend rad),
        twist (rad), lean (sideways rad), and 'loc'/'rot' for the controller."""
        T, rig, pb = self.T, self.rig, self.rig.pose.bones
        for n in ("hand_L", "hand_R", "foot_L", "foot_R", "look"):
            if n in pose:
                T[n].location = pose[n]; T[n].keyframe_insert("location", frame=f)
        rig.location = pose.get("hips", Vector()); rig.keyframe_insert("location", frame=f)
        bend, twist, lean = pose.get("spine", 0.0), pose.get("twist", 0.0), pose.get("lean", 0.0)
        for n, k in (("Spine", 0.35), ("Spine1", 0.35), ("Spine2", 0.3)):
            b = pb["mixamorig:" + n]; b.rotation_euler = (bend * k, twist * k, lean * k)
            b.keyframe_insert("rotation_euler", frame=f)
        if "loc" in pose:
            self.ctrl.location = pose["loc"]; self.ctrl.keyframe_insert("location", frame=f)
        if "rot" in pose:
            self.ctrl.rotation_euler = (pose.get("rx", 0.0), 0, pose["rot"]); self.ctrl.keyframe_insert("rotation_euler", frame=f)

    CLIP_FOR = {"dance_bounce": "win", "dance_wave": "win", "dance_disco": "emote", "dance_step": "win", "dance_shuffle": "win",
                "hold_cup": "idle", "smoke": "idle", "chat": "idle", "kiss": "idle", "lean_over_table": "idle", "sit_bong": "idle",
                "swim": "idle", "cheer": "win", "tuck": "hit"}
    def bake(self, move, f0, f1, fps=30, step=2, **kw):
        if not self.ik:
            self.play(self.CLIP_FOR.get(move.__name__, "idle"), f0); return
        for f in range(f0, f1 + 1, step):
            self.key(f, move(self, (f - f0) / fps, **kw))

# ------------------------------------------------------------------------------------------------ the moves
# every move: (char, t seconds, **options) -> pose dict

def idle_feet(c, t, sway=0.0):
    return {"foot_L": c.footL, "foot_R": c.footR}

def dance_bounce(c, t, phase=0.0):
    """Fist pumps: knees on the beat, alternate fists punching up."""
    b = bounce(t, phase); k = ((t / BEAT) + phase) % 2.0
    up_l = 1.0 if k < 1 else 0.25
    return {**idle_feet(c, t), "hips": Vector((0, 0, -0.12 * c.leg * b)),
            "hand_L": c.arm_at("L", 0.25, 0.25, 0.95 * up_l), "hand_R": c.arm_at("R", 0.25, 0.25, 0.95 * (1.25 - up_l)),
            "spine": -0.1 * b, "look": c.headp + Vector((0, -2, 0.4))}

def dance_wave(c, t, phase=0.0):
    """Hands in the air, swaying side to side."""
    s = math.sin(TAU * (t / (2 * BEAT) + phase))
    return {**idle_feet(c, t), "hips": Vector((0.05 * c.leg * s, 0, -0.06 * c.leg * bounce(t, phase))),
            "hand_L": c.arm_at("L", 0.1, 0.25 + 0.2 * s, 0.9), "hand_R": c.arm_at("R", 0.1, 0.25 - 0.2 * s, 0.9),
            "lean": 0.25 * s, "look": c.headp + Vector((0.6 * s, -2, 0.8))}

def dance_disco(c, t, phase=0.0):
    """The disco point: right hand up to the sky, then down across the body, hips twisting."""
    x = ((t / (2 * BEAT)) + phase) % 1.0
    up = x < 0.5
    hr = c.arm_at("R", 0.2, 0.55, 0.85) if up else c.arm_at("R", 0.55, -0.45, -0.35)
    return {**idle_feet(c, t), "hips": Vector((0, 0, -0.08 * c.leg * bounce(t, phase))),
            "hand_R": hr, "hand_L": Vector((c.hip.x + 0.12, c.hip.y - 0.05, c.hip.z + 0.05)),
            "twist": 0.35 if up else -0.35, "look": c.headp + Vector((-1.2 if up else 0.6, -2, 1.0 if up else -0.4))}

def dance_step(c, t, phase=0.0):
    """Side step: feet stepping out and in, elbows bent, shoulders rolling."""
    k = ((t / BEAT) + phase) % 2.0
    out = tri(k / 2.0)
    lift = 0.08 * c.leg * max(0.0, math.sin(math.pi * (k % 1)))
    fl = c.footL + Vector((0.12 * out * c.leg, 0, lift if k < 1 else 0.0))
    fr = c.footR + Vector((-0.12 * out * c.leg, 0, lift if k >= 1 else 0.0))
    s = math.sin(TAU * (t / BEAT + phase))
    return {"foot_L": fl, "foot_R": fr, "hips": Vector((0.04 * c.leg * s, 0, -0.07 * c.leg * bounce(t, phase))),
            "hand_L": c.arm_at("L", 0.55, 0.15, -0.1 + 0.15 * s), "hand_R": c.arm_at("R", 0.55, 0.15, -0.1 - 0.15 * s),
            "lean": 0.12 * s, "look": c.headp + Vector((0, -2, 0))}

def dance_shuffle(c, t, phase=0.0):
    """Arms rolling in front, deep bounce, head nodding to the beat."""
    a = TAU * (t / BEAT + phase)
    return {**idle_feet(c, t), "hips": Vector((0, 0, -0.14 * c.leg * bounce(t, phase))),
            "hand_L": c.arm_at("L", 0.6 + 0.12 * math.cos(a), 0.05, 0.05 + 0.15 * math.sin(a)),
            "hand_R": c.arm_at("R", 0.6 - 0.12 * math.cos(a), 0.05, 0.05 - 0.15 * math.sin(a)),
            "spine": 0.15 * bounce(t, phase), "look": c.headp + Vector((0, -2, -0.6 * bounce(t, phase)))}

DANCES = [dance_bounce, dance_wave, dance_disco, dance_step, dance_shuffle]

def hold_cup(c, t, period=3.2, phase=0.0, toward=None):
    """A drink in the right hand at the chest, lifted to the mouth every few seconds; the other hand on the hip."""
    x = ((t / period) + phase) % 1.0
    sip = max(0.0, math.sin(math.pi * min(1.0, x / 0.3))) if x < 0.3 else 0.0
    mouth = c.headp + Vector((-0.04, -0.12, -0.02))
    chest = c.arm_at("R", 0.45, -0.1, -0.35)
    hr = chest.lerp(mouth, sip)
    look = toward if toward is not None else c.headp + Vector((0, -2, 0.3 * sip))
    return {**idle_feet(c, t), "hips": Vector((0, 0, -0.03 * c.leg * bounce(t, phase))), "hand_R": hr,
            "hand_L": Vector((c.hip.x + 0.16, c.hip.y + 0.02, c.hip.z + 0.06)), "spine": -0.12 * sip, "look": look}

def smoke(c, t, period=4.0, phase=0.0, toward=None):
    """A cigarette: hand to the lips, a long drag, hand down and out; the other arm folded."""
    x = ((t / period) + phase) % 1.0
    drag = math.sin(math.pi * min(1.0, x / 0.35)) if x < 0.35 else 0.0
    mouth = c.headp + Vector((-0.03, -0.1, -0.03))
    down = c.arm_at("R", 0.35, 0.2, -0.45)
    return {**idle_feet(c, t), "hand_R": down.lerp(mouth, drag),
            "hand_L": c.arm_at("L", 0.35, -0.55, -0.42), "spine": -0.05,
            "look": toward if toward is not None else c.headp + Vector((0, -2, 0.5 * (1 - drag)))}

def chat(c, t, phase=0.0, toward=None):
    """Talking with the hands: gestures on a loose rhythm, nods."""
    a = TAU * (t / 1.7 + phase); b2 = TAU * (t / 2.3 + phase * 1.7)
    return {**idle_feet(c, t), "hips": Vector((0, 0, -0.02 * c.leg * (0.5 + 0.5 * math.sin(a)))),
            "hand_L": c.arm_at("L", 0.55 + 0.1 * math.sin(a), 0.1, -0.2 + 0.18 * math.sin(b2)),
            "hand_R": c.arm_at("R", 0.55 + 0.1 * math.cos(b2), 0.1, -0.25 + 0.15 * math.cos(a)),
            "twist": 0.08 * math.sin(b2), "look": toward if toward is not None else c.headp + Vector((0, -2, 0.1 * math.sin(a)))}

def kiss(c, t, partner_head=None, phase=0.0):
    """Leaning in, arms around the partner (partner_head in this character's space)."""
    p = partner_head if partner_head is not None else c.headp + Vector((0, -0.35, 0))
    sway = math.sin(TAU * (t / 3.0 + phase))
    return {**idle_feet(c, t), "hips": Vector((0.01 * sway, 0, 0)),
            "hand_L": p + Vector((0.18, 0.05, -0.12)), "hand_R": p + Vector((-0.18, 0.05, -0.22)),
            "spine": 0.22, "lean": 0.05 * sway, "look": p + Vector((0, 0, 0.02))}

def lean_over_table(c, t, table_z=0.45, phase=0.0, bend=1.25, dip=0.18):
    """Bent over a low table, a rolled note to the nose, the other hand steadying on the table."""
    x = ((t / 3.0) + phase) % 1.0
    snort = math.sin(math.pi * min(1.0, x / 0.4)) if x < 0.4 else 0.0
    tablept = Vector((0, -0.45, table_z))
    return {**idle_feet(c, t), "hips": Vector((0, 0.12 * bend / 1.25, -dip * c.leg)), "spine": bend + 0.2 * snort,
            "hand_R": c.headp.lerp(tablept, 0.55) + Vector((-0.04, -0.15, 0)) , "hand_L": tablept + Vector((0.2, 0, 0.02)),
            "look": tablept + Vector((0.1 * math.sin(TAU * x), 0, 0))}

def sit_bong(c, t, phase=0.0):
    """Sitting (hips dropped back onto a seat), both hands on a bong between the knees, leaning in for a hit, then back."""
    x = ((t / 5.0) + phase) % 1.0
    hit = math.sin(math.pi * min(1.0, x / 0.45)) if x < 0.45 else 0.0
    seat = Vector((0, 0.12, -c.leg * 0.45))
    bong = Vector((0, -0.35, c.hip.z - c.leg * 0.2))
    return {"foot_L": c.footL + Vector((0, -0.25, 0)), "foot_R": c.footR + Vector((0, -0.25, 0)), "hips": seat,
            "hand_L": bong + Vector((0.07, 0, 0.0)), "hand_R": bong + Vector((-0.07, 0, -0.08)),
            "spine": 0.15 + 0.45 * hit, "look": bong + Vector((0, 0, 0.35 + 0.3 * (1 - hit)))}

def swim(c, t, phase=0.0):
    """Treading water (the body sunk to the chest by the scene): arms sculling, a slow bob."""
    a = TAU * (t / 1.6 + phase)
    return {"foot_L": c.footL + Vector((0.05, 0.1 * math.sin(a), 0.1)), "foot_R": c.footR + Vector((-0.05, -0.1 * math.sin(a), 0.1)),
            "hips": Vector((0, 0, 0.03 * math.sin(a))),
            "hand_L": c.arm_at("L", 0.5 + 0.2 * math.sin(a), 0.4, -0.25), "hand_R": c.arm_at("R", 0.5 - 0.2 * math.sin(a), 0.4, -0.25),
            "look": c.headp + Vector((0, -2, 0.3))}

def cheer(c, t, phase=0.0):
    """Both arms up, jumping on the spot."""
    b = abs(math.sin(math.pi * (t / BEAT + phase)))
    return {**idle_feet(c, t), "hips": Vector((0, 0, 0.1 * c.leg * b)),
            "hand_L": c.arm_at("L", 0.1, 0.4, 0.85), "hand_R": c.arm_at("R", 0.1, 0.4, 0.85), "look": c.headp + Vector((0, -2, 1))}

def tuck(c, t):
    """Cannonball: knees up, arms around them."""
    knees = c.hip + Vector((0, -0.15, -0.05))
    return {"foot_L": c.hip + Vector((0.08, -0.12, -c.leg * 0.45)), "foot_R": c.hip + Vector((-0.08, -0.12, -c.leg * 0.45)),
            "hand_L": knees + Vector((0.1, -0.12, 0.0)), "hand_R": knees + Vector((-0.1, -0.12, 0.0)),
            "spine": 0.5, "look": c.headp + Vector((0, -2, -0.5))}

def make_it_rain(c, t, phase=0.0):
    """Flinging cash: the right hand whips up and out on every beat, the left fans the stack."""
    x = (((t - BEAT0) / BEAT) + phase) % 1.0
    fling = math.sin(math.pi * x) ** 2
    return {**idle_feet(c, t), "hips": Vector((0, 0, -0.04 * c.leg * bounce(t, phase))),
            "hand_R": c.arm_at("R", 0.4 + 0.5 * fling, 0.2, -0.1 + 0.9 * fling), "hand_L": c.arm_at("L", 0.5, -0.1, -0.15),
            "spine": -0.1 * fling, "look": c.headp + Vector((0, -2, -0.3))}

def fart(c, t, phase=0.0):
    """Bent forward, hands on the knees, aiming."""
    x = ((t / 3.5) + phase) % 1.0
    push = math.sin(math.pi * min(1.0, x / 0.3)) if x < 0.3 else 0.0
    return {**idle_feet(c, t), "hips": Vector((0, 0.06 * push, -0.08 * c.leg)), "spine": 0.55 + 0.15 * push,
            "hand_L": c.arm_at("L", 0.6, -0.2, -0.75), "hand_R": c.arm_at("R", 0.6, -0.2, -0.75), "look": c.headp + Vector((0.8, 1.5, 0))}
