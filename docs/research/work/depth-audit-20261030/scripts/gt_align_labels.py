"""GROUND-TRUTH SIDE (label-robustness check of the depth-audit calibration; run only after every audit exists).
Copied unchanged in its computation from verifier 1's vgeo/glob_label.py (30 Oct 2026). Same registration as
pipeline/score_registered.py (kit functions, same seeds), then the per-frame symmetric ADD under three scene alignments:
  adds_kit   : the kit's frame-0 scene alignment (T3._align_registered_scene; must equal perception_adds_cm),
  adds_glob  : one global SE(3) fitted over ALL frames and objects (Kabsch on registered centres plus surface points of
               objects without a symmetry axis); it also absorbs any constant per-episode offset, so it is a lenient label,
  adds_f0all : the same Kabsch fit on frame 0 only, over all objects (not just the kit's anchor object).
align_rot_diff_deg: rotation between the kit's alignment and the global fit.
Reads the public parquet's observation.objects poses (mocap): never import or call from inference code.
Usage: python -I gt_align_labels.py EP POSES_WORLD_VO T3 KIT MESHES OUT.npz   (OUT under a .../gt/... directory)"""
import sys, os, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
ep, src, t3, kit, meshes, out = int(sys.argv[1]), *sys.argv[2:7]
sys.path.insert(0, kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
def scan_path(n):
    q = f'{t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{t3}/mesh/{n}/{n}_visual.glb'
def load_vf(p):
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
def host_geometry(n, slot):
    v, f = load_vf(scan_path(n)); c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)
tab = pq.read_table(f'{t3}/ep{ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]; B = len(names)
def gt_xyzw(o):
    q = np.array(o['pose'], float); return np.r_[q[:3], q[4:7], q[3]]
P = np.load(src); T = len(P[names[0]])
ach = np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()] for n in names] for i in range(T)])
gt = np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]) for n in names] for fr in range(T)])
H = [host_geometry(n, s) for s, n in enumerate(names)]
REG = []
for s, n in enumerate(names):
    cand = budget_mesh(f'{meshes}/{n}.glb', 4096, 4096)
    REG.append(T3._register_object_body(cand, H[s]['mesh'], H[s]['anchor'], 1_000_003 * ep + 101 * s))
a = ach[:, None].copy(); r = gt[:, None].copy()
for s in range(B):
    a[:, :, s] = T3._convert_object_body(a[:, :, s], *REG[s])
    r[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(r[:, :, s, 3:]), H[s]['anchor'])
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
def adds(x):
    return np.stack([T3._symmetry_point_errors(x[:, :, s], r[:, :, s], pts[s], axes[s], orders[s])[:, 0] for s in range(B)], 1) * 100
kitA = T3._align_registered_scene(a, r, axes)
adds_kit = adds(kitA)
# global Kabsch: correspondences = registered centres of all objects, plus 50 surface points of non-symmetric objects
def fit(fr):
    Xa, Xr = [], []
    for s in range(B):
        Ra, Rr = T3._rotation_matrix(a[fr, 0, s, 3:]), T3._rotation_matrix(r[fr, 0, s, 3:])
        Xa.append(a[fr, 0, s, :3]); Xr.append(r[fr, 0, s, :3])
        if not np.any(axes[s]):
            q = pts[s][::20]
            Xa.append((np.einsum('tij,vj->tvi', Ra, q) + a[fr, 0, s, None, :3]).reshape(-1, 3))
            Xr.append((np.einsum('tij,vj->tvi', Rr, q) + r[fr, 0, s, None, :3]).reshape(-1, 3))
    Xa, Xr = np.concatenate(Xa), np.concatenate(Xr)
    ok = np.isfinite(Xa).all(1) & np.isfinite(Xr).all(1); Xa, Xr = Xa[ok], Xr[ok]
    ca, cr = Xa.mean(0), Xr.mean(0); U, S_, Vt = np.linalg.svd((Xa - ca).T @ (Xr - cr))
    dS = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); Rg = Vt.T @ dS @ U.T; tg = cr - Rg @ ca
    qg = Rot.from_matrix(Rg).as_quat()
    g = a.copy(); g[..., :3] = a[..., :3] @ Rg.T + tg; g[..., 3:] = T3._quaternion_multiply(qg, a[..., 3:])
    return Rg, g
Rg, g = fit(slice(None)); adds_glob = adds(g)
_, g0 = fit(slice(0, 1)); adds_f0all = adds(g0)
# difference between the two alignments (the anchor-object frame-0 error the kit pushes into the scene)
fx = [i for i, x in enumerate(axes) if not np.any(x)]; an = fx[0] if fx else 0
Rk = T3._rotation_matrix(kitA[0, 0, an, 3:]) @ T3._rotation_matrix(a[0, 0, an, 3:]).T
dR = float(np.degrees(Rot.from_matrix(Rg @ Rk.T).magnitude()))
np.savez(out, names=np.array(names), frames=np.arange(T), adds_kit=adds_kit, adds_glob=adds_glob, adds_f0all=adds_f0all, align_rot_diff_deg=dR)
print(ep, names, 'kit med', np.median(adds_kit, 0).round(2), 'glob med', np.median(adds_glob, 0).round(2), 'rotdiff', round(float(dR), 2))
