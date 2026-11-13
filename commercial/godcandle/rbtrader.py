"""The trader: a real-looking man in a hoodie from Microsoft Rocketbox (github.com/microsoft/Microsoft-Rocketbox, MIT licence; avatar Male_Adult_18),
posed by hand-written FK/IK on its 3ds Max Biped skeleton (no twist bones, so no constraints: every bone gets an explicit rotation).

He sits low (a beanbag), hood up, head down over his phone.  The RIGHT hand cradles the phone from BEHIND (fingers up its back, thumb along its edge, nothing
across the glass; the hold is solved so the wrist is nearly straight and no part of the hand is inside the phone); the LEFT index finger taps it.  All the maths is in "body space": the avatar as imported (metres, facing -Y, his left = +X, Z up).

  T = RBTrader(seat_xy=(x, y), face=math.pi)        # face = world yaw; pi means he looks toward +Y
  W = T.pose(frame, t, tip_local)                   # keys the tapping arm; returns the phone's world matrix (origin = centre of its back, +Y top, +Z screen)
"""
import bpy, os, math
from mathutils import Vector, Matrix, Quaternion
RB = os.path.expanduser(os.environ.get('ROCKETBOX', '/home/user/microsoft/microsoft-rocketbox'))
AV = 'Male_Adult_18'
def qrot(axis, ang): return Quaternion(Vector(axis).normalized(), ang)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
THUMB_IN = 0.5
HOLD = dict(t=(0.05, 0.15, 0.15), i=(0.10, 0.10, 0.06), m=(0.10, 0.10, 0.06), r=(0.12, 0.12, 0.06), p=(0.14, 0.14, 0.08))
POINT = dict(t=(0.45, 0.45, 0.35), i=(0.04, 0.05, 0.03), m=(1.1, 1.25, 0.8), r=(1.2, 1.25, 0.8), p=(1.25, 1.25, 0.8))
PW, PL, PD = 0.072, 0.150, 0.0082                     # the phone


class RBTrader:
    def __init__(self, seat_xy, face=math.pi, hip_z=0.50, lean_deg=16.0, pitch=0.62, yaw=0.45, subd=1):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(RB, 'Assets', 'Avatars', 'Adults', AV, 'Export', AV + '.fbx'))
        new = [o for o in bpy.data.objects if o not in before]
        self.arm = arm = next(o for o in new if o.type == 'ARMATURE'); self.mesh = next(o for o in new if o.type == 'MESH')
        for o in new:
            if o.type == 'EMPTY': bpy.data.objects.remove(o)
        for o in (arm, self.mesh): o.animation_data_clear()                  # the FBX carries a baked take: it would override every pose we set
        self._materials()
        if subd:
            sd = self.mesh.modifiers.new('subd', 'SUBSURF'); sd.levels = 0; sd.render_levels = subd; sd.uv_smooth = 'PRESERVE_BOUNDARIES'
        for p in self.mesh.data.polygons: p.use_smooth = True
        # limb bones point at their child, so lengths and directions are plain
        bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones
        for s in 'LR':
            for a_, b_ in (('UpperArm', 'Forearm'), ('Forearm', 'Hand'), ('Thigh', 'Calf'), ('Calf', 'Foot')):
                eb[f'Bip01 {s} {a_}'].tail = eb[f'Bip01 {s} {b_}'].head
        bpy.ops.object.mode_set(mode='OBJECT')
        self.A0 = A0 = arm.matrix_world.copy(); B = arm.data.bones
        def norm(M):
            R = M.to_3x3(); R = Matrix((R.col[0].normalized(), R.col[1].normalized(), R.col[2].normalized())).transposed(); O = R.to_4x4(); O.translation = M.translation; return O
        self.rest = {b.name: norm(A0 @ b.matrix_local) for b in B}; self.parent = {b.name: (b.parent.name if b.parent else None) for b in B}
        self.head_of = {b.name: A0 @ b.head_local for b in B}; self.tail_of = {b.name: A0 @ b.tail_local for b in B}
        for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
        self.mw = Matrix.Translation((seat_xy[0], seat_xy[1], 0)) @ Matrix.Rotation(face, 4, 'Z'); arm.matrix_world = self.mw @ A0
        H = self.head_of
        self.T = Vector((0, 0.03, hip_z - H['Bip01 Pelvis'].z))                      # the pelvis, down onto the seat
        self.L1 = (H['Bip01 L Forearm'] - H['Bip01 L UpperArm']).length; self.L2 = (H['Bip01 L Hand'] - H['Bip01 L Forearm']).length
        self.T1 = (H['Bip01 L Calf'] - H['Bip01 L Thigh']).length; self.T2 = (H['Bip01 L Foot'] - H['Bip01 L Calf']).length
        self.eyes_rest = (H['Bip01 LEye'] + H['Bip01 REye']) / 2
        # palm frames (X = Y x Z, Y = fingers, Z = out of the palm), in each hand bone's frame; finger curl axes
        self.palm, self.idx, self.curl_axis = {}, {}, {}
        for s in 'LR':
            n_ = lambda k: f'Bip01 {s} {k}'
            bases = [H[n_(f'Finger{i}')] for i in (1, 2, 3, 4)]; tips = [self.tail_of[n_(f'Finger{i}2')] for i in (1, 2, 3, 4)]; wr = H[n_('Hand')]
            base_c = sum(bases, Vector()) / 4; fdir = (sum(tips, Vector()) / 4 - wr).normalized(); lat = (bases[0] - bases[3]).normalized(); n = fdir.cross(lat).normalized()
            if (n.x > 0) == (s == 'L'): n = -n                                         # out of the palm = toward the body's midline in the A-pose
            n = (n - fdir * n.dot(fdir)).normalized(); lat = fdir.cross(n).normalized(); self.idx[s] = 1 if (bases[0] - bases[3]).dot(lat) > 0 else -1
            F = Matrix((lat, fdir, n)).transposed().to_4x4(); F.translation = (wr * 0.35 + base_c * 0.65) + n * 0.012
            self.palm[s] = self.rest[n_('Hand')].inverted() @ F; self.Fpalm = getattr(self, 'Fpalm', {}); self.Fpalm[s] = F
            for i in range(5):
                names = [n_(f'Finger{i}'), n_(f'Finger{i}1'), n_(f'Finger{i}2')]
                for j, bn in enumerate(names):
                    d = ((H[names[j + 1]] - H[bn]) if j < 2 else (self.tail_of[bn] - H[bn])).normalized()
                    nn = n if i else (n * 0.6 - fdir * 0.4).normalized(); self.curl_axis[bn] = d.cross(nn).normalized()
        self.lean = math.radians(lean_deg); self.pitch = pitch; self.yaw = yaw
        self._static()
    # ------------------------------------------------------------------ materials: the avatar's own colour / normal / specular maps
    def _materials(self):
        tex = os.path.join(RB, 'Assets', 'Avatars', 'Adults', AV, 'Textures'); files = os.listdir(tex)
        for slot in self.mesh.material_slots:
            m = slot.material; part = 'head' if 'head' in m.name else 'body'; m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
            out = nt.nodes.new('ShaderNodeOutputMaterial'); b = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs[0], out.inputs['Surface'])
            def img(kind, noncolor=False):
                fn = next(f for f in files if f.endswith(f'_{part}_{kind}.tga')); ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(os.path.join(tex, fn))
                if noncolor: ti.image.colorspace_settings.name = 'Non-Color'
                return ti
            nt.links.new(img('color').outputs['Color'], b.inputs['Base Color'])
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8; nt.links.new(img('normal', True).outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
            sp = img('specular', True); mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.9; mr.inputs['To Max'].default_value = 0.45
            nt.links.new(sp.outputs['Color'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
    # ------------------------------------------------------------------ FK
    def fk(self, Q, bone, _c=None):
        """Body-space matrix of `bone` for local rotations Q (pelvis moved by self.T)."""
        c = _c if _c is not None else {}
        if bone in c: return c[bone]
        p = self.parent[bone]; q = Q.get(bone, Quaternion()).to_matrix().to_4x4()
        M = (Matrix.Translation(self.T) @ self.rest[bone] @ q) if p is None else (self.fk(Q, p, c) @ (self.rest[p].inverted() @ self.rest[bone]) @ q)
        c[bone] = M; return M
    def local_q(self, bone, q_body):
        R = self.rest[bone].to_quaternion(); return R.inverted() @ q_body @ R
    def set_world_rot(self, Q, bone, R_des):
        """Give `bone` the body-space orientation R_des (a quaternion), whatever its parents are doing."""
        p = self.parent[bone]; U = (self.fk(Q, p) @ (self.rest[p].inverted() @ self.rest[bone])).to_quaternion(); Q[bone] = U.inverted() @ R_des
    def fingers(self, s, shape, Q):
        for i, key in enumerate('timrp'):
            for j, suf in enumerate(('', '1', '2')):
                bn = f'Bip01 {s} Finger{i}{suf}'; Q[bn] = self.local_q(bn, qrot(self.curl_axis[bn], shape[key][j]))
    def limb(self, Q, s, up, lo, end, target, hint, L1, L2, R_end=None):
        """Two-bone IK: `up` and `lo` reach `target` (body space) with the joint toward `hint`; the end bone takes R_end (or keeps its rest orientation)."""
        n_ = lambda k: f'Bip01 {s} {k}'; S = self.fk(Q, n_(up)).translation; d = target - S; dist = min(d.length, (L1 + L2) * 0.995); ax = d.normalized()
        a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist); hgt = math.sqrt(max(L1 * L1 - a * a, 0.0)); perp = (hint - ax * hint.dot(ax)).normalized(); E = S + ax * a + perp * hgt; Wp = S + ax * dist
        H = self.head_of
        d1 = (H[n_(lo)] - H[n_(up)]).normalized(); self.set_world_rot(Q, n_(up), d1.rotation_difference((E - S).normalized()) @ self.rest[n_(up)].to_quaternion())
        d2 = (H[n_(end)] - H[n_(lo)]).normalized(); Rf = d2.rotation_difference((Wp - E).normalized()) @ self.rest[n_(lo)].to_quaternion()
        Re = R_end if R_end is not None else self.rest[n_(end)].to_quaternion()
        if R_end is not None:                                  # twist the forearm along its own axis toward the hand, so the wrist is not wrung
            rel = Rf.inverted() @ Re; axl = Vector((0, 1, 0)); v = Vector((rel.x, rel.y, rel.z)); tw = Quaternion((rel.w, *(axl * v.dot(axl))))
            if tw.magnitude > 1e-6: tw.normalize(); Rf = Rf @ Quaternion((1, 0, 0, 0)).slerp(tw, 0.7)
        self.set_world_rot(Q, n_(lo), Rf); self.set_world_rot(Q, n_(end), Re); self._fa = (Wp - E).normalized(); return Wp
    @staticmethod
    def frame(pos, y, z):
        y = Vector(y).normalized(); z = Vector(z); z = (z - y * z.dot(y)).normalized(); x = y.cross(z); M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = pos; return M
    def hand_for_palm(self, s, palm_body): return palm_body @ self.palm[s].inverted()
    # ------------------------------------------------------------------ the pose that never changes: body, legs, head, the hand holding the phone
    HS, TS = 'R', 'L'            # he holds the phone in his right hand (the phone is turned to his right, so that forearm lines up with it) and taps with his left
    def _apply(self, Q):
        P_ = self.arm.pose.bones
        P_['Bip01 Pelvis'].location = (self.A0.to_3x3() @ self.arm.data.bones['Bip01 Pelvis'].matrix_local.to_3x3()).inverted() @ self.T
        for b, q in Q.items(): P_[b].rotation_quaternion = q
    def _hold(self, Q, eyes, fwd, down, off):
        """Pose the holding arm for a phone `fwd` in front of and `down` below his eyes; returns (phone matrix, wrist bend in radians)."""
        s = self.HS; sx = {'L': 1, 'R': -1}[s]
        tgt = eyes + Vector((0, -fwd, -down)); n = (eyes - tgt).normalized(); n = (Matrix.Rotation(self.yaw, 3, 'Z') @ n).normalized()
        zup = Vector((0, 0, 1)); top = (zup - n * zup.dot(n)).normalized(); P = self.frame(tgt, top, n)                 # phone: +Y top, +Z screen, origin = centre of the back
        # the palm behind it: fingers straight up the back of the phone (hidden by it), the heel of the hand below its lower end, the thumb along its edge
        t_p = Vector((0, 1, 0)); z_p = Vector((0, 0, 1)); x_p = t_p.cross(z_p); M = Matrix((x_p, t_p, z_p)).transposed().to_4x4(); M.translation = Vector((-self.idx[s] * (0.004 + off[0]), 0.047 + off[1], 0.010 + off[2]))
        palm = P @ M.inverted(); Hd = self.hand_for_palm(s, palm)
        self.limb(Q, s, 'UpperArm', 'Forearm', 'Hand', Hd.translation, Vector((sx * 0.30, 0.2, -1.0)), self.L1, self.L2, Hd.to_quaternion())
        bend = self._fa.angle(palm.to_3x3().col[1]); reach = (Hd.translation - self.fk(Q, f'Bip01 {s} UpperArm').translation).length / (self.L1 + self.L2)
        cx = getattr(self, 'curl_x', 0.0); shape = {k: ((v[0] + cx, v[1] + cx * 0.5, v[2]) if k != 't' else v) for k, v in HOLD.items()}
        self.fingers(s, shape, Q); b0 = f'Bip01 {s} Finger0'; nrm = self.Fpalm[s].to_3x3().col[2]; Q[b0] = self.local_q(b0, qrot(nrm, self.idx[s] * getattr(self, 'thumb_a', THUMB_IN)) @ qrot(self.curl_axis[b0], HOLD['t'][0]))
        return P, bend, reach
    def _inside(self, Q, P, hand_v):
        """How many skinned vertices of the holding hand (thumb, others) are inside the phone."""
        self._apply(Q); bpy.context.view_layer.update(); ev = self.mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh(); Pi = (self.mw @ P).inverted() @ ev.matrix_world; th = fi = 0
        for vi, is_thumb in hand_v:
            p = Pi @ me.vertices[vi].co
            if abs(p.x) < PW / 2 - 0.0003 and abs(p.y) < PL / 2 - 0.0003 and -0.0003 < p.z < PD - 0.0003:
                if is_thumb: th += 1
                else: fi += 1
        ev.to_mesh_clear(); return th, fi
    def _static(self):
        Q = {}; sx = {'L': 1, 'R': -1}; H = self.head_of
        for b, w in (('Bip01 Spine1', 0.5), ('Bip01 Spine2', 0.5)): Q[b] = self.local_q(b, qrot((1, 0, 0), self.lean * w))
        for b, w in (('Bip01 Neck', 0.45), ('Bip01 Head', 0.55)): Q[b] = self.local_q(b, qrot((1, 0, 0), (self.pitch - self.lean * 0.4) * w))
        for s in 'LR':                                                 # feet flat on the floor in front of the seat
            hip = self.fk(Q, f'Bip01 {s} Thigh').translation; ank = Vector((hip.x + sx[s] * 0.07, hip.y - (self.T1 + 0.06), H[f'Bip01 {s} Foot'].z))
            self.limb(Q, s, 'Thigh', 'Calf', 'Foot', ank, Vector((sx[s] * 0.15, -0.4, 1.0)), self.T1, self.T2)
        head = self.fk(Q, 'Bip01 Head'); eyes = head @ (self.rest['Bip01 Head'].inverted() @ self.eyes_rest); self.eyes = eyes
        # where to hold it: the spot (in front of / below his eyes) that bends the wrist least
        best = None
        for fwd in (0.14, 0.18, 0.22, 0.26, 0.30):
            for down in (0.30, 0.36, 0.42, 0.48):
                P, bend, reach = self._hold(dict(Q), eyes, fwd, down, (0, 0, 0)); cost = bend + (4.0 * (reach - 0.93) if reach > 0.93 else 0.0) + (0.5 * (0.5 - reach) if reach < 0.5 else 0.0)
                if best is None or cost < best[0]: best = (cost, fwd, down, bend)
        _, fwd, down, bend = best
        # push the phone off the hand until no part of the palm or fingers is inside it (the skinned mesh itself is tested)
        vg = {g.index: g.name for g in self.mesh.vertex_groups}; hs = self.HS; hand_v = []
        for v in self.mesh.data.vertices:
            if not v.groups: continue
            g = max(v.groups, key=lambda x: x.weight); nm = vg[g.group]
            if nm.startswith(f'Bip01 {hs} Finger') or nm == f'Bip01 {hs} Hand': hand_v.append((v.index, 'Finger0' in nm))
        off = [0.0, 0.0, 0.0]; self.thumb_a = THUMB_IN; self.curl_x = 0.0
        for it in range(80):                                           # lift the phone off the palm; swing the thumb out from under it
            Qc = dict(Q); P, bend, reach = self._hold(Qc, eyes, fwd, down, off); th, fi = self._inside(Qc, P, hand_v)
            if not th and not fi: break
            if fi: off[2] += 0.001
            if th: self.thumb_a -= 0.05
        for it2 in range(25):                                          # then curl the fingers up until they touch its back
            self.curl_x += 0.03; Qc = dict(Q); P, bend, reach = self._hold(Qc, eyes, fwd, down, off); th, fi = self._inside(Qc, P, hand_v)
            if th or fi: self.curl_x -= 0.03; break
        print('HOLD fwd %.2f down %.2f  wrist bend %.0f deg  reach %.2f  lift %.1f mm  thumb %.2f  curl +%.2f' % (fwd, down, math.degrees(bend), reach, off[2] * 1000, self.thumb_a, self.curl_x))
        Q2 = dict(Q); P, bend, reach = self._hold(Q2, eyes, fwd, down, off); Q = Q2; self.Pm = P
        self.fingers(self.TS, POINT, Q)
        # the tapping fingertip in that palm's frame
        ts = self.TS; tipb = f'Bip01 {ts} Finger12'; Qf = {k: v for k, v in Q.items() if f' {ts} Finger' in k}; T_keep = self.T; self.T = Vector()
        tip = self.fk(Qf, tipb) @ (self.rest[tipb].inverted() @ self.tail_of[tipb]); self.T = T_keep; self.tip_pp = self.Fpalm[ts].inverted() @ tip
        self.Q = Q; self._apply(Q); self.Rh0 = self.fk(Q, f'Bip01 {self.HS} Hand')           # where the holding hand starts (body space)
    # ------------------------------------------------------------------ per frame: the tapping arm
    def pose(self, f, t, tip_local):
        Q = dict(self.Q); P = self.Pm; R3 = P.to_3x3(); u, v, n = R3.col[0], R3.col[1], R3.col[2]; s = self.TS; sx = {'L': 1, 'R': -1}[s]
        l = tip_local(t); tip = P.translation + u * l[0] + v * l[1] + n * (l[2] + PD + 0.0005)
        # the finger continues the line of its own forearm (elbow hanging at his side) and dips onto the glass: the wrist stays straight
        S = self.fk(Q, f'Bip01 {s} UpperArm').translation; elbow = S + Vector((sx * 0.05, 0.03, -self.L1 * 0.95)); fa = (tip - elbow).normalized()
        for _ in range(5):                                             # settle: the finger direction follows the forearm the IK actually gives
            fdir = (fa * 0.9 - n * 0.32).normalized(); F = self.frame(Vector(), fdir, Vector((-sx * 0.45, 0.0, -0.85))); F.translation = tip - F.to_3x3() @ self.tip_pp
            Hd = self.hand_for_palm(s, F)
            self.limb(Q, s, 'UpperArm', 'Forearm', 'Hand', Hd.translation, Vector((sx * 0.55, 0.15, -0.8)), self.L1, self.L2, Hd.to_quaternion()); fa = self._fa
        if not hasattr(self, '_said'): self._said = 1; print('TAP wrist bend %.0f deg' % math.degrees(self._fa.angle(fdir)))
        P_ = self.arm.pose.bones
        for b in (f'Bip01 {s} UpperArm', f'Bip01 {s} Forearm', f'Bip01 {s} Hand'):
            pb = P_[b]; q = Q[b]
            prev = getattr(self, '_prev', {}).get(b)
            if prev is not None and prev.dot(q) < 0: q = -q
            self._prev = getattr(self, '_prev', {}); self._prev[b] = q.copy(); pb.rotation_quaternion = q; pb.keyframe_insert('rotation_quaternion', frame=f)
        self._last_left = (Hd.translation.copy(), Hd.to_quaternion())
        return self.mw @ P
    def _key_bones(self, Q, names, f):
        P_ = self.arm.pose.bones; self._prev = getattr(self, '_prev', {})
        for b in names:
            if b not in Q: continue
            q = Q[b]; prev = self._prev.get(b)
            if prev is not None and prev.dot(q) < 0: q = -q
            self._prev[b] = q.copy(); pb = P_[b]; pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = q; pb.keyframe_insert('rotation_quaternion', frame=f)
    def key_right(self, f, disp_body, e_open=0.0, shock=0.0):
        """The phone hand: held where it always was, plus `disp_body` (body space) for the throw; the fingers open by e_open; `shock` (0..1) pulls the hand back and up beside his shoulder."""
        s = self.HS; sx = {'L': 1, 'R': -1}[s]; Q = dict(self.Q); sh = self.fk(Q, f'Bip01 {s} UpperArm').translation
        tgt = self.Rh0.translation + disp_body + Vector((sx * 0.10, 0.12, 0.16)) * shock
        self.limb(Q, s, 'UpperArm', 'Forearm', 'Hand', tgt, Vector((sx * 0.30, 0.2, -1.0)), self.L1, self.L2, self.Rh0.to_quaternion())
        OPEN = dict(t=(0.05, 0.1, 0.1), i=(0.06, 0.06, 0.04), m=(0.08, 0.08, 0.05), r=(0.12, 0.12, 0.06), p=(0.16, 0.16, 0.1))
        shape = {k: tuple(h * (1 - e_open) + o * e_open for h, o in zip(HOLD[k], OPEN[k])) for k in HOLD}; keep = Q.get(f'Bip01 {s} Finger0')
        self.fingers(s, shape, Q)
        if keep is not None: Q[f'Bip01 {s} Finger0'] = keep
        self._key_bones(Q, [f'Bip01 {s} UpperArm', f'Bip01 {s} Forearm', f'Bip01 {s} Hand'] + [b for b in Q if f'Bip01 {s} Finger' in b], f)
    def shock_left(self, f, e):
        """The tapping hand leaves the screen and flies out to the side in alarm (e = 0..1 from where it last was)."""
        s = self.TS; sx = {'L': 1, 'R': -1}[s]; Q = dict(self.Q); S = self.fk(Q, f'Bip01 {s} UpperArm').translation
        t0, q0 = self._last_left; t1 = S + Vector((sx * 0.30, -0.16, -0.02)); tgt = t0.lerp(t1, e)
        self.limb(Q, s, 'UpperArm', 'Forearm', 'Hand', tgt, Vector((sx * 0.55, 0.15, -0.8)), self.L1, self.L2, q0)
        self._key_bones(Q, [f'Bip01 {s} UpperArm', f'Bip01 {s} Forearm', f'Bip01 {s} Hand'], f)
    def react(self, f, e, look_up=-1.05):
        """Shock, e = 0..1: head thrown back to stare straight up, jaw dropped, brows and upper lids raised.  Keyed at frame f."""
        P_ = self.arm.pose.bones; B = self.arm.data.bones; A3 = self.A0.to_3x3()
        ang = (self.pitch - self.lean * 0.4) * (1 - e) + look_up * e
        for b, w in (('Bip01 Neck', 0.45), ('Bip01 Head', 0.55)):
            pb = P_[b]; pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = self.local_q(b, qrot((1, 0, 0), ang * w)); pb.keyframe_insert('rotation_quaternion', frame=f)
        if 'Bip01 MJaw' in P_:
            pb = P_['Bip01 MJaw']; pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = self.local_q('Bip01 MJaw', qrot((1, 0, 0), 0.42 * e)); pb.keyframe_insert('rotation_quaternion', frame=f)
        for b, dz in (('Bip01 LInnerEyebrow', 0.007), ('Bip01 RInnerEyebrow', 0.007), ('Bip01 LOuterEyebrow', 0.008), ('Bip01 ROuterEyebrow', 0.008), ('Bip01 MMiddleEyebrow', 0.006),
                      ('Bip01 LEyeBlinkTop', 0.0025), ('Bip01 REyeBlinkTop', 0.0025), ('Bip01 MBottomLip', -0.004)):
            if b in P_:
                pb = P_[b]; pb.location = (A3 @ B[b].matrix_local.to_3x3()).inverted() @ Vector((0, 0, dz * e)); pb.keyframe_insert('location', frame=f)
    def finish(self):
        ad = self.arm.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
