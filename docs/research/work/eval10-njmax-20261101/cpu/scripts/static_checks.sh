#!/bin/bash
# Static checks of the eval-10 njmax diagnostic build (BUILD.md section 5): the default paths' files are unchanged or
# changed only as described, the new job copies e10v's recipe lines verbatim, every script parses.
# Usage: static_checks.sh REPO OUT.txt   (BASE = the build's base commit 68f1421)
set -u
R=$1; OUT=$2; BASE=68f1421; fails=0
say() { echo "$1 $2" | tee -a $OUT; [ "$1" = PASS ] || fails=$((fails + 1)); }
: > $OUT
for f in ops/jobs/ev10_v4p.sh tools/e10v_score.py tools/e10v_verify.py tools/e10v_verdict.py tools/e10v_track.sh ops/box/lib.sh ops/box/store.sh \
         ops/box/run_job.sh ops/box/watchdog.sh tools/ckpt_curve.sh tools/ckpt_curve_summary.py pipeline/qa.py ops/jobs/h5_reeval.sh ops/jobs/pack_eval.sh \
         ops/jobs/submit_pack.sh ops/jobs/mass_eval.sh ops/jobs/ep11_gate.sh; do
  if git -C $R diff --quiet $BASE -- $f; then say PASS "unchanged since $BASE: $f"; else say FAIL "CHANGED since $BASE: $f"; fi
done
ch=$(git -C $R diff $BASE --numstat -- ops/jobs/glock_public.sh)
add=$(git -C $R diff $BASE -- ops/jobs/glock_public.sh | grep '^+[^+]' | grep -v '^+#' | wc -l)
del=$(git -C $R diff $BASE -- ops/jobs/glock_public.sh | grep '^-[^-]' | wc -l)
[ "$add" = 1 ] && [ "$del" = 0 ] && say PASS "glock_public.sh: 1 code line added (the EVAL_NJ_DIAG alternative of the eval PERC guard), 0 removed, the rest comments ($ch)" \
  || say FAIL "glock_public.sh: $add code lines added, $del removed ($ch)"
rec() { sed -n '/^# the packed eval-10 recipe (gl10A2) as the ep11 gate used it/,/CONTACT_RETARGET TRAIN_LOCK CK_SWEEP$/p' $1; }
if [ -n "$(rec $R/ops/jobs/ev10_v4p.sh)" ] && diff <(rec $R/ops/jobs/ev10_v4p.sh) <(rec $R/ops/jobs/ev10_nj.sh) > /dev/null; then
  say PASS "ev10_nj.sh's recipe lines (export / unset, $(rec $R/ops/jobs/ev10_nj.sh | wc -l) lines) are ev10_v4p.sh's, verbatim"
else say FAIL "ev10_nj.sh's recipe lines differ from ev10_v4p.sh's"; fi
for f in ops/jobs/ev10_nj.sh ops/jobs/glock_public.sh ops/jobs/ev10_v4p.sh; do bash -n $R/$f && say PASS "bash -n $f" || say FAIL "bash -n $f"; done
for f in tools/e10nj.py tools/e10nj_solver_check.py tools/no_oracle.py tools/pack_swap_rollouts.py; do
  python3 -m py_compile $R/$f && say PASS "py_compile $f" || say FAIL "py_compile $f"; done
grep -q 'case "${RUN_ID:-}" in \*-e10nj-\*)' $R/ops/jobs/ev10_nj.sh && say PASS "ev10_nj.sh refuses a run id without -e10nj-" || say FAIL "run-id check missing"
n=$(grep -c 'NJ_ARGS' $R/ops/jobs/ev10_nj.sh); grep -q 'TRAIN_ARGS="$NJ_ARGS" bash $REPO_DIR/ops/jobs/glock_public.sh' $R/ops/jobs/ev10_nj.sh \
  && say PASS "the sim overrides go to the one glock_public.sh training call only (NJ_ARGS used $n times)" || say FAIL "TRAIN_ARGS hand-off not found"
echo "RESULT: $([ $fails = 0 ] && echo ALL PASS || echo "$fails FAILED")" | tee -a $OUT
[ $fails = 0 ]
