#!/bin/bash
# A/B of the hand identity linker (2026-10-20 night): for public episodes whose perc2 perception exists, run
# hands_mp.py + mkref.py twice, A = --linker greedy into /content/refs/perc2g/epN, B = --linker viterbi into
# /content/refs/perc2v/epN, then ref_report.py for both. No training. Started by hand on the sweep box after its job;
# refreshes a 30-min HOLD while running and removes it at the end so the watchdog cleans up.
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=/content/job.log; EPS=${EPS:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
(while sleep 300; do [ -e $ST/ab_done ] && break; echo $(( $(date +%s) + 1800 )) > /content/HOLD; done) &
echo $(( $(date +%s) + 1800 )) > /content/HOLD
ln -sfn /content/perc2 /content/perc2v; ln -sfn /content/perc2 /content/perc2g   # same perception for ref_report
one() {
  local ep=$1 V=$2 R=/content/refs/perc2$2/ep$1 D
  D=$(readlink -f /content/perc2/ep$ep/depths_fs0.5.npy); mkdir -p $R
  [ -s /content/perc2/ep$ep/poses.npz ] || { log "ab $V ep$ep: no perception" >> $J; return; }
  /content/mpvenv/bin/python $P/hands_mp.py --ep $ep --linker $([ $V = g ] && echo greedy || echo viterbi) \
    --depth $D --poses /content/perc2/ep$ep/poses.npz --out $R \
    > $R/hands_log.txt 2>&1 || { log "ab $V ep$ep: hands FAILED" >> $J; return; }
  PYTHONPATH=/content/v2d/robotic_grounding/source/robotic_grounding /content/rtvenv/bin/python $P/mkref.py --ep $ep \
    --poses /content/perc2/ep$ep/poses.npz --depth $D --hands $R/hands.npz --out $R > $R/mkref_log.txt 2>&1
  log "ab $V ep$ep: mkref rc=$?" >> $J
}
label "hands A/B"
n=0
for ep in $EPS; do
  for V in g v; do
    one $ep $V &
    n=$((n + 1)); [ $((n % 6)) -eq 0 ] && wait                          # 6 runs at a time (CPU-bound)
  done
done
wait
python $P/ref_report.py perc2g > /content/results/ref_report_perc2g.txt 2>&1
python $P/ref_report.py perc2v > /content/results/ref_report_perc2v.txt 2>&1
{ echo "== A (greedy)"; cat /content/results/ref_report_perc2g.txt; echo "== B (viterbi)"; cat /content/results/ref_report_perc2v.txt; } >> $J
touch $ST/ab_done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
pgrep -f '[t]rain_runs.sh' > /dev/null || rm -f /content/HOLD          # trainings on this box keep their own hold
