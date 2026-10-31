#!/bin/bash
# End-to-end CPU mock of the pack 9b D arm (2026-10-31): the JOBS.txt job strings, in launch order, each on a fresh box
# sharing one fake store (setup.sh, run_box.sh; masses-eval mock pattern), then the CPU merge, the confirmation box, the
# CPU scoring + verdict, and the checks. usage: run_all.sh MS OUT_DIR
#   G     ARM=dr MODE=glock EPS="14 16 33" SEEDS="42 43"     (grasp lock, waves of TRAIN_SLOTS 2 per seed)
#   S25a  ARM=dr MODE=std EPS="25" SEEDS="42"   S25b  ... SEEDS="43"   (ev25 pieces in /content/assets)
#   S30a  ARM=dr MODE=std EPS="30" SEEDS="42"   S30b  ... SEEDS="43"
#   merge tools/dr_eval_merge.py over the five pushed results/dr_eval/summary.json (rule 2 across S25a/b, S30a/b)
#   C     the merge's ops/jobs/h5_reeval.sh job string, N=10 as on the real box (KEEP_RESULTS = pack 7's sources, DR_EPS)
#   score tools/dr_score.py per episode: conf = C's results/h5/r*/ep<N>, packed = the store's H5p7 set, old = pack 6 / c33B
#   verdict tools/dr_verdict.py (merge, mock table, scores, C's two dr_pack_check files)
# then check_train.py and check_pack.py. Mock scores are synthetic: the mock tests the plumbing, not D.
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); mkdir -p $OUT; R=/home/user/v2d-track3
bash $M/setup.sh $MS > $OUT/mock_setup.txt 2>&1 || { cat $OUT/mock_setup.txt; exit 1; }
bash $M/run_box.sh $MS G 20261101-drG-mocksha 'ARM=dr MODE=glock EPS="14 16 33" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S25a 20261101-drS25s42-mocksha 'ARM=dr MODE=std EPS="25" SEEDS="42" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S25b 20261101-drS25s43-mocksha 'ARM=dr MODE=std EPS="25" SEEDS="43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S30a 20261101-drS30s42-mocksha 'ARM=dr MODE=std EPS="30" SEEDS="42" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S30b 20261101-drS30s43-mocksha 'ARM=dr MODE=std EPS="30" SEEDS="43" bash ops/jobs/mass_eval.sh'
P=$(. $MS/tmpl/env.sh; echo $MOCK_PY); mkdir -p $MS/merge
for r in drG drS25s42 drS25s43 drS30s42 drS30s43; do
  sed "s#$MS/box/content#/content#g" $MS/store/runs/20261101-$r-mocksha/results/dr_eval/summary.json > $MS/merge/$r.json
done
$P -I $R/tools/dr_eval_merge.py --table $R/docs/research/work/masses-eval-20261031/packed_refs.json --out $OUT/mock_merge.json \
  $MS/merge/{drG,drS25s42,drS25s43,drS30s42,drS30s43}.json > $OUT/mock_merge.txt
CONF=$(sed -n 's/^JOB: //p' $OUT/mock_merge.txt)
echo "$CONF" > $OUT/mock_confirmation_job.txt
bash $M/run_box.sh $MS C 20261101-drC-mocksha "$CONF"
mv $MS/box $MS/done_C
# CPU scoring + verdict, as JOBS.txt "After the confirmation box" (here on the mock store / the C box's files)
KIT=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/kit/v2d_submission_kit
TABM=$MS/tmpl/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json
SC=""
for e in 14 16 25 30 33; do
  E6=$(printf %06d $e); src=$($P -I -c "import json, sys; x = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]]; print(x['source_run'] + '/' + x['reference'])" $TABM $e)
  old=20261026-pack6-5203d42; [ $e = 33 ] && old=20261030-c33B-0202139
  ( cd $R && $P -I tools/dr_score.py --kit $KIT --lib meshes/library_v3 --ep $e --ref P=$MS/store/runs/$src --out $OUT/score_ep$e.json \
      --set "conf:P:$MS/done_C/content/results/h5/r*/ep$e/episode_$E6.parquet" \
      --set "packed:P:$MS/store/runs/20261031-h5p7-1a7cdff/results/h5/r*/ep$e/episode_$E6.parquet" \
      --set "old:P:$MS/store/runs/$old/results/submission/results/episode_$E6.parquet" ) > $OUT/score_ep$e.txt 2>&1
  SC="$SC --score $OUT/score_ep$e.json"
done
$P -I $R/tools/dr_verdict.py --merge $OUT/mock_merge.json --table $TABM $SC \
  --pack-check $MS/done_C/content/results/final_eval/dr_pack_check.json --pack-check $MS/done_C/content/results/h5/dr_pack_check.json \
  --out $OUT/mock_verdict.json > $OUT/mock_verdict.txt 2>&1; echo "verdict rc=$?" >> $OUT/mock_verdict.txt
$P -I $M/check_train.py $MS $OUT/mock_check_train.json; $P -I $M/check_pack.py $MS $OUT/mock_check_pack.json $OUT/mock_merge.json $OUT/mock_verdict.json
for b in G S25a S25b S30a S30b C; do sed "s#$MS#MS#g" $MS/done_$b/content/job.log > $OUT/mock_job_$b.log; done
for b in G S25a S25b S30a S30b; do sed "s#$MS#MS#g" $MS/done_$b/content/results/dr_eval/verify.txt > $OUT/mock_verify_$b.txt; done
for b in G S25a; do                                            # one training log each: the D line as the box wrote it
  find $MS/done_$b/content/runs -name train.log | sort | head -1 | xargs grep -h 'v2d FC_DR_RESET' > $OUT/mock_dline_$b.txt
done
