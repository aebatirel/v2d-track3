"""GT-free look at why the F-I4.2 outline fill is < 0.9 on the ep24 boards (after T-I11 fi4b; diagnosis only, no rule
change). Recomputes plate_info / resolve_one_face / plate_body exactly as the run, then the outline mask, its
min-area rectangle and where the rectangle is empty. Writes JSON + a PNG of each mask."""
import json, os, sys
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
import numpy as np, cv2, trimesh
from scipy import ndimage
from gmg import guard, interlock as IL, platebody as PB

run, bundle, cands, outd = sys.argv[1:5]
guard.set_run(run)
b = IL.load_bundle_any(bundle)
info = {}
for obj in b.objects:
    m = trimesh.load(os.path.join(cands, obj, 'shell_t5p36.glb'), force='mesh')
    m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    info[obj] = PB.plate_info(b, obj, m)
o1, o2 = b.objects
res = {}
for obj, par in ((o1, o2), (o2, o1)):
    pi = PB.resolve_one_face(info[obj], info[par])
    bd = PB.plate_body(b, obj, pi)
    # recompute the mask as plate_body does, in the rectangle frame
    P, F = pi['_P'], pi['_F']
    n = np.asarray(pi['mid_n'], float); n /= np.linalg.norm(n)
    t = pi['t_m']; sig = b.sigma(obj)
    s = P @ n - pi['mid_d']
    k = np.abs(s) <= t / 2 + 3 * sig
    A = np.asarray(bd['box']['axes']); c = np.asarray(bd['box']['centre']); h = np.asarray(bd['box']['half'])
    U = (P[k] - c) @ A[:2].T
    fr = F[k]
    r = 0.002
    ij = np.floor((U + h[:2]) / r).astype(int)
    shp = np.ceil(2 * h[:2] / r).astype(int) + 1
    ok = np.all((ij >= 0) & (ij < shp), 1)
    key = np.unique(np.stack([ij[ok, 0], ij[ok, 1], fr[ok].astype(int)], 1), axis=0)
    cnt = np.zeros(shp, int); np.add.at(cnt, (key[:, 0], key[:, 1]), 1)
    M = cnt >= 3
    M = ndimage.binary_closing(np.pad(M, 2), structure=np.ones((3, 3)))[2:-2, 2:-2]
    M = ndimage.binary_fill_holes(M)
    lab, nl = ndimage.label(M, structure=np.ones((3, 3)))
    big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    M = lab == big
    # occupancy profile: share of each 2 mm column along a_L / row along a_W that is filled
    colL = M.mean(1); rowW = M.mean(0)
    # extents of the filled region at 2-98 % of the cells, and the empty share per rectangle quadrant / border band
    ii, jj = np.nonzero(M)
    q = lambda x, p: float(np.percentile(x, p)) * r * 1e3
    res[obj] = dict(t_source=pi.get('t_source'), t_mm=round(t * 1e3, 2), slab_mm=round((t / 2 + 3 * sig) * 1e3, 2),
                    L_mm=bd['L_mm'], W_mm=bd['W_mm'], fill=bd['fill'],
                    filled_extent_L_2_98_mm=round(q(ii, 98) - q(ii, 2), 1),
                    filled_extent_W_2_98_mm=round(q(jj, 98) - q(jj, 2), 1),
                    filled_extent_L_0_100_mm=round((ii.max() - ii.min() + 1) * r * 1e3, 1),
                    filled_extent_W_0_100_mm=round((jj.max() - jj.min() + 1) * r * 1e3, 1),
                    cols_L_fill_lt_0p5=int((colL < 0.5).sum()), rows_W_fill_lt_0p5=int((rowW < 0.5).sum()),
                    rowW_fill_profile=[round(float(x), 2) for x in rowW],
                    colL_fill_profile_every5=[round(float(x), 2) for x in colL[::5]])
    im = np.zeros(M.shape + (3,), np.uint8); im[M] = (200, 200, 200)
    im[(cnt >= 3) & ~M] = (0, 0, 255)
    im = cv2.resize(im, (M.shape[1] * 3, M.shape[0] * 3), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(outd, f'outline_{obj}.png'), im)
    print(obj, json.dumps({k: v for k, v in res[obj].items() if 'profile' not in k}), flush=True)
json.dump(res, open(os.path.join(outd, 'diag_outline.json'), 'w'), indent=1)
