#!/bin/bash
# Batch-2 generative probe, queue 2 (2026-10-29): Pixal3D-MV again after box_queue.sh's Pixal3D steps failed on
# relative view paths (fixed in gen_pixal_mv.py), then SAM 3D Objects once its weights are in the store.
# Waits for the TRELLIS.2 reruns so the GPU is not shared three ways (that caused OOM). Log: /content/results/gen/queue2.log
set -u
exec >> /content/results/gen/queue2.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen; R=/content/results/gen; cd /content/gin
while pgrep -f "[g]en_trellis2.py" > /dev/null || pgrep -f "^bash /content/v2d-track3/docs/research/mesh-2026-10-26/gen/box_queue.sh" > /dev/null; do sleep 10; done
(
  unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
  step "pixal3d_mv"
  /content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_mv --seeds 42,7 views_final/ep* > $R/pixal_mv.log 2>&1
  step "pixal3d view 0 only"
  /content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_v1 --num_views 1 --suffix _v1 --seeds 42,7 \
    views_final/ep23_wooden_piece_2 views_final/ep39_mini_dust_pan > $R/pixal_v1.log 2>&1
  step "pixal done"
)
step "sam3d weights"
mkdir -p /content/w/sam3d
for f in pipeline.yaml ss_generator.yaml slat_generator.yaml ss_decoder.yaml slat_decoder_gs.yaml slat_decoder_gs_4.yaml \
  slat_decoder_mesh.yaml ss_encoder.yaml slat_encoder.yaml ss_decoder.ckpt slat_decoder_gs.ckpt slat_decoder_gs_4.ckpt \
  slat_decoder_mesh.ckpt slat_generator.ckpt ss_generator.ckpt; do
  for t in $(seq 40); do
    hf download $HF_STORE runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints/$f --repo-type dataset \
      --local-dir /content/w/sam3d > /dev/null 2>&1 && break
    sleep 30                                  # the agent session may still be uploading the two large files
  done
done
C=/content/w/sam3d/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints
ls -la $C
unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
step "sam3d"
cd /content/gin && /content/genv3/bin/python $G/gen_sam3d.py --ckpt $C/pipeline.yaml --out $R/sam3d --seeds 42,7 \
  $(ls crops/ep*/*_k*.png) > $R/sam3d.log 2>&1
step "QUEUE2-DONE"
