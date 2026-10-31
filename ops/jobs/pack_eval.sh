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
python $REPO_DIR/tools/no_oracle.py ${RUNS:-} ${PICK:-} ${KEEP_RESULTS:-} ${ASSET_PIECES:-} ${EP_LIB:-} ${ASSET_LIB:-} >> $J 2>&1 \
  || { log "pack_eval: REFUSED: an input is an oracle twin (mocap-derived; tools/no_oracle.py)" >> $J; exit 1; }
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # kit packer budget_mesh (2026-10-24: missing, pack failed)
# Standard-learner references (hard_ab.sh, refs/perc2mcks) name /content/assets/... (make_assets.py on the training box);
# MA_ARGS (2026-10-31): the same make_assets.py arguments the standard learners were trained with, e.g. --physics
# docs/research/physics-2026-10-30/props_masses_only.json (realistic masses); unset = the 0.3 kg placeholder.
# grasp-lock references carry their own copies (refs/sf/ep<N>/assets). Rebuild the same assets from ASSET_LIB, the
# library the standard learners were trained with (2026-10-25: the first pack with standard-learner policies).
# ASSET_PIECES (2026-10-26): the collision pieces a carved standard learner was trained with (pipeline/interaction_carve.py,
# e.g. meshes/carve/ev25: eval 25's board slots; only the objects in it change, and the boards occur in eval 25 only).
# Several folders (space-separated, e.g. "meshes/carve/ev25 meshes/carve/ev10") are merged per object, first wins. Only
# standard-learner references use /content/assets (1, 19, 25, 28, 30, carved 10); grasp-lock references carry their own.
if [ -n "${ASSET_PIECES:-}" ] && [ "$(echo $ASSET_PIECES | wc -w)" -gt 1 ]; then
  PM=/content/pieces_merged; mkdir -p $PM
  for d in $ASSET_PIECES; do for o in $d/*/; do [ -n "$(ls $o/piece_*.obj 2>/dev/null)" ] && [ ! -e $PM/$(basename $o) ] && ln -s $(readlink -f $o) $PM/$(basename $o); done; done
  log "pack_eval: merged collision pieces: $(ls $PM | tr '\n' ' ')" >> $J; ASSET_PIECES=$PM
fi
[ -d /content/assets ] || python $REPO_DIR/pipeline/make_assets.py ${ASSET_LIB:-$REPO_DIR/meshes/library_v3} /content/assets \
  ${ASSET_PIECES:+--pieces $ASSET_PIECES} ${MA_ARGS:-} >> $J 2>&1 || { log "pack_eval: make_assets FAILED" >> $J; exit 1; }
# record of the collision copy the evaluated episodes saw (2026-10-30; the head of job.log can be overwritten)
( cd /content/assets && find . -type f | sort | xargs md5sum; grep -c "<collision>" urdf/*_rigid.urdf ) > $F/assets_md5.txt 2>&1 || true
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
    if [ "${kind#ck=}" != "$kind" ]; then                          # EP:RUN:ck=<path in the run> (2026-10-26: a carve_rerun
      f=${kind#ck=}; hf download "$HF_STORE" --repo-type dataset --include "runs/$r/$f" --local-dir $d > /dev/null \
        || { log "pack_eval: PICK $x download FAILED" >> $J; exit 1; }   # checkpoint, chosen by the pre-registered rule)
      p=$d/runs/$r/$f
    else
    hf download "$HF_STORE" --repo-type dataset --include "runs/$r/$sub/*" --local-dir $d > /dev/null \
      || { log "pack_eval: PICK $x download FAILED" >> $J; exit 1; }
    p=$d/runs/$r/$sub/policy.safetensors
    fi
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
  # 2026-10-26: KEEP_RESULTS may list several packs ("pack3 pack2"); per episode the first whose rollout names the same
  # checkpoint sha256 is kept (pack 3 re-evaluated 10 episodes; pack 2 holds the seed-43 rollouts of 3/5/15/16)
  KEPT=$F/kept; mkdir -p $KEPT; OLD=""
  for kr in $KEEP_RESULTS; do
    K=/content/keep/$kr; mkdir -p $K
    hf download "$HF_STORE" --repo-type dataset --include "runs/$kr/results/submission/results/episode_*" --local-dir $K > /dev/null \
      || { log "pack_eval: KEEP_RESULTS $kr download FAILED" >> $J; exit 1; }
    OLD="$OLD $K/runs/$kr/results/submission/results"
  done
  python - $F/checkpoints.json $F/checkpoints_eval.json $KEPT $OLD << 'PYEOF' >> $J 2>&1 || exit 1
import hashlib, json, os, shutil, sys
ck, out, kept, olds = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]; m = json.load(open(ck)); ev, keep = {}, {}
for ep, p in m.items():
    h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    for old in olds:
        j = f'{old}/episode_{int(ep):06d}.json'
        if os.path.exists(j) and os.path.exists(j[:-5] + '.parquet') and json.load(open(j)).get('checkpoint_sha256') == h:
            for x in ('.json', '.parquet'):
                shutil.copy(j[:-5] + x, kept)
            keep[int(ep)] = old.split('/runs/')[1].split('/')[0]; break
    else:
        ev[ep] = p
json.dump(ev, open(out, 'w'), indent=1, sort_keys=True)
print(f'pack_eval: earlier official rollout kept for {dict(sorted(keep.items()))} (checkpoint unchanged); evaluating {sorted(map(int, ev))}')
PYEOF
  CK_EVAL=$F/checkpoints_eval.json
fi
if [ -n "${EVAL_ONLY:-}" ]; then   # EVAL_ONLY="EP ..." (2026-10-30, h5_reeval.sh ASSET_PIECES_EXTRA): the only episodes that
  # may get a fresh rollout. A carved piece in the shared /content/assets (e.g. eval 1's white_pot) would reach any other
  # evaluated episode with the same object (eval 28), so stop before the evaluator instead.
  python -c "import json, sys; x = sorted(set(json.load(open(sys.argv[1]))) - set(sys.argv[2:]), key=int); print(f'pack_eval: EVAL_ONLY {sys.argv[2:]}, other episodes to evaluate: {x}'); sys.exit(1 if x else 0)" \
    $CK_EVAL $EVAL_ONLY >> $J 2>&1 || { log "pack_eval: episodes outside EVAL_ONLY would be evaluated; stopped" >> $J; exit 1; }
fi
# 2026-10-26 (forensics): a pulled pack run brings its own results/submission; submit_pack.sh copies KEPT rollouts with
# cp -n, so pack 3 silently kept the FIRST pack's seed-42 rollouts for 3/5/15/16 instead of pack 2's seed-43 ones.
# Start from an empty submission folder, then verify every packed rollout names the intended checkpoint.
rm -rf /content/results/submission
CHECKPOINTS=$CK_EVAL KEPT_DIR=$KEPT LIB=${LIB:-$REPO_DIR/meshes/library_v3} bash $REPO_DIR/ops/jobs/submit_pack.sh
python - $F/checkpoints.json /content/results/submission/results << 'PYEOF' >> $J 2>&1 || { log "pack_eval: packed rollouts do not match the chosen checkpoints" >> $J; exit 1; }
import hashlib, json, sys
m, d = json.load(open(sys.argv[1])), sys.argv[2]; bad = []
for ep, p in m.items():
    want = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    got = json.load(open(f'{d}/episode_{int(ep):06d}.json')).get('checkpoint_sha256')
    if got != want:
        bad.append((ep, (got or '')[:12], want[:12]))
print(f'pack_eval: checkpoint check of {len(m)} packed rollouts: {"OK" if not bad else bad}')
sys.exit(1 if bad else 0)
PYEOF
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
