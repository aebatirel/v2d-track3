#!/bin/sh
# usage: sh c1_batch.sh <stride> <prefix> <pubonly 0/1> <eps...>; 3 parallel workers; logs in c1log/
S=$1; P=$2; PO=$3; shift 3
cd /Users/aebatirel/Documents/Code/v2d-research/work/18
for e in "$@"; do echo $e; done | xargs -P 3 -I{} sh -c "C1_PUBONLY=$PO perl -e 'alarm 2400; exec @ARGV' venv18/bin/python c1_reloc.py run1/sparse/0 evaluation {} c1/${P}_e{}.json 0 $S > c1log/${P}_e{}.log 2>&1"
echo BATCH_DONE $P
