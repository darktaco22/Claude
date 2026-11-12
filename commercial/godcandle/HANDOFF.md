# HANDOFF: "GOD CANDLE" cinematic (Meme Royale)

Branch `claude/clash-final` (repo `darktaco22/claude`). Code: `commercial/godcandle/`. Work folder (not in git): `~/gc_work` (`/root/gc_work`).
Follow the root `CLAUDE.md`: long jobs run as tracked background tasks (`run_in_background`, timeout 7200000), exit 3 means run again.

## HOLD: do not start the full render before 9:30 AM (the user's local time)

The user asked to stall the full render until 9:30 AM and will `/compact` at 9:30. Everything needed is in this file and in git.
Test stills and contact sheets are fine before then; `render_all.sh` is not.

## What the user asked for (their words, in order; all still apply)

1. The god candle comes off a pump.fun chart and lands in the game from the sky; cinematic, special camera angles and effects.
2. It opens as an **over-the-shoulder view of a trader on his phone making a trade on the pump.fun app**, then it **zooms into the phone**,
   the god candle zooms up and falls down into the game.
3. Use their **screenshot of the real pump.fun app** for the phone UI (`ref_ui.png`), and the **Imagine Game Studio chart** in it.
4. The fall: a cinematic shot of it **falling on actual game characters in the actual Meme Royale arena**, camera **like a rocket falling back
   into Earth's orbit**.
5. The trader must be a **real-looking human** found on GitHub (not blocky): Microsoft Rocketbox `Male_Adult_18` (MIT), the man in the grey hoodie.
6. **You must be able to see the phone.**
7. **Fix every bug or glitch**: fingers in the way of the screen, the palm inside the phone, a wrist bent at 90 degrees, anything else found.
8. **Whale and giga are overused: different characters.** Now: chillhouse vs goat in the centre; popcat/pnut, apu/michi, dope/walter, pippin/nyancat.
9. **Clouds and a blue sky; the brown ground round the arena must not be visible** (blur it, hide it in cloud, or a city).

## The film (474 frames, 19.75 s, 24 fps, 1280x544 rendered, finished to 1920x1080 letterbox)

`scene.py` builds everything and writes `edl.json` (the shot list; `render_edl.py` renders film frames from it, with speed ramps, follow cameras,
orbits, roll, fstop ramps and an up-vector ease). Timeline constants are at the top of `scene.py` (T_SWAP 3.4, T_LAUNCH 4.5, T_CEIL 4.65,
T_FLASH 6.2, T_DROP 6.25, T_IMP 9.45).

| Shot | Film frames | What |
|---|---|---|
| 1 | 1-82 | Over his right shoulder, pushing in on the phone: he taps Buy, the 5 chip, Buy; the chart goes parabolic |
| 2 | 83-113 | The candle leaves the screen (slow motion) |
| 3 | 114-137 | From the side: it rises past him |
| 4 | 138-157 | Up through the ceiling |
| 5 | 158-180 | The chase into the blue sky |
| 6-9 | 181-279 | The fall: onboard camera rolling, long-lens chase, ground look-up, low approach among the fighters |
| 10-13 | 280-399 | The slam in slow motion: orbit, shockwave, top-down, flying fighters |
| 14 | 400-474 | Crane up and back over the stadium; title "GOD CANDLE" (finish.py adds 40 hold frames) |

Files: `ui.py` (phone screen frames from `ref_ui.png` + monitors), `rbtrader.py` (the Rocketbox trader: FK/IK, hold solved for least wrist
bend, hand fitted to the phone by testing skinned vertices), `rb_test.py` (stills of the trader alone), `scene.py`, `render_edl.py`,
`finish.py` (grade, flashes, punches, edge blur on the fall, title, sound), `render_all.sh` (everything, resumable).
`trader.py` / `trader_test.py` / `setup_humans.sh` are the earlier MakeHuman trader: unused now (the user wanted the GitHub human).

## Update: ceiling break and rooftop shot (film is now 529 frames, 22.05 s, plus a 40-frame title hold)

The user added: the ceiling literally breaks open as the candle flies up, then an aerial shot of the house roof looking down through the
hole at the trader, who looks up shocked (comedy beat). Both are in `scene.py` (search `T_CEIL`, `bursty`, `fbox`, `rfrag`) and
`rbtrader.py` (`react`). Shots: 1: 1-82, 2: 83-113, 3: 114-137, 4 ceiling: 138-170, 4b rooftop crash zoom: 171-211, 5 chase: 212-234,
arena from 235. Room frames 1-234 are rendered and reviewed; `render_all.sh` splits room/arena at `shots[5]`.
Trap: clash `box()` applies location, so `o.location` is (0,0,0); use `fbox`/`centre` for anything that must move or be distance-tested.
Known nit: the hole edge is stair-stepped (0.2 m grid).

## State when this was written (older; frame counts below predate the update above)

- Trader pose fixed on the blank test set (`rb_test.py`): holds in the RIGHT hand, taps with the LEFT; wrist bends 18 and 21 degrees; no hand
  vertex inside the phone. Open nit: the holding thumb sticks out sideways rather than resting on the phone's edge (THUMB_IN / HOLD['t'] in
  `rbtrader.py` were just changed, not yet looked at).
- `~/gc_work/room.blend` and `scene.blend` are STALE (built before the hand swap and the latest `scene.py` edits). Rebuild both before anything.
- Arena fixes made but NOT yet seen in a render: soft cloud deck with a hole over the stadium (was "popcorn" puffs), duels moved inside the
  court, ground cameras moved out of the wall, saturated green candle, dimmer ceiling break, smaller explosion smoke.
- `finish.py` (grade + sound) has never been run: test it on a few frames, then the whole film; check the mix isn't clipping.
- Nothing of the final film is rendered. Per-frame time: about 18 s (room, shots 1-5) and 25-60 s (arena): roughly 4.5 h in total, 3 chunks.

## To finish

1. Rebuild and re-test (allowed before 9:30; run as one tracked background command from `commercial/godcandle`):
   ```
   export W=$HOME/gc_work B=/opt/blender/blender-4.2.3-linux-x64/blender
   $B -b --factory-startup -P rb_test.py -- $W/rb 1.7                       # stills: $W/rb_{ots,phone,left,side}.png
   rm -f $W/room.blend $W/scene.blend
   $B -b --factory-startup -P scene.py -- --out $W/room.blend --ui $W/ui --room > $W/build_room.log 2>&1
   $B -b --factory-startup -P scene.py -- --out $W/scene.blend --ui $W/ui > $W/build.log 2>&1
   echo "10 40 62 80 95 112 125 148 168" > $W/testA.txt; echo "190 220 245 270 285 300 335 365 420 470" > $W/testB.txt; rm -f $W/test?.txt.done
   $B -b $W/room.blend -P render_edl.py -- $W/testA.txt > $W/testA.log 2>&1; $B -b $W/scene.blend -P render_edl.py -- $W/testB.txt > $W/testB.log 2>&1
   ```
   Make a contact sheet of `$W/frames/f_*.png` and LOOK at every frame. Check: phone visible and readable; no finger across the glass; wrists;
   the candle leaving the screen where the 2D candle was; nothing blown out; no camera inside a wall, tower, fighter or smoke; no bare brown
   ground from above (frames 190, 220); cloud deck looks like cloud; candle solid green; fighters under the candle.
2. Fix what is wrong, rebuild, re-test until clean. Send the user a sheet.
3. After 9:30 AM: `cd commercial/godcandle && ./render_all.sh` (tracked background, timeout 7200000). Exit 3 / "RELAUNCH": run it again.
   It ends with `ALL-DONE` and writes `commercial/output/meme-royale-god-candle.mp4`.
4. Watch the result (contact sheet of `$W/fin`), fix glitches (re-render only the affected frames: delete them from `$W/full_*.txt.done`),
   commit the mp4 and push to `claude/clash-final`. Send the user the video. No pull request unless asked.

## Fresh machine

`render_all.sh` installs Blender (`../noobpro/setup.sh`), clones the one Rocketbox avatar (sparse, into `/home/user/microsoft/microsoft-rocketbox`),
regenerates the UI frames and builds both scenes. FBX import needs no add-on (`--factory-startup` is fine).
