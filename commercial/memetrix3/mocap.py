"""Motion-capture retargeting for THE MEMETRIX III fights.

CMU mocap (cgspeed BVH conversion, github.com/una-dinosauria/cmu-mocap, free to use) -> the game's Mixamo-named rigs.

Method (full rotations, so spine twist, wrist roll and head turns all transfer):
  1. Parse the BVH and run forward kinematics in numpy (Y-up, +Z forward  ->  Blender Z-up, -Y forward).
  2. Build a reference T-pose for the target: each target bone is turned (shortest arc) from its rest direction to the
     direction of the matching source segment on the source's T-pose frame (frame 0 in cgspeed files).
  3. For every frame:  R_target(b) = R_source(b, f) * R_source(b, T)^-1 * R_targetT(b)   (armature space),
     converted to local pose-bone quaternions down the hierarchy. The root translation is scaled by hip height.

Usage inside Blender:
    import mocap
    act = mocap.retarget(arm_obj, '/path/86_01.bvh', name='zcat:86_01', start=0, end=None, fps=30)
"""
import math
import numpy as np
from mathutils import Matrix, Quaternion, Vector

C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))          # BVH (Y-up, +Z fwd) -> Blender (Z-up, -Y fwd)
CI = C.transposed()

# target bone -> (source joint whose rotation drives it, segment start, segment end) for the T-pose direction
MAP = {
    'Hips': ('Hips', 'Hips', 'Spine1'),
    'Spine': ('LowerBack', 'Hips', 'Spine'),
    'Spine1': ('Spine', 'Spine', 'Spine1'),
    'Spine2': ('Spine1', 'Spine1', 'Neck'),
    'Neck': ('Neck', 'Neck', 'Head'),
    'Head': ('Head', 'Neck1', 'Head'),
}
for s in ('Left', 'Right'):
    MAP.update({
        s + 'Shoulder': (s + 'Shoulder', s + 'Shoulder', s + 'Arm'),
        s + 'Arm': (s + 'Arm', s + 'Arm', s + 'ForeArm'),
        s + 'ForeArm': (s + 'ForeArm', s + 'ForeArm', s + 'Hand'),
        s + 'Hand': (s + 'Hand', s + 'Hand', s + 'FingerBase'),
        s + 'UpLeg': (s + 'UpLeg', s + 'UpLeg', s + 'Leg'),
        s + 'Leg': (s + 'Leg', s + 'Leg', s + 'Foot'),
        s + 'Foot': (s + 'Foot', s + 'Foot', s + 'ToeBase'),
        s + 'ToeBase': (s + 'ToeBase', s + 'Foot', s + 'ToeBase'),
    })


def _rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == 'X':
        return np.stack([np.stack([np.ones_like(a), 0 * a, 0 * a], -1), np.stack([0 * a, c, -s], -1), np.stack([0 * a, s, c], -1)], -2)
    if axis == 'Y':
        return np.stack([np.stack([c, 0 * a, s], -1), np.stack([0 * a, np.ones_like(a), 0 * a], -1), np.stack([-s, 0 * a, c], -1)], -2)
    return np.stack([np.stack([c, -s, 0 * a], -1), np.stack([s, c, 0 * a], -1), np.stack([0 * a, 0 * a, np.ones_like(a)], -1)], -2)


def load_bvh(path):
    """-> names, parents, offsets (J,3), world rotations (F,J,3,3), world positions (F,J,3), frame time."""
    toks = open(path).read().split()
    i = 0
    names, parents, offsets, chans = [], [], [], []
    stack = []
    while toks[i] != 'MOTION':
        t = toks[i]
        if t in ('ROOT', 'JOINT'):
            names.append(toks[i + 1]); parents.append(stack[-1] if stack else -1); offsets.append(None); chans.append([])
            i += 2
        elif t == 'End':
            names.append(names[stack[-1]] + '_end'); parents.append(stack[-1]); offsets.append(None); chans.append([])
            i += 2
        elif t == '{':
            stack.append(len(names) - 1); i += 1
        elif t == '}':
            stack.pop(); i += 1
        elif t == 'OFFSET':
            offsets[stack[-1]] = [float(x) for x in toks[i + 1:i + 4]]; i += 4
        elif t == 'CHANNELS':
            n = int(toks[i + 1]); chans[stack[-1]] = toks[i + 2:i + 2 + n]; i += 2 + n
        else:
            i += 1
    nf = int(toks[i + 2]); ft = float(toks[i + 5])
    data = np.array(toks[i + 6:], dtype=float).reshape(nf, -1)
    J = len(names)
    R = np.zeros((nf, J, 3, 3)); P = np.zeros((nf, J, 3))
    col = 0
    for j in range(J):
        loc = np.zeros((nf, 3)) + np.array(offsets[j])
        rot = np.broadcast_to(np.eye(3), (nf, 3, 3)).copy()
        for c in chans[j]:
            v = data[:, col]; col += 1
            if c.endswith('position'):
                loc[:, 'XYZ'.index(c[0])] = v
            else:
                rot = rot @ _rot(c[0], v)
        p = parents[j]
        if p < 0:
            R[:, j] = rot; P[:, j] = loc
        else:
            R[:, j] = R[:, p] @ rot
            P[:, j] = P[:, p] + np.einsum('fij,fj->fi', R[:, p], loc)
    return names, parents, offsets, R, P, ft


def _m3(a):
    return Matrix([list(r) for r in a])


def sample(arm, bvh_path, start=0, end=None, fps=30, tpose_frame=0, jump_scale=0.8):
    """Retarget source frames [start, end) (source frame numbers) -> per output frame:
    hips_rot (armature-space 3x3), hips_pos (armature-space head position), local {bone: basis quaternion}."""
    if bvh_path not in _BVH:
        _BVH[bvh_path] = load_bvh(bvh_path)
    names, parents, offsets, R, P, ft = _BVH[bvh_path]
    idx = {n: k for k, n in enumerate(names)}
    step = max(1, int(round(1.0 / (ft * fps))))
    end = len(R) if end is None else min(end, len(R))
    frames = list(range(start, end, step))
    bones = arm.data.bones
    pre = 'mixamorig:'
    tb = [b for b in bones if b.name.startswith(pre) and b.name[len(pre):] in MAP]

    def src_rot(j, f):
        return C @ _m3(R[f, j]) @ CI

    def src_pos(j, f):
        return C @ Vector(P[f, j])

    tref = {}
    for b in tb:
        _, a, z = MAP[b.name[len(pre):]]
        if a not in idx or z not in idx:
            continue
        d = (src_pos(idx[z], tpose_frame) - src_pos(idx[a], tpose_frame))
        if d.length < 1e-6:
            continue
        rest = b.matrix_local.to_3x3()
        tref[b.name] = (rest.col[1].normalized().rotation_difference(d.normalized()).to_matrix() @ rest)
    toes = [n for n in ('LeftToeBase', 'RightToeBase') if n in idx]
    # the floor: low percentile of the lowest toe over the whole capture (frame 0 is not always standing on it)
    floor = float(np.percentile(np.minimum(*[P[:, idx[n], 1] for n in toes]), 1)) - 0.0
    floor = (C @ Vector((0, floor, 0))).z
    feet0 = min(src_pos(idx[n], tpose_frame).z for n in toes)
    src_hip = src_pos(idx['Hips'], tpose_frame).z - feet0         # standing hip height (T pose)
    hb = bones[pre + 'Hips']
    k = hb.head_local.z / max(1e-6, src_hip)
    out = {'hips_rot': [], 'hips_pos': [], 'local': [], 'src_low': []}
    prevq = {}
    for f in frames:
        pose = {}
        for b in tb:
            if b.name in tref:
                j = idx[MAP[b.name[len(pre):]][0]]
                pose[b.name] = src_rot(j, f) @ src_rot(j, tpose_frame).inverted() @ tref[b.name]
        loc = {}
        for b in tb:
            if b.name not in pose or b.parent is None:
                continue
            rest = b.matrix_local.to_3x3()
            prest = b.parent.matrix_local.to_3x3()
            par = pose.get(b.parent.name, prest)
            q = (rest.inverted() @ prest @ par.inverted() @ pose[b.name]).to_quaternion()
            if b.name in prevq and prevq[b.name].dot(q) < 0:
                q.negate()
            prevq[b.name] = q
            loc[b.name] = q
        pw = src_pos(idx['Hips'], f)
        out['hips_rot'].append(pose[hb.name])
        dz = (pw.z - floor) - src_hip                 # up/down relative to standing hip height
        kz = max(k, jump_scale * 0.95 / max(1e-6, src_hip)) if dz > 0 else k   # 0.95 m: a human hip        # short-legged rigs still jump high; crouches fit their legs
        out['hips_pos'].append(Vector((hb.head_local.x + pw.x * k, hb.head_local.y + pw.y * k, hb.head_local.z + dz * kz)))
        out['local'].append(loc)
        low = min(src_pos(j, f).z for j in range(len(names))) - floor     # lowest joint above the floor (source units)
        out['src_low'].append(max(0.0, low) * 0.95 / max(1e-6, src_hip))   # in metres, for a human-sized body
    return out


_BVH = {}


def retarget(arm, bvh_path, name, start=0, end=None, fps=30, tpose_frame=0, root_motion=True, mirror=False):
    names, parents, offsets, R, P, ft = load_bvh(bvh_path)
    idx = {n: k for k, n in enumerate(names)}
    step = max(1, int(round(1.0 / (ft * fps))))
    end = len(R) if end is None else min(end, len(R))
    frames = list(range(start, end, step))
    bones = arm.data.bones
    pre = 'mixamorig:'
    tb = [b for b in bones if b.name.startswith(pre) and b.name[len(pre):] in MAP]

    def src_rot(j, f):
        return C @ _m3(R[f, j]) @ CI

    def src_pos(j, f):
        return C @ Vector(P[f, j])

    # reference T pose for the target (armature space rotations)
    tref = {}
    for b in tb:
        key = b.name[len(pre):]
        _, a, z = MAP[key]
        if a not in idx or z not in idx:
            continue
        d = (src_pos(idx[z], tpose_frame) - src_pos(idx[a], tpose_frame))
        if d.length < 1e-6:
            continue
        rest = b.matrix_local.to_3x3()
        cur = rest.col[1].normalized()
        tref[b.name] = (cur.rotation_difference(d.normalized()).to_matrix() @ rest)

    # scale for root motion: hip height
    src_hip = src_pos(idx['Hips'], tpose_frame).z - min(src_pos(idx[n], tpose_frame).z for n in ('LeftToeBase', 'RightToeBase') if n in idx)
    tgt_hip = bones[pre + 'Hips'].head_local.z
    k = tgt_hip / max(1e-6, src_hip)
    p0 = src_pos(idx['Hips'], frames[0])

    act = arm.animation_data.action if False else None
    import bpy
    act = bpy.data.actions.new(name)
    fcs = {}

    def fc(path, i, grp):
        key = (path, i)
        if key not in fcs:
            fcs[key] = act.fcurves.new(path, index=i, action_group=grp)
        return fcs[key]

    prevq = {}
    for n_, f in enumerate(frames):
        pose = {}
        for b in tb:                                    # parents come before children in bones order
            if b.name not in tref:
                continue
            j = idx[MAP[b.name[len(pre):]][0]]
            Rt = src_rot(j, f) @ src_rot(j, tpose_frame).inverted() @ tref[b.name]
            pose[b.name] = Rt
        for b in tb:
            if b.name not in pose:
                continue
            rest = b.matrix_local.to_3x3()
            if b.parent and b.parent.name in pose:
                prest = b.parent.matrix_local.to_3x3()
                basis = rest.inverted() @ prest @ pose[b.parent.name].inverted() @ pose[b.name]
            else:
                basis = rest.inverted() @ pose[b.name]
            q = basis.to_quaternion()
            if b.name in prevq and prevq[b.name].dot(q) < 0:
                q.negate()
            prevq[b.name] = q
            path = 'pose.bones["%s"].rotation_quaternion' % b.name
            for i in range(4):
                fc(path, i, b.name).keyframe_points.insert(n_ + 1, q[i], options={'FAST'})
        if root_motion:
            hb = bones[pre + 'Hips']
            pw = src_pos(idx['Hips'], f)
            d = Vector(((pw.x - p0.x) * k, (pw.y - p0.y) * k, pw.z * k))
            world = Vector((hb.head_local.x + d.x, hb.head_local.y + d.y, d.z))
            loc = hb.matrix_local.to_3x3().inverted() @ (world - hb.head_local)
            for i in range(3):
                fc('pose.bones["%s"].location' % hb.name, i, hb.name).keyframe_points.insert(n_ + 1, loc[i], options={'FAST'})
    for c in act.fcurves:
        c.update()
    act['mocap_src'] = bvh_path.split('/')[-1]
    act['frames'] = len(frames)
    return act
