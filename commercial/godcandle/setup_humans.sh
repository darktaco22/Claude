#!/bin/bash
# MPFB 2 (MakeHuman for Blender) and the CC0 MakeHuman asset packs the trader needs.  Run as a TRACKED background task.
set -e
BL=/opt/blender/blender-4.2.3-linux-x64/blender; PY=$(ls /opt/blender/blender-4.2.3-linux-x64/4.2/python/bin/python3.1*)
$PY -m pip install -q pillow scipy
if [ ! -d ~/.config/blender/4.2/extensions/user_default/mpfb ]; then
  curl -sSfL -A 'scene-builder/1.0' -o /tmp/mpfb.zip 'https://extensions.blender.org/download/sha256:c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad/add-on-mpfb-v2.0.18.zip'
  $BL -b --factory-startup --command extension install-file -r user_default -e /tmp/mpfb.zip
fi
U=~/.config/blender/4.2/extensions/.user/user_default/mpfb/data; mkdir -p $U $HOME/gc_work/mhzip
if [ ! -d $U/skins ]; then
  cd $HOME/gc_work/mhzip
  for p in makehuman_system_assets skins01 skins02 hair01 shirts01 pants01 dress01 shoes01 eyebrows01 eyelashes01 suits01 glasses01 system_hair_materials01; do
    curl -sSfL -A 'scene-builder/1.0' -O https://files.makehumancommunity.org/asset_packs/$p/${p}_cc0.zip; done
  curl -sSfL -A 'scene-builder/1.0' -O https://files.makehumancommunity.org/functional/visemes01.zip
  for z in *.zip; do unzip -q -o $z -d $U; done
fi
echo HUMANS-SETUP-DONE
