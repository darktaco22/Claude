# Meme Royale: A Natural History (59.9 s)

Deadpan wildlife-documentary parody. Output: `commercial/output/meme-royale-natural-history.mp4`.

## Rebuild
Work folder `/root/wild_work` (not in git). Needs Blender 4.2.3, `pip install kokoro-onnx`, the Kokoro model files in
`$W/kokoro`.

1. `python3 voices.py $W/kokoro $W/vo [voice]` – narration (default `bm_george`) and `vo.json`.
2. `python3 tex.py $W/tex` – rug texture.
3. `./render_all.sh` – builds `scene.blend`, renders 1339 frames, finishes and encodes. Launch it as a tracked
   background job (timeout 7200000). It stops before the 2-hour cap and prints `RELAUNCH`; run it again until
   `ALL-DONE` (four chunks, about 7 hours on 4 cores).

Changing the narrator: keep each line's duration equal to the value in `vo.json` so `edl.json` stays valid, then rerun
only `finish.py` and the encode.

## Known soft spots
- Eruption and timber shots bloom close to white.
- Impact fire puffs in the timber shot look ball-like.
- Audio mix was set by levels only; nobody has listened to it.
