"""PUBOWN box inputs: (1) the run's inputs/ folder (SHA256SUMS first, then every listed file, sha256-checked), (2) the
reused C0b public-box outputs listed in plan.json 'reuse' (runs/<c0b_run>/results/c0b/<rel>, each checked against the
sha256 of C0b's own SHA256SUMS). From the HF store (per-file hf_hub_download, parallel, retried) or from a local fake
store directory for the dry run (--local DIR: same layout, files are symlinked). No depth: PUBOWN reuses C0b's
observed points. Never fetches scans, mocap, parquets or *_align files.
Usage: pubown_fetch.py --run RUN_ID --inputs DIR --reuse DIR [--local DIR] [--workers 8]
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
    p.add_argument('--inputs', required=True); p.add_argument('--reuse', required=True)
    p.add_argument('--local', default=None); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    a.tmp = os.path.join(os.path.dirname(os.path.abspath(a.inputs)), 'hf_tmp')
    t0 = time.time()
    base = f'runs/{a.run}/inputs'
    sums = get(a, f'{base}/SHA256SUMS', os.path.join(a.inputs, 'SHA256SUMS'))
    files = []
    for line in open(sums):
        if line.strip():
            h, f = line.split(None, 1)
            f = f.strip().lstrip('*')
            files.append((h, f[2:] if f.startswith('./') else f))
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(lambda hf: get(a, f'{base}/{hf[1]}', os.path.join(a.inputs, hf[1])), files))
    bad = [f for h, f in files if sha256(os.path.join(a.inputs, f)) != h]
    print(json.dumps(dict(inputs=len(files), sha_bad=bad, sec=round(time.time() - t0, 1))), flush=True)
    if bad:
        sys.exit('PUBOWN-INPUTS-SHA-FAIL')
    plan = json.load(open(os.path.join(a.inputs, 'plan.json')))
    rbase = f'runs/{plan["c0b_run"]}/results/c0b'
    t1 = time.time()
    items = sorted(plan['reuse'].items())
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(lambda kv: get(a, f'{rbase}/{kv[0]}', os.path.join(a.reuse, kv[0])), items))
    bad = [r for r, h in items if sha256(os.path.join(a.reuse, r)) != h]
    mb = sum(os.path.getsize(os.path.join(a.reuse, r)) for r, _ in items) / 1e6
    print(json.dumps(dict(reuse=len(items), from_run=plan['c0b_run'], sha_bad=bad, mb=round(mb, 1),
                          sec=round(time.time() - t1, 1))), flush=True)
    if bad:
        sys.exit('PUBOWN-REUSE-SHA-FAIL')
    shutil.rmtree(a.tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
