#!/bin/bash
# Rack round R (C4 PREREG s14 "addendum 9", 2026-11-03) on the box, after box_setup.sh (envs A/B, weights),
# sam3d_setup.sh (env C) and the hf-2.2 weight fix (launch_box_r.sh). Copy of G3 box_g3.sh: R inputs, six seeds.
# Inputs (GT-free): runs/$RUN_ID/inputs/r_inputs.tar from the store = crops_flat/ep<E>_<obj>_k<k>.png (scripts/crops.py,
# ranks 3-6 per rack episode) + obs_sub/ep<E>_<obj>.npz (40k of our observed points) + views_final/ep<E>_<obj>/ (gen/mv_views.py
# posed view sets, our object frame). No scan, mocap, parquet pose or *_align.
# Order on the GPU (one large model at a time; Hunyuan3D-2.1 shape is small and runs alongside, as in G2):
#   1  SAM 3D Objects (env C) alongside Hunyuan3D-2.1 shape (env B)            every crop x seeds 42,7,123,2025,31337,777
#   2  Pixal3D-MV 1536 cascade (env A), every view set x seeds; 1024 for pairs still missing (pixal_mv_1024)
#   3  TRELLIS.2-4B 1536 cascade (env A); then 1024 for the (crop, seed) pairs still missing (trellis2_1024)
# CPU, alongside: GT-free Sim(3) fit (sim3_fit.py) of every single-image output to the observed points of the crop's own
# episode. Pixal3D-MV outputs are already in our object frame (no Sim(3)).
# Resumable: each step runs only the (input, seed) pairs without an ok record.
# Ends with gen/SHA256SUMS over every generated .ply (raw, Sim(3), Pixal3D-MV _gen and object frame) and R-GEN-DONE.
# Log: /content/results/gen/r_queue.log
set -u
R=/content/results/gen; mkdir -p $R
exec >> $R/r_queue.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen
SEEDS="42 7 123 2025 31337 777"; NP=${NP:-$(( $(nproc) > 12 ? $(nproc) - 8 : 4 ))}
mkdir -p /content/gin && cd /content/gin
if [ ! -d crops_flat ]; then
  for i in 1 2 3 4 5; do   # HF 502 retries (G3 NOTES)
    hf download $HF_STORE runs/$RUN_ID/inputs/r_inputs.tar --repo-type dataset --local-dir /content/gin > /dev/null 2>&1 && break
    sleep 20; done
  tar xf runs/$RUN_ID/inputs/r_inputs.tar && step "INPUTS-OK $(sha256sum runs/$RUN_ID/inputs/r_inputs.tar | cut -c1-16)" \
    || { step "INPUTS-FAIL"; exit 1; }
fi
ALL=$(ls crops_flat/ep*_k*.png); VIEWS=$(ls -d views_final/ep*_*/)
step "crops: $(echo $ALL | wc -w); view sets: $(echo $VIEWS | wc -w); NP=$NP"
C=/content/w/sam3d/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints
until grep -q SETUP-DONE $R/setup.log 2> /dev/null && grep -qE "C-IMPORT-(OK|FAIL)" $R/sam3d_setup.log 2> /dev/null; do sleep 20; done
step "setup markers: $(grep -aoE '[A-Z0-9-]+-(OK|FAIL)' $R/setup.log $R/sam3d_setup.log | sed 's/.*://' | sort -u | tr '\n' ' ')"
unset HF_TOKEN GH_TOKEN CONTAINER_API_KEY; export HF_HOME=/content/hfcache
groups() {  # $1 model dir, rest: inputs -> one line per group of seeds with the same missing inputs: "s1,s2 in in ..."
  local d=$1; shift
  /content/genv/bin/python - $d "$SEEDS" "$@" <<'PY'
import json, os, sys
d, seeds, ins = sys.argv[1], [int(x) for x in sys.argv[2].split()], sys.argv[3:]
ok = set()
for sub in (d, d + '_1024'):                     # a pair done at 1024 counts as done
    p = os.path.join(sub, 'gen_log.jsonl')
    if os.path.exists(p):
        for l in open(p):
            r = json.loads(l)
            if r.get('ok'):
                ok.add((r['tag'], r['seed']))
g = {}
for s in seeds:
    miss = tuple(c for c in ins if (os.path.splitext(os.path.basename(c.rstrip('/')))[0], s) not in ok)
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
    done | xargs -r -P $NP -L 1 sh -c 'OMP_NUM_THREADS=1 nice -n 5 /content/genv/bin/python '$G'/sim3_fit.py --obs $1 --out $2 $0' \
      >> $R/${m}_sim3/fits.jsonl 2>> $R/${m}_sim3/errors.log
    step "sim3 $m: $(grep -c . $R/${m}_sim3/fits.jsonl) fit lines, $(ls $R/${m}_sim3/*.ply 2> /dev/null | wc -l) meshes"
  done
}
rm -f $R/.hy21_gen_done
(
  groups $R/hy21 $ALL | while read -r ss M; do
    step "hy21 seeds $ss: $(echo $M | wc -w) crops"
    /content/genv2/bin/python $G/gen_envb.py --model hy21 --out $R/hy21 --seeds $ss $M >> $R/hy21.log 2>&1 < /dev/null
  done
  step "hy21 done: $(grep -c '"ok": true' $R/hy21/gen_log.jsonl) ok"; touch $R/.hy21_gen_done
  sim3 hy21
) &
if grep -q C-IMPORT-OK $R/sam3d_setup.log; then
  groups $R/sam3d $ALL | while read -r ss M; do
    step "sam3d seeds $ss: $(echo $M | wc -w) crops"
    /content/genv3/bin/python $G/gen_sam3d.py --ckpt $C/pipeline.yaml --out $R/sam3d --seeds $ss $M >> $R/sam3d.log 2>&1 < /dev/null
  done
  step "sam3d done: $(grep -c '"ok": true' $R/sam3d/gen_log.jsonl) ok"
else
  step "sam3d SKIPPED: env C import failed (see sam3d_setup.log)"
fi
sim3 sam3d &
groups $R/pixal_mv $VIEWS | while read -r ss M; do                     # Pixal3D-MV after SAM 3D (one large model)
  step "pixal_mv 1536 seeds $ss: $(echo $M | wc -w) view sets"
  /content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_mv --seeds $ss $M >> $R/pixal_mv.log 2>&1 < /dev/null
done
groups $R/pixal_mv $VIEWS | while read -r ss M; do                     # still missing (out of memory at 1536)
  step "pixal_mv 1024 seeds $ss: $M"
  /content/genv/bin/python $G/gen_pixal_mv.py --out $R/pixal_mv_1024 --res 1024 --seeds $ss $M >> $R/pixal_mv_1024.log 2>&1 < /dev/null
done
step "pixal_mv done: $(grep -c '"ok": true' $R/pixal_mv/gen_log.jsonl 2> /dev/null) ok at 1536, $(grep -c '"ok": true' $R/pixal_mv_1024/gen_log.jsonl 2> /dev/null) at 1024"
groups $R/trellis2 $ALL | while read -r ss M; do
  step "trellis2 1536 seeds $ss: $(echo $M | wc -w) crops"
  /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2 --seeds $ss $M >> $R/trellis2.log 2>&1 < /dev/null
done
groups $R/trellis2 $ALL | while read -r ss M; do                       # still missing (out of memory at 1536)
  step "trellis2 1024 seeds $ss: $M"
  /content/genv/bin/python $G/gen_trellis2.py --out $R/trellis2_1024 --res 1024 --seeds $ss $M >> $R/trellis2_1024.log 2>&1 < /dev/null
done
step "trellis2 done: $(grep -c '"ok": true' $R/trellis2/gen_log.jsonl) ok at 1536, $(grep -c '"ok": true' $R/trellis2_1024/gen_log.jsonl 2> /dev/null) at 1024"
wait
sim3 trellis2 trellis2_1024 hy21 sam3d                                   # fills every gap
cd /content/results && find gen -name '*.ply' | sort | xargs sha256sum > gen/SHA256SUMS
step "SHA256SUMS: $(wc -l < gen/SHA256SUMS) files"
step "R-GEN-DONE"
