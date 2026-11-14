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
- Script, voices, scene, renderer, finish and graphics all written and tested on a low-res run-through
  (`$W/ani`, every 6th frame at 40 %): all 29 shots read.
- A rebuild with four shot fixes was running (walk hero camera moved behind the squad's landing point, "useless
  wins" camera out of the smoke, interview microphone lowered, king-tower smoke thinned), followed by tests
  `$W/t4` (the fixed shots, half size) and `$W/t5` (five full-size frames for timing: `grep DONE $W/t5.log`).

## Next steps
1. Look at `$W/t4/*.png` (walk hero ×5, useless wins, interview, collapse ×2). Fix anything still wrong.
2. Read the full-size frame times in `$W/t5.log`. Budget: 2852 frames. Half-size tests took 12–15 s a frame, so
   expect 20–30 s at full size (16–24 h). If over ~25 s, render with `SCALE=85` (finish.py upscales anyway).
3. `rm -f $W/all.txt $W/all.txt.done; rm -rf $W/frames` then `./render_all.sh` in 2-hour chunks until `ALL-DONE`.
   Disk: about 4 GB free; frames need ~2.5 GB, finished frames ~6 GB → delete `$W/ani`, `$W/t1..t5`,
   `/root/tools/vdb`, `/root/tools/cast`, `/root/wild_work/frames` first, and encode straight after finishing.
4. Review with contact sheets + dark-frame scan, check mp4 < 100 MB (raise `-crf` if not), commit, push, send.
5. Not yet heard by anyone: the mix. Say so when delivering.

## Known soft spots
- Opening aerial is plain; the booth shot shows the commentators from behind and is dark.
- Whale fills the frame at the end of the replay burst (kept: "He's simply enormous").
- Telestrator whale arrow uses fixed screen positions, tuned to the replay camera (38 mm).
