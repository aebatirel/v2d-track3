#!/bin/bash
# Relocalise episodes against a room map, P single-threaded workers (pipeline/roommap.py reloc; reads no GT).
# Usage: bash ops/jobs/roommap_reloc.sh WORK MAP SPLIT OUTDIR P EP [EP...]
set -u
WORK=$1; MAP=$2; SPLIT=$3; OUT=$4; P=$5; shift 5
T3=${T3:-/content/t3}; HERE=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p $OUT
printf '%s\n' "$@" | OMP_NUM_THREADS=1 xargs -P $P -I{} sh -c \
  "[ -s $OUT/ep{}.npz ] || python3 $HERE/pipeline/roommap.py reloc --t3 $T3 --work $WORK --name $MAP --split $SPLIT --ep {} --out $OUT/ep{}.npz > $OUT/ep{}.log 2>&1"
echo ALL-DONE
