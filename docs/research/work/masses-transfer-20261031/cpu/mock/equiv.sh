#!/bin/bash
# Default-off check for the glock_public.sh / ckpt_curve.sh hooks of 2026-10-31 (REF_ONLY, NO_PUSH, EVAL_TIMEOUT):
# run the OLD (git BASE, default 6bbb52a = before the hooks) and the NEW (working tree) scripts in two identical mocks on
# existing-caller job strings, and compare what they train, evaluate and build (audit logs), what they log (timestamps
# and mock paths normalised), which files they write and what they upload. usage: equiv.sh WORK
#   job 1 = recipe arm A on ep12 (recipe_arms_launch.sh g(): stored reference, REUSE_REF=1)
#   job 2 = the same recipe building ep2's reference from its base and training it (REUSE_REF=0, physics_arms.sh style)
W=$1; M=$(cd $(dirname $0) && pwd); R=/home/user/v2d-track3; rm -rf $W; mkdir -p $W
read -r -d '' JOB << 'EOF'
export SF=1 REPLAN=0 EVOLVE=1 CURVE_REP=3 NREP=5 LIB=/content/v2d-track3/meshes/library_v3 SPLIT=public SEED=42
export GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"
REUSE_REF=1 PULL_SUB="refs/perc2mc/ep12 refs/sf/ep12 refs/glockt/ep12 results/glock_public/ep12" PAIRS="12:20261024-ev2-2c1e4dd:mc" bash ops/jobs/glock_public.sh
REUSE_REF=0 PULL_SUB="refs/perc2mck/ep2" PAIRS="2:20261024-ev3-2c1e4dd:mck" bash ops/jobs/glock_public.sh
EOF
for ver in old new; do
  MR=$W/$ver; bash $M/setup.sh $MR > /dev/null
  if [ $ver = old ]; then
    for f in ops/jobs/glock_public.sh tools/ckpt_curve.sh; do
      /usr/bin/git -C $R show ${BASE:-6bbb52a}:$f | sed "s#/content#$MR/content#g" > $MR/content/v2d-track3/$f
    done
  fi
  bash $M/run_mock.sh $MR "$JOB"; echo "$ver rc $(cat $MR/rc.txt)"
  norm() { sed -e "s#$MR#MR#g" -e 's/^\[[0-9T:Z-]*\] //' -e 's/"t": [0-9.e+]*/"t": T/' -e 's/pulled_[0-9]*/pulled_T/g' -e 's/prev_[0-9]*/prev_T/g' "$@"; }
  norm $MR/content/job.log | grep -v '^hf \|^cp: warning' > $W/$ver.joblog
  cat $MR/train_audit.log $MR/eval_audit.log $MR/ref_audit.log 2> /dev/null | norm | sort > $W/$ver.audit
  find $MR/content/results $MR/content/runs $MR/content/refs -type f 2> /dev/null | sed "s#$MR#MR#g" | sed 's/prev_[0-9]*/prev_T/g; s/pulled_[0-9]*/pulled_T/g' | sort > $W/$ver.files
  sed -e "s#$MR#MR#g" -e 's/: [0-9T:-]*Z$/: T/' $MR/hf.log > $W/$ver.hf
done
for k in joblog audit files hf; do
  if cmp -s $W/old.$k $W/new.$k; then echo "$k: IDENTICAL ($(wc -l < $W/new.$k) lines)"; else echo "$k: DIFFERS"; diff $W/old.$k $W/new.$k | head -20; fi
done
echo "uploads: old $(grep -c '^hf upload' $W/old.hf), new $(grep -c '^hf upload' $W/new.hf); trainings: old $(grep -c '"steps"' $W/old.audit), new $(grep -c '"steps"' $W/new.audit); evaluations: old $(grep -c '"ck"' $W/old.audit), new $(grep -c '"ck"' $W/new.audit)"
