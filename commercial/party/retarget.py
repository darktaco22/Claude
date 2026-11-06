"""
Retargets CMU motion capture (cgspeed's BVH conversion) onto the game's Mixamo rigs, rest-pose relative:
each mapped bone takes the source bone's rotation away from its own rest, re-expressed in the target's frame, so
the different rest poses and bone axes of the two skeletons don't matter.

    clip = sample("93_03.bvh")                         # once per clip, before the characters are loaded
    apply(char, clip, f0=1, f1=720, start=0.0, travel=0.2)
"""
import bpy, math
from mathutils import Quaternion, Vector, Matrix

MAP = {"Hips": "Hips", "LeftUpLeg": "LeftUpLeg", "LeftLeg": "LeftLeg", "LeftFoot": "LeftFoot", "LeftToeBase": "LeftToeBase",
       "RightUpLeg": "RightUpLeg", "RightLeg": "RightLeg", "RightFoot": "RightFoot", "RightToeBase": "RightToeBase",
       "LowerBack": "Spine", "Spine": "Spine1", "Spine1": "Spine2", "Neck": "Neck", "Head": "Head",
       "LeftShoulder": "LeftShoulder", "LeftArm": "LeftArm", "LeftForeArm": "LeftForeArm", "LeftHand": "LeftHand",
       "RightShoulder": "RightShoulder", "RightArm": "RightArm", "RightForeArm": "RightForeArm", "RightHand": "RightHand"}

def _yaw(q_from_vec, to_vec):
    a = math.atan2(to_vec.y, to_vec.x) - math.atan2(q_from_vec.y, q_from_vec.x)
    return Quaternion((0, 0, 1), a)

def sample(path, fps=30):
    """Import a BVH, read every mapped bone's world rotation per frame at `fps`, then remove it."""
    sc = bpy.context.scene
    before = set(bpy.data.objects); acts = set(bpy.data.actions)
    old_fps = sc.render.fps; sc.render.fps = fps
    bpy.ops.import_anim.bvh(filepath=path, use_fps_scale=True, update_scene_fps=False, update_scene_duration=False, frame_start=1, rotate_mode="NATIVE")
    src = next(o for o in bpy.data.objects if o not in before)
    act = src.animation_data.action
    f_end = int(act.frame_range[1])
    rest = {n: (src.matrix_world @ src.data.bones[n].matrix_local).to_quaternion() for n in MAP}
    lu = src.matrix_world @ src.data.bones["LeftUpLeg"].head_local; ru = src.matrix_world @ src.data.bones["RightUpLeg"].head_local
    hip_rest = src.matrix_world @ src.data.bones["Hips"].head_local
    toe = min((src.matrix_world @ src.data.bones[n].head_local).z for n in ("LeftToeBase", "RightToeBase", "LeftFoot", "RightFoot"))
    stand = hip_rest.z - toe   # how high the hips stand above the toes in the rest pose
    rest_fwd = (lu - ru).cross(Vector((0, 0, 1))); rest_fwd.z = 0; rest_fwd.normalize()
    frames = []
    for f in range(1, f_end + 1):
        sc.frame_set(f)
        pb = src.pose.bones
        rot = {n: (src.matrix_world @ pb[n].matrix).to_quaternion() for n in MAP}
        hp = src.matrix_world @ pb["Hips"].head
        l = src.matrix_world @ pb["LeftUpLeg"].head; r = src.matrix_world @ pb["RightUpLeg"].head
        fwd = (l - r).cross(Vector((0, 0, 1))); fwd.z = 0
        frames.append((rot, hp.copy(), fwd.normalized() if fwd.length > 1e-6 else rest_fwd.copy()))
    sc.render.fps = old_fps
    bpy.data.objects.remove(src)
    for a in set(bpy.data.actions) - acts: bpy.data.actions.remove(a)
    return {"rest": rest, "frames": frames, "hip_rest": hip_rest, "stand": stand, "rest_fwd": rest_fwd, "n": len(frames)}

def _pose_at(clip, t):
    """The clip's frame at time t (in frames, float), looping with a short cross-fade."""
    n = clip["n"]; fade = min(12, n // 4)
    def get(i): return clip["frames"][int(i) % n]
    i = t % n
    a = get(i)
    if fade and i > n - fade:   # blend into the loop's start
        k = (i - (n - fade)) / fade; b = get(i - (n - fade))
        rot = {name: a[0][name].slerp(b[0][name], k) for name in a[0]}
        return rot, a[1].lerp(b[1], k), a[2].lerp(b[2], k)
    return a

def apply(c, clip, f0, f1, start=0.0, travel=0.15, speed=1.0, step=1, height_scale=None):
    """Key the clip onto character c (a moves.Char) from scene frame f0 to f1."""
    rig = c.rig
    for pbn in rig.pose.bones:
        for cn in pbn.constraints: cn.mute = True
    B = rig.data.bones; pb = rig.pose.bones
    tgt = {s: d for s, d in MAP.items() if ("mixamorig:" + d) in B}
    rest_t = {d: B["mixamorig:" + d].matrix_local.to_quaternion() for d in tgt.values()}
    parent_of = {d: (B["mixamorig:" + d].parent.name.split(":")[-1] if B["mixamorig:" + d].parent else None) for d in tgt.values()}
    # the source's rest facing turned to the target's (-Y); then the clip's own first facing, so frame one faces -Y
    Rc = _yaw(clip["rest_fwd"], Vector((0, -1, 0)))
    acc = Vector((0, 0, 0))   # the clip's average facing over its first four seconds from `start`
    for k in range(0, 120, 6): acc += _pose_at(clip, start * 30 + k * speed)[2]
    f_first = Rc @ (acc.normalized() if acc.length > 1e-6 else _pose_at(clip, start * 30)[2])
    Ry = _yaw(f_first, Vector((0, -1, 0)))
    R = Ry @ Rc
    s_h = (c.hip.z / max(1e-3, clip["stand"])) if height_scale is None else height_scale
    p0 = None
    for pbn in pb: pbn.rotation_mode = "QUATERNION"
    for f in range(f0, f1 + 1, step):
        rot, hp, _ = _pose_at(clip, start * 30 + (f - f0) * speed)
        if p0 is None: p0 = hp.copy()
        pose_arm = {}
        for s, d in tgt.items():
            delta = rot[s] @ clip["rest"][s].inverted()
            pose_arm[d] = (R @ delta @ R.inverted()) @ rest_t[d]
        for d in tgt.values():
            p = parent_of[d]
            if p in pose_arm:
                rel_rest = rest_t[p].inverted() @ rest_t[d]
                basis = rel_rest.inverted() @ pose_arm[p].inverted() @ pose_arm[d]
            else:
                basis = rest_t[d].inverted() @ pose_arm[d]
            b = pb["mixamorig:" + d]; b.rotation_quaternion = basis; b.keyframe_insert("rotation_quaternion", frame=f)
        # the hips' travel: up and down at the target's scale, sideways damped by `travel`
        d = R @ (hp - p0); dz = (hp.z - clip["stand"]) * s_h   # (the capture's floor is z = 0)
        loc_arm = Vector((d.x * s_h * travel, d.y * s_h * travel, dz))
        hb = B["mixamorig:Hips"]
        pb["mixamorig:Hips"].location = hb.matrix_local.to_3x3().inverted() @ loc_arm
        pb["mixamorig:Hips"].keyframe_insert("location", frame=f)
    rig.location = (0, 0, 0)
