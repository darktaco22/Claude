#!/bin/bash
# Final cut: unpack the six part videos, draw the 2D layer and the end card, mix the sound, encode 1080x1920.
# Usage: ./assemble.sh WORK_DIR OUT.mp4   (parts/part_*.mp4 must be present next to this script)
set -e
HERE=$(cd $(dirname $0) && pwd); W=$1; OUT=$2; BL=/opt/blender/blender-4.2.3-linux-x64/blender
mkdir -p $W/frames $W/comp
for p in $HERE/parts/part_*.mp4; do a=$(basename $p .mp4 | cut -d_ -f2); ffmpeg -v error -y -i $p -start_number $((10#$a)) $W/frames/f_%04d.png; done
[ -f $W/overlay.json ] || $BL -b --factory-startup -P $HERE/build.py -- --out $W/scene_chk.blend --overlay $W/overlay.json > $W/build.log 2>&1
python3 $HERE/overlay.py $W/frames $W/overlay.json $W/comp
ffmpeg -v error -y -framerate 30 -i $W/comp/c_%04d.png -i $W/comp/mix.wav -vf "scale=1080:1920:flags=lanczos" -c:v libx264 -preset slow -crf 17 \
  -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $OUT
ls -la $OUT
