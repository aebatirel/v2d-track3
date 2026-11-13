#!/bin/bash
# Runs INSIDE the overlay+chroot sandbox (box.sh): emulates one Vast box of test A from onstart.sh to self-destroy.
# Dry-run deviations from a real box (each one stated in the README): SETUP=none (no env-snapshot restore: the
# snapshot is 16 GB of CUDA builds; this replaces it with a small venv and the scratchpad's FlashCHORD checkout at the
# same pin), REXEC=0 (no Cloudflare tunnel), training and the evaluator stubbed, Vast API and HF uploads intercepted.
set -u
BOX=$1; RUN_ID=$2; COMMIT=$3; GA=$4; OUT=$GA/out/$BOX
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root
FCSRC=$(dirname $GA)/wgate/fc/v2d
mkdir -p /dryrun $OUT
cp $GA/dry/fakes/{fake_train.py,fake_eval.py,compose_check.py,example_rollout.parquet} /dryrun/
# --- "image": python venv at /venv/main (as on vastai/pytorch), fake curl (Vast API), fake hf upload ---
install -m 755 $GA/dry/fakes/curl /usr/local/sbin/curl
mkdir -p /venv && ln -sfn $GA/venv_main /venv/main
[ -e $GA/venv_main/bin/hf.real ] || mv $GA/venv_main/bin/hf $GA/venv_main/bin/hf.real      # copy-up: sandbox only
install -m 755 $GA/dry/fakes/hf $GA/venv_main/bin/hf
# --- what onstart.sh does first on a real box ---
mkdir -p /workspace && { [ -e /content ] || ln -s /workspace /content; }
# --- "env snapshot" stand-ins: FlashCHORD at the evaluator pin (8c778f9) with a stubbed interpreter, the kit ---
ln -sfn $FCSRC /workspace/v2d
FCV=/workspace/v2d/robotic_grounding/flash_chord/.venv/bin
[ -e $FCV/python.real ] || mv $FCV/python $FCV/python.real
install -m 755 $GA/dry/fakes/fc_python $FCV/python
mkdir -p /workspace/kit && ln -sfn $GA/kit/v2d_submission_kit /workspace/kit/v2d_submission_kit
# --- dataset: the real fetch_data.sh (what run_job.sh runs after a snapshot restore); download cache pre-seeded ---
ln -sfn $GA/hfds /workspace/hfds
( . /venv/main/bin/activate; REPO_DIR=/home/user/v2d-track3 bash /home/user/v2d-track3/pipeline/fetch_data.sh ) > $OUT/fetch_data.log 2>&1
echo "fetch_data: $(tail -2 $OUT/fetch_data.log | tr '\n' ' ')"
# --- the instance env exactly as ops/vast.sh create builds it (plus the dry-run switches) ---
export RUN_ID V2D_COMMIT=$COMMIT JOB_B64=$(base64 -w0 < $GA/jobs/$BOX.job) \
       V2D_IMAGE=vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16 ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 \
       HF_STORE=aebatirel/v2d-store SETUP=none REXEC=0 CONTAINER_ID=DRYRUN-$BOX CONTAINER_API_KEY=dryrun-not-a-key
t0=$(date +%s)
[ $BOX = stall ] && export STALL_MIN=2      # stall-watchdog test only
bash /home/user/v2d-track3/ops/box/onstart.sh > $OUT/onstart.log 2>&1
echo "onstart rc=$?: $(cat $OUT/onstart.log)"
# --- wait for run_job.sh: job, push, self-destroy (DELETE intercepted) ---
for i in $(seq 1 360); do
  grep -q 'onstart: .*FAIL' $OUT/onstart.log && { echo "onstart failed"; pkill -f 'sleep 1200'; break; }
  grep -q "destroy requested\|DESTROY FAILED" /workspace/run_job.log 2> /dev/null && break
  sleep 10
done
echo "box finished after $(( $(date +%s) - t0 )) s"
pkill -f '/content/v2d-track3/ops/box/watchdog.sh' 2> /dev/null; [ $BOX = stall ] && pkill -f 'sleep 100000'; sleep 1
# --- evidence ---
cp /workspace/run_job.log /content/*.log $OUT/ 2> /dev/null
cp /dryrun/*.log /dryrun/*.jsonl $OUT/ 2> /dev/null
sed 's/CONTAINER_API_KEY=.*/CONTAINER_API_KEY=<fake>/' /etc/v2d_env > $OUT/v2d_env.txt
(cd /dryrun/fakestore && find . -type f -printf '%s\t%p\n' | sort -k2) > $OUT/fakestore_files.tsv
du -sh /dryrun/fakestore/runs/* > $OUT/fakestore_du.txt 2>&1
(cd /content && find perc2 refs runs results -maxdepth 3 | sort) > $OUT/content_tree.txt
for d in /content/runs/perc2s/*/; do cp $d/DRYRUN_train_call.json $OUT/train_call_$(basename $d).json; cp $d/DRYRUN_compose.yaml $OUT/compose_$(basename $d).yaml 2>/dev/null; done
cp -r /content/results/hard_ab $OUT/results_hard_ab 2> /dev/null
for d in /content/results/perc2s/*/; do mkdir -p $OUT/results_pipeline/$(basename $d); cp $d/*.json $OUT/results_pipeline/$(basename $d)/ 2>/dev/null; done
for d in /content/refs/perc2s/*/; do cp $d/qa_ref.json $OUT/qa_ref_$(basename $d).json 2>/dev/null; done
git -C /content/v2d-track3 rev-parse HEAD > $OUT/box_commit.txt
git -C /content/v2d-track3 status --short > $OUT/box_git_status.txt
(cd /workspace/v2d && git status --short | grep -v '/assets/meshes/' > $OUT/flashchord_patched_files.txt)
df -h /workspace > $OUT/df.txt; du -sh /content/ /content/* 2>/dev/null > $OUT/du_content.txt
echo DRYRUN-COMPLETE
