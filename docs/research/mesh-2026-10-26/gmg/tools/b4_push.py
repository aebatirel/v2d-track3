"""b4_push: upload a clean B4 run (bundles are data: not in git) to the HF store under runs/mesh-<run name>/.

Uploads RUN/{bundle,hands,manifests,identity,validate,logs}/**, RUN/outputs.jsonl and RUN/run_tier.json (never aux/),
the dev B.3 run's b3/ records under b3_dev/, and the strace logs and audit reports of the run under audit/. Refuses to
upload when the store already holds STORE_MAX_GB (ops/box/store.sh rule, default 800 GB). Ops tool, not a gmg process
(no guard): it reads only the two run folders and the audit files it names.
Usage: python -I gmg/tools/b4_push.py --run <clean run> --dev-run <dev run> --audit-glob '<DATA>/gmg/audit/b4-<run>-*'
"""
import argparse
import glob
import os
import shutil
import tempfile

STORE = os.environ.get('HF_STORE', 'aebatirel/v2d-store')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--dev-run', required=True)
    ap.add_argument('--audit-glob', required=True)
    ap.add_argument('--max-gb', type=int, default=int(os.environ.get('STORE_MAX_GB', 800)))
    a = ap.parse_args()
    from huggingface_hub import HfApi
    api = HfApi()
    info = api.dataset_info(STORE, expand=['usedStorage'])
    used = int(getattr(info, 'used_storage', 0) or 0) / 1e9
    print(f'store {STORE} holds {used:.1f} GB')
    if used >= a.max_gb:
        raise SystemExit(f'store holds {used:.1f} GB >= {a.max_gb}: not uploading')
    run = os.path.realpath(a.run)
    name = 'mesh-' + os.path.basename(run)
    dest = f'runs/{name}'
    pats = ['bundle/**', 'hands/**', 'manifests/**', 'identity/**', 'validate/**', 'logs/**', 'outputs.jsonl',
            'run_tier.json']
    api.upload_folder(repo_id=STORE, repo_type='dataset', folder_path=run, path_in_repo=dest, allow_patterns=pats,
                      ignore_patterns=['aux/**'], commit_message=f'{name}: clean B4 bundles (gmg)')
    print('uploaded run', dest)
    api.upload_folder(repo_id=STORE, repo_type='dataset', folder_path=os.path.realpath(a.dev_run),
                      path_in_repo=f'{dest}/b3_dev', allow_patterns=['b3/**', 'run_tier.json', 'outputs.jsonl'],
                      commit_message=f'{name}: B.3 dev validation records')
    files = sorted(glob.glob(a.audit_glob))
    if files:
        tmp = tempfile.mkdtemp()
        for f in files:
            shutil.copy(f, tmp)
        api.upload_folder(repo_id=STORE, repo_type='dataset', folder_path=tmp, path_in_repo=f'{dest}/audit',
                          commit_message=f'{name}: strace audits')
        shutil.rmtree(tmp)
    print('uploaded audits', len(files))


if __name__ == '__main__':
    main()
