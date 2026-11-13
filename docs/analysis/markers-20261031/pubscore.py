"""SCORING ONLY (public episodes): kit Track 3 registered chain on apply.py's variants vs public mocap.

Reads ground truth (public mocap via the parquet `pose` field, public scans as the host stand-in) through
docs/analysis/rpe-decomp-20261031/rdlib.py, AFTER inference. Nothing here feeds the correction.
Usage: python -I pubscore.py APPLY_DIR EPS(comma) OUT_JSON
"""
import json, os, sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor

RDLIB = '/home/user/v2d-track3/docs/analysis/rpe-decomp-20261031'
S = os.environ.get('MK_SCRATCH', '/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad')
LIB = '/home/user/v2d-track3/meshes/library_v3'
VARS = ['base', 'primary', 'novote', 'nocarry', 'fused']


def run(args):
    ep, adir = args
    sys.path.insert(0, RDLIB)
    import rdlib as L
    L.load_kit(f'{S}/dl/kit/v2d_submission_kit'); L.guard(ep)
    t3 = f'{S}/t3'; names = L.names_of(t3, ep)
    A = np.load(f'{adir}/ep{ep}.npz')
    H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
    REG = [L.kit_reg(LIB, n, H[s], ep, s) for s, n in enumerate(names)]
    out = dict(ep=ep, names=names, variants={})
    T = len(A[f'base/{names[0]}'])
    G = L.ref_anchor(L.mocap7(t3, ep, names, T), H)                       # GROUND TRUTH (scoring only)
    for v in VARS:
        P7 = np.stack([L.to7(A[f'{v}/{n}']) for n in names], 1)
        m = L.score(L.convert(P7, REG), G, H)
        out['variants'][v] = {k: (round(x, 4) if isinstance(x, float) else [round(y, 4) for y in x]) for k, x in m.items()}
    print(ep, names, ' '.join(f"{v}: AUC {out['variants'][v]['AUC']:.4f} obj {out['variants'][v]['obj_AUC']}" for v in VARS), flush=True)
    return out


def main():
    adir, eps, outp = sys.argv[1], [int(x) for x in sys.argv[2].split(',')], sys.argv[3]
    with ProcessPoolExecutor(4) as ex:
        res = {str(r['ep']): r for r in ex.map(run, [(e, adir) for e in eps])}
    json.dump(dict(kind='marker-layer public scoring', note='reads public mocap and scans; scoring only', episodes=res),
              open(outp, 'w'), indent=1)


if __name__ == '__main__':
    main()
