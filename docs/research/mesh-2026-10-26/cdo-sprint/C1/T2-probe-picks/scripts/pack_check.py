"""GT-free pack check (C1/T2): does the kit packer's budget_mesh(4096, 4096) see the same shape in the placed copy as in
the probe-scored mesh? Compares budget_mesh(placed.glb) with the placement Sim(3) applied to budget_mesh(probe.ply):
symmetric mean surface distance (kit sampler, 20000 points), in mm and relative to the placed mesh's kit radius,
against its sampling floor (the placed budget mesh against itself, another seed), plus vertex-to-vertex distances.
No scan, mocap or parquet is read.
Usage: pack_check.py KIT PLACE.json [PLACE.json ...]
"""
import json, sys
import numpy as np

kit = sys.argv[1]
sys.path.insert(0, kit)
from v2dlb.mesh_budget import budget_mesh                    # noqa: E402
from v2dlb.object_mesh import _surface_moments               # noqa: E402
from v2dlb.mesh_common import _sample_mesh_surface           # noqa: E402
from scipy.spatial import cKDTree                            # noqa: E402

for p in sys.argv[2:]:
    info = json.load(open(p))
    s, R, t = info['scale'], np.asarray(info['R']), np.asarray(info['t'])
    vp, fp = (np.asarray(x) for x in budget_mesh(info['candidate'], 4096, 4096))
    vq, fq = (np.asarray(x) for x in budget_mesh(info['out'], 4096, 4096))
    vp2 = s * vp @ R.T + t
    A = _sample_mesh_surface(vp2, fp, 20000, 5); B = _sample_mesh_surface(vq, fq, 20000, 5)
    d = 0.5 * (cKDTree(B).query(A)[0].mean() + cKDTree(A).query(B)[0].mean())
    c, r = _surface_moments(vq, fq)
    A2 = _sample_mesh_surface(vq, fq, 20000, 6)                     # sampling floor: same mesh, another seed
    floor = 0.5 * (cKDTree(B).query(A2)[0].mean() + cKDTree(A2).query(B)[0].mean())
    dv = cKDTree(vp2).query(vq)[0]                                  # vertex-to-vertex (decimation identity)
    print(json.dumps(dict(object=info['object'], probe_budget=[len(vp), len(fp)], placed_budget=[len(vq), len(fq)],
                          same_vertex_count=len(vp) == len(vq), symdist_mm=round(d * 1e3, 4),
                          symdist_rel_radius=round(d / r, 6),
                          floor_same_mesh_mm=round(floor * 1e3, 4), vertex_nn_med_mm=round(float(np.median(dv)) * 1e3, 4),
                          vertex_nn_max_mm=round(float(dv.max()) * 1e3, 4), kit_radius_mm=round(r * 1e3, 2),
                          placed_kit_centroid_mm=np.round(c * 1e3, 2).tolist())))
