"""Summarise stage-2 cameras: per-marker mean offsets (systematic marker-model or GT error), within-frame vs frame-mean
scatter, LOMO in mm, VO drift corrections, and camera-motion stats."""
import sys, json, numpy as np, cv2
import lib17 as L
ep = int(sys.argv[1]); q = json.load(open(f'out/reg2_{ep}.json')); gt = L.load_gt(ep); FA = L.cam('a')[0][0, 0]
cams = {'a': q['cams'], 'b': q['cams_b'], 'c': q['cams_c']}
rows = []
for (t, c, j, k, u, v, z) in q['obs']:
    R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); X = L.markers_world(gt, t, j)[k]
    p, _ = L.project(X[None], R, C, c, own=True); sc = FA / L.cam(c)[0][0, 0]
    rows.append((t, 'abc'.index(c), j, k, (u - p[0, 0]) * sc, (v - p[0, 1]) * sc, z))
r = np.array(rows)
print(f'ep {ep}: obs {len(r)}; in-sample |res| med {np.median(np.hypot(r[:,4],r[:,5])):.2f} px (a-eq)')
for j in np.unique(r[:, 2]).astype(int):
    for k in np.unique(r[r[:, 2] == j, 3]).astype(int):
        m = (r[:, 2] == j) & (r[:, 3] == k)
        mu = r[m, 4:6].mean(0); mm = np.linalg.norm(mu) * r[m, 6].mean() / FA * 1000
        print(f'   {gt["names"][j][:14]:14s} m{k} n {m.sum():3d} mean offset ({mu[0]:+.2f},{mu[1]:+.2f}) px = {mm:.2f} mm; sd ({r[m,4].std():.2f},{r[m,5].std():.2f}) px; depth {r[m,6].mean():.2f} m; cams {sorted(set("abc"[int(x)] for x in r[m,1]))}')
wf, fm = [], []
for t in np.unique(r[:, 0]):
    m = (r[:, 0] == t) & (r[:, 1] == 0)
    if m.sum() >= 2: wf.append(r[m, 4:6] - r[m, 4:6].mean(0)); fm.append(r[m, 4:6].mean(0))
if wf:
    wf = np.concatenate(wf); fm = np.array(fm)
    print(f'   cam a within-frame scatter sd ({wf[:,0].std():.2f},{wf[:,1].std():.2f}) px; frame-mean sd ({fm[:,0].std():.2f},{fm[:,1].std():.2f}) px over {len(fm)} frames')
if 'lomo' in q:
    lo = np.array([(a[4], a[5], a[6]) for a in q['lomo']]); e = np.hypot(lo[:, 0], lo[:, 1]); mm = e * lo[:, 2] / FA * 1000
    print(f'   LOMO n {len(lo)}: px med {np.median(e):.2f} p90 {np.percentile(e,90):.2f}; mm med {np.median(mm):.2f} p90 {np.percentile(mm,90):.2f}; depth range {lo[:,2].min():.2f}-{lo[:,2].max():.2f} m')
# camera trajectory stats
C = np.array([c['C'] for c in q['cams']]); R = np.array([c['Rwc'] for c in q['cams']])
ang = [np.degrees(np.linalg.norm(cv2.Rodrigues(R[0].T @ x)[0])) for x in R]
print(f'   cam a: centre at f0 {np.round(C[0],3)}, heading {np.degrees(np.arctan2(R[0][1,2],R[0][0,2])):.2f} pitch {-np.degrees(np.arcsin(R[0][2,2])):.2f}; max rot from f0 {max(ang):.1f} deg; path range mm {np.round(np.ptp(C,0)*1000)}')
# coverage: frames with >= 1 / >= 3 static-marker observations (any cam), longest gap without observations
T = len(q['cams']); cnt = np.zeros(T, int)
for o in q['obs']: cnt[o[0]] += 1
gaps, g = [], 0
for t in range(T):
    if cnt[t] == 0: g += 1
    else:
        if g: gaps.append(g)
        g = 0
if g: gaps.append(g)
print(f'   coverage: frames with >=1 obs {np.mean(cnt>=1):.2f}, >=3 obs {np.mean(cnt>=3):.2f}; longest gap {max(gaps) if gaps else 0} frames; delta(a vs b) {q["delta"]:.3f}')
