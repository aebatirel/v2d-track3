#!/bin/bash
# All eval-20 b1 retrain mock scenarios (CPU). One check line each into OUT/mock_checks.txt; details OUT/mock_check_<n>.txt.
#   pass      MOCK_POLICY=copy (tracks P), 0 overflow lines                     -> gate met, SWAP-ELIGIBLE, INCLUDE in pack 10
#   floor     MOCK_POLICY=floor (objects left at frame 0)                        -> NO-SWAP (training-box gate not met), no draws
#   unclean   MOCK_POLICY=copy, 5,000 overflow lines per training                 -> SWAP-ELIGIBLE [pieces not clean in training]
#   invalid   MOCK_POLICY=copy, one extra config key in seed 43's training        -> INVALID (cells), no official draw
#   tamper    one pitcher piece edited in the box's repo copy                     -> STOP at the piece check (INVALID), nothing pulled
#   badrun    RUN_ID without -e20b1-                                              -> refused at the start (exit 1), nothing run
# The packed side (K, old) is the REAL H5p7 / pack 6 files in every scenario; the new side is synthetic (mock numbers are NOT
# evidence about the b1 pieces). usage: run_all.sh [scenario ...]   (default: all)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/e20b1/mock; M=$(cd $(dirname $0) && pwd)
R=$(cd $M/../../../../../.. && pwd); EV=$R/docs/research/work/perception-sprint-20261031/ev10retrain/cpu/mock; O=$M/../out
PY=$S/map/scoring/venv/bin/python; mkdir -p $W $O
run() {  # $1 name, $2 expect, then env assignments
  local n=$1 e=$2; shift 2
  bash $M/setup.sh $W/$n $R > /dev/null
  [ $n = tamper ] && echo '# edited' >> $W/$n/content/v2d-track3/meshes/carve/ev20b1/water_pitcher/piece_07.obj
  ( cd /tmp && env "$@" nice -n 5 bash $EV/run_mock.sh $W/$n "bash ops/jobs/ev20_b1.sh" )
  ovf=$(echo "$@" | grep -o 'MOCK_OVF_512=[0-9]*' | cut -d= -f2)
  (cd /tmp && env "$@" $PY -I $M/check.py $W/$n "$e" ${ovf:+--ovf $ovf}) > $O/mock_check_$n.txt 2>&1
  echo "$n (expect $e): $(tail -1 $O/mock_check_$n.txt)" >> $O/mock_checks.txt
  mkdir -p $O/mock_$n; for f in summary.json verdict.txt verify.txt pieces.txt inputs.txt assets.txt carve.txt arms.txt cells.txt choice.txt gate.txt \
      overflow.txt score.txt rest_check_b1.json STOPPED; do
    [ -f $W/$n/content/results/ev20_b1/$f ] && cp $W/$n/content/results/ev20_b1/$f $O/mock_$n/; done
  grep -a "ev20_b1\|TRAIN_ARGS\|glock_public code" $W/$n/content/job.log | cut -c1-900 > $O/mock_$n/job_ev20_b1_lines.txt
  cp $W/$n/test_edits.json $O/mock_$n/ 2> /dev/null
  sed -i "s#$W/$n#<MR>#g; s#$S#<S>#g" $O/mock_$n/* 2> /dev/null
}
for sc in ${@:-pass floor unclean invalid tamper badrun}; do
  case $sc in
    pass) run pass "SWAP-ELIGIBLE:INCLUDE" MOCK_POLICY=copy MOCK_OVF_512=0 ;;
    floor) run floor "NO-SWAP:GATE" MOCK_POLICY=floor MOCK_OVF_512=0 ;;
    unclean) run unclean "SWAP-ELIGIBLE:UNCLEAN" MOCK_POLICY=copy MOCK_OVF_512=5000 ;;
    invalid) run invalid "INVALID:CELLS" MOCK_POLICY=copy MOCK_OVF_512=0 MOCK_CFG_EXTRA='e20b1s43_glock/' ;;
    tamper) run tamper "INVALID:piece set check FAILED" MOCK_POLICY=copy ;;
    badrun) run badrun "REFUSED" MOCK_POLICY=copy MOCK_RUN_ID=20261101-e20x-mocksha ;;
  esac
done
cat $O/mock_checks.txt
