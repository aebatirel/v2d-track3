#!/usr/bin/env python3
"""GT-free gross-error screen of object tracks / references (31 Oct 2026). Inference side only.

Reads our perception poses (poses.npz: world_T_cam, cam_T_<obj>), our FlashCHORD references (refs/<variant>/...
parquet: object_body_position / object_body_wxyz in the table frame), our table frames (table_frame.npz from mkref:
T_table_from_world, plane_n, plane_d, table_z) or a depth-audit global plane (audit.json, public calibration), and our
meshes. It never opens a dataset parquet, mocap, a scan or a score file (refine.assert_inference_input on every
input except the reference parquet, which must sit under refs/<variant>/ and have no observation.* column).

Per object, over the whole episode (frame = video frame):
  jump      per-frame step of the centre of mass (cm) and of the orientation (deg; for cups the symmetry axis only)
  below     lowest mesh vertex below the table plane (cm, any frame)
  float     static frames, nothing under the object: lowest vertex above the table plane (cm)
  tilt      static frames, on the table (|lowest vertex| < 1.5 cm), nothing under it: angle between the table-down
            direction in the object frame and the nearest stable convex-hull facet normal (facets >= 2 % of hull area)
  pen       2-object episodes, every STRIDE-th frame: deepest penetration of 400 surface samples of one object into the
            other's mesh (cm; trimesh signed distance, both directions)
  refperc   reference only: per-frame distance of the reference pose from the feeding perception pose (cm, deg)
Usage: python3 -I screen.py MANIFEST.json OUT.json [--stride 5]
MANIFEST: list of {"ep", "split", "kind": "perc"|"ref", "poses", "table" | "plane": {"n","d"}, "ref", "meshes",
                    "mesh_over": {name: path}}"""
import argparse
import json
import os
import sys
import time

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine  # noqa: E402  (assert_inference_input)

CUPS = {'blue_cup', 'beige_cup'}
T0 = time.time()


def log(*a):
    print(f'[screen {time.time() - T0:6.1f}s]', *a, flush=True)


def assert_ref(path):
    import pyarrow.parquet as pq
    low = os.path.realpath(path).lower()
    parts = low.split('/')
    if 'refs' not in parts[:-1] or any(s in low for s in ('observation', 'quarantine_gt', '/gt/', 'calib_gt', 'score')):
        raise AssertionError(f'refusing reference {path}')
    cols = pq.read_schema(path).names
    if any(c.startswith('observation') for c in cols) or 'object_body_position' not in cols:
        raise AssertionError(f'refusing reference {path}: {cols[:8]}')
    return path


def quat_wxyz_to_R(q):
    from scipy.spatial.transform import Rotation as Rot
    return Rot.from_quat(np.c_[q[:, 1:], q[:, :1]]).as_matrix()


class Mesh:
    def __init__(self, name, path):
        import trimesh
        self.name = name
        self.m = trimesh.load(path, force='mesh')
        self.V = np.asarray(self.m.vertices, float)
        self.com = np.asarray(self.m.center_mass if self.m.is_watertight else self.m.centroid, float)
        rng = np.random.default_rng(7)
        self.S = np.asarray(self.m.sample(400, seed=7) if 'seed' in self.m.sample.__code__.co_varnames
                            else self.m.sample(400), float)
        del rng
        # symmetry axis for cups: the principal axis whose moment differs most from the other two
        I = np.asarray(self.m.moment_inertia, float)
        w, U = np.linalg.eigh(I)
        k = int(np.argmax([min(abs(w[i] - w[j]) for j in range(3) if j != i) for i in range(3)]))
        self.axis = U[:, k]
        # stable facets of the convex hull
        h = self.m.convex_hull
        fa = np.asarray(h.facets_area) if len(h.facets) else np.zeros(0)
        normals = [np.asarray(h.facets_normal)[i] for i in range(len(fa)) if fa[i] >= 0.02 * h.area]
        # single big triangles that are not part of a facet group
        tri_area = np.asarray(h.area_faces)
        in_facet = np.zeros(len(h.faces), bool)
        for f in h.facets:
            in_facet[f] = True
        normals += [np.asarray(h.face_normals)[i] for i in np.where((~in_facet) & (tri_area >= 0.02 * h.area))[0]]
        self.facets = np.array(normals) if normals else np.zeros((0, 3))


def load_plane(item):
    if 'table' in item:
        Z = np.load(refine.checked(item['table']), allow_pickle=False)
        n, d = np.asarray(Z['plane_n'], float), float(Z['plane_d'])
        A = np.asarray(Z['T_table_from_world'], float)
        tz = float(Z['table_z']) if 'table_z' in Z else 0.6
        return n, d, A, tz
    p = item['plane']
    return np.asarray(p['n'], float), float(p['d']), None, None


def load_perc(path):
    P = np.load(refine.checked(path), allow_pickle=False)
    W = np.asarray(P['world_T_cam'], float)
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    O = np.stack([W @ np.asarray(P[f'cam_T_{n}'], float) for n in names], 1)  # (T,B,4,4) world
    return names, O


def load_ref(path, A):
    import pyarrow.parquet as pq
    t = pq.read_table(assert_ref(path), columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    rn = [str(n) for n in t.column('object_body_names')[0].as_py()]
    pos = np.array(t.column('object_body_position')[0].as_py(), float).reshape(-1, len(rn), 3)
    q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(-1, len(rn), 4)
    T = len(pos)
    O = np.tile(np.eye(4), (T, len(rn), 1, 1))
    for b in range(len(rn)):
        O[:, b, :3, :3] = quat_wxyz_to_R(q[:, b])
        O[:, b, :3, 3] = pos[:, b]
    Ainv = np.linalg.inv(A)
    return rn, np.einsum('ij,tbjk->tbik', Ainv, O)  # table frame -> world


def ang(Ra, Rb):
    c = (np.einsum('...ij,...ij->...', Ra, Rb) - 1) / 2
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def axis_ang(Ra, Rb, ax):
    a, b = Ra @ ax, Rb @ ax
    return np.degrees(np.arccos(np.clip((a * b).sum(-1), -1, 1)))


def static_mask(O, com, still_cm=0.5, still_deg=2.0):
    from scipy.ndimage import uniform_filter1d
    c = O[:, :3, :3] @ com + O[:, :3, 3]
    v = np.r_[0.0, np.linalg.norm(np.diff(uniform_filter1d(c, 3, axis=0), axis=0), axis=1) * 100]
    w = uniform_filter1d(np.r_[0.0, ang(O[1:, :3, :3], O[:-1, :3, :3])], 3)
    st = (v < still_cm) & (w < still_deg)
    # keep runs >= 5 frames
    out = np.zeros_like(st)
    t = 0
    while t < len(st):
        if st[t]:
            u = t
            while u < len(st) and st[u]:
                u += 1
            if u - t >= 5:
                out[t:u] = True
            t = u
        else:
            t += 1
    return out


def footprint_over(Wj_com, Wk_V, n):
    """True if j's COM projects (along n) inside k's projected convex footprint."""
    from scipy.spatial import ConvexHull
    e1 = np.cross(n, [1.0, 0, 0] if abs(n[0]) < 0.9 else [0, 1.0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    try:
        ch = ConvexHull(np.c_[Wk_V @ e1, Wk_V @ e2])
    except Exception:  # noqa: BLE001
        return False
    c2 = np.array([Wj_com @ e1, Wj_com @ e2])
    return bool(np.min(-(ch.equations[:, :2] @ c2 + ch.equations[:, 2])) >= 0)


def screen_item(item, meshes, stride):
    n, d, A, tz = load_plane(item)
    if item['kind'] == 'perc':
        names, O = load_perc(item['poses'])
    else:
        names, O = load_ref(item['ref'], A)
        pn, PO = load_perc(item['poses'])
        PO = PO[:, [pn.index(x) for x in names]]
    T, B = O.shape[:2]
    M = [meshes[x] for x in names]
    res = dict(ep=item['ep'], split=item['split'], kind=item['kind'], names=names, T=T, objects={})
    # heights of every object's lowest vertex and COM, per frame
    hmin = np.zeros((T, B)); comw = np.zeros((T, B, 3))
    for b in range(B):
        Vw = np.einsum('tij,vj->tvi', O[:, b, :3, :3], M[b].V) + O[:, b, None, :3, 3]
        hmin[:, b] = (Vw @ n).min(1) + d
        comw[:, b] = O[:, b, :3, :3] @ M[b].com + O[:, b, :3, 3]
    # is j over k (COM inside k's footprint, j's bottom above k's bottom)? per frame, every 1 frame (cheap enough)
    over = np.zeros((T, B), bool)
    for t in range(T):
        for j in range(B):
            for k in range(B):
                if k != j and hmin[t, j] > hmin[t, k] + 0.002:
                    Vk = (O[t, k, :3, :3] @ M[k].V.T).T + O[t, k, :3, 3]
                    if footprint_over(comw[t, j], Vk, n):
                        over[t, j] = True
    for b in range(B):
        mb = M[b]; Ob = O[:, b]
        step_cm = np.r_[0, np.linalg.norm(np.diff(comw[:, b], axis=0), axis=1) * 100]
        if names[b] in CUPS:
            step_deg = np.r_[0, axis_ang(Ob[1:, :3, :3], Ob[:-1, :3, :3], mb.axis)]
        else:
            step_deg = np.r_[0, ang(Ob[1:, :3, :3], Ob[:-1, :3, :3])]
        st = static_mask(Ob, mb.com)
        free_rest = st & ~over[:, b]
        h = hmin[:, b] * 100
        on_tab = free_rest & (np.abs(h) < 1.5)
        tilt = np.full(T, np.nan)
        if len(mb.facets):
            down_obj = -np.einsum('tji,j->ti', Ob[:, :3, :3], n)  # table-down direction in the object frame
            cosv = down_obj @ mb.facets.T
            tilt = np.degrees(np.arccos(np.clip(cosv.max(1), -1, 1)))
        o = dict(
            jump_cm_max=float(step_cm.max()), jump_cm_argmax=int(step_cm.argmax()),
            jump_deg_max=float(step_deg.max()), jump_deg_argmax=int(step_deg.argmax()),
            n_step_gt3cm=int((step_cm > 3).sum()), n_step_gt5cm=int((step_cm > 5).sum()),
            n_step_gt20deg=int((step_deg > 20).sum()),
            below_cm_min=float(h.min()), below_cm_argmin=int(h.argmin()), n_below_3cm=int((h < -3).sum()),
            h0_cm=float(h[0]),
            static_frames=int(st.sum()), free_rest_frames=int(free_rest.sum()), on_table_rest_frames=int(on_tab.sum()),
            float_rest_cm_p50=float(np.median(h[free_rest])) if free_rest.any() else None,
            float_rest_cm_max=float(h[free_rest].max()) if free_rest.any() else None,
            n_float_rest_gt3cm=int((h[free_rest] > 3).sum()),
            tilt_rest_deg_p50=float(np.nanmedian(tilt[on_tab])) if on_tab.any() else None,
            tilt_rest_deg_max=float(np.nanmax(tilt[on_tab])) if on_tab.any() else None,
            n_tilt_rest_gt20=int((tilt[on_tab] > 20).sum()) if on_tab.any() else 0,
            tilt0_deg=float(tilt[0]), h_traj_cm=[round(float(x), 2) for x in h[::stride]],
        )
        if item['kind'] == 'ref':
            dp = np.linalg.norm(comw[:, b] - (PO[:, b, :3, :3] @ mb.com + PO[:, b, :3, 3]), axis=1) * 100
            dr = axis_ang(Ob[:, :3, :3], PO[:, b, :3, :3], mb.axis) if names[b] in CUPS else ang(Ob[:, :3, :3], PO[:, b, :3, :3])
            o.update(refperc_cm_max=float(dp.max()), refperc_cm_argmax=int(dp.argmax()), refperc_cm_p50=float(np.median(dp)),
                     refperc_deg_max=float(dr.max()), refperc_deg_p50=float(np.median(dr)),
                     n_refperc_gt5cm=int((dp > 5).sum()), n_refperc_gt20deg=int((dr > 20).sum()),
                     refperc_cm_traj=[round(float(x), 2) for x in dp[::stride]])
        res['objects'][names[b]] = o
    # penetration
    if B == 2:
        import trimesh
        pens = []
        for t in range(0, T, stride):
            pm = []
            for j, k in ((0, 1), (1, 0)):
                Sj = (O[t, j, :3, :3] @ M[j].S.T).T + O[t, j, :3, 3]
                Rk, pk = O[t, k, :3, :3], O[t, k, :3, 3]
                Sk = (Sj - pk) @ Rk  # into k's frame
                # cheap reject: bounding box
                lo, hi = M[k].V.min(0) - 0.001, M[k].V.max(0) + 0.001
                inb = ((Sk > lo) & (Sk < hi)).all(1)
                if not inb.any():
                    pm.append(0.0); continue
                sd = trimesh.proximity.signed_distance(M[k].m, Sk[inb])  # > 0 inside
                pm.append(float(max(0.0, sd.max()) * 100))
            pens.append((t, pm[0], pm[1]))
        P = np.array(pens)
        res['pen'] = dict(frames=P[:, 0].astype(int).tolist(), a_in_b_cm=P[:, 1].round(2).tolist(),
                          b_in_a_cm=P[:, 2].round(2).tolist(), max_cm=float(P[:, 1:].max()),
                          argmax_frame=int(P[np.unravel_index(P[:, 1:].argmax(), P[:, 1:].shape)[0], 0]),
                          share_gt2cm=float((P[:, 1:].max(1) > 2).mean()), share_gt1cm=float((P[:, 1:].max(1) > 1).mean()))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest'); ap.add_argument('out'); ap.add_argument('--stride', type=int, default=5)
    a = ap.parse_args()
    items = json.load(open(a.manifest))
    cache = {}
    out = []
    for it in items:
        mdir = it['meshes']
        names = None
        res = None
        try:
            if it['kind'] == 'perc':
                names = [k[6:] for k in np.load(refine.checked(it['poses'])).files if k.startswith('cam_T_')]
            else:
                import pyarrow.parquet as pq
                names = [str(x) for x in pq.read_table(assert_ref(it['ref']), columns=['object_body_names'])
                         .column('object_body_names')[0].as_py()]
            meshes = {}
            for x in names:
                p = it.get('mesh_over', {}).get(x, os.path.join(mdir, f'{x}.glb'))
                if p not in cache:
                    cache[p] = Mesh(x, p)
                meshes[x] = cache[p]
            res = screen_item(it, meshes, a.stride)
            log(it['split'], it['ep'], it['kind'], 'ok')
        except Exception as ex:  # noqa: BLE001
            res = dict(ep=it['ep'], split=it['split'], kind=it['kind'], error=repr(ex)[:400])
            log(it['split'], it['ep'], it['kind'], 'ERROR', repr(ex)[:300])
        res['inputs'] = {k: v for k, v in it.items() if k in ('poses', 'ref', 'table', 'plane', 'meshes', 'mesh_over')}
        out.append(res)
    json.dump(dict(tool='evalgross screen.py', time_utc=time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
                   stride=a.stride, items=out), open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
