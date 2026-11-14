# "The Final" (Meme Royale Championship) – handoff and render plan

Sports-broadcast parody, 2 min 07.6 s (3D ends at 118.84 s, 2852 frames at 24 fps, then a 2D end card).
Output: `commercial/output/meme-royale-the-final.mp4`. Work folder `/root/final_work` (not in git).

## Story
Two commentators (Chip Ledger, play-by-play, voice `am_michael`; Basil Hodl, analysis, voice `bm_george`) call the
final. Giga (44–0) sends the Whale through Pepe's towers; Pepe (3–41, down 99%) plays nothing; his one card is
Useless, who walks the pitch unmarked, taps the king's tower and wins 3–2. Interview: Pepe says nothing.
28 lines in `voices.py` ("Pepe" is spelled "Pepay" for speech). No real person's voice is cloned.

## Files
- `voices.py` – Kokoro narration → `$W/vo/*.wav`, `vo.json`.
- `scene.py` – exec's slices of `../clash/scene.py` (arena, stadium, crowd, units, FX), adds the match, booth,
  microphone, confetti, explosion cards, and the 29-shot edit. Writes `edl.json` (shots, cues, ev, gfx, cards).
  Build takes ~12 min. Explosion "fire" spheres are replaced by a transparent material (`NOFIRE`); fire is stock
  footage on cards (`fx_card`), smoke/dust thinned.
- `render_edl.py` – renders film frames from `edl.json`; recorded handheld shake (`../tools/shakify`), pre-flight
  check, sets each explosion card's video frame from animation time (move `frame_start`, not `frame_offset`).
  Env: `W`, `OUT`, `SCALE`, `SAMPLES`, `RENDER_BUDGET` (exit 3 = run again).
- `finish.py` – 1080p grade + broadcast graphics (title, name straps, stat cards, score bug, clock, win probability,
  LIVE/REPLAY, wipes, telestrator, ticker, captions, full-time board, cinema bars for the walk, end card) and the
  sound mix. `python3 finish.py FRAMES OUT VO [f1,f2]`; `SOUND_ONLY=1`.
- `render_all.sh` – build if needed → render all → finish → encode. Prints `RELAUNCH` (exit 3) or `ALL-DONE`.

## To rebuild the work folder from nothing
1. Kokoro model files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) in `$W/kokoro` (currently in `/root/wild_work/kokoro`;
   `pip install kokoro-onnx`). `python3 voices.py KOKORO $W/vo`.
2. `$W/fx/explosion.mp4` = CGHeven "Aerial explosion 06 front, 1K H.264" (CC0, 4 MB):
   `https://cdn.cgheven.com/file/cghaven-2025/VFX/Explosion/Aerial_Explosion/Aerial_Explosion_06/Front/Videos/H.264/Aerial_explosion_06_Front_1K_H.264.mp4`
3. `KOKORO=/root/wild_work/kokoro ./render_all.sh` as a tracked background job (timeout 7200000); on exit 3 run again.

## State when this was written
- Script, voices, scene, renderer, finish and graphics all written and tested on a low-res run-through: all 29
  shots read. Graphics tested on those frames.
- Measured: full size is 35–48 s a frame (32 h). Decision: render at `SCALE=75 SAMPLES=7` (now the default in
  `render_all.sh`), about 16 h in 2-hour chunks.
- Test `$W/t4` showed: walk-hero camera was INSIDE the red right tower (black frames; tower footprint is
  x 12.05–16.95, y −8.95 to −4.05) and the squad landed inside it too; "useless wins" showed the coin's blank back;
  interview microphone was out of frame. Fixed in `scene.py` (camera at y −9.3, squad lands at y −10.4, Useless
  turns to face south after the collapse, microphone raised). A rebuild plus test `$W/t6` (8 frames at render
  settings; times in `$W/t6.log`) was running.

## Full render: STARTED
- Test `$W/t6` passed (walk, squad pass, celebration, collapse all read; ~22 s a frame at 75 % / 7 samples, so
  about 17.5 h for 2852 frames). The interview microphone was moved once more; that change is in `scene.py` AND was
  patched straight into `$W/scene.blend` (`$W/patch.py`) to avoid a rebuild.
- Running: `cd commercial/final && KOKORO=/root/wild_work/kokoro ./render_all.sh 2>&1 | tail -5` (tracked background
  job, timeout 7200000). Frames go to `$W/frames`; progress: `ls $W/frames | wc -l` of 2852.

## Next steps
1. Each time the job ends with `RELAUNCH` (exit 3 inside the script; the pipe reports exit 0, so read the output),
   run the same command again, about 9 times, until `ALL-DONE`. If the container was reclaimed, rebuild the work
   folder (section above), then run it.
2. Disk: finished frames need ~6 GB. If finish.py dies on disk space, free space (`$W/frames` is no longer needed
   once `$W/fin` is complete) and run finish.py + the ffmpeg line from `render_all.sh` by hand.
3. Review with contact sheets + dark-frame scan, check mp4 < 100 MB (raise `-crf` if not), commit, push, send.
4. Not yet heard by anyone: the mix. Say so when delivering.

## Known soft spots
- Opening aerial is plain; the booth shot shows the commentators from behind and is dark.
- Whale fills the frame at the end of the replay burst (kept: "He's simply enormous").
- Telestrator whale arrow uses fixed screen positions, tuned to the replay camera (38 mm).
