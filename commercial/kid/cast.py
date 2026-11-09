"""7 CENTS: four original MakeHuman people (MPFB 2, CC0) built with the Degens pipeline. Nobody here is a real person."""
import humans
humans.CAST.update({
  # the kid: thirteen, ponytail, a grey tracksuit
  'kid':  dict(phen=dict(gender=0.0, age=0.25, muscle=0.45, weight=0.45, height=1.0, proportions=0.5, cupsize=0.2, firmness=0.5, race=dict(caucasian=0.7, asian=0.2, african=0.1)),
               skin='young_caucasian_female', hair='ponytail01', brows='eyebrow010', lashes='eyelashes03',
               clothes=['toigo_fisherman_sweater', 'cortu_cargo_pants', 'shoes05'], tint={'toigo_fisherman_sweater': (0.0, 0.15, 0.75, None)}),
  # dad: mid-forties, glasses, a work shirt, already exhausted
  'dad':  dict(phen=dict(gender=1.0, age=0.6, muscle=0.45, weight=0.62, height=0.55, proportions=0.5, race=dict(caucasian=0.75, asian=0.2, african=0.05)),
               skin='middleage_caucasian_male', hair='short04', brows='eyebrow001', lashes='eyelashes01',
               clothes=['namuhekam_male_polo_shirt', 'cortu_cargo_pants', 'shoes01', 'kwnet_at_optical_glasses'], tint={'namuhekam_male_polo_shirt': (0.55, 0.6, 0.7, None)}),
  # mom: a dusky-pink robe, coffee before words
  'mom':  dict(phen=dict(gender=0.0, age=0.56, muscle=0.4, weight=0.52, height=0.5, proportions=0.55, cupsize=0.5, firmness=0.5, race=dict(caucasian=0.75, asian=0.2, african=0.05)),
               skin='middleage_caucasian_female', hair='toigo_curled_under_bob', brows='eyebrow011', lashes='eyelashes02',
               clothes=['mindfront_kimono', 'toigo_flats'], tint={'mindfront_kimono': (0.0, 0.5, 0.9, (0.85, 0.55, 0.6))}),
  # the repo man: work coveralls, no expression
  'repo': dict(phen=dict(gender=1.0, age=0.55, muscle=0.75, weight=0.7, height=0.65, proportions=0.5, race=dict(caucasian=0.3, asian=0.0, african=0.7)),
               skin='middleage_african_male', hair='short02', brows='eyebrow002', lashes='eyelashes01',
               clothes=['male_worksuit01', 'shoes01'], tint={'short02': (0.0, 0.2, 0.15, None)}),
})
KEYS = ['kid', 'dad', 'mom', 'repo']
def build(key): return humans.build(key)
