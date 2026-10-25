import sys, numpy as np
sys.path.insert(0, '.')
from lathe_lib import *
L = '/home/user/v2d-track3/meshes/'
for name, path in [('blue_cup', L+'library_v3/blue_cup.glb'), ('beige_cup_v3', L+'library_v3/beige_cup.glb'),
                   ('beige_cup_v3x', L+'library_v3x/beige_cup.glb'), ('white_pot', L+'library_v3/white_pot.glb'),
                   ('white_pot_lid', L+'library_v3/white_pot_lid.glb'), ('water_pitcher', L+'library_v3/water_pitcher.glb')]:
    m = load(path); P, N = sample(m, 60000)
    c = P.mean(0); ev, V = np.linalg.eigh(np.cov((P - c).T))
    print('==', name, 'pca eig (cm^2)', np.round(ev * 1e4, 1))
    for k in range(3):
        d = V[:, k]
        c1, d1 = refine_axis(P, N, c, d)
        hc, Ro, Ri, h = profile(P, N, c1, d1, dh=0.005)
        ro = np.nanmedian(Ro, 1); cov = np.mean(np.isfinite(Ro), 1); covi = np.mean(np.isfinite(Ri), 1)
        # circularity: MAD of Ro over theta / median
        circ = np.nanmedian(np.abs(Ro - ro[:, None]), 1) / ro
        print(f' axis{k} d={np.round(d1,3)} c={np.round(c1*100,2)}cm  h[{h.min()*100:.1f},{h.max()*100:.1f}] median circ {np.nanmedian(circ):.3f}')
        if k == np.argmin([0,0,0]) or True:
            for i in range(len(hc)):
                ri = np.nanmedian(Ri[i]) if np.isfinite(Ri[i]).any() else np.nan
                print(f'   h {hc[i]*100:6.1f}  ro {ro[i]*100:5.2f} cov {cov[i]:.2f} circ {circ[i]:.3f} | ri {ri*100:5.2f} covi {covi[i]:.2f}')
