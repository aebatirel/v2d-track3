"""Inference-side summary of what each step did (reads only refine outputs pose_opt.json). -> arms/step_summary.json"""
import json
R = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
out = {}
for arm, st in [('S1', 'S1'), ('S3', 'S3'), ('S4', 'S4')]:
    out[arm] = {}
    for e in EPS:
        d = json.load(open(f'{R}/arms/{arm}/ep{e}/pose_opt.json'))['steps'][st]
        row = {}
        for n, v in d.items():
            if n == 'delta':
                continue
            dl = d['delta'][n]
            if st == 'S1':
                rs = [(s['frames'], s.get('shift_cm')) for s in v.get('rest_segments', []) if s.get('snapped')]
                row[n] = f"f0 {v['f0_shift_cm']:+.2f}cm" + ('' if v['table_supported'] else ' (gated off)') + (f" rest {rs}" if rs else '')
            elif st == 'S3':
                row[n] = (f"tilt {v['tilt_deg']:.2f}deg" if v.get('applied') else f"skip: {v.get('skipped', v.get('reason', '?'))[:70]}")
            else:
                row[n] = (f"hold {v['hold']} ({v['reason']}) {dl['frames_changed']}fr max {dl['max_cm']:.2f}cm/{dl['max_deg']:.1f}deg"
                          if v.get('applied') else f"skip: {v.get('skipped', v.get('reason', '?'))[:60]}")
        out[arm][e] = row
json.dump(out, open(f'{R}/arms/step_summary.json', 'w'), indent=1)
for arm in out:
    print('==', arm)
    for e, row in out[arm].items():
        print(f'  ep{e}: ' + ' | '.join(f'{n}: {s}' for n, s in row.items()))
