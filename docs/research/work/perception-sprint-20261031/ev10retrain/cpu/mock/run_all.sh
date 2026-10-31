#!/bin/bash
# All eval-10 V4p retrain mock scenarios (CPU, ~5-8 min each with 2 scoring workers); one check.py line each into OUT/mock_checks.txt.
#   pass        MOCK_POLICY=copy (the new policy tracks V)                       -> SWAP-ELIGIBLE
#   floor       MOCK_POLICY=floor (the new policy fails like the packed one)      -> SWAP-ELIGIBLE [EQUAL FLOOR] (documents the rule)
#   worse       MOCK_POLICY=worse (floor + the beige knocked away)                -> NO-SWAP
#   invalid     one extra config key in seed 43's training                        -> INVALID (config diff vs the packed checkpoint)
#   incomplete  seed 43's training fails                                          -> INCOMPLETE (no confirmation)
#   rerun       a new box: RERUN_FROM=<incomplete's run> SEEDS_TODO=43            -> SWAP-ELIGIBLE over both seeds
#   topup       the 3rd official draw fails                                       -> SWAP-ELIGIBLE (11 calls, 10 scored draws)
#   nopacked    the H5p7 run not in the store yet (404)                           -> INCOMPLETE on the box (no long waits);
#               then cpu_after.sh completes the packed side from the store as on CPU after the box -> SWAP-ELIGIBLE
#   b0stop      the committed expectation replaced by the stored track            -> STOP before any reference (B0 MISMATCH)
#   badinput    a corrupted eval-10 track served by the store                     -> STOP before anything (md5)
# usage: run_all.sh [scenario ...]   (default: all, in the order above)
set -u
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/ev10retrain/mock; M=$(cd $(dirname $0) && pwd)
PY=$S/map/scoring/venv/bin/python; JOB='bash ops/jobs/ev10_v4p.sh'
run() {  # $1 name, then env assignments
  local n=$1; shift
  bash $M/setup.sh $W/$n > /dev/null
  ( cd /tmp && env "$@" nice -n 5 bash $M/run_mock.sh $W/$n "$JOB" )
}
for sc in ${@:-pass floor worse invalid incomplete rerun topup nopacked b0stop badinput}; do
  case $sc in
    pass) run pass MOCK_POLICY=copy ;;
    floor) run floor MOCK_POLICY=floor ;;
    worse) run worse MOCK_POLICY=worse ;;
    invalid) run invalid MOCK_POLICY=copy MOCK_CFG_EXTRA='perc2e10vs43_glock/' ;;
    incomplete) run incomplete MOCK_POLICY=copy MOCK_FAIL_TRAIN='perc2e10vs43_glock/' ;;
    rerun) rm -rf $W/rerun $W/incomplete_run1; mv $W/incomplete $W/incomplete_run1   # the re-run box keeps the first box's paths
           bash $M/setup.sh $W/incomplete /home/user/v2d-track3 $W/incomplete_run1/store > /dev/null
           ( cd /tmp && RUN_ID=20261031-e10v-mockrr MOCK_POLICY=copy nice -n 5 bash $M/run_mock.sh $W/incomplete \
               "RERUN_FROM=20261031-e10v-mocksha SEEDS_TODO=\"43\" $JOB" )
           mv $W/incomplete $W/rerun; mv $W/incomplete_run1 $W/incomplete ;;
    topup) run topup MOCK_POLICY=copy MOCK_CONF_FAIL_DRAW=3 ;;
    nopacked) run nopacked MOCK_POLICY=copy MOCK_HIDE=h5p7 ;;
    b0stop) bash $M/setup.sh $W/b0stop > /dev/null
            E=$W/b0stop/content/v2d-track3/docs/research/work/perception-sprint-20261031/ev10retrain/expect
            cp $W/b0stop/store/runs/20261026-pack6-5203d42/perc2/ep10/poses.npz $E/V_poses.npz
            $PY -I -c "import json,sys,hashlib; f=sys.argv[1]; d=json.load(open(f)); d['tracks']['V']['poses.npz']=hashlib.md5(open(sys.argv[2],'rb').read()).hexdigest(); json.dump(d,open(f,'w'))" $E/expect.json $E/V_poses.npz
            ( cd /tmp && nice -n 5 bash $M/run_mock.sh $W/b0stop "$JOB" ) ;;
    badinput) run badinput MOCK_BADPOSES=1 ;;
  esac
done
