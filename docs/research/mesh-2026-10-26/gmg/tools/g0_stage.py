"""Stage and upload the G0 job inputs to the private HF store (build step B3; not a gmg process: no gmg import).

  python g0_stage.py --src RUN/g0 --run-id mesh-YYYYMMDD-g0-<commit7> [--stage DIR] [--dry]

Copies RUN/g0/inputs/* and RUN/g0/jobs.json into STAGE/inputs/, writes SHA256SUMS there (the box checks it before any
SAM 3D run), and uploads STAGE/inputs/ to runs/<run-id>/inputs/ of the store (one commit). The inputs are our RGB
frames, masks and depth pointmaps only (no scan, mocap, parquet pose or library file).
"""
import argparse
import hashlib
import os
import shutil


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--stage', default=None)
    ap.add_argument('--store', default=os.environ.get('HF_STORE', 'aebatirel/v2d-store'))
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    stage = os.path.join(a.stage or os.path.join(os.path.dirname(os.path.abspath(a.src)), 'stage'), 'inputs')
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    files = sorted(os.listdir(os.path.join(a.src, 'inputs')))
    for f in files:
        shutil.copy(os.path.join(a.src, 'inputs', f), os.path.join(stage, f))
    shutil.copy(os.path.join(a.src, 'jobs.json'), os.path.join(stage, 'jobs.json'))
    names = files + ['jobs.json']
    with open(os.path.join(stage, 'SHA256SUMS'), 'w') as fo:
        for f in names:
            fo.write(f'{sha256(os.path.join(stage, f))}  {f}\n')
    size = sum(os.path.getsize(os.path.join(stage, f)) for f in os.listdir(stage))
    print(f'staged {len(names) + 1} files, {size / 1e6:.1f} MB in {stage}')
    if a.dry:
        return
    from huggingface_hub import HfApi
    HfApi().upload_folder(folder_path=stage, path_in_repo=f'runs/{a.run_id}/inputs', repo_id=a.store,
                          repo_type='dataset', commit_message=f'G0 inputs {a.run_id}')
    print(f'uploaded to {a.store} runs/{a.run_id}/inputs')


if __name__ == '__main__':
    main()
