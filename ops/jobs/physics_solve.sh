#!/bin/bash
# Physics solver, GPU stage G1 (2026-10-30; owner approved option 3 "go nuts with all"; GPU cap ~$2 for this step).
# Pre-registered bar, settings and reading: docs/research/physics-2026-10-30/physics-solver.md section 5.1 (written
# before any GPU result). No ground truth: every score is sim_vs_ref against OUR reference (pipeline/qa.py's metric).
# Per public episode (EPS, run concurrently on the one GPU):
#   0. input = the stored grasp-lock + ILC (+ EVOLVE) reference of the S1 physics arm (store run SRC,
#      refs/glockt/ep<N>/processed/*/*/ref_gl_ilc.parquet), objects = NVIDIA's public scans with the S1 plausible
#      masses (make_assets --physics props_public_scans.json on /content/scanlib, exactly as ops/jobs/physics_arms.sh).
#      Missing in SRC -> the same episode from ALT (the S0 arm's reference, built under placeholder masses; run here
#      with the S1 assets; logged). Missing in both -> rebuilt here from the 24 Oct base reference with
#      pipeline/grasp_lock.py + pipeline/wrist_ilc.py (the CPU recipe of tools/cpu_glock_zero.sh, no EVOLVE; logged);
#   1. tools/physics_solve/jitter_check.py on that reference: JK worlds (copy 0 = the plain zero-action replay, the
#      others with N(0, 0.5 mm) wrist-position and N(0, 0.005 rad) finger target noise on every frame, seed 0);
#   2. tools/physics_solve/solve.py --device cuda SOLVE_ARGS --deadline_s (DLPF x frames) -> ref_ps.parquet;
#   3. official zero-action replay of ref_ps (tools/trace_rollout.py zero, DEV=cuda) + tools/trace_score.py (nominal);
#   4. jitter_check.py on ref_ps with the same K and seed (same noise draws: common random numbers).
# Summary /content/results/physics_solve/summary.json: per episode both jittered means/sds, the difference, nominal
# scores, solve wall time / deadline / rollbacks, input source; verdict PASS iff the solved jittered mean beats the
# grasp lock + ILC one by >= 0.03 on >= 2 of the 4 episodes (an episode that fails counts as not beating it).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'bash ops/jobs/physics_solve.sh'
# Knobs (defaults = the pre-registered G1 settings): EPS SRC ALT JK DLPF SOLVE_ARGS.
. /content/v2d-track3/ops/box/lib.sh
R=$REPO_DIR; T=$R/tools; P=$R/pipeline; J=${J:-/content/job.log}
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/physics_solve; mkdir -p $O
EPS=${EPS:-"2 12 18 24"}; SRC=${SRC:-20261030-physS1-6a814df}; ALT=${ALT:-20261030-physS0-6a814df}
JK=${JK:-64}; DLPF=${DLPF:-4}
SOLVE_ARGS=${SOLVE_ARGS:-"--worlds 1024 --robust 4 --horizon 20 --knot 4 --ctrl 4 --iters 4 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.6 --retries 6 --retry 0.05 --back 3 --rob_pos 0.0005 --rob_fin 0.005 --seed 0"}
GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"
declare -A BASE=([2]="20261024-ev3-2c1e4dd:mck" [12]="20261024-ev2-2c1e4dd:mc" [18]="20261024-ev3-2c1e4dd:mc" [24]="20261024-ev3-2c1e4dd:mc")
export EMB=sharpa_hands_mid OMP_NUM_THREADS=1
log "physics_solve code $(git -C $R rev-parse --short HEAD), eps [$EPS], src $SRC (alt $ALT), JK $JK, DLPF $DLPF, SOLVE_ARGS [$SOLVE_ARGS]" >> $J
label "physics_solve: assets"

# objects: NVIDIA's public scans + S1 plausible masses (as physics_arms.sh ARM=S1)
mkdir -p /content/scanlib
for d in /content/t3/mesh/*/; do
  n=$(basename $d); f=$d/$n.glb; [ -f $f ] || f=$d/${n}_collision.glb
  [ -f $f ] && [ "$n" != wooden_spoon ] && ln -sf $f /content/scanlib/$n.glb
done
python $P/make_assets.py /content/scanlib /content/assets --physics $R/docs/research/physics-2026-10-30/props_public_scans.json >> $J 2>&1 \
  || { log "make_assets FAILED" >> $J; exit 1; }
grep -h mass /content/assets/urdf/*.urdf > $O/asset_masses.txt 2>&1
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml   # kp 400 wrist embodiment
[ -s $E ] || cp $R/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }

fix_assets() {  # as glock_public.sh: a reference names the absolute asset root of the box that built it
  python - "$1" << 'EOF'
import os, sys, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1])
for r in sorted({os.path.dirname(os.path.dirname(p)) for p in t.column('object_urdf_paths')[0].as_py() if not os.path.exists(p)}):
    if r.startswith('/content/') and not os.path.lexists(r):
        os.symlink('/content/assets', r); print('linked', r, '-> /content/assets')
    else:
        print('MISSING assets under', r); sys.exit(1)
EOF
}
ref_of() { ls /content/refs/glockt/ep$1/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1; }

# inputs: SRC, then ALT for what is missing, then a rebuild here
label "physics_solve: inputs"
PULL_SUB="$(for e in $EPS; do echo -n "refs/glockt/ep$e "; done)" bash $OPS/store.sh pull-run $SRC >> $J 2>&1 || log "pull-run $SRC: error (checking per episode)" >> $J
declare -A SRCOF
for e in $EPS; do [ -n "$(ref_of $e)" ] && SRCOF[$e]=$SRC; done
miss=$(for e in $EPS; do [ -z "${SRCOF[$e]:-}" ] && echo -n "$e "; done)
if [ -n "$miss" ]; then
  log "physics_solve: not in $SRC: ep [$miss]; trying $ALT" >> $J
  PULL_SUB="$(for e in $miss; do echo -n "refs/glockt/ep$e "; done)" bash $OPS/store.sh pull-run $ALT >> $J 2>&1 || true
  for e in $miss; do [ -n "$(ref_of $e)" ] && SRCOF[$e]=$ALT; done
fi
rebuild() {  # $1 episode: grasp lock + ILC on the 24 Oct base reference (tools/cpu_glock_zero.sh recipe, on the GPU)
  local ep=$1 run base R0 P0 hive G LG=/content/rebuild_ep$1.log
  IFS=: read -r run base <<< "${BASE[$ep]}"
  PULL_SUB="refs/perc2$base/ep$ep" bash $OPS/store.sh pull-run $run >> $LG 2>&1 || true
  R0=/content/refs/perc2$base/ep$ep; P0=$(ls $R0/processed/*/*/*.parquet 2> /dev/null | head -1)
  [ -s "$P0" ] || { log "physics_solve ep$ep: no base reference in $run" >> $J; return 1; }
  fix_assets $P0 >> $LG 2>&1 || return 1
  hive=$(dirname ${P0#$R0/}); G=/content/refs/glockt/ep$ep; mkdir -p $G/$hive; cp -r $R0/reconstructed_stage $G/
  ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 $G/$hive/ref_gl.parquet $GL_ARGS ) >> $LG 2>&1 || return 1
  ( cd $FC && .venv/bin/python $P/wrist_ilc.py $G/$hive/ref_gl.parquet $G/$hive/ref_gl_ilc.parquet --iters 4 --device cuda ) >> $LG 2>&1 || return 1
  log "physics_solve ep$ep: reference rebuilt here from $run perc2$base (grasp lock + ILC, no EVOLVE)" >> $J
}
for e in $EPS; do
  [ -n "${SRCOF[$e]:-}" ] && continue
  rebuild $e && SRCOF[$e]="rebuilt:${BASE[$e]}" || log "physics_solve ep$e: no input reference (skipped)" >> $J
done
for e in $EPS; do log "physics_solve ep$e input: ${SRCOF[$e]:-none} $(ref_of $e)" >> $J; done

jitter() {  # $1 episode $2 reference $3 tag
  ( cd $FC && DEV=cuda .venv/bin/python $T/physics_solve/jitter_check.py $2 --device cuda --k $JK --seed 0 \
      --json $O/ep$1/jitter_$3.json ) >> $O/ep$1/jitter_$3.log 2>&1
}
prep() {  # $1 episode: the solver's working tree /content/refs/psolve/ep<N> (reference + reconstructed_stage)
  local ep=$1 P0 hive W
  P0=$(ref_of $ep); fix_assets $P0 >> $O/ep$ep/prep.log 2>&1 || return 1
  hive=$(dirname ${P0#/content/refs/glockt/ep$ep/}); W=/content/refs/psolve/ep$ep
  mkdir -p $W/$hive; cp -r /content/refs/glockt/ep$ep/reconstructed_stage $W/; cp $P0 $W/$hive/ref_in.parquet
  echo $W/$hive
}
one() {
  local ep=$1 D N DL t0
  D=$(prep $ep) || { log "physics_solve ep$ep: assets missing" >> $J; return 1; }
  N=$(python -c "import pyarrow.parquet as pq; print(len(pq.read_table('$D/ref_in.parquet').column('robot_left_wrist_position')[0].as_py()))")
  [ -s $O/ep$ep/jitter_glock.json ] || jitter $ep $D/ref_in.parquet glock
  log "physics_solve ep$ep: grasp lock + ILC jittered $(python -c "import json; d=json.load(open('$O/ep$ep/jitter_glock.json')); print('nominal', d['nominal'], 'mean', d['mean'], 'sd', d['sd'], 'wall', d['wall_s'])" 2>&1 | tail -1)" >> $J
  DL=$(( N * DLPF )); t0=$(date +%s)
  ( cd $FC && .venv/bin/python $T/physics_solve/solve.py $D/ref_in.parquet $D/ref_ps.parquet --device cuda $SOLVE_ARGS --deadline_s $DL ) > $O/ep$ep/solve.out 2>&1 \
    || { log "physics_solve ep$ep: solve FAILED ($(tail -2 $O/ep$ep/solve.out | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
  cp $D/ref_ps_solve.json $D/ref_ps_solve.log $O/ep$ep/ 2> /dev/null
  log "physics_solve ep$ep: solved in $(( $(date +%s) - t0 )) s (deadline $DL s); $(grep -a 'deadline .* reached\|bit-identical\|rollback' $O/ep$ep/solve.out | cut -c1-200 | tr '\n' ' ' | cut -c1-900)" >> $J
  ( cd $FC && DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero_ps.npz $D/ref_ps.parquet $N ) > $O/ep$ep/zero.log 2>&1
  ( cd $R && python $T/trace_score.py $D/ref_ps.parquet $O/ep$ep/zero_ps.npz:zero_ps $D/ref_ps_solve.npz:truth ) > $O/ep$ep/zero_score.txt 2>&1
  jitter $ep $D/ref_ps.parquet solved
  log "physics_solve ep$ep: solved jittered $(python -c "import json; d=json.load(open('$O/ep$ep/jitter_solved.json')); print('nominal', d['nominal'], 'mean', d['mean'], 'sd', d['sd'])" 2>&1 | tail -1); $(tr '\n' ' ' < $O/ep$ep/zero_score.txt)" >> $J
}

label "physics_solve: running [$EPS]"
first=$(for e in $EPS; do [ -n "$(ref_of $e)" ] && echo $e && break; done)
if [ -n "$first" ]; then                          # one jitter run alone first: Warp compiles the CUDA kernels once
  mkdir -p $O/ep$first; D=$(prep $first) && jitter $first $D/ref_in.parquet glock
fi
pids=()
for e in $EPS; do
  [ -n "$(ref_of $e)" ] || continue
  mkdir -p $O/ep$e; one $e & pids+=($!); sleep 20
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"

python - $O "$EPS" << EOF > $O/summary.json
import json, os, sys
O, eps = sys.argv[1], sys.argv[2].split(); src = {$(for e in $EPS; do echo -n "'$e': '${SRCOF[$e]:-none}', "; done)}
out, wins, harm = {}, 0, []
for e in eps:
    r = dict(input=src.get(e))
    for tag in ('glock', 'solved'):
        f = f'{O}/ep{e}/jitter_{tag}.json'
        if os.path.exists(f):
            d = json.load(open(f)); r[tag] = {k: d[k] for k in ('nominal', 'mean', 'sd', 'min', 'max', 'k')}
    f = f'{O}/ep{e}/ref_ps_solve.json'
    if os.path.exists(f):
        d = json.load(open(f)); r['solve'] = dict(wall_s=d.get('wall_s'), deadline_t=d.get('deadline_t'), rollbacks=d.get('rollbacks'))
    f = f'{O}/ep{e}/zero_score.txt'
    if os.path.exists(f):
        r['zero_score'] = open(f).read().strip().splitlines()
    if 'glock' in r and 'solved' in r:
        r['delta'] = round(r['solved']['mean'] - r['glock']['mean'], 4)
        wins += r['delta'] >= 0.03
        if r['delta'] <= -0.05:
            harm.append(e)
    out['ep' + e] = r
out['verdict'] = dict(rule='PASS iff solved jittered mean - grasp lock + ILC jittered mean >= 0.03 on >= 2 of 4 episodes',
                      episodes_beating=int(wins), PASS=bool(wins >= 2), harm_flag_episodes=harm)
print(json.dumps(out, indent=1))
EOF
log "physics_solve summary: $(tr -d '\n ' < $O/summary.json | cut -c1-1500)" >> $J
label "physics_solve: done $(python -c "import json; v=json.load(open('$O/summary.json'))['verdict']; print('PASS' if v['PASS'] else 'no pass', v['episodes_beating'], '/4')" 2>/dev/null)"
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
