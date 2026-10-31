#!/bin/bash
# Re-track CPU mock (2026-10-31): ops/jobs/perc_leak.sh in LIB_EP_DIR mode with stub deliveries, the template-dependent
# stub perc2 (stub_rtk.py) and Phase 1's stub hf / run_mock.sh; everything else is the real code of the working tree.
# usage: run_rtk.sh MR FIXTURES OUT     (FIXTURES = make_fixtures.py output with VALIDATION.json in v3copy/, partial/)
#   ref       LIB_EP_DIR unset, ARMS=o, all 20 episodes, an -orc run id: the P_o tracks every scenario is compared with
#   box A/B   the EXACT JOBS.txt strings (parsed), LIB_EP_DIR swapped to the v3copy stub (library_v3 byte copies for
#             every object): must reproduce P_o exactly (check_rtk.py)
#   partial   E0-like scope (pot, lid, rack, blue cup), ep2 white_pot and ep13 rack moved: sources per object, only
#             those two tracks differ from P_o; plus ARMS=o,o2 REPEAT=2 (o2 uses the same template folder)
#   refusals  rtk run id without LIB_EP_DIR; rtk id with arm s; non-hex rtk id; LIB_EP_DIR missing; a delivery
#             without VALIDATION.json; a mesh changed after validation; an unlisted mesh added after validation;
#             (all rc 1, no download, no perc2); an -orc run id with LIB_EP_DIR (allowed, rc 0)
set -u
MR=$1; FX=$2; O=$3; M=$(cd "$(dirname "$0")" && pwd); REPO=/home/user/v2d-track3
PY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python
P1M=$REPO/docs/research/work/leak-decomp-20261030/phase1/mock; RM="bash $P1M/run_mock.sh"
mkdir -p $O; REF=$(dirname $MR)/rtk_ref; L='LIB=/content/v2d-track3/meshes/library_v3'
bash $M/setup_rtk.sh $MR $REPO rtk $FX > /dev/null
DV=$MR/content/v2d-track3/meshes                                          # deliveries as the job sees them
cp -r $DV/rtk_partial $DV/rtk_tamper; printf 'x' >> $DV/rtk_tamper/ep2/white_pot_lid.glb
cp -r $DV/rtk_partial $DV/rtk_extra; cp $DV/library_v3/mini_sweeper.glb $DV/rtk_extra/ep18/ 2> /dev/null \
  || { mkdir -p $DV/rtk_extra/ep18; cp $DV/library_v3/mini_sweeper.glb $DV/rtk_extra/ep18/; }
ALL=$(awk -F'\t' 'NR > 1 {printf "%s ", $1}' $REPO/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv)
line() { echo "$1: rc $(cat $MR/rc.txt), perc2 runs $(cat $MR/perc2_audit.log 2> /dev/null | wc -l), downloads $(grep -c '"kind": "file"' $MR/hf.log 2> /dev/null): $(grep -a 'perc_leak' $MR/content/job.log | tail -1 | cut -c23-220 | sed "s#$MR#<MR>#g")"; }

# ref: P_o (LIB_EP_DIR unset)
$RM $MR 20261031-orcRref-mocksha "EPS=\"$ALL\" ARMS=o $L bash ops/jobs/perc_leak.sh" < /dev/null
rm -rf $REF; mkdir -p $REF; for e in $ALL; do mkdir -p $REF/ep$e; cp -r $MR/content/results/leak_p1/ep$e/perc2 $REF/ep$e/; done
line "ref (unset, ARMS=o, 20 episodes)" > $O/rtk_ref.txt
# box A / B: the JOBS.txt strings, delivery -> the v3copy stub
sed -n "s/^ops\/vast.sh .* create <offer \(.\)> \$D-rtk.-\$S7 '\(.*\)'$/\1|\2/p" $M/../JOBS.txt > $O/rtk_jobs_parsed.txt
[ $(wc -l < $O/rtk_jobs_parsed.txt) = 2 ] || { echo "run_rtk: expected 2 box strings in JOBS.txt"; exit 1; }
while IFS='|' read -r k job; do
  job=${job//meshes\/rtk_e0b_public/meshes\/rtk_v3copy}; rid=20261031-rtk$k-abc1234
  eps=$(echo "$job" | sed 's/.*EPS="\([^"]*\)".*/\1/')
  $RM $MR $rid "$job" < /dev/null
  { echo "MOCK (stub perc2 whose track depends on the template bytes, stub hf); job string = JOBS.txt box $k with"
    echo "LIB_EP_DIR=meshes/rtk_v3copy (library_v3 byte copies for every object): must reproduce P_o exactly"
    echo "== $job  (run id $rid)"
    $PY -I $M/check_rtk.py $MR $rid "$eps" $DV/rtk_v3copy $REF; echo "check rc=$?"
    echo "-- job.log"; sed "s#$MR#<MR>#g" $MR/content/job.log | cut -c1-240; echo "-- push"; cat $MR/push.out; } > $O/rtk_box$k.txt 2>&1
done < $O/rtk_jobs_parsed.txt
# partial delivery
$RM $MR 20261031-rtkP-abc1234 "EPS=\"2 11 13 18\" ARMS=o $L LIB_EP_DIR=meshes/rtk_partial bash ops/jobs/perc_leak.sh" < /dev/null
{ echo "== partial: EPS=\"2 11 13 18\" ARMS=o LIB_EP_DIR=meshes/rtk_partial (E0-like scope; ep2 white_pot and ep13 rack moved)"
  $PY -I $M/check_rtk.py $MR 20261031-rtkP-abc1234 "2 11 13 18" $DV/rtk_partial $REF; echo "check rc=$?"
  echo "-- job.log (LIB_EP_DIR, bundle, RESULT lines)"; grep -a 'LIB_EP_DIR\|verify\|bundle\|RESULT\|guard' $MR/content/job.log | sed "s#$MR#<MR>#g" | cut -c1-240
  echo "-- ep2 bundle templates (perc2):"; $PY -I -c "import json; b = json.load(open('$MR/content/results/leak_p1/ep2/bundle.json'))
for n, t in b['arms']['perc2']['templates'].items(): print(' ', n, t['source'], t['md5'], t['real'].replace('$MR', '<MR>'))
print('  template_sources', b['template_sources'])"; } > $O/rtk_partial.txt 2>&1
$RM $MR 20261031-rtkQ-abc1234 "EPS=\"2 18\" REPEAT=\"2\" ARMS=o,o2 $L LIB_EP_DIR=meshes/rtk_partial bash ops/jobs/perc_leak.sh" < /dev/null
{ echo; echo "== partial with the repeat arm: EPS=\"2 18\" REPEAT=\"2\" ARMS=o,o2"
  $PY -I $M/check_rtk.py $MR 20261031-rtkQ-abc1234 "2 18" $DV/rtk_partial $REF o,o2 2; echo "check rc=$?"; } >> $O/rtk_partial.txt 2>&1
# refusals (rc 1, no work) and the one allowed variant
{ for c in "20261031-rtkA-abc1234|EPS=\"2\" ARMS=o $L bash ops/jobs/perc_leak.sh|rtk run id, LIB_EP_DIR unset" \
           "20261031-rtkA-abc1234|EPS=\"2\" ARMS=o,s $L LIB_EP_DIR=meshes/rtk_v3copy bash ops/jobs/perc_leak.sh|rtk run id with arm s" \
           "20261031-rtkA-mocksha|EPS=\"2\" ARMS=o $L LIB_EP_DIR=meshes/rtk_v3copy bash ops/jobs/perc_leak.sh|rtk run id with a non-hex sha" \
           "20261031-rtkA-abc1234|EPS=\"2\" ARMS=o $L LIB_EP_DIR=meshes/rtk_nonexistent bash ops/jobs/perc_leak.sh|LIB_EP_DIR missing" \
           "20261031-rtkA-abc1234|EPS=\"2\" ARMS=o $L LIB_EP_DIR=meshes/rtk_bad_name bash ops/jobs/perc_leak.sh|delivery without VALIDATION.json" \
           "20261031-rtkA-abc1234|EPS=\"2\" ARMS=o $L LIB_EP_DIR=meshes/rtk_tamper bash ops/jobs/perc_leak.sh|a mesh changed after validation" \
           "20261031-rtkA-abc1234|EPS=\"18\" ARMS=o $L LIB_EP_DIR=meshes/rtk_extra bash ops/jobs/perc_leak.sh|an unlisted mesh added after validation" \
           "20261031-orcRx-mocksha|EPS=\"2\" ARMS=o $L LIB_EP_DIR=meshes/rtk_v3copy bash ops/jobs/perc_leak.sh|-orc run id with LIB_EP_DIR (allowed)"; do
    IFS='|' read -r rid job what <<< "$c"
    $RM $MR $rid "$job" < /dev/null; line "$what [$rid]"
    grep -a 'rtk_mesh_check verify' -A3 $MR/content/job.log | grep -v '^\[' | sed "s#$MR#<MR>#g" | cut -c1-200 | sed 's/^/    /'
  done; } > $O/rtk_refusals.txt 2>&1
grep -h 'RESULT\|check rc\|tracks vs P_o' $O/rtk_box?.txt $O/rtk_partial.txt; cat $O/rtk_ref.txt $O/rtk_refusals.txt
