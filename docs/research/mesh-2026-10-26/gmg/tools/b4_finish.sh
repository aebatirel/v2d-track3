#!/bin/bash
# B4 finish (after every episode of the clean run is done): the cross-object identity test over all public bundles
# (PREREG B.15; updates each episode.json) and the B.2a leakage test, each as a clean guarded process under the strace
# audit; then the git summaries (gmg/build/b4/) and the HF store upload (runs/mesh-<run>/).
# Usage: b4_finish.sh CLEAN_RUN DEV_RUN [--no-push]
set -u
RUN=$1; DEVRUN=$2; PUSH=${3:-push}
REPO=$(cd "$(dirname "$0")/../../../../.." && pwd)
MR=$REPO/docs/research/mesh-2026-10-26
DATA=${GMG_DATA_ROOT:-/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad}
V=$DATA/venv/bin/python
AUD=$DATA/gmg/audit
TAG=$(basename "$RUN")
LOGD=$DATA/gmg/b4/logs/$TAG
mkdir -p "$LOGD"
cd "$MR" || exit 1
for step in identity b2a; do
  if [ -f "$LOGD/$step.done" ]; then echo "$step skip"; continue; fi
  GMG_MODE=clean "$V" -W ignore gmg/tools/strace_audit.py run --log "$AUD/b4-$TAG-$step.strace" \
    --manifest "$RUN/manifests/$step.json" -- \
    "$V" -W ignore "gmg/tools/b4_$step.py" --run "$RUN" > "$LOGD/$step.log" 2>&1
  RC=$?
  gzip -f "$AUD/b4-$TAG-$step.strace" 2> /dev/null
  echo "$step rc=$RC $(date -u +%H:%M:%S)"
  [ "$RC" = 0 ] || { echo "$step failed; see $LOGD/$step.log"; exit 1; }
  echo "rc=$RC" > "$LOGD/$step.done"
done
"$V" -I gmg/tools/b4_report.py --run "$RUN" --dev-run "$DEVRUN" --out gmg/build/b4 \
  --audit-glob "$AUD/b4-$TAG-*.audit.json" > "$LOGD/report.log" 2>&1 || { echo "report failed"; exit 1; }
tail -n 1 "$LOGD/report.log"
if [ "$PUSH" = push ]; then
  (cd /tmp && "$V" -I "$MR/gmg/tools/b4_push.py" --run "$RUN" --dev-run "$DEVRUN" --audit-glob "$AUD/b4-$TAG-*") \
    > "$LOGD/push.log" 2>&1 && echo "pushed" || echo "push failed; see $LOGD/push.log"
fi
echo FINISH_DONE
