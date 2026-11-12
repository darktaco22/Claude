#!/bin/bash
# GOD CANDLE: build (if needed), render every film frame, finish, encode.   Usage: ./render_all.sh
# Launch as a TRACKED background task (Bash run_in_background, timeout 7200000), never setsid/nohup/&.
# It stops before the 2 h cap (RENDER_BUDGET, default 6300 s) and exits 3 with "RELAUNCH": run the same command again; finished frames are kept.
set -e
T0=$(date +%s); BUDGET=${RENDER_BUDGET:-6300}
HERE=$(cd $(dirname $0) && pwd); BL=/opt/blender/blender-4.2.3-linux-x64/blender; export W=${W:-$HOME/gc_work}; mkdir -p $W/frames $W/ui
RB=${ROCKETBOX:-/home/user/microsoft/microsoft-rocketbox}
[ -x $BL ] || bash $HERE/../noobpro/setup.sh > $W/setup.log 2>&1
python3 -c "import numpy, PIL, soundfile" 2>/dev/null || pip install -q numpy pillow soundfile
if [ ! -f $RB/Assets/Avatars/Adults/Male_Adult_18/Export/Male_Adult_18.fbx ]; then      # the trader (Microsoft Rocketbox, MIT)
  mkdir -p $(dirname $RB); GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/microsoft-rocketbox $RB
  git -C $RB sparse-checkout set --no-cone '/Assets/Avatars/Adults/Male_Adult_18/'
fi
cd $HERE
[ -f $W/ui/u_0001.png ] || { python3 ui.py $W/ui > $W/ui.log; python3 ui.py $W/ui monitors; }
[ -f $W/room.blend ] || { rm -f $W/full_*.txt.done; $BL -b --factory-startup -P scene.py -- --out $W/room.blend --ui $W/ui --room > $W/build_room.log 2>&1; }
[ -f $W/scene.blend ] || { rm -f $W/full_*.txt.done; $BL -b --factory-startup -P scene.py -- --out $W/scene.blend --ui $W/ui > $W/build.log 2>&1; }
read N RL < <(python3 -c "import json;e=json.load(open('edl.json'));print(e['last'], round(e['shots'][4]['t1']*e['fps']))")      # the first five shots are in the room
seq 1 $RL | tr '\n' ' ' > $W/full_room.txt; seq $((RL + 1)) $N | tr '\n' ' ' > $W/full_arena.txt
for part in room arena; do
  B=$W/room.blend; [ $part = arena ] && B=$W/scene.blend; L=$W/full_$part.txt
  [ -f $L.done ] && [ $B -nt $L.done ] && rm -f $L.done
  export RENDER_BUDGET=$((BUDGET - $(date +%s) + T0)); [ $RENDER_BUDGET -gt 120 ] || { echo "RELAUNCH: time budget used before $part"; exit 3; }
  rc=0; $BL -b $B -P render_edl.py -- $L >> $W/render_$part.log 2>&1 || rc=$?
  if [ $rc = 3 ]; then echo "RELAUNCH: time budget used, $(grep -o 'BUDGET-STOP [0-9]*' $W/render_$part.log | tail -1) frames left in $part"; exit 3; fi
  [ $rc = 0 ] || { echo "render failed ($rc), see $W/render_$part.log"; tail -20 $W/render_$part.log; exit $rc; }
done
[ "$(ls $W/frames/f_*.png | wc -l)" -ge $N ] || { echo "FRAMES MISSING"; exit 1; }
python3 finish.py $W/frames $W/fin > $W/finish.log 2>&1
O=$HERE/../output/meme-royale-god-candle.mp4
NF=$(ls $W/fin/c_*.png | wc -l)
ffmpeg -v error -y -framerate 24 -i $W/fin/c_%04d.png -i $W/fin/mix.wav -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $O
ls -la $O; echo ALL-DONE $NF frames
