#!/bin/bash
# Default-off check of the pack 9b D-arm changes (2026-10-31): the OLD scripts (git MOCK_BASE, default 880db25 = the last
# commit before any D-arm change to these files) and the NEW ones (working tree) on existing-caller job strings in
# identical fresh boxes, with every new hook unset (no ARM, no FC_DR_PATCH, no DR_EPS); compared: exit code, the job log
# (timestamps and pulled_/prev_ suffixes normalised), what the stub trainer / evaluators loaded and which FlashCHORD patches
# ran (audits without timestamps), the files written (names + md5; JSON without mass_arm.py's "created" timestamp line:
# the first run showed EG's arms_ep{15,33}.json differing only there) and the store traffic; and no training log of any
# of these boxes holds a "v2d FC_DR_RESET" line (the D line is absent in non-D trainings).
#   EG mass_eval.sh MODE=glock EPS="33 15" SEEDS="42 43" (the masses G2 box): mass_eval.sh + glock_public.sh
#   ES mass_eval.sh MODE=std EPS="1" SEEDS="42" (the masses S1a box): mass_eval.sh + hard_ab.sh
#   E2 hard_ab.sh + pipeline/pipeline_ep.sh on the eval-1 carve path (masses-eval equiv E2)
#   E3 pack_eval.sh + h5_reeval.sh rebuilding pack 7, draws 2..3 for evals 3 and 19 (masses-eval equiv E3)
# usage: equiv.sh MS OUT_DIR   (MS from setup.sh; the boxes run as MS/box in turn)
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); mkdir -p $OUT; R=$OUT/equiv.txt; : > $R
BASE=${MOCK_BASE:-880db25}
read -r -d '' E2 << 'EOF'
PULL_SUB="refs/perc2mck/ep1 perc2/ep1" bash ops/box/store.sh pull-run 20261024-pack-31ef267 > /dev/null 2>&1
. ops/box/lib.sh; export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
SPLIT=eval PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=3 SEED=43 LIB=/content/v2d-track3/meshes/library_v3 PIECES=/content/v2d-track3/meshes/carve/ev01 PAIRS="1:local:mck" bash ops/jobs/hard_ab.sh
EOF
E3='N=3 KEEP_RESULTS="20261026-pack6-5203d42 20261030-c33B-0202139" PICK_EXTRA="33:20261029-rcB-34bf6ae" EPS_ONLY="3 19" bash ops/jobs/h5_reeval.sh'
norm() { sed -e "s#$MS#MS#g" -e 's/^\[[0-9T:Z-]*\] //' -e 's/\[[0-9:]*\] //' -e 's/"t": [0-9.e+]*/"t": T/g' -e 's/pulled_[0-9]*/pulled_T/g' -e 's/prev_[0-9]*/prev_T/g' "$@"; }
run() {  # $1 name, $2 old files, $3 run id, $4 job
  for ver in old new; do
    if [ $ver = old ]; then MOCK_OLD="$2" MOCK_BASE=$BASE bash $M/run_box.sh $MS $1_$ver $3 "$4" > /dev/null
    else bash $M/run_box.sh $MS $1_$ver $3 "$4" > /dev/null; fi
    B=$MS/box; W=$OUT/equiv_$1_$ver; mkdir -p $W
    norm $B/content/job.log | grep -v '^cp: warning' > $W.joblog
    cat $B/train_audit.log $B/eval_audit.log $B/kit_audit.log $B/patch_audit.log 2> /dev/null | norm | sort > $W.audit
    # md5 per file; JSON files without their "created" timestamp line (tools/mass_arm.py writes the creation time)
    ( cd $B/content && find results runs refs -type f 2> /dev/null | sort | while read -r f; do
        case $f in *.json) echo "$f $(grep -v '^ *"created": "[0-9T:Z-]*",\?$' $f | md5sum | cut -c1-32)" ;; *) echo "$f $(md5sum < $f | cut -c1-32)" ;; esac
      done ) | norm > $W.files
    norm $B/hf.log | sed 's/: [0-9T:-]*Z$/: T/' > $W.hf; echo "rc $(cat $B/rc.txt)" > $W.rc
    echo "$(find $B/content/runs -name train.log 2> /dev/null | wc -l) training logs, $(find $B/content/runs -name train.log -exec grep -l 'v2d FC_DR_RESET' {} + 2> /dev/null | wc -l) with a v2d FC_DR_RESET line" > $W.dline
    rm -rf $W
  done
  for k in rc joblog audit files hf dline; do
    if cmp -s $OUT/equiv_$1_old.$k $OUT/equiv_$1_new.$k; then echo "$1 $k: IDENTICAL ($(wc -l < $OUT/equiv_$1_new.$k) lines)" >> $R
    else echo "$1 $k: DIFFERS" >> $R; diff $OUT/equiv_$1_old.$k $OUT/equiv_$1_new.$k | head -10 >> $R; fi
  done
  echo "$1: trainings $(grep -c '"steps"' $OUT/equiv_$1_new.audit), evaluations $(grep -c '"ck"' $OUT/equiv_$1_new.audit), patch calls $(grep -c '"patch"' $OUT/equiv_$1_new.audit), uploads $(grep -c '^hf upload' $OUT/equiv_$1_new.hf); D line: $(cat $OUT/equiv_$1_new.dline)" >> $R
}
run EG "ops/jobs/mass_eval.sh ops/jobs/glock_public.sh" 20261101-mevG2-mocksha 'MODE=glock EPS="33 15" SEEDS="42 43" bash ops/jobs/mass_eval.sh'
run ES "ops/jobs/mass_eval.sh ops/jobs/hard_ab.sh" 20261101-mevS1s42-mocksha 'MODE=std EPS="1" SEEDS="42" bash ops/jobs/mass_eval.sh'
run E2 "ops/jobs/hard_ab.sh pipeline/pipeline_ep.sh" 20261101-eqE2-mocksha "$E2"
run E3 "ops/jobs/pack_eval.sh ops/jobs/h5_reeval.sh" 20261101-eqE3-mocksha "$E3"
mv $MS/box $MS/done_equiv_last
cat $R
