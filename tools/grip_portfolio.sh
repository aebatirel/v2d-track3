#!/bin/bash
# Grip-type portfolio for one hold (2026-10-25; owner: "try all the possible grip types and pick the best or most
# stable, decided on how the piece moves and how it is released"; docs/research/approaches-2026-10-25/
# approach3-grasp-taxonomy.md §11, pre-registered test P1 in docs/work-log.md). Per candidate (the human copy + each
# template of pipeline/grip_types.py): grasp_lock (GL_ARGS [+ --templates]) -> wrist ILC -> robust CMA-ES
# (tools/grasp_evolve.py --from0 --f1 F1 --cvar 0.25 --push_cm, all objects) -> a fresh K-copy re-score of its best.
# The choice (tools/grip_choose.py) keeps the copy unless a type beats it by MARGIN on the re-scored CVaR. No ground truth.
#   tools/grip_portfolio.sh IN_PARQUET OUT_DIR TPL_DIR PHASE F1 "copy clamp_long clamp_short platform"
# Env: GL_ARGS, POP (8), GENS (14), ROBUST (2), RESCORE (8), PUSH_CM (1), FCD, PY, DEV (cpu), PAR (2 candidates at once).
set -u
IN=$1; OUT=$2; TPL=$3; PH=$4; F1=$5; CANDS=$6
S=/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad
FCD=${FCD:-$S/src/video_to_data/robotic_grounding/flash_chord}; PY=${PY:-$S/fcvenv/bin/python}; DEV=${DEV:-cpu}
REPO=$(cd "$(dirname "$0")/.." && pwd)
GL_ARGS=${GL_ARGS:-"--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"}
POP=${POP:-8}; GENS=${GENS:-14}; ROBUST=${ROBUST:-2}; RESCORE=${RESCORE:-8}; PUSH_CM=${PUSH_CM:-1}; PAR=${PAR:-2}
SUB=$(echo "$IN" | grep -o 'processed/.*' | xargs dirname); ROOT=${IN%%/processed/*}
mkdir -p $OUT; echo "$(date -u +%FT%TZ) code $(git -C $REPO rev-parse --short HEAD) in $IN phase $PH f1 $F1 cands [$CANDS] pop $POP gens $GENS robust $ROBUST rescore $RESCORE push $PUSH_CM [$GL_ARGS]" >> $OUT/portfolio.log
EV="--phase $PH --from0 --f1 $F1 --all_objects --cvar 0.25 --push_cm $PUSH_CM --jitter 0.005 --sigma_pos 0.03 --sigma_fin 0.3"
one() {
  c=$1; A=$OUT/$c; D=$A/$SUB; mkdir -p $D; cp -f "$IN" $D/ref_in.parquet
  [ -e $A/reconstructed_stage ] || ln -s $ROOT/reconstructed_stage $A/reconstructed_stage
  tp=""; [ $c != copy ] && tp="--templates $TPL/$c.json"
  cd $FCD
  ( FC=$FCD GL_WRIST_KP=400 nice -n 10 $PY $REPO/pipeline/grasp_lock.py $D/ref_in.parquet $D/ref_gl.parquet $GL_ARGS $tp ) > $A/gl.log 2>&1 || { echo "$c GL_FAIL" >> $OUT/portfolio.log; return; }
  ( EMB=sharpa_hands_mid nice -n 10 $PY $REPO/pipeline/wrist_ilc.py $D/ref_gl.parquet $D/ref_gl_ilc.parquet --iters 4 --device $DEV ) > $A/ilc.log 2>&1 || { echo "$c ILC_FAIL" >> $OUT/portfolio.log; return; }
  ( EMB=sharpa_hands_mid DEV=$DEV nice -n 10 $PY $REPO/tools/grasp_evolve.py $D/ref_gl_ilc.parquet $D/ref_gl_grasp_lock.json $A/evolve.json $EV \
      --pop $POP --gens $GENS --robust $ROBUST --seed 0 --bake $D/ref_baked.parquet ) > $A/evolve.log 2>&1 || { echo "$c EVOLVE_FAIL" >> $OUT/portfolio.log; return; }
  ( EMB=sharpa_hands_mid DEV=$DEV nice -n 10 $PY $REPO/tools/grasp_evolve.py $D/ref_gl_ilc.parquet $D/ref_gl_grasp_lock.json $A/rescore_dummy.json $EV \
      --pop $RESCORE --rescore $RESCORE --init $A/evolve.json --seed 1 ) > $A/rescore.log 2>&1 || { echo "$c RESCORE_FAIL" >> $OUT/portfolio.log; return; }
  echo "$(date -u +%T) $c $(grep '"rescore"' $A/rescore.log | tail -1)" >> $OUT/portfolio.log
}
n=0; for c in $CANDS; do one $c & n=$((n + 1)); [ $((n % PAR)) = 0 ] && wait; done; wait
echo "$(date -u +%FT%TZ) DONE" >> $OUT/portfolio.log
