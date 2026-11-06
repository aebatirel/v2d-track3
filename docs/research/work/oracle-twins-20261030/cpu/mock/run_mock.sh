#!/bin/bash
# usage: run_mock.sh MR 'JOB STRING' (as in JOBS.txt; /content is mapped to MR/content). Runs it as run_job.sh would:
# from the repo root, output to MR/content/job.log.
MR=$1; . $MR/env.sh; JOB=${2//\/content/$MR\/content}
(cd $MR/content/v2d-track3 && eval "$JOB") > $MR/content/job.log 2>&1; echo "rc=$?" > $MR/rc.txt
