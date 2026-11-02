"""Build the C4 audit table and apply the pre-registered adoption rule (PREREG.md section 3).
Usage: table.py RAW_DIR CANDIDATES.json SCAN_DIR OUT_DIR
"""
import glob, hashlib, json, os, sys

raw, cands, scans, out = sys.argv[1:5]
plan = json.load(open(cands))
scan_md5 = {hashlib.md5(open(p, 'rb').read()).hexdigest() for p in glob.glob(os.path.join(scans, '*.glb'))}
W = {'wooden_spoon': 10, 'white_pot': 6, 'plastic_dish_rack': 5, 'blue_cup': 5, 'beige_cup': 2, 'mini_dust_pan': 2,
     'mini_sweeper': 2, 'white_pot_lid': 1, 'water_pitcher': 1, 'wooden_piece_1': 1, 'wooden_piece_2': 1}
recs = {}
for p in glob.glob(os.path.join(raw, '*.json')):
    r = json.load(open(p)); recs[r['c4']['index']] = r
rows = []
for i, it in enumerate(plan):
    r = recs.get(i)
    s = r['c4']['summary'] if r else None
    rows.append(dict(i=i, object=it['object'], label=it['label'], role=it['role'], md5=it['md5'], s=s,
                     scan_copy=it['md5'] in scan_md5))
order = ['shipped_13f', 'shipped_13e_only', 'library_v3', 'candidate']
lines = ['| object (pairs) | role | mesh | md5 | CD-O med | FLIP | W30 | anchor med / p90 mm | rot med / p90 deg | ADD med mm | amb / floor mm |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
adopt = {}
for o in W:
    if o == 'wooden_spoon':
        continue
    rs = sorted([r for r in rows if r['object'] == o], key=lambda r: (order.index(r['role']), r['i']))
    for r in rs:
        s = r['s']
        if s is None:
            lines.append(f"| {o} ({W[o]}) | {r['role']} | {r['label']} | {r['md5'][:8]} | pending | | | | | | |"); continue
        amb = f"{s['amb_mm']:.2f} / {s['amb_floor_mm']:.2f}" if s.get('amb_mm') is not None else ''
        lines.append(f"| {o} ({W[o]}) | {r['role']} | {r['label']} | {r['md5'][:8]} | {s['cdo_med']:.4f} | {s['flip']:.2f} | "
                     f"{s['w30']:.2f} | {s['anc_med']:.1f} / {s['anc_p90']:.1f} | {s['rot_med']:.1f} / {s['rot_p90']:.1f} | "
                     f"{s['add_med']:.1f} | {amb} |")
    base = next((r for r in rs if r['role'] == 'shipped_13f'), None)
    if base is None or base['s'] is None:
        adopt[o] = dict(decision='pending'); continue
    S = base['s']; ok = []
    for r in rs:
        if r is base or r['s'] is None:
            continue
        C = r['s']
        if r['scan_copy'] or C['cdo_med'] < 0.10:
            continue
        A = C['cdo_med'] <= S['cdo_med'] - 0.020 and C['w30'] <= S['w30'] + 0.05
        B = C['w30'] <= S['w30'] - 0.20 and C['cdo_med'] <= S['cdo_med'] + 0.005 and C['anc_med'] <= S['anc_med'] + 2.0
        if A or B:
            ok.append((C['w30'], C['cdo_med'], C['anc_med'], r['label'], 'A' if A else 'B', r['md5'], r['i']))
    pend = [r['label'] for r in rs if r['s'] is None]
    if ok:
        best = sorted(ok)[0]
        adopt[o] = dict(decision='adopt', label=best[3], rule=best[4], md5=best[5], index=best[6],
                        cdo_med=best[1], w30=best[0], anc_med=best[2], base=S, pending=pend,
                        qualifying=[q[3] for q in sorted(ok)])
    else:
        adopt[o] = dict(decision='keep 13f', base=S, pending=pend,
                        priority_build=S['w30'] >= 0.20)
os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'audit_table.md'), 'w').write('\n'.join(lines) + '\n')
json.dump(adopt, open(os.path.join(out, 'adoption.json'), 'w'), indent=1)
print('\n'.join(lines))
print(json.dumps({o: {k: v for k, v in a.items() if k != 'base'} for o, a in adopt.items()}, indent=1))
