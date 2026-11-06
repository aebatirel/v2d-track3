#!/bin/bash
# All ep11-gate mock scenarios (CPU, ~4-5 min each); one check.py line per scenario into OUT/mock_checks.txt.
#   pass        default (mock effect +0.12 on the V4p arm)                       -> PASS
#   fail        MOCK_EFFECT=0.02                                                 -> FAIL (delta < +0.05)
#   seeddrop    MOCK_EFFECT=0.20, seed 43 of T lowered by 0.27                   -> FAIL (seed clause; delta +0.065 >= +0.05)
#   invalid     one extra config key in T s42's training                         -> INVALID (config diff)
#   incomplete  T s43's training fails                                           -> INCOMPLETE
#   rerun       a new box re-runs only e11t:43 on incomplete's stored references -> PASS over all 4 cells
#   b0stop      the committed expectation of T replaced by C's                   -> STOP before any reference (B0 MISMATCH)
#   badinput    a corrupted P_o poses.npz served by the store                    -> STOP before anything (md5)
# usage: run_all.sh [scenario ...]   (default: all, in the order above)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/ep11gate/mock; M=$(cd $(dirname $0) && pwd)
O=$M/../out; PY=$S/map/scoring/venv/bin/python; JOB='bash ops/jobs/ep11_gate.sh'; mkdir -p $O
run() {  # $1 name, $2 expect, then env assignments
  local n=$1 e=$2; shift 2
  [ "$n" = rerun ] || bash $M/setup.sh $W/$n > /dev/null
  ( cd /tmp && env "$@" bash $M/run_mock.sh $W/$n "$JOB" )
}
for sc in ${@:-pass fail seeddrop invalid incomplete rerun b0stop badinput}; do
  case $sc in
    pass) run pass PASS ;;
    fail) run fail FAIL MOCK_EFFECT=0.02 ;;
    seeddrop) run seeddrop FAIL MOCK_EFFECT=0.20 MOCK_DROP_SEED=43 MOCK_DROP=0.27 ;;
    invalid) run invalid INVALID MOCK_CFG_EXTRA='perc2e11ts42_glock/' ;;
    incomplete) run incomplete INCOMPLETE MOCK_FAIL_TRAIN='perc2e11ts43_glock/' ;;
    rerun) # a real re-run box has the same /content as the first box, so the first run's checkpoint configs (absolute
           # task.parquet paths) resolve on it; here the re-run tree takes the incomplete tree's path while it runs
           rm -rf $W/rerun $W/incomplete_run1; mv $W/incomplete $W/incomplete_run1
           bash $M/setup.sh $W/incomplete /home/user/v2d-track3 $W/incomplete_run1/store > /dev/null
           ( cd /tmp && RUN_ID=20261031-e11g-mockrr bash $M/run_mock.sh $W/incomplete \
               "RERUN_FROM=20261031-e11g-mocksha CELLS=\"e11t:43\" $JOB" )
           mv $W/incomplete $W/rerun; mv $W/incomplete_run1 $W/incomplete ;;
    b0stop) bash $M/setup.sh $W/b0stop > /dev/null
            E=$W/b0stop/content/v2d-track3/docs/research/work/perception-sprint-20261031/ep11gate/expect
            cp $E/C_poses.npz $E/T_poses.npz
            $PY -I -c "import json,sys; f=sys.argv[1]; d=json.load(open(f)); d['tracks']['T']=d['tracks']['C']; json.dump(d,open(f,'w'))" $E/expect.json
            ( cd /tmp && bash $M/run_mock.sh $W/b0stop "$JOB" ) ;;
    badinput) run badinput STOP MOCK_BADPOSES=1 ;;
  esac
done
