"""The HUD's state for every frame (hand, next card, COPIUM, clock), from the scene's timeline in overlay.json.
python3 build_hud.py overlay.json hud.json   -> hud_capture.js renders the game's real HUD from it."""
import json, sys
O = json.load(open(sys.argv[1])); MK = O['marks']
COST = {'lmao': 4, 'chillguy': 3, 'troll': 2, 'ket': 3, 'useless': 2, 'lasereyes': 5, 'fud': 2}
REGEN = 1 / 84.0          # COPIUM per frame (one every 2.8 s, the game's rate)
F = {}
def seg(f0, f1, cop0, t0, plays, hand, nxt, queue):
    """plays: [(frame, slot)] in order; each refills the slot with `nxt`, the next becomes queue.pop(0)"""
    hand = hand[:]; cop = cop0; P = dict(plays); q = queue[:]
    for f in range(f0, f1 + 1):
        gone = None
        if f in P:
            s = P[f]; cop -= COST[hand[s]]; hand[s] = nxt; nxt = q.pop(0) if q else 'fud'; gone = s
        cop = min(10.0, cop + REGEN)
        t = max(0.0, t0 - (f - f0) / 30)
        F[f] = {'hand': hand[:], 'next': nxt, 'cop': round(cop, 3), 't': round(t, 2), 'costs': [COST[c] for c in hand],
                'gone': None}
        # the played slot is empty for a few frames, then the new card slides in (as in the game)
        if f in P: F[f]['gone'] = s
        elif f - 1 in P or f - 2 in P or f - 3 in P: F[f]['gone'] = [P[k] for k in (f - 1, f - 2, f - 3) if k in P][0]
seg(1, MK['noob'][1], 5.3, 104.0, [(MK['drop_lmao'] - 6, 0)], ['lmao', 'chillguy', 'troll', 'ket'], 'useless', ['fud'])
seg(MK['pro'][0], 720, 7.6, 104.0, [(MK['drop_idol'] - 6, 0), (MK['drop_useless'] - 6, 1)],
    ['lasereyes', 'useless', 'chillguy', 'troll'], 'ket', ['fud', 'lmao'])
json.dump({'opp': {'name': 'whale_maxi', 'clout': 1840}, 'frames': F}, open(sys.argv[2], 'w'))
print('HUD frames', len(F))
