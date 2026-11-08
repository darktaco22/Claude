# Builds the soundtrack from the render's event log: the game's lofi battle music under everything, the scripted voice lines
# and pings, and the sim's own events (spells, towers falling, troops dropping) mapped to the game's sound files.
# usage: python3 mix.py events.json total_seconds out.m4a
import json, subprocess, sys, os
ev = json.load(open(sys.argv[1])); total = float(sys.argv[2]); out = sys.argv[3]
D = os.path.dirname(os.path.abspath(__file__)) + '/sfx/'
SPELL = {'panicsell': 'spell_panicsell', 'rug': 'spell_rug', 'godcandle': 'spell_godcandle', 'airdrop': 'spell_airdrop'}
cues = []   # (t, file, vol)
last = {}
def add(t, f, v=0.8, gap=0.0):
    if not os.path.exists(D + f + '.mp3'): return
    if gap and t - last.get(f, -9) < gap: return
    last[f] = t; cues.append((t, f, v))
for e in ev:
    t, k = e['t'], e['k']
    if k == 'sfx': add(t, {'win': 'victory'}.get(e['s'], e['s']), e.get('vol') or 0.8)
    elif k == 'spell' and e.get('card') in SPELL: add(t, SPELL[e['card']], 0.9)
    elif k == 'tower_down': add(t, 'tower_destroy', 1.0); add(t + 0.1, 'crowd_ooh', 0.6)
    elif k == 'die': add(t, 'unit_die_1', 0.45, gap=0.25)
    elif k == 'knock': add(t, 'punch_heavy_1', 0.5, gap=0.2)
    elif k == 'feared': add(t, 'feared', 0.5, gap=0.6)
for t0, f0, v0 in [(4.85, 'ui_swoosh', 0.7), (8.55, 'ui_swoosh', 0.9), (15.55, 'ui_swoosh', 0.9), (31.95, 'ui_swoosh', 0.9), (39.0, 'ui_swoosh', 0.9), (39.3, 'emote_pop', 0.8)]: add(t0, f0, v0)
ins = ['-i', D + 'mus_battle_lofi.mp3']
flt = [f'[0:a]atrim=0:{total},volume=0.42,afade=t=in:d=0.6,afade=t=out:st={total - 1.6}:d=1.6[m]']
for i, (t, f, v) in enumerate(cues, 1):
    ins += ['-i', D + f + '.mp3']
    flt.append(f'[{i}:a]volume={v},adelay={int(t * 1000)}|{int(t * 1000)}[c{i}]')
mixin = '[m]' + ''.join(f'[c{i}]' for i in range(1, len(cues) + 1))
flt.append(f'{mixin}amix=inputs={len(cues) + 1}:normalize=0:dropout_transition=0,alimiter=limit=0.95,atrim=0:{total}[a]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ac', '2', '-ar', '44100', '-c:a', 'aac', '-b:a', '192k', out], check=True)
print(len(cues), 'cues ->', out)
