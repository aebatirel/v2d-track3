"""C2/P lathe parameters per source (PREREG.md section 3; C0b PREREG 3.3, 3.5, 3.7 applied to the pitcher).
  app_d       = 3 sigma (gmg A.2 sigma of the source's observations; merged: median of the episodes' sigma);
  t_fallback  = thickness chain: gmg thickness.py median of the source's two-sided measurements if >= 200 (merged:
                pooled), else t0_C0b (the C0b box's results/t0_c0b.json, store run mesh-20261031-c0b-00e8584, if it is
                fittable and present in W/t0_c0b.json), else -1 (lathe_obs.py then FAILS if it needs the fallback);
                clamped to [1.5, 8] mm. Used by lathe_obs.py only when fewer than 3 two-wall bins are measured.
  fixed       = --tie 1.0 --floor base_t --tmax 0.008 --tmin 0.0015 (C0b lathe_args).
Usage: params_p.py W      (writes W/params_p.json)
"""
import json, os, sys
import numpy as np

W = sys.argv[1]
CLAMP = (0.0015, 0.008)
MIN_MEAS = 200
t0 = None
t0src = 'absent'
if os.path.exists(f'{W}/t0_c0b.json'):
    j = json.load(open(f'{W}/t0_c0b.json'))
    if j.get('fittable'):
        t0, t0src = float(np.clip(j['t0_m'], *CLAMP)), 't0_C0b (C0b box)'
    else:
        t0src = 't0_C0b not fittable'


def chain(rows):
    T = np.concatenate([np.load(r) for r in rows])
    T = T[np.isfinite(T)]
    if len(T) >= MIN_MEAS:
        return float(np.clip(np.median(T), *CLAMP)), f'thickness.py (n={len(T)})'
    if t0 is not None:
        return t0, f'{t0src} (thickness.py n={len(T)} < 200)'
    return -1.0, f'none: thickness.py n={len(T)} < 200 and {t0src}; lathe fails if it needs the fallback'


sig = {e: json.load(open(f'{W}/sigma/ep{e}_water_pitcher.json'))['sigma_m'] for e in (21, 22)}
th = {e: f'{W}/thick/ep{e}_water_pitcher.npy' for e in (21, 22)}
out = dict(t0_c0b_m=t0, t0_src=t0src, clamp_m=list(CLAMP), targets={})
srcs = {'ep21': ([21], f'{W}/pts/B/ep21_water_pitcher.npz'), 'ep22': ([22], f'{W}/pts/B/ep22_water_pitcher.npz'),
        'merged': ([21, 22], f'{W}/pts/M/merged_water_pitcher.npz')}
for s, (eps, obs) in srcs.items():
    sg = float(np.median([sig[e] for e in eps]))
    t, tsrc = chain([th[e] for e in eps])
    args = ['--tie', '1.0', '--floor', 'base_t', '--t_fallback', f'{t:.6g}', '--tmax', '0.008', '--tmin', '0.0015',
            '--app_d', f'{3 * sg:.6g}']
    out['targets'][s] = dict(obs=obs, episodes=eps, sigma_m=sg, app_d_m=3 * sg, t_fallback_m=t, t_src=tsrc, lathe_args=args)
json.dump(out, open(f'{W}/params_p.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
