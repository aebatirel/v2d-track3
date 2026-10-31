"""Figures of the BI2 dev runs (cv2 only; matplotlib is not in the gmg venv). GT-free: our meshes, our voxel sets.

  python i_png.py OUT_DIR(RUN/interlock/public/ep<N>-tag) CAND_DIR PICKS(obj=cid,...) PNG_PREFIX

Writes PNG_PREFIX_objects.png (per object: face-on view of the pick with the motion region, the carved region, the
placed SAM 3D notch and the silhouette see-through voxels; plus the DIAG slotted mesh), PNG_PREFIX_assembled.png
(the pair at the median assembled pose: collider overlap of the default pieces and of the DIAG carved pieces) and
PNG_PREFIX_track.png (per frame: placement offset per candidate, partner overlap per candidate, collider overlap).
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
import trimesh

W = 520
COL = dict(region=(40, 40, 230), carve=(200, 0, 200), gen=(230, 120, 0), sil=(0, 170, 0), surf=(150, 150, 150))


def centres(lo, vox, shape, lin):
    idx = np.stack(np.unravel_index(np.asarray(lin, np.int64), tuple(shape)), 1)
    return np.asarray(lo) + (idx + 0.5) * vox


def frame_of(mesh):
    X = trimesh.sample.sample_surface(mesh, 30000, seed=0)[0]
    c = X.mean(0); U = np.linalg.svd(X - c, full_matrices=False)[2]
    return c, U, X


def canvas():
    return np.full((W, W, 3), 255, np.uint8)


def draw(img, P, c, U, ax=(0, 1), col=(0, 0, 0), r=1, scale=None, depth_shade=False):
    A = (P - c) @ U.T
    s = scale
    u = (A[:, ax[0]] * s + W / 2).astype(int); v = (W / 2 - A[:, ax[1]] * s).astype(int)
    k = (u >= 0) & (u < W) & (v >= 0) & (v < W)
    if depth_shade:
        o = [x for x in (0, 1, 2) if x not in ax][0]
        z = A[k, o]; sh = (60 + (z - z.min()) / (np.ptp(z) + 1e-9) * 150).astype(int)
        for uu, vv, g in zip(u[k], v[k], sh):
            img[vv, uu] = (g, g, g)
        return
    for uu, vv in zip(u[k], v[k]):
        cv2.circle(img, (int(uu), int(vv)), r, col, -1)


def label(img, txt, y=18, col=(0, 0, 0)):
    cv2.putText(img, txt, (6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)


def objects_png(out_dir, cand_dir, picks, prefix):
    rows = []
    for obj, cid in picks.items():
        vz = os.path.join(out_dir, f'voxels_{obj}.npz')
        if not os.path.exists(vz):
            continue
        z = dict(np.load(vz))
        lo, vox, shape = z['lo'], float(z['vox']), z['shape']
        sshape = shape * 2
        m = trimesh.load(os.path.join(cand_dir, obj, f'{cid}.glb'), force='mesh')
        c, U, X = frame_of(m)
        scale = 0.85 * W / max(np.ptp((X - c) @ U.T, axis=0)[:2].max(), 1e-6)
        panels = []
        for ax, name in (((0, 1), 'face-on (long x width)'), ((0, 2), 'edge (long x thickness)')):
            img = canvas()
            draw(img, X, c, U, ax, scale=scale, depth_shade=True)
            for k in sorted(z):
                if k.endswith('_region'):
                    draw(img, centres(lo, vox, shape, z[k]), c, U, ax, COL['region'], 2, scale)
            for k in sorted(z):
                if k.endswith('_sim_sub'):
                    draw(img, centres(lo, vox / 2, sshape, z[k]), c, U, ax, COL['carve'], 1, scale)
            if 'gen_C_a' in z:
                draw(img, centres(lo, vox, shape, np.nonzero(z['gen_C_a'])[0]), c, U, ax, COL['gen'], 2, scale)
            if 'sil' in z:
                draw(img, centres(lo, vox, shape, np.nonzero(z['sil'])[0]), c, U, ax, COL['sil'], 2, scale)
            label(img, f'{obj} pick {cid}: {name}')
            label(img, 'red motion region R  magenta sim carve', 36, (0, 0, 160))
            label(img, 'blue SAM3D notch (placed)  green silhouette SIL', 52, (160, 80, 0))
            panels.append(img)
        dg = glob.glob(os.path.join(out_dir, 'diag', obj, 'DIAG_slot_*.glb'))
        img = canvas()
        if dg:
            md = trimesh.load(dg[0], force='mesh')
            Xd = trimesh.sample.sample_surface(md, 40000, seed=0)[0]
            draw(img, Xd, c, U, (0, 1), scale=scale, depth_shade=True)
            label(img, f'DIAG slotted {os.path.basename(dg[0])[:-4]} ({len(md.faces)} f, wt {md.is_watertight})')
            label(img, 'diagnostic only: never submitted / delivered', 36, (0, 0, 200))
        else:
            label(img, 'no DIAG slotted mesh')
        panels.append(img)
        rows.append(np.hstack(panels))
    if rows:
        cv2.imwrite(prefix + '_objects.png', np.vstack(rows))


def load_hulls(d):
    return [np.asarray(trimesh.load(f, force='mesh').vertices) for f in sorted(glob.glob(os.path.join(d, 'piece_*.obj')))]


def assembled_png(out_dir, sim_dir, objs, prefix, T_op, title=''):
    """Pair at T_op (= T_{o<-p} median assembled): default pieces (sim r0) and DIAG carved pieces; overlap points."""
    from scipy.spatial import ConvexHull
    o, p = objs
    panels = []
    for name, dirs in (('default pieces (delivered r0)', (os.path.join(sim_dir, o), os.path.join(sim_dir, p))),
                       ('DIAG carved pieces', (os.path.join(out_dir, 'diag', o), os.path.join(out_dir, 'diag', p)))):
        ho, hp = load_hulls(dirs[0]), load_hulls(dirs[1])
        img = canvas()
        if not ho or not hp:
            label(img, f'{name}: none'); panels.append(img); continue
        P = np.vstack(ho); c = P.mean(0); U = np.linalg.svd(P - c, full_matrices=False)[2]
        scale = 0.8 * W / np.ptp((P - c) @ U.T, axis=0)[:2].max()
        # sample both colliders
        def samp(hs, n=40000):
            Q = np.vstack(hs); lo, hi = Q.min(0), Q.max(0)
            G = np.random.default_rng(0).uniform(lo, hi, (n, 3))
            ins = np.zeros(len(G), bool)
            for V in hs:
                e = ConvexHull(V).equations; ins |= np.all(G @ e[:, :3].T + e[:, 3] <= 0, axis=1)
            return G[ins]
        So = samp(ho); Sp = samp(hp) @ T_op[:3, :3].T + T_op[:3, 3]
        ov = np.zeros(len(Sp), bool)
        for V in ho:
            e = ConvexHull(V).equations; ov |= np.all(Sp @ e[:, :3].T + e[:, 3] <= 0, axis=1)
        draw(img, So, c, U, (0, 1), (190, 190, 190), 1, scale)
        draw(img, Sp, c, U, (0, 1), (230, 180, 120), 1, scale)
        draw(img, Sp[ov], c, U, (0, 1), (0, 0, 230), 1, scale)
        vol = ov.mean() * np.prod(np.vstack(hp).max(0) - np.vstack(hp).min(0)) * len(Sp) / max(len(Sp), 1)
        label(img, f'{name}: {len(ho)}+{len(hp)} pieces')
        label(img, f'grey {o}, blue {p} at median assembled pose; red overlap', 36)
        panels.append(img)
    cv2.imwrite(prefix + '_assembled.png', np.hstack(panels))


def plot(series, title, ylabel, w=W * 2, h=260):
    img = np.full((h, w, 3), 255, np.uint8)
    xs = [x for s in series.values() for x in s[0]]
    ys = [y for s in series.values() for y in s[1]]
    if not xs:
        return img
    x0, x1 = min(xs), max(xs) + 1e-9; y0, y1 = 0.0, max(max(ys), 1e-6) * 1.1
    cols = [(200, 60, 0), (0, 120, 220), (0, 160, 0), (160, 0, 160), (90, 90, 90)]
    for i, (name, (x, y)) in enumerate(series.items()):
        pts = [(int(50 + (a - x0) / (x1 - x0) * (w - 70)), int(h - 30 - (b - y0) / (y1 - y0) * (h - 60))) for a, b in
               zip(x, y)]
        for q0, q1 in zip(pts[:-1], pts[1:]):
            cv2.line(img, q0, q1, cols[i % 5], 1, cv2.LINE_AA)
        cv2.putText(img, name, (60 + 230 * i, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.42, cols[i % 5], 1, cv2.LINE_AA)
    cv2.putText(img, f'{title}   (y: {ylabel}, max {y1 / 1.1:.2f}; x: frame {int(x0)}-{int(x1)})', (6, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.line(img, (50, h - 30), (w - 20, h - 30), (0, 0, 0), 1)
    return img


def track_png(out_dir, prefix):
    pcs = json.load(open(os.path.join(out_dir, 'physcheck.json')))
    rows = []
    for obj, cs in pcs.items():
        ser = {}
        for cid, f in cs.items():
            pf = f['placement'].get('per_frame_t_mm', {})
            ks = sorted(int(k) for k in pf)
            ser[f'{cid} |offset| mm'] = (ks, [pf[str(k)] if str(k) in pf else pf[k] for k in ks])
        rows.append(plot(ser, f'{obj}: per-frame placement offset of each candidate vs our depth', 'mm'))
    for f in sorted(glob.glob(os.path.join(out_dir, 'overlap_*.json'))):
        ov = json.load(open(f))
        ser = {f'{k} collider overlap cm3': (sorted(int(x) for x in v['series']),
                                             [v['series'][x] for x in sorted(v['series'], key=int)]) for k, v in ov.items()}
        rows.append(plot(ser, os.path.basename(f)[:-5] + ': collider overlap along our track (CoACD = FlashCHORD default)',
                         'cm3'))
    for f in sorted(glob.glob(os.path.join(out_dir, 'diag_*.json'))):
        dj = json.load(open(f))
        ph = dj.get('physics') or {}
        os_ = ph.get('overlap_series')
        if os_:
            ser = {f'{k} pieces': (sorted(int(x) for x in v), [v[x] for x in sorted(v, key=int)]) for k, v in os_.items()}
            rows.append(plot(ser, os.path.basename(f)[:-5] + ': collider overlap, default vs DIAG carved', 'cm3'))
    if rows:
        cv2.imwrite(prefix + '_track.png', np.vstack(rows))


def main():
    out_dir, cand_dir, picks, prefix = sys.argv[1:5]
    picks = dict(kv.split('=') for kv in picks.split(','))
    objects_png(out_dir, cand_dir, picks, prefix)
    rep = json.load(open(os.path.join(out_dir, 'report.json')))
    objs = list(picks)
    if len(objs) == 2 and rep.get('sim_dir') and os.path.exists(os.path.join(out_dir, 'T_asm.npy')):
        assembled_png(out_dir, rep['sim_dir'], objs, prefix, np.load(os.path.join(out_dir, 'T_asm.npy')))
    track_png(out_dir, prefix)
    print('wrote', prefix + '_*.png')


if __name__ == '__main__':
    main()
