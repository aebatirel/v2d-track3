"""posefix diagnostics (READS GROUND TRUTH: public parquet mocap poses and public scans). Run only after the transformed
tracks are written and their sha256 recorded (PREREG section 6). Decides nothing about the transform.

It replicates pipeline/score_registered.py's chain (same kit functions, same seeds, same scan stand-ins) to get:
  - a check that the replicated perception AUC equals the scorer's JSON (before and after);
  - mean symmetric ADD (cm) per object and episode (the AUC's own per-frame error), before / after;
  - the direction check: per shifted segment, cosine between the push (anchor displacement after - before, rotated
    into the mocap world by the BEFORE scene alignment) and the correction (mocap - ours, BEFORE alignment), segment
    frame means;
  - the mesh check: overlap volume and max depth of OUR meshes placed at the MOCAP poses (pose = mocap anchor pose
    composed with the inverse of the kit's registration of our mesh), and of the public scans at the mocap poses, at
    every frame where both objects of a pair are at rest (our H30 rest segments), next to the overlap at our poses.

Usage: python -I pf_diag.py EP BEFORE_NPZ AFTER_NPZ POSEFIX_JSON --t3 T3 --kit KIT --meshes MESHDIR --out JSON
"""
import argparse, json, os, sys
import numpy as np
import trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

p = argparse.ArgumentParser()
p.add_argument('ep', type=int); p.add_argument('before'); p.add_argument('after'); p.add_argument('posefix')
p.add_argument('--t3'); p.add_argument('--kit'); p.add_argument('--meshes'); p.add_argument('--out')
p.add_argument('--scorer_before'); p.add_argument('--scorer_after')
a = p.parse_args()
sys.path.insert(0, a.kit)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
import pf_lib as L

SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


def host_geometry(n, slot):
    m = trimesh.load(scan_path(n), force='mesh')
    v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
            axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order)


tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
B = len(names)


def gt_xyzw(o):
    q = np.array(o['pose'], float)
    return np.r_[q[:3], q[4:7], q[3]]


def traj(path):
    P = np.load(path)
    T = len(P[names[0]])
    return np.stack([[np.r_[P[n][i][:3, 3], Rot.from_matrix(P[n][i][:3, :3]).as_quat()] for n in names]
                     for i in range(T)]), {n: np.asarray(P[n], np.float64) for n in names}


X0, M0 = traj(a.before)
X1, M1 = traj(a.after)
T = len(X0)
gt = np.stack([[gt_xyzw([o for o in tab['observation.objects'].iloc[fr] if o['name'] == n][0]) for n in names]
               for fr in range(T)])
H = [host_geometry(n, s) for s, n in enumerate(names)]
REG = []
for s, n in enumerate(names):
    cand = budget_mesh(f'{a.meshes}/{n}.glb', 4096, 4096)
    REG.append(T3._register_object_body(cand, H[s]['mesh'], H[s]['anchor'], 1_000_003 * a.ep + 101 * s))
axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
ref = gt[:, None].copy()
for s in range(B):
    ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])


def convert(X):
    ach = X[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
    return ach


def alignment(ach):
    """The kit's scene alignment as (R, offset) (re-derived from _align_registered_scene's output)."""
    al = T3._align_registered_scene(ach, ref, axes)
    # world transform: al_pos = R @ ach_pos + off; recover R from orientations of slot 0 and off from frame 0
    R = T3._rotation_matrix(al[0, 0, 0, 3:]) @ T3._rotation_matrix(ach[0, 0, 0, 3:]).T
    off = al[0, 0, 0, :3] - R @ ach[0, 0, 0, :3]
    return al, R, off


C0, C1 = convert(X0), convert(X1)
A0, R0, o0 = alignment(C0)
A1, R1, o1 = alignment(C1)
res = dict(ep=a.ep, objects=names, frames=T)
for tag, A_ in (('before', A0), ('after', A1)):
    res[f'auc_{tag}'] = round(float(T3._registered_pose_metric('add_auc', A_, ref, pts, axes, orders)), 4)
    res[f'add_cm_{tag}'] = {n: round(float(T3._symmetry_point_errors(A_[:, :, s], ref[:, :, s], pts[s], axes[s],
                                                                       orders[s]).mean() * 100), 4)
                            for s, n in enumerate(names)}
for tag, path in (('before', a.scorer_before), ('after', a.scorer_after)):
    if path and os.path.exists(path):
        res[f'auc_{tag}_scorer'] = json.load(open(path))['perception']['AUC']
# ---- direction check ----
PF = json.load(open(a.posefix))
segs = []
C1b = C1.copy()                                   # after poses under the BEFORE alignment
C1b[:, 0, :, :3] = C1[:, 0, :, :3] @ R0.T + o0
for g in PF['segments']:
    if g['t_norm_mm'] == 0 and g['r_deg'] == 0:
        continue
    s = names.index(g['obj']); fr = np.arange(g['start'], g['end'] + 1)
    push = (C1b[fr, 0, s, :3] - A0[fr, 0, s, :3]).mean(0)
    corr = (ref[fr, 0, s, :3] - A0[fr, 0, s, :3]).mean(0)
    cos = float(push @ corr / max(np.linalg.norm(push) * np.linalg.norm(corr), 1e-12))
    err_b = np.linalg.norm(ref[fr, 0, s, :3] - A0[fr, 0, s, :3], axis=1).mean()
    err_a_samealign = np.linalg.norm(ref[fr, 0, s, :3] - C1b[fr, 0, s, :3], axis=1).mean()
    err_a_scored = np.linalg.norm(ref[fr, 0, s, :3] - A1[fr, 0, s, :3], axis=1).mean()
    segs.append(dict(obj=g['obj'], start=g['start'], end=g['end'], status=g['status'],
                     push_mm=round(float(1000 * np.linalg.norm(push)), 2),
                     corr_mm=round(float(1000 * np.linalg.norm(corr)), 2),
                     corr_along_push_mm=round(float(1000 * push @ corr / max(np.linalg.norm(push), 1e-12)), 2),
                     cos=round(cos, 3),
                     pos_err_mm_before=round(float(1000 * err_b), 2),
                     pos_err_mm_after_same_alignment=round(float(1000 * err_a_samealign), 2),
                     pos_err_mm_after_scored=round(float(1000 * err_a_scored), 2)))
res['direction'] = segs
# ---- mesh check ----
def Xmat(s):
    ca, Rb = REG[s]
    X = np.eye(4); X[:3, :3] = Rb.T; X[:3, 3] = ca
    return X


def mat(q):
    M = np.eye(4); M[:3, :3] = T3._rotation_matrix(q[3:]); M[:3, 3] = q[:3]
    return M


ours = {n: L.SDF(n, *L.load_mesh(n, a.meshes)) for n in names}
scans = {}
for s, n in enumerate(names):
    v, f = budget_mesh(scan_path(n), 4096, 4096)
    scans[n] = L.SDF(n, np.asarray(v, np.float64), np.asarray(f, np.int64), cache=f'{L.SP}/sdf_scan')


def pair_overlap(sa, sb, Ma, Mb):
    small, big, Ms, Mg = (sa, sb, Ma, Mb) if sa.volume_cm3 <= sb.volume_cm3 else (sb, sa, Mb, Ma)
    vol = float((big.query(L.tf(L.inv(Mg) @ Ms, small.inside_nodes)) < 0).sum()) * L.GRID_H ** 3 * 1e6
    d1 = -sb.query(L.tf(L.inv(Mb) @ Ma, sa.probes)).min(); d2 = -sa.query(L.tf(L.inv(Ma) @ Mb, sb.probes)).min()
    return vol, 1000 * max(0.0, d1, d2)


rest = {n: np.zeros(T, bool) for n in names}
for g in PF['segments']:
    rest[g['obj']][g['start']:g['end'] + 1] = True
mesh = []
for i in range(B):
    for j in range(i + 1, B):
        a_, b_ = names[i], names[j]
        fr = np.nonzero(rest[a_] & rest[b_])[0]
        if not len(fr):
            continue
        rows = []
        for t in fr[::2]:
            Ra, Rb_ = mat(ref[t, 0, i]), mat(ref[t, 0, j])                  # scan-anchor poses in the mocap world
            Oa, Ob = Ra @ np.linalg.inv(Xmat(i)), Rb_ @ np.linalg.inv(Xmat(j))   # our meshes at the mocap poses
            Sa = mat(gt[t, i]); Sb = mat(gt[t, j])                            # scans at the mocap poses
            v_m, d_m = pair_overlap(ours[a_], ours[b_], Oa, Ob)
            v_o, d_o = pair_overlap(ours[a_], ours[b_], M0[a_][t], M0[b_][t])
            v_s, d_s = pair_overlap(scans[a_], scans[b_], Sa, Sb)
            rows.append((int(t), v_o, d_o, v_m, d_m, v_s, d_s))
        R_ = np.array(rows)
        mesh.append(dict(pair=f'{a_}|{b_}', rest_frames=int(len(fr)), sampled=int(len(R_)),
                         ours_at_ours=dict(median_cm3=round(float(np.median(R_[:, 1])), 2), max_cm3=round(float(R_[:, 1].max()), 2),
                                           median_depth_mm=round(float(np.median(R_[:, 2])), 2)),
                         ours_at_mocap=dict(median_cm3=round(float(np.median(R_[:, 3])), 2), max_cm3=round(float(R_[:, 3].max()), 2),
                                            median_depth_mm=round(float(np.median(R_[:, 4])), 2)),
                         scans_at_mocap=dict(median_cm3=round(float(np.median(R_[:, 5])), 2), max_cm3=round(float(R_[:, 5].max()), 2),
                                             median_depth_mm=round(float(np.median(R_[:, 6])), 2)),
                         frames=[list(map(lambda x: round(float(x), 2), r)) for r in rows]))
res['mesh_check'] = mesh
json.dump(res, open(a.out, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('mesh_check',)}, indent=None)[:2000])
for m in mesh:
    print(m['pair'], m['rest_frames'], m['ours_at_ours'], m['ours_at_mocap'], m['scans_at_mocap'])
