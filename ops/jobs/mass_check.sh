#!/bin/bash
# Realistic-mass transfer check on OUR meshes (2026-10-31; pre-registered: docs/research/work/masses-transfer-20261031/
# PREREG.md, written before any result; build notes BUILD.md, launch string JOBS.txt). PUBLIC episodes only, one box.
# The physics session (branch claude/determined-wright-3joens, physics-2026-10-30/README.md "Round 3") found realistic
# per-object masses (props_masses_only.json) instead of the 0.3 kg placeholder raised grasp-lock policies vs mocap by
# +0.090 on 4 public episodes, with the organiser SCANS as simulator meshes. This job asks whether that transfers to our
# pipeline: library_v3 meshes, our perceived references, the frozen grasp-lock recipe (recipe_arms_launch.sh GLOCK_COMMON).
#   episodes  ep2 (pot + lid; base reference 20261024-ev3-2c1e4dd perc2mck) and ep12 (cup into rack; the stored
#             grasp-lock reference of 20261024-ev2-2c1e4dd perc2mc, as recipe arm A trained on).
#             MODE build: the grasp-lock reference is built HERE once (frozen recipe, 0.3 kg; glock_public.sh REF_ONLY=1):
#             ep2 has no stored grasp-lock reference made with the frozen recipe (its stored one is E3's of 23 Oct:
#             approach 6 cm, REPLAN 1, no onset anchor, no evolutionary search). MODE reuse: the stored one.
#   arms      mass0 = 0.3 kg placeholder (control); mass1 = props_masses_only.json (mass only; COM and inertia shape stay
#             the mesh's own). Each episode's two arms train on the SAME reference: tools/mass_arm.py copies its asset
#             folder per arm (refs/<arm>_sf/ep<N>/assets; mass1's URDF masses rewritten, inertia scaled by the mass
#             ratio as make_assets.py --physics) and its parquet per arm and seed with object_urdf_paths pointing there
#             (every other column identical). MA_ARGS is NOT used: a grasp-lock reference names its own asset copy
#             (refs/sf/ep<N>/assets), so make_assets.py never reaches it.
#   seeds     42 and 43, one glock_public.sh invocation per seed (4 trainings = 2 waves of TRAIN_SLOTS=2: ep2's arms, then
#             ep12's), REUSE_REF=1 REQUIRE_REUSE=1 on the arm copies (glock_public.sh exits, rebuilding nothing, if an arm
#             copy is not a finished reference), 70M steps, checkpoint chosen by sim_vs_ref (no ground truth), then
#             NREP=10 official evaluations each scored sim_vs_ref + registered ADD-AUC vs mocap (library_v3).
#             EVAL_TIMEOUT=1200 (timeout -k 60): each evaluation's exit code -> eval_rc.txt; cuts are counted per cell
#             (verify.json eval_timeouts) and printed right after the verdict label (never silently accepted).
#   checks    tools/mass_verify.py: each chosen checkpoint's saved config -> reference parquet -> URDFs (what FlashCHORD and
#             the official evaluator load) carry the arm's masses; same reference fingerprint; configs differ only in
#             output_dir / task.parquet (or by the arm's name only); seeds and steps. A cell without a chosen checkpoint
#             is listed as missing (verdict INCOMPLETE), not a verify failure. tools/mass_verdict.py: summary + the
#             pre-registered verdict. Build amendments of 31 Oct (mechanics only): PREREG.md section 6.
# Integrity: public only; mocap is read only by score_registered.py after each rollout (scoring). Nothing here goes to
# an eval pack: run ids carry "-mass-"; the arm folders are refs/mass{0,1}*, results/mass{0,1}s*_glock_public.
# Output: /content/results/mass_check/{summary.json,verify.json,arms_ep<N>.json,stored_refs.txt}; RESULT lines in
# /content/job.log. One store push at the end (glock_public.sh runs with NO_PUSH=1).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-mass-<sha7> 'bash ops/jobs/mass_check.sh'
# Masses v2 (2026-10-31, opt-in; without MV2_TAB everything above and below runs exactly as before): MV2_TAB=<table json,
# repo-relative> MV2_EPS="<this box's episodes>" -> 4 public episodes over 2 boxes (docs/research/work/masses-v2-20261031/
# PREREG.md, table refs_v2.json, job strings JOBS.txt). Per episode the table names the stored finished grasp-lock reference
# (source run, base) and its files: each is pulled with ONE single-file download (store.sh pull-files; no store listing)
# and placed under /content as pull-run would; the reference's md5 + fingerprint must equal the table's, else the episode
# is dropped (its cells missing -> INCOMPLETE; never rebuilt, never swapped). The props md5 must be the table's. RUN_ID must
# contain -mv2. The box's verdict line is mass_verdict.py --rule v2 --partial (a reading, never the verdict: that merges
# both boxes on CPU). An INCOMPLETE re-run sets SEEDS and SRC_EP<N>=<that v2 run id>:<base>:reuse (same table paths).
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; J=${J:-/content/job.log}; MC=/content/results/mass_check; mkdir -p $MC
if [ -n "${MV2_TAB:-}" ]; then
  case "${RUN_ID:-}" in *-mv2*) ;; *) log "mass_check v2: RUN_ID '${RUN_ID:-}' must contain -mv2" >> $J; exit 1 ;; esac
else
case "${RUN_ID:-}" in *-mass-*) ;; *) log "mass_check: RUN_ID '${RUN_ID:-}' must contain -mass-" >> $J; exit 1 ;; esac
fi
EPS="2 12"; ARMS="mass0 mass1"; PROPS=$REPO_DIR/docs/research/physics-2026-10-30/props_masses_only.json
# SEEDS / SRC_EP<N> are set only for an INCOMPLETE re-run (PREREG section 3): the missing seed(s) on THIS run's stored
# references, e.g. SEEDS=43 SRC_EP2=<this run id>:mck:reuse SRC_EP12=<this run id>:mc:reuse (never rebuild ep2's reference)
SEEDS=${SEEDS:-"42 43"}; SRC_EP2=${SRC_EP2:-20261024-ev3-2c1e4dd:mck:build}; SRC_EP12=${SRC_EP12:-20261024-ev2-2c1e4dd:mc:reuse}
if [ -n "${MV2_TAB:-}" ]; then                                    # Masses v2: episodes and sources from the table
  TAB=$REPO_DIR/$MV2_TAB
  tabv() { python -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]; print(' '.join(v) if isinstance(v, list) else v)" $TAB $1 $2; }
  [ -f "$TAB" ] || { log "mass_check v2: table $TAB missing" >> $J; exit 1; }
  [ "$(md5sum < $PROPS | cut -c1-32)" = "$(python -c "import json, sys; print(json.load(open(sys.argv[1]))['props_md5'])" $TAB)" ] \
    || { log "mass_check v2: $PROPS md5 is not the table's props_md5" >> $J; exit 1; }
  EPS=${MV2_EPS:-}
  [ -n "$EPS" ] || { log "mass_check v2: MV2_EPS is required" >> $J; exit 1; }
  for e in $EPS; do
    python -c "import json, sys; T = json.load(open(sys.argv[1])); sys.exit(0 if sys.argv[2] in T['episodes'] and int(sys.argv[2]) in T['all_eps'] else 1)" $TAB $e \
      || { log "mass_check v2: episode $e is not one of the table's episodes" >> $J; exit 1; }
    v=SRC_EP$e; [ -n "${!v:-}" ] || eval "SRC_EP$e=$(tabv $e source_run):$(tabv $e base):$(tabv $e mode)"
  done
fi
# the frozen grasp-lock recipe (recipe_arms_launch.sh GLOCK_COMMON) with NREP 10 / PAR 2 (oracle twins); nothing overridable
export SPLIT=public LIB=$REPO_DIR/meshes/library_v3 SF=1 REPLAN=0 EVOLVE=1 CURVE_REP=3 NREP=10 PAR=2 TRAIN_SLOTS=2 STEPS=70004736 \
  EVAL_TIMEOUT=1200 NO_PUSH=1
export GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"
unset MA_ARGS PIECES SETTLE CURR_SCALE ES FC_DROP_START TRAIN_ARGS TRAIN_ENV REF_ONLY REUSE_REF REQUIRE_REUSE
for e in $EPS; do unset ENV_EP$e; done
if [ -n "${MV2_TAB:-}" ]; then
  log "mass_check v2 code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], seeds [$SEEDS], arms [$ARMS], props $PROPS ($(md5sum < $PROPS | cut -c1-12)), sources$(for e in $EPS; do v=SRC_EP$e; printf ' ep%s %s' $e ${!v}; done), table $MV2_TAB ($(md5sum < $TAB | cut -c1-12)), LIB $LIB, NREP $NREP, STEPS $STEPS, GL_ARGS [$GL_ARGS]" >> $J
else
log "mass_check code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], seeds [$SEEDS], arms [$ARMS], props $PROPS ($(md5sum < $PROPS | cut -c1-12)), sources ep2 $SRC_EP2 ep12 $SRC_EP12, LIB $LIB, NREP $NREP, STEPS $STEPS, GL_ARGS [$GL_ARGS]" >> $J
fi
cp $PROPS $MC/props_used.json

pull() {  # $1 run, $2 PULL_SUB: up to 3 tries (HF 429)
  local i
  for i in 1 2 3; do
    PULL_SUB="$2" timeout 2400 bash $OPS/store.sh pull-run $1 >> $J 2>&1 && return 0
    log "mass_check: pull-run $1 [$2] try $i failed" >> $J; sleep $((120 * i))
  done
  return 1
}
label "mass check: pulling references"
BUILD=""; REUSE=""
if [ -n "${MV2_TAB:-}" ]; then                                    # Masses v2: the table's files, one download each
  for e in $EPS; do
    v=SRC_EP$e; IFS=: read -r run base mode <<< "${!v}"
    if [ "$mode" != reuse ] || [ "$base" != "$(tabv $e base)" ]; then
      log "mass_check v2 ep$e: source ${!v} is not a reuse of the table's base $(tabv $e base); episode dropped (its cells missing -> INCOMPLETE)" >> $J; continue
    fi
    miss=""
    for f in $(tabv $e pull); do                                  # store.sh pull-files: hf_hub_download, retried, no listing
      bash $OPS/store.sh pull-files runs/$run/$f >> $J 2>&1 \
        && { mkdir -p /content/$(dirname $f); [ -e /content/$f ] || cp /content/hfstore/runs/$run/$f /content/$f; } || miss="$miss $f"
    done
    for f in $(tabv $e pull_optional); do                         # mass_arm copies them when present (not needed to train)
      bash $OPS/store.sh pull-files runs/$run/$f >> $J 2>&1 \
        && { mkdir -p /content/$(dirname $f); [ -e /content/$f ] || cp /content/hfstore/runs/$run/$f /content/$f; } \
        || log "mass_check v2 ep$e: optional $f of $run not pulled" >> $J
    done
    R=$(ls /content/refs/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null); got="none"
    [ "$(echo "$R" | grep -c parquet)" = 1 ] && got="$(md5sum $R | cut -c1-32) $(python -c "import sys; sys.path.insert(0, '$T'); import mass_arm, pyarrow.parquet as pq; print(mass_arm.traj_fingerprint(pq.read_table(sys.argv[1])))" $R)"
    want="$(tabv $e glockt_md5) $(tabv $e glockt_fingerprint)"
    echo "ep$e v2 $run missing [${miss# }] reference [$got] table [$want]" >> $MC/stored_refs_v2.txt
    if [ -n "$miss" ] || [ "$got" != "$want" ]; then              # never trained on another file than the PREREG's
      log "mass_check v2 ep$e: REFUSED (pull-files failed for [${miss# }]; reference [$got], table [$want]); episode dropped (its cells missing -> INCOMPLETE; never rebuilt, never swapped)" >> $J
      [ -d /content/refs/glockt/ep$e ] && mv /content/refs/glockt/ep$e /content/refs/glockt/ep$e.refused_$(date +%s)
      continue
    fi
    log "mass_check v2 ep$e: pulled the $(echo $(tabv $e pull) | wc -w) files of $run named in the table (single-file downloads, no store listing); reference md5 + fingerprint = the table's" >> $J
    REUSE="$REUSE $e"
  done
else
for e in $EPS; do
  v=SRC_EP$e; IFS=: read -r run base mode <<< "${!v}"
  if [ "$mode" = reuse ]; then
    pull $run "refs/perc2$base/ep$e refs/sf/ep$e refs/glockt/ep$e" || { log "mass_check ep$e: pull of $run FAILED" >> $J; exit 1; }
    bash $OPS/store.sh pull-files runs/$run/results/glock_public/ep$e/rest_check.json >> $J 2>&1 \
      && mkdir -p /content/results/glock_public/ep$e && cp /content/hfstore/runs/$run/results/glock_public/ep$e/rest_check.json /content/results/glock_public/ep$e/ \
      || { log "mass_check ep$e: rest_check.json of $run missing" >> $J; exit 1; }
    REUSE="$REUSE $e"
  else
    pull $run "refs/perc2$base/ep$e" || { log "mass_check ep$e: pull of $run FAILED" >> $J; exit 1; }
    BUILD="$BUILD $e:local:$base"
  fi
done
fi
# record what was pulled / built (md5 and the reference fingerprint, compared with PREREG section 2 by the agent)
( for e in $EPS; do
    v=SRC_EP$e; IFS=: read -r run base mode <<< "${!v}"
    for f in /content/refs/perc2$base/ep$e/processed/*/*/*.parquet /content/refs/glockt/ep$e/processed/*/*/*.parquet; do
      [ -f $f ] && echo "ep$e $mode $run $(md5sum $f | cut -c1-32) fingerprint $(python -c "import sys; sys.path.insert(0, '$T'); import mass_arm, pyarrow.parquet as pq; print(mass_arm.traj_fingerprint(pq.read_table(sys.argv[1])))" $f) $f"
    done
  done ) > $MC/stored_refs.txt 2>&1

if [ -n "$BUILD" ]; then                                            # grasp-lock reference of ep2, built once (0.3 kg)
  label "mass check: building references$BUILD"
  log "mass_check: building the grasp-lock reference(s) here with the frozen recipe:$BUILD" >> $J
  ( REUSE_REF=0 REF_ONLY=1 SEED=42 PAIRS="${BUILD# }" bash $REPO_DIR/ops/jobs/glock_public.sh ) \
    || log "mass_check: reference build returned $?" >> $J
  ( for x in $BUILD; do e=${x%%:*}; f=$(ls /content/refs/glockt/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1)
      [ -f "$f" ] && echo "ep$e built $(md5sum $f | cut -c1-32) fingerprint $(python -c "import sys; sys.path.insert(0, '$T'); import mass_arm, pyarrow.parquet as pq; print(mass_arm.traj_fingerprint(pq.read_table(sys.argv[1])))" $f) $f"
    done ) >> $MC/stored_refs.txt 2>&1
fi

label "mass check: arm copies"
PAIRS_S=""; MANS=""
for e in $EPS; do
  v=SRC_EP$e; IFS=: read -r run base mode <<< "${!v}"
  python $T/mass_arm.py --ep $e --base $base --arms "mass0:none mass1:$PROPS" --seeds "$SEEDS" --out $MC/arms_ep$e.json > $MC/arms_ep$e.txt 2>&1 \
    || { log "mass_check ep$e: mass_arm FAILED ($(tail -2 $MC/arms_ep$e.txt | tr '\n' ' ' | cut -c1-300)); episode dropped -> verdict INCOMPLETE" >> $J; continue; }
  log "mass_check ep$e: $(tail -1 $MC/arms_ep$e.txt | cut -c1-700)" >> $J
  MANS="$MANS $MC/arms_ep$e.json"; PAIRS_S="$PAIRS_S $e:$base"
done
[ -n "$PAIRS_S" ] || { log "mass_check: no episode has a finished reference" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }

for s in $SEEDS; do                                                 # one invocation per seed: ep2's arms, then ep12's
  P=""; for x in $PAIRS_S; do for a in $ARMS; do P="$P ${x%%:*}:local:${x#*:}:${a}s$s"; done; done
  label "mass check: seed $s [$P ]"
  log "mass_check: seed $s, PAIRS [${P# }]" >> $J
  ( REUSE_REF=1 REQUIRE_REUSE=1 SEED=$s PAIRS="${P# }" bash $REPO_DIR/ops/jobs/glock_public.sh ) || log "mass_check: seed $s returned $?" >> $J
done

label "mass check: verify + verdict"
python $T/mass_verify.py --eps "$EPS" --seeds "$SEEDS" --arms "mass0:none mass1:$PROPS" --steps $STEPS --manifests "${MANS# }" \
  --out $MC/verify.json > $MC/verify.txt 2>&1
log "mass_check verify: $(cut -c1-1200 $MC/verify.txt)" >> $J
if [ -n "${MV2_TAB:-}" ]; then                                    # one box = 2 of the 4 episodes: a reading, not the verdict
  python $T/mass_verdict.py --rule v2 --partial --eps "$EPS" --seeds "$SEEDS" --control mass0 --treatment mass1 --verify $MC/verify.json \
    --manifests "${MANS# }" --out $MC/summary.json > $MC/verdict.txt 2>&1
  log "mass_check v2 BOX RESULT (the verdict merges both boxes on CPU, JOBS.txt): $(cut -c1-1500 $MC/verdict.txt)" >> $J
else
python $T/mass_verdict.py --eps "$EPS" --seeds "$SEEDS" --control mass0 --treatment mass1 --verify $MC/verify.json \
  --manifests "${MANS# }" --out $MC/summary.json > $MC/verdict.txt 2>&1
log "mass_check RESULT: $(cut -c1-1500 $MC/verdict.txt)" >> $J
fi
for c in /content/results/mass*_glock_public/ep*/best/policy.safetensors; do       # stored config of each chosen checkpoint
  /content/v2d/robotic_grounding/flash_chord/.venv/bin/python $T/ckpt_meta.py $c
done > $MC/ckpt_meta.txt 2>&1
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "mass_check: push FAILED (self_destroy retries)" >> $J
