#!/bin/bash
# Writes the four test-A job strings (one file per box) from the pairs and the reference sha256s.
# Usage: make_jobs.sh OUT_DIR
O=$1; mkdir -p $O
declare -A SHA=(
 [12]=86316dcedab00803ab79347e63dd71982c60ca5c606f3790ebcbb19e0ff24955 [31]=4eded4a37ad70bbe8379c854fac37464c05109f038fb32322ea0bed357f606a6
 [40]=26b969a60c506fefe076b1a3ce1a3b628f2da0297b5b0c0b6e372c974752c121 [21]=1af78da9de49b4cd9ab8d6e4c3c9e4991c7298d67fdf42206074dd529f14ab6d
 [23]=4ad4020ceabd333a21988693a9bc90074c7714ce25bcc9913174c1f86e4f98d2 [2]=a35dc7069a6a2980acacd106a2c42f32054fdd21502c2390db8b0fec00494d4f
 [18]=477cefec725393793ac7479b7935df4bc29d1a33fbe2ba955540277b1409ba8b [24]=a13533659dcecf49a17a1961e68bf9251651d735524bbdcf4452f19bfb3efae0)
k=0
for pair in "12 31" "40 21" "23 2" "18 24"; do
  k=$((k + 1)); set -- $pair; a=$1; b=$2
  cat > $O/gA$k.job << JOB
# test A box gA$k: public ep$a then ep$b (training order). Plan: docs/work-log.md 2026-11-13 ~02:30 and ~03:00 UTC.
R=20261020-refsweep-ea14fdf
for i in 1 2 3; do
  PULL_SUB="perc2/ep$a refs/perc2/ep$a perc2/ep$b refs/perc2/ep$b" bash ops/box/store.sh pull-run \$R >> /content/prepull.log 2>&1 && break
  echo "[\$(date -u +%FT%TZ)] test A: pull of \$R failed (try \$i)" >> /content/job.log; sleep 120
done
for x in $a:${SHA[$a]} $b:${SHA[$b]}; do
  e=\${x%%:*}; f=\$(ls /content/refs/perc2/ep\$e/processed/*/*/*.parquet 2> /dev/null | head -1)
  [ -n "\$f" ] && [ "\$(sha256sum < \$f | cut -c1-64)" = "\${x#*:}" ] && [ -s /content/perc2/ep\$e/poses.npz ] \\
    || { echo "[\$(date -u +%FT%TZ)] test A: ep\$e reference or perception missing, or reference sha256 mismatch" >> /content/job.log; exit 1; }
  echo "[\$(date -u +%FT%TZ)] test A: ep\$e reference \$f sha256 OK (the gate's input)" >> /content/job.log
done
. /content/v2d-track3/ops/box/lib.sh
export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="\$FDR_TRAIN_ARGS" \\
  SPLIT=public PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=1 SEED=42 LIB=/content/v2d-track3/meshes/library_v3 \\
  PAIRS="$a:local: $b:local:"
bash ops/jobs/hard_ab.sh
JOB
done
sha256sum $O/*.job
