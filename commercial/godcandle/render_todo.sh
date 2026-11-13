#!/bin/bash
# Render only the frames listed in $W/todo_{room,space,arena}.txt (made by reuse_frames.py), then finish and encode.  Run as a tracked background task
# (run_in_background, timeout 7200000); exit 3 / "RELAUNCH" means run it again.
set -e
T0=$(date +%s); BUDGET=${RENDER_BUDGET:-6600}; HERE=$(cd $(dirname $0) && pwd); BL=/opt/blender/blender-4.2.3-linux-x64/blender; export W=${W:-$HOME/gc_work}; cd $HERE
for pair in "room room.blend" "space room.blend" "arena scene.blend"; do
  set -- $pair; L=$W/todo_$1.txt; [ -s $L ] || continue
  export RENDER_BUDGET=$((BUDGET - $(date +%s) + T0)); [ $RENDER_BUDGET -gt 120 ] || { echo "RELAUNCH: time budget used before $1"; exit 3; }
  rc=0; $BL -b $W/$2 -P render_edl.py -- $L >> $W/render_$1.log 2>&1 || rc=$?
  if [ $rc = 3 ]; then echo "RELAUNCH: time budget used in $1, $(grep -o 'BUDGET-STOP [0-9]*' $W/render_$1.log | tail -1) frames left"; exit 3; fi
  [ $rc = 0 ] || { echo "render of $1 failed ($rc)"; tail -20 $W/render_$1.log; exit $rc; }
done
N=$(python3 -c "import json;print(json.load(open('edl.json'))['last'])")
for f in $(seq 1 $N); do [ -f $W/frames/f_$(printf %04d $f).png ] || { echo "FRAME MISSING $f"; exit 1; }; done
rm -rf $W/fin; python3 finish.py $W/frames $W/fin > $W/finish.log 2>&1
O=$HERE/../output/meme-royale-god-candle.mp4
ffmpeg -v error -y -framerate 24 -i $W/fin/c_%04d.png -i $W/fin/mix.wav -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $O
ls -la $O; echo ALL-DONE
