import sys, json, numpy as np
R = [(0, 37), (38, 46), (47, 99), (100, 117), (118, 160)]
for p in sys.argv[1:]:
    Z = np.load(p); H = json.load(open(p[:-4] + '.json')); names = [str(x) for x in Z['objects']]
    print('==', p.split('/')[-1], 'flags', [f[:90] for f in H['flags']], 'counts', H['counts'], 'checks', {k: v for k, v in H['checks'].items() if k != 'fiducial_box'})
    fr, tg, pa, dep = Z['frame'], Z['target'], Z['partner'], Z['depth_m']
    fpF, fpT, vol = Z['fp_frame'], Z['fp_target'], Z['intr_vol_m3']
    T = H['frames']
    for t in range(2):
        for a, b in R + [(161, 10**6)]:
            m = (fr >= a) & (fr <= b) & (tg == t); r = (fpF >= a) & (fpF <= b) & (fpT == t) & (vol > 0)
            if a >= T:
                continue
            nf = len(np.unique(fpF[r]))
            if nf == 0:
                print(f'  {names[1-t]} in {names[t]} f{a}-{b}: 0 frames'); continue
            # per-frame max depth then stats
            fmax = np.array([dep[m & (fr == f)].max() for f in np.unique(fr[m])])
            print(f'  {names[1-t]} in {names[t]} f{a}-{b}: frames {nf}, depth max {dep[m].max()*1e3:.1f} mm, median(all samples) {np.median(dep[m])*1e3:.1f} mm, median per-frame max {np.median(fmax)*1e3:.1f}; vol max {vol[r].max()*1e6:.1f} cm3 median {np.median(vol[r])*1e6:.1f}')
