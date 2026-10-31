"""Stub `hf` CLI of the eval-10 V4p retrain CPU mock (after ep11gate/cpu/mock/hf_stub.py). One JSON line per call in
MR/hf.log:
  download with ONE filename -> kind 'file' (hf_hub_download, no listing), served from the fake store MR/store/<path>;
                                cache/depth/eval/ep10/depths_fs0.5.npy is served as a sparse file of the store's size
                                (1,030,400,128 B, 161 x 1000 x 1600) whose frame 0 is the store's real frame 0 (range read)
  download with --include or several files -> kind 'LISTING' (the real CLI lists the whole store): refused
  upload LOCAL PATH          -> kind 'upload'; LOCAL is copied into the fake store at PATH (so a re-run box can pull it)
Fault injection: MOCK_BADPOSES=1 serves a corrupted eval-10 stored track (md5 mismatch)."""
import json, os, shutil, sys
MR, ST, F0 = os.environ['MOCK_MR'], os.environ['MOCK_STORE'], os.environ['MOCK_DEPTH_F0']
a = sys.argv[1:]


def logit(**kw):
    with open(f'{MR}/hf.log', 'a') as f:
        f.write(json.dumps(kw) + '\n')


def opt(k):
    return a[a.index(k) + 1] if k in a else None


if a[:1] == ['upload']:
    src, dst = a[2], a[3]
    if os.path.isdir(src):
        shutil.copytree(src, f'{ST}/{dst}', dirs_exist_ok=True)
    logit(kind='upload', src=src.replace(MR, '<MR>'), dst=dst, msg=opt('--commit-message')); sys.exit(0)
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
os.makedirs(os.path.dirname(dst), exist_ok=True)
if f == 'cache/depth/eval/ep10/depths_fs0.5.npy':
    import numpy as np
    from numpy.lib import format as Fm
    d0 = np.load(F0)[0]
    with open(dst, 'wb') as g:
        Fm.write_array_header_1_0(g, dict(descr='<f4', fortran_order=False, shape=(161, 1000, 1600)))
        g.write(d0.astype('<f4').tobytes()); g.truncate(1030400128)
elif os.path.isfile(f'{ST}/{f}'):
    shutil.copyfile(f'{ST}/{f}', dst)
    if os.environ.get('MOCK_BADPOSES') and f == 'runs/20261026-pack6-5203d42/perc2/ep10/poses.npz':
        open(dst, 'ab').write(b'corrupt')
else:
    logit(kind='file', path=f, result='404'); sys.exit(f'hf stub: {f} not in the store (404)')
logit(kind='file', path=f, result='ok', bytes=os.path.getsize(dst))
