#!/bin/bash
# Frozen stage-1b run over the 20 public episodes (PREREG.md). Per episode: fetch inputs (store, read-only), run
# stage1b.py with ARGS, score control C and the arm with the registered scorer (per-frame errors kept), delete the depth.
# Usage: B=<work dir> DEP=<depth dir> PY=<python> T3=<t3 dir> KIT=<kit dir> TAG=<arm tag> ARGS="..." bash run_all.sh [EPS...]
set -u
H=$(cd "$(dirname "$0")" && pwd)
EPS=${*:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
X="--t3 $T3 --kit $KIT"
one() {
  local e=$1 o=$B/arms/$TAG/ep$e
  [ -s $o/score.json ] && { echo "ep$e $TAG done already"; return; }
  if [ ! -s $B/C/ep$e/score.json ]; then
    $PY -I $B/code/score_registered.py $e $B/C/ep$e/poses_world_vo.npz --meshes $B/meshes_9aplus $X \
      --per_frame $B/C/ep$e/pf.npz --out $B/C/ep$e/score.json > $B/C/ep$e/score.log 2>&1
  fi
  mkdir -p $o
  $PY -I $B/code/stage1b.py $e $B/C/ep$e/poses.npz $DEP/ep$e.npy $B/C/ep$e/vos_masks.npz $B/C/ep$e/det_f0.npz \
    $B/meshes_9aplus $o ${ARGS:-} > $o/fit.log 2>&1 || { echo "ep$e $TAG FIT FAILED: $(tail -2 $o/fit.log)"; return; }
  local M=$o/meshes; case " ${ARGS:-} " in *" --no_shape "*) M=$B/meshes_9aplus ;; esac
  $PY -I $B/code/score_registered.py $e $o/poses_world_vo.npz --meshes $M $X --per_frame $o/pf.npz \
    --out $o/score.json > $o/score.log 2>&1 || { echo "ep$e $TAG SCORE FAILED"; return; }
  echo "ep$e $TAG $(python3 -c "import json; c=json.load(open('$B/C/ep$e/score.json'))['perception']; v=json.load(open('$o/score.json'))['perception']; print('C', c['AUC'], 'arm', v['AUC'], 'dAUC', round(v['AUC'] - c['AUC'], 4))")"
}
pids=()
for e in $EPS; do
  B=$B DEP=$DEP bash $H/fetch_ep.sh $e > /dev/null 2>&1 || { echo "ep$e FETCH FAILED"; continue; }
  src=$(cat $B/C/ep$e/SOURCE); [ -s $B/C/ep$e/log.txt ] || curl -sS -L -f -o $B/C/ep$e/log.txt \
    "https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/$src/log.txt" -H "Authorization: Bearer dummy"
  ( one $e; [ "${KEEP_DEPTH:-0}" = 1 ] || rm -f $DEP/ep$e.npy ) & pids+=($!)
  if [ ${#pids[@]} -ge ${PAR:-2} ]; then wait "${pids[0]}"; pids=("${pids[@]:1}"); fi
done
wait
