"""M4: do the convex pieces survive FlashCHORD's own decomposition as delivered? Each piece_XX.obj (one URDF <collision>
element after make_assets.py --pieces, i.e. one Newton mesh shape) is passed to flash_chord.assets.mesh.convex_decompose
with the scene builder's defaults (decompose_params None: threshold 0.05, preprocess auto), as
scene.objects._decompose_object_collision does. Pass per piece: 1 hull, volume within 1 %, and surface deviation <= 0.1 mm
(max over the piece's vertices of their distance outside the returned hull's half-spaces, and vice versa; a vertex-set
Hausdorff is also reported but flags redundant on-face vertices that CoACD drops).
Usage (fcvenv, FLASH_CHORD_CACHE_DIR set to a scratch dir): m4.py CARVE_DIR OUT.json"""
import sys, glob, json, time
import numpy as np, trimesh
from scipy.spatial import cKDTree, ConvexHull
from flash_chord.assets.mesh import convex_decompose
C, outp = sys.argv[1:3]; res = {}
for n in ('blue_cup', 'beige_cup'):
    rows = []
    for f in sorted(glob.glob(f'{C}/{n}/piece_*.obj')):
        m = trimesh.load(f, force='mesh', process=False); t0 = time.time()
        hs = convex_decompose(np.asarray(m.vertices), np.asarray(m.faces))
        HV = np.concatenate([np.asarray(h.vertices, float) for h in hs])
        vol = sum(trimesh.Trimesh(np.asarray(h.vertices, float), np.asarray(h.faces).reshape(-1, 3)).volume for h in hs)
        hd = max(cKDTree(HV).query(m.vertices)[0].max(), cKDTree(m.vertices).query(HV)[0].max())
        EH = ConvexHull(HV).equations; EP = ConvexHull(np.asarray(m.vertices)).equations
        dev = max(float((np.asarray(m.vertices) @ EH[:, :3].T + EH[:, 3]).max(1).max()), float((HV @ EP[:, :3].T + EP[:, 3]).max(1).max()))
        rows.append(dict(piece=f.split('/')[-1], hulls=len(hs), vol_ratio=round(float(vol / m.volume), 5), hausdorff_mm=round(float(hd) * 1e3, 4),
                         surface_dev_mm=round(dev * 1e3, 4),
                         sec=round(time.time() - t0, 2)))
    ok = [r['hulls'] == 1 and abs(r['vol_ratio'] - 1) <= 0.01 and r['surface_dev_mm'] <= 0.1 for r in rows]
    res[n] = dict(pieces=len(rows), pass_all=bool(all(ok)), n_fail=int(len(ok) - sum(ok)), max_hulls=max(r['hulls'] for r in rows),
                  vol_ratio_minmax=[min(r['vol_ratio'] for r in rows), max(r['vol_ratio'] for r in rows)],
                  hausdorff_max_mm=max(r['hausdorff_mm'] for r in rows),
                  surface_dev_max_mm=max(r['surface_dev_mm'] for r in rows), rows=rows)
json.dump(res, open(outp, 'w'), indent=1)
print(json.dumps({n: {k: v for k, v in r.items() if k != 'rows'} for n, r in res.items()}))
