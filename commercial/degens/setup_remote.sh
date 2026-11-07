#!/bin/bash
# Fresh-machine setup for rendering the Degens remake: Blender 4.2, MPFB + CC0 MakeHuman assets,
# Poly Haven assets. Usage: W=~/da_work ./setup_remote.sh
set -e
HERE=$(cd $(dirname $0) && pwd)
export W=${W:-$HOME/da_work}; mkdir -p $W/tex $W/ph $W/mhzip
if [ ! -x /opt/blender/blender-4.2.3-linux-x64/blender ]; then
  mkdir -p /opt/blender && cd /opt/blender && curl -sSfLO https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf blender-4.2.3-linux-x64.tar.xz && rm blender-4.2.3-linux-x64.tar.xz
fi
(apt-get install -y -q libegl1 libgl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 >/dev/null 2>&1 || (apt-get update -q >/dev/null && apt-get install -y -q libegl1 libgl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 >/dev/null))
BL=/opt/blender/blender-4.2.3-linux-x64/blender; PY=$(ls /opt/blender/blender-4.2.3-linux-x64/4.2/python/bin/python3.1*)
$PY -m pip install -q pillow scipy
if [ ! -d ~/.config/blender/4.2/extensions/user_default/mpfb ]; then
  curl -sSfL -A 'scene-builder/1.0' -o /tmp/mpfb.zip 'https://extensions.blender.org/download/sha256:c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad/add-on-mpfb-v2.0.18.zip'
  $BL -b --factory-startup --command extension install-file -r user_default -e /tmp/mpfb.zip
fi
U=~/.config/blender/4.2/extensions/.user/user_default/mpfb/data; mkdir -p $U
if [ ! -d $U/skins ]; then
  cd $W/mhzip
  for p in makehuman_system_assets skins01 skins02 hair01 shirts01 pants01 dress01 shoes01 eyebrows01 eyelashes01 suits01 glasses01 system_hair_materials01; do
    curl -sSfL -A 'scene-builder/1.0' -O https://files.makehumancommunity.org/asset_packs/$p/${p}_cc0.zip; done
  curl -sSfL -A 'scene-builder/1.0' -O https://files.makehumancommunity.org/functional/visemes01.zip
  for z in *.zip; do unzip -q -o $z -d $U; done
fi
cd $W
python3 $HERE/phget.py SchoolChair_01 WoodenChair_01 hanging_picture_frame_02 korean_fire_extinguisher_01 potted_plant_02 \
  concrete_block_wall:tex concrete_block_wall_02:tex old_linoleum_flooring_01:tex worn_tile_floor:tex ceiling_interior:tex dark_brick_wall:tex asphalt_02:tex rusty_painted_metal:tex painted_plaster_wall:tex cobblestone_street_night:hdri
python3 $HERE/phgltf.py cardboard_box_01 cigarette_pack croissant fire_alarm folding_wooden_stool jug_01 metal_office_desk metal_stool_01 metal_trash_can modified_thermos \
  mounted_fluorescent_lights painted_wooden_stool plastic_monobloc_chair_01 plastic_thermos standing_chalkboard_01 vintage_lighter wall_clock wine_bottles_01 wooden_stool_01
echo SETUP-DONE
