#!/bin/bash
# usage: run_mock.sh MR 'JOB STRING' [ENV...] (as in JOBS.txt; /content is mapped to MR/content). Runs it as run_job.sh does:
# `bash -c "$JOB"` from the repo root with RUN_ID from the environment, output to MR/content/job.log; rc in MR/rc.txt.
MR=$1; . $MR/env.sh; JOB=${2//\/content/$MR\/content}
(cd $MR/content/v2d-track3 && bash -c "$JOB") > $MR/content/job.log 2>&1; echo "rc=$?" > $MR/rc.txt
