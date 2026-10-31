#!/bin/bash
# Pull the per-draw rollouts of the oracle-twin run (public ep11/13/31, arms P = glock_public, O = oracle_glock_public,
# 10 official draws each) from the HF store into $1. Read-only; the session proxy authenticates huggingface.co.
OUT=${1:?out dir}; R=https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/runs/20261030-orcB-38234d1/results
for arm in glock_public oracle_glock_public; do for e in 11 13 31; do for i in $(seq 1 10); do
  d=$OUT/$arm/ep$e/r$i; mkdir -p $d
  for f in episode_0000$e.parquet qa_policy.json; do
    curl -sS -fL -o $d/$f "$R/$arm/ep$e/best/r$i/$f" -H "Authorization: Bearer dummy" || echo "miss $d/$f"
  done
done; done; done
