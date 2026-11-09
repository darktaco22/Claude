"""CASH 4 GOLD: three original MakeHuman people (MPFB 2, CC0), built with the Degens pipeline; and the two
Meme Royale units (USELESS, SLERF), loaded from the game's own models and only placed, never modified."""
import bpy, math, os
from mathutils import Vector, Euler
import humans

humans.CAST.update({
  # the pawnbroker: 50s, dyed-red blunt bob, leopard reading glasses, a dark cardigan suit
  'broker':  dict(phen=dict(gender=0.0, age=0.68, muscle=0.4, weight=0.62, height=0.45, proportions=0.45, cupsize=0.5, firmness=0.4, race=dict(caucasian=0.85, asian=0.0, african=0.15)),
                  skin='middleage_caucasian_female', hair='toigo_blunt_bob', brows='eyebrow011', lashes='eyelashes02',
                  clothes=['toigo_fisherman_sweater', 'toigo_wool_pants', 'toigo_flats', 'toigo_round_glasses_leopard'],
                  tint={'toigo_blunt_bob': (0.02, 1.3, 0.8, (0.75, 0.22, 0.12)), 'toigo_fisherman_sweater': (0.33, 0.6, 0.35, (0.35, 0.45, 0.32)), 'toigo_wool_pants': (0.0, 0.3, 0.35, None)}),
  # the groom: tuxedo and bow tie, twenty minutes before his wedding
  'groom':   dict(phen=dict(gender=1.0, age=0.42, muscle=0.55, weight=0.5, height=0.6, proportions=0.6, race=dict(caucasian=0.1, asian=0.0, african=0.9)),
                  skin='young_african_male', hair='short02', brows='eyebrow002', lashes='eyelashes01',
                  clothes=['toigo_suit_with_jacket_and_bowtie', 'shoes01'], tint={'toigo_suit_with_jacket_and_bowtie': (0.0, 0.2, 0.35, None), 'short02': (0.0, 0.2, 0.12, None)}),
  # the grandmother: white bun, navy church dress, pearls of patience
  'grandma': dict(phen=dict(gender=0.0, age=1.0, muscle=0.3, weight=0.6, height=0.35, proportions=0.4, cupsize=0.4, firmness=0.2, race=dict(caucasian=1.0, asian=0.0, african=0.0)),
                  skin='old_caucasian_female', hair='rehmanpolanski_hair_bun_brown', brows='eyebrow011', lashes='eyelashes02',
                  clothes=['toigo_shift_dress', 'toigo_flats', 'spamrakuen_tbm_glasses_frames_01'],
                  tint={'rehmanpolanski_hair_bun_brown': (0.0, 0.0, 4.0, (0.9, 0.9, 0.9)), 'toigo_shift_dress': (0.0, 0.7, 0.45, (0.25, 0.3, 0.6))}),
})
KEYS = ['broker', 'groom', 'grandma']


def build(key):
    return humans.build(key)


def load_unit(path, name):
    """A Meme Royale unit (assets/units/<name>.glb): rig '<name>_rig', mesh '<name>', clips '<clip>_<name>_rig'."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
    rig = bpy.data.objects[f'{name}_rig']; mesh = next(o for o in rig.children if o.type == 'MESH')
    for a in bpy.data.actions:
        if a.name.endswith(f'_{name}_rig'): a.use_fake_user = True
    mesh.cycles.use_motion_blur = True; mesh.cycles.use_deform_motion = False
    rig.animation_data_create(); rig.animation_data.action = None
    return rig, mesh


def schedule(rig, name, sched, fps=30):
    """[(t0, clip, blend_in_s, speed, repeat[, last_frame])], one NLA track per strip, later strips blend over."""
    ad = rig.animation_data
    for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
    for i, e in enumerate(sched):
        t0, clip, blend, speed, rep = e[:5]
        a = bpy.data.actions[f'{clip}_{name}_rig']; tr = ad.nla_tracks.new()
        st = tr.strips.new(f'{i}_{clip}', int(round(t0 * fps)) + 1, a)
        if len(e) > 5: st.action_frame_end = e[5]
        st.scale = 1.0 / speed; st.repeat = rep; st.blend_in = blend * fps; st.extrapolation = 'HOLD' if i == 0 else 'HOLD_FORWARD'
        st.use_auto_blend = False; st.blend_type = 'REPLACE'
