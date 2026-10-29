#!/bin/bash
# Free the HF store (owner-approved 2026-10-21: "delete and squash for now, I will upgrade HF later"):
#   1) delete every runs/**/state_* checkpoint (resume-only; all those trainings finished and were evaluated),
#   2) super_squash_history (IRREVERSIBLE: old revisions disappear; current files stay),
# and print the store's size before and after. Run with SETUP=none on any cheap box (needs the account HF_TOKEN).
. /content/v2d-track3/ops/box/lib.sh
label "store cleanup"
pip install -q -U huggingface_hub > /dev/null 2>&1
python - <<'EOF' 2>&1 | tee -a /content/job.log
import os
from huggingface_hub import HfApi, CommitOperationDelete
api = HfApi(token=os.environ['HF_TOKEN']); repo = os.environ['HF_STORE']
def files():
    return [f for f in api.list_repo_tree(repo, repo_type='dataset', recursive=True) if f.__class__.__name__ == 'RepoFile']
def used():
    try:
        return getattr(api.dataset_info(repo, expand=['usedStorage']), 'used_storage', None)
    except Exception as e:
        return f'n/a ({e.__class__.__name__})'
F = files(); print(f'before: {len(F)} files, {sum(f.size for f in F) / 1e9:.1f} GB in the tree, usedStorage {used()}')
dele = [f.path for f in F if f.path.startswith('runs/') and '/state_' in f.path]
print(f'deleting {len(dele)} state_ files, {sum(f.size for f in F if f.path in set(dele)) / 1e9:.1f} GB')
for i in range(0, len(dele), 200):
    api.create_commit(repo, repo_type='dataset', operations=[CommitOperationDelete(p) for p in dele[i:i + 200]],
                      commit_message=f'cleanup: delete resume-only state_ checkpoints ({i + 1}-{min(i + 200, len(dele))})')
api.super_squash_history(repo_id=repo, repo_type='dataset', commit_message='squash history after state_ cleanup')
F = files(); print(f'after: {len(F)} files, {sum(f.size for f in F) / 1e9:.1f} GB in the tree, usedStorage {used()}')
print('STORE-CLEANUP-DONE')
EOF
exit 0
