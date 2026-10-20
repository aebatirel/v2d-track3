"""Verifier r2, C2 layout: independent marker finder for the cup scans (no use of selfsim/markers.py).
Axis: up = R^T z from public GT ep 11 f0 (analysis only); axis point = least-squares circle centre of outer-wall points
(radial 40-48 mm band at mid height). Marker = cluster of surface points standing > 6 mm proud of the local wall
radius; sphere centre = algebraic sphere fit to the cluster's bright points. Report (theta, h, r), spacings, chords."""
import numpy as np, trimesh, pandas as pd, itertools, json, sys
from scipy.spatial.transform import Rotation as Rr
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
import scipy.sparse as sp
ROOT = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3'
name = sys.argv[1] if len(sys.argv) > 1 else 'beige_cup'
ep = 11
s = trimesh.load(f'{ROOT}/public/mesh/{name}/{name}.glb'); g = list(s.geometry.values())[0]
P, fi = trimesh.sample.sample_surface(g, 800000, seed=7)
uv = g.visual.uv[g.faces[fi]].mean(1)
tex = np.asarray(g.visual.material.baseColorTexture.convert('RGB')).astype(float) / 255
H, W = tex.shape[:2]
C = tex[np.clip(((1 - uv[:, 1] % 1) * (H - 1)).round().astype(int), 0, H - 1), np.clip(((uv[:, 0] % 1) * (W - 1)).round().astype(int), 0, W - 1)]
d = pd.read_parquet(f'{ROOT}/public/data/chunk-000/episode_{ep:06d}.parquet')
o = [x for x in d['observation.objects'].iloc[0] if x['name'] == name][0]['pose']
R = Rr.from_quat([o[4], o[5], o[6], o[3]]).as_matrix(); up = R.T @ np.array([0, 0, 1.])
# frame: e1, e2 perpendicular to up
e1 = np.cross(up, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(up, e1)
h = P @ up; xy = np.c_[P @ e1, P @ e2]
# axis point: iterate circle fit on outer wall at mid height
c = np.zeros(2)
for _ in range(5):
    r = np.linalg.norm(xy - c, axis=1)
    m = (np.abs(h - np.median(h)) < 0.03) & (r > np.percentile(r[np.abs(h - np.median(h)) < 0.03], 60))
    A = np.c_[2 * xy[m], np.ones(m.sum())]; b = (xy[m] ** 2).sum(1); sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c = sol[:2]
r = np.linalg.norm(xy - c, axis=1); th = np.degrees(np.arctan2(xy[:, 1] - c[1], xy[:, 0] - c[0]))
# local outer radius per 4 mm height bin = 90th pct of r
hb = np.floor(h / 0.004).astype(int); rout = np.zeros(len(P))
for k in np.unique(hb):
    mm = hb == k; rout[mm] = np.percentile(r[mm], 80)
proud = r > rout + 0.006
Q = P[proud]; T = cKDTree(Q); pr = T.query_pairs(0.003, output_type='ndarray')
G = sp.coo_matrix((np.ones(len(pr)), (pr[:, 0], pr[:, 1])), shape=(len(Q), len(Q)))
nc, lab = connected_components(G, directed=False)
mk = []
for k in range(nc):
    mm = lab == k
    if mm.sum() < 300: continue
    X = Q[mm]; Cc = C[proud][mm]; br = Cc.mean(1) > 0.45
    Y = X[br] if br.sum() > 50 else X
    A = np.c_[2 * Y, np.ones(len(Y))]; b = (Y * Y).sum(1); sol = np.linalg.lstsq(A, b, rcond=None)[0]
    cen = sol[:3]; rad = np.sqrt(sol[3] + cen @ cen)
    q = cen @ np.c_[e1, e2] - c; mk.append(dict(n=int(mm.sum()), nbright=int(br.sum()), centre=cen.tolist(), rad_mm=rad * 1e3,
              theta=float(np.degrees(np.arctan2(q[1], q[0]))), h_mm=float(cen @ up * 1e3), r_mm=float(np.linalg.norm(q) * 1e3)))
mk.sort(key=lambda z: z['theta'])
print(name, 'wall r at mid height %.1f mm; axis centre (e1,e2) %s mm; clusters %d' % (np.median(rout[np.abs(h - np.median(h)) < 0.03]) * 1e3, np.round(c * 1e3, 2), len(mk)))
for z in mk: print('  theta %7.1f  h %6.1f  r %5.1f  sphere r %.1f mm  n %d bright %d' % (z['theta'], z['h_mm'], z['r_mm'], z['rad_mm'], z['n'], z['nbright']))
ths = sorted(z['theta'] for z in mk)
print('  spacings', np.round(np.diff(ths + [ths[0] + 360]), 1).tolist())
M = np.array([z['centre'] for z in mk])
for i, j in itertools.combinations(range(len(M)), 2): print('  chord %d-%d %.1f mm' % (i, j, np.linalg.norm(M[i] - M[j]) * 1e3))
json.dump(mk, open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/r2/c2_layout_{name}.json', 'w'), indent=1)
# refinement: robust sphere fit on all bright points within 11 mm of the initial centre (not only the proud cap)
TP = cKDTree(P); print('refined (all bright pts within 11 mm, 3 robust iterations, tol 0.6 mm):')
M2 = []
for z in mk:
    cen = np.array(z['centre']); rad = z['rad_mm'] / 1e3
    for it in range(4):
        idx = np.array(TP.query_ball_point(cen, 0.011)); Y = P[idx][C[idx].mean(1) > 0.45]
        if it: Y = Y[np.abs(np.linalg.norm(Y - cen, axis=1) - rad) < 0.0006]
        A = np.c_[2 * Y, np.ones(len(Y))]; b = (Y * Y).sum(1); sol = np.linalg.lstsq(A, b, rcond=None)[0]
        cen = sol[:3]; rad = np.sqrt(sol[3] + cen @ cen)
    q = cen @ np.c_[e1, e2] - c; M2.append(cen)
    print('  theta %7.1f h %6.1f r %5.1f sphere r %.2f mm n %d' % (np.degrees(np.arctan2(q[1], q[0])), cen @ up * 1e3, np.linalg.norm(q) * 1e3, rad * 1e3, len(Y)))
M2 = np.array(M2)
for i, j in itertools.combinations(range(len(M2)), 2): print('  chord %d-%d %.1f mm' % (i, j, np.linalg.norm(M2[i] - M2[j]) * 1e3))
import sys as _s; _s.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12')
import os; os.chdir('/Users/aebatirel/Documents/Code/v2d-research/work/12')
from selfsim import good_markers
G0 = good_markers(name)
for k, cen in enumerate(M2): print('  dist to stage-A centre %.2f mm' % (np.linalg.norm(G0 - cen, axis=1).min() * 1e3))
