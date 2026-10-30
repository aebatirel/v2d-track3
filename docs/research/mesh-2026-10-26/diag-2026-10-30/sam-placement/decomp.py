"""[D] Decompose the placement error of a mesh in OUR object frame against the public scan.

For a placed mesh P (our frame, which the kit treats as the scan frame: library_v3 ADD is 2-10 mm and the display
alignments are <= 6 deg / 4.5 mm), find the similarity A = (s, R, t) that best maps P onto the scan (multi-start:
identity + 24 PCA cube starts, symmetric trimmed Sim(3) ICP). A = identity means a perfect placement.
  size_err   = 1/s - 1         (our mesh is this much too big)
  rot        = angle(R), axis in the scan's PCA basis (long/mid/short), swing-twist about the reference axis
  trans      = |A(c) - c| for the placed mesh's surface centroid c
  addlike    = mean |A(x) - x| over surface samples (all effects, mm); add_rigid = same with the scale removed
               about the centroid (what the kit's scale-normalised registration sees)
  shape      = symmetric mean distance after A (mm, all / best 90 %), extents ratio along the scan PCA axes and along
               our crop camera ray (single-view stretch test)
Usage: decomp.py --models sam3d,pixal_mv,hy21,trellis2 --out decomp.jsonl [--placed label=obj=path ...]
"""
import argparse, json, math, sys, time
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa


def ref_axes(obj, Y):
    c, V, sd = pca(Y)
    return c, V


def extent_along(X, u, lo=2, hi=98):
    p = X @ u
    return np.percentile(p, hi) - np.percentile(p, lo)


def decompose(P, obj, Y=None, cam=None, n=4000):
    scan = load_scan(obj)
    X, _ = surf(P, n, seed=1)
    if Y is None:
        Y, _ = surf(scan, n, seed=2)
    ident = (1.0, np.eye(3), np.zeros(3))
    A, res = best_sim3(X, Y, extra_starts=[ident], keep=0.9, iters=40)
    s, R, t = A
    # second-best distinct minimum (rotation > 30 deg away): ambiguity of the scan registration itself
    alt = [r for r in res if angle_deg(r[1][1] @ R.T) > 30]
    c = (X).mean(0)
    cY, V = ref_axes(obj, Y)
    ax = rot_axis(R)
    comp = np.abs(V.T @ ax)
    tw = [swing_twist(R, V[:, k])[1] for k in range(3)]
    tilt = [swing_twist(R, V[:, k])[0] for k in range(3)]
    AX = apply(A, X)
    addlike = np.linalg.norm(AX - X, axis=1).mean()
    Ac = apply(A, c[None])[0]
    rig = (X - c) @ R.T + Ac
    add_rigid = np.linalg.norm(rig - X, axis=1).mean()
    ext_ratio = [extent_along(AX, V[:, k]) / extent_along(Y, V[:, k]) for k in range(3)]
    out = dict(scale_A=s, size_err_pct=(1 / s - 1) * 100, rot_deg=angle_deg(R), axis_pca=comp.round(3).tolist(),
               twist_pca_deg=np.round(tw, 1).tolist(), tilt_pca_deg=np.round(tilt, 1).tolist(),
               trans_mm=float(np.linalg.norm(Ac - c) * 1e3), addlike_mm=float(addlike * 1e3),
               add_rigid_mm=float(add_rigid * 1e3), shape_mm=float(sym_dist(AX, Y) * 1e3),
               shape90_mm=float(sym_dist(AX, Y, 0.9) * 1e3), ext_ratio_pca=np.round(ext_ratio, 3).tolist(),
               alt_gap=float((alt[0][0] - res[0][0]) * 1e3) if alt else None,
               R=R.round(5).tolist(), t=np.round(t, 5).tolist(), scan_pca=V.round(4).tolist())
    if obj in SYM:
        # symmetry axis: scan PCA axis most invariant under a 90 / 180 deg turn (mesh_metric.sym_axis rule)
        from scipy.spatial import cKDTree
        tr = cKDTree(Y - cY)
        best = None
        ang = math.pi / 2 if SYM[obj] == 'axial' else math.pi
        from scipy.spatial.transform import Rotation as Rot
        for k in range(3):
            Rk = Rot.from_rotvec(V[:, k] * ang).as_matrix()
            d = tr.query((Y - cY) @ Rk.T)[0].mean()
            if best is None or d < best[0]:
                best = (d, k)
        k = best[1]
        out['sym_axis_pca'] = k
        out['sym_tilt_deg'], out['sym_roll_deg'] = swing_twist(R, V[:, k])
    if cam is not None:
        u = Y.mean(0) - cam; u /= np.linalg.norm(u)
        # two perpendiculars
        a = np.cross(u, [0, 0, 1.0]); a /= np.linalg.norm(a); b = np.cross(u, a)
        ra = extent_along(AX, u) / extent_along(Y, u)
        rp = [extent_along(AX, a) / extent_along(Y, a), extent_along(AX, b) / extent_along(Y, b)]
        out.update(ray_ratio=float(ra), perp_ratio=[float(x) for x in rp], ray_vs_perp=float(ra / np.mean(rp)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', default='sam3d,pixal_mv,hy21,trellis2')
    ap.add_argument('--objs', default=','.join(OBJS))
    ap.add_argument('--seeds', default='42,7')
    ap.add_argument('--out', required=True)
    ap.add_argument('--placed', nargs='*', default=[])
    a = ap.parse_args()
    fo = open(a.out, 'a')
    jobs = []
    for model in [m for m in a.models.split(',') if m]:
        for obj in a.objs.split(','):
            for seed in a.seeds.split(','):
                m2 = 'trellis2_1024' if (model == 'trellis2' and obj == 'blue_cup') else model
                _, p = gen_paths(m2, obj, seed)
                jobs.append((model, obj, int(seed), p))
    for spec in a.placed:
        lab, obj, p = spec.split('=', 2)
        jobs.append((lab, obj, None, p))
    cams = {}
    for model, obj, seed, p in jobs:
        if not os.path.exists(p):
            print('missing', p, flush=True); continue
        t0 = time.time()
        if obj not in cams:
            obs = load_obs(obj, n=2000)
            cams[obj] = crop_cam(obj, obs)[0]
        P = load_mesh(p)
        r = decompose(P, obj, cam=cams[obj])
        r.update(model=model, obj=obj, seed=seed, path=p, secs=round(time.time() - t0, 1))
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                          if k not in ('R', 't', 'scan_pca')}), flush=True)
        fo.write(json.dumps(r) + '\n'); fo.flush()


if __name__ == '__main__':
    main()
