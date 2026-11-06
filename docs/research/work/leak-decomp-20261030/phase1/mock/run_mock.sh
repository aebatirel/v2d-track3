#!/bin/bash
# usage: run_mock.sh MR RUN_ID 'JOB STRING' [VAR=value ...]   (JOB as in JOBS.txt; /content is mapped to MR/content)
# Runs the job as run_job.sh would (from the repo root, output MR/content/job.log, exit code MR/rc.txt), then the final
# push of run_job.sh's self_destroy (store.sh push-run with the stub hf: staged files stay in MR/content/push/RUN_ID).
# Extra VAR=value words (fault injection, see stub.py / hf_stub.py) are exported first. Each call starts clean.
MR=$1; RID=$2; JOB=${3//\/content/$MR\/content}; shift 3
. $MR/env.sh; for v in "$@"; do export "$v"; done
rm -rf $MR/content/results $MR/content/hfstore $MR/content/run_state $MR/content/push $MR/content/*.log $MR/hf.log \
       $MR/hf_429_seen.txt $MR/perc2_audit.log $MR/gdino_tries.txt $MR/gdino_cached
export RUN_ID=$RID
(cd $MR/content/v2d-track3 && eval "$JOB") > $MR/content/job.log 2>&1; echo $? > $MR/rc.txt
bash $MR/content/v2d-track3/ops/box/store.sh push-run > $MR/push.out 2>&1; echo "push rc=$?" >> $MR/push.out
