"""Frame-level attribution of a registered-AUC difference between two object paths of one public episode
(refcheck/chain, 26 Oct 2026; DIAGNOSTIC: reads public mocap, after inference).

Reproduces pipeline/score_registered.py exactly (same kit functions, same stand-in host geometry, same registration
seeds, same frame-0 scene alignment) for two sources A and B (poses_world_vo.npz-style files: perception, or a reference
converted by ref2npz.py), then, per object and frame, computes
  s_t   = the frame's share of the ADD AUC: trapezoid over the kit thresholds (1..9 cm) of [ADD_t < thr] (symmetry-aware
          ADD exactly as the kit), so per-object AUC = mean_t s_t and AUC(B) - AUC(A) = mean_t (s_t(B) - s_t(A));
  ADD, anchor position error, symmetry-aware orientation error (kit definitions), vertical / horizontal parts of the
          anchor position error (mocap z is up);
  hybrids: B's anchor position with A's orientation (B_pos) and A's position with B's orientation (B_rot): which part of
          the change (translation or rotation) moves the AUC;
  the direct change B - A in the aligned frame (anchor position cm, vertical cm, orientation deg).
Segments: consecutive frames where s_t(B) - s_t(A) < -0.05 (or > 0.05). The frame-0 alignment difference (how the
anchor object's frame-0 pose differs between A and B) moves every frame of every object; it shows up as a frame-0
change of the non-anchor objects (the anchor object itself is aligned onto mocap at frame 0 in both).
Usage: python -I diag.py EP A.npz B.npz [--meshes DIR] [--meshes_b DIR|scan] --t3 T3 --kit KIT --out OUT.json [--pf OUT.npz]
  (--meshes_b scores B with other candidate meshes than A: A = B = the same path gives the registration cost.)
"""
import argparse, json, os, sys
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser()
p.add_argument('ep', type=int); p.add_argument('A'); p.add_argument('B')
p.add_argument('--meshes', default=None, help='candidate meshes for both A and B (default: the public scans)')
p.add_argument('--meshes_b', default=None, help="candidate meshes for B only ('scan' = public scans); default = --meshes")
p.add_argument('--t3', required=True); p.add_argument('--kit', required=True)
p.add_argument('--out', required=True); p.add_argument('--pf', default=None); p.add_argument('--n_points', type=int, default=1000)
a = p.parse_args()
sys.path.insert(0, a.kit)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
from v2dlb.object_pose import _ADD_THRESHOLDS_M

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


def load_vf(path):
    m = trimesh.load(path, force='mesh')
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def host_geometry(n, slot):                      # identical to score_registered.py
    v, f = load_vf(scan_path(n))
    c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, a.n_points, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


def candidate_mesh(n, meshes):                   # identical to score_registered.py
    if meshes in (None, 'scan'):
        return budget_mesh(scan_path(n), 4096, 4096)
    for q in (f'{meshes}/episode_{a.ep:06d}/{n}.glb', f'{meshes}/{n}.glb'):
        if os.path.exists(q):
            return budget_mesh(q, 4096, 4096)
    raise SystemExit(f'no candidate mesh for {n} under {meshes}')


tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
B = len(names)


def load(src):
    P = np.load(src); T = len(P[names[0]])
    return np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()] for n in names] for i in range(T)])


XA, XB = load(a.A), load(a.B)
T = min(len(XA), len(XB)); XA, XB = XA[:T], XB[:T]
gt = np.stack([[(lambda q: np.r_[q[:3], q[4:7], q[3]])(np.array([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]['pose'], float))
                for n in names] for fr in range(T)])
H = [host_geometry(n, s) for s, n in enumerate(names)]
MB = a.meshes if a.meshes_b is None else a.meshes_b
REG_A = [T3._register_object_body(candidate_mesh(n, a.meshes), H[s]['mesh'], H[s]['anchor'], 1_000_003 * a.ep + 101 * s) for s, n in enumerate(names)]
REG_B = REG_A if MB == a.meshes else [T3._register_object_body(candidate_mesh(n, MB), H[s]['mesh'], H[s]['anchor'], 1_000_003 * a.ep + 101 * s) for s, n in enumerate(names)]
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
ref = gt[:, None].copy()
for s in range(B):
    ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])


def aligned(X, REG):
    ach = X[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
    return T3._align_registered_scene(ach, ref, axes)


AA, AB = aligned(XA, REG_A), aligned(XB, REG_B)
thr = _ADD_THRESHOLDS_M; xs = np.linspace(0, 1, thr.size)


def per_frame(X):
    add = np.stack([T3._symmetry_point_errors(X[:, :, s], ref[:, :, s], pts[s], axes[s], orders[s]) for s in range(B)], -1)[:, 0]
    s_t = np.trapezoid((add[..., None] < thr).astype(float), x=xs, axis=-1)
    pos = X[:, 0, :, :3] - ref[:, 0, :, :3]
    rot = np.degrees(T3._symmetry_orientation_errors(X, ref, axes, orders))[:, 0]
    return dict(add_cm=add * 100, s=s_t, pos_cm=np.linalg.norm(pos, axis=-1) * 100, dz_cm=pos[..., 2] * 100,
                dxy_cm=np.linalg.norm(pos[..., :2], axis=-1) * 100, rot_deg=rot)


FA, FB = per_frame(AA), per_frame(AB)
HP = AA.copy(); HP[..., :3] = AB[..., :3]          # B's position, A's orientation
HR = AA.copy(); HR[..., 3:] = AB[..., 3:]          # A's position, B's orientation
FP, FR = per_frame(HP), per_frame(HR)
dpos = AB[:, 0, :, :3] - AA[:, 0, :, :3]
drot = np.degrees(np.stack([(Rot.from_quat(AB[:, 0, s, 3:]) * Rot.from_quat(AA[:, 0, s, 3:]).inv()).magnitude() for s in range(B)], -1))


def segments(d, lo=-0.05, gap=5):
    """Runs of frames with d below LO (or above, LO > 0), merged across gaps of up to GAP frames."""
    idx = np.nonzero(d < lo if lo < 0 else d > lo)[0]; out = []
    for t in idx:
        if out and t - out[-1][1] <= gap:
            out[-1][1] = int(t)
        else:
            out.append([int(t), int(t)])
    return out


fixed = [i for i, ax in enumerate(axes) if not np.any(ax)]
reg_info = lambda REG: {n: dict(rot_deg=round(float(np.degrees(Rot.from_matrix(REG[s][1]).magnitude())), 2),
                                anchor_shift_cm=round(float(np.linalg.norm(REG[s][0] - H[s]['anchor']) * 100), 2),
                                anchor_shift_xyz_cm=np.round((REG[s][0] - H[s]['anchor']) * 100, 2).tolist()) for s, n in enumerate(names)}
res = dict(episode=a.ep, A=a.A, B=a.B, meshes_A=a.meshes or 'public scans', meshes_B=MB or 'public scans', frames=T, objects=names,
           registration_A=reg_info(REG_A), registration_B=reg_info(REG_B),
           alignment_anchor=(names[fixed[0]] if fixed else f'{names[0]} axis + direction to {names[1] if B > 1 else "-"}'),
           per_object={})
for s, n in enumerate(names):
    d = FB['s'][:, s] - FA['s'][:, s]
    seg_lo = segments(d, -0.05); seg_hi = segments(d, 0.05)

    def seg_rows(sg):
        return [dict(frames=[int(u), int(v)], n=int(v - u + 1), dAUC=round(float(d[u:v + 1].sum() / T), 4),
                     add_cm_A=round(float(FA['add_cm'][u:v + 1, s].mean()), 2), add_cm_B=round(float(FB['add_cm'][u:v + 1, s].mean()), 2),
                     dpos_cm=round(float(np.linalg.norm(dpos[u:v + 1, s], axis=-1).mean() * 100), 2),
                     dz_cm=round(float(dpos[u:v + 1, s, 2].mean() * 100), 2), drot_deg=round(float(drot[u:v + 1, s].mean()), 2))
                for u, v in sg]
    res['per_object'][n] = dict(
        AUC_A=round(float(FA['s'][:, s].mean()), 4), AUC_B=round(float(FB['s'][:, s].mean()), 4),
        dAUC=round(float(d.mean()), 4), dAUC_frame0=round(float(d[0] / T), 4),
        dAUC_translation_only=round(float((FP['s'][:, s] - FA['s'][:, s]).mean()), 4),
        dAUC_rotation_only=round(float((FR['s'][:, s] - FA['s'][:, s]).mean()), 4),
        frame0=dict(add_cm_A=round(float(FA['add_cm'][0, s]), 2), add_cm_B=round(float(FB['add_cm'][0, s]), 2),
                    dpos_cm=round(float(np.linalg.norm(dpos[0, s]) * 100), 2), dz_cm=round(float(dpos[0, s, 2] * 100), 2),
                    drot_deg=round(float(drot[0, s]), 2)),
        change_B_minus_A=dict(dpos_cm_mean=round(float(np.linalg.norm(dpos[:, s], axis=-1).mean() * 100), 2),
                              dpos_cm_max=round(float(np.linalg.norm(dpos[:, s], axis=-1).max() * 100), 2),
                              dz_cm_mean=round(float(dpos[:, s, 2].mean() * 100), 2),
                              drot_deg_mean=round(float(drot[:, s].mean()), 2), drot_deg_max=round(float(drot[:, s].max()), 2)),
        error_A=dict(add_cm_mean=round(float(FA['add_cm'][:, s].mean()), 2), dz_cm_mean=round(float(FA['dz_cm'][:, s].mean()), 2),
                     dxy_cm_mean=round(float(FA['dxy_cm'][:, s].mean()), 2), rot_deg_mean=round(float(FA['rot_deg'][:, s].mean()), 2)),
        error_B=dict(add_cm_mean=round(float(FB['add_cm'][:, s].mean()), 2), dz_cm_mean=round(float(FB['dz_cm'][:, s].mean()), 2),
                     dxy_cm_mean=round(float(FB['dxy_cm'][:, s].mean()), 2), rot_deg_mean=round(float(FB['rot_deg'][:, s].mean()), 2)),
        frames_worse=int((d < -0.05).sum()), frames_better=int((d > 0.05).sum()),
        segments_worse=sorted(seg_rows(seg_lo), key=lambda r: r['dAUC'])[:6],
        segments_better=sorted(seg_rows(seg_hi), key=lambda r: -r['dAUC'])[:6])
print(json.dumps(res, indent=1))
json.dump(res, open(a.out, 'w'), indent=1)
if a.pf:
    np.savez(a.pf, names=np.array(names), **{f'A_{k}': v for k, v in FA.items()}, **{f'B_{k}': v for k, v in FB.items()},
             **{f'Bpos_{k}': v for k, v in FP.items()}, **{f'Brot_{k}': v for k, v in FR.items()}, dpos=dpos, drot=drot)
