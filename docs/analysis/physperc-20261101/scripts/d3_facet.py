"""D3 (DIAGNOSTIC, reads mocap via D1's g_true): contact-facet prior (hull facet nearest the tracker's down axis, no
stability test) vs the truth, for several min-area settings. Usage: python -I d3_facet.py SCRATCH OUT_JSON"""
import sys, json, numpy as np
S, OUT = sys.argv[1:3]; sys.path.insert(0, f'{S}/kit/v2d_submission_kit')
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/physperc-20261101/scripts')
from v2dlb import track3_pose as T3; from v2dlb.mesh_budget import budget_mesh; from v2dlb.object_mesh import _surface_moments
import physlib as PL
ang = lambda a, b: float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
D1 = json.load(open('/home/user/v2d-track3/docs/analysis/physperc-20261101/diag/d1_tilt_9a.json'))
out = {}
for e, objs in D1.items():
    for n, D in objs.items():
        mp = f'{S}/mesh9a/{n}.glb'
        sv, sf = PL.load_vf(PL.scan_path(S, n)); c, _ = _surface_moments(sv, sf)
        ca, B = T3._register_object_body(budget_mesh(mp, 4096, 4096), (sv, sf), c, 1_000_003 * int(e) + 101 * D['slot'])
        gt = np.array(D['g_true']); go = np.array(D['g_ours']); gb = B.T @ go
        r = dict(e_now=D['e_now'], e_stable=D['e_prior'])
        for ma in (1e-4, 1e-3, 3e-3):
            Nf, Af = PL.hull_facets.__wrapped__(mp, ma)
            k = int(np.argmax(Nf @ gb))
            r[f'e_facet_{ma:g}'] = round(ang(B @ Nf[k], gt), 2); r[f'match_{ma:g}'] = round(ang(Nf[k], gb), 2)
            r[f'area_cm2_{ma:g}'] = round(float(Af[k]) * 1e4, 1)
        out[f'{e}:{n}'] = r
        print(e, n[:13].ljust(13), r, flush=True)
json.dump(out, open(OUT, 'w'), indent=1)
