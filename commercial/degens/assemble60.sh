#!/bin/bash
# assemble60.sh FRAMES60 OVERLAYS60 AUDIO OUT.mp4
set -e
F=$1; O=$2; A=$3; OUT=$4
ffmpeg -v error -y -framerate 60 -i "$F/%08d.png" -framerate 60 -i "$O/o_%04d.png" -i "$A" \
  -filter_complex "[0:v]scale=1080:1920:flags=lanczos,unsharp=5:5:0.45:5:5:0,format=rgba[bg];[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v];[2:a]atrim=0:48.4,afade=t=out:st=47.6:d=0.8[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -t 48.4 -r 60 "$OUT"
ffprobe -v error -show_entries stream=codec_type,width,height,nb_frames,r_frame_rate -show_entries format=duration,size -of compact "$OUT"
