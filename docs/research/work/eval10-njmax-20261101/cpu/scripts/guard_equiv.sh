#!/bin/bash
# Proof that the opt-in EVAL_NJ_DIAG change of ops/jobs/glock_public.sh leaves every default PERC decision unchanged
# (eval-10 njmax diagnostic, BUILD.md section 5; after ev10retrain/cpu/scripts/guard_equiv.sh). The PERC guard block of
# one() (from `if [ "$perc" != perc2 ]` to the `pre=${perc}_` line and the `fi` after it) is cut out of the build's base
# commit (68f1421, OLD) and of the working tree (NEW) and run as a function over SPLIT x PERC x RUN x REQUIRE_REUSE x
# episode x EVAL_LOCAL_REF x FC_DR_PATCH x EVAL_NJ_DIAG; each case prints its decision (allowed + prefix, or refused + the
# logged message). OLD vs NEW must be identical on every case with EVAL_NJ_DIAG unset or 0; with EVAL_NJ_DIAG=1 the only
# differences are perc2e10njs<seed>, SPLIT=eval, episode 10, RUN local, REQUIRE_REUSE=1. Usage: guard_equiv.sh REPO OUTDIR
set -u
R=$1; O=$2; mkdir -p $O
cut_guard() {  # $1 file -> the guard block as the body of a function g()
  awk '/if \[ "\$perc" != perc2 \]; then/{f=1} f{print} f&&/pre=\$\{perc\}_;/{getline; print; exit}' $1
}
git -C $R show 68f1421:ops/jobs/glock_public.sh > $O/glock_public_base.sh
for v in OLD NEW; do
  f=$([ $v = OLD ] && echo $O/glock_public_base.sh || echo $R/ops/jobs/glock_public.sh)
  { echo 'log() { echo "LOG $*"; }'; echo 'g() { local ep=$1 run=$2 base=$3 perc=$4 pre=""; J=/dev/stdout'
    cut_guard $f; echo '  echo "ALLOWED pre=$pre"; }'; } > $O/guard_$v.sh
  : > $O/decisions_$v.txt
  for split in public eval; do for perc in perc2 perc2e10v perc2e10vs43 perc2e10nj perc2e10njs42 perc2e10njs43 perc2e10njsx perc2e10njs43x e10njs43 mass1s42 drs42 oracle; do
  for run in local new 20261031-e10v-caf38fb; do for rr in "" 0 1; do for ep in 10 11; do for elr in unset 1; do for dr in unset 1; do for nj in unset 0 1; do
    out=$( ( . $O/guard_$v.sh; SPLIT=$split; if [ -n "$rr" ]; then REQUIRE_REUSE=$rr; else unset REQUIRE_REUSE; fi
             if [ $elr = unset ]; then unset EVAL_LOCAL_REF; else EVAL_LOCAL_REF=$elr; fi
             if [ $dr = unset ]; then unset FC_DR_PATCH; else FC_DR_PATCH=$dr; fi
             if [ $nj = unset ]; then unset EVAL_NJ_DIAG; else EVAL_NJ_DIAG=$nj; fi
             g $ep $run mck $perc 2>&1 | tr '\n' ' '; echo "rc=${PIPESTATUS[0]}" ) )
    echo "split=$split perc=$perc run=$run REQUIRE_REUSE=${rr:-unset} ep=$ep EVAL_LOCAL_REF=$elr FC_DR_PATCH=$dr EVAL_NJ_DIAG=$nj :: $out" >> $O/decisions_$v.txt
  done; done; done; done; done; done; done; done
done
n=$(wc -l < $O/decisions_OLD.txt)
d_def=$(diff <(grep -v 'EVAL_NJ_DIAG=1 ' $O/decisions_OLD.txt) <(grep -v 'EVAL_NJ_DIAG=1 ' $O/decisions_NEW.txt) | grep -c '^[<>]')
diff $O/decisions_OLD.txt $O/decisions_NEW.txt | grep '^>' > $O/changed_with_opt_in.txt
bad=$(grep -v 'split=eval perc=perc2e10njs4[23] run=local REQUIRE_REUSE=1 ep=10 .* EVAL_NJ_DIAG=1 ' $O/changed_with_opt_in.txt | wc -l)
allowed=$(grep -c 'ALLOWED' $O/changed_with_opt_in.txt)
echo "cases $n; differing with EVAL_NJ_DIAG unset/0: $d_def; changed with EVAL_NJ_DIAG=1: $(wc -l < $O/changed_with_opt_in.txt) (all newly ALLOWED: $allowed; outside perc2e10njs<seed> / eval / ep 10 / local / REQUIRE_REUSE=1: $bad)" | tee $O/summary.txt
[ "$d_def" = 0 ] && [ "$bad" = 0 ]
