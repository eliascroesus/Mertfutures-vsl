#!/bin/bash
# Render the composited video in chunks (resumable: finished chunks are skipped), then join them.
#   render_chunks.sh elements.json base.mp4 text.ass out.mp4 total nchunks
cd /home/user/work
EL=$1; BASE=$2; ASS=$3; OUT=$4; TOTAL=$5; N=$6
D=${OUT%.mp4}_parts; mkdir -p $D
pids=()
for i in $(seq 0 $((N-1))); do
  s=$(python3 -c "print(round($TOTAL*$i/$N*30)/30)"); e=$(python3 -c "print(round($TOTAL*($i+1)/$N*30)/30)")
  [ -f $D/p$i.done ] && continue
  ( venv/bin/python scripts/compositor.py $EL $BASE $ASS $D/p$i.mp4 $TOTAL $s $e > $D/p$i.log 2>&1 && touch $D/p$i.done ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
for i in $(seq 0 $((N-1))); do [ -f $D/p$i.done ] || { echo "chunk $i failed"; exit 1; }; echo "file 'p$i.mp4'"; done > $D/list.txt
ffmpeg -y -v error -f concat -safe 0 -i $D/list.txt -c copy -movflags +faststart $OUT && echo "joined $OUT"
