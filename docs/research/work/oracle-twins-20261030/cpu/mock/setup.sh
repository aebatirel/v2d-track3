#!/bin/bash
# CPU mock of ops/jobs/oracle_twins.sh: a copy of the repo with /content -> $MR/content, stub GPU programs
# (perception, hands, mkref stage (a) emulation, contact retargeting, grasp lock, training, evaluation, qa, rollout
# scoring) and the REAL oracle_poses.py / ref_vs_mocap.py / score_registered.py (npz) on local public inputs.
# usage: setup.sh MR
set -e
MR=$1; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; R=/home/user/v2d-track3
MS=$S/oracle/mock_scripts; PY=$S/map/scoring/venv/bin/python
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $R/meshes/carve $MR/content/v2d-track3/meshes/
find $MR/content/v2d-track3 -name '*.sh' -o -name '*.py' | xargs sed -i "s#/content#$MR/content#g"
mkdir -p $MR/content/t3 $MR/content/kit
for f in $S/map/scoring/t3/ep*.parquet; do ln -s $f $MR/content/t3/; done
ln -s $S/map/scoring/t3/mesh $MR/content/t3/mesh; ln -s $S/hfds/track_3/public/meta/camera_calibration.json $MR/content/t3/calib.json
ln -s $S/map/scoring/kit/v2d_submission_kit $MR/content/kit/v2d_submission_kit
FC=$MR/content/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
mkdir -p $MR/content/mpvenv/bin $MR/content/rtvenv/bin
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $MS $2 > $1; chmod +x $1; }
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc; w $MR/content/mpvenv/bin/python mp; w $MR/content/rtvenv/bin/python rt
printf '#!/bin/bash\necho "hf $*" >> %s/hf.log\nexit 0\n' $MR > $MR/bin/hf
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\nexit 0\n' > $MR/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $MR/bin/git
chmod +x $MR/bin/*
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_IN=$S/refine/in MOCK_PY=$PY RENDER=0" > $MR/env.sh
echo "mock at $MR"
