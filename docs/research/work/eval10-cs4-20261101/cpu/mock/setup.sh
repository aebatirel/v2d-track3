#!/bin/bash
# CPU mock of ops/jobs/ev10_cs.sh (eval-10 cavity-safe retrain, 2026-11-01). Built like the njmax diagnostic's mock
# (eval10-njmax-20261101/cpu/mock/setup.sh) on the eval-10 V4p retrain mock (perception-sprint-20261031/ev10retrain/cpu/mock/
# setup.sh: a repo copy with /content -> MR/content, stub GPU / IK programs, a stub `hf` that serves single files from a fake
# store and refuses listings, the REAL kit), with this folder's stub.py and a fake store taken from an e10v mock run at
# E10V_MR (the default-path scenario of run_all.sh, on this build's code): that run is renamed to 20261031-e10v-caf38fb (the
# run ev10_cs.sh reads) and given e10v's REAL curve.json files of both seeds (eval10-njmax-20261101/cpu/out/control) as the
# lift control. The repo copy also holds meshes/carve/ev10cs4 and ev10cs5 (REAL make_assets.py builds the assets from them).
# fix_store.py then makes the mock faithful to a real box on two points (test-only edits, listed in MR/test_edits.json):
#   - e10v's stored V names e10v's box assets, /content/assets/urdf/*: on a real box that is this box's /content/assets (the
#     same path); in the mock the e10v run's content root differs, so V's two asset-path columns are rewritten to this mock's
#     root (trajectory fingerprint unchanged: it excludes those columns) and e10v's arms.json gets the new md5;
#   - tools/e10cs.py pins the REAL V md5 / fingerprint / base md5; the mock's V is a mock reference, so the repo COPY's three
#     constants are set to the mock V's values. Everything else (the piece-set and URDF pins, the packed sha256) is real.
# usage: setup.sh MR E10V_MR [REPO_SRC]
set -e
MR=$1; EM=$2; R=${3:-/home/user/v2d-track3/.claude/worktrees/agent-a85860be5329e0f22}
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
EV=$R/docs/research/work/perception-sprint-20261031/ev10retrain/cpu/mock; M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python
bash $EV/setup.sh $MR $R $EM/store > /dev/null
cp -r $R/meshes/carve/ev10cs4 $R/meshes/carve/ev10cs5 $MR/content/v2d-track3/meshes/carve/
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
FC=$MR/content/v2d/robotic_grounding/flash_chord
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc; w $MR/content/rtvenv/bin/python rt; w $MR/content/mpvenv/bin/python mp
printf '#!/bin/bash\necho "41000, 97887, 95"\n' > $MR/bin/nvidia-smi; chmod +x $MR/bin/nvidia-smi
ST=$MR/store/runs; rm -rf $ST/20261031-e10v-caf38fb; mv $ST/20261031-e10v-mocksha $ST/20261031-e10v-caf38fb
for s in 42 43; do
  d=$ST/20261031-e10v-caf38fb/results/perc2e10vs${s}_glock_public/ep10/curve; mkdir -p $d
  cp $R/docs/research/work/eval10-njmax-20261101/cpu/out/control/e10v_s${s}_curve.json $d/curve.json
done
$PY -I $M/fix_store.py $MR $EM
mkdir -p $MR/tmp
echo "export TMPDIR=$MR/tmp RUN_ID=\${MOCK_RUN_ID:-20261101-e10cs-mocksha}" >> $MR/env.sh
echo "cs mock at $MR (store from $EM)"
