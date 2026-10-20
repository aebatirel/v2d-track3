"""Up axis (world z expressed in object frame) at frame 0 and over episode, from public GT."""
import numpy as np, pandas as pd, json
from scipy.spatial.transform import Rotation as R
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000'
EPS = [0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45]
NAMES = ['blue_cup','beige_cup','white_pot_lid','white_pot','water_pitcher']
res = {n: [] for n in NAMES}
for e in EPS:
    df = pd.read_parquet(f'{D}/episode_{e:06d}.parquet', columns=['observation.objects'])
    objs0 = df['observation.objects'].iloc[0]
    for k, o in enumerate(objs0):
        n = o['name']
        if n not in res: continue
        Ps = np.array([list(df['observation.objects'].iloc[t][k]['pose']) for t in range(len(df))])
        q = Ps[:, [4, 5, 6, 3]]  # x y z w
        Rm = R.from_quat(q).as_matrix()
        up = Rm[:, 2, :]          # row 2 of R = world z in object coords
        res[n].append(dict(ep=e, slot=k, up0=up[0].round(3).tolist(), z0=float(Ps[0, 2]),
                           upmin=float(np.abs(up[:, :] @ up[0]).min())))
for n in NAMES:
    print(n)
    for r in res[n]: print('  ep', r['ep'], 'slot', r['slot'], 'up0', r['up0'], 'z0 %.3f' % r['z0'], 'min cos(up_t, up_0) %.2f' % r['upmin'])
json.dump(res, open('out/upaxis.json', 'w'), indent=1)
