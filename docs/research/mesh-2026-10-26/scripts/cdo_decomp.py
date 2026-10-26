"""[D] Decompose the kit CD-O of a candidate mesh against a reference scan (diagnostic only, after inference).

Reproduces CD-O.py _object_chamfer_cm step by step and reports: the RMS-radius scale ratio the scorer applies
(1.0 = the candidate's area distribution matches the scan at metric scale), the two directed mean distances
(ref->cand = missing surface / completeness, cand->ref = extra or misplaced surface / accuracy), their quantiles, and
the same Chamfer with the TRUE metric scale (ratio forced to 1), so a scale mismatch can be told from a shape error.
Usage: cdo_decomp.py KIT_DIR REF.glb CAND.glb [seed]
"""
import sys, importlib.util, numpy as np
from scipy.spatial import cKDTree
kit = sys.argv[1]
spec = importlib.util.spec_from_file_location('cdo', f'{kit}/metric_code/track_3/CD-O.py')
cdo = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdo)
sys.path.insert(0, kit)
from v2dlb.mesh_budget import budget_mesh
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 10000063
rv, rf = budget_mesh(sys.argv[2], 4096, 4096); cv, cf = budget_mesh(sys.argv[3], 4096, 4096)
out = {}
for mode in ('kit', 'metric'):
    _, rr = cdo._surface_moments(rv, rf); cc, cr = cdo._surface_moments(cv, cf)
    ratio = cr / rr if mode == 'kit' else 1.0
    v = (cv - cc) / ratio + cc
    R_m = cdo._sample_mesh_surface(rv, rf, 10000, seed); C_m = cdo._sample_mesh_surface(v, cf, 10000, seed)
    R_a = cdo._sample_mesh_surface(rv, rf, 3000, seed + 1); C_a = cdo._sample_mesh_surface(v, cf, 3000, seed + 1)
    Rot, t = cdo._align_rigid(R_a, C_a)
    C = C_m @ Rot.T + t
    d_rc = cKDTree(C).query(R_m)[0] * 100; d_cr = cKDTree(R_m).query(C)[0] * 100
    out[mode] = dict(ratio=round(float(cr / rr), 4), cdo=round(0.5 * (d_rc.mean() + d_cr.mean()), 4),
                     ref_to_cand=round(float(d_rc.mean()), 4), cand_to_ref=round(float(d_cr.mean()), 4),
                     ref_to_cand_q=[round(float(x), 3) for x in np.percentile(d_rc, [50, 90, 99])],
                     cand_to_ref_q=[round(float(x), 3) for x in np.percentile(d_cr, [50, 90, 99])],
                     frac_ref_gt5mm=round(float(np.mean(d_rc > 0.5)), 3), frac_cand_gt5mm=round(float(np.mean(d_cr > 0.5)), 3))
import json; print(json.dumps(dict(cand=sys.argv[3], **out)))
