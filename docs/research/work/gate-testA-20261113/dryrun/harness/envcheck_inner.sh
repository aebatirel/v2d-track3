#!/bin/bash
# DRY RUN ONLY, inside the sandbox: patched FlashCHORD (the same three patch scripts hard_ab.sh runs) + the 8 test-A
# references (local copies, sha256 = store) + the kit assets at /content/t3; then cpu_env_check.py per episode.
set -u
GA=$1; OUT=$GA/out/envcheck; export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root
FCSRC=$(dirname $GA)/wgate/fc/v2d; WS=$(dirname $GA)/wgate/store/runs/20261020-refsweep-ea14fdf/refs/perc2
mkdir -p /workspace $OUT && ln -s /workspace /content && ln -sfn $FCSRC /workspace/v2d && ln -sfn $GA/hfds /workspace/hfds
mkdir -p /venv && ln -sfn $GA/venv_main /venv/main; . /venv/main/bin/activate
mv $GA/venv_main/bin/hf $GA/venv_main/bin/hf.real 2>/dev/null; install -m 755 $GA/dry/fakes/hf $GA/venv_main/bin/hf; mkdir -p /dryrun
REPO_DIR=/home/user/v2d-track3 bash /home/user/v2d-track3/pipeline/fetch_data.sh > $OUT/fetch_data.log 2>&1
FC=/content/v2d/robotic_grounding/flash_chord
for p in patch_flashchord.py patch_flashchord_fdr.py patch_flashchord_voc.py; do python /home/user/v2d-track3/ops/box/$p $FC >> $OUT/patches.log 2>&1 || echo "PATCH FAIL $p" >> $OUT/patches.log; done
cd $FC
for e in 12 31 40 21 23 2 18 24; do
  mkdir -p /content/refs/perc2s && cp -r $WS/ep$e /content/refs/perc2s/ep$e
  f=$(ls /content/refs/perc2s/ep$e/processed/*/*/*.parquet)
  ( FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 OMP_NUM_THREADS=1 \
      timeout 1800 .venv/bin/python -B $GA/dry/cpu_env_check.py $f 5 $OUT/env_ep$e.json > $OUT/env_ep$e.log 2>&1; echo "ep$e rc=$?" >> $OUT/rc.txt ) &
  [ $(jobs -r | wc -l) -ge 3 ] && wait -n
done
wait
echo ENVCHECK-COMPLETE
