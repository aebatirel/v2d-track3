"""Independent re-implementation (verify_scorer check, 27 Oct 2026) of the registered Track 3 scoring.

Written from the official metric file (metric_code/track_3/AUC.py), NOT from pipeline/score_registered.py or the scorer
check's score_variants.py. What is shared with them, on purpose:
  - the registration itself: `_register_object_body` and `_sample_mesh_surface`, `_surface_moments` are taken from the
    OFFICIAL metric file (metric_code/track_3/AUC.py, loaded by path), not from v2dlb;
  - the candidate mesh: the kit packer's budget_mesh(glb, 4096, 4096) (what the packer uploads);
  - the stand-in definition for the hidden host geometry (anchor = scan surface centroid, 1000 surface points with seed
    7+slot, cup axis = distinct PCA axis, lid axis = thinnest PCA axis), because the numbers to verify are defined
    with it. The anchor and the PCA axis are recomputed here with my own code.
Own code: parquet readers (GT w-first -> xyzw; rollout via pyarrow), pose conversion to the anchor, frame-0 scene
alignment, symmetric ADD, AUC, SP-SR, MP-SR (numpy + scipy Rotation).
Ground truth (public mocap) is read only for scoring.
"""
import importlib.util, os, sys
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot

R = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
KIT = f'{R}/kit/v2d_submission_kit'
T3D = f'{R}/t3'
STORE = f'{R}/store'
LIB = '/home/user/v2d-track3/meshes'
SYM = {'beige_cup': 360, 'blue_cup': 360, 'white_pot_lid': 2}


def official(name='AUC'):
    spec = importlib.util.spec_from_file_location(f'off_{name.replace("-", "_")}', f'{KIT}/metric_code/track_3/{name}.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


OFF = official('AUC')


def budget(path):
    sys.path.insert(0, KIT)
    from v2dlb.mesh_budget import budget_mesh
    return budget_mesh(path, 4096, 4096)


def scan_path(n):
    q = f'{T3D}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{T3D}/mesh/{n}/{n}_visual.glb'


def load_vf(path):
    m = trimesh.load(path, force='mesh')
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def my_centroid(v, f):
    t = v[f]; ar = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
    k = ar > 1e-12
    return (t[k].mean(1) * ar[k, None]).sum(0) / ar[k].sum()


def host(n, slot, n_points=1000, faces=0, weld_dec=None, anchor_mode='centroid'):
    """Stand-in host geometry. faces>0: the REGISTRATION scan is welded and decimated (my own weld via trimesh
    merge_vertices + fast_simplification, or weld_dec='cluster' for vertex clustering); anchor, points, axis stay full."""
    v, f = load_vf(scan_path(n))
    c0 = my_centroid(v, f)
    c = (v.min(0) + v.max(0)) / 2 if anchor_mode == 'bbox' else c0
    pts = OFF._sample_mesh_surface(v, f, n_points, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        p1000 = OFF._sample_mesh_surface(v, f, 1000, 7 + slot) - c0
        w, U = np.linalg.eigh(np.cov(p1000.T))
        if SYM[n] == 2:
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            axis, order = U[:, k], 360
    rv, rf = v, f
    if faces:
        m = trimesh.Trimesh(v, f, process=False); m.merge_vertices(); m.remove_unreferenced_vertices()
        wv, wf = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
        if weld_dec == 'cluster':
            rv, rf = cluster_decimate(wv, wf, faces)
        else:
            import fast_simplification
            rv, rf = fast_simplification.simplify(wv, wf, target_count=faces)
            rv, rf = np.asarray(rv, np.float64), np.asarray(rf, np.int64)
    return dict(mesh=(rv, rf), anchor=c, points=pts, axis=axis, order=order, name=n)


def cluster_decimate(v, f, target):
    """Vertex-clustering decimation (a different re-meshing than quadric collapse): grid cell size searched so the
    face count is near target."""
    lo, hi = 1e-4, 0.05
    for _ in range(30):
        h = np.sqrt(lo * hi)
        key = np.floor(v / h).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
        nf = inv[f]
        keep = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
        nf = np.unique(np.sort(nf[keep], 1), axis=0) if False else nf[keep]
        if len(nf) > target:
            lo = h
        else:
            hi = h
    nv = np.zeros((inv.max() + 1, 3)); cnt = np.zeros(inv.max() + 1)
    np.add.at(nv, inv, v); np.add.at(cnt, inv, 1); nv /= np.maximum(cnt, 1)[:, None]
    return nv, nf


def load_gt(ep):
    tab = pq.read_table(f'{T3D}/ep{ep}.parquet', columns=['observation.objects']).to_pandas()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    G = np.zeros((len(tab), len(names), 7))
    for t, objs in enumerate(tab['observation.objects']):
        d = {str(o['name']): np.asarray(o['pose'], float) for o in objs}
        for s, n in enumerate(names):
            x = d[n]
            G[t, s] = np.r_[x[:3], x[4:7], x[3]]          # parquet x,y,z,qw,qx,qy,qz -> x,y,z,qx,qy,qz,qw
    return names, G


def load_rollout(path):
    t = pq.read_table(path)
    md = {k.decode(): v.decode() for k, v in t.schema.metadata.items()}
    assert md['flash_chord.quaternion_order'] == 'xyzw', md
    d = t.to_pandas()
    d = d[d.environment_id == d.environment_id.min()].sort_values(['step', 'object_body_id'])
    steps = np.unique(d.step); B = d.object_body_id.nunique()
    names = [str(x) for x in d[d.step == steps[0]].object_body_name]
    ach = d[[f'achieved_position_{c}' for c in 'xyz'] + [f'achieved_quaternion_{c}' for c in 'xyzw']].to_numpy(np.float64)
    ref = d[[f'reference_position_{c}' for c in 'xyz'] + [f'reference_quaternion_{c}' for c in 'xyzw']].to_numpy(np.float64)
    rf = d.reference_frame.to_numpy().reshape(len(steps), B)
    return names, ach.reshape(len(steps), B, 7), ref.reshape(len(steps), B, 7), steps, rf, md


def npz_track(path, names):
    P = np.load(path)
    return np.stack([np.concatenate([P[n][:, :3, 3], Rot.from_matrix(P[n][:, :3, :3]).as_quat()], 1) for n in names], 1)


def register(cand, H, seed):
    return OFF._register_object_body(cand, H['mesh'], H['anchor'], seed)


def rotm(q):
    return Rot.from_quat(q.reshape(-1, 4)).as_matrix().reshape(*q.shape[:-1], 3, 3)


def to_q(Rm):
    return Rot.from_matrix(Rm.reshape(-1, 3, 3)).as_quat().reshape(*Rm.shape[:-2], 4)


def my_score(ach, gt, Hs, regs, f0=None):
    """ach, gt [T,B,7] xyzw. regs: list of (candidate_anchor, body_rotation). Returns dict."""
    T, B, _ = ach.shape
    Ra, Rr = rotm(ach[..., 3:]), rotm(gt[..., 3:])
    pa = np.empty((T, B, 3)); pr = np.empty((T, B, 3)); Ra2 = np.empty_like(Ra)
    for s in range(B):
        ca, Rb = regs[s]
        pa[:, s] = ach[:, s, :3] + Ra[:, s] @ ca
        Ra2[:, s] = Ra[:, s] @ Rb.T
        pr[:, s] = gt[:, s, :3] + Rr[:, s] @ Hs[s]['anchor']
    axes = [h['axis'] for h in Hs]
    fixed = [s for s in range(B) if not np.any(axes[s])]
    if fixed or B == 1:
        k = fixed[0] if fixed else 0
        A = Rr[0, k] @ Ra2[0, k].T
    else:
        def basis(ax, d):
            p = d - ax * (ax @ d); p /= np.linalg.norm(p)
            return np.column_stack((p, np.cross(ax, p), ax))
        A = basis(Rr[0, 0] @ axes[0], pr[0, 1] - pr[0, 0]) @ basis(Ra2[0, 0] @ axes[0], pa[0, 1] - pa[0, 0]).T
    off = pr[0, 0] - A @ pa[0, 0]
    pa = pa @ A.T + off
    Ra2 = np.einsum('ij,tbjk->tbik', A, Ra2)
    # ADD with symmetry
    add = np.zeros((T, B)); ori = np.zeros((T, B))
    for s in range(B):
        X = Hs[s]['points']; ax = axes[s]; order = Hs[s]['order']
        Xa = np.einsum('tij,nj->tni', Ra2[:, s], X) + pa[:, s, None]
        if np.any(ax):
            ang = np.arange(order) * 2 * np.pi / order
            S = Rot.from_rotvec(ang[:, None] * ax[None]).as_matrix()
        else:
            S = np.eye(3)[None]
        best = np.full(T, np.inf)
        for Sk in S:
            Xr = np.einsum('tij,nj->tni', Rr[:, s], X @ Sk.T) + pr[:, s, None]
            best = np.minimum(best, np.linalg.norm(Xa - Xr, axis=-1).mean(-1))
        add[:, s] = best
        # orientation error
        if order == 2:
            Rsym = Rot.from_rotvec(np.pi * ax).as_matrix()
            e1 = Rot.from_matrix(np.einsum('tji,tjk->tik', Rr[:, s], Ra2[:, s])).magnitude()
            e2 = Rot.from_matrix(np.einsum('tji,tjk->tik', Rr[:, s] @ Rsym, Ra2[:, s])).magnitude()
            ori[:, s] = np.minimum(e1, e2)
        elif np.any(ax):
            u, w = Ra2[:, s] @ ax, Rr[:, s] @ ax
            ori[:, s] = np.arctan2(np.linalg.norm(np.cross(u, w), axis=-1), np.clip((u * w).sum(-1), -1, 1))
        else:
            ori[:, s] = Rot.from_matrix(np.einsum('tji,tjk->tik', Rr[:, s], Ra2[:, s])).magnitude()
    th = np.arange(1, 10) * 0.01
    w = np.ones(9); w[0] = w[-1] = 0.5; w /= 8
    per_obj = [float((np.array([(add[:, s] < t).mean() for t in th]) * w).sum()) for s in range(B)]
    pos = np.linalg.norm(pa - pr, axis=-1)
    sp = float((pos.mean(0).mean() <= 0.1) and (ori.mean(0).mean() <= 0.5))
    mp = float(np.all((pos.mean(0) < 0.03) & (ori.mean(0) < np.deg2rad(30))))
    return dict(AUC=float(np.mean(per_obj)), per_obj=per_obj, SP=sp, MP=mp, add=add, A=A)


def reg_angle(Rb):
    return float(np.degrees(Rot.from_matrix(Rb).magnitude()))
