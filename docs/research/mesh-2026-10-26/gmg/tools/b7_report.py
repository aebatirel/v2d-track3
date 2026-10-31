"""b7_report: GT-free markdown tables of B7 dev runs (structure hypotheses, marker balls) from their b7_summary.json
files. Reads only the run summaries given on the command line (dev outputs, tier DEV; never scored).

Usage: python gmg/tools/b7_report.py RUN_DIR_OR_SUMMARY [...]      later files win for the same (episode, object)
"""
import json
import os
import sys


def load(paths):
    anchors, struct, marks = {}, {}, {}
    for p in paths:
        f = os.path.join(p, 'b7_summary.json') if os.path.isdir(p) else p
        S = json.load(open(f))
        run = S.get('run', os.path.basename(os.path.dirname(f)))
        for e, o in S['anchors']:
            anchors[(int(e), o)] = True
        for ep, E in S['episodes'].items():
            for o, h in E['structure'].items():
                struct[(int(ep), o)] = dict(h, sigma=E['sigma_mm'][o], run=run)
            M = E.get('markers')
            if M:
                for o, rad in M['radii_mm'].items():
                    marks[(int(ep), o)] = dict(
                        radii=rad, nd=M['normal_dev_deg'][o], orr=M['outside_ratio'][o], passes=M['passes'][o],
                        consensus=M['r_consensus_mm'], unimodal=M['unimodal'], objects=M.get('objects', list(M['radii_mm'])), run=run,
                        sigma=E['sigma_mm'][o])
    return anchors, struct, marks


def rng(xs, fmt='{:.0f}'):
    xs = [x for x in xs if x is not None]
    return (fmt.format(min(xs)) + '-' + fmt.format(max(xs))) if xs else '-'


def main():
    anchors, struct, marks = load(sys.argv[1:])
    print('| anchor | sigma mm | points | lathe | rotc sigma | lathe_mad sigma | rot FREE | mirrors acc | '
          'best mirror resid sigma / obs / FREE | plate pairs mm (overlap) | planes | repeats acc | sec | run |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for (ep, o), h in sorted(struct.items()):
        mir = h['mirrors']
        acc = [m for m in mir if m['accepted']]
        best = min(mir, key=lambda m: (m['resid_sigma'] or 99) + 20 * m['free_viol']) if mir else None
        print(f"| ep{ep} {o} | {h['sigma']:.2f} | {h['n_points']} | {'yes' if h['lathe'] else 'no'} | "
              f"{h['rotc_sigma']:.2f} | {h['lathe_mad_sigma']:.1f} | {h['rot_free_viol']:.2f} | {len(acc)}/{len(mir)} | "
              + (f"{best['resid_sigma']:.2f} / {best['observed']:.2f} / {best['free_viol']:.3f}" if best else '-')
              + ' | ' + (', '.join(f"{p['thickness_mm']:.1f} ({p['overlap']:.2f})" for p in h['plate_pairs']) or '-')
              + f" | {h['planes']} | " + (','.join(f"C{r}" for r in h['repeats_accepted']) or '-')
              + f" | {h['timing_s'].get('total'):.0f} | {h['run']} |")
    print()
    print('| object | balls | radii mm (sorted) | consensus mm | B.4 share within 15 % | pass-1 share (diag.) | '
          'normal_dev deg | normal_dev <= 20 / > 25 | outside ratio | pass 2 | pooled over | run |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for (ep, o), M in sorted(marks.items()):
        nd = [x for x in M['nd'] if x is not None]
        u = M['unimodal']
        r1 = [r for r, p in zip(M['radii'], M['passes']) if p == 1]     # diagnostic: the unimodal share before pass 2
        s1 = '-'
        if r1:
            med = sorted(r1)[len(r1) // 2] if len(r1) % 2 else 0.5 * sum(sorted(r1)[len(r1) // 2 - 1:len(r1) // 2 + 1])
            s1 = f"{sum(abs(r - med) <= 0.15 * med for r in r1) / len(r1):.2f} (n {len(r1)})"
        print(f"| ep{ep} {o}{' (anchor)' if (ep, o) in anchors else ''} | {len(M['radii'])} | "
              + (', '.join(f'{r:.1f}' for r in sorted(M['radii'])) or '-') + f" | {M['consensus']} | "
              + (f"{u['share_within_15pct']:.2f} ({'unimodal' if u['unimodal_b4'] else 'not unimodal'})" if u else '-')
              + f" | {s1} | {rng(nd)} | {sum(x <= 20 for x in nd)} / {sum(x > 25 for x in nd)} | "
              f"{rng(M['orr'], '{:.2f}')} | {sum(p == 2 for p in M['passes'])} | {'+'.join(M['objects'])} | {M['run']} |")


if __name__ == '__main__':
    main()
