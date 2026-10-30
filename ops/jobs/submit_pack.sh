#!/bin/bash
# Track 3 submission file from trained eval policies (2026-10-24; kit tracks/track_3/README.md). On a GPU box:
#   1. a PRISTINE FlashCHORD (git worktree of the box's checkout at the same commit, without our training-only
#      patches: FDR rewards, VOC inertia fix, drop starts) runs the kit's evaluator (examples/run_policy_evaluation.py)
#      once per episode: frame 0, explicit reset, no assist, one world -> results/episode_XXXXXX.parquet + .json;
#   2. meshes: our library mesh for every (episode, object) of data/track_3_evaluation_objects.json, copied as
#      meshes/episode_XXXXXX/<object>.glb (the same files the simulator built its bodies from, so body frames match);
#   3. tools/pack_submission.py --track track_3 -> track3_submission.parquet (provenance: checkpoint, evaluator,
#      packer and uploader hashes; code commit URL).
# Uploading (submit/v2d_submit.py) needs the owner's Kaggle account and the accepted rules: done by the owner.
# Usage: CHECKPOINTS=/content/results/final_eval/checkpoints.json COMMIT_URL=https://github.com/<o>/<r>/commit/<sha> \
#        LIB=/content/v2d-track3/meshes/library_v3 bash ops/jobs/submit_pack.sh
. /content/v2d-track3/ops/box/lib.sh
KIT=/content/kit/v2d_submission_kit; OUT=${OUT:-/content/results/submission}; J=${J:-/content/job.log}
LIB=${LIB:-$REPO_DIR/meshes/library_v3}; CLEAN=/content/v2d_clean; FCV=/content/v2d/robotic_grounding/flash_chord/.venv/bin/python
[ -s "${CHECKPOINTS:-}" ] || { log "submit_pack: CHECKPOINTS json missing" >> $J; exit 1; }
[ -n "${COMMIT_URL:-}" ] || { log "submit_pack: COMMIT_URL missing" >> $J; exit 1; }
python $REPO_DIR/tools/no_oracle.py $CHECKPOINTS ${KEPT_DIR:-} $LIB >> $J 2>&1 \
  || { log "submit_pack: REFUSED: a checkpoint is an oracle twin (mocap-derived; tools/no_oracle.py)" >> $J; exit 1; }
mkdir -p $OUT/results $OUT/meshes
[ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || { log "submit_pack: clean worktree FAILED" >> $J; exit 1; }
log "submit_pack: clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files: $(git -C $CLEAN status --short | wc -l)" >> $J
if [ "$(python -c "import json, sys; print(len(json.load(open(sys.argv[1]))))" $CHECKPOINTS)" -gt 0 ]; then
( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
    $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CHECKPOINTS --results $OUT/results \
    --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $OUT/eval.log 2>&1 || { log "submit_pack: evaluation FAILED ($(tail -2 $OUT/eval.log | tr '\n' ' ' | cut -c1-200))" >> $J; exit 1; }
fi
if [ -n "${KEPT_DIR:-}" ]; then                                   # KEEP_RESULTS (pack_eval.sh): earlier official rollouts of
  cp -n $KEPT_DIR/episode_* $OUT/results/                         # unchanged checkpoints; never over a new evaluation
  log "submit_pack: kept earlier rollouts: $(ls $KEPT_DIR | grep -c parquet) episodes" >> $J
fi
# EP_LIB="EP:DIR ..." (2026-10-25): the library an episode's policy was trained with when it is not LIB (e.g. a v5
# pitcher); the packed mesh must be the file the simulator built the body from
python - $KIT/data/track_3_evaluation_objects.json $LIB $OUT/meshes "${EP_LIB:-}" << 'EOF' >> $J 2>&1 || exit 1
import json, os, shutil, sys
roster, lib, out = json.load(open(sys.argv[1]))['episodes'], sys.argv[2], sys.argv[3]
per = dict(x.split(':', 1) for x in sys.argv[4].split())
for ep, objs in roster.items():
    d = f'{out}/episode_{int(ep):06d}'; os.makedirs(d, exist_ok=True)
    for o in objs:
        shutil.copy(f'{per.get(str(ep), lib)}/{o}.glb', f'{d}/{o}.glb')
print(f'submit_pack: meshes for {len(roster)} episodes from {lib}; per-episode libraries {per}')
EOF
( cd $KIT && python tools/pack_submission.py --track track_3 --results $OUT/results --meshes $OUT/meshes \
    --code-commit "$COMMIT_URL" --eval-script $KIT/flash_chord/scripts/evaluate_policy.py -o $OUT/track3_submission.parquet ) \
    > $OUT/pack.log 2>&1 || { log "submit_pack: pack FAILED ($(tail -3 $OUT/pack.log | tr '\n' ' ' | cut -c1-300))" >> $J; exit 1; }
log "submit_pack: $(ls -la $OUT/track3_submission.parquet | awk '{print $5}') bytes; warnings: $(grep -c 'MESH WARNING' $OUT/pack.log)" >> $J
