#!/usr/bin/env python
"""B1 box-with-slot rule (RULES.md). GT-free: our library meshes + OUR ep24 reference (last frame, slot) only."""
import sys, json, numpy as np, trimesh
sys.path.insert(0, '.')
import refpose
L = '/home/user/v2d-track3/meshes/library_v3/'
OUT = 'out/boards/'
import os; os.makedirs(OUT, exist_ok=True)

def frame_and_box(nm):
    z = np.load(f'out/{nm}_thick.npz'); TH, us, vs, c, V = z['TH'], z['us'], z['vs'], z['c'], z['V']
    LO, HI = z['LO'], z['HI']
    t, w, l = V[:, 0], V[:, 1], V[:, 2]
    pos = TH > 0
    T = float(np.median(TH[pos])); mid = float(np.nanmedian(((LO + HI) / 2)[pos]))
    U, Vv = np.meshgrid(us, vs, indexing='ij')
    ulo, uhi = np.percentile(U[pos], [0.5, 99.5]); vlo, vhi = np.percentile(Vv[pos], [0.5, 99.5])
    g = us[1] - us[0]
    ulo -= g / 2; uhi += g / 2; vlo -= g / 2; vhi += g / 2      # cell centres -> cell edges
    Rf = np.c_[l, w, t]                                          # columns: board axes (u=l, v=w, s=t) in mesh frame
    centre = c + Rf @ np.array([(ulo + uhi) / 2, (vlo + vhi) / 2, mid])
    ext = np.array([uhi - ulo, vhi - vlo, T])
    return dict(T=T, mid=mid, Rf=Rf, centre=centre, ext=ext, c=c)

def box_mesh(b, grow=0.0):
    tf = np.eye(4); tf[:3, :3] = b['Rf']; tf[:3, 3] = b['centre']
    if np.linalg.det(b['Rf']) < 0:
        tf[:3, 2] *= -1
    return trimesh.creation.box(extents=b['ext'] + 2 * grow, transform=tf)

def appendages(nm, b):
    m = trimesh.load(L + nm + '.glb', force='mesh')
    s = (m.triangles_center - b['c']) @ b['Rf'][:, 2]
    k = np.abs(s - b['mid']) > b['T'] / 2 + 0.002
    return m, (m.submesh([np.where(k)[0]], append=True) if k.any() else None), int(k.sum())

def main():
    names, pos, q = refpose.load('ep24')
    B = {nm: frame_and_box(nm) for nm in names}
    boxes = {nm: box_mesh(B[nm]) for nm in names}
    info = {nm: dict(T_mm=round(B[nm]['T'] * 1e3, 2), ext_cm=[round(x * 100, 2) for x in B[nm]['ext']]) for nm in names}
    f = len(pos) - 1
    # who moved down relative to the other over the last 60 frames (world z of origins)
    dz = (pos[f, 1, 2] - pos[f, 0, 2]) - (pos[f - 60, 1, 2] - pos[f - 60, 0, 2])
    inserted = names[1] if dz < 0 else names[0]
    info['halving'] = dict(rel_dz_cm_piece2_minus_piece1=round(dz * 100, 2), inserted=inserted)
    slotted = {}
    for i, a in enumerate(names):
        o = names[1 - i]
        A = boxes[a]; Ob = box_mesh(B[o], grow=0.0005)
        # Ob in A's mesh frame at the last frame
        Tw_o = np.eye(4); Tw_o[:3, :3] = refpose.R_of(q[f, 1 - i]); Tw_o[:3, 3] = pos[f, 1 - i]
        Tw_a = np.eye(4); Tw_a[:3, :3] = refpose.R_of(q[f, i]); Tw_a[:3, 3] = pos[f, i]
        Ob_a = Ob.copy(); Ob_a.apply_transform(np.linalg.inv(Tw_a) @ Tw_o)
        col = A.intersection(Ob_a, engine='manifold')
        rec = dict(column_volume_cm3=round(float(col.volume) * 1e6, 2) if col is not None and len(col.faces) else 0.0)
        if col is None or not len(col.faces) or col.volume < 1e-7:
            rec['slot'] = 'none (boards do not overlap at the last frame)'; slotted[a] = A; info[a].update(rec); continue
        # world up in A's frame
        up_a = refpose.R_of(q[f, i]).T @ np.array([0, 0, 1.0])
        cv = col.vertices; hv = cv @ up_a; hmid = 0.5 * (hv.min() + hv.max())
        # slot = column half (upper half for the receiving board, lower for the inserted one), extended to the edge
        keep_upper = (a != inserted)
        bigger = 0.30
        # half-space box aligned with up_a: build a large box and intersect with column grown along up_a
        z_ax = up_a / np.linalg.norm(up_a)
        x_ax = np.cross(z_ax, [1, 0, 0]); x_ax = x_ax if np.linalg.norm(x_ax) > 1e-3 else np.cross(z_ax, [0, 1, 0]); x_ax /= np.linalg.norm(x_ax)
        y_ax = np.cross(z_ax, x_ax)
        Rh = np.c_[x_ax, y_ax, z_ax]
        hs_tf = np.eye(4); hs_tf[:3, :3] = Rh
        hs_tf[:3, 3] = (hmid + (bigger / 2 if keep_upper else -bigger / 2)) * z_ax + (cv.mean(0) - (cv.mean(0) @ z_ax) * z_ax)
        half = trimesh.creation.box(extents=[bigger, bigger, bigger], transform=hs_tf)
        # prism = the other plate (grown 0.5 mm) swept along up: approximate by the other plate box elongated along up
        ext_o = B[o]['ext'].copy(); Ob_long_tf = np.eye(4)
        Ob_long = box_mesh(dict(B[o], ext=ext_o + np.array([0.0, 0.0, 0.0])), grow=0.0005)
        Ob_long.apply_transform(np.linalg.inv(Tw_a) @ Tw_o)
        # extend the other plate along up by translating copies (convex hull of the plate and its shifted copy)
        sh = 0.15 * z_ax * (1 if keep_upper else -1)
        sweep = trimesh.convex.convex_hull(np.r_[Ob_long.vertices, Ob_long.vertices + sh])
        cutter = sweep.intersection(half, engine='manifold')
        Aslot = A.difference(cutter, engine='manifold')
        rec.update(slot='upper half' if keep_upper else 'lower half', removed_cm3=round(float(A.volume - Aslot.volume) * 1e6, 2),
                   slotted_watertight=bool(Aslot.is_watertight))
        slotted[a] = Aslot; info[a].update(rec)
    for nm in names:
        m, app, napp = appendages(nm, B[nm])
        info[nm]['appendage_faces'] = napp
        for tag, body in (('box', boxes[nm]), ('boxslot', slotted[nm])):
            body.export(OUT + f'{nm}_{tag}_body.glb')
            sc = trimesh.util.concatenate([body, app]) if app is not None else body
            sc.export(OUT + f'{nm}_{tag}.glb')
        from scipy.spatial import cKDTree
        sc = trimesh.load(OUT + f'{nm}_boxslot.glb', force='mesh')
        A_ = m.sample(20000); B_ = sc.sample(20000)
        dA = cKDTree(B_).query(A_)[0]; dB = cKDTree(A_).query(B_)[0]
        info[nm].update(M_sym_mean_mm=round(0.5 * (dA.mean() + dB.mean()) * 1e3, 2), M_ours_to_fit_p90_mm=round(float(np.percentile(dA, 90)) * 1e3, 2))
    json.dump(info, open(OUT + 'boards.json', 'w'), indent=1); print(json.dumps(info, indent=1))

main()
