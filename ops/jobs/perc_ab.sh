#!/bin/bash
# A/B of the frame-0 detection prior (2026-10-20 night): perc2 with DET_PRIOR=compact (joint choice over all
# size-gated proposals, penalising a 3-D spread beyond DET_D0) vs the baseline perc2 from refs_sweep.sh, per public
# episode, scored against mocap after inference (perc2's result.json). Reuses the baseline's depth cache, so it waits
# for each episode's baseline to exist. Output: /content/perc2c/epN, summary in /content/results/perc_ab.txt.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log; EPS=${EPS:-"12 27 26 0 31 2 39 11 40 13 41 18 42 21 43 22 44 23 45 24"}
for ep in $EPS; do
  for i in $(seq 1 240); do [ -s /content/perc2/ep$ep/result.json ] && break; sleep 10; done
  [ -s /content/perc2/ep$ep/result.json ] || { log "perc_ab ep$ep: no baseline" >> $J; continue; }
  O=/content/perc2c/ep$ep; mkdir -p $O; ln -sf $(readlink -f /content/perc2/ep$ep/depths_fs0.5.npy) $O/depths_fs0.5.npy
  DET_PRIOR=compact DET_K=${DET_K:-80} KF_MIN=120 EP=$ep OUT=$O python $P/perc2.py > $O/log.txt 2>&1
  log "perc_ab ep$ep rc=$?" >> $J
done
python - <<'EOF' | tee /content/results/perc_ab.txt >> $J
import json, os
rows = []
for ep in [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]:
    try:
        a = json.load(open(f'/content/perc2/ep{ep}/result.json'))['vo']; b = json.load(open(f'/content/perc2c/ep{ep}/result.json'))['vo']
    except Exception:
        continue
    rows.append((ep, a['AUC'], b['AUC'], a['MP_SR'], b['MP_SR']))
    print(f"ep{ep:>2} AUC base {a['AUC']:.3f} compact {b['AUC']:.3f} ({b['AUC'] - a['AUC']:+.3f})  MP {a['MP_SR']:.2f} -> {b['MP_SR']:.2f}")
if rows:
    n = len(rows); print(f"mean over {n}: AUC base {sum(r[1] for r in rows) / n:.3f} compact {sum(r[2] for r in rows) / n:.3f}; "
                       f"MP {sum(r[3] for r in rows) / n:.2f} -> {sum(r[4] for r in rows) / n:.2f}")
EOF
