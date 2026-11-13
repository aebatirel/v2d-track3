#!/bin/bash
# Static checks of the eval-10 cavity-safe retrain build (BUILD.md section 6): the default paths' files are unchanged or
# changed only as described, the new job copies e10v's recipe lines verbatim but for PIECES, every script parses.
# Usage: static_checks.sh REPO OUT.txt   (BASE = the build's base commit d153ea9)
set -u
R=$1; OUT=$2; BASE=d153ea9; fails=0
say() { echo "$1 $2" | tee -a $OUT; [ "$1" = PASS ] || fails=$((fails + 1)); }
: > $OUT
for f in ops/jobs/ev10_v4p.sh ops/jobs/ev10_nj.sh tools/e10v_score.py tools/e10v_verify.py tools/e10v_verdict.py tools/e10v_track.sh tools/e10nj.py \
         tools/no_oracle.py pipeline/make_assets.py ops/box/lib.sh ops/box/store.sh ops/box/run_job.sh ops/box/watchdog.sh tools/ckpt_curve.sh \
         tools/ckpt_curve_summary.py pipeline/qa.py ops/jobs/h5_reeval.sh ops/jobs/pack_eval.sh ops/jobs/submit_pack.sh ops/jobs/mass_eval.sh \
         ops/jobs/ep11_gate.sh tools/pack_swap_rollouts.py meshes/carve/ev10 meshes/library_v3; do
  if git -C $R diff --quiet $BASE -- $f; then say PASS "unchanged since $BASE: $f"; else say FAIL "CHANGED since $BASE: $f"; fi
done
ch=$(git -C $R diff $BASE --numstat -- ops/jobs/glock_public.sh)
add=$(git -C $R diff $BASE -- ops/jobs/glock_public.sh | grep '^+[^+]' | grep -v '^+#' | wc -l)
del=$(git -C $R diff $BASE -- ops/jobs/glock_public.sh | grep '^-[^-]' | wc -l)
[ "$add" = 1 ] && [ "$del" = 0 ] && say PASS "glock_public.sh: 1 code line added (the EVAL_CS_REF alternative of the eval PERC guard), 0 removed, the rest comments ($ch)" \
  || say FAIL "glock_public.sh: $add code lines added, $del removed ($ch)"
rec() { sed -n '/^# the packed eval-10 recipe (gl10A2) as the ep11 gate used it/,/CONTACT_RETARGET TRAIN_LOCK CK_SWEEP$/p' $1; }
d=$(diff <(rec $R/ops/jobs/ev10_v4p.sh) <(rec $R/ops/jobs/ev10_cs.sh) | grep '^[<>]')
want="< export SPLIT=eval LIB=\$REPO_DIR/meshes/library_v3 PIECES=\$REPO_DIR/meshes/carve/ev10 SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 \\
> export SPLIT=eval LIB=\$REPO_DIR/meshes/library_v3 PIECES=\$REPO_DIR/meshes/carve/\$PS SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 \\"
if [ -n "$(rec $R/ops/jobs/ev10_v4p.sh)" ] && [ "$d" = "$want" ]; then
  say PASS "ev10_cs.sh's recipe lines (export / unset, $(rec $R/ops/jobs/ev10_cs.sh | wc -l) lines) are ev10_v4p.sh's, verbatim except PIECES=meshes/carve/\$PS"
else say FAIL "ev10_cs.sh's recipe lines differ from ev10_v4p.sh's beyond PIECES: $d"; fi
cfm() { sed -n '/^  have() { ls \$G\/conf\/r\*\/ep\$EP\/qa_policy.json/,/^  done$/p' $1 | sed 's/ev10_v4p/X/g; s/ev10 v4p/X/g; s/ev10_cs/X/g; s/ev10 cs/X/g'; }
dc=$(diff <(cfm $R/ops/jobs/ev10_v4p.sh) <(cfm $R/ops/jobs/ev10_cs.sh) | grep '^[<>]')
if [ -n "$(cfm $R/ops/jobs/ev10_cs.sh)" ] && [ "$(echo "$dc" | grep -c '^[<>]')" -le 4 ]; then
  say PASS "confirm()'s draw loop is ev10_v4p.sh's but for the job name, the overflow count in the draw log line and list_results ($(echo "$dc" | grep -c '^[<>]') differing lines)"
else say FAIL "confirm() draw loop differs from ev10_v4p.sh's: $dc"; fi
for f in ops/jobs/ev10_cs.sh ops/jobs/glock_public.sh ops/jobs/ev10_v4p.sh ops/jobs/ev10_nj.sh; do bash -n $R/$f && say PASS "bash -n $f" || say FAIL "bash -n $f"; done
for f in tools/e10cs.py tools/e10cs_pieces.py tools/no_oracle.py; do python3 -m py_compile $R/$f && say PASS "py_compile $f" || say FAIL "py_compile $f"; done
grep -q 'case "${RUN_ID:-}" in \*-e10cs-\*)' $R/ops/jobs/ev10_cs.sh && say PASS "ev10_cs.sh refuses a run id without -e10cs-" || say FAIL "run-id check missing"
grep -q 'case "${PIECESET:-}" in ev10cs4|ev10cs5) ;;' $R/ops/jobs/ev10_cs.sh && say PASS "ev10_cs.sh refuses a PIECESET other than ev10cs4 / ev10cs5" || say FAIL "PIECESET check missing"
n=$(grep -c 'EVAL_CS_REF=1' $R/ops/jobs/ev10_cs.sh); grep -q 'REUSE_REF=1 REQUIRE_REUSE=1 EVAL_CS_REF=1 SEED=$s' $R/ops/jobs/ev10_cs.sh \
  && say PASS "the opt-in goes to the glock_public.sh training calls only ($n mentions)" || say FAIL "EVAL_CS_REF hand-off not found"
grep -q 'sim\.njmax\|sim\.nconmax' $R/ops/jobs/ev10_cs.sh && say FAIL "ev10_cs.sh names a sim limit" || say PASS "ev10_cs.sh passes no sim limit (stock 512 / 256)"
for s in ev10cs4 ev10cs5; do python3 $R/tools/e10cs_pieces.py check --dir $R/meshes/carve/$s > /dev/null && say PASS "piece set $s: check ok (MD5SUMS = files = FROZEN.md)" || say FAIL "piece set $s check"; done
python3 $R/tools/e10cs_pieces.py compare --base $R/meshes/carve/ev10cs4 --cand $R/meshes/carve/ev10cs5 > /dev/null && say PASS "ev10cs5 vs ev10cs4: clause (a) holds" || say FAIL "clause (a)"
echo "RESULT: $([ $fails = 0 ] && echo ALL PASS || echo "$fails FAILED")" | tee -a $OUT
[ $fails = 0 ]
