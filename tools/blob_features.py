#!/usr/bin/env python3
"""Contact-wrench "blob" features per held frame of a reference (2026-11-12, owner: "use the physical contact blob from
exercise 3 ... through the decision tree"; rule pre-registered in docs/work-log.md, 2026-11-12 ~23:05 UTC).

The blob is exercise 3's 6-D support function of the grasp, h(u) = max(0, max_i u . w_i), over the contact wrench
generators w_i of pipeline/wrench_gate.py (both hands, friction cone 8 edges + normal, torque scaled by object_mesh_radius).
Rows are the gate's own rows: every (object, frame) in its held windows. Eight features per row:
  score       the gate's NNLS residual (wrench_gate.feasibility)
  h_demand    support along the unit demand wrench W/|W|
  h_up        support along a pure upward force [0, 0, 1, 0, 0, 0]
  gap         share of 512 fixed unit 6-D directions (Gaussian, seed 0, normalised) with zero support
  contacts    number of active contact points on the object
  hands       number of hands with at least one active contact (0, 1, 2)
  F_N, tau_Nm demand force and torque norms
Inference only, no ground truth: reads our reference and the object assets it names, nothing else.
Usage: blob_features.py OUT.csv EP=REF.parquet [EP=REF.parquet ...] [--assets DIR]
"""
import argparse, csv, os, sys

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline'))
import wrench_gate as wg  # noqa: E402

DIRS = np.random.default_rng(0).standard_normal((512, 6))
DIRS /= np.linalg.norm(DIRS, axis=1, keepdims=True)
FIELDS = ['episode', 'object', 'frame', 'score', 'h_demand', 'h_up', 'gap', 'contacts', 'hands', 'F_N', 'tau_Nm']


def support(G, u):
    """h(u) = max(0, max_i u . g_i) for the columns g_i of G (6, K); 0 without contacts. u: (6,) or (N, 6)."""
    if G.shape[1] == 0:
        return np.zeros(np.atleast_2d(u).shape[0])
    return np.maximum(0.0, (np.atleast_2d(u) @ G).max(axis=1))


def rows(ep, ref, assets=None, mu=wg.MU):
    t = pq.read_table(ref)
    names, P, Q = wg.object_tracks(ref)
    T = P.shape[0]; OR = [Rot.from_quat(Q[:, j]) for j in range(len(names))]
    col = lambda c: t.column(c)[0].as_py() if c in t.column_names else None  # noqa: E731
    rc_all = np.asarray(col('object_mesh_radius') or [0.1] * len(names), float)
    urdfs = col('object_urdf_paths') or [None] * len(names); meshes = col('object_mesh_paths') or [None] * len(names)
    C = {s: (np.array(col(f'mano_{s}_object_contact_positions'), float).reshape(T, -1, 3),
             np.array(col(f'mano_{s}_object_contact_normals'), float).reshape(T, -1, 3),
             np.array(col(f'mano_{s}_object_contact_part_ids')).reshape(T, -1)) for s in wg.SIDES}
    wins = wg.held_windows(ref, names, P, OR); up = np.array([0, 0, 1, 0, 0, 0], float)
    for j, n in enumerate(names):
        rc = float(rc_all[j]); ph = wg.object_physics(n, urdfs[j], meshes[j], rc, assets, None)
        W, com_w = wg.demand_wrench(P[:, j], Q[:, j], ph, wg.FPS)
        Wn = np.hstack([W[:, :3], W[:, 3:] / rc])
        for (a, b, _info) in wins[n]:
            for f in range(a, b):
                pts, nrm, hands = [], [], 0
                for s in wg.SIDES:
                    cp, cn, pid = C[s]
                    act = (pid[f] == j + 1) & (np.linalg.norm(cn[f], axis=1) > 1e-3)
                    pts.append(cp[f][act]); nrm.append(cn[f][act]); hands += int(act.any())
                pts, nrm = np.vstack(pts), np.vstack(nrm)
                G = wg.generators(pts, nrm, com_w[f], rc, mu)
                w = Wn[f]; nw = np.linalg.norm(w)
                yield dict(episode=ep, object=n, frame=int(f), score=wg.feasibility(w, G),
                           h_demand=float(support(G, w / nw)[0]) if nw > 1e-12 else 0.0, h_up=float(support(G, up)[0]),
                           gap=float((support(G, DIRS) <= 1e-12).mean()), contacts=int(len(pts)), hands=hands,
                           F_N=float(np.linalg.norm(W[f, :3])), tau_Nm=float(np.linalg.norm(W[f, 3:])))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('refs', nargs='+'); ap.add_argument('--assets')
    a = ap.parse_args()
    with open(a.out, 'w', newline='') as fh:
        wr = csv.DictWriter(fh, FIELDS); wr.writeheader(); n = 0
        for item in a.refs:
            ep, ref = item.split('=', 1)
            for r in rows(ep, ref, a.assets):
                wr.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}); n += 1
    print(f'{n} rows -> {a.out}')


if __name__ == '__main__':
    main()
