"""THE REAPING - the burned-out mentor: Gigachad slumped in an armchair in a warm, messy lounge (Poly Haven 'Fireplace'
HDRI, CC0), protein shaker in hand. 'My advice? Be me.'"""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from mathutils import Vector
sc = reset(); TEX = os.path.join(A, 'tex')
world_hdri(os.path.join(PH, 'fireplace_4k.hdr'), strength=0.7, rot_deg=arg('--hrot', -25.0, float))
sc.view_settings.look = 'AgX - Medium High Contrast'
g = plane('catcher', 12, 12, (0, 0, 0)); g.is_shadow_catcher = True
CH = Vector((0.0, 1.3, 0.0))
ph('ArmChair_01', tuple(CH), 0.0, 0.82)
SEATZ = seat_top(CH.x, CH.y - 0.05)
G = load('giga', (CH.x, CH.y - 0.02, 0.0), face(0, -1), 1.08)
SEAT = 0.44
sh_m = mat('shaker', (0.06, 0.06, 0.07), 0.35); lid = mat('lid', (0.9, 0.2, 0.2), 0.4)
shaker = cyl('shaker', 0.042, 0.19, (0, 0, 0), sh_m); cap = cyl('shaker_lid', 0.044, 0.05, (0, 0, 0.12), lid); cap.parent = shaker
lab = plane('shaker_label', 0.08, 0.06, (0, -0.0425, 0.0), rot=(math.pi / 2, 0, 0), m=image_mat('shlab', os.path.join(TEX, 'shaker_label.png'), rough=0.5)); lab.parent = shaker
TOTAL = 90; sc.frame_start, sc.frame_end = 1, TOTAL
off, kL, kR = sit_fk(G, SEATZ, front_y=-0.25, flesh=0.1, slope=float(arg('--slope', 19)))
for f in range(1, TOTAL + 1, 2):
    br = math.sin(f * 0.12)
    lift = min(1.0, max(0.0, (f - 40) / 10)) * (1 - min(1.0, max(0.0, (f - 70) / 12)))   # the little toast on "Be me."
    G.key(f, {'hips': off, 'spine': 0.05 + 0.02 * br, 'lean': 0.04, 'twist': 0.05,
              'hand_L': kL + Vector((0.1, 0.1, 0.1)), 'hand_R': Vector((-0.26 + 0.08 * lift, kR.y + 0.15 - 0.2 * lift, kR.z + 0.12 + 0.36 * lift)),
              'look': G.headp + Vector((0.15, -2.0, -0.25 + 0.2 * lift)), 'nosafe': True})
cn = shaker.constraints.new('COPY_LOCATION'); cn.target = G.rig; cn.subtarget = 'mixamorig:RightHand'; shaker.location = (0, 0, 0.02)
cn.use_offset = True
lamp('lamp_key', 'AREA', (-1.5, -0.8, 1.9), tuple(CH + Vector((0, 0, 1.1))), energy=140, color=(1.0, 0.72, 0.45), size=0.8)
lamp('fire_rim', 'POINT', (0.9, 3.4, 0.6), None, energy=90, color=(1.0, 0.45, 0.15), size=0.3)
c = camera('M_giga', (0.3, -0.5, 0.98), tuple(CH + Vector((0, 0, 0.88))), lens=40, fstop=2.2); bind(c, 1)
key_cam(c, 1, loc=(0.3, -0.5, 0.98)); key_cam(c, 90, loc=(0.26, -0.3, 1.0)); handheld(c, seed=21)
sc.camera = c
if '--cams' in argv:
    out = arg('--out', '/tmp/stills'); os.makedirs(out, exist_ok=True)
    for spec in arg('--cams').split(','):
        cn_, f = spec.split('@')
        if cn_ == 'side':
            for m in list(sc.timeline_markers): sc.timeline_markers.remove(m)
            sc.camera = camera('side', (2.0, CH.y - 0.3, 0.8), tuple(CH + Vector((0, 0, 0.7))), lens=35, fstop=11)
        sc.frame_set(int(f)); sc.render.filepath = os.path.join(out, f'{cn_}_{int(f):04d}.png'); bpy.ops.render.render(write_still=True)
finish()
