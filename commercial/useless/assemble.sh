#!/bin/bash
# assemble.sh FRAMES OVERLAYS AUDIO OUT.mp4: native 1080x1920 Cycles frames, the last frame held under the end card,
# the HTML overlays on top, a touch of film grain, and the mix.
set -e
F=$1; O=$2; A=$3; OUT=$4; DUR=39.0
ffmpeg -v error -y -framerate 30 -i "$F/f_%04d.png" -framerate 30 -i "$O/o_%04d.png" -i "$A" \
  -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=3,noise=alls=3:allf=t,format=rgba[bg];[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v];[2:a]atrim=0:$DUR[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 17 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -t $DUR "$OUT"
ffprobe -v error -show_entries stream=codec_type,width,height,nb_frames -show_entries format=duration,size -of compact "$OUT"
