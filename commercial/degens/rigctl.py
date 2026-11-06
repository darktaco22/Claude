"""Pose controller for a MakeHuman 'default' rig.

Everything is driven by functions of time. Per frame we decide:
  * where the rig object stands (seat or a path) and its facing
  * small FK rotations (root/spine/neck/head/eyes/jaw/lids/fingers), expressed as rotations about
    *armature-space* axes and converted to each bone's local frame
  * IK targets for the hands and feet (world matrices); the wrist copies the target's rotation,
    so the hand's world matrix equals the target and props can be placed exactly at the hand.
A small FK evaluator mirrors Blender's pose math, so we know where the head/mouth/nose will be
without asking Blender to evaluate the scene.
"""
import bpy, math
from mathutils import Matrix, Vector, Quaternion

ARM_CHAIN = ['upperarm01', 'upperarm02', 'lowerarm01', 'lowerarm02']
LEG_CHAIN = ['upperleg01', 'upperleg02', 'lowerleg01', 'lowerleg02']
FINGERS = [f'finger{i}-{j}' for i in range(1, 6) for j in range(1, 4)]


def qrot(axis, ang):
    return Quaternion(Vector(axis).normalized(), ang)


class Keys:
    """Collects keyframe values and writes them in bulk."""
    def __init__(self):
        self.d = {}

    def add(self, idb, path, idx, frame, val):
        self.d.setdefault((idb, path, idx), []).append((frame, val))

    def flush(self, interp='LINEAR'):
        for (idb, path, idx), pts in self.d.items():
            if idb.animation_data is None:
                idb.animation_data_create()
            ad = idb.animation_data
            if ad.action is None:
                ad.action = bpy.data.actions.new(idb.name + '_act')
            fc = ad.action.fcurves.find(path, index=idx) or ad.action.fcurves.new(path, index=idx)
            fc.keyframe_points.clear()
            fc.keyframe_points.add(len(pts))
            flat = [c for p in pts for c in p]
            fc.keyframe_points.foreach_set('co', flat)
            ip = {'LINEAR': 1, 'CONSTANT': 0, 'BEZIER': 2}[interp]
            fc.keyframe_points.foreach_set('interpolation', [ip] * len(pts))
            fc.update()
        self.d = {}


class Actor:
    def __init__(self, name, rig, body, side_names=('L', 'R')):
        self.name, self.rig, self.body = name, rig, body
        B = rig.data.bones
        self.rest = {b.name: b.matrix_local.copy() for b in B}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in B}
        for pb in rig.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        hv = lambda n: B[n].head_local.copy()
        self.hip = {s: hv(f'upperleg01.{s}') for s in 'LR'}
        self.knee = {s: hv(f'lowerleg01.{s}') for s in 'LR'}
        self.ankle = {s: hv(f'foot.{s}') for s in 'LR'}
        self.shoulder = {s: hv(f'upperarm01.{s}') for s in 'LR'}
        self.wrist0 = {s: hv(f'wrist.{s}') for s in 'LR'}
        self.thigh = (self.hip['L'] - self.knee['L']).length
        self.shin = (self.knee['L'] - self.ankle['L']).length
        self.uarm = (self.shoulder['L'] - hv('lowerarm01.L')).length
        self.farm = (hv('lowerarm01.L') - self.wrist0['L']).length
        # mouth / nose / eyes, rest positions (armature space)
        self.mouth = hv('oris01') + Vector((0, -0.012, -0.004)) if 'oris01' in B else hv('head') + Vector((0, -0.11, -0.05))
        self.nose = hv('head') + Vector((0, -0.125, 0.0))
        self.palm = {}
        for s in 'LR':
            w = self.rest[f'wrist.{s}']
            bases = [B[f'finger{i}-1.{s}'].head_local for i in (2, 3, 4, 5)]
            tips = [B[f'finger{i}-3.{s}'].tail_local for i in (2, 3, 4, 5)]
            base_c = sum(bases, Vector()) / 4
            fdir = (sum(tips, Vector()) / 4 - hv(f'wrist.{s}')).normalized()
            lat = (B[f'finger2-1.{s}'].head_local - B[f'finger5-1.{s}'].head_local).normalized()   # pinky -> index
            n = fdir.cross(lat).normalized()
            # palm normal must point to the body's midline in the rest A-pose
            if (n.x > 0) == (s == 'L'):
                n = -n
            n = (n - fdir * n.dot(fdir)).normalized()
            lat = fdir.cross(n).normalized()
            # the palm frame (armature space, right-handed): Y = fingers, Z = palm normal, X = Y x Z
            self.idx_sign = getattr(self, 'idx_sign', {}); self.idx_sign[s] = 1 if (B[f'finger2-1.{s}'].head_local - B[f'finger5-1.{s}'].head_local).dot(lat) > 0 else -1
            F = Matrix((lat, fdir, n)).transposed().to_4x4()
            F.translation = (hv(f'wrist.{s}') * 0.35 + base_c * 0.65) + n * 0.012
            # palm frame expressed in the wrist bone's own frame
            self.palm[s] = w.inverted() @ F
        self.curl_axis = {}
        for s in 'LR':
            n = (self.rest[f'wrist.{s}'] @ self.palm[s]).to_3x3().col[2]
            for f in FINGERS:
                bn = f'{f}.{s}'
                if bn not in B:
                    continue
                d = (B[bn].tail_local - B[bn].head_local).normalized()
                nn = n if not f.startswith('finger1') else (n * 0.6 + (self.rest[f'wrist.{s}'] @ self.palm[s]).to_3x3().col[1] * -0.4).normalized()
                self.curl_axis[bn] = d.cross(nn).normalized()
        self._make_ik()
        self.K = Keys()

    # ------------------------------------------------------------------ setup
    def _empty(self, n, size=0.05):
        o = bpy.data.objects.new(f'{self.name}.{n}', None)
        o.empty_display_size = size
        bpy.context.scene.collection.objects.link(o)
        o.rotation_mode = 'QUATERNION'
        return o

    def _make_ik(self):
        P = self.rig.pose.bones
        self.tgt, self.pole = {}, {}
        for s in 'LR':
            for limb, chain, tipb in (('hand', ARM_CHAIN, 'wrist'), ('foot', LEG_CHAIN, 'foot')):
                t = self._empty(f'{limb}_{s}'); p = self._empty(f'{limb}pole_{s}', 0.03)
                self.tgt[limb, s], self.pole[limb, s] = t, p
                last = P[f'{chain[-1]}.{s}']
                c = last.constraints.new('IK'); c.target = t; c.pole_target = p; c.chain_count = 4
                c.use_tail = True; c.use_stretch = False; c.iterations = 500
                c.pole_angle = math.radians(-90)
                for tw in (chain[1], chain[3]):     # twist bones only twist
                    pb = P[f'{tw}.{s}']; pb.lock_ik_x = True; pb.lock_ik_z = True
                cr = P[f'{tipb}.{s}'].constraints.new('COPY_ROTATION'); cr.target = t
                cr.target_space = 'WORLD'; cr.owner_space = 'WORLD'
        self.cr = {s: P[f'wrist.{s}'].constraints[-1] for s in 'LR'}

    # ------------------------------------------------------------------ FK math
    def local_q(self, bone, q_arm):
        """A rotation given in armature-rest axes, as this bone's local pose rotation."""
        R = self.rest[bone].to_3x3().to_quaternion()
        return R.inverted() @ q_arm @ R

    def fk(self, Q, root_loc, bone):
        """Pose matrix (armature space) of `bone` given local quats Q and the root's location."""
        chain = []
        b = bone
        while b:
            chain.append(b); b = self.parent[b]
        M = None
        for b in reversed(chain):
            q = Q.get(b, Quaternion())
            if M is None:
                M = Matrix.Translation(root_loc) @ self.rest[b] @ q.to_matrix().to_4x4()
            else:
                p = self.parent[b]
                M = M @ (self.rest[p].inverted() @ self.rest[b]) @ q.to_matrix().to_4x4()
        return M

    def point_on(self, Q, root_loc, bone, rest_point, mw):
        """World position of a point rigidly attached to `bone` (given at rest, armature space)."""
        M = self.fk(Q, root_loc, bone)
        return mw @ (M @ (self.rest[bone].inverted() @ rest_point))

    # ------------------------------------------------------------------ keys
    def key_pose(self, f, mw, Q, root_loc, hands, feet, poles, shape=None):
        K = self.K
        K.add(self.rig, 'location', 0, f, mw.translation.x); K.add(self.rig, 'location', 1, f, mw.translation.y); K.add(self.rig, 'location', 2, f, mw.translation.z)
        e = mw.to_euler()
        K.add(self.rig, 'rotation_euler', 2, f, e.z)
        for b, q in Q.items():
            for i in range(4):
                K.add(self.rig, f'pose.bones["{b}"].rotation_quaternion', i, f, q[i])
        rl = self.rest['root'].to_3x3().inverted() @ root_loc   # root_loc is armature-space; pose location is bone-local
        for i in range(3):
            K.add(self.rig, 'pose.bones["root"].location', i, f, rl[i])
        for (limb, s), M in list(hands.items()) + list(feet.items()):
            t = self.tgt[limb, s]
            loc, q = M.translation, M.to_quaternion()
            for i in range(3): K.add(t, 'location', i, f, loc[i])
            for i in range(4): K.add(t, 'rotation_quaternion', i, f, q[i])
        for (limb, s), p in poles.items():
            for i in range(3): K.add(self.pole[limb, s], 'location', i, f, p[i])
        if shape:
            for kname, v in shape.items():
                K.add(self.body.data.shape_keys, f'key_blocks["{kname}"].value', 0, f, v)

    @staticmethod
    def frame(pos, y, z):
        """A right-handed world matrix with the given Y (fingers) and Z (palm normal) directions."""
        y = Vector(y).normalized(); z = Vector(z); z = (z - y * z.dot(y)).normalized(); x = y.cross(z)
        M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = pos; return M

    def hand_matrix_for_palm(self, s, palm_world):
        """World matrix the wrist (and so the IK target) must have so the palm frame lands on palm_world."""
        return palm_world @ self.palm[s].inverted()
