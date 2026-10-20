# Diagnostic: back-project b2_front's cam-a outline edges and limb axis onto b_geom's table-parallel plane (h = 7.2 mm) and
# compute b_geom's statistic (bowl midline vs handle line, table-plane mm, + toward M1) from OUR edges.
# Usage: b2_cmpgeom.py <ep> <k>   (rest frames; meas_e<ep>.json table plane)
import sys, json, numpy as np
a = [x for x in sys.argv[1:] if not x.startswith('--')]; sys.argv = ['b2_front.py', a[0], '--rest'] + [x for x in sys.argv[1:] if x.startswith('--')]
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b2_front.py').read().split('\nfor k in KS:')[0]
src = src.replace("    ok = [x for x in rows if x is not None]\n", "    ok = [x for x in rows if x is not None]; DUMP.update(ok=ok, o=o, es=es, en=en, mpu=mm_per_unit, sM=sM)\n")
src = src.replace("    cf = variants[best]; keep = both\n", "    cf = variants[best]; keep = both; DUMP.update(variants=variants, smm=smm, sMmm=sMmm, kL=kL, kR=kR)\n")
DUMP = {}; exec(compile(src, 'b2_front', 'exec'))
k = int(a[1]); res = measure(k); r = H[k]
c, n = np.array(r['plane_c']), np.array(r['plane_n']); M = np.array(r['M_r'])
o, es, en = DUMP['o'], DUMP['es'], DUMP['en']; ok = np.array(DUMP['ok'])
def bp(xy, h):        # cam-a normalised -> rect frame point on plane (table + h mm)
    d = np.c_[xy, np.ones(len(xy))] @ R_a2r.T; t = ((c + h * 1e-3 * n - t_a2r) @ n) / (d @ n); return t_a2r + t[:, None] * d
foot = lambda X: X - ((X - c) @ n)[..., None] * n
F = foot(M); O0 = 0.5 * (F[0] + F[1]); u = F[2] - O0; u /= np.linalg.norm(u); wv = np.cross(n, u)
if (M[0] - O0) @ wv < 0: wv = -wv                         # + toward M1
s_, l_, r_ = ok[:, 0], ok[:, 1], ok[:, 2]
vv = O0 - t_a2r; vh = vv - (vv @ n) * n; el = np.arcsin(-(vv @ n) / np.linalg.norm(vv)); azr = np.arctan2(vh @ wv, vh @ u)
aco, bco = np.sin(el), np.cos(el) * np.sin(azr); nrm_ = np.hypot(aco, bco)
print(f'e{ep} k{k}: elev {np.degrees(el):.1f} az {np.degrees(azr):+.1f} -> image-lateral = {aco/nrm_:.3f} w + {bco/nrm_:.3f} h ; cot {bco/aco:.3f}')
for h in (7.2, 8.5):
    PL = bp(o + s_[:, None] * es + l_[:, None] * en, h); PR = bp(o + s_[:, None] * es + r_[:, None] * en, h)
    Pm = 0.5 * (PL + PR); sw = np.c_[(Pm - O0) @ u, (Pm - O0) @ wv] * 1e3; wid = np.linalg.norm(PR - PL, axis=1) * 1e3
    Ms = np.c_[(M - O0) @ u, (M - O0) @ wv] * 1e3
    out = []
    for name, cf in DUMP['variants'].items():           # our limb axis back-projected onto the same plane
        A = bp(o + np.array([[-0.2], [0.2]]) * es + np.polyval(cf, np.array([-0.2, 0.2]))[:, None] * en, h)
        A2 = np.c_[(A - O0) @ u, (A - O0) @ wv] * 1e3; ch = np.polyfit(A2[:, 0], A2[:, 1], 1)
        bm = (wid > 30) & (sw[:, 0] < Ms[0, 0] - 30)
        bowl = np.median(sw[bm, 1]) - np.polyval(ch, np.median(sw[bm, 0]))
        # b_geom-style handle line from OUR midpoints (handle rows, width 12-30, M2+20 .. M3-12)
        hm = (wid > 12) & (wid < 30) & (sw[:, 0] > Ms[1, 0] + 20) & (sw[:, 0] < Ms[2, 0] - 12)
        ch2 = np.polyfit(sw[hm, 0], sw[hm, 1], 1) if hm.sum() > 10 else None
        bowl2 = np.median(sw[bm, 1]) - np.polyval(ch2, np.median(sw[bm, 0])) if ch2 is not None else np.nan
        lat = [Ms[j, 1] - np.polyval(ch, Ms[j, 0]) for j in range(3)]
        lat2 = [Ms[j, 1] - np.polyval(ch2, Ms[j, 0]) for j in range(3)] if ch2 is not None else [np.nan] * 3
        if name == 'midpts': out.append(f'midpts-axis: bowl {bowl:+.2f} markers ' + ' '.join(f'{x:+.1f}' for x in lat) + f' asym {lat[0]+lat[1]:+.1f} | tableplane-midpt-line: bowl {bowl2:+.2f} markers ' + ' '.join(f'{x:+.1f}' for x in lat2) + f' asym {lat2[0]+lat2[1]:+.1f}')
    print(f'e{ep} k{k} h {h}: ' + ' | '.join(out))
import os
gf = f'{OUT}/geom_e{ep}' + ('_end' if '--end' in sys.argv else '') + '.json'
g = [x for x in json.load(open(gf)) if x['k'] == k] if os.path.exists(gf) else []
if g: print('   h_mm(table):', np.round(r['h_mm'], 1), '| b_geom:', {h: (round(v['bowl_vs_handleline'], 2) if v['bowl_vs_handleline'] is not None else None, [round(x, 1) for x in v['lat_handle']]) for h, v in g[0]['per_h'].items() if h in ('5.0', '7.2', '10.0')})
