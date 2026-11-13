#!/bin/bash
# CPU mock of ops/jobs/ep11_gate.sh (2026-10-31), after masses-transfer-20261031/cpu/mock and leak-decomp phase1/mock.
# A copy of the repo with /content -> $MR/content; stub GPU / IK programs (stub.py), a stub `hf` that serves single files
# from a fake store and refuses listings (hf_stub.py), and REAL e11g_tracks.sh / refine.py / nest_physics.py (in the
# local pinned venvs MOCK_VR / MOCK_VP, which the job's `python -m venv` is mapped onto), make_assets.py, pipeline_ep.sh,
# glock_public.sh, ckpt_curve.sh, store.sh, e11g_verify.py and e11g_verdict.py.
# Fake store ($MR/store unless STORE is given): the five input files from single-file downloads of the real store
# (DL = scratchpad ep11gate/dl), served under their store paths; the depth cache is synthesised by hf_stub.py.
# usage: setup.sh MR [REPO_SRC] [STORE_SRC]   (STORE_SRC: copy an existing fake store, e.g. the one a mock run pushed to)
set -e
MR=$1; R=${2:-/home/user/v2d-track3}; SS=${3:-}; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/ep11gate; M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python; DL=$W/dl
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes $MR/content/t3 $MR/store
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; mkdir -p $MR/content/v2d-track3/meshes/carve
cp -r $R/meshes/carve/ev10 $MR/content/v2d-track3/meshes/carve/
GD=docs/research/work/perception-sprint-20261031/ep11gate; mkdir -p $MR/content/v2d-track3/$GD; cp -r $R/$GD/expect $MR/content/v2d-track3/$GD/
find $MR/content/v2d-track3 \( -name '*.sh' -o -name '*.py' \) -exec sed -i "s#/content#$MR/content#g" {} +
FC=$MR/content/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
mkdir -p $MR/content/rtvenv/bin $MR/content/mpvenv/bin
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc; w $MR/content/rtvenv/bin/python rt; w $MR/content/mpvenv/bin/python mp
printf '#!/bin/bash\nexec %s -I %s/hf_stub.py "$@"\n' $PY $M > $MR/bin/hf
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\necho "pip $*" >> %s/pip.log\nexit 0\n' $MR > $MR/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $MR/bin/git
chmod +x $MR/bin/*
ln -s $S/map/scoring/t3/ep11.parquet $MR/content/t3/ep11.parquet
ln -s $S/hfds/track_3/public/meta/camera_calibration.json $MR/content/t3/calib.json
if [ -n "$SS" ]; then cp -r $SS/. $MR/store/; else
  for f in runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/perc2/poses.npz runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/perc2/poses_world_vo.npz \
           runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/depth0.npy runs/20261025-g1-022fece/refs/perc2m/ep11/hands_refined.npz \
           runs/20261025-g1-022fece/refs/perc2m/ep11/hands.npz; do mkdir -p $MR/store/$(dirname $f); cp $DL/$f $MR/store/$f; done
fi
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_PY=$PY MOCK_STORE=$MR/store MOCK_VR=$W/e11g_venv MOCK_VP=$W/phys_venv RUN_ID=\${RUN_ID:-20261031-e11g-mocksha}" > $MR/env.sh
echo "mock at $MR"
