#!/bin/bash
# Re-track CPU mock setup (2026-10-31): Phase 1's mock setup (docs/research/work/leak-decomp-20261030/phase1/mock/
# setup.sh: repo copy with /content -> MR/content, stub hf serving the refine mirror, stub transformers, placeholder
# public files, the real scans) run on the code of SRC instead of the working tree, then optionally the re-track stub
# perc2 (stub_rtk.py: track depends on the template bytes) and stub deliveries copied into the mock repo.
# usage: setup_rtk.sh MR SRC [p1|rtk] [FIXTURES_DIR]
#   SRC        a repo tree (the working tree, or a HEAD snapshot for the before/after comparison)
#   p1|rtk     stub perc2: Phase 1's stub.py (default) or stub_rtk.py
#   FIXTURES   make_fixtures.py output; every sub-folder is copied to MR/content/v2d-track3/meshes/rtk_<name>/
set -e
MR=$1; SRC=$2; KIND=${3:-p1}; FX=${4:-}
M=$(cd "$(dirname "$0")" && pwd); P1M=$SRC/docs/research/work/leak-decomp-20261030/phase1/mock
[ -d $P1M ] || P1M=/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/phase1/mock
PY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python
T=$(mktemp); sed -e "s#R=/home/user/v2d-track3#R=$SRC#" -e "s#MS=\$(cd \"\$(dirname \"\$0\")\" \&\& pwd)#MS=$P1M#" $P1M/setup.sh > $T
grep -q "R=$SRC" $T && grep -q "MS=$P1M" $T || { echo "setup_rtk: could not retarget $P1M/setup.sh"; exit 1; }
bash $T $MR > /dev/null; rm -f $T
if [ $KIND = rtk ]; then
  for b in python python3; do printf '#!/bin/bash\nexec %s -I %s %s "$@"\n' $PY $M/stub_rtk.py main > $MR/bin/$b; chmod +x $MR/bin/$b; done
fi
if [ -n "$FX" ]; then
  for d in $FX/*/; do n=$(basename $d); cp -r $d $MR/content/v2d-track3/meshes/rtk_$n; done
fi
echo "mock at $MR (code from $SRC, stub $KIND${FX:+, fixtures $FX})"
