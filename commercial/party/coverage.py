# Camera coverage: does the sweep actually show everyone, and every gag when it happens?
# Every 5 frames, for each guest: in frame?  unblocked (rays from the camera to head and chest)?  how tall on screen?
# Prints, per guest, how long and how big it is seen, then each gag's moment.
#   blender -b party.blend -P coverage.py
import bpy, math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view as w2c
sc = bpy.context.scene; cam = sc.camera
rigs = {o.name.split("_ctrl")[0]: o for o in bpy.data.objects if o.name.endswith("_ctrl")}
def rig(n): return next((r for r in rigs[n].children if r.type == "ARMATURE"), None)
gm = {m: n for n, c in rigs.items() for r in c.children if r.type == "ARMATURE" for m in r.children if m.type == "MESH"}
SEE = ("puff", "cloud", "smoke", "gas", "bill", "confetti", "laser", "glass", "pane", "string", "trail", "launch", "chamber", "bubble", "doge_", "lbl")
def pts_of(n):
    r = rig(n); out = []
    for b in ("mixamorig:Head", "mixamorig:Spine1", "mixamorig:Hips"):
        pb = r.pose.bones.get(b) if r else None
        if pb:
            p = r.matrix_world @ pb.head
            if p.z > -0.05 or not out: out.append(p)   # swimmers: count what's above the water
    if not out: out = [rigs[n].matrix_world.translation + Vector((0, 0, 0.6))]
    return out
def look(n, dg):
    """(fraction of points in frame and unblocked, on-screen height as a fraction of the frame)"""
    cp = cam.matrix_world.translation; P = pts_of(n); good = 0; ys = []
    top = P[0] + Vector((0, 0, 0.25)); foot = rigs[n].matrix_world.translation
    for p in P:
        v = w2c(sc, cam, p)
        if not (0.02 < v.x < 0.98 and 0.02 < v.y < 0.98 and v.z > 0.3): continue
        d = p - cp; L = d.length; d.normalize(); o = cp.copy(); t = 0.0; ok = True
        while t < L - 0.2:
            hit, loc, _, _, ob, _ = sc.ray_cast(dg, o + d * (t + 0.01), d, distance=L - t)
            if not hit: break
            if ob in gm and gm[ob] == n: break
            if ob in gm or any(k in ob.name.lower() for k in SEE): t = (loc - o).length + 0.02; continue
            ok = False; break
        if ok: good += 1
    a, b = w2c(sc, cam, top), w2c(sc, cam, foot)
    h = abs(a.y - b.y) if (a.z > 0 and b.z > 0) else 0.0
    return good / len(P), h

stats = {n: [0, 0.0, 0] for n in rigs}   # frames seen well, biggest size, frame of biggest
for f in range(1, sc.frame_end + 1, 5):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    for n in rigs:
        frac, h = look(n, dg)
        if frac >= 0.67 and h > 0.12:
            stats[n][0] += 5
            if h > stats[n][1]: stats[n][1], stats[n][2] = h, f
for n, (fr, h, f) in sorted(stats.items(), key=lambda kv: kv[1][0]):
    flag = "  <-- BARELY SEEN" if fr < 30 or h < 0.2 else ""
    print(f"COVER {n:12s} seen well {fr:4d} frames ({fr / 30:4.1f} s), biggest {h:4.2f} of frame at f{f}{flag}")

# the gags at their moments: (name, frames, guests that must be in shot)
GAGS = [("popcat cannonball", (195, 205, 215, 222), ("popcat",)), ("swordcat backflip", (384, 392, 400, 408), ("swordcat",)),
        ("whale + girls make it rain", (380, 395, 410, 425), ("whale", "wojakgirl", "doomergirl")),
        ("farter snort + lmao", (490, 505, 520, 535), ("farter", "lmao")), ("window kiss", (480, 500, 520, 540), ("troll", "michi")),
        ("island snort", (585, 595, 605, 615), ("ket", "cate")), ("pergola kiss", (650, 665, 680), ("pepe", "pippin")),
        ("smokers", (685, 695, 705, 715), ("walter", "floki", "toshi")), ("bong", (735, 745, 755, 765, 772), ("wojak", "apu")),
        ("dj + dance floor", (300, 320, 340), ("triplet", "giga", "brett", "npcwojak")), ("conga", (800, 815, 830), ("useless", "wif", "bonk", "pnut")),
        ("drunk on the lawn", (800, 840, 870), ("chillhouse",)), ("pink wojak", (180, 200, 220), ("pinkwojak",)), ("doge", (120, 140, 160), ("doge",)),
        ("fwog on the pizza", (170, 190, 210, 230), ("fwog",)), ("walkers", (230, 260, 800, 830), ("chillguy", "jeanphil")), ("dope inside", (480, 540, 560), ("dope",))]
for name, frs, who in GAGS:
    res = []
    for f in frs:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        res.append(" ".join(f"{n}:{'ok' if (lambda fh: fh[0] >= 0.67 and fh[1] > 0.1)(look(n, dg)) else '--'}" for n in who if n in rigs))
    print(f"GAG {name:28s} " + " | ".join(f"f{f} {r}" for f, r in zip(frs, res)))
r = bpy.data.objects.get("rocket")
if r:
    out = []
    for f in (800, 820, 840, 860, 880, 900):
        sc.frame_set(f); v = w2c(sc, cam, r.matrix_world.translation + Vector((0, 0, 1.5)))
        out.append(f"f{f} {'in' if 0 < v.x < 1 and 0 < v.y < 1 and v.z > 0 else 'out'}")
    print("GAG rocket launch               " + " | ".join(out))
print("COVERAGE DONE")
