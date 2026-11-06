"""PUBOWN report-only alternative pick with E0's pre-registered frame gate (GT-free; no scoring).
E0 PREREG s4 excludes a candidate whose identity frame check against meshes/library_v3/<obj>.glb exceeds 3x the C0
public mesh's value (E0 inputs/thresholds.json, fixed before E0 ran and before PUBOWN): area-weighted centroid offset,
median symmetric surface distance, PCA axis angles (ill-defined axes not checked). PUBOWN's own rule (C0b s5) has no
frame gate; this script does NOT change the PUBOWN pick. It re-applies C0b s5 per pair (lowest own fid, ties -> fewer
raw faces -> label) to the candidates that pass the E0 gate as well, so the re-track consumer can run both sets.
beige_cup has no E0 threshold row: its candidates are measured and reported, and the gate is not applied to them.
Also reports, per candidate, the connected bodies (count, largest stray body, farthest body distance).
Usage: python -I pubown_gate_alt.py REPO RESULTS THRESHOLDS.json OUT.json
"""
import json, os, sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

REPO, R, THR, OUT = sys.argv[1:5]
T = json.load(open(THR))['objects']
SEED_N, SEED_L, N = 1234, 4321, 100000


def load(p):
    return trimesh.load(p, force='mesh', process=False)


def surf(m, n, seed):
    return trimesh.sample.sample_surface(m, n, seed=seed)[0]


def area_centroid(m):
    w = m.area_faces
    return (m.triangles_center * w[:, None]).sum(0) / w.sum()


def pca(p):
    X = p - p.mean(0)
    ev, evec = np.linalg.eigh(X.T @ X / len(X))
    o = np.argsort(ev)[::-1]
    return evec[:, o]


LIB = {}


def lib(o):
    if o not in LIB:
        b = load(os.path.join(REPO, 'meshes/library_v3', o + '.glb'))
        pb = surf(b, N, SEED_L)
        LIB[o] = (area_centroid(b), pca(pb), pb, cKDTree(pb))
    return LIB[o]


def ident(path, o):
    a = load(path)
    cb, vb, pb, tb = lib(o)
    pa = surf(a, N, SEED_N)
    va = pca(pa)
    d1, _ = tb.query(pa)
    d2, _ = cKDTree(pa).query(pb)
    w = trimesh.Trimesh(a.vertices, a.faces, process=True)
    parts = sorted(w.split(only_watertight=False), key=lambda p: -p.area)
    c0 = parts[0].bounds.mean(0)
    dist = [float(np.linalg.norm(p.bounds.mean(0) - c0) * 1000) for p in parts[1:]]
    return dict(centroid_offset_mm=float(np.linalg.norm(area_centroid(a) - cb) * 1000),
                surf_sym_median_mm=float(np.median(np.concatenate([d1, d2])) * 1000),
                axis_angle_deg=[round(float(np.degrees(np.arccos(min(1.0, abs(float(va[:, i] @ vb[:, i])))))), 3) for i in range(3)],
                extent_mm=[round(float(x) * 1000, 1) for x in a.extents],
                bodies=len(parts), main_extent_mm=[round(float(x) * 1000, 1) for x in parts[0].extents],
                main_area_frac=round(float(parts[0].area / w.area), 4),
                largest_other_mm=round(max([float(max(p.extents)) * 1000 for p in parts[1:]], default=0.0), 1),
                farthest_other_mm=round(max(dist, default=0.0), 1))


def gate(o, f):
    if o not in T:
        return None, 'no E0 threshold for this object (reported only)'
    t = T[o]
    why = []
    if f['centroid_offset_mm'] > t['max_centroid_offset_mm']:
        why.append(f"centroid {f['centroid_offset_mm']:.2f} > {t['max_centroid_offset_mm']:.2f}")
    if f['surf_sym_median_mm'] > t['max_surf_symmetric_median_mm']:
        why.append(f"median {f['surf_sym_median_mm']:.2f} > {t['max_surf_symmetric_median_mm']:.2f}")
    for i, (chk, mx) in enumerate(zip(t['axis_checked'], t['max_axis_angle_deg'])):
        if chk and f['axis_angle_deg'][i] > mx:
            why.append(f"axis{i} {f['axis_angle_deg'][i]:.2f} > {mx:.2f}")
    return (not why), '; '.join(why) or 'pass'


S = json.load(open(os.path.join(R, 'selection.json')))
res = json.load(open(OUT)) if os.path.exists(OUT) else dict(thresholds=os.path.relpath(THR, REPO), samples=N, cands={}, pairs={})
for pair, rows in sorted(S['table'].items()):
    for r in rows:
        key = r['label']
        if key in res['cands'] or r['excluded']:
            continue
        p = os.path.join(R, os.path.relpath(r['path'], '/content/results/pubown'))
        f = ident(p, r['object'])
        ok, why = gate(r['object'], f)
        res['cands'][key] = dict(pair=pair, fid_own_sum_mm=r['fid_own_sum_mm'], faces_raw=r['faces_raw'], gate_pass=ok, gate=why, **f)
        print(key, round(r['fid_own_sum_mm'], 3), ok, why, f['extent_mm'], f['bodies'], f['farthest_other_mm'], flush=True)
        json.dump(res, open(OUT, 'w'), indent=1)
for pair, s in sorted(S['selection'].items()):
    C = [(k, c) for k, c in res['cands'].items() if c['pair'] == pair]
    if not C:
        res['pairs'][pair] = dict(pubown_pick=s.get('pick'), alt_pick=None, alt='library_v3 (no PUBOWN candidate)')
        continue
    el = [(k, c) for k, c in C if c['gate_pass'] is not False]
    el.sort(key=lambda kc: (round(kc[1]['fid_own_sum_mm'], 3), kc[1]['faces_raw'], kc[0].encode()))
    alt = el[0][0] if el else None
    res['pairs'][pair] = dict(pubown_pick=s['pick'], pubown_pick_gate=res['cands'][s['pick']]['gate'],
                              alt_pick=alt, alt=('same as PUBOWN' if alt == s['pick'] else (alt or 'library_v3 (all candidates fail the E0 gate)')),
                              alt_fid_own_sum_mm=res['cands'][alt]['fid_own_sum_mm'] if alt else None,
                              n_pass=sum(c['gate_pass'] is True for _, c in C), n_cand=len(C))
    print(pair, json.dumps(res['pairs'][pair]), flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
print('WROTE', OUT)
