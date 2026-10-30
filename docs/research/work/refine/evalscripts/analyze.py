"""SCORER SIDE (reads scores derived from mocap). Combines arms/<arm>/score/ep<N>_{lib,scan}.json (+ _rot.npz) into
arms/<arm>/score/ep<N>.json and applies the plan.md §1 gates. Writes arms/gates.json and prints tables.
Usage: python3 -I analyze.py ARM [ARM ...]   (the 'none' arm must be scored: it is the flip baseline)"""
import json, os, sys
import numpy as np
R = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
arms = sys.argv[1:]
F0 = json.load(open(f'{R}/arms/frame0_check.json'))
base = {e: json.load(open(f'{R}/baseline/ep{e}.json')) for e in EPS}


def load(arm, e):
    out = {'ep': e, 'arm': arm}
    for k in ('lib', 'scan'):
        p = f'{R}/arms/{arm}/score/ep{e}_{k}.json'
        if not os.path.exists(p):
            return None
        s = json.load(open(p)); pc = s['perception']
        rot = np.load(f'{R}/arms/{arm}/score/ep{e}_{k}_rot.npz')
        out[k] = dict(AUC=pc['AUC'], per_obj_AUC=pc['per_obj_AUC'], registration=s['registration'],
                      metrics={m: pc[m] for m in ('SP_SR', 'MP_SR', 'MPPE_cm', 'RPE_cm')},
                      flip_frac_gt90={str(n): round(float(np.mean(rot['rot_deg'][:, i] > 90)), 4)
                                      for i, n in enumerate(rot['names'])},
                      rot_med_deg={str(n): round(float(np.median(rot['rot_deg'][:, i])), 2)
                                   for i, n in enumerate(rot['names'])})
    json.dump(out, open(f'{R}/arms/{arm}/score/ep{e}.json', 'w'), indent=1)
    return out


S = {a: {e: load(a, e) for e in EPS} for a in arms}
none = S.get('none') or {e: load('none', e) for e in EPS}
# sanity: the none arm (byte-identical copy) must reproduce the baseline exactly
san = {k: max(abs(none[e][k]['AUC'] - base[e][k]['AUC']) for e in EPS) for k in ('lib', 'scan')}
print('none-vs-baseline max |dAUC|:', san)
G = {'none_vs_baseline_max_abs': san, 'arms': {}}
m = lambda xs: round(float(np.mean(xs)), 4)  # noqa: E731
bl = {k: [base[e][k]['AUC'] for e in EPS] for k in ('lib', 'scan')}
for a in arms:
    if a == 'none':
        continue
    rows = S[a]
    if any(rows[e] is None for e in EPS):
        print(a, 'incomplete'); continue
    g = {}
    for k in ('lib', 'scan'):
        v = [rows[e][k]['AUC'] for e in EPS]; d = [rows[e][k]['AUC'] - base[e][k]['AUC'] for e in EPS]
        i23 = EPS.index(23)
        g[k] = dict(mean=m(v), base=m(bl[k]), delta=m(d),
                    mean_no23=m([x for i, x in enumerate(v) if i != i23]),
                    base_no23=m([x for i, x in enumerate(bl[k]) if i != i23]),
                    delta_no23=m([x for i, x in enumerate(d) if i != i23]),
                    better=int(sum(x > 0.00005 for x in d)), worse=int(sum(x < -0.00005 for x in d)),
                    unchanged=int(sum(abs(x) <= 0.00005 for x in d)),
                    worse_gt_0p001=int(sum(x < -0.001 for x in d)),
                    drops_gt_0p02={e: round(x, 4) for e, x in zip(EPS, d) if x < -0.02},
                    per_ep_delta={e: round(x, 4) for e, x in zip(EPS, d)})
        # gate 3: new flips (object > 90 deg symmetric rotation error on > 5 % of frames, not so in the none arm)
        g[k]['new_flips'] = [(e, n, f, none[e][k]['flip_frac_gt90'][n]) for e in EPS
                             for n, f in rows[e][k]['flip_frac_gt90'].items()
                             if f > 0.05 and none[e][k]['flip_frac_gt90'][n] <= 0.05]
        g[k]['existing_flips'] = [(e, n, f) for e in EPS for n, f in rows[e][k]['flip_frac_gt90'].items()
                                  if f > 0.05 and none[e][k]['flip_frac_gt90'][n] > 0.05]
    g['gate1_mean_lib_ge_base_plus_0p005'] = bool(g['lib']['delta'] >= 0.005)
    g['gate2_no_drop_gt_0p02'] = not g['lib']['drops_gt_0p02']
    g['gate2_S3_rule_mean_rises_and_worse_le_third'] = bool(g['lib']['delta'] > 0 and g['lib']['worse'] <= len(EPS) / 3)
    g['gate3_no_new_flips_lib'] = not g['lib']['new_flips']
    g['gate3_no_new_flips_scan'] = not g['scan']['new_flips']
    f0 = F0.get(a, {})
    g['frame0_changed_objects'] = [(int(e), n) for e in f0 for n, v in f0[e]['obj'].items() if not v['f0_cam_identical']]
    g['gate4_frame0_byte_identical'] = not g['frame0_changed_objects']
    g['world_T_cam_and_keys_ok'] = all(f0[e]['world_T_cam_identical'] and f0[e]['keys_same'] for e in f0)
    G['arms'][a] = g
    print(f"{a:5s} lib {g['lib']['mean']:.4f} ({g['lib']['delta']:+.4f}) no23 {g['lib']['mean_no23']:.4f} ({g['lib']['delta_no23']:+.4f}) "
          f"b/w/= {g['lib']['better']}/{g['lib']['worse']}/{g['lib']['unchanged']} drops>0.02 {g['lib']['drops_gt_0p02']} | "
          f"scan {g['scan']['mean']:.4f} ({g['scan']['delta']:+.4f}) no23 {g['scan']['mean_no23']:.4f} ({g['scan']['delta_no23']:+.4f}) "
          f"drops {g['scan']['drops_gt_0p02']} | newflips lib {g['lib']['new_flips']} scan {g['scan']['new_flips']} | f0 ident {g['gate4_frame0_byte_identical']}")
# falsifiers
po = lambda a, e, n, k='lib': S[a][e][k]['per_obj_AUC'][n] if a in S and S[a][e] else None  # noqa: E731
pb = lambda e, n, k='lib': base[e][k]['per_obj_AUC'][n]  # noqa: E731
FZ = {}
if 'S1' in S:
    FZ['S1_ep26_pot_ge_0p93'] = dict(value=po('S1', 26, 'white_pot'), base=pb(26, 'white_pot'), scan=po('S1', 26, 'white_pot', 'scan'),
                                     passed=po('S1', 26, 'white_pot') >= 0.93)
if 'S2h0' in G['arms']:
    FZ['S2_gain_ge_0p003_frame0_held'] = dict(delta=G['arms']['S2h0']['lib']['delta'], delta_no23=G['arms']['S2h0']['lib']['delta_no23'],
                                              scan_delta=G['arms']['S2h0']['scan']['delta'],
                                              passed=G['arms']['S2h0']['lib']['delta'] >= 0.003)
if 'S3' in G['arms']:
    FZ['S3_mean_rises_and_worse_le_third'] = dict(delta=G['arms']['S3']['lib']['delta'], worse=G['arms']['S3']['lib']['worse'],
                                                  passed=G['arms']['S3']['gate2_S3_rule_mean_rises_and_worse_le_third'])
if 'S4' in S:
    c = dict(ep11_blue_cup=(po('S4', 11, 'blue_cup'), pb(11, 'blue_cup')), ep24_board2=(po('S4', 24, 'wooden_piece_2'), pb(24, 'wooden_piece_2')),
             ep2_lid=(po('S4', 2, 'white_pot_lid'), pb(2, 'white_pot_lid')))
    FZ['S4'] = dict(values={k: dict(value=v, base=b, delta=round(v - b, 4)) for k, (v, b) in c.items()},
                    passed=bool(c['ep11_blue_cup'][0] - c['ep11_blue_cup'][1] >= 0.01 and c['ep24_board2'][0] - c['ep24_board2'][1] >= 0.01
                                and c['ep2_lid'][0] - c['ep2_lid'][1] >= -0.02))
G['falsifiers'] = FZ
print(json.dumps(FZ, indent=1))
json.dump(G, open(f'{R}/arms/gates.json', 'w'), indent=1)
# per-episode x arm table (lib) and per-object
print('\n| ep | base | ' + ' | '.join(a for a in arms if a != 'none') + ' |')
for e in EPS:
    print(f'| {e} | {base[e]["lib"]["AUC"]:.4f} | ' + ' | '.join(f'{S[a][e]["lib"]["AUC"]:.4f} ({S[a][e]["lib"]["AUC"] - base[e]["lib"]["AUC"]:+.4f})'
                                                              for a in arms if a != 'none' and S[a][e]) + ' |')
