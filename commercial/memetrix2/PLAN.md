# THE MEMETRIX II: build plan and state

Script: `SCRIPT.md` (approved: "Go ahead"). Same pipeline as episode 1 (`../memetrix/`): voices -> sets -> scene.py (staging and
shots as cine data, solved) -> check frames + before/after sheets for the user -> workers render -> finish.py (titles, grade,
mix) -> review at 3 fps + pop detector -> send.

## Done
- **Voices:** `voices.py` -> `pack/vo` (34 lines, 87.9 s). New voices: whale bm_lewis 0.8, swordcat af_kore, This-Is-Fine
  am_puck, Toshi af_sky; `jean12` = one take layered 12x with 8-90 ms delays (the copied agent). Slerf's fast line at 2.3x.
- **New characters measured** (idle pose, front + side height grids; `/root/mx_probe/measure.py`): all ~1.68 m tall.
  Eye heights: whale 1.37 (eyes on the sides of the head), swordcat 1.30 (armoured kitten knight with a sword),
  thisisfine 1.28 (cartoon dog, bowler hat), toshi 1.21 (blue ninja cat with two katanas: the Keyholder).
- **Sets** (`sets2.py`, look test `look_sets_v1.jpg`): the burning café FINE at (600,0,0) (diner tiles, red booths, chrome
  stools, counter, chalk menu "EXIT ... ?", code rain outside the window, 12 animated flame clusters with flickering
  lights, warm haze and embers); the white room at (800,0,0) (white cyclorama, 8 x 6 monitor wall playing episode 1 frames,
  SELL / HOLD doors outlined in light); rooftop rain (instanced streaks, driver-animated). Flame emission lowered to 9
  after the last look test (pink-white at 14): re-check.

## State (2026-11-25)
- scene2.py builds (W/scene2_v2.blend): 56 shots, 145.8 s. Full preview reviewed (anim2_v1), first fix pass rendered (anim2_v2).
- Doors: red / green falling code (user request), done.
- Fixed in pass 1: basement wide (camera was above the ceiling), Mensa's second shot, café establishing shot (camera was outside
  the walls), Jeanphil "Me. Too." wide (a clone's fist filled the frame), Michi's rooftop line, the door wide, the save.
- Still to fix: Swordcat's "He holds." and Toshi's / This-Is-Fine's lines after the duel (the other café characters block
  them: restage the three after the duel); the duel catch (Swordcat too far from Anon in the catch shot: check headings);
  the Whale's close-ups look down onto his hat (use MS/MCU from eye level, not CU); the cracked bull (no crack yet);
  the rocket candle reads as a green bar beside Anon; then the 2D work in finish.py (crash opening, LIQUIDATION stamp,
  liquidation bar over Michi, closing).

## State (2026-11-25, later)
- Duel: blade catch measured on Swordcat's sword prop (`prop_blade`, parented to his right hand: attack1 at 60 % holds it level
  at 1.31 m pointing ahead); Anon steps in so his raised paws close on it. Side-on duel cameras from the open side of the café.
- Bull crack (ray-placed glowing fissure + falling chunk), rocket candle (size 2.6) with a tapered green exhaust streak.
- finish.py for episode 2: crash opening (code turns red column by column and falls; news ticker), typed messages,
  THE MEMETRIX II + red LIQUIDATION stamp with a crack, café and white-room grades, clone glitches, shockwave/save flashes,
  liquidation bar over the film with the world draining of colour (MARGIN RESTORED after the save), "To be continued...",
  new cast cards, taglines NOBODY HOLDS FOREVER. / WATCH ME., new sound (fire, white-room drone, battle music in the brawl,
  duel steel, clone zaps, shockwave, rocket launch, margin call riser, the save). Test sheets in review/.

## State (2026-11-25, evening)
- Café: real 3D city through a Boolean-cut window (towers with lit windows, wet street, neon PAWN / HODL 24H / NOODLES,
  street lamps); volumetric fire (12 fire volumes + wall/curtain fire, smoke layer under the ceiling, scorch marks); all café
  lights hidden from camera/glass/gloss rays. Café frames are ~3x slower than episode 1's: use more workers.
- CRT insert (n11_1): one Jeanphil, then four, then sixteen on the screen as the camera pulls back from inside Mensa;
  TV model's sticky notes removed from the glass. cine.py gained `look_at` (absolute look point for prop inserts).
- n11_0 holds a fixed heading while Mensa spins; f10 re-angled; key ring dimmer.

## Next
1. Full preview anim2_full3 (scene2_v17) -> hunt and fix.
2. Detail passes: rooftop rain and wet reflections, white room, brawl choreography, the Whale.
3. RENDER_LATER-style package for episode 2 (workers, 67 % / 6 samples, fog + motion blur ON).

## Earlier plan (kept for reference)
1. scene.py for episode 2 (copy ../memetrix/scene.py; keep Actor, glue, posed/fist_top/place, held poses, custom poses,
   IK-with-pole, cam_at, swallow-style measured targets). New: Swordcat duel (blocks, slow-motion lean, blade catch:
   glue Anon's paws to the blade), 12 Jeanphil clones (instances of the jeanphil character, shades fitted once and glued),
   green shockwave (expanding emissive torus + displaced floor), rocket candle flight (Anon on a path, sparks), Michi's
   liquidation (2D bar in the finish + grey-out material swap), the Whale floating (bob like Bome).
2. Rooftop: wet floor (lower roughness, puddle decals) + rain_cloud, night grade.
3. finish.py: the crash opening (green candles turn red and fall), red LIQUIDATION stamp with a crack, news ticker, closing
   tagline "NOBODY HOLDS FOREVER." / "WATCH ME.", cast cards for the 4 new characters.
4. Check frames per shot, before/after sheets to the user, then render with workers (see ../memetrix/RENDER_LATER.md).
