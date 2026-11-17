"""WHO SOLD? - a Meme Royale true-crime documentary parody. Timeline assembler."""
import json, os, subprocess, sys, numpy as np, soundfile as sf
sys.path.insert(0, '/root/road/who'); import gfx, synth as S
R = '/root/road'; W = R + '/who'; G = W + '/g/'; SH = R + '/shots/'; HERO = R + '/hero/'; VO = W + '/vo/'; SEG = W + '/seg/'
for d in (G, SEG, VO): os.makedirs(d, exist_ok=True)
SR = 44100
LJ = json.load(open('/home/user/Claude/commercial/who-sold/voice/lines.json'))
LINES = {k: (r, t) for k, r, t in LJ['lines']}
def run(*a): subprocess.run([str(x) for x in a], check=True)
def probe(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode())
def vdur(key):
    p = VO + key + '.wav'
    if os.path.exists(p): return sf.info(p).duration
    return 0.36 * len(LINES[key][1].split()) + 0.7          # placeholder until the voices arrive
BEATS = []; AUD = []; T = [0.0]
def clip(path, ss=0.0, avail=None): return ('clip', path, ss, avail)
def still(png): return ('still', png)
BLACK = ('black',)
def beat(name, src, vo=(), tail=0.45, lead=0.25, dur=None, overlays=(), sfx=(), vf='', captions=True, gap=0.3, speed_cap=1.8):
    """vo: keys spoken in order (each starts after the previous + gap). overlays: (png, t0, t1, anim). sfx: (array|path, t, gain)."""
    t = lead; ov = list(overlays); spans = {}
    for key in vo:
        d = vdur(key); spans[key] = (t, t + d); AUD.append(('vo', key, T[0] + t))
        if captions: ov.append((gfx.caption(LINES[key][1], G + f'cap_{key}.png'), t, t + d + 0.15, 'none'))
        t += d + gap
    D = dur if dur else max(t - gap + tail, 1.0)
    for a, tt, g in sfx: AUD.append(('sfx', a, T[0] + (tt if tt >= 0 else D + tt), g))
    out = SEG + name + '.mp4'; inp = []; fc = []
    base = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30'
    if src[0] == 'clip':
        _, path, ss, avail = src; avail = avail or (probe(path) - ss - 0.05)
        need = D; f = min(max(need / avail, 1.0), speed_cap)
        inp += ['-ss', f'{ss:.3f}', '-t', f'{avail:.3f}', '-i', path]
        fc.append(f"[0:v]setpts={f:.4f}*PTS,{base},tpad=stop_mode=clone:stop_duration={D:.2f}{(',' + vf) if vf else ''}[b0]")
    elif src[0] == 'still':
        inp += ['-loop', '1', '-framerate', '30', '-t', f'{D:.3f}', '-i', src[1]]
        fc.append(f"[0:v]scale=w='trunc(1080*(1+0.045*t/{D:.2f})/2)*2':h=-2:eval=frame,crop=1080:1920,setsar=1,fps=30{(',' + vf) if vf else ''}[b0]")
    else:
        inp += ['-f', 'lavfi', '-t', f'{D:.3f}', '-i', 'color=c=black:s=1080x1920:r=30']; fc.append('[0:v]setsar=1[b0]')
    cur = 'b0'
    for i, (png, t0, t1, anim) in enumerate(ov):
        t1 = D + 1 if t1 is None else t1
        inp += ['-loop', '1', '-framerate', '30', '-t', f'{D:.3f}', '-i', png]; k = i + 1
        if anim == 'slide': ex = f"x='-1080*pow(1-min(max(t-{t0:.2f},0)/0.35,1),3)':y=0"
        elif anim == 'drop': ex = f"x=0:y='-260*pow(1-min(max(t-{t0:.2f},0)/0.3,1),3)'"
        elif anim == 'pop': ex = f"x=0:y='-40*pow(max(1-(t-{t0:.2f})/0.14,0),2)'"
        elif anim == 'shake': ex = f"x='6*sin(t*61)':y='5*sin(t*47)'"
        else: ex = 'x=0:y=0'
        if anim == 'fade': fc.append(f"[{k}:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.35:alpha=1[o{k}]"); srcl = f'o{k}'
        else: srcl = f'{k}:v'
        fc.append(f"[{cur}][{srcl}]overlay={ex}:enable='between(t,{t0:.2f},{t1:.2f})':format=auto[v{k}]"); cur = f'v{k}'
    fc.append(f'[{cur}]format=yuv420p[v]')
    run('ffmpeg', '-v', 'error', '-y', *inp, '-filter_complex', ';'.join(fc), '-map', '[v]', '-t', f'{D:.3f}', '-r', '30', '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', out)
    BEATS.append((name, out, T[0], D)); T[0] += D; return spans
def shot(key): return SH + key + ('_g' if os.path.exists(SH + key + '_g.mp4') else '') + '.mp4'
def frame_of(path, t, out):
    run('ffmpeg', '-v', 'error', '-y', '-ss', t, '-i', path, '-frames:v', '1', out); return out
DOC = 'eq=saturation=0.86:contrast=1.07,vignette=PI/5'
NIGHT = 'eq=brightness=-0.10:saturation=0.75:contrast=1.08,colorbalance=bs=0.22:bm=0.08:rs=-0.05,vignette=PI/4'
CCTV = 'fps=10,hue=s=0,eq=contrast=1.35:brightness=-0.04,noise=alls=26:allf=t,gblur=sigma=1.2,fps=30'
def interview(key, card, role, line, count, extra_vo=(), **kw):
    lt = gfx.lower_third(card, role, G + f'lt_{key}.png'); d = vdur(line)
    ov = [(lt, 0.5, 0.5 + min(4.2, d + 1.0), 'slide')]; sfx = [(S.whoosh(0.35), 0.45, 0.25)]
    if count:
        tb = 0.25 + d - 0.9; ov.append((gfx.phone_banner(count, G + f'ph_{count}.png'), tb, None, 'drop')); sfx.append((S.beep(2, 0.35), tb, 0.5))
    return beat('iv_' + key, clip(shot(key), 0.0), vo=(line,) + tuple(extra_vo), overlays=ov, sfx=sfx, vf=DOC, **kw)
def build():
    # ---- cold open
    c1 = gfx.card(['The following is a true story.'], G + 'c_true1.png'); c2 = gfx.card(['The following is a true story.', '', 'Some names have been changed.', 'Mostly to Pepe.'], G + 'c_true2.png')
    beat('open', BLACK, dur=3.9, overlays=[(c1, 0.25, 1.6, 'fade'), (c2, 1.6, 3.7, 'none')], sfx=[(S.typewriter(30), 0.25, 0.5), (S.typewriter(42), 1.6, 0.5)])
    sl = gfx.slam('NEVER SELL\nTHE GAME.', G + 'slam_never.png', size=230)
    d1 = vdur('n01'); beat('mine', clip(shot('mine'), 0.0), vo=('n01',), tail=1.3, vf=NIGHT, overlays=[(sl, 0.25 + d1 + 0.25, None, 'pop')], sfx=[(S.boom(2.5), 0.25 + d1 + 0.25, 0.8)], speed_cap=2.0)
    beat('order', still(gfx.order_ticket(G + 'order.png')), vo=('n02',), tail=0.9, sfx=[(S.shutter(), 0.05, 0.6), (S.riser(1.6), -1.6, 0.5)])
    beat('title', still(gfx.title(G + 'title.png')), dur=2.6, sfx=[(S.boom(3.0), 0.0, 1.0)])
    # ---- the suspects
    beat('lineup', clip(shot('lineup'), 0.0), vo=('n03',), tail=0.9, vf=DOC, overlays=[(gfx.tag('THE SUSPECTS', G + 'tag_sus.png'), 0.3, None, 'none')], sfx=[(S.sting_low(), 0.0, 0.5)])
    interview('giga', 'GIGACHAD', 'Witness. Did not skip arm day.', 'giga1', 12)
    beat('re_giga', clip(HERO + 'beach.mp4', 2.6), vo=('n04',), vf=DOC, overlays=[(gfx.tag('DRAMATIC REENACTMENT', G + 'tag_re.png'), 0.0, None, 'none')], speed_cap=1.15)
    interview('wojak', 'WOJAK', 'Prime suspect. The crying is unrelated.', 'wojak1', 23)
    beat('re_wojak', clip(HERO + 'cemetery.mp4', 2.8), vo=('n05',), vf=DOC, overlays=[(gfx.tag('EXHIBIT A: HIS FACE (2010 - PRESENT)', G + 'tag_exa.png'), 0.0, None, 'none')], speed_cap=1.15)
    interview('whale', 'THE WHALE', 'Asked not to be named. Is named The Whale.', 'whale1', 31)
    beat('news', still(gfx.newspaper(G + 'news.png')), vo=('n06',), tail=1.3, sfx=[(S.shutter(), 0.05, 0.6)])
    interview('pepe', 'PEPE', 'Local wizard. Has a theory.', 'pepe1', 38)
    ph = []
    for k, lab in [('giga', 'ALIBI??'), ('bonk', 'DUCKS'), ('troll', 'THE CART'), ('pepe', 'ME (INNOCENT)'), ('wojak', 'CRYING. WHY?'), ('whale', 'THE MOON')]:
        fp = G + f'still_{k}.png'
        if os.path.exists(shot(k)): frame_of(shot(k), 2.0, fp)
        ph.append((fp, lab))
    beat('board', still(gfx.evidence_board(ph, G + 'board.png')), vo=('n07',), lead=1.6, tail=1.0, sfx=[(S.shutter(), 0.05, 0.6)])
    lt = gfx.lower_third('BONK', 'Eyewitness.', G + 'lt_bonk.png'); db = vdur('bonk1')
    tr = gfx.caption('[ translated from Bonk ]   "Bonk."', G + 'cap_bonk_tr.png', y=1560)
    bh = R + '/aud/sfx/atk_bonk.mp3'
    beat('iv_bonk', clip(shot('bonk'), 0.0), vo=('bonk1', 'n08'), lead=1.3, gap=1.5, captions=False, vf=DOC,
         overlays=[(lt, 0.4, 3.6, 'slide'), (tr, 1.3, 1.3 + db + 1.3, 'none'), (gfx.caption(LINES['n08'][1], G + 'cap_n08.png'), 1.3 + db + 1.5, None, 'none')])
    # ---- the evidence
    beat('cctv', clip(HERO + 'casino.mp4', 0.4), vo=('n09', 'n10'), gap=0.35, tail=0.7, vf=CCTV, overlays=[(gfx.cctv_overlay(G + 'cctv.png'), 0.0, None, 'none')], speed_cap=1.15, sfx=[(S.shutter(), 0.05, 0.5)])
    interview('troll', 'TROLL', 'Confessed. Repeatedly.', 'troll1', 46, extra_vo=('n11',))
    beat('phone', still(gfx.phone_full(G + 'phone.png')), vo=('n12',), tail=1.1, overlays=[], sfx=[(S.beep(4, 0.45), 0.2, 0.7), (S.beep(3, 0.45), -1.5, 0.7)])
    # ---- the reveal
    d13 = vdur('n13'); beat('trace', clip(shot('basement2'), 0.0), vo=('n13',), tail=0.9, vf=NIGHT, speed_cap=3.0, sfx=[(S.riser(3.0), 0.25 + d13 - 3.0, 0.6), (S.boom(2.0), 0.25 + d13 + 0.1, 0.7)])
    AUD.append(('mark', 'reveal', T[0]))
    beat('pause', still(gfx.pause_menu(G + 'pause.png')), dur=2.4, sfx=[(S.tick(), 0.9, 0.9)])
    ltm = gfx.lower_third('THE NARRATOR', 'Narrator. Had a reservation.', G + 'lt_nar.png'); dm = vdur('n13b')
    thr = frame_of(shot('basement2'), str(probe(shot('basement2')) - 0.15), G + 'throne.png')
    beat('confess', still(thr), vo=('n13b',), lead=0.9, tail=0.9, vf=DOC, overlays=[(ltm, 0.9 + dm * 0.45, None, 'slide')])
    AUD.append(('mark', 'after', T[0]))
    beat('resv', still(gfx.reservation(G + 'resv.png')), dur=2.3, sfx=[(S.beep(1, 0.5), 0.3, 0.8)])
    beat('peas', clip(HERO + 'basement.mp4', 5.6), vo=('n14',), tail=0.9, vf=DOC, speed_cap=1.15)
    # ---- where are they now
    EP = [('wojak', 'WOJAK', ['was cleared of all charges.', 'He is still crying.', 'Doctors say it is unrelated.']),
          ('whale', 'THE WHALE', ['now owns this documentary.']),
          ('basement', 'THE NARRATOR', ['was banned from ranked for life.', 'Says the pasta was worth it.']),
          ('mine', 'DIAMOND HANDS MINE', ['reopened on Monday.', 'Dinner is now post-match.'])]
    for k, nm, ls in EP:
        bg = G + f'epbg_{k}.png'; src = shot(k) if os.path.exists(shot(k)) else HERO + 'basement.mp4'; frame_of(src, 1.5, bg)
        ep = gfx.epilogue(nm, ls, G + f'ep_{k}.png'); n = sum(len(x) for x in ls)
        beat('ep_' + k, still(bg), dur=2.5 + 0.035 * n, overlays=[(ep, 0.0, None, 'none')], sfx=[(S.typewriter(min(n, 60)), 0.25, 0.4)], vf='eq=saturation=0.5:brightness=-0.08')
    beat('end', still(gfx.endcard(G + 'end.png')), vo=('n15',), lead=0.8, tail=2.6, captions=False, sfx=[(S.boom(3.0), 0.0, 0.8)])
def mix(total):
    n = int(total * SR) + SR; vo = np.zeros(n); fx = np.zeros(n); marks = {}
    def put(buf, a, t, g=1.0):
        s = int(t * SR)
        if s >= n: return
        a = a[:n - s]; buf[s:s + len(a)] += a * g
    for ev in AUD:
        if ev[0] == 'mark': marks[ev[1]] = ev[2]
        elif ev[0] == 'vo':
            p = VO + ev[1] + '.wav'
            if not os.path.exists(p): continue
            a, sr = sf.read(p, dtype='float32')
            if a.ndim > 1: a = a.mean(1)
            if sr != SR:
                run('ffmpeg', '-v', 'error', '-y', '-i', p, '-ar', SR, '-ac', 1, W + '/tmp.wav'); a, _ = sf.read(W + '/tmp.wav', dtype='float32')
            act = a[np.abs(a) > 0.02]; a = a * (0.2 / (np.sqrt((act ** 2).mean()) + 1e-6)); put(vo, np.tanh(a * 1.05) / 1.05, ev[2])
        else:
            a = ev[1]
            if isinstance(a, str):
                run('ffmpeg', '-v', 'error', '-y', '-i', a, '-ar', SR, '-ac', 1, W + '/tmp.wav'); a, _ = sf.read(W + '/tmp.wav', dtype='float32')
            a = np.asarray(a, dtype='float64'); a = a / (np.abs(a).max() + 1e-9); put(fx, a, ev[2], ev[3] * 0.55)
    rv = marks.get('reveal', total * 0.75); af = marks.get('after', rv + 6); tt = np.arange(n) / SR
    title_t = next(t0 for nm, _, t0, _ in BEATS if nm == 'title')
    bed = np.zeros(n); dr = S.drone(n / SR); bed[:len(dr)] += dr[:n] * 1.0
    def addto(buf, start, arr, g):
        m = min(len(arr), len(buf) - start)
        if m > 0: buf[start:start + m] += arr[:m] * g
    a1 = int((title_t + 3.0) * SR); b1 = int(rv * SR)
    pn = S.piano_line((b1 - a1) / SR, S.MINOR); addto(bed, a1, pn, 0.55)
    hb = S.heartbeat((b1 - a1) / SR, 46); g = np.linspace(0.15, 0.6, len(hb)); addto(bed, a1, hb * g, 0.5)
    # the reveal: music drops out completely for the confession, then resolves in major
    gate = np.ones(n); s0 = int((rv - 0.15) * SR); s1 = int(af * SR); gate[s0:s1] = 0.0
    k = int(0.25 * SR); gate = np.convolve(gate, np.ones(k) / k, 'same'); bed *= gate
    a2 = int((af + 0.2) * SR); mj = S.piano_line((n - a2) / SR, S.MAJOR, step=1.9, start=0.2); addto(bed, a2, mj, 0.6)
    env = np.abs(vo); kk = int(0.18 * SR); env = np.convolve(env, np.ones(kk) / kk, 'same'); duck = 1 - 0.6 * np.clip(env * 9, 0, 1)
    bed = bed / (np.abs(bed).max() + 1e-9) * 0.22 * duck
    out = vo + fx + bed; fo = int(1.2 * SR); out[-fo:] *= np.linspace(1, 0, fo)
    out = np.tanh(out * 1.1) / 1.1
    sf.write(W + '/master.wav', np.stack([out, out], 1).astype('float32'), SR); return W + '/master.wav'
if __name__ == '__main__':
    build(); total = T[0]
    lst = W + '/concat.txt'; open(lst, 'w').write(''.join(f"file '{p}'\n" for _, p, _, _ in BEATS))
    run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', W + '/picture.mp4')
    wav = mix(total)
    json.dump([(n, round(t0, 2), round(d, 2)) for n, _, t0, d in BEATS], open(W + '/beats.json', 'w'), indent=0)
    lut = R + '/fx/cine_srgb.cube'
    fc = (f"[0:v]eq=contrast=1.03,format=gbrp,split=2[o1][o2];[o2]lut3d=file={lut}[lg];[o1][lg]blend=all_expr=A*0.55+B*0.45,"
          f"noise=alls=7:allf=t,format=yuv420p,fade=t=in:d=0.5,fade=t=out:st={total - 1.0:.2f}:d=1.0[v];[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    out = W + '/who_sold.mp4'
    run('ffmpeg', '-v', 'error', '-y', '-i', W + '/picture.mp4', '-i', wav, '-filter_complex', fc, '-map', '[v]', '-map', '[a]', '-t', f'{total:.2f}', '-r', '30',
        '-c:v', 'libx264', '-crf', '21', '-maxrate', '5M', '-bufsize', '10M', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out)
    print(out, round(total, 1), 's', os.path.getsize(out) // 1000000, 'MB'); print(json.dumps([(n, round(t0, 1)) for n, _, t0, _ in BEATS]))
