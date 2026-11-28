"""The Liquidators: procedural animation for the Polygonal Mind xyz creatures (CC0, rigged, no animations).

Bones are classified by name (legs, arms, wings, tentacles, fins, tails, spine, head), and each class gets its own
motion: legs alternate in a gait, wings flap, tentacles and tails wave with the phase running down the chain, spines
undulate, heads track. On top of that are actions: walk, run, fly, lunge (wind-up, strike, recover) and recoil.

    b = bots.Bot(arm_obj, kind='bear')
    b.cycle(t0, t1, gait='run', speed=1.6)     # locomotion cycle (place the root yourself)
    b.lunge(t_strike)                          # wind-up 0.35 s before, strike, recover
    b.bake(t0, t1)
"""
import math
import re
from mathutils import Euler, Quaternion

CLASSES = [
    ('wing', re.compile(r'wing', re.I)),
    ('tentacle', re.compile(r'tentacle|tentac', re.I)),
    ('fin', re.compile(r'fin', re.I)),
    ('tail', re.compile(r'tail', re.I)),
    ('leg', re.compile(r'thigh|shin|leg|foot|toe|upperleg', re.I)),
    ('arm', re.compile(r'arm|hand|claw|shoulder', re.I)),
    ('head', re.compile(r'head|jaw|neck', re.I)),
    ('spine', re.compile(r'spine|hips|chest|body', re.I)),
]


def side(name):
    n = name.lower()
    if re.search(r'(\.|_|-)l(\.|$|_)|left', n):
        return -1
    if re.search(r'(\.|_|-)r(\.|$|_)|right', n):
        return 1
    return 0


def front(name):
    return 1 if re.search(r'front|fr', name, re.I) else (-1 if re.search(r'back|bk|rear', name, re.I) else 0)


def depth(b):
    d = 0
    while b.parent is not None and b.parent.name.split('.')[0].lower()[:4] == b.name.split('.')[0].lower()[:4]:
        d += 1
        b = b.parent
    return d


class Bot:
    def __init__(self, arm, kind='bot', seed=0):
        self.arm, self.kind = arm, kind
        self.cls = {}
        for b in arm.data.bones:
            if re.search(r'IK|PT|_end$|End', b.name):
                continue
            for c, rx in CLASSES:
                if rx.search(b.name):
                    self.cls[b.name] = c
                    break
        self.cycles = []          # (t0, t1, gait, speed)
        self.events = []          # (t, kind, power)
        self.phase = seed * 0.37
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'

    def cycle(self, t0, t1, gait='walk', speed=1.0):
        self.cycles.append((t0, t1, gait, speed))

    def lunge(self, t, power=1.0):
        self.events.append((t, 'lunge', power))

    def recoil(self, t, power=1.0):
        self.events.append((t, 'recoil', power))

    def _gait(self, t):
        for t0, t1, g, sp in self.cycles:
            if t0 <= t <= t1:
                fade = min(1.0, (t - t0) / 0.25, (t1 - t) / 0.25)
                return g, sp, max(0.0, fade)
        return 'idle', 1.0, 1.0

    def rot(self, bone, t):
        """Euler offset (radians, bone-local) for one bone at time t."""
        c = self.cls.get(bone.name)
        if c is None:
            return Euler()
        g, sp, fade = self._gait(t)
        hz = {'idle': 0.6, 'walk': 1.6, 'run': 2.8, 'fly': 3.2}[g] * sp
        amp = {'idle': 0.25, 'walk': 0.8, 'run': 1.0, 'fly': 1.0}[g] * fade + (0.25 * (1 - fade))
        w = 2 * math.pi * hz * t + self.phase
        s, fr, dp = side(bone.name), front(bone.name), depth(bone)
        e = Euler()
        if c == 'leg':
            ph = w + (math.pi if s > 0 else 0) + (math.pi if fr < 0 else 0)
            e.x = math.radians(32) * amp * math.sin(ph - dp * 0.6)
        elif c == 'arm':
            ph = w + (0 if s > 0 else math.pi)
            e.x = math.radians(22) * amp * math.sin(ph - dp * 0.5)
        elif c == 'wing':
            f = 2.2 if g == 'fly' else 0.5
            e.z = s * math.radians(45) * (0.4 + 0.6 * amp) * math.sin(w * f - dp * 0.7)
        elif c in ('tentacle', 'tail', 'fin'):
            e.x = math.radians(18 + 6 * dp) * (0.5 + amp) * math.sin(w * 0.8 - dp * 0.9)
            e.z = math.radians(10 + 4 * dp) * (0.5 + amp) * math.cos(w * 0.6 - dp * 0.9 + s)
        elif c == 'spine':
            e.z = math.radians(4) * amp * math.sin(w)
            e.x = math.radians(3) * amp * math.sin(2 * w)
        elif c == 'head':
            e.x = math.radians(6) * amp * math.sin(2 * w + 0.5)
        # actions
        for te, k, p in self.events:
            dt = t - te
            if k == 'lunge' and -0.4 < dt < 0.5:
                # wind-up back (negative), snap forward at the strike, settle
                if dt < 0:
                    v = -math.sin(min(1.0, (dt + 0.4) / 0.4) * math.pi / 2) * 0.6
                else:
                    v = math.exp(-dt * 6) * math.cos(dt * 10)
                if c in ('spine', 'head'):              # several spine bones add up: keep each one small
                    e.x += math.radians(7) * p * v
                if c in ('arm', 'tentacle'):
                    e.x += math.radians(35) * p * v
                if c == 'wing':
                    e.z += s * math.radians(35) * p * v
            if k == 'recoil' and 0 <= dt < 0.8:
                v = math.exp(-dt * 7) * math.cos(dt * 16)
                if c in ('spine', 'head'):
                    e.x -= math.radians(9) * p * v
        return e

    def bake(self, t0, t1, name=None):
        import bpy
        act = bpy.data.actions.new(name or (self.arm.name + ':bot'))
        fcs = {}
        for fr in range(int(t0 * 30), int(t1 * 30) + 1):
            t = fr / 30.0
            for pb in self.arm.pose.bones:
                if pb.name not in self.cls:
                    continue
                q = self.rot(pb.bone, t).to_quaternion()
                for i in range(4):
                    key = (pb.name, i)
                    if key not in fcs:
                        fcs[key] = act.fcurves.new('pose.bones["%s"].rotation_quaternion' % pb.name, index=i, action_group=pb.name)
                    fcs[key].keyframe_points.insert(fr + 1, q[i], options={'FAST'})
        for c in act.fcurves:
            c.update()
        self.arm.animation_data_create()
        self.arm.animation_data.action = act
        return act
