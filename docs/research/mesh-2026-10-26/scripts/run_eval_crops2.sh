cd /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
FR=$(python3 -c "print(','.join(str(i) for i in range(0,421,8)))")
run() { e=$1; o=$2; lib=/home/user/v2d-track3/meshes/library_v3; [ $e = 8 ] && lib=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/lib_ep8
  [ -f evalcrops/ep$e/${o}_crops.json ] && { echo "skip ep$e $o"; return; }
  venv/bin/python -W ignore /home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts/crops.py --video data/eval/ep${e}_a.mp4 --poses data/eval/ep$e/poses.npz --calib data/calib.json --lib $lib --obj $o --out evalcrops/ep$e --frames $FR --n 1 > evalcrops/log_ep${e}_$o.txt 2>&1 || echo "FAIL ep$e $o"; echo "done ep$e $o"; }
i=0; while read e o; do run $e $o & i=$((i+1)); [ $((i % 4)) = 0 ] && wait; done < eval_pairs.txt; wait; echo EVAL-CROPS-DONE
