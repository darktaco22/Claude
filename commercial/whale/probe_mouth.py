"""Find the Whale's mouth line from his mesh: vertices on the boundary between the grey head and the white jaw
(sampled from his base-colour texture at each vertex's UV), in head-bone space at rest."""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.environ['WHALE'])
WR = bpy.data.objects['whale_rig']; WM = bpy.data.objects['whale']
WR.animation_data_create(); WR.animation_data.action = None
for pb in WR.pose.bones: pb.matrix_basis.identity()
bpy.context.view_layer.update()
me = WM.data; mt = WM.active_material
img = next(n.image for n in mt.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and 'base' in (n.label + n.name + n.image.name).lower() or (n.type == 'TEX_IMAGE' and n.image))
w, h = img.size; px = np.array(img.pixels[:]).reshape(h, w, 4)
uvl = me.uv_layers.active.data; vuv = {}
for l in me.loops: vuv[l.vertex_index] = uvl[l.index].uv
hb = WR.pose.bones['mixamorig:Head']; Mh = (WR.matrix_world @ hb.matrix).inverted(); Mw = WM.matrix_world
gi = WM.vertex_groups.get('mixamorig:Head').index
rows = []
for v in me.vertices:
    if not any(g.group == gi and g.weight > 0.5 for g in v.groups): continue
    uv = vuv.get(v.index); 
    if uv is None: continue
    c = px[int(uv.y % 1 * (h - 1)), int(uv.x % 1 * (w - 1)), :3]; lum = c.mean(); sat = c.max() - c.min()
    p = Mw @ v.co; rows.append((p.x, p.y, p.z, lum, sat))
R = np.array(rows); print('HEAD verts', len(R), 'z', R[:, 2].min().round(2), R[:, 2].max().round(2), 'y', R[:, 1].min().round(2), R[:, 1].max().round(2), 'x', R[:, 0].min().round(2), R[:, 0].max().round(2))
# front half of the head; print a lum profile along z at x=0 (front surface) to see grey->white
front = R[R[:, 1] < np.percentile(R[:, 1], 30)]
for z in np.arange(front[:, 2].min(), front[:, 2].max(), 0.03):
    s = front[(abs(front[:, 2] - z) < 0.015) & (abs(front[:, 0]) < 0.08)]
    if len(s): print('Z', round(z, 3), 'lum', round(s[:, 3].mean(), 2), 'y', round(s[:, 1].min(), 3), 'n', len(s))
print('HEADBONE world', tuple(round(x, 3) for x in WR.matrix_world @ hb.head), 'tail', tuple(round(x, 3) for x in WR.matrix_world @ hb.tail))
np.save(sys.argv[-1], R)
