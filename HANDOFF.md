# HANDOFF: Degens Anonymous, realistic remake

Branch: `claude/blender-meme-royale-commercial-y76uf9` (repo `darktaco22/Claude`). Code lives in `commercial/degens/`.
The earlier house-party project's handoff moved to `commercial/party/HANDOFF.md`.

## Goal

Remake the 48.4 s vertical (1080×1920) skit **"Degens Anonymous"** as realistic 3D with sound, keeping the original
timing, dialogue, shots and gags exactly. A 3 AM church-basement support group for crypto degens. The person asked for:

- Realistic people (no famous characters), real props, nothing clipping, hands really holding things.
- **NEET** (their game's character, `studio/models/neet.glb`) left exactly as he is. He's never modified, only placed.
- A high-quality cigarette: tan filter between Earl's lips (seam found by a ray scan), drooping with gravity, ash and
  ember on the white end, pinched in the index–middle finger gap when in his hand.
- Dark, gloomy lighting. The launched coin is **$ROYALE**. Voices say **"NEET"**, never "Gary".
- Kokoro voices (they liked them). A straw slurp for Linda's sips. As smooth as possible: motion blur, a gliding
  camera, plus a 60 fps version made with RIFE.
- An over-the-shoulder shot of the PnL on Pam's phone instead of a full-screen pop-up.
- Repeated glitch hunts. They explicitly want visual anomalies found and fixed.

## Concept and shot list (t in seconds; frame = t·30 + 1)

| t | Shot | What happens |
|---|---|---|
| 0–3.2 | Rainy alley, push-in | NEET walks to the door under the "Degens ANONYMOUS / MEETS NIGHTLY · 3 AM" neon. Caption "he left the basement for this." Line "Leaving the basement!" |
| 3.2–7.2 | Wide, dolly in | The circle of chairs. Pam: "Welcome back, everyone. Who would like to share?" |
| 7.2–9.25 | NEET single | NEET stands: "Hi. I'm NEET." |
| 9.25–10.9 | Wide | Everyone: "Hi, NEET." |
| 10.9–13.5 | NEET single | "It's been… four minutes… since my last trade." |
| 13.5–15.3 | Pam single | "That's a new record, NEET." |
| 15.3–16.8 | NEET single | NEET celebrates (win clip). Pam and Linda slap their thighs twice (applause, mugs in their other hands) |
| 16.8–22.8 | Linda singles (close cut 19.9–20.75) | "I told my husband I lost our savings at the casino." Sips the wine bottle hidden in her WORLD'S BEST MOM mug through a straw (slurp). "Because that's less embarrassing." |
| 22.8–29.1 | Earl singles (close cut 25.0–26.4) | Cigarette in his lips: "I sold a kidney to buy the dip." He drags (ember glows), exhales volumetric smoke: "I'm thinking about selling the other one." He wears a nasal cannula to an oxygen tank |
| 29.1–29.7 | NEET single | "Let's go!" (fist pump) |
| 29.7–34.3 | Chad single | Sniff and nose wipe. "I'm not addicted. I can stop anytime." Phone ding. "After this one." |
| 34.3–36.7 | Wide | Every phone pings ($ROYALE launch alert), room lights drop, faces lit by phones, they look around |
| 36.7–39.4 | Pam single | "Let's… take a five minute break." |
| 39.4–41.6 | Wide toward the exit | Stampede: Chad, Earl, Linda and NEET run out the real doorway into the corridor. Chairs topple back. Door slams at 41.2 |
| 41.6–42.4 | Empty-room shot | Pam alone among the toppled chairs |
| 42.4–44.6 | Over Pam's right shoulder | Her phone: DEV WALLET $ROYALE +$2,413,907, chart, Holders: 5 (she's the dev). She sips her mug |
| 44.6–48.4 | Pam push-in | Lights switch off one by one, her face lit by the phone: "Same time next week." Black at 48.0 |

## Done

- **Scene:** `director.py` builds everything and keys every frame (about 1.5 min per build, deterministic):
  - Cast: Pam, Linda, Earl and Chad are original MakeHuman people (MPFB 2, CC0) on the full MakeHuman rig, with
    jaw, eyelid and viseme lip-sync.
  - NEET is the game model with his own clips via NLA.
  - Props: Poly Haven CC0 props, plus modelled mugs, can, phones, oxygen tank and cannula.
  - Sets: basement with a real exit doorway and corridor, and the rainy alley.
- **Clipping work:**
  - Seat fitting (two-way contact tests, per-person chair scale).
  - NEET on a low stool fitted to his own sit pose, so he isn't moved or changed.
  - Exact skinned-hand grip solving (`grips.py`). Fingers stop 1–3 mm from the prop surface.
  - The cigarette's finger gap is measured on the evaluated hand.
  - Hand-on-thigh clearance search.
  - The cannula is skinned to the skin with smoothed weights.
  - Clothing masks.
  - Sweeps: `qa_all.py`, `propcheck.py`. Remaining known minor contacts: Chad's glasses temples behind his ears
    and a 1 cm brush when Chad and Earl stand at 39.8. "Linda into NEET" in the sweep is a false positive (NEET's
    open mesh).
- **Glitches fixed:**
  - Black wedges were the wall's lower band z-fighting with the wall (wrong normal; it now sits 8 mm in front, and
    the rail is full length).
  - The 1-frame "metronome" tube flicker became eight irregular bursts (`FLICKER_BURSTS`).
  - A wall was missing its doorway; it now has one.
  - Rain fills the alley.
- **Sound:**
  - `audio/mix_kokoro.m4a` is the final mix: Kokoro voices fitted to the original line timing, every line says
    NEET, "Let's go!" is audible, plus the slurp.
  - Rebuild it with `voices.py` → `mixvo.py` (`audio/cues.json`, `audio/vo_kokoro/`, `audio/sfx/`).
- **Frames:**
  - Rendered with the final scene for frames **1–363 and 726–1452**. Parts came from worker sessions on branches
    `claude/degens-part-1b, -1c, -3, -4, -5` (each holds `commercial/renders/part_A_B.mp4`, x264 yuv444 crf 9,
    720×1280).
  - The previous complete video (before motion blur and the latest fixes) is `commercial/output/degens-anonymous-realistic.mp4`.

## Left to do

1. **Render frames 364–725.** This session was rendering them locally (see "How to render"). The six worker sessions
   for this range (`degens-part-2, -2b … -2f`) stopped when the account hit its weekly usage limit, and none of
   their output was pushed.
2. **Unpack the part videos into frames** (if this machine is fresh): `merge_parts.sh`, or `ffmpeg -i part_A_B.mp4 -start_number A f_%04d.png`.
   Check every frame count.
3. **30 fps:**
   ```
   assemble.sh $W/frames $W/ovl audio/mix_kokoro.m4a ../output/degens-anonymous-realistic.mp4
   ```
   Make the overlays first with `node overlays.js $W/ovl` (30 fps). Run the glitch scan
   `python3 spikes.py $W/frames` (in the scratch workspace; it's a 15-line script that flags 1-frame jumps).
   Look at what it flags; periodic hits every 16 frames used to be the old flicker.
4. **60 fps:**
   1. `node overlays.js $W/ovl60 60`
   2. `python3 interp60.py $W/frames $W/f60 <rife dir>` (RIFE `rife-ncnn-vulkan-20221029-ubuntu`, model `rife-v4.6`,
      from GitHub nihui/rife-ncnn-vulkan; needs `apt-get install mesa-vulkan-drivers`; the person allowed running
      it). The script holds frames at cuts.
   3. `assemble60.sh $W/f60 $W/ovl60 audio/mix_kokoro.m4a ../output/degens-anonymous-realistic-60fps.mp4`
5. Send both MP4s to the person, commit them, and spot-check frames (cigarette, PnL shot, stampede, ending).

## Key decisions

- **Cast and content:** original MakeHuman people only (never real or famous people). NEET is untouched. If he
  clips, move his seat or stool, never him.
- **Rendering:** Cycles on CPU (4 cores, no GPU) at 720×1280 with 8 samples and OIDN (albedo and normal), then
  upscaled to 1080×1920 with lanczos plus unsharp. Motion blur is on (shutter 0.5) for the camera and objects; body
  deformation blur is off (a speed choice the person picked). The camera keys are linear within shots and constant
  at cuts (`CUTS` in `director.py`).
- **Overlays:** subtitles, the launch alert and the caption are HTML (`overlay.html`) rendered as transparent PNGs
  and laid over the frames. The wallet pop-up is disabled; the PnL lives on Pam's phone screen instead.
- **Containers:** cloud containers here get recycled after about 15 minutes idle, which kills detached renders.
  `render_list.py` writes `<list>.done` so restarts skip finished frames. Check every 15 minutes and restart.
- **Worker sessions:** these used a lot of the account's weekly usage. Prefer rendering in one session unless the
  person asks for parallel.
- **Assets:**
  - Poly Haven needs the User-Agent `scene-builder/1.0`.
  - Some Poly Haven `.blend` files are newer than 4.2 and fall back to glTF automatically.
  - MakeHuman packs come from files.makehumancommunity.org.

## File paths

- Code: `commercial/degens/`
  - Scene: `director.py`
  - People: `humans.py`
  - Pose and IK: `rigctl.py`
  - Grips: `grips.py`
  - Props: `props.py`
  - Sets: `room.py`
  - Asset loader: `assets.py`
- QA:
  - `qa.py`: stills
  - `closeqa.py`: close-ups (env `CQ=…`)
  - `qa_all.py`: clipping sweep
  - `propcheck.py`
  - `clipcheck.py`
- Render:
  - `render_list.py`: resumable list renderer
  - `render_part.sh` + `setup_remote.sh`: fresh-machine setup and range render
  - `merge_parts.sh`
- Video:
  - `assemble.sh` / `assemble60.sh`
  - `interp60.py`
  - `overlays.js` + `overlay.html` (+ `lilita.woff2`, `vo.json`)
- Sound: `voices.py` (Kokoro via `kokoro-onnx`, model files from GitHub thewh1teagle/kokoro-onnx release
  `model-files-v1.0`), `mixvo.py`, `slurp.py`, `audio/`
- Studio inputs: `studio/vo.json` (line timing and lip-sync envelopes), `studio/models/neet.glb`
- Scratch workspace (not in git): `W` in `env.sh` holds `frames/`, `ovl/`, `da8.blend` (the final scene) and `ph/`
  (Poly Haven).

## How to render (fresh machine)

```bash
cd commercial/degens
export W=$HOME/da_work
./setup_remote.sh                               # Blender 4.2, MPFB + CC0 MakeHuman packs, Poly Haven assets (about 5–20 min)
export DA_STUDIO=$PWD/studio; . ./env.sh; export W DA_STUDIO PH=$W/ph DA_TEX=$W/tex
$BL -b -P director.py -- --out $W/scene.blend   # build the scene (about 1.5 min)
seq 364 725 | tr '\n' ' ' > $W/mid.txt
setsid nohup $BL -b $W/scene.blend -P render_list.py -- $W/mid.txt > $W/render.log 2>&1 < /dev/null &
# resumable: rerun the same line after a container recycle; progress: wc -w $W/mid.txt.done
# or one range in one go: ./render_part.sh 364 725 $HOME/part.mp4
```

Then follow "Left to do" steps 2–5. Builds are deterministic, so frames from different machines match.
