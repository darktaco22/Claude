#!/bin/bash
# Prepare a machine to build and render DEPLOYED from the repo alone. Idempotent.
#   W (work folder, default ~/dep_work).  Leaves: Blender 4.2.3, $W/chars.blend, $W/assets (sky + grass), $W/scene.blend
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export W=${W:-$HOME/dep_work}; mkdir -p "$W/assets"
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
if [ ! -x "$BL" ]; then
  mkdir -p /opt/blender && (cd /opt/blender && curl -sSL -o b.tar.xz https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf b.tar.xz && rm b.tar.xz)
fi
python3 -c "import PIL, numpy, soundfile" 2>/dev/null || pip install -q pillow numpy soundfile
cd "$HERE"
[ -f "$W/chars.blend" ] || "$BL" -b -P ../tools/assets.py -- build ../comeback/models ../noobpro/models/units.json "$W/chars.blend" > "$W/chars.log" 2>&1
[ -f "$W/assets/kloppenheim_06_puresky/kloppenheim_06_puresky_2k.exr" ] || python3 ../tools/polyhaven.py "$W/assets" hdri kloppenheim_06_puresky 2k
[ -d "$W/assets/grass_bermuda_01" ] || python3 ../tools/polyhaven.py "$W/assets" model grass_bermuda_01 1k
if [ ! -f "$W/scene.blend" ] || [ scene.py -nt "$W/scene.blend" ] || [ sets.py -nt "$W/scene.blend" ]; then
  cp edl.json "$W/edl_repo.json"
  "$BL" -b --factory-startup -P scene.py -- --out "$W/scene.blend" --lib "$W/chars.blend" --assets "$W/assets" > "$W/build.log" 2>&1
  grep -q BUILT "$W/build.log" || { echo "build failed"; tail -20 "$W/build.log"; exit 1; }
  cmp -s edl.json "$W/edl_repo.json" || echo "WARNING: rebuilt edl.json differs from the repo's"
fi
echo SETUP-OK
