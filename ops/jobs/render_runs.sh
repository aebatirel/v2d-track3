#!/bin/bash
# Re-render finished policies over the WHOLE episode (render_rollout.sh used to stop at 181 frames). Written
# 2026-10-21. SPECS = "RUN_ID:PERCVARIANT:EP ..." (e.g. "20261021-hard-ep18-6f2f98a:perc2c:18"); each run's outputs
# are pulled from the store (policy, reference, perception) so the checkpoint's paths resolve, then the newest
# policy is rendered to /content/results/<percvariant>/ep<EP>-s42/render_full/ and everything is pushed back.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log
label "render full: $SPECS"
for r in $(for s in $SPECS; do echo ${s%%:*}; done | sort -u); do
  bash $OPS/store.sh pull-run $r >> $J 2>&1 || log "pull-run $r FAILED" >> $J
done
for s in $SPECS; do
  IFS=: read -r run pv ep <<< "$s"
  CK=$(ls -v /content/runs/$pv/ep$ep-s42/policy_*.safetensors 2>/dev/null | tail -1)
  [ -n "$CK" ] || { log "$s: no policy" >> $J; continue; }
  perc=${pv%%[cvwm]*}; [ -s /content/$perc/ep$ep/poses.npz ] || perc=perc2
  NF=$(python -c "import numpy as np; print(len(np.load('/content/$perc/ep$ep/poses.npz')['world_T_cam']))" 2>/dev/null || echo 400)
  bash $P/render_rollout.sh $CK /content/results/$pv/ep$ep-s42/render_full $NF >> $J 2>&1
  log "$s: rendered $NF frames rc=$? ($CK)" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
exit 0
