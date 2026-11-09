#!/bin/bash
# Fresh-machine setup: Blender 4.2 and its system libraries. Idempotent.
set -e
if [ ! -x /opt/blender/blender-4.2.3-linux-x64/blender ]; then
  mkdir -p /opt/blender && cd /opt/blender && curl -sSfLO https://download.blender.org/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz \
    && tar xf blender-4.2.3-linux-x64.tar.xz && rm blender-4.2.3-linux-x64.tar.xz
fi
L="libegl1 libgl1 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6"
apt-get install -y -q $L >/dev/null 2>&1 || (apt-get update -q >/dev/null && apt-get install -y -q $L >/dev/null)
which ffmpeg >/dev/null || apt-get install -y -q ffmpeg >/dev/null
/opt/blender/blender-4.2.3-linux-x64/blender -b --version | head -1
echo SETUP-DONE
