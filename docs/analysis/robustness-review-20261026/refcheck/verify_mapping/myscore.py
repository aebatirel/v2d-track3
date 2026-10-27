"""Independent re-implementation (verify_mapping) of the three per-rollout numbers the mapping check uses:
  T = registered Track 3 ADD AUC of the simulated path vs public mocap (host scan as stand-in for the hidden mesh),
  R = the same for the rollout's reference_xyzw vs mocap,
  S = pipeline/qa.py sim_vs_ref (frame-0 warp, 500 points on a 5 cm sphere, no symmetry).
Written from the kit source, NOT from calibrate.py. Own code for: parquet reading (pyarrow, no read_trajectory),
mocap quaternion reorder, frame matching by frame_index / reference_frame, body conversion, scene alignment,
symmetric point errors (closed form over the 360 / 2 discrete angles), AUC, frame-0 warp, sphere ADD.
Only the kit's ICP registration (_register_object_body), its mesh budget (budget_mesh) and its surface sampler
(_sample_mesh_surface, needed to reproduce the stand-in host points with the same seeds) are imported.
Ground truth is read here only for scoring (diagnostic, after inference).
"""
import hashlib, json, os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as Rot

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
KIT = f'{SP}/kit/v2d_submission_kit'
T3D = f'{SP}/t3'
REPO = '/home/user/v2d-track3'
sys.path.insert(0, KIT)
from v2dlb.track3_pose import _register_object_body          # noqa: E402  (official ICP registration)
from v2dlb.mesh_budget import budget_mesh                      # noqa: E402
from v2dlb.mesh_common import _sample_mesh_surface             # noqa: E402

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
THR = np.arange(1, 10) / 100.0                                  # 1..9 cm
XAX = np.linspace(0, 1, 9)


def auc_curve(err):
    """err: [F] metres -> area under accuracy curve (trapezoid on 9 equally spaced thresholds)."""
    acc = np.array([np.mean(err < t) for t in THR])
    return float(np.sum((acc[1:] + acc[:-1]) / 2 * np.diff(XAX)))


def scan_path(n):
    q = f'{T3D}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{T3D}/mesh/{n}/{n}_visual.glb'


def centroid(v, f):
    tri = v[f]
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    k = ar > 1e-12
    return (tri[k].mean(1) * ar[k, None]).sum(0) / ar[k].sum()


_GT, _HOST, _REG = {}, {}, {}


def gt(ep):
    """names (episode order), frame_index array, [F, B, 7] xyzw mocap poses."""
    if ep not in _GT:
        df = pq.read_table(f'{T3D}/ep{ep}.parquet').to_pandas().sort_values('frame_index')
        names = [str(o['name']) for o in df['observation.objects'].iloc[0]]
        P = np.zeros((len(df), len(names), 7))
        for i, objs in enumerate(df['observation.objects']):
            d = {str(o['name']): np.asarray(o['pose'], float) for o in objs}
            for b, n in enumerate(names):
                x, y, z, qw, qx, qy, qz = d[n]
                P[i, b] = [x, y, z, qx, qy, qz, qw]
        _GT[ep] = (names, df['frame_index'].to_numpy(), P)
    return _GT[ep]


def host(ep):
    if ep not in _HOST:
        names = gt(ep)[0]; H = []
        for s, n in enumerate(names):
            m = trimesh.load(scan_path(n), force='mesh')
            v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
            c = centroid(v, f)
            pts = _sample_mesh_surface(v, f, 1000, 7 + s) - c
            axis, order = np.zeros(3), 0
            if n in SYM:
                w, U = np.linalg.eigh(np.cov(pts.T))
                if SYM[n] == 'half':
                    axis, order = U[:, 0], 2
                else:
                    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
                    axis, order = U[:, k], 360
            H.append(dict(vf=(v, f), c=c, pts=pts, axis=axis, order=order))
        _HOST[ep] = H
    return _HOST[ep]


def registration(ep, lib):
    """lib: 'scan' or a meshes/library_* name. Returns [(candidate_anchor, R_body)] per slot."""
    names = gt(ep)[0]
    key = (ep, tuple(hashlib.md5(open(scan_path(n) if lib == 'scan' else f'{REPO}/meshes/{lib}/{n}.glb', 'rb').read()).hexdigest()
                     for n in names))
    if key not in _REG:
        H = host(ep); out = []
        for s, n in enumerate(names):
            cand = budget_mesh(scan_path(n) if lib == 'scan' else f'{REPO}/meshes/{lib}/{n}.glb', 4096, 4096)
            out.append(_register_object_body(cand, H[s]['vf'], H[s]['c'], 1_000_003 * ep + 101 * s))
        _REG[key] = out
    return _REG[key]


def read_rollout(path, names):
    """Own reader of the flash_chord evaluator parquet: world 0, grid [F, B, 7] (xyzw) for achieved and reference."""
    t = pq.read_table(path)
    md = {k.decode(): v.decode() for k, v in (t.schema.metadata or {}).items()}
    qo = md.get('flash_chord.quaternion_order', 'xyzw')
    df = t.to_pandas()
    df = df[df.environment_id == df.environment_id.min()]
    fcol = 'reference_frame' if 'reference_frame' in df else 'step'
    frames = np.sort(df[fcol].unique())
    bodies = df.drop_duplicates('object_body_id').sort_values('object_body_id')
    order = [str(x) for x in bodies.object_body_name]
    if order != names:
        raise ValueError(f'body order {order} != episode order {names}')
    out = {}
    for pre in ('achieved', 'reference'):
        cols = [f'{pre}_position_{a}' for a in 'xyz'] + [f'{pre}_quaternion_{a}' for a in ('xyzw' if qo == 'xyzw' else 'wxyz')]
        G = np.full((len(frames), len(names), 7), np.nan)
        fi = np.searchsorted(frames, df[fcol].to_numpy()); bi = df.object_body_id.to_numpy()
        vals = df[cols].to_numpy(float)
        if qo == 'wxyz':
            vals = vals[:, [0, 1, 2, 4, 5, 6, 3]]
        G[fi, bi] = vals
        out[pre] = G
    return frames, out['achieved'], out['reference'], md, bool(df.environment_valid.all())


def _R(q):
    return Rot.from_quat(q.reshape(-1, 4)).as_matrix().reshape(*q.shape[:-1], 3, 3)


def sym_err(Pa, Ra, Pr, Rr, pts, axis, order):
    """Mean point error [F] (m), minimised over the approved rotations about the body axis.
    Pa, Pr: [F,3]; Ra, Rr: [F,3,3]; pts [V,3] body-frame points."""
    A = np.einsum('fij,vj->fvi', Ra, pts) + Pa[:, None]
    if order == 0:
        Bm = np.einsum('fij,vj->fvi', Rr, pts) + Pr[:, None]
        return np.linalg.norm(A - Bm, axis=-1).mean(-1)
    ax = axis / np.linalg.norm(axis)
    par = np.outer(pts @ ax, ax); perp = pts - par; crs = np.cross(ax, perp)
    X = A - (np.einsum('fij,vj->fvi', Rr, par) + Pr[:, None])
    C = np.einsum('fij,vj->fvi', Rr, perp); E = np.einsum('fij,vj->fvi', Rr, crs)
    XX = np.einsum('fvi,fvi->fv', X, X) + np.einsum('vi,vi->v', perp, perp)[None]
    XC = np.einsum('fvi,fvi->fv', X, C); XE = np.einsum('fvi,fvi->fv', X, E)
    th = np.arange(order) * (2 * np.pi / order)
    best = np.full(len(Pa), np.inf)
    for i in range(0, order, 45):
        c, s = np.cos(th[i:i + 45]), np.sin(th[i:i + 45])
        d2 = XX[:, None] - 2 * c[None, :, None] * XC[:, None] - 2 * s[None, :, None] * XE[:, None]
        best = np.minimum(best, np.sqrt(np.maximum(d2, 0)).mean(-1).min(-1))
    return best


def registered(ep, lib, traj, frames, gt_shift=0, return_err=False):
    """T (traj = sim) or R (traj = reference): own glue around the kit registration."""
    names, fidx, G = gt(ep); H = host(ep); REG = registration(ep, lib); B = len(names)
    rows = np.searchsorted(fidx, frames)
    assert np.all(fidx[rows] == frames)
    rows = np.clip(rows + gt_shift, 0, len(fidx) - 1)
    ref = G[rows]
    # mocap pose -> pose of the scan anchor
    Rr = _R(ref[..., 3:]); Pr = ref[..., :3] + np.einsum('fbij,bj->fbi', Rr, np.stack([h['c'] for h in H]))
    # candidate body pose -> pose of the registered candidate anchor, rotation R_q @ R_body^T
    Ra = _R(traj[..., 3:]); Pa = traj[..., :3].copy(); Ra2 = np.empty_like(Ra)
    for s in range(B):
        ca, Rb = REG[s]
        Pa[:, s] += Ra[:, s] @ ca
        Ra2[:, s] = Ra[:, s] @ Rb.T
    # one rigid world transform at frame 0
    axes = [h['axis'] for h in H]
    fixed = [i for i in range(B) if not np.any(axes[i])]
    if fixed or B == 1:
        k = fixed[0] if fixed else 0
        Rw = Rr[0, k] @ Ra2[0, k].T
    else:
        def basis(ax, d):
            p = d - ax * (ax @ d)
            if np.linalg.norm(p) < 1e-8:
                p = np.eye(3)[np.argmin(np.abs(ax))]; p = p - ax * (ax @ p)
            p = p / np.linalg.norm(p)
            return np.column_stack((p, np.cross(ax, p), ax))
        Rw = basis(Rr[0, 0] @ axes[0], Pr[0, 1] - Pr[0, 0]) @ basis(Ra2[0, 0] @ axes[0], Pa[0, 1] - Pa[0, 0]).T
        # (kit: rotation through a quaternion of Rw; identical up to rounding)
    off = Pr[0, 0] - Rw @ Pa[0, 0]
    Pa = Pa @ Rw.T + off
    Ra2 = np.einsum('ij,fbjk->fbik', Rw, Ra2)
    err = np.stack([sym_err(Pa[:, s], Ra2[:, s], Pr[:, s], Rr[:, s], H[s]['pts'], H[s]['axis'], H[s]['order'])
                    for s in range(B)], 1)
    if return_err:
        return err
    per = {n: round(auc_curve(err[:, s]), 4) for s, n in enumerate(names)}
    return round(float(np.mean([auc_curve(err[:, s]) for s in range(B)])), 4), per


SPHERE = None


def sphere():
    global SPHERE
    if SPHERE is None:
        rng = np.random.default_rng(0); p = rng.normal(size=(500, 3))
        SPHERE = 0.05 * p / np.linalg.norm(p, axis=1, keepdims=True)
    return SPHERE


def sim_vs_ref(sim, ref, per_object=False):
    """qa.py yardstick, own implementation: warp sim so object 0 matches the reference at frame 0, then ADD on a
    5 cm sphere per object, AUC per object, mean over objects."""
    B = sim.shape[1]
    r0 = Rot.from_quat(ref[0, 0, 3:]); a0 = Rot.from_quat(sim[0, 0, 3:])
    Wr = r0 * a0.inv()
    Rw = Wr.as_matrix(); off = ref[0, 0, :3] - Rw @ sim[0, 0, :3]
    P = sim[..., :3] @ Rw.T + off
    Ra = np.einsum('ij,fbjk->fbik', Rw, _R(sim[..., 3:])); Rr = _R(ref[..., 3:])
    v = sphere(); per = {}
    vals = []
    for b in range(B):
        d = np.einsum('fij,vj->fvi', Ra[:, b] - Rr[:, b], v) + (P[:, b] - ref[:, b, :3])[:, None]
        e = np.linalg.norm(d, axis=-1).mean(-1)
        vals.append(auc_curve(e)); per[b] = round(vals[-1], 4)
    S = round(float(np.mean(vals)), 4)
    return (S, per) if per_object else S


def ref_digest(ref):
    return hashlib.sha256(np.round(np.nan_to_num(ref), 6).tobytes()).hexdigest()[:16]
