"""Hands vs held props over the film: blender -b scene.blend -P propcheck.py"""
import bpy, sys
sys.path.insert(0, '/home/user/Claude/commercial/degens'); sys.argv += ['--', '--frames', '1']
import director as D
PROPS = {'chad': ['chad_can', 'chad_phone'], 'earl': ['earl_cig', 'earl_phone'], 'pam': ['pam_mug', 'pam_phone'], 'linda': ['linda_mug', 'linda_phone']}
sc = bpy.context.scene; worst = {}
for t in [x * 2.0 + 1.0 for x in range(24)] + [8.3, 13.4, 16.0, 16.4, 20.3, 22.5, 25.6, 29.9, 33.0, 42.9]:
    sc.frame_set(int(D.fr(t))); dg = bpy.context.evaluated_depsgraph_get()
    for k, pl in PROPS.items():
        body = bpy.data.objects[k + '.body']
        for pn in pl:
            p = bpy.data.objects[pn]
            if p.hide_render or body.hide_render: continue
            bad = [d for _, d in D.penetration([body], p, dg) if d > 0.002]
            if bad:
                print(f'PROP t={t:5.1f} {k:6s} {pn:12s} n={len(bad):4d} deepest={max(bad)*100:.2f}cm')
                worst[pn] = max(worst.get(pn, 0), max(bad))
print('PROP worst', {k: round(v * 100, 2) for k, v in worst.items()})
