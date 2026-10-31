#!/bin/bash
# Default-off proof for the Masses v2 changes (2026-10-31): ops/jobs/mass_check.sh (MV2_TAB block) and
# tools/mass_verdict.py (--rule v2) must leave the FIRST check's job unchanged. Runs the first check's CPU mock
# (docs/research/work/masses-transfer-20261031/cpu/mock: setup.sh, stub.py, run_mock.sh, check.py; unchanged) twice on its
# JOBS.txt string 'bash ops/jobs/mass_check.sh' (RUN_ID 20261031-mass-mocksha): OLD = mass_check.sh + mass_verdict.py of
# git BASE (default HEAD = 2ed46ea's versions, the ones the first check ran), NEW = the working tree. Compares the job log
# (timestamps and mock paths normalised), what was trained / evaluated / built (audit logs), every file written under
# results/ runs/ refs/, the store traffic, and summary.json / verify.json / verdict.txt byte for byte (mock paths
# normalised). usage: equiv_default.sh WORK
W=$1; V1=/home/user/v2d-track3/docs/research/work/masses-transfer-20261031/cpu/mock; R=/home/user/v2d-track3; rm -rf $W; mkdir -p $W
for ver in old new; do
  MR=$W/$ver; bash $V1/setup.sh $MR > /dev/null
  if [ $ver = old ]; then
    for f in ops/jobs/mass_check.sh tools/mass_verdict.py; do
      /usr/bin/git -C $R show ${BASE:-HEAD}:$f | sed "s#/content#$MR/content#g" > $MR/content/v2d-track3/$f
    done
  fi
  md5sum $MR/content/v2d-track3/ops/jobs/mass_check.sh $MR/content/v2d-track3/tools/mass_verdict.py | sed "s#$MR#MR#g" > $W/$ver.scripts
  bash $V1/run_mock.sh $MR 'bash ops/jobs/mass_check.sh'; echo "$ver rc $(cat $MR/rc.txt)"
  /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring/venv/bin/python -I $V1/check.py $MR $W/$ver.check.json 2>&1 | tail -1 || true
  norm() { sed -e "s#$MR#MR#g" -e 's/^\[[0-9T:Z-]*\] //' -e 's/"t": [0-9.e+]*/"t": T/' -e 's/pulled_[0-9]*/pulled_T/g' -e 's/prev_[0-9]*/prev_T/g' "$@"; }
  norm $MR/content/job.log | grep -v '^hf \|^cp: warning' > $W/$ver.joblog
  cat $MR/train_audit.log $MR/eval_audit.log $MR/ref_audit.log 2> /dev/null | norm | sort > $W/$ver.audit
  find $MR/content/results $MR/content/runs $MR/content/refs -type f 2> /dev/null | sed "s#$MR#MR#g" | sed 's/prev_[0-9]*/prev_T/g; s/pulled_[0-9]*/pulled_T/g' | sort > $W/$ver.files
  sed -e "s#$MR#MR#g" -e 's/: [0-9T:-]*Z$/: T/' $MR/hf.log > $W/$ver.hf
  for f in summary.json verify.json verdict.txt verify.txt; do
    norm $MR/content/results/mass_check/$f | python3 -c "import sys, re; print(re.sub(r'\"created\": \"[^\"]*\"', '\"created\": T', sys.stdin.read()), end='')" > $W/$ver.$f
  done
done
for k in joblog audit files hf summary.json verify.json verdict.txt verify.txt; do
  if cmp -s $W/old.$k $W/new.$k; then echo "$k: IDENTICAL ($(wc -l < $W/new.$k) lines)"; else echo "$k: DIFFERS"; diff $W/old.$k $W/new.$k | head -20; fi
done
echo "scripts old vs new (they must differ, the outputs must not):"; paste $W/old.scripts $W/new.scripts | awk '{print $2, $1, "->", $3}'
echo "uploads: old $(grep -c '^hf upload' $W/old.hf), new $(grep -c '^hf upload' $W/new.hf); trainings: old $(grep -c '"steps"' $W/old.audit), new $(grep -c '"steps"' $W/new.audit); evaluations: old $(grep -c '"ck"' $W/old.audit), new $(grep -c '"ck"' $W/new.audit)"
echo "verdict old: $(cat $W/old.verdict.txt)"; echo "verdict new: $(cat $W/new.verdict.txt)"
