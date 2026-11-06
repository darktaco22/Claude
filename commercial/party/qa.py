# Per-character glitch check: every other guest hidden, the camera in front of the character's real head (it may have walked
# or been carried by its mocap), framed on its whole body. One image per (character, frame).
import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
names = argv[argv.index("--qa") + 1].split(","); frames = [int(x) for x in argv[argv.index("--qf") + 1].split(",")]; od = argv[argv.index("--qo") + 1]
sc = bpy.context.scene
cam = bpy.data.objects.new("QACam", bpy.data.cameras.new("QACam")); sc.collection.objects.link(cam); sc.camera = cam
for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
cam.data.lens = 35
sc.render.resolution_x, sc.render.resolution_y = 360, 360; sc.cycles.samples = 6
rigs = {o.name.split("_ctrl")[0]: o for o in bpy.data.objects if o.name.endswith("_ctrl")}
def rig_of(n):
    return next((o for o in rigs[n].children if o.type == "ARMATURE"), None)
others = {}
for n, ctrl in rigs.items():
    meshes = [m for r in ctrl.children if r.type == "ARMATURE" for m in r.children if m.type == "MESH"]
    others[n] = meshes
for n in names:
    if n not in rigs: continue
    for k, ms in others.items():
        for m in ms: m.hide_render = (k != n)
    rig = rig_of(n)
    for f in frames:
        sc.frame_set(f)
        hb = rig.pose.bones.get("mixamorig:Head") or rig.pose.bones.get("mixamorig:Hips")
        head = rig.matrix_world @ hb.head
        fwd = -(rig.matrix_world.to_3x3() @ Vector((0, 1, 0))); fwd.z = 0
        fwd = fwd.normalized() if fwd.length > 1e-4 else Vector((0, -1, 0))
        mid = Vector((head.x, head.y, max(0.4, head.z * 0.6)))
        cam.location = mid + fwd * 3.0 + Vector((0.5, 0, 0.5))
        cam.rotation_euler = (mid - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = f"{od}/qa_{n}_{f:04d}.png"; bpy.ops.render.render(write_still=True)
for ms in others.values():
    for m in ms: m.hide_render = False
