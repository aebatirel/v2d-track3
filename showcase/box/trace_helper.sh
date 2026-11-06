# Showcase trace helper (agent, 2026-11-06): the job's own render step fails on these boxes (pyglet: no GL config), so
# after each robot's summary.json appears, record its evaluator-style replay with the viewer off (trace_cmd.sh) and
# push. The box is held (bounded /content/HOLD) until every robot is processed, then released: run_job's held exit
# makes the watchdog save and destroy. usage: trace_helper.sh "ROBOTS"
. /content/v2d-track3/ops/box/lib.sh
R="$1"; L=/content/trace_helper.log
log "trace helper start [$R]" >> $L
while :; do
  left=0
  for r in $R; do
    O=/content/results/showcase/ep27_$r
    if [ -s $O/summary.json ] && [ ! -s $O/policy_trace.npz ] && [ ! -f $O/trace_tried ]; then
      touch $O/trace_tried; log "tracing $r" >> $L; bash /content/trace_cmd.sh $r >> $L 2>&1
      bash $OPS/store.sh push-run > /dev/null 2>&1 || true
    fi
    [ -s $O/summary.json ] || [ -f $ST/done ] || left=$((left + 1))
    [ -s $O/summary.json ] && [ ! -s $O/policy_trace.npz ] && [ ! -f $O/trace_tried ] && left=$((left + 1))
  done
  if [ $left -eq 0 ] && [ -f $ST/done ]; then
    bash $OPS/store.sh push-run > /dev/null 2>&1 || true
    log "all robots processed; releasing HOLD" >> $L; rm -f /content/HOLD; break
  fi
  sleep 60
done
