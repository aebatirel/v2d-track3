"""ORACLE-SIDE frame conversion (public episodes only): object poses between our library-mesh body frames ("lib") and
the organiser-scan body frames ("scan"), for the leak decomposition (docs/research/work/leak-decomp-20261030/PLAN.md, B2).

X = scan_T_lib per object (tools/xstar_fit.py): a point p of our mesh's body frame sits at X p in the scan's body frame,
  scan-frame pose = lib-frame pose @ inv(X)   (--to scan)        lib-frame pose = scan-frame pose @ X   (--to lib)
which is pipeline/oracle_poses.py's convention (there X is the kit registration, our-mesh pose = mocap pose @ X).
Converts PERC_DIR/poses.npz (world_T_cam kept; cam_T_<name> right-multiplied, its dtype kept) and poses_world_vo.npz
(4x4 per name), links every other file of PERC_DIR unchanged (depth, hands, detections, VO: none holds a body-frame
pose) and writes xform.json (the X used, direction, input md5s).
--xform FILE: xstar_geom.json (X*_geom per object, fitted to the scans) or xstar_trk.json (X*_trk per episode and
object, fitted to MOCAP: oracle diagnostic only). There is no default X: the scan frames are an oracle input, so this
refuses eval episodes, SPLIT != public, and output paths without 'oracle' in them (tools/no_oracle.py refuses those).
Usage: python -I frame_xform.py EP PERC_DIR OUT_DIR --xform FILE --to scan|lib
(2026-10-30)
"""
import argparse, hashlib, json, os, sys
import numpy as np

EVAL = {1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38}       # as oracle_poses.py
FILES = ('poses.npz', 'poses_world_vo.npz')


def load_xform(path, ep, names):
    """{name: X (4x4, scan_T_lib)} from an xstar_fit.py json; geom files are per object, trk files per episode."""
    d = json.load(open(path))
    if d.get('kind') == 'geom':
        src = d['objects']
    elif d.get('kind') == 'trk':
        if str(ep) not in d['episodes']:
            sys.exit(f'{path} has no X*_trk for episode {ep}')
        src = d['episodes'][str(ep)]['objects']
    else:
        sys.exit(f'{path}: kind must be geom or trk, not {d.get("kind")!r}')
    miss = [n for n in names if n not in src or 'X_scan_T_lib' not in src[n]]
    if miss:
        sys.exit(f'{path} has no X for {miss}')
    X = {n: np.asarray(src[n]['X_scan_T_lib'], np.float64) for n in names}
    for n, M in X.items():
        if M.shape != (4, 4) or not np.allclose(M[:3, :3] @ M[:3, :3].T, np.eye(3), atol=1e-6) or not np.allclose(M[3], [0, 0, 0, 1]):
            sys.exit(f'{path}: X of {n} is not a rigid 4x4')
    return X, d['kind']


def right(X, to):  # the matrix poses are right-multiplied by
    return np.linalg.inv(X) if to == 'scan' else X


def convert(T, X, to):  # (..., 4, 4) poses of one object
    return np.einsum('...ij,jk->...ik', np.asarray(T, np.float64), right(X, to))


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('ep', type=int); p.add_argument('perc_dir'); p.add_argument('out_dir')
    p.add_argument('--xform', required=True, help='xstar_geom.json or xstar_trk.json (tools/xstar_fit.py)')
    p.add_argument('--to', required=True, choices=['scan', 'lib'])
    a = p.parse_args()
    if a.ep in EVAL:
        sys.exit(f'episode {a.ep} is an eval episode: scan frames are an oracle input, public episodes only')
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit(f'SPLIT={os.environ["SPLIT"]}: scan frames are an oracle input, public episodes only')
    if 'oracle' not in os.path.abspath(a.out_dir):
        sys.exit(f'{a.out_dir}: the output path must contain "oracle" so that tools/no_oracle.py keeps it out of packs')
    src = {f: f'{a.perc_dir}/{f}' for f in FILES if os.path.exists(f'{a.perc_dir}/{f}')}
    if not src:
        sys.exit(f'{a.perc_dir} has neither {FILES[0]} nor {FILES[1]}')
    if os.path.realpath(a.perc_dir) == os.path.realpath(a.out_dir):
        sys.exit('OUT_DIR must differ from PERC_DIR')
    rec = dict(episode=a.ep, to=a.to, xform=os.path.abspath(a.xform), xform_md5=md5(a.xform), perc_dir=os.path.abspath(a.perc_dir),
               inputs={f: md5(q) for f, q in src.items()}, note='ORACLE-SIDE frame conversion (scan frames); public episodes only')
    P = np.load(src['poses.npz']) if 'poses.npz' in src else None                 # names and X first: a refusal writes nothing
    V = np.load(src['poses_world_vo.npz']) if 'poses_world_vo.npz' in src else None
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')] if P is not None else list(V.files)
    if P is not None and V is not None and sorted(names) != sorted(V.files):
        sys.exit(f'poses.npz names {names} != poses_world_vo.npz names {V.files}')
    X, kind = load_xform(a.xform, a.ep, names)
    os.makedirs(a.out_dir, exist_ok=True)
    if P is not None:
        out = {k: P[k] for k in P.files}
        for n in names:
            out[f'cam_T_{n}'] = convert(P[f'cam_T_{n}'], X[n], a.to).astype(P[f'cam_T_{n}'].dtype)
        np.savez(f'{a.out_dir}/poses.npz', **out)
    if V is not None:
        np.savez(f'{a.out_dir}/poses_world_vo.npz', **{n: convert(V[n], X[n], a.to).astype(V[n].dtype) for n in V.files})
    rec.update(kind=kind, objects=names, X_scan_T_lib={n: np.round(X[n], 9).tolist() for n in names}, linked=[])
    for f in sorted(os.listdir(a.perc_dir)):                       # frame-independent inputs, linked unchanged
        q = os.path.realpath(f'{a.perc_dir}/{f}')
        if f in FILES or f == 'xform.json' or not os.path.isfile(q) or os.path.lexists(f'{a.out_dir}/{f}'):
            continue
        os.symlink(q, f'{a.out_dir}/{f}'); rec['linked'].append(f)
    json.dump(rec, open(f'{a.out_dir}/xform.json', 'w'), indent=1)
    print(f'frame_xform ep{a.ep}: {sorted(src)} -> {a.to} frames ({kind}) in {a.out_dir}; linked {len(rec["linked"])} files')


if __name__ == '__main__':
    main()
