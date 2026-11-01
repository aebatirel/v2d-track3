#!/bin/bash
# Proof that the opt-in EVAL_E20B1 change of ops/jobs/glock_public.sh leaves every default PERC decision unchanged (eval-20 b1
# retrain, BUILD.md section 6; after eval10-cs4-20261101/cpu/scripts/guard_equiv.sh). The PERC guard block of one() (from
# `if [ "$perc" != perc2 ]` to the `pre=${perc}_` line and the `fi` after it) is cut out of the build's base commit (7bac1b5,
# OLD) and of the working tree (NEW) and run as a function over SPLIT x PERC x RUN x REQUIRE_REUSE x episode x EVAL_LOCAL_REF x
# FC_DR_PATCH x EVAL_CS_REF x EVAL_E20B1; each case prints its decision (allowed + prefix, or refused + the logged message).
# OLD vs NEW must be identical on every case with EVAL_E20B1 unset or 0; with EVAL_E20B1=1 the only differences are
# e20b1s<seed>, SPLIT=eval, episode 20, RUN local, REQUIRE_REUSE=1. Usage: guard_equiv.sh REPO OUTDIR
set -u
R=$1; O=$2; mkdir -p $O
cut_guard() {  # $1 file -> the guard block as the body of a function g()
  awk '/if \[ "\$perc" != perc2 \]; then/{f=1} f{print} f&&/pre=\$\{perc\}_;/{getline; print; exit}' $1
}
git -C $R show 7bac1b53:ops/jobs/glock_public.sh > $O/glock_public_base.sh
for v in OLD NEW; do
  f=$([ $v = OLD ] && echo $O/glock_public_base.sh || echo $R/ops/jobs/glock_public.sh)
  { echo 'log() { echo "LOG $*"; }'; echo 'g() { local ep=$1 run=$2 base=$3 perc=$4 pre=""; J=/dev/stdout'
    cut_guard $f; echo '  echo "ALLOWED pre=$pre"; }'; } > $O/guard_$v.sh
  : > $O/decisions_$v.txt
  for split in public eval; do for perc in perc2 e20b1s42 e20b1s43 e20b1sx e20b1s43x xe20b1s42 e20b1 perc2e10css42 perc2e10vs43 mass1s42 drs42 oracle; do
  for run in local new 20261025-evb1420-ee7ba8e; do for rr in "" 0 1; do for ep in 10 20 21; do for elr in unset 1; do for dr in unset 1; do for cs in unset 1; do for eb in unset 0 1; do
    out=$( ( . $O/guard_$v.sh; SPLIT=$split; if [ -n "$rr" ]; then REQUIRE_REUSE=$rr; else unset REQUIRE_REUSE; fi
             if [ $elr = unset ]; then unset EVAL_LOCAL_REF; else EVAL_LOCAL_REF=$elr; fi
             if [ $dr = unset ]; then unset FC_DR_PATCH; else FC_DR_PATCH=$dr; fi
             if [ $cs = unset ]; then unset EVAL_CS_REF; else EVAL_CS_REF=$cs; fi
             if [ $eb = unset ]; then unset EVAL_E20B1; else EVAL_E20B1=$eb; fi
             unset EVAL_NJ_DIAG
             g $ep $run mck $perc 2>&1 | tr '\n' ' '; echo "rc=${PIPESTATUS[0]}" ) )
    echo "split=$split perc=$perc run=$run REQUIRE_REUSE=${rr:-unset} ep=$ep EVAL_LOCAL_REF=$elr FC_DR_PATCH=$dr EVAL_CS_REF=$cs EVAL_E20B1=$eb :: $out" >> $O/decisions_$v.txt
  done; done; done; done; done; done; done; done; done
done
n=$(wc -l < $O/decisions_OLD.txt)
d_def=$(diff <(grep -v 'EVAL_E20B1=1 ' $O/decisions_OLD.txt) <(grep -v 'EVAL_E20B1=1 ' $O/decisions_NEW.txt) | grep -c '^[<>]')
diff $O/decisions_OLD.txt $O/decisions_NEW.txt | grep '^>' > $O/changed_with_opt_in.txt
bad=$(grep -v 'split=eval perc=e20b1s4[23] run=local REQUIRE_REUSE=1 ep=20 .* EVAL_E20B1=1 ' $O/changed_with_opt_in.txt | wc -l)
allowed=$(grep -c 'ALLOWED' $O/changed_with_opt_in.txt)
echo "cases $n; differing with EVAL_E20B1 unset/0: $d_def; changed with EVAL_E20B1=1: $(wc -l < $O/changed_with_opt_in.txt) (all newly ALLOWED: $allowed; outside e20b1s<seed> / eval / ep 20 / local / REQUIRE_REUSE=1: $bad)" | tee $O/summary.txt
rm -f $O/decisions_OLD.txt $O/decisions_NEW.txt $O/guard_OLD.sh $O/guard_NEW.sh $O/glock_public_base.sh
[ "$d_def" = 0 ] && [ "$bad" = 0 ]
