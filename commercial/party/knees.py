# Knee check: a knee should bend forward (the way the character faces), never backwards or sideways past its hip line.
# For every guest every 30 frames: the knee's offset from the hip-ankle line, in the character's own frame.
#   blender -b party.blend -P knees.py
import bpy
from mathutils import Vector
sc = bpy.context.scene
rigs = {o.name.split("_ctrl")[0]: o for o in bpy.data.objects if o.name.endswith("_ctrl")}
bad = {}
for f in range(1, sc.frame_end + 1, 30):
    sc.frame_set(f)
    for n, c in rigs.items():
        r = next((x for x in c.children if x.type == "ARMATURE"), None)
        if not r: continue
        pb = r.pose.bones; W = r.matrix_world
        hb = pb.get("mixamorig:Hips")
        if not hb: continue
        # the character's facing: its controller's -Y (every move is written facing -Y in controller space)
        fwd = c.matrix_world.to_3x3() @ Vector((0, -1, 0)); fwd.z = 0
        if fwd.length < 1e-4: continue
        fwd.normalize()
        for side in ("Left", "Right"):
            up, kn, an = pb.get(f"mixamorig:{side}UpLeg"), pb.get(f"mixamorig:{side}Leg"), pb.get(f"mixamorig:{side}Foot")
            if not (up and kn and an): continue
            h, k, a = W @ up.head, W @ kn.head, W @ an.head
            ha = a - h
            if ha.length < 1e-4: continue
            t = max(0.0, min(1.0, (k - h).dot(ha) / ha.length_squared)); off = k - (h + ha * t)
            bentness = off.length / ha.length
            if bentness < 0.08: continue          # nearly straight: nothing to judge
            if off.normalized().dot(fwd) < -0.3:   # bent the wrong way
                bad.setdefault(n, []).append((f, side, round(bentness, 2)))
        # elbows: should sit behind or beside the shoulder-wrist line, never tucked into the body
        M = c.matrix_world.to_3x3(); left = M @ Vector((1, 0, 0))
        for side, sg in (("Left", 1), ("Right", -1)):
            sh, el = pb.get(f"mixamorig:{side}Arm"), pb.get(f"mixamorig:{side}ForeArm")
            if not (sh and el): continue
            hd = pb.get(f"mixamorig:{side}Hand"); s_, e_ = W @ sh.head, W @ el.head; w_ = W @ (hd.head if hd else el.tail)
            sw = w_ - s_
            if sw.length < 1e-4: continue
            t = max(0.0, min(1.0, (e_ - s_).dot(sw) / sw.length_squared)); off = e_ - (s_ + sw * t)
            if off.length / sw.length < 0.08: continue
            if off.normalized().dot(left) * sg < -0.5:
                bad.setdefault(n, []).append((f, side + "Elbow-in", round(off.length / sw.length, 2)))
for n, v in sorted(bad.items()):
    print(f"KNEE {n:12s} backwards at {len(v)} checks, e.g. {v[:4]}")
print("KNEES DONE", len(bad), "guests flagged")
