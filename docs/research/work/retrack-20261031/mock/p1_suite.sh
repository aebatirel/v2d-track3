#!/bin/bash
# Phase 1's whole CPU mock suite (leak-decomp-20261030/phase1/mock/run_all.sh: boxes a/b/c, B8 guard, faults,
# Grounding DINO, public data, refusals) run twice from scratch copies of that mock, once on the code BEFORE this
# change (HEAD snapshot) and once AFTER it (working tree), LIB_EP_DIR unset; the outputs (out/*.txt) are diffed after
# blanking UTC timestamps and per-run seconds. The stored 30 Oct outputs in the repo are not touched.
# usage: p1_suite.sh WORK BEFORE_SRC AFTER_SRC OUT
set -u
WK=$1; BEF=$2; AFT=$3; O=$4; P1M=/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/phase1/mock
mkdir -p $O; rc=0
norm() { sed -E -e 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z/[TS]/g' -e 's/(rc=-?[0-9]+) [0-9]+ s:/\1 _ s:/g' \
              -e 's/(rc -?[0-9]+) [0-9]+ s /\1 _ s /g' "$1"; }
for side in before after; do
  src=$BEF; [ $side = after ] && src=$AFT
  C=$WK/p1mock_$side; rm -rf $C; cp -r $P1M $C; rm -rf $C/out/* $C/__pycache__
  sed -i "s#R=/home/user/v2d-track3#R=$src#" $C/setup.sh
  grep -q "R=$src" $C/setup.sh || { echo "p1_suite: could not retarget setup.sh"; exit 1; }
  bash $C/run_all.sh $WK/mr_suite > $C/out/run_all.txt 2>&1
  echo "$side: $(ls $C/out | wc -l) output files"
done
for f in $(ls $WK/p1mock_before/out); do
  if diff <(norm $WK/p1mock_before/out/$f) <(norm $WK/p1mock_after/out/$f) > $O/p1_suite_$f.diff; then
    echo "out/$f: identical"; rm -f $O/p1_suite_$f.diff
  else
    echo "out/$f: DIFFERS ($(wc -l < $O/p1_suite_$f.diff) diff lines)"; rc=1
  fi
done
grep -h 'RESULT\|check rc' $WK/p1mock_after/out/mock_box?.txt | grep -v 'perc_leak RESULT' | sort | uniq -c
echo "p1_suite: $([ $rc = 0 ] && echo 'IDENTICAL (all Phase-1 mock outputs, LIB_EP_DIR unset)' || echo 'DIFFERENCES FOUND')"
exit $rc
