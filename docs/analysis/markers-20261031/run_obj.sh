#!/bin/bash
# GT-free marker layer for one object over its episodes (after scan.py has run for each (ep, obj)).
# The layout is pooled over the object's episodes in our tracks' own body frame (no cross-episode rotation):
#   pass 1:  census.py --discover (free discovery: clusters seen in >= 2 episodes, marker-like 3-D radius), or for the
#            spoon --seed-template (our template's video-measured layout only labels; the layout is re-measured)
#   guided:  guided.py per episode (second detection pass around predicted markers)
#   pass 2:  census.py --seed <pass-1 layout> on the guided detections -> fix files used by correct.py / apply.py
# (consensus.py, the cross-episode registration variant, was tried and dropped before scoring: spurious 3-point
#  registrations, e.g. a 175 deg flip of pot ep42; see README.)
# Usage: run_obj.sh SPLIT OBJ EPS(comma) [spoon]
set -e
SPLIT=$1; OBJ=$2; EPS=$3; MODE=${4:-free}
D=$(dirname "$0"); S=${MK_SCRATCH:-/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad}
export PYTHONPATH=$S/eg/pylib
OUT=$S/mk/census; mkdir -p $OUT
rm -f $S/mk/scan/fix_${SPLIT}*_${OBJ}.npz $S/mk/scan/${SPLIT}*_${OBJ}_g.json   # no stale fixes
SEED=--discover; [ "$MODE" = spoon ] && SEED=--seed-template
python3 $D/census.py $OBJ $SPLIT $EPS $OUT/${SPLIT}_${OBJ}_p1.json $SEED > $OUT/${SPLIT}_${OBJ}_p1.log
python3 -c "import json,sys; r=json.load(open('$OUT/${SPLIT}_${OBJ}_p1.json')); sys.exit(0 if len(r.get('layout_body_m', []))>=2 else 3)" \
  || { echo "$OBJ: fewer than 2 pooled markers: not eligible"; grep -A30 discovery $OUT/${SPLIT}_${OBJ}_p1.log | head -12; exit 0; }
for e in ${EPS//,/ }; do python3 $D/guided.py $SPLIT $e $OBJ; done
MK_SUFFIX=_g python3 $D/census.py $OBJ $SPLIT $EPS $OUT/${SPLIT}_${OBJ}.json --seed $OUT/${SPLIT}_${OBJ}_p1.json
