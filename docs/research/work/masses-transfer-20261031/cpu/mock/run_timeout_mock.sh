#!/bin/bash
# End-to-end injected evaluation stalls for the masses transfer check (2026-10-31, review fix 4): the exact JOBS.txt
# string in a CPU mock (setup.sh) whose mass_check.sh copy has EVAL_TIMEOUT=4 instead of 1200 (the only change to the
# script under test), with three evaluations made to hang by the stub (stub.py MOCK_HANG / MOCK_HANG_NOTERM):
#   mass1s42 ep2  best/r3                     hangs, ends on SIGTERM        -> expected eval_rc 124
#   mass1s43 ep2  curve/policy_9998336/r2     hangs, ends on SIGTERM        -> expected eval_rc 124
#   mass0s43 ep12 best/r7                     hangs and IGNORES SIGTERM     -> expected eval_rc 137 (timeout -k 60 kill)
# then timeout_check.py MR OUT.json. usage: run_timeout_mock.sh MR OUT.json
MR=$1; OUT=$2; M=$(cd $(dirname $0) && pwd)
bash $M/setup.sh $MR > /dev/null || exit 1
sed -i 's/^  EVAL_TIMEOUT=1200 NO_PUSH=1$/  EVAL_TIMEOUT=4 NO_PUSH=1/' $MR/content/v2d-track3/ops/jobs/mass_check.sh
grep -q '^  EVAL_TIMEOUT=4 NO_PUSH=1$' $MR/content/v2d-track3/ops/jobs/mass_check.sh || { echo "EVAL_TIMEOUT line not found"; exit 1; }
echo "export MOCK_HANG='mass1s42_glock_public/ep2/best/r3/|mass1s43_glock_public/ep2/curve/policy_9998336/r2/' MOCK_HANG_NOTERM='mass0s43_glock_public/ep12/best/r7/'" >> $MR/env.sh
bash $M/run_mock.sh $MR 'bash ops/jobs/mass_check.sh'
$(. $MR/env.sh; echo $MOCK_PY) -I $M/timeout_check.py $MR $OUT
