#!/bin/bash
# One mock box (2026-10-31): a fresh MS/box from MS/tmpl (the previous box is kept as MS/done_<its name>), then the job
# string as run_job.sh runs it: `bash -c "$JOB"` from the repo root with RUN_ID set, output to box/content/job.log, rc to
# box/rc.txt; /content in the job string is mapped to the box's content root. The boxes share only MS/store.
# usage: run_box.sh MS NAME RUN_ID 'JOB STRING'
MS=$1; NAME=$2; RID=$3; JOB=$4
[ -d $MS/box ] && mv $MS/box $MS/done_$(cat $MS/box/NAME)
cp -a $MS/tmpl $MS/box; ln -s $MS/store $MS/box/store; echo $NAME > $MS/box/NAME
. $MS/box/env.sh; JOB=${JOB//\/content/$MS\/box\/content}
(cd $MS/box/content/v2d-track3 && RUN_ID=$RID bash -c "$JOB") > $MS/box/content/job.log 2>&1; echo "rc=$?" > $MS/box/rc.txt
echo "box $NAME ($RID): $(cat $MS/box/rc.txt), $(grep -c . $MS/box/content/job.log) log lines"
