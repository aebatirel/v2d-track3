#!/bin/bash
# check.py on every scenario of run_all.sh; one summary line each into OUT/mock_checks.txt, details OUT/mock_check_<n>.txt,
# and each verdict scenario's own outputs (summary.json, verify.json, verdict / verify / b0 / choice / identity / score text) under OUT/mock_<n>/.
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/ev10retrain/mock; M=$(cd $(dirname $0) && pwd)
O=$M/../out; PY=$S/map/scoring/venv/bin/python; : > $O/mock_checks.txt
for x in pass:SWAP-ELIGIBLE noswap:NO-SWAP invalid:INVALID incomplete:INCOMPLETE rerun:SWAP-ELIGIBLE topup:SWAP-ELIGIBLE b0stop:"STOP:B0 MISMATCH" badinput:STOP:md5; do
  n=${x%%:*}; e=${x#*:}; extra=""; rid=20261031-e10v-mocksha
  [ -d $W/$n ] || continue
  [ $n = rerun ] && { rid=20261031-e10v-mockrr; extra="--rerun 43"; }
  (cd /tmp && $PY -I $M/check.py $W/$n "$e" $rid $extra) > $O/mock_check_$n.txt 2>&1
  echo "$n (expect $e): $(tail -1 $O/mock_check_$n.txt)" >> $O/mock_checks.txt
  G=$W/$n/content/results/ev10_v4p; mkdir -p $O/mock_$n
  for f in summary.json verify.json verdict.txt verify.txt b0.txt choice.txt identity.txt score.txt arms.txt STOPPED; do [ -f $G/$f ] && cp $G/$f $O/mock_$n/; done
  grep -a "ev10_v4p" $W/$n/content/job.log | sed "s#$W/$n#<MR>#g" | cut -c1-700 > $O/mock_$n/job_ev10_v4p_lines.txt
  sed -i "s#$W/$n#<MR>#g; s#$W/incomplete#<MR>#g" $O/mock_$n/* 2>/dev/null
done
cat $O/mock_checks.txt
