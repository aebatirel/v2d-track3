#!/bin/bash
# placement_carve.py place on one case: run_place.sh TAG HOST GUEST OUTDIR
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve
export FLASH_CHORD_CACHE_DIR=$S/fccache
tag=$1; host=$2; guest=$3; out=$4; shift 4; lt=${LOGTAG:-$tag}
read _ tree assets < <(grep "^$tag " $S/cases.txt)
p=$(find $tree/processed -name "*.parquet" | head -1)
( time $S/fcvenv/bin/python /home/user/v2d-track3/pipeline/placement_carve.py place $assets "$p" --host $host --guest $guest --out $out "$@" ) > $S/blogs/place_$lt.log 2>&1
echo "$tag place exit $? $(grep real $S/blogs/place_$lt.log)"
