"""EVALUATION-ONLY oracle: replace perception's object poses with mocap, keep perception's camera trajectory.

Reads ground truth, so it must never feed an eval-episode submission; it refuses eval episode ids (and SPLIT=eval).
Purpose: train a policy on a near-perfect object reference to separate reference error from robot/simulation error
(oracle twins, docs/research/work/oracle-twins-20261030/). Output has the perc2 format: poses.npz (perception's
world_T_cam, cam_T_<name> = the oracle), poses_world_vo.npz (world poses per name), a link to perception's depth.
v2 (2026-10-30) fixes three defects measured on 6 public twins (CPU check, work log 30 Oct):
  --meshes DIR  mocap gives poses of the SCAN body frames, the simulator uses OUR meshes. Each object is converted with
                the kit registration that score_registered.py --meshes applies (budget_mesh 4096, seed
                1_000_003 ep + 101 slot): our-mesh pose = mocap pose @ X, X = [R, c - R ca]; the converted track scores
                1.000 vs mocap. Without --meshes the scan-frame poses are used as they are (the 20 Oct behaviour).
  --align gravity (default)  mocap world -> perception world G: the rotation maps mocap +z (gravity: the objects'
                frame-0 bottoms agree within 0.1-0.7 cm in mocap z) onto the table normal that mkref's own fit_table
                finds in perception's frame-0 depth; yaw about that normal and the translation are a least-squares fit
                of all objects' surface points at frame 0 (perception vs oracle). Measured: up vs table normal
                0.00-0.04 deg, frame-0 centres 0.3-1.3 cm from perception (where the perceived hands expect them).
  --align anchor0  the 20 Oct rule, kept to reproduce it: G = W_C[0] cam_T_anchor[0] inv(mocap_anchor[0]) (anchor
                = slot 0 or --anchor). A cup's arbitrary spin about its axis then moves the other object 16-22 cm.
  --xform FILE  (with --meshes; leak decomposition B2) take X from a tools/xstar_fit.py json instead of the kit
                registration: xstar_geom.json (X*_geom, the rigid surface fit of our mesh to the scan) or xstar_trk.json
                (X*_trk of this episode, fitted to mocap). Opt-in only, never a default. oracle.json then also scores
                the oracle track in the * convention (poses taken to scan frames by the same X; 1.000 before the snap).
oracle.json records the conversion, G, the table mkref will fit, the expected per-object snap and the oracle track's
registered AUC vs mocap (our meshes) before and after that snap.
Usage: python oracle_poses.py EP PERC_DIR OUT_DIR [--meshes DIR [--xform FILE]] [--align gravity|anchor0]
       [--anchor NAME] [--t3 /content/t3] [--kit /content/kit/v2d_submission_kit] [--calib T3/calib.json] [--depth FILE]
(v1 written 2026-10-20; v2 2026-10-30; --xform 2026-10-30)
"""
import argparse, json, os, sys, types
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot

EVAL = {1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38}
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('ep', type=int); p.add_argument('perc_dir'); p.add_argument('out_dir')
p.add_argument('--meshes', default=None, help='our mesh library (DIR/<obj>.glb), as score_registered.py --meshes')
p.add_argument('--xform', default=None, help='with --meshes: X from this xstar_fit.py json, not the kit registration')
p.add_argument('--align', choices=['gravity', 'anchor0'], default='gravity')
p.add_argument('--anchor', default=None, help='--align anchor0: the anchor object (default slot 0)')
p.add_argument('--t3', default='/content/t3'); p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
p.add_argument('--calib', default=None, help='default T3/calib.json')
p.add_argument('--depth', default=None, help='frame-0 depth: a (T,H,W) stack or one (H,W) frame; default PERC_DIR/depths_fs0.5.npy')
a = p.parse_args()
if a.xform and not a.meshes:
    sys.exit("--xform converts mocap to our meshes' frames: it needs --meshes")
ROSTER = f'{a.kit}/data/track_3_evaluation_objects.json'
if a.ep in EVAL or (os.path.exists(ROSTER) and str(a.ep) in json.load(open(ROSTER)).get('episodes', {})):
    sys.exit(f'episode {a.ep} is an eval episode: the oracle reads ground truth and is for public episodes only')
if os.environ.get('SPLIT', 'public') != 'public':
    sys.exit(f'SPLIT={os.environ["SPLIT"]}: the oracle reads ground truth and is for public episodes only')
sys.path.insert(0, a.kit); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2dlb import track3_pose as T3                                    # noqa: E402
from v2dlb.mesh_budget import budget_mesh                              # noqa: E402
from v2dlb.object_mesh import _surface_moments                         # noqa: E402
from v2dlb.mesh_common import _sample_mesh_surface                     # noqa: E402
import mkref as MK                                                      # noqa: E402  (fit_table, rectified_K)

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}            # as score_registered.py
MKA = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03,
                            support_max=0.05)                                       # mkref.py defaults
SNAP_MAX = 0.02                                                                     # mkref --snap_max


def T_of(pose):  # parquet pose is x, y, z, qw, qx, qy, qz
    T = np.eye(4); T[:3, :3] = Rot.from_quat([pose[4], pose[5], pose[6], pose[3]]).as_matrix(); T[:3, 3] = pose[:3]
    return T


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


def vf(path):
    m = trimesh.load(path, force='mesh'); return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def host_geometry(n, slot):  # the stand-in for the hidden scan geometry, exactly as score_registered.py
    v, f = vf(scan_path(n)); c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


def our_mesh_path(n):
    for q in (f'{a.meshes}/episode_{a.ep:06d}/{n}.glb', f'{a.meshes}/{n}.glb', f'{a.meshes}/{n}.obj', f'{a.meshes}/{n}.ply'):
        if os.path.exists(q):
            return q
    sys.exit(f'no mesh for {n} under {a.meshes}')


def rot_a_to_b(u, w):
    u = u / np.linalg.norm(u); w = w / np.linalg.norm(w); c = np.cross(u, w)
    if np.linalg.norm(c) < 1e-12:
        return np.eye(3)
    return Rot.from_rotvec(c / np.linalg.norm(c) * np.arccos(np.clip(u @ w, -1, 1))).as_matrix()


# ---------------- inputs
P = np.load(f'{a.perc_dir}/poses.npz')
W_C = P['world_T_cam'].astype(np.float64); N = len(W_C)
tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet', columns=['observation.objects']).to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]                # slot order
perc_names = sorted(k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_'))
if sorted(names) != perc_names:
    sys.exit(f'object names differ: episode {names}, perception {perc_names}')
if len(tab) < N:
    sys.exit(f'ground truth has {len(tab)} frames, the perception output {N}')
gt = {n: np.stack([T_of(np.array([o for o in row if o['name'] == n][0]['pose'], float))
                   for row in tab['observation.objects'].iloc[:N]]) for n in names}
camT = {n: P[f'cam_T_{n}'].astype(np.float64) for n in names}
perc_w = {n: np.einsum('tij,tjk->tik', W_C, camT[n]) for n in names}
B = len(names)

# ---------------- mesh-frame conversion (scan body frame -> our mesh frame) with the scorer's own registration
H = [host_geometry(n, s) for s, n in enumerate(names)]
cand_p = {n: (our_mesh_path(n) if a.meshes else scan_path(n)) for n in names}
REG = [T3._register_object_body(budget_mesh(cand_p[n], 4096, 4096), H[s]['mesh'], H[s]['anchor'], 1_000_003 * a.ep + 101 * s)
       for s, n in enumerate(names)]
X = {}
for s, n in enumerate(names):
    ca, R = REG[s]; M = np.eye(4)
    if a.meshes:
        M[:3, :3] = R; M[:3, 3] = H[s]['anchor'] - R @ ca
    X[n] = M
if a.xform:                                                                         # opt-in: X*_geom or X*_trk
    import frame_xform as FX                                                        # noqa: E402
    X, xkind = FX.load_xform(a.xform, a.ep, names)
REG_X = [((np.linalg.inv(X[n]) @ np.r_[H[s]['anchor'], 1.0])[:3], X[n][:3, :3].copy()) for s, n in enumerate(names)]
conv = {n: np.einsum('tij,jk->tik', gt[n], X[n]) for n in names}
vis = {n: trimesh.load(cand_p[n], force='mesh') for n in names}
surf = {n: _sample_mesh_surface(np.asarray(vis[n].vertices, np.float64), np.asarray(vis[n].faces, np.int64), 800, 3)
        for n in names}

# ---------------- mocap world -> perception world
calib = a.calib or f'{a.t3}/calib.json'
KR = MK.rectified_K(calib)
D = np.load(a.depth or f'{a.perc_dir}/depths_fs0.5.npy', mmap_mode='r')
depth0 = np.asarray(D[0] if D.ndim == 3 else D, np.float32)
info = dict(episode=a.ep, align=a.align, meshes=a.meshes or 'none (scan body frames)', objects=names, frames=N,
            note='EVALUATION-ONLY oracle built from mocap; never use for eval-episode inference')
if a.align == 'anchor0':
    anchor = a.anchor or names[0]
    G = W_C[0] @ camT[anchor][0] @ np.linalg.inv(conv[anchor][0]); info['anchor'] = anchor
else:
    n_p, d_p, frac, npts, rms = MK.fit_table(depth0, KR, W_C[0], {n: camT[n][0] for n in names}, vis, MKA)
    R1 = rot_a_to_b(np.array([0.0, 0.0, 1.0]), n_p)
    Pm = np.concatenate([surf[n] @ conv[n][0][:3, :3].T + conv[n][0][:3, 3] for n in names]) @ R1.T
    Pp = np.concatenate([surf[n] @ perc_w[n][0][:3, :3].T + perc_w[n][0][:3, 3] for n in names])
    qc, pc = Pm - Pm.mean(0), Pp - Pp.mean(0)                          # closed-form yaw about n_p (2-D Procrustes)
    psi = np.arctan2(np.sum(np.cross(qc, pc) @ n_p), np.sum(qc * pc) - np.sum((qc @ n_p) * (pc @ n_p)))
    Rz = Rot.from_rotvec(n_p * psi).as_matrix()
    G = np.eye(4); G[:3, :3] = Rz @ R1; G[:3, 3] = Pp.mean(0) - Rz @ Pm.mean(0)
    info['perceived_table'] = dict(normal=np.round(n_p, 5).tolist(), inlier_frac=round(float(frac), 3),
                                   rms_mm=round(float(rms) * 1000, 2), yaw_deg=round(float(np.degrees(psi)), 3))
tr = {n: np.einsum('ij,tjk->tik', G, conv[n]) for n in names}

# ---------------- what mkref will see: the table it fits on the oracle frame 0, the per-object snap, AUC vs mocap
n_, d_, *_ = MK.fit_table(depth0, KR, W_C[0], {n: np.linalg.inv(W_C[0]) @ tr[n][0] for n in names}, vis, MKA)
h = np.array([float((np.asarray(vis[n].vertices) @ tr[n][0][:3, :3].T + tr[n][0][:3, 3]).dot(n_).min() + d_) for n in names])
shift = np.where(np.abs(h) <= SNAP_MAX, -h, 0.0)
snapped = {n: tr[n].copy() for n in names}
for s, n in enumerate(names):
    snapped[n][:, :3, 3] += shift[s] * n_


def to7(Tm):  # 4x4 -> x y z qx qy qz qw (kit order)
    return np.r_[Tm[:3, 3], Rot.from_matrix(Tm[:3, :3]).as_quat()]


def score(track, reg=None):  # registered ADD-AUC vs mocap, score_registered.py's chain (our meshes with --meshes);
    reg = reg or REG          # reg=REG_X: the * convention (the conversion's own X instead of the kit registration)
    ach = np.stack([[to7(track[n][t]) for n in names] for t in range(N)])[:, None]
    ref = np.stack([[to7(gt[n][t]) for n in names] for t in range(N)])[:, None]
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *reg[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [x['axis'] for x in H]; orders = [x['order'] for x in H]; pts = [x['points'] for x in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    per = {n: round(float(T3._registered_pose_metric('add_auc', ach[:, :, s:s + 1], ref[:, :, s:s + 1], pts[s:s + 1],
                                                     axes[s:s + 1], orders[s:s + 1])), 4) for s, n in enumerate(names)}
    return dict(AUC=round(float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders)), 4), per_obj_AUC=per)


up = G[:3, :3] @ np.array([0.0, 0.0, 1.0])
info.update(
    G=np.round(G, 6).tolist(),
    mesh_frame_offset={n: dict(rot_deg=round(float(np.degrees(Rot.from_matrix(X[n][:3, :3]).magnitude())), 2),
                               off_cm=round(float(np.linalg.norm(X[n][:3, 3]) * 100), 2)) for n in names},
    mocap_f0_bottom_z_cm={n: round(float((H[s]['mesh'][0] @ gt[n][0][:3, :3].T + gt[n][0][:3, 3])[:, 2].min() * 100), 2)
                          for s, n in enumerate(names)},
    up_vs_table_normal_deg=round(float(np.degrees(np.arccos(np.clip(up @ n_, -1, 1)))), 3),
    f0_bottom_above_table_cm={n: round(float(x * 100), 2) for n, x in zip(names, h)},
    expected_snap_cm={n: round(float(x * 100), 2) for n, x in zip(names, shift)},
    support_check_ok=bool(-MKA.support_tol <= h.min() <= MKA.support_max),
    f0_centre_vs_perception_cm={n: round(float(np.linalg.norm(tr[n][0][:3, 3] - perc_w[n][0][:3, 3]) * 100), 2) for n in names},
    perception_vs_mocap=score(perc_w), raw_vs_mocap=score(tr), after_snap_vs_mocap=score(snapped))
if a.xform:
    info.update(xform=dict(file=os.path.abspath(a.xform), kind=xkind, note='X from tools/xstar_fit.py, not the kit '
                           'registration; the *_star scores take the tracks to scan frames by the same X'),
                perception_vs_mocap_star=score(perc_w, REG_X), raw_vs_mocap_star=score(tr, REG_X),
                after_snap_vs_mocap_star=score(snapped, REG_X))

# ---------------- outputs (perc2 layout; dtypes as perception's)
os.makedirs(a.out_dir, exist_ok=True)
out = {'world_T_cam': P['world_T_cam']}
for n in names:
    out[f'cam_T_{n}'] = np.einsum('tij,tjk->tik', np.linalg.inv(W_C), tr[n]).astype(P[f'cam_T_{n}'].dtype)
np.savez(f'{a.out_dir}/poses.npz', **out)
np.savez(f'{a.out_dir}/poses_world_vo.npz', **{n: tr[n] for n in names})
for f in ('depths_fs0.5.npy',):                                              # hands/mkref read depth next to poses
    src = os.path.realpath(f'{a.perc_dir}/{f}')
    if os.path.exists(src) and not os.path.lexists(f'{a.out_dir}/{f}'):
        os.symlink(src, f'{a.out_dir}/{f}')
json.dump(info, open(f'{a.out_dir}/oracle.json', 'w'), indent=1)
print(json.dumps(info, indent=1))
if not info['support_check_ok'] or max(info['f0_centre_vs_perception_cm'].values()) > 3:
    print('WARNING: the oracle start is far from perception or off the table (see oracle.json)', file=sys.stderr)
