"""Reference-reuse evidence (BUILD.md section 2; CPU, GT-free): how far would eval 10's V4p track move if its nest_physics
seat (tools/nest_physics.py --mode inner, plain MuJoCo) were re-run with another collision piece set? Input: the V4p track
rebuilt on CPU with meshes/carve/ev10 (md5 fa449903..., = mask10's = the V that e10v trained on before mkref) and the same
pipeline re-run with ev10cs4 / ev10cs5 (tools/nest_physics.py + refine.py S2 on the same S12 output). Per object, the
world-frame position difference (cm) over the S12 window [53, 161) and the hands-off frames [122, 161), and the beige
cup's height difference (cm, world z) there. Also the trained V vs the packed reference P from e10v's identity.json.
Usage: python seat_compare.py --base ev10/V/ep10/poses.npz --cand NAME=poses.npz ... --out J"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..', 'tools'))
from e11g_verify import world   # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('--base', required=True); ap.add_argument('--cand', action='append', required=True)
ap.add_argument('--out', required=True); a = ap.parse_args()
B, _ = world(a.base); res = dict(base=a.base, windows=dict(s12=[53, 161], hands_off=[122, 161]), cands={})
for spec in a.cand:
    n, f = spec.split('=', 1); C, _ = world(f); row = {}
    for o in sorted(B):
        d = np.linalg.norm(C[o][:, :3, 3] - B[o][:, :3, 3], axis=1) * 100; dz = (C[o][:, 2, 3] - B[o][:, 2, 3]) * 100
        row[o] = {w: dict(median_cm=round(float(np.median(d[lo:hi])), 3), max_cm=round(float(d[lo:hi].max()), 3),
                          dz_median_cm=round(float(np.median(dz[lo:hi])), 3))
                  for w, (lo, hi) in res['windows'].items()}
        row[o]['frames_differing'] = int((d > 1e-4).sum())
    res['cands'][n] = dict(poses=f, objects=row)
json.dump(res, open(a.out, 'w'), indent=1)
for n, c in res['cands'].items():
    print(n, '; '.join(f"{o}: s12 median {v['s12']['median_cm']} max {v['s12']['max_cm']} cm, hands-off median {v['hands_off']['median_cm']} "
                       f"(dz {v['hands_off']['dz_median_cm']}) cm, frames differing {v['frames_differing']}" for o, v in c['objects'].items()))
