#!/bin/bash
# Fresh-machine setup for rendering 7 CENTS: the Degens setup (Blender 4.2, MPFB, CC0 MakeHuman
# packs) plus this skit's Poly Haven assets and the Whale (the game's own model). Usage: W=~/kd_work ./setup_worker.sh
# Run it as a tracked background task (see CLAUDE.md), never detached.
set -e
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/kd_work}; mkdir -p $W/tex
# reuse an earlier Degens setup's Poly Haven downloads; never its scene or frames (this job has its own folder)
[ -d $HOME/da_work/ph ] && [ ! -e $W/ph ] && ln -s $HOME/da_work/ph $W/ph; mkdir -p $W/ph
if [ -x /opt/blender/blender-4.2.3-linux-x64/blender ] && [ -d ~/.config/blender/4.2/extensions/.user/user_default/mpfb/data/skins ]; then
  echo "Blender and MPFB already set up"
else
  W=$W bash $HERE/../degens/setup_remote.sh
fi
cd $W
python3 $HERE/../degens/phget.py electric_stove vintage_microwave vintage_electric_kettle bananas food_apple_01 wooden_bowl_01 wall_clock potted_plant_02 Television_01 wood_floor:tex white_plaster_02:tex marble_01:tex

python3 $HERE/../degens/phgltf.py electric_stove vintage_microwave vintage_electric_kettle bananas food_apple_01 wooden_bowl_01 wall_clock potted_plant_02 Television_01 || true
bash $HERE/../pawn/screens.sh $W; python3 $HERE/screens.py $W

ls /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf >/dev/null || (apt-get install -y -q fonts-dejavu-core >/dev/null)
echo KID-SETUP-DONE
