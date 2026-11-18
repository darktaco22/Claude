"""THE REAPING - timeline assembler. Segments -> seg/*.mp4 -> concat; master audio built in numpy; final grade."""
import json, os, subprocess, sys, numpy as np, soundfile as sf
sys.path.insert(0, '/root/road/reap'); import rgfx, rsynth as R
W = '/root/road/reap'; G = W + '/g/'; SEG = W + '/seg/'; SH = '/root/road/rshots/'; OLD = '/root/road/shots/'; VO = W + '/vo/'; SFX = W + '/sfx/'
SR = 44100
LJ = json.load(open('/home/user/Claude/commercial/reaping/voice/lines.json')); LINE = {k: t for k, r, t in LJ['lines']}
def run(*a): subprocess.run([str(x) for x in a], check=True)
def probe(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode())
def vdur(k):
    p = VO + k + '.wav'
    return sf.info(p).duration if os.path.exists(p) else 0.33 * len(LINE[k].split()) + 0.5
SEGS = []; AUD = []; T = [0.0]; MARK = {}
GRADE = 'eq=saturation=1.04:contrast=1.04'
def seg(name, src, dur, ovs=(), vf='', vo=(), sfx=(), caps=True, speed=1.0):
    """src: ('clip', path, ss) | ('still', png) | ('black',). vo: [(key, t)]. sfx: [(arr|path, t, gain)]. overlays: (png, t0, t1, anim)."""
    ov = list(ovs)
    for k, t in vo:
        AUD.append(('vo', k, T[0] + t))
        if caps: ov.append((rgfx.caption(LINE[k], G + f'cap_{k}.png', y=1560), t, t + vdur(k) + 0.2, 'none'))
    for a, t, g in sfx: AUD.append(('sfx', a, T[0] + t, g))
    out = SEG + f'{len(SEGS):02d}_{name}.mp4'; inp = []; fc = []
    base = 'scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,fps=30,unsharp=5:5:0.3'
    if src[0] == 'clip':
        _, path, ss = src; avail = probe(path) - ss - 0.04
        inp += ['-ss', f'{ss:.3f}', '-t', f'{avail:.3f}', '-i', path]
        fc.append(f"[0:v]setpts={1/speed:.4f}*PTS,{base},tpad=stop_mode=clone:stop_duration={dur + 1:.2f}{(',' + vf) if vf else ''}[b0]")
    elif src[0] == 'still':
        inp += ['-loop', '1', '-framerate', '30', '-t', f'{dur:.3f}', '-i', src[1]]
        fc.append(f"[0:v]scale=w='trunc(1080*(1+0.04*t/{dur:.2f})/2)*2':h=-2:eval=frame,crop=1080:1920,setsar=1,fps=30{(',' + vf) if vf else ''}[b0]")
    else:
        inp += ['-f', 'lavfi', '-t', f'{dur:.3f}', '-i', 'color=c=black:s=1080x1920:r=30']; fc.append('[0:v]setsar=1[b0]')
    cur = 'b0'
    for i, (png, t0, t1, anim) in enumerate(ov):
        t1 = dur + 1 if t1 is None else t1; k = i + 1
        inp += ['-loop', '1', '-framerate', '30', '-t', f'{dur:.3f}', '-i', png]
        if anim == 'slide': ex = f"x='-1080*pow(1-min(max(t-{t0:.2f},0)/0.3,1),3)':y=0"
        elif anim == 'drop': ex = f"x=0:y='-200*pow(1-min(max(t-{t0:.2f},0)/0.25,1),3)'"
        elif anim == 'pop': ex = f"x=0:y='-40*pow(max(1-(t-{t0:.2f})/0.14,0),2)'"
        else: ex = 'x=0:y=0'
        if anim in ('fade', 'fadeio'):
            f = f"[{k}:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.3:alpha=1" + (f",fade=t=out:st={t1 - 0.3:.2f}:d=0.3:alpha=1" if anim == 'fadeio' else '') + f"[o{k}]"; fc.append(f); srcl = f'o{k}'
        else: srcl = f'{k}:v'
        fc.append(f"[{cur}][{srcl}]overlay={ex}:enable='between(t,{t0:.2f},{t1:.2f})':format=auto[v{k}]"); cur = f'v{k}'
    fc.append(f'[{cur}]format=yuv420p[v]')
    nf = int(round(dur * 30))
    run('ffmpeg', '-v', 'error', '-y', *inp, '-filter_complex', ';'.join(fc), '-map', '[v]', '-frames:v', nf, '-r', '30', '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', out)
    SEGS.append((name, out, T[0], nf / 30)); T[0] += nf / 30
def mark(k): MARK[k] = T[0]
def loadwav(p):
    if p.endswith('.mp3') or not p.endswith('.wav'):
        run('ffmpeg', '-v', 'error', '-y', '-i', p, '-ar', SR, '-ac', 1, W + '/tmp.wav'); p = W + '/tmp.wav'
    a, sr = sf.read(p, dtype='float32')
    if a.ndim > 1: a = a.mean(1)
    if sr != SR: run('ffmpeg', '-v', 'error', '-y', '-i', p, '-ar', SR, '-ac', 1, W + '/tmp2.wav'); a, _ = sf.read(W + '/tmp2.wav', dtype='float32')
    return a.astype('float64')
