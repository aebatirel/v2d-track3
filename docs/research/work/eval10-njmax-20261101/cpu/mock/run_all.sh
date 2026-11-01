#!/bin/bash
# All eval-10 njmax diagnostic mock scenarios (CPU). One check line each into OUT/mock_checks.txt; details OUT/mock_check_<n>.txt.
#   e10v          the DEFAULT path on this build's code: the eval-10 V4p retrain mock 'pass' (its own setup.sh, stub.py and
#                 check.py, unchanged) -> SWAP-ELIGIBLE, 28/28 as on 31 Oct; its pushed store is the nj scenarios' e10v run
#   supported     MOCK_POLICY=copy (the policy tracks V), MOCK_POLICY_512=floor, 40 overflow lines at 1024   -> SUPPORTED
#   falsified     MOCK_POLICY=floor (cups left at frame 0), 0 overflow lines                                 -> FALSIFIED
#   inconclusive  MOCK_POLICY=copy, 5,000 overflow lines at 1024                                             -> INCONCLUSIVE
#   partial       MOCK_POLICY=lift (beige lifted 8 cm at f30-60, put back; otherwise frame 0)              -> PARTIAL
#   invalid       one extra config key in the 1024 training                     -> STOP at identity, INVALID, no official draw
# usage: run_all.sh [scenario ...]   (default: all; the e10v scenario must exist before the others)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/nj/mock; M=$(cd $(dirname $0) && pwd)
R=$(cd $M/../../../../../.. && pwd); EV=$R/docs/research/work/perception-sprint-20261031/ev10retrain/cpu/mock; O=$M/../out
PY=$S/map/scoring/venv/bin/python; mkdir -p $W $O
run() {  # $1 name, $2 expect, then env assignments
  local n=$1 e=$2; shift 2
  bash $M/setup.sh $W/$n $W/e10v $R > /dev/null
  ( cd /tmp && env "$@" nice -n 5 bash $EV/run_mock.sh $W/$n 'bash ops/jobs/ev10_nj.sh' )
  ovf=$(echo "$@" | grep -o 'MOCK_OVF_1024=[0-9]*' | cut -d= -f2)
  (cd /tmp && $PY -I $M/check.py $W/$n "$e" ${ovf:+--ovf $ovf}) > $O/mock_check_$n.txt 2>&1
  echo "$n (expect $e): $(tail -1 $O/mock_check_$n.txt)" >> $O/mock_checks.txt
  mkdir -p $O/mock_$n; for f in summary.json verdict.txt overflow.txt lift.txt identity.txt ck512.txt solver_check.txt solver_build.txt guard.txt arms.txt score.txt STOPPED; do
    [ -f $W/$n/content/results/ev10_nj/$f ] && cp $W/$n/content/results/ev10_nj/$f $O/mock_$n/; done
  grep -a "ev10_nj\|TRAIN_ARGS" $W/$n/content/job.log | cut -c1-900 > $O/mock_$n/job_ev10_nj_lines.txt
  sed -i "s#$W/$n#<MR>#g; s#$W/e10v#<E10V_MR>#g; s#$S#<S>#g" $O/mock_$n/* 2> /dev/null
}
for sc in ${@:-e10v supported falsified inconclusive partial invalid}; do
  case $sc in
    e10v) rm -rf $W/e10v; bash $EV/setup.sh $W/e10v $R > /dev/null
          ( cd /tmp && MOCK_POLICY=copy nice -n 5 bash $EV/run_mock.sh $W/e10v 'bash ops/jobs/ev10_v4p.sh' )
          (cd /tmp && $PY -I $EV/check.py $W/e10v SWAP-ELIGIBLE) > $O/mock_check_e10v.txt 2>&1
          echo "e10v default path (expect SWAP-ELIGIBLE, 28 checks): $(tail -1 $O/mock_check_e10v.txt)" >> $O/mock_checks.txt ;;
    supported) run supported SUPPORTED MOCK_POLICY=copy MOCK_POLICY_512=floor MOCK_OVF_1024=40 ;;
    falsified) run falsified FALSIFIED MOCK_POLICY=floor MOCK_OVF_1024=0 ;;
    inconclusive) run inconclusive INCONCLUSIVE MOCK_POLICY=copy MOCK_OVF_1024=5000 ;;
    partial) run partial PARTIAL MOCK_POLICY=lift MOCK_OVF_1024=40 ;;
    invalid) run invalid "INVALID:identity FAILED" MOCK_POLICY=copy MOCK_OVF_1024=40 MOCK_CFG_EXTRA='perc2e10njs43_glock/' ;;
  esac
done
cat $O/mock_checks.txt
