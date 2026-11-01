"""Eval precheck of the collision-carve round 2 (DIAGNOSTIC ONLY; decides nothing, nothing tuned on it).

PREREG F-I5.15 (3) precheck measures (table penetration, support / float, pairwise overlap) and the cavity question,
on the PACKED references of focused-pascal's docs/research/work/masses-eval-20261031/packed_refs.json (branch
claude/focused-pascal-2nz9s1, c6fe323) with the packed simulator assets (library_v3 / support-filled sf assets; carve
pieces meshes/carve/ev10, ev01 where packed) and FlashCHORD's packed decomposition (coacd 1.0.11, threshold 0.05) of the
visual meshes (packed_coacd.py).

Standalone on purpose: the gmg guard refuses '.parquet' and 'library_v3' paths, and both are this diagnostic's inputs
(the pack's own references and simulator assets; they are measured, never used as shape evidence for any mesh).
GT-free: no scan, mocap, dataset parquet 'pose' field or *_align file is read; the references are our perception
(tier P1). Reference columns read: object_body_names / _position / _wxyz, object_mesh_paths, object_urdf_paths, fps,
robot_{left,right}_frames (hand points), mano_{left,right}_object_contact_part_ids / _positions (the reference's hand
contact labels), sequence_id.

Colliders per object, all in the object's link frame:
  visual   the packed visual mesh (= the collision source mesh of the pack's URDF)
  packed   carve pieces (one convex hull each: FlashCHORD keeps a convex piece as one hull) or the coacd 1.0.11 hulls
  faithful the visual mesh's 2 mm cells, centre inside (F-I5.15 (3); exact vertical-ray parity voxelisation)
Thresholds: s_max 4 mm for (a) table and (b) support (F-I5.15 (3), informed F-I1.14); overlap counted at > 0 (the
F-I5.15 (3c) trigger) and at >= 1 cm3 (informed: the spoon-diag frame threshold); hands: the reference's contact
labels (primary 'hands-off' set H0 = no label in either hand), plus the F-I5.3 (2) 30 mm rule on the robot hand points.

Usage: python -I evalcheck.py CONFIG.json OUT_DIR [ep,...]
"""
import json
import os
import re
import sys
import time

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vox  # noqa: E402  (copy of cdo-sprint/spoon-diag/scripts/vox.py: exact parity voxelisation)

SMAX = 0.004          # F-I5.15 (3) s_max (informed F-I1.14)
OV_FRAME_CM3 = 1.0    # informed: cdo-sprint/spoon-diag frame threshold
HAND_MM = 0.030       # F-I5.3 (2) / F-I5.16 (3) hands-off radius
STATIC_M = 0.002      # F-I1.1 static: < 2 mm per frame
STATIC_N = 5          # F-I1.1 >= 5 frames
P_VIS, P_GUEST, P_FA, P_SURF = 0.001, 0.0015, 0.002, 0.002
RECV_ORDER = ['plastic_dish_rack', 'white_pot', 'blue_cup']   # receiver by role (cup / pot / rack hold the partner)
COLS = ['object_body_names', 'object_body_position', 'object_body_wxyz', 'object_mesh_paths', 'object_urdf_paths',
        'fps', 'robot_left_frames', 'robot_right_frames', 'mano_left_object_contact_part_ids',
        'mano_right_object_contact_part_ids', 'mano_left_object_contact_positions',
        'mano_right_object_contact_positions', 'sequence_id']


# ---------------------------------------------------------------------------------------------------- inputs
def support(usda):
    s = open(usda).read()
    h = float(re.search(r'double height = ([-0-9.e]+)', s).group(1))
    r = float(re.search(r'double radius = ([-0-9.e]+)', s).group(1))
    t = [float(x) for x in re.search(r'xformOp:translate = \(([^)]*)\)', s).group(1).split(',')]
    assert s.count('def Cylinder') == 1 and 'upAxis = "Z"' in s, usda
    return dict(top_z=t[2] + h / 2, centre_xy=t[:2], radius=r, height=h, file=usda)


def load_ref(p):
    row = pq.read_table(p, columns=COLS).to_pylist()[0]
    pos = np.asarray(row['object_body_position'], float)
    q = np.asarray(row['object_body_wxyz'], float)
    nf, no = pos.shape[:2]
    T = np.tile(np.eye(4), (nf, no, 1, 1))
    T[:, :, :3, :3] = Rot.from_quat(q[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(nf, no, 3, 3)
    T[:, :, :3, 3] = pos
    hands = np.concatenate([np.asarray(row['robot_left_frames'], float)[:, 1:, :3],
                            np.asarray(row['robot_right_frames'], float)[:, 1:, :3]], 1)   # drop 'universe'
    pid = np.concatenate([np.asarray(row['mano_left_object_contact_part_ids']),
                          np.asarray(row['mano_right_object_contact_part_ids'])], 1)
    cpos = np.concatenate([np.asarray(row['mano_left_object_contact_positions'], float),
                           np.asarray(row['mano_right_object_contact_positions'], float)], 1)
    return dict(names=list(row['object_body_names']), T=T, hands=hands, pid=pid, cpos=cpos, fps=row['fps'],
                mesh_paths=list(row['object_mesh_paths']), urdf_paths=list(row['object_urdf_paths']),
                seq=row['sequence_id'], frames=nf)


def tf(T, X):
    return np.asarray(X) @ T[:3, :3].T + T[:3, 3]


def union_occ(hulls, pitch, pad=0.002):
    """Centre-inside occupancy of the union of convex hulls on a grid of PITCH."""
    allv = np.vstack(hulls)
    lo = allv.min(0) - pad; hi = allv.max(0) + pad
    n = np.ceil((hi - lo) / pitch).astype(int)
    occ = np.zeros(n, bool)
    for V in hulls:
        e = ConvexHull(V).equations
        a = np.clip(np.floor((V.min(0) - lo) / pitch).astype(int), 0, n - 1)
        b = np.clip(np.ceil((V.max(0) - lo) / pitch).astype(int), 0, n - 1)
        ax = [lo[k] + (np.arange(a[k], b[k] + 1) + 0.5) * pitch for k in range(3)]
        G = np.stack(np.meshgrid(*ax, indexing='ij'), -1)
        ins = np.all(G.reshape(-1, 3) @ e[:, :3].T + e[:, 3] <= 1e-9, 1).reshape(G.shape[:3])
        occ[a[0]:b[0] + 1, a[1]:b[1] + 1, a[2]:b[2] + 1] |= ins
    return vox.Grid(lo, pitch, occ)


def surf_samples(mesh, pitch, seed=0):
    n = int(np.ceil(mesh.area / pitch ** 2))
    return np.asarray(trimesh.sample.sample_surface_even(mesh, n, seed=seed)[0]) if n > 0 else np.zeros((0, 3))


class Obj:
    def __init__(self, name, mesh_path, hulls, pieces_src):
        m = trimesh.load(mesh_path, force='mesh')
        self.mesh = trimesh.Trimesh(np.asarray(m.vertices, float), np.asarray(m.faces), process=True)
        self.name, self.mesh_path, self.pieces_src = name, mesh_path, pieces_src
        self.V = np.asarray(self.mesh.vertices)
        self.vis1 = vox.voxelize(self.mesh, P_VIS)
        self.gpts = vox.voxelize(self.mesh, P_GUEST).centres()
        fa = vox.voxelize(self.mesh, P_FA)
        self.fa = fa
        idx = np.argwhere(fa.occ)
        self.fa_cells = fa.lo + (idx + 0.5) * fa.pitch
        cor = np.vstack([fa.lo + (idx + np.array(o)) * fa.pitch for o in np.ndindex(2, 2, 2)])
        self.fa_corners = np.unique(np.round(cor, 9), axis=0)
        self.fa_tree = cKDTree(self.fa_cells)
        self.hulls = [np.asarray(h, float) for h in hulls]
        self.pk1 = union_occ(self.hulls, P_VIS)
        self.pk_gpts = union_occ(self.hulls, P_GUEST).centres()
        self.pk_V = np.vstack(self.hulls)
        self.surf = surf_samples(self.mesh, P_SURF)
        self.surf_tree = cKDTree(self.surf)
        pks = [surf_samples(trimesh.convex.convex_hull(h), P_SURF) for h in self.hulls]
        self.pk_surf = np.vstack([p for p in pks if len(p)])
        self.pk_tree = cKDTree(self.pk_surf)
        ch = ConvexHull(self.V)
        self.hull_eq = ch.equations
        self.hull_lo, self.hull_hi = self.V.min(0), self.V.max(0)
        self.bbox = np.array([[x, y, z] for x in self.hull_lo[[0]].tolist() + self.hull_hi[[0]].tolist()
                              for y in (self.hull_lo[1], self.hull_hi[1]) for z in (self.hull_lo[2], self.hull_hi[2])])
        self.info = dict(name=name, mesh=mesh_path, pieces_src=pieces_src, n_pieces=len(self.hulls),
                         vis_cm3=round(float(self.mesh.volume) * 1e6, 2),
                         vis1_cm3=round(float(self.vis1.occ.sum()) * P_VIS ** 3 * 1e6, 2),
                         faithful_cm3=round(float(fa.occ.sum()) * P_FA ** 3 * 1e6, 2),
                         faithful_cells=int(fa.occ.sum()),
                         packed_union_cm3=round(float(self.pk1.occ.sum()) * P_VIS ** 3 * 1e6, 2),
                         packed_outside_visual_cm3=round(float((~self.vis1.lookup(self.pk1.centres())).sum())
                                                         * P_VIS ** 3 * 1e6, 2),
                         watertight=bool(self.mesh.is_watertight))

    def in_hull_region(self, X):
        """Inside the visual mesh's convex hull (AABB prefilter)."""
        out = np.zeros(len(X), bool)
        m = np.all((X >= self.hull_lo - 1e-9) & (X <= self.hull_hi + 1e-9), 1)
        if m.any():
            Y = X[m]
            out[np.nonzero(m)[0]] = np.all(Y @ self.hull_eq[:, :3].T + self.hull_eq[:, 3] <= 1e-9, 1)
        return out


def cube_dist(tree, cells, pitch, X, k=8):
    if not len(X):
        return np.zeros(0)
    d, j = tree.query(X, k=min(k, len(cells)))
    if j.ndim == 1:
        j = j[:, None]
    C = cells[j]
    q = np.maximum(np.abs(X[:, None, :] - C) - 0.5 * pitch, 0.0)
    return np.linalg.norm(q, axis=2).min(1)


# ---------------------------------------------------------------------------------------------------- per frame
def pair_frame(R, G, T_wr, T_wg):
    """Guest G against receiver R at one frame. Volumes in cm3, lengths in mm."""
    T_rg = np.linalg.inv(T_wr) @ T_wg
    v15 = P_GUEST ** 3 * 1e6
    Xg = tf(T_rg, G.gpts)
    in_rv = R.vis1.lookup(Xg)
    in_rp = R.pk1.lookup(Xg)
    in_hr = R.in_hull_region(Xg)
    Xgp = tf(T_rg, G.pk_gpts)
    in_pp = R.pk1.lookup(Xgp)
    Xgf = tf(T_rg, G.fa_cells)
    in_ff = R.fa.lookup(Xgf)
    o = dict(V_faithful=float(in_ff.sum()) * P_FA ** 3 * 1e6, V_packed=float(in_pp.sum()) * v15,
             V_visual=float(in_rv.sum()) * v15, V_gvis_in_rpk=float(in_rp.sum()) * v15,
             V_gvis_in_rpk_only=float((in_rp & ~in_rv).sum()) * v15,
             V_gvis_in_rcavity=float((in_hr & ~in_rv).sum()) * v15)
    # depths (mm) of guest visual points inside the receiver visual / packed (distance to that surface; packed is a
    # lower bound: distances to internal piece faces count)
    o['depth_vis_mm'] = float(R.surf_tree.query(Xg[in_rv])[0].max() * 1e3) if in_rv.any() else 0.0
    o['depth_pk_mm'] = float(R.pk_tree.query(Xg[in_rp])[0].max() * 1e3) if in_rp.any() else 0.0
    # distances (mm): faithful (cube distance), visual surfaces, packed surfaces
    if in_ff.any():
        o['dist_faithful_mm'] = 0.0
    else:
        d1 = cube_dist(R.fa_tree, R.fa_cells, P_FA, tf(T_rg, G.fa_corners)).min()
        d2 = cube_dist(G.fa_tree, G.fa_cells, P_FA, tf(np.linalg.inv(T_rg), R.fa_corners)).min()
        o['dist_faithful_mm'] = float(min(d1, d2) * 1e3)
    o['dist_visual_mm'] = 0.0 if in_rv.any() else float(R.surf_tree.query(tf(T_rg, G.surf))[0].min() * 1e3)
    o['dist_packed_mm'] = 0.0 if in_pp.any() else float(R.pk_tree.query(tf(T_rg, G.pk_surf))[0].min() * 1e3)
    return o


def obj_frame(O, T_w, sup):
    top = sup['top_z']
    zf = tf(T_w, O.fa_corners)
    zv = tf(T_w, O.V)
    zp = tf(T_w, O.pk_V)
    i = int(np.argmin(zv[:, 2]))
    r_xy = float(np.linalg.norm(zv[i, :2] - np.asarray(sup['centre_xy'])))
    return dict(low_faithful_mm=float((zf[:, 2].min() - top) * 1e3), low_visual_mm=float((zv[:, 2].min() - top) * 1e3),
                low_packed_mm=float((zp[:, 2].min() - top) * 1e3), lowest_r_xy_mm=r_xy * 1e3,
                off_support=bool(r_xy > sup['radius']))


def static_mask(T, objs):
    nf = T.shape[0]
    disp = np.zeros((nf, len(objs)))
    for j, O in enumerate(objs):
        P = np.stack([tf(T[f, j], O.bbox) for f in range(nf)])
        disp[1:, j] = np.linalg.norm(P[1:] - P[:-1], axis=2).max(1)
    disp[0] = disp[1] if nf > 1 else 0
    st = np.all(disp < STATIC_M, 1)
    runs, f = [], 0
    while f < nf:
        if st[f]:
            g = f
            while g + 1 < nf and st[g + 1]:
                g += 1
            if g - f + 1 >= STATIC_N:
                runs.append((f, g))
            f = g + 1
        else:
            f += 1
    return disp, runs


def run_episode(ep, cfg, out_dir, log):
    t0 = time.time()
    R_ = load_ref(cfg['ref'])
    sup = support(cfg['support'])
    names = R_['names']
    objs = []
    for j, n in enumerate(names):
        oc = cfg['objects'][n]
        hulls = [np.load(oc['packed_npz'])[f'v{i}'] for i in range(int(np.load(oc['packed_npz'])['n']))] \
            if oc.get('packed_npz') else [np.asarray(trimesh.load(p, force='mesh').vertices, float)
                                         for p in oc['pieces']]
        objs.append(Obj(n, oc['mesh'], hulls, oc['pieces_src']))
        log(f'ep{ep} {n}: {objs[-1].info}')
    nf = R_['frames']
    T = R_['T']
    # hands: contact labels (attributed to the nearest object surface), robot hand points within 30 mm
    lab = R_['pid'] > 0
    contact_any = lab.any(1)
    contact_obj = np.zeros((nf, len(objs)), bool)
    hand_min = np.full((nf, len(objs)), np.inf)
    for f in range(nf):
        P = R_['cpos'][f][lab[f]]
        dd = []
        for j, O in enumerate(objs):
            Ti = np.linalg.inv(T[f, j])
            dd.append(O.surf_tree.query(tf(Ti, P))[0] if len(P) else np.zeros(0))
            hand_min[f, j] = O.surf_tree.query(tf(Ti, R_['hands'][f]))[0].min()
        if len(P):
            k = np.argmin(np.stack(dd), 0)
            for j in range(len(objs)):
                contact_obj[f, j] = bool((k == j).any())
    H0 = ~contact_any
    H30 = np.all(hand_min >= HAND_MM, 1)
    disp, runs = static_mask(T, objs)
    # roles
    ir = min(range(len(names)), key=lambda j: RECV_ORDER.index(names[j]) if names[j] in RECV_ORDER else 99)
    ig = 1 - ir
    Rr, Gg = objs[ir], objs[ig]
    # F-I1.1 relative speed: the guest origin in the receiver's frame, per frame
    rel = np.array([(np.linalg.inv(T[f, ir]) @ T[f, ig])[:3, 3] for f in range(nf)])
    rel_speed = np.r_[0.0, np.linalg.norm(np.diff(rel, axis=0), axis=1)] if nf > 1 else np.zeros(1)
    if nf > 1:
        rel_speed[0] = rel_speed[1]
    np.savez(os.path.join(out_dir, f'ep{ep}_poses.npz'), T=T, names=np.array(names), ir=ir, ig=ig)
    per = dict(pair=[], obj={n: [] for n in names})
    for f in range(nf):
        pf = pair_frame(Rr, Gg, T[f, ir], T[f, ig])
        per['pair'].append(pf)
        for j, O in enumerate(objs):
            per['obj'][names[j]].append(obj_frame(O, T[f, j], sup))
    # verdicts per frame (faithful colliders; F-I5.15 (3) thresholds)
    rows = []
    for f in range(nf):
        pf = per['pair'][f]
        r = dict(frame=f, H0=bool(H0[f]), H30=bool(H30[f]), contact=[bool(x) for x in contact_obj[f]],
                 rel_speed_mm=round(float(rel_speed[f]) * 1e3, 2),
                 hand_min_mm=[round(float(x) * 1e3, 1) for x in hand_min[f]], static_disp_mm=[round(float(x) * 1e3, 2)
                                                                                         for x in disp[f]])
        fails = []
        for j, n in enumerate(names):
            of = per['obj'][n][f]
            pen = max(0.0, -of['low_faithful_mm'])
            gap_t = max(0.0, of['low_faithful_mm'])
            sup_d = min(gap_t, pf['dist_faithful_mm'])
            gap_tv = max(0.0, of['low_visual_mm'])
            sup_dv = min(gap_tv, pf['dist_visual_mm'])
            of.update(pen_faithful_mm=pen, pen_visual_mm=max(0.0, -of['low_visual_mm']),
                      pen_packed_mm=max(0.0, -of['low_packed_mm']), float_faithful_mm=sup_d, float_visual_mm=sup_dv)
            if pen > SMAX * 1e3:
                fails.append(f'a_table:{n}')
            if sup_d > SMAX * 1e3:
                fails.append(f'b_float:{n}')
        if pf['V_faithful'] >= OV_FRAME_CM3:
            fails.append('c_overlap>=1cm3')
        r['fails'] = fails
        rows.append(r)
    res = dict(ep=ep, seq=R_['seq'], frames=nf, fps=R_['fps'], names=names, receiver=names[ir], guest=names[ig],
               support=sup, objects=[O.info for O in objs], n_H0=int(H0.sum()), n_H30=int(H30.sum()),
               n_contact_frames=int(contact_any.sum()), static_runs_world_bbox=[list(map(int, r)) for r in runs],
               secs=round(time.time() - t0, 1))
    out = dict(summary=res, per_frame=dict(rows=rows, pair=per['pair'], obj=per['obj']))
    json.dump(out, open(os.path.join(out_dir, f'ep{ep}_frames.json'), 'w'), default=float)
    log(f'ep{ep} done in {res["secs"]} s: H0 {res["n_H0"]} / {nf}, H30 {res["n_H30"]}, receiver {names[ir]}')
    return out


def main():
    cfg = json.load(open(sys.argv[1]))
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    eps = sys.argv[3].split(',') if len(sys.argv) > 3 else list(cfg['episodes'])
    lf = open(os.path.join(out_dir, 'evalcheck.log'), 'a')

    def log(s):
        line = time.strftime('%H:%M:%S ', time.gmtime()) + s
        print(line, flush=True)
        lf.write(line + '\n'); lf.flush()
    for ep in eps:
        run_episode(ep, cfg['episodes'][ep], out_dir, log)


if __name__ == '__main__':
    main()
