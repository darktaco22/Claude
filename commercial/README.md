# MEME ROYALE: 20-second commercial (Blender)

A 20-second 3D commercial for **[memeroyale.imaginestudio.fun](https://memeroyale.imaginestudio.fun)**,
*"Bulls vs Bears: real-time meme card battles."*

- **Video:** `output/meme_royale_commercial.mp4` (1280×720, 30 fps, H.264 + AAC)
- **Blender scene:** `meme_royale_commercial.blend` (Blender 4.2 LTS, Cycles)
- **Source:** `build_commercial.py` builds the whole scene in code: models, materials, animation, cameras and titles.
  `make_audio.py` synthesizes the music and sound effects, timed to the same frames.

## Storyboard

| Time | Frames | Shot | On screen |
|---|---|---|---|
| 0:00–0:03 | 1–90 | **Face-off.** The green Bull and the red Bear drop into the arena. | BULLS · VS · BEARS |
| 0:03–0:07 | 91–210 | **The cards.** PUMP IT, RUG PULL, GOD CANDLE and FUD fly in as a hand; the legendary God Candle card spins forward on a gold sunburst. | COLLECT 74 MEME CARDS · LEGENDARY! |
| 0:07–0:12 | 211–360 | **The battle.** The Bull gallops down the lane and knocks over a Bear tower. Coins burst out, a candle chart pumps behind the arena and a giant gold God Candle shoots up. | REAL-TIME MEME CARD BATTLES · +1,000,000 CLOUT · GOD CANDLE! |
| 0:12–0:15 | 361–450 | **The twist.** The Bear yanks the rug and the Bull flips onto its head. The music cuts out, then the Bull springs back twice its size and the Bear runs off. | RUG PULL! … PUMP IT! |
| 0:15–0:20 | 451–600 | **End card.** The official logo slams in over the game's key art while gold coins rain down. | PLAY FREE NOW · memeroyale.imaginestudio.fun |

The look follows the site: its royal purple (`#2A1070`) and gold palette, its Lilita One display font, its logo and title art
(downloaded from the site into `assets/`), and card names, rarities and the card count (74) from the game's own `data.js`.
The Bull, the Bear, the arena and the cards are original models built from primitives in the script.

## Rebuild / re-render

Needs Blender 4.2+, Python 3 with numpy, and ffmpeg.

```bash
BLENDER=/path/to/blender ./render.sh                 # 720p, about 12 s/frame on 4 CPU cores
W=1920 H=1080 SAMPLES=32 BLENDER=... ./render.sh     # full HD, slower
```

Quick preview stills (half resolution, low samples):

```bash
blender -b --factory-startup -P build_commercial.py -- --preview --stills 80,195,330,440,590 stills/
```

Open `meme_royale_commercial.blend` to tweak it by hand. Each shot has its own camera, and timeline markers S1–S5 switch between them.
