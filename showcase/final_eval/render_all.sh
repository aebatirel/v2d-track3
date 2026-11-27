#!/bin/bash
# Styled renders of the final pack's eval replays (replay_all.sh), two views per episode: a fixed side camera and the
# person's own head-camera path (render_style.py --ego). Render-only swaps: clean meshes (RENDER_ASSETS: library_c0 lid
# and rack, flat-bottomed pot, other objects the simulator's own), the real 46 cm table at the fitted centre
# (results/table_fits.json), per-object colours. The final auto-reset row of each replay is not drawn.
#   FC=<flash_chord dir> bash render_all.sh [OUT=/content/ev] [EPS="1 3 ..."] [SIZE=660x496] [VIEWS="side ego"] [PAR=2]
set -u
FC=${FC:?FC missing}; OUT=${OUT:-/content/ev}; SIZE=${SIZE:-660x496}; PAR=${PAR:-2}; VIEWS=${VIEWS:-side ego}
RA=${RENDER_ASSETS:-$OUT/render_assets}; HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd $HERE/../.. && pwd)
EYE=${EYE:-0.42,-0.95,1.18}; TGT=${TGT:--0.04,-0.06,0.72}
EPS=${EPS:-$(ls -d $OUT/ep* | sed 's#.*/ep##' | sort -n | tr '\n' ' ')}
one() {  # $1 episode, $2 view
  local ep=$1 v=$2 D=$OUT/ep$1 T N TB o
  o=$D/render_$v.mp4; [ -s $o ] && return 0
  T=$(python3 -c "import json; print(json.load(open('$D/setup.json'))['task'])")
  N=$(python3 -c "import numpy as np; f=np.load('$D/replay_cpu.npz')['frame']; print(int((np.r_[True, np.diff(f) > 0]).sum()))")
  TB=$(python3 -c "import json; c=json.load(open('$HERE/results/table_fits.json'))['episodes']['$ep']; print(f\"{c['radius']},{c['center_xy'][0]:.4f},{c['center_xy'][1]:.4f}\")")
  local extra=(); [ $v = ego ] && extra=(--ego $D/ego,$D/perc) || extra=(--eye=$EYE --target=$TGT)
  ( cd $FC && timeout 3600 xvfb-run -a -s "-screen 0 1280x1024x24" .venv/bin/python $REPO/showcase/tools/render_style.py $T $o \
      --emb sharpa_hands_mid --trace $D/replay_cpu.npz --frames 0:$N --size $SIZE --objects_dir $RA --table $TB --palette "${extra[@]}" ) > $D/render_$v.log 2>&1
  echo "ep$ep $v: $(grep -o 'rendered [0-9]* frames' $D/render_$v.log || echo FAILED)"
}
pids=()
for ep in $EPS; do for v in $VIEWS; do
  one $ep $v & pids+=($!)
  [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
done; done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"; exit 0
