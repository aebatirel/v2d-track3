#!/bin/bash
# CPU mock of ops/jobs/ev20_b1.sh (eval-20 b1 retrain, 2026-11-01). Built like the eval-10 cavity-safe mock
# (eval10-cs4-20261101/cpu/mock/setup.sh, on perception-sprint-20261031/ev10retrain/cpu/mock/setup.sh): a repo copy with
# /content -> MR/content, stub GPU programs (this folder's stub.py: eval10-cs4's stub, unchanged in substance), the eval-10
# mock's stub `hf` (serves single files from a fake store, refuses listings), stub git / curl / pip / nvidia-smi, the REAL kit
# (qa.py's metric, dr_score.py's chain) and REAL make_assets.py, placement_carve.py, glock_public.sh, ckpt_curve.sh, store.sh,
# no_oracle.py, e20b1.py, e10nj.py, dr_score.py. The fake store holds REAL files of the real store (make_store.py): the packed
# run's eval-20 reference, base, sf asset copy (the packed pitcher URDF with the glb + 8 foot STLs, the blue cup with its 0.5 cm
# fill), result files and packed checkpoint; the packed policy's H5p7 eval-20 draws; pack 6's eval-20 rollout.
# Test-only edits (MR/test_edits.json): the packed run's parquets name /content/... asset paths; in the mock they are rewritten
# to MR/content/... (fingerprint unchanged, asserted), so the repo COPY's tools/e20b1.py REF_MD5 and packed_refs.json's eval-20
# md5 are set to the rewritten P's md5. Everything else (piece, URDF, glb, stage and packed-sha256 pins, the gate) is real.
# usage: setup.sh MR [REPO_SRC]
set -e
MR=$1; R=${2:-/home/user/v2d-track3}; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
M=$(cd $(dirname $0) && pwd); PY=$S/map/scoring/venv/bin/python; DL=$S/e20b1/dl
EV=$R/docs/research/work/perception-sprint-20261031/ev10retrain/cpu/mock
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes/carve $MR/store $MR/content/kit $MR/tmp
for d in ops pipeline tools flashchord_conf; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; cp -r $R/meshes/carve/ev20b1 $MR/content/v2d-track3/meshes/carve/
TD=docs/research/work/masses-eval-20261031; mkdir -p $MR/content/v2d-track3/$TD; cp $R/$TD/packed_refs.json $MR/content/v2d-track3/$TD/
find $MR/content/v2d-track3 \( -name '*.sh' -o -name '*.py' \) -exec sed -i "s#/content#$MR/content#g" {} +
FC=$MR/content/v2d/robotic_grounding/flash_chord; mkdir -p $FC/.venv/bin $FC/scripts $FC/src/flash_chord/configs/embodiment
ln -s $S/map/scoring/kit/v2d_submission_kit $MR/content/kit/v2d_submission_kit
w() { printf '#!/bin/bash\nexec %s -I %s/stub.py %s "$@"\n' $PY $M $2 > $1; chmod +x $1; }
w $MR/bin/python main; w $MR/bin/python3 main; w $FC/.venv/bin/python fc
printf '#!/bin/bash\nexec %s -I %s/hf_stub.py "$@"\n' $PY $EV > $MR/bin/hf
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\necho "pip $*" >> %s/pip.log\nexit 0\n' $MR > $MR/bin/pip
printf '#!/bin/bash\necho "41000, 97887, 95"\n' > $MR/bin/nvidia-smi
cat > $MR/bin/git << GEOF
#!/bin/bash
# git stub: rev-parse -> a fixed sha; worktree add DIR -> an empty pristine tree; status -> clean
echo "git \$*" >> $MR/git.log
for x in "\$@"; do case \$x in rev-parse) echo mocksha0000000; exit 0 ;; worktree) d=\${@: -2:1}; mkdir -p \$d/robotic_grounding/flash_chord; exit 0 ;; status) exit 0 ;; esac; done
exit 0
GEOF
chmod +x $MR/bin/*
$PY -I $M/make_store.py $DL $MR $R/$TD/packed_refs.json
$PY -I - $MR << 'PYEOF'
import json, re, sys
MR = sys.argv[1]; e = json.load(open(f'{MR}/store_edits.json')); real, mock = e['P']['md5_real'], e['P']['md5_mock']
R = f'{MR}/content/v2d-track3'; f = f'{R}/tools/e20b1.py'; s = open(f).read(); assert s.count(f"'{real}'") == 1; open(f, 'w').write(s.replace(f"'{real}'", f"'{mock}'"))
t = f'{R}/docs/research/work/masses-eval-20261031/packed_refs.json'; d = json.load(open(t)); assert d['episodes']['20']['md5'] == real
d['episodes']['20']['md5'] = mock; json.dump(d, open(t, 'w'), indent=1)
json.dump(dict(store_parquets_rewritten=[dict(file=x['file'], md5_real=x['md5_real'], md5_mock=x['md5_mock']) for x in e['edits']],
               repo_copy=[dict(file='tools/e20b1.py', what=f'REF_MD5 {real} -> {mock} (the rewritten P)'),
                          dict(file='docs/research/work/masses-eval-20261031/packed_refs.json', what=f'episodes.20.md5 {real} -> {mock}')],
               unchanged='piece set, URDF / glb / stage / packed sha256 pins, the gate bar, the reference fingerprint'), open(f'{MR}/test_edits.json', 'w'), indent=1)
PYEOF
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_PY=$PY MOCK_STORE=$MR/store MOCK_DEPTH_F0=/dev/null MOCK_PACKED_CK=$MR/store/runs/20261025-evb1420-ee7ba8e/results/final_eval/ep20/policy.safetensors E10V_SCORE_JOBS=\${E10V_SCORE_JOBS:-2} TMPDIR=$MR/tmp RUN_ID=\${MOCK_RUN_ID:-20261101-e20b1-mocksha}" > $MR/env.sh
echo "e20b1 mock at $MR"
