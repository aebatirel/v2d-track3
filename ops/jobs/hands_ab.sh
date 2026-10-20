#!/bin/bash
# A/B of the hand identity linker (2026-10-20 night): rerun hands_mp.py (--linker viterbi, the new default) and mkref.py
# for public episodes whose perc2 perception exists, into /content/refs/perc2v/epN, then ref_report.py for both
# variants. perc2 (refs_sweep.sh, greedy linker) is A, perc2v is B. No training. Started by hand on the sweep box
# after its job; refreshes a 30-min HOLD while running and removes it at the end so the watchdog cleans up.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log; EPS=${EPS:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
(while sleep 300; do [ -e $ST/ab_done ] && break; echo $(( $(date +%s) + 1800 )) > /content/HOLD; done) &
echo $(( $(date +%s) + 1800 )) > /content/HOLD
ln -sfn /content/perc2 /content/perc2v                                  # same perception; ref_report reads it
one() {
  local ep=$1 R=/content/refs/perc2v/ep$1 D
  D=$(readlink -f /content/perc2/ep$ep/depths_fs0.5.npy); mkdir -p $R
  [ -s /content/perc2/ep$ep/poses.npz ] || { log "ab ep$ep: no perception" >> $J; return; }
  /content/mpvenv/bin/python $P/hands_mp.py --ep $ep --depth $D --poses /content/perc2/ep$ep/poses.npz --out $R \
    > $R/hands_log.txt 2>&1 || { log "ab ep$ep: hands FAILED" >> $J; return; }
  PYTHONPATH=/content/v2d/robotic_grounding/source/robotic_grounding /content/rtvenv/bin/python $P/mkref.py --ep $ep \
    --poses /content/perc2/ep$ep/poses.npz --depth $D --hands $R/hands.npz --out $R > $R/mkref_log.txt 2>&1
  log "ab ep$ep: mkref rc=$?" >> $J
}
label "hands A/B"
n=0
for ep in $EPS; do
  one $ep &
  n=$((n + 1)); [ $((n % 4)) -eq 0 ] && wait                            # 4 episodes at a time
done
wait
python $P/ref_report.py perc2  > /content/results/ref_report_perc2.txt 2>&1
python $P/ref_report.py perc2v > /content/results/ref_report_perc2v.txt 2>&1
{ echo "== A (greedy)"; cat /content/results/ref_report_perc2.txt; echo "== B (viterbi)"; cat /content/results/ref_report_perc2v.txt; } >> $J
touch $ST/ab_done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
rm -f /content/HOLD
