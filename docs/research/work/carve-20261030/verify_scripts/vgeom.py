"""Verifier's independent overlap + sink check (scratch, 2026-10-30). Hulls = the ones the BUILT FlashCHORD model uses
(vsim.py npz, mesh frame), poses = own parse of our reference parquet; Monte Carlo volume (random points, not a grid).
Usage: vgeom.py REF.parquet DEF.npz CUT.npz HOST GUEST PLACED SEGS_JSON OUT.json   (no ground truth)"""
import json, sys
import numpy as np, pyarrow.parquet as pq
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot

ref, fdef, fcut, host, guest, placed, segs, out = sys.argv[1:9]; placed = int(placed); segs = json.loads(segs)
row = pq.read_table(ref, columns=['object_body_names', 'object_body_position', 'object_body_wxyz']).to_pylist()[0]
nb = list(row['object_body_names']); P = np.array(row['object_body_position'], float); Q = np.array(row['object_body_wxyz'], float)
nF = len(P)


def pose(n, f):
    k = nb.index(n); T = np.eye(4); T[:3, :3] = Rot.from_quat(Q[f, k][[1, 2, 3, 0]]).as_matrix(); T[:3, 3] = P[f, k]; return T


def hulls(npz, n):
    d = np.load(npz); V = d[n]; c = np.cumsum(np.r_[0, d[n + '_n']])
    hs = [V[c[i]:c[i + 1]] for i in range(len(c) - 1)]
    return [(ConvexHull(h).equations, h.min(0), h.max(0), ConvexHull(h).volume) for h in hs]


def inside(H, X, tol=1e-9):
    m = np.zeros(len(X), bool)
    for eq, lo, hi, _ in H:
        s = np.flatnonzero(~m & np.all(X >= lo - tol, 1) & np.all(X <= hi + tol, 1))
        if len(s):
            m[s[np.all(X[s] @ eq[:, :3].T + eq[:, 3] <= tol, 1)]] = True
    return m


Hd = {n: hulls(fdef, n) for n in (host, guest)}; Hc = {n: hulls(fcut, n) for n in (host, guest)}
rng = np.random.default_rng(7)
allv = np.vstack([np.vstack([[lo, hi] for _, lo, hi, _ in Hd[guest]])])
lo, hi = allv.min(0), allv.max(0); N = 600000; box = np.prod(hi - lo)
S = lo + rng.random((N, 3)) * (hi - lo); w = box / N * 1e6          # cm3 per sample
inGd = inside(Hd[guest], S); inGc = inside(Hc[guest], S)
Sd, Sc = S[inGd], S[inGc]
rep = dict(method='MC %d pts, built-model hulls' % N, hulls_def={n: len(Hd[n]) for n in Hd}, hulls_cut={n: len(Hc[n]) for n in Hc},
           guest_union_cm3=[round(len(Sd) * w, 1), round(len(Sc) * w, 1)],
           carved_guest_points_outside_default=int((inGc & ~inGd).sum()),
           host_cut_minus_def_hull_cm3=round(sum(h[3] for h in Hc[host]) * 1e6 - sum(h[3] for h in Hd[host]) * 1e6, 2))
# host pieces must lie inside the default host hulls (subset): check piece vertices
Vh = np.vstack([np.load(fcut)[host]]); rep['host_piece_vertices_outside_default'] = int((~inside(Hd[host], Vh, tol=2e-4)).sum())
Vg = np.load(fcut)[guest]; rep['guest_piece_vertices_outside_default'] = int((~inside(Hd[guest], Vg, tol=2e-4)).sum())
rel = lambda f: np.linalg.inv(pose(host, f)) @ pose(guest, f)
ap = lambda T, X: X @ T[:3, :3].T + T[:3, 3]
rest = sorted({f for s, e in segs for f in range(s, e + 1)})
frames = sorted(set(range(0, nF, 3)) | {0, placed, nF - 1} | set(rest))
od, oc = {}, {}
for f in frames:
    T = rel(f); od[f] = inside(Hd[host], ap(T, Sd)).sum() * w; oc[f] = inside(Hc[host], ap(T, Sc)).sum() * w
inc = max(oc[f] - od[f] for f in frames)
rep['overlap_cm3'] = dict(frame0=[round(od[0], 2), round(oc[0], 2)], placed=[round(od[placed], 2), round(oc[placed], 2)],
                          rest_max=[round(max(od[f] for f in rest), 2), round(max(oc[f] for f in rest), 2)],
                          all_max=[round(max(od.values()), 2), round(max(oc.values()), 2)],
                          all_argmax_def=int(max(od, key=od.get)), all_argmax_cut=int(max(oc, key=oc.get)),
                          max_increase=round(inc, 3), frames=len(frames), note='[default, carved], MC')
# sink / pocket test: translate the guest (carved hulls) in the host frame; free travel before contact (> 0.05 cm3)
def travel(f, dvec):
    T = rel(f); X = ap(T, Sc); res = []
    for mm in range(0, 41):
        res.append(inside(Hc[host], X + dvec * mm * 1e-3).sum() * w)
        if res[-1] > 0.05:
            return mm, [round(x, 2) for x in res]
    return '>40', None
sink = {}
for f in sorted({0, placed}):
    Rh = pose(host, f)[:3, :3]; down = Rh.T @ np.array([0, 0, -1.0])
    hx = Rh.T @ np.array([1.0, 0, 0]); hy = Rh.T @ np.array([0, 1.0, 0])
    sink[str(f)] = {'down_mm': travel(f, down)[0], 'up_mm': travel(f, -down)[0],
                    'lateral_mm': {k: travel(f, v)[0] for k, v in (('+x', hx), ('-x', -hx), ('+y', hy), ('-y', -hy))}}
rep['free_travel_carved'] = sink
json.dump(rep, open(out, 'w'), indent=1); print(json.dumps(rep))
