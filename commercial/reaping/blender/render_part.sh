#!/bin/bash
# Render a frame range of one Blender scene, encode it, commit + push it. Resumable (existing frames are skipped).
# Usage: bash render_part.sh SCENE A B      (SCENE = lot | studio | mentor)
# Launch as a tracked background task (run_in_background, timeout 7200000); on exit 3 run it again.
set -u
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(git -C "$HERE" rev-parse --show-toplevel); SC=$1; FA=$2; FB=$3
A=${A:-/root/reap3d}; OUT=$A/frames/$SC; mkdir -p $OUT
BL=/opt/blender/blender-4.2.3-linux-x64/blender
[ -s $A/ph/mall_meme_16k.hdr ] || A=$A bash $HERE/setup_worker.sh
need=0; for f in $(seq $FA $FB); do [ -s $OUT/f_$(printf %04d $f).png ] || need=1; done
if [ $need = 1 ]; then
  timeout ${RENDER_BUDGET:-6600} $BL -b --factory-startup -P $HERE/$SC.py -- --assets $A --w 864 --h 1536 --samples 24 --range $FA-$FB --out $OUT > $A/render_$SC.log 2>&1
  for f in $(seq $FA $FB); do [ -s $OUT/f_$(printf %04d $f).png ] || { echo "RELAUNCH: frame $f missing"; exit 3; }; done
fi
P=$REPO/commercial/reaping/renders; mkdir -p $P; NAME=${SC}_$(printf %04d $FA)_$(printf %04d $FB).mp4
ffmpeg -v error -y -framerate 30 -start_number $FA -i $OUT/f_%04d.png -frames:v $((FB - FA + 1)) -c:v libx264 -crf 12 -preset slow -pix_fmt yuv420p $P/$NAME
cd $REPO && git add commercial/reaping/renders/$NAME && git commit -q -m "THE REAPING render: $NAME" || true
for t in 1 2 3 4 5; do git pull -q --rebase origin claude/last-line-final && git push -q origin HEAD:claude/last-line-final && break; sleep $((t * 5)); done
echo "PART-DONE $NAME"
