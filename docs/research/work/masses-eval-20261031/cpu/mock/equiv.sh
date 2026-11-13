#!/bin/bash
# Default-off check of the 2026-10-31 changes (masses eval retrain): the OLD scripts (git MOCK_BASE, default 14ae515 = the last commit before
# this build) and the NEW ones (working tree) on existing-caller job strings in identical fresh boxes, with every new
# hook unset; compared: the job log (timestamps and pulled_/prev_ suffixes normalised), what the stub trainer and
# evaluators loaded (audits without timestamps), the files written (names + md5) and the store traffic.
#   E2 hard_ab.sh + pipeline/pipeline_ep.sh: the carve_rerun / std_learner path on eval 1 (no EVAL_TIMEOUT, no NO_PUSH)
#   E3 pack_eval.sh + h5_reeval.sh: pack 7 rebuilt (KEEP_RESULTS pack 6 + c33B, PICK_EXTRA 33:rcB; no MASS_EPS,
#      RUNS_EXTRA, PACKED_TXT), draws 2..3 for evals 3 and 19. Expected since ab55e8c (31 Oct 09:59, KEEP_ROLLOUTS
#      defaults to 1, a separate intended change): new = old except draws 2..N keep their rollout parquets;
#   E3k the same with KEEP_ROLLOUTS=0 (2026-10-31, review F5): must be identical in every respect
# (glock_public.sh: masses-transfer-20261031/cpu/mock/equiv.sh with BASE=HEAD, its public job strings.)
# usage: equiv.sh MS OUT_DIR   (MS from setup.sh; the boxes run as MS/box in turn)
MS=$1; OUT=$2; M=$(cd $(dirname $0) && pwd); mkdir -p $OUT; R=$OUT/equiv.txt; : > $R
read -r -d '' E2 << 'EOF'
PULL_SUB="refs/perc2mck/ep1 perc2/ep1" bash ops/box/store.sh pull-run 20261024-pack-31ef267 > /dev/null 2>&1
. ops/box/lib.sh; export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"
SPLIT=eval PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=3 SEED=43 LIB=/content/v2d-track3/meshes/library_v3 PIECES=/content/v2d-track3/meshes/carve/ev01 PAIRS="1:local:mck" bash ops/jobs/hard_ab.sh
EOF
E3='N=3 KEEP_RESULTS="20261026-pack6-5203d42 20261030-c33B-0202139" PICK_EXTRA="33:20261029-rcB-34bf6ae" EPS_ONLY="3 19" bash ops/jobs/h5_reeval.sh'
norm() { sed -e "s#$MS#MS#g" -e 's/^\[[0-9T:Z-]*\] //' -e 's/\[[0-9:]*\] //' -e 's/"t": [0-9.e+]*/"t": T/g' -e 's/pulled_[0-9]*/pulled_T/g' -e 's/prev_[0-9]*/prev_T/g' "$@"; }
run() {  # $1 name, $2 old files, $3 job
  for ver in old new; do
    if [ $ver = old ]; then MOCK_OLD="$2" MOCK_BASE=${MOCK_BASE:-14ae515} bash $M/run_box.sh $MS $1_$ver 20261101-eq$1-mocksha "$3" > /dev/null
    else bash $M/run_box.sh $MS $1_$ver 20261101-eq$1-mocksha "$3" > /dev/null; fi
    B=$MS/box; W=$OUT/equiv_$1_$ver; mkdir -p $W
    norm $B/content/job.log | grep -v '^cp: warning' > $W.joblog
    cat $B/train_audit.log $B/eval_audit.log $B/kit_audit.log 2> /dev/null | norm | sort > $W.audit
    ( cd $B/content && find results runs refs -type f 2> /dev/null | sort | while read -r f; do echo "$f $(md5sum < $f | cut -c1-32)"; done ) | norm > $W.files
    norm $B/hf.log | sed 's/: [0-9T:-]*Z$/: T/' > $W.hf; echo "rc $(cat $B/rc.txt)" > $W.rc; rm -rf $W
  done
  for k in rc joblog audit files hf; do
    if cmp -s $OUT/equiv_$1_old.$k $OUT/equiv_$1_new.$k; then echo "$1 $k: IDENTICAL ($(wc -l < $OUT/equiv_$1_new.$k) lines)" >> $R
    else echo "$1 $k: DIFFERS" >> $R; diff $OUT/equiv_$1_old.$k $OUT/equiv_$1_new.$k | head -10 >> $R; fi
  done
  echo "$1: trainings $(grep -c '"steps"' $OUT/equiv_$1_new.audit), evaluations $(grep -c '"ck"' $OUT/equiv_$1_new.audit), uploads $(grep -c '^hf upload' $OUT/equiv_$1_new.hf)" >> $R
}
run E2 "ops/jobs/hard_ab.sh pipeline/pipeline_ep.sh" "$E2"
run E3 "ops/jobs/pack_eval.sh ops/jobs/h5_reeval.sh" "$E3"
run E3k "ops/jobs/pack_eval.sh ops/jobs/h5_reeval.sh" "KEEP_ROLLOUTS=0 $E3"
mv $MS/box $MS/done_equiv_last
cat $R
