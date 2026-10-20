"""Analyse registration residuals: per-frame consistency (camera error) vs per-observation scatter (detection)."""
import sys, json, numpy as np
import lib17 as L
ep = int(sys.argv[1]); q = json.load(open(f'out/reg_{ep}.json')); gt = L.load_gt(ep)
rows = []
for (t, c, j, k, u, v) in q['obs']:
    cm = q['cams'][t]; R, C = np.array(cm['Rwc']), np.array(cm['C'])
    X = L.markers_world(gt, t, j)[k]; p, z = L.project(X[None], R, C, c)
    rows.append((t, c, j, k, u - p[0, 0], v - p[0, 1], z[0]))
r = np.array([(a[0], 'abc'.index(a[1]), a[2], a[3], a[4], a[5], a[6]) for a in rows], float)
for ci, c in enumerate('abc'):
    m = r[:, 1] == ci
    if not m.any(): continue
    du, dv = r[m, 4], r[m, 5]
    print(f'cam {c}: n {m.sum()} mean resid (u,v) px ({du.mean():+.2f},{dv.mean():+.2f}) sd ({du.std():.2f},{dv.std():.2f}); |res| med {np.median(np.hypot(du,dv)):.2f}')
    # within-frame consistency: frames with >= 2 obs
    fr = np.unique(r[m, 0]); wf = []; bf = []
    for t in fr:
        mm = m & (r[:, 0] == t)
        if mm.sum() >= 2: wf.append(np.c_[r[mm, 4] - r[mm, 4].mean(), r[mm, 5] - r[mm, 5].mean()]); bf.append([r[mm, 4].mean(), r[mm, 5].mean()])
    if wf:
        wf = np.concatenate(wf); bf = np.array(bf)
        print(f'   within-frame scatter sd ({wf[:,0].std():.2f},{wf[:,1].std():.2f}) [n {len(wf)}]; frame-mean sd ({bf[:,0].std():.2f},{bf[:,1].std():.2f}) [frames {len(bf)}]')
    # per object/marker mean
    for j in np.unique(r[m, 2]):
        for k in np.unique(r[m & (r[:, 2] == j), 3]):
            mm = m & (r[:, 2] == j) & (r[:, 3] == k)
            print(f'   {gt["names"][int(j)][:10]} m{int(k)} n {mm.sum():3d} mean ({r[mm,4].mean():+.2f},{r[mm,5].mean():+.2f}) sd ({r[mm,4].std():.2f},{r[mm,5].std():.2f}) depth {r[mm,6].mean():.2f}')
