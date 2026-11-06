#!/bin/bash
# Proof that the opt-in EVAL_LOCAL_REF change of ops/jobs/glock_public.sh leaves every default PERC decision unchanged
# (2026-10-31, ev10retrain BUILD.md section 4). The PERC guard block of one() (from `if [ "$perc" != perc2 ]` to the
# `pre=${perc}_` line and the `fi` after it) is cut out of the committed file (git HEAD, OLD) and of the working tree (NEW) and run as a
# function over a matrix of SPLIT x PERC x RUN x REQUIRE_REUSE x episode x EVAL_LOCAL_REF; each case prints its decision
# (allowed + prefix, or refused + the logged message). Output: OLD vs NEW must be identical on every case with
# EVAL_LOCAL_REF unset or 0; with EVAL_LOCAL_REF=1 the only differences are perc2e10v / perc2e10vs<seed>, SPLIT=eval,
# episode 10, RUN local. Usage: guard_equiv.sh REPO OUTDIR
set -u
R=$1; O=$2; mkdir -p $O
cut_guard() {  # $1 file -> the guard block as the body of a function g()
  awk '/if \[ "\$perc" != perc2 \]; then/{f=1} f{print} f&&/pre=\$\{perc\}_;/{getline; print; exit}' $1
}
git -C $R show HEAD:ops/jobs/glock_public.sh > $O/glock_public_HEAD.sh
for v in OLD NEW; do
  f=$([ $v = OLD ] && echo $O/glock_public_HEAD.sh || echo $R/ops/jobs/glock_public.sh)
  { echo 'log() { echo "LOG $*"; }'; echo 'g() { local ep=$1 run=$2 base=$3 perc=$4 pre=""; J=/dev/stdout'
    cut_guard $f; echo '  echo "ALLOWED pre=$pre"; }'; } > $O/guard_$v.sh
  : > $O/decisions_$v.txt
  for split in public eval; do for perc in perc2 perc2e10v perc2e10vs42 perc2e10vs43 perc2e10vx perc2e10vs mass1s42 mass1 oracle perc2e11c perc2e11ts42 e10v; do
  for run in local new 20261026-gl10A2-5e0e100; do for rr in "" 0 1; do for ep in 10 11 8; do for elr in unset 0 1; do
    out=$( ( . $O/guard_$v.sh; SPLIT=$split; if [ -n "$rr" ]; then REQUIRE_REUSE=$rr; else unset REQUIRE_REUSE; fi
             if [ $elr = unset ]; then unset EVAL_LOCAL_REF; else EVAL_LOCAL_REF=$elr; fi
             g $ep $run mck $perc 2>&1 | tr '\n' ' '; echo "rc=${PIPESTATUS[0]}" ) )
    echo "split=$split perc=$perc run=$run REQUIRE_REUSE=${rr:-unset} ep=$ep EVAL_LOCAL_REF=$elr :: $out" >> $O/decisions_$v.txt
  done; done; done; done; done; done
done
n=$(wc -l < $O/decisions_OLD.txt)
d_def=$(diff <(grep -v 'EVAL_LOCAL_REF=1 ' $O/decisions_OLD.txt) <(grep -v 'EVAL_LOCAL_REF=1 ' $O/decisions_NEW.txt) | grep -c '^[<>]')
diff $O/decisions_OLD.txt $O/decisions_NEW.txt | grep '^>' > $O/changed_with_opt_in.txt
bad=$(grep -v 'split=eval perc=perc2e10v\(s4[23]\)\? run=local .* ep=10 EVAL_LOCAL_REF=1 ' $O/changed_with_opt_in.txt | wc -l)
echo "cases $n; differing with EVAL_LOCAL_REF unset/0: $d_def; changed with EVAL_LOCAL_REF=1: $(wc -l < $O/changed_with_opt_in.txt) (outside perc2e10v[s<seed>] / eval / ep 10 / local: $bad)" | tee $O/summary.txt
[ "$d_def" = 0 ] && [ "$bad" = 0 ]
