#!/bin/bash
# End-to-end CPU mock of the masses eval retrain (2026-10-31): the JOBS.txt job strings, in order, each on a fresh box
# sharing one fake store (setup.sh, run_box.sh), then the checks. usage: run_all.sh MS OUT_DIR
#   G1  MODE=glock EPS="20 8"  SEEDS="42 43"   (wave 1; eval 8 on library_v3x)
#   G2  MODE=glock EPS="33 15" SEEDS="42 43"   (wave 1, spoon pilots; eval 33 CURR_SCALE 0.4 through ENV_EP33)
#   G4  MODE=glock EPS="10"    SEEDS="42"      (O4 only; the one grasp-lock reference that names /content/assets, ev10)
#   S1  MODE=std   EPS="1"     SEEDS="43"      (wave 1, the S1b box; ev01 pieces + MA_ARGS)
#   C1  ops/jobs/h5_reeval.sh confirmation of every candidate, built from the boxes' pushed summary.json the way the
#       orchestrator does (join the strings): N=3 draws here (10 on the real box), KEEP_RESULTS = pack 7's sources.
# then check_train.py and check_pack.py. Mock scores are synthetic: the mock tests the plumbing, not masses.
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); mkdir -p $OUT
bash $M/setup.sh $MS > $OUT/mock_setup.txt 2>&1 || { cat $OUT/mock_setup.txt; exit 1; }
bash $M/run_box.sh $MS G1 20261101-mevG1-mocksha 'MODE=glock EPS="20 8" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS G2 20261101-mevG2-mocksha 'MODE=glock EPS="33 15" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS G4 20261101-mevG4-mocksha 'MODE=glock EPS="10" SEEDS="42" bash ops/jobs/mass_eval.sh'
bash $M/run_box.sh $MS S1 20261101-mevS1s43-mocksha 'MODE=std EPS="1" SEEDS="43" bash ops/jobs/mass_eval.sh'
# the confirmation strings: each box's summary.json from the store (one file each), joined
CONF=$($(. $MS/tmpl/env.sh; echo $MOCK_PY) -I - $MS/store/runs << 'EOF'
import json, sys
k = dict(RUNS_EXTRA=[], PICK_EXTRA=['33:20261029-rcB-34bf6ae'], MASS_EPS=[], MA_ARGS=set(), ASSET_PIECES_EXTRA=set())
for r in ('20261101-mevG1-mocksha', '20261101-mevG2-mocksha', '20261101-mevG4-mocksha', '20261101-mevS1s43-mocksha'):
    c = json.load(open(f'{sys.argv[1]}/{r}/results/mass_eval/summary.json'))['confirmation']
    for x in ('RUNS_EXTRA', 'PICK_EXTRA', 'MASS_EPS'):
        k[x] += c[x].split()
    for x in ('MA_ARGS', 'ASSET_PIECES_EXTRA'):
        k[x] |= {c[x]} if c[x] else set()
e = ' '.join(k['MASS_EPS'])
print(f'N=3 KEEP_RESULTS="20261026-pack6-5203d42 20261030-c33B-0202139" RUNS_EXTRA="{" ".join(k["RUNS_EXTRA"])}" '
      f'PICK_EXTRA="{" ".join(k["PICK_EXTRA"])}" MASS_EPS="{e}" EVAL_ONLY="{e}" EPS_ONLY="{e}" MA_ARGS="{" ".join(k["MA_ARGS"])}" '
      f'ASSET_PIECES_EXTRA="{" ".join(sorted(k["ASSET_PIECES_EXTRA"]))}" '
      'PACKED_TXT=/content/v2d-track3/results/submissions/20261030-track3g-candidate/summary.txt bash ops/jobs/h5_reeval.sh')
EOF
)
echo "$CONF" > $OUT/mock_confirmation_job.txt
bash $M/run_box.sh $MS C1 20261101-mevC1-mocksha "$CONF"
mv $MS/box $MS/done_C1
P=$(. $MS/tmpl/env.sh; echo $MOCK_PY)
$P -I $M/check_train.py $MS $OUT/mock_check_train.json; $P -I $M/check_pack.py $MS $OUT/mock_check_pack.json
for b in G1 G2 G4 S1 C1; do sed "s#$MS#MS#g" $MS/done_$b/content/job.log > $OUT/mock_job_$b.log; done
for b in G1 G2 G4 S1; do sed "s#$MS#MS#g" $MS/done_$b/content/results/mass_eval/verify.txt > $OUT/mock_verify_$b.txt; done
