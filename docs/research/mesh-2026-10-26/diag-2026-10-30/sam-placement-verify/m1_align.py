"""M1 [D]: display alignment magnitudes and direction; scan glb vs kit cache frame."""
import glob, numpy as np
from vlib import *
from scipy.spatial import cKDTree
print('kit symmetric objects:', kit_sym())
for obj in EPS:
    v, f = load_scan(obj)
    z = np.load(f'{SCR}/interact/v5/metric/cache/{obj}_b4096.npz')
    d = cKDTree(sample(v, f, 20000, 1)).query(z['v'])[0]
    print(f'{obj:18s} scan glb vs kit cache: max vert->glb surf {d.max()*1e3:.2f} mm, ext_cm {np.round(np.ptp(v,0)*100,1)}')
files = sorted(glob.glob(f'{SCR}/obs/*_align.npz') + glob.glob(f'{SCR}/page/align/*_align.npz'))
for fn in files:
    a = np.load(fn); R, t = a['R'], a['t']
    name = fn.split('/')[-1].replace('_align.npz', '')
    ep, obj = name.split('_', 1)
    if obj not in EPS: 
        print(name, 'skip'); continue
    v, f = load_scan(obj)
    sc = sample(v, f, 30000, 2); ts = cKDTree(sc)
    obs = np.load(f'{SCR}/obs_all/{ep}_{obj}.npz')['pts'] if os.path.exists(f'{SCR}/obs_all/{ep}_{obj}.npz') else np.load(f'{SCR}/obs/{ep}_{obj}.npz')['pts']
    rng = np.random.default_rng(0); O = obs[rng.choice(len(obs), min(20000, len(obs)), replace=False)]
    d_id = ts.query(O)[0]; d_fw = ts.query(O @ R.T + t)[0]; d_bw = ts.query((O - t) @ R)[0]
    lev = np.ptp(sc, 0).max() / 2
    print(f'{name:28s} rot {rot_angle(R):5.2f} deg |t| {np.linalg.norm(t)*1e3:5.2f} mm  (max motion at half-extent {lev*math.radians(rot_angle(R))*1e3+np.linalg.norm(t)*1e3:5.1f} mm) '
          f'obs->scan median mm: identity {np.median(d_id)*1e3:.2f} | R p+t {np.median(d_fw)*1e3:.2f} | R^T(p-t) {np.median(d_bw)*1e3:.2f}; frac>10mm id {np.mean(d_id>0.01):.2f} aligned {np.mean(d_fw>0.01):.2f}')
