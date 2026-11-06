#!/bin/bash
# End-to-end CPU mock of the masses eval retrain (2026-10-31): the JOBS.txt job strings, in order, each on a fresh box
# sharing one fake store (setup.sh, run_box.sh), then the checks. usage: run_all.sh MS OUT_DIR
#   G1  MODE=glock EPS="20 8"  SEEDS="42 43"   (wave 1; eval 8 on library_v3x)
#   G2  MODE=glock EPS="33 15" SEEDS="42 43"   (wave 1, spoon pilots; eval 33 CURR_SCALE 0.4 through ENV_EP33)
#   G4  MODE=glock EPS="10"    SEEDS="42 43"   (O4 only; the one grasp-lock reference that names /content/assets, ev10;
#       both seeds since review F1: with one seed the merge makes eval 10 INCOMPLETE, so C1 would no longer cover it)
#   S1a / S1b MODE=std EPS="1" SEEDS="42" / "43" (wave 1, two boxes; ev01 pieces + MA_ARGS)
#   G1v MODE=glock EPS="20" SEEDS="42 43"   (review F3: the cheaper G1 without eval 8; an alternative to G1, not merged)
#   C1  ops/jobs/h5_reeval.sh confirmation of every candidate, built from the boxes' pushed summary.json by
#       tools/mass_eval_merge.py (rule 2 across boxes): N=3 draws here (10 on the real box), KEEP_RESULTS = pack 7's sources.
#   rule: tools/mass_eval_rule.py over C1's h5_summary.json + the merge (review F4; N 3 < 8 here, so rule 4 makes every
#       candidate INCOMPLETE: the plumbing; the verdict branches are covered by ../rule_tests/test_rule.py)
# then check_train.py and check_pack.py. Mock scores are synthetic: the mock tests the plumbing, not masses.
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); mkdir -p $OUT
bash $M/setup.sh $MS > $OUT/mock_setup.txt 2>&1 || { cat $OUT/mock_setup.txt; exit 1; }
bash $M/run_box.sh $MS G1 20261101-mevG1-mocksha 'MODE=glock EPS="20 8" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS G2 20261101-mevG2-mocksha 'MODE=glock EPS="33 15" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS G4 20261101-mevG4-mocksha 'MODE=glock EPS="10" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S1a 20261101-mevS1s42-mocksha 'MODE=std EPS="1" SEEDS="42" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S1b 20261101-mevS1s43-mocksha 'MODE=std EPS="1" SEEDS="43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS G1v 20261101-mevG1v20-mocksha 'MODE=glock EPS="20" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
mv $MS/box $MS/done_G1v
# the confirmation job as the orchestrator builds it: tools/mass_eval_merge.py over the boxes' pushed summary.json files
# (rule 2 across S1a / S1b for eval 1), N 3 here; the box paths in the summaries read as /content
P=$(. $MS/tmpl/env.sh; echo $MOCK_PY); mkdir -p $MS/merge
for r in mevG1 mevG2 mevG4 mevS1s42 mevS1s43; do
  sed "s#$MS/box/content#/content#g" $MS/store/runs/20261101-$r-mocksha/results/mass_eval/summary.json > $MS/merge/$r.json
done
$P -I $M/../../../../../../tools/mass_eval_merge.py --table $M/../../packed_refs.json --n 3 --out $OUT/mock_merge.json \
  $MS/merge/mev{G1,G2,G4,S1s42,S1s43}.json > $OUT/mock_merge.txt
CONF=$(sed -n 's/^JOB: //p' $OUT/mock_merge.txt)
echo "$CONF" > $OUT/mock_confirmation_job.txt
bash $M/run_box.sh $MS C1 20261101-mevC1-mocksha "$CONF"
mv $MS/box $MS/done_C1
$P -I $M/../../../../../../tools/mass_eval_rule.py --h5 $MS/done_C1/content/results/h5/h5_summary.json --merge $OUT/mock_merge.json \
  --board pack7 --c1-run 20261101-mevC1-mocksha --out $OUT/mock_rule.json > $OUT/mock_rule.txt; echo "rule rc=$?" >> $OUT/mock_rule.txt
$P -I $M/check_train.py $MS $OUT/mock_check_train.json; $P -I $M/check_pack.py $MS $OUT/mock_check_pack.json $OUT/mock_merge.json $OUT/mock_rule.json
for b in G1 G2 G4 S1a S1b G1v C1; do sed "s#$MS#MS#g" $MS/done_$b/content/job.log > $OUT/mock_job_$b.log; done
for b in G1 G2 G4 S1a S1b G1v; do sed "s#$MS#MS#g" $MS/done_$b/content/results/mass_eval/verify.txt > $OUT/mock_verify_$b.txt; done
