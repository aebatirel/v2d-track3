#!/bin/bash
# Restart this box's job in place with newer code (2026-10-22: a bug found after launch while offers were scarce, so
# the boxes were kept instead of re-rented). On the box: bash restart_job.sh <commit> '<job command>'.
# Holds the box, stops the running job's processes (not the watchdog, tunnel or HTTPS shell), checks <commit> out and
# starts the job again. The hold is refreshed only while logs or outputs change (30 min window) and released when the
# job ends, so the watchdog saves and destroys as usual, and a stalled job still lapses.
set -u
SHA=$1; JOB=$2
echo $(( $(date +%s) + 1800 )) > /content/HOLD
pkill -f '^bash ops/jobs/' ; pkill -f '^bash /content/job2.sh'; pkill -f '^bash .*pipeline/pipeline_ep.sh'
pkill -f '^bash .*pipeline/auto_ep.sh'                    # 2026-10-23: auto_runs' children outlive their parent
pkill -f '[t]rain_flash_sac.py'; pkill -f '[e]valuate_policy.py'; pkill -f '[c]ontact_retarget.py'
pkill -f '[s]core_registered.py'; pkill -f '[r]ender_rollout'
sleep 5
git -C /content/v2d-track3 checkout -q "$SHA" || { echo "checkout $SHA failed"; exit 1; }
printf '%s\n' "cd /content/v2d-track3" "$JOB" > /content/job2.sh
cat > /content/hold2.sh << 'EOH'
sleep 90
while pgrep -f '^bash /content/job2.sh' > /dev/null; do
  [ -n "$(find /content/*.log /content/runs /content/results /content/refs -type f -mmin -30 2> /dev/null | head -1)" ] \
    && echo $(( $(date +%s) + 1800 )) > /content/HOLD
  sleep 60
done
rm -f /content/HOLD
EOH
setsid nohup bash /content/hold2.sh > /dev/null 2>&1 < /dev/null &
echo "[$(date -u +%FT%TZ)] restart at $SHA: $JOB" >> /content/job.log
setsid nohup bash /content/job2.sh >> /content/job.log 2>&1 < /dev/null &
sleep 2; pgrep -fa '^bash /content/job2.sh' | head -2; echo restarted
