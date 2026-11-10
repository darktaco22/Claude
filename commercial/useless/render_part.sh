#!/bin/bash
# Render frames FIRST..LAST of NO UTILITY and encode them for transfer.
# Usage: W=~/nu_work ./render_part.sh FIRST LAST OUT.mp4
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never with setsid/nohup.
# It stops itself before the 2 h cap (RENDER_BUDGET, default 6600 s) and exits 3 ("RELAUNCH") with frames left:
# then run the same command again. Finished frames are never re-rendered.
set -e
export RENDER_BUDGET=${RENDER_BUDGET:-6600}
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/nu_work}; export PH=$W/ph DA_TEX=$W/tex GAME=$W/game
BL=/opt/blender/blender-4.2.3-linux-x64/blender
cd $HERE/../degens; mkdir -p $W/frames
[ -f $W/scene.blend ] || { rm -f $W/part_*.txt.done; $BL -b -P $HERE/director.py -- --out $W/scene.blend --res 1080 > $W/build.log 2>&1; }
L=$W/part_$1_$2.txt; seq $1 $2 | tr '\n' ' ' > $L
[ -f $L.done ] && [ $W/scene.blend -nt $L.done ] && rm -f $L.done
# KEEP="1-330 961-1080": frames already in $W/frames inside these ranges are taken as finished (a scene change that left them alone)
if [ -n "$KEEP" ] && [ ! -f $L.done ]; then
  for f in $(seq $1 $2); do for r in $KEEP; do
    [ $f -ge ${r%-*} ] && [ $f -le ${r#*-} ] && [ -s $W/frames/$(printf 'f_%04d.png' $f) ] && printf '%s ' $f >> $L.done
  done; done
fi
rc=0; $BL -b $W/scene.blend -P render_list.py -- $L >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc), see $W/render.log"; exit $rc; }
ffmpeg -v error -y -start_number $1 -framerate 30 -i $W/frames/f_%04d.png -frames:v $(( $2 - $1 + 1 )) -c:v libx264 -preset slow -crf 10 -pix_fmt yuv444p $3
ls -la $3
