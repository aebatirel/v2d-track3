#!/bin/bash
# T3 build: frozen fit settings (cfg_frozen.json) on all 10 picks, sequentially, one process. GT-free (fit.py reads
# only the placed generated mesh and our observed points). A finished object (fit.glb present) is skipped.
# Usage: bash run_fits.sh CFG.json OUTROOT [obj1,obj2,...]   (default: all 10)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
T=/home/user/v2d-track3/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts
CFG=$1; OUT=$2; ONLY=${3:-}
mkdir -p $OUT
$S/venv/bin/python -I $T/picks.py > $OUT/picks${ONLY:+_$$}.jsonl
PK=$OUT/picks${ONLY:+_$$}.jsonl
while read -r line; do
  o=$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin)['object'])")
  m=$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin)['placed'])")
  b=$(echo "$line" | python3 -c "import sys,json;print(json.load(sys.stdin)['obs'])")
  [ -n "$ONLY" ] && [[ ",$ONLY," != *",$o,"* ]] && continue
  [ -s $OUT/$o/fit.glb ] && { echo "$(date -u +%FT%TZ) skip $o"; continue; }
  echo "$(date -u +%FT%TZ) start $o"
  nice -n 5 $S/venv/bin/python -I $T/fit.py --mesh $m --obs $b --out $OUT/$o --cfg $CFG > $OUT/$o.out 2>&1 \
    && echo "$(date -u +%FT%TZ) OK $o" || echo "$(date -u +%FT%TZ) FAIL $o"
done < $PK
echo "$(date -u +%FT%TZ) all done"
