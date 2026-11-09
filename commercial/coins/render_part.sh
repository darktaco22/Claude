#!/bin/bash
# Render frames FIRST..LAST of "Wait... they're COINS?" and encode them as one near-lossless part video.
# Usage: ./render_part.sh FIRST LAST     (writes parts/part_FIRST_LAST.mp4 next to this script)
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never setsid/nohup/&.
# Stops before the 2 h cap (RENDER_BUDGET, default 6600 s) and exits 3 with "RELAUNCH"; then run it again.
set -e
export RENDER_BUDGET=${RENDER_BUDGET:-6600}
HERE=$(cd $(dirname $0) && pwd); DG=$HERE/../degens; BL=/opt/blender/blender-4.2.3-linux-x64/blender
export W=${W:-$HOME/gm_work}; export PH=$W/ph DA_TEX=$W/tex GM_SCREEN=$W/screen
mkdir -p $W/frames $HERE/parts
# Blender, MPFB 2 with the CC0 MakeHuman packs, Poly Haven props (idempotent), plus the bedroom pieces
[ -f $W/.setup_done ] || { bash $DG/setup_remote.sh > $W/setup.log 2>&1; (cd $W && python3 $DG/phget.py GothicBed_01 throw_pillows_01 desk_lamp_arm_01 Shelf_01 potted_plant_01 wooden_floor_02:tex beige_wall_001:tex && python3 $DG/phgltf.py throw_pillows_01 desk_lamp_arm_01) >> $W/setup.log 2>&1; touch $W/.setup_done; }
[ -f $GM_SCREEN/s_0880.png ] || { mkdir -p $GM_SCREEN; ffmpeg -v error -y -i $HERE/screen.mp4 -start_number 1 $GM_SCREEN/s_%04d.png; }
[ -f $W/scene.blend ] || { rm -f $W/part_*.txt.done; $BL -b -P $HERE/gamer.py -- --out $W/scene.blend --frames 880 > $W/build.log 2>&1; }
L=$W/part_$1_$2.txt; seq $1 $2 | tr '\n' ' ' > $L
[ -f $L.done ] && [ $W/scene.blend -nt $L.done ] && rm -f $L.done
rc=0; $BL -b $W/scene.blend -P $DG/render_list.py -- $L >> $W/render.log 2>&1 || rc=$?
if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render.log | tail -1) frames left"; exit 3; fi
[ $rc = 0 ] || { echo "render failed ($rc), see $W/render.log"; tail -20 $W/render.log; exit $rc; }
O=$HERE/parts/part_$(printf %04d $1)_$(printf %04d $2).mp4
ffmpeg -v error -y -start_number $1 -framerate 30 -i $W/frames/f_%04d.png -frames:v $(( $2 - $1 + 1 )) -c:v libx264 -preset slow -crf 10 -pix_fmt yuv444p $O
ls -la $O; echo PART-DONE $O
