"""posefix report: formats the stored run JSONs (scorer, posefix.json, pf_diag) into tables and the gate verdict.
It only reads results; it computes no new score.  Usage: python -I pf_report.py OUT_DIR(repo posefix folder)"""
import json, os, sys
import numpy as np

S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
SP = f'{S}/posefix'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
VARS = ['A', 'B', 'C', 'D']
M = ['AUC', 'SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm']
STORED = {e: f'{S}/cdo_c0/runs/c0/ep{e}.json' for e in [0, 2, 26, 27, 31, 41, 42, 43, 44, 45]}
STORED.update({e: f'{S}/cdo_c0/runs/single_plastic_dish_rack/ep{e}.json' for e in [12, 13]})
STORED.update({e: f'{S}/cdo_c0/runs/base/ep{e}.json' for e in [21, 22]})
STORED[11] = f'{S}/cdo_c1/t1/auc/runs/single_ep11.json'
STORED.update({e: f'{S}/cdo_c1/t2/auc/runs/single_mini_dust_pan/ep{e}.json' for e in [18, 39, 40]})
out = sys.argv[1]


def J(p):
    return json.load(open(p)) if os.path.exists(p) else None


R = {'before': {e: J(f'{SP}/runs/before/ep{e}.json') for e in EPS}}
for V in VARS:
    R[V] = {e: J(f'{SP}/runs/{V}/ep{e}.json') for e in EPS}
PF = {V: {e: J(f'{SP}/out/{V}/ep{e}/posefix.json') for e in EPS} for V in VARS}
DG = {V: {e: J(f'{SP}/diag/{V}/ep{e}.json') for e in EPS} for V in VARS}
res = dict(stored_check=[], per_episode=[], summary={}, gate={}, direction={}, mesh_check=[], bottom_check=[])

# ---- before = stored ----
for e in EPS:
    b = R['before'][e]
    s = J(STORED[e]) if e in STORED else None
    row = dict(ep=e, stored=STORED.get(e, '').replace(S + '/', '<scratch>/') or None)
    if b and s:
        bp, sp = b['perception'], s['perception']
        diffs = {k: round(bp[k] - sp[k], 4) for k in M}
        diffs.update({f'AUC_{n}': round(bp['per_obj_AUC'][n] - sp['per_obj_AUC'][n], 4) for n in bp['per_obj_AUC']})
        row.update(equal=all(v == 0 for v in diffs.values()), diffs=diffs)
    else:
        row.update(equal=None)
    res['stored_check'].append(row)

# ---- per episode ----
for e in EPS:
    b = R['before'][e]['perception']
    row = dict(ep=e, objects=R['before'][e]['objects'], before={k: b[k] for k in M})
    for V in VARS:
        a = R[V][e]['perception'] if R[V][e] else None
        pf = PF[V][e]
        segs = pf['segments'] if pf else []
        sh = [g for g in segs if g['t_norm_mm'] > 0 or g['r_deg'] > 0]
        row[V] = dict(d={k: round(a[k] - b[k], 4) for k in M} if a else None,
                      per_obj_dAUC={n: round(a['per_obj_AUC'][n] - b['per_obj_AUC'][n], 4) for n in b['per_obj_AUC']} if a else None,
                      segments=len(segs), shifted=len(sh),
                      unresolved=sum(g['status'].startswith('unresolved') for g in segs),
                      statuses={st: sum(g['status'] == st for g in segs) for st in sorted({g['status'] for g in segs})},
                      max_shift_mm=round(max([g['t_norm_mm'] for g in sh], default=0.0), 2),
                      changed_frames=pf['changed_frames'] if pf else None)
        dg = DG[V][e]
        if dg:
            row[V]['dADD_cm'] = {n: round(dg['add_cm_after'][n] - dg['add_cm_before'][n], 4) for n in dg['add_cm_before']}
            row[V]['auc_replica_ok'] = (dg['auc_before'] == dg.get('auc_before_scorer')) and (dg['auc_after'] == dg.get('auc_after_scorer'))
    if DG['A'][e]:
        row['ADD_cm_before'] = DG['A'][e]['add_cm_before']
    res['per_episode'].append(row)

for V in VARS:
    d = np.array([[r[V]['d'][k] for k in M] for r in res['per_episode'] if r[V]['d']])
    n = len(d)
    sm = dict(n=n, mean={k: round(float(d[:, i].mean()), 5) for i, k in enumerate(M)},
              min={k: round(float(d[:, i].min()), 4) for i, k in enumerate(M)},
              max={k: round(float(d[:, i].max()), 4) for i, k in enumerate(M)},
              episodes_changed=sum(1 for r in res['per_episode'] if r[V]['changed_frames'] and sum(r[V]['changed_frames'].values()) > 0),
              argmin_dAUC=int([r['ep'] for r in res['per_episode'] if r[V]['d']][int(np.argmin(d[:, 0]))]))
    add = [np.mean(list(r[V]['dADD_cm'].values())) for r in res['per_episode'] if r[V].get('dADD_cm')]
    sm['mean_dADD_cm'] = round(float(np.mean(add)), 4) if add else None
    pots = [r[V]['d']['AUC'] for r in res['per_episode'] if r['ep'] in (41, 42, 43, 44, 45) and r[V]['d']]
    sm['mean_dAUC_41_45'] = round(float(np.mean(pots)), 5) if pots else None
    res['summary'][V] = sm
sA = res['summary']['A']
res['gate'] = dict(rule='mean dAUC >= +0.002 and min dAUC >= -0.01 (variant A, 20 episodes)',
                   mean_dAUC=sA['mean']['AUC'], min_dAUC=sA['min']['AUC'], n=sA['n'],
                   passes=bool(sA['n'] == 20 and sA['mean']['AUC'] >= 0.002 and sA['min']['AUC'] >= -0.01))

# ---- direction ----
for V in VARS:
    rows = []
    for e in EPS:
        dg, pf = DG[V][e], PF[V][e]
        if not dg:
            continue
        segmap = {(g['obj'], g['start']): g for g in pf['segments']}
        for s in dg['direction']:
            g = segmap[(s['obj'], s['start'])]
            pair = sum(g['pair_frames'].values()) > 0
            rows.append(dict(ep=e, pair=pair, **s))
    cos = np.array([r['cos'] for r in rows])
    pr = np.array([r['pair'] for r in rows], bool)
    res['direction'][V] = dict(n=len(rows), n_cos_le0=int((cos <= 0).sum()), median_cos=round(float(np.median(cos)), 3) if len(cos) else None,
                               pair=dict(n=int(pr.sum()), n_cos_le0=int((cos[pr] <= 0).sum())),
                               table_only=dict(n=int((~pr).sum()), n_cos_le0=int((cos[~pr] <= 0).sum())),
                               falsified=bool(len(rows) and (cos <= 0).sum() > len(rows) / 2), segments=rows)
# ---- mesh / bottoms (from A's diag: rest frames are the same in every variant) ----
for e in EPS:
    dg = DG['A'][e]
    if not dg:
        continue
    for m in dg['mesh_check']:
        res['mesh_check'].append(dict(ep=e, pair=m['pair'], rest_frames=m['rest_frames'], ours_at_ours=m['ours_at_ours'],
                                      ours_at_mocap=m['ours_at_mocap'], scans_at_mocap=m['scans_at_mocap']))
    for b in dg['bottom_check']:
        res['bottom_check'].append(dict(ep=e, **b))
json.dump(res, open(f'{out}/results.json', 'w'), indent=1)

# ---- markdown tables ----
L = []
L.append('### Before = stored 9a+ runs\n')
L.append('| ep | stored run | equal (AUC, SR, MPPE, RPE, per-object AUC) |')
L.append('|---|---|---|')
for r in res['stored_check']:
    L.append(f"| {r['ep']} | {r['stored'] or '-'} | {'yes' if r['equal'] else ('no: ' + json.dumps(r.get('diffs')) if r['equal'] is False else 'no stored run')} |")
L.append('\n### Per episode (perception, kit chain; d = after - before)\n')
L.append('| ep | objects | AUC before | MPPE before cm | RPE before cm | A segments: shifted / unresolved / all, max shift mm | dAUC A | dMPPE A | dRPE A | dADD A cm (mean of objects) | dAUC B | dAUC C | dAUC D |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for r in res['per_episode']:
    a = r['A']
    dadd = np.mean(list(a['dADD_cm'].values())) if a.get('dADD_cm') else float('nan')
    L.append(f"| {r['ep']} | {', '.join(r['objects'])} | {r['before']['AUC']:.4f} | {r['before']['MPPE_cm']:.3f} | {r['before']['RPE_cm']:.3f} | "
             f"{a['shifted']} / {a['unresolved']} / {a['segments']}, {a['max_shift_mm']:.1f} | {a['d']['AUC']:+.4f} | {a['d']['MPPE_cm']:+.3f} | {a['d']['RPE_cm']:+.3f} | {dadd:+.3f} | "
             f"{r['B']['d']['AUC']:+.4f} | {r['C']['d']['AUC']:+.4f} | {r['D']['d']['AUC']:+.4f} |")
L.append('\n### Means over the 20 episodes\n')
L.append('| variant | episodes changed | mean dAUC | min dAUC (ep) | max dAUC | mean dMPPE cm | mean dRPE cm | mean dSP-SR | mean dMP-SR | mean dADD cm | mean dAUC 41-45 |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|')
for V in VARS:
    s = res['summary'][V]
    L.append(f"| {V} | {s['episodes_changed']} | {s['mean']['AUC']:+.5f} | {s['min']['AUC']:+.4f} ({s['argmin_dAUC']}) | {s['max']['AUC']:+.4f} | "
             f"{s['mean']['MPPE_cm']:+.4f} | {s['mean']['RPE_cm']:+.4f} | {s['mean']['SP_SR']:+.3f} | {s['mean']['MP_SR']:+.3f} | {s['mean_dADD_cm']:+.4f} | {s['mean_dAUC_41_45']:+.5f} |")
L.append('\n### Direction check (cos of push vs correction = mocap - ours)\n')
L.append('| variant | shifted segments | cos <= 0 | median cos | with pair constraint: n / cos <= 0 | table only: n / cos <= 0 | falsified (cos <= 0 on > half) |')
L.append('|---|---|---|---|---|---|---|')
for V in VARS:
    d = res['direction'][V]
    L.append(f"| {V} | {d['n']} | {d['n_cos_le0']} | {d['median_cos']} | {d['pair']['n']} / {d['pair']['n_cos_le0']} | {d['table_only']['n']} / {d['table_only']['n_cos_le0']} | {'yes' if d['falsified'] else 'no'} |")
L.append('\n#### Variant A segments\n')
L.append('| ep | object | frames | status | pair | push mm | correction mm | correction along push mm | cos | pos err before mm | after (same alignment) mm |')
L.append('|---|---|---|---|---|---|---|---|---|---|---|')
for s in res['direction']['A']['segments']:
    L.append(f"| {s['ep']} | {s['obj']} | {s['start']}-{s['end']} | {s['status']} | {'yes' if s['pair'] else 'no'} | {s['push_mm']:.1f} | {s['corr_mm']:.1f} | {s['corr_along_push_mm']:+.1f} | {s['cos']:+.3f} | {s['pos_err_mm_before']:.1f} | {s['pos_err_mm_after_same_alignment']:.1f} |")
L.append('\n### Mesh check (pairs at rest together; every second frame; medians, max)\n')
L.append('| ep | pair | rest frames | ours at our poses: median / max cm3, median depth mm | ours at mocap poses | scans at mocap poses |')
L.append('|---|---|---|---|---|---|')
for m in res['mesh_check']:
    f = lambda x: f"{x['median_cm3']:.2f} / {x['max_cm3']:.2f}, {x['median_depth_mm']:.1f}"
    L.append(f"| {m['ep']} | {m['pair'].replace('|', ' / ')} | {m['rest_frames']} | {f(m['ours_at_ours'])} | {f(m['ours_at_mocap'])} | {f(m['scans_at_mocap'])} |")
L.append('\n### Bottom check (mocap z up; our mesh lowest point at the mocap pose minus the scan lowest point; rest frames)\n')
L.append('| ep | object | frames | ours - scan, median mm | scan lowest z median mm (IQR) |')
L.append('|---|---|---|---|---|')
for b in res['bottom_check']:
    L.append(f"| {b['ep']} | {b['obj']} | {b['rest_frames_sampled']} | {b['ours_minus_scan_lowest_mm_median']:+.1f} | {b['scan_lowest_z_mm_median']:.1f} ({b['scan_lowest_z_mm_iqr']:.1f}) |")
open(f'{out}/tables.md', 'w').write('\n'.join(L) + '\n')
print(json.dumps(res['gate']), json.dumps({V: res['summary'][V]['mean'] for V in VARS}))
print({V: {k: v for k, v in res['direction'][V].items() if k != 'segments'} for V in VARS})
