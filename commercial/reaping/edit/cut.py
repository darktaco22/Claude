"""THE REAPING - final cut. Blender parts (commercial/reaping/renders), game captures, voices, sfx, score; master + grade."""
import glob, json, os, re, sys, numpy as np, soundfile as sf
sys.path.insert(0, '/root/road/reap'); import edit as E, rgfx, rsynth as R
from edit import seg, AUD, SEGS, T, MARK, mark, run, probe, vdur, loadwav, G, W, SR
REPO = '/home/user/Claude/commercial/reaping'; E.VO = REPO + '/voice/out/'; VO = E.VO; SFX = W + '/sfx/'
UP = 'scale=1080:1920:flags=lanczos,unsharp=5:5:0.35'
PARTS = []
for p in glob.glob(REPO + '/renders/*.mp4'):
    m = re.match(r'(\w+)_(\d{4})_(\d{4})\.mp4', os.path.basename(p)); PARTS.append((m.group(1), int(m.group(2)), int(m.group(3)), p))
def bl(scene, f0, f1):
    """a Blender frame range -> (src, dur)"""
    for s, a, b, p in PARTS:
        if s == scene and a <= f0 and f1 <= b: return ('clip', p, (f0 - a) / 30.0), (f1 - f0 + 1) / 30.0
    raise SystemExit(f'missing render {scene} {f0}-{f1}')
def game(name, t0, dur):
    p = REPO + f'/shots/{name}.mp4'
    if not os.path.exists(p): p = f'/root/road/rshots/{name}.mp4'
    return ('clip', p, t0), dur
def sfx(name): return SFX + name + '.mp3'
def B(name, scene, f0, f1, **kw):
    src, d = bl(scene, f0, f1); kw['vf'] = (kw.get('vf', '') + ',' if kw.get('vf') else '') + 'eq=contrast=1.02'
    seg(name, src, d, **kw)
GG = 'eq=contrast=1.06:saturation=1.05'
CUE = json.load(open(W + '/cues.json')) if os.path.exists(W + '/cues.json') else {}
def build():
    ctx = rgfx.context_tag(G + 'ctx.png')
    # ---------- the reaping
    mark('reap0')
    B('hook', 'lot', 1, 74, ovs=[(ctx, 0.0, 2.45, 'fade')], sfx=[(R.whoosh(0.5), 0.35, 0.25), (sfx('card_reveal'), 1.55, 0.5)])
    B('read', 'lot', 108, 138, vo=[('host1', 0.05)])
    B('cry', 'lot', 175, 222, sfx=[(sfx('crowd_gasp'), 0.0, 0.55)])
    B('vol', 'lot', 301, 350, vo=[('host2', 0.12)])
    mark('crickets'); B('hop', 'lot', 380, 470, sfx=[(R.crickets(1.2), 0.0, 0.5), (R.hop(), 0.98, 0.55), (sfx('ui_swoosh'), 1.0, 0.3)])
    mark('pepe'); B('pepe', 'lot', 511, 628, vo=[('pepe1', 0.33), ('pepe2', 2.72)], sfx=[(R.riser(2.0), 0.5, 0.35)])
    B('react', 'lot', 641, 690, sfx=[(sfx('crowd_ooh'), 0.05, 0.6), (R.boom(2.0), 0.0, 0.5)])
    mark('title'); seg('title', ('still', rgfx.title(G + 'title.png')), 2.2, sfx=[(R.braam(3.0), 0.0, 1.0)])
    # ---------- trailer cards over fast cuts
    B('nine', 'lot', 420, 456, ovs=[(rgfx.word('NINE MEMES.', G + 'w_nine.png'), 0.0, None, 'pop')], sfx=[(R.boom(1.2), 0.0, 0.5)])
    src, d = game('intro', 0.6, 1.2); seg('arena', src, d, vf=GG, ovs=[(rgfx.word('ONE ARENA.', G + 'w_arena.png'), 0.0, None, 'pop')], sfx=[(R.boom(1.2), 0.0, 0.5)])
    src, d = game('victory', CUE.get('hud', 2.4), 1.0); seg('copium', src, d, vf=GG, ovs=[(rgfx.word('TEN COPIUM.', G + 'w_copium.png', y=760), 0.0, None, 'pop')], sfx=[(R.boom(1.2), 0.0, 0.5)])
    mark('mentor'); B('mentor', 'mentor', 1, 76, vo=[('giga1', 0.35)])
    # ---------- the talk show
    mark('show'); B('studio', 'studio', 1, 60, ovs=[(rgfx.chyron(G + 'chy.png'), 0.5, None, 'slide')], sfx=[(R.jingle(), 0.0, 0.7), (sfx('crowd_cheer'), 0.1, 0.45)])
    B('pop1', 'studio', 81, 150, vo=[('pop1', 0.2)])
    B('bad', 'studio', 161, 205, vo=[('wojak1', 0.3)])
    B('aww', *(('studio', 231, 285) if os.path.exists(REPO + '/renders/studio_0231_0290.mp4') else ('studio', 10, 64)), sfx=[(VO + k + '.wav', 0.05 + 0.04 * i, 0.32) for i, k in enumerate(['aww_whale', 'aww_mom', 'aww_narrator', 'aww_giga', 'aww_pepe', 'aww_bonk'])])
    B('incredible', 'studio', 301, 340, vo=[('pop2', 0.15)])
    # ---------- the Games
    mark('games'); f = CUE.get('fight', 4.0)
    src, d = game('victory', f - 1.7, 2.5); seg('fight', src, d, vf=GG, sfx=[(sfx('battle_start'), 1.8, 0.7), (sfx('vo_fight'), 1.85, 0.8)])
    for nm, shot, t0, fallen, label in (('clashA', 'clashA', CUE.get('clashA', 2.0), CUE.get('fallenA', 'troll'), 'TROLL'), ('clashB', 'clashB', CUE.get('clashB', 2.0), CUE.get('fallenB', 'popcat'), 'POPCAT')):
        src, d = game(shot, t0, 2.4); seg(nm, src, d, vf=GG, sfx=[(sfx('punch_heavy_2') if os.path.exists(sfx('punch_heavy_2')) else R.boom(0.6), 0.6, 0.4)])
        seg('sky_' + nm, ('still', rgfx.sky(G + f'still_{fallen}.png' if os.path.exists(G + f'still_{fallen}.png') else f'/root/road/who/g/still_{fallen}.png', label, G + f'sky_{fallen}.png')), 1.1, sfx=[(R.cannon(3.0), 0.0, 1.0)])
    src, d = game('standoff2', 0.3, 4.4); seg('standoff', src, d, vf=GG, sfx=[(R.heartbeat(4.4, 70), 0.0, 0.5)])
    seg('sky_giga', ('still', rgfx.sky('/root/road/who/g/still_giga.png', 'GIGACHAD', G + 'sky_giga.png')), 1.1, sfx=[(R.cannon(3.0), 0.0, 1.0)])
    mark('victory'); src, d = game('victory', CUE.get('vic', 9.0), 2.7); seg('victory', src, d, vf=GG, vo=[('host3', 0.25)], sfx=[(sfx('victory'), 0.0, 0.6), (sfx('crowd_cheer'), 0.2, 0.5)])
    src, d = game('standoff2', 5.0, 1.9); seg('home', src, d, vf=GG, vo=[('wojak2', 0.3)])
    mark('tag'); seg('tag', ('still', rgfx.tagline(G + 'tag.png')), 2.3, sfx=[(R.braam(3.0), 0.0, 0.9)])
    seg('end', ('still', rgfx.endcard(G + 'end.png')), 2.6)
    mark('loop'); B('loop', 'lot', 1, 44, vo=[('host4', 0.0)])
def mix(total):
    n = int(total * SR) + SR; vo = np.zeros(n); fx = np.zeros(n); mus = np.zeros(n)
    def put(buf, a, t, g=1.0):
        s = int(t * SR); a = np.asarray(a, dtype='float64')[:max(0, n - s)]; buf[s:s + len(a)] += a * g
    for ev in AUD:
        if ev[0] == 'vo':
            a = loadwav(VO + ev[1] + '.wav'); act = a[np.abs(a) > 0.02]; a = a * (0.22 / (np.sqrt((act ** 2).mean()) + 1e-6)); put(vo, np.tanh(a * 1.05) / 1.05, ev[2])
        else:
            a = ev[1]; a = loadwav(a) if isinstance(a, str) else np.asarray(a, dtype='float64'); a = a / (np.abs(a).max() + 1e-9); put(fx, a, ev[2], ev[3] * 0.55)
    M = MARK
    # score: low drone + heartbeat under the reaping, silence for the crickets, pad swell for Pepe, trailer pulse from title to the end card
    dr = R.S.drone(M['crickets'] - M['reap0'] + 0.3); put(mus, dr * 0.5, M['reap0'])
    put(mus, R.S.heartbeat(M['crickets'] - M['reap0'], 62) * 0.35, M['reap0'])
    put(mus, R.pad(M['title'] - M['pepe'] - 0.2) * 0.7, M['pepe'] + 0.3)
    put(mus, R.pulse(M['mentor'] - M['title'], 124) * 0.9, M['title'])
    put(mus, R.pulse(M['victory'] - M['games'], 132, notes=(0, 0, 3, 0, 7, 0, 5, 3)) * 0.95, M['games'])
    put(mus, R.pad(M['loop'] - M['victory'], chord=(0, 4, 7), root=146.83) * 0.6, M['victory'])
    env = np.convolve(np.abs(vo), np.ones(int(0.15 * SR)) / int(0.15 * SR), 'same'); duck = 1 - 0.55 * np.clip(env * 9, 0, 1)
    mus = mus / (np.abs(mus).max() + 1e-9) * 0.3 * duck
    out = vo + fx + mus; out = np.tanh(out * 1.1) / 1.1
    sf.write(W + '/master.wav', np.stack([out, out], 1).astype('float32'), SR); return W + '/master.wav'
if __name__ == '__main__':
    for f in glob.glob(E.SEG + '*.mp4'): os.remove(f)
    build(); total = T[0]
    lst = W + '/concat.txt'; open(lst, 'w').write(''.join(f"file '{p}'\n" for _, p, _, _ in SEGS))
    run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', W + '/picture.mp4')
    wav = mix(total)
    json.dump([(nm, round(t0, 2), round(d, 2)) for nm, _, t0, d in SEGS], open(W + '/beats.json', 'w'), indent=0)
    fc = (f"[0:v]noise=alls=5:allf=t,vignette=PI/6,format=yuv420p,fade=t=in:d=0.25[v];[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.85:level=disabled[a]")
    out = W + '/the_reaping.mp4'
    run('ffmpeg', '-v', 'error', '-y', '-i', W + '/picture.mp4', '-i', wav, '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-t', f'{total:.2f}', '-r', '30',
        '-c:v', 'libx264', '-crf', '19', '-maxrate', '8M', '-bufsize', '16M', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out)
    print(out, round(total, 1), 's'); print(json.dumps([(nm, round(t0, 1)) for nm, _, t0, _ in SEGS]))
