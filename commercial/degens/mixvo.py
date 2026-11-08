# DEGENS ANONYMOUS soundtrack: voice lines, procedural foley and ambience, from the render's cue list.
import json, subprocess, sys, os
cues = json.load(open(sys.argv[1])); body = float(sys.argv[2]); total = float(sys.argv[3]); out = sys.argv[4]
H = os.path.dirname(os.path.abspath(__file__)); SFX = os.environ.get('SFX_DIR', H + '/sfx/') + '/'; VO = os.environ.get('VO_DIR', H + '/../da/vo/') + '/'
ins, flt, n = [], [], 0
def add(path, t, vol, extra=''):
    global n; ms = int(t * 1000); ins.extend(['-i', path]); flt.append(f"[{n}:a]aresample=44100,aformat=channel_layouts=mono,{extra}volume={vol},adelay={ms}|{ms}[c{n}]"); n += 1
for c in cues:
    if 'vo' in c: add(VO + c['vo'] + '.wav', c['t'], 1.0, 'highpass=f=90,aecho=0.8:0.3:35:0.18,')   # a hard basement room
    elif c['s'] == 'room': add(SFX + 'room.wav', c['t'], c['vol'], f"atrim=0:{45.5 - c['t']},")      # the hum dies with the last light
    elif c['vol'] > 0: add(SFX + c['s'] + '.wav', c['t'], c['vol'] * {'rain': 0.35, 'thunder': 0.45}.get(c['s'], 1))
mix = ''.join(f'[c{i}]' for i in range(n))
flt.append(f"{mix}amix=inputs={n}:normalize=0:dropout_transition=0,loudnorm=I=-15:TP=-1.5:LRA=11,apad,atrim=0:{total}[a]")
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', '44100', '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(n, 'cues ->', out)
