#!/bin/bash
# Static checks of the eval-20 b1 retrain build (BUILD.md section 6). Usage: static_checks.sh REPO OUT.txt
R=$1; O=$2; B=7bac1b53; fail=0; : > $O
chk() { if eval "$2"; then echo "PASS $1" >> $O; else echo "FAIL $1" >> $O; fail=1; fi; }
cd $R
ch=$(git diff --name-only $B -- . ; git ls-files --others --exclude-standard)
chk "only the intended files differ from the base $B (glock_public.sh, ev20_b1.sh, e20b1.py, meshes/carve/ev20b1, the work folder)" \
  '[ -z "$(echo "$ch" | sort -u | grep -v "^ops/jobs/glock_public.sh$\|^ops/jobs/ev20_b1.sh$\|^tools/e20b1.py$\|^meshes/carve/ev20b1/\|^docs/research/work/eval20-b1-20261101/")" ]'
for f in pipeline/placement_carve.py pipeline/make_assets.py tools/no_oracle.py tools/dr_score.py tools/dr_verdict.py tools/e10v_score.py tools/e10cs.py \
         tools/e10cs_pieces.py tools/e10nj.py tools/mass_verify.py tools/mass_arm.py tools/e11g_verify.py ops/jobs/ev10_cs.sh ops/jobs/ev10_v4p.sh \
         ops/jobs/mass_eval.sh ops/box/lib.sh ops/box/store.sh ops/box/run_job.sh meshes/library_v3 docs/research/work/masses-eval-20261031/packed_refs.json; do
  chk "unchanged since $B: $f" "git diff --quiet $B -- $f"
done
add=$(git diff $B -- ops/jobs/glock_public.sh | grep '^+[^+]' | grep -v '^+#' | wc -l); del=$(git diff $B -- ops/jobs/glock_public.sh | grep '^-[^-]' | wc -l)
chk "glock_public.sh: 1 code line added (the EVAL_E20B1 guard), 0 removed (got +$add / -$del)" '[ $add = 1 ] && [ $del = 0 ]'
chk "the added line is the EVAL_E20B1 / e20b1s<seed> / ep 20 / local / REQUIRE_REUSE=1 guard" \
  'git diff $B -- ops/jobs/glock_public.sh | grep "^+[^+#]" | grep -q "EVAL_E20B1:-0}\" = 1 \] && \[ \"\$ep\" = 20 \] && \[\[ \$perc =~ \^e20b1s\[0-9\]+\$ \]\] && \[ \"\$run\" = local \] && \[ \"\${REQUIRE_REUSE:-0}\" = 1 \]"'
chk "bash -n ev20_b1.sh, glock_public.sh" 'bash -n ops/jobs/ev20_b1.sh && bash -n ops/jobs/glock_public.sh'
chk "py_compile e20b1.py and the CPU scripts" 'python3 -m py_compile tools/e20b1.py docs/research/work/eval20-b1-20261101/cpu/scripts/*.py docs/research/work/eval20-b1-20261101/cpu/mock/*.py'
chk "ev20_b1.sh names no sim.* override and no TRAIN_ARGS of its own (stock limits; fc_patches sets TRAIN_ARGS)" \
  '! grep -v "^#" ops/jobs/ev20_b1.sh | grep -q "sim\.njmax\|sim\.nconmax\|TRAIN_ARGS=" '
chk "ev20_b1.sh never calls make_assets.py --pieces and unsets PIECES" '! grep -v "^ *#" ops/jobs/ev20_b1.sh | grep -q "make_assets.py" && grep -q "^unset PIECES " ops/jobs/ev20_b1.sh'
chk "ev20_b1.sh applies the pieces with placement_carve.py assets on refs/sf/ep20/assets (A=/content/refs/sf/ep\$EP/assets)" \
  'grep -q "A=/content/refs/sf/ep\$EP/assets" ops/jobs/ev20_b1.sh && grep -q "placement_carve.py assets \$A \$PIECES_DIR /content/sf20_b1" ops/jobs/ev20_b1.sh'
chk "ev20_b1.sh exports SF=0 and the packed GL_ARGS / REPLAN 1 / EVOLVE 0 / STEPS 70004736 / CURVE_REP 3" \
  'grep -q "SF=0 SETTLE=0 REPLAN=1 EVOLVE=0 CURVE_REP=3" ops/jobs/ev20_b1.sh && grep -q "STEPS=70004736" ops/jobs/ev20_b1.sh && grep -q -- "--wrap_where_held 1 --snap 1 --approach_cm 15\"" ops/jobs/ev20_b1.sh'
d=$(diff <(awk '/^confirm\(\) \{/,/^}/' ops/jobs/ev10_cs.sh) <(awk '/^confirm\(\) \{/,/^}/' ops/jobs/ev20_b1.sh) | grep -c '^[<>]')
chk "confirm() is ev10_cs.sh's verbatim but for names (raw differing lines: $d; job name, label, kit key '10' -> '20')" \
  'python3 -I docs/research/work/eval20-b1-20261101/cpu/scripts/confirm_same.py ops/jobs/ev10_cs.sh ops/jobs/ev20_b1.sh > /dev/null'
chk "the piece set passes tools/e20b1.py pieces (pinned MD5SUMS / FROZEN.md)" 'python3 -I tools/e20b1.py pieces --dir meshes/carve/ev20b1 --out /dev/null > /dev/null'
chk "no_oracle accepts the piece set" 'python3 -I tools/no_oracle.py meshes/carve/ev20b1 > /dev/null'
chk "the piece set's 41 files are byte-identical at bold-albattani 9c0bc0c and 83d18d0" \
  'for c in 9c0bc0c9 83d18d09; do for f in meshes/carve/ev20b1/water_pitcher/piece_*.obj; do [ "$(git show $c:docs/research/mesh-2026-10-26/rebase/sets/ev20/water_pitcher/$(basename $f) | md5sum | cut -c1-32)" = "$(md5sum < $f | cut -c1-32)" ] || exit 1; done; done'
echo "$([ $fail = 0 ] && echo ALL PASS || echo SOME FAILED) ($(grep -c ^PASS $O) pass, $(grep -c ^FAIL $O) fail)" >> $O
cat $O; exit $fail
