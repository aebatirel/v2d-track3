#!/bin/bash
# PUBOWN box job (PLAN docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/PLAN.md): one clean C0b-family mesh per public
# (episode, object) pair, built only from that episode's own observed points, for the perception re-track test. Adapted
# from E0's e0_box.sh and C0b's c0b_box.sh. Started by ops/box/run_job.sh with SETUP=none (stall watchdog, push of
# /content/results to the HF store runs/<RUN_ID>/, self-destroy; ops/box/lib.sh). Steps (xargs -P):
#   0. venv (C0b's c0b_setup.sh = E0's pinned req_main.txt); gmg marker settings sha; code sha256 = C0b box commit
#   1. inputs: store runs/<RUN_ID>/inputs/ (pubown_stage.py; sha256-checked) + the reused C0b public-box outputs
#      (runs/<c0b run>/results/c0b/: pass-B points, thickness rows, sigma, markers, t0_C0b, beige M_sep json;
#      sha256 = C0b's SHA256SUMS), symlinked into results/pubown (symlinks are not re-pushed)
#   2. sigma of the pairs C0b did not measure; 3. markers of the episodes whose prim-object set differs from C0b's (ep0)
#   4. params (C0b thickness chain per pair, own measurements; t0_C0b) and builds: pot {fit, nostem, nomk, thick},
#      lid {a6b1, a6b2} x {fit, nostem, nomk, thick}, blue cup / beige {g1, g0} per pair (C0b's own build lines);
#      rack prim_rack.py run --episodes <e> per episode (full, nomk)
#   5. exclusion checks (watertight raw, kit budget) and obs_fidelity on the pair's own points; 6. per-pair pick
#      (pubown_select.py) -> meshes/ep<N>/<object>.glb + manifest.tsv
#   7. SHA256SUMS, push to the store, exit (run_job.sh self-destroys)
# Inputs never include scans, mocap, parquet poses or *_align files. Nothing is scored here.
# Box:   bash docs/research/mesh-2026-10-26/cdo-sprint/PUBOWN/jobs/pubown_box.sh      (RUN_ID from ops/vast.sh)
# Local dry run (no store writes): PUB_LOCAL=1 PUB_ROOT=<dir> PUB_STORE_LOCAL=<fake store> PUB_SETUP=0 PUB_PY=<python>
#   RUN_ID=<id> bash pubown_box.sh
set -u
JOBD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -z "${PUB_LOCAL:-}" ]; then
  . /content/v2d-track3/ops/box/lib.sh
else
  REPO_DIR=$(cd $JOBD/../../../../../.. && pwd)
  log() { echo "[$(date -u +%FT%TZ)] $*"; }; label() { :; }
fi
: "${RUN_ID:?RUN_ID is not set}"
ROOT=${PUB_ROOT:-/content}; W=$ROOT/pubw; R=$ROOT/results/pubown; IN=$W/inputs; REUSE=$W/reuse
NPROC=${PUB_NPROC:-$(nproc)}
RAMGB=$(free -g | awk '/Mem/{print $2}')
FIDP=$(( RAMGB / 8 )); [ $FIDP -gt $NPROC ] && FIDP=$NPROC; [ $FIDP -lt 1 ] && FIDP=1    # obs_fidelity: C0b's RAM rule
PY=${PUB_PY:-$W/venv/bin/python}
C0B_COMMIT=00e858434419b3e6bb11508ec8b35e092d76199f    # C0b public box code; checked against plan.json below
CODE=$W/code                                          # the code tree at C0B_COMMIT (pubown_freeze.sh); builders run from here
C0BJ=$CODE/docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-2} MKL_NUM_THREADS=${MKL_NUM_THREADS:-2}
export HF_HUB_DISABLE_PROGRESS_BARS=1 HF_XET_CHUNK_CACHE_SIZE_BYTES=0 PYTHONDONTWRITEBYTECODE=1
export GMG_DATA_ROOT=$W GMG_MODE=clean          # gmg guard roots (its audit hook refuses ground-truth paths)
mkdir -p $W $R/{logs/{sigma,markers,build,fid,check},status,pts/B,thick,sigma,markers,axis,commands,meshes} \
  $R/cand/{white_pot,white_pot_lid,blue_cup,beige_cup,rack} $R/fid/{pot,lid,rack,cup,beige} $R/check/{pot,lid,rack,cup,beige}
exec >> $R/pubown_job.log 2>&1
T0=$(date +%s)
log "PUBOWN job start: run $RUN_ID commit $(git -C $REPO_DIR rev-parse HEAD) workers $NPROC (fid $FIDP) ram $RAMGB GB disk $(df -h $ROOT | awk 'NR==2{print $4}') free"
fail() { log "PUBOWN-FAIL: $*"; label "PUBOWN FAIL: $*"; finish 1; }
cnt() { local n; n=$(grep -c "$1" "$2" 2> /dev/null); echo ${n:-0}; }
cputot() { ps -eo cputimes,comm --no-headers 2> /dev/null | awk '$2 ~ /python/ {s += $1} END {print s + 0}'; }
progress() {  # one line per minute when a status changed; every 5 min a CPU heartbeat if worker CPU time grew
  local last="" lastcpu=0 k=0
  while sleep 60; do
    k=$((k + 1))
    local cur="$(for s in sigma markers build check fid; do printf '%s %s/%s ' $s $(cnt '^OK' $R/status/$s.txt) $(cnt '^FAIL' $R/status/$s.txt); done) files $(find $R -type f | wc -l)"
    [ "$cur" != "$last" ] && log "progress (ok/fail): $cur load $(cut -d' ' -f1 /proc/loadavg)" && last=$cur
    if [ $((k % 5)) = 0 ]; then
      local c; c=$(cputot)
      [ "$c" -gt "$lastcpu" ] && log "alive: python workers cpu $c s (+$((c - lastcpu)) s), load $(cut -d' ' -f1 /proc/loadavg), mem used $(free -g | awk '/Mem/{print $3}') GB"
      lastcpu=$c
    fi
  done
}
prun() {  # $1 command list [$2 workers [$3 status stage]]: run commands/<$1>.txt; the tasks write status/<$3>.txt
  local n p=${2:-$NPROC} st=${3:-$1}; n=$(grep -c . $R/commands/$1.txt || true)
  log "stage $1: $n tasks, $p workers"; label "PUBOWN $1 ($n tasks)"
  [ "$n" -gt 0 ] && xargs -d '\n' -P $p -n 1 bash -c < $R/commands/$1.txt
  log "stage $1 done: status/$st.txt OK $(cnt '^OK' $R/status/$st.txt) FAIL $(cnt '^FAIL' $R/status/$st.txt)" \
      "$(grep '^FAIL' $R/status/$st.txt 2> /dev/null | cut -d' ' -f2 | tr '\n' ' ')"
}
finish() {
  kill $PROG 2> /dev/null
  (cd $R && find . -type f ! -name SHA256SUMS ! -name pubown_job.log -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  log "SHA256SUMS: $(wc -l < $R/SHA256SUMS) files, $(du -sh $R | cut -f1); total $(( ($(date +%s) - T0) / 60 )) min"
  if [ -n "${PUB_LOCAL:-}" ]; then
    log "local run: no store push"
  else
    label "PUBOWN push"; bash $OPS/store.sh push-run && log "PUBOWN pushed to the store runs/$RUN_ID" || log "PUBOWN push FAILED (run_job.sh pushes again before destroy)"
  fi
  log "PUBOWN-$([ $1 = 0 ] && echo DONE || echo INCOMPLETE) rc=$1"
  exit $1
}
progress & PROG=$!

# 0. pinned code + environment
bash $JOBD/pubown_freeze.sh $REPO_DIR $C0B_COMMIT $CODE > $R/frozen_code.json 2> $R/logs/freeze.log || fail "freeze: $(tail -2 $R/logs/freeze.log)"
log "code tree at C0b commit $C0B_COMMIT: $(cat $R/frozen_code.json)"
if [ "${PUB_SETUP:-1}" = 1 ]; then
  label "PUBOWN setup"; log "setup venv"
  bash $C0BJ/c0b_setup.sh $W $R/logs/setup.log || fail "setup (main venv)"
  cp $W/freeze_main.txt $R/ 2> /dev/null
fi
"$PY" -c "import numpy, trimesh, manifold3d, skimage" || fail "python $PY"
GMGSHA=$("$PY" -I -c "import sys; sys.path.insert(0, '$CODE/docs/research/mesh-2026-10-26'); from gmg import markers; print(markers.SETTINGS_SHA256)") \
  || fail "gmg markers import"
[ "$GMGSHA" = 488ac3b638aa7e68c12843a5b761ed8882106bc78d8307d9e3059932502aa128 ] || fail "markers settings sha $GMGSHA"
log "gmg markers settings sha256 $GMGSHA (frozen A.6 v2) OK"

# 1. inputs + reused C0b outputs
label "PUBOWN inputs"
"$PY" -I $JOBD/pubown_fetch.py --run $RUN_ID --inputs $IN --reuse $REUSE ${PUB_STORE_LOCAL:+--local $PUB_STORE_LOCAL} \
  --workers ${PUB_DL_WORKERS:-10} > $R/logs/fetch.log 2>&1 || fail "inputs: $(tail -1 $R/logs/fetch.log)"
log "inputs: $(grep -c . $IN/SHA256SUMS) files sha256 OK; reuse $(tail -1 $R/logs/fetch.log)"
cp $IN/plan.json $R/ && cp $IN/SHA256SUMS $R/inputs_SHA256SUMS
"$PY" -I -c "
import json, sys
p = json.load(open('$R/plan.json')); f = json.load(open('$R/frozen_code.json'))
ok = p['c0b_code_commit'] == f['commit'] == '$C0B_COMMIT' and p['frozen_code'] == f
print(json.dumps(dict(plan_commit=p['c0b_code_commit'], box_commit=f['commit'], trees_equal=p['frozen_code'] == f)))
sys.exit(0 if ok else 1)" > $R/logs/frozen_code.log 2>&1 || fail "code tree differs from the staged plan: $(cat $R/logs/frozen_code.log)"
log "code: $(cat $R/logs/frozen_code.log)"
"$PY" -I -c "
import json, os
p = json.load(open('$R/plan.json'))
for rel in p['reuse']:
    d = os.path.join('$R', rel); os.makedirs(os.path.dirname(d), exist_ok=True)
    os.path.lexists(d) or os.symlink(os.path.join('$REUSE', rel), d)
print(len(p['reuse']), 'reused C0b files linked')" > $R/logs/link.log 2>&1 || fail "link reuse: $(tail -2 $R/logs/link.log)"
log "$(cat $R/logs/link.log); t0_C0b $("$PY" -I -c "import json; j=json.load(open('$R/t0_c0b.json')); print(j['t0_m'], 'fittable', j['fittable'])")"
cat > $R/env.json << JSON
{"PY": "$PY", "REPO": "$CODE", "R": "$R", "IN": "$IN", "DEPTH": "-", "KIT": "$IN/kit", "STRIDE": "2"}
JSON
T() { "$PY" -I $JOBD/pubown_tasks.py $1 --plan $R/plan.json --env $R/env.json > $R/commands/$1.txt || fail "task list $1"; }

# 2. sigma C0b did not compute (needed by params and by the new marker detections)
T sigma; prun sigma
# 3-4. params (thickness chain + 3 sigma; reads no marker file), then the new marker detections (the long pole) run
# in the background while every build that does not read a new marker file runs; the rest builds after them
"$PY" -I $JOBD/pubown_tasks.py params --plan $R/plan.json --env $R/env.json > $R/logs/params.log 2>&1 || fail "params: $(tail -2 $R/logs/params.log)"
T markers; T build
"$PY" -I -c "
import json; p = json.load(open('$R/plan.json')); E = p['recompute']['markers']
L = [l for l in open('$R/commands/build.txt').read().splitlines() if l.strip()]
late = lambda l: any(f'markers/ep{e}.json' in l or f' --episodes {e} ' in l for e in E)
open('$R/commands/build_a.txt', 'w').write(''.join(l + chr(10) for l in L if not late(l)))
open('$R/commands/build_b.txt', 'w').write(''.join(l + chr(10) for l in L if late(l)))
print(len(L), 'build tasks:', sum(not late(l) for l in L), 'now,', sum(map(late, L)), 'after markers of', E)" > $R/logs/split.log 2>&1 \
  || fail "build split: $(tail -2 $R/logs/split.log)"
log "$(cat $R/logs/split.log)"
prun markers $NPROC & MPID=$!
prun build_a $NPROC build
wait $MPID
for f in $R/logs/markers/*.log; do [ -f "$f" ] && log "markers $(basename $f .log): $(tail -1 $f | cut -c1-400)"; done
prun build_b $NPROC build
"$PY" -I $JOBD/pubown_tasks.py candidates --plan $R/plan.json --env $R/env.json > $R/candidates.json || fail "candidate list"
log "candidates built: $("$PY" -c "import json,collections; c=json.load(open('$R/candidates.json')); print(len(c), dict(collections.Counter(x['object'] for x in c)))")"

# 5. checks + own-point fidelity, 6. per-pair pick
T check; T fid
prun check; prun fid $FIDP
"$PY" -I $JOBD/pubown_select.py --results $R --cands $R/candidates.json --plan $R/plan.json > $R/logs/select.log 2>&1 \
  && log "select: $(tr '\n' ' ' < $R/logs/select.log | cut -c1-3000)" || log "select FAILED: $(tail -3 $R/logs/select.log)"
finish 0
