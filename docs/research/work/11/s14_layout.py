"""Staging-line test: bearing (mod 180) of the inter-object vector at start for every 2-object public episode with
separated objects (>8 cm). If people stage objects along the table edge, these bearings reveal the table axis in the
mocap world and its constancy across tasks/sessions. Research only."""
from c11 import *
import json
rows = []
for ep in PUBLIC:
    e = load_episode(ep); nm = e['names']
    if len(nm) < 2: continue
    for f, tag in ((0, 'start'), (-1, 'end')):
        d = e['pose'][f, 1, :2] - e['pose'][f, 0, :2]; L = np.linalg.norm(d)
        b = float(np.degrees(np.arctan2(d[1], d[0])))
        rows.append(dict(ep=ep, task=e['task'], when=tag, pair=nm, dist_cm=round(L * 100, 1), bearing=round(b, 1),
                         mod180=round(float(b % 180), 1), plusy=nm[1] if d[1] > 0 else nm[0]))
for r in rows: print(r)
s = [r['mod180'] for r in rows if r['when'] == 'start' and r['dist_cm'] > 8]
s2 = np.radians(np.array(s) * 2); m = np.degrees(np.angle(np.exp(1j * s2).mean())) / 2 % 180
print('start, separated pairs: n', len(s), 'mod180', s, 'axial mean', round(m, 1), 'rms', round(float(np.sqrt(np.mean(((np.array(s) - m + 90) % 180 - 90) ** 2))), 1))
json.dump(rows, open('s14_layout.json', 'w'), indent=1)
