#!/bin/bash
# Eval depth audit for one episode: fetch the eval depth cache (single file), run pipeline/depth_audit.py in
# perception mode (feeding perception) and reference mode (pack-7 policy reference), delete the cache.
# Usage: bash run_depth.sh EP   (env: S scratch root, R repo)
set -u
e=$1; D=$R/docs/analysis/evalgross-20261031; W=$S/eg
line=$(grep "\"ep\": $e," $W/fetch_small.log)
get() { python3 -c "import json,sys; print(json.loads(sys.argv[1])[sys.argv[2]])" "$line" "$1"; }
P=$(get poses); REF=$(get ref); TAB=$(get table); H=$(get hands)
LIB=$R/meshes/library_v3; [ "$e" = 8 ] && LIB=$R/meshes/library_v3x
mkdir -p $W/dldepth_ep$e $W/depth
python3 -I $D/fetch.py $W/dldepth_ep$e depth $e > $W/depth/fetch_ep$e.log 2>&1
DEP=$W/dldepth_ep$e/cache/depth/eval/ep$e/depths_fs0.5.npy
if [ ! -s $DEP ]; then echo "ep$e: depth missing" >> $W/depth/errors.log; exit 0; fi
OMP_NUM_THREADS=2 python3 -I $R/pipeline/depth_audit.py --poses $P --depth $DEP --hands $H --meshes $LIB \
  --out $W/depth/perc/ep$e --pylib $W/pylib --no_rest --force > $W/depth/perc_ep$e.log 2>&1
OMP_NUM_THREADS=2 python3 -I $R/pipeline/depth_audit.py --poses $P --ref $REF --table $TAB --depth $DEP --hands $H \
  --meshes $LIB --out $W/depth/ref/ep$e --pylib $W/pylib --no_rest --force > $W/depth/ref_ep$e.log 2>&1
rm -rf $W/dldepth_ep$e
echo "ep$e done $(date -u +%H:%M:%S)" >> $W/depth/done.log
