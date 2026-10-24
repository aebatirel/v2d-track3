"""Human grasp census per (episode, hand, object) from OUR reference parquet (perceived MANO hands + perceived object
poses; no ground truth). For every hold (contiguous frames with MANO contacts on the object):
  - per-link contact share (palm, thumb1-3, index1-3, ... pinky1-3)
  - contact positions in the object frame (where on the object), mean / p10 / p90 per object PCA axis
  - which side of the object each digit group touches (sign of the contact normal along the PCA thin axis)
  - task wrench along the reference while held: |F| = |m(a - g)|, max acceleration, tilt range, grip torque about
    the human contact centroid (mass 0.3 kg = the simulator's placeholder; inertia from our mesh scaled to 0.3 kg)
Usage: human_grasp_census.py PARQUET LIBRARY_DIR OUT_JSON
"""
import json, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot

G = np.array([0.0, 0.0, -9.81]); MASS = 0.3; FPS = 20.0
LINKS = ['palm', 'thumb1', 'thumb2', 'thumb3', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3',
         'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3']


def holds(mask, min_len=5, gap=3):
    """contiguous runs of True (gaps up to `gap` frames bridged), at least min_len frames."""
    idx = np.where(mask)[0]
    if len(idx) == 0: return []
    runs = []; s = idx[0]; p = idx[0]
    for i in idx[1:]:
        if i - p > gap + 1: runs.append((s, p)); s = i
        p = i
    runs.append((s, p))
    return [(a, b) for a, b in runs if b - a + 1 >= min_len]


def main(parquet, lib, out):
    t = pq.read_table(parquet)
    names = t.column('object_body_names')[0].as_py()
    P = np.array(t.column('object_body_position')[0].as_py(), float)
    T = P.shape[0]
    Q = np.array(t.column('object_body_wxyz')[0].as_py(), float)[:, :, [1, 2, 3, 0]]
    res = dict(parquet=parquet, objects=names, frames=T, holds=[])
    meshes = {}
    for k, n in enumerate(names):
        m = trimesh.load(f'{lib}/{n}.glb', force='mesh')
        c = m.center_mass if m.is_watertight else m.vertices.mean(0)
        I = m.moment_inertia * (MASS / m.mass) if m.is_watertight and m.mass > 0 else np.eye(3) * 1e-3
        Ib = np.linalg.eigvalsh(I)
        _, _, Vt = np.linalg.svd(m.vertices - m.vertices.mean(0), full_matrices=False)
        meshes[n] = dict(com=c, I=I, axes=Vt, ext=np.ptp(np.asarray(m.vertices) @ Vt.T, axis=0))
    for side in ('left', 'right'):
        pid = np.array(t.column(f'mano_{side}_object_contact_part_ids')[0].as_py())
        cpos = np.array(t.column(f'mano_{side}_object_contact_positions')[0].as_py(), float)
        cnrm = np.array(t.column(f'mano_{side}_object_contact_normals')[0].as_py(), float)
        for k, n in enumerate(names):
            on = pid == (k + 1)                       # (T, 16)
            for a, b in holds(on.any(1)):
                fr = np.arange(a, b + 1)
                R = Rot.from_quat(Q[fr, k]); Pk = P[fr, k]
                share = on[fr].mean(0)
                # contact points in the object frame and in its PCA frame
                M = meshes[n]; ax = M['axes']
                pts, nrm, lab = [], [], []
                for j, f in enumerate(fr):
                    for l in np.where(on[f])[0]:
                        po = R[j].inv().apply(cpos[f, l] - Pk[j])
                        no = R[j].inv().apply(cnrm[f, l])
                        pts.append(ax @ (po - M['com'])); nrm.append(ax @ no); lab.append(l)
                pts = np.array(pts); nrm = np.array(nrm); lab = np.array(lab)
                grp = {'palm': [0], 'thumb': [1, 2, 3], 'fingers': list(range(4, 16))}
                where = {}
                for g, ls in grp.items():
                    s = np.isin(lab, ls)
                    if s.sum() == 0: continue
                    where[g] = dict(n=int(s.sum()),
                                    pos_mean_cm=(pts[s].mean(0) * 100).round(1).tolist(),
                                    pos_p10_cm=(np.percentile(pts[s], 10, 0) * 100).round(1).tolist(),
                                    pos_p90_cm=(np.percentile(pts[s], 90, 0) * 100).round(1).tolist(),
                                    normal_mean=nrm[s].mean(0).round(2).tolist(),
                                    thin_axis_normal_pos_share=round(float((nrm[s][:, 2] > 0).mean()), 2))
                # task wrench over the whole object track (savgol), reported over this hold
                Rall = Rot.from_quat(Q[:, k]); Pc = P[:, k] + Rall.apply(M['com'])
                win = 9 if T >= 9 else (T // 2) * 2 - 1
                acc = savgol_filter(Pc, win, 3, deriv=2, delta=1 / FPS, axis=0, mode='interp')
                vel = savgol_filter(Pc, win, 3, deriv=1, delta=1 / FPS, axis=0, mode='interp')
                F = MASS * (acc - G)
                grip = pts.mean(0) if len(pts) else np.zeros(3)          # PCA frame, relative to COM
                grip_obj = ax.T @ grip                                    # object frame, relative to COM
                r_w = Rall[fr].apply(grip_obj)                            # COM -> grip, world
                tau_grip = np.cross(-r_w, F[fr])                          # gravity + inertial load about the grip
                tilt = np.degrees((Rall[fr] * Rall[a].inv()).magnitude())
                lift = (Pc[fr, 2] - Pc[0, 2]) * 100
                res['holds'].append(dict(
                    side=side, object=n, frames=[int(a), int(b)], n=len(fr),
                    link_share={LINKS[i]: round(float(share[i]), 2) for i in range(16) if share[i] > 0.05},
                    where=where, mesh_pca_extent_cm=(M['ext'] * 100).round(1).tolist(),
                    grip_from_com_cm=round(float(np.linalg.norm(grip) * 100), 1),
                    F_max_N=round(float(np.linalg.norm(F[fr], axis=1).max()), 2),
                    acc_p95_ms2=round(float(np.percentile(np.linalg.norm(acc[fr], axis=1), 95)), 2),
                    speed_max_ms=round(float(np.linalg.norm(vel[fr], axis=1).max()), 2),
                    tau_grip_max_Nm=round(float(np.linalg.norm(tau_grip, axis=1).max()), 3),
                    tau_grip_p50_Nm=round(float(np.median(np.linalg.norm(tau_grip, axis=1))), 3),
                    tilt_max_deg=round(float(tilt.max()), 1), lift_max_cm=round(float(lift.max()), 1)))
    json.dump(res, open(out, 'w'), indent=1)
    for h in res['holds']:
        if h['n'] < 10: continue
        print(h['side'], h['object'], h['frames'], 'n', h['n'], '| F_max', h['F_max_N'], 'acc95', h['acc_p95_ms2'],
              'tau_grip', h['tau_grip_p50_Nm'], '/', h['tau_grip_max_Nm'], '| grip', h['grip_from_com_cm'], 'cm',
              '| tilt', h['tilt_max_deg'], 'lift', h['lift_max_cm'])
        print('   links', h['link_share'])
        for g, w in h['where'].items():
            print('   ', g, 'n', w['n'], 'pos', w['pos_mean_cm'], 'p10', w['pos_p10_cm'], 'p90', w['pos_p90_cm'],
                  'nrm', w['normal_mean'], '+thin', w['thin_axis_normal_pos_share'])


if __name__ == '__main__':
    main(*sys.argv[1:4])
