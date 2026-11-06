"""E0 box inputs: the run's inputs/ folder (SHA256SUMS first, then every listed file, sha256-checked) and the eval
depth caches of the plan's episodes, from the HF store (per-file hf_hub_download, parallel, retried), or from a local
fake store directory for the dry run (--local DIR: same layout, files are symlinked).
Never fetches scans, mocap, parquets or *_align files: the inputs list is what the agent uploaded (e0_stage_inputs.py)
and the depth paths are cache/depth/eval/ep<N>/depths_fs0.5.npy only.
Usage: e0_fetch.py --store REPO --run RUN_ID --inputs DIR --depth DIR [--local DIR] [--workers 8] [--eps "1 3 ..."]
"""
import argparse, hashlib, json, os, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor


def get(a, rel, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if a.local:
        src = os.path.join(a.local, rel)
        if not os.path.exists(src):
            raise FileNotFoundError(src)
        if os.path.lexists(dest):
            os.remove(dest)
        os.symlink(os.path.abspath(src), dest)
        return dest
    from huggingface_hub import hf_hub_download
    for i in range(5):
        try:
            p = hf_hub_download(a.store, rel, repo_type='dataset', local_dir=a.tmp)
            if os.path.abspath(p) != os.path.abspath(dest):
                if os.path.lexists(dest):
                    os.remove(dest)
                shutil.move(p, dest)
            return dest
        except Exception as ex:  # noqa: BLE001
            print(f'retry {i + 1} {rel}: {type(ex).__name__} {str(ex)[:200]}', flush=True)
            time.sleep(10 * (i + 1))
    raise RuntimeError(f'download failed: {rel}')


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--store', default='aebatirel/v2d-store'); p.add_argument('--run', required=True)
    p.add_argument('--inputs', required=True); p.add_argument('--depth', required=True)
    p.add_argument('--local', default=None); p.add_argument('--workers', type=int, default=8)
    p.add_argument('--eps', default=None, help='override the plan episodes (dry run)')
    a = p.parse_args()
    a.tmp = os.path.join(os.path.dirname(os.path.abspath(a.inputs)), 'hf_tmp')
    t0 = time.time()
    base = f'runs/{a.run}/inputs'
    sums = get(a, f'{base}/SHA256SUMS', os.path.join(a.inputs, 'SHA256SUMS'))
    rows = [l.split(None, 1) for l in open(sums) if l.strip()]
    files = []
    for h, f in rows:
        f = f.strip().lstrip('*')
        files.append((h, f[2:] if f.startswith('./') else f))
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(lambda hf: get(a, f'{base}/{hf[1]}', os.path.join(a.inputs, hf[1])), files))
    bad = [f for h, f in files if sha256(os.path.join(a.inputs, f)) != h]
    print(json.dumps(dict(inputs=len(files), sha_bad=bad, sec=round(time.time() - t0, 1))), flush=True)
    if bad:
        sys.exit('E0-INPUTS-SHA-FAIL')
    plan = json.load(open(os.path.join(a.inputs, 'plan.json')))
    eps = [int(e) for e in a.eps.split()] if a.eps else sorted({int(e) for v in plan['episodes_by_object'].values() for e in v})
    t1 = time.time()

    def dep(e):
        d = get(a, f'cache/depth/eval/ep{e}/depths_fs0.5.npy', os.path.join(a.depth, f'ep{e}', 'depths_fs0.5.npy'))
        n = os.path.getsize(d)
        want = plan['episodes'][str(e)]['depth_bytes']
        print(json.dumps(dict(depth_ep=e, bytes=n, expected=want, ok=(n == want), sec=round(time.time() - t1, 1))), flush=True)
        return n == want
    with ThreadPoolExecutor(min(a.workers, len(eps))) as ex:
        ok = list(ex.map(dep, eps))
    print(json.dumps(dict(depth_eps=eps, all_ok=all(ok), gb=round(sum(os.path.getsize(os.path.join(a.depth, f'ep{e}', 'depths_fs0.5.npy')) for e in eps) / 1e9, 2),
                          sec=round(time.time() - t1, 1))), flush=True)
    if not all(ok):
        sys.exit('E0-DEPTH-FAIL')
    shutil.rmtree(a.tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
