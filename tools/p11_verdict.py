#!/usr/bin/env python3
"""Pack 11 verdict (1 Nov 2026; docs/research/work/eval10-njmax-20261101/PREREG_AMENDMENT_pack11.md).

Applies the standing pack-9b rule a / b / c / s on V and P, i.e. tools/e10v_verdict.verdict UNCHANGED, to:
  conf   = the njmax-1024-trained eval-10 policy's stock-config copy (ck512, sha256 aaa077eb…), its 10 official draws;
  packed = the policy now in pack 10 for eval 10 (run 20261101-e10cs-50c2d90 s43, sha256 ca7c4e3a…), its 10 official draws;
  old    = pack 10's eval-10 rollout (that run's confirmation draw 1).
The only change against e10v_verdict is which checkpoint the packed / old sides must name (PACKED_SHA = pack 10's
eval-10 checkpoint instead of gl10A2's) and the binding pack-inclusion bar: (new - packed) mean sim_vs_ref >= +0.02 on
BOTH V and P. `verify` comes from the amendment's required checks, passed in as a JSON file (ok + the evidence).
Usage: python tools/p11_verdict.py --score SCORE.json --checks CHECKS.json --out OUT.json
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e10v_verdict as ev  # noqa: E402

PACK10_EVAL10_SHA = 'ca7c4e3a162ab11ecda1b8a040ad151763c2e57dcd1e97a1334c6623c2906131'
CANDIDATE_SHA = 'aaa077ebae863650c926d13550d368704889d445bcfc96ef9e4773f17c04d55f'
BAR = 0.02


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--score', required=True); ap.add_argument('--checks', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    d = json.load(open(a.score))
    sets = d['sets']
    refs_md5 = {X: info.get('md5') for X, info in d.get('refs', {}).items()}
    refs_md5 = {'P': refs_md5.get('P'), 'V': {refs_md5.get('V')}}
    checks = json.load(open(a.checks))
    ev.PACKED_SHA = PACK10_EVAL10_SHA                     # the packed / old sides are pack 10's eval-10 policy
    choice = {'chosen': '43', 'sha256': CANDIDATE_SHA}
    label, why, clauses, sides = ev.verdict(sets, checks, choice, 10, refs_md5)
    gain = {X: round(sides[X]['new']['sim_vs_ref']['mean'] - sides[X]['packed']['sim_vs_ref']['mean'], 4)
            for X in ev.REFS} if label == 'SWAP-ELIGIBLE' else None
    include = bool(label == 'SWAP-ELIGIBLE' and all(g >= BAR for g in gain.values()))
    out = dict(label=label, why=why, clauses=clauses, sides=sides, pack_inclusion=dict(bar=BAR, gain=gain, include=include),
               candidate_sha256=CANDIDATE_SHA, packed_sha256=PACK10_EVAL10_SHA, checks=checks,
               note='standing rule applied to already-seen 512-readout draws (PREREG_AMENDMENT_pack11.md); not a blind test')
    json.dump(out, open(a.out, 'w'), indent=1)
    line = (f"p11 RESULT: {label} :: pack 11: {'INCLUDE' if include else 'not included'} (gain {gain}; bar {BAR}) :: "
            + ' | '.join(f"{k} {'ok' if v['holds'] else 'FAIL'} margin {v['margin']}" for k, v in clauses.items())
            + f" :: {'; '.join(why)}")
    print(line)
    open(os.path.splitext(a.out)[0] + '.txt', 'w').write(line + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
