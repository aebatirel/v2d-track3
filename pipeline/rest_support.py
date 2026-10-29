"""Support rule (mesh pipeline v5, docs/mesh-v5-spec-draft.md section 6; port of the interaction-meshes prototype
minimal/auto_rest.py, with the spec's acceptance checks). An object seen resting on the table without a hand must be
statically stable in that pose; if our mesh is not (a rounded, unobserved underside), its underside is flattened along
that rest's up (flatten_base.flatten, 8 mm), and the change is kept only if every check passes. Inputs are ours only:
the mesh (body frame), our tracks, our MediaPipe hands, the table plane per frame from our own depth (recon_mesh obs
grids store them), and the object's evidence grid. No scan, no mocap.

1. Unassisted rests: recon_mesh.rest_frames (still and hand-far for >= 15 frames; see its notes on two deviations from
   the spec), the robust plane of a run = the median of its per-frame planes, the mesh's lowest point within +-20 mm.
2. Rests clustered by their up vector in the object frame (10 deg).
3. Stability: snap to the hull facet within 5 deg of the observed up; stable if the centre-of-mass margin is >= 2 mm
   and the support area >= 1 cm2 (else the hull vertices within 1.5 mm of the lowest point).
4. Unstable: flatten(up, 8 mm); accept only if (i) stable at that rest, (ii) no other observed rest becomes unstable,
   (iii) solid removed inside strongly observed voxels (W4 >= 3, mean4 < 0) <= 0.5 cm3, (iv) the X flip check against
   the unflattened mesh passes, (v) registering the flattened mesh to the unflattened one moves it <= 2 mm and 2 deg.
5. The result serves both the submitted mesh and the collision copy. The spoon is excluded (a template). An object with
   no observed unassisted rest is never edited.
[H] hull stability predicts the simulator; falsified if an accepted mesh tilts > 5 deg in tools/replay_rest.py.
Usage: python rest_support.py MESH_FULL.glb OUT.glb OBJECT --ep POSES HANDS PLANES [--ep ...] [--grid GRID.npz]
       PLANES: an obs grid (its plane_ep<k> arrays, k = the --ep order in that grid) as GRID.npz:k, or a mkref
       table_frame.npz (one plane), or 'nx,ny,nz,c' (world frame, n up).
"""
import argparse, json, os, sys, tempfile

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatten_base import flatten  # noqa: E402

MARGIN_MM, AREA_CM2, SNAP_DEG, HTOL, DEPTH = 2.0, 1.0, 5.0, 0.02, 0.008


def _margin(V_sup, com, up):
    e1 = np.cross(up, [1, 0, 0]); e1 = e1 if np.linalg.norm(e1) > 0.1 else np.cross(up, [0, 1, 0])
    e1 /= np.linalg.norm(e1); e2 = np.cross(up, e1)
    S = np.c_[V_sup @ e1, V_sup @ e2]; c2 = np.array([com @ e1, com @ e2])
    try:
        ch = ConvexHull(S); return float(np.min(-(ch.equations[:, :2] @ c2 + ch.equations[:, 2]))), float(ch.volume)
    except Exception:
        return (-float(np.min(np.linalg.norm(S - c2, axis=1))) if len(S) else -1.0), 0.0


def stability(m, up, snap_deg=SNAP_DEG):
    """Static stability of mesh m resting with object-frame up UP (prototype rule, spec thresholds)."""
    up = np.asarray(up, float); up /= np.linalg.norm(up)
    hull = m.convex_hull; com = m.center_mass if m.is_watertight else m.centroid; best = None
    facets = [list(f) for f in hull.facets]
    rest_faces = set(range(len(hull.faces))) - set(np.concatenate(hull.facets).tolist() if len(hull.facets) else [])
    for g in facets + [[i] for i in rest_faces]:
        nf = hull.face_normals[g[0]]; ang = np.degrees(np.arccos(np.clip(-nf @ up, -1, 1)))
        if ang > snap_deg:
            continue
        u = -nf; V = hull.vertices[np.unique(hull.faces[g])]; h0 = float((V @ u).min())
        mg, area = _margin(V, com, u)
        if best is None or mg > best[0]:
            best = (mg, area, float(com @ u - h0), ang)
    if best is None:
        V = np.asarray(hull.vertices); h = V @ up; h0 = h.min(); mg, area = _margin(V[h < h0 + 0.0015], com, up)
        best = (mg, area, float(com @ up - h0), -1.0)
    mg, area, hc, ang = best
    return dict(margin_mm=round(mg * 1000, 1), area_cm2=round(area * 1e4, 2), com_h_mm=round(hc * 1000, 1),
                tip_deg=round(float(np.degrees(np.arctan2(mg, hc))), 1), facet_deg=round(ang, 1),
                stable=bool(mg * 1000 >= MARGIN_MM and area * 1e4 >= AREA_CM2))


def _planes(spec, N):
    """Per-frame world planes (N, 4): n . x + c = 0, n up."""
    if ':' in spec and spec.split(':')[0].endswith('.npz'):
        g, k = spec.rsplit(':', 1); P = np.load(g)[f'plane_ep{k}']
        return P[:N] if len(P) >= N else np.vstack([P, np.full((N - len(P), 4), np.nan)])
    if spec.endswith('.npz'):
        z = np.load(spec); n = np.asarray(z['plane_n'], float).ravel()[:3]; c = float(np.asarray(z['plane_d']).ravel()[0])
        return np.tile([*n, c], (N, 1))
    v = [float(x) for x in spec.split(',')]
    return np.tile(v, (N, 1))


def observed_rests(m, obj, episodes):
    """[(episode index, (t0, t1), object-frame up, lowest point above the plane m)] of the unassisted rests."""
    import recon_mesh as rm
    surf = trimesh.sample.sample_surface(m, 20000, seed=0)[0]; V = np.asarray(m.vertices); out = []
    for e, (poses, hands, planes) in enumerate(episodes):
        P = np.load(poses); W = P['world_T_cam'].astype(float); T = P[f'cam_T_{obj}'].astype(float); N = min(len(W), len(T))
        rest = rm.rest_frames(T[:N], W[:N], None if hands == '-' else hands, surf)
        PL = _planes(planes, N); d = np.diff(np.r_[0, rest.astype(int), 0])
        for t0, t1 in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]):
            pl = np.nanmedian(PL[t0:t1], axis=0)
            if not np.all(np.isfinite(pl)):
                continue
            n = pl[:3] / np.linalg.norm(pl[:3]); c = pl[3] / np.linalg.norm(pl[:3])
            WO = [W[t] @ T[t] for t in range(t0, t1)]
            hmin = float(np.median([((V @ w[:3, :3].T + w[:3, 3]) @ n + c).min() for w in WO]))
            if abs(hmin) > HTOL:
                continue
            up = np.mean([w[:3, :3].T @ n for w in WO], axis=0); up /= np.linalg.norm(up)
            out.append((e, (int(t0), int(t1)), up, hmin))
    return out


def removed_observed_cm3(grid, before, after):
    """Solid removed by the edit inside strongly observed inside voxels (W4 >= 3 and mean4 < 0) of the evidence grid."""
    z = np.load(grid); W4 = z['W4']; m4 = np.where(W4 > 0, z['S4'] / np.maximum(W4, 1), 0)
    ijk = np.argwhere((W4 >= 3) & (m4 < 0))
    if not len(ijk):
        return 0.0
    X = np.asarray(z['lo']) + (ijk + 0.5) * float(z['voxel'])
    gone = before.contains(X) & ~after.contains(X)
    return round(float(gone.sum()) * float(z['voxel']) ** 3 * 1e6, 3)


def support_rule(m, obj, episodes, grid=None, kit_ok=True):
    """(mesh, report). episodes = [(poses, hands, planes spec)]."""
    rep = dict(obj=obj, rests=[], clusters=[])
    if obj == 'wooden_spoon':
        rep['skipped'] = 'spoon: a template (spec section 9)'; return m, rep
    rests = observed_rests(m, obj, episodes)
    rep['rests'] = [dict(ep=e, frames=f, up=np.round(u, 4).tolist(), hmin_cm=round(h * 100, 2)) for e, f, u, h in rests]
    if not rests:
        rep['skipped'] = 'no observed unassisted rest'; return m, rep
    clusters = []
    for e, f, u, h in rests:
        for cl in clusters:
            if np.degrees(np.arccos(np.clip(cl['up'] @ u, -1, 1))) < 10:
                cl['segs'].append((e, f)); cl['ups'].append(u); cl['up'] = np.mean(cl['ups'], 0) / np.linalg.norm(np.mean(cl['ups'], 0)); break
        else:
            clusters.append(dict(up=u, ups=[u], segs=[(e, f)]))
    cur = m
    for cl in clusters:
        st0 = stability(cur, cl['up']); rec = dict(up=np.round(cl['up'], 4).tolist(), segs=cl['segs'], before=st0)
        if not st0['stable']:
            f, nmov = flatten(cur, cl['up'], DEPTH); st1 = stability(f, cl['up'])
            chk = dict(i_stable=st1['stable'],
                       ii_others_stable=all(stability(f, o['up'])['stable'] or not stability(cur, o['up'])['stable']
                                            for o in clusters if o is not cl))
            if grid:
                chk['iii_removed_observed_cm3'] = removed_observed_cm3(grid, cur, f); chk['iii'] = chk['iii_removed_observed_cm3'] <= 0.5
            else:
                chk['iii'] = None                                        # not checked: no grid given
            if kit_ok:
                import mesh_gates
                with tempfile.TemporaryDirectory() as td:
                    a, b = f'{td}/flat.glb', f'{td}/base.glb'; f.export(a); cur.export(b)
                    x = mesh_gates.flip_check(a, b, obj); g6 = mesh_gates.registration_move(a, b, obj)
                chk.update(iv_xflips=x['xflips'], iv=x['pass'], v_rot_max=g6['rot_max'], v_off_max_mm=g6['off_max'], v=g6['pass'])
            ok = chk['i_stable'] and chk['ii_others_stable'] and chk['iii'] is not False and chk.get('iv', True) and chk.get('v', True)
            rec.update(flattened=st1, vertices_moved=nmov, checks=chk, accepted=bool(ok))
            if ok:
                cur = f
        rep['clusters'].append(rec)
    rep['changed'] = cur is not m
    return cur, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mesh'); ap.add_argument('out'); ap.add_argument('object')
    ap.add_argument('--ep', nargs=3, action='append', metavar=('POSES', 'HANDS', 'PLANES'), required=True)
    ap.add_argument('--grid'); ap.add_argument('--no_kit', action='store_true', help='skip checks iv / v (tests only)')
    a = ap.parse_args()
    m = trimesh.load(a.mesh, force='mesh'); m.merge_vertices()
    out, rep = support_rule(m, a.object, [tuple(e) for e in a.ep], a.grid, not a.no_kit)
    out.export(a.out); json.dump(rep, open(os.path.splitext(a.out)[0] + '.rest.json', 'w'), indent=1, default=str)
    print(json.dumps(rep, default=str)[:3000])


if __name__ == '__main__':
    main()
