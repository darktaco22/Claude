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

## State (2026-11-19, polish pass 3 in progress — read this first after a compaction)
**Sent to the user:** v1 (edit 2292f1afb0) and v2 (edit 50dff5a2ee, 2:34, new titles) = `commercial/output/meme-royale-memetrix.mp4`.
**User feedback since v2, worked on in scene.py (NOT rendered as a film yet):** the user said "don't render until told; keep finding
and fixing bugs; before each new hunt show before/after images of what you fixed and wait for confirmation".

### Liked by the user (keep)
Candle freeze wall on the rooftop, Mom's door seen up the staircase, Slerf holding out both candles.

### Done in code (latest build: `W/scene_v21.blend`, edl backed up as `W/edl_v21.json`; W = /root/mx_work)
- Props on characters: `posed()`/`paw_top()`/`paw_fwd()`/`place()`/`bone_verts()` in scene.py measure a paw on the clip pose the
  character holds (`'clip@0.3'` = held pose, supported in Actor.finish) and `glue()` the prop to vertices of that arm only.
  IK arms were dropped: they twisted Slerf's gauntlets and Anon's paws (only Alon's card IK and Slerf's fight IK remain).
- Candles: Slerf holds pose `attack1@0.3`; red on his LEFT paw (out to the side), green on the right; candles size 1.5 standing ON
  the paw (STAND); each held candle has a coloured point light (GLOW dict). Anon steps to TAKE_AT so his `attack2@0.4` punch paw
  meets the red candle (both centred at 0.96 m).
- Swallow: close-up placed on the bag's mouth hole found by a ray on the posed mesh (EAT_MOUTH, 49 cm in front of the rig);
  `candle_eat` rises, tips, slides in; camera = `cam_at`/`cam_at1` (new fixed-camera keys in tools/cine.py). finish.py glitch
  starts at u 0.56. UNCONFIRMED: user still found it bad at v19; v21 check frames pending.
- Diamond hands: held `win@0.25`, a diamond glued above each raised paw, shown from A08 to the end.
- Bullet time: Anon holds `ready`, small lean (16 deg) + spine bend action (NLA COMBINE, BEND_SIGN measured); bullets from
  Jeanphil's posed hand, staggered 0.035 s, spread x 0.2 m, heights = bent body top + 0.22..0.46 m; glow=3.0; muzzle flash
  sphere + point light; orbit bearing 100, amount 130 (side-on, never crossing the barrage).
- Fight fall: Anon lowered LIE_DROP 0.27 m and his tail swung flat by a hook modifier (`tail_hook`, empty parented to the
  armature, matrix_inverse from world matrices) until LIE_END. Body rests on the mat (top 0.06).
- Farter: holds a phone (screen texture `pack/props/phone_chart.png`, "$FART +6,942%"), new `phone_insert` shot before f01.
- Bome: bobs, then at OFFER turns his right glove (with the cookie, now 1.6x) to Anon and sinks; new `cookie_take` shot.
- Staircase: treads with nosing, risers, red runner, closed side panel, balusters, handrail, newel, landing rail, family photos,
  light switch, laundry basket, shoes, landing + lit half-open door.
- Basement: CRT turned to face Mensa with the rain screen on its glass; chair moved behind Slerf.
- Agents' shades: `fitted_shades` on measured eyes (AGENT_EYES: jean 1.465 m; planks 1.405 m, flat wrap) — verified on renders.
- Slerf's "leverage": `voices.py` supports `PH:` phoneme pieces; s08 regenerated with lˈɛvəɹɪdʒ (user to confirm by ear).
- tools/cine.py: `with=[partner]`, `cam_at`/`cam_at1`, solver rejects cameras inside characters.
- Film is now 137.8 s of 3D (3307 frames) + titles (PRE 6 s, closing 14 s) because of the two new shots.

### Next steps
1. Review `W/chk21` (check frames of v21; list in `W/check21.txt`), make before/after sheets with `/root/mx_probe/ba.py`
   (compares to frames_jpg/50dff5a2ee — NOTE shot times moved by +~3 s after s/phone_insert: compare by shot, not frame number),
   send them, wait for the user.
2. Open items: swallow look; Bome cookie readability; take_red bag overlapping Slerf's arm; phone insert framing.
3. Only when the user says so: commit edl.json, workers render (render_worker.sh A B, reuse list for unchanged shots),
   finish_all.sh, review at 3 frames/s plus the pop detector (see PLAYBOOK), send.
- Tools in /root/mx_probe (not in git): face.py (ortho face grid), grid.py, clips.py (pose sheets), sheet.py, ba.py,
  lying.py, check13.py. Copies of the important ones are in `commercial/memetrix/probe/`.
- Cleanup pending the user's OK: worker sessions (tag memetrix-render) and branches claude/memetrix-w1..w10.
