#!/bin/bash
# Eval-10 retrain on the S12 V4p reference (2026-10-31): launched only after the ep11 rollout gate PASSes (its PREREG
# section 5) and on the owner's go. Pre-registered in docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md
# (written before any eval-10 V4p result); build notes BUILD.md, launch string and cost JOBS.txt there. EVAL episode 10:
# no ground truth exists or is read; every score is GT-free (against our references V and P). One box, one arm, seeds 42
# and 43, the packed eval-10 recipe (run 20261026-gl10A2-5e0e100) exactly as the ep11 gate used it, with SPLIT=eval:
#   1. inputs, one single-file store download each (store.sh pull-files; no listing), md5 checked: eval 10's stored
#      perc2 track (pack 6 copies = evB's), the packed base reference's hands, the packed reference P and checkpoint,
#      the old packed draw, the eval-10 depth cache (bytes, shape, frame-0 sha256; mkref's depth by the PREREG 3.2 rule);
#   2. the V4p track rebuilt here with the committed code (tools/e10v_track.sh, pinned venvs as the gate), then B0
#      (tools/e10v_verify.py b0 vs ev10retrain/expect/): IDENTICAL / NUMERIC / DIFFERS go on, MISMATCH stops;
#   3. the base reference (mck): pipeline_ep.sh 10 SPLIT=eval PERC=perc2 VARIANT=e10vmck PDIR=<V4p track>, the stored
#      hands copied in, mkref --wrist_cost 3.0, contact retargeting --rest_settle 1, /content/assets = library_v3 +
#      meshes/carve/ev10 -> refs/perc2e10vmck/ep10; identity by content (V4p, not the stored track, reached mkref);
#   4. the grasp-lock reference stages once (glock_public.sh REF_ONLY=1 SEED=42 EVAL_LOCAL_REF=1, prefix perc2e10v) ->
#      refs/perc2e10v_glockt/ep10 (= V); byte copies per seed (tools/e10v_verify.py arms);
#   5. per seed one glock_public.sh call (REUSE_REF=1 REQUIRE_REUSE=1): 70M steps, checkpoint by sim_vs_ref vs V over 3
#      evaluations per curve checkpoint, NREP 10 training-box evaluations; then rule 2 picks the seed (e10v_verify.py choose);
#   6. 10 fresh official draws of the chosen checkpoint: the kit's run_policy_evaluation.py on the pristine FlashCHORD
#      worktree (submit_pack.sh / h5_reeval.sh), one invocation per draw, cut at EVAL_TIMEOUT -> results/ev10_v4p/conf/r<i>;
#   7. tools/e10v_score.py scores every rollout against V and P (sim_vs_ref as qa.py; GT-free RPE / MPPE / AUC as the
#      score-status session's audit.py): the confirmation draws, the training-box draws, the old packed draw and, when
#      they can be pulled, the packed policy's H5p7 eval-10 draws (H5P7_RUN; else scored on CPU after, same tool);
#   8. tools/e10v_verify.py verify (INVALID on failure) and tools/e10v_verdict.py (the PREREG section 5 swap rule:
#      SWAP-ELIGIBLE / NO-SWAP / INCOMPLETE / INVALID); one store push at the end. Nothing is packed or uploaded here.
# Integrity: new names only (refs/perc2e10v*, runs/perc2e10vs*_glock, results/perc2e10v*_glock_public, results/ev10_v4p);
# the packed reference P lives under results/ev10_v4p/packed_ref/, never refs/. tools/no_oracle.py must accept every
# input (before training and before the confirmation). Run ids carry -e10v- (refused otherwise).
# INCOMPLETE re-run (PREREG section 6; on THIS run's stored reference, same commit):
#   RERUN_FROM=<run id> SEEDS_TODO="43" bash ops/jobs/ev10_v4p.sh   (SEEDS_TODO may be empty: confirmation top-up only)
#   pulls rerun_files.txt of that run (reference, track, manifests) and the files its rerun_results.txt lists (each finished
#   seed's best/ results, the earlier confirmation draws; only files that exist), trains SEEDS_TODO, re-applies rule 2, adds confirmation draws of the chosen checkpoint until 10
#   are scored (draws of another checkpoint are set aside under conf_prev/), then score / verify / verdict.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-e10v-<sha7> 'bash ops/jobs/ev10_v4p.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; G=/content/results/ev10_v4p; mkdir -p $G
GD=$REPO_DIR/docs/research/work/perception-sprint-20261031/ev10retrain; HS=/content/hfstore
case "${RUN_ID:-}" in *-e10v-*) ;; *) log "ev10_v4p: RUN_ID '${RUN_ID:-}' must contain -e10v-" >> $J; exit 1 ;; esac
EP=10; BASE=mck; PRE=perc2e10v; SEEDS="42 43"; NCONF=10
# the packed eval-10 recipe (gl10A2) as the ep11 gate used it, SPLIT=eval; nothing overridable from the job string
export SPLIT=eval LIB=$REPO_DIR/meshes/library_v3 PIECES=$REPO_DIR/meshes/carve/ev10 SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 \
  CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1 ASSETS=/content/assets EVAL_LOCAL_REF=1
export MESH_DIR=$LIB GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
unset MA_ARGS CURR_SCALE ES ES_TARGET ES_N ES_PATIENCE FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE \
  ILC_HOLD ILC_ITERS ILC_GAIN EV_POP EV_GENS EV_ROBUST EV_JITTER CURVE_EVERY FDR FC_VOC_INERTIA FC_FDR_OBJ FC_FDR_TIPS \
  FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME ENV_EP10 VARIANT PDIR HANDS_ARGS HAND_REFINE MKREF_ARGS CR_ARGS \
  CONTACT_RETARGET TRAIN_LOCK CK_SWEEP
# inputs (PREREG section 2): store path, md5
P6=runs/20261026-pack6-5203d42; GA=runs/20261026-gl10A2-5e0e100; HIVE=processed/sequence_id=t3_ep010/robot_name=sharpa_wave
PREF=$GA/refs/glockt/ep10/$HIVE/ref_gl_ilc.parquet; PCK=$GA/results/glock_public/ep10/best/policy.safetensors
OLDP=$P6/results/submission/results/episode_000010
INPUTS="$P6/perc2/ep10/poses.npz 4fc5529eb457d706588e9b9fcf703baa
$P6/perc2/ep10/vo.json 64248915f0f480069521e4847da190c3
$P6/perc2/ep10/det_f0.npz 94c63769e568da177406ff6c39317349
$P6/refs/perc2mck/ep10/hands_refined.npz 419c230800b727240663597916cba59e
$GA/refs/perc2mck/ep10/hands.npz 15196aaf02dd9fa7c0b076ccd0e4c463
$GA/refs/perc2mck/ep10/hands_refined.npz 419c230800b727240663597916cba59e
$PREF 1a5003d94852c275519066645a1b9869
$PCK 1aadc8122769a2b54d120cdd58852922
$OLDP.parquet 64fdd8561f5e2cf51cd27e247a854a4a
$OLDP.json 92afa9d53b8fd438602c57c1e04559d9"
DEPTH0_MD5=d1543641b2f20cf024cdf1039631f671                        # refine's depth0.npy built from det_f0 (T1 / mask10)
# mkref's depth: D2 by the PREREG 3.2 rule (BUILD.md section 3: reproduces the packed table frame exactly)
DEPTH=cache/depth/eval/ep10/depths_fs0.5.npy; DEPTH_BYTES=1030400128; DEPTH_N=161
DEPTH0_SHA=ab38c4d79f6864be4b82afc9be1ed0ad97ee95ce6953230c2f8a6698ae1293cc
H5P7_RUN=${H5P7_RUN-20261031-h5p7-1a7cdff}                          # the packed policy's fresh draws (pack-10 comparison set)
case "$H5P7_RUN" in ''|*-h5p7-*) ;; *) log "ev10_v4p: H5P7_RUN '$H5P7_RUN' is not an h5p7 run" >> $J; exit 1 ;; esac
log "ev10_v4p code $(git -C $REPO_DIR rev-parse --short HEAD), ep $EP, prefix $PRE, seeds [$SEEDS], LIB $LIB, PIECES $PIECES, NREP $NREP, NCONF $NCONF, STEPS $STEPS, GL_ARGS [$GL_ARGS], H5P7_RUN ${H5P7_RUN:-none}${RERUN_FROM:+, RERUN_FROM $RERUN_FROM SEEDS_TODO [${SEEDS_TODO:-}]}" >> $J

stop() {  # $1 reason: push what exists, exit 1 (run_job.sh then self-destroys)
  log "ev10_v4p STOP: $1" >> $J; label "ev10 v4p stopped: $1"; echo "$1" > $G/STOPPED
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev10_v4p: push FAILED (self_destroy retries)" >> $J; exit 1
}
pull_md5() {  # $1 store path, $2 md5: single-file download, md5 checked
  bash $OPS/store.sh pull-files $1 >> $J 2>&1 || return 1
  [ "$(md5sum < $HS/$1 | cut -c1-32)" = "$2" ] || { log "ev10_v4p: $1 md5 $(md5sum < $HS/$1 | cut -c1-32) != $2" >> $J; return 1; }
}
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # as glock_public.sh (kit budget_mesh, support_fill union)
python $P/make_assets.py $LIB $ASSETS --pieces $PIECES >> $J 2>&1 || stop "make_assets FAILED"   # the references name /content/assets

train_seed() {  # $1 seed: one glock_public.sh call on this box's stored V copy
  local s=$1; label "ev10 v4p: seed $s"; log "ev10_v4p: seed $s, PAIRS [$EP:local:$BASE:${PRE}s$s]" >> $J
  ( REUSE_REF=1 REQUIRE_REUSE=1 SEED=$s PAIRS="$EP:local:$BASE:${PRE}s$s" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "ev10_v4p: seed $s returned $?" >> $J
}

confirm() {  # draws of the chosen checkpoint on the pristine evaluator until NCONF have a qa_policy.json (PREREG 3.4)
  local ck sha CK CLEAN=/content/v2d_clean KIT=/content/kit/v2d_submission_kit FCV=/content/v2d/robotic_grounding/flash_chord/.venv/bin/python i have n O tries=0
  ck=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['checkpoint'])" $G/choice.json)
  sha=$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sha256'])" $G/choice.json)
  python $T/no_oracle.py $ck $(python -c "import json, sys; d = json.load(open(sys.argv[1])); print(d['seeds'][d['chosen']]['results'])" $G/choice.json) >> $J 2>&1 \
    || stop "no_oracle refused the chosen checkpoint or its results"
  CK=$G/conf_checkpoints.json; python -c "import json, sys; json.dump({'10': sys.argv[2]}, open(sys.argv[1], 'w'))" $CK $ck
  [ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || stop "clean evaluator worktree FAILED"
  log "ev10_v4p: confirmation of $ck (sha256 ${sha:0:12}) on the clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files $(git -C $CLEAN status --short | wc -l)" >> $J
  mkdir -p $G/conf; for O in $G/conf/r*/; do                       # (re-run) draws of another checkpoint are set aside
    [ -d "$O" ] || continue
    [ "$(python -c "import json, sys; print(json.load(open(sys.argv[1])).get('checkpoint_sha256'))" $O/ep$EP/episode_0000$EP.json 2>/dev/null)" = "$sha" ] \
      || { mkdir -p $G/conf_prev; mv $O $G/conf_prev/$(basename $O)_$(date +%s); }
  done
  have() { ls $G/conf/r*/ep$EP/qa_policy.json 2> /dev/null | wc -l; }
  while [ "$(have)" -lt $NCONF ] && [ $tries -lt $((NCONF + 3)) ]; do
    n=$(( $(ls -d $G/conf/r* 2> /dev/null | sed 's#.*/r##' | sort -n | tail -1 || echo 0) + 1 )); O=$G/conf/r$n; tries=$((tries + 1))
    label "ev10 v4p: confirmation draw $n"; mkdir -p $O/results $O/ep$EP
    ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK --results $O/results \
        --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1
    echo $? > $O/eval_rc.txt
    cp $O/results/episode_0000$EP.* $O/ep$EP/ 2> /dev/null && python $P/qa.py policy $O/ep$EP $EP > /dev/null 2>&1 || true
    rm -rf $O/results
    log "ev10_v4p: confirmation draw $n rc $(cat $O/eval_rc.txt) sim_vs_ref $(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $O/ep$EP/qa_policy.json 2>/dev/null || echo none)" >> $J
  done
}

finish() {  # score, verify, verdict, push
  local sets
  label "ev10 v4p: scoring, verify, verdict"
  # the packed policy's fresh draws (else scored on CPU after): only once that run has finished (its h5_summary.json is
  # pushed last), and with short retries, so an absent file costs ~1 min, not store.sh's default ~10 min per file
  if [ -n "$H5P7_RUN" ] && PULL_RETRY_S=5 bash $OPS/store.sh pull-files runs/$H5P7_RUN/results/h5/h5_summary.json >> $J 2>&1; then
    for i in $(seq 1 10); do for x in parquet json; do
      f=runs/$H5P7_RUN/results/h5/r$i/ep10/episode_000010.$x
      PULL_RETRY_S=5 bash $OPS/store.sh pull-files $f >> $J 2>&1 && mkdir -p $G/packed_h5/r$i/ep10 && cp $HS/$f $G/packed_h5/r$i/ep10/ \
        || log "ev10_v4p: $f not pulled (the packed side is then completed on CPU after)" >> $J
    done; done
  else
    log "ev10_v4p: ${H5P7_RUN:-H5P7_RUN} has no h5_summary.json in the store (not finished?): the packed side is scored on CPU after" >> $J
  fi
  V=$(ls /content/refs/${PRE}_glockt/ep$EP/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1)
  sets="--set conf:V:$G/conf/r*/ep$EP/episode_0000$EP.parquet --set old:P:$G/old/r1/episode_0000$EP.parquet --set packed:P:$G/packed_h5/r*/ep10/episode_000010.parquet"
  for s in $SEEDS; do sets="$sets --set train$s:V:/content/results/${PRE}s${s}_glock_public/ep$EP/best/r*/episode_0000$EP.parquet"; done
  [ -n "$V" ] && python $T/e10v_score.py --kit /content/kit/v2d_submission_kit --lib $LIB --ref V=$V --ref P=$G/packed_ref/ref_gl_ilc.parquet \
    --out $G/score.json $sets > $G/score.txt 2>&1 || log "ev10_v4p: scoring FAILED or no V ($(tail -2 $G/score.txt 2>/dev/null | tr '\n' ' ' | cut -c1-300))" >> $J
  log "ev10_v4p scores: $(cut -c1-1500 $G/score.txt 2>/dev/null | tr '\n' ' ')" >> $J
  python $T/e10v_verify.py verify --content /content --seeds "$SEEDS" --steps $STEPS --dir $G --packed_ck $G/packed_ck/policy.safetensors \
    --out $G/verify.json > $G/verify.txt 2>&1
  log "ev10_v4p verify: $(cut -c1-1500 $G/verify.txt)" >> $J
  python $T/e10v_verdict.py --score $G/score.json --verify $G/verify.json --choice $G/choice.json --out $G/summary.json > $G/verdict.txt 2>&1
  log "ev10_v4p RESULT: $(cut -c1-2500 $G/verdict.txt)" >> $J
  ( cd /content && find results/${PRE}s*_glock_public/ep$EP/best -maxdepth 2 -type f \( -name summary.json -o -name policy.safetensors \
      -o -name qa_policy.json -o -name "episode_0000$EP.*" \) 2> /dev/null; find results/ev10_v4p/conf -mindepth 2 -maxdepth 3 -type f \
      \( -name qa_policy.json -o -name "episode_0000$EP.*" -o -name eval_rc.txt \) 2> /dev/null ) | sort > $G/rerun_results.txt   # what a re-run pulls
  for c in /content/results/${PRE}s*_glock_public/ep$EP/best/policy.safetensors; do   # stored config of each chosen checkpoint
    [ -f $c ] && /content/v2d/robotic_grounding/flash_chord/.venv/bin/python $T/ckpt_meta.py $c
  done > $G/ckpt_meta.txt 2>&1
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ev10_v4p: push FAILED (self_destroy retries)" >> $J
}

choose_and_confirm() {
  python $T/e10v_verify.py choose --content /content --seeds "$SEEDS" --out $G/choice.json > $G/choice.txt 2>&1; local rc=$?
  log "ev10_v4p choice: $(cut -c1-600 $G/choice.txt)" >> $J
  if [ $rc = 0 ]; then confirm; else log "ev10_v4p: INCOMPLETE before the confirmation (a seed is missing or thin; re-run RERUN_FROM=$RUN_ID SEEDS_TODO=...)" >> $J; fi
}

if [ -n "${RERUN_FROM:-}" ]; then   # ----- INCOMPLETE re-run on RERUN_FROM's stored reference (same commit)
  case "$RERUN_FROM" in *-e10v-*) ;; *) stop "RERUN_FROM '$RERUN_FROM' is not an e10v run" ;; esac
  for s in ${SEEDS_TODO:-}; do case " $SEEDS " in *" $s "*) ;; *) stop "bad seed $s in SEEDS_TODO" ;; esac; done
  label "ev10 v4p re-run: pulling $RERUN_FROM"
  bash $OPS/store.sh pull-files runs/$RERUN_FROM/results/ev10_v4p/rerun_files.txt >> $J 2>&1 || stop "rerun_files.txt of $RERUN_FROM missing"
  mapfile -t RF < $HS/runs/$RERUN_FROM/results/ev10_v4p/rerun_files.txt
  # the result files that run pushed (finish(): finished seeds' best/, confirmation draws), listed there: only files that
  # exist are pulled (a guessed absent path costs store.sh's 5 retries, ~10 min each: CPU mock, 31 Oct)
  bash $OPS/store.sh pull-files runs/$RERUN_FROM/results/ev10_v4p/rerun_results.txt >> $J 2>&1 \
    && while read -r f; do
         s_=$(echo $f | sed -n "s#^results/${PRE}s\([0-9]*\)_glock_public/.*#\1#p")
         [ -n "$s_" ] && case " ${SEEDS_TODO:-} " in *" $s_ "*) continue ;; esac   # a seed to retrain starts clean
         RF+=("$f")
       done < $HS/runs/$RERUN_FROM/results/ev10_v4p/rerun_results.txt
  for f in "${RF[@]}"; do
    bash $OPS/store.sh pull-files runs/$RERUN_FROM/$f >> $J 2>&1 || { log "ev10_v4p: re-run pull of $f failed" >> $J; continue; }
    mkdir -p /content/$(dirname $f) && cp -n $HS/runs/$RERUN_FROM/$f /content/$f
  done
  python $T/e10v_verify.py arms --content /content --seeds "$SEEDS" --out $G/arms_rerun.json --expect_manifest $G/arms.json > $G/arms_rerun.txt 2>&1 \
    || stop "seed copies of $RERUN_FROM's reference FAILED ($(tail -2 $G/arms_rerun.txt | tr '\n' ' ' | cut -c1-300))"
  for s in ${SEEDS_TODO:-}; do train_seed $s; done
  choose_and_confirm; finish; exit 0
fi

# ----- 1. inputs (single-file downloads), checked
label "ev10 v4p: inputs"
while read -r f m; do pull_md5 $f $m || stop "input $f missing or md5 mismatch"; done <<< "$INPUTS"
bash $OPS/store.sh pull-files $DEPTH >> $J 2>&1 || stop "pull of $DEPTH FAILED"
python - $HS/$DEPTH $DEPTH_BYTES $DEPTH0_SHA $DEPTH_N << 'EOF' > $G/depth_check.json || stop "depth cache check FAILED ($(cut -c1-300 $G/depth_check.json))"
import hashlib, json, os, sys
import numpy as np
f, nb, sha, n = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]); D = np.load(f, mmap_mode='r')
r = dict(path=f, bytes=os.path.getsize(f), shape=list(D.shape), frame0_sha256=hashlib.sha256(np.ascontiguousarray(D[0]).tobytes()).hexdigest())
r['ok'] = r['bytes'] == nb and r['frame0_sha256'] == sha and D.shape[1:] == (1000, 1600) and D.shape[0] == n
print(json.dumps(r)); sys.exit(0 if r['ok'] else 1)
EOF
IN=$G/in/ep$EP; mkdir -p $IN $G/packed_ref $G/packed_ck $G/old/r1
cp $HS/$P6/perc2/ep10/poses.npz $HS/$P6/perc2/ep10/vo.json $HS/$P6/refs/perc2mck/ep10/hands_refined.npz $IN/
python -c "
import numpy as np, sys
d = np.load(sys.argv[1])['depth'].astype(np.float32); np.save(sys.argv[2], np.repeat(np.repeat(d, 2, 0), 2, 1))" $HS/$P6/perc2/ep10/det_f0.npz $IN/depth0.npy \
  && [ "$(md5sum < $IN/depth0.npy | cut -c1-32)" = $DEPTH0_MD5 ] || stop "depth0.npy from det_f0 is not md5 $DEPTH0_MD5"
cp $HS/$PREF $G/packed_ref/ref_gl_ilc.parquet; cp $HS/$PCK $G/packed_ck/policy.safetensors; cp $HS/$OLDP.parquet $HS/$OLDP.json $G/old/r1/
python $T/no_oracle.py $(echo "$INPUTS" | cut -d' ' -f1) $DEPTH $IN/poses.npz $IN/hands_refined.npz $IN/depth0.npy $HS/$GA/refs/perc2mck/ep10/hands.npz \
  $G/packed_ref/ref_gl_ilc.parquet $G/packed_ck/policy.safetensors > $G/no_oracle_inputs.txt 2>&1 || stop "no_oracle refused an input ($(tail -2 $G/no_oracle_inputs.txt | tr '\n' ' ' | cut -c1-300))"
log "ev10_v4p: inputs ok ($(tr -d '\n' < $G/depth_check.json | cut -c1-300)); no_oracle: $(tail -1 $G/no_oracle_inputs.txt | cut -c1-200)" >> $J

# ----- 2. the V4p track, rebuilt here; B0
label "ev10 v4p: V4p track + B0"
mkvenv() {  # $1 dir, then pinned packages: python -m venv + pip, else uv (the box env has uv 0.13.4); as ep11_gate.sh
  local d=$1; shift
  { python -m venv $d && $d/bin/pip install -q "$@"; } >> $J 2>&1 && return 0
  rm -rf $d; { uv venv -q -p "$(command -v python)" $d && VIRTUAL_ENV=$d uv pip install -q "$@"; } >> $J 2>&1
}
VR=/content/e10v_vr; VP=/content/e10v_vp
mkvenv $VR numpy==2.5.4 scipy==1.18.1 trimesh==5.2.0 rtree==1.4.1 || stop "refine venv FAILED"
mkvenv $VP numpy==2.4.6 scipy==1.18.0 trimesh==4.12.2 mujoco==3.8.1 || stop "physics venv FAILED"
{ lscpu | grep 'Model name'; $VP/bin/python -c 'import numpy; numpy.show_runtime()'; } > $G/cpu.txt 2>&1 || true
bash $T/e10v_track.sh $IN $G/track $VR/bin/python $VP/bin/python >> $J 2>&1 || stop "V4p track FAILED (see $G/track/logs)"
python $T/e10v_verify.py b0 --tracks $G/track --expect $GD/expect --out $G/b0.json > $G/b0.txt 2>&1; rc=$?
log "ev10_v4p B0: $(cut -c1-800 $G/b0.txt)" >> $J
[ $rc = 0 ] || stop "B0 MISMATCH: the rebuilt V4p track is not the pre-registered one (b0.json); no reference built"

# ----- 3. the base reference (mck) on the V4p track
label "ev10 v4p: reference"
PD=$G/track/V/ep$EP; R=/content/refs/${PRE}$BASE/ep$EP
mkdir -p $R && cp $HS/$GA/refs/perc2mck/ep10/hands.npz $HS/$GA/refs/perc2mck/ep10/hands_refined.npz $R/ && ln -sfn $HS/$DEPTH $PD/depths_fs0.5.npy \
  || stop "reference folder setup FAILED"
M0=$(md5sum < $PD/poses.npz | cut -c1-32)
( export PERC=perc2 VARIANT=e10v$BASE PDIR=$PD MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" \
    STEPS=0 STOP_AFTER=reference SEED=42; bash $P/pipeline_ep.sh $EP ) > /content/ref_e10v_ep$EP.log 2>&1; rc=$?
python - $PD $R $M0 $rc "$HS/$DEPTH" << 'EOF' > $G/build.json
import glob, hashlib, json, os, sys
pd, R, m0, rc, depth = sys.argv[1:6]
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None
pq = sorted(glob.glob(f'{R}/processed/*/*/*.parquet'))
print(json.dumps(dict(rc=int(rc), pdir=pd, poses_md5_before=m0, poses_md5_after=md5(f'{pd}/poses.npz'),
                      depth=os.path.realpath(f'{pd}/depths_fs0.5.npy'), depth_expected=depth, hands_md5=md5(f'{R}/hands.npz'),
                      hands_refined_md5=md5(f'{R}/hands_refined.npz'), mkref_args='--wrist_cost 3.0', cr_args='--rest_settle 1',
                      reference=pq, reference_md5=[md5(f) for f in pq], table_frame=os.path.isfile(f'{R}/table_frame.npz'),
                      contact_retarget=os.path.isfile(f'{R}/contact_retarget.json')), indent=1))
EOF
[ $rc = 0 ] || stop "base reference FAILED ($(tail -3 /content/ref_e10v_ep$EP.log | tr '\n' ' ' | cut -c1-300))"
log "ev10_v4p: reference built ($(grep -a 'qa_ref\|contact_retarget:' /content/ref_e10v_ep$EP.log | cut -c1-200 | tr '\n' ' ' | cut -c1-500); table: $(grep -a 'table plane:\|object bottoms' $R/mkref_log.txt | cut -c1-200 | tr '\n' ' '))" >> $J

# ----- 4. grasp-lock reference stages once (seed 42) -> V; identity; byte copies per seed
label "ev10 v4p: grasp-lock reference"
( REUSE_REF=0 REF_ONLY=1 SEED=42 PAIRS="$EP:local:$BASE:$PRE" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "ev10_v4p: reference stages returned $?" >> $J
python $T/e10v_verify.py identity --content /content --track $PD/poses.npz --stored $IN/poses.npz --packed_ref $G/packed_ref/ref_gl_ilc.parquet \
  --out $G/identity.json > $G/identity.txt 2>&1 || stop "identity by content FAILED ($(cut -c1-400 $G/identity.txt))"
log "ev10_v4p identity: $(cut -c1-700 $G/identity.txt)" >> $J
python $T/e10v_verify.py arms --content /content --seeds "$SEEDS" --out $G/arms.json > $G/arms.txt 2>&1 \
  || stop "seed copies FAILED ($(tail -2 $G/arms.txt | tr '\n' ' ' | cut -c1-300))"
log "ev10_v4p arms: $(tail -1 $G/arms.txt | cut -c1-700)" >> $J
python $T/no_oracle.py /content/refs/${PRE}_glockt/ep$EP /content/refs/${PRE}$BASE/ep$EP $(for s in $SEEDS; do echo /content/refs/${PRE}s${s}_glockt/ep$EP; done) \
  > $G/no_oracle_refs.txt 2>&1 || stop "no_oracle refused a V4p reference ($(tail -2 $G/no_oracle_refs.txt | tr '\n' ' ' | cut -c1-300))"
( cd /content && find refs/${PRE}$BASE/ep$EP refs/${PRE}_glockt/ep$EP -type f ! -name 'depths_*'   # what a re-run pulls
  for f in rest_check.json zero_score.txt; do echo results/${PRE}_glock_public/ep$EP/$f; done
  for f in b0.json build.json depth_check.json arms.json identity.json track/V/ep10/poses.npz in/ep10/poses.npz packed_ref/ref_gl_ilc.parquet \
           packed_ck/policy.safetensors old/r1/episode_000010.parquet old/r1/episode_000010.json; do echo results/ev10_v4p/$f; done ) > $G/rerun_files.txt

# ----- 5. training: one call per seed; rule 2; 6. confirmation; 7-8. score, verify, verdict, push
for s in $SEEDS; do train_seed $s; done
choose_and_confirm
finish
