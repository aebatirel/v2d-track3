#!/bin/bash
# Batch-2 generative probe, queue 3 (2026-10-29): TRELLIS.2 at 1024 for the (crop, seed) pairs still missing after the
# 1536 reruns (blue cup and a few others OOM at 1536 even alone), then the Sim(3) fits of the single-image models.
set -u
exec >> /content/results/gen/queue3.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen; R=/content/results/gen; cd /content/gin
while pgrep -f "^bash /content/v2d-track3/docs/research/mesh-2026-10-26/gen/box_queue.sh" > /dev/null; do sleep 10; done
unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
for s in 42 7; do
  MISSING=$(/content/genv/bin/python - $R/trellis2/gen_log.jsonl $s <<'PY'
import json, sys
ok, bad = set(), {}
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r['seed'] != int(sys.argv[2]): continue
    (ok.add(r['tag']) if r.get('ok') else bad.__setitem__(r['tag'], r['crop']))
print(' '.join(c for t, c in bad.items() if t not in ok))
PY
)
  step "trellis2 1024 seed $s: $MISSING"
  [ -n "$MISSING" ] && /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2_1024 --res 1024 --seeds $s $MISSING >> $R/trellis2_1024.log 2>&1
done
step "sim3 trellis2 hy21 trellis2_1024"
sed -i 's/xargs -P 48/xargs -P 20/' $G/box_sim3.sh
bash $G/box_sim3.sh trellis2 hy21 trellis2_1024 >> $R/sim3_more.log 2>&1
step "QUEUE3-DONE"
