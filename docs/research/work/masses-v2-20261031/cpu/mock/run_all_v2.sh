#!/bin/bash
# Masses v2 CPU mock, end to end (2026-10-31): both box job strings of JOBS.txt, the CPU merge + v2 verdict, and the
# failure paths. usage: run_all_v2.sh WORK OUTDIR    (WORK: scratch, wiped; OUTDIR: kept evidence)
#   A, B   the two JOBS.txt strings (MOCK_EFF +0.05 on every episode: synthetic, tests the plumbing to a verdict)
#   merge  mass_verdict.py --rule v2 over the two pushed runs in the fake store (as the CPU merge after both boxes)
#   F      box A again with an injected training failure (ep13 mass1 seed 43) -> box line INCOMPLETE; merge INCOMPLETE
#   R      the INCOMPLETE re-run string (SEEDS=43 MV2_EPS=13 SRC_EP13=<F run>:mck:reuse): pulls F's pushed reference files
#          one by one; merge [F, B, R] -> a verdict; merge [A, B, R] -> REFUSED (the pair exists twice)
#   T      box B on a store whose ep31 reference has one changed value -> ep31 REFUSED, never trained; INCOMPLETE
#   G      guards: v2 with a -mass- run id; the default with a -mv2 id; an episode outside the table; a changed props file
W=$1; O=$2; M=$(cd $(dirname $0) && pwd); R=/home/user/v2d-track3
PY=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python
rm -rf $W; mkdir -p $W $O; MR=$W/box; ST=$W/store
TAB=docs/research/work/masses-v2-20261031/refs_v2.json
JA="MV2_TAB=$TAB MV2_EPS=\"24 13\" bash ops/jobs/mass_check.sh"; JB="MV2_TAB=$TAB MV2_EPS=\"11 31\" bash ops/jobs/mass_check.sh"
export MOCK_EFF='{"24": 0.05, "11": 0.05, "13": 0.05, "31": 0.05}'
save() {  # $1 name
  mkdir -p $O/$1; cp $MR/content/job.log $MR/hf.log $MR/rc.txt $O/$1/ 2> /dev/null
  cp $MR/content/results/mass_check/{summary.json,verify.json,verdict.txt,stored_refs_v2.txt,stored_refs.txt} $O/$1/ 2> /dev/null
  sed -i "s#$MR#MR#g; s#$W#WORK#g" $O/$1/job.log $O/$1/hf.log 2> /dev/null; true
}
box() {  # $1 name, $2 run id, $3 job, $4 "eps", [$5 check args...]
  local n=$1 rid=$2 job=$3 eps=$4; shift 4
  bash $M/setup_v2.sh $MR $ST > /dev/null
  RUN_ID=$rid bash $M/run_mock.sh $MR "$job"
  $PY -I $M/check_v2.py $MR $ST "$eps" $rid $O/check_$n.json "$@" | sed "s/^/$n: /"; echo "$n $(cat $MR/rc.txt) box line: $(cut -c1-260 $MR/content/results/mass_check/verdict.txt)"
  save $n
}
merge() {  # $1 name, $2.. run ids
  local n=$1; shift; local roots="" vfs="" mans=""
  for r in "$@"; do roots="$roots $ST/runs/$r"; vfs="$vfs $ST/runs/$r/results/mass_check/verify.json"; mans="$mans $(ls $ST/runs/$r/results/mass_check/arms_ep*.json | tr '\n' ' ')"; done
  $PY -I $R/tools/mass_verdict.py --rule v2 --eps "24 11 13 31" --seeds "42 43" --control mass0 --treatment mass1 \
    --content "${roots# }" --verify "${vfs# }" --manifests "$mans" --out $O/merge_$n.json > $O/merge_$n.txt 2>&1; echo "rc=$?" >> $O/merge_$n.txt
  sed -i "s#$ST#STORE#g" $O/merge_$n.txt; [ -f $O/merge_$n.json ] && sed -i "s#$ST#STORE#g; s#$W#WORK#g" $O/merge_$n.json
  echo "merge $n: $(head -c 400 $O/merge_$n.txt | tr '\n' ' ')"
}
box A 20261031-mv2a-mocksha "$JA" "24 13"
box B 20261031-mv2b-mocksha "$JB" "11 31"
merge AB 20261031-mv2a-mocksha 20261031-mv2b-mocksha
MOCK_TRAIN_FAIL='mass1s43_glock/ep13' box F 20261031-mv2f-mocksha "$JA" "24 13" --expect_missing ep13/mass1/s43
merge FB 20261031-mv2f-mocksha 20261031-mv2b-mocksha
box R 20261031-mv2r-mocksha "SEEDS=43 SRC_EP13=20261031-mv2f-mocksha:mck:reuse MV2_TAB=$TAB MV2_EPS=13 bash ops/jobs/mass_check.sh" "13" \
  --seeds 43 --src "13=20261031-mv2f-mocksha"
merge FBR 20261031-mv2f-mocksha 20261031-mv2b-mocksha 20261031-mv2r-mocksha
merge ABR_ambiguous 20261031-mv2a-mocksha 20261031-mv2b-mocksha 20261031-mv2r-mocksha
# T: tampered ep31 reference (one value of one column changed, schema and asset paths kept)
rm -rf $W/storeT; cp -r $ST $W/storeT
$PY -I - $W/storeT << 'PYEOF'
import glob, sys, pyarrow as pa, pyarrow.parquet as pq
f = glob.glob(f'{sys.argv[1]}/runs/20261024-ev30rp-07eef1a/refs/glockt/ep31/processed/*/*/ref_gl_ilc.parquet')[0]
t = pq.read_table(f); c = 'robot_left_wrist_position'; v = t.column(c)[0].as_py()
if isinstance(v[0], list): v[0][0] += 0.001
else: v[0] += 0.001
pq.write_table(t.set_column(t.column_names.index(c), c, pa.array([v], type=t.schema.field(c).type)), f); print('tampered', f.split('/runs/')[1])
PYEOF
bash $M/setup_v2.sh $MR $W/storeT > /dev/null; RUN_ID=20261031-mv2t-mocksha bash $M/run_mock.sh $MR "$JB"; save T
echo "T $(cat $MR/rc.txt): $(grep -c '"steps"' $MR/train_audit.log 2> /dev/null) trainings; $(grep -o 'mass_check v2 ep31: REFUSED[^;]*' $MR/content/job.log | head -1); box line: $(cut -c1-200 $MR/content/results/mass_check/verdict.txt)"
# G: guards (each exits before pulling anything)
for g in "mv2bad 20261031-mass-mocksha $JA" "dflt 20261031-mv2a-mocksha bash ops/jobs/mass_check.sh" \
         "ep2 20261031-mv2a-mocksha MV2_TAB=$TAB MV2_EPS=2 bash ops/jobs/mass_check.sh" "props 20261031-mv2a-mocksha PROPS_CHANGED $JA"; do
  set -- $g; n=$1; rid=$2; shift 2; job="$*"
  bash $M/setup_v2.sh $MR $ST > /dev/null
  if [ "$1" = PROPS_CHANGED ]; then shift; job="$*"; sed -i 's/"mass_kg": 0.1389/"mass_kg": 0.139/' $MR/content/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json; fi
  RUN_ID=$rid bash $M/run_mock.sh $MR "$job"
  echo "G_$n $(cat $MR/rc.txt): $(grep -v '^\s*$' $MR/content/job.log | grep -v 'Activated' | head -2 | sed "s#$MR#MR#g" | cut -c1-200 | tr '\n' ' ') downloads $(grep -c '^hf download' $MR/hf.log 2> /dev/null)"
done
