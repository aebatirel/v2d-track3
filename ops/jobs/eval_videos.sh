#!/bin/bash
# Videos of the submitted eval policies for the owner (2026-10-24, "I need the videos of all the 20 evals"; reporting
# only: no ground truth, nothing is chosen from them). Pulls the eval runs (the first run listed wins, as in
# pack_eval.sh), sets FlashCHORD up as glock_public.sh does, then per episode:
#   ops/jobs/vid_after.sh: the chosen checkpoint played like the official evaluator (frame 0 to the end, no assist, no
#     termination), recorded as a body-pose trace, with FlashCHORD's own 3-D render (view.mp4);
#   tools/sim_vs_real_video.py: real camera a | simulated objects, our reference outline and the robot hand skeleton
#     drawn on camera a | the 3-D render.
# Output: /content/results/eval_videos/ep<N>.mp4 plus per-episode traces under results/glock_public/ep<N>/vid/.
# The replay is a fresh rollout of the same checkpoint, so it can differ from the packed rollout where an episode has
# two outcome modes (3, 5, 15).
# Usage: RUNS="..." EPS="1 3 ..." [SCORES="1:0.205 3:0.875 ..."] [PAR=3] bash ops/jobs/eval_videos.sh
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; OUTV=/content/results/eval_videos; mkdir -p $OUTV
FC=/content/v2d/robotic_grounding/flash_chord; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
for r in ${RUNS:?RUNS missing}; do bash $OPS/store.sh pull-run $r >> $J 2>&1 || log "eval_videos: pull-run $r FAILED" >> $J; done
pip install -q fast_simplification manifold3d >> $J 2>&1 || true
python $REPO_DIR/pipeline/make_assets.py $LIB /content/assets >> $J 2>&1 || { log "eval_videos: make_assets FAILED" >> $J; exit 1; }
fc_patches $J || exit 1
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml
[ -s $E ] || cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E

one() {
  local ep=$1 O V REF MD sc
  O=/content/results/glock_public/ep$ep; V=$O/vid
  bash $REPO_DIR/ops/jobs/vid_after.sh $ep >> /content/vid_ep$ep.log 2>&1
  if [ ! -s $V/policy_trace.npz ] || [ ! -s $V/view.mp4 ]; then
    log "eval_videos ep$ep: trace/view FAILED ($(tail -2 $V/trace.log 2>/dev/null | tr '\n' ' ' | cut -c1-200))" >> $J; return 1
  fi
  REF=$(ls /content/refs/glockt/ep$ep/processed/*/*/ref_gl_ilc.parquet | head -1)
  MD=/content/refs/sf/ep$ep/assets/mesh; [ -d $MD ] || MD=/content/assets/mesh
  sc=$(echo " ${SCORES:-} " | grep -o " $ep:[0-9.]*" | cut -d: -f2)
  python $REPO_DIR/tools/sim_vs_real_video.py $V/policy_trace.npz $REF /content/refs/perc2mck/ep$ep /content/perc2/ep$ep \
      /content/t3/eval/v/ep${ep}_a.mp4 $MD $V/view.mp4 $OUTV/ep$ep.mp4 \
      --title "eval $ep: submitted policy, played like the official evaluator" \
      --score "${sc:+submitted rollout: sim_vs_ref $sc vs our reference (not ground truth)}" > $V/svr.log 2>&1 \
    && log "eval_videos ep$ep: $(du -h $OUTV/ep$ep.mp4 | cut -f1), rest check $(cut -c1-200 $V/rest_check_policy.json)" >> $J \
    || log "eval_videos ep$ep: sim_vs_real FAILED ($(tail -2 $V/svr.log | tr '\n' ' ' | cut -c1-200))" >> $J
}

pids=()
for ep in ${EPS:?EPS missing}; do
  one $ep & pids+=($!)
  [ ${#pids[@]} -ge ${PAR:-3} ] && { wait "${pids[@]}"; pids=(); }
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
log "eval_videos: $(ls $OUTV/*.mp4 2>/dev/null | wc -l) videos" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
