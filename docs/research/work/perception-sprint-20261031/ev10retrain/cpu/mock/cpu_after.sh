#!/bin/bash
# The "After the box" CPU completion of JOBS.txt on the 'nopacked' mock (2026-10-31): the box ended INCOMPLETE because the
# H5p7 run was not in the store; now its eval-10 rollouts and the pushed V are taken from the (fake) store, scored with the
# same tool and the verdict is re-applied with both score files (later --score files win a set name).
# usage: cpu_after.sh MR OUTDIR
set -u
MR=$1; O=$2; S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; PY=$S/map/scoring/venv/bin/python
R=/home/user/v2d-track3; ST=$MR/store/runs/20261031-e10v-mocksha; G=$ST/results/ev10_v4p; mkdir -p $O
V=$(ls $ST/refs/perc2e10v_glockt/ep10/processed/*/*/ref_gl_ilc.parquet); P=$G/packed_ref/ref_gl_ilc.parquet
cd /tmp && E10V_SCORE_JOBS=2 $PY -I $R/tools/e10v_score.py --kit $S/map/scoring/kit/v2d_submission_kit --lib $R/meshes/library_v3 \
  --ref V=$V --ref P=$P --out $O/score_packed.json \
  --set packed:P:"$MR/store/runs/20261031-h5p7-1a7cdff/results/h5/r*/ep10/episode_000010.parquet" > $O/score_packed.txt 2>&1
$PY -I $R/tools/e10v_verdict.py --score $G/score.json --score $O/score_packed.json --verify $G/verify.json --choice $G/choice.json \
  --out $O/summary_cpu.json > $O/verdict_cpu.txt 2>&1
sed -i "s#$MR#<MR>#g" $O/*; cut -c1-300 $O/verdict_cpu.txt
