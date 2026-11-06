#!/bin/bash
# All eval-10 cavity-safe retrain mock scenarios (CPU). One check line each into OUT/mock_checks.txt; details OUT/mock_check_<n>.txt.
#   e10v       the DEFAULT path on this build's code: the eval-10 V4p retrain mock 'pass' (its own setup.sh, stub.py and
#              check.py, unchanged) -> SWAP-ELIGIBLE, 28/28 as on 31 Oct; its pushed store is the cs scenarios' e10v run
#   pass5      PIECESET=ev10cs5, MOCK_POLICY=copy (tracks V), 0 overflow lines        -> gate met, SWAP-ELIGIBLE, INCLUDE in pack 10
#   floor4     PIECESET=ev10cs4, MOCK_POLICY=floor (cups left at frame 0)            -> NO-SWAP (training-box gate not met), no draws
#   unclean5   PIECESET=ev10cs5, MOCK_POLICY=copy, 5,000 overflow lines per training -> SWAP-ELIGIBLE [pieces not clean in training]
#   invalid5   PIECESET=ev10cs5, one extra config key in seed 43's training           -> INVALID (cells), no official draw
#   tamper5    PIECESET=ev10cs5 with one blue piece edited in the box's repo copy     -> STOP at the piece check (INVALID), nothing pulled
#   badset     PIECESET=ev10cs6                                                       -> refused at the start (exit 1), nothing run
# usage: run_all.sh [scenario ...]   (default: all; the e10v scenario must exist before the others)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/e10cs/mock; M=$(cd $(dirname $0) && pwd)
R=$(cd $M/../../../../../.. && pwd); EV=$R/docs/research/work/perception-sprint-20261031/ev10retrain/cpu/mock; O=$M/../out
PY=$S/map/scoring/venv/bin/python; mkdir -p $W $O
run() {  # $1 name, $2 expect, $3 piece set, then env assignments
  local n=$1 e=$2 ps=$3; shift 3
  bash $M/setup.sh $W/$n $W/e10v $R > /dev/null
  [ $n = tamper5 ] && echo '# edited' >> $W/$n/content/v2d-track3/meshes/carve/ev10cs5/blue_cup/piece_03.obj
  ( cd /tmp && env "$@" nice -n 5 bash $EV/run_mock.sh $W/$n "PIECESET=$ps bash ops/jobs/ev10_cs.sh" )
  ovf=$(echo "$@" | grep -o 'MOCK_OVF_512=[0-9]*' | cut -d= -f2)
  (cd /tmp && $PY -I $M/check.py $W/$n "$e" $ps ${ovf:+--ovf $ovf}) > $O/mock_check_$n.txt 2>&1
  echo "$n (expect $e, $ps): $(tail -1 $O/mock_check_$n.txt)" >> $O/mock_checks.txt
  mkdir -p $O/mock_$n; for f in summary.json verdict.txt verify.txt pieces.txt assets.txt arms.txt cells.txt choice.txt gate.txt overflow.txt \
      lift_s42.txt lift_s43.txt score.txt STOPPED; do
    [ -f $W/$n/content/results/ev10_cs/$f ] && cp $W/$n/content/results/ev10_cs/$f $O/mock_$n/; done
  grep -a "ev10_cs\|TRAIN_ARGS" $W/$n/content/job.log | cut -c1-900 > $O/mock_$n/job_ev10_cs_lines.txt
  cp $W/$n/test_edits.json $O/mock_$n/ 2> /dev/null
  sed -i "s#$W/$n#<MR>#g; s#$W/e10v#<E10V_MR>#g; s#$S#<S>#g" $O/mock_$n/* 2> /dev/null
}
for sc in ${@:-e10v pass5 floor4 unclean5 invalid5 tamper5 badset}; do
  case $sc in
    e10v) rm -rf $W/e10v; bash $EV/setup.sh $W/e10v $R > /dev/null
          ( cd /tmp && MOCK_POLICY=copy nice -n 5 bash $EV/run_mock.sh $W/e10v 'bash ops/jobs/ev10_v4p.sh' )
          (cd /tmp && $PY -I $EV/check.py $W/e10v SWAP-ELIGIBLE) > $O/mock_check_e10v.txt 2>&1
          echo "e10v default path (expect SWAP-ELIGIBLE, 28 checks): $(tail -1 $O/mock_check_e10v.txt)" >> $O/mock_checks.txt ;;
    pass5) run pass5 "SWAP-ELIGIBLE:INCLUDE" ev10cs5 MOCK_POLICY=copy MOCK_OVF_512=0 ;;
    floor4) run floor4 "NO-SWAP:GATE" ev10cs4 MOCK_POLICY=floor MOCK_OVF_512=0 ;;
    unclean5) run unclean5 "SWAP-ELIGIBLE:UNCLEAN" ev10cs5 MOCK_POLICY=copy MOCK_OVF_512=5000 ;;
    invalid5) run invalid5 "INVALID:CELLS" ev10cs5 MOCK_POLICY=copy MOCK_OVF_512=0 MOCK_CFG_EXTRA='perc2e10css43_glock/' ;;
    tamper5) run tamper5 "INVALID:piece set check FAILED" ev10cs5 MOCK_POLICY=copy ;;
    badset) run badset "REFUSED" ev10cs6 MOCK_POLICY=copy ;;
  esac
done
cat $O/mock_checks.txt
