#!/bin/bash
# CPU mock of ops/jobs/perc_leak.sh (2026-10-30), after docs/research/work/oracle-twins-20261030/cpu/mock: a copy of the
# repo with /content -> $MR/content, a stub perc2 (stub.py) and a stub `hf` (hf_stub.py) that serves the store from
# the local refine mirror; everything else is the real code (lib.sh, store.sh push-run / pull-files, tools/leak_p1.py,
# tools/no_oracle.py). The depth caches are served as sparse files of the store's size whose frame 0 is the store
# frame 0 (refine/in/ep<N>/depth0.npy). /content/t3 holds placeholder public files and the real scans (symlink).
# usage: setup.sh MR
set -e
MR=$1; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; R=/home/user/v2d-track3
MS=$(cd "$(dirname "$0")" && pwd); PY=$S/map/scoring/venv/bin/python; P1=docs/research/work/leak-decomp-20261030/phase1
rm -rf "${MR:?}"; mkdir -p $MR/bin $MR/content/v2d-track3/meshes $MR/content/v2d-track3/$P1 $MR/content/t3
for d in ops pipeline tools; do cp -r $R/$d $MR/content/v2d-track3/; done
cp -r $R/meshes/library_v3 $MR/content/v2d-track3/meshes/; cp $R/$P1/inputs.tsv $MR/content/v2d-track3/$P1/
find $MR/content/v2d-track3 -name '*.sh' -o -name '*.py' | xargs sed -i "s#/content#$MR/content#g"
ln -s $S/hfds/track_3/public/mesh $MR/content/t3/mesh
# the public files perc_leak.sh checks before any download (mechanics review F2): placeholders, the stub perc2 reads none
mkdir -p $MR/content/t3/v; echo '{}' > $MR/content/t3/calib.json
for e in $(awk -F'\t' 'NR > 1 {print $1}' $R/$P1/inputs.tsv); do
  echo x > $MR/content/t3/ep$e.parquet; for c in a b c; do echo x > $MR/content/t3/v/ep${e}_$c.mp4; done
done
# a stub `transformers` (on PYTHONPATH for every non-isolated python): from_pretrained logs each call with the
# HF_HUB_OFFLINE it saw to MR/gdino_tries.txt and marks MR/gdino_cached on success; MOCK_GDINO_FAIL1=1 fails the
# first call, MOCK_GDINO_FAILALL=1 every call (as under HF 429). The stub perc2 has no grounding unless it is cached.
mkdir -p $MR/fakepy/transformers
cat > $MR/fakepy/transformers/__init__.py <<'PY'
import os
class _L:
    @staticmethod
    def from_pretrained(g):
        mr = os.environ['MOCK_MR']; m = f'{mr}/gdino_tries.txt'
        n = (len(open(m).read().splitlines()) if os.path.exists(m) else 0) + 1
        fail = os.environ.get('MOCK_GDINO_FAILALL') == '1' or (os.environ.get('MOCK_GDINO_FAIL1') == '1' and n == 1)
        open(m, 'a').write(f'{n} {g} offline={os.environ.get("HF_HUB_OFFLINE")} {"429" if fail else "ok"}\n')
        if fail:
            raise OSError('429 Client Error: Too Many Requests (mock)')
        open(f'{mr}/gdino_cached', 'w').write(g)
        return object()
AutoProcessor = AutoModelForZeroShotObjectDetection = _L
PY
w() { printf '#!/bin/bash\nexec %s -I %s %s "$@"\n' $PY "$2" "$3" > $1; chmod +x $1; }
w $MR/bin/python $MS/stub.py main; w $MR/bin/python3 $MS/stub.py main; w $MR/bin/hf $MS/hf_stub.py ''
printf '#!/bin/bash\necho "{}"\n' > $MR/bin/curl
printf '#!/bin/bash\nexit 0\n' > $MR/bin/pip
printf '#!/bin/bash\necho mocksha0000000\n' > $MR/bin/git
printf '#!/bin/bash\necho "MOCK GPU (CPU mock)"\n' > $MR/bin/nvidia-smi
chmod +x $MR/bin/*
echo "export PATH=$MR/bin:\$PATH PYTHONPATH=$MR/fakepy HF_STORE=mock/store MOCK_MR=$MR MOCK_IN=$S/refine/in MOCK_PY=$PY PULL_RETRY_S=1" > $MR/env.sh
echo "mock at $MR"
