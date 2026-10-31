"""PREREG F-I5.15 (4e): DO_NOT_USE.json (labelled post hoc) beside the manifests of the five round-1 public folders
(build/I/results/collcarve-public/ep*/r0/) and in the scratch round folders runs-dev/20261031-fi5pub-3053a78/sim/
public/ep*-fi5/r0 where they exist on this machine. A file is added; nothing is overwritten. The shares are the
round-1 README's measured delivered-box volume / SHELL volume (diagnostic F-I5.14 (7), verify_cc_1 B2).

  python docs/research/mesh-2026-10-26/gmg/build/I/fi515_round1_markers.py
"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results', 'collcarve-public')
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..'))
SCR = os.path.join(REPO, 'runs-dev', '20261031-fi5pub-3053a78', 'sim', 'public')


def shares():
    out = {}
    for line in open(os.path.join(RES, 'README.md')):
        m = re.match(r'^\| (\d+) \| (\w+) \| [\d.]+ \| .* \| (\d+) \| ([\d.]+) / ([\d.]+) \(([\d.]+) %\) \|', line)
        if m:
            ep, obj = int(m.group(1)), m.group(2)
            out.setdefault(ep, {})[obj] = dict(pieces=int(m.group(3)), delivered_cm3=float(m.group(4)),
                                               shell_cm3=float(m.group(5)), share=round(float(m.group(6)) / 100, 4))
    return out


def marker(ep, rows):
    return dict(do_not_use={o: f'delivered pieces keep {r["share"]:.3f} < f_keep 0.5 of the SHELL volume' for o, r in
                            rows.items()},
                rule='PREREG F-I5.15 (4e) (applying the F-I5.15 (4c)(i) floor to the round-1 delivery)',
                post_hoc=True, labelled_post_hoc='this rule was written after the round-1 results (verify_cc_0 N1, '
                                                 'verify_cc_1 B2, diagnostic F-I5.14 (7))',
                shares=rows, also='S fails at every round-1 S frame on faithful SHELL boxes (verify_cc_1 B2)',
                written_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), episode=ep)


def main():
    sh = shares()
    done = []
    for ep, rows in sorted(sh.items()):
        for d in (os.path.join(RES, f'ep{ep}', 'r0'), os.path.join(SCR, f'ep{ep}-fi5', 'r0')):
            if not os.path.isdir(d):
                done.append((d, 'absent on this machine'))
                continue
            p = os.path.join(d, 'DO_NOT_USE.json')
            if os.path.exists(p):
                done.append((d, 'exists: not overwritten'))
                continue
            with open(p, 'w') as fh:
                json.dump(marker(ep, rows), fh, indent=1)
            done.append((d, 'written'))
    for d, s in done:
        print(os.path.relpath(d, REPO), s)


if __name__ == '__main__':
    main()
