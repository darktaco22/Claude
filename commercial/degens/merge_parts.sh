#!/bin/bash
# Pull the rendered sections from the worker branches, unpack them into frames, then build both videos.
set -e
. $(dirname $0)/env.sh; cd /home/user/Claude
for n in 1b 1c 2 2b 2c 2d 3 4 5; do git fetch -q origin claude/degens-part-$n; done
mkdir -p $W/parts && rm -f $W/parts/*
for n in 1b 1c 2 2b 2c 2d 3 4 5; do
  for f in $(git ls-tree -r --name-only origin/claude/degens-part-$n commercial/renders/ | sort); do
    git show origin/claude/degens-part-$n:$f > $W/parts/$(basename $f)
  done
done
cd $W/parts
for base in $(ls | sed -E 's/\.mp4.*//' | sort -u); do [ -f $base.mp4 ] || cat $(ls $base.mp4?* | sort) > $base.mp4; done
for v in part_*.mp4; do
  a=$(echo $v | sed -E 's/part_0*([0-9]+)_.*/\1/'); b=$(echo $v | sed -E 's/part_[0-9]+_0*([0-9]+)\.mp4/\1/')
  ffmpeg -v error -y -i $v -start_number $a -pix_fmt rgb24 $W/frames/f_%04d.png
  n=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 $v)
  echo "unpacked $v: $n frames (expected $((b - a + 1)))"
done
