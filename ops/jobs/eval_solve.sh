#!/bin/bash
# Physics solve of the grasp-lock EVAL episodes' packed references for pack 10 (2026-10-31). Launched only when the
# pre-registered clean re-test (docs/research/physics-2026-10-30/physics-solver.md section 9) reads "signal": the owner
# pre-approved eval solving then (~$15). EVAL episodes: no ground truth exists or is read; every score is sim_vs_ref
# against OUR reference (no mocap, no `pose` field of observation.objects).
# Per episode of EPS (grasp-lock evals of the pack builder's table TAB; standard-learner episodes are refused):
#   1. pull the packed policy's trained reference exactly: the table's pull_files under runs/<source_run>/refs/glockt/ep<N>/
#      (ref_gl_ilc.parquet + its support stage) and its asset copy runs/<source_run>/refs/sf/ep<N>/assets/ (eval 10: none,
#      its reference names the shared /content/assets), one single-file download each (store.sh pull-files, no listing),
#      placed under /content as pull-run places them;
#      REF_EP<N>=<store path of a parquet> replaces the table's reference (eval 10's V4p reference if the ep11 gate passes):
#      its stage <base>/reconstructed_stage/<seq>_support.usda (or STAGE_EP<N>) and FILES_EP<N>="<store paths>" (e.g. an
#      own asset copy) are pulled with it; MD5_EP<N> = its expected md5 (refused on a mismatch);
#   2. /content/assets, only if a reference names it: pipeline/make_assets.py meshes/<lib> with the table's pieces (eval
#      10: library_v3 + meshes/carve/ev10), at the 0.3 kg placeholder: what the packed eval-10 training used and what
#      mass_eval.sh builds (ASSET_LIB / ASSET_PIECES override; references needing different builds are dropped);
#   3. tools/physics_solve/eval_inputs.py check: md5 = the table's (the trained file), objects and asset root as the
#      table, every URDF and mesh present, the support stage present; md5s of the reference, stage and asset files used;
#   4. working copy /content/refs/evsolve/ep<N>/processed/<seq>/<robot>/ref_in.parquet (byte copy, md5-checked) + the stage;
#   5. 64-copy jitter check of the input (tools/physics_solve/jitter_check.py, seed 0, 0.5 mm / 0.005 rad: G2's check);
#   6. tools/physics_solve/solve.py at G2 scale (SOLVE_ARGS = physics_solve_rl.sh's G2_ARGS: 1,024 candidates x 4 robust
#      copies, 3 s horizon, 0.5 s commits, <= 32 iterations with early stop, <= 3 rollbacks), pace PACE s/frame, hard
#      deadline DLPF s x frames -> ref_ps.parquet (+ _solve.json/.npz/.log) next to ref_in.parquet;
#   7. official zero-action replay of ref_ps (tools/trace_rollout.py zero) + tools/trace_score.py + tools/rest_check.py
#      (the files glock_public.sh REUSE_REF needs), then the same 64-copy jitter check of ref_ps (common random numbers);
#   8. tools/physics_solve/eval_solve_summary.py -> /content/results/eval_solve/{summary.json,handoff.tsv,handoff.md}
#      (store paths, md5 in / out, jittered input vs solved per episode; no verdict: pack 10's rule decides); store push.
# Concurrency: PAR (2) episodes at a time on the one GPU, longest first (G2 ran two 4,096-world solves together on one
# 96 GB card: ep2 3,952 s, ep12 2,471 s). One jitter run first, alone (Warp compiles the CUDA kernels once).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-evsolve<k>-<sha7> \
#     'EPS="35 33 5 32 8 16 10 37" bash ops/jobs/eval_solve.sh'
# Knobs: EPS TAB PAR JK DLPF PACE SOLVE_ARGS DEV REF_EP<N> STAGE_EP<N> FILES_EP<N> MD5_EP<N> ASSET_LIB ASSET_PIECES.
# Exit 0 when at least one episode was solved (failures are listed in summary.json), 1 otherwise.
. /content/v2d-track3/ops/box/lib.sh
R=$REPO_DIR; T=$R/tools; P=$R/pipeline; J=${J:-/content/job.log}
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/eval_solve; HS=/content/hfstore; mkdir -p $O
TAB=${TAB:-$R/docs/research/physics-2026-10-30/eval_solve/packed_refs.json}
EPS=${EPS:-"3 5 6 8 10 14 15 16 20 32 33 35 36 37 38"}
PAR=${PAR:-2}; JK=${JK:-64}; DLPF=${DLPF:-18}; PACE=${PACE:-14.4}; DEV=${DEV:-cuda}
SOLVE_ARGS=${SOLVE_ARGS:-"--worlds 4096 --robust 4 --horizon 60 --knot 4 --ctrl 10 --iters 32 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.9518 --retries 3 --retry 0.05 --back 1 --rob_pos 0.0005 --rob_fin 0.005 --early_rel 0.02 --early_n 2 --min_iters 6 --seed 0"}
IE="python $T/physics_solve/eval_inputs.py"
export EMB=sharpa_hands_mid OMP_NUM_THREADS=1
m5() { md5sum "$1" 2> /dev/null | cut -c1-32; }
: "${RUN_ID:?RUN_ID is not set}"
log "eval_solve code $(git -C $R rev-parse --short HEAD), run $RUN_ID, eps [$EPS], PAR $PAR, JK $JK, DLPF $DLPF, PACE $PACE, DEV $DEV, table $TAB ($(m5 $TAB)), md5 solve.py $(m5 $T/physics_solve/solve.py) jitter_check.py $(m5 $T/physics_solve/jitter_check.py) eval_inputs.py $(m5 $T/physics_solve/eval_inputs.py) eval_solve.sh $(m5 $R/ops/jobs/eval_solve.sh), SOLVE_ARGS [$SOLVE_ARGS]" >> $J
for e in $EPS; do v=REF_EP$e; [ -n "${!v:-}" ] && log "eval_solve ep$e: REF_EP$e=${!v} STAGE_EP$e=$(eval echo \${STAGE_EP$e:-}) FILES_EP$e=[$(eval echo \${FILES_EP$e:-})] MD5_EP$e=$(eval echo \${MD5_EP$e:-})" >> $J; done

# ---- 1. pulls (single-file downloads; the reference is line 1 of each list)
label "eval_solve: pulling [$EPS]"
declare -A REF; PULLED=""
for e in $EPS; do
  mkdir -p $O/ep$e; v=REF_EP$e; s=STAGE_EP$e; x=FILES_EP$e
  $IE files $TAB $e --root /content ${!v:+--ref ${!v}} ${!s:+--stage ${!s}} ${!x:+--extra "${!x}"} > $O/ep$e/pull_list.tsv 2> $O/ep$e/pull_list.err \
    || { log "eval_solve ep$e: no pull list ($(tr '\n' ' ' < $O/ep$e/pull_list.err | cut -c1-300)); dropped" | tee $O/ep$e/dropped.txt >> $J; continue; }
  ok=1
  while IFS=$'\t' read -r f l; do
    if ! bash $OPS/store.sh pull-files "$f" >> $O/ep$e/pull.log 2>&1; then log "eval_solve ep$e: pull-files FAILED for $f" >> $J; ok=0; continue; fi
    mkdir -p "$(dirname "$l")"
    if [ -e "$l" ] && ! cmp -s "$l" "$HS/$f"; then log "eval_solve ep$e: $l exists and differs from $f" >> $J; ok=0; continue; fi
    [ -e "$l" ] || cp "$HS/$f" "$l"
  done < $O/ep$e/pull_list.tsv
  [ $ok = 1 ] || { log "eval_solve ep$e: inputs incomplete (pull.log); dropped" | tee $O/ep$e/dropped.txt >> $J; continue; }
  head -1 $O/ep$e/pull_list.tsv | cut -f1 > $O/ep$e/input_store_path.txt
  REF[$e]=$(head -1 $O/ep$e/pull_list.tsv | cut -f2); PULLED="$PULLED $e"
  log "eval_solve ep$e: pulled $(wc -l < $O/ep$e/pull_list.tsv) files; reference $(cat $O/ep$e/input_store_path.txt)" >> $J
done

# ---- 2. the shared /content/assets, if a reference names it (eval 10: library_v3 + ev10 pieces, 0.3 kg)
label "eval_solve: assets"
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml   # kp 400 wrist embodiment
[ -s $E ] || cp $R/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "eval_solve: embodiment copy FAILED" >> $J; exit 1; }
pairs=$(for e in $PULLED; do echo -n "$e:${REF[$e]} "; done)
if [ -n "$pairs" ]; then
  if a_=$($IE assets $TAB "$pairs" --root /content ${ASSET_LIB:+--lib $ASSET_LIB} ${ASSET_PIECES+--pieces "$ASSET_PIECES"} 2>> $J); then
    eval "$a_"
    if [ -n "$LIB" ]; then
      python $P/make_assets.py $R/meshes/$LIB /content/assets ${PIECES:+--pieces $R/$PIECES} > $O/make_assets.log 2>&1 \
        || { log "eval_solve: make_assets FAILED ($(tail -2 $O/make_assets.log | tr '\n' ' '))" >> $J; exit 1; }
      ( cd /content/assets && find . -type f | sort | xargs md5sum ) > $O/assets_md5.txt
      log "eval_solve: /content/assets = make_assets meshes/$LIB pieces ${PIECES:-none} (0.3 kg placeholder; $(wc -l < $O/assets_md5.txt) files)" >> $J
    fi
  else
    log "eval_solve: references need different builds of /content/assets; the episodes naming it are dropped" >> $J
    keep=""; for e in $PULLED; do python -c "import sys, pyarrow.parquet as pq; sys.exit(any(u.startswith('/content/assets/') for u in pq.read_table(sys.argv[1]).column('object_urdf_paths')[0].as_py()))" ${REF[$e]} && keep="$keep $e"; done
    PULLED=$keep
  fi
fi

# ---- 3./4. checks and working copies
label "eval_solve: checks"
OK=""; declare -A WORK
for e in $PULLED; do
  v=REF_EP$e; m=MD5_EP$e
  $IE check $TAB $e ${REF[$e]} --root /content --out $O/ep$e/inputs.json ${!v:+--override} ${!m:+--want_md5 ${!m}} >> $J 2>&1 \
    || { log "eval_solve ep$e: input check REFUSED ($(python -c "import json; print(json.load(open('$O/ep$e/inputs.json')).get('refused'))" 2>&1 | cut -c1-300)); dropped" >> $J; continue; }
  src=$(dirname ${REF[$e]}); hive=processed/$(basename $(dirname $src))/$(basename $src); base=/content/refs/evsolve/ep$e; W=$base/$hive
  mkdir -p $W $base/reconstructed_stage; cp ${REF[$e]} $W/ref_in.parquet
  cp "$(python -c "import json; print(json.load(open('$O/ep$e/inputs.json'))['stage'])")" $base/reconstructed_stage/
  [ "$(m5 $W/ref_in.parquet)" = "$(python -c "import json; print(json.load(open('$O/ep$e/inputs.json'))['md5'])")" ] \
    || { log "eval_solve ep$e: working copy md5 differs; dropped" >> $J; continue; }
  echo $W > $O/ep$e/work.txt; WORK[$e]=$W; OK="$OK $e"
done
OK=${OK# }
log "eval_solve: inputs checked for [$OK] of [$EPS]" >> $J
nframes() { python -c "import pyarrow.parquet as pq; print(len(pq.read_table('$1').column('robot_left_wrist_position')[0].as_py()))"; }
jitter() {  # $1 episode $2 reference $3 tag: the 64-copy jitter check (G2's), same seed and K for input and output
  ( cd $FC && DEV=$DEV .venv/bin/python $T/physics_solve/jitter_check.py $2 --device $DEV --k $JK --seed 0 \
      --json $O/ep$1/jitter_$3.json ) >> $O/ep$1/jitter_$3.log 2>&1
}
jmean() { python -c "import json; d=json.load(open('$1')); print(d['mean'], '+-', d['sd'], 'nominal', d['nominal'])" 2> /dev/null; }

# ---- 5.-7. per episode: jitter of the input, solve, replay + rest check, jitter of the output
one() {
  local e=$1 W=${WORK[$1]} N DL t0
  N=$(nframes $W/ref_in.parquet); DL=$(python -c "print(int($N * $DLPF))")
  [ -s $O/ep$e/jitter_in.json ] || jitter $e $W/ref_in.parquet in
  ( cd $FC && DEV=$DEV .venv/bin/python $T/trace_rollout.py zero $O/ep$e/zero_in.npz $W/ref_in.parquet $N ) > $O/ep$e/zero_in.log 2>&1
  ( cd $R && python $T/trace_score.py $W/ref_in.parquet $O/ep$e/zero_in.npz:zero_action ) > $O/ep$e/zero_score_in.txt 2>&1
  python $T/rest_check.py $O/ep$e/zero_in.npz $W/ref_in.parquet > $O/ep$e/rest_check_in.json 2>&1
  log "eval_solve ep$e: input jittered $(jmean $O/ep$e/jitter_in.json); $(tr '\n' ' ' < $O/ep$e/zero_score_in.txt); solving $N frames, deadline $DL s" >> $J
  t0=$(date +%s)
  ( cd $FC && .venv/bin/python $T/physics_solve/solve.py $W/ref_in.parquet $W/ref_ps.parquet --device $DEV $SOLVE_ARGS \
      --deadline_s $DL --pace_s $PACE ) > $O/ep$e/solve.out 2>&1 \
    || { log "eval_solve ep$e: solve FAILED ($(tail -2 $O/ep$e/solve.out | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
  cp $W/ref_ps_solve.json $W/ref_ps_solve.log $O/ep$e/ 2> /dev/null
  log "eval_solve ep$e: solved in $(( $(date +%s) - t0 )) s; $(python -c "import json; d=json.load(open('$W/ref_ps_solve.json')); print('deadline_t', d['deadline_t'], 'rollbacks', d['rollbacks'], 'paced', d.get('paced_replans'), 'mean iterations', d.get('mean_iters'))" 2>&1 | tail -1); $(grep -a 'bit-identical' $O/ep$e/solve.out | cut -c1-200)" >> $J
  ( cd $FC && DEV=$DEV .venv/bin/python $T/trace_rollout.py zero $O/ep$e/zero_ps.npz $W/ref_ps.parquet $N ) > $O/ep$e/zero_ps.log 2>&1
  ( cd $R && python $T/trace_score.py $W/ref_ps.parquet $O/ep$e/zero_ps.npz:zero_action $W/ref_ps_solve.npz:truth ) > $O/ep$e/zero_score_ps.txt 2>&1
  python $T/rest_check.py $O/ep$e/zero_ps.npz $W/ref_ps.parquet > $O/ep$e/rest_check_ps.json 2>&1
  jitter $e $W/ref_ps.parquet ps
  log "eval_solve ep$e: solved jittered $(jmean $O/ep$e/jitter_ps.json) (input $(jmean $O/ep$e/jitter_in.json)); $(tr '\n' ' ' < $O/ep$e/zero_score_ps.txt); rest $(tr -d '\n ' < $O/ep$e/rest_check_ps.json | cut -c1-200)" >> $J
}
if [ -n "$OK" ]; then
  order=$(for e in $OK; do echo "$(nframes ${WORK[$e]}/ref_in.parquet) $e"; done | sort -rn | awk '{print $2}' | tr '\n' ' ')
  label "eval_solve: solving [$order] ($PAR at a time)"
  log "eval_solve: order (longest first) [$order], $PAR at a time" >> $J
  first=${order%% *}; jitter $first ${WORK[$first]}/ref_in.parquet in   # alone: the CUDA kernels compile once
  running=0
  for e in $order; do
    if [ $running -ge $PAR ]; then wait -n; running=$((running - 1)); fi
    one $e & running=$((running + 1)); sleep 20
  done
  wait
fi

# ---- 8. summary, hand-off, push
python $T/physics_solve/eval_solve_summary.py $O "$EPS" --run $RUN_ID --root /content > /dev/null 2> $O/summary.err \
  || log "eval_solve: summary FAILED ($(tail -2 $O/summary.err | tr '\n' ' '))" >> $J
nsol=$(python -c "import json; print(len(json.load(open('$O/summary.json'))['solved']))" 2> /dev/null || echo 0)
log "eval_solve summary: solved $nsol of [$EPS]; $(python -c "import json; d=json.load(open('$O/summary.json')); print('failed', d['failed'], '| delta', d['delta_jittered'])" 2>&1 | cut -c1-900)" >> $J
cat $O/handoff.tsv >> $J 2> /dev/null
label "eval_solve: done, solved $nsol"
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "eval_solve: push-run FAILED (run_job.sh pushes again)" >> $J
[ "$nsol" -gt 0 ]
