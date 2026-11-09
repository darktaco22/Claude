#!/bin/bash
# Fresh-machine setup for rendering CASH 4 GOLD: the Degens setup (Blender 4.2, MPFB, CC0 MakeHuman
# packs) plus this skit's Poly Haven assets and the Whale (the game's own model). Usage: W=~/pw_work ./setup_worker.sh
# Run it as a tracked background task (see CLAUDE.md), never detached.
set -e
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/pw_work}; mkdir -p $W/tex
# reuse an earlier Degens setup's Poly Haven downloads; never its scene or frames (this job has its own folder)
[ -d $HOME/da_work/ph ] && [ ! -e $W/ph ] && ln -s $HOME/da_work/ph $W/ph; mkdir -p $W/ph
if [ -x /opt/blender/blender-4.2.3-linux-x64/blender ] && [ -d ~/.config/blender/4.2/extensions/.user/user_default/mpfb/data/skins ]; then
  echo "Blender and MPFB already set up"
else
  W=$W bash $HERE/../degens/setup_remote.sh
fi
cd $W
python3 $HERE/../degens/phget.py steel_frame_shelves_01 portable_cassette_player brass_vase_01 desk_lamp_arm_01 binder_notebook old_linoleum_flooring_01:tex painted_plaster_wall:tex ceiling_interior:tex asphalt_02:tex

python3 $HERE/../degens/phgltf.py steel_frame_shelves_01 portable_cassette_player brass_vase_01 desk_lamp_arm_01 binder_notebook cardboard_box_01 wine_bottles_01 mounted_fluorescent_lights metal_trash_can || true
for u in useless slerf; do [ -s $W/$u.glb ] || curl -sSfL -A 'scene-builder/1.0' -o $W/$u.glb https://memeroyale.imaginestudio.fun/assets/units/$u.glb; done
bash $HERE/screens.sh $W
ls /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf >/dev/null || (apt-get install -y -q fonts-dejavu-core >/dev/null)
echo PAWN-SETUP-DONE
