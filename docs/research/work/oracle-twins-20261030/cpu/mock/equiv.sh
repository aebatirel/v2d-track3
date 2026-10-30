#!/bin/bash
# Behaviour check for existing callers: run the OLD (git BASE, default be2b2a9 = before the oracle-twin hooks) and the NEW glock_public.sh / hard_ab.sh in a mock that
# already holds P references (3-field PAIRS, no PERC field), and compare what they train and evaluate (audit logs) and
# what they log (timestamps and paths normalised). usage: equiv.sh MR_SRC WORK
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; R=/home/user/v2d-track3
SRC=$1; W=$2; rm -rf $W; mkdir -p $W
for ver in old new; do
  for job in glock_public hard_ab; do
    MR=$W/$ver-$job; cp -a $SRC $MR
    find $MR/bin $MR/content/v2d-track3 $MR/content/mpvenv $MR/content/rtvenv $MR/content/v2d $MR/env.sh -type f -exec sed -i "s#$SRC#$MR#g" {} +
    for l in $(find $MR/content -maxdepth 3 -type l); do t=$(readlink $l); case $t in $SRC*) ln -sfn ${t/$SRC/$MR} $l ;; esac; done
    C=$MR/content; rm -rf $C/results/glock_public $C/results/oracle* $C/results/hard_ab $C/results/perc2mcks $C/runs/glock $C/runs/oracle* $C/runs/perc2mcks \
      $C/refs/glock $C/refs/glockt* $C/refs/sf $C/refs/oracle_* $C/refs/perc2mcks $C/*.log $C/push $C/run_state $C/train.lock* $MR/*.log
    if [ $ver = old ]; then /usr/bin/git -C $R show ${BASE:-be2b2a9}:ops/jobs/$job.sh | sed "s#/content#$C#g" > $C/v2d-track3/ops/jobs/$job.sh
    else sed "s#/content#$C#g" $R/ops/jobs/$job.sh > $C/v2d-track3/ops/jobs/$job.sh; fi           # the working-tree version
    . $MR/env.sh; export RUN_ID=20261030-equiv-mock SPLIT=public LIB=$C/v2d-track3/meshes/library_v3 SEED=42 NREP=2
    if [ $job = glock_public ]; then
      (cd $C/v2d-track3 && PAIRS="11:local:mck 13:local:mck" REPLAN=1 CURVE_REP=1 bash ops/jobs/glock_public.sh) > $C/job.log 2>&1
    else
      (cd $C/v2d-track3 && export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 PDIR_ROOT=$C/perc2 SUF=s CR=0 BASE_EVAL=0 \
         PAIRS="11:local:mck" STEPS=250003456 && bash ops/jobs/hard_ab.sh) > $C/job.log 2>&1
    fi
    echo "$ver $job rc=$?"
    norm() { sed -e "s#$MR#MR#g" -e 's/^\[[0-9T:Z-]*\] //' -e 's/"t": [0-9.]*/"t": T/' -e 's/\[[0-9:]*\]/[T]/g' "$@"; }
    norm $C/job.log | grep -v '^pulled runs/local\|^hf ' > $W/$ver-$job.joblog
    cat $MR/train_audit.log $MR/eval_audit.log $MR/ref_audit.log 2>/dev/null | norm | sort > $W/$ver-$job.audit
    find $C/results $C/runs $C/refs -type f 2>/dev/null | sed "s#$MR#MR#g" | sort > $W/$ver-$job.files
  done
done
for job in glock_public hard_ab; do
  for k in joblog audit files; do
    if cmp -s $W/old-$job.$k $W/new-$job.$k; then echo "$job $k: IDENTICAL ($(wc -l < $W/new-$job.$k) lines)"; else echo "$job $k: DIFFERS"; diff $W/old-$job.$k $W/new-$job.$k | head -20; fi
  done
done
