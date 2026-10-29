#!/bin/bash
# Batch-2 generative probe: GT-free Sim(3) fits (sim3_fit.py) of the single-image outputs to OUR observed points, on the
# box's CPUs, so ADD and flips can be read for them too. $@ = model folders under /content/results/gen.
# Output: /content/results/gen/<model>_sim3/<tag>_s<seed>.ply and fits.jsonl.
set -u
R=/content/results/gen; G=/content/v2d-track3/docs/research/mesh-2026-10-26/gen; cd /content/gin
[ -d obs_sub ] || { hf download $HF_STORE runs/mesh-20261029-gen-f3fbeb0/inputs/obs_sub.tar --repo-type dataset --local-dir /content/gin > /dev/null 2>&1; tar xf runs/mesh-20261029-gen-f3fbeb0/inputs/obs_sub.tar; }
declare -A EP=([white_pot]=41 [white_pot_lid]=2 [blue_cup]=22 [water_pitcher]=22 [wooden_piece_1]=23 [wooden_piece_2]=23
               [plastic_dish_rack]=26 [mini_sweeper]=31 [mini_dust_pan]=39 [beige_cup]=11)
for m in "$@"; do
  mkdir -p $R/${m}_sim3
  for f in $R/$m/*_s*.ply; do
    b=$(basename $f .ply); obj=${b%_k*}
    [ -s $R/${m}_sim3/$b.ply ] && continue
    echo "$f /content/gin/obs_sub/ep${EP[$obj]}_$obj.npz $R/${m}_sim3/$b.ply"
  done | xargs -P 20 -L 1 sh -c 'OMP_NUM_THREADS=1 /content/genv/bin/python '$G'/sim3_fit.py --obs $1 --out $2 $0' >> $R/${m}_sim3/fits.jsonl 2>> $R/${m}_sim3/errors.log
  echo "$m: $(grep -c . $R/${m}_sim3/fits.jsonl) fits"
done
