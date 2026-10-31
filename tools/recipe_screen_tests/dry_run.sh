#!/bin/bash
# CPU dry run of ops/jobs/recipe_screen.sh (physics-solver.md section 8): two "boxes" (SEEDS=42 | SEEDS=43, the 2-box
# plan) in scratch roots with training, evaluation, scoring and the store stubbed (tools/recipe_screen_tests/stubs.py:
# FAKE numbers), the real job script, early_stop.sh, recipe_screen.py and patch_flashchord_dr.py (applied to a copy of
# FlashCHORD's lifecycle/reset.py). Injected faults: D/ep24-s43 training crashes after 2 checkpoints (a missing cell),
# K/ep2-s42 best draw r7 hangs (EVAL_TIMEOUT), the ES watcher of C/ep18-s42 hangs (ES_TAIL). Then the merge
# (recipe_screen.py verdict) and the checks (dry_check.py).
# Phase 2 (arm S, physics-solver.md section 9; 2026-10-31): a fake store run 20261030-psolverl-04301a2 with stand-in
# solved references (stubs.py fake_solved: REF with the robot wrist targets shifted, objects unchanged; ep18 = REF byte
# for byte, as G1's), plus decoys the job must not use (G1's ep2/ep12 outputs in refs/psolve, G3's copies in refs/glockt).
# Boxes sboxS42 / sboxS43 (ARMS=S SEEDS=42 | 43, REF_MD5_CHECK=0: the stub files are not the registered ones), sboxSX
# (ARMS=S, REF_MD5_CHECK=1: every S reference must be refused), sboxM (CELLS="C:12:42 S:12:42": both sets in one job).
# Then the merge of A + B + sboxS42 + sboxS43 (with the stub md5s, and with the registered ones) and dry_check_s.py.
# Usage: dry_run.sh DRY_DIR STOCK_FLASHCHORD_DIR JOB_PYTHON FC_VENV_PYTHON REF.parquet [OLD_DRY_DIR]
#   DRY_DIR must not exist; OLD_DRY_DIR: a dry run of the code before arm S (e.g. dry4), for the C/K/D train-command
#   comparison in dry_check_s.py
set -u
DRY=$1; FCSRC=$2; PYV=$3; FCPY=$4; REF=$5; OLD=${6:-}
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
$PYV $HERE/dry_check.py $DRY; rc1=$?

# ---- phase 2: arm S (the same mkbox; S boxes are named sbox* so that dry_check.py's box* globs see phase 1 only)
PSR=$DRY/fakestore/runs/20261030-psolverl-04301a2/refs
hv() { echo processed/sequence_id=t3_ep$(printf %03d $1)/robot_name=sharpa_wave; }
mkps() {  # $1 solve folder, $2 episode, $3 shift (m) of its stand-in solved file
  mkdir -p $1/$(hv $2) $1/reconstructed_stage; echo stub > $1/reconstructed_stage/stage.usda; cp $REF $1/$(hv $2)/ref_in.parquet
  $PYV $HERE/stubs.py fake_solved $REF $1/$(hv $2)/ref_ps.parquet $3; echo '{}' > $1/$(hv $2)/ref_ps_solve.json; echo stub > $1/$(hv $2)/ref_ps_solve.log
}
mkps $PSR/psolve2/ep2 2 0.001; mkps $PSR/psolve2/ep12 12 0.0015; mkps $PSR/psolve/ep18 18 0; mkps $PSR/psolve/ep24 24 0.0005
mkps $PSR/psolve/ep2 2 0.002; mkps $PSR/psolve/ep12 12 0.002                     # decoys: G1's ep2 / ep12 outputs
for e in 2 12 18 24; do                                                           # decoys: G3's training copies (refs/glockt)
  mkdir -p $PSR/glockt/ep$e/$(hv $e) $PSR/glockt/ep$e/reconstructed_stage; echo stub > $PSR/glockt/ep$e/reconstructed_stage/stage.usda
  $PYV $HERE/stubs.py fake_solved $REF $PSR/glockt/ep$e/$(hv $e)/ref_gl_ilc.parquet 0.003
done
$PYV -c 'import hashlib, json, sys
m = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
sub = {2: "psolve2", 12: "psolve2", 18: "psolve", 24: "psolve"}
hv = lambda e: f"processed/sequence_id=t3_ep{e:03d}/robot_name=sharpa_wave"
json.dump(dict(base={str(e): m(sys.argv[1]) for e in sub}, solved={str(e): m(f"{sys.argv[2]}/{sub[e]}/ep{e}/{hv(e)}/ref_ps.parquet") for e in sub}),
          open(sys.argv[3], "w"), indent=1)' $REF $PSR $DRY/stub_ref_md5.json
sbox() {  # $1 box name, $2 seed, $3 REF_MD5_CHECK, $4 the cell selection (ARMS=... or CELLS=...)
  local ROOT=$DRY/sbox$1; mkbox $ROOT
  ( cd $ROOT/v2d-track3 && env CROOT=$ROOT DRY_ROOT=$ROOT PATH=$ROOT/bin:$PATH ES_EVAL=$ROOT/bin/es_eval DRY_CK_SLEEP=${DRY_CK_SLEEP:-12} \
      SLOT_POLL=1 CELL_GAP=1 ZERO=0 PIP=0 EVAL_TIMEOUT=8 ES_TAIL=40 CURVE_TIMEOUT=120 RUN_ID=dry-sbox$1-$2 SEEDS=$2 \
      REF_MD5_CHECK=$3 "$4" FC_DR_RESET=9,9,9 CURR_SCALE=0.4 bash ops/jobs/recipe_screen.sh > $ROOT/stdout.txt 2>&1
    echo "sbox$1 job exit $?" >> $DRY/exits_s.txt )
}
sbox S42 42 0 ARMS=S & sbox S43 43 0 ARMS=S & sbox SX 42 1 ARMS=S & sbox M 42 0 "CELLS=C:12:42 S:12:42" &
wait
cat $DRY/exits_s.txt
A=$DRY/boxA/results/recipe_screen/summary.json; B=$DRY/boxB/results/recipe_screen/summary.json
S2=$DRY/sboxS42/results/recipe_screen/summary.json; S3=$DRY/sboxS43/results/recipe_screen/summary.json
$PYV $REPO/tools/recipe_screen.py verdict $A $B $S2 $S3 --ref-md5 $DRY/stub_ref_md5.json --out $DRY/merged_S.json > $DRY/merged_S.txt 2>&1
echo "merge S (stub md5s) exit $?"
$PYV $REPO/tools/recipe_screen.py verdict $A $B $S2 $S3 --out $DRY/merged_S_registered.json > $DRY/merged_S_registered.txt 2>&1
echo "merge S (registered md5s) exit $?"
$PYV $HERE/dry_check_s.py $DRY $REF $OLD; rc2=$?
exit $(( rc1 || rc2 ))
