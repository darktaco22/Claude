"""The trader: a realistic MakeHuman man (MPFB 2, CC0 assets) on MakeHuman's full rig, from the Degens project's toolkit
(humans.py builds him, rigctl.py poses him, grips.py solves how his hand wraps the phone).

He sits low (a beanbag), head down over his phone: the LEFT hand holds it, the RIGHT index finger taps it.  Everything is solved in the rig's
seat space (the body faces -Y there) and keyed per frame; the phone's world matrix falls out of the held hand, and the scene hangs the screen on it.

  from trader import Trader
  T = Trader(seat_xy=(x, y), face=math.pi)            # face = world yaw; pi means he looks toward +Y
  T.pose(frame, t, taps_fn)                           # keys body, face, both hands; returns the phone's world matrix
"""
import bpy, os, sys, math
from mathutils import Vector, Matrix, Quaternion
DEG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'degens'); sys.path.insert(0, DEG)
import humans, rigctl, grips

CAST_DEFAULT = TRADER = dict(phen=dict(gender=1.0, age=0.36, muscle=0.35, weight=0.42, height=0.55, proportions=0.55, race=dict(caucasian=0.75, asian=0.1, african=0.15)),
              skin='young_caucasian_male', hair='cortu_short_messy_hair', brows='eyebrow002', lashes='eyelashes01', clothes=['male_casualsuit02', 'shoes05'], tint={})
POINT = dict(t=(0.45, 0.5, 0.4), i=(0.04, 0.05, 0.03), m=(1.1, 1.2, 0.8), r=(1.2, 1.2, 0.8), p=(1.25, 1.2, 0.8))
HOLD_PHONE = 'phone'
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, u): return a + (b - a) * u


class Trader:
    def __init__(self, seat_xy, face=math.pi, hip_z=0.50, lean_deg=16.0, cast=None):
        if cast: humans.CAST['trader'] = cast
        else: humans.CAST['trader'] = TRADER
        self.rig, self.body, self.parts = humans.build('trader')
        self.a = a = rigctl.Actor('trader', self.rig, self.body); a.parts = self.parts
        self.mw = Matrix.Translation((seat_xy[0], seat_xy[1], 0)) @ Matrix.Rotation(face, 4, 'Z')
        hipc = (a.hip['L'] + a.hip['R']) / 2
        self.root_loc = Vector((0, 0.035 - hipc.y, hip_z - hipc.z)); self.lean = math.radians(lean_deg)
        c, M, w = grips.phone(a, 'L'); a.G = {'phone': (c, M)}; print('GRIP trader phone', {f: round(v * 1000, 1) for f, v in w.items()})
        # the holding hand's pose is constant; the tapping hand's finger shape is 'point'
        self.tip_pp = self.tip_in_palm('R')
    # ------------------------------------------------------------------ pose parts
    def fingers(self, s, shape, Q):
        a = self.a
        if shape == 'phone': Q.update(grips.curlQ(a, s, a.G['phone'][0])); return
        sh = shape
        for fi, key in enumerate('timrp', start=1):
            for j in range(1, 4):
                bn = f'finger{fi}-{j}.{s}'
                if bn in a.curl_axis: Q[bn] = a.local_q(bn, rigctl.qrot(a.curl_axis[bn], sh[key][j - 1]))
    def body_Q(self, t, pitch):
        a = self.a; Q = {}
        lean = self.lean + math.sin(t * 2.0) * 0.012
        for b, w in (('spine05', .15), ('spine04', .2), ('spine03', .25), ('spine02', .2), ('spine01', .2)): Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), lean * w))
        for b, w in (('neck01', .3), ('neck02', .3), ('neck03', .2), ('head', .2)): Q[b] = a.local_q(b, rigctl.qrot((1, 0, 0), (pitch - lean * 0.9) * w))
        blink = 1.0 if (t + 0.8) % 3.9 < 0.12 else 0.0
        for s in 'LR':
            Q[f'orbicularis03.{s}'] = a.local_q(f'orbicularis03.{s}', rigctl.qrot((1, 0, 0), 0.4 * blink + 0.1)); Q[f'orbicularis04.{s}'] = a.local_q(f'orbicularis04.{s}', rigctl.qrot((1, 0, 0), -0.2 * blink))
            Q[f'eye.{s}'] = a.local_q(f'eye.{s}', rigctl.qrot((1, 0, 0), -0.25))          # eyes down at the screen
        return Q
    def eyes_pos(self, Q):
        a = self.a; head = a.fk(Q, self.root_loc, 'head')
        return head @ (a.rest['head'].inverted() @ (a.rest['head'].translation + Vector((0, -0.085, 0.04)))), head
    def phone_matrix(self, Q, yaw=0.0):
        """Armature-space matrix of the phone (origin = centre of its back, +Y top, +Z screen) when the left hand holds it up to his eyes."""
        a = self.a; eyes, head = self.eyes_pos(Q)
        flat = Vector((0, -1, 0)); zup = Vector((0, 0, 1))
        tgt = eyes + flat * 0.36 - zup * 0.20 + Vector((-0.02, 0, 0))
        n = (eyes - tgt).normalized()
        if yaw: n = (Matrix.Rotation(yaw, 3, 'Z') @ n).normalized()          # turned a little toward the camera on his right (armature -X)
        upp = (zup - n * zup.dot(n)).normalized(); X = upp * a.idx_sign['L']; Y = n.cross(X)
        F = a.frame(Vector(), Y, n); F.translation = tgt - F.to_3x3() @ a.G['phone'][1].translation
        return F
    def tip_in_palm(self, s='R'):
        """Where the index fingertip is in the palm frame for the pointing shape."""
        a = self.a; Q = {}; self.fingers(s, POINT, Q)
        bn = f'finger2-3.{s}'
        B = a.rig.data.bones[bn]; tail_rest = B.tail_local.copy()
        M = a.fk(Q, Vector(), bn) @ a.rest[bn].inverted()
        p_arm = M @ tail_rest
        return (a.palm[s].inverted() @ a.rest[f'wrist.{s}'].inverted()) @ p_arm
    # ------------------------------------------------------------------ the frame
    def pose(self, f, t, tip_local, pitch=0.5, yaw=0.30):
        """Key the whole pose at frame f; tip_local(t) = (x, y, z) of the tapping fingertip in the PHONE's frame (metres).  Returns the phone's world matrix."""
        a = self.a; K = a.K; mw = self.mw; root_loc = self.root_loc; sx = {'L': 1, 'R': -1}
        Q = self.body_Q(t, pitch); Pm = self.phone_matrix(Q, yaw)                       # phone, armature space
        pal = Pm @ a.G['phone'][1].inverted()                                           # the holding palm frame
        hands = {'L': pal}; shapes = {'L': 'phone', 'R': POINT}
        # the tapping hand: fingertip at the target, finger leaning onto the screen from below-right
        u, v, n = Pm.to_3x3().col[0], Pm.to_3x3().col[1], Pm.to_3x3().col[2]
        l = tip_local(t); tip = Pm.translation + u * l[0] + v * l[1] + n * (l[2] + 0.004)
        fdir = (-n * 0.55 + v * 0.70 - u * 0.30).normalized(); z0 = Vector((0.8, 0.0, -0.5))
        tp = self.tip_pp
        F = a.frame(Vector(), fdir, z0); pos = tip - F.to_3x3() @ tp; F.translation = pos
        hands['R'] = F
        for s in 'LR': self.fingers(s, shapes[s], Q)
        # keep the hands within reach
        reach = (a.uarm + a.farm) * 0.985
        for s in 'LR':
            wp = a.hand_matrix_for_palm(s, hands[s]).translation; sh = a.fk(Q, root_loc, f'upperarm01.{s}').translation; dv = wp - sh
            if dv.length > reach: hands[s] = Matrix.Translation(dv.normalized() * (reach - dv.length)) @ hands[s]
        H = {('hand', s): mw @ a.hand_matrix_for_palm(s, hands[s]) for s in 'LR'}
        feet, poles = {}, {}
        for s in 'LR':
            hip = a.hip[s] + root_loc; ank = Vector((hip.x + sx[s] * 0.06, -(a.thigh + 0.10), 0.085))
            Fm = a.rest[f'foot.{s}'].copy(); Fm.translation = ank; feet['foot', s] = mw @ Fm; poles['foot', s] = mw @ Vector((hip.x + sx[s] * 0.08, -1.2, 0.55))
            pv = Vector((sx[s] * 0.7, 0.45, -0.45)).lerp(Vector((sx[s] * 0.22, 0.35, -0.75)), 1.0); poles['hand', s] = mw @ (a.shoulder[s] + root_loc + pv)
        a.key_pose(f, mw, Q, root_loc, H, feet, poles, {})
        return mw @ Pm
