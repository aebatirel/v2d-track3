# Debris re-draw test. mode "prep": write each listed part (original) and a copy rotated by ANG deg about the x axis
# (the rotation would be compensated by the <collision><origin rpy>, which FlashCHORD keeps for every hull, A3) into
# c2/rd/. mode "run": exact FlashCHORD CoACD call (macOS wheel) on every c2/rd/*.npz input -> c2/rd/mac/.
# mode "stat": min hull volumes and counts for c2/rd/mac and c2/rd/lin (Linux results written by c/c_lincoacd.py).
import sys, os, glob, time, numpy as np
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19'
RD = W + '/c2/rd'
PARTS = ['b/S120/plastic_dish_rack/plastic_dish_rack_p009', 'b/S60/white_pot_lid/white_pot_lid_p000',
         'b/S60/blue_cup/blue_cup_p007', 'b/S60/beige_cup/beige_cup_p000']
mode = sys.argv[1]
if mode == 'prep':
    ang = float(sys.argv[2]); os.makedirs(RD, exist_ok=True)
    a = np.deg2rad(ang); R = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    for p in PARTS:
        d = np.load(f'{W}/{p}.npz'); nm = os.path.basename(p)
        np.savez(f'{RD}/{nm}_r0.npz', v=d['v'], f=d['f'])
        np.savez(f'{RD}/{nm}_r{ang:g}.npz', v=d['v'] @ R.T, f=d['f'])
    print('prepared', sorted(os.listdir(RD)))
elif mode == 'run':
    sys.path.insert(0, W + '/../15-verify/pylib11'); import coacd
    os.makedirs(RD + '/mac', exist_ok=True)
    for p in sorted(glob.glob(RD + '/*.npz')):
        o = RD + '/mac/' + os.path.basename(p)
        if os.path.exists(o): continue
        d = np.load(p); t = time.time()
        parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d['v'], dtype=np.float64), np.ascontiguousarray(d['f'], dtype=np.int64)),
                                threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
        np.savez(o, n=len(parts), **{f'v{i}': np.asarray(q[0]) for i, q in enumerate(parts)}, **{f'f{i}': np.asarray(q[1]) for i, q in enumerate(parts)})
        print('RESULT', os.path.basename(p), 'hulls', len(parts), 'sec %.0f' % (time.time() - t), flush=True)
else:
    from scipy.spatial import ConvexHull
    def vol(v):
        try: return ConvexHull(v).volume
        except Exception: return 0.0
    for plat in ['mac', 'lin']:
        for f in sorted(glob.glob(f'{RD}/{plat}/*.npz')):
            d = np.load(f); n = int(d['n']); vv = np.sort([vol(d[f'v{i}']) for i in range(n)])
            print(f'{plat} {os.path.basename(f):34s} hulls {n:4d} min vol {vv[0]:.2e} 2nd {vv[1]:.2e} n<1e-12 {(vv<1e-12).sum()} n<1e-15 {(vv<1e-15).sum()}')
