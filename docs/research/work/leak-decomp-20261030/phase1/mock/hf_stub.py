"""Stub `hf` CLI of the perc_leak CPU mock. Logs every call to MR/hf.log as one JSON line:
  download with ONE filename  -> kind 'file' (hf_hub_download, no listing); served from the local refine mirror
                                 (MOCK_IN/store/<path>); a depth cache cache/depth/public/ep<N>/depths_fs0.5.npy as a
                                 sparse file of the store's size whose frame 0 is MOCK_IN/ep<N>/depth0.npy
  download with several files or --include -> kind 'LISTING' (the real CLI lists the whole repo first); refused
  upload                      -> kind 'upload' (nothing is sent)
Fault injection: MOCK_429=<path>[,<path>] fails the first attempt of those files (exit 1, as on HTTP 429);
MOCK_BADHANDS=<path> serves a corrupted copy of that file (md5 mismatch); MOCK_SHORTDEPTH=<ep> serves that episode's
depth cache one frame short (a truncated cache)."""
import json, os, shutil, sys
MR, IN = os.environ['MOCK_MR'], os.environ['MOCK_IN']
a = sys.argv[1:]


def logit(**kw):
    with open(f'{MR}/hf.log', 'a') as f:
        f.write(json.dumps(kw) + '\n')


def opt(k):
    return a[a.index(k) + 1] if k in a else None


if a[:1] == ['upload']:
    logit(kind='upload', src=a[2].replace(MR, '<MR>'), dst=a[3], msg=opt('--commit-message')); sys.exit(0)
if a[:1] != ['download']:
    logit(kind='other', argv=a); sys.exit(0)
skip = {'--repo-type', '--local-dir', '--include', '--exclude', '--revision'}
pos, i = [], 1
while i < len(a):
    if a[i] in skip:
        i += 2; continue
    pos.append(a[i]); i += 1
files, ld = pos[1:], opt('--local-dir')
if len(files) != 1 or '--include' in a:
    logit(kind='LISTING', argv=a); sys.exit('hf stub: multi-file / --include download lists the repo: refused in this mock')
f = files[0]; dst = f'{ld}/{f}'
st = f'{MR}/hf_429_seen.txt'; seen = open(st).read().split() if os.path.exists(st) else []
if f in (os.environ.get('MOCK_429') or '').split(',') and f not in seen:
    open(st, 'a').write(f + '\n'); logit(kind='file', path=f, result='429'); sys.exit('429 Client Error: Too Many Requests (mock)')
os.makedirs(os.path.dirname(dst), exist_ok=True)
if f.startswith('cache/depth/public/'):
    import numpy as np
    from numpy.lib import format as F
    ep = int(f.split('/')[3][2:]); d0 = np.load(f'{IN}/ep{ep}/depth0.npy')
    m = [json.loads(l) for l in open(f'{IN}/depth0_manifest.jsonl') if json.loads(l)['ep'] == ep][0]
    with open(dst, 'wb') as g:
        F.write_array_header_1_0(g, dict(descr='<f4', fortran_order=False, shape=tuple(m['shape_full'])))
        g.write(d0.astype('<f4').tobytes()); g.truncate(m['store_bytes'] - (6400000 if os.environ.get('MOCK_SHORTDEPTH') == str(ep) else 0))
else:
    shutil.copyfile(os.path.realpath(f'{IN}/store/{f}'), dst)
    if f == os.environ.get('MOCK_BADHANDS'):
        open(dst, 'ab').write(b'corrupt')
logit(kind='file', path=f, result='ok', bytes=os.path.getsize(dst))
