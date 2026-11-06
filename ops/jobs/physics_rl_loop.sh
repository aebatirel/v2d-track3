#!/bin/bash
# Solver <-> RL loop ("option 3") and its cheap control ("option 1") on one box, 4 public episodes (2026-10-31; owner
# approved). Pre-registered design, settings, readings and cost: docs/research/physics-2026-10-30/physics-solver.md 6.1.
# Scored run = the learned policy in the unchanged evaluator; every change below is training-side. Realistic (S1) masses.
# Ground truth is read only by the final scoring (registered AUC vs mocap of public episodes, as rounds 1-3).
#
# Start references (both arms): the solved references G3 trained on (store run SRCREF, refs/glockt/ep<N>: G2's for
# ep2/ep12, G1's for ep18/ep24), S1 scan assets.
# O1 = option-1 control: ops/jobs/glock_public.sh REUSE_REF=1 on them, frozen recipe (FDR + VOC fix, seed 42, cap 70M,
#   CURVE_REP 3, NREP 5) plus early stopping (ES=1: target 0.9, patience 20M, from 20M) and CURR_SCALE 0.4.
# O3 = option 3, per episode three training rounds on one FlashSAC run (seed 42, CURR_SCALE 0.4, same rewards):
#   round A 0 -> 30M on the solved reference R0;
#   then: the newest checkpoint played like the evaluator (tools/trace_rollout.py policy, STATE=1) -> its failures
#   (tools/physics_solve/failures.py: an object > 3 cm off its reference for >= 8 frames; up to MAXWIN windows from
#   0.5 s before each failure, 3 s long) -> the solver from the POLICY'S state at each window start
#   (tools/physics_solve/solve.py --start_state, LOOP_SOLVE_ARGS) -> tools/physics_solve/merge_ref.py: the solved targets
#   (+ the solver's simulated contacts) merged into the reference -> R1, and a reset-state bank (the policy's states
#   before each failure + the solver's states along each window);
#   round B: RESUME the same run (actor, critic, optimiser; replay refills) 30M -> 50M on R1 with FC_STATE_RESET = the
#   bank (ops/box/patch_flashchord_states.py: a share BANK_P of the training resets start from banked states);
#   the same diagnosis on round B's newest checkpoint -> R2 (+ bank appended); round C 50M -> 70M on R2.
#   robot_<side>_frames (the RL hand-tracking target) and the object reference stay unchanged in every round.
#   Checkpoint choice as rounds 1-3: every checkpoint (10M..70M) scored by CURVE_REP official evaluations
#   (sim_vs_ref, our reference), the best by sim_vs_ref gets NREP evaluations with registered AUC vs mocap.
# Summary: /content/results/physics_rl_loop/summary.json (readings with their pre-registered rules).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'bash ops/jobs/physics_rl_loop.sh'
# Knobs: EPS SRCREF SEED ARMS ("O1 O3") CURR_SCALE ROUNDS BANK_P MAXWIN DLWIN LOOP_SOLVE_ARGS NREP CURVE_REP.
. /content/v2d-track3/ops/box/lib.sh
R=$REPO_DIR; T=$R/tools; P=$R/pipeline; J=${J:-/content/job.log}
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/physics_rl_loop; mkdir -p $O
EPS=${EPS:-"2 12 18 24"}; SRCREF=${SRCREF:-20261030-psolverl-04301a2}; SEED=${SEED:-42}; ARMS=${ARMS:-"O1 O3"}
CURR_SCALE=${CURR_SCALE:-0.4}; ROUNDS=(${ROUNDS:-30003200 50003968 70004736}); BANK_P=${BANK_P:-0.25}
MAXWIN=${MAXWIN:-2}; DLWIN=${DLWIN:-900}; NREP=${NREP:-5}; CURVE_REP=${CURVE_REP:-3}; PAR=${PAR:-3}
LOOP_SOLVE_ARGS=${LOOP_SOLVE_ARGS:-"--worlds 1024 --robust 4 --horizon 40 --knot 4 --ctrl 8 --iters 16 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.903 --retries 2 --retry 0.05 --back 1 --rob_pos 0.0005 --rob_fin 0.005 --early_rel 0.02 --early_n 2 --min_iters 6 --seed 0"}
declare -A BASE=([2]="20261024-ev3-2c1e4dd:mck" [12]="20261024-ev2-2c1e4dd:mc" [18]="20261024-ev3-2c1e4dd:mc" [24]="20261024-ev3-2c1e4dd:mc")
export EMB=sharpa_hands_mid OMP_NUM_THREADS=1
log "physics_rl_loop code $(git -C $R rev-parse --short HEAD), eps [$EPS], arms [$ARMS], refs $SRCREF, seed $SEED, CURR_SCALE $CURR_SCALE, rounds [${ROUNDS[*]}], BANK_P $BANK_P, MAXWIN $MAXWIN, LOOP_SOLVE_ARGS [$LOOP_SOLVE_ARGS]" >> $J
label "rl_loop: setup"

# ---- assets (S1), embodiment, FlashCHORD patches: FDR rewards + VOC fix (the recipe), then the reset-state bank patch
mkdir -p /content/scanlib
for d in /content/t3/mesh/*/; do
  n=$(basename $d); f=$d/$n.glb; [ -f $f ] || f=$d/${n}_collision.glb
  [ -f $f ] && [ "$n" != wooden_spoon ] && ln -sf $f /content/scanlib/$n.glb
done
export LIB=/content/scanlib MA_ARGS="--physics $R/docs/research/physics-2026-10-30/props_public_scans.json"
python $P/make_assets.py /content/scanlib /content/assets $MA_ARGS >> $J 2>&1 || { log "make_assets FAILED" >> $J; exit 1; }
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml
[ -s $E ] || cp $R/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }
fc_patches $J || exit 1                                          # exports FC_FDR_*, FC_VOC_INERTIA; sets TRAIN_ARGS
python $R/ops/box/patch_flashchord_states.py $FC >> $J 2>&1 || { log "state-bank patch FAILED" >> $J; exit 1; }
CURR="curriculum.thresholds=$(python -c "s = $CURR_SCALE; t = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]; print('[' + ','.join(str(int(x * s)) for x in t) + ']')")"
TRAIN_ARGS_O3="$TRAIN_ARGS $CURR"
log "rl_loop: patches applied; O3 TRAIN_ARGS [$TRAIN_ARGS_O3]" >> $J

fix_assets() {  # as glock_public.sh
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
nframes() { python -c "import pyarrow.parquet as pq; print(len(pq.read_table('$1').column('robot_left_wrist_position')[0].as_py()))"; }
train_slot() {  # the GPU training slots shared with glock_public.sh (at most 2 trainings at once: 40 GB each)
  local s
  while :; do
    for s in 1 2; do mkdir /content/train_slot_$s 2> /dev/null && { echo $s; return; }; done
    sleep 30
  done
}
evalrep() {  # $1 checkpoint, $2 output dir, $3 episode: NREP official evaluations, each scored (as glock_public.sh)
  local ck=$1 d=$2 ep=$3 E6 i pids=()
  E6=$(printf %06d $ep); mkdir -p $d
  for i in $(seq 1 $NREP); do
    ( mkdir -p $d/r$i; cd $FC && MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py \
        evaluation.checkpoint=$ck evaluation.world_count=1 evaluation.reset_mode=explicit \
        evaluation.metrics_output=$d/r$i/episode_$E6.json evaluation.object_trajectories_output=$d/r$i/episode_$E6.parquet \
        hydra.run.dir=$d/r$i/hydra logging.mode=disabled > $d/r$i/eval.log 2>&1 \
      && python $P/qa.py policy $d/r$i $ep > /dev/null 2>&1 \
      && python $P/score_registered.py $ep $d/r$i --meshes /content/scanlib > /dev/null 2>&1 ) & pids+=($!)
    [ ${#pids[@]} -ge $PAR ] && { wait "${pids[@]}"; pids=(); }
  done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  python - $d $ep $ck << 'EOF' > $d/summary.json
import glob, json, os, sys
import numpy as np
d, ep, ck = sys.argv[1], int(sys.argv[2]), sys.argv[3]; rows = []
for r in sorted(glob.glob(f'{d}/r*/')):
    try:
        q = json.load(open(f'{r}qa_policy.json')); row = dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=q['sim_vs_ref'])
        if os.path.exists(f'{r}score_registered_ep{ep}.json'):
            s = json.load(open(f'{r}score_registered_ep{ep}.json'))['sim']; row.update(auc=s['AUC'], sp=s['SP_SR'], mp=s['MP_SR'])
        rows.append(row)
    except Exception as e:
        rows.append(dict(rollout=os.path.basename(r[:-1]), error=str(e)[:120]))
ok = [x for x in rows if 'sim_vs_ref' in x]; agg = {}
for k in ('sim_vs_ref', 'auc'):
    v = np.array([x[k] for x in ok if k in x], float)
    if len(v):
        agg[k] = dict(mean=round(float(v.mean()), 4), std=round(float(v.std()), 4), min=round(float(v.min()), 4), max=round(float(v.max()), 4))
print(json.dumps(dict(checkpoint=ck, n=len(ok), **agg, rollouts=rows), indent=1))
EOF
}

# ---- start references: the G3 training references (one parquet per task dir) and their rest checks (REUSE_REF)
label "rl_loop: references"
PULL_SUB="$(for e in $EPS; do echo -n "refs/glockt/ep$e "; done)" bash $OPS/store.sh pull-run $SRCREF >> $J 2>&1 || log "pull-run $SRCREF: error (checking)" >> $J
GP=/content/results/glock_public; READY=
for e in $EPS; do
  P0=$(ls /content/refs/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
  [ -s "$P0" ] || { log "rl_loop ep$e: no solved reference in $SRCREF (skipped)" >> $J; continue; }
  n=$(find /content/refs/glockt/ep$e/processed -name '*.parquet' | wc -l); [ "$n" = 1 ] || { log "rl_loop ep$e: $n parquets in its task tree (skipped)" >> $J; continue; }
  fix_assets $P0 >> $J 2>&1 || { log "rl_loop ep$e: assets missing" >> $J; continue; }
  hive=$(dirname ${P0#/content/refs/glockt/ep$e/}); N=$(nframes $P0); mkdir -p $GP/ep$e $O/ep$e
  ( cd $FC && DEV=cuda .venv/bin/python $T/trace_rollout.py zero $GP/ep$e/zero.npz $P0 $N ) > $O/ep$e/r0_zero.log 2>&1
  python $T/rest_check.py $GP/ep$e/zero.npz $P0 > $GP/ep$e/rest_check.json 2>&1
  L=/content/refs/loop/ep$e/r0; mkdir -p $L/$hive; cp -r /content/refs/glockt/ep$e/reconstructed_stage $L/; cp $P0 $L/$hive/ref_gl_ilc.parquet
  echo $hive > $O/ep$e/hive; READY="$READY $e"
done
log "rl_loop: references ready for [$READY]" >> $J

# ---- O1: glock_public.sh REUSE_REF on the solved references, ES + CURR_SCALE (started first: it clears stale slots)
if [[ " $ARMS " == *" O1 "* ]] && [ -n "$READY" ]; then
  ( export SF=0 REPLAN=0 EVOLVE=0 CURVE_REP=$CURVE_REP NREP=$NREP SEED=$SEED REUSE_REF=1 HUMAN=0 \
      ES=1 ES_TARGET=${ES_TARGET:-0.9} ES_PATIENCE=${ES_PATIENCE:-20000000} ES_MIN=${ES_MIN:-20000000} CURR_SCALE=$CURR_SCALE \
      PULL_SUB="refs/perc2mck/ep2 refs/perc2mc/ep12 refs/perc2mc/ep18 refs/perc2mc/ep24" \
      PAIRS="$(for e in $READY; do echo -n "$e:${BASE[$e]} "; done)"
    bash $R/ops/jobs/glock_public.sh ) &
  O1PID=$!
  for i in $(seq 1 120); do                                      # its setup first (assets, patches, pulls, then it clears
    grep -aq 'glock ep[0-9]*: base' $J && break; sleep 10        # stale training slots): O3 starts after its first
  done                                                           # episode line, so the two arms share 2 slots exactly
fi

# ---- O3: the loop
o3() {
  local ep=$1 hive RUN OL r END RD ck st slot rc bank= sc win k N
  hive=$(cat $O/ep$ep/hive); RUN=/content/runs/loop/ep$ep-s$SEED; OL=$O/ep$ep/o3; mkdir -p $RUN $OL
  for r in 0 1 2; do
    END=${ROUNDS[$r]}; RD=/content/refs/loop/ep$ep/r$r
    st=$(ls -v $RUN/state_*.safetensors 2> /dev/null | tail -1)
    slot=$(train_slot)
    log "rl_loop O3 ep$ep: round $r -> $END steps on $RD (slot $slot, resume ${st:-none}, bank ${bank:-none})" >> $J
    ( cd $FC && env ${bank:+FC_STATE_RESET=$bank FC_STATE_RESET_P=$BANK_P} MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        .venv/bin/python scripts/train_flash_sac.py experiment=sharpa_flash_sac embodiment=sharpa_hands_mid \
        "task.parquet='$RD/$hive'" task.motion_speed=1.0 reset.seed=$SEED logging.mode=disabled output_dir=$RUN \
        training.total_environment_steps=$END ${st:+training.resume=true training.checkpoint_path=$st} $TRAIN_ARGS_O3 ) >> $RUN/train_r$r.log 2>&1
    rc=$?; rmdir /content/train_slot_$slot
    [ $rc = 0 ] || { log "rl_loop O3 ep$ep: round $r training FAILED ($(tail -2 $RUN/train_r$r.log | tr '\n' ' ' | cut -c1-300))" >> $J; break; }
    [ $r = 2 ] && break
    # diagnosis: the newest checkpoint played like the evaluator, its failures, the solver from its states, the merge
    ck=$(ls -v $RUN/policy_*.safetensors | tail -1); N=$(nframes $RD/$hive/ref_gl_ilc.parquet); mkdir -p $OL/r$r
    ( cd $FC && DEV=cuda STATE=1 MUJOCO_GL=egl .venv/bin/python $T/trace_rollout.py policy $OL/r$r/trace.npz evaluation.checkpoint=$ck \
        viewer.backend=none viewer.num_frames=$N reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true \
        termination.wrist_position.enabled=false termination.object_position.enabled=false termination.object_orientation.enabled=false ) > $OL/r$r/trace.log 2>&1
    ( cd $R && python $T/trace_score.py $RD/$hive/ref_gl_ilc.parquet $OL/r$r/trace.npz:policy ) > $OL/r$r/trace_score.txt 2>&1
    python $T/physics_solve/failures.py $RD/$hive/ref_gl_ilc.parquet $OL/r$r/trace.npz $OL/r$r/failures.json --max $MAXWIN > $OL/r$r/failures.log 2>&1
    log "rl_loop O3 ep$ep: round $r $(basename $ck): $(grep -a policy: $OL/r$r/trace_score.txt | tr -s ' ' | cut -c1-60); failures $(python -c "import json; d=json.load(open('$OL/r$r/failures.json')); print({k: v['onset'] for k, v in d['objects'].items()}, 'windows', [(w['start'], w['end']) for w in d['windows']])" 2>&1 | tail -1)" >> $J
    segs=(); k=0
    for win in $(python -c "import json; print(' '.join(f\"{w['start']}:{w['end']}\" for w in json.load(open('$OL/r$r/failures.json'))['windows']))" 2> /dev/null); do
      local S0=${win%:*} S1=${win#*:} SD=/content/refs/loop/ep$ep/seg_r${r}_w$k
      mkdir -p $SD/$hive; cp -r $RD/reconstructed_stage $SD/; cp $RD/$hive/ref_gl_ilc.parquet $SD/$hive/base.parquet
      ( cd $FC && .venv/bin/python $T/physics_solve/solve.py $SD/$hive/base.parquet $SD/$hive/seg.parquet --device cuda $LOOP_SOLVE_ARGS \
          --start_state $OL/r$r/trace.npz --t0 $S0 --stop $S1 --record --deadline_s $DLWIN ) > $OL/r$r/solve_w$k.out 2>&1 \
        && segs+=($SD/$hive/seg.parquet) || log "rl_loop O3 ep$ep: round $r window $k solve FAILED ($(tail -1 $OL/r$r/solve_w$k.out | cut -c1-200))" >> $J
      k=$((k + 1))
    done
    local NX=/content/refs/loop/ep$ep/r$((r + 1)); mkdir -p $NX/$hive; cp -r $RD/reconstructed_stage $NX/
    if [ ${#segs[@]} -gt 0 ]; then
      python $T/physics_solve/merge_ref.py $RD/$hive/ref_gl_ilc.parquet $NX/$hive/ref_gl_ilc.parquet --seg "${segs[@]}" \
          --trace $OL/r$r/trace.npz --windows $OL/r$r/failures.json --bank $OL/bank_r$((r + 1)).npz ${bank:+--bank_in $bank} --contacts \
          > $OL/r$r/merge.log 2>&1 && mv $NX/$hive/ref_gl_ilc_merge.json $OL/r$r/merge.json 2> /dev/null
      rm -f $NX/$hive/*_sim_contacts.json                        # one parquet per task dir (FlashCHORD reads the dir)
      [ -s $NX/$hive/ref_gl_ilc.parquet ] || cp $RD/$hive/ref_gl_ilc.parquet $NX/$hive/
      [ -s $OL/bank_r$((r + 1)).npz ] && bank=$OL/bank_r$((r + 1)).npz
      log "rl_loop O3 ep$ep: round $r merge $(tail -1 $OL/r$r/merge.log | cut -c1-300)" >> $J
    else
      cp $RD/$hive/ref_gl_ilc.parquet $NX/$hive/
      log "rl_loop O3 ep$ep: round $r no solved window; the next round keeps the reference" >> $J
    fi
  done
  # scoring as rounds 1-3: every checkpoint by CURVE_REP evaluations, the best by sim_vs_ref gets NREP with AUC vs mocap
  REPO_DIR=$R PAR=$PAR REP=$CURVE_REP bash $T/ckpt_curve.sh $RUN $OL/curve $ep >> $OL/curve.log 2>&1
  python $T/ckpt_curve_summary.py $OL/curve > $OL/curve.txt 2>&1
  ck=$(python - $OL/curve $RUN << 'EOF'
import glob, json, os, sys
best = max(((json.load(open(f)).get('sim_vs_ref', -1), os.path.basename(os.path.dirname(f))) for f in glob.glob(f'{sys.argv[1]}/policy_*/qa_policy.json')), default=None)
print(f'{sys.argv[2]}/{best[1]}.safetensors' if best else '')
EOF
)
  [ -s "$ck" ] || { log "rl_loop O3 ep$ep: no scored checkpoint" >> $J; return 1; }
  # the final checkpoint's rollout too ([H-teach]: does the first failure move later than after round A?)
  local CF=$(ls -v $RUN/policy_*.safetensors | tail -1) N2=$(nframes $RD/$hive/ref_gl_ilc.parquet); mkdir -p $OL/final
  ( cd $FC && DEV=cuda STATE=1 MUJOCO_GL=egl .venv/bin/python $T/trace_rollout.py policy $OL/final/trace.npz evaluation.checkpoint=$CF \
      viewer.backend=none viewer.num_frames=$N2 reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true \
      termination.wrist_position.enabled=false termination.object_position.enabled=false termination.object_orientation.enabled=false ) > $OL/final/trace.log 2>&1
  python $T/physics_solve/failures.py /content/refs/loop/ep$ep/r0/$hive/ref_gl_ilc.parquet $OL/final/trace.npz $OL/final/failures.json > /dev/null 2>&1
  evalrep $ck $OL/best $ep; cp $ck $OL/best/policy.safetensors
  log "rl_loop O3 ep$ep RESULT ($(basename $ck)): $(python -c "import json; d=json.load(open('$OL/best/summary.json')); print('sim_vs_ref', d.get('sim_vs_ref'), 'AUC', d.get('auc'))" 2>&1 | tail -1); curve $(tr -s ' ' < $OL/curve.txt | cut -c1-24 | tr '\n' ';' | cut -c1-300)" >> $J
}
if [[ " $ARMS " == *" O3 "* ]]; then
  label "rl_loop: running [$ARMS]"
  pids=()
  for e in $READY; do o3 $e & pids+=($!); sleep 60; done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
fi
[ -n "${O1PID:-}" ] && wait $O1PID

# ---- summary with the pre-registered readings (physics-solver.md 6.1)
python - $O $GP "$EPS" << 'EOF' > $O/summary.json
import glob, json, os, re, sys
O, GP, eps = sys.argv[1], sys.argv[2], sys.argv[3].split()
G3 = {'2': 0.584, '12': 0.892, '18': 0.622, '24': 0.244}                 # G3: solved refs, frozen recipe, seed 42
S1R1 = {'2': 0.7362, '12': 0.8847, '18': 0.6245, '24': 0.2324}           # round 1: GL+ILC refs, S1, seed 42
jl = lambda f: json.load(open(f)) if os.path.exists(f) else None
def auc(d):
    return d['auc']['mean'] if d and d.get('auc') else None
out = {}
for e in eps:
    r = dict(O1=jl(f'{GP}/ep{e}/best/summary.json'), O3=jl(f'{O}/ep{e}/o3/best/summary.json'))
    for k in ('O1', 'O3'):
        if r[k]:
            r[k].pop('rollouts', None)
    for k, f in (('O1_curve', f'{GP}/ep{e}/curve.txt'), ('O3_curve', f'{O}/ep{e}/o3/curve.txt')):
        if os.path.exists(f):
            r[k] = open(f).read().splitlines()
    rounds = []
    for rr in ('r0', 'r1', 'final'):
        fj = jl(f'{O}/ep{e}/o3/{rr}/failures.json'); mj = jl(f'{O}/ep{e}/o3/{rr}/merge.json')
        ts = f'{O}/ep{e}/o3/{rr}/trace_score.txt'
        rounds.append(dict(round=rr, onsets={k: v['onset'] for k, v in fj['objects'].items()} if fj else None,
                           windows=[(w['start'], w['end']) for w in fj['windows']] if fj else None,
                           trace=open(ts).read().strip().splitlines() if os.path.exists(ts) else None,
                           bank=mj.get('bank') if mj else None))
    r['O3_loop'] = rounds; r['G3_auc'] = G3[e]; r['S1_round1_auc'] = S1R1[e]
    out['ep' + e] = r
def reading(a, b, name):
    d = {e: round(auc(out['ep' + e][a]) - (b[e] if isinstance(b, dict) else auc(out['ep' + e][b])), 4)
         for e in eps if auc(out['ep' + e][a]) is not None and (isinstance(b, dict) or auc(out['ep' + e][b]) is not None)}
    v = list(d.values()); m = sum(v) / len(v) if v else None
    return dict(comparison=name, deltas=d, mean=None if m is None else round(m, 4), missing=[e for e in eps if e not in d],
                rule='signal iff mean >= +0.03 and none <= -0.05; harm iff mean <= -0.03 or any <= -0.10; else inconclusive',
                verdict='no result' if m is None else ('signal' if m >= 0.03 and min(v) > -0.05 else
                                                        'harm' if m <= -0.03 or min(v) <= -0.10 else 'inconclusive'))
out['readings'] = dict(primary_O3_vs_O1=reading('O3', 'O1', 'O3 - O1, registered AUC vs mocap'),
                       secondary_O1_vs_G3=reading('O1', G3, 'O1 - G3'), secondary_O3_vs_G3=reading('O3', G3, 'O3 - G3'),
                       report_O3_vs_round1=reading('O3', S1R1, 'O3 - round-1 S1 seed 42'))
ht = []
for e in eps:
    rr = out['ep' + e]['O3_loop']; a = rr[0]['onsets'] or {}; f = rr[2]['onsets'] or {}
    first = lambda o: min([x for x in o.values() if x is not None], default=10 ** 6)
    if a or f:
        ht.append(dict(ep=e, after_round_A=first(a), final=first(f), later=first(f) > first(a)))
out['readings']['H_teach'] = dict(rule='the first failure frame of the final policy is later than after round A on >= 2 of 4 episodes '
                                       '(no failure = frame 10^6)', episodes=ht, verdict='supported' if sum(x['later'] for x in ht) >= 2 else 'not supported')
print(json.dumps(out, indent=1))
EOF
log "rl_loop summary: $(python -c "import json; d=json.load(open('$O/summary.json'))['readings']; print({k: (v.get('verdict'), v.get('mean')) for k, v in d.items()})" 2>&1 | tail -1)" >> $J
label "rl_loop: done"
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
