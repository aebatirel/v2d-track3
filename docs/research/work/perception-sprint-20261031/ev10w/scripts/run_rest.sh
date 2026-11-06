#!/bin/bash
# Rest robustness in the carve.json style (FlashCHORD harness tools/carve_fc_test.py, CPU, hands parked 3 m away,
# no drive: --free_until 1000): (1) both cups from start frames 0,2,..,10 to f38 (the blue cup stands alone; the beige
# stands beside it), (2) the nested pair hands-free from f120 to f160. Mesh sets ev10 and ev10w (assets from
# pipeline/make_assets.py --pieces). Output JSONs in out/rest/.
W=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w
FPY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve/fcvenv/bin/python
export FC=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/src/video_to_data/robotic_grounding/flash_chord
export FLASH_CHORD_CACHE_DIR=$W/fccache_fc
TREE=$W/dl/runs/20261026-gl10A2-5e0e100/refs/glockt/ep10
mkdir -p $W/out/rest; cd $W
for m in ev10 ev10w; do
  for s in 0 2 4 6 8 10; do
    $FPY -I /home/user/v2d-track3/tools/carve_fc_test.py --tree $TREE --assets $W/assets/$m --out $W/out/rest/${m}_rest_s$s.json \
      --names blue_cup,beige_cup --start $s --end 38 --free_until 1000 > $W/logs/rest_${m}_s$s.log 2>&1
  done
  $FPY -I /home/user/v2d-track3/tools/carve_fc_test.py --tree $TREE --assets $W/assets/$m --out $W/out/rest/${m}_nest_s120.json \
    --names blue_cup,beige_cup --start 120 --end 160 --free_until 1000 > $W/logs/rest_${m}_nest.log 2>&1
done
