#!/bin/bash
# Fresh-machine setup for rendering LAST WILL & TESTAMENT: the Degens setup (Blender 4.2, MPFB, CC0 MakeHuman
# packs) plus this skit's Poly Haven assets and the Whale (the game's own model). Usage: W=~/wh_work ./setup_worker.sh
# Run it as a tracked background task (see CLAUDE.md), never detached.
set -e
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/wh_work}; mkdir -p $W/tex $W/ph
W=$W bash $HERE/../degens/setup_remote.sh
cd $W
python3 $HERE/../degens/phget.py GothicBed_01 ClassicNightstand_01 ArmChair_01 ornate_mirror_01 fancy_picture_frame_01 potted_plant_01 GothicCabinet_01 \
  herringbone_parquet:tex dark_paneled_wood:tex quatrefoil_jacquard_fabric:tex velour_velvet:tex
python3 $HERE/../degens/phgltf.py vintage_grandfather_clock_01 fancy_picture_frame_01 potted_plant_01 GothicCabinet_01 || true
[ -s $W/whale.glb ] || curl -sSfL -A 'scene-builder/1.0' -o $W/whale.glb https://memeroyale.imaginestudio.fun/assets/units/whale.glb
ls /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf >/dev/null || (apt-get install -y -q fonts-dejavu-core >/dev/null)
echo WHALE-SETUP-DONE
