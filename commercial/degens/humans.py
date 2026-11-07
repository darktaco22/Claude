"""The cast as realistic MakeHuman people (MPFB 2 with CC0 assets) on MakeHuman's full 'default' rig
(face bones: jaw, eyelids, eyes), plus each character's finishing: clothing masks so skin never pokes
through, recolours, Earl's flannel, Chad's backwards cap and shades, and lip-sync visemes."""
import bpy, os, math, importlib
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

MPFB_DATA = os.path.expanduser('~/.config/blender/4.2/extensions/.user/user_default/mpfb/data')
def HS():
    return importlib.import_module('bl_ext.user_default.mpfb.services.humanservice').HumanService
def TS():
    return importlib.import_module('bl_ext.user_default.mpfb.services.targetservice').TargetService

CAST = {
  # the host: grey bob, black frames, mustard cable-knit, wool slacks
  'pam':   dict(phen=dict(gender=0.0, age=0.82, muscle=0.4, weight=0.62, height=0.4, proportions=0.5, cupsize=0.5, firmness=0.35, race=dict(caucasian=0.9, asian=0.05, african=0.05)),
               skin='old_caucasian_female', hair='bob02', brows='eyebrow011', lashes='eyelashes02',
               clothes=['toigo_fisherman_sweater', 'toigo_wool_pants', 'toigo_flats', 'spamrakuen_tbm_glasses_frames_01'],
               tint={'toigo_fisherman_sweater': (0.10, 1.25, 0.95, (0.85, 0.62, 0.22)), 'bob02': (0.0, 0.25, 0.78, None)}),
  # blonde curled bob, pink sweater
  'linda': dict(phen=dict(gender=0.0, age=0.6, muscle=0.45, weight=0.58, height=0.45, proportions=0.6, cupsize=0.55, firmness=0.45, race=dict(caucasian=1.0, asian=0.0, african=0.0)),
               skin='middleage_caucasian_female', hair='toigo_curled_under_bob', brows='eyebrow010', lashes='eyelashes03',
               clothes=['toigo_fisherman_sweater', 'toigo_wool_pants', 'toigo_ballet_flats'],
               tint={'toigo_fisherman_sweater': (0.0, 0.85, 1.25, (0.92, 0.55, 0.68)), 'toigo_curled_under_bob': (0.0, 0.75, 2.1, (1.0, 0.86, 0.55)), 'toigo_wool_pants': (0.0, 0.6, 0.55, None)}),
  # bald, heavy, red flannel and jeans
  'earl':  dict(phen=dict(gender=1.0, age=0.9, muscle=0.35, weight=0.85, height=0.5, proportions=0.4, race=dict(caucasian=0.95, asian=0.0, african=0.05)),
               skin='old_caucasian_male', hair=None, brows='eyebrow001', lashes='eyelashes01',
               clothes=['male_casualsuit03', 'shoes01'], tint={}),
  # backwards red cap, shades, white tee
  'chad':  dict(phen=dict(gender=1.0, age=0.5, muscle=0.8, weight=0.6, height=0.62, proportions=0.6, race=dict(caucasian=0.7, asian=0.0, african=0.3)),
               skin='young_caucasian_male', hair='short02', brows='eyebrow002', lashes='eyelashes01',
               clothes=['male_casualsuit06', 'shoes05', 'frankyaye_glasses_library_male'], tint={}),
}
VISEMES = {'aa': 'aa_02', 'ow': 'ow_08', 'ee': 'y_iy_ih_ix_06', 'mm': 'p_b_m_21', 'ff': 'f_v_18'}


def build(key, subdiv=1):
    H = HS(); c = CAST[key]
    info = {'name': key, 'phenotype': c['phen'], 'rig': 'default', 'skin_mhmat': f"skins/{c['skin']}/{c['skin']}.mhmat",
            'skin_material_type': 'ENHANCED_SSS', 'eyes': 'eyes/high-poly/high-poly.mhclo', 'eyes_material_type': 'MAKESKIN',
            'eyebrows': f"eyebrows/{c['brows']}/{c['brows']}.mhclo", 'eyelashes': f"eyelashes/{c['lashes']}/{c['lashes']}.mhclo",
            'teeth': 'teeth/teeth_base/teeth_base.mhclo', 'tongue': 'tongue/tongue01/tongue01.mhclo',
            'hair': f"hair/{c['hair']}/{c['hair']}.mhclo" if c['hair'] else '',
            'clothes': [f"clothes/{n}/{n}.mhclo" for n in c['clothes']], 'clothes_material_type': 'MAKESKIN',
            'targets': [], 'proxy': '', 'alternative_materials': {}}
    s = H.get_default_deserialization_settings(); s['subdiv_levels'] = subdiv
    body = H.deserialize_from_dict(info, s)
    rig = body.parent
    parts = {o.name.split('.', 1)[1]: o for o in rig.children if o.type == 'MESH'}
    for n, (hue, sat, val, mult) in c['tint'].items():
        tint(parts[n], hue, sat, val, mult)
    for o in parts.values():
        o.cycles.use_motion_blur = False   # deformation blur is slow; object blur is enough
    if key == 'earl':
        flannel(parts['male_casualsuit03'])
    if key == 'chad':
        shades(parts['frankyaye_glasses_library_male']); plain_tee(parts['male_casualsuit06'])
    garments = [o for n, o in parts.items() if n in c['clothes'] and 'glasses' not in n and 'shoes' not in n and 'flats' not in n]
    mask_under(body, garments + [o for n, o in parts.items() if 'shoes' in n or 'flats' in n])
    # garment over garment: the trousers' waist under a sweater
    tops = [o for n, o in parts.items() if 'sweater' in n]
    for o in parts.values():
        if 'pants' in o.name and tops:
            mask_under(o, tops, reach=0.035)
    for v, f in VISEMES.items():
        TS().load_target(body, f'{MPFB_DATA}/targets/visemes/{f}.target', weight=0.0, name='v_' + v)
    return rig, body, parts


def tint(obj, hue_shift, sat, val, mult):
    m = obj.active_material; nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    link = bsdf.inputs['Base Color'].links[0]; src = link.from_socket
    hsv = nt.nodes.new('ShaderNodeHueSaturation'); hsv.inputs['Hue'].default_value = 0.5 + hue_shift
    hsv.inputs['Saturation'].default_value = sat; hsv.inputs['Value'].default_value = val
    nt.links.new(src, hsv.inputs['Color']); out = hsv.outputs['Color']
    if mult:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        mx.inputs[7].default_value = (*mult, 1); nt.links.new(out, mx.inputs[6]); out = mx.outputs[2]
    nt.links.new(out, bsdf.inputs['Base Color'])


def flannel(obj):
    """Repaint the striped shirt of male_casualsuit03 as worn red buffalo-check flannel (jeans untouched)."""
    m = obj.active_material; nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and 'diffuse' in n.image.name)
    img = tex.image; w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    jeans = (b > r + 0.04) & (b > 0.12)
    shirt = (~jeans) & (lum > 0.03)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    P = 96.0
    u = ((xx % P) < P * 0.5).astype(np.float32); v = ((yy % P) < P * 0.5).astype(np.float32)
    thin_u = (np.abs((xx % P) - P * 0.75) < 2.5).astype(np.float32); thin_v = (np.abs((yy % P) - P * 0.75) < 2.5).astype(np.float32)
    dark = u * v; mid = np.clip(u + v, 0, 1) - dark
    red = np.array([0.42, 0.035, 0.03]); blk = np.array([0.025, 0.02, 0.02]); mixc = np.array([0.17, 0.025, 0.022])
    col = red[None, None, :] * (1 - mid - dark)[..., None] + mixc[None, None, :] * mid[..., None] + blk[None, None, :] * dark[..., None]
    col = col * (1 - 0.35 * np.clip(thin_u + thin_v, 0, 1))[..., None] + np.array([0.25, 0.2, 0.12])[None, None, :] * (0.35 * np.clip(thin_u + thin_v, 0, 1))[..., None] * 0.3
    noise = np.random.default_rng(3).normal(1, 0.06, (h, w)).astype(np.float32)
    shade = np.clip(lum / max(np.percentile(lum[shirt], 70), 1e-3), 0.35, 1.25) * 0.55 + 0.45
    out = px.copy()
    for i in range(3):
        out[..., i] = np.where(shirt, col[..., i] * shade * noise, px[..., i])
    new = bpy.data.images.new('earl_flannel', w, h, alpha=True)
    new.pixels.foreach_set(out.ravel()); new.pack()
    tex.image = new


def plain_tee(obj):
    """Paint out the printed logo on male_casualsuit06's white tee (upper part of the atlas)."""
    m = obj.active_material; nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and 'diffuse' in n.image.name)
    img = tex.image; w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rows = np.arange(h)[:, None] > h * 0.55          # pixel rows are bottom-up: the tee is the top of the image
    sat = px[..., :3].max(-1) - px[..., :3].min(-1); lum = px[..., :3].mean(-1)
    logo = rows & ((sat > 0.06) | (lum < 0.62)) & (px[..., 2] < px[..., 0] + 0.15)
    from scipy import ndimage
    logo = ndimage.binary_dilation(logo, iterations=4) & rows
    base = np.median(px[rows & ~logo][:, :3], axis=0)
    px[logo, :3] = base
    new = bpy.data.images.new('chad_tee', w, h, alpha=True); new.pixels.foreach_set(px.ravel()); new.pack(); tex.image = new


def shades(obj):
    """Make the library glasses read as dark sunglasses: black frame, tinted glossy lenses.
    The temples are widened a little so they rest on the ears instead of entering the head."""
    for v in obj.data.vertices:
        if abs(v.co.x) > 0.04: v.co.x *= 1.0 + 0.12 * min(1.0, (abs(v.co.x) - 0.04) / 0.03)
    m = obj.active_material; nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    for l in list(bsdf.inputs['Base Color'].links): nt.links.remove(l)
    bsdf.inputs['Base Color'].default_value = (0.01, 0.01, 0.012, 1); bsdf.inputs['Roughness'].default_value = 0.08
    bsdf.inputs['Metallic'].default_value = 0.2
    for l in list(bsdf.inputs['Alpha'].links): nt.links.remove(l)
    bsdf.inputs['Alpha'].default_value = 1.0


def mask_under(target, covers, reach=0.05, inside=0.025):
    """Hide the target's vertices that a cover garment sits right over: a ray along the vertex normal
    hits the garment within `reach` outside, or within `inside` beneath the surface (the garment fitted
    a little inside the body, which is where skin pokes through). The same test a centimetre to each
    side must hit too, so cuffs and necklines keep their edges."""
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for c in covers:
        ev = c.evaluated_get(dg); me = ev.to_mesh()
        trees.append(BVHTree.FromPolygons([c.matrix_world @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons]))
        ev.to_mesh_clear()
    # the target as it really is (shape keys applied), with no topology-changing modifiers
    saved = [(m, m.show_viewport) for m in target.modifiers]
    for m, _ in saved:
        if m.type != 'ARMATURE': m.show_viewport = False
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(dg); me = ev.to_mesh()
    mw = target.matrix_world; nm = mw.to_3x3().inverted().transposed()
    P = [mw @ v.co for v in me.vertices]; N = [(nm @ v.normal).normalized() for v in me.vertices]
    ev.to_mesh_clear()
    for m, sv in saved: m.show_viewport = sv
    allowed = None
    vg = target.vertex_groups.get('body')
    if vg is not None and target.name.endswith('.body'):
        allowed = {v.index for v in target.data.vertices if any(g.group == vg.index for g in v.groups)}
    def covered(t, p, n):
        if t.ray_cast(p - n * 0.003, n, reach)[0] is not None: return True
        return t.ray_cast(p + n * 0.003, -n, inside)[0] is not None
    # forearms and wrists need a wide margin (sleeves ride up when arms bend); elsewhere a narrow one
    wide = set()
    if target.name.endswith('.body'):
        gn = {g.index: g.name for g in target.vertex_groups}
        for v in target.data.vertices:
            gs = [(gn[g.group], g.weight) for g in v.groups if gn[g.group].startswith(('lowerarm', 'wrist', 'upperarm', 'finger', 'metacarpal', 'spine', 'neck', 'clavicle', 'pelvis', 'upperleg', 'lowerleg', 'foot', 'head', 'breast', 'root'))]
            if gs and max(gs, key=lambda x: x[1])[0].startswith(('lowerarm', 'wrist')): wide.add(v.index)
    hide = []
    for i, (p, n) in enumerate(zip(P, N)):
        if allowed is not None and i not in allowed:
            continue
        margin = 0.03 if i in wide else 0.012
        for t in trees:
            if not covered(t, p, n):
                continue
            a = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized(); b = n.cross(a)
            if all(covered(t, p + d * margin, n) for d in (a, -a, b, -b)):
                hide.append(i); break
    g = target.vertex_groups.new(name='under_clothes'); g.add(hide, 1.0, 'REPLACE')
    mod = target.modifiers.new('under_clothes', 'MASK'); mod.vertex_group = 'under_clothes'; mod.invert_vertex_group = True
    i = target.modifiers.find('under_clothes')
    while i > 0 and target.modifiers[i - 1].type != 'ARMATURE':
        target.modifiers.move(i, i - 1); i -= 1
    return len(hide)
