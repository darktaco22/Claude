#!/bin/bash
# Prepare a machine to build and render THE MEMETRIX from the repo alone. Idempotent.
#   W (work folder, default ~/mx_work).  Leaves: Blender 4.2.3, $W/chars.blend, $W/scene.blend (about 1 min)
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export W=${W:-$HOME/mx_work}; mkdir -p "$W"
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
if [ ! -x "$BL" ]; then
  mkdir -p /opt/blender && (cd /opt/blender && curl -sSL -o b.tar.xz https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf b.tar.xz && rm b.tar.xz)
fi
python3 -c "import PIL, numpy, soundfile" 2>/dev/null || pip install -q pillow numpy soundfile
cd "$HERE"
for a in exchange basement metaverse; do ln -sfn ../../arena "pack/arenas/$a/arena"; done
[ -f "$W/chars.blend" ] || "$BL" -b -P ../tools/assets.py -- build ../comeback/models ../noobpro/models/units.json "$W/chars.blend" > "$W/chars.log" 2>&1
if [ ! -f "$W/scene.blend" ] || [ scene.py -nt "$W/scene.blend" ] || [ mxsets.py -nt "$W/scene.blend" ] || [ edl.json -nt "$W/scene.blend" ]; then
  cp edl.json "$W/edl_repo.json"
  "$BL" -b --factory-startup -P scene.py -- --out "$W/scene.blend" --lib "$W/chars.blend" > "$W/build.log" 2>&1
  grep -q SAVED "$W/build.log" || { echo "build failed"; tail -20 "$W/build.log"; exit 1; }
  cmp -s edl.json "$W/edl_repo.json" || { cp "$W/edl_repo.json" edl.json; echo "ERROR: the edit rebuilt here differs from the committed edl.json (stale checkout? git pull). Not rendering."; exit 1; }
fi
echo SETUP-OK
