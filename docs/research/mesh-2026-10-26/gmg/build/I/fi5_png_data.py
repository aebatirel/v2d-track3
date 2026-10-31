"""PREREG F-I5.14 (T-I13 public): figure data for one episode of an F-I5 run (report only, decides nothing).

  GMG_MODE=dev python fi5_png_data.py --run RUN --ep N --bundle BUNDLE_DIR [--tag fi5]
Reads the driver outputs (RUN/interlock/public/ep<N>-<tag>/fi5.json) and the round folder (RUN/sim/public/ep<N>-<tag>/r0:
_default/<obj>/piece_XX.obj, <obj>/piece_XX.obj delivered, _carved_failed/<o>_<p>/piece_XX.obj) and the bundle's
tracks; writes RUN/fi5png/ep<N>.json + .npz: per pair the collider overlap along the track (2 mm samples of one object
inside the other's pieces, every 2nd frame) for the default and the delivered pieces, the pair's frame sets (build
frames entered, S frames, overshoot frames) and, for an in-scope pair with a rest pose, a 3 mm slab section through the
guest's collider centroid (plane spanned by gravity and the receiver's principal horizontal axis) of the receiver's default / delivered /
failed-carve pieces and the guest at T_rest. GT-free: our bundle tracks and our pieces only.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
from gmg import interlock as IL, collcarve as CC, cavpieces as CP  # noqa: E402


def load_pieces(d):
    import trimesh
    fs = sorted(glob.glob(os.path.join(d, 'piece_*.obj')))
    return [np.asarray(trimesh.load(f, force='mesh').vertices) for f in fs] or None


def section(H, T, c, u, v, w, slab, X=None):
    """Side-view projection onto (u, v) of the points of H (2 mm samples inside the pieces, or X) within SLAB of the
    plane through c (slab None: all points, a projection)."""
    if X is None:
        if H is None:
            return np.zeros((0, 2))
        X = CC.collider_samples(H, 0.002)
    if T is not None:
        X = X @ T[:3, :3].T + T[:3, 3]
    Y = X - c
    m = np.abs(Y @ w) <= slab if slab is not None else np.ones(len(Y), bool)
    return np.c_[Y[m] @ u, Y[m] @ v]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--bundle', required=True); ap.add_argument('--tag', default='fi5')
    a = ap.parse_args()
    guard.set_run(a.run)
    od = os.path.join(a.run, 'interlock', 'public', f'ep{a.ep}-{a.tag}')
    r0 = os.path.join(a.run, 'sim', 'public', f'ep{a.ep}-{a.tag}', 'r0')
    f5 = json.load(open(os.path.join(od, 'fi5.json')))
    b = IL.load_bundle_any(a.bundle)
    T = int(b.meta['T'])
    objs = list(f5['routes'])
    dflt = {o: load_pieces(os.path.join(r0, '_default', o)) for o in objs}
    dlv = {o: load_pieces(os.path.join(r0, o)) for o in objs}
    out = dict(ep=a.ep, T=T, objects=objs, routes={o: (f5['routes'][o] or {}).get('route') for o in objs}, pairs={})
    # collider volume (union of the pieces, 2 mm samples) vs the F-I5 body (the SHELL candidate solid), report only
    import trimesh
    rep = json.load(open(os.path.join(od, 'report.json')))
    vols = {}
    for o in objs:
        cid = (rep.get('fi5_body') or {}).get(o)
        bm = trimesh.load(os.path.join(a.run, 'cand', 'public', f'ep{a.ep}', o, f'{cid}.glb'), force='mesh') \
            if cid else None
        cell = CC.k_('sample_m') ** 3 * 1e6
        vols[o] = dict(body=cid, body_cm3=round(float(abs(bm.volume)) * 1e6, 2) if bm is not None else None,
                       body_watertight=bool(bm.is_watertight) if bm is not None else None,
                       default_pieces=None if dflt[o] is None else len(dflt[o]),
                       default_cm3=None if dflt[o] is None else round(len(CC.collider_samples(dflt[o])) * cell, 2),
                       delivered_pieces=None if dlv[o] is None else len(dlv[o]),
                       delivered_cm3=None if dlv[o] is None else round(len(CC.collider_samples(dlv[o])) * cell, 2))
    out['volumes'] = vols
    arrs = {}
    frames = list(range(0, T, 2))
    for key, W in (f5.get('pairs') or {}).items():
        o, p = key.split('|')
        row = dict(in_scope=W.get('in_scope'), receiver=W.get('receiver'), guest=W.get('guest'),
                   deliver=W.get('deliver'), overlap={})
        for t, q in ((o, p), (p, o)):
            for name, H in (('default', dflt), ('delivered', dlv)):
                if H[t] is None or H[q] is None:
                    continue
                Xq = CC.collider_samples(H[q])
                ser = CC.overlap_track(H[t], Xq, CC.k_('sample_m') ** 3, b, t, q, frames)
                row['overlap'][f'{t}<-{q}|{name}'] = [round(ser[f], 3) for f in frames]
        row['frames'] = frames
        comps = W.get('components') or []
        if comps:
            c0 = comps[0]
            g = c0.get('gates') or {}
            row['run'] = g.get('run')
            row['s_frames'] = (c0.get('rest') or {}).get('s_frames')
            row['overshoot'] = [x['f'] for x in c0.get('overshoot_frames') or []]
            Tr = c0.get('T_rest')
            recv, guest = W['receiver'], W['guest']
            if Tr is not None:
                Tr = np.asarray(Tr)
                # plane through the guest centroid at rest, spanned by gravity (receiver frame at the first S frame)
                # and the receiver's principal horizontal axis (PCA of its default collider samples)
                Xg = CC.collider_samples(dflt[guest])
                cg = Xg.mean(0) @ Tr[:3, :3].T + Tr[:3, 3]
                fs = row['s_frames'] or [row['run'][0]]
                f = fs[0]
                Wr = b.poses['world_T_cam'][f].astype(float) @ b.poses[f'cam_T_{recv}'][f].astype(float)
                n = np.asarray(b.meta['table']['n'], float) if b.meta.get('table') else np.array([0, 0, 1.0])
                gdir = -(Wr[:3, :3].T @ n); gdir /= np.linalg.norm(gdir)
                Xr = CC.collider_samples(dflt[recv])
                Ax = np.linalg.svd(Xr - Xr.mean(0), full_matrices=False)[2]
                u = gdir
                v = max((A - (A @ u) * u for A in Ax), key=np.linalg.norm)
                if np.linalg.norm(v) < 0.2:                # d nearly along gravity: any horizontal axis
                    v = np.cross(u, [1.0, 0, 0]) if abs(u[0]) < 0.9 else np.cross(u, [0, 1.0, 0])
                v /= np.linalg.norm(v)
                w = np.cross(u, v)
                slab = None                                # side-view projection of every sample
                arrs[f'{key}|recv_default'] = section(dflt[recv], None, cg, u, v, w, slab)
                arrs[f'{key}|recv_delivered'] = section(dlv[recv], None, cg, u, v, w, slab)
                fc = os.path.join(r0, '_carved_failed', f'{o}_{p}')
                arrs[f'{key}|recv_failed'] = section(load_pieces(fc) if os.path.isdir(fc) else None, None, cg, u,
                                                     v, w, slab)
                arrs[f'{key}|guest_rest'] = section(dflt[guest], Tr, cg, u, v, w, slab)
                for x, T_ in ((recv, None), (guest, Tr)):     # the F-I5 body (SHELL candidate) the pieces stand for
                    cid = (rep.get('fi5_body') or {}).get(x)
                    if cid:
                        bm = trimesh.load(os.path.join(a.run, 'cand', 'public', f'ep{a.ep}', x, f'{cid}.glb'),
                                          force='mesh')
                        Xb = np.asarray(trimesh.sample.sample_surface(bm, 6000, seed=0)[0])
                        arrs[f'{key}|body_{"recv" if x == recv else "guest"}'] = section(None, T_, cg, u, v, w, None,
                                                                                         X=Xb)
                row['section'] = dict(axes='u = gravity (down), v = the receiver principal horizontal axis (receiver frame)',
                                      projection='side view of every 2 mm collider sample and of 6000 body surface '
                                                 'samples', centre='guest collider centroid at T_rest', s_frame=int(f))
        out['pairs'][key] = row
    os.makedirs(os.path.join(a.run, 'fi5png'), exist_ok=True)
    with open(os.path.join(a.run, 'fi5png', f'ep{a.ep}.json'), 'w') as fh:
        json.dump(out, fh, default=IL._jdefault)
    np.savez_compressed(os.path.join(a.run, 'fi5png', f'ep{a.ep}.npz'), **{k.replace('|', '__'): v
                                                                           for k, v in arrs.items()})
    print('ok', a.ep, list(out['pairs']))


if __name__ == '__main__':
    main()
