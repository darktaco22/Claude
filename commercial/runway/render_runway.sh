#!/usr/bin/env bash
# The character runway, from the game's models to an mp4.
#   ./render_runway.sh                       # fetch models if missing, 1920x1080, 16 samples
#   STEP=3 W=960 H=540 SAMPLES=6 ./render_runway.sh    # quick preview (every 3rd frame, low res)
#   ORDER=giga,pepe,moodeng,popcat MUSIC=/path/mus_battle.mp3 ./render_runway.sh
# Env: BLENDER, MODELS, OUT, W, H, SAMPLES, FPS, STEP, ORDER, BGDIR, MUSIC, GPU=1, FIT=1
set -euo pipefail
cd "$(dirname "$0")"
BLENDER=${BLENDER:-blender}
MODELS=${MODELS:-models}; OUT=${OUT:-../output/meme-royale-runway.mp4}
W=${W:-1920}; H=${H:-1080}; SAMPLES=${SAMPLES:-16}; FPS=${FPS:-30}; STEP=${STEP:-1}
FRAMES=${FRAMES:-frames}

if ! ls "$MODELS"/*.gl* >/dev/null 2>&1; then
  python3 fetch_models.py --out "$MODELS"
fi
mkdir -p "$FRAMES" "$(dirname "$OUT")"

"$BLENDER" -b --factory-startup -P runway_showcase.py -- --models "$MODELS" \
  ${ORDER:+--order "$ORDER"} ${BGDIR:+--bgdir "$BGDIR"} ${GPU:+--gpu} ${FIT:+--fit} \
  --w "$W" --h "$H" --samples "$SAMPLES" --fps "$FPS" --step "$STEP" \
  --save runway.blend --render "$FRAMES"

TMP="$(dirname "$OUT")/.runway_video.mp4"
ffmpeg -y -framerate "$FPS/$STEP" -pattern_type glob -i "$FRAMES/f_*.png" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart "$TMP"
if [ -n "${MUSIC:-}" ]; then
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP")
  FADE=$(python3 -c "print(max(0.0, $DUR - 1.5))")
  ffmpeg -y -i "$TMP" -i "$MUSIC" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
    -af "afade=t=in:d=0.4,afade=t=out:st=$FADE:d=1.5,loudnorm=I=-14:TP=-1.5" -shortest -movflags +faststart "$OUT"
  rm -f "$TMP"
else
  mv "$TMP" "$OUT"
fi
echo "done: $OUT"
