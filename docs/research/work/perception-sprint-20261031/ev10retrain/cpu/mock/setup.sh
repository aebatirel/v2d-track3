#!/bin/bash
# CPU mock of ops/jobs/ev10_v4p.sh (2026-10-31), after ep11gate/cpu/mock. A copy of the repo with /content -> $MR/content;
# stub GPU / IK programs (stub.py), a stub `hf` that serves single files from a fake store and refuses listings (hf_stub.py),
# the REAL kit (metric code, reader, roster) and REAL e10v_track.sh / refine.py / nest_physics.py (in the local pinned venvs
# MOCK_VR / MOCK_VP, which the job's `python -m venv` is mapped onto), make_assets.py, pipeline_ep.sh, glock_public.sh,
# ckpt_curve.sh, store.sh, qa.py, no_oracle.py, e10v_score.py, e10v_verify.py, e10v_verdict.py.
# usage: setup.sh MR [REPO_SRC] [STORE_SRC]   (STORE_SRC: copy an existing fake store, e.g. the one a mock run pushed to)
set -e
MR=$1; R=${2:-/home/user/v2d-track3}; SS=${3:-}; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
W=$S/ev10retrain; M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes/carve $MR/content/t3 $MR/store $MR/content/kit
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; cp -r $R/meshes/carve/ev10 $MR/content/v2d-track3/meshes/carve/
GD=docs/research/work/perception-sprint-20261031/ev10retrain; mkdir -p $MR/content/v2d-track3/$GD; cp -r $R/$GD/expect $MR/content/v2d-track3/$GD/
find $MR/content/v2d-track3 \( -name '*.sh' -o -name '*.py' \) -exec sed -i "s#/content#$MR/content#g" {} +
FC=$MR/content/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
mkdir -p $MR/content/rtvenv/bin $MR/content/mpvenv/bin
ln -s $S/map/scoring/kit/v2d_submission_kit $MR/content/kit/v2d_submission_kit
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc; w $MR/content/rtvenv/bin/python rt; w $MR/content/mpvenv/bin/python mp
printf '#!/bin/bash\nexec %s -I %s/hf_stub.py "$@"\n' $PY $M > $MR/bin/hf
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\necho "pip $*" >> %s/pip.log\nexit 0\n' $MR > $MR/bin/pip
cat > $MR/bin/git << GEOF
#!/bin/bash
# git stub: rev-parse -> a fixed sha; worktree add DIR -> an empty pristine tree; status -> clean
echo "git \$*" >> $MR/git.log
for x in "\$@"; do case \$x in rev-parse) echo mocksha0000000; exit 0 ;; worktree) d=\${@: -2:1}; mkdir -p \$d/robotic_grounding/flash_chord; exit 0 ;; status) exit 0 ;; esac; done
exit 0
GEOF
chmod +x $MR/bin/*
ln -s $S/hfds/track_3/public/meta/camera_calibration.json $MR/content/t3/calib.json
if [ -n "$SS" ]; then cp -r $SS/. $MR/store/; else $PY -I $M/make_store.py $MR/store $W/dl $S/e1conf > /dev/null; fi
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_PY=$PY MOCK_STORE=$MR/store MOCK_VR=$S/ep11gate/e11g_venv MOCK_VP=$S/ep11gate/phys_venv MOCK_DEPTH_F0=$W/depthrule/ev10_cache_f0.npy MOCK_PACKED_CK=$MR/store/runs/20261026-gl10A2-5e0e100/results/glock_public/ep10/best/policy.safetensors E10V_SCORE_JOBS=\${E10V_SCORE_JOBS:-2} RUN_ID=\${RUN_ID:-20261031-e10v-mocksha}" > $MR/env.sh
echo "mock at $MR"
