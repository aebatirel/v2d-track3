#!/bin/bash
# Queue a second job on this box behind the running one (2026-10-24: on evF the training of eval 33 ran out of GPU
# memory while eval 35 / 36 went on). On the box: bash followup_job.sh <commit> '<job command>'.
# Holds the box so it does not self-destroy when the first job ends, waits for that job (run_state/done), checks
# <commit> out, runs the follow-up (output appended to /content/job.log), saves to the HF store and releases the hold;
# the watchdog then saves and destroys as usual. While the follow-up runs, the hold is refreshed only while logs or
# outputs change (30 min window), so a stalled follow-up still lapses.
set -u
SHA=$1; JOB=$2
echo $(( $(date +%s) + 1800 )) > /content/HOLD
printf '%s\n' "cd /content/v2d-track3" "$JOB" > /content/job3.sh
cat > /content/followup.sh << EOF
. /content/v2d-track3/ops/box/lib.sh
while [ ! -f \$ST/done ]; do echo \$(( \$(date +%s) + 1800 )) > /content/HOLD; sleep 60; done
git -C /content/v2d-track3 fetch -q origin && git -C /content/v2d-track3 checkout -q $SHA \
  || { log "followup: checkout $SHA FAILED" >> /content/job.log; rm -f /content/HOLD; exit 1; }
log "followup at $SHA: \$(tail -1 /content/job3.sh)" >> /content/job.log
label "followup running"
bash /content/job3.sh >> /content/job.log 2>&1 &
jp=\$!
while kill -0 \$jp 2> /dev/null; do
  [ -n "\$(find /content/*.log /content/runs /content/results /content/refs -type f -mmin -30 2> /dev/null | head -1)" ] \
    && echo \$(( \$(date +%s) + 1800 )) > /content/HOLD
  sleep 60
done
wait \$jp; log "followup exit \$?" >> /content/job.log
bash \$OPS/store.sh push-run >> /content/job.log 2>&1 || log "followup: push-run FAILED" >> /content/job.log
rm -f /content/HOLD
EOF
setsid nohup bash /content/followup.sh > /content/followup.out 2>&1 < /dev/null &
sleep 2; pgrep -fa '[f]ollowup.sh' | head -2; echo "followup queued at $SHA"
