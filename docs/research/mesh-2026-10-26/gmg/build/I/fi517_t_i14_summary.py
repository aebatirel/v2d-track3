"""Collect the T-I14 synthetic results of collision-carve round 2 (PREREG F-I5.15 / F-I5.16 / F-I5.17) into
build/I/results/collcarve-r2/t_i14/: one JSON per test group (copied from the scratch outputs) and summary.json.

  python docs/research/mesh-2026-10-26/gmg/build/I/fi517_t_i14_summary.py <scratch>/gmg/interlock/test_collcarve2.json \
      <scratch>/cc2b/nest/*.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results', 'collcarve-r2', 't_i14')


def main(paths):
    os.makedirs(OUT, exist_ok=True)
    allr = {}
    for p in paths:
        d = json.load(open(p))
        allr.update(d)
    summ = {}
    if 'r3_intrusion' in allr:
        summ['rings_r3'] = {k: {n: dict(min_wall_mm=v['min_wall_mm'], intrusion_construction_mm=v['intrusion_construction_mm'],
                                         intrusion_continuity_mm=v['continuity'].get('intrusion_max_mm'),
                                         continuity_ok=v['continuity']['ok'], gap_share=v['continuity']['gap_share'],
                                         formula_min_wall_mm=v.get('formula_min_wall_mm'))
                                for n, v in rows.items()} for k, rows in allr['r3_intrusion'].items()}
    if 'r1' in allr:
        r = allr['r1']
        summ['r1'] = dict(round1_self_check=r['round1_self_check']['ok'], intrusion_mm=r['intrusion_construction']['max_mm'],
                          continuity2_ok=r['continuity2']['ok'], gap_share=r['continuity2']['gap_share'])
    if 'r2' in allr:
        r = allr['r2']
        summ['r2'] = dict(default_ok=r['default']['ok'], forced_ring_ok=r['forced_ring']['ok'],
                          forced_ring_worst_height=r['forced_ring']['worst_height_gap_share'],
                          thin_self_check=r['thin']['self_check'], thin_continuity2_ok=r['thin']['continuity2']['ok'])
    if 'r4_r5' in allr:
        summ['search'] = {k: dict(accepted=v['accepted'],
                                  tried=[(t['n_s'], t['base'], t['n_r'], t.get('fail') or 'accepted') for t in v['tried']])
                          for k, v in allr['r4_r5'].items()}
    if 'precheck' in allr:
        summ['precheck'] = {k: v['fails'] for k, v in allr['precheck'].items()}
    for k in ('gate_g1_g3', 'gate_g2'):
        if k in allr:
            v = allr[k]
            summ[k] = {kk: vv['verdict'] for kk, vv in v.items() if isinstance(vv, dict) and 'verdict' in vv} \
                if k == 'gate_g1_g3' else v['verdict']
    for k in ('x6_x10_r2', 'rev1_reachable'):
        if k in allr:
            summ[k] = allr[k]
    for k in ('n1', 'n3', 'tn0', 'tn1', 'n2a'):
        if k in allr and 'summary' in allr[k]:
            s = allr[k]['summary']
            summ[k] = dict(deliver=s['deliver'], why=s.get('why'), n_s=s['n_s'],
                           components=[dict(why=c.get('why'), ok_frames=c.get('ok_frames'), c_mm=c.get('c_mm'),
                                            off_axis=c.get('off_axis')) for c in s['components']],
                           caps_fail=(s.get('caps') or {}).get('fail'), tests=s.get('tests'), failing=s.get('failing'),
                           S_delivered=s['S_delivered'], floor_pass=s['floor_pass'], floor_fails=s['floor_fails'],
                           g1=s['g1'], g1_pairs=s['g1_pairs'])
    for name, keys in (('rings', ('r1', 'r2', 'r3_intrusion', 'r4_r5')), ('precheck', ('precheck',)),
                       ('gate', ('gate_g1_g3', 'gate_g2')), ('controls', ('x6_x10_r2', 'rev1_reachable')),
                       ('nests', ('n1', 'n3', 'tn0', 'tn1', 'n2a'))):
        sub = {k: allr[k] for k in keys if k in allr}
        if sub:
            with open(os.path.join(OUT, f'{name}.json'), 'w') as fh:
                json.dump(sub, fh, indent=1)
    with open(os.path.join(OUT, 'summary.json'), 'w') as fh:
        json.dump(summ, fh, indent=1)
    print(json.dumps(summ, indent=1)[:6000])


if __name__ == '__main__':
    main(sys.argv[1:])
