"""H1 (PREREG_bias.md): per episode and object, the body-frame placement Delta that maps our tracked pose onto the
mocap pose through the kit's conversion: T . Delta . G = A . S~ (G = kit registration of the submitted mesh to the
scan, S~ = mocap pose at the scan anchor, A = world alignment). DIAGNOSTIC / CALIBRATION: reads public mocap; its
output is only used leave-one-episode-out (never on the episode it came from).
Usage: python -I bias_fit.py SCRATCH EP TRACK_NPZ MESH_DIR OUT_JSON"""
import sys, os, json, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
S, EP, TRK, MD, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
sys.path.insert(0, f'{S}/kit/v2d_submission_kit')
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
tab = pq.read_table(f'{S}/t3/ep{EP}.parquet', columns=['observation.objects']).to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
P = np.load(TRK)
T = {n: np.asarray(P[n], float) for n in names}
N = min(len(tab), min(len(v) for v in T.values()))


def M4(R, t):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t; return M


def chordal(Rs):
    U, _, Vt = np.linalg.svd(np.sum(Rs, 0)); R = U @ Vt
    if np.linalg.det(R) < 0: U[:, -1] *= -1; R = U @ Vt
    return R


def scan_path(n):
    q = f'{S}/t3/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{S}/t3/mesh/{n}/{n}_visual.glb'


G, Stl, axes_m, rest = {}, {}, {}, {}
for s, n in enumerate(names):
    m = trimesh.load(scan_path(n), force='mesh'); sv, sf = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(sv, sf)
    ca, Rb = T3._register_object_body(budget_mesh(f'{MD}/{n}.glb', 4096, 4096), (sv, sf), c, 1_000_003 * EP + 101 * s)
    G[n] = M4(Rb.T, ca)
    q = np.array([[o['pose'] for o in r if o['name'] == n][0] for r in tab['observation.objects'].iloc[:N]], float)
    Rm = Rot.from_quat(np.c_[q[:, 4:7], q[:, 3]]).as_matrix()
    Stl[n] = np.stack([M4(Rm[i], q[i, :3] + Rm[i] @ c) for i in range(N)])
    if n in SYM:                                             # scorer's symmetry axis in the scan frame -> mesh frame
        pts = _sample_mesh_surface(sv, sf, 1000, 7 + s) - c
        w, U = np.linalg.eigh(np.cov(pts.T))
        a_s = U[:, 0] if SYM[n] == 'half' else U[:, int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))]
        axes_m[n] = Rb.T @ a_s
    X = T[n][:N]
    sp = np.r_[0, np.linalg.norm(np.diff(X[:, :3, 3], axis=0), axis=1)] * 100
    rt = np.r_[0, [np.degrees(Rot.from_matrix(X[i - 1, :3, :3].T @ X[i, :3, :3]).magnitude()) for i in range(1, N)]]
    sm = lambda v: np.convolve(v, np.ones(3) / 3, 'same')
    still = (sm(sp) < 0.5) & (sm(rt) < 2.0); idx, s0 = [], None
    for i, v in enumerate(np.r_[still, False]):
        if v and s0 is None: s0 = i
        if not v and s0 is not None:
            if i - s0 >= 10: idx += list(range(s0, i))
            s0 = None
    rest[n] = np.array(idx, int)


def remove_twist(R, a):
    q = Rot.from_matrix(R).as_quat()                        # x, y, z, w
    p = np.dot(q[:3], a) * a; tw = np.r_[p, q[3]]
    if np.linalg.norm(tw) < 1e-9: return R
    tw /= np.linalg.norm(tw)
    return (Rot.from_quat(q) * Rot.from_quat(tw).inv()).as_matrix()


D = {n: np.eye(4) for n in names}
for it in range(5):
    src = np.concatenate([np.stack([(T[n][i] @ D[n] @ G[n])[:3, 3] for i in range(N)]) for n in names])
    dst = np.concatenate([Stl[n][:, :3, 3] for n in names])
    # A maps mocap world -> our world: src ~ A_R dst + A_t (Kabsch on positions; symmetric-safe)
    mu_s, mu_d = src.mean(0), dst.mean(0)
    U, _, Vt = np.linalg.svd((dst - mu_d).T @ (src - mu_s)); dd = np.sign(np.linalg.det(Vt.T @ U.T))
    AR = Vt.T @ np.diag([1, 1, dd]) @ U.T; A = M4(AR, mu_s - AR @ mu_d)
    for n in names:
        fr = rest[n] if len(rest[n]) >= 10 else np.arange(N)
        Xs = np.stack([np.linalg.inv(T[n][i]) @ A @ Stl[n][i] @ np.linalg.inv(G[n]) for i in fr])
        R = chordal(Xs[:, :3, :3])
        if n in axes_m: R = remove_twist(R, axes_m[n])
        D[n] = M4(R, np.median(Xs[:, :3, 3], 0))
res = dict(episode=EP, objects={})
for n in names:
    res['objects'][n] = dict(delta=np.round(D[n], 7).tolist(), rest_frames=int(len(rest[n])),
                             rot_deg=round(float(np.degrees(Rot.from_matrix(D[n][:3, :3]).magnitude())), 3),
                             trans_mm=round(float(np.linalg.norm(D[n][:3, 3]) * 1000), 2), symmetric=n in SYM)
    print(EP, n, res['objects'][n]['rot_deg'], 'deg', res['objects'][n]['trans_mm'], 'mm', 'rest', len(rest[n]), flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
