"""Synthetic runtime benchmark for a trajectory-level physics fit (no repo data, no ground truth of real episodes).
One rigid object (0.2 kg box 8x8x10 cm): rests on a table (f0-99), is lifted/carried by 5 fingertip contacts (f100-199),
is put back (f200-299). Perceived poses = truth + noise. Variables per frame: pose correction (6), 5 fingertip contacts
x 4 pyramid edge weights, 4 table corner contacts x 4 edge weights = 42. Residuals: pose prior, Newton-Euler (accelerations
from central differences of the optimised poses), complementarity gap*force, penetration, force L2.
Usage: python fit_bench.py [T] [n_objects]"""
import sys, time
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation as R

T = int(sys.argv[1]) if len(sys.argv) > 1 else 300
NOBJ = int(sys.argv[2]) if len(sys.argv) > 2 else 2
dt, g, m, mu = 0.05, np.array([0, 0, -9.81]), 0.2, 1.0
I = np.diag([m * (0.08**2 + 0.10**2) / 12, m * (0.08**2 + 0.10**2) / 12, m * (0.08**2 * 2) / 12])
rng = np.random.default_rng(0)
# truth
t = np.arange(T)
lift = np.clip((t - 100) / 20, 0, 1) * np.clip((200 - t) / 20, 0, 1)
P0 = np.stack([0.3 * np.clip((t - 120) / 60, 0, 1), np.zeros(T), 0.05 + 0.15 * lift], 1)
ang = 0.5 * lift
Q0 = R.from_rotvec(np.stack([np.zeros(T), np.zeros(T), ang], 1))
corners = np.array([[sx * 0.04, sy * 0.04, -0.05] for sx in (-1, 1) for sy in (-1, 1)])   # table support points (obj frame)
tips_obj = np.array([[0.04, 0.0, 0.0], [0.04, 0.02, 0.02], [-0.04, 0.0, 0.01], [-0.04, 0.02, -0.01], [0.0, 0.04, 0.0]])
tips_n = np.array([[-1, 0, 0], [-1, 0, 0], [1, 0, 0], [1, 0, 0], [0, -1, 0]], float)      # inward normals (obj frame)
holding = (t >= 100) & (t < 200)
# perceived fingertips: on the surface while holding (+ noise), 5 cm away otherwise
tips_w = Q0[:, None].apply(np.broadcast_to(tips_obj, (T, 5, 3)).reshape(-1, 3)).reshape(T, 5, 3) if False else \
    np.einsum('tij,kj->tki', Q0.as_matrix(), tips_obj) + P0[:, None]
tips_w = tips_w + (~holding)[:, None, None] * 0.05 + rng.normal(0, 0.005, tips_w.shape)
Pp = P0 + rng.normal(0, 0.01, P0.shape)                                     # perceived pose: 1 cm, ~3 deg noise
Qp = Q0 * R.from_rotvec(rng.normal(0, np.deg2rad(3), (T, 3)))

def pyr(n):
    """4 edge directions of the friction pyramid around unit normal(s) n (..,3) -> (..,4,3)."""
    a = np.where(np.abs(n[..., :1]) < 0.9, np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    t1 = np.cross(n, a); t1 /= np.linalg.norm(t1, axis=-1, keepdims=True); t2 = np.cross(n, t1)
    return np.stack([n + mu * t1, n - mu * t1, n + mu * t2, n - mu * t2], -2) / np.sqrt(1 + mu**2)

NV = 6 + 5 * 4 + 4 * 4
W = dict(pos=1 / 0.01, rot=1 / np.deg2rad(3), F=1 / (0.05 * m * 9.81), M=1 / 0.005, comp=1 / (0.002 * 1.0), pen=1 / 0.001,
         f=0.03)

def residuals(x):
    X = x.reshape(T, NV)
    dp, dr = X[:, :3], X[:, 3:6]
    wt, wc = X[:, 6:26].reshape(T, 5, 4), X[:, 26:42].reshape(T, 4, 4)
    P = Pp + dp
    Rm = (Qp * R.from_rotvec(dr)).as_matrix()                                  # (T,3,3)
    # kinematics: central differences
    a = np.zeros_like(P); a[1:-1] = (P[2:] - 2 * P[1:-1] + P[:-2]) / dt**2
    Rrel = np.einsum('tji,tjk->tik', Rm[:-1], Rm[1:])                          # R_t^T R_{t+1}
    wb = R.from_matrix(Rrel).as_rotvec() / dt                                  # body angular velocity between frames
    wbb = np.zeros_like(P); wbb[1:-1] = 0.5 * (wb[1:] + wb[:-1])
    al = np.zeros_like(P); al[1:-1] = (wb[1:] - wb[:-1]) / dt
    # contact forces (world)
    nt_w = np.einsum('tij,kj->tki', Rm, tips_n)
    Ft = np.einsum('tke,tked->tkd', wt, pyr(nt_w))                             # (T,5,3)
    Fc = np.einsum('tke,ked->tkd', wc, np.broadcast_to(pyr(np.array([0, 0, 1.0])), (4, 4, 3)))
    pt = np.einsum('tij,kj->tki', Rm, tips_obj)                                # lever arms (world, from COM=origin)
    pc = np.einsum('tij,kj->tki', Rm, corners)
    Fsum = Ft.sum(1) + Fc.sum(1) + m * g
    Msum = np.cross(pt, Ft).sum(1) + np.cross(pc, Fc).sum(1)
    Mb = np.einsum('tji,tj->ti', Rm, Msum)                                     # body frame
    rF = (Fsum - m * a)[1:-1] * W['F']
    rM = (Mb - (wbb @ I.T + np.cross(wbb, wbb @ I.T)) - al @ I.T)[1:-1] * W['M']
    # gaps
    gt = np.linalg.norm((pt + P[:, None]) - tips_w, axis=-1)  # tip gap (T,5)
    gc = (pc + P[:, None])[..., 2]                                             # corner height above table z=0 (T,4)
    rcomp = np.concatenate([(wt.sum(-1) * gt).ravel(), (wc.sum(-1) * np.maximum(gc, 0)).ravel()]) * W['comp']
    rpen = np.minimum(gc, 0).ravel() * W['pen']
    return np.concatenate([(dp * W['pos']).ravel(), (dr * W['rot']).ravel(), rF.ravel(), rM.ravel(), rcomp, rpen,
                           (W['f'] * X[:, 6:]).ravel()])

def sparsity():
    nres = residuals(np.zeros(T * NV)).size
    S = lil_matrix((nres, T * NV), dtype=int); r = 0
    for k in range(T):                       # dp
        for j in range(3): S[r, k * NV + j] = 1; r += 1
    for k in range(T):
        for j in range(3): S[r, k * NV + 3 + j] = 1; r += 1
    for blk in range(2):                     # rF, rM: frames k-1..k+1, poses + forces at k
        for k in range(1, T - 1):
            for j in range(3):
                for kk in (k - 1, k, k + 1): S[r, kk * NV:kk * NV + 6] = 1
                S[r, k * NV + 6:k * NV + NV] = 1; r += 1
    for k in range(T):
        for c in range(5): S[r, k * NV:k * NV + 6] = 1; S[r, k * NV + 6 + 4 * c:k * NV + 10 + 4 * c] = 1; r += 1
    for k in range(T):
        for c in range(4): S[r, k * NV:k * NV + 6] = 1; S[r, k * NV + 26 + 4 * c:k * NV + 30 + 4 * c] = 1; r += 1
    for k in range(T):
        for c in range(4): S[r, k * NV:k * NV + 6] = 1; r += 1
    for k in range(T):
        for j in range(36): S[r, k * NV + 6 + j] = 1; r += 1
    assert r == nres
    return S

def err(x):
    X = x.reshape(T, NV); P = Pp + X[:, :3]
    return 100 * np.median(np.linalg.norm(P - P0, axis=1))

def ne_viol(x, mask):
    r = residuals(x); n = 6 * T; rF = r[n:n + 3 * (T - 2)].reshape(T - 2, 3) / W['F']
    return np.median(np.linalg.norm(rF[mask[1:-1]], axis=1))

S = sparsity()
tot = 0
for o in range(NOBJ):
    x0 = np.zeros(T * NV); x0[np.arange(T)[:, None] * NV + np.arange(6, NV)] = 0.05
    t0 = time.time()
    sol = least_squares(residuals, x0, jac_sparsity=S, bounds=(np.where(np.arange(T * NV) % NV >= 6, 0, -np.inf), np.inf),
                        method='trf', tr_solver='lsmr', x_scale='jac', max_nfev=200, verbose=0)
    el = time.time() - t0; tot += el
    print(f'object {o}: T={T} vars={T*NV} res={sol.fun.size} nfev={sol.nfev} njev={sol.njev} time={el:.1f}s '
          f'pos err cm perceived {err(np.zeros(T*NV)):.2f} -> fit {err(sol.x):.2f}; |F residual| N (carry) '
          f'{ne_viol(np.zeros(T*NV), holding):.3f} -> {ne_viol(sol.x, holding):.3f} ; status {sol.status}')
print(f'total {tot:.1f}s for {NOBJ} objects x {T} frames')
