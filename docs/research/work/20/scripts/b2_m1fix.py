# Stage B re-run: repair M1's depth in held-scan records geometrically. M2, M3 (b/c NCC 0.98-0.99) are trusted; M1 lies on its
# cam-a ray (through the detected centre) at |M1 - M2| = 53.0 mm, root chosen by |M1 - M3| ~ 194.2 mm. Reports the depth change,
# the repaired triangle's frontalness (normal . view) and the axis-vs-view angle. Usage: b2_m1fix.py <ep> [ep ...]
# Validation mode: b2_m1fix.py --rest <ep>  (compares with Stage B's table-constrained M1 in meas_e<ep>.json)
import sys, json, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
R_a2c = R.T @ Rab; t_a2c = R.T @ (tab - T.ravel()); R_a2r = R1 @ R_a2c; t_a2r = R1 @ t_a2c
def ray(uv): d = undist_a_pts(np.array([uv])) @ R_a2r.T; d = d[0] / np.linalg.norm(d[0]); return t_a2r, d
def fix(M, uv1):
    A, d = ray(uv1); best = None
    for target in (0.0530,):
        b = 2 * d @ (A - M[1]); c = (A - M[1]) @ (A - M[1]) - target ** 2; disc = b * b - 4 * c
        if disc < 0: return None
        for t in ((-b - np.sqrt(disc)) / 2, (-b + np.sqrt(disc)) / 2):
            X = A + t * d; e = abs(np.linalg.norm(X - M[2]) - 0.1942)
            if best is None or e < best[0]: best = (e, X)
    return best
def front(M):
    nrm = np.cross(M[1] - M[0], M[2] - M[0]); nrm /= np.linalg.norm(nrm); v = M.mean(0) - t_a2r; v /= np.linalg.norm(v)
    ax = M[2] - 0.5 * (M[0] + M[1]); ax /= np.linalg.norm(ax); return abs(nrm @ v), abs(ax @ v)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if '--rest' in sys.argv:
    for ep in map(int, args):
        H = {json.loads(l)['k']: json.loads(l) for l in open(f'/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/held_e{ep}.jsonl')}
        for r in json.load(open(f'{OUT}/meas_e{ep}.json')):
            if r.get('M_r') is None or r['k'] not in H or 'uv' not in H[r['k']]: continue
            Mt = np.array(r['M_r']); h = H[r['k']]; Mf = np.array(h['M_r']); fx = fix(Mf, h['uv'][0])
            if fx is None: print(ep, r['k'], 'no root'); continue
            print(f"e{ep} k{r['k']}: M1 table-constrained vs free {1e3*np.linalg.norm(Mt[0]-Mf[0]):5.1f} mm, vs repaired {1e3*np.linalg.norm(Mt[0]-fx[1]):5.1f} mm "
                  f"(|M1M3| err {1e3*fx[0]:.1f}) | M2 diff {1e3*np.linalg.norm(Mt[1]-Mf[1]):.1f} M3 diff {1e3*np.linalg.norm(Mt[2]-Mf[2]):.1f} | front table {front(Mt)[0]:.3f} free {front(Mf)[0]:.3f} repaired {front(np.array([fx[1], Mf[1], Mf[2]]))[0]:.3f}")
    sys.exit()
for ep in map(int, args):
    for l in open(f'/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/held_e{ep}.jsonl'):
        h = json.loads(l)
        if 'M_r' not in h: continue
        Mf = np.array(h['M_r']); fx = fix(Mf, h['uv'][0])
        if fx is None: continue
        Mr = np.array([fx[1], Mf[1], Mf[2]]); fr, av = front(Mr)
        rec = dict(ep=ep, k=h['k'], front_free=h['tri_n_dot_view'], front_fix=float(fr), ax_view=float(av), dM1_mm=float(1e3 * np.linalg.norm(fx[1] - Mf[0])),
                   m13_err_mm=float(1e3 * fx[0]), ncc=h['ncc'], speed=h['speed_px'], wood=h.get('wood_frac'))
        print(json.dumps(rec))
