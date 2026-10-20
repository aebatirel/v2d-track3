# Table-frame marker offsets relative to the stereo handle axis (rest, radial clips): axis = line fit of limb midpoints over the
# handle rows (paired far/near limbs per row), extrapolated to the marker stations. Output per (clip, frame).
import json, sys, numpy as np
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b'
rows = []
for tag, ks in (('e5', (0, 1, 2, 3)), ('e32', (0, 1, 2, 3))):
    for k in ks:
        try: J = json.load(open(f'{OUT}/estereo_{tag}_k{k}.json'))
        except FileNotFoundError: continue
        R = np.array([[r['y'], r['side'], r['s'], r['w'], r['h']] for r in J['rows']])
        sM, wM, hM = map(np.array, (J['s_markers'], J['w_markers'], J['h_markers']))
        # pair limbs per image row on the handle
        mids = []
        for y in np.unique(R[:, 0]):
            m = (R[:, 0] == y)
            if m.sum() != 2: continue
            a, b = R[m]
            if not (sM[1] + 20 < a[2] < sM[2] - 12): continue
            wd = abs(a[3] - b[3])
            if not 15 < wd < 25: continue
            mids.append([(a[2] + b[2]) / 2, (a[3] + b[3]) / 2, (a[4] + b[4]) / 2, wd / 2])
        if len(mids) < 10: continue
        Mi = np.array(mids); A = np.c_[np.ones(len(Mi)), Mi[:, 0]]
        cw = np.linalg.lstsq(A, Mi[:, 1], rcond=None)[0]; ch = np.linalg.lstsq(A, Mi[:, 2], rcond=None)[0]
        rw = Mi[:, 1] - A @ cw; rh = Mi[:, 2] - A @ ch
        aw = lambda s: cw[0] + cw[1] * s; ah = lambda s: ch[0] + ch[1] * s
        off = [(wM[i] - aw(sM[i]), hM[i] - ah(sM[i])) for i in range(3)]
        rows.append([int(tag[1:]), k, *[v for o in off for v in o], ch[0] + ch[1] * 0, ch[1] * 1e3, cw[1] * 1e3, np.median(Mi[:, 3])])
        print(f'{tag} k{k}: handle rows {len(Mi)} (s {Mi[:,0].min():.0f}..{Mi[:,0].max():.0f}) axis h(s=0) {ah(0):.1f} slope {ch[1]*1e3:+.1f} mm/m, w(s=0) {aw(0):+.1f} '
              f'slope {cw[1]*1e3:+.1f} mm/m, rho {np.median(Mi[:,3]):.1f}, res w/h {rw.std():.2f}/{rh.std():.2f} | '
              f'M1 (w {off[0][0]:+.1f}, h {off[0][1]:+.1f}) M2 (w {off[1][0]:+.1f}, h {off[1][1]:+.1f}) M3 (w {off[2][0]:+.1f}, h {off[2][1]:+.1f})')
R = np.array(rows); np.save(f'{OUT}/axisrel.npy', R)
print('mean: M1 w %+.1f h %+.1f | M2 w %+.1f h %+.1f | M3 w %+.1f h %+.1f | sd' % tuple(R[:, 2:8].mean(0)), np.round(R[:, 2:8].std(0), 1))
