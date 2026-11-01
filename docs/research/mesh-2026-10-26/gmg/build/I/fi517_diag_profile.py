"""Diagnostic (report only, decides nothing; T-I16, 1 Nov): why the round-2 ring search finds no layout on a real
SHELL (every candidate min wall far below zero). Builds the same Profile2 as the run (structure axis from the run's
structure_<obj>.json, the shell_t5p36 body, the bundle's sigma) and reports, per wall run and for the 12-sector one-band
b1 layout, the rays that set each sector's outer and inner envelopes: their r_in / r_out against the sector's median,
the interval count, and how many rays sit far below the median outer radius (stray inner intervals).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/build/I/fi517_diag_profile.py --run <run> --bundle <v6>/epN \
      --body <run>/cand/public/epN/<obj>/shell_t5p36.glb --structure <run>/interlock/public/epN-fi5r2/structure_<obj>.json \
      --obj <obj> --out <json>
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
if MR not in sys.path:
    sys.path.insert(0, MR)


def main():
    ap = argparse.ArgumentParser()
    for k in ('run', 'bundle', 'body', 'structure', 'obj', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--n-s', type=int, default=12)
    a = ap.parse_args()
    import numpy as np
    from gmg import guard
    guard.set_run(a.run)
    from gmg import interlock as IL, cavpieces as CP
    from gmg.tools.interlock_dev import load_mesh
    b = IL.load_bundle_any(a.bundle)
    body = load_mesh(a.body)
    hyp = json.load(open(a.structure))
    ax = hyp['axis']
    prof = CP.Profile2(body, ax['c'], ax['a'], b.sigma(a.obj))
    runs, rinfo = prof.runs()
    out = dict(obj=a.obj, profile=dict(prof.info, **{k: v for k, v in rinfo.items()}), runs=[])
    ri, ro, ni = prof.rin, prof.rout, prof.nint
    for r in runs or []:
        rows = list(range(r['row0'], r['row1'] + 1))
        R_in, R_out, N = ri[rows], ro[rows], ni[rows]
        has = np.isfinite(R_out)
        med_out = np.nanmedian(np.where(has, R_out, np.nan), axis=1)
        med_in = np.nanmedian(np.where(has, R_in, np.nan), axis=1)
        low = has & (R_out < med_out[:, None] - 0.010)                # outer radius > 10 mm below the row median
        start_in = has & (R_in == 0)
        row = dict(kind=r['kind'], lo_mm=round(r['lo'] * 1e3, 2), hi_mm=round(r['hi'] * 1e3, 2), rows=len(rows),
                   rays=int(has.size), rays_hit=int(has.sum()), rays_no_hit=int((~has).sum()),
                   nint_hist={int(k): int(v) for k, v in zip(*np.unique(N[has], return_counts=True))},
                   r_out_median_mm=[round(float(np.nanmin(med_out)) * 1e3, 2), round(float(np.nanmax(med_out)) * 1e3, 2)],
                   r_in_median_mm=[round(float(np.nanmin(med_in)) * 1e3, 2), round(float(np.nanmax(med_in)) * 1e3, 2)],
                   wall_median_mm=round(float(np.nanmedian(med_out - med_in)) * 1e3, 2),
                   rays_rout_10mm_below_median=int(low.sum()), rows_with_such_rays=int(low.any(1).sum()),
                   rays_starting_in_material=int(start_in.sum()))
        if low.any():
            k = np.argwhere(low)
            ex = []
            for i, j in k[np.argsort(R_out[low])][:8]:
                ex.append(dict(h_mm=round(float(prof.H[rows[i]]) * 1e3, 2), phi_deg=int(round(np.degrees(prof.phis[j]))),
                               r_in_mm=round(float(R_in[i, j]) * 1e3, 2), r_out_mm=round(float(R_out[i, j]) * 1e3, 2),
                               nint=int(N[i, j]), row_median_out_mm=round(float(med_out[i]) * 1e3, 2)))
            row['lowest_rout_rays'] = ex
            az = np.unique(k[:, 1])
            row['azimuths_with_low_rays'] = int(len(az))
            hs = np.array([prof.H[rows[i]] for i, j in k])
            sol = [(q['lo'], q['hi']) for q in runs if q['kind'] == 'solid']
            if sol:
                dist = np.min([np.where(hs < lo, lo - hs, np.where(hs > hi, hs - hi, 0.0)) for lo, hi in sol], axis=0)
                row['low_rays_distance_to_solid_mm'] = dict(
                    q10=round(float(np.percentile(dist, 10)) * 1e3, 1), q50=round(float(np.percentile(dist, 50)) * 1e3, 1),
                    q90=round(float(np.percentile(dist, 90)) * 1e3, 1), max=round(float(dist.max()) * 1e3, 1),
                    share_within_15mm=round(float(np.mean(dist <= 0.015)), 3))
            rr = np.array([R_out[i, j] for i, j in k]); rm = np.array([med_out[i] for i, j in k])
            row['low_rays_rout_over_median'] = dict(q10=round(float(np.percentile(rr / rm, 10)), 3),
                                                    q50=round(float(np.percentile(rr / rm, 50)), 3))
        out['runs'].append(row)
    lay = CP.build_layout(prof, a.n_s, 'b1', {})
    pcs = lay.get('pieces') or []
    walls = [p for p in pcs if p.get('kind') == 'wall']
    out['layout'] = dict(n_s=a.n_s, base='b1', n_r=lay.get('n_r'), ring_cm3=round(lay.get('ring_cm3', 0.0), 3),
                         min_wall_mm=lay.get('min_wall_mm'), dropped_negative_wall=lay.get('dropped_negative_wall'),
                         pieces=[dict({k: (round(v, 5) if isinstance(v, float) else v) for k, v in p.items()
                                       if isinstance(v, (int, float, str)) or v is None},
                                      wall_min_mm=round(CP.piece_wall_min(p) * 1e3, 2)) for p in walls[:40]])
    with open(a.out, 'w') as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != 'layout'}, default=str)[:4000])
    print(json.dumps(out['layout'], default=str)[:3000])


if __name__ == '__main__':
    main()
