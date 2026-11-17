#!/bin/bash
# THE REAPING (Blender) fresh-machine setup: Blender 4.2 LTS, the game's character models, Poly Haven assets (CC0),
# the MEME MALL HDRI patch, and the set textures. Idempotent. Usage: A=/root/reap3d bash setup_worker.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd); A=${A:-/root/reap3d}; mkdir -p $A/units $A/ph $A/tex
BL=/opt/blender/blender-4.2.3-linux-x64/blender
if [ ! -x $BL ]; then
  mkdir -p /opt/blender && cd /opt/blender && curl -sSfLO https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf blender-4.2.3-linux-x64.tar.xz && rm blender-4.2.3-linux-x64.tar.xz
fi
(apt-get install -y -q libegl1 libgl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 >/dev/null 2>&1 || (apt-get update -q >/dev/null && apt-get install -y -q libegl1 libgl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 >/dev/null)) || true
cd $A/units
for u in whale wojak pepe giga bonk troll chillguy popcat goat floki cate toshi pnut walter slerf nyancat swordcat; do
  [ -s $u.glb ] || curl -sSfL -A 'reaping-scene-builder/1.0' -o $u.glb https://memeroyale.imaginestudio.fun/assets/units/$u.glb || echo "miss $u"; done
cd $A
python3 - <<'PY'
import json, os, urllib.request
UA = {'User-Agent': 'reaping-scene-builder/1.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=300).read()
for a, res in [('mall_parking_lot', '16k'), ('shanghai_bund', '8k'), ('fireplace', '4k')]:
    p = f'ph/{a}_{res}.hdr'
    if not os.path.exists(p) or os.path.getsize(p) < 1e6:
        open(p + '.part', 'wb').write(get(json.loads(get(f'https://api.polyhaven.com/files/{a}'))['hdri'][res]['hdr']['url'])); os.replace(p + '.part', p); print('hdri', p)
PY
python3 $HERE/phfetch.py flood_lights street_lamp_01 concrete_road_barrier WetFloorSign_01 security_camera_01 metal_trash_can fire_hydrant modern_arm_chair_01 sofa_03 modern_coffee_table_01 potted_plant_02 pachira_aquatica_01 calathea_orbifolia_01 ArmChair_01 side_table_01 | tr '\n' ' '
python3 $HERE/phfetch.py asphalt_02:tex dark_wooden_planks:tex marble_01:tex | tr '\n' ' '; echo
cp -n $HERE/tex/* $A/tex/
[ -s $A/ph/mall_meme_16k.hdr ] || $BL -b --factory-startup -P $HERE/sign_fix.py -- $A 2>&1 | grep -E "SIGN|Error" || true
ls -la $A/ph/mall_meme_16k.hdr && echo REAPING-SETUP-DONE
