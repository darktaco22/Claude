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

## Next
1. scene.py for episode 2 (copy ../memetrix/scene.py; keep Actor, glue, posed/fist_top/place, held poses, custom poses,
   IK-with-pole, cam_at, swallow-style measured targets). New: Swordcat duel (blocks, slow-motion lean, blade catch:
   glue Anon's paws to the blade), 12 Jeanphil clones (instances of the jeanphil character, shades fitted once and glued),
   green shockwave (expanding emissive torus + displaced floor), rocket candle flight (Anon on a path, sparks), Michi's
   liquidation (2D bar in the finish + grey-out material swap), the Whale floating (bob like Bome).
2. Rooftop: wet floor (lower roughness, puddle decals) + rain_cloud, night grade.
3. finish.py: the crash opening (green candles turn red and fall), red LIQUIDATION stamp with a crack, news ticker, closing
   tagline "NOBODY HOLDS FOREVER." / "WATCH ME.", cast cards for the 4 new characters.
4. Check frames per shot, before/after sheets to the user, then render with workers (see ../memetrix/RENDER_LATER.md).
