#!/bin/bash
# ep11 rollout gate for the eval-10 cup-nest fix S12 V4p (2026-10-31). Pre-registered in
# docs/research/work/perception-sprint-20261031/ep11gate/PREREG.md (written before any result); build notes BUILD.md, launch
# string and cost JOBS.txt there. PUBLIC ep11 (eval 10's twin) only, one box. Two arms that differ ONLY in the refined track
# the reference is built from (PREREG section 2):
#   e11c (C, control)    the P_o track (Phase-1 run 20261030-orcP1b-87fc869, perc2 with library_v3) -> refine.py --steps S2
#   e11t (T, treatment)  the same track -> S12 --s12_mode support -> nest_physics.py --mode inner (meshes/carve/ev10) -> S2 (V4p)
# Steps (each arm the same way; nothing reads ground truth until score_registered.py scores a finished rollout):
#   1. inputs, one single-file store download each (store.sh pull-files; no listing), checked against the md5s mask10 used;
#      the ep11 depth cache (frame-0 sha256 as phase1/inputs.tsv) for mkref;
#   2. the two refined tracks rebuilt HERE with the committed code (tools/e11g_tracks.sh) in two pinned venvs (refine:
#      numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, rtree 1.4.1; physics: numpy 2.4.6, scipy 1.18.0, trimesh 4.12.2, mujoco
#      3.8.1: the versions that reproduce the mask10 files byte for byte on CPU), then B0 (tools/e11g_verify.py b0) against
#      the CPU outputs committed in ep11gate/expect/: IDENTICAL / NUMERIC / DIFFERS (T only) go on, MISMATCH stops the job
#      before any reference is built;
#   3. per arm the base reference as the packed eval-10 one (mck): pipeline_ep.sh with PDIR = the refined track, the stored
#      hands copied in (hands_mp / hand_refine skipped), mkref --wrist_cost 3.0, contact retargeting --rest_settle 1, assets
#      library_v3 + the ev10 collision pieces -> refs/perc2<arm>mck/ep11;
#   4. the grasp-lock reference stages once per arm (glock_public.sh REF_ONLY=1, seed 42) -> refs/perc2<arm>_glockt/ep11;
#      byte copies per seed (tools/e11g_verify.py arms) -> refs/perc2<arm>s<seed>_glockt/ep11;
#   5. per seed (42, 43) one glock_public.sh call training both arms in one wave (REUSE_REF=1 REQUIRE_REUSE=1): 70M steps,
#      checkpoint by sim_vs_ref over 3 evaluations per curve checkpoint, NREP 10 official evaluations, each scored
#      sim_vs_ref + registered ADD-AUC vs mocap (library_v3); EVAL_TIMEOUT 1200 (timeout -k 60);
#   6. tools/e11g_verify.py verify (chain + config diff; INVALID on failure), tools/e11g_verdict.py (the PREREG rule:
#      PASS / FAIL / INCOMPLETE / INVALID); one store push at the end.
# The recipe is the packed eval-10 policy's (run 20261026-gl10A2-5e0e100 job.log): SF 0, PIECES ev10, REPLAN 1, EVOLVE 0,
# CURVE_REP 3, 70,004,736 steps, its GL_ARGS; nothing of it can be overridden from the job string.
# INCOMPLETE re-run (PREREG section 3; only the missing cells, on THIS run's stored references, same commit):
#   RERUN_FROM=<run id> CELLS="e11t:43 ..." bash ops/jobs/ep11_gate.sh
#   pulls the files listed in runs/<RERUN_FROM>/results/ep11_gate/rerun_files.txt (references, manifests) and each other
#   cell's best/summary.json + best/policy.safetensors, trains the listed cells only, then verify + verdict over all cells.
# Integrity: public only; mocap is read only by score_registered.py after each rollout. Run ids carry -e11g-; folders carry
# the arm prefixes perc2e11c / perc2e11t (no eval job pulls them; an ep11 policy cannot serve an eval episode).
# Output: /content/results/ep11_gate/{b0.json,build_<arm>.json,arms.json,verify.json,summary.json,tracks/,...}; RESULT
# lines in /content/job.log.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-e11g-<sha7> 'bash ops/jobs/ep11_gate.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; G=/content/results/ep11_gate; mkdir -p $G
GD=$REPO_DIR/docs/research/work/perception-sprint-20261031/ep11gate; HS=/content/hfstore
case "${RUN_ID:-}" in *-e11g-*) ;; *) log "ep11_gate: RUN_ID '${RUN_ID:-}' must contain -e11g-" >> $J; exit 1 ;; esac
EP=11; ARMS="e11c e11t"; BASE=mck; SEEDS="42 43"; declare -A TRK=([e11c]=C [e11t]=T)
# the packed eval-10 recipe (gl10A2), NREP 10 / PAR 2 / EVAL_TIMEOUT as mass_check.sh; nothing overridable
export SPLIT=public LIB=$REPO_DIR/meshes/library_v3 PIECES=$REPO_DIR/meshes/carve/ev10 SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 \
  CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1 ASSETS=/content/assets
export MESH_DIR=$LIB GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"
unset MA_ARGS CURR_SCALE ES ES_TARGET ES_N ES_PATIENCE FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE \
  ILC_HOLD ILC_ITERS ILC_GAIN EV_POP EV_GENS EV_ROBUST EV_JITTER CURVE_EVERY FDR FC_VOC_INERTIA FC_FDR_OBJ FC_FDR_TIPS \
  FC_OBJECT_KEYPOINT_SCALE FC_IMMEDIATE_FIRST_FRAME ENV_EP11 VARIANT PDIR HANDS_ARGS HAND_REFINE MKREF_ARGS CR_ARGS \
  CONTACT_RETARGET TRAIN_LOCK CK_SWEEP
# inputs (PREREG section 2.1): store path -> md5 (the files mask10 used)
P1=runs/20261030-orcP1b-87fc869/results/leak_p1/ep11; HD=runs/20261025-g1-022fece/refs/perc2m/ep11
declare -A INP=([$P1/perc2/poses.npz]=2f4800ff07fd37da531acf2ee60f120e [$P1/perc2/poses_world_vo.npz]=6e2c2ff5fd0ea38c0b0f21b4783048a4
                [$P1/depth0.npy]=5b9fb362bda1264854c5fdc0c9e4c502 [$HD/hands_refined.npz]=d9c391deaf73509b6c52e3b743580272
                [$HD/hands.npz]=0c7652fde628e502b6fd4836ced85f72)
DEPTH=cache/depth/public/ep11/depths_fs0.5.npy; DEPTH_BYTES=876800128; DEPTH0_SHA=070547135e460052c1c2cf15862068feaf6225076b2bf614fef9a63494680588
log "ep11_gate code $(git -C $REPO_DIR rev-parse --short HEAD), arms [$ARMS], seeds [$SEEDS], LIB $LIB, PIECES $PIECES, NREP $NREP, STEPS $STEPS, GL_ARGS [$GL_ARGS]${RERUN_FROM:+, RERUN_FROM $RERUN_FROM CELLS [${CELLS:-}]}" >> $J

stop() {  # $1 reason: push what exists, exit 1 (run_job.sh then self-destroys)
  log "ep11_gate STOP: $1" >> $J; label "ep11 gate stopped: $1"; echo "$1" > $G/STOPPED
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ep11_gate: push FAILED (self_destroy retries)" >> $J; exit 1
}
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # as glock_public.sh (kit budget_mesh, support_fill union)
python $P/make_assets.py $LIB $ASSETS --pieces $PIECES >> $J 2>&1 || stop "make_assets FAILED"   # the references name /content/assets

verify_and_verdict() {  # $1 extra verify args
  label "ep11 gate: verify + verdict"
  python $T/e11g_verify.py verify --content /content --arms "$ARMS" --seeds "$SEEDS" --base $BASE --steps $STEPS --gate $G \
    ${1:-} --out $G/verify.json > $G/verify.txt 2>&1
  log "ep11_gate verify: $(cut -c1-1500 $G/verify.txt)" >> $J
  python $T/e11g_verdict.py --content /content --arms "$ARMS" --seeds "$SEEDS" --gate $G --out $G/summary.json > $G/verdict.txt 2>&1
  log "ep11_gate RESULT: $(cut -c1-2000 $G/verdict.txt)" >> $J
  for c in /content/results/perc2e11?s*_glock_public/ep11/best/policy.safetensors; do   # stored config of each chosen checkpoint
    [ -f $c ] && /content/v2d/robotic_grounding/flash_chord/.venv/bin/python $T/ckpt_meta.py $c
  done > $G/ckpt_meta.txt 2>&1
}

train_seed() {  # $1 seed, $2 "arm ..." to train: one glock_public.sh call (one wave), on this box's stored references
  local s=$1 x pr=""
  for x in $2; do pr="$pr 11:local:$BASE:perc2${x}s$s"; done
  label "ep11 gate: seed $s [$pr ]"; log "ep11_gate: seed $s, PAIRS [${pr# }]" >> $J
  ( REUSE_REF=1 REQUIRE_REUSE=1 SEED=$s PAIRS="${pr# }" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "ep11_gate: seed $s returned $?" >> $J
}

if [ -n "${RERUN_FROM:-}" ]; then   # ----- INCOMPLETE re-run: only the missing cells, on RERUN_FROM's stored references
  case "$RERUN_FROM" in *-e11g-*) ;; *) stop "RERUN_FROM '$RERUN_FROM' is not an ep11-gate run" ;; esac
  [ -n "${CELLS:-}" ] || stop "RERUN_FROM needs CELLS (arm:seed ...)"
  for c in $CELLS; do case " $ARMS " in *" ${c%%:*} "*) ;; *) stop "bad cell $c" ;; esac
                      case " $SEEDS " in *" ${c#*:} "*) ;; *) stop "bad cell $c" ;; esac; done
  label "ep11 gate re-run: pulling $RERUN_FROM"
  bash $OPS/store.sh pull-files runs/$RERUN_FROM/results/ep11_gate/rerun_files.txt >> $J 2>&1 || stop "rerun_files.txt of $RERUN_FROM missing"
  mapfile -t RF < $HS/runs/$RERUN_FROM/results/ep11_gate/rerun_files.txt
  RF+=(results/ep11_gate/verify.json results/ep11_gate/summary.json)  # the earlier verdict (eval timeouts of the other cells)
  for a in $ARMS; do for s in $SEEDS; do                             # the other cells' results (verify pairs + verdict)
    case " $CELLS " in *" $a:$s "*) continue ;; esac
    RF+=(results/perc2${a}s${s}_glock_public/ep11/best/summary.json results/perc2${a}s${s}_glock_public/ep11/best/policy.safetensors)
  done; done
  for f in "${RF[@]}"; do
    bash $OPS/store.sh pull-files runs/$RERUN_FROM/$f >> $J 2>&1 || { log "ep11_gate: re-run pull of $f failed" >> $J; continue; }
    mkdir -p /content/$(dirname $f) && cp -n $HS/runs/$RERUN_FROM/$f /content/$f
  done
  mkdir -p $G/prior && for f in verify.json summary.json b0.json; do [ -f $G/$f ] && cp $G/$f $G/prior/; done
  python $T/e11g_verify.py arms --content /content --arms "$ARMS" --seeds "$SEEDS" --base $BASE --out $G/arms_rerun.json \
    --expect_manifest $G/arms.json > $G/arms_rerun.txt 2>&1 || stop "arm copies of $RERUN_FROM's references FAILED ($(tail -2 $G/arms_rerun.txt | tr '\n' ' ' | cut -c1-300))"
  for s in $SEEDS; do
    x=""; for a in $ARMS; do case " $CELLS " in *" $a:$s "*) x="$x $a" ;; esac; done
    [ -n "$x" ] && train_seed $s "${x# }"
  done
  verify_and_verdict "--prior $G/prior/verify.json"
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ep11_gate: push FAILED (self_destroy retries)" >> $J
  exit 0
fi

# ----- 1. inputs (single-file downloads), checked
label "ep11 gate: inputs"
for f in "${!INP[@]}" $DEPTH; do
  bash $OPS/store.sh pull-files $f >> $J 2>&1 || stop "pull of $f FAILED"
done
for f in "${!INP[@]}"; do
  m=$(md5sum < $HS/$f | cut -c1-32); [ "$m" = "${INP[$f]}" ] || stop "$f md5 $m != ${INP[$f]}"
done
python - $HS/$DEPTH $DEPTH_BYTES $DEPTH0_SHA << 'EOF' > $G/depth_check.json || stop "depth cache check FAILED ($(cut -c1-300 $G/depth_check.json))"
import hashlib, json, os, sys
import numpy as np
f, nb, sha = sys.argv[1], int(sys.argv[2]), sys.argv[3]; D = np.load(f, mmap_mode='r')
r = dict(path=f, bytes=os.path.getsize(f), shape=list(D.shape), frame0_sha256=hashlib.sha256(np.array(D[0]).tobytes()).hexdigest())
r['ok'] = r['bytes'] == nb and r['frame0_sha256'] == sha and D.shape[1:] == (1000, 1600) and D.shape[0] == 137
print(json.dumps(r)); sys.exit(0 if r['ok'] else 1)
EOF
IN=$G/in/ep11; mkdir -p $IN
cp $HS/$P1/perc2/poses.npz $HS/$P1/perc2/poses_world_vo.npz $HS/$P1/depth0.npy $HS/$HD/hands_refined.npz $IN/
log "ep11_gate: inputs ok ($(tr -d '\n' < $G/depth_check.json | cut -c1-300))" >> $J

# ----- 2. the two refined tracks, rebuilt here; B0
label "ep11 gate: refined tracks + B0"
mkvenv() {  # $1 dir, then pinned packages: python -m venv + pip, else uv (the box env has uv 0.13.4)
  local d=$1; shift
  { python -m venv $d && $d/bin/pip install -q "$@"; } >> $J 2>&1 && return 0
  rm -rf $d; { uv venv -q -p "$(command -v python)" $d && VIRTUAL_ENV=$d uv pip install -q "$@"; } >> $J 2>&1
}
VR=/content/e11g_vr; VP=/content/e11g_vp
mkvenv $VR numpy==2.5.4 scipy==1.18.1 trimesh==5.2.0 rtree==1.4.1 || stop "refine venv FAILED"
mkvenv $VP numpy==2.4.6 scipy==1.18.0 trimesh==4.12.2 mujoco==3.8.1 || stop "physics venv FAILED"
bash $T/e11g_tracks.sh $IN $G/tracks $VR/bin/python $VP/bin/python >> $J 2>&1 || stop "refined tracks FAILED (see $G/tracks/logs)"
python $T/e11g_verify.py b0 --tracks $G/tracks --expect $GD/expect --out $G/b0.json > $G/b0.txt 2>&1; rc=$?
log "ep11_gate B0: $(cut -c1-800 $G/b0.txt)" >> $J
[ $rc = 0 ] || stop "B0 MISMATCH: the rebuilt tracks are not the pre-registered ones (b0.json); no reference built"

# ----- 3. base references (mck), both arms concurrently
label "ep11 gate: references"
build_ref() {  # $1 arm
  local a=$1 V=$1$BASE PD=$G/tracks/${TRK[$1]}/ep11 R=/content/refs/perc2$1$BASE/ep11
  mkdir -p $R && cp $HS/$HD/hands.npz $HS/$HD/hands_refined.npz $R/ && ln -sfn $HS/$DEPTH $PD/depths_fs0.5.npy || return 1
  local m0; m0=$(md5sum < $PD/poses.npz | cut -c1-32)
  ( export PERC=perc2 VARIANT=$V PDIR=$PD MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" \
      STEPS=0 STOP_AFTER=reference SEED=42; bash $P/pipeline_ep.sh $EP ) > /content/ref_${a}_ep11.log 2>&1; local rc=$?
  python - $a $PD $R $m0 $rc "$HS/$DEPTH" << 'EOF' > $G/build_$a.json
import glob, hashlib, json, os, sys
a, pd, R, m0, rc, depth = sys.argv[1:7]
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None
pq = sorted(glob.glob(f'{R}/processed/*/*/*.parquet'))
print(json.dumps(dict(arm=a, rc=int(rc), pdir=pd, poses_md5_before=m0, poses_md5_after=md5(f'{pd}/poses.npz'),
                      depth=os.path.realpath(f'{pd}/depths_fs0.5.npy'), depth_expected=depth, hands_md5=md5(f'{R}/hands.npz'),
                      hands_refined_md5=md5(f'{R}/hands_refined.npz'), mkref_args='--wrist_cost 3.0', cr_args='--rest_settle 1',
                      reference=pq, reference_md5=[md5(f) for f in pq], table_frame=os.path.isfile(f'{R}/table_frame.npz'),
                      contact_retarget=os.path.isfile(f'{R}/contact_retarget.json')), indent=1))
EOF
  [ $rc = 0 ] || { log "ep11_gate $a: reference FAILED ($(tail -3 /content/ref_${a}_ep11.log | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
  log "ep11_gate $a: reference built ($(grep -a 'qa_ref\|contact_retarget:' /content/ref_${a}_ep11.log | cut -c1-200 | tr '\n' ' ' | cut -c1-500))" >> $J
}
pids=(); for a in $ARMS; do build_ref $a & pids+=($!); sleep 30; done
for p in "${pids[@]}"; do wait $p || stop "a base reference FAILED (build_<arm>.json, /content/ref_<arm>_ep11.log)"; done

# ----- 4. grasp-lock reference stages once per arm (seed 42), then byte copies per seed
label "ep11 gate: grasp-lock references"
( REUSE_REF=0 REF_ONLY=1 SEED=42 PAIRS="11:local:$BASE:perc2e11c 11:local:$BASE:perc2e11t" bash $REPO_DIR/ops/jobs/glock_public.sh ) \
  || log "ep11_gate: reference stages returned $?" >> $J
python $T/e11g_verify.py arms --content /content --arms "$ARMS" --seeds "$SEEDS" --base $BASE --out $G/arms.json > $G/arms.txt 2>&1 \
  || stop "arm copies FAILED ($(tail -2 $G/arms.txt | tr '\n' ' ' | cut -c1-300))"
log "ep11_gate arms: $(tail -1 $G/arms.txt | cut -c1-900)" >> $J
( cd /content && for a in $ARMS; do                                  # what an INCOMPLETE re-run pulls (one file each)
    find refs/perc2$a$BASE/ep11 refs/perc2${a}_glockt/ep11 -type f ! -name 'depths_*'
    for f in rest_check.json zero_score.txt; do echo results/perc2${a}_glock_public/ep11/$f; done
  done; for f in b0.json arms.json build_e11c.json build_e11t.json tracks/C/ep11/poses.npz tracks/T/ep11/poses.npz; do
    echo results/ep11_gate/$f; done ) > $G/rerun_files.txt

# ----- 5. training: one wave per seed, both arms
for s in $SEEDS; do train_seed $s "$ARMS"; done

# ----- 6. verify + verdict, push
verify_and_verdict
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "ep11_gate: push FAILED (self_destroy retries)" >> $J
