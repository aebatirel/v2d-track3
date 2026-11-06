#!/bin/bash
# Negative tests of the pack 9b D arm (2026-10-31), on the store of a finished run_all.sh (MS): each must be refused or
# give the stated label. usage: neg.sh MS OUT_DIR. Results: OUT/neg.txt (one line each), OUT/neg.json.
#  training side (mass_eval.sh ARM=dr / glock_public.sh):
#   N1 ARM=dr with a run id without -dr                      -> refused before any pull (rc 1)
#   N2 a patch file that is not the 4e5c8a0 port (md5)      -> refused before any pull
#   N3 ARM=bogus                                             -> refused
#   N4 the hook prints nothing (MOCK_DR_SILENT)              -> trains, dr_eval_verify INVALID (no D line)
#   N5 the hook reads another seed (MOCK_DR_SEED_SHIFT)      -> INVALID (D line seed)
#   N6 std without the skip flag reaching the hook           -> INVALID (no skip tail)
#   N7 a non-D training log on the D box                     -> INVALID (other training logs)
#   N8 glock_public.sh PERC drs42 on SPLIT=eval without FC_DR_PATCH -> refused for that pair (no training)
#  confirmation side (the merge's h5_reeval.sh job string, altered):
#   C1 a D reference copy not pulled (RUNS_EXTRA without ep16) -> dr_pack_check refuses before the kit evaluator
#   C2 DR_EPS lists 14 but PICK_EXTRA keeps the packed eval-14 checkpoint -> refused before the kit evaluator (with
#      KEEP_RESULTS the packed checkpoint's pack-6 rollout is kept, so dr_pack_check finds 14 "in DR_EPS but not evaluated
#      here"; without KEEP_RESULTS it would read "the D PICK did not take")
#   C3 the verdict without the pack-check files (a box run without DR_EPS) -> every candidate INVALID
#   C4 the verdict with a packed-side H5p7 draw replaced by another checkpoint's rollout -> that episode INVALID
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); mkdir -p $OUT; R=/home/user/v2d-track3; : > $OUT/neg.txt
P=$(. $MS/tmpl/env.sh; echo $MOCK_PY)
res() { echo "$1 $2 :: $3" | tee -a $OUT/neg.txt; }
box() { bash $M/run_box.sh $MS $1 $2 "$3" > /dev/null; }
J() { sed "s#$MS#MS#g" $MS/box/content/job.log; }
ntrain() { find $MS/box/content/runs -name 'policy_*.safetensors' 2> /dev/null | wc -l; }
vstat() { $P -I -c "import json, sys; V = json.load(open(sys.argv[1])); print(' '.join(f'ep{e} {x[\"status\"]}: {(x[\"failures\"] or [\"\"])[0][:160]}' for e, x in V['episodes'].items()))" $MS/box/content/results/dr_eval/verify.json 2> /dev/null || echo 'no verify.json'; }

box N1 20261101-mevN1-mocksha 'ARM=dr MODE=glock EPS="14" SEEDS="42" bash ops/jobs/mass_eval.sh'
g=$(J | grep -c 'must contain -dr'); res N1 $([ "$g" = 1 ] && [ "$(ntrain)" = 0 ] && [ ! -s $MS/box/hf.log ] && echo PASS || echo FAIL) "$(J | tail -1 | cut -c1-200)"
box N2 20261101-drN2-mocksha 'echo "# altered" >> ops/box/patch_flashchord_dr.py; ARM=dr MODE=glock EPS="14" SEEDS="42" bash ops/jobs/mass_eval.sh'
g=$(J | grep -c 'md5 is not 570a7f47'); res N2 $([ "$g" = 1 ] && [ "$(ntrain)" = 0 ] && [ ! -s $MS/box/hf.log ] && echo PASS || echo FAIL) "$(J | tail -1 | cut -c1-200)"
box N3 20261101-drN3-mocksha 'ARM=bogus MODE=glock EPS="14" SEEDS="42" bash ops/jobs/mass_eval.sh'
g=$(J | grep -c "ARM 'bogus' unknown"); res N3 $([ "$g" = 1 ] && [ "$(ntrain)" = 0 ] && echo PASS || echo FAIL) "$(J | tail -1 | cut -c1-200)"
box N4 20261101-drN4-mocksha 'MOCK_DR_SILENT=1 ARM=dr MODE=glock EPS="14" SEEDS="42" bash ops/jobs/mass_eval.sh'
v=$(vstat); res N4 $(echo "$v" | grep -q 'ep14 INVALID.*no "v2d FC_DR_RESET" line' && echo PASS || echo FAIL) "$v"
box N5 20261101-drN5-mocksha 'MOCK_DR_SEED_SHIFT=1 ARM=dr MODE=glock EPS="16" SEEDS="43" bash ops/jobs/mass_eval.sh'
v=$(vstat); res N5 $(echo "$v" | grep -q 'ep16 INVALID.*D line seed 44 != the cell seed 43' && echo PASS || echo FAIL) "$v"
box N6 20261101-drN6-mocksha 'MOCK_DR_NO_SKIP=1 ARM=dr MODE=std EPS="30" SEEDS="42" bash ops/jobs/mass_eval.sh'
v=$(vstat); res N6 $(echo "$v" | grep -q 'ep30 INVALID.*without the skip-immediate tail' && echo PASS || echo FAIL) "$v"
box N7 20261101-drN7-mocksha 'mkdir -p /content/runs/perc2x/ep9-s42 && echo "a training without D" > /content/runs/perc2x/ep9-s42/train.log; ARM=dr MODE=std EPS="30" SEEDS="43" bash ops/jobs/mass_eval.sh'
v=$(vstat); res N7 $(echo "$v" | grep -q 'ep30 INVALID.*non-D trainings on this D box' && echo PASS || echo FAIL) "$v"
box N8 20261101-drN8-mocksha 'SPLIT=eval NREP=1 PAIRS="14:local:mck:drs42" LIB=/content/v2d-track3/meshes/library_v3 bash ops/jobs/glock_public.sh'
g=$(J | grep -c 'PERC drs42 (D arm) with SPLIT=eval needs RUN local, REQUIRE_REUSE=1 and FC_DR_PATCH=1'); res N8 $([ "$g" = 1 ] && [ "$(ntrain)" = 0 ] && [ "$(cat $MS/box/patch_audit.log 2> /dev/null | grep -c patch_flashchord_dr)" = 0 ] && echo PASS || echo FAIL) "$(J | grep 'drs42' | tail -1 | cut -c1-200)"
CONF=$(cat $OUT/../outA/mock_confirmation_job.txt 2> /dev/null || cat $OUT/mock_confirmation_job.txt)
C1=$(echo "$CONF" | sed 's# [^ "]*@refs/drs[0-9]*_glockt/ep16##')
box C1 20261101-drNC1-mocksha "$C1"
g=$(J | grep -c 'dr_pack_check: REFUSED'); k=$(cat $MS/box/kit_audit.log 2> /dev/null | wc -l)
res C1 $([ "$g" -ge 1 ] && [ "$k" = 0 ] && echo PASS || echo FAIL) "kit evaluations $k; $(J | grep 'dr_pack_check: REFUSED' | head -1 | cut -c1-220)"
C2=$(echo "$CONF" | sed 's# 14:[^ "]*:ck=results/drs[0-9]*_glock_public/ep14/best/policy.safetensors##')
box C2 20261101-drNC2-mocksha "$C2"
g=$(J | grep -c 'dr_pack_check: REFUSED (1): ep14: \(in DR_EPS but not evaluated here\|the checkpoint to evaluate is the packed one\)'); k=$(cat $MS/box/kit_audit.log 2> /dev/null | wc -l)
res C2 $([ "$g" -ge 1 ] && [ "$k" = 0 ] && echo PASS || echo FAIL) "kit evaluations $k; $(J | grep -o 'REFUSED (1): ep14: [^:]*' | head -1)"
A=$OUT/../outA; TABM=$MS/tmpl/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json
SC=$(for e in 14 16 25 30 33; do printf -- '--score %s ' $A/score_ep$e.json; done)
$P -I $R/tools/dr_verdict.py --merge $A/mock_merge.json --table $TABM $SC --out $OUT/neg_C3.json > $OUT/neg_C3.txt 2>&1
n=$($P -I -c "import json, sys; print(sum(x['label'] == 'INVALID' for x in json.load(open(sys.argv[1]))['episodes'].values()))" $OUT/neg_C3.json)
res C3 $([ "$n" = 5 ] && echo PASS || echo FAIL) "$n of 5 INVALID: $(head -1 $OUT/neg_C3.txt | cut -c1-200)"
$P -I - $A/score_ep25.json $OUT/neg_C4_score25.json << 'EOF'
import json, sys
d = json.load(open(sys.argv[1])); r = d['sets']['packed']['rollouts'][4]; r['checkpoint_sha256'] = 'c' * 64
json.dump(d, open(sys.argv[2], 'w'))
EOF
SC4=$(for e in 14 16 30 33; do printf -- '--score %s ' $A/score_ep$e.json; done)
$P -I $R/tools/dr_verdict.py --merge $A/mock_merge.json --table $TABM $SC4 --score $OUT/neg_C4_score25.json \
  --pack-check $MS/done_C/content/results/final_eval/dr_pack_check.json --pack-check $MS/done_C/content/results/h5/dr_pack_check.json --out $OUT/neg_C4.json > $OUT/neg_C4.txt 2>&1
l=$($P -I -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes']; print(v['25']['label'], v['25']['why'][0][:120], sum(x['label'] == 'INVALID' for x in v.values()))" $OUT/neg_C4.json)
res C4 $(echo "$l" | grep -q '^INVALID packed/r5: checkpoint cccccccccccc.* 1$' && echo PASS || echo FAIL) "$l"
mv $MS/box $MS/done_neg_last
$P -I -c "import json, sys; L = [l.split(' :: ')[0].split() for l in open(sys.argv[1])]; json.dump(dict(n=len(L), passed=sum(x[1] == 'PASS' for x in L), cases={x[0]: x[1] for x in L}), open(sys.argv[2], 'w'), indent=1); print(f'neg: {sum(x[1] == \"PASS\" for x in L)} / {len(L)} as expected')" $OUT/neg.txt $OUT/neg.json
