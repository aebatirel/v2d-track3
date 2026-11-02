#!/bin/bash
# G2 generation batch (C4 PREREG s7 "addendum 2", 2026-11-02) on the box, after box_setup.sh (envs A/B, weights) and
# sam3d_setup.sh (env C, SAM 3D checkpoints from the store). Started in the background through `ops/vast.sh exec`.
# Inputs (GT-free): runs/$RUN_ID/inputs/g2_inputs.tar from the store = crops_flat/ep<E>_<obj>_k<k>.png (scripts/crops.py,
# top-2 per episode) + obs_sub/ep<E>_<obj>.npz (40k of our observed points). No scan, mocap, parquet pose or *_align.
# Order on the GPU (one large model at a time; TRELLIS.2 ran out of memory when it shared the GPU on 29 Oct):
#   1  SAM 3D Objects (env C) alongside Hunyuan3D-2.1 shape (env B, small)   every crop x seeds 42,7,123,2025
#   2  TRELLIS.2-4B 1536 cascade alone (env A); then 1024 for the (crop, seed) pairs still missing (trellis2_1024)
# CPU, alongside: GT-free Sim(3) fit (sim3_fit.py) of every output to the observed points of the crop's own episode.
# Resumable (interruptible box): each step runs only the (crop, seed) pairs without an ok record.
# Ends with gen/SHA256SUMS over every generated .ply (raw and Sim(3)) and the marker G2-GEN-DONE.
# Log: /content/results/gen/g2_queue.log
set -u
R=/content/results/gen; mkdir -p $R
exec >> $R/g2_queue.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen
SEEDS="42 7 123 2025"; NP=${NP:-$(( $(nproc) > 12 ? $(nproc) - 8 : 4 ))}
mkdir -p /content/gin && cd /content/gin
if [ ! -d crops_flat ]; then
  hf download $HF_STORE runs/$RUN_ID/inputs/g2_inputs.tar --repo-type dataset --local-dir /content/gin > /dev/null 2>&1
  tar xf runs/$RUN_ID/inputs/g2_inputs.tar && step "INPUTS-OK $(sha256sum runs/$RUN_ID/inputs/g2_inputs.tar | cut -c1-16)" \
    || { step "INPUTS-FAIL"; exit 1; }
fi
ALL=$(ls crops_flat/ep*_k*.png); step "crops: $(echo $ALL | wc -w); NP=$NP"
C=/content/w/sam3d/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints
until grep -q SETUP-DONE $R/setup.log 2> /dev/null && grep -qE "C-IMPORT-(OK|FAIL)" $R/sam3d_setup.log 2> /dev/null; do sleep 20; done
step "setup markers: $(grep -aoE '[A-Z0-9-]+-(OK|FAIL)' $R/setup.log $R/sam3d_setup.log | sed 's/.*://' | sort -u | tr '\n' ' ')"
unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
groups() {  # $1 model dir -> one line per group of seeds with the same missing crops: "s1,s2 crop crop ..."
  /content/genv/bin/python - $1 "$SEEDS" $ALL <<'PY'
import json, os, sys
d, seeds, crops = sys.argv[1], [int(x) for x in sys.argv[2].split()], sys.argv[3:]
ok = set()
for sub in (d, d + '_1024'):                     # a pair done at 1024 counts as done for TRELLIS.2
    p = os.path.join(sub, 'gen_log.jsonl')
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l)
            if r.get('ok'):
                ok.add((r['tag'], r['seed']))
g = {}
for s in seeds:
    miss = tuple(c for c in crops if (os.path.splitext(os.path.basename(c))[0], s) not in ok)
    if miss:
        g.setdefault(miss, []).append(str(s))
for miss, ss in g.items():
    print(','.join(ss), ' '.join(miss))
PY
}
sim3() {  # $@ model folders: fit every output that has no Sim(3) copy yet (tag ep<E>_<obj>_k<k>_s<seed>)
  for m in "$@"; do
    mkdir -p $R/${m}_sim3
    for f in $R/$m/*_s*.ply; do
      [ -e "$f" ] || continue
      b=$(basename $f .ply); e=${b%%_*}; rest=${b#*_}; obj=${rest%_k*}
      [ -s $R/${m}_sim3/$b.ply ] && continue
      echo "$f /content/gin/obs_sub/${e}_$obj.npz $R/${m}_sim3/$b.ply"
    done | xargs -P $NP -L 1 sh -c 'OMP_NUM_THREADS=1 nice -n 5 /content/genv/bin/python '$G'/sim3_fit.py --obs $1 --out $2 $0' \
      >> $R/${m}_sim3/fits.jsonl 2>> $R/${m}_sim3/errors.log
    step "sim3 $m: $(grep -c . $R/${m}_sim3/fits.jsonl) fit lines, $(ls $R/${m}_sim3/*.ply 2> /dev/null | wc -l) meshes"
  done
}
rm -f $R/.hy21_gen_done
(
  groups $R/hy21 | while read -r ss M; do
    step "hy21 seeds $ss: $(echo $M | wc -w) crops"
    /content/genv2/bin/python $G/gen_envb.py --model hy21 --out $R/hy21 --seeds $ss $M >> $R/hy21.log 2>&1 < /dev/null
  done
  step "hy21 done: $(grep -c '"ok": true' $R/hy21/gen_log.jsonl) ok"; touch $R/.hy21_gen_done
  sim3 hy21
) &
if grep -q C-IMPORT-OK $R/sam3d_setup.log; then
  groups $R/sam3d | while read -r ss M; do
    step "sam3d seeds $ss: $(echo $M | wc -w) crops"
    /content/genv3/bin/python $G/gen_sam3d.py --ckpt $C/pipeline.yaml --out $R/sam3d --seeds $ss $M >> $R/sam3d.log 2>&1 < /dev/null
  done
  step "sam3d done: $(grep -c '"ok": true' $R/sam3d/gen_log.jsonl) ok"
else
  step "sam3d SKIPPED: env C import failed (see sam3d_setup.log)"
fi
sim3 sam3d &
until [ -e $R/.hy21_gen_done ]; do sleep 10; done                  # TRELLIS.2 alone on the GPU
groups $R/trellis2 | while read -r ss M; do
  step "trellis2 1536 seeds $ss: $(echo $M | wc -w) crops"
  /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2 --seeds $ss $M >> $R/trellis2.log 2>&1 < /dev/null
done
groups $R/trellis2 | while read -r ss M; do                              # still missing (out of memory at 1536)
  step "trellis2 1024 seeds $ss: $M"
  /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2_1024 --res 1024 --seeds $ss $M >> $R/trellis2_1024.log 2>&1 < /dev/null
done
step "trellis2 done: $(grep -c '"ok": true' $R/trellis2/gen_log.jsonl) ok at 1536, $(grep -c '"ok": true' $R/trellis2_1024/gen_log.jsonl 2> /dev/null) at 1024"
wait
sim3 trellis2 trellis2_1024 hy21 sam3d                                   # fills every gap
cd /content/results && find gen -name '*.ply' | sort | xargs sha256sum > gen/SHA256SUMS
step "SHA256SUMS: $(wc -l < gen/SHA256SUMS) files"
step "G2-GEN-DONE"
