"""RPE / MPPE / AUC decomposition helpers (31 Oct 2026). PUBLIC EPISODES ONLY. Reads ground truth (public mocap, the
`pose` field of observation.objects, and the public scans): an ORACLE DIAGNOSTIC library, used only after inference,
never an input of any eval-side fix.

Scoring is the kit's registered Track 3 chain, called from the kit's own metric file (metric_code/track_3/RPE.py, which
is byte-identical to MPPE.py and AUC.py apart from the _METRIC constant):
  1. _register_object_body: our submitted mesh (library_v3, budget_mesh 4096/4096) registered to the host scan
     (stand-in: the public scan; anchor = its surface centroid; 1000 surface samples, seed 7+slot; cups: distinct
     principal axis, order 360; lid: thinnest axis, order 2) with seed 1_000_003*ep + 101*slot.
  2. _convert_object_body: our body-frame poses -> poses of the host anchor in the scan body frame.
  3. reference: mocap pose + R*anchor.
  4. _align_registered_scene: one rigid transform per world, from frame 0 (translation from slot 0, rotation from the
     first object without a symmetry axis; if all have axes, slot 0's axis and the direction to slot 1).
  5. _registered_pose_metric('add_auc' | 'mppe_cm' | 'rpe_cm').
Same stand-in as pipeline/score_registered.py and tools/xstar_fit.py (leak-decomp phase 1).
"""
import importlib.util, os, sys
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
EVAL = {1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38}
M = None          # the kit metric module
BUDGET = None     # v2dlb.mesh_budget.budget_mesh (the packer's decimation)


def load_kit(kitdir):
    global M, BUDGET
    spec = importlib.util.spec_from_file_location('kit_track3_rpe', f'{kitdir}/metric_code/track_3/RPE.py')
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    sys.path.insert(0, kitdir)
    from v2dlb.mesh_budget import budget_mesh
    BUDGET = budget_mesh
    return M


def guard(ep):
    if ep in EVAL or ep not in PUBLIC:
        sys.exit(f'episode {ep}: this oracle diagnostic runs on public episodes only')


def scan_path(t3, n):
    q = f'{t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{t3}/mesh/{n}/{n}_visual.glb'


def load_vf(path):
    m = trimesh.load(path, force='mesh'); return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def host_geometry(t3, n, slot, n_points=1000):
    v, f = load_vf(scan_path(t3, n)); c, r = M._surface_moments(v, f)
    pts = M._sample_mesh_surface(v, f, n_points, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(name=n, mesh=(v, f), anchor=c, radius=r, points=pts, axis=axis, order=order)


def kit_reg(lib, n, H, ep, slot):
    return M._register_object_body(BUDGET(f'{lib}/{n}.glb', 4096, 4096), H['mesh'], H['anchor'], 1_000_003 * ep + 101 * slot)


def reg_of_X(X, anchor):  # registration (candidate anchor, rotation) that applies inv(X) (X = scan_T_lib), as xstar_fit
    return (np.linalg.inv(X) @ np.r_[anchor, 1.0])[:3], X[:3, :3].copy()


# ---------------- poses
def to4(x7):  # (..., 7) x y z qx qy qz qw -> (..., 4, 4)
    out = np.zeros(x7.shape[:-1] + (4, 4)); out[..., 3, 3] = 1
    out[..., :3, :3] = Rot.from_quat(x7[..., 3:].reshape(-1, 4)).as_matrix().reshape(x7.shape[:-1] + (3, 3))
    out[..., :3, 3] = x7[..., :3]; return out


def to7(T):
    q = Rot.from_matrix(T[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(T.shape[:-2] + (4,))
    return np.concatenate([T[..., :3, 3], q], -1)


def names_of(t3, ep):
    row = pq.read_table(f'{t3}/ep{ep}.parquet', columns=['observation.objects']).column('observation.objects')[0].as_py()
    return [str(o['name']) for o in row]


def mocap7(t3, ep, names, N):
    """GROUND TRUTH: (N, B, 7) xyzw scan body-frame poses (parquet stores x y z qw qx qy qz)."""
    tab = pq.read_table(f'{t3}/ep{ep}.parquet', columns=['observation.objects']).column('observation.objects').to_pylist()
    if len(tab) < N:
        sys.exit(f'ep{ep}: ground truth has {len(tab)} frames, the track {N}')
    out = np.zeros((N, len(names), 7))
    for t, row in enumerate(tab[:N]):
        d = {str(o['name']): np.asarray(o['pose'], float) for o in row}
        for s, n in enumerate(names):
            q = d[n]; out[t, s] = np.r_[q[:3], q[4:7], q[3]]
    return out


def track7(npz, names):
    V = np.load(npz)
    if sorted(V.files) != sorted(names):
        sys.exit(f'{npz}: names {V.files} != slots {names}')
    return np.stack([to7(V[n].astype(np.float64)) for n in names], 1)          # (T, B, 7)


# ---------------- kit chain
def convert(ach7, REG):
    """our lib-frame poses (T,B,7) -> host-anchor poses in OUR world (T,B,7) (kit _convert_object_body)."""
    out = ach7.copy()
    for s, (ca, R) in enumerate(REG):
        out[:, s] = M._convert_object_body(ach7[:, s], ca, R)
    return out


def ref_anchor(gt7, H):
    out = gt7.copy()
    for s, h in enumerate(H):
        out[:, s, :3] += np.einsum('...ij,j->...i', M._rotation_matrix(gt7[:, s, 3:]), h['anchor'])
    return out


def align(C7, R7, H):
    """kit frame-0 scene alignment of converted poses C7 (T,B,7) onto reference anchors R7 -> (T,B,7)."""
    a = M._align_registered_scene(C7[:, None].copy(), R7[:, None].copy(), [h['axis'] for h in H])
    return a[:, 0]


def metrics(A7, R7, H, per_frame=False):
    """kit metrics on aligned achieved A7 vs reference R7 (T,B,7)."""
    a, r = A7[:, None], R7[:, None]
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    # the kit's add_auc is _add_auc(stack of _symmetry_point_errors per body) = mean of the per-body AUCs, and its
    # mppe_cm is the mean of the per-body keypoint errors: computed once per body here (same functions, same result)
    adds = [M._symmetry_point_errors(a[:, :, s], r[:, :, s], pts[s], axes[s], orders[s]) for s in range(len(H))]
    kp = M._MPPE_KEYPOINT_DIRECTIONS * M._MPPE_KEYPOINT_RADIUS_M
    mp = [M._symmetry_point_errors(a[:, :, s], r[:, :, s], kp, axes[s], orders[s]) for s in range(len(H))]
    out = dict(AUC=float(M._add_auc(np.stack(adds, axis=-1))), MPPE=float(np.mean(mp) * 100),
               RPE=float(M._registered_pose_metric('rpe_cm', a, r, pts, axes, orders)))
    out['obj_AUC'] = [float(M._add_auc(x[..., None])) for x in adds]
    out['obj_MPPE'] = [float(x.mean() * 100) for x in mp]
    if per_frame:
        out['pf_mppe_cm'] = np.stack([x[:, 0] for x in mp], 1) * 100            # (T,B)
        out['pf_adds_cm'] = np.stack([x[:, 0] for x in adds], 1) * 100
        out['pf_rpe_cm'] = rpe_per_frame(A7, R7, H)
    return out


def rpe_per_frame(A7, R7, H):
    """per-frame error of the kit's _symmetry_relative_position_cm, pair (0,1) only (all public/eval eps have <= 2)."""
    if len(H) < 2:
        return np.zeros(len(A7))
    ra, rr = M._rotation_matrix(A7[:, 0, 3:]), M._rotation_matrix(R7[:, 0, 3:])
    la = np.einsum('tji,tj->ti', ra, A7[:, 1, :3] - A7[:, 0, :3]); lr = np.einsum('tji,tj->ti', rr, R7[:, 1, :3] - R7[:, 0, :3])
    ax, o = H[0]['axis'], H[0]['order']
    if o == 2:
        alt = lr @ M._axial_rotations(ax, 2)[1]
        e = np.minimum(np.linalg.norm(la - lr, axis=-1), np.linalg.norm(la - alt, axis=-1))
    elif np.any(ax):
        ha, hr = la @ ax, lr @ ax
        pa = np.linalg.norm(la - ha[:, None] * ax, axis=-1); pr = np.linalg.norm(lr - hr[:, None] * ax, axis=-1)
        e = np.hypot(ha - hr, pa - pr)
    else:
        e = np.linalg.norm(la - lr, axis=-1)
    return e * 100


def score(C7, R7, H, per_frame=False):
    """C7: converted poses in our world; returns metrics after the kit's own alignment."""
    return metrics(align(C7, R7, H), R7, H, per_frame)


# ---------------- oracle world fit (diagnostic): W* maps our world onto the mocap world
def keypoints(h):
    if h['order']:                    # cups and lid: points on the symmetry axis (spin / flip unobservable or ambiguous)
        r = float(np.sqrt((h['points'] ** 2).sum(1).mean()))
        return np.outer([-1.0, 0.0, 1.0], h['axis']) * r
    return h['points'][::20]


def world_fit(C7, R7, H, trim=0.8, iters=15):
    """GROUND-TRUTH FIT: robust rigid W* (4x4) minimising sum_s,t |W C_s(t) k - R_s(t) k| over object keypoints."""
    src, dst = [], []
    for s, h in enumerate(H):
        k = keypoints(h)
        Ca, Ra = to4(C7[:, s]), to4(R7[:, s])
        src.append(np.einsum('tij,kj->tki', Ca[:, :3, :3], k) + Ca[:, None, :3, 3])
        dst.append(np.einsum('tij,kj->tki', Ra[:, :3, :3], k) + Ra[:, None, :3, 3])
    src = np.concatenate([x.reshape(-1, 3) for x in src]); dst = np.concatenate([x.reshape(-1, 3) for x in dst])
    keep = np.arange(len(src))
    for _ in range(iters):
        R, t = M._kabsch(src[keep], dst[keep])
        d = np.linalg.norm(src @ R.T + t - dst, axis=1)
        keep = np.argpartition(d, int(len(d) * trim) - 1)[:int(len(d) * trim)]
    W = np.eye(4); W[:3, :3] = R; W[:3, 3] = t
    return W


def anchor_slots(H):
    """(translation slot, rotation slot or None) used by the kit's _align_registered_scene."""
    fixed = [i for i, h in enumerate(H) if not np.any(h['axis'])]
    if fixed or len(H) == 1:
        return 0, (fixed[0] if fixed else 0)
    return 0, None


def retarget_start(C4, new0, rot_only=False):
    """keep our world-frame motion deltas C(t) C(0)^-1, replace the start pose by new0 (4x4)."""
    if rot_only:
        out = C4.copy()
        out[:, :3, :3] = np.einsum('tij,jk->tik', C4[:, :3, :3] @ C4[0, :3, :3].T, new0[:3, :3])
        return out
    D = C4 @ np.linalg.inv(C4[0])
    return D @ new0


def rest_mask(R7, win=5, pos_cm=0.5, rot_deg=2.0):
    """GROUND TRUTH: (T,B) True where the mocap object is still (over +-win frames: < pos_cm and < rot_deg)."""
    T, B = R7.shape[:2]
    Rm = to4(R7)
    still = np.zeros((T, B), bool)
    for s in range(B):
        for t in range(T):
            a, b = max(0, t - win), min(T - 1, t + win)
            seg = Rm[a:b + 1, s]
            dp = np.linalg.norm(seg[:, :3, 3] - Rm[t, s, :3, 3], axis=1).max() * 100
            dr = np.degrees(Rot.from_matrix(np.einsum('tij,kj->tik', seg[:, :3, :3], Rm[t, s, :3, :3])).magnitude()).max()
            still[t, s] = dp < pos_cm and dr < rot_deg
    return still


def motion_span(R7):
    """GROUND TRUTH: per object max travel (cm) and max rotation (deg) from frame 0."""
    Rm = to4(R7); out = []
    for s in range(R7.shape[1]):
        tr = float(np.linalg.norm(Rm[:, s, :3, 3] - Rm[0, s, :3, 3], axis=1).max() * 100)
        rt = float(np.degrees(Rot.from_matrix(np.einsum('tij,kj->tik', Rm[:, s, :3, :3], Rm[0, s, :3, :3])).magnitude()).max())
        out.append((tr, rt))
    return out
