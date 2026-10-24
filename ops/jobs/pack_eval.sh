#!/bin/bash
# Pack the Track 3 submission from finished eval runs (2026-10-24). Pulls each glock_public SPLIT=eval run from the HF
# store (references, assets and results land at their /content paths), builds the kit checkpoints JSON from every
# results/glock_public/ep<N>/best/policy.safetensors (the checkpoint chosen by sim_vs_ref on our reference, no ground
# truth), checks all 20 roster episodes are present, then runs ops/jobs/submit_pack.sh (pristine evaluator, our
# library meshes, kit packer). Uploading stays with the owner.
# Usage: RUNS="20261024-evA-xxxxxxx 20261024-evB-xxxxxxx ..." COMMIT_URL=https://github.com/<o>/<r>/commit/<sha> bash ops/jobs/pack_eval.sh
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; F=/content/results/final_eval; mkdir -p $F
for r in ${RUNS:?RUNS missing}; do bash $OPS/store.sh pull-run $r >> $J 2>&1 || { log "pack_eval: pull-run $r FAILED" >> $J; exit 1; }; done
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
log "pack_eval: checkpoints $(tr -d '\n ' < $F/checkpoints.json | cut -c1-300)" >> $J
CHECKPOINTS=$F/checkpoints.json LIB=${LIB:-$REPO_DIR/meshes/library_v3} bash $REPO_DIR/ops/jobs/submit_pack.sh
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
