#!/bin/bash
# CPU mock of ops/jobs/ev10_nj.sh (eval-10 njmax diagnostic, 2026-11-01). Built on the eval-10 V4p retrain mock
# (perception-sprint-20261031/ev10retrain/cpu/mock/setup.sh: a repo copy with /content -> MR/content, stub GPU / IK
# programs, a stub `hf` that serves single files from a fake store and refuses listings, the REAL kit, ...), with this
# folder's stub.py, a stub nvidia-smi, and a fake store taken from an e10v mock run at E10V_MR: that run is renamed to
# 20261031-e10v-caf38fb (the run ev10_nj.sh reads) and given e10v's REAL curve.json files of both seeds (cpu/out/control;
# pulled from the store 1 Nov) as the lift control. The stored e10v files keep naming E10V_MR (as a real re-run box reads
# a reference whose paths name the first box's /content), so E10V_MR must stay on disk.
# usage: setup.sh MR E10V_MR [REPO_SRC]
set -e
MR=$1; EM=$2; R=${3:-/home/user/v2d-track3/.claude/worktrees/agent-ac592c6308cf07a10}
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
EV=$R/docs/research/work/perception-sprint-20261031/ev10retrain/cpu/mock; M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python
bash $EV/setup.sh $MR $R $EM/store > /dev/null
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
FC=$MR/content/v2d/robotic_grounding/flash_chord
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc; w $MR/content/rtvenv/bin/python rt; w $MR/content/mpvenv/bin/python mp
printf '#!/bin/bash\necho "41000, 97887, 95"\n' > $MR/bin/nvidia-smi; chmod +x $MR/bin/nvidia-smi
ST=$MR/store/runs; rm -rf $ST/20261031-e10v-caf38fb; mv $ST/20261031-e10v-mocksha $ST/20261031-e10v-caf38fb
for s in 42 43; do
  d=$ST/20261031-e10v-caf38fb/results/perc2e10vs${s}_glock_public/ep10/curve; mkdir -p $d
  cp $R/docs/research/work/eval10-njmax-20261101/cpu/out/control/e10v_s${s}_curve.json $d/curve.json
done
mkdir -p $MR/tmp
echo "export MOCK_FCPY=$S/carve/fcvenv/bin/python MOCK_FC_PYTHONPATH=$S/nj/fcextra TMPDIR=$MR/tmp RUN_ID=\${MOCK_RUN_ID:-20261101-e10nj-mocksha}" >> $MR/env.sh
echo "nj mock at $MR (store from $EM)"
