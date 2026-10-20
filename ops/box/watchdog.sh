#!/bin/bash
# Stall watchdog (CLAUDE.md): no fixed time limit. Destroys the box only when the job has stopped making progress for
# STALL_MIN minutes, after saving what exists. Also pushes interim results every PUSH_MIN minutes and enforces HOLD
# expiry once the job is done. Written 2026-10-20, not yet run on Vast.
# Progress = a new or changed file under the output paths, OR GPU utilisation >= 10 %. The GPU signal guards against
# killing a healthy training run that logs rarely (FlashCHORD runs with logging.mode=disabled); drop it if box 1
# shows that training writes regular log lines.
. /content/v2d-track3/ops/box/lib.sh
STALL_MIN=${STALL_MIN:-30}; PUSH_MIN=${PUSH_MIN:-30}
W="/workspace/run_job.log /content/job.log /content/setup.log /content/setup_flashchord.log /content/setup_data.log
   /content/setup_hands.log /content/perc2 /content/perc4 /content/refs /content/runs /content/results /content/hfds
   /content/hfstore /content/snap /content/cache"
touch $ST/progress; last_push=$(date +%s)
while sleep 120; do
  util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2> /dev/null | sort -n | tail -1)
  if [ -n "$(find $W -newer $ST/progress -type f 2> /dev/null | head -1)" ] || [ "${util:-0}" -ge 10 ]; then
    touch $ST/progress
  fi
  now=$(date +%s); idle=$(( (now - $(stat -c %Y $ST/progress)) / 60 ))
  if [ -f $ST/done ] && [ ! -f $ST/held_exit ]; then          # run_job.sh is saving and destroying
    [ $(( (now - $(stat -c %Y $ST/done)) / 60 )) -ge 90 ] && { self_destroy "still up 90 min after the job ended"; exit 0; }
    continue
  fi
  if [ -f $ST/held_exit ]; then
    held || { self_destroy "job finished; hold expired"; exit 0; }
    continue
  fi
  if [ $idle -ge $STALL_MIN ] && ! held; then
    log "stalled: no progress for $idle min"; self_destroy "stalled ${idle} min"; exit 0
  fi
  if [ $(( now - last_push )) -ge $(( PUSH_MIN * 60 )) ]; then
    bash $OPS/store.sh push-run > /dev/null 2>&1 &
    last_push=$now
  fi
done
