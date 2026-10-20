import json, glob, numpy as np
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b'
rows = []
print('ep  k |  d12   d23   d13 |  h1    h2    h3  | h2-h1 | ncc1 ncc2 ncc3 | wd1 wd2 wd3')
for e in [3, 5, 6, 15, 16, 32, 33, 35, 36, 37]:
    for r in json.load(open(f'{OUT}/meas_e{e}.json')):
        if not r.get('triple'): continue
        tr = r['triple']; M = np.array(r['M_r']) * 1e3; c = [r['cands'][j] for j in tr[1:4]]
        d = [np.linalg.norm(M[0] - M[1]), np.linalg.norm(M[1] - M[2]), np.linalg.norm(M[0] - M[2])]
        if not (45 < d[0] < 62 and 145 < d[1] < 160 and 185 < d[2] < 202): continue
        h = r['h_mm']; rows.append([e, r['k'], *d, *h])
        print(f"{e:3d} {r['k']} | {d[0]:5.1f} {d[1]:5.1f} {d[2]:5.1f} | {h[0]:5.1f} {h[1]:5.1f} {h[2]:5.1f} | {h[1]-h[0]:+5.1f} | "
              f"{c[0]['ncc']:.2f} {c[1]['ncc']:.2f} {c[2]['ncc']:.2f} | {c[0]['wdepth_mm']:.0f} {c[1]['wdepth_mm']:.0f} {c[2]['wdepth_mm']:.0f}")
R = np.array(rows)
print('all: d12 %.1f+-%.1f d23 %.1f+-%.1f d13 %.1f+-%.1f | h1 %.1f+-%.1f h2 %.1f+-%.1f h3 %.1f+-%.1f | h2-h1 %.1f+-%.1f (n %d)' % (
    *[v for j in (2, 3, 4, 5, 6, 7) for v in (R[:, j].mean(), R[:, j].std())], (R[:, 6] - R[:, 5]).mean(), (R[:, 6] - R[:, 5]).std(), len(R)))
for e in np.unique(R[:, 0]):
    m = R[:, 0] == e; print(f'  e{int(e)}: h1 {R[m,5].mean():5.1f} h2 {R[m,6].mean():5.1f} h3 {R[m,7].mean():5.1f} h2-h1 {(R[m,6]-R[m,5]).mean():+5.1f} (sd {(R[m,6]-R[m,5]).std():.1f}, n {m.sum()}) d12 {R[m,2].mean():.1f}')
np.save(f'{OUT}/sum1.npy', R)
