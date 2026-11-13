#!/bin/bash
# E0b eval box job (C0b PREREG docs/research/mesh-2026-10-26/cdo-sprint/C0b/PREREG.md, sections 9-11): the C0b
# scan-free methods on the eval episodes of white_pot, white_pot_lid, plastic_dish_rack, blue_cup and beige_cup, on
# one many-core CPU box. A copy of ../../C0b/jobs/c0b_box.sh with the eval task lists (e0b_tasks.py); the C0b helpers
# (c0b_prep via e0b_prep, c0b_obs.sh, c0b_check.py, c0b_fetch.py, c0b_setup.sh) run unchanged. Started by
# ops/box/run_job.sh with SETUP=none (stall watchdog, push of /content/results to the HF store runs/<RUN_ID>/,
# self-destroy; ops/box/lib.sh). Steps, each in parallel (xargs -P):
#   0. venv (C0b's c0b_setup.sh, E0's pinned req_main.txt)
#   1. inputs: store runs/<RUN_ID>/inputs/ (e0b_stage.py; sha256-checked) + eval depth (size + LFS sha256 checked)
#   2. obsA: obs_points.py --roi_cube 0.30, no co-objects, every tracked object of the 14 eval episodes; cube guard
#   3. obsB: the final target files (pot, lid, rack, blue cup, beige cup), --others_pts = co-objects' pass-A points
#   4. derive: beige M_sep(own) on eval 8 and 10; merged blue-cup points (5 episodes); derive2: merged beige points
#      if both beige episodes qualify
#   5. measure: thickness.py rows and A.2 sigma of every build input (t0_C0b = the frozen public value)
#   6. markers: gmg markers.detect_episode per eval episode (frozen A.6 settings, sha asserted)
#   7. params (thickness chain steps 1-2 on eval points, step 3 public t0_C0b; 3 sigma) and builds
#   8. checks (watertight raw, kit budget); frame refs (public candidates vs the C0b public pick) -> thresholds ->
#      frame check of every eval candidate vs the C0b public pick; fidelity (ALL + per episode) of every candidate and
#      of the C0b public picks; 9. e0b_select.py (pick + PREREG 9 (e) ship rule)
#  10. report (after the pick; reported only): C0's meshes, library_v3 (+ v3x beige), E0's picks on the eval points
#  11. SHA256SUMS, push to the store, exit (run_job.sh self-destroys)
# Inputs never include scans, mocap, parquet poses or *_align files. Progress lines go to results/e0b/e0b_job.log.
# Box:   bash docs/research/mesh-2026-10-26/cdo-sprint/E0b/jobs/e0b_box.sh       (RUN_ID from ops/vast.sh)
# Local dry run (no store writes): E0B_LOCAL=1 E0B_ROOT=<dir> E0B_STORE_LOCAL=<fake store> E0B_SETUP=0 E0B_PY=<python>
#   E0B_EPS="10 14" E0B_STRIDE=8 RUN_ID=<id> bash e0b_box.sh   (E0B_STRIDE != 2 marks the run DRY)
set -u
JOBD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CJOB=$(cd $JOBD/../../C0b/jobs && pwd)
if [ -z "${E0B_LOCAL:-}" ]; then
  . /content/v2d-track3/ops/box/lib.sh
else
  REPO_DIR=$(cd $JOBD/../../../../../.. && pwd)
  log() { echo "[$(date -u +%FT%TZ)] $*"; }; label() { :; }
fi
: "${RUN_ID:?RUN_ID is not set}"
ADOPTED=white_pot,beige_cup        # C0b PUBLIC_RESULTS (d84bc87): WIN + AUC guard (PREREG 8)
ROOT=${E0B_ROOT:-/content}; W=$ROOT/e0bw; R=$ROOT/results/e0b; IN=$W/inputs; DEPTH=$W/depth
NPROC=${E0B_NPROC:-$(nproc)}; STRIDE=${E0B_STRIDE:-2}
PY=${E0B_PY:-$W/venv/bin/python}
RAMGB=$(free -g | awk '/Mem/{print $2}')
FIDP=$(( RAMGB / 8 )); [ $FIDP -gt $NPROC ] && FIDP=$NPROC; [ $FIDP -lt 1 ] && FIDP=1    # obs_fidelity loads ALL points
OBSP=$(( RAMGB / 6 )); [ $OBSP -gt $NPROC ] && OBSP=$NPROC; [ $OBSP -lt 1 ] && OBSP=1
FRP=$(( RAMGB / 6 )); [ $FRP -gt $NPROC ] && FRP=$NPROC; [ $FRP -lt 1 ] && FRP=1          # frame_check: ~3 GB per process (closest_point on 25-54 k-face picks)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2}
export HF_HUB_DISABLE_PROGRESS_BARS=1 HF_XET_CHUNK_CACHE_SIZE_BYTES=0 PYTHONDONTWRITEBYTECODE=1
export GMG_DATA_ROOT=$W GMG_MODE=clean          # gmg guard roots (its audit hook refuses ground-truth paths)
[ "$STRIDE" != 2 ] && export C0B_STRIDE=$STRIDE  # c0b_obs.sh reads C0B_STRIDE (dry run only)
mkdir -p $W $R/{logs/{obsA,obsB,derive,derive2,measure,markers,build,fid,check,fref,frame,report},status,pts/{A,B,M},guard,thick,sigma,markers,axis,commands} \
  $R/cand/{white_pot,white_pot_lid,blue_cup,beige_cup,rack} $R/fid/{pot,lid,rack,cup,beige} $R/check/{pot,lid,rack,cup,beige} \
  $R/fref/{pot,rack,cup,beige} $R/frame/{pot,rack,cup,beige} $R/report/{pot,lid,rack,cup,beige}
exec >> $R/e0b_job.log 2>&1
T0=$(date +%s)
log "E0b job start: run $RUN_ID commit $(git -C $REPO_DIR rev-parse HEAD) dirty=$(git -C $REPO_DIR status --porcelain -- docs/research/mesh-2026-10-26/scripts docs/research/mesh-2026-10-26/gmg/markers.py docs/research/mesh-2026-10-26/gmg/thickness.py docs/research/mesh-2026-10-26/gmg/bundle.py docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs docs/research/mesh-2026-10-26/cdo-sprint/E0b/jobs pipeline | wc -l) cpus $NPROC ram $RAMGB GB (obs workers $OBSP, fid workers $FIDP, frame workers $FRP) disk $(df -h $ROOT | awk 'NR==2{print $4}') free; stride $STRIDE${E0B_EPS:+, episodes [$E0B_EPS] (DRY subset)}"
[ "$STRIDE" = 2 ] || log "DRY: obs_points stride $STRIDE (production is the default 2)"
fail() { log "E0B-FAIL: $*"; label "E0b FAIL: $*"; finish 1; }
cnt() { local n; n=$(grep -c "$1" "$2" 2> /dev/null); echo ${n:-0}; }
cputot() { ps -eo cputimes,comm --no-headers 2> /dev/null | awk '$2 ~ /python/ {s += $1} END {print s + 0}'; }
progress() {  # one line per minute when a status changed; every 5 min a CPU heartbeat if worker CPU time grew
  local last="" lastcpu=0 k=0
  while sleep 60; do
    k=$((k + 1))
    local cur="$(for s in obsA obsB derive derive2 measure markers build check fref frame fid report; do printf '%s %s/%s ' $s $(cnt '^OK' $R/status/$s.txt) $(cnt '^FAIL' $R/status/$s.txt); done) files $(find $R -type f | wc -l)"
    [ "$cur" != "$last" ] && log "progress (ok/fail): $cur load $(cut -d' ' -f1 /proc/loadavg)" && last=$cur
    if [ $((k % 5)) = 0 ]; then
      local c; c=$(cputot)
      [ "$c" -gt "$lastcpu" ] && log "alive: python workers cpu $c s (+$((c - lastcpu)) s), load $(cut -d' ' -f1 /proc/loadavg), mem used $(free -g | awk '/Mem/{print $3}') GB"
      lastcpu=$c
    fi
  done
}
prun() {  # $1 stage [$2 workers]: run commands/<stage>.txt
  local n p=${2:-$NPROC}; n=$(grep -c . $R/commands/$1.txt || true)
  log "stage $1: $n tasks, $p workers"; label "E0b $1 ($n tasks)"
  [ "$n" -gt 0 ] && xargs -d '\n' -P $p -n 1 bash -c < $R/commands/$1.txt
  log "stage $1 done: OK $(cnt '^OK' $R/status/$1.txt) FAIL $(cnt '^FAIL' $R/status/$1.txt)" \
      "$(grep '^FAIL' $R/status/$1.txt 2> /dev/null | cut -d' ' -f2 | tr '\n' ' ')"
}
finish() {
  kill $PROG 2> /dev/null
  (cd $R && find . -type f ! -name SHA256SUMS ! -name e0b_job.log -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  log "SHA256SUMS: $(wc -l < $R/SHA256SUMS) files, $(du -sh $R | cut -f1); total $(( ($(date +%s) - T0) / 60 )) min"
  if [ -n "${E0B_LOCAL:-}" ]; then
    log "local run: no store push"
  else
    label "E0b push"; bash $OPS/store.sh push-run && log "E0b pushed to the store runs/$RUN_ID" || log "E0b push FAILED (run_job.sh pushes again before destroy)"
  fi
  log "E0B-$([ $1 = 0 ] && echo DONE || echo INCOMPLETE) rc=$1"
  exit $1
}
progress & PROG=$!

# 0. environment
if [ "${E0B_SETUP:-1}" = 1 ]; then
  label "E0b setup"; log "setup venv"
  bash $CJOB/c0b_setup.sh $W $R/logs/setup.log || fail "setup (main venv)"
  cp $W/freeze_main.txt $R/ 2> /dev/null
fi
"$PY" -c "import numpy, trimesh, manifold3d, skimage" || fail "python $PY"
GMGSHA=$(cd $JOBD && "$PY" -I -c "import sys; sys.path.insert(0, '$REPO_DIR/docs/research/mesh-2026-10-26'); from gmg import markers; print(markers.SETTINGS_SHA256)") \
  || fail "gmg markers import"
[ "$GMGSHA" = 488ac3b638aa7e68c12843a5b761ed8882106bc78d8307d9e3059932502aa128 ] || fail "markers settings sha $GMGSHA"
log "gmg markers settings sha256 $GMGSHA (frozen A.6 v2) OK"

# 1. inputs
label "E0b inputs"
"$PY" -I $CJOB/c0b_fetch.py --run $RUN_ID --inputs $IN --depth $DEPTH ${E0B_STORE_LOCAL:+--local $E0B_STORE_LOCAL} \
  ${E0B_EPS:+--eps "$E0B_EPS"} --split eval --workers ${E0B_DL_WORKERS:-10} > $R/logs/fetch.log 2>&1 || fail "inputs: $(tail -1 $R/logs/fetch.log)"
log "inputs: $(grep -c . $IN/SHA256SUMS) files sha256 OK; depth $(tail -1 $R/logs/fetch.log)"
cp $IN/plan.json $R/ && cp $IN/SHA256SUMS $R/inputs_SHA256SUMS && cp $IN/t0_c0b.json $R/t0_c0b.json
log "t0_C0b (public, frozen): $("$PY" -c "import json; j=json.load(open('$R/t0_c0b.json')); print(j['t0_m'], 'fittable', j['fittable'])")"
if [ -n "${E0B_EPS:-}" ]; then   # dry subset: keep only these episodes in the plan
  "$PY" -I -c "
import json; p=json.load(open('$IN/plan.json')); keep=set('$E0B_EPS'.split())
p['episodes']={e:v for e,v in p['episodes'].items() if e in keep}
p['candidate_eps']={o:[e for e in v if str(e) in keep] for o,v in p['candidate_eps'].items()}
p['all_set']={o:[e for e in v if str(e) in keep] for o,v in p['all_set'].items()}
p['all_set']={o:v for o,v in p['all_set'].items() if v}
p['marker_objects']={e:v for e,v in p['marker_objects'].items() if e in keep}
for o,v in p['frame_refs'].items(): v['references']=v['references'][:2]; v['n_references']=len(v['references'])
json.dump(p, open('$R/plan.json','w'), indent=1)"
fi
cat > $R/env.json << JSON
{"PY": "$PY", "REPO": "$REPO_DIR", "R": "$R", "IN": "$IN", "DEPTH": "$DEPTH", "KIT": "$IN/kit", "STRIDE": "$STRIDE"}
JSON
T() { "$PY" -I $JOBD/e0b_tasks.py $1 --plan $R/plan.json --env $R/env.json > $R/commands/$1.txt || fail "task list $1"; }

# frame-check references first (public meshes only; independent of every eval stage), in the background
T fref; ( prun fref $FRP; "$PY" -I $JOBD/e0b_prep.py fthr $R/frame_thresholds.json $R/plan.json $R/fref > $R/logs/fthr.log 2>&1 \
  && log "frame thresholds: $(tr '\n' ' ' < $R/logs/fthr.log | cut -c1-900)" || log "frame thresholds FAILED: $(tail -3 $R/logs/fthr.log)" ) &
FREF=$!

# 2-3. observed points
T obsA; prun obsA $OBSP
T obsB; prun obsB $OBSP
for f in $R/guard/*.jsonl; do log "cube guard $(basename $f .jsonl): $(tr '\n' ' ' < $f)"; done
[ "$(cnt '^FAIL' $R/status/obsB.txt)" = 0 ] || log "WARNING: obsB failures (those object-episodes have no E0b points)"

# 4-5. derived points, thickness rows, sigma
T derive; prun derive
log "M_sep: $(grep -h '"qualifies"' $R/logs/derive/*.log | cut -c1-400 | tr '\n' ' ')"
T derive2; prun derive2
T measure; prun measure

# 6. markers (the long stage)
T markers; prun markers
for f in $R/logs/markers/*.log; do log "markers $(basename $f .log): $(tail -1 $f | cut -c1-400)"; done

# 7. params + builds
"$PY" -I $JOBD/e0b_tasks.py params --plan $R/plan.json --env $R/env.json > $R/logs/params.log 2>&1 || fail "params: $(tail -2 $R/logs/params.log)"
T build; prun build
"$PY" -I $JOBD/e0b_tasks.py candidates --plan $R/plan.json --env $R/env.json > $R/candidates.json || fail "candidate list"
log "candidates built: $("$PY" -c "import json,collections; c=json.load(open('$R/candidates.json')); print(len(c), dict(collections.Counter(x['object'] for x in c)))")"

# 8. checks, frame check, fidelity; 9. pick
wait $FREF
T check; T frame; T fid
prun check; prun frame $FRP; prun fid $FIDP
"$PY" -I $JOBD/e0b_select.py --results $R --cands $R/candidates.json --plan $R/plan.json --adopted $ADOPTED > $R/logs/select.log 2>&1 \
  && log "select: $(tr '\n' ' ' < $R/logs/select.log)" || log "select FAILED: $(tail -3 $R/logs/select.log)"

# 10. reported only (after the pick): C0's meshes, library_v3 (+ v3x beige), E0's picks on the same points
T report; prun report $FIDP
finish 0
