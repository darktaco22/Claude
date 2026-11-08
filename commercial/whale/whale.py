"""The Whale (Meme Royale's legendary unit, assets/units/whale.glb). He is never modified: only placed (propped up
in bed by rotating and moving his rig object) and animated with his own clips through NLA strips."""
import bpy, math, os
import numpy as np
from mathutils import Vector, Euler

TILT = -35.0                                    # leaning back against the pillows (degrees about X)
HIP = Vector((0.0, 0.35, 0.62))                 # where his hips sit on the mattress (bed origin at y=0.2)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)      # an export helper, not part of him
    rig = bpy.data.objects['whale_rig']; mesh = bpy.data.objects['whale']
    for a in list(bpy.data.actions):
        if a.name.endswith('_whale_rig'): a.use_fake_user = True
    mesh.cycles.use_motion_blur = True; mesh.cycles.use_deform_motion = False
    rig.animation_data_create(); rig.animation_data.action = None
    return rig, mesh


def clip(name): return bpy.data.actions[f'{name}_whale_rig']


def place(rig):
    rig.rotation_mode = 'XYZ'; rig.rotation_euler = Euler((math.radians(TILT), 0, 0)); rig.location = (0, 0, 0)
    bpy.context.view_layer.update()
    h = rig.matrix_world @ rig.pose.bones['mixamorig:Hips'].head
    rig.location = HIP - h
    bpy.context.view_layer.update()


def schedule(rig, sched, fps=30):
    """sched: [(t0, clip, blend_in_s, speed, repeat)] played back to back on NLA tracks (alternating for blends)."""
    ad = rig.animation_data; ad.action = None
    for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
    tracks = []
    for i, e in enumerate(sched):
        t0, name, blend, speed, rep = e[:5]
        a = clip(name); tr = ad.nla_tracks.new(); tracks.append(tr)     # one track per strip: later ones blend over
        st = tr.strips.new(f'{i}_{name}', int(round(t0 * fps)) + 1, a)
        if len(e) > 5: st.action_frame_end = e[5]          # play only part of the clip, then hold that pose
        st.scale = 1.0 / speed; st.repeat = rep; st.blend_in = blend * fps; st.extrapolation = 'HOLD_FORWARD'
        st.use_auto_blend = False; st.blend_type = 'REPLACE'
        if i == 0: st.extrapolation = 'HOLD'
    return tracks


def body_points(mesh, frames, step=3):
    """World positions of his evaluated mesh at the given frames (every step-th vertex)."""
    sc = bpy.context.scene; out = []
    for f in frames:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); e = mesh.evaluated_get(dg); M = mesh.matrix_world
        co = np.empty(len(e.data.vertices) * 3); e.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)[::step]
        out.append(co @ np.array(M.to_3x3()).T + np.array(M.translation))
    return np.concatenate(out)
