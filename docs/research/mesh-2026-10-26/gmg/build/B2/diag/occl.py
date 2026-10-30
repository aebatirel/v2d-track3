"""Diagnostic (dev, GT-free): distribution of (reprojected depth - target front depth) inside the target footprint."""
import sys, time, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, bundle as BU, gen_inputs as GI
S = guard.CFG['data']
ep = int(sys.argv[1]); ks = [int(x) for x in sys.argv[2].split(',')]
BU._sigma = lambda obs, fr: (0.001, {'stub': True})
b = BU.from_obs_all(ep)
geo = GI.camera_geometry(f'{S}/data/calib.json')
H = guard.load_npz(f'{S}/data/sweep/ep{ep}/hands.npz', 'dev_hands')
D = np.load(guard.open_input(f'{S}/cache/depth/public/ep{ep}/depths_fs0.5.npy', 'depth'), mmap_mode='r')
for k in ks:
    L = GI.frame_layers(b, k, geo, H, D)
    for o in b.objects:
        S_ = L.fp[o]
        ok = S_ & L.valid & np.isfinite(L.zf[o])
        d = (L.depth_z[ok] - L.zf[o][ok]) * 1000
        if not len(d):
            continue
        q = np.percentile(d, [1, 5, 25, 50, 75, 95, 99])
        print(ep, k, o, 'n', ok.sum(), 'of', S_.sum(), 'pct(1,5,25,50,75,95,99) mm', np.round(q, 1),
              'frac < -10mm %.3f  < -20mm %.3f  < -30mm %.3f' % ((d < -10).mean(), (d < -20).mean(), (d < -30).mean()))
