#!/bin/bash
# Prepare a machine to build and render THE MEMETRIX II from the repo alone. Idempotent.
#   W (work folder, default ~/mx_work).  Leaves: Blender 4.2.3, $W/chars.blend, $W/fire_sims, $W/scene2.blend (~20 min first time)
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export W=${W:-$HOME/mx_work}; mkdir -p "$W"
BL=${BL:-/opt/blender/blender-4.2.3-linux-x64/blender}
if [ ! -x "$BL" ]; then
  mkdir -p /opt/blender && (cd /opt/blender && curl -sSL -o b.tar.xz https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz && tar xf b.tar.xz && rm b.tar.xz)
fi
python3 -c "import PIL, numpy, soundfile" 2>/dev/null || pip install -q pillow numpy soundfile
EP1="$HERE/../memetrix"
for a in exchange basement metaverse; do ln -sfn ../../arena "$EP1/pack/arenas/$a/arena"; done   # episode 1's sets are reused
cd "$HERE"
[ -f "$W/chars.blend" ] || "$BL" -b -P ../tools/assets.py -- build ../comeback/models ../noobpro/models/units.json "$W/chars.blend" > "$W/chars.log" 2>&1
# the café's simulated fires (firesims.py): seven fuels, baked once per machine (about 15 min, 1.7 GB; deterministic)
for n in table booth grease paper sheet debris machine; do
  [ -f "$W/fire_sims/$n/DONE.json" ] || "$BL" -b --factory-startup -P firesims.py -- "$W/fire_sims" $n > "$W/firesims_$n.log" 2>&1
  [ -f "$W/fire_sims/$n/DONE.json" ] || { echo "fire bake failed: $n"; tail -5 "$W/firesims_$n.log"; exit 1; }
done
B="$W/scene2.blend"
if [ ! -f "$B" ] || [ scene2.py -nt "$B" ] || [ sets2.py -nt "$B" ] || [ edl.json -nt "$B" ] || [ ../memetrix/mxsets.py -nt "$B" ] || [ ../tools/cine.py -nt "$B" ]; then
  cp edl.json "$W/edl2_repo.json"
  touch "$W/build2.start"
  # (unbuffered, so nothing is lost if it is stopped; Blender sometimes hangs inside its save after the file is written,
  # so the build has a time limit and a file written after the start counts: Blender writes to a temporary name and
  # renames it at the end, so a newer scene2.blend is a complete one)
  PYTHONUNBUFFERED=1 timeout 1800 "$BL" -b --factory-startup -P scene2.py -- --out "$B" --lib "$W/chars.blend" > "$W/build2.log" 2>&1
  if ! grep -q SAVED "$W/build2.log"; then
    if grep -q "^EDL " "$W/build2.log" && grep -q "SAVING" "$W/build2.log" && [ "$B" -nt "$W/build2.start" ]; then
      echo "build: Blender hung after writing the scene (known); the written file is complete, carrying on"
    else
      echo "build failed"; tail -20 "$W/build2.log"; exit 1
    fi
  fi
  cmp -s edl.json "$W/edl2_repo.json" || { cp "$W/edl2_repo.json" edl.json; echo "ERROR: the edit rebuilt here differs from the committed edl.json (stale checkout? git pull). Not rendering."; exit 1; }
fi
echo SETUP-OK
