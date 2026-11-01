#!/bin/bash
# C2/R builds, fidelity, exclusion checks and the pick (PREREG sections 4-5). GT-free; CPU, $0 when local.
# Inputs: c2r_stage.py output dir IN (C0b pass-B rack points, markers, params.json, kit dir KIT).
# Each step skips work whose output exists (a crash is resumed unchanged; nothing is re-run with changed settings).
# Usage: bash c2r_build.sh IN OUT KIT [PAR]      (PAR = parallel runs / fidelity workers, default 2)
set -u
IN=$1; OUT=$2; KIT=$3; PAR=${4:-2}
SCR=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
PY=${C2R_PY:-$SCR/venv/bin/python}
REPO=$(cd "$(dirname "$0")/../../../../../../.." && pwd)
S=$REPO/docs/research/mesh-2026-10-26/scripts
J=$REPO/docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs
HERE=$(cd "$(dirname "$0")" && pwd)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2}
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $OUT/logs $OUT/fid $OUT/check
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a $OUT/c2r_build.log; }
T=$($PY -c "import json; print(repr(json.load(open('$IN/params.json'))['targets']['rack/run']['t_wall_m']))") || { log "FAIL: no rack T"; exit 1; }
[ "$T" = None ] && { log "FAIL: C0b rack T not fittable"; exit 1; }
EPS=${C2R_EPS:-12,13,26,27,31}     # C2R_EPS / C2R_SETS: dry-run subsets only (logged as DRY)
OBS=$(for e in ${EPS//,/ }; do printf '%s,' $IN/pts/B/ep${e}_plastic_dish_rack.npz; done); OBS=${OBS%,}
log "C2/R build: commit $(git -C $REPO rev-parse HEAD) dirty=$(git -C $REPO status --porcelain -- docs/research/mesh-2026-10-26/scripts | wc -l) T=$T PAR=$PAR"
declare -A FL=([base]="" [E]="--end_draft" [K]="--peg_kappa_free" [Q]="--cup_quad" [EK]="--end_draft --peg_kappa_free"
               [EQ]="--end_draft --cup_quad" [KQ]="--peg_kappa_free --cup_quad" [EKQ]="--end_draft --peg_kappa_free --cup_quad")
SETS=${C2R_SETS:-"base E K Q EK EQ KQ EKQ"}
[ -n "${C2R_EPS:-}${C2R_SETS:-}" ] && log "DRY: episodes $EPS sets $SETS"
for k in $SETS; do
  echo "[ -s $OUT/cand/$k/selection.json ] || ( cd $OUT && PRIM_CUP_LEAN=1 nice -n 10 $PY -I $S/prim_rack.py run --obs_dir $IN/pts/B --out $OUT/cand/$k --episodes $EPS --t_wall $T --s0_min_t --markers_dir $IN/markers ${FL[$k]} > $OUT/logs/run_$k.log 2>&1 && echo OK $k || echo FAIL $k ) >> $OUT/logs/status_runs.txt"
done > $OUT/logs/cmd_runs.txt
log "runs: $(wc -l < $OUT/logs/cmd_runs.txt) commands"
xargs -d '\n' -P $PAR -n 1 bash -c < $OUT/logs/cmd_runs.txt
log "runs done: $(tr '\n' ' ' < $OUT/logs/status_runs.txt)"
ls $OUT/cand/*/plastic_dish_rack/*.glb > $OUT/meshes.txt
log "meshes: $(wc -l < $OUT/meshes.txt)"
while read m; do
  k=$(echo $m | awk -F/ '{print $(NF-2)}'); b=$(basename $m .glb); t=${k}__$b
  echo "[ -s $OUT/fid/$t.json ] || nice -n 10 $PY -I $S/obs_fidelity.py $OBS $m > $OUT/fid/$t.json 2> $OUT/fid/$t.err; [ -s $OUT/check/$t.json ] || nice -n 10 $PY -I $J/c0b_check.py $KIT $m $OUT/check/$t.json > /dev/null 2>&1"
done < $OUT/meshes.txt > $OUT/logs/cmd_fid.txt
xargs -d '\n' -P $PAR -n 1 bash -c < $OUT/logs/cmd_fid.txt
log "fidelity: $(ls $OUT/fid/*.json | wc -l) files, checks: $(ls $OUT/check/*.json | wc -l)"
$PY -I $HERE/c2r_select.py $OUT > $OUT/logs/select.log 2>&1 && log "select: $(tail -1 $OUT/logs/select.log)" || log "select FAILED: $(tail -3 $OUT/logs/select.log)"
log "C2R-BUILD-DONE"
