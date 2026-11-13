#!/bin/bash
# rts INFERENCE side (PREREG §3; GT-free): pipeline/refine.py on the 20 public episodes, two input arms as heldpose /
# mask10: Po = Phase-1 P_o tracks linked in $S/leak/t1/in_Po, refineP = 25 Oct tracks in $S/refine/in (both with
# refine/in's hands and frame-0 depth). Nothing here reads mocap; refine.assert_inference_input checks every input.
#   PHASE=pre   code BEFORE S13 existed (HEAD fef059b, clean tree): control S2 and the default chain (DEF, no --steps)
#               -> $W/runs_pre/<arm>/<variant>/ep<N>
#   PHASE=post  code WITH S13: control S2, default chain DEF, treatment S13 (= --steps S2,S13)
#               -> $W/runs/<arm>/<variant>/ep<N>
# Scoring (oracle side, after this): rts_score.py.  Usage: rts_run.sh pre|post
set -u
PHASE=${1:?usage: rts_run.sh pre|post}
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/rts; R=$S/refine/in; PO=$S/leak/t1/in_Po
PY=$S/map/scoring/venv/bin/python; REPO=/home/user/v2d-track3
EPS="0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"
case $PHASE in
  pre)  OUT=$W/runs_pre; VARS="S2 DEF";;
  post) OUT=$W/runs;     VARS="S2 DEF S13";;
  *) echo "PHASE must be pre or post"; exit 2;;
esac
mkdir -p $OUT
{ date -u +%Y-%m-%dT%H:%M:%SZ; sha256sum $REPO/pipeline/refine.py; [ -f $REPO/pipeline/rts.py ] && sha256sum $REPO/pipeline/rts.py
  (cd $REPO && git rev-parse HEAD && git status --short pipeline/ tests/); } > $OUT/code_version.txt
J=$OUT/jobs.txt; : > $J
for arm in Po refineP; do
  for v in $VARS; do
    mkdir -p $OUT/$arm/$v/logs
    case $v in S2) st="--steps S2";; DEF) st="";; S13) st="--steps S2,S13";; esac
    for e in $EPS; do
      inp=$R/ep$e; [ $arm = Po ] && inp=$PO/ep$e
      echo "$PY -I $REPO/pipeline/refine.py --in $inp --out $OUT/$arm/$v/ep$e $st --force > $OUT/$arm/$v/logs/ep$e.log 2>&1 || echo FAIL $arm $v ep$e" >> $J
    done
  done
done
cd /tmp && xargs -P 4 -I{} bash -c '{}' < $J
grep -l "Traceback" $OUT/*/*/logs/*.log || echo "no tracebacks"
date -u +%Y-%m-%dT%H:%M:%SZ >> $OUT/code_version.txt
