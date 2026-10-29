#!/bin/bash
# Batch-2 generative probe: resume after the interruptible box was outbid and stopped (2026-10-29 ~22:52 UTC; bid
# raised to $1.30/h and restarted). Container processes were lost; /content (envs, weights, results) survived.
# Runs whatever is still missing, one large model on the GPU at a time:
#   1 Hunyuan3D-2.1 missing (crop, seed) pairs                      (env B, small; alongside 2)
#   2 Pixal3D-MV on the final view sets (+ view-0-only for the sets with > 1 view)
#   3 TRELLIS.2 missing pairs at 1536 alone, then any still missing at 1024 (trellis2_1024)
#   4 SAM 3D Objects on crops.py's first-ranked crop of each object (the crops that are scored), seeds 42/7
#   5 Sim(3) fits of the single-image outputs (CPU), filling all gaps
# Log: /content/results/gen/resume.log
set -u
exec >> /content/results/gen/resume.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen; R=/content/results/gen; cd /content/gin
C=/content/w/sam3d/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints
mkdir -p /content/w/sam3d
for f in pipeline.yaml ss_generator.yaml slat_generator.yaml ss_decoder.yaml slat_decoder_gs.yaml slat_decoder_gs_4.yaml \
  slat_decoder_mesh.yaml ss_encoder.yaml slat_encoder.yaml ss_decoder.ckpt slat_decoder_gs.ckpt slat_decoder_gs_4.ckpt \
  slat_decoder_mesh.ckpt slat_generator.ckpt ss_generator.ckpt; do
  [ -s $C/$f ] || hf download $HF_STORE runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints/$f \
    --repo-type dataset --local-dir /content/w/sam3d > /dev/null 2>&1 || step "sam3d weight $f FAIL"
done
step "sam3d weights: $(ls $C | wc -l) files"
unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
missing() {  # $1 model dir, $2 seed, rest: crops -> the crops without an ok record for that seed
  /content/genv/bin/python - "$@" <<'PY'
import json, os, sys
d, seed, crops = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ok = set()
for sub in (d, d + '_1024'):
    p = os.path.join(sub, 'gen_log.jsonl')
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l)
            if r.get('ok') and r['seed'] == seed:
                ok.add(r['tag'])
print(' '.join(c for c in crops if os.path.splitext(os.path.basename(c))[0] not in ok))
PY
}
ALL=$(ls crops/ep*/*_k*.png)
FIRST=$(/content/genv/bin/python -c "
import json, glob
print(' '.join(sorted(f'crops/{p.split(\"/\")[1]}/' + json.load(open(p))['chosen'][0]['tag'] + '.png' for p in glob.glob('crops/ep*/*_crops.json'))))")
(
  for s in 42 7; do
    M=$(missing $R/hy21 $s $ALL); step "hy21 seed $s: $M"
    [ -n "$M" ] && /content/genv2/bin/python $G/gen_envb.py --model hy21 --out $R/hy21 --seeds $s $M >> $R/hy21_resume.log 2>&1
  done
  step "hy21 done"
) &
step "pixal3d_mv"
/content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_mv --seeds 42,7 views_final/ep* > $R/pixal_mv.log 2>&1
/content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_v1 --num_views 1 --suffix _v1 --seeds 42,7 \
  views_final/ep23_wooden_piece_2 views_final/ep39_mini_dust_pan > $R/pixal_v1.log 2>&1
step "pixal done"
for s in 42 7; do
  M=$(missing $R/trellis2 $s $ALL); step "trellis2 1536 seed $s: $M"
  [ -n "$M" ] && /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2 --seeds $s $M >> $R/trellis2_resume.log 2>&1
  M=$(missing $R/trellis2 $s $ALL); step "trellis2 1024 seed $s: $M"
  [ -n "$M" ] && /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2_1024 --res 1024 --seeds $s $M >> $R/trellis2_1024.log 2>&1
done
step "trellis2 done"
step "sam3d: $FIRST"
/content/genv3/bin/python $G/gen_sam3d.py --ckpt $C/pipeline.yaml --out $R/sam3d --seeds 42,7 $FIRST > $R/sam3d.log 2>&1
step "sam3d done"
wait
bash $G/box_sim3.sh triposg trellis2 hy21 trellis2_1024 sam3d >> $R/sim3_more.log 2>&1
step "RESUME-DONE"
