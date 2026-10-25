#!/bin/bash
# Pack the Track 3 submission from finished eval runs (2026-10-24). Pulls each glock_public SPLIT=eval run from the HF
# store (references, assets and results land at their /content paths), builds the kit checkpoints JSON from every
# results/glock_public/ep<N>/best/policy.safetensors (the checkpoint chosen by sim_vs_ref on our reference, no ground
# truth), checks all 20 roster episodes are present, then runs ops/jobs/submit_pack.sh (pristine evaluator, our
# library meshes, kit packer). Uploading stays with the owner.
# Usage: RUNS="20261024-evA-xxxxxxx 20261024-evB-xxxxxxx ..." COMMIT_URL=https://github.com/<o>/<r>/commit/<sha> bash ops/jobs/pack_eval.sh
# PICK="EP:RUN ..." replaces those episodes' checkpoints with the chosen checkpoint of another run trained on the SAME
# reference (REUSE_REF, e.g. a second seed); the choice between runs is made beforehand by sim_vs_ref (no ground truth).
# "EP:RUN:final" takes RUN's results/final_eval/ep<EP>/policy.safetensors (tools/choose_learner.py's choice); list RUN in
# RUNS too, so the reference that policy was trained on is pulled. EP_LIB="EP:DIR ..." packs those episodes' meshes from
# DIR (the library their policy was trained with; ops/jobs/submit_pack.sh).
# RUNS entries may be RUN@sub1,sub2 to pull only those sub-folders of a run (e.g. RUN@refs: the references a PICKed
# policy was trained on, without the run's checkpoints). Order matters: store.sh pull-run never overwrites (cp -rn), so the FIRST run listed wins for a file path. Put the
# runs that redid an episode first (2026-10-24: evR redid eval 25, whose failed evD attempt left references with the
# same names; the policy must be evaluated on the reference it was trained on).
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; F=/content/results/final_eval; mkdir -p $F
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # kit packer budget_mesh (2026-10-24: missing, pack failed)
# Standard-learner references (hard_ab.sh, refs/perc2mcks) name /content/assets/... (make_assets.py on the training box);
# grasp-lock references carry their own copies (refs/sf/ep<N>/assets). Rebuild the same assets from ASSET_LIB, the
# library the standard learners were trained with (2026-10-25: the first pack with standard-learner policies).
[ -d /content/assets ] || python $REPO_DIR/pipeline/make_assets.py ${ASSET_LIB:-$REPO_DIR/meshes/library_v3} /content/assets >> $J 2>&1 \
  || { log "pack_eval: make_assets FAILED" >> $J; exit 1; }
for x in ${RUNS:?RUNS missing}; do             # RUN or RUN@sub1,sub2 (2026-10-25: only those sub-folders, e.g. RUN@refs)
  r=${x%%@*}; sub=; [ "$r" != "$x" ] && sub=${x#*@}
  PULL_SUB="${sub//,/ }" bash $OPS/store.sh pull-run $r >> $J 2>&1 || { log "pack_eval: pull-run $x FAILED" >> $J; exit 1; }
done
python - $F/checkpoints.json /content/kit/v2d_submission_kit/data/track_3_evaluation_objects.json << 'PYEOF' >> $J 2>&1 || exit 1
import glob, json, os, sys
out, roster = sys.argv[1], json.load(open(sys.argv[2]))['episodes']
m = {}
for p in sorted(glob.glob('/content/results/glock_public/ep*/best/policy.safetensors')):
    ep = int(p.split('/ep')[1].split('/')[0])
    if str(ep) in roster:
        m[str(ep)] = p
missing = sorted(set(roster) - set(m), key=int)
json.dump(m, open(out, 'w'), indent=1, sort_keys=True)
print(f'pack_eval: {len(m)} of {len(roster)} episodes have a chosen checkpoint; missing {missing}')
sys.exit(1 if missing and not os.environ.get('ALLOW_MISSING') else 0)
PYEOF
if [ -n "${PICK:-}" ]; then                                         # PICK="EP:RUN ...": that run's chosen checkpoint for EP
  for x in $PICK; do                                               # (e.g. a second seed trained on the same reference)
    IFS=: read -r ep r kind <<< "$x"; d=/content/pick/$r; mkdir -p $d   # EP:RUN:final = that run's learner choice
    sub=results/glock_public/ep$ep/best; [ "$kind" = final ] && sub=results/final_eval/ep$ep   # (std_learner / eval_both)
    hf download "$HF_STORE" --repo-type dataset --include "runs/$r/$sub/*" --local-dir $d > /dev/null \
      || { log "pack_eval: PICK $x download FAILED" >> $J; exit 1; }
    p=$d/runs/$r/$sub/policy.safetensors
    [ -s $p ] || { log "pack_eval: PICK $x has no best/policy.safetensors" >> $J; exit 1; }
    python -c "import json, sys; f = sys.argv[1]; m = json.load(open(f)); m[sys.argv[2]] = sys.argv[3]; json.dump(m, open(f, 'w'), indent=1, sort_keys=True)" \
      $F/checkpoints.json $ep $p
  done
fi
log "pack_eval: checkpoints $(tr -d '\n ' < $F/checkpoints.json | cut -c1-300)" >> $J
CK_EVAL=$F/checkpoints.json; KEPT=
if [ -n "${KEEP_RESULTS:-}" ]; then   # KEEP_RESULTS=<earlier pack run> (2026-10-25): an episode whose chosen checkpoint is
  # byte-identical (sha256) to the one that pack evaluated keeps that pack's official rollout; only changed episodes are
  # evaluated again. The rule depends on the checkpoint alone, never on a score: re-rolling an unchanged, bimodal
  # episode (evals 3, 5, 15: one bad mode in five) would add variance and no expected gain.
  K=/content/keep/$KEEP_RESULTS; KEPT=$F/kept; mkdir -p $K $KEPT
  hf download "$HF_STORE" --repo-type dataset --include "runs/$KEEP_RESULTS/results/submission/results/episode_*" --local-dir $K > /dev/null \
    || { log "pack_eval: KEEP_RESULTS $KEEP_RESULTS download FAILED" >> $J; exit 1; }
  python - $F/checkpoints.json $K/runs/$KEEP_RESULTS/results/submission/results $F/checkpoints_eval.json $KEPT << 'PYEOF' >> $J 2>&1 || exit 1
import hashlib, json, os, shutil, sys
ck, old, out, kept = sys.argv[1:5]; m = json.load(open(ck)); ev, keep = {}, []
for ep, p in m.items():
    j = f'{old}/episode_{int(ep):06d}.json'; h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    if os.path.exists(j) and os.path.exists(j[:-5] + '.parquet') and json.load(open(j)).get('checkpoint_sha256') == h:
        for x in ('.json', '.parquet'):
            shutil.copy(j[:-5] + x, kept)
        keep.append(int(ep))
    else:
        ev[ep] = p
json.dump(ev, open(out, 'w'), indent=1, sort_keys=True)
print(f'pack_eval: earlier official rollout kept for {sorted(keep)} (checkpoint unchanged); evaluating {sorted(map(int, ev))}')
PYEOF
  CK_EVAL=$F/checkpoints_eval.json
fi
CHECKPOINTS=$CK_EVAL KEPT_DIR=$KEPT LIB=${LIB:-$REPO_DIR/meshes/library_v3} bash $REPO_DIR/ops/jobs/submit_pack.sh
S=/content/results/submission                                       # each packed rollout scored against our reference
for p in $S/results/episode_*.parquet; do                           # (sim_vs_ref, qa.py policy; no ground truth)
  e=$((10#$(basename $p .parquet | cut -d_ -f2))); mkdir -p $S/qa/ep$e; cp ${p%.parquet}.* $S/qa/ep$e/
  python $REPO_DIR/pipeline/qa.py policy $S/qa/ep$e $e > /dev/null 2>&1 || true
done
python - $S/qa > $S/summary.txt 2>&1 << 'PYEOF'
import glob, json, sys
v = {f.split('/ep')[-1].split('/')[0]: json.load(open(f))['sim_vs_ref'] for f in glob.glob(f'{sys.argv[1]}/ep*/qa_policy.json')}
v = dict(sorted(v.items(), key=lambda x: int(x[0])))
print(json.dumps({k: round(x, 4) for k, x in v.items()})); print('n', len(v), 'mean', round(sum(v.values()) / max(len(v), 1), 4))
PYEOF
log "pack_eval: packed rollouts sim_vs_ref $(tr '\n' ' ' < $S/summary.txt | cut -c1-600)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
