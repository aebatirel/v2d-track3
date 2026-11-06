#!/bin/bash
# Negative tests of the masses eval retrain (2026-10-31), on a finished run_all.sh mock (its store holds the four
# training boxes' runs). Each variant must be refused, and pack-side variants must stop BEFORE the kit evaluator runs
# (no kit_audit.log). Review fixes (31 Oct): N14 (F2, a base support stage that is not the packed one: refused before
# training), and CPU re-verifications of finished boxes with one thing changed: N15 (F2 in B3: INVALID), N16 (F6: a cut
# main evaluation is INCOMPLETE, not INVALID), N17 (F1: a seed with 7 scored rollouts makes the episode INCOMPLETE and the
# merge names the seed to retrain); N16b / N17e show what the reviewed build's tool (2d2b76e) did instead.
# usage: neg.sh MS OUT_DIR   -> OUT_DIR/neg.txt, OUT_DIR/neg.json
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
# (review F2) the base's support stage is not the packed reference's (the store's refs/perc2mck/ep15 stage changed): refused
# before any training
SG=$(ls $MS/store/runs/20261024-pack-31ef267/refs/perc2mck/ep15/reconstructed_stage/*.usda); cp $SG $SG.bak; echo '# changed' >> $SG
v N14_support_stage_not_packed 'REFUSED: support stage of refs/perc2mck/ep15' 'MODE=glock EPS="15" SEEDS="42" bash ops/jobs/mass_eval.sh' 1
[ -e $MS/box/train_audit.log ] && echo "FAIL N14: a training ran" >> $R
mv $SG.bak $SG
mv $MS/box $MS/done_neg_last
# ---- CPU re-verification of finished boxes (a copy at MS/box, the path the box ran at), with one thing changed ----
B=$MS/box; ME=$B/content/results/mass_eval; VT=$B/content/v2d-track3/tools
vrun() {  # $1 tool, $2 mode, $3 eps, $4 seeds, $5 run, $6 extra args -> $B/rv_<tool>.{json,txt}, $B/rs_<tool>.json
  ( . $B/env.sh; eval $P -I $VT/$1.py --mode $2 --eps \"$3\" --seeds \"$4\" --props $B/content/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json \
      --table $B/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json --run $5 --packed $ME/packed $6 \
      --out $B/rv_$1.json --summary $B/rs_$1.json ) > $B/rv_$1.txt 2>&1
}
# the reviewed build's tool (2d2b76e, before the review fixes; later WIP commits already carry the fixed one)
old_verify() { git -C /home/user/v2d-track3 show 2d2b76e:tools/mass_eval_verify.py | sed "s#/content#$B/content#g" > $VT/mass_eval_verify_head.py; }
res() {  # $1 name, $2 pattern that must match, $3 file, [$4 pattern that must NOT match]
  local hit; hit=$(grep -a -m1 -E "$2" $3 | sed "s#$MS#MS#g" | cut -c1-420)
  if [ -n "$hit" ] && { [ -z "${4:-}" ] || ! grep -q -E "$4" $3; }; then echo "PASS $1: $hit" >> $R
  else echo "FAIL $1: expected /$2/$([ -n "${4:-}" ] && echo " and not /$4/"); got: $(head -c 400 $3 | sed "s#$MS#MS#g" | tr '\n' ' ')" >> $R; fi
}
# N15 (review F2, B3): a trained reference whose support stage is not the packed one -> INVALID
cp -a $MS/done_G2 $B; echo '# changed' >> $B/content/refs/mass1s42_glockt/ep15/reconstructed_stage/t3_ep015_support.usda
vrun mass_eval_verify glock "33 15" "42 43" 20261101-mevG2-mocksha "--manifests \"$ME/arms_ep33.json $ME/arms_ep15.json\""
res N15_trained_support_stage_not_packed 'ep15 INVALID .*support stage .*is not the packed reference' $B/rv_mass_eval_verify.txt
res N15b_other_episode_unaffected '^ep33 VERIFIED' $B/rv_mass_eval_verify.txt
cp $B/rv_mass_eval_verify.txt $OUT/neg_N15_verify.txt; rm -rf $B
# N16 (review F6): a standard-learner main evaluation cut by EVAL_TIMEOUT (eval_rc 124, so no sweep and no selection.json)
# -> INCOMPLETE with seed 42 to retrain, not INVALID; the reviewed build's tool (2d2b76e) said INVALID
cp -a $MS/done_S1a $B; rm $B/content/results/perc2mcks/ep1-s42/selection.json; echo 124 > $B/content/results/perc2mcks/ep1-s42/eval_rc.txt
vrun mass_eval_verify std 1 42 20261101-mevS1s42-mocksha "--assets03 $ME/assets_03"
res N16_main_eval_timeout_incomplete "^ep1 INCOMPLETE .*main evaluation cut .*retrain seeds \['42'\]" $B/rv_mass_eval_verify.txt 'INVALID'
old_verify; vrun mass_eval_verify_head std 1 42 20261101-mevS1s42-mocksha "--assets03 $ME/assets_03"
res N16b_reviewed_build_said_invalid "^ep1 INVALID .*no selection.json" $B/rv_mass_eval_verify_head.txt
cp $B/rv_mass_eval_verify.txt $OUT/neg_N16_verify.txt; cp $B/rv_mass_eval_verify_head.txt $OUT/neg_N16_verify_head.txt; rm -rf $B
# N17 (review F1): seed 43 of eval 20 with 7 scored rollouts (3 of 10 lost) -> INCOMPLETE, retrain only seed 43; the merge
# gives no candidate for 20 and keeps 8; the reviewed build's tool (2d2b76e) took eval 20's candidate from 7 rollouts
cp -a $MS/done_G1 $B; rm $B/content/results/mass1s43_glock_public/ep20/best/r{1,2,3}/qa_policy.json
vrun mass_eval_verify glock "20 8" "42 43" 20261101-mevG1-mocksha "--manifests \"$ME/arms_ep20.json $ME/arms_ep8.json\""
res N17_thin_seed_incomplete "^ep20 INCOMPLETE .*thin \(n < 8\) \['ep20/s43'\] retrain seeds \['43'\]" $B/rv_mass_eval_verify.txt
res N17b_other_episode_verified '^ep8 VERIFIED' $B/rv_mass_eval_verify.txt
sed "s#$B/content#/content#g" $B/rs_mass_eval_verify.json > $B/rs_mapped.json
$P -I /home/user/v2d-track3/tools/mass_eval_merge.py --table $B/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json \
  --out $B/merge17.json $B/rs_mapped.json > $B/merge17.txt 2>&1
res N17c_merge_incomplete_retrain_43 "^ep20: INCOMPLETE \(seeds \['43'\] missing or n < 8.* s43: missing or n < 8 on 20261101-mevG1-mocksha \(n 7\): retrain only this seed" $B/merge17.txt
res N17d_merge_keeps_8 '^ep8: CANDIDATE' $B/merge17.txt
old_verify; vrun mass_eval_verify_head glock "20 8" "42 43" 20261101-mevG1-mocksha "--manifests \"$ME/arms_ep20.json $ME/arms_ep8.json\""
res N17e_reviewed_build_took_n7 '^ep20 VERIFIED .*s43 n 7 ' $B/rv_mass_eval_verify_head.txt
cp $B/rv_mass_eval_verify.txt $OUT/neg_N17_verify.txt; cp $B/merge17.txt $OUT/neg_N17_merge.txt; cp $B/rv_mass_eval_verify_head.txt $OUT/neg_N17_verify_head.txt
rm -rf $B
sed -i "s#$MS#MS#g" $OUT/neg_N1[5-7]*.txt
cat $R
$P -I -c "import json, sys; L = open(sys.argv[1]).read().splitlines(); json.dump(dict(ok=all(x.startswith('PASS') for x in L), n=len(L), results=L), open(sys.argv[2], 'w'), indent=1)" $R $OUT/neg.json
