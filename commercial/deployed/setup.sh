#!/bin/bash
# Prepare a machine to build and render DEPLOYED from the repo alone. Idempotent.
#   W (work folder, default ~/dep_work).  Leaves: Blender 4.2.3, $W/chars.blend, $W/assets (sky), $W/scene.blend (about 3 min)
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export W=${W:-$HOME/dep_work}; mkdir -p "$W/assets"
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
if [ ! -x "$BL" ]; then
  mkdir -p /opt/blender && (cd /opt/blender && curl -sSL -o b.tar.xz https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf b.tar.xz && rm b.tar.xz)
fi
python3 -c "import PIL, numpy, soundfile" 2>/dev/null || pip install -q pillow numpy soundfile
BP=$(dirname "$BL")/4.2/python/bin/python3.11
"$BP" -c "import PIL, numpy" 2>/dev/null || { "$BP" -m ensurepip >/dev/null 2>&1 || true; "$BP" -m pip install -q pillow numpy; }
cd "$HERE"
[ -f "$W/chars.blend" ] || "$BL" -b -P ../tools/assets.py -- build ../comeback/models ../noobpro/models/units.json "$W/chars.blend" > "$W/chars.log" 2>&1
[ -f "$W/assets/kloppenheim_06_puresky/kloppenheim_06_puresky_2k.exr" ] || python3 ../tools/polyhaven.py "$W/assets" hdri kloppenheim_06_puresky 2k
if [ ! -f "$W/scene.blend" ] || [ scene.py -nt "$W/scene.blend" ] || [ sets.py -nt "$W/scene.blend" ]; then
  cp edl.json "$W/edl_repo.json"
  "$BL" -b --factory-startup -P scene.py -- --out "$W/scene.blend" --pack "$HERE/pack" --lib "$W/chars.blend" --assets "$W/assets" --mon "$HERE/pack/monitor.mp4" > "$W/build.log" 2>&1
  grep -q BUILT "$W/build.log" || { echo "build failed"; tail -20 "$W/build.log"; exit 1; }
  cmp -s edl.json "$W/edl_repo.json" || { echo "ERROR: the edit rebuilt on this machine differs from the committed edl.json (stale checkout? git pull). Not rendering."; exit 1; }
fi
echo SETUP-OK
