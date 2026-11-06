#!/bin/bash
# Job-string replay (2026-10-31): Phase 1's three EXACT job strings (parsed from leak-decomp-20261030/phase1/JOBS.txt),
# run through the Phase-1 CPU mock once on the code BEFORE this change (HEAD snapshot) and once AFTER it (working
# tree), same mock path MR, LIB_EP_DIR unset (as in Phase 1). Every pushed / written file, job.log, the perc2 audit
# (what each perc2 run saw: MESH_DIR, templates, KF_MIN, SPLIT, HF_HUB_OFFLINE, depth cache) and the store traffic
# are snapshotted (snap.py: wall-clock and inode values blanked) and diffed. Expected: 0 differences on all 3 boxes.
# usage: replay.sh MR BEFORE_SRC AFTER_SRC OUTDIR
set -u
MR=$1; BEF=$2; AFT=$3; O=$4; M=$(cd "$(dirname "$0")" && pwd)
PY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python
P1=/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/phase1
mkdir -p $O; rc_all=0
sed -n "s/^ops\/vast.sh .* create <offer> <date>-orcP1\(.\)-\$S7 '\(.*\)'$/\1|\2/p" $P1/JOBS.txt > $O/jobs_parsed.txt
[ $(wc -l < $O/jobs_parsed.txt) = 3 ] || { echo "replay: expected 3 job strings in $P1/JOBS.txt"; exit 1; }
for side in before after; do
  src=$BEF; [ $side = after ] && src=$AFT
  bash $M/setup_rtk.sh $MR $src p1 > /dev/null
  while IFS='|' read -r k job; do
    bash $P1/mock/run_mock.sh $MR 20261030-orcP1$k-mocksha "$job" < /dev/null
    $PY -I $M/snap.py snap $MR $O/${side}_box$k.json > /dev/null
    echo "$side box $k: job rc $(cat $MR/rc.txt), perc2 runs $(wc -l < $MR/perc2_audit.log), downloads $(grep -c '"kind": "file"' $MR/hf.log), $(tail -1 $MR/push.out)"
  done < $O/jobs_parsed.txt
done
for k in a b c; do $PY -I $M/snap.py diff $O/before_box$k.json $O/after_box$k.json || rc_all=1; done
echo "replay: $([ $rc_all = 0 ] && echo 'IDENTICAL on all 3 Phase-1 job strings' || echo 'DIFFERENCES FOUND')"
exit $rc_all
