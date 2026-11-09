#!/bin/bash
# Render frames FIRST..LAST of NOOB vs PRO and encode them as one near-lossless part video.
# Usage: [BUILD=build_splash.py PARTS=parts_splash] ./render_part.sh FIRST LAST   (writes $PARTS/part_FIRST_LAST.mp4)
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never setsid/nohup/&.
# Stops before the 2 h cap (RENDER_BUDGET, default 6600 s) and exits 3 with "RELAUNCH"; then run it again.
set -e
export RENDER_BUDGET=${RENDER_BUDGET:-6600}
HERE=$(cd $(dirname $0) && pwd); BL=/opt/blender/blender-4.2.3-linux-x64/blender
BUILD=${BUILD:-build.py}; PARTS=${PARTS:-parts}
export W=${W:-$HOME/np_work_${BUILD%.py}}; mkdir -p $W/frames $HERE/$PARTS
[ -x $BL ] || bash $HERE/setup.sh
[ -f $W/scene.blend ] || { rm -f $W/part_*.txt.done; $BL -b --factory-startup -P $HERE/$BUILD -- --out $W/scene.blend > $W/build.log 2>&1; }
L=$W/part_$1_$2.txt; seq $1 $2 | tr '\n' ' ' > $L
[ -f $L.done ] && [ $W/scene.blend -nt $L.done ] && rm -f $L.done
rc=0; $BL -b $W/scene.blend -P $HERE/render_list.py -- $L >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc), see $W/render.log"; tail -20 $W/render.log; exit $rc; }
O=$HERE/$PARTS/part_$(printf %04d $1)_$(printf %04d $2).mp4
ffmpeg -v error -y -start_number $1 -framerate 30 -i $W/frames/f_%04d.png -frames:v $(( $2 - $1 + 1 )) -c:v libx264 -preset slow -crf 10 -pix_fmt yuv444p $O
ls -la $O; echo PART-DONE $O
