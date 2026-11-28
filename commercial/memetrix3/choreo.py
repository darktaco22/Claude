"""Fight choreography for THE MEMETRIX III (runs inside Blender).

Builds each fighter's animation from retargeted mocap moves (mocap.py), instead of the game's three looping attack clips:
  - moves are cut from CMU clips (MOVES: clip, frame range, strike frame, striking limb), chained with crossfades;
  - every move after the first continues from where the last one ended (position and facing), so fighters travel;
  - attack(): places the attacker so the striking fist or foot lands exactly on the target bone at the strike frame;
  - hits on the defender are procedural and directional (spine, neck and head whip away from the blow, the body is
    driven back, the knees dip, then a damped spring settles), so no two hits look the same, or a mocap fall or
    stumble is played instead;
  - FIGHT events are logged (time, who, kind, contact point) for sound, sparks and camera shake.

    f = choreo.Fighter(arm_obj, fps=30)
    f.play(t, 'guard', at=(x, y), face=yaw)
    f.then('jab_cross')
    f.attack(t, 'roundhouse', target=other, bone='Head')     # placed so the foot connects
    other.hit(t_strike, from_fighter=f, power=1.0)            # or other.react(t_strike, 'fall_back')
    f.bake(t0, t1)
"""
import math
import mocap
from mathutils import Matrix, Quaternion, Vector

MOCAP_DIR = '/root/mx_work/ext3/mocap/'
PRE = 'mixamorig:'

# name: (clip, first frame, last frame, strike frame or None, striking bone)      frames are 30 fps frames of the clip
MOVES = {
    # stances and footwork
    'guard': ('13_17', 20, 50, None, None),
    'bounce': ('14_01', 0, 40, None, None),
    'feint': ('76_02', 120, 200, None, None),
    'circle': ('76_03', 60, 140, None, None),
    # hands
    'jab': ('143_23', 6, 26, 16, 'LeftHand'),
    'cross': ('143_23', 24, 46, 35, 'RightHand'),
    'jab_cross': ('143_23', 6, 46, 35, 'RightHand'),
    'one_two_three': ('143_23', 52, 90, 79, 'RightHand'),
    'hook': ('13_17', 45, 75, 60, 'RightHand'),
    'haymaker': ('13_18', 295, 330, 318, 'RightHand'),
    'uppercut': ('14_01', 30, 58, 43, 'RightHand'),
    'body_shot': ('15_13', 125, 155, 139, 'RightHand'),
    'flurry': ('13_18', 355, 400, 388, 'RightHand'),
    # legs
    'front_kick': ('135_04', 78, 112, 94, 'RightFoot'),
    'front_kick_l': ('135_04', 130, 165, 146, 'LeftFoot'),
    'roundhouse': ('144_05', 185, 222, 201, 'RightFoot'),
    'high_kick': ('144_05', 128, 165, 145, 'RightFoot'),
    'snap_kick': ('74_04', 25, 60, 37, 'RightFoot'),
    'knee': ('86_06', 800, 830, 813, 'RightFoot'),
    'kick_combo': ('141_14', 82, 120, 106, 'RightFoot'),
    # aerial
    'jump_kick': ('90_06', 92, 140, 112, 'LeftFoot'),
    'flying_kick': ('75_16', 40, 86, 63, 'RightFoot'),
    'spin_kick': ('88_06', 0, 50, 21, 'LeftFoot'),
    'jump_spin_kick': ('87_01', 44, 100, 68, 'LeftFoot'),
    'kickflip': ('85_07', 128, 180, 157, 'RightFoot'),
    'side_flip': ('90_08', 30, 85, None, None),
    'backflip': ('87_03', 0, 62, None, None),
    'cartwheel_flip': ('88_05', 0, 38, None, None),
    'dive_roll': ('128_10', 0, 107, None, None),
    # defence
    'duck': ('77_09', 80, 140, None, None),
    'duck_under': ('134_01', 10, 70, None, None),
    # reactions
    'stumble': ('22_12', 0, 77, None, None),
    'fall_face': ('90_16', 60, 182, None, None),
    'fall_back': ('90_18', 0, 99, None, None),
    'flip_fall': ('90_12', 40, 207, None, None),
    'twist_fall': ('85_15', 220, 332, None, None),
    'getup_back': ('139_18', 0, 214, None, None),
    'getup_face': ('140_01', 0, 208, None, None),
    # weapons (Swordcat)
    'sword_a': ('02_07', 0, 180, None, 'RightHand'),
    'sword_b': ('02_08', 0, 180, None, 'RightHand'),
    'sword_c': ('02_09', 0, 180, None, 'RightHand'),
}

# moves whose mocap root wanders (the actor drifted around the capture stage): keep most of them in place
TRAVEL = {'guard': 0.15, 'bounce': 0.2, 'feint': 0.4, 'circle': 0.5, 'duck': 0.2, 'duck_under': 0.25, 'flurry': 0.5}

FIGHT = []          # (time s, attacker, defender, move, kind, contact xyz)
_CACHE = {}


def yaw_of(m3):
    """Facing yaw of a hips world rotation (characters face -Y at rest)."""
    f = m3 @ Vector((0, -1, 0))
    return math.atan2(-f.x, -f.y)


def rotz(a):
    return Matrix.Rotation(a, 3, 'Z')


class Clip:
    """Per-frame retargeted data of one move on one rig: hips world rotation and position, local quats of the rest."""

    def __init__(self, arm, move):
        clip, f0, f1, strike, limb = MOVES[move]
        self.move, self.strike, self.limb = move, (None if strike is None else strike - f0), limb
        data = mocap.sample(arm, MOCAP_DIR + clip + '.bvh', f0 * 4, f1 * 4 + 1)
        self.hrot, self.hpos, self.local = data['hips_rot'], data['hips_pos'], data['local']
        self.n = len(self.hrot)
        # normalise: start at the origin, facing yaw 0
        y0 = yaw_of(self.hrot[0])
        p0 = self.hpos[0].copy(); p0.z = 0
        r = rotz(-y0)
        self.hrot = [r @ m for m in self.hrot]
        self.hpos = [r @ (p - p0) + Vector((0, 0, 0)) for p in self.hpos]
        for p, q in zip(self.hpos, data['hips_pos']):
            p.z = q.z

    def at(self, i):
        i = max(0, min(self.n - 1, i))
        return self.hrot[i], self.hpos[i], self.local[i]


def clip(arm, move):
    key = (arm.name, move)
    if key not in _CACHE:
        _CACHE[key] = Clip(arm, move)
    return _CACHE[key]


def fk(arm, hrot, hpos, local):
    """Armature-space head/tail positions of every bone for one pose."""
    bones = arm.data.bones
    mats = {}
    out = {}
    for b in bones:
        rest = b.matrix_local
        if b.parent is None:
            m = Matrix.Translation(hpos) @ hrot.to_4x4()
            m = m @ Matrix.Translation(Vector((0, 0, 0)))
            # hpos is the hips head position; hrot is its world rotation
        else:
            q = local.get(b.name, Quaternion())
            m = mats[b.parent.name] @ (b.parent.matrix_local.inverted() @ rest) @ q.to_matrix().to_4x4()
        mats[b.name] = m
        out[b.name] = (m.translation.copy(), (m @ Vector((0, b.length, 0))))
    return out


def limb_tip(arm, pts, limb):
    """End point of the striking limb; rigs without hand bones (zcat) use the forearm's tail."""
    for name in (limb, limb.replace('Hand', 'ForeArm'), limb.replace('Foot', 'ToeBase')):
        if PRE + name in pts:
            return pts[PRE + name][1]
    raise KeyError(limb)


class Seg:
    def __init__(self, t, c, yaw, off, speed=1.0, blend=0.15, travel=1.0, i0=0):
        self.t, self.c, self.yaw, self.off, self.speed, self.blend, self.travel, self.i0 = t, c, yaw, off, speed, blend, travel, i0
        self.t1 = t + (c.n - 1 - i0) / 30.0 / speed

    def pose(self, t):
        i = self.i0 + int(round((t - self.t) * 30 * self.speed))
        hr, hp, loc = self.c.at(i)
        if self.travel != 1.0:
            hp = Vector((hp.x * self.travel, hp.y * self.travel, hp.z))
        r = rotz(self.yaw)
        return r @ hr, r @ hp + self.off, loc


class Fighter:
    def __init__(self, arm, name=None, fps=30):
        self.arm, self.name, self.fps = arm, name or arm.name, fps
        self.segs = []
        self.hits = []                 # (t, direction, power)
        for b in arm.pose.bones:
            b.rotation_mode = 'QUATERNION'

    # ---------------------------------------------------------------- building the timeline
    def play(self, t, move, at=None, face=None, speed=1.0, blend=0.15, travel=None):
        c = clip(self.arm, move)
        if at is None or face is None:
            yaw, off = self._continue(t, c)
            if face is not None:
                yaw = face
            if at is not None:
                off = Vector((at[0], at[1], 0))
        else:
            yaw, off = face, Vector((at[0], at[1], 0))
        if travel is None:
            travel = TRAVEL.get(move, 1.0)
        s = Seg(t, c, yaw, off, speed, blend, travel)
        self.segs.append(s)
        self.segs.sort(key=lambda s_: s_.t)
        return s

    def then(self, move, speed=1.0, gap=0.0, blend=0.15, travel=None, face=None):
        t = (self.segs[-1].t1 - blend + gap) if self.segs else 0.0
        return self.play(t, move, speed=speed, blend=blend, travel=travel, face=face)

    def _continue(self, t, c):
        """Yaw/offset so the new clip starts where this fighter is at time t."""
        if not self.segs:
            return 0.0, Vector()
        hr, hp, _ = self.pose_at(t)
        yaw = yaw_of(hr)
        off = Vector((hp.x, hp.y, 0))
        return yaw, off

    def attack(self, t_strike, move, target, bone='Head', aim=(0, 0, 0), reach=0.0, speed=1.0, blend=0.15):
        """Start `move` so that its strike frame lands at t_strike with the striking limb on target's bone."""
        c = clip(self.arm, move)
        t0 = t_strike - c.strike / 30.0 / speed
        i0 = 0
        before = [s_ for s_ in self.segs if s_.t < t_strike]
        if before:                                   # never cut the previous move shorter than 0.3 s: trim the wind-up
            earliest = before[-1].t + 0.3
            if t0 < earliest:
                i0 = min(c.strike - 4, int(math.ceil((earliest - t0) * 30 * speed)))
                t0 += i0 / 30.0 / speed
        thr, thp, tloc = target.where(t_strike)
        tgt = fk(target.arm, thr, thp, tloc)[PRE + bone][0] + Vector(aim)
        # where the limb is, relative to the clip's own root, at the strike frame
        hr, hp, loc = c.at(c.strike)
        tip = limb_tip(self.arm, fk(self.arm, hr, hp, loc), c.limb)
        # facing: turn so the limb's direction from the start point points at the target
        me = self.where(t0)[1] if before else None
        lim = Vector((tip.x, tip.y))
        start = Vector((me.x, me.y)) if me is not None else Vector((tgt.x, tgt.y)) - lim
        want = Vector((tgt.x - start.x, tgt.y - start.y))
        yaw = math.atan2(want.y, want.x) - math.atan2(lim.y, lim.x) if lim.length > 1e-4 else 0.0
        r = rotz(yaw)
        tipw = r @ tip
        off = Vector((tgt.x - tipw.x, tgt.y - tipw.y, 0))
        if reach:
            off -= Vector((want.x, want.y, 0)).normalized() * reach
        if me is not None:                      # stepping in: blend over a time that fits the distance covered
            st = r @ c.hpos[i0]
            step = (Vector((off.x + st.x, off.y + st.y)) - Vector((me.x, me.y))).length
            blend = max(blend, min(0.45, step / 2.2, (c.strike - i0) / 30.0 / speed * 0.8))
            if step > 0.6:
                print('CHOREO WARN %s %s at %.2f: lunges %.2f m in %.2f s (stage them closer)' % (self.name, move, t_strike, step, blend))
        s = Seg(t0, c, yaw, off, speed, blend, TRAVEL.get(move, 1.0), i0)
        self.segs.append(s)
        self.segs.sort(key=lambda s_: s_.t)
        FIGHT.append((t_strike, self.name, target.name, move, 'kick' if 'Foot' in c.limb else 'punch', tuple(tgt)))
        return s, tgt, Vector((want.x, want.y, 0)).normalized()

    def hit(self, t, from_fighter=None, direction=None, power=1.0):
        """Procedural directional hit reaction (added on top of whatever the fighter is doing)."""
        if direction is None and from_fighter is not None:
            a = from_fighter.where(t)[1]
            b = self.where(t)[1]
            direction = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
        self.hits.append((t, Vector(direction), power))
        FIGHT.append((t, from_fighter.name if from_fighter else '?', self.name, 'hit', 'hit', tuple(self.pose_at(t)[1])))

    def react(self, t, move, direction=None, from_fighter=None, speed=1.0):
        """Play a mocap reaction (fall, stumble) turned so the body goes along `direction`."""
        if direction is None and from_fighter is not None:
            a = from_fighter.where(t)[1]
            b = self.where(t)[1]
            direction = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
        c = clip(self.arm, move)
        hr, hp, _ = self.where(t)
        # the clip's own travel direction (start -> end) is aligned with the blow
        travel = c.hpos[-1] - c.hpos[0]
        if direction is not None and Vector((travel.x, travel.y)).length > 0.05:
            yaw = math.atan2(direction.y, direction.x) - math.atan2(travel.y, travel.x)
        else:
            yaw = yaw_of(hr)
        s = Seg(t, c, yaw, Vector((hp.x, hp.y, 0)), speed, 0.08)
        self.segs.append(s)
        self.segs.sort(key=lambda s_: s_.t)
        FIGHT.append((t, from_fighter.name if from_fighter else '?', self.name, move, 'fall', tuple(hp)))
        return s

    # ---------------------------------------------------------------- evaluation
    def pose_at(self, t):
        """Blended pose (hips world rot, hips pos, local quats) at time t, without hit reactions."""
        live = [s for s in self.segs if s.t <= t]
        if not live:
            s = self.segs[0]
            return s.pose(s.t)
        cur = live[-1]
        hr, hp, loc = cur.pose(t)
        if len(live) > 1 and t - cur.t < cur.blend:
            prev = live[-2]
            w = (t - cur.t) / cur.blend
            w = w * w * (3 - 2 * w)
            phr, php, ploc = prev.pose(min(t, prev.t1))
            hr = phr.to_quaternion().slerp(hr.to_quaternion(), w).to_matrix()
            hp = php.lerp(hp, w)
            loc = {k: ploc.get(k, Quaternion()).slerp(q, w) for k, q in loc.items()}
        return hr, hp, loc

    def where(self, t):
        """pose_at plus the push of hits already taken (where the body really is)."""
        hr, hp, loc = self.pose_at(t)
        push, _ = self._hit_offsets(t)
        return hr, hp + push, loc

    def _sep(self, t):
        sep = getattr(self, 'sep', None)
        if not sep:
            return Vector()
        f = t * 30.0
        i = int(math.floor(f))
        a = sep.get(i, Vector()); b = sep.get(i + 1, Vector())
        return a.lerp(b, f - i)

    def _hit_offsets(self, t):
        """(root push, per-bone extra world rotation) from all hits so far."""
        push = Vector()
        rots = {}
        for th, d, p in self.hits:
            dt = t - th
            if dt < 0:
                continue
            # push: fast then easing (critically damped), 0.35 m per unit power
            push += d * (0.35 * p * (1 - math.exp(-dt * 9)) * (1 + dt * 0) )
            # whip: damped spring, starting at full deflection
            env = math.exp(-dt * 7) * math.cos(dt * 14)
            axis = Vector((0, 0, 1)).cross(d).normalized()          # tip away from the blow
            for bn, k in (('Spine', 0.25), ('Spine1', 0.3), ('Spine2', 0.35), ('Neck', 0.4), ('Head', 0.6)):
                a = math.radians(38) * p * k * env
                rots[bn] = Quaternion(axis, a) @ rots.get(bn, Quaternion())
            dip = math.exp(-dt * 6) * math.sin(min(math.pi, dt * 12)) * 0.06 * p
            push.z -= dip
        return push, rots

    # ---------------------------------------------------------------- baking
    def bake(self, t0, t1, action_name=None):
        import bpy
        act = bpy.data.actions.new(action_name or (self.name + ':fight'))
        arm = self.arm
        bones = arm.data.bones
        hb = bones[PRE + 'Hips']
        fcs = {}

        def put(path, i, grp, f, v):
            key = (path, i)
            if key not in fcs:
                fcs[key] = act.fcurves.new(path, index=i, action_group=grp)
            fcs[key].keyframe_points.insert(f, v, options={'FAST'})

        prev = {}
        f0, f1 = int(round(t0 * 30)), int(round(t1 * 30))
        for fr in range(f0, f1 + 1):
            t = fr / 30.0
            hr, hp, loc = self.pose_at(t)
            push, extra = self._hit_offsets(t)
            hp = hp + push + self._sep(t)
            # hips: world rotation -> basis
            q = (hb.matrix_local.to_3x3().inverted() @ hr).to_quaternion()
            vals = {hb.name: q}
            # extra world rotations on the spine chain: convert to local by conjugating with the bone's pose frame
            if extra:
                poses = {}
                for b in bones:
                    if b.parent is None:
                        poses[b.name] = hr
                    else:
                        lq = loc.get(b.name, Quaternion())
                        poses[b.name] = poses[b.parent.name] @ (b.parent.matrix_local.to_3x3().inverted() @ b.matrix_local.to_3x3()) @ lq.to_matrix()
                for bn, eq in extra.items():
                    name = PRE + bn
                    if name not in poses or name not in loc:
                        continue
                    P = poses[name]
                    loc = dict(loc)
                    loc[name] = loc[name] @ (P.inverted() @ eq.to_matrix() @ P).to_quaternion()
            for k, v in loc.items():
                vals[k] = v
            for k, v in vals.items():
                if k in prev and prev[k].dot(v) < 0:
                    v = -v
                prev[k] = v
                path = 'pose.bones["%s"].rotation_quaternion' % k
                for i in range(4):
                    put(path, i, k, fr + 1, v[i])
            lw = hb.matrix_local.to_3x3().inverted() @ (hp - hb.head_local)
            for i in range(3):
                put('pose.bones["%s"].location' % hb.name, i, hb.name, fr + 1, lw[i])
        for c in act.fcurves:
            c.update()
        arm.animation_data_create()
        return act


def separate(fighters, t0, t1, min_d=0.55, radius=None, iters=3, head_r=None):
    """Keep fighters' bodies apart: where two hips come closer than (r_a + r_b), push both apart, then smooth the
    correction over +-0.25 s so it reads as footwork, not a jump. Stores fighter.sep {frame: Vector}."""
    radius = radius or {}
    head_r = head_r or {}
    f0, f1 = int(t0 * 30), int(t1 * 30)
    for F in fighters:
        F.sep = {}
    for _ in range(iters):
        raw = {F: {} for F in fighters}
        side = {}
        for fr in range(f0, f1 + 1):
            t = fr / 30.0
            pos = {}
            for F in fighters:
                hr, hp, loc = F.pose_at(t)
                push, _ = F._hit_offsets(t)
                o = push + F._sep(t)
                hd = fk(F.arm, hr, hp, loc)[PRE + 'Head'][0] + o
                p = hp + o
                pos[F] = (Vector((p.x, p.y)), Vector((hd.x, hd.y)))
            for i, A in enumerate(fighters):
                for B in fighters[i + 1:]:
                    # whichever is closer relative to its limit: hips (bodies) or heads (bags, hair, hats)
                    dh = pos[B][0] - pos[A][0]
                    dd = pos[B][1] - pos[A][1]
                    nh = radius.get(A.name, min_d / 2) + radius.get(B.name, min_d / 2)
                    nd = head_r.get(A.name, 0.2) + head_r.get(B.name, 0.2)
                    if dd.length - nd < dh.length - nh:
                        d, need = dd, nd
                    else:
                        d, need = dh, nh
                    key = (A.name, B.name)
                    if d.length >= need or key not in side:
                        side[key] = d.normalized() if d.length > 1e-4 else Vector((1, 0))
                    if d.length < need:
                        n = side[key]                # keep each fighter on its own side: never push them through
                        d = n * max(0.0, d.dot(n))
                        corr = (need - d.length) / 2
                        raw[A][fr] = raw[A].get(fr, Vector((0, 0))) - n * corr
                        raw[B][fr] = raw[B].get(fr, Vector((0, 0))) + n * corr
        for F in fighters:
            k = 7
            for fr in range(f0, f1 + 1):
                acc = Vector((0, 0)); wsum = 0
                for j in range(-k, k + 1):
                    w = 1 - abs(j) / (k + 1)
                    acc += raw[F].get(fr + j, Vector((0, 0))) * w; wsum += w
                # raw correction is a minimum: keep the max of smoothed and raw so contact never interpenetrates
                v = acc / wsum
                r = raw[F].get(fr)
                if r is not None and r.length > v.length:
                    v = r
                F.sep[fr] = F.sep.get(fr, Vector()) + Vector((v.x, v.y, 0))
