"""The family and the professionals, as original MakeHuman people (MPFB 2, CC0 assets), built with the Degens
pipeline (humans.build: full rig with face bones, clothing masks, visemes). Nobody here is a real person."""
import bpy, math
import humans

humans.CAST.update({
  # the family lawyer: silver hair, half-rim glasses, three-piece suit and tie
  'lawyer': dict(phen=dict(gender=1.0, age=0.82, muscle=0.4, weight=0.5, height=0.55, proportions=0.5, race=dict(caucasian=0.95, asian=0.0, african=0.05)),
                 skin='old_caucasian_male', hair='short02', brows='eyebrow001', lashes='eyelashes01',
                 clothes=['toigo_male_suit_tie_and_jacket', 'shoes01', 'kwnet_at_optical_glasses'],
                 tint={'short02': (0.0, 0.0, 3.2, (0.78, 0.78, 0.8)), 'toigo_male_suit_tie_and_jacket': (0.0, 0.5, 0.55, None)}),
  # the much younger trophy wife: platinum hair, black halter dress, stilettos
  'wife':   dict(phen=dict(gender=0.0, age=0.38, muscle=0.5, weight=0.42, height=0.62, proportions=0.75, cupsize=0.7, firmness=0.7, race=dict(caucasian=1.0, asian=0.0, african=0.0)),
                 skin='toigo_light_skin_with_makeup', hair='long01', brows='eyebrow010', lashes='eyelashes03',
                 clothes=['toigo_halter_dress_midi', 'toigo_stiletto_booties'],
                 tint={'toigo_halter_dress_midi': (0.0, 0.2, 0.09, None), 'long01': (0.0, 0.3, 5.0, (1.0, 0.92, 0.74)), 'toigo_stiletto_booties': (0.0, 0.2, 0.15, None)}),
  # the son: slicked hair, open suit, sunglasses indoors
  'son':    dict(phen=dict(gender=1.0, age=0.47, muscle=0.6, weight=0.55, height=0.6, proportions=0.6, race=dict(caucasian=0.85, asian=0.1, african=0.05)),
                 skin='young_caucasian_male2', hair='short04', brows='eyebrow002', lashes='eyelashes01',
                 clothes=['toigo_male_suit_3', 'shoes05', 'spamrakuen_sagerfrogs_glasses_01'], tint={}),
  # the priest: white hair, black suit (a clerical collar is added as a prop)
  'priest': dict(phen=dict(gender=1.0, age=0.93, muscle=0.3, weight=0.7, height=0.45, proportions=0.4, race=dict(caucasian=0.9, asian=0.0, african=0.1)),
                 skin='onlytheghosts_old_eurasian_male', hair='short02', brows='eyebrow001', lashes='eyelashes01',
                 clothes=['male_elegantsuit01', 'shoes01'],
                 tint={'male_elegantsuit01': (0.0, 0.15, 0.18, None), 'short02': (0.0, 0.0, 5.0, (0.92, 0.92, 0.92))}),
})

KEYS = ['lawyer', 'wife', 'son', 'priest']


def build(key):
    rig, body, parts = humans.build(key)
    if key == 'son':
        humans.shades(parts['spamrakuen_sagerfrogs_glasses_01'])
    if key == 'priest':
        clerical(parts['male_elegantsuit01'])
    return rig, body, parts


def clerical(obj):
    """Turn male_elegantsuit01's shirt and tie black (a clerical shirt); the white collar tab is a prop."""
    import numpy as np
    m = obj.active_material; nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and 'diffuse' in n.image.name.lower())
    img = tex.image; w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    lum = px[..., :3].mean(-1); sat = px[..., :3].max(-1) - px[..., :3].min(-1)
    suit = np.percentile(lum[px[..., 3] > 0.5], 30)
    light = (lum > suit + 0.08) | (sat > 0.08)          # shirt and tie are lighter or coloured than the black suit
    px[light, :3] = px[light, :3] * 0.0 + (0.035 + 0.04 * (lum[light] - lum[light].mean()))[:, None].clip(0.01, 0.08)
    new = bpy.data.images.new('priest_shirt', w, h, alpha=True); new.pixels.foreach_set(px.ravel()); new.pack(); tex.image = new
