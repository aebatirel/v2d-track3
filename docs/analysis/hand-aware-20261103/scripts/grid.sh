#!/bin/bash
# dev grid: mask {on,off} x gate {contact,near} x tau {1.0,1.5,2.0} cm, band 0.25
cd /home/user/work; EPS="$@"
for m in "" "--no_hand_mask"; do for g in contact near; do for t in 0.010 0.015 0.020; do
  tag=g_${g}_t${t#0.0}$( [ -n "$m" ] && echo _nm ); echo "$tag|--band 0.25 --tau $t --gate $g $m"
done; done; done | xargs -P 3 -I{} bash -c 'IFS="|" read tag args <<< "{}"; ./run_hrc.sh $tag "$args" '"$EPS"
