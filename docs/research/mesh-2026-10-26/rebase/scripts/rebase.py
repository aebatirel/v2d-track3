"""Collision-only re-base of one object (pot / pitcher) for one reference (GATES.md, pushed 0b8291f before any
candidate was measured). GT-free: our reference parquet (object poses, robot hand frames), our table estimate (the
reference's support usda), our meshes and the packed collision pieces. Nothing else is read.

  python -I rebase.py CONFIG.json OUT_DIR

CONFIG: {"set", "ref", "usda", "target", "objects": {name: {"visual": glb, "urdf": urdf,
          "packed": {"npz": coacd npz} | {"files": [piece files]}}}, "packed_count"}
OUT_DIR: frames.json, rebase.json, cand_a/<target>/piece_XX.obj, cand_b/<target>/piece_XX.obj.
G3 / G4 (MuJoCo) and G5 / coacd checks are separate steps (settle.py, checks.py) on the same OUT_DIR.
"""
import hashlib
import json
import os
import re
import sys
import time

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.optimize import linprog
from scipy.spatial import ConvexHull, HalfspaceIntersection, cKDTree
from scipy.spatial.transform import Rotation as Rot

HAND_M = 0.030          # H30
NEAR_M = 0.015          # on the table: lowest packed point within +-15 mm (support_fill NEAR)
TOUCH_M = 0.004         # packed pieces within 4 mm
STATIC_M = 0.002        # < 2 mm per frame
RUN_N = 5               # runs >= 5 frames
D_MIN_MM, D_MAX_MM = 1.0, 12.0
PITCH_OV = 0.0015       # overlap grid
SURF = 0.002            # surface samples
DEBRIS_M3, THIN_M = 2e-8, 2e-4
RECV_ORDER = ['plastic_dish_rack', 'white_pot', 'blue_cup']


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def support(usda):
    s = open(usda).read()
    h = float(re.search(r'double height = ([-0-9.e]+)', s).group(1))
    r = float(re.search(r'double radius = ([-0-9.e]+)', s).group(1))
    t = [float(x) for x in re.search(r'xformOp:translate = \(([^)]*)\)', s).group(1).split(',')]
    assert s.count('def Cylinder') == 1 and 'upAxis = "Z"' in s, usda
    return dict(top_z=t[2] + h / 2, centre_xy=t[:2], radius=r, height=h, file=usda, md5=md5(usda))


def load_ref(p):
    cols = ['object_body_names', 'object_body_position', 'object_body_wxyz', 'robot_left_frames', 'robot_right_frames',
            'sequence_id', 'object_urdf_paths']
    row = pq.read_table(p, columns=cols).to_pylist()[0]
    pos = np.asarray(row['object_body_position'], float); q = np.asarray(row['object_body_wxyz'], float)
    nf, no = pos.shape[:2]
    T = np.tile(np.eye(4), (nf, no, 1, 1))
    T[:, :, :3, :3] = Rot.from_quat(q[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(nf, no, 3, 3)
    T[:, :, :3, 3] = pos
    hands = np.concatenate([np.asarray(row['robot_left_frames'], float)[:, 1:, :3],
                            np.asarray(row['robot_right_frames'], float)[:, 1:, :3]], 1)   # drop 'universe'
    return dict(names=list(row['object_body_names']), T=T, hands=hands, nf=nf, seq=row['sequence_id'],
                urdf_paths=list(row['object_urdf_paths']), md5=md5(p))


def load_mesh(p):
    m = trimesh.load(p, force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices, float), np.asarray(m.faces), process=True)


def load_pieces(spec):
    """Packed pieces: the CoACD hulls of the collision glb ('npz', FlashCHORD's call), then any extra collision files
    of the URDF ('files': ev01 carve pieces, support_fill arc feet), in URDF order."""
    out, src = [], []
    if 'npz' in spec:
        z = np.load(spec['npz'])
        out += [np.asarray(z[f'v{i}'], float) for i in range(int(z['n']))]; src += [None] * int(z['n'])
    for f in spec.get('files', []):
        out.append(np.asarray(trimesh.load(f, force='mesh').vertices, float)); src.append(f)
    return out, src


def tf(T, X):
    return np.asarray(X) @ T[:3, :3].T + T[:3, 3]


def runs(mask, n=RUN_N):
    out, f = [], 0
    while f < len(mask):
        if mask[f]:
            g = f
            while g + 1 < len(mask) and mask[g + 1]:
                g += 1
            if g - f + 1 >= n:
                out.append([int(f), int(g)])
            f = g + 1
        else:
            f += 1
    return out


def run_mask(rs, nf):
    m = np.zeros(nf, bool)
    for a, b in rs:
        m[a:b + 1] = True
    return m


def hull_surface(hulls, pitch=SURF):
    pts = []
    for V in hulls:
        h = trimesh.convex.convex_hull(V)
        n = max(8, int(np.ceil(h.area / pitch ** 2)))
        pts.append(trimesh.sample.sample_surface_even(h, n, seed=0)[0]); pts.append(V)
    return np.vstack(pts)


class Hulls:
    def __init__(self, hulls):
        self.V = [np.asarray(V, float) for V in hulls]
        self.EQ = [ConvexHull(V).equations for V in self.V]
        self.lo = np.array([V.min(0) for V in self.V]); self.hi = np.array([V.max(0) for V in self.V])
        self.LO, self.HI = self.lo.min(0), self.hi.max(0)

    def depth(self, X):
        """Per point: depth inside the union (max over containing hulls of the distance to that hull's boundary; a lower
        bound on the union depth), -1 if outside every hull."""
        out = np.full(len(X), -1.0)
        for k, eq in enumerate(self.EQ):
            sel = np.flatnonzero(np.all(X > self.lo[k], 1) & np.all(X < self.hi[k], 1))
            if len(sel):
                v = X[sel] @ eq[:, :3].T + eq[:, 3]
                mx = v.max(1); ins = mx <= 1e-12
                if ins.any():
                    s = sel[ins]; out[s] = np.maximum(out[s], -mx[ins])
        return out


def solid_grid(hulls, pitch=PITCH_OV):
    H = Hulls(hulls)
    ax = [np.arange(H.LO[k] + pitch / 2, H.HI[k], pitch) for k in range(3)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    return G[H.depth(G) >= 0]


def clip(V, n, c):
    """Convex hull of V intersected with n.x >= c (n unit); None if empty, < DEBRIS_M3 or thinner than a THIN_M ball.
    (interaction_carve.clip's method: Chebyshev centre by LP, then the half-space intersection.)"""
    eq = ConvexHull(V).equations
    H = np.vstack([eq, np.r_[-n, c][None]])                        # -n.x + c <= 0
    A, b = H[:, :3], -H[:, 3]; nrm = np.linalg.norm(A, axis=1)
    res = linprog(np.r_[0, 0, 0, -1.0], A_ub=np.c_[A, nrm], b_ub=b, bounds=[(None, None)] * 3 + [(0, None)])
    if not res.success or res.x[3] < THIN_M:
        return None
    P = HalfspaceIntersection(H, res.x[:3]).intersections
    try:
        h = ConvexHull(P)
    except Exception:
        return None
    if h.volume < DEBRIS_M3:
        return None
    return P[h.vertices]


def write_obj(path, V):
    h = trimesh.convex.convex_hull(np.asarray(V, float))
    with open(path, 'w') as f:
        for v in h.vertices:
            f.write(f'v {v[0]:.9g} {v[1]:.9g} {v[2]:.9g}\n')
        for t in h.faces:
            f.write(f'f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n')


def stats(x):
    x = np.asarray(x, float)
    if not len(x):
        return dict(n=0, median=None, max=None, min=None)
    return dict(n=int(len(x)), median=round(float(np.median(x)), 3), max=round(float(x.max()), 3),
                min=round(float(x.min()), 3), q90=round(float(np.quantile(x, 0.9)), 3))


def main():
    cfg = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    t0 = time.time()
    R = load_ref(cfg['ref']); sup = support(cfg['usda']); top = sup['top_z']
    names = R['names']; tgt = cfg['target']; io = names.index(tgt); nf = R['nf']; T = R['T']
    O = {}
    for n in names:
        oc = cfg['objects'][n]
        m = load_mesh(oc['visual']); hulls, src = load_pieces(oc['packed'])
        surf_vis = trimesh.sample.sample_surface_even(m, int(np.ceil(m.area / SURF ** 2)), seed=0)[0]
        O[n] = dict(mesh=m, hulls=hulls, src=src, tree_vis=cKDTree(surf_vis), surf_p=hull_surface(hulls),
                    V=np.vstack(hulls), visual_md5=md5(oc['visual']))
        O[n]['tree_p'] = cKDTree(O[n]['surf_p']); O[n]['H'] = Hulls(hulls)
    o = O[tgt]
    # ---------------------------------------------------------------- per-frame quantities (packed geometry only)
    hand_min = {n: np.zeros(nf) for n in names}
    low = np.zeros(nf); disp = np.zeros(nf)
    pair_d = {n: np.full(nf, np.inf) for n in names if n != tgt}
    rel_disp = {n: np.zeros(nf) for n in names if n != tgt}
    for f in range(nf):
        for j, n in enumerate(names):
            Ti = np.linalg.inv(T[f, j])
            hand_min[n][f] = O[n]['tree_vis'].query(tf(Ti, R['hands'][f]))[0].min()
        Vw = tf(T[f, io], o['V']); low[f] = Vw[:, 2].min()
        g = f - 1 if f > 0 else 1
        disp[f] = np.linalg.norm(Vw - tf(T[g, io], o['V']), axis=1).max()
        for j, n in enumerate(names):
            if n == tgt:
                continue
            X = tf(np.linalg.inv(T[f, j]) @ T[f, io], o['surf_p'])
            pair_d[n][f] = O[n]['tree_p'].query(X)[0].min()
            Ho = O[n]['H']
            if (Ho.depth(X[np.all((X > Ho.LO) & (X < Ho.HI), 1)]) >= 0).any():
                pair_d[n][f] = 0.0
            rel = lambda k: (np.linalg.inv(T[k, io]) @ T[k, j])[:3, 3]
            rel_disp[n][f] = np.linalg.norm(rel(f) - rel(g))
    pen_packed = (top - low) * 1e3                                  # mm, > 0 into the table
    H30 = hand_min[tgt] >= HAND_M
    on_table = np.abs(low - top) <= NEAR_M
    rank = lambda n: RECV_ORDER.index(n) if n in RECV_ORDER else 99
    not_held = np.ones(nf, bool)
    for n in pair_d:
        if rank(n) < rank(tgt):
            not_held &= pair_d[n] > TOUCH_M
    static = disp < STATIC_M
    rest_runs = runs(H30 & on_table & not_held & static)
    rest = run_mask(rest_runs, nf); F = np.flatnonzero(rest)
    # partner-rest frames (G2)
    prest = {}
    for j, n in enumerate(names):
        if n == tgt:
            continue
        rs = runs((hand_min[n] >= HAND_M) & (rel_disp[n] < STATIC_M) & (pair_d[n] <= TOUCH_M))
        prest[n] = rs
    frames = dict(set=cfg['set'], ref=cfg['ref'], ref_md5=R['md5'], seq=R['seq'], names=names, target=tgt, frames=nf,
                  support=sup, rest_runs=rest_runs, n_rest=int(len(F)), partner_rest_runs=prest,
                  per_frame=dict(pen_packed_mm=np.round(pen_packed, 2).tolist(), H30=H30.tolist(),
                                 on_table=on_table.tolist(), not_held=not_held.tolist(),
                                 disp_mm=np.round(disp * 1e3, 2).tolist(),
                                 hand_min_mm={n: np.round(np.minimum(v, 9.99) * 1e3, 1).tolist() for n, v in hand_min.items()},
                                 pair_dist_mm={n: np.round(np.minimum(v, 9.99) * 1e3, 1).tolist() for n, v in pair_d.items()},
                                 rel_disp_mm={n: np.round(v * 1e3, 2).tolist() for n, v in rel_disp.items()}))
    json.dump(frames, open(f'{out}/frames.json', 'w'))
    rep = dict(set=cfg['set'], ref=cfg['ref'], ref_md5=R['md5'], target=tgt, support=sup, rest_runs=rest_runs,
               n_rest=int(len(F)), partner_rest_runs=prest, packed_count=len(o['hulls']),
               packed_count_listed=cfg.get('packed_count'), visual_md5={n: O[n]['visual_md5'] for n in names},
               packed_src={n: cfg['objects'][n]['packed'] for n in names}, gates_file='GATES.md (0b8291f)')
    if not len(F):
        rep['verdict'] = 'no T-rest frames: nothing measured'
        json.dump(rep, open(f'{out}/rebase.json', 'w'), indent=1); print(json.dumps(rep)[:2000]); return
    # ---------------------------------------------------------------- shift and axis
    U = np.array([T[f, io, :3, :3].T @ np.array([0, 0, 1.0]) for f in F])
    u = U.mean(0); u /= np.linalg.norm(u)
    dev = np.degrees(np.arccos(np.clip(U @ u, -1, 1)))
    d_mm = float(np.median(pen_packed[F]))
    rep.update(u=np.round(u, 6).tolist(), u_dev_deg=stats(dev), d_mm=round(d_mm, 3),
               pen_packed_signed_mm=stats(pen_packed[F]), G1_packed=stats(np.maximum(pen_packed[F], 0)))
    m_u = float((o['V'] @ u).min())
    status = 'build' if D_MIN_MM <= d_mm <= D_MAX_MM else ('not needed (d < 1 mm)' if d_mm < D_MIN_MM else 'no candidate (d > 12 mm)')
    rep['status'] = status
    cands = {}
    if status == 'build':
        d = d_mm * 1e-3
        cands['a'] = [V + d * u for V in o['hulls']]
        cb, kept, cut, dropped = [], 0, 0, 0
        for V in o['hulls']:
            s = V @ u
            if s.min() >= m_u + d - 1e-12:
                cb.append(V); kept += 1
            elif s.max() <= m_u + d + 1e-12:
                dropped += 1
            else:
                P = clip(V, u, m_u + d)
                if P is None:
                    dropped += 1
                else:
                    cb.append(P); cut += 1
        cands['b'] = cb
        rep['rule_b'] = dict(base_level_m=round(m_u, 6), plane_m=round(m_u + d, 6), pieces_untouched=kept,
                             pieces_cut=cut, pieces_dropped=dropped)
    vol = lambda hs: round(sum(ConvexHull(V).volume for V in hs) * 1e6, 2)
    rep['packed_cm3'] = vol(o['hulls'])
    # ---------------------------------------------------------------- G1 / G2 / G6 / convexity per candidate
    qgrid = {n: solid_grid(O[n]['hulls']) for n in prest}

    def g2(hulls):
        H = Hulls(hulls); res = {}
        for n, rs in prest.items():
            fr = np.flatnonzero(run_mask(rs, nf)); jq = names.index(n); vs, ds = [], []
            for f in fr:
                X = tf(np.linalg.inv(T[f, io]) @ T[f, jq], qgrid[n])
                X = X[np.all((X > H.LO) & (X < H.HI), 1)]
                dep = H.depth(X) if len(X) else np.zeros(0)
                vs.append(float((dep >= 0).sum()) * PITCH_OV ** 3 * 1e6); ds.append(float(dep.max()) * 1e3 if len(dep) and dep.max() >= 0 else 0.0)
            res[n] = dict(frames=int(len(fr)), overlap_cm3=stats(vs), depth_mm=stats(ds),
                          per_frame=dict(zip(map(int, fr), [round(v, 3) for v in vs])))
        return res

    def evaluate(hulls):
        Vall = np.vstack(hulls)
        pen = np.array([(top - tf(T[f, io], Vall)[:, 2].min()) * 1e3 for f in range(nf)])
        conv = []
        for V in hulls:
            h = ConvexHull(V)
            conv.append(bool(len(h.vertices) == len(np.unique(np.round(V, 12), axis=0)) or
                             abs(h.volume - trimesh.convex.convex_hull(V).volume) < 1e-9))
        return dict(count=len(hulls), cm3=vol(hulls), G1=stats(np.maximum(pen[F], 0)), pen_signed=stats(pen[F]),
                    pen_all_frames_mm=np.round(pen, 2).tolist(), convex_all=bool(all(conv)), G2=g2(hulls))
    ev = {'packed': evaluate(o['hulls'])}
    for k, hs in cands.items():
        ev[k] = evaluate(hs)
        os.makedirs(f'{out}/cand_{k}/{tgt}', exist_ok=True)
        for i, V in enumerate(hs):
            write_obj(f'{out}/cand_{k}/{tgt}/piece_{i:02d}.obj', V)
    for k in ev:
        e = ev[k]; g1 = e['G1']
        e['G1_pass'] = bool(g1['median'] <= 1.0 and g1['max'] <= 3.0)
        e['G6_pass'] = bool(e['count'] <= len(o['hulls']))
        if k != 'packed':
            e['G2_pass'] = all(
                (x['frames'] == 0) or (x['overlap_cm3']['median'] <= ev['packed']['G2'][n]['overlap_cm3']['median'] + 0.5
                                       and x['overlap_cm3']['max'] <= ev['packed']['G2'][n]['overlap_cm3']['max'] + 0.5)
                for n, x in e['G2'].items())
            e['G2_vacuous'] = all(x['frames'] == 0 for x in e['G2'].values())
    rep['eval'] = ev
    rep['secs'] = round(time.time() - t0, 1)
    json.dump(rep, open(f'{out}/rebase.json', 'w'), indent=1)
    brief = {k: dict(count=v['count'], cm3=v['cm3'], G1=v['G1'], G1_pass=v['G1_pass'], G6_pass=v['G6_pass'],
                     G2={n: (x['frames'], x['overlap_cm3']['median'], x['overlap_cm3']['max'], x['depth_mm']['max'])
                         for n, x in v['G2'].items()}, G2_pass=v.get('G2_pass'), convex=v['convex_all'])
             for k, v in ev.items()}
    print(json.dumps(dict(set=cfg['set'], n_rest=rep['n_rest'], rest_runs=rest_runs, d_mm=rep['d_mm'], u=rep['u'],
                          u_dev=rep['u_dev_deg'], status=status, rule_b=rep.get('rule_b'), eval=brief,
                          partner_rest_runs=prest, secs=rep['secs']), indent=None))


if __name__ == '__main__':
    main()
