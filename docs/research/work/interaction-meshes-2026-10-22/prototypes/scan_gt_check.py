"""DIAGNOSTIC sanity check: public scans posed by mocap (reliable-solid scans only). Real objects cannot overlap, so this
measures the floor of the method (mocap noise, scan error, deformation such as bristles)."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_gtdiag as G, census1 as C
res = {}
for ep in map(int, sys.argv[1:]):
    names = json.load(open(f'{C.S}/loc/perc/ep{ep}/result.json'))['objects']
    gp, _ = G.gt_poses(ep, names)
    A, B = C.load_obj(names[0], 'scan'), C.load_obj(names[1], 'scan')
    ov, pen, ds = [], [], []
    for t in range(len(gp[names[0]])):
        if not (np.isfinite(gp[names[0]][t]).all() and np.isfinite(gp[names[1]][t]).all()):
            ov.append(np.nan); pen.append(np.nan); ds.append(np.nan); continue
        Tab = np.linalg.inv(gp[names[1]][t]) @ gp[names[0]][t]
        iA, dA, _ = C.inside(A, B, Tab); iB, dB, _ = C.inside(B, A, np.linalg.inv(Tab))
        ov.append(0.5 * (len(iA) + len(iB)) * C.H3); pen.append(max(dA.max() if len(dA) else 0, dB.max() if len(dB) else 0) * 1e3)
        ds.append(C.surf_dist(A, B, Tab) * 1e3)
    ov, pen, ds = map(np.array, (ov, pen, ds))
    res[ep] = dict(max_ov_cm3=float(np.nanmax(ov)), f=int(np.nanargmax(ov)), frames_gt1=int(np.nansum(ov > 1)),
                   contact_lt5mm=int(np.nansum(ds < 5)), max_pen_mm=float(np.nanmax(pen)),
                   ov_median_contact=float(np.nanmedian(ov[ds < 5])) if np.nansum(ds < 5) else None)
    print(ep, res[ep], flush=True)
json.dump(res, open(f'{C.OUT}/scan_mocap_check.json', 'w'), indent=1)
