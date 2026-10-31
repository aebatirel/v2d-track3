#!/bin/bash
# E0 box job (CD-O sprint; PREREG docs/research/mesh-2026-10-26/cdo-sprint/E0/PREREG.md): C0's mesh methods with the
# frozen public settings, rebuilt on every eval episode of white_pot, white_pot_lid, plastic_dish_rack and blue_cup,
# on one many-core CPU box. Started by ops/box/run_job.sh with SETUP=none (stall watchdog, push of /content/results to
# the HF store runs/<RUN_ID>/, self-destroy; ops/box/lib.sh). Steps, each in parallel over all cores (xargs -P):
#   0. venvs (e0_setup.sh, pinned to the local venvs)
#   1. inputs: store runs/<RUN_ID>/inputs/ (uploaded by the agent; sha256-checked) + cache/depth/eval/ep<N>/ (e0_fetch.py)
#   2. hands: pipeline/hands_mp.py per episode (how the public G1 refs hands.npz were made); a failed episode runs
#      obs_points without --hands (public rule: hands where they exist)
#   3. obs_points.py per (episode, object) pair, the prep_obs.sh command
#   4. candidate builds: pot prim_potlid fit/nostem/tsdf/thick per episode; lid fit/tsdf at PRIM_T_LID=0.0025; rack
#      prim_rack.py run (T_WALL 2.5 mm, CUP_LEAN 1) over the rack's eval episodes (per-episode full/nomk + joint);
#      blue cup lathe_obs.py g1 (defaults) and g0 (--appendages 0) per episode + g1 on the merged points
#   5. obs_fidelity.py per (mesh, point set): every candidate, the C0 mesh and library_v3, on ALL eval points of the
#      object and on each episode's points
#   6. C0 frame_check.py (frame vs library_v3 + kit budget_mesh) per candidate; 7. e0_select.py (pre-registered pick)
#   8. SHA256SUMS of results/e0, push to the store, exit (run_job.sh self-destroys)
# Inputs never include scans, mocap, parquet poses or *_align files. Progress lines go to results/e0/e0_job.log.
# Box:   bash docs/research/mesh-2026-10-26/cdo-sprint/E0/jobs/e0_box.sh       (RUN_ID from ops/vast.sh)
# Local dry run (no store writes): E0_LOCAL=1 E0_ROOT=<dir> E0_STORE_LOCAL=<fake store> E0_SETUP=0 E0_PY=<python>
#   E0_MPPY=<mp python> E0_EPS="14" E0_STRIDE=8 RUN_ID=<id> bash e0_box.sh   (E0_STRIDE != 2 marks the run DRY)
set -u
JOBD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -z "${E0_LOCAL:-}" ]; then
  . /content/v2d-track3/ops/box/lib.sh
else
  REPO_DIR=$(cd $JOBD/../../../../../.. && pwd)
  log() { echo "[$(date -u +%FT%TZ)] $*"; }; label() { :; }
fi
: "${RUN_ID:?RUN_ID is not set}"
ROOT=${E0_ROOT:-/content}; W=$ROOT/e0w; R=$ROOT/results/e0; IN=$W/inputs; DEPTH=$W/depth
NPROC=${E0_NPROC:-$(nproc)}; STRIDE=${E0_STRIDE:-2}
PY=${E0_PY:-$W/venv/bin/python}; MPPY=${E0_MPPY:-$W/mpvenv/bin/python}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2}
export HF_HUB_DISABLE_PROGRESS_BARS=1 HF_XET_CHUNK_CACHE_SIZE_BYTES=0 PYTHONDONTWRITEBYTECODE=1
mkdir -p $W $R/{logs/{hands,obs,build,fid,check},status,hands,obs,axis,commands} $R/cand/{white_pot,white_pot_lid,blue_cup,rack} \
  $R/fid/{pot,lid,rack,cup} $R/check/{pot,lid,rack,cup}
exec >> $R/e0_job.log 2>&1
T0=$(date +%s)
log "E0 job start: run $RUN_ID commit $(git -C $REPO_DIR rev-parse HEAD) dirty=$(git -C $REPO_DIR status --porcelain -- docs/research/mesh-2026-10-26/scripts docs/research/mesh-2026-10-26/cdo-sprint/E0/jobs pipeline | wc -l) cpus $(nproc) workers $NPROC ram $(free -g | awk '/Mem/{print $2}') GB disk $(df -h $ROOT | awk 'NR==2{print $4}') free; stride $STRIDE${E0_EPS:+, episodes [$E0_EPS] (DRY subset)}"
[ "$STRIDE" = 2 ] || log "DRY: obs_points stride $STRIDE (production is the public default 2)"
fail() { log "E0-FAIL: $*"; label "E0 FAIL: $*"; finish 1; }
progress() {  # one line per minute, only when something changed (the stall watchdog must still see a real stall)
  local last=""
  while sleep 60; do
    local cur="$(for s in hands obs build fid check; do printf '%s %s/%s ' $s $(grep -c '^OK' $R/status/$s.txt 2> /dev/null || echo 0) $(grep -c '^FAIL' $R/status/$s.txt 2> /dev/null || echo 0); done) files $(find $R -type f | wc -l)"
    [ "$cur" != "$last" ] && log "progress (ok/fail): $cur load $(cut -d' ' -f1 /proc/loadavg)" && last=$cur
  done
}
prun() {  # $1 stage: run commands/<stage>.txt with NPROC workers
  local n; n=$(grep -c . $R/commands/$1.txt || true)
  log "stage $1: $n tasks, $NPROC workers"; label "E0 $1 ($n tasks)"
  [ "$n" -gt 0 ] && xargs -d '\n' -P $NPROC -n 1 bash -c < $R/commands/$1.txt
  log "stage $1 done: OK $(grep -c '^OK' $R/status/$1.txt 2> /dev/null || echo 0) FAIL $(grep -c '^FAIL' $R/status/$1.txt 2> /dev/null || echo 0)" \
      "$(grep '^FAIL' $R/status/$1.txt 2> /dev/null | cut -d' ' -f2 | tr '\n' ' ')"
}
finish() {
  kill $PROG 2> /dev/null
  (cd $R && find . -type f ! -name SHA256SUMS ! -name e0_job.log -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  log "SHA256SUMS: $(wc -l < $R/SHA256SUMS) files, $(du -sh $R | cut -f1); total $(( ($(date +%s) - T0) / 60 )) min"
  if [ -n "${E0_LOCAL:-}" ]; then
    log "local run: no store push"
  else
    label "E0 push"; bash $OPS/store.sh push-run && log "E0 pushed to the store runs/$RUN_ID" || log "E0 push FAILED (run_job.sh pushes again before destroy)"
  fi
  log "E0-$([ $1 = 0 ] && echo DONE || echo INCOMPLETE) rc=$1"
  exit $1
}
progress & PROG=$!

# 0. environment
if [ "${E0_SETUP:-1}" = 1 ]; then
  label "E0 setup"; log "setup venvs"
  bash $JOBD/e0_setup.sh $W $R/logs/setup.log || fail "setup (main venv)"
  cp $W/freeze_main.txt $W/freeze_mp.txt $R/ 2> /dev/null
  log "setup: $(grep -aoE 'E0-SETUP-[A-Z]+-(OK|FAIL)' $R/logs/setup.log | tr '\n' ' ')"
fi
"$PY" -c "import numpy, trimesh, manifold3d" || fail "main python $PY"

# 1. inputs
label "E0 inputs"
"$PY" -I $JOBD/e0_fetch.py --run $RUN_ID --inputs $IN --depth $DEPTH ${E0_STORE_LOCAL:+--local $E0_STORE_LOCAL} \
  ${E0_EPS:+--eps "$E0_EPS"} --workers ${E0_DL_WORKERS:-8} > $R/logs/fetch.log 2>&1 || fail "inputs: $(tail -1 $R/logs/fetch.log)"
log "inputs: $(grep -c . $IN/SHA256SUMS) files sha256 OK; depth $(tail -1 $R/logs/fetch.log)"
cp $IN/plan.json $IN/SHA256SUMS $R/ && mv $R/SHA256SUMS $R/inputs_SHA256SUMS
cat > $R/env.json << JSON
{"PY": "$PY", "MPPY": "$MPPY", "REPO": "$REPO_DIR", "R": "$R", "IN": "$IN", "DEPTH": "$DEPTH", "KIT": "$IN/kit",
 "STRIDE": "$STRIDE", "EPS": "${E0_EPS:-}"}
JSON
T() { "$PY" -I $JOBD/e0_tasks.py $1 --plan $IN/plan.json --env $R/env.json > $R/commands/$1.txt || fail "task list $1"; }

# 2. hands (MediaPipe), 3. observed points
if [ -x "$MPPY" ] && "$MPPY" -c "import mediapipe" 2> /dev/null; then T hands; prun hands; else log "no MediaPipe venv: obs_points without --hands"; fi
T obs; prun obs
[ "$(grep -c '^OK' $R/status/obs.txt 2> /dev/null || echo 0)" -gt 0 ] || fail "no observed points"
for f in $R/obs/*.npz; do log "obs $(basename $f .npz): $(tail -1 $R/logs/obs/$(basename $f .npz | sed -E 's/^ep([0-9]+)_(.*)$/\2__ep\1/; s/^white_pot_lid/lid/; s/^white_pot/pot/; s/^plastic_dish_rack/rack/; s/^blue_cup/cup/').log 2> /dev/null)"; done

# 4. candidate builds
T build; prun build
"$PY" -I $JOBD/e0_tasks.py candidates --plan $IN/plan.json --env $R/env.json > $R/candidates.json || fail "candidate list"
log "candidates built: $("$PY" -c "import json,collections; c=json.load(open('$R/candidates.json')); print(dict(collections.Counter((x['object'], x['kind']) for x in c)))")"

# 5. fidelity, 6. frame + budget checks (one parallel pool)
T fid; T check
prun fid; prun check

# 7. pre-registered pick
"$PY" -I $JOBD/e0_select.py --results $R --cands $R/candidates.json --thresholds $JOBD/../inputs/thresholds.json \
  --plan $IN/plan.json > $R/logs/select.log 2>&1 && log "select: $(tr '\n' ' ' < $R/logs/select.log)" || log "select FAILED: $(tail -3 $R/logs/select.log)"
finish 0
