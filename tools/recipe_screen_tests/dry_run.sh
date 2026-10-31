#!/bin/bash
# CPU dry run of ops/jobs/recipe_screen.sh (physics-solver.md section 8): two "boxes" (SEEDS=42 | SEEDS=43, the 2-box
# plan) in scratch roots with training, evaluation, scoring and the store stubbed (tools/recipe_screen_tests/stubs.py:
# FAKE numbers), the real job script, early_stop.sh, recipe_screen.py and patch_flashchord_dr.py (applied to a copy of
# FlashCHORD's lifecycle/reset.py). Injected faults: D/ep24-s43 training crashes after 2 checkpoints (a missing cell),
# K/ep2-s42 best draw r7 hangs (EVAL_TIMEOUT), the ES watcher of C/ep18-s42 hangs (ES_TAIL). Then the merge
# (recipe_screen.py verdict) and the checks (dry_check.py).
# Usage: dry_run.sh DRY_DIR STOCK_FLASHCHORD_DIR JOB_PYTHON FC_VENV_PYTHON REF.parquet   (DRY_DIR must not exist)
set -u
DRY=$1; FCSRC=$2; PYV=$3; FCPY=$4; REF=$5
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd $HERE/../.. && pwd)
[ -e "$DRY" ] && { echo "$DRY exists"; exit 1; }
mkdir -p $DRY/fakestore/runs/20261030-physS1-6a814df/refs/glockt
for e in 2 12 18 24; do
  d=$DRY/fakestore/runs/20261030-physS1-6a814df/refs/glockt/ep$e
  mkdir -p $d/processed/sequence_id=t3_ep$(printf %03d $e)/robot_name=sharpa_wave $d/reconstructed_stage
  cp $REF $d/processed/sequence_id=t3_ep$(printf %03d $e)/robot_name=sharpa_wave/ref_gl_ilc.parquet; echo stub > $d/reconstructed_stage/stage.usda
done
wrap() { printf 'import sys\nsys.path.insert(0, "%s")\nimport stubs\nstubs.main("%s")\n' "$HERE" "$2" > "$1"; }
mkbox() {
  local ROOT=$1 F
  F=$ROOT/v2d/robotic_grounding/flash_chord
  mkdir -p $ROOT/v2d-track3/{ops/box,ops/jobs,tools,pipeline,docs/research/physics-2026-10-30,flashchord_conf/embodiment} $ROOT/bin \
           $F/scripts $F/.venv/bin $F/src/flash_chord/lifecycle $F/src/flash_chord/configs/embodiment $ROOT/t3/mesh/blue_cup $ROOT/t3/mesh/wooden_spoon
  cp $REPO/ops/jobs/recipe_screen.sh $ROOT/v2d-track3/ops/jobs/; cp $REPO/ops/box/patch_flashchord_dr.py $ROOT/v2d-track3/ops/box/
  cp $REPO/tools/recipe_screen.py $REPO/tools/early_stop.sh $ROOT/v2d-track3/tools/
  cp $REPO/docs/research/physics-2026-10-30/props_public_scans.json $ROOT/v2d-track3/docs/research/physics-2026-10-30/
  cp $REPO/flashchord_conf/embodiment/sharpa_hands_mid.yaml $ROOT/v2d-track3/flashchord_conf/embodiment/
  cp $FCSRC/src/flash_chord/lifecycle/reset.py $F/src/flash_chord/lifecycle/
  touch $ROOT/t3/mesh/blue_cup/blue_cup.glb $ROOT/t3/mesh/wooden_spoon/wooden_spoon.glb
  { echo "export REPO_DIR=$ROOT/v2d-track3 PYTHONUNBUFFERED=1; OPS=\$REPO_DIR/ops/box"
    echo 'log() { echo "[$(date -u +%FT%TZ)] $*"; }'
    echo "label() { echo \"LABEL \$*\" >> $ROOT/labels.txt; }"
    grep '^FDR_TRAIN_ARGS=' $REPO/ops/box/lib.sh
    echo 'fc_patches() { export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 TRAIN_ARGS="$FDR_TRAIN_ARGS ${TRAIN_ARGS:-}"; echo "STUB fc_patches (FDR + VOC env as lib.sh)" >> $1; }'
  } > $ROOT/v2d-track3/ops/box/lib.sh
  cat > $ROOT/v2d-track3/ops/box/store.sh << EOF
#!/bin/bash
case \$1 in
pull-run) F=$DRY/fakestore/runs/\$2; [ -d \$F ] || { echo "stub: no run \$2"; exit 1; }
  for s in \${PULL_SUB:-.}; do [ -e \$F/\$s ] && { mkdir -p $ROOT/\$(dirname \$s); cp -rn \$F/\$s $ROOT/\$(dirname \$s)/; }; done; echo "stub pulled \$2 [\${PULL_SUB:-}]";;
push-run) echo "stub push-run \$(date -u +%FT%TZ)" >> $ROOT/push.txt;;
esac
EOF
  wrap $ROOT/v2d-track3/pipeline/make_assets.py assets; wrap $ROOT/v2d-track3/pipeline/qa.py qa
  wrap $ROOT/v2d-track3/pipeline/score_registered.py score; wrap $ROOT/v2d-track3/tools/ckpt_curve_summary.py curve_summary
  printf '#!/bin/bash\nexec %s %s/stubs.py curve "$@"\n' "$PYV" "$HERE" > $ROOT/v2d-track3/tools/ckpt_curve.sh
  wrap $F/scripts/train_flash_sac.py train; wrap $F/scripts/evaluate_policy.py evaluate
  printf '#!/bin/bash\nexec %s "$@"\n' "$FCPY" > $F/.venv/bin/python
  printf '#!/bin/bash\nexec %s "$@"\n' "$PYV" > $ROOT/bin/python
  printf '#!/bin/bash\nexec %s %s/stubs.py es_eval "$@"\n' "$PYV" "$HERE" > $ROOT/bin/es_eval
  chmod +x $F/.venv/bin/python $ROOT/bin/python $ROOT/bin/es_eval $ROOT/v2d-track3/tools/ckpt_curve.sh $ROOT/v2d-track3/ops/box/store.sh
}
for b in A:42 B:43; do
  box=${b%%:*}; seed=${b#*:}; ROOT=$DRY/box$box; mkbox $ROOT
  ( cd $ROOT/v2d-track3 && env CROOT=$ROOT DRY_ROOT=$ROOT PATH=$ROOT/bin:$PATH ES_EVAL=$ROOT/bin/es_eval DRY_CK_SLEEP=${DRY_CK_SLEEP:-12} \
      SLOT_POLL=1 CELL_GAP=1 ZERO=0 PIP=0 EVAL_TIMEOUT=8 ES_TAIL=40 CURVE_TIMEOUT=120 RUN_ID=dry-box$box-$seed SEEDS=$seed \
      FC_DR_RESET=9,9,9 CURR_SCALE=0.4 bash ops/jobs/recipe_screen.sh > $ROOT/stdout.txt 2>&1; echo "box $box job exit $?" >> $DRY/exits.txt ) &
done
wait
cat $DRY/exits.txt
$PYV $REPO/tools/recipe_screen.py verdict $DRY/boxA/results/recipe_screen/summary.json $DRY/boxB/results/recipe_screen/summary.json \
  --out $DRY/merged.json > $DRY/merged.txt 2>&1; echo "merge exit $?"
$PYV $HERE/dry_check.py $DRY
