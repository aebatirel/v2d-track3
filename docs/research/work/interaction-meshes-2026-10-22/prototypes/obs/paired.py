import json, numpy as np
A = json.load(open('slotlook.json')); B = json.load(open('slotlook_ctrl.json')); out = {}
for k in A:
    ra = {r['t']: r for r in A[k]['rows']}; rb = {r['t']: r for r in B[k]['rows']}
    ts = sorted(set(ra) & set(rb))
    for name, cond in (('face-on inc<50', lambda r: r['inc'] < 50), ('oblique 50-80', lambda r: 50 <= r['inc'] < 80), ('edge-on >=80', lambda r: r['inc'] >= 80)):
        tt = [t for t in ts if cond(ra[t])]
        da = np.array([ra[t]['med_excess_mm'] for t in tt], float); db = np.array([rb[t]['med_excess_mm'] for t in tt], float)
        ok = np.isfinite(da) & np.isfinite(db) & (np.abs(da) < 60) & (np.abs(db) < 60)
        if ok.sum() < 3:
            continue
        dd = da[ok] - db[ok]; T = np.array(tt)[ok]
        r = dict(n=int(ok.sum()), frames=f'{T.min()}-{T.max()}', slot_med=round(float(np.median(da[ok])), 1), ctrl_med=round(float(np.median(db[ok])), 1),
                 diff_med=round(float(np.median(dd)), 1), diff_iqr=[round(float(np.percentile(dd, 25)), 1), round(float(np.percentile(dd, 75)), 1)],
                 frames_diff_gt4mm=int((dd > 4).sum()), inc_med=round(float(np.median([ra[t]['inc'] for t in T])), 0),
                 az_med=round(float(np.median([ra[t]['az'] for t in T])), 0), px_med=round(float(np.median([ra[t]['px'] for t in T])), 1))
        out[f'{k} {name}'] = r; print(k, name, json.dumps(r))
json.dump(out, open('slotlook_paired.json', 'w'), indent=1)
