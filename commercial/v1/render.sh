#!/usr/bin/env bash
# Rebuilds the MEME ROYALE commercial from scratch: scene -> frames -> soundtrack -> mp4.
#   BLENDER=/path/to/blender ./render.sh            # 1280x720, 12 samples (~12 s/frame on 4 CPU cores)
#   W=1920 H=1080 SAMPLES=32 ./render.sh             # full HD
set -euo pipefail
cd "$(dirname "$0")"
BLENDER=${BLENDER:-blender}
W=${W:-1280}; H=${H:-720}; SAMPLES=${SAMPLES:-12}
FRAMES=${FRAMES:-frames}
mkdir -p "$FRAMES" output

"$BLENDER" -b --factory-startup -P build_commercial.py -- \
  --w "$W" --h "$H" --samples "$SAMPLES" \
  --save meme_royale_commercial.blend \
  --render --out "$FRAMES/f_"

python3 make_audio.py soundtrack.wav

ffmpeg -y -framerate 30 -i "$FRAMES/f_%04d.png" -i soundtrack.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 192k -shortest output/meme_royale_commercial.mp4
echo "done: output/meme_royale_commercial.mp4"
