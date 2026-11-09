# HANDOFF: MEME ROYALE videos

Branch: `claude/blender-meme-royale-commercial-y76uf9` (repo `darktaco22/Claude`). Everything below lives in `commercial/`.

## Goal

Videos for the game at https://memeroyale.imaginestudio.fun. Characters, models, card art, logo, font and sounds are the
game's own files, taken from the live site.

**Current focus: the house party.** All the characters throw a wild party at a mansion with a pool, in one panoramic camera
sweep. The person's notes ask for: drinking, cannonballs, couples kissing, smoking, a bong, lines being snorted (bending
right down, a puff of powder), dancing with real dance moves, people walking around, The Whale making it rain, more
crypto-meme characters, club music with heavy bass, no generated voices, rich textures and real trees (no low-poly blobs),
a populated background, and repeated glitch checks. They asked for as much time as it takes to make it look high quality.

## Done (all in `commercial/output/`)

| File | What |
|---|---|
| `meme-royale-seeker-blender.mp4` | 16:9, 29 s. Solana dApp Store / Seeker commercial: real engine footage, PEPE on a phone in space (Blender), cut in Blender's sequencer. |
| `meme-royale-seeker-raea.mp4` | 9:16, 20 s, the same message, made with raea. |
| `meme-royale-runway.mp4` | 2:54. All 39 characters walk a runway one by one, pose, exit; backdrops cross-fade (raea). |
| `meme-royale-house-party.mp4` | The **previous** 24 s party render. The person rejected it (glitches, voices, low poly, empty background). Kept for reference only. |
| `raea-showcase.mp4` | A raea demo. |

The party has been rebuilt since that render, and the new version **is not rendered yet**. Its source is in
`commercial/party/`:

- `party.py`: the scene, guests, camera and render settings. It runs `dressing.py` and `environment.py` inside its own namespace.
- `moves.py`: IK moves for poses mocap can't cover (kiss, snort, bong sit, swim, despair, cheer, tuck, make-it-rain), plus the `Char` controller (body-safe hand targets, clip playback through NLA).
- `retarget.py`: CMU BVH mocap onto the game's Mixamo rigs, relative to each rig's rest pose. Used by dancers, DJ, smokers, chuggers, LMAO, the drunk.
- `dressing.py`: architecture, the kitchen, and the mess (cups, cans, pizza boxes, confetti, balloons, shopping cart, cones, neon signs).
- `environment.py`: the city-skyline HDRI, terrain, perimeter wall, Poly Haven trees and plants (instanced), and PBR textures on every surface.
- `qa.py`: glitch check. Hides every other guest and frames one character's real head at chosen frames.
- `checkpoint.sh`: builds the scene and saves `party.blend`, renders scene stills, then runs the QA close-ups for all 45 guests.
- `mix.py`: the soundtrack. Club track plus the game's crowd and effects sounds, no voices.
- `assemble.sh`: frames plus mix into the final MP4, with the end logo card and the music credit.
- `setup_assets.sh`: re-downloads everything that lives outside the repo.
- `assets/`: `bill.png` (MEME BUCKS banknote), `ComicNeue-Bold.ttf` (OFL, for the doge words).

What the new party contains (30 s, 900 frames at 30 fps):

- **Characters:** 45 guests. These are the 39 game characters plus six new memes recolored from the game's own models: DOGE (with floating "wow / such party / much rich" words), dogwifhat (pink knit beanie, in the conga), Brett (blue PEPE), NPC Wojak (grey, does the robot), Pink Wojak (despair at the pool edge) and Fwog (tiny frog on the pizza float). The DJ has laser eyes.
- **Motion:** mocap dances for the dancers (salsa, Charleston, moonwalk, robot, breakdance, Russian dance, lambada, twist, chicken dance, Mickey dance). The drinkers chug and the smokers raise a cigarette on a hand-to-mouth clip. LMAO laughs, and Chill House does a drunk walk on the lawn. Chill Guy, Jean Phil and DOPE walk loops on the game's own walk clip, matched to pace.
- **Gags:**
  - POPCAT stands, runs, then cannonballs. Before this, it ran on the spot.
  - SWORDCAT backflips off the balcony.
  - The Whale throws 350 textured bills from the balcony.
  - KET and CATE snort at the kitchen island and FARTER at the coffee table: they bend right down, a powder puff rises, and lines shrink.
  - PEPE + PIPPIN and Trollface + MICHI kiss.
  - The smokers stand under the pergola and the bong sits by the east lounge chairs. Both were restaged so the camera actually frames them.
- **Set:** a villa with a kitchen (cabinets, fridge, hood, island), parquet, a stone wing, a pergola, a fire pit, a perimeter wall, city lights, and hills with neighbours' houses.
- **Music:** Kevin MacLeod, "Cut and Run" (CC BY 4.0, credited on the end card). It was the bassiest of the candidates measured with librosa, cut to its strongest 30 s from a beat at 101.05 s.

## Left to do

1. **Finish checkpoint 3 and review it.** It was running at handoff, output in `$W/ck3`. Look at every scene still and every `qa_<name>_<frame>.png`. Check:
   - the snort reads: nose at the line, puff, line shrinking
   - the new characters' colors and the WIF beanie's fit on the head bone (tune the offset in `beanie()`)
   - Fwog on the float, the DOGE words, the DJ's lasers
   - no limbs through bodies, nobody overlapping, the camera not inside anything

   Fix, then repeat the checkpoint until clean. The person explicitly wants these checkpoints.
2. **Final render** from `party.blend`, 900 frames at 1280×720, 12 samples. At about 35–41 s a frame that's about 9–10 h. It resumes: frames that exist are skipped (`use_overwrite = False`). Check finished frames mid-way, for example at 25%, 50% and 75%.
3. **Mix, assemble and check.** Run `mix.py`, then `assemble.sh` (the end card comes in at 27.2 s), then `raea check` or ffmpeg loudness. Target is -14 LUFS with true peak ≤ -1.5 dB. AAC overshoots, so the mix already masters to TP -3.
4. **Deliver.** Commit `commercial/output/meme-royale-house-party.mp4`, replacing the old one, plus a contact sheet. Send it to the person.

## Key decisions

- **Real people:** characters that look like real, identifiable people (GIGA, NEET, Jean Phil, MENSA, MITCH, Alon) are never shown using drugs or kissing. They dance, walk and drink only. The person accepted this. Drug and kiss gags go to fictional cartoon characters.
- **Renderer:** Cycles, not EEVEE. EEVEE runs on software GL here and was about 4× slower. The CPU has 4 cores, there's no GPU, and RAM is 15 GB.
- **Subdivision:** characters get render-level-1 subdivision with `use_limit_surface=False` and `quality=1`. The default OpenSubdiv limit surface blew memory past 11 GB, and the kernel killed the process.
- **Mocap:** CMU BVH from the `una-dinosauria/cmu-mocap` GitHub mirror (cgspeed's conversion, free for any use), sparse-checked-out per clip. Rigs that aren't Mixamo-standard (BOME, DOPE, MENSA, MOO DENG, POPCAT) play the game's own clips instead.
- **Sources:**
  - Allowed, all CC0: Poly Haven (HDRIs, models, textures). Poly Haven needs a non-default User-Agent, so use `party-scene-builder/1.0`.
  - Blocked: Poly Pizza, Kenney and Quaternius's itch.io downloads. That's why the new memes are recolors of game models.
- **Voices:** removed. Don't reintroduce generated voices; the person didn't like the Chatterbox lines.
- **Credit:** the music credit is required (CC BY): "Music: Cut and Run by Kevin MacLeod (incompetech.com), CC BY 4.0". It's drawn on the end card by `assemble.sh`.

## How to rebuild and render (fresh container)

```bash
# Blender 4.2 LTS (headless; needs: apt-get install -y libegl1 libgl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6)
mkdir -p /opt/blender && cd /opt/blender && curl -sSO https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf blender-4.2.3-linux-x64.tar.xz
export BLENDER=/opt/blender/blender-4.2.3-linux-x64/blender
pip install librosa                      # only for re-picking music beats

W=/tmp/party-work                        # any scratch dir with ~5 GB free
cd /home/user/Claude/commercial/party
./setup_assets.sh $W                     # game models + cards + logo, Poly Haven, CMU clips, music, game sounds

# 1. checkpoint (build + save $W/party.blend + stills + per-guest QA close-ups)
./checkpoint.sh $W $W/ck 180,230,300,345,395,520,600,700,760,800

# 2. final frames (resumable; run detached so a lost shell doesn't stop it)
mkdir -p $W/frames
setsid nohup $BLENDER -b --factory-startup -P party.py -- --models $W/models --ph $W/ph --cmu $W/cmu \
  --w 1280 --h 720 --samples 12 --render $W/frames > $W/render.log 2>&1 < /dev/null &
#   (or render the saved file: $BLENDER -b $W/party.blend -o $W/frames/f_ -a)

# 3. sound, assembly, check
cd $W && cp /home/user/Claude/commercial/party/mix.py . && python3 mix.py     # -> $W/party_mix.wav (30 s)
/home/user/Claude/commercial/party/assemble.sh $W/frames $W/party_mix.wav \
  /home/user/Claude/commercial/assets/logo.png /home/user/Claude/commercial/assets/lilita.ttf \
  /home/user/Claude/commercial/output/meme-royale-house-party.mp4
ffmpeg -i /home/user/Claude/commercial/output/meme-royale-house-party.mp4 -af loudnorm=print_format=summary -f null -
```

Useful flags on `party.py`: `--stills F1,F2 DIR`, `--save FILE`, `--samples N`, `--w/--h`, `--frames N` (default 900),
`--sky 0.55`, `--sky_rot 200`, `--nosubd`, `--clean` (drops the substance gags).

In this session's container the work dir was `/tmp/claude-0/-home-user-Claude/413acb09-d245-518f-9732-6f706f9d32b5/scratchpad`.
Its folders map to the layout above:

- models, cards and `logo.png` are in `runway/media/`, so pass `--models runway/media/models`
- the Poly Haven assets are in `party/ph`
- the CMU clips are in `cmu`
- the music, the game sounds and `mix.py`'s working copy are in `party/`

Those all need `setup_assets.sh` again after a container rebuild.

## Other tools used earlier (for the commercials, not needed for the party)

raea, installed from https://raea.io/install with `RAEA_VERSION=0.1.0-canary.2` because the GitHub API is rate-limited. It
needs `apt-get install mesa-vulkan-drivers` and `WGPU_BACKEND=vulkan VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json`. The
engine-capture harness for the commercials is in `commercial/engine/capture/`, using Playwright with a virtual clock on the live game.
See `commercial/README.md`.

## 7 CENTS (Meme Royale commercial) — render in progress (2026-11-09 15:23 UTC)

Code: `commercial/kid/` (director.py, kitchen.py, cast.py, screens.py [real shop screenshot shop_real.png from a throwaway
free account], audio.py, overlay.html/overlays.js, setup_worker.sh, render_part.sh, assemble.sh, kqa.py, vo/).
Scene: 924 frames (30.8 s), built to scratchpad/kd/k1.blend; mix scratchpad/kd/mix.m4a; overlays scratchpad/kd/ovl.
Rule: every long job runs as a tracked background task (CLAUDE.md); workers push commercial/renders/kpart_A_B.mp4.

| Machine | Frames | Pushes to |
|---|---|---|
| this session | 1-132 (scratchpad/kd/local.txt, tracked) | — |
| part 2  session_011y2L9gpQAxugSUWVRRHu2U | 133-264 | claude/degens-part-2 |
| part 2b session_011y2L9iQnevydUzK69bSkEC | 265-396 | claude/degens-part-2b |
| part 2c session_011y2L9hi1yPvG77Fmtky1C2 | 397-528 | claude/degens-part-2c |
| part 2d session_011y2L9hwrQnn4cYRc1wmzHW | 529-660 | claude/degens-part-2d |
| part 2e session_011y2L9eqzr9vpBoRgeJVmGr | 661-792 | claude/degens-part-2e |
| part 2f session_011y2L9drzqzTRCjM3pB3d7y | 793-924 | claude/degens-part-2f |

Finish: unpack each part with `scratchpad/kd/unpack.sh BRANCH kpart_A_B.mp4 A` (fills scratchpad/kd/frames); if a worker
stalls, render its frames locally from k1.blend (tracked). Then
`commercial/kid/assemble.sh scratchpad/kd/frames scratchpad/kd/ovl scratchpad/kd/mix.m4a commercial/output/meme-royale-7-cents.mp4`,
glitch scan `python3 scratchpad/spikes.py scratchpad/kd/frames`, send the MP4 to the user, commit and push.
The user wants a message only when the video is done. A fallback check is scheduled for 16:39 UTC.
Lesson from CASH 4 GOLD: volumetric smoke made frames ~20x slower; avoid long smoke in shot or spread those frames.

## NO UTILITY (USELESS tragedy short) — render state, started 2026-11-09 ~19:30 UTC
Code: commercial/useless (director.py, sets.py, game.py, overlay.html/overlays.js, audio.py, *.sh), commit 17e9ae8.
Native 1080x1920, 1080 frames (36 s) + 3 s end card held from the last frame. ~77 s/frame.
| Machine | Frames | Output |
|---|---|---|
| this session (task bta6heo9m, W=scratchpad/nu/lw) | 1-150 | frames in scratchpad/nu/lw/frames; then overlays -> scratchpad/nu/ovl, mix -> scratchpad/nu/mix.m4a |
| part-2 session_011y2L9gpQAxugSUWVRRHu2U | 151-305 | claude/degens-part-2 commercial/renders/upart_0151_0305.mp4 |
| part-2b session_011y2L9iQnevydUzK69bSkEC | 306-460 | claude/degens-part-2b upart_0306_0460.mp4 |
| part-2c session_011y2L9hi1yPvG77Fmtky1C2 | 461-615 | claude/degens-part-2c upart_0461_0615.mp4 |
| part-2d session_011y2L9hwrQnn4cYRc1wmzHW | 616-770 | claude/degens-part-2d upart_0616_0770.mp4 |
| part-2e session_011y2L9eqzr9vpBoRgeJVmGr | 771-925 | claude/degens-part-2e upart_0771_0925.mp4 |
| part-2f session_011y2L9drzqzTRCjM3pB3d7y | 926-1080 | claude/degens-part-2f upart_0926_1080.mp4 |
Finish: scratchpad/nu/unpack.sh BRANCH FILE FIRST for each part (fills scratchpad/nu/lw/frames); local exit 3 -> rerun the
same render command (W=scratchpad/nu/lw bash commercial/useless/render_part.sh 1 150 ...); when 1080 frames are in:
commercial/useless/assemble.sh scratchpad/nu/lw/frames scratchpad/nu/ovl scratchpad/nu/mix.m4a commercial/output/meme-royale-no-utility.mp4,
check stills, SendUserFile, commit + push to claude/meme-royale-research. User wants a message only when the video is done.
