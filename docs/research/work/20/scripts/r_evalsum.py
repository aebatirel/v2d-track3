"""DIG 20 Stage C re-run: eval-clip summary of the GT-free detector (no eval GT exists). Compares the detector's
cam-a frames with the note-15 viewing reference (approximate, sampled every ~8 frames; design check only).
usage: r_evalsum.py -> out/c2/eval_summary.json"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
OUT2 = f'{L.ROOT}/work/20/out/c2'
REF = json.load(open(f'{OUT2}/eval_view_ref.json'))
rows = []
for ep in L.EV:
    key = f'e{ep}'; ref = REF[key]
    f = f'{OUT2}/run_{key}.npz'
    if not os.path.exists(f): print(key, 'not run'); continue
    d = json.loads(str(np.load(f)['dec'])); m = json.load(open(f'{OUT2}/pose0_{key}.json'))
    pk = m['peaks'][0] if 'peaks' in m else m['blobs'][0]
    pick = (f"tmpl s{pk['score']:.2f} dcol{pk['dcol']:.0f}" if 'peaks' in m else f"blob s{pk['score']:.2f} h{pk['h'] * 100:.0f} l{pk['l1'] * 100:.0f}")
    c0 = ref['contact'][0] if ref['contact'] else None; m0 = ref['motion'][0] if ref['motion'] else None
    ca = d['c_a']
    flag = []
    if d['empty']: flag.append('EMPTY')
    if m0 is not None and ca - 3 > m0 + 8: flag.append('LATE?')
    if d['C_a'] is not None and c0 is not None and d['C_a'] < c0 - 12: flag.append('C-early')
    if d['C_a'] is None: flag.append('no-C')
    row = dict(ep=ep, slot0=ref['slot0'], pick=pick, depth=m['depth_m'], **d, view_contact=ref['contact'], view_motion=ref['motion'],
               flags=flag, note=ref['note'])
    rows.append(row)
    print(f"{key:4s} {ref['slot0'][:12]:12s} {pick:22s} z{m['depth_m']:.2f} | C a{str(d['C_a']):>4s} M a{str(d['M_a']):>5s} -> a{ca:5d} end row {d['window_end_row']:5d} "
          f"| view contact {ref['contact']} motion {ref['motion']} | {' '.join(flag)}")
ends = np.array([r['window_end_row'] for r in rows])
print(f"n {len(rows)}; empty {int((ends < 0).sum())}; window end median {np.median(ends):.0f}; flags: "
      + ', '.join(f"e{r['ep']}:{'/'.join(r['flags'])}" for r in rows if r['flags']))
json.dump(rows, open(f'{OUT2}/eval_summary.json', 'w'), indent=1, default=float)
