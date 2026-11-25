#!/bin/bash
# After all frames exist in $W/frames2_<hash> (.png) or frames_jpg/<hash> (.jpg): finish, mix and encode THE MEMETRIX II.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); export W=${W:-$HOME/mx_work}; cd "$HERE"; EH=$(sha1sum edl.json | cut -c1-10); FR="$W/final2_$EH"; rm -rf "$FR"; mkdir -p "$FR"
cp frames_jpg/$EH/*.jpg "$FR/" 2>/dev/null || true; cp "$W/frames2_$EH"/*.png "$FR/" 2>/dev/null || true
read T0 N < <(python3 -c "import json;e=json.load(open('edl.json'));print(int(e['title']*e['fps'])+1, e['last'])")
for f in $(seq "$T0" "$N"); do p=$(printf %04d "$f"); [ -f "$FR/f_$p.png" ] || [ -f "$FR/f_$p.jpg" ] || { echo "FRAME MISSING $f"; exit 1; }; done
rm -rf "$W/fin2"; python3 finish.py "$FR" "$W/fin2" > "$W/finish2.log" 2>&1
O="$HERE/../output/meme-royale-memetrix-2-liquidation.mp4"
ffmpeg -v error -y -framerate 24 -i "$W/fin2/c_%04d.jpg" -i "$W/fin2/mix.wav" -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 \
  -c:v libx264 -preset slow -b:v 4500k -maxrate 7000k -bufsize 12000k -pix_fmt yuv420p -c:a aac -b:a 160k -shortest -movflags +faststart "$O"
ls -la "$O"; tail -6 "$W/finish2.log"; echo ALL-DONE
