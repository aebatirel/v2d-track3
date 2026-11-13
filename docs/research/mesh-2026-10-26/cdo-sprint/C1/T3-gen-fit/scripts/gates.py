#!/usr/bin/env python
"""T3 verdicts (PREREG.md sections 5 and 7). Reads the one-shot score records (score.py output) and applies the
pre-registered CD-O GATE per object (per eval pair for the beige cup), compares with the raw pick's [D] score
(results/gen-probe/scores.jsonl) and the C0 candidates, and states the H-GF verdict. No selection beyond the rules.
Usage: python -I gates.py SCORES.jsonl OUT.json
"""
import json, sys

REPO = '/home/user/v2d-track3/docs/research/mesh-2026-10-26'
# per eval pair packed baseline (public-scan CD-O [D], baseline_library.jsonl) and library add_med (mm)
BASE = {
    'white_pot': [('pack', 0.4371, 6.69)], 'white_pot_lid': [('pack', 0.4211, 8.13)],
    'plastic_dish_rack': [('pack', 0.5551, 5.79)], 'blue_cup': [('pack', 0.5233, 10.14)],
    'beige_cup': [('eval10 library_v3', 0.8562, 6.965), ('eval8 library_v3x', 0.7299, 5.51)],
    'water_pitcher': [('pack', 0.8942, 7.97)], 'mini_dust_pan': [('pack', 0.3307, 5.65)],
    'mini_sweeper': [('pack', 0.3170, 5.245)], 'wooden_piece_1': [('pack', 0.2219, 2.49)],
    'wooden_piece_2': [('pack', 0.2158, 3.315)],
}
C0 = {'white_pot': 0.3417, 'white_pot_lid': 0.2199, 'plastic_dish_rack': 0.4560, 'blue_cup': 0.2906}
FLIP30 = ('mini_sweeper', 'wooden_piece_1', 'wooden_piece_2')
SYMM = ('beige_cup', 'blue_cup', 'white_pot_lid')      # kit-declared symmetric (mesh_metric is symmetry-aware)
RAW_LABEL = {}


def main():
    scores, out = sys.argv[1], sys.argv[2]
    sel = json.load(open(f'{REPO}/results/gen-probe/selection.json'))['selection']
    raw = {}
    for l in open(f'{REPO}/results/gen-probe/scores.jsonl'):
        r = json.loads(l); raw[r['label']] = r
    rows, wins, worse_than_raw = [], 0, 0
    recs = {json.loads(l)['object']: json.loads(l) for l in open(scores)}
    for s in sel:
        o = s['object']; r = recs.get(o)
        rw = raw[s['pick']]
        row = dict(object=o, pick=s['pick'], raw_cdo=rw['cdo_eval'], raw_add_med=rw['add_med'], raw_flips=rw['flips_all'],
                   raw_n=rw['n_seeds'])
        if r is None or 'error' in r:
            row['error'] = 'missing' if r is None else r['error']; rows.append(row); continue
        row.update(cdo=r['cdo_eval'], add_med=r['add_med'], flips_all=r['flips_all'], n_seeds=r['n_seeds'],
                   flips_extra=r.get('flips_extra'), n_extra=r.get('n_extra'), flips_eval=r['flips_eval'], sha=r['sha'])
        if o in FLIP30:
            flip_ok = r.get('flips_extra', 99) <= 1 and r['flips_eval'] == 0
            flip_rule = 'flips <= 1 of 30 extra seeds and 0 on eval seeds'
        else:
            flip_ok = r['flips_all'] == 0
            flip_rule = '0 flips (symmetry-aware for declared-symmetric objects)'
        pairs = []
        for name, b_cdo, b_add in BASE[o]:
            c_ok = r['cdo_eval'] <= b_cdo - 0.02
            a_ok = r['add_med'] <= b_add + 2.0
            pairs.append(dict(pair=name, base_cdo=b_cdo, base_add_med=b_add, cdo_ok=c_ok, add_ok=a_ok, flip_ok=flip_ok,
                              win=bool(c_ok and a_ok and flip_ok)))
        row['pairs'] = pairs; row['flip_rule'] = flip_rule
        row['win'] = any(p['win'] for p in pairs)
        row['d_vs_raw'] = r['cdo_eval'] - rw['cdo_eval']
        row['worse_than_raw'] = bool(r['cdo_eval'] > rw['cdo_eval'])
        if o in C0:
            row['c0_cdo'] = C0[o]; row['beats_c0_by_0.02'] = bool(r['cdo_eval'] <= C0[o] - 0.02)
        wins += row['win']; worse_than_raw += row['worse_than_raw']
        rows.append(row)
    n = sum('cdo' in r for r in rows)
    verdict = ('FALSIFIED' if (wins < 3 or worse_than_raw > n / 2) else 'SUPPORTED')
    res = dict(rows=rows, wins=wins, worse_than_raw=worse_than_raw, n_scored=n,
               rule='H-GF falsified if fitted is a WIN on < 3 of 10 objects OR fitted CD-O > raw CD-O on a majority',
               verdict=verdict)
    json.dump(res, open(out, 'w'), indent=1)
    for r in rows:
        print(r['object'], r.get('cdo'), r.get('raw_cdo'), r.get('add_med'), r.get('flips_all'), r.get('flips_extra'),
              'WIN' if r.get('win') else '-', r.get('error', ''))
    print('wins', wins, 'worse_than_raw', worse_than_raw, 'of', n, '->', verdict)


if __name__ == '__main__':
    main()
