#!/bin/bash
# C0b public box job (PREREG docs/research/mesh-2026-10-26/cdo-sprint/C0b/PREREG.md, sections 2-5, 10, 11): the C0 mesh
# methods rebuilt on the public episodes with every scan-derived or unknown constant replaced (option flags), on one
# many-core CPU box. Started by ops/box/run_job.sh with SETUP=none (stall watchdog, push of /content/results to the HF
# store runs/<RUN_ID>/, self-destroy; ops/box/lib.sh). Steps, each in parallel (xargs -P):
#   0. venv (c0b_setup.sh, E0's pinned req_main.txt)
#   1. inputs: store runs/<RUN_ID>/inputs/ (c0b_stage.py; sha256-checked) + public depth (size + LFS sha256 checked)
#   2. obsA: obs_points.py --roi_cube 0.30, no co-objects, every tracked object of the 20 public episodes (33 files);
#      cube guard (rebuild once at 0.45 m)
#   3. obsB: the final files, --others_pts = the co-objects' pass-A points (single-object episodes: pass B = pass A)
#   4. derive: beige ep11 M_sep(own) mask; blue cup ep21+22 merged points
#   5. measure: thickness.py rows (33 + beige masked) and gmg A.2 sigma of every build input; 6. t0_C0b (A.1)
#   7. markers: gmg markers.detect_episode per episode (frozen A.6 settings, sha asserted)
#   8. params (thickness chain, 3 sigma) and builds: pot 8 x {fit, nostem, nomk, thick}; lid 2 x {a6b1, a6b2} x
#      {fit, nostem, nomk, thick}; rack prim_rack.py run (full, nomk per episode; joint, joint_nomk); blue cup g1/g0 on
#      21, 22 + merged g1; beige g1/g0 on the masked ep11 points
#   9. fidelity (ALL + per episode) and exclusion checks (watertight raw, kit budget); 10. c0b_select.py (the pick)
#  11. report (after the pick is written; reported only): fidelity of C0's meshes and library_v3 on the same points
#  12. SHA256SUMS, push to the store, exit (run_job.sh self-destroys)
# Inputs never include scans, mocap, parquet poses or *_align files. Progress lines go to results/c0b/c0b_job.log.
# Box:   bash docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs/c0b_box.sh       (RUN_ID from ops/vast.sh)
# Local dry run (no store writes): C0B_LOCAL=1 C0B_ROOT=<dir> C0B_STORE_LOCAL=<fake store> C0B_SETUP=0 C0B_PY=<python>
#   C0B_EPS="11 12" C0B_STRIDE=8 RUN_ID=<id> bash c0b_box.sh   (C0B_STRIDE != 2 marks the run DRY)
set -u
JOBD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -z "${C0B_LOCAL:-}" ]; then
  . /content/v2d-track3/ops/box/lib.sh
else
  REPO_DIR=$(cd $JOBD/../../../../../.. && pwd)
  log() { echo "[$(date -u +%FT%TZ)] $*"; }; label() { :; }
fi
: "${RUN_ID:?RUN_ID is not set}"
ROOT=${C0B_ROOT:-/content}; W=$ROOT/c0bw; R=$ROOT/results/c0b; IN=$W/inputs; DEPTH=$W/depth
NPROC=${C0B_NPROC:-$(nproc)}; STRIDE=${C0B_STRIDE:-2}
PY=${C0B_PY:-$W/venv/bin/python}
RAMGB=$(free -g | awk '/Mem/{print $2}')
FIDP=$(( RAMGB / 8 )); [ $FIDP -gt $NPROC ] && FIDP=$NPROC; [ $FIDP -lt 1 ] && FIDP=1    # obs_fidelity loads ALL points
OBSP=$(( RAMGB / 6 )); [ $OBSP -gt $NPROC ] && OBSP=$NPROC; [ $OBSP -lt 1 ] && OBSP=1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2}
export HF_HUB_DISABLE_PROGRESS_BARS=1 HF_XET_CHUNK_CACHE_SIZE_BYTES=0 PYTHONDONTWRITEBYTECODE=1
export GMG_DATA_ROOT=$W GMG_MODE=clean          # gmg guard roots (its audit hook refuses ground-truth paths)
[ "$STRIDE" != 2 ] && export C0B_STRIDE=$STRIDE
mkdir -p $W $R/{logs/{obsA,obsB,derive,measure,t0,markers,build,fid,check,report},status,pts/{A,B,M},guard,thick,sigma,markers,axis,commands} \
  $R/cand/{white_pot,white_pot_lid,blue_cup,beige_cup,rack} $R/fid/{pot,lid,rack,cup,beige} $R/check/{pot,lid,rack,cup,beige} \
  $R/report/{pot,lid,rack,cup,beige}
exec >> $R/c0b_job.log 2>&1
T0=$(date +%s)
log "C0b job start: run $RUN_ID commit $(git -C $REPO_DIR rev-parse HEAD) dirty=$(git -C $REPO_DIR status --porcelain -- docs/research/mesh-2026-10-26/scripts docs/research/mesh-2026-10-26/gmg/markers.py docs/research/mesh-2026-10-26/gmg/thickness.py docs/research/mesh-2026-10-26/gmg/bundle.py docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs pipeline | wc -l) cpus $NPROC ram $RAMGB GB (obs workers $OBSP, fid workers $FIDP) disk $(df -h $ROOT | awk 'NR==2{print $4}') free; stride $STRIDE${C0B_EPS:+, episodes [$C0B_EPS] (DRY subset)}"
[ "$STRIDE" = 2 ] || log "DRY: obs_points stride $STRIDE (production is the public default 2)"
fail() { log "C0B-FAIL: $*"; label "C0b FAIL: $*"; finish 1; }
cnt() { local n; n=$(grep -c "$1" "$2" 2> /dev/null); echo ${n:-0}; }
cputot() { ps -eo cputimes,comm --no-headers 2> /dev/null | awk '$2 ~ /python/ {s += $1} END {print s + 0}'; }
progress() {  # one line per minute when a status changed; every 5 min a CPU heartbeat if worker CPU time grew
  local last="" lastcpu=0 k=0
  while sleep 60; do
    k=$((k + 1))
    local cur="$(for s in obsA obsB derive measure t0 markers build fid check report; do printf '%s %s/%s ' $s $(cnt '^OK' $R/status/$s.txt) $(cnt '^FAIL' $R/status/$s.txt); done) files $(find $R -type f | wc -l)"
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
  log "stage $1: $n tasks, $p workers"; label "C0b $1 ($n tasks)"
  [ "$n" -gt 0 ] && xargs -d '\n' -P $p -n 1 bash -c < $R/commands/$1.txt
  log "stage $1 done: OK $(cnt '^OK' $R/status/$1.txt) FAIL $(cnt '^FAIL' $R/status/$1.txt)" \
      "$(grep '^FAIL' $R/status/$1.txt 2> /dev/null | cut -d' ' -f2 | tr '\n' ' ')"
}
finish() {
  kill $PROG 2> /dev/null
  (cd $R && find . -type f ! -name SHA256SUMS ! -name c0b_job.log -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  log "SHA256SUMS: $(wc -l < $R/SHA256SUMS) files, $(du -sh $R | cut -f1); total $(( ($(date +%s) - T0) / 60 )) min"
  if [ -n "${C0B_LOCAL:-}" ]; then
    log "local run: no store push"
  else
    label "C0b push"; bash $OPS/store.sh push-run && log "C0b pushed to the store runs/$RUN_ID" || log "C0b push FAILED (run_job.sh pushes again before destroy)"
  fi
  log "C0B-$([ $1 = 0 ] && echo DONE || echo INCOMPLETE) rc=$1"
  exit $1
}
progress & PROG=$!

# 0. environment
if [ "${C0B_SETUP:-1}" = 1 ]; then
  label "C0b setup"; log "setup venv"
  bash $JOBD/c0b_setup.sh $W $R/logs/setup.log || fail "setup (main venv)"
  cp $W/freeze_main.txt $R/ 2> /dev/null
fi
"$PY" -c "import numpy, trimesh, manifold3d, skimage" || fail "python $PY"
GMGSHA=$(cd $JOBD && "$PY" -I -c "import sys; sys.path.insert(0, '$REPO_DIR/docs/research/mesh-2026-10-26'); from gmg import markers; print(markers.SETTINGS_SHA256)") \
  || fail "gmg markers import"
[ "$GMGSHA" = 488ac3b638aa7e68c12843a5b761ed8882106bc78d8307d9e3059932502aa128 ] || fail "markers settings sha $GMGSHA"
log "gmg markers settings sha256 $GMGSHA (frozen A.6 v2) OK"

# 1. inputs
label "C0b inputs"
"$PY" -I $JOBD/c0b_fetch.py --run $RUN_ID --inputs $IN --depth $DEPTH ${C0B_STORE_LOCAL:+--local $C0B_STORE_LOCAL} \
  ${C0B_EPS:+--eps "$C0B_EPS"} --split public --workers ${C0B_DL_WORKERS:-10} > $R/logs/fetch.log 2>&1 || fail "inputs: $(tail -1 $R/logs/fetch.log)"
log "inputs: $(grep -c . $IN/SHA256SUMS) files sha256 OK; depth $(tail -1 $R/logs/fetch.log)"
cp $IN/plan.json $R/ && cp $IN/SHA256SUMS $R/inputs_SHA256SUMS
if [ -n "${C0B_EPS:-}" ]; then   # dry subset: keep only these episodes in the plan
  "$PY" -I -c "
import json; p=json.load(open('$IN/plan.json')); keep=set('$C0B_EPS'.split())
p['episodes']={e:v for e,v in p['episodes'].items() if e in keep}
p['candidate_eps']={o:[e for e in v if str(e) in keep] for o,v in p['candidate_eps'].items()}
p['all_set']={o:[e for e in v if str(e) in keep] for o,v in p['all_set'].items()}
p['all_set']={o:v for o,v in p['all_set'].items() if v}
p['marker_objects']={e:v for e,v in p['marker_objects'].items() if e in keep}
json.dump(p, open('$R/plan.json','w'), indent=1)"
fi
cat > $R/env.json << JSON
{"PY": "$PY", "REPO": "$REPO_DIR", "R": "$R", "IN": "$IN", "DEPTH": "$DEPTH", "KIT": "$IN/kit", "STRIDE": "$STRIDE"}
JSON
T() { "$PY" -I $JOBD/c0b_tasks.py $1 --plan $R/plan.json --env $R/env.json > $R/commands/$1.txt || fail "task list $1"; }

# 2-3. observed points
T obsA; prun obsA $OBSP
T obsB; prun obsB $OBSP
for f in $R/guard/*.jsonl; do log "cube guard $(basename $f .jsonl): $(tr '\n' ' ' < $f)"; done
[ "$(cnt '^FAIL' $R/status/obsB.txt)" = 0 ] || log "WARNING: obsB failures (those object-episodes have no C0b points)"

# 4-6. derived points, thickness rows, sigma, t0_C0b
T derive; prun derive
T measure; prun measure
T t0; prun t0 1
log "t0_C0b: $(tail -1 $R/logs/t0/t0.log)"
log "M_sep: $(grep -h '"qualifies"' $R/logs/derive/*.log | head -3 | tr '\n' ' ')"

# 7. markers (the long stage)
T markers; prun markers
for f in $R/logs/markers/*.log; do log "markers $(basename $f .log): $(tail -1 $f | cut -c1-400)"; done

# 8. params + builds
"$PY" -I $JOBD/c0b_tasks.py params --plan $R/plan.json --env $R/env.json > $R/logs/params.log 2>&1 || fail "params: $(tail -2 $R/logs/params.log)"
T build; prun build
"$PY" -I $JOBD/c0b_tasks.py candidates --plan $R/plan.json --env $R/env.json > $R/candidates.json || fail "candidate list"
log "candidates built: $("$PY" -c "import json,collections; c=json.load(open('$R/candidates.json')); print(len(c), dict(collections.Counter(x['object'] for x in c)))")"

# 9. fidelity + exclusion checks, 10. pick
T fid; T check
prun check; prun fid $FIDP
"$PY" -I $JOBD/c0b_select.py --results $R --cands $R/candidates.json > $R/logs/select.log 2>&1 \
  && log "select: $(tr '\n' ' ' < $R/logs/select.log)" || log "select FAILED: $(tail -3 $R/logs/select.log)"

# 11. reported only (after the pick): C0's meshes and library_v3 on the same points
T report; prun report $FIDP
finish 0
