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

# how each strike lands (mocap velocity at contact is noisy): sideways whip and lift, by move
STYLE = {
    'hook': {'lat': 0.95}, 'haymaker': {'lat': 1.0}, 'roundhouse': {'lat': 0.9}, 'high_kick': {'lat': 0.7},
    'spin_kick': {'lat': 0.8}, 'jump_spin_kick': {'lat': 0.8}, 'kickflip': {'up': 0.6},
    'uppercut': {'up': 0.85, 'lat': 0.0}, 'knee': {'up': 0.5}, 'front_kick': {'lat': 0.0}, 'front_kick_l': {'lat': 0.0},
    'jab': {'lat': 0.1}, 'cross': {'lat': 0.15}, 'jab_cross': {'lat': 0.15}, 'body_shot': {'lat': 0.2},
}

FIGHT = []          # (time s, attacker, defender, move, kind, contact xyz)
_CACHE = {}


HIPS_REST = {}


def facing(arm, hr):
    """Horizontal facing vector of a hips pose rotation (armature space). Characters face -Y at rest, and hr includes
    the hips bone's rest orientation (its Y axis points up), so the rest rotation is divided out first."""
    if arm.name not in HIPS_REST:
        HIPS_REST[arm.name] = arm.data.bones[PRE + 'Hips'].matrix_local.to_3x3().inverted()
    f = hr @ HIPS_REST[arm.name] @ Vector((0, -1, 0))
    f = Vector((f.x, f.y, 0))
    return f.normalized() if f.length > 1e-4 else Vector((0, -1, 0))


def yaw_of(arm, hr):
    f = facing(arm, hr)
    return math.atan2(f.x, -f.y)                 # 0 = facing -Y; +90 deg = facing +X (matches rotz)


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
        # normalise: start at the origin, and turn so the performer's average line of sight is -Y (yaw 0). Boxers
        # stand bladed and turn their hips, but they always look at the opponent, so 'face=' means 'look at'.
        sx = sy = 0.0
        for i in range(len(self.hrot)):
            v = look_dir(arm, self.hrot[i], self.hpos[i], self.local[i])
            sx += v.x; sy += v.y
        y0 = dir_yaw(Vector((sx, sy, 0))) if abs(sx) + abs(sy) > 1e-3 else yaw_of(arm, self.hrot[0])
        p0 = self.hpos[0].copy(); p0.z = 0
        r = rotz(-y0)
        self.hrot = [r @ m for m in self.hrot]
        self.hpos = [r @ (p - p0) + Vector((0, 0, 0)) for p in self.hpos]
        for p, q in zip(self.hpos, data['hips_pos']):
            p.z = q.z
        # airborne frames: a short-legged rig must still clear the floor by as much as the performer did (x0.8);
        # no frame may sink below the floor. The lift is smoothed so it reads as a jump, not a pop.
        lift = []
        for i in range(self.n):
            pts = fk(arm, self.hrot[i], self.hpos[i], self.local[i])
            low = min(min(h.z, tl.z) for h, tl in pts.values())
            sl = data['src_low'][i]
            want = 0.8 * sl if sl > 0.08 else 0.0
            lift.append(max(0.0, want - low, -low))
        k = 3
        for i in range(self.n):
            win = lift[max(0, i - k):i + k + 1]
            self.hpos[i].z += max(lift[i], sum(win) / len(win))

        # strike frame: the moment of full extension (largest horizontal reach from the hips) near the marked frame
        if self.strike is not None:
            best, bi = -1.0, self.strike
            for i in range(max(2, self.strike - 6), min(self.n - 1, self.strike + 7)):
                pts = fk(arm, self.hrot[i], self.hpos[i], self.local[i])
                tip = limb_tip(arm, pts, self.limb)
                rch = Vector((tip.x - self.hpos[i].x, tip.y - self.hpos[i].y)).length
                if rch > best:
                    best, bi = rch, i
            self.strike, self.reach = bi, best

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
    fk.mats = mats
    return out


def look_dir(arm, hr, hp, loc):
    """Horizontal direction the character is looking (head forward): where a fighter's opponent is."""
    fk(arm, hr, hp, loc)
    b = arm.data.bones.get(PRE + 'Head')
    if b is None:
        return facing(arm, hr)
    f = fk.mats[b.name].to_3x3() @ b.matrix_local.to_3x3().inverted() @ Vector((0, -1, 0))
    f = Vector((f.x, f.y, 0))
    return f.normalized() if f.length > 1e-4 else facing(arm, hr)


def dir_yaw(v):
    """rotz angle that turns -Y onto v."""
    return math.atan2(v.x, -v.y)


def limb_tip(arm, pts, limb):
    """End point of the striking limb; rigs without hand bones (zcat) use the forearm's tail."""
    for name in (limb, limb.replace('Hand', 'ForeArm'), limb.replace('Foot', 'ToeBase')):
        if PRE + name in pts:
            return pts[PRE + name][1]
    raise KeyError(limb)


def leg_ik(arm, hr, loc, mats, targets):
    """Two-bone IK: put each ankle (Foot head) on its target, keeping the knee in its original bending plane and
    the foot's world orientation. mats: armature-space pose matrices for the current pose (fk.mats)."""
    loc = dict(loc)
    B = arm.data.bones
    for sd, F in targets.items():
        nu, nl, nf = PRE + sd + 'UpLeg', PRE + sd + 'Leg', PRE + sd + 'Foot'
        Mu, Ml, Mf = mats[nu], mats[nl], mats[nf]
        H, K, A = Mu.translation, Ml.translation, Mf.translation
        if (F - A).length < 1e-4:
            continue
        a, b = (K - H).length, (A - K).length
        d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, (F - H).length))
        u = (F - H).normalized()
        n = (A - H).cross(K - H)
        if n.length < 1e-6:
            n = (A - H).cross(Vector((1, 0, 0)))
        v = n.cross(u).normalized()
        if v.dot(K - H) < 0:
            v = -v
        ca = (a * a + d * d - b * b) / (2 * a * d)
        ca = max(-1.0, min(1.0, ca))
        Kn = H + u * a * ca + v * a * math.sqrt(max(0.0, 1 - ca * ca))
        Fn = H + u * d
        R1 = (K - H).normalized().rotation_difference((Kn - H).normalized()).to_matrix()
        up3 = R1 @ Mu.to_3x3()
        leg_old = R1 @ Ml.to_3x3()
        shin_old = R1 @ (A - K)
        R2 = shin_old.normalized().rotation_difference((Fn - Kn).normalized()).to_matrix()
        leg3 = R2 @ leg_old
        foot3 = Mf.to_3x3()
        bu, bl, bf = B[nu], B[nl], B[nf]
        par3 = mats[bu.parent.name].to_3x3()
        rel = lambda bb: (bb.parent.matrix_local.to_3x3().inverted() @ bb.matrix_local.to_3x3())
        loc[nu] = ((par3 @ rel(bu)).inverted() @ up3).to_quaternion()
        loc[nl] = ((up3 @ rel(bl)).inverted() @ leg3).to_quaternion()
        loc[nf] = ((leg3 @ rel(bf)).inverted() @ foot3).to_quaternion()
    return loc


class Seg:
    def __init__(self, t, c, yaw, off, speed=1.0, blend=0.15, travel=1.0, i0=0):
        self.t, self.c, self.yaw, self.off, self.speed, self.blend, self.travel, self.i0 = t, c, yaw, off, speed, blend, travel, i0
        self.t1 = t + (c.n - 1 - i0) / 30.0 / speed

    def pose(self, t, warp=None):
        if warp is not None:
            i = self.i0 + int(round((warp(t) - warp(self.t)) * 30 * self.speed))
        else:
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
        self.hits = []                 # dicts, see hit()
        self.stops = []                # hit-stop times (this fighter's blow connected)
        self.plant = True              # planted-foot IK and catch-up steps
        # which way local X bends the knee back / lifts the thigh forward on this rig (rest pose, facing -Y)
        self.knee_sign = [1, 1]
        for i, (bn, want_back) in enumerate((('LeftUpLeg', False), ('LeftLeg', True))):
            b = arm.data.bones.get(PRE + bn)
            if b is None:
                continue
            r = b.matrix_local.to_3x3()
            yp = (r @ Quaternion((1, 0, 0), 0.4).to_matrix() @ Vector((0, 1, 0))).y
            ym = (r @ Quaternion((1, 0, 0), -0.4).to_matrix() @ Vector((0, 1, 0))).y
            self.knee_sign[i] = (1 if yp > ym else -1) * (1 if want_back else -1)
        for b in arm.pose.bones:
            b.rotation_mode = 'QUATERNION'

    # ---------------------------------------------------------------- building the timeline
    def play(self, t, move, at=None, face=None, speed=1.0, blend=0.15, travel=None):
        c = clip(self.arm, move)
        if face is None and getattr(self, 'opponent', None) is not None and self.opponent.segs:
            me = self.where(t)[1] if self.segs else Vector((at[0], at[1], 0))
            op = self.opponent.where(t)[1]
            v = Vector((op.x - me.x, op.y - me.y, 0))
            if v.length > 0.05:
                face = dir_yaw(v)
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
        yaw = yaw_of(self.arm, hr)
        off = Vector((hp.x, hp.y, 0))
        return yaw, off

    def attack(self, t_strike, move, target, bone='Head', aim=(0, 0, 0), reach=0.0, speed=1.0, blend=0.15,
               power=None, zone=None):
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
        lim = Vector((tip.x - hp.x, tip.y - hp.y))      # fist/foot direction from the hips at the strike frame
        start = Vector((me.x, me.y)) if me is not None else Vector((tgt.x, tgt.y)) - lim
        # the line of attack runs from the attacker to the defender's body (hips), not to the exact target point
        want = Vector((thp.x - start.x, thp.y - start.y))
        if want.length < 0.3 and me is not None:     # on top of each other: keep the attacker's current facing
            fv = facing(self.arm, self.where(t0)[0])
            want = Vector((fv.x, fv.y))
        # aim the strike: turn so the line hips -> fist (or foot) points at the target (boxers stand bladed, so
        # the hips themselves face sideways), then slide so the fist lands on it
        aimv = lim if lim.length > 0.08 else Vector((facing(self.arm, hr).x, facing(self.arm, hr).y))
        yaw = math.atan2(want.y, want.x) - math.atan2(aimv.y, aimv.x)
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
        # the blow's travel: the striking limb's velocity just before contact
        hr2, hp2, loc2 = c.at(c.strike - 4)
        tip2 = limb_tip(self.arm, fk(self.arm, hr2, hp2, loc2), c.limb)
        hr3, hp3, loc3 = c.at(c.strike - 1)
        tip3 = limb_tip(self.arm, fk(self.arm, hr3, hp3, loc3), c.limb)
        vel = r @ (tip3 - tip2)                      # the limb's travel over the last frames before contact
        if Vector((vel.x, vel.y)).length < 1e-3:
            vel = Vector((want.x, want.y, 0))
        if power is not None:                       # it connects: the target reacts, this fighter gets a hit-stop
            if zone is None:
                zone = {'Head': 'head', 'Neck': 'head', 'Spine2': 'chest', 'Spine1': 'chest', 'Spine': 'gut',
                        'Hips': 'gut'}.get(bone, 'legs')
            # mostly the limb's direction, but always away from the attacker
            away = Vector((want.x, want.y, 0)).normalized()
            vh = Vector((vel.x, vel.y, 0))
            wv = 0.5 * min(1.0, vh.length / max(1e-6, vel.length))      # kicks travel up: trust the line of attack
            dirv = vh.normalized() * wv + away * (1 - wv) if vh.length > 1e-4 else away
            if dirv.dot(away) < 0.2:                                     # never push the defender toward the attacker
                dirv = away
            dirv = dirv.normalized()
            dirv.z = vel.normalized().z
            # sideways component of the blow relative to the line of attack: hooks and roundhouses twist the
            # defender, straight punches don't
            lat = away.cross(vh.normalized()).z * min(1.0, vh.length / max(1e-6, vel.length)) if vh.length > 1e-4 else 0
            st = STYLE.get(move, {})
            if 'lat' in st:                             # keep the measured side, use the move's strength
                sgn = (1 if lat >= 0 else -1) if abs(lat) > 0.05 else (1 if 'Right' in c.limb else -1)
                lat = sgn * st['lat']
            if 'up' in st:
                dirv.z = max(dirv.z, st['up'])
            target.hit(t_strike, self, direction=dirv, power=power, zone=zone, contact=tgt, lat=lat)
            self.stops.append(t_strike)
        return s, tgt, vel.normalized()

    def hit(self, t, from_fighter=None, direction=None, power=1.0, zone='head', contact=None, lat=None):
        """Full-body procedural hit reaction, added on top of whatever the fighter is doing.

        direction: travel of the blow (3D; from the attacker's limb velocity when called from attack()).
        zone: 'head' (snap), 'chest' (rock back), 'gut' (fold over the fist), 'legs' (buckle).
        The underlying motion is interrupted (slowed) for a moment, arms lag and flail, hips twist, knees give."""
        if direction is None and from_fighter is not None:
            a = from_fighter.where(t)[1]
            b = self.where(t)[1]
            direction = Vector((b.x - a.x, b.y - a.y, 0))
        d = Vector(direction)
        dh = Vector((d.x, d.y, 0))
        dh = dh.normalized() if dh.length > 1e-4 else Vector((1, 0, 0))
        up = max(-0.6, min(0.9, d.normalized().z if d.length > 1e-4 else 0.0))
        hr, hp, loc = self.where(t)
        f = facing(self.arm, hr)
        lateral = f.cross(dh).z if lat is None else -lat * 1.0   # sign: + twists the fighter to their left
        self.hits.append({'t': t, 'd': dh, 'up': up, 'p': power, 'zone': zone, 'lat': lateral, 'face': f})
        FIGHT.append((t, from_fighter.name if from_fighter else '?', self.name, 'hit', zone,
                      tuple(contact) if contact is not None else tuple(hp)))

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
            yaw = yaw_of(self.arm, hr)
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
            return s.pose(s.t, self._warp)
        cur = live[-1]
        hr, hp, loc = cur.pose(t, self._warp)
        if len(live) > 1 and t - cur.t < cur.blend:
            prev = live[-2]
            w = (t - cur.t) / cur.blend
            w = w * w * (3 - 2 * w)
            phr, php, ploc = prev.pose(min(t, prev.t1), self._warp)
            hr = phr.to_quaternion().slerp(hr.to_quaternion(), w).to_matrix()
            hp = php.lerp(hp, w)
            loc = {k: ploc.get(k, Quaternion()).slerp(q, w) for k, q in loc.items()}
        return hr, hp, loc

    def where(self, t):
        """pose_at plus the push of hits already taken (where the body really is)."""
        hr, hp, loc = self.pose_at(t)
        push, _, _ = self._hit_offsets(t)
        return hr, hp + push, loc

    def _sep(self, t):
        sep = getattr(self, 'sep', None)
        if not sep:
            return Vector()
        f = t * 30.0
        i = int(math.floor(f))
        a = sep.get(i, Vector()); b = sep.get(i + 1, Vector())
        return a.lerp(b, f - i)

    ZONES = {   # spine-chain pitch weights (positive: away from the blow; negative: folds toward it)
        'head': (('Spine', 0.10), ('Spine1', 0.15), ('Spine2', 0.25), ('Neck', 0.55), ('Head', 1.0)),
        'chest': (('Spine', 0.30), ('Spine1', 0.45), ('Spine2', 0.55), ('Neck', 0.30), ('Head', 0.45)),
        'gut': (('Spine', -0.6), ('Spine1', -0.8), ('Spine2', -0.6), ('Neck', -0.3), ('Head', 0.4)),
        'legs': (('Spine', -0.1), ('Spine1', -0.1), ('Spine2', 0.05), ('Neck', 0.1), ('Head', 0.2)),
    }

    @staticmethod
    def _snap(dt, k=6.5, w=13.0):
        """Impact envelope: 2-frame rise, overshoot, damped settle."""
        if dt < 0:
            return 0.0
        return (1 - math.exp(-dt * 45)) * math.exp(-dt * k) * math.cos(dt * w)

    @staticmethod
    def _slow(dt, rise=22.0, decay=3.2):
        if dt < 0:
            return 0.0
        return (1 - math.exp(-dt * rise)) * math.exp(-dt * decay)

    def _hit_offsets(self, t):
        """(root push, {bone: extra world rotation}, {bone: extra local rotation}) from all hits so far."""
        push = Vector()
        rots, lrots = {}, {}

        def add(store, bn, q):
            store[bn] = q @ store.get(bn, Quaternion())

        Z = Vector((0, 0, 1))
        for h in self.hits:
            dt = t - h['t']
            p, d, zone = h['p'], h['d'], h['zone']
            kpush = 0.32 * p * (1.15 if zone == 'gut' else 0.9 if zone == 'head' else 1.0)
            if dt < 0:
                continue
            if dt > 2.5:
                push += d * kpush
                continue
            # body driven back (more for body shots), with a small hop or drop
            push += d * kpush * (1 - math.exp(-dt * 8))
            push.z += (0.05 * h['up'] * p) * self._slow(dt, 30, 6) - 0.07 * p * self._slow(dt, 18, 5)
            axis = Z.cross(d).normalized()
            env = self._snap(dt)
            pitch = math.radians(34) * p
            for bn, k in self.ZONES[zone]:
                ang = pitch * k * env
                if bn in ('Neck', 'Head') and h['up'] > 0.2:            # uppercut: chin lifts
                    ang += math.radians(25) * p * h['up'] * env
                add(rots, bn, Quaternion(axis, ang))
            # hooks and side kicks: twist the chain and the hips with the blow
            tw = math.radians(28) * p * h['lat']
            for bn, k in (('Hips', 0.25), ('Spine1', 0.2), ('Spine2', 0.3), ('Neck', 0.4), ('Head', 0.7)):
                add(rots, bn, Quaternion(Z, tw * k * self._snap(dt, 6.0, 11.0)))
            # arms: inertia (they trail the torso's whip, then catch up) and a flail on big hits
            lag = 0.07
            whip = pitch * (self._snap(dt) - self._snap(dt - lag)) * (1.0 if zone != 'gut' else -0.8)
            flail = math.radians(48) * max(0.0, p - 0.55) * self._slow(dt, 18, 3.8)
            right = h['face'].cross(Z).normalized()          # the fighter's right
            for sd, sgn in (('Left', -1), ('Right', 1)):
                outv = right * sgn
                add(rots, sd + 'Arm', Quaternion(axis, -whip * 1.3))
                add(rots, sd + 'ForeArm', Quaternion(axis, -whip * 0.9))
                # flail: the arm swings out and up, the side the blow travels toward swings more
                bias = 1.0 + 0.6 * (sgn * -h['lat'])
                add(rots, sd + 'Arm', Quaternion(outv.cross(Z).normalized(), -flail * bias))
                add(rots, sd + 'Shoulder', Quaternion(outv.cross(Z).normalized(), -flail * 0.25 * bias))
                add(rots, sd + 'ForeArm', Quaternion(outv.cross(Z).normalized(), -flail * 0.35 * bias))
            # legs: knees give, more for body shots and leg kicks
            kb = math.radians(26) * p * (1.4 if zone in ('gut', 'legs') else 1.0) * self._slow(dt, 20, 4.5)
            for sd in ('Left', 'Right'):
                add(lrots, sd + 'UpLeg', Quaternion((1, 0, 0), self.knee_sign[0] * kb * 0.6))
                add(lrots, sd + 'Leg', Quaternion((1, 0, 0), self.knee_sign[1] * kb))
        return push, rots, lrots

    def _warp(self, t):
        """Local clip time: a hit interrupts the current move (it nearly stops for ~0.25 s), an attacker's
        contact gets a 2-frame hit-stop."""
        w = t
        for h in self.hits:
            dt = t - h['t']
            if dt > 0:
                hold = 0.22 + 0.12 * h['p']
                w -= 0.75 * min(dt, hold)
        for ts in self.stops:
            dt = t - ts
            if dt > 0:
                w -= 0.9 * min(dt, 0.07)
        return w

    # ---------------------------------------------------------------- feet
    STEP_AT = 0.11          # m of drift before a foot steps
    STEP_T = 0.2            # s per step
    LIFT = 0.07             # m foot lift at mid-step

    def _feet(self, t, hr, hp, loc, o, st, oz=0.0):
        """Planted-foot IK with catch-up steps. o: the root offset the mocap does not know about (push + spacing).
        Each foot carries how much of that offset it has caught up with (st[side]['s']); the foot is drawn at
        (mocap position - o + s), so a foot that has not stepped stays planted on the floor."""
        arm = self.arm
        pts = fk(arm, hr, hp, loc)
        mats = dict(fk.mats)
        targets = {}
        for sd in ('Left', 'Right'):
            fb = PRE + sd + 'Foot'
            if fb not in mats or PRE + sd + 'UpLeg' not in mats or PRE + sd + 'Leg' not in mats:
                return loc
            S = st.setdefault(sd, {'s': o.copy(), 'step': None})
            ank = mats[fb].translation
            grounded = ank.z < arm.data.bones[fb].head_local.z + 0.06        # ankle near its standing height
            if not grounded:                         # in the air (kicks, jumps): the foot drifts back under the body
                S['step'] = None
                g = o - S['s']
                if g.length > 0.025:
                    g = g.normalized() * 0.025
                S['s'] = S['s'] + g
            elif S['step'] is not None:
                ts, a, b = S['step']
                u = (t - ts) / self.STEP_T
                if u >= 1:
                    S['s'] = b.copy(); S['step'] = None
                else:
                    w = u * u * (3 - 2 * u)
                    S['s'] = a.lerp(b, w)
                    S['lift'] = self.LIFT * math.sin(math.pi * u)
            other = st.get('Right' if sd == 'Left' else 'Left')
            lag = o - S['s']
            if grounded and S['step'] is None and lag.length > self.STEP_AT and not (other and other.get('step')):
                # step to where the body is going, a little past it
                S['step'] = (t, S['s'].copy(), o + lag.normalized() * 0.04)
            lift = S.get('lift', 0.0) if S['step'] is not None else 0.0
            targets[sd] = ank - o + S['s'] + Vector((0, 0, lift - oz))      # the knees take the dip, not the feet
        return leg_ik(arm, hr, loc, mats, targets)

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
        feet_state = {}
        f0, f1 = int(round(t0 * 30)), int(round(t1 * 30))
        for fr in range(f0, f1 + 1):
            t = fr / 30.0
            hr, hp, loc = self.pose_at(t)
            push, extra, lextra = self._hit_offsets(t)
            hp = hp + push + self._sep(t)
            if lextra:
                loc = dict(loc)
                for bn, lq in lextra.items():
                    if PRE + bn in loc:
                        loc[PRE + bn] = loc[PRE + bn] @ lq
            if PRE + 'Hips' in [PRE + k for k in extra] and 'Hips' in extra:
                hr = extra.pop('Hips').to_matrix() @ hr
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
            # feet: the root was moved by pushes and spacing, the mocap feet were not. Planted feet stay where they
            # are (leg IK) and when the body has drifted too far the fighter takes a quick step to catch up.
            if self.plant:
                o = push + self._sep(t)
                o = Vector((o.x, o.y, 0))
                loc = self._feet(t, hr, hp, loc, o, feet_state, push.z)
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
                push, _, _ = F._hit_offsets(t)
                o = push + F._sep(t)
                hh = fk(F.arm, hr, hp, loc)[PRE + 'Head']
                hd = (hh[0] + hh[1]) / 2 + o
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
