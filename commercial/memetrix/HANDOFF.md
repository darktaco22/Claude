# THE MEMETRIX (Meme Royale Matrix parody, about 2:18, 16:9)

Original script; only the genre tropes are borrowed (code rain, the red/green choice, "the real world", training program,
the kid with the bent card, the oracle, agents in shades, the rooftop bullet-time dodge). No film dialogue, music or likeness.
The user asked for characters that earlier films rarely used:

| Role | Character | | Role | Character |
|---|---|---|---|---|
| Anon, the chosen one | zcat (paper bag) | | Operator | mensa |
| Mentor, talks... slowly | slerf | | Traitor | farter |
| Fighter | michi | | Kid with the card | alon |
| Oracle (a book) | bome | | Agent lead | jeanphil (+ shades) |
| Agent clones | triplet x3 | | Mom | voice only, upstairs |

## Sections (film time)
0-5 s opening (2D in the finish: code rain, "Wake up, Anon...", title) · trading floor at night (Anon at his desk, Michi)
· the choice under the bull (Slerf, red/green candle) · swallow → code → Mom's basement (wake up, Mom gag, Mensa, Farter)
· Metaverse dojo (I know candlesticks, the fight) · basement waiting room (Alon's card, Bome's cookie)
· **rooftop** (agents, "Sell.", bullet-time dodge with a 300-degree orbit, second barrage stopped in the air, candles turn green)
· end card "THERE IS NO CHART." (4 s).

## Files
| File | Job |
|---|---|
| `voices.py` | 30 Kokoro lines → `pack/vo` (Slerf's pauses via ` / `) |
| `coderain.py` | Code rain frames (screens, opening, transitions) → `pack/rain` |
| `mxsets.py` | Trading floor, basement, dojo (game arena props, `pack/arenas`), rooftop (code only), hand props |
| `scene.py` | Cast, staging, every shot as `tools/cine.py` data, solved against the geometry → `scene.blend` + `edl.json` |
| `track.py` | Character positions over time (shared by build and renderer) |
| `render_edl.py` | Renders film frames; camera from `cine.place`, handheld from `shakify`, per-set lights and camera fill |
| `animatic.py` | 3 small frames per shot + labelled sheets. Run after every staging change |
| `finish.py` | Opening, grade per world, letterbox, captions, glitch transitions, end card, sound mix |
| `setup.sh`, `render_worker.sh A B`, `finish_all.sh` | Same system as DEPLOYED (frames_jpg/<edit hash>, 15-min slices, exit 3 = relaunch) |

## Lessons (also in tools/PLAYBOOK.md)
- Measure eye heights on a height-grid render, never guess (Slerf's eyes are at 1.30 m, not 1.5). Long-bodied
  characters (Mensa) need `cine.EYE_FWD`; cartoon heads need `cine.FRAME_SCALE` ≈ 1.35.
- Over-the-shoulder shots past bulky characters (Slerf, Bome, Alon's hair) fill the lens: use clean singles.
- `DRY=1` writes an unsolved edl.json; always do a full build before rendering.
- Inserts with `look_offset` can put the camera inside the subject (the solver looks through the subject): give inserts
  an explicit `distance`.

## State (2026-11-18, polish pass)
- v1 film (edit 2292f1afb0) sent. The user asked for bug fixes, better rigging and prop placement (Slerf's shades on his eyes).
- Polish edit **50dff5a2ee**: skin-glued props (`glue()`), fitted wraparound shades, IK blocks/push in the dojo fight, Alon's
  IK arm holding a card that curls in its insert, cleaned cameras and staging (see the commit log and PLAYBOOK lessons).
- Re-render: frames listed in `reuse_50dff5a2ee.txt` (10 untouched shots, 452 frames) are copied from
  `frames_jpg/2292f1afb0`; 2657 frames are rendered by 8 workers on `claude/memetrix-w1..w8`, ranges
  121-661, 662-1071, 1072-1437, 1438-1829, 1830-2204, 2205-2536, 2537-2896, 2897-3229 (`render_worker.sh` skips reused frames).
- Titles (finish.py, 2D, no re-render): 11 s opening (terminal, dive through three depths of code with zoom blur, chrome
  title slam with sweep, flare and shake, burn to embers) and a 14 s closing (nine cast cards with stills, logo scan-build,
  tagline, call to action). The film is shifted by PRE = 6 s in the finish; output 2:34.5.
- DONE 2026-11-18 19:xx: all 3109 frames of 50dff5a2ee collected (workers w1, w4-w10), finished to
  `commercial/output/meme-royale-memetrix.mp4` (2:34.5, 1080p).
- (old note) Then: collect, copy the reused frames in, `W=~/mx_work ./finish_all.sh`, review, send.
- Afterwards (pending the user's OK): delete the claude/memetrix-w* branches and archive the workers.
