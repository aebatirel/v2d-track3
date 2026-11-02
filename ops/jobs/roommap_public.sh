#!/bin/bash
# Public leave-out validation (PREREG docs/analysis/roommap-20261102/PREREG.md): 5 fold maps, fold k = PUBLIC[k::5]
# excluded from map k; each public episode relocalised only against the map that excludes it. Reads no GT.
# Usage: T3=... bash ops/jobs/roommap_public.sh WORK [THREADS]
set -u
WORK=$1; TH=${2:-4}; T3=${T3:-/content/t3}; HERE=$(cd "$(dirname "$0")/../.." && pwd)
FOLDS=("0 18 26 41" "2 21 27 42" "11 22 31 43" "12 23 39 44" "13 24 40 45")
for k in 0 1 2 3 4; do
  ex=$(echo ${FOLDS[$k]} | tr ' ' ',')
  [ -s $WORK/maps/fold$k/bank.npz ] || python3 $HERE/pipeline/roommap.py map --t3 $T3 --work $WORK --name fold$k \
      --exclude $ex --threads $TH > $WORK/map_fold$k.log 2>&1
  echo "fold$k map: $(cat $WORK/maps/fold$k/summary.json | tr -d '\n ')"
done
for k in 0 1 2 3 4; do
  T3=$T3 bash $HERE/ops/jobs/roommap_reloc.sh $WORK fold$k public $WORK/reloc/public_lo $TH ${FOLDS[$k]}
done
echo PUBLIC-DONE
