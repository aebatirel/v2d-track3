#!/bin/bash
# CPU mock of ops/jobs/perc_leak.sh (2026-10-30), after docs/research/work/oracle-twins-20261030/cpu/mock: a copy of the
# repo with /content -> $MR/content, a stub perc2 (stub.py) and a stub `hf` (hf_stub.py) that serves the store from
# the local refine mirror; everything else is the real code (lib.sh, store.sh push-run / pull-files, tools/leak_p1.py,
# tools/no_oracle.py). The depth caches are served as sparse files of the store's size whose frame 0 is the store
# frame 0 (refine/in/ep<N>/depth0.npy). usage: setup.sh MR
set -e
MR=$1; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; R=/home/user/v2d-track3
MS=$(cd "$(dirname "$0")" && pwd); PY=$S/map/scoring/venv/bin/python; P1=docs/research/work/leak-decomp-20261030/phase1
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes $MR/content/v2d-track3/$P1 $MR/content/t3
for d in ops pipeline tools; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; cp $R/$P1/inputs.tsv $MR/content/v2d-track3/$P1/
find $MR/content/v2d-track3 -name '*.sh' -o -name '*.py' | xargs sed -i "s#/content#$MR/content#g"
ln -s $S/hfds/track_3/public/mesh $MR/content/t3/mesh
w() { printf '#!/bin/bash\nexec %s -I %s %s "$@"\n' $PY "$2" "$3" > $1; chmod +x $1; }
w $MR/bin/python $MS/stub.py main; w $MR/bin/python3 $MS/stub.py main; w $MR/bin/hf $MS/hf_stub.py ''
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\nexit 0\n' > $MR/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $MR/bin/git
printf '#!/bin/bash\necho "MOCK GPU (CPU mock)"\n' > $MR/bin/nvidia-smi
chmod +x $MR/bin/*
echo "export PATH=$MR/bin:\$PATH HF_STORE=mock/store MOCK_MR=$MR MOCK_IN=$S/refine/in MOCK_PY=$PY PULL_RETRY_S=1" > $MR/env.sh
echo "mock at $MR"
