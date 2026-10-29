#!/bin/bash
# Batch-2 generative probe: the remaining runs on the box, in two GPU queues (2026-10-29). Log: /content/results/gen/queue.log
#  A (env A, large): Pixal3D-MV on the final view sets (all views; and view 0 only where a set has > 1 view), then
#    TRELLIS.2 reruns of the crops that failed (OOM while three jobs shared the GPU) and the ep11 beige-cup crops
#  B (env B, small): TripoSG and Hunyuan3D-2.1 on the beige-cup crops, after the running hy21 batch
set -u
exec >> /content/results/gen/queue.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen; R=/content/results/gen; cd /content/gin
hf download $HF_STORE runs/mesh-20261029-gen-f3fbeb0/inputs/views_final.tar --repo-type dataset --local-dir /content/gin > /dev/null 2>&1
tar xf runs/mesh-20261029-gen-f3fbeb0/inputs/views_final.tar && cp -r inputs2/crops/ep11 crops/ && step "INPUTS-OK $(sha256sum runs/mesh-20261029-gen-f3fbeb0/inputs/views_final.tar | cut -c1-16)"
BEIGE="crops/ep11/beige_cup_k0.png crops/ep11/beige_cup_k6.png"
(
  while pgrep -f "[g]en_trellis2.py" > /dev/null; do sleep 10; done
  step "A: pixal3d_mv"
  /content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_mv --seeds 42,7 views_final/ep* > $R/pixal_mv.log 2>&1
  MULTI=$(for d in views_final/ep*; do [ $(grep -c file_path $d/transforms.json) -gt 1 ] && echo $d; done)
  step "A: pixal3d view 0 only: $MULTI"
  [ -n "$MULTI" ] && /content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_v1 --num_views 1 --suffix _v1 --seeds 42,7 $MULTI > $R/pixal_v1.log 2>&1
  for s in 42 7; do
    FAILED=$(/content/genv/bin/python - $R/trellis2/gen_log.jsonl $s <<'PY'
import json, sys
ok, bad = set(), {}
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r['seed'] != int(sys.argv[2]): continue
    (ok.add(r['tag']) if r.get('ok') else bad.__setitem__(r['tag'], r['crop']))
print(' '.join(c for t, c in bad.items() if t not in ok))
PY
)
    step "A: trellis2 seed $s reruns: $FAILED + beige"
    /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2 --seeds $s $FAILED $BEIGE >> $R/trellis2_rerun.log 2>&1
  done
  step "A-DONE"
) &
(
  while pgrep -f "[g]en_envb.py" > /dev/null || pgrep -f "[w]hile pgrep" > /dev/null; do sleep 10; done
  step "B: triposg + hy21 beige"
  /content/genv2/bin/python $G/gen_envb.py --model triposg --out $R/triposg --seeds 42,7 $BEIGE >> $R/triposg_beige.log 2>&1
  /content/genv2/bin/python $G/gen_envb.py --model hy21 --out $R/hy21 --seeds 42,7 $BEIGE >> $R/hy21_beige.log 2>&1
  step "B-DONE"
) &
wait
step "QUEUE-DONE"
