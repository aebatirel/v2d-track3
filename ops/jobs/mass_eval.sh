#!/bin/bash
# Eval retrain with realistic masses, ONE box of the batch (2026-10-31; plan docs/research/work/masses-eval-20261031/
# PLAN.md, adoption rule section 5 fixed before any result; build notes BUILD.md, job strings JOBS.txt). EVAL episodes
# only (no ground truth exists or is read; every score is sim_vs_ref against our own stored reference). Launched only
# after the public transfer check (20261031-mass-2ed46ea, masses-transfer-20261031/PREREG.md) ADOPTs, on the owner's GO.
# Each retrained episode trains on the PACKED policy's stored reference, unchanged (the table packed_refs.json in the plan
# folder: source run, md5, fingerprint, packed checkpoint), with the masses of docs/research/physics-2026-10-30/
# props_masses_only.json (mass-only, md5 asserted) in the simulator, for training and evaluation:
#   MODE=glock EPS="20 8" SEEDS="42 43": per episode its stored grasp-lock reference refs/glockt/ep<N> with its asset
#     copy refs/sf/ep<N>/assets (eval 10: /content/assets, library_v3 + pieces ev10, built here at 0.3 kg) and base
#     refs/perc2mck/ep<N> are pulled (the table's pull_files: single-file downloads, no store listing), md5 and
#     fingerprint checked, and the base's support stage must be the packed reference's (md5); tools/mass_arm.py --arms "mass1:<props>" copies the
#     asset folder to refs/mass1_sf/ep<N>/assets (masses rewritten, COM kept, inertia x m / 0.3) and the parquet per seed
#     to refs/mass1s<seed>_glockt/ep<N> (only object_urdf_paths differs). Then per seed ONE glock_public.sh invocation over
#     the episodes (waves of TRAIN_SLOTS 2) with SPLIT=eval REUSE_REF=1 REQUIRE_REUSE=1 (nothing is rebuilt; it exits if a
#     copy is not a finished reference): the packed runs' training recipe (70,004,736 steps, kp 400 embodiment, FDR + VOC,
#     the episode's ENV from the table, i.e. eval 33 CURR_SCALE 0.4), CURVE_REP 3, NREP 10, EVAL_TIMEOUT 1200.
#   MODE=std EPS=1 SEEDS=43: per episode the stored base refs/perc2mck/ep<N> (its processed parquet is a byte copy of the
#     packed refs/perc2mcks file: md5 checked) and perception perc2/ep<N>; then per seed hard_ab.sh SPLIT=eval CR=0 SUF=s,
#     the std_learner / carve_rerun recipe (FDR + VOC + deployment-exact starts 0.25, 250,003,456 steps, sweep 0.4/0.6/0.8),
#     MA_ARGS="--physics <props>" and the packed pieces (eval 1 ev01, eval 25 ev25) in the ONE /content/assets, NREP 10,
#     EVAL_TIMEOUT 1200. The episodes of one std box must share their pieces (eval 1's ev01 pot vs eval 28's default pot).
# Checks: tools/mass_eval_verify.py (each chosen checkpoint's saved config -> reference -> URDFs: the packed reference,
# the props masses with COM kept, the packed pieces, steps and seed, the rollouts' checkpoint sha256, and the saved config
# equal to the packed checkpoint's except paths and seed: one header download per episode) -> results/mass_eval/
# {verify.json, summary.json}: per episode VERIFIED / INVALID / INCOMPLETE, per seed n / mean / sd / min of the 10
# training-box rollouts, the rule-2 candidate and the confirmation strings for ops/jobs/h5_reeval.sh (rule 4).
# Run ids carry "-mev" (refused otherwise); every folder is new (refs/mass1*, results/mass1s*_glock_public, results/
# hard_ab/ep<N>/mcks-s<seed>, results/mass_eval); nothing a pack pulls by default is changed. One store push at the end.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-mevG1-<sha7> \
#     'MODE=glock EPS="20 8" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
# ARM=dr (2026-10-31, pack 9b D arm; docs/research/work/pack9b-20261031/{PREREG,BUILD}.md, JOBS.txt; opt-in, unset = the
# masses retrain above, unchanged): the same pulls and checks of the packed reference, then the packed recipe with
# start-state randomisation in training INSTEAD of masses: no mass_arm, no --physics, the 0.3 kg placeholder everywhere.
#   - ops/box/patch_flashchord_dr.py (md5 pinned below: determined-wright 4e5c8a0) after the jobs' other patches
#     (FC_DR_PATCH=1 in glock_public.sh / hard_ab.sh); FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=<seed> in the TRAINING
#     process (grasp lock: TRAIN_ENV; standard learner: ENV_EP<N>, plus FC_DR_SKIP_IMMEDIATE=1);
#   - grasp lock: tools/dr_arm.py makes per-seed BYTE copies refs/drs<seed>_glockt/ep<N> of the packed reference (same
#     URDF paths: the packed asset copy), PAIRS <N>:local:mck:drs<seed>; standard learner: hard_ab.sh SUF=dr (refs/
#     perc2mckdr, the CR=0 byte copy), MA_ARGS empty;
#   - tools/dr_eval_verify.py (as mass_eval_verify.py, plus the D training-log line) -> results/dr_eval/{verify,summary}.json;
#   - run ids carry "-dr" (refused otherwise); every folder is new (refs/drs*, results/drs*_glock_public, results/hard_ab/
#     ep<N>/mckdr-s<seed>, results/perc2mckdr, results/dr_eval); nothing a pack pulls by default is changed.
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-drG-<sha7> \
#     'ARM=dr MODE=glock EPS="14 16 33" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; J=${J:-/content/job.log}; ARM=${ARM:-}; ME=/content/results/mass_eval; [ "$ARM" = dr ] && ME=/content/results/dr_eval
mkdir -p $ME/packed
TAB=$REPO_DIR/docs/research/work/masses-eval-20261031/packed_refs.json
PROPS=$REPO_DIR/docs/research/physics-2026-10-30/props_masses_only.json; PROPS_MD5=d55089307ff2ced3e3244c95be22c9d6
APRE=mass1s                                                     # the per-seed reference prefix (ARM=dr: drs)
case "$ARM" in
  '') ;;
  dr)                                                           # (2026-10-31) pack 9b D arm; fixed here, never from the env
    case "${RUN_ID:-}" in *-dr*) ;; *) log "mass_eval ARM=dr: RUN_ID '${RUN_ID:-}' must contain -dr" >> $J; exit 1 ;; esac
    DR_PATCH_MD5=570a7f47793d02ba5b0bf3d5e6fd6eac                 # ops/box/patch_flashchord_dr.py of determined-wright 4e5c8a0
    [ "$(md5sum < $REPO_DIR/ops/box/patch_flashchord_dr.py | cut -c1-32)" = $DR_PATCH_MD5 ] \
      || { log "mass_eval ARM=dr: ops/box/patch_flashchord_dr.py md5 is not $DR_PATCH_MD5 (the 4e5c8a0 port the PREREG names)" >> $J; exit 1; }
    for v in FC_DR_RESET FC_DR_SEED FC_DR_SKIP_IMMEDIATE FC_DR_PATCH TRAIN_ENV; do
      [ -n "${!v:-}" ] && log "mass_eval ARM=dr: ignoring $v=${!v} from the environment" >> $J; unset $v
    done
    DR_RESET=1.5,0.015,0.01; APRE=drs ;;
  *) log "mass_eval: ARM '$ARM' unknown (unset = masses, dr = start-state randomisation)" >> $J; exit 1 ;;
esac
[ "$ARM" = dr ] || case "${RUN_ID:-}" in *-mev*) ;; *) log "mass_eval: RUN_ID '${RUN_ID:-}' must contain -mev" >> $J; exit 1 ;; esac
MODE=${MODE:-}; EPS=${EPS:-}; SEEDS=${SEEDS:-}
[ -n "$MODE" ] && [ -n "$EPS" ] && [ -n "$SEEDS" ] || { log "mass_eval: MODE, EPS and SEEDS are required" >> $J; exit 1; }
[ "$(md5sum < $PROPS | cut -c1-32)" = $PROPS_MD5 ] || { log "mass_eval: $PROPS md5 is not $PROPS_MD5" >> $J; exit 1; }
[ "$ARM" = dr ] || cp $PROPS $ME/props_used.json
tab() { python -c "import json, sys; print(json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]])" $TAB $1 $2; }
# the box's LIB and PIECES from the table (refused: an episode of the other mode; std episodes with different pieces or
# libraries in the one shared /content/assets; eval 8 (v3x beige cup) with eval 10 (whose assets are /content/assets, v3))
eval "$(python - $TAB "$MODE" "$EPS" << 'EOF'
import json, sys
T = json.load(open(sys.argv[1]))['episodes']; mode, eps = sys.argv[2], sys.argv[3].split()
def out(lib, pieces, err=''):
    print(f'BOX_LIB={lib}; BOX_PIECES={pieces or ""}; BOX_ERR="{err}"'); sys.exit()
bad = [e for e in eps if e not in T or T[e]['mode'] != mode]
if mode not in ('glock', 'std') or bad or len(set(eps)) != len(eps):
    out('', '', f'mode {mode}: episodes {bad or eps} are not distinct {mode} episodes of packed_refs.json')
shared = [e for e in eps if T[e]['shared_assets']]                           # references that name /content/assets
libs, pieces = {T[e]['lib'] for e in shared}, {T[e]['pieces'] for e in shared}
if len(libs) > 1 or len(pieces) > 1:
    out('', '', f'episodes {shared} share /content/assets but need libraries {sorted(libs)} / pieces {sorted(map(str, pieces))}')
lib = libs.pop() if libs else ('library_v3x' if any(T[e]['lib'] == 'library_v3x' for e in eps) else 'library_v3')
if shared and any(T[e]['lib'] != lib for e in eps):
    out('', '', f'episodes {eps}: /content/assets for {shared} is {lib}, another episode was trained with another library')
out(lib, pieces.pop() if pieces else '')
EOF
)"
[ -z "$BOX_ERR" ] && [ -n "$BOX_LIB" ] || { log "mass_eval: REFUSED: ${BOX_ERR:-no box settings}" >> $J; exit 1; }
LIB=$REPO_DIR/meshes/$BOX_LIB; PIECES=${BOX_PIECES:+$REPO_DIR/$BOX_PIECES}
log "mass_eval code $(git -C $REPO_DIR rev-parse --short HEAD), mode $MODE, episodes [$EPS], seeds [$SEEDS], props $PROPS ($PROPS_MD5), LIB $LIB, PIECES ${PIECES:-none}, table $TAB ($(md5sum < $TAB | cut -c1-12))" >> $J
[ "$ARM" = dr ] && log "mass_eval ARM=dr: NO masses (props NOT used: 0.3 kg placeholder everywhere); start-state randomisation FC_DR_RESET=$DR_RESET FC_DR_SEED=<seed>$([ $MODE = std ] && echo ' FC_DR_SKIP_IMMEDIATE=1') in the training process; patch ops/box/patch_flashchord_dr.py md5 $DR_PATCH_MD5; folders $ME, $([ $MODE = glock ] && echo 'refs/drs<seed>_glockt, results/drs<seed>_glock_public' || echo 'refs/perc2mckdr, results/hard_ab/ep<N>/mckdr-s<seed>')" >> $J

pull() {  # $1 episode: the table's pull_files (review F7, 2026-10-31): the store files under its pull sub-folders as the
  # 29 Oct store listing has them, ONE single-file download each (store.sh pull-files: retried, no store listing; before,
  # each sub-folder was a pull-run --include, i.e. a listing of the whole store), then placed under /content exactly as
  # pull-run places them (runs/<src>/<rel> -> /content/<rel>, an existing file is kept). Logs and images (*.txt, *.jpg,
  # *_log.json; nothing reads them here) may fail (pull-files refuses an empty file); any other file failing drops the episode.
  local e=$1 src f r miss=""
  src=$(tab $e source_run)
  for f in $(python -c "import json, sys; print(' '.join(json.load(open(sys.argv[1]))['episodes'][sys.argv[2]]['pull_files']))" $TAB $e); do
    if ! bash $OPS/store.sh pull-files $f 2>> $J > /dev/null; then   # its retries and failures go to the log
      case $f in *.txt|*.jpg|*_log.json) log "mass_eval ep$e: optional file $f not pulled (a log or image)" >> $J; continue ;; esac
      miss="$miss $f"; continue
    fi
    r=${f#runs/$src/}; mkdir -p /content/$(dirname $r); [ -e /content/$r ] || cp /content/hfstore/$f /content/$r
  done
  [ -z "$miss" ] || { log "mass_eval ep$e: pull-files FAILED for [${miss# }]" >> $J; return 1; }
  log "mass_eval ep$e: pulled $(python -c "import json, sys; print(len(json.load(open(sys.argv[1]))['episodes'][sys.argv[2]]['pull_files']))" $TAB $e) files of $src (pull_files, no store listing)" >> $J
}
fpmd5() {  # md5 and mass_arm fingerprint of one parquet
  echo "$(md5sum $1 | cut -c1-32) $(python -c "import sys; sys.path.insert(0, '$T'); import mass_arm, pyarrow.parquet as pq; print(mass_arm.traj_fingerprint(pq.read_table(sys.argv[1])))" $1)"
}
label "mass eval: pulling references [$EPS]"
OK_EPS=""
for e in $EPS; do
  src=$(tab $e source_run)
  pull $e || { log "mass_eval ep$e: pull of $src FAILED; episode dropped (INCOMPLETE)" >> $J; continue; }
  if [ $MODE = glock ]; then
    files=$(python -c "import json, sys; print(' '.join(json.load(open(sys.argv[1]))['episodes'][sys.argv[2]]['result_files']))" $TAB $e)
    mkdir -p /content/results/glock_public/ep$e; okf=1
    for f in $files; do                                           # REUSE_REF needs rest_check.json (+ zero_score, support_fill)
      bash $OPS/store.sh pull-files $f >> $J 2>&1 && cp /content/hfstore/$f /content/results/glock_public/ep$e/ || okf=0
    done
    [ $okf = 1 ] || { log "mass_eval ep$e: result files of $src missing ($files); episode dropped (INCOMPLETE)" >> $J; continue; }
    R=$(ls /content/refs/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null)
  else
    R=$(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet 2> /dev/null)
    [ -s /content/refs/perc2mck/ep$e/hands.npz ] && [ -s /content/perc2/ep$e/poses.npz ] \
      || { log "mass_eval ep$e: hands.npz / perc2 poses.npz of $src missing; episode dropped (INCOMPLETE)" >> $J; continue; }
  fi
  [ "$(echo "$R" | grep -c parquet)" = 1 ] || { log "mass_eval ep$e: $(echo "$R" | grep -c parquet) reference parquets from $src (one expected); dropped" >> $J; continue; }
  got=$(fpmd5 $R); want="$(tab $e md5) $(tab $e traj_fingerprint)"
  echo "ep$e $MODE $src $got $R" >> $ME/stored_refs.txt
  [ "$got" = "$want" ] || { log "mass_eval ep$e: REFUSED: stored reference $R is $got, the packed policy's is $want; dropped" >> $J; continue; }
  if [ $MODE = glock ]; then   # (review F2) the support stage: glock_public.sh copies refs/perc2mck/ep<N>/reconstructed_stage into
    # the arm copy (FlashCHORD reads <reference>/../../reconstructed_stage/<seq>_support.usda); it must be the packed
    # reference's (refs/glockt/ep<N>/reconstructed_stage): same file names, same md5
    sg=$(cd /content/refs/glockt/ep$e/reconstructed_stage 2> /dev/null && md5sum *.usda 2> /dev/null | sort -k2)
    sp=$(cd /content/refs/perc2mck/ep$e/reconstructed_stage 2> /dev/null && md5sum *.usda 2> /dev/null | sort -k2)
    echo "ep$e stage packed [$(echo $sg)] base [$(echo $sp)]" >> $ME/stored_refs.txt
    [ -n "$sg" ] && [ "$sg" = "$sp" ] || { log "mass_eval ep$e: REFUSED: support stage of refs/perc2mck/ep$e [$(echo $sp)] is not the packed reference's refs/glockt/ep$e [$(echo $sg)]; dropped" >> $J; continue; }
  fi
  rec=$(tab $e recipe_checkpoint)                                  # header of the packed checkpoint (recipe diff, verify)
  bash $OPS/store.sh pull-files $rec >> $J 2>&1 && cp /content/hfstore/$rec $ME/packed/ep$e.safetensors \
    || log "mass_eval ep$e: packed checkpoint $rec not pulled (verify: INCOMPLETE until it is read on CPU)" >> $J
  OK_EPS="$OK_EPS $e"
done
OK_EPS=${OK_EPS# }
[ -n "$OK_EPS" ] || { log "mass_eval: no episode has its packed reference on this box" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
log "mass_eval: packed references checked for [$OK_EPS] ($(tr '\n' ';' < $ME/stored_refs.txt | cut -c1-900))" >> $J

if [ $MODE = glock ]; then
  # the frozen glock_public training path on the stored references; nothing of the reference stages runs (REUSE_REF +
  # REQUIRE_REUSE), so SF / REPLAN / EVOLVE / GL_ARGS are only logged by glock_public.sh
  export SPLIT=eval LIB NREP=10 PAR=2 TRAIN_SLOTS=2 CURVE_REP=3 STEPS=70004736 EVAL_TIMEOUT=1200 NO_PUSH=1
  unset MA_ARGS SETTLE CURR_SCALE ES FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE ILC_HOLD
  if [ -n "$PIECES" ]; then export PIECES; else unset PIECES; fi
  for e in $OK_EPS; do v=$(tab $e env); unset ENV_EP$e; [ -n "$v" ] && export ENV_EP$e="$v" && log "mass_eval ep$e: ENV_EP$e=$v" >> $J; done
  label "mass eval: assets + arm copies [$OK_EPS]"
  # /content/assets at the 0.3 kg placeholder (glock_public.sh rebuilds it with the same arguments): the asset source of
  # a reference that names it (eval 10, pieces ev10); the other references carry their own refs/sf copies
  python $REPO_DIR/pipeline/make_assets.py $LIB /content/assets ${PIECES:+--pieces $PIECES} >> $J 2>&1 || { log "mass_eval: make_assets FAILED" >> $J; exit 1; }
  PAIRS_E=""; MANS=""
  for e in $OK_EPS; do
    if [ "$ARM" = dr ]; then                                       # byte copies of the packed reference, one per seed
      python $T/dr_arm.py --ep $e --base mck --seeds "$SEEDS" --table $TAB --out $ME/arms_ep$e.json > $ME/arms_ep$e.txt 2>&1 \
        || { log "mass_eval ep$e: dr_arm FAILED ($(tail -2 $ME/arms_ep$e.txt | tr '\n' ' ' | cut -c1-300)); episode dropped (INCOMPLETE)" >> $J; continue; }
    else
    python $T/mass_arm.py --ep $e --base mck --arms "mass1:$PROPS" --seeds "$SEEDS" --out $ME/arms_ep$e.json > $ME/arms_ep$e.txt 2>&1 \
      || { log "mass_eval ep$e: mass_arm FAILED ($(tail -2 $ME/arms_ep$e.txt | tr '\n' ' ' | cut -c1-300)); episode dropped (INCOMPLETE)" >> $J; continue; }
    fi
    log "mass_eval ep$e: $(tail -1 $ME/arms_ep$e.txt | cut -c1-700)" >> $J
    PAIRS_E="$PAIRS_E $e"; MANS="$MANS $ME/arms_ep$e.json"
  done
  [ -n "$PAIRS_E" ] || { log "mass_eval: no arm copy" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
  for s in $SEEDS; do                                              # one invocation per seed; its episodes in waves of 2
    P=""; for e in $PAIRS_E; do P="$P $e:local:mck:$APRE$s"; done
    label "mass eval: seed $s [$P ]"; log "mass_eval: seed $s, PAIRS [${P# }]" >> $J
    ( [ "$ARM" = dr ] && export FC_DR_PATCH=1 TRAIN_ENV="FC_DR_RESET=$DR_RESET FC_DR_SEED=$s"   # training process only
      REUSE_REF=1 REQUIRE_REUSE=1 SEED=$s PAIRS="${P# }" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "mass_eval: seed $s returned $?" >> $J
  done
  VARGS="--manifests \"${MANS# }\""
else
  # the std_learner.sh / carve_rerun.sh recipe on the pulled base (RUN local: hard_ab.sh copies refs/perc2mck -> perc2mcks)
  export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
  unset CURR_SCALE TRAIN_ENV ASSET_SRC FC_OBJECT_KEYPOINT_SCALE CK_SWEEP_EXTRA RENDER
  for e in $OK_EPS; do unset ENV_EP$e; done
  P=""; for e in $OK_EPS; do P="$P $e:local:mck"; done
  for s in $SEEDS; do
    label "mass eval: std seed $s [$P ]"; log "mass_eval: std seed $s, PAIRS [${P# }]" >> $J
    if [ "$ARM" = dr ]; then                                       # SUF dr: refs/perc2mckdr (the CR=0 byte copy); no masses
      ( for e in $OK_EPS; do export ENV_EP$e="FC_DR_RESET=$DR_RESET FC_DR_SEED=$s FC_DR_SKIP_IMMEDIATE=1"; done
        SPLIT=eval PDIR_ROOT=/content/perc2 SUF=dr CR=0 BASE_EVAL=0 NREP=10 SEED=$s LIB=$LIB PIECES=$PIECES MA_ARGS= FC_DR_PATCH=1 \
          EVAL_TIMEOUT=1200 NO_PUSH=1 PAIRS="${P# }" bash $REPO_DIR/ops/jobs/hard_ab.sh ) || log "mass_eval: std seed $s returned $?" >> $J
    else
    ( SPLIT=eval PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=10 SEED=$s LIB=$LIB PIECES=$PIECES MA_ARGS="--physics $PROPS" \
        EVAL_TIMEOUT=1200 NO_PUSH=1 PAIRS="${P# }" bash $REPO_DIR/ops/jobs/hard_ab.sh ) || log "mass_eval: std seed $s returned $?" >> $J
    fi
  done
  # the same /content/assets at the 0.3 kg placeholder: the yardstick for COM, inertia shape and collision pieces
  python $REPO_DIR/pipeline/make_assets.py $LIB $ME/assets_03 ${PIECES:+--pieces $PIECES} >> $J 2>&1 || log "mass_eval: 0.3 kg twin build FAILED" >> $J
  VARGS="--assets03 $ME/assets_03"
fi

label "mass eval: verify"
if [ "$ARM" = dr ]; then                                           # (2026-10-31) as mass_eval_verify.py, no masses, + D log line
  eval python $T/dr_eval_verify.py --mode $MODE --eps \"$OK_EPS\" --seeds \"$SEEDS\" --table $TAB --run $RUN_ID \
    --packed $ME/packed $VARGS --fc /content/v2d/robotic_grounding/flash_chord --out $ME/verify.json --summary $ME/summary.json > $ME/verify.txt 2>&1
  log "mass_eval ARM=dr RESULT: $(cut -c1-2500 $ME/verify.txt | tr '\n' ' ')" >> $J
else
eval python $T/mass_eval_verify.py --mode $MODE --eps \"$OK_EPS\" --seeds \"$SEEDS\" --props $PROPS --table $TAB --run $RUN_ID \
  --packed $ME/packed $VARGS --out $ME/verify.json --summary $ME/summary.json > $ME/verify.txt 2>&1
log "mass_eval RESULT: $(cut -c1-2500 $ME/verify.txt | tr '\n' ' ')" >> $J
fi
[ "$OK_EPS" = "$EPS" ] || log "mass_eval: episodes dropped before training: [$(for e in $EPS; do case " $OK_EPS " in *" $e "*) ;; *) printf '%s ' $e ;; esac; done)] (INCOMPLETE)" >> $J
for c in /content/results/$APRE*_glock_public/ep*/best/policy.safetensors $(python -c "
import json, sys
for e, x in json.load(open(sys.argv[1]))['episodes'].items():
    for s in x['seeds'].values():
        print(s.get('checkpoint') or '') if sys.argv[2] == 'std' else None" $ME/summary.json $MODE 2> /dev/null); do
  [ -s "$c" ] && /content/v2d/robotic_grounding/flash_chord/.venv/bin/python $T/ckpt_meta.py $c
done > $ME/ckpt_meta.txt 2>&1
# the store paths a pack would pull for these candidates (the reference and asset copies, each cell's chosen checkpoint): a
# later pack-side single-file pull can use this list instead of a store listing (review F7; push-run uploads every file
# under refs/ and keeps every checkpoint a results file names)
FD="refs/mass1_sf refs/mass1s*_glockt refs/perc2mcks"; [ "$ARM" = dr ] && FD="refs/drs*_glockt refs/perc2mckdr"
{ ( cd /content && find $FD -type f 2> /dev/null )
  python -c "
import json, os, sys
for x in json.load(open(sys.argv[1]))['episodes'].values():
    for s in x['seeds'].values():
        if s.get('checkpoint'):
            print(os.path.relpath(os.path.realpath(s['checkpoint']), os.path.realpath('/content')))" $ME/summary.json 2> /dev/null
} | sort -u | sed "s#^#runs/$RUN_ID/#" > $ME/files.txt
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "mass_eval: push FAILED (self_destroy retries)" >> $J
