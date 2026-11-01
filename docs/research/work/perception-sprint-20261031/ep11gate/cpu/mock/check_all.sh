#!/bin/bash
# check.py on every scenario of run_all.sh; one summary line each into OUT/mock_checks.txt, details OUT/mock_check_<n>.txt,
# and the gate's own outputs of each verdict scenario (summary.json, verify.json, verdict / verify / b0 text) under OUT/mock_<n>/.
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/ep11gate/mock; M=$(cd $(dirname $0) && pwd)
O=$M/../out; PY=$S/map/scoring/venv/bin/python; : > $O/mock_checks.txt
for x in pass:PASS fail:FAIL seeddrop:FAIL invalid:INVALID incomplete:INCOMPLETE rerun:PASS b0stop:"STOP:B0 MISMATCH" badinput:STOP:md5; do
  n=${x%%:*}; e=${x#*:}; extra=""; rid=20261031-e11g-mocksha
  [ $n = rerun ] && { rid=20261031-e11g-mockrr; extra="--rerun e11t:43"; }
  (cd /tmp && $PY -I $M/check.py $W/$n "$e" $rid $extra) > $O/mock_check_$n.txt 2>&1
  echo "$n (expect $e): $(tail -1 $O/mock_check_$n.txt)" >> $O/mock_checks.txt
  G=$W/$n/content/results/ep11_gate; mkdir -p $O/mock_$n
  for f in summary.json verify.json verdict.txt verify.txt b0.txt arms.txt STOPPED; do [ -f $G/$f ] && cp $G/$f $O/mock_$n/; done
  grep -a "ep11_gate" $W/$n/content/job.log | sed "s#$W/$n#<MR>#g" | cut -c1-600 > $O/mock_$n/job_ep11_gate_lines.txt
  sed -i "s#$W/$n#<MR>#g" $O/mock_$n/* 2>/dev/null
done
cat $O/mock_checks.txt
