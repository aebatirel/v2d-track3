#!/usr/bin/env python
"""T3 generate-then-fit (CD-O sprint C1): non-rigid fit of a Sim(3)-placed generated mesh to OUR observed points.

GT-free. Reads only: the placed generated mesh (the probe's own Sim(3) output, our object frame, metres) and the
episode's observed points (scripts/obs_points.py npz: pts, cam, frame, voxel hit/free grid). No scan, no mocap, no
parquet pose, no *_align.npz.

Method (optimal-step non-rigid ICP, Amberg et al. CVPR 2007, own implementation so the data term can be robust):
  unknowns: one 3x4 affine per vertex (X, 4n x 3), stiffness alpha * ||(M kron G) X||^2 over mesh edges (M = node-arc
  incidence, G = diag(1,1,1,gamma)), alpha decreasing over a schedule; per alpha, iterate correspondences -> solve.
  Data term (robust, both directions, observed regions only):
    s2t  (weight w_s2t, default 0 since v2) each vertex -> nearest of its knn observed points that passes the tests:
         kept iff distance <= cap and the vertex faces the camera that saw the
         point: n_vertex . unit(cam - p) >= cos_vis (visibility test; a wall face turned away from that camera, e.g.
         the inner face behind a seen outer wall, cannot have produced the point), then the worst (1 - trim_q) of the
         kept residuals are dropped;
    t2s  each observed point -> nearest of its knn surface samples of the current mesh (barycentric row on its face)
         that passes the same tests with the face normal; total weight w_t2s * n (n = vertices). v1 (s2t + t2s,
         nearest only) shrank the dev pot by 2 % away from its observed band: in a noisy band around a thin wall the
         vertex->nearest-point direction picks the band's near edge or the other wall's band.
    Point-to-plane via projected targets: target = x + (n n^T + beta (I - n n^T)) (p - x), n = the mesh normal at x
    (beta = small point-to-point share, as in Li et al. 2008 / 2009). (v0 used PCA normals of the observed points:
    too noisy at 2 mm, lambda0/sum median 0.22, so dropped.)
  A tiny Tikhonov term eps ||X - X_prev||^2 keeps unobserved, unconnected pieces in place (no data -> no motion).
Hold-out: observed points from frame blocks (block index % holdout_mod == holdout_res) are never used in the fit; the
held-out residual is a GT-free over-fitting check.
Post: repair (trimesh: weld, degenerate/duplicate faces, winding, small holes), quadric decimation to <= out_faces
(fast_simplification, the kit packer's simplifier), kit budget_mesh check.

Usage: fit.py --mesh PLACED.ply --obs OBS.npz --out OUTDIR [--cfg CFG.json] [--stages-only]
Outputs in OUTDIR: fit.glb (final, packed), stage_<k>.ply (per alpha stage, working resolution), diag.json.
"""
import argparse, json, os, sys, time, hashlib
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree
import trimesh

DEFAULT = dict(
    work_faces=12000,         # working resolution of the deformed mesh
    ds_vox=0.002,             # observed points: voxel-average at 2 mm (uniform density, light denoise)
    nrm_k=16,                 # neighbours for observed-normal PCA
    holdout_block=10, holdout_mod=5, holdout_res=2,   # 20 % of 10-frame blocks held out
    alphas=[100.0, 50.0, 25.0, 12.0, 6.0, 3.0],
    gamma=1.0, max_it=5, tol=2e-4,                    # tol in normalised units (bbox diagonal = 1)
    cap_m=0.010, trim_q=0.9, cos_vis=0.2, beta=0.1, w_t2s=1.0, w_s2t=0.0, knn=32, eps=1e-4,
    mesh_samples=20000,       # coarse enough that knn=32 reaches the other face of a thin wall (6-9 mm patch)
    obs_per_it=40000,         # random subset of the (voxel-averaged) training points per iteration (speed)
    stop_stage=None,          # index into alphas of the last stage kept (None = all)
    out_faces=4000, close_hole_max=200,
)


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# ------------------------------------------------------------------------------------------------- observations
def voxel_avg(P, C, vox):
    key = np.floor(P / vox).astype(np.int64)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    out_p = np.zeros((len(cnt), 3)); out_c = np.zeros((len(cnt), 3))
    for k in range(3):
        out_p[:, k] = np.bincount(inv, P[:, k], minlength=len(cnt)) / cnt
        out_c[:, k] = np.bincount(inv, C[:, k], minlength=len(cnt)) / cnt
    return out_p, out_c, cnt


def oriented_normals(P, C, k):
    tree = cKDTree(P)
    _, idx = tree.query(P, k=min(k, len(P)))
    Q = P[idx] - P[idx].mean(1, keepdims=True)
    cov = np.einsum('nki,nkj->nij', Q, Q) / Q.shape[1]
    w, V = np.linalg.eigh(cov)
    n = V[:, :, 0]
    s = np.sign(np.einsum('ni,ni->n', n, C - P)); s[s == 0] = 1
    n = n * s[:, None]
    curv = w[:, 0] / np.maximum(w.sum(1), 1e-18)
    return n, curv


def load_obs(path, cfg):
    z = np.load(path)
    P = z['pts'].astype(np.float64); C = z['cam'].astype(np.float64); fr = z['frame'].astype(np.int64)
    held = (fr // cfg['holdout_block']) % cfg['holdout_mod'] == cfg['holdout_res']
    out = {}
    for name, m in (('train', ~held), ('held', held)):
        p, c, cnt = voxel_avg(P[m], C[m], cfg['ds_vox'])
        u = c - p
        u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-12)
        out[name] = dict(p=p, u=u, cnt=cnt, raw=int(m.sum()))
    grid = dict(lo=z['lo'], vox=float(z['vox']), hits=z['hits'], free=z['free'])
    return out, grid


# ------------------------------------------------------------------------------------------------- mesh helpers
def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-18)


def face_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    return fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-18)


def sample_bary(V, F, n, seed):
    """Area-weighted surface samples with face ids and barycentric coordinates."""
    rng = np.random.default_rng(seed)
    a = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    fid = rng.choice(len(F), n, p=a / a.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    b = np.stack([1 - s, s * (1 - r2), s * r2], 1)
    pts = np.einsum('nk,nkj->nj', b, V[F[fid]])
    return pts, fid, b


def proj_target(x, p, n, beta):
    d = p - x
    dn = np.einsum('ni,ni->n', d, n)[:, None] * n
    return x + dn + beta * (d - dn)


def obs_residuals(V, F, P, seed=1, n=300000):
    S, _, _ = sample_bary(V, F, n, seed)
    d = cKDTree(S).query(P)[0]
    ds = np.sort(d)
    return dict(med_mm=float(np.median(d) * 1e3), tmean90_mm=float(ds[:int(0.9 * len(ds))].mean() * 1e3),
                p90_mm=float(np.quantile(d, 0.9) * 1e3))


def mesh_to_obs(V, F, P, seed=2, n=100000):
    S, _, _ = sample_bary(V, F, n, seed)
    lo, hi = P.min(0), P.max(0)
    inb = np.all((S > lo) & (S < hi), 1)
    d = cKDTree(P).query(S[inb])[0]
    ds = np.sort(d)
    return dict(tmean90_mm=float(ds[:int(0.9 * len(ds))].mean() * 1e3), frac_inbox=float(inb.mean()))


def free_violation(V, F, grid, seed=3, n=100000):
    """Fraction of surface samples in voxels our cameras saw THROUGH (free >= 3 and hit ratio < 0.1)."""
    S, _, _ = sample_bary(V, F, n, seed)
    ijk = np.floor((S - grid['lo']) / grid['vox']).astype(int)
    sh = np.array(grid['hits'].shape)
    ok = np.all((ijk >= 0) & (ijk < sh), 1)
    h = np.zeros(n); f = np.zeros(n)
    h[ok] = grid['hits'][tuple(ijk[ok].T)]; f[ok] = grid['free'][tuple(ijk[ok].T)]
    bad = (f >= 3) & (h / np.maximum(h + f, 1) < 0.1)
    return dict(free_frac=float(bad.mean()), outside_grid=float((~ok).mean()))


def self_intersections(V, F):
    try:
        import pymeshlab
        ms = pymeshlab.MeshSet(); ms.add_mesh(pymeshlab.Mesh(V, F))
        ms.compute_selection_by_self_intersections_per_face()
        return int(ms.current_mesh().selected_face_number())
    except Exception as err:                                           # noqa: BLE001
        print('self-intersection check failed:', err, file=sys.stderr)
        return -1


def distortion(V0, V, F):
    a0 = 0.5 * np.linalg.norm(np.cross(V0[F[:, 1]] - V0[F[:, 0]], V0[F[:, 2]] - V0[F[:, 0]]), axis=1)
    a1 = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    flip = np.einsum('ni,ni->n', face_normals(V0, F), face_normals(V, F)) < 0
    E = trimesh.Trimesh(V0, F, process=False).edges_unique
    l0 = np.linalg.norm(V0[E[:, 0]] - V0[E[:, 1]], axis=1); l1 = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    lr = np.abs(np.log(np.maximum(l1, 1e-12) / np.maximum(l0, 1e-12)))
    disp = np.linalg.norm(V - V0, axis=1) * 1e3
    def rms(Vx, ax):                                                   # area-weighted RMS radius (CD-O's scale fix)
        cen = V0[F].mean(1) if Vx is V0 else V[F].mean(1)
        c = (cen * ax[:, None]).sum(0) / ax.sum()
        return np.sqrt((((cen - c) ** 2).sum(1) * ax).sum() / ax.sum())
    return dict(area_ratio=float(a1.sum() / a0.sum()), rms_ratio=float(rms(V, a1) / rms(V0, a0)),
                flip_frac=float((flip * a0).sum() / a0.sum()),
                edge_logratio_med=float(np.median(lr)), edge_logratio_p99=float(np.quantile(lr, 0.99)),
                disp_med_mm=float(np.median(disp)), disp_p95_mm=float(np.quantile(disp, 0.95)),
                disp_max_mm=float(disp.max()))


# ------------------------------------------------------------------------------------------------- NICP
def nicp(V0, F, P, UP, cfg, log, stage_cb=None):
    """V0, P in normalised units. Returns list of per-stage vertex arrays."""
    n = len(V0)
    E = trimesh.Trimesh(V0, F, process=False).edges_unique
    ne = len(E)
    M = sp.coo_matrix((np.r_[np.ones(ne), -np.ones(ne)], (np.r_[np.arange(ne), np.arange(ne)], np.r_[E[:, 0], E[:, 1]])),
                      shape=(ne, n)).tocsr()
    G = sp.diags([1.0, 1.0, 1.0, cfg['gamma']])
    MG = sp.kron(M, G).tocsr()
    rows = np.repeat(np.arange(n), 4); cols = np.arange(4 * n)
    D = sp.csr_matrix((np.c_[V0, np.ones(n)].ravel(), (rows, cols)), shape=(n, 4 * n))
    X = np.tile(np.r_[np.eye(3), np.zeros((1, 3))], (n, 1))
    tP = cKDTree(P)
    cap = cfg['cap_m']; cosv = cfg['cos_vis']; beta = cfg['beta']
    I4 = sp.identity(4 * n, format='csr')
    stages = []
    for si, alpha in enumerate(cfg['alphas']):
        for it in range(cfg['max_it']):
            V = D @ X
            vn = vertex_normals(V, F)
            # s2t
            kn = cfg['knn']
            dk, jk = tP.query(V, k=kn)
            vk = (dk <= cap) & (np.einsum('ni,nki->nk', vn, UP[jk]) >= cosv)
            first = np.argmax(vk, 1); ok = vk.any(1)
            d = dk[np.arange(n), first]; j = jk[np.arange(n), first]
            if ok.sum() > 10:
                ok &= d <= np.quantile(d[ok], cfg['trim_q'])
            Us = proj_target(V[ok], P[j[ok]], vn[ok], beta)
            Ds = D[np.where(ok)[0]]
            # t2s
            S, fid, b = sample_bary(V, F, cfg['mesh_samples'], seed=100 * si + it)
            fn = face_normals(V, F)
            sub = np.random.default_rng(1000 * si + it).choice(len(P), min(len(P), cfg['obs_per_it']), replace=False)
            Pi, Ui = P[sub], UP[sub]
            dtk, kk_ = cKDTree(S).query(Pi, k=kn)
            vt = (dtk <= cap) & (np.einsum('nki,ni->nk', fn[fid[kk_]], Ui) >= cosv)
            ft = np.argmax(vt, 1); okt = vt.any(1)
            dt = dtk[np.arange(len(Pi)), ft]; k = kk_[np.arange(len(Pi)), ft]
            if okt.sum() > 10:
                okt &= dt <= np.quantile(dt[okt], cfg['trim_q'])
            kk = k[okt]
            B = sp.csr_matrix((b[kk].ravel(), (np.repeat(np.arange(len(kk)), 3), F[fid[kk]].ravel())), shape=(len(kk), n))
            Ut = proj_target(S[kk], Pi[okt], fn[fid[kk]], beta)
            Dt = B @ D
            ws = cfg['w_s2t']                                         # per-row weights; totals in units of n
            wt = cfg['w_t2s'] * np.sqrt(n / max(okt.sum(), 1))
            A = sp.vstack([alpha * MG, ws * Ds, wt * Dt, np.sqrt(cfg['eps']) * I4]).tocsr()
            Bv = np.vstack([np.zeros((MG.shape[0], 3)), ws * Us, wt * Ut, np.sqrt(cfg['eps']) * X])
            X_new = spsolve((A.T @ A).tocsc(), A.T @ Bv)
            X_new = np.asarray(X_new).reshape(4 * n, 3)
            dv = np.abs(D @ X_new - V).max()
            X = X_new
            log(f'  stage {si} alpha {alpha:g} it {it}: s2t {int(ok.sum())}/{n} t2s {int(okt.sum())}/{len(Pi)} '
                f'med_s2t {np.median(d[ok]) if ok.any() else -1:.5f} med_t2s {np.median(dt[okt]) if okt.any() else -1:.5f} max_dv {dv:.5f}')
            if dv < cfg['tol']:
                break
        Vs = D @ X
        stages.append(Vs.copy())
        if stage_cb:
            stage_cb(si, alpha, Vs)
    return stages


# ------------------------------------------------------------------------------------------------- post
def repair_and_pack(V, F, cfg, out_path):
    """Repair with trimesh (weld, drop degenerate/duplicate faces, fix winding, fill 3/4-edge holes), then quadric
    decimation to <= out_faces with fast_simplification (the kit packer's own simplifier). pymeshlab's meshing plugins
    do not load on this machine (no libOpenGL), so its hole closing is not used."""
    import fast_simplification
    tm = trimesh.Trimesh(V, F, process=True)
    tm.update_faces(tm.nondegenerate_faces()); tm.update_faces(tm.unique_faces()); tm.remove_unreferenced_vertices()
    trimesh.repair.fix_winding(tm)
    trimesh.repair.fill_holes(tm)
    if len(tm.faces) > cfg['out_faces']:
        v, f = fast_simplification.simplify(np.asarray(tm.vertices, np.float64), np.asarray(tm.faces, np.int64),
                                            target_count=cfg['out_faces'])
        tm = trimesh.Trimesh(v, f, process=True)
        tm.update_faces(tm.nondegenerate_faces()); tm.remove_unreferenced_vertices()
        trimesh.repair.fix_winding(tm); trimesh.repair.fill_holes(tm)
    tm.export(out_path)
    return tm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mesh', required=True); ap.add_argument('--obs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--cfg'); ap.add_argument('--kit', default='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/loc/kit/v2d_submission_kit')
    ap.add_argument('--stages-only', action='store_true', help='write every stage, no final pack')
    a = ap.parse_args()
    cfg = dict(DEFAULT)
    if a.cfg:
        cfg.update(json.load(open(a.cfg)))
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, 'fit.log'), 'a')

    def log(s):
        print(s, flush=True); logf.write(s + '\n'); logf.flush()

    t0 = time.time()
    log(f'fit.py mesh {a.mesh} obs {a.obs} cfg {json.dumps(cfg)}')
    obs, grid = load_obs(a.obs, cfg)
    log(f'obs train {obs["train"]["raw"]} raw -> {len(obs["train"]["p"])} vox; held {obs["held"]["raw"]} -> {len(obs["held"]["p"])} ({time.time() - t0:.0f} s)')
    raw = trimesh.load(a.mesh, force='mesh', process=True)
    import fast_simplification
    v, f = fast_simplification.simplify(np.asarray(raw.vertices, np.float64), np.asarray(raw.faces, np.int64),
                                        target_count=cfg['work_faces'])
    w = trimesh.Trimesh(v, f, process=True)
    w.update_faces(w.nondegenerate_faces()); w.remove_unreferenced_vertices()
    V0m, F = np.asarray(w.vertices, np.float64), np.asarray(w.faces, np.int64)
    log(f'work mesh {len(V0m)} v {len(F)} f (raw {len(raw.vertices)} v {len(raw.faces)} f) watertight {w.is_watertight} bodies {w.body_count}')
    c = V0m.mean(0); s = float(np.linalg.norm(V0m.max(0) - V0m.min(0)))
    nz = lambda x: (x - c) / s                                        # noqa: E731
    dz = lambda x: x * s + c                                          # noqa: E731
    cfgn = dict(cfg); cfgn['cap_m'] = cfg['cap_m'] / s; cfgn['tol'] = cfg['tol']
    P, UP = nz(obs['train']['p']), obs['train']['u']
    Ph = obs['held']['p']
    diag = dict(mesh=a.mesh, mesh_sha256=sha256(a.mesh), obs=a.obs, cfg=cfg, norm_scale_m=s, work_v=len(V0m), work_f=len(F),
                obs_train=len(P), obs_held=len(Ph), stages=[])

    def evaluate(tag, Vm, alpha=None):
        r = dict(tag=tag, alpha=alpha)
        r['train_o2m'] = obs_residuals(Vm, F, obs['train']['p'])
        r['held_o2m'] = obs_residuals(Vm, F, Ph)
        r['m2o'] = mesh_to_obs(Vm, F, obs['train']['p'])
        r.update(free_violation(Vm, F, grid))
        r.update(distortion(V0m, Vm, F))
        r['selfint_faces'] = self_intersections(Vm, F)
        return r

    r0 = evaluate('input', V0m)
    diag['stages'].append(r0)
    log(json.dumps(r0))
    trimesh.Trimesh(V0m, F, process=False).export(os.path.join(a.out, 'stage_in.ply'))

    def cb(si, alpha, Vn):
        Vm = dz(Vn)
        trimesh.Trimesh(Vm, F, process=False).export(os.path.join(a.out, f'stage_{si}.ply'))
        r = evaluate(f'stage_{si}', Vm, alpha)
        diag['stages'].append(r)
        log(json.dumps(r) + f' ({time.time() - t0:.0f} s)')
        json.dump(diag, open(os.path.join(a.out, 'diag.json'), 'w'), indent=1)

    alphas = cfg['alphas'] if cfg['stop_stage'] is None else cfg['alphas'][:cfg['stop_stage'] + 1]
    cfgn['alphas'] = alphas
    stages = nicp(nz(V0m), F, P, UP, cfgn, log, stage_cb=cb)
    if not a.stages_only:
        Vf = dz(stages[-1])
        outp = os.path.join(a.out, 'fit.glb')
        tm = repair_and_pack(Vf, F, cfg, outp)
        sys.path.insert(0, a.kit)
        from v2dlb.mesh_budget import budget_mesh
        bv, bf = budget_mesh(outp, 4096, 4096)
        real = ~((bf[:, 0] == bf[:, 1]) | (bf[:, 1] == bf[:, 2]) | (bf[:, 0] == bf[:, 2]))
        Vp, Fp = np.asarray(tm.vertices), np.asarray(tm.faces)
        fin = dict(path=outp, sha256=sha256(outp), faces=int(len(tm.faces)), verts=int(len(tm.vertices)),
                   watertight=bool(tm.is_watertight), bodies=int(tm.body_count), budget_faces=int(real.sum()),
                   budget_verts=int(len(np.unique(bf[real]))),
                   train_o2m=obs_residuals(Vp, Fp, obs['train']['p']), held_o2m=obs_residuals(Vp, Fp, Ph),
                   m2o=mesh_to_obs(Vp, Fp, obs['train']['p']), **free_violation(Vp, Fp, grid))
        diag['final'] = fin
        log('final ' + json.dumps(fin))
    diag['secs'] = round(time.time() - t0, 1)
    json.dump(diag, open(os.path.join(a.out, 'diag.json'), 'w'), indent=1)
    log(f'done {diag["secs"]} s')


if __name__ == '__main__':
    main()
