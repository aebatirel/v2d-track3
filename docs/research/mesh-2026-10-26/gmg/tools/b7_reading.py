"""b7_reading: join the visual crop reading (build/b7/crops/reading.json) with the ball records of the archived B7 dev
runs (build/b7/runs/<run>/ep<N>.json) and print per-class counts, votes, radii and the diagnostic statistics.
GT-free (reads only B7 dev outputs and the reading). Usage: python gmg/tools/b7_reading.py
"""
import json
import os

B7 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'b7')
CLASSES = ('real', 'partial', 'next', 'hand', 'geometry')


def rng(xs, f='{:.1f}'):
    return (f.format(min(xs)) + '-' + f.format(max(xs))) if xs else '-'


def main():
    R = json.load(open(os.path.join(B7, 'crops', 'reading.json')))
    rows, pooled = [], {c: [] for c in CLASSES}
    for group in ('episodes', 'non_anchor'):
        for ep, e in R[group].items():
            d = json.load(open(os.path.join(B7, 'runs', e['run'], f'ep{ep}.json')))
            balls = sorted(d['markers']['balls'][e['obj']], key=lambda b: -b['votes'])
            n = {c: len(e[c]) for c in CLASSES}
            rows.append(f"| ep{ep} {e['obj']}{'' if group == 'episodes' else ' (not an anchor)'} | {len(balls)} | "
                        f"{e['checked']} | " + ' | '.join(str(n[c]) for c in CLASSES) + ' |')
            if group == 'episodes':
                for c in CLASSES:
                    pooled[c] += [balls[i] for i in e[c]]
    print('| object | balls | checked (top by votes) | ' + ' | '.join(CLASSES) + ' |')
    print('|---|---|---|' + '---|' * len(CLASSES))
    print('\n'.join(rows))
    print()
    print('| class (10 anchors pooled) | n | votes | r mm | normal_dev deg | outside ratio | cap deg | pass 2 |')
    print('|---|---|---|---|---|---|---|---|')
    for c in CLASSES:
        b = pooled[c]
        print(f"| {c} | {len(b)} | {rng([x['votes'] for x in b], '{:d}')} | {rng([x['r_mm'] for x in b])} | "
              f"{rng([x['normal_dev_deg'] for x in b if x['normal_dev_deg'] is not None])} | "
              f"{rng([x['outside_ratio'] for x in b if x['outside_ratio'] is not None], '{:.2f}')} | "
              f"{rng([x['cap_deg'] for x in b], '{:.0f}')} | {sum(x['pass_'] == 2 for x in b)} |")


if __name__ == '__main__':
    main()
