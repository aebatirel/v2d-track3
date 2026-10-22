"""Support rule prototype (minimal-carve design, scratch 2026-10-22): an object observed RESTING on the table without a
hand must be statically stable in that pose. Inputs are inference-legal only: our mesh, our tracks (poses.npz), our
MediaPipe hands (hands.npz, world frame), and the table plane fitted on our own frame-0 depth (n.x + c = 0, n up).
1. Rest segments: world displacement of the object origin < MOVE mm/frame (5-frame median) for >= MINLEN frames,
   the mesh's lowest point within HTOL of the plane, no hand joint within HAND_D of the mesh surface in >= 80 % of
   the segment's frames.
2. Up vector per segment in the object frame (R^T n); segments clustered by angle (< 10 deg).
3. Stability per cluster: support = hull vertices within 1.5 mm of the lowest point along up; margin = signed distance
   of the centre of mass (uniform density, solid) projected on the support plane to the support polygon (> 0 inside);
   tip = atan(margin / COM height).
4. If unstable (margin <= 0 or support area < 1 cm^2) at an observed unassisted rest: flatten (flatten_base.flatten, depth
   8 mm) along that up, re-check, accept only if the flattened mesh is stable there.
Usage: auto_rest.py MESH POSES.npz OBJ HANDS.npz PLANE_JSON_EP OUT.glb
"""
import json, sys
import numpy as np, trimesh
from scipy import ndimage
from scipy.spatial import ConvexHull, cKDTree
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from flatten_base import flatten

MOVE, MINLEN, HTOL, HAND_D = 2.0, 15, 0.02, 0.02


def _margin(V_sup, com, up, h0):
    e1 = np.cross(up, [1, 0, 0]); e1 = e1 if np.linalg.norm(e1) > 0.1 else np.cross(up, [0, 1, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(up, e1)
    S = np.c_[V_sup @ e1, V_sup @ e2]; c2 = np.array([com @ e1, com @ e2])
    try:
        ch = ConvexHull(S); return float(np.min(-(ch.equations[:, :2] @ c2 + ch.equations[:, 2]))), float(ch.volume)
    except Exception:
        return (-float(np.min(np.linalg.norm(S - c2, axis=1))) if len(S) else -1.0), 0.0


def stability(m, up, snap_deg=5.0):
    """Static stability of mesh M resting with world-up UP (object frame). The object settles onto the convex-hull facet
    whose outward normal is within SNAP_DEG of -UP (as a slightly tilted placement would); without such a facet the
    support is the hull vertices within 1.5 mm of the lowest point. margin > 0: centre of mass inside the support."""
    up = np.asarray(up, float); up /= np.linalg.norm(up)
    hull = m.convex_hull; com = m.center_mass if m.is_watertight else m.centroid
    best = None
    groups = [list(f) for f in hull.facets] + [[i] for i in set(range(len(hull.faces))) - set(np.concatenate(hull.facets) if len(hull.facets) else [])]
    for g in groups:
        nf = hull.face_normals[g[0]]
        ang = np.degrees(np.arccos(np.clip(-nf @ up, -1, 1)))
        if ang > snap_deg:
            continue
        u = -nf; V = hull.vertices[np.unique(hull.faces[g])]; h0 = float((V @ u).min())
        mg, area = _margin(V, com, u, h0)
        if best is None or mg > best[0]:
            best = (mg, area, float(com @ u - h0), ang)
    if best is None:                                    # no facet near: vertex support around the lowest point
        V = np.asarray(hull.vertices); h = V @ up; h0 = h.min(); mg, area = _margin(V[h < h0 + 0.0015], com, up, h0)
        best = (mg, area, float(com @ up - h0), -1.0)
    mg, area, hc, ang = best
    return dict(margin_mm=round(mg * 1000, 1), area_cm2=round(area * 1e4, 2), com_h_mm=round(hc * 1000, 1),
                tip_deg=round(float(np.degrees(np.arctan2(mg, hc))), 1), facet_deg=round(ang, 1))


def main():
    mp, pp, obj, hp, plane_ep, out = sys.argv[1:7]
    m = trimesh.load(mp, force='mesh'); m.merge_vertices()
    P = np.load(pp); W = P['world_T_cam'].astype(float); T = P[f'cam_T_{obj}'].astype(float); N = min(len(W), len(T))
    if plane_ep.endswith('.npz'):                                  # plane captured by fuse_grid.py from recon_mesh.table_plane
        z = np.load(plane_ep); n, c = np.asarray(z['plane_n'][0], float), float(z['plane_c'][0])
    else:
        tab = json.load(open('/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/census/table_support.json'))['own_depth_plane'][plane_ep]['plane0']
        n, c = np.array(tab['n']), float(tab['c'])
    WO = np.array([W[t] @ T[t] for t in range(N)])
    pos = WO[:, :3, 3]; step = np.r_[0, np.linalg.norm(np.diff(pos, axis=0), axis=1)] * 1000
    step = ndimage.median_filter(step, 5, mode='nearest')
    V = np.asarray(m.vertices); surf = trimesh.sample.sample_surface(m, 4000, seed=0)[0]
    hmin = np.array([(V @ WO[t, :3, :3].T + WO[t, :3, 3]) @ n + c for t in range(N)]).min(1)
    H = np.load(hp); hand_near = np.zeros(N, bool)
    for t in range(N):
        S = surf @ WO[t, :3, :3].T + WO[t, :3, 3]; tree = None
        for side in ('left', 'right'):
            if t < len(H[f'valid_{side}']) and H[f'valid_{side}'][t]:
                J = H[f'joints_{side}'][t]
                if np.all(np.isfinite(J)):
                    if tree is None:
                        tree = cKDTree(S)
                    if tree.query(J, k=1)[0].min() < HAND_D:
                        hand_near[t] = True
    still = (step < MOVE) & (np.abs(hmin) < HTOL)
    segs, t = [], 0
    while t < N:
        if still[t]:
            s = t
            while t < N and still[t]:
                t += 1
            if t - s >= MINLEN and hand_near[s:t].mean() <= 0.2:
                ups = np.array([WO[k, :3, :3].T @ n for k in range(s, t)]); u = ups.mean(0); u /= np.linalg.norm(u)
                segs.append(dict(frames=[s, t - 1], up=u.round(4).tolist(), hmin_cm=round(float(np.median(hmin[s:t])) * 100, 2),
                                 hand_frac=round(float(hand_near[s:t].mean()), 2)))
        else:
            t += 1
    clusters = []
    for sg in segs:
        for cl in clusters:
            if np.degrees(np.arccos(np.clip(np.dot(cl['up'], sg['up']), -1, 1))) < 10:
                cl['segs'].append(sg['frames']); break
        else:
            clusters.append(dict(up=np.array(sg['up']), segs=[sg['frames']]))
    res = dict(mesh=mp, obj=obj, segments=segs, clusters=[])
    cur = m
    for cl in clusters:
        st0 = stability(cur, cl['up']); rec = dict(up=cl['up'].round(4).tolist(), segs=cl['segs'], before=st0)
        if st0['margin_mm'] <= 0:
            f, nmov = flatten(cur, cl['up'], 0.008); st1 = stability(f, cl['up']); rec.update(flattened=st1, vertices_moved=nmov)
            if st1['margin_mm'] > 0:
                cur = f; rec['accepted'] = True
            else:
                rec['accepted'] = False
        res['clusters'].append(rec)
    cur.export(out); json.dump(res, open(out.replace('.glb', '.rest.json'), 'w'), indent=1); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
