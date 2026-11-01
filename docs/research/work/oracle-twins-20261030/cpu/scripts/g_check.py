"""Oracle design check (CPU, PUBLIC episodes only, diagnostic; reads mocap).

Question: how should the mocap object motion be placed on perc2's camera trajectory so that, after mkref's table
frame and per-object snap, the oracle reference still equals mocap (registered AUC ~1) and sits consistently on the
perceived table (gravity)? Options for the world alignment G (mocap world -> perception world):
  raw0   : pipeline/oracle_poses.py as written (scan-frame mocap poses used as our-mesh poses, anchor slot 0 at f0)
  conv0  : mocap converted to OUR mesh body frames with the kit registration (as score_registered.py --meshes), anchor slot 0 f0
  convK  : converted, G = Kabsch fit of all objects' surface points at frame 0 (perception vs oracle)
  convG  : converted, G rotation = (mocap z -> perceived table normal) then yaw + translation by Kabsch at frame 0
Per option: angle between mocap up (G e_z) and mkref's fitted table normal, frame-0 object bottoms above the table
(mkref's per-object snap moves |h| <= 2 cm), and registered ADD-AUC vs mocap (our meshes) before / after the snap.
Usage: python -I g_check.py KIT REPO LIB SCANS PARQUET_DIR CALIB IN_DIR EP [EP ...]
"""
import sys, os, json, types
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

KIT, REPO, LIB, SCANS, PQD, CALIB, IND = sys.argv[1:8]
EPS = [int(x) for x in sys.argv[8:]]
sys.path.insert(0, KIT); sys.path.insert(0, f'{REPO}/pipeline')
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
import mkref as MK

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
A = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05)
KR = MK.rectified_K(CALIB)


def scan_path(n):
    q = f'{SCANS}/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{SCANS}/{n}/{n}_visual.glb'


def vf(p):
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)


def host(n, s):
    v, f = vf(scan_path(n)); c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + s) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


def T_of7(p):  # parquet pose x y z qw qx qy qz
    T = np.eye(4); T[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); T[:3, 3] = p[:3]; return T


def to7(T):  # 4x4 -> x y z qx qy qz qw (kit order)
    return np.r_[T[:3, 3], Rot.from_matrix(T[:3, :3]).as_quat()]


def kabsch(P, Q):  # R, t minimising |R P + t - Q|
    cp, cq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - cp).T @ (Q - cq))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ D @ U.T
    return R, cq - R @ cp


def rot_a_to_b(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = a @ b
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3)
    return Rot.from_rotvec(v / np.linalg.norm(v) * np.arccos(np.clip(c, -1, 1))).as_matrix()


report = {}
for ep in EPS:
    d = f'{IND}/ep{ep}'
    P = np.load(f'{d}/poses.npz'); W = P['world_T_cam'].astype(float); N = len(W)
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    tab = pq.read_table(f'{PQD}/episode_{ep:06d}.parquet', columns=['observation.objects']).to_pandas()
    pq_names = [o['name'] for o in tab['observation.objects'].iloc[0]]
    assert pq_names == names, (pq_names, names)
    gt = {n: np.stack([T_of7(np.array([o for o in row if o['name'] == n][0]['pose'], float))
                       for row in tab['observation.objects'].iloc[:N]]) for n in names}
    B = len(names); H = [host(n, s) for s, n in enumerate(names)]
    cand = [budget_mesh(f'{LIB}/{n}.glb', 4096, 4096) for n in names]
    REG = [T3._register_object_body(cand[s], H[s]['mesh'], H[s]['anchor'], 1_000_003 * ep + 101 * s) for s in range(B)]
    X = []
    for s in range(B):                      # our-mesh pose = scan pose @ X   (R_o = R_g R, t_o = t_g + R_g (c - R ca))
        ca, R = REG[s]; M = np.eye(4); M[:3, :3] = R; M[:3, 3] = H[s]['anchor'] - R @ ca; X.append(M)
    vis = {n: trimesh.load(f'{LIB}/{n}.glb', force='mesh') for n in names}
    pts_our = {n: np.asarray(vis[n].sample(800, seed=3) if hasattr(vis[n], 'sample') else vis[n].vertices) for n in names}
    perc_w = {n: np.einsum('tij,tjk->tik', W, P[f'cam_T_{n}'].astype(float)) for n in names}
    depth0 = np.load(f'{d}/depth0.npy')

    def score(tr):  # tr: {name: (T,4,4) world poses of OUR mesh frames} -> registered AUC vs mocap (our meshes)
        ach = np.stack([[to7(tr[n][t]) for n in names] for t in range(N)])[:, None]
        ref = np.stack([[np.r_[gt[n][t][:3, 3], Rot.from_matrix(gt[n][t][:3, :3]).as_quat()] for n in names] for t in range(N)])[:, None]
        for s in range(B):
            ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
            ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
        axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
        ach = T3._align_registered_scene(ach, ref, axes)
        return round(float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders)), 4), \
            {n: round(float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1], pts[s:s + 1],
                                                       axes[s:s + 1], orders[s:s + 1])), 4) for s, n in enumerate(names)}

    out = dict(objects=names, frames=N, mesh_frame_offset={n: dict(rot_deg=round(float(np.degrees(Rot.from_matrix(REG[s][1]).magnitude())), 2),
                                                                     off_cm=round(float(np.linalg.norm(X[s][:3, 3]) * 100), 2))
                                                             for s, n in enumerate(names)})
    out['perception_AUC'] = score(perc_w)
    # perceived table (mkref fit on the PERCEIVED frame-0 poses): the plane is depth-driven; reused as the gravity target
    n_p, d_p, frac, npts, rms = MK.fit_table(depth0, KR, W[0], {n: P[f'cam_T_{n}'][0].astype(float) for n in names}, vis, A)
    # mocap check: is mocap z the table normal? bottoms of each object at f0 in mocap world (scan meshes)
    out['mocap_f0_bottom_z_cm'] = {n: round(float(((H[s]['mesh'][0] @ gt[n][0][:3, :3].T + gt[n][0][:3, 3])[:, 2]).min() * 100), 2)
                                   for s, n in enumerate(names)}
    conv = {n: np.einsum('tij,jk->tik', gt[n], X[s]) for s, n in enumerate(names)}
    G = {}
    a0 = names[0]
    G['raw0'] = (perc_w[a0][0] @ np.linalg.inv(gt[a0][0]), gt)
    G['conv0'] = (perc_w[a0][0] @ np.linalg.inv(conv[a0][0]), conv)
    Pm = np.concatenate([(conv[n][0][:3, :3] @ pts_our[n].T).T + conv[n][0][:3, 3] for n in names])
    Pp = np.concatenate([(perc_w[n][0][:3, :3] @ pts_our[n].T).T + perc_w[n][0][:3, 3] for n in names])
    R, t = kabsch(Pm, Pp); M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t; G['convK'] = (M, conv)
    R1 = rot_a_to_b(np.array([0, 0, 1.0]), n_p)       # mocap up -> perceived table normal
    Q = Pm @ R1.T
    best = None                                        # yaw about n_p, then translation, least squares
    for psi in np.radians(np.arange(-180, 180, 0.1)):
        Rz = Rot.from_rotvec(n_p * psi).as_matrix(); Y = Q @ Rz.T; tt = (Pp - Y).mean(0); e = np.mean(np.sum((Y + tt - Pp) ** 2, 1))
        if best is None or e < best[0]:
            best = (e, Rz @ R1, tt)
    M = np.eye(4); M[:3, :3] = best[1]; M[:3, 3] = best[2]; G['convG'] = (M, conv)
    for k, (Gm, src) in G.items():
        tr = {n: np.einsum('ij,tjk->tik', Gm, src[n]) for n in names}
        camT0 = {n: np.linalg.inv(W[0]) @ tr[n][0] for n in names}
        n_, d_, *_ = MK.fit_table(depth0, KR, W[0], camT0, vis, A)
        up = Gm[:3, :3] @ np.array([0, 0, 1.0])
        h = np.array([float(((np.asarray(vis[n].vertices) @ tr[n][0][:3, :3].T + tr[n][0][:3, 3]) @ n_).min() + d_) for n in names])
        shift = np.where(np.abs(h) <= 0.02, -h, 0.0)
        snapped = {n: tr[n].copy() for n in names}
        for s, n in enumerate(names):
            snapped[n][:, :3, 3] += shift[s] * n_
        f0err = {n: round(float(np.linalg.norm(tr[n][0][:3, 3] - perc_w[n][0][:3, 3]) * 100), 2) for n in names}
        out[k] = dict(up_vs_table_normal_deg=round(float(np.degrees(np.arccos(np.clip(up @ n_, -1, 1)))), 2),
                      f0_bottom_above_table_cm={n: round(float(x * 100), 2) for n, x in zip(names, h)},
                      snap_shift_cm={n: round(float(x * 100), 2) for n, x in zip(names, shift)},
                      support_check_ok=bool(-0.03 <= h.min() <= 0.05),
                      f0_centre_vs_perception_cm=f0err,
                      AUC_before_snap=score(tr), AUC_after_snap=score(snapped))
    report[ep] = out
    print(json.dumps({ep: out}), flush=True)
pass
