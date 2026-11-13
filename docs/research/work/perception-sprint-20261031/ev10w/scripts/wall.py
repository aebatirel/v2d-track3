"""Measured cavity radius, outer radius and wall thickness of a carved blue cup about its LATHE axis (DIAGNOSTIC).
For each axial height s (2 mm steps, reported as the diagnostic height h = -z of the axis point) and 72 azimuths, a ray
in the plane perpendicular to the axis from the axis outward (0.1 mm steps): inner = first radius inside a piece,
outer = last; wall = the solid length along the ray (inside samples x step). Reports per height the median/min inner,
median outer and min wall over azimuths, and over the band h < H_LO: min wall, median wall.
Usage: wall.py CARVE_DIR BLUE_PROFILE.npz OUT.json"""
import sys, glob, json, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
C, pb, outp = sys.argv[1:4]
B = np.load(pb); c0, d, e1, e2 = (np.asarray(B[k], float) for k in ('c0', 'd', 'e1', 'e2'))
U = I.Union(sorted(glob.glob(f'{C}/blue_cup/piece_*.obj')))
ang = np.linspace(0, 2 * np.pi, 72, endpoint=False); rs = np.arange(0.020, 0.050, 0.0001)
rows = []
for s in np.arange(-0.0836, 0.0764 + 1e-9, 0.002):
    X = np.stack([c0 + s * d + rs[:, None] * (np.cos(a) * e1 + np.sin(a) * e2) for a in ang])
    ins = (U.depth_lb(X.reshape(-1, 3)) > 0).reshape(len(ang), len(rs))
    if not ins.any(1).all():                                         # a ray with no solid: a hole through the wall
        rows.append(dict(s_mm=round(s * 1e3, 1), h_diag_mm=round(-(c0[2] + s * d[2]) * 1e3, 1), hole=True,
                         azimuths_without_solid=int((~ins.any(1)).sum())))
        continue
    inner = np.array([rs[np.argmax(r)] for r in ins]); outer = np.array([rs[len(r) - 1 - np.argmax(r[::-1])] for r in ins])
    wall = ins.sum(1) * 1e-4
    rows.append(dict(s_mm=round(s * 1e3, 1), h_diag_mm=round(-(c0[2] + s * d[2]) * 1e3, 1), inner_med_mm=round(float(np.median(inner)) * 1e3, 2),
                     inner_min_mm=round(float(inner.min()) * 1e3, 2), outer_med_mm=round(float(np.median(outer)) * 1e3, 2),
                     wall_min_mm=round(float(wall.min()) * 1e3, 2), wall_med_mm=round(float(np.median(wall)) * 1e3, 2)))
band = lambda lo, hi: [r for r in rows if lo <= r['h_diag_mm'] < hi and not r.get('hole')]
summ = {}
for lab, lo, hi in (('h<-47.4 (widened band)', -86, -47.4), ('-47.4<=h<-40', -47.4, -40), ('h>=-40', -40, 100)):
    b = band(lo, hi)
    if b:
        summ[lab] = dict(wall_min_mm=min(r['wall_min_mm'] for r in b), wall_med_mm=float(np.median([r['wall_med_mm'] for r in b])),
                         inner_med_mm=dict(min=min(r['inner_med_mm'] for r in b), max=max(r['inner_med_mm'] for r in b)))
summ['holes'] = [r for r in rows if r.get('hole')]
json.dump(dict(carve=C, rows=rows, summary=summ), open(outp, 'w'), indent=1)
print(json.dumps(summ))
for r in rows:
    if r['h_diag_mm'] < -30 or r.get('hole'):
        print(r)
