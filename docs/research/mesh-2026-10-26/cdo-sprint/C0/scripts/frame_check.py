"""C0 GT-free frame and format check (CD-O sprint, stage 1).

For each swapped mesh vs the library_v3 mesh it replaces, with NO registration (both are read in their own file
frames, which should be the library_v3 object frame):
  - centroid offset (area-weighted surface centroid), mm;
  - angles between matched principal axes of the area-weighted surface (PCA), deg, with the eigenvalue spectra so a
    near-degenerate pair (lathes) is visible;
  - symmetric surface distance: exact closest-point distance from N surface samples of each mesh to the other mesh,
    median of each direction and of the pooled set, mm.
After the kit's budget_mesh(path, 4096, 4096) (v2dlb/mesh_budget.py, what Kaggle receives):
  - non-padding faces <= 4096, vertices <= 4096; watertight; number of bodies (face-connected components).
Reads only mesh files (ours). No scan, no mocap, no parquet.

Usage: python -I frame_check.py KIT_DIR OUT.json NAME:NEW.glb:LIB.glb [...]
"""
import hashlib
import json
import sys

import numpy as np
import trimesh

KIT, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh  # noqa: E402

N = 20000
SEED = 0


def load(path):
    return trimesh.load(path, force='mesh', process=False)


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def pca(m):
    w = m.area_faces
    c = (m.triangles_center * w[:, None]).sum(0) / w.sum()
    pts, _ = trimesh.sample.sample_surface(m, 200000, seed=SEED)
    X = pts - pts.mean(0)
    ev, evec = np.linalg.eigh(X.T @ X / len(X))
    order = np.argsort(ev)[::-1]
    return c, ev[order], evec[:, order]


def surf_dist(a, b):
    pa, _ = trimesh.sample.sample_surface(a, N, seed=SEED)
    pb, _ = trimesh.sample.sample_surface(b, N, seed=SEED + 1)
    _, dab, _ = trimesh.proximity.closest_point(b, pa)
    _, dba, _ = trimesh.proximity.closest_point(a, pb)
    return dab * 1000, dba * 1000


def budget_info(path):
    v, f = budget_mesh(path, 4096, 4096)
    keep = ~((f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 0] == f[:, 2]))
    fr = f[keep]
    m = trimesh.Trimesh(v, fr, process=True)
    m.remove_unreferenced_vertices()
    bodies = len(m.split(only_watertight=False))
    return dict(faces=int(len(fr)), vertices=int(len(m.vertices)), watertight=bool(m.is_watertight),
                bodies=int(bodies), faces_ok=bool(len(fr) <= 4096), vertices_ok=bool(len(m.vertices) <= 4096)), m


res = {}
for spec in sys.argv[3:]:
    name, new_p, lib_p = spec.split(':')
    a, b = load(new_p), load(lib_p)
    ca, eva, va = pca(a)
    cb, evb, vb = pca(b)
    ang = [float(np.degrees(np.arccos(min(1.0, abs(float(va[:, i] @ vb[:, i])))))) for i in range(3)]
    dab, dba = surf_dist(a, b)
    bud_new, ma = budget_info(new_p)
    bud_lib, mb = budget_info(lib_p)
    dab_b, dba_b = surf_dist(ma, mb)
    res[name] = dict(
        new=dict(path=new_p, sha256=sha256(new_p), faces_raw=int(len(a.faces)),
                 watertight_raw=bool(trimesh.Trimesh(a.vertices, a.faces, process=True).is_watertight),
                 bodies_raw=int(len(trimesh.Trimesh(a.vertices, a.faces, process=True).split(only_watertight=False))),
                 extent_mm=[float(x) for x in (a.extents * 1000)], pca_sd_mm=[float(x) for x in np.sqrt(eva) * 1000]),
        lib=dict(path=lib_p, sha256=sha256(lib_p), faces_raw=int(len(b.faces)),
                 extent_mm=[float(x) for x in (b.extents * 1000)], pca_sd_mm=[float(x) for x in np.sqrt(evb) * 1000]),
        centroid_offset_mm=float(np.linalg.norm(ca - cb) * 1000),
        centroid_delta_mm=[float(x) for x in (ca - cb) * 1000],
        axis_angle_deg=ang,
        axis_note='angles of matched PCA axes (major, middle, minor); an axis whose eigenvalue is within ~10% of '
                  'another is ill-defined (lathe symmetry) and its angle is not meaningful',
        surf_new_to_lib_median_mm=float(np.median(dab)), surf_lib_to_new_median_mm=float(np.median(dba)),
        surf_symmetric_median_mm=float(np.median(np.concatenate([dab, dba]))),
        surf_symmetric_p90_mm=float(np.percentile(np.concatenate([dab, dba]), 90)),
        budget_new=bud_new, budget_lib=bud_lib,
        budgeted_surf_symmetric_median_mm=float(np.median(np.concatenate([dab_b, dba_b]))),
    )
    print(name, json.dumps({k: res[name][k] for k in ('centroid_offset_mm', 'axis_angle_deg',
                                                      'surf_symmetric_median_mm', 'budget_new', 'budget_lib')}),
          flush=True)

json.dump(dict(method=__doc__, n_samples=N, seed=SEED, results=res), open(OUT, 'w'), indent=1)
