#!/bin/bash
# Pack 9b D arm, after the confirmation box (JOBS.txt section "After C"). CPU only. Run from the repo root.
set -euo pipefail
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad
DL=$S/d9b_dl; W=$S/d9b_work; RC=20261101-drC-a1a7e25
PY=$S/map/scoring/venv/bin/python; KIT=$S/map/scoring/kit/v2d_submission_kit
. ops/config.env
mkdir -p $W
# 1. downloads: one hf_hub_download per file, no listing
L=$W/c_files.txt; : > $L
for N in 14 16 25 30 33; do E6=$(printf %06d $N)
  for i in $(seq 1 10); do echo "runs/$RC/results/h5/r$i/ep$N/episode_$E6.parquet" >> $L; echo "runs/$RC/results/h5/r$i/ep$N/episode_$E6.json" >> $L; done
done
for f in results/final_eval/dr_pack_check.json results/h5/dr_pack_check.json results/h5/h5_summary.json run_job.log job.log; do echo "runs/$RC/$f" >> $L; done
python3 -I - "$HF_STORE" "$DL" "$L" <<'PY'
import sys, time
from huggingface_hub import hf_hub_download
store, dl, lst = sys.argv[1:4]; ok = bad = 0
for p in [l.strip() for l in open(lst) if l.strip()]:
    for t in range(5):
        try:
            hf_hub_download(store, p, repo_type='dataset', local_dir=dl, force_download=True); ok += 1; break
        except Exception as e:
            if t == 4: print('MISSING', p, type(e).__name__); bad += 1
            time.sleep(5)
print('downloaded', ok, 'missing', bad)
PY
# 2. P per episode (packed_refs.json source_run + reference)
declare -A P=(
 [14]=runs/20261025-evb1420-ee7ba8e/refs/glockt/ep14/processed/sequence_id=t3_ep014/robot_name=sharpa_wave/ref_gl_ilc.parquet
 [16]=runs/20261024-pack-31ef267/refs/glockt/ep16/processed/sequence_id=t3_ep016/robot_name=sharpa_wave/ref_gl_ilc.parquet
 [25]=runs/20261026-c25s42-feb0407/refs/perc2mcks/ep25/processed/sequence_id=t3_ep025/robot_name=sharpa_wave/2057d9f10b3a421ebbfd847c1219d1a0-0.parquet
 [30]=runs/20261025-std30-ee7ba8e/refs/perc2mcks/ep30/processed/sequence_id=t3_ep030/robot_name=sharpa_wave/a2eb7d276dd84fe6bed9251b46e93770-0.parquet
 [33]=runs/20261026-fr3233s43-6a8a0e2/refs/glockt/ep33/processed/sequence_id=t3_ep033/robot_name=sharpa_wave/ref_gl_ilc.parquet )
declare -A OLD=(
 [14]=runs/20261026-pack6-5203d42/results/submission/results/episode_000014.parquet
 [16]=runs/20261026-pack6-5203d42/results/submission/results/episode_000016.parquet
 [25]=runs/20261026-pack6-5203d42/results/submission/results/episode_000025.parquet
 [30]=runs/20261026-pack6-5203d42/results/submission/results/episode_000030.parquet
 [33]=runs/20261030-c33B-0202139/results/submission/results/episode_000033.parquet )
# 3. score
SC=()
for N in 14 16 25 30 33; do E6=$(printf %06d $N)
  SPLIT=eval OMP_NUM_THREADS=1 $PY -I tools/dr_score.py --kit $KIT --lib meshes/library_v3 --ep $N --ref P=$DL/${P[$N]} \
    --out $W/score_ep$N.json --set "conf:P:$DL/runs/$RC/results/h5/r*/ep$N/episode_$E6.parquet" \
    --set "packed:P:$DL/runs/20261031-h5p7-1a7cdff/results/h5/r*/ep$N/episode_$E6.parquet" --set "old:P:$DL/${OLD[$N]}" --jobs 8 \
    2>&1 | tail -3
  SC+=(--score $W/score_ep$N.json)
done
# 4. verdict
$PY -I tools/dr_verdict.py --merge $W/c_merge.json \
  --table docs/research/work/masses-eval-20261031/packed_refs.json "${SC[@]}" \
  --pack-check $DL/runs/$RC/results/final_eval/dr_pack_check.json --pack-check $DL/runs/$RC/results/h5/dr_pack_check.json \
  --out $W/verdict.json | tee $W/verdict.txt
