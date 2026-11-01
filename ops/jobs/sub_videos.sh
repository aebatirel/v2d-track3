#!/bin/bash
# Videos of the SUBMITTED policies of a pack (2026-10-26; owner: "get the videos of our current episodes", then forensics;
# reporting only: no ground truth, nothing is chosen from them). eval_videos.sh handled grasp-lock policies only; the
# third pack mixes standard-learner, grasp-lock and frozen-recipe policies, so this job follows the pack itself:
#   1. pulls what PACK_RUN's pack_eval.sh pulled (RUNS with their sub-folders, then the fallback run) plus, per source run
#      and episode, the base reference and perception the side-by-side video needs (refs/perc2mck, refs/perc2mcks,
#      refs/glockt, refs/sf, perc2); PICK checkpoints exactly as pack_eval.sh;
#   2. the checkpoint per episode = PACK_RUN's results/final_eval/checkpoints.json, verified against the sha256 recorded in
#      the pack's official rollout (results/submission/results/episode_XXXXXX.json): a video of another file is refused;
#   3. per episode: the checkpoint played like the official evaluator (frame 0 to the end, no assist, no termination) on
#      the reference stored in the checkpoint's own config, with FlashCHORD's 3-D render (view.mp4) and a body-pose trace
#      (tools/trace_rollout.py; CONTACTS=1 records contact forces for the forensics); then tools/sim_vs_real_video.py.
# A replay is a fresh rollout: where a policy has two outcome modes it can differ from the packed rollout (the packed
# rollouts themselves are rendered on CPU by tools/render_eval_rollout.py).
# Usage: PACK_RUN=20261025-pack3-3758189 RUNS="<as the pack>" PICK="<as the pack>" [EPS="1 3 ..."] [PAR=3] bash ops/jobs/sub_videos.sh
# Output: /content/results/sub_videos/ep<N>.mp4 and /content/results/sub_videos/ep<N>/{view.mp4,policy_trace.npz,...}
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; OUTV=/content/results/sub_videos; mkdir -p $OUTV
FC=/content/v2d/robotic_grounding/flash_chord; LIB=${LIB:-$REPO_DIR/meshes/library_v3}; PR=${PACK_RUN:?PACK_RUN missing}
log "sub_videos code $(git -C $REPO_DIR rev-parse --short HEAD), pack $PR" >> $J
label "sub_videos $PR"
for inc in "runs/$PR/results/final_eval/checkpoints.json" "runs/$PR/results/submission/results/episode_*.json" \
           "runs/$PR/results/submission/summary.txt"; do                # one pattern per call (26 Oct: three patterns in one
  hf download "$HF_STORE" --repo-type dataset --include "$inc" --local-dir /content/packinfo >> $J 2>&1 \
    || { log "sub_videos: pack info $inc download FAILED" >> $J; exit 1; }   # --include fetched nothing, 0 videos)
done
PI=/content/packinfo/runs/$PR/results
EPS=${EPS:-$(python -c "import json; print(' '.join(sorted(json.load(open('$PI/final_eval/checkpoints.json')), key=int)))")}
[ -n "$EPS" ] || { log "sub_videos: no episodes (checkpoints.json missing?)" >> $J; exit 1; }
for x in ${RUNS:-}; do                                 # as pack_eval.sh (first run wins), plus the video inputs
  r=${x%%@*}; sub=; [ "$r" != "$x" ] && sub=${x#*@}
  if [ -n "$sub" ]; then                                           # + base reference and perception of this run's episodes
    eps=$( { echo "$sub" | grep -o 'ep[0-9]*' | tr -d ep; for p in ${PICK:-}; do IFS=: read -r e pr _ <<< "$p"; [ "$pr" = "$r" ] && echo $e; done; } | sort -un)
    PULL_SUB="${sub//,/ }" bash $OPS/store.sh pull-run $r >> $J 2>&1 || log "sub_videos: pull-run $x FAILED" >> $J
    for e in $eps; do for f in refs/perc2mck/ep$e refs/perc2mcks/ep$e perc2/ep$e; do   # one call each: a folder the run
      PULL_SUB=$f bash $OPS/store.sh pull-run $r >> $J 2>&1 || true                       # lacks must not stop the others
    done; done
  else
    bash $OPS/store.sh pull-run $r >> $J 2>&1 || log "sub_videos: pull-run $r FAILED" >> $J
  fi
done
for x in ${PICK:-}; do                                             # as pack_eval.sh
  IFS=: read -r ep r kind <<< "$x"; d=/content/pick/$r; mkdir -p $d
  sub=results/glock_public/ep$ep/best; [ "$kind" = final ] && sub=results/final_eval/ep$ep
  if [ "${kind#ck=}" != "$kind" ]; then                            # EP:RUN:ck=<path in the run>, as pack_eval.sh (1 Nov:
    hf download "$HF_STORE" --repo-type dataset --include "runs/$r/${kind#ck=}" --local-dir $d > /dev/null \
      || log "sub_videos: PICK $x FAILED" >> $J                    # the 30 Oct eval-25 video failed without this branch)
  else
  hf download "$HF_STORE" --repo-type dataset --include "runs/$r/$sub/*" --local-dir $d > /dev/null || log "sub_videos: PICK $x FAILED" >> $J
  fi
done
pip install -q fast_simplification manifold3d >> $J 2>&1 || true
if [ -n "${ASSET_PIECES:-}" ] && [ "$(echo $ASSET_PIECES | wc -w)" -gt 1 ]; then   # several folders: merged per object,
  PM=/content/pieces_merged; mkdir -p $PM                                          # first wins (as pack_eval.sh, 30 Oct)
  for d in $ASSET_PIECES; do for o in $d/*/; do [ -n "$(ls $o/piece_*.obj 2>/dev/null)" ] && [ ! -e $PM/$(basename $o) ] && ln -s $(readlink -f $o) $PM/$(basename $o); done; done
  log "sub_videos: merged collision pieces: $(ls $PM | tr '\n' ' ')" >> $J; ASSET_PIECES=$PM
fi
python $REPO_DIR/pipeline/make_assets.py $LIB /content/assets ${ASSET_PIECES:+--pieces $ASSET_PIECES} ${MA_ARGS:-} >> $J 2>&1 || { log "sub_videos: make_assets FAILED" >> $J; exit 1; }
fc_patches $J || exit 1
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml; [ -s $E ] || cp $REPO_DIR/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E
mkdir -p /workspace && { [ -e /workspace/refs ] || ln -s /content/refs /workspace/refs; } && { [ -e /workspace/pick ] || ln -s /content/pick /workspace/pick; }

one() {  # $1 episode, $2 optional replay tag (REPLAYS, 1 Nov): outputs ep<N>_<tag>.mp4 and folder ep<N>_<tag>
  local ep=$1 tag=${2:-} E6 CK sha want TASK REFDIR N MD O sc NAME
  E6=$(printf %06d $ep); NAME=ep$ep${tag:+_$tag}; O=$OUTV/$NAME; mkdir -p $O
  # the checkpoint the SUBMITTED rollout names (26 Oct: for 3/5/15/16 pack 3's checkpoints.json said seed 43 but the
  # packed rollouts are the first pack's seed-42 ones, kept by cp -n), else the pack's checkpoints.json entry
  CK=$(python -c "import json; print(json.load(open('$PI/submission/results/episode_$E6.json'))['checkpoint'])" | sed 's#^/workspace/#/content/#')
  [ -s "$CK" ] || CK=$(python -c "import json; print(json.load(open('$PI/final_eval/checkpoints.json'))['$ep'])" | sed 's#^/workspace/#/content/#')
  [ -s "$CK" ] || { log "sub_videos ep$ep: checkpoint $CK missing" >> $J; return 1; }
  sha=$(sha256sum $CK | cut -d' ' -f1); want=$(python -c "import json; print(json.load(open('$PI/submission/results/episode_$E6.json'))['checkpoint_sha256'])")
  [ "$sha" = "$want" ] || { log "sub_videos ep$ep: sha256 $sha != submitted $want: refused" >> $J; return 1; }
  TASK=$(cd $FC && .venv/bin/python -c "import sys
from flash_chord.training.checkpoint import read_checkpoint_metadata
from flash_chord.training.checkpoint_metadata import checkpoint_config
print(checkpoint_config(read_checkpoint_metadata(sys.argv[1]))['task']['parquet'])" $CK 2>> $O/err.log | tail -1)
  TASK=${TASK/#\/workspace\//\/content\/}
  [ -s "$TASK" ] || { log "sub_videos ep$ep: reference $TASK missing" >> $J; return 1; }
  REFDIR=$(echo $TASK | sed 's#/processed/.*##'); [ -s $REFDIR/table_frame.npz ] || REFDIR=/content/refs/perc2mck/ep$ep
  N=$(python -c "import numpy as np, pyarrow.parquet as pq; print(len(np.array(pq.read_table('$TASK').column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3)))")
  local OV="evaluation.checkpoint=$CK task.parquet='$TASK' reset.voc_decay_steps=0 reset.always_reset_to_first_frame=true"
  for t in wrist_position object_position object_orientation; do OV="$OV termination.$t.enabled=false"; done
  OV="$OV viewer.backend=mp4 viewer.headless=true viewer.realtime=false viewer.output_path=$O/view.mp4 viewer.num_frames=$N"
  OV="$OV viewer.width=960 viewer.height=540 markers.keypoints=false markers.contacts=false"
  ( cd $FC && CONTACTS=1 DEV=cuda PYGLET_HEADLESS=1 MUJOCO_GL=egl timeout 1500 .venv/bin/python $REPO_DIR/tools/trace_rollout.py policy $O/policy_trace.npz $OV \
      "viewer.camera_position=[0.55,-0.45,1.05]" "viewer.camera_target=[0.0,0.0,0.65]" ) > $O/trace.log 2>&1
  [ -s $O/policy_trace.npz ] && [ -s $O/view.mp4 ] || { log "sub_videos ep$ep: trace/view FAILED ($(tail -2 $O/trace.log | tr '\n' ' ' | cut -c1-200))" >> $J; return 1; }
  ( cd $FC && KIT=/content/kit/v2d_submission_kit python $REPO_DIR/tools/trace_score.py $TASK $O/policy_trace.npz:replay ) > $O/score.txt 2>&1
  MD=/content/refs/sf/ep$ep/assets/mesh; [ -d $MD ] || MD=/content/assets/mesh
  sc=$(python -c "import json; print(json.loads(open('$PI/submission/summary.txt').readline())['$ep'])" 2>/dev/null)
  echo "$CK $TASK $REFDIR $MD" > $O/inputs.txt
  python $REPO_DIR/tools/sim_vs_real_video.py $O/policy_trace.npz $TASK $REFDIR /content/perc2/ep$ep /content/t3/eval/v/ep${ep}_a.mp4 $MD \
      $O/view.mp4 $OUTV/$NAME.mp4 --title "eval $ep: submitted policy, replayed like the official evaluator${tag:+ ($tag)}" \
      --score "${sc:+packed rollout sim_vs_ref $sc; this replay $(tail -1 $O/score.txt | cut -c1-60) (vs our reference, not ground truth)}" > $O/svr.log 2>&1 \
    && log "sub_videos $NAME: $(du -h $OUTV/$NAME.mp4 | cut -f1); replay $(tail -1 $O/score.txt | cut -c1-120)" >> $J \
    || log "sub_videos $NAME: sim_vs_real FAILED ($(tail -2 $O/svr.log | tr '\n' ' ' | cut -c1-200))" >> $J
}

reps() {  # REPLAYS="EP:K ..." (opt-in, 1 Nov): K fresh replays of EP (tags r1..rK); unset or absent: one replay, no tag
  local x; for x in ${REPLAYS:-}; do [ "${x%%:*}" = "$1" ] && { echo "${x#*:}"; return; }; done; echo 0
}
pids=()
for ep in $EPS; do
  k=$(reps $ep)
  if [ "$k" -gt 0 ] 2>/dev/null; then
    for i in $(seq 1 $k); do
      one $ep r$i & pids+=($!)
      [ ${#pids[@]} -ge ${PAR:-3} ] && { wait "${pids[@]}"; pids=(); }
    done
  else
    one $ep & pids+=($!)
    [ ${#pids[@]} -ge ${PAR:-3} ] && { wait "${pids[@]}"; pids=(); }
  fi
done
[ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
log "sub_videos: $(ls $OUTV/*.mp4 2>/dev/null | wc -l) videos of $(echo $EPS | wc -w)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
