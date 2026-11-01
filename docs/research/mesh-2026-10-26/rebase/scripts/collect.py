"""Collect the per-set outputs (rebase.json, frames.json, settle_*.json) into results/summary.json and markdown tables.
Report-only addition (not a gate): the packed penetration over every on-table static frame with the hands allowed
(H30 dropped), to show the T-rest result does not hinge on the few hands-off frames.
Usage: python -I collect.py OUT_ROOT SET [SET ...] > tables.md   (writes OUT_ROOT/summary.json)"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebase as rb  # noqa: E402

root = sys.argv[1]; sets = sys.argv[2:]
S = {}
rows, srows, crows = [], [], []
for s in sets:
    r = json.load(open(f'{root}/{s}/rebase.json')); fr = json.load(open(f'{root}/{s}/frames.json')); pf = fr['per_frame']
    pen = np.array(pf['pen_packed_mm']); on = np.array(pf['on_table']); nh = np.array(pf['not_held'])
    st = np.array(pf['disp_mm']) < rb.STATIC_M * 1e3
    allf = rb.run_mask(rb.runs(on & nh & st), len(pen))
    diag = dict(n=int(allf.sum()), signed=rb.stats(pen[allf]), pen=rb.stats(np.maximum(pen[allf], 0)))
    H30 = np.array(pf['H30'])                                   # second report-only set: receiver contact allowed
    rf = rb.run_mask(rb.runs(on & H30 & st), len(pen))
    diag_rc = dict(n=int(rf.sum()), runs=rb.runs(on & H30 & st), signed=rb.stats(pen[rf]), pen=rb.stats(np.maximum(pen[rf], 0)))
    ev = r.get('eval', {}); pk = ev.get('packed', {})
    g2 = {n: (x['frames'], x['overlap_cm3']['median'], x['overlap_cm3']['max'], x['depth_mm']['max'])
          for n, x in pk.get('G2', {}).items()}
    st_ = {}
    for v in ('packed', 'a', 'b', 'b1'):
        p = f'{root}/{s}/settle_{v}.json'
        if os.path.exists(p):
            st_[v] = json.load(open(p))
    S[s] = dict(ref=r['ref'], ref_md5=r['ref_md5'], target=r['target'], support_top_z=r['support']['top_z'],
                usda_md5=r['support']['md5'], packed_count=r['packed_count'], n_rest=r['n_rest'], rest_runs=r['rest_runs'],
                d_mm=r.get('d_mm'), u=r.get('u'), u_dev_deg=r.get('u_dev_deg'), status=r.get('status', r.get('verdict')),
                G1_packed=pk.get('G1'), G1_packed_pass=pk.get('G1_pass'), signed_packed=r.get('pen_packed_signed_mm'),
                G2_packed=g2, partner_rest_runs=r['partner_rest_runs'], diag_all_on_table_static=diag, diag_receiver_contact_allowed=diag_rc,
                visual_md5=r['visual_md5'], settle={v: dict(test_frames=x['test_frames'], diagnostic_only=x['diagnostic_only'],
                                                            G3_pass=x['G3_pass'],
                                                            frames=[dict(frame=f['frame'], target_mm=f['G3']['final_mm'][x['names'].index(x['target'])],
                                                                         target_deg=f['G3']['final_deg'][x['names'].index(x['target'])],
                                                                         all_mm=f['G3']['final_mm'], all_deg=f['G3']['final_deg'],
                                                                         nefc0=f['G3']['nefc0'], max_nefc=f['G3']['max_nefc'],
                                                                         G4_max_nefc=f['G4']['max_nefc'], G4_max_ncon=f['G4']['max_ncon'],
                                                                         G4_overflow=f['G4']['overflow_copies'],
                                                                         G4_target_final_mm=f['G4']['target_final_mm'])
                                                                    for f in x['frames']], names=x['names'])
                                                     for v, x in st_.items()})
    g1 = pk.get('G1') or {}
    sg = r.get('pen_packed_signed_mm') or {}
    rows.append(f"| {s} | {r['target']} | {r['ref_md5'][:8]} | {r['packed_count']} | {r['n_rest']} {r['rest_runs']} | "
                f"{sg.get('median')} / {sg.get('min')} / {sg.get('max')} | {g1.get('median')} / {g1.get('max')} | "
                f"{r.get('d_mm')} | {r.get('status', r.get('verdict'))} | "
                f"{diag['n']}: {diag['signed']['median']} / {diag['pen']['max']} | {diag_rc['n']}: {diag_rc['signed']['median']} / {diag_rc['pen']['max']} | "
                + '; '.join(f"{n}: {a} fr, {b} / {c} cm3, {d} mm" for n, (a, b, c, d) in g2.items()) + ' |')
    for v, x in S[s]['settle'].items():
        for f in x['frames']:
            srows.append(f"| {s} | {v} | f{f['frame']}{' (diag)' if x['diagnostic_only'] else ''} | {f['target_mm']} / {f['target_deg']} | "
                         + ', '.join(f"{n} {a} / {b}" for n, a, b in zip(x['names'], f['all_mm'], f['all_deg']) if n != S[s]['target'])
                         + f" | {f['nefc0']} / {f['max_nefc']} | {f['G4_max_nefc']} / {f['G4_max_ncon']} / {f['G4_overflow']} |")
    for k, e in ev.items():
        if k == 'packed':
            continue
        S[s].setdefault('candidates', {})[k] = dict(count=e['count'], cm3=e['cm3'], G1=e['G1'], G1_pass=e['G1_pass'],
                                                    G2_pass=e.get('G2_pass'), G2_vacuous=e.get('G2_vacuous'), G6_pass=e['G6_pass'],
                                                    convex_all=e['convex_all'], rule=r.get('rule_' + k))
        crows.append(f"| {s} | {k} | {e['count']} (packed {pk['count']}) | {e['cm3']} (packed {pk['cm3']}) | {e['G1']['median']} / {e['G1']['max']} | "
                     f"{'pass' if e['G1_pass'] else 'FAIL'} | {'pass (vacuous)' if e.get('G2_vacuous') else ('pass' if e.get('G2_pass') else 'FAIL')} | "
                     f"{'pass' if e['G6_pass'] else 'FAIL'} | {e['convex_all']} | {r.get('rule_' + k)} |")
json.dump(S, open(f'{root}/summary.json', 'w'), indent=1)
print('| Set | Object | Ref md5 | Packed pieces | T-rest frames [runs] | Signed pen. median / min / max, mm | G1: pen. median / max, mm | d, mm | Rule outcome | Report only, hands allowed: n: signed median / max pen., mm | Report only, receiver contact allowed: n: signed median / max pen., mm | Partner-rest frames, packed: frames, overlap median / max cm3, depth mm |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|')
print('\n'.join(rows))
print()
print('| Set | Pieces | Frame | Target at 2 s, mm / deg | Partners at 2 s, mm / deg | nefc step 0 / max | G4 16 copies: max nefc / ncon / overflow |')
print('|---|---|---|---|---|---|---|')
print('\n'.join(srows))
print()
print('| Set | Candidate | Pieces | Volume cm3 | G1 pen. median / max, mm | G1 | G2 | G6 | Convex | Rule numbers |')
print('|---|---|---|---|---|---|---|---|---|---|')
print('\n'.join(crows))
