#!/bin/sh
# DIG 18 C13: default module end to end = public-only map run3, stride 5, all 20 eval clips; 3 parallel workers. Reads no GT.
# usage: sh c13_batch.sh <model dir> <stride> <prefix> <eps...>
M=$1; S=$2; P=$3; shift 3
cd /Users/aebatirel/Documents/Code/v2d-research/work/18
for e in "$@"; do echo $e; done | xargs -P 3 -I{} sh -c "OMP_NUM_THREADS=2 perl -e 'alarm 2400; exec @ARGV' venv18/bin/python c1_reloc.py $M evaluation {} c1/${P}_e{}.json 0 $S > c1log/${P}_e{}.log 2>&1"
echo BATCH_DONE $P
