"""The real Meme Royale assets (downloaded from the live game: assets/units/*.glb, assets/arena/*.glb). Units are never
modified: they are placed, scaled to their in-game size, and animated with their own clips through NLA strips."""
import bpy, math, os
from mathutils import Vector

G = os.environ.get('GAME', '')
VIS = 2.15
WORLD = 0.5          # the whole cast and the towers at half the game's size (same proportions)
H = dict(useless=0.8, giga=1.75, whale=2.3, goat=1.5, bonk=1.4, cate=1.3, walter=1.35)     # data.js unit.h
FPS = 30


def vis_h(k): return WORLD * VIS * H[k] ** 0.85                     # render/units.js visH: the height the game draws them at


class Unit:
    """One instance of a game unit. ctrl (an empty) carries position/heading; the rig is its child."""
    _src = {}

    def __init__(self, kind, name=None):
        self.kind = kind; self.name = name or kind
        if kind not in Unit._src:
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=f'{G}/units/{kind}.glb')
            new = [o for o in bpy.data.objects if o not in before]
            for o in new:
                if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
            rig = bpy.data.objects[f'{kind}_rig']; mesh = bpy.data.objects[kind]
            for a in bpy.data.actions:
                if a.name.endswith(f'_{kind}_rig'): a.use_fake_user = True
            Unit._src[kind] = (rig, mesh); self.rig, self.mesh = rig, mesh
        else:                                              # a second instance: copies sharing mesh data and clips
            r0, m0 = Unit._src[kind]
            self.rig = r0.copy(); self.mesh = m0.copy()
            for o in (self.rig, self.mesh): bpy.context.scene.collection.objects.link(o)
            self.mesh.parent = self.rig
            for md in self.mesh.modifiers:
                if md.type == 'ARMATURE': md.object = self.rig
            self.rig.animation_data_clear()
        self.rig.animation_data_create(); self.rig.animation_data.action = None
        for tr in list(self.rig.animation_data.nla_tracks): self.rig.animation_data.nla_tracks.remove(tr)
        self.mesh.cycles.use_motion_blur = True; self.mesh.cycles.use_deform_motion = True
        # scale to the in-game height (mesh rest height)
        self.rig.location = (0, 0, 0); self.rig.rotation_euler = (0, 0, 0); self.rig.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        zs = [(self.mesh.matrix_world @ Vector(c)).z for c in self.mesh.bound_box]
        h = max(zs) - min(zs); self.base = min(zs)
        self.ctrl = bpy.data.objects.new(f'{self.name}_ctrl', None); bpy.context.scene.collection.objects.link(self.ctrl)
        s = vis_h(kind) / h
        self.rig.parent = self.ctrl; self.rig.scale = (s, s, s); self.rig.location = (0, 0, -self.base * s)
        self.ctrl.rotation_mode = 'XYZ'
        self.height = vis_h(kind)
        # the glTF faces +Y in Blender after import (game models face +Z in three.js); heading 0 => facing +Y
        self.strips = []

    def clip(self, name):
        return bpy.data.actions[f'{name}_{self.kind}_rig']

    def clip_len(self, name):
        a = self.clip(name); return a.frame_range[1] - a.frame_range[0]

    def play(self, sched):
        """sched: [(t0, clip, speed, repeat, blend_s)] -> NLA strips, each on its own track (later ones override)."""
        ad = self.rig.animation_data
        for i, e in enumerate(sched):
            t0, name = e[0], e[1]; speed = e[2] if len(e) > 2 else 1.0; rep = e[3] if len(e) > 3 else 1.0
            blend = e[4] if len(e) > 4 else 0.12
            a = self.clip(name); tr = ad.nla_tracks.new()
            st = tr.strips.new(f'{i}_{name}', int(round(t0 * FPS)) + 1, a)
            st.scale = 1.0 / speed; st.repeat = rep; st.blend_in = blend * FPS if i else 0
            st.extrapolation = 'HOLD' if i == 0 else 'HOLD_FORWARD'; st.use_auto_blend = False
            self.strips.append(st)

    def hide(self, f_ranges_hidden, nf):
        """Keys hide_render/hide_viewport on rig + mesh: hidden inside any (f0, f1) range."""
        for f in range(1, nf + 1):
            h = any(a <= f < b for a, b in f_ranges_hidden)
            for o in (self.mesh,):
                o.hide_render = h; o.keyframe_insert('hide_render', frame=f)


def place(path, loc, rz=0.0, s=1.0, name=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name or os.path.basename(path), None); bpy.context.scene.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, rz); root.scale = (s, s, s)
    return root, new


def layer(u, nf, pose_fn, arms_fn=None, fps=FPS):
    """Custom animation on top of the game's clips (the clips stay as they are, untouched underneath):
    pose_fn(t) -> {bone: (x, y, z) degrees}: rotations COMBINED with the clip's pose (bend, lean, tremble).
    arms_fn(t) -> 0..1: how much the arms open wide (their rest pose), REPLACING the clip's arms."""
    import math
    from mathutils import Euler
    ad = u.rig.animation_data
    bones = sorted({b for f in range(1, nf + 1) for b in pose_fn((f - 1) / fps)})
    a = bpy.data.actions.new(f'cust_{u.name}')
    for b in bones:
        pts = [[] for _ in range(4)]
        for f in range(1, nf + 1):
            d = pose_fn((f - 1) / fps).get(b, (0, 0, 0))
            q = Euler([math.radians(x) for x in d]).to_quaternion()
            for i in range(4): pts[i] += [f, q[i]]
        for i in range(4):
            fc = a.fcurves.new(f'pose.bones["mixamorig:{b}"].rotation_quaternion', index=i, action_group=b)
            fc.keyframe_points.add(nf); fc.keyframe_points.foreach_set('co', pts[i])
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    if bones:
        tr = ad.nla_tracks.new(); st = tr.strips.new('cust', 1, a)
        st.blend_type = 'COMBINE'; st.extrapolation = 'HOLD'; st.use_auto_blend = False
    if arms_fn:
        b = bpy.data.actions.new(f'arms_{u.name}')
        brace = Euler((math.radians(28), 0, 0)).to_quaternion()        # arms out wide and angled down: shielding
        for bn in ('LeftShoulder', 'RightShoulder', 'LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm'):
            for i, v in enumerate(brace if bn.endswith('Arm') and 'Fore' not in bn else (1, 0, 0, 0)):
                fc = b.fcurves.new(f'pose.bones["mixamorig:{bn}"].rotation_quaternion', index=i, action_group=bn)
                fc.keyframe_points.add(2); fc.keyframe_points.foreach_set('co', [1, v, nf, v])
        tr = ad.nla_tracks.new(); st = tr.strips.new('arms', 1, b)
        st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD'; st.use_auto_blend = False; st.use_animated_influence = True
        for f in range(1, nf + 1):
            st.influence = arms_fn((f - 1) / fps); st.keyframe_insert('influence', frame=f)
