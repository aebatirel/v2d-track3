#!/bin/bash
# Pull ep2's per-draw rollouts of the masses-check run (20261031-mass-2ed46ea; arms mass0 = 0.3 kg placeholders,
# mass1 = estimated masses pot 0.2771 kg / lid 0.0882 kg; seeds 42 / 43; 10 official draws each) into $1. Read-only.
OUT=${1:?out dir}; R=https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/runs/20261031-mass-2ed46ea/results
for arm in mass0s42_glock_public mass0s43_glock_public mass1s42_glock_public mass1s43_glock_public; do for i in $(seq 1 10); do
  d=$OUT/$arm/ep2/r$i; mkdir -p $d
  for f in episode_000002.parquet qa_policy.json; do
    curl -sS -fL -o $d/$f "$R/$arm/ep2/best/r$i/$f" -H "Authorization: Bearer dummy" || echo "miss $d/$f"
  done
done; done
# then: python drawdiv.py $OUT mass0s42_glock_public 2 mass0s43_glock_public 2 mass1s42_glock_public 2 mass1s43_glock_public 2
