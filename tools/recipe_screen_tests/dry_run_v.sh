#!/bin/bash
# CPU dry run for arm V and RESCORE (physics-solver.md section 10, 2026-10-31). Reuses dry_run.sh's mkbox (same stubs,
# FAKE numbers) with a stub store that also serves `pull-files`. Boxes:
#   vC42  ARMS=C SEEDS=42                       (stand-in control, seed 42)
#   vC43  CELLS="C:2:43 C:12:43 C:18:43"        (stand-in control, seed 43, without C/ep24-s43)
#   vV42  ARMS=V SEEDS=42
#   vV43  ARMS=V SEEDS=43 RESCORE="C:24:43:20261031-rscr43-865dfbb"   (the real plan for box 2)
# The fake store holds STORED_CKPT (the REAL stored C/ep24-s43 chosen checkpoint, so ckcfg and the config check run on
# the real file) at the path the job pulls. Then: merge OLD4 (a summary holding only the 4-draw C/ep24-s43 record, first
# in the merge order) + the four boxes with the stub md5s, and dry_check_v.py.
# Usage: dry_run_v.sh DRY_DIR STOCK_FLASHCHORD_DIR JOB_PYTHON FC_VENV_PYTHON REF.parquet STORED_CKPT OLD4.json
set -u
DRY=$1; FCSRC=$2; PYV=$3; FCPY=$4; REF=$5; CK=$6; OLD4=$7
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd $HERE/../.. && pwd)
[ -e "$DRY" ] && { echo "$DRY exists"; exit 1; }
mkdir -p $DRY/fakestore/runs/20261030-physS1-6a814df/refs/glockt
for e in 2 12 18 24; do
  d=$DRY/fakestore/runs/20261030-physS1-6a814df/refs/glockt/ep$e
  mkdir -p $d/processed/sequence_id=t3_ep$(printf %03d $e)/robot_name=sharpa_wave $d/reconstructed_stage
  cp $REF $d/processed/sequence_id=t3_ep$(printf %03d $e)/robot_name=sharpa_wave/ref_gl_ilc.parquet; echo stub > $d/reconstructed_stage/stage.usda
done
f=$DRY/fakestore/runs/20261031-rscr43-865dfbb/results/recipe_screen/C/ep24-s43/best; mkdir -p $f; cp $CK $f/policy.safetensors
eval "$(sed -n '/^wrap() {/p' $HERE/dry_run.sh)"
eval "$(sed -n '/^mkbox() {/,/^}/p' $HERE/dry_run.sh)"
vbox() {  # $1 name, then env assignments for the job
  local n=$1 ROOT=$DRY/vbox$1; shift; mkbox $ROOT
  cat > $ROOT/v2d-track3/ops/box/store.sh << EOS
#!/bin/bash
case \$1 in
pull-run) F=$DRY/fakestore/runs/\$2; [ -d \$F ] || { echo "stub: no run \$2"; exit 1; }
  for s in \${PULL_SUB:-.}; do [ -e \$F/\$s ] && { mkdir -p $ROOT/\$(dirname \$s); cp -rn \$F/\$s $ROOT/\$(dirname \$s)/; }; done; echo "stub pulled \$2 [\${PULL_SUB:-}]";;
pull-files) shift; for x in "\$@"; do [ -s $DRY/fakestore/\$x ] || { echo "stub pull-files: no \$x" >&2; exit 1; }
  mkdir -p $ROOT/hfstore/\$(dirname \$x); cp $DRY/fakestore/\$x $ROOT/hfstore/\$x; echo "pulled \$x"; done;;
push-run) echo "stub push-run \$(date -u +%FT%TZ)" >> $ROOT/push.txt;;
esac
EOS
  ( cd $ROOT/v2d-track3 && env CROOT=$ROOT DRY_ROOT=$ROOT PATH=$ROOT/bin:$PATH ES_EVAL=$ROOT/bin/es_eval DRY_CK_SLEEP=${DRY_CK_SLEEP:-3} \
      SLOT_POLL=1 CELL_GAP=1 ZERO=0 PIP=0 EVAL_TIMEOUT=8 ES_TAIL=40 CURVE_TIMEOUT=120 RUN_ID=dry-vbox$n "$@" \
      bash ops/jobs/recipe_screen.sh > $ROOT/stdout.txt 2>&1; echo "vbox$n job exit $?" >> $DRY/exits.txt )
}
vbox C42 ARMS=C SEEDS=42 & vbox C43 "CELLS=C:2:43 C:12:43 C:18:43" & vbox V42 ARMS=V SEEDS=42 &
vbox V43 ARMS=V SEEDS=43 "RESCORE=C:24:43:20261031-rscr43-865dfbb" &
wait
cat $DRY/exits.txt
$PYV -c 'import hashlib, json, sys
m = hashlib.md5(open(sys.argv[1], "rb").read()).hexdigest()
json.dump(dict(base={str(e): m for e in (2, 12, 18, 24)}, solved={str(e): m for e in (2, 12, 18, 24)}), open(sys.argv[2], "w"))' $REF $DRY/stub_ref_md5.json
$PYV -c 'import json, sys
c = json.load(open(sys.argv[1])); c["ref_md5"] = json.load(open(sys.argv[2]))["base"]["24"]   # the old 4-draw record, stub md5
json.dump(dict(run="old4", steps=70004736, cells={"C/ep24-s43": c}), open(sys.argv[3], "w"))' $OLD4 $DRY/stub_ref_md5.json $DRY/old4_summary.json
B=$DRY/vbox; $PYV $REPO/tools/recipe_screen.py verdict $DRY/old4_summary.json $B''C42/results/recipe_screen/summary.json \
  $B''C43/results/recipe_screen/summary.json $B''V42/results/recipe_screen/summary.json $B''V43/results/recipe_screen/summary.json \
  --ref-md5 $DRY/stub_ref_md5.json --out $DRY/merged_V.json > $DRY/merged_V.txt 2>&1; echo "merge V exit $?"
$PYV $HERE/dry_check_v.py $DRY $CK
