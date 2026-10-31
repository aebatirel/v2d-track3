#!/bin/bash
# Negative tests of the masses eval retrain (2026-10-31), on a finished run_all.sh mock (its store holds the four
# training boxes' runs). Each variant must be refused, and pack-side variants must stop BEFORE the kit evaluator runs
# (no kit_audit.log). usage: neg.sh MS OUT_DIR   -> OUT_DIR/neg.txt, OUT_DIR/neg.json
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); BASE=$(cat $OUT/mock_confirmation_job.txt); R=$OUT/neg.txt; : > $R
P=$(. $MS/tmpl/env.sh; echo $MOCK_PY)
v() {  # $1 name, $2 expected log pattern, $3 job string [, $4 1 = training variant]
  bash $M/run_box.sh $MS $1 20261101-mevN$1-mocksha "$3" > /dev/null
  local L=$MS/box/content/job.log hit rc ev
  hit=$(grep -a -m1 -E "$2" $L | sed "s#$MS#MS#g" | cut -c1-420); rc=$(cat $MS/box/rc.txt); ev=no
  [ -s $MS/box/kit_audit.log ] && ev=yes
  if [ -n "$hit" ] && { [ "${4:-0}" = 1 ] || [ $ev = no ]; }; then echo "PASS $1 ($rc, kit evaluator ran: $ev): $hit" >> $R
  else echo "FAIL $1 ($rc, kit evaluator ran: $ev): expected /$2/; log tail: $(tail -3 $L | sed "s#$MS#MS#g" | tr '\n' ' ' | cut -c1-400)" >> $R; fi
}
# ---- pack side: the confirmation string with one thing wrong ----
v N1_no_MA_ARGS 'REFUSED: an evaluated episode|ep1: white_pot would be evaluated with 0.3' "${BASE/MA_ARGS=\"--physics \/content\/v2d-track3\/docs\/research\/physics-2026-10-30\/props_masses_only.json\"/MA_ARGS=\"\"}"
v N2_no_mass_sf_folder 'NOT A FILE|is not a file' "${BASE/@refs\/mass1_sf\/ep20,/@}"
v N3_no_MASS_EPS 'MA_ARGS --physics needs KEEP_RESULTS, EVAL_ONLY and MASS_EPS|REFUSED: a masses run \(-mev\)' "$(echo "$BASE" | sed 's/MASS_EPS="[^"]*"/MASS_EPS=""/')"
v N3b_no_MASS_EPS_no_MA_ARGS 'REFUSED: a masses run \(-mev\)' "$(echo "$BASE" | sed -e 's/MASS_EPS="[^"]*"/MASS_EPS=""/' -e 's/MA_ARGS="[^"]*"/MA_ARGS=""/')"
v N4_MASS_EPS_without_1 'ep1: white_pot would be evaluated with 0.2771' "$(echo "$BASE" | sed 's/MASS_EPS="1 /MASS_EPS="/')"
# a mass check run directly on N4's box (pulled, /content/assets built with MA_ARGS): an UNCHANGED standard-learner
# episode (19) evaluated in the masses /content/assets must be refused
B=$MS/box; X=$B/mpc19; mkdir -p $X
echo "{\"19\": \"$(ls $B/content/pick/20261025-std1928-ee7ba8e/runs/20261025-std1928-ee7ba8e/results/final_eval/ep19/policy.safetensors)\"}" > $X/ck19.json
( . $MS/box/env.sh; $P -I $B/content/v2d-track3/tools/mass_pack_check.py --checkpoints $X/ck19.json \
     --props $B/content/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json --mass-eps "1" --out $X/mpc19.json ) > $OUT/neg_N6.txt 2>&1
grep -q 'REFUSED.*ep19: mini_sweeper would be evaluated with 0.045' $OUT/neg_N6.txt && echo "PASS N6_unchanged_std_in_masses_assets: $(sed "s#$MS#MS#g" $OUT/neg_N6.txt | cut -c1-300)" >> $R \
  || echo "FAIL N6_unchanged_std_in_masses_assets: $(sed "s#$MS#MS#g" $OUT/neg_N6.txt | cut -c1-300)" >> $R
sed -i "s#$MS#MS#g" $OUT/neg_N6.txt
v N13_no_ev01_pieces 'ep1: white_pot has 1 collision pieces .*trained with the 53 of meshes/carve/ev01' "$(echo "$BASE" | sed 's#ASSET_PIECES_EXTRA="[^"]*" ##')"
v N5_no_KEEP_RESULTS 'needs KEEP_RESULTS(,| and) EVAL_ONLY' "${BASE/KEEP_RESULTS=\"20261026-pack6-5203d42 20261030-c33B-0202139\"/KEEP_RESULTS=\"\"}"
# ---- training side ----
v N7_box_8_with_10 'REFUSED: episodes .*assets for' 'MODE=glock EPS="8 10" SEEDS="42" bash ops/jobs/mass_eval.sh' 1
v N8_box_1_with_28 'REFUSED: episodes .* share .*assets but need' 'MODE=std EPS="1 28" SEEDS="42" bash ops/jobs/mass_eval.sh' 1
v N9_wrong_mode 'REFUSED: mode std' 'MODE=std EPS="20" SEEDS="42" bash ops/jobs/mass_eval.sh' 1
v N10_run_id 'must contain -mev' 'RUN_ID=20261101-x-mocksha MODE=glock EPS="20" SEEDS="42" bash ops/jobs/mass_eval.sh' 1
# a stored reference that is not the packed one (the mock table's fingerprint for 15 changed): dropped, nothing trained
T=$MS/tmpl/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json; cp $T $T.bak
$P -I -c "import json, sys; d = json.load(open(sys.argv[1])); d['episodes']['15']['traj_fingerprint'] = '0' * 32; json.dump(d, open(sys.argv[1], 'w'))" $T
v N11_not_the_packed_reference 'REFUSED: stored reference .* is .* the packed policy' 'MODE=glock EPS="15" SEEDS="42" bash ops/jobs/mass_eval.sh' 1
[ -e $MS/box/train_audit.log ] && echo "FAIL N11: a training ran" >> $R
cp $T.bak $T
# eval 33 without its per-episode curriculum (the table's ENV cleared, i.e. what ENV_EP33 did before the glock_public fix):
# trained, then INVALID by the recipe check against the packed rcB checkpoint
$P -I -c "import json, sys; d = json.load(open(sys.argv[1])); d['episodes']['33']['env'] = ''; json.dump(d, open(sys.argv[1], 'w'))" $T
v N12_eval33_default_curriculum 'ep33 INVALID .*recipe differs from the packed checkpoint in .*curriculum.thresholds' 'MODE=glock EPS="33" SEEDS="43" bash ops/jobs/mass_eval.sh' 1
cp $T.bak $T; rm $T.bak
mv $MS/box $MS/done_neg_last
cat $R
$P -I -c "import json, sys; L = open(sys.argv[1]).read().splitlines(); json.dump(dict(ok=all(x.startswith('PASS') for x in L), n=len(L), results=L), open(sys.argv[2], 'w'), indent=1)" $R $OUT/neg.json
