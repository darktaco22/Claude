#!/bin/bash
# Fresh-machine setup for rendering NO UTILITY: Blender 4.2 (via the Degens setup if missing), the game's own assets and
# three Poly Haven (CC0) assets. Usage: W=~/nu_work ./setup_worker.sh   (run as a tracked background task, see CLAUDE.md)
set -e
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/nu_work}; mkdir -p $W/ph $W/tex
[ -x /opt/blender/blender-4.2.3-linux-x64/blender ] || W=$W bash $HERE/../degens/setup_remote.sh
bash $HERE/fetch_game.sh $W/game
cd $W && python3 $HERE/../degens/phget.py castle_wall_slates:tex cobblestone_floor_08:tex Lantern_01
echo NU-SETUP-DONE
