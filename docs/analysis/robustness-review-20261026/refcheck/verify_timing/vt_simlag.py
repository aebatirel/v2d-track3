"""verify_timing: onset timing of the SIMULATED object (stored rollouts r1-r5) against OUR reference, own code
(27 Oct 2026, CPU; no ground truth needed for sim - ref; mocap only for the sim - mocap column).
Rollouts read with the kit's read_trajectory (pose_xyzw for the sim path, reference_xyzw for the reference column).
Usage: python -I vt_simlag.py OUT.json
"""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
from vt_lag import cross, rot_from_rest, principal_axis
sys.path.insert(0, f'{L.RC}/kit/v2d_submission_kit')
from v2dlb.submission_parquet import read_trajectory


def grid(tr, Q, B):
    w0 = tr.world_index == tr.world_index.min()
    fr = np.unique(tr.frame_index[w0]); G = np.full((len(fr), B, 7), np.nan)
    for f, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]):
        G[np.searchsorted(fr, f), s] = q
    return G


def main():
    C = L.canon(); out = []
    for ep in L.PUBLIC:
        e = C[ep]
        if not e.get('results_dir'):
            continue
        names, gt = L.load_mocap(ep); lib = L.lib_of(e, 'ref')
        for f in sorted(glob.glob(f"{L.STORE}/{e['results_dir']}/r*/episode_*.parquet")):
            tr = read_trajectory(f)
            S = grid(tr, tr.pose_xyzw, len(names)); R = grid(tr, tr.reference_xyzw, len(names))
            for s, n in enumerate(names):
                cg = L.surf_centroid(L.scan_mesh(n)); co = L.surf_centroid(L.our_mesh(lib, n))
                Pg = L.point_path(gt[n], cg); dg = np.linalg.norm(Pg - Pg[:5].mean(0), axis=1)
                if dg.max() < 0.03:
                    continue
                row = dict(ep=ep, obj=n, r=os.path.basename(os.path.dirname(f)))
                ax = principal_axis(L.our_mesh(lib, n)) if 'cup' in n else None
                axg = principal_axis(L.scan_mesh(n)) if 'cup' in n else None
                tg = {'1cm': cross(dg, 0.01), '10deg': cross(rot_from_rest(gt[n], axg), 10.0)}
                for lab, G in (('sim', S), ('ref', R)):
                    M = L.to44(G[:, s, :3], L.quat_wxyz_to_R(G[:, s, [6, 3, 4, 5]]))
                    P = L.point_path(M, co); d = np.linalg.norm(P - P[:5].mean(0), axis=1)
                    row[lab] = {'1cm': cross(d, 0.01), '10deg': cross(rot_from_rest(M, ax), 10.0)}
                for k in ('1cm', '10deg'):
                    a, b = row['sim'][k], row['ref'][k]
                    row[f'sim_minus_ref_{k}'] = None if a is None or b is None else round(a - b, 3)
                    row[f'ref_minus_mocap_{k}'] = None if b is None or tg[k] is None else round(b - tg[k], 3)
                out.append(row)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    for k in ('1cm', '10deg'):
        v = np.array([r[f'sim_minus_ref_{k}'] for r in out if r[f'sim_minus_ref_{k}'] is not None])
        vv = v[np.abs(v) <= 5]
        print(k, 'pairs', len(v), 'median %.2f' % np.median(v), 'IQR %.2f..%.2f' % tuple(np.percentile(v, [25, 75])),
              '| |x|<=5: n', len(vv), 'median %.2f' % np.median(vv))


if __name__ == '__main__':
    main()
