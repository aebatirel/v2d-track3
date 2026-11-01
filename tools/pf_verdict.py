"""Verdicts of the perfect-following hand-assignment arms (2026-11-01; rules fixed in
docs/research/work/pf-hands-20261101/PREREG.md before any result). Three modes:

  public  --results DIR --eps "13" --arms "s 2h" --seeds "42 43" --out J
          Per arm and seed: the chosen checkpoint's NREP training-box rollouts (results/pf<arm>s<seed>_glock_public/ep<N>/
          best/summary.json): mean registered AUC vs mocap (public evaluation only), mean sim_vs_ref; plain and symmetric
          sim_vs_ref from each rollout's timeline.json (tools/simref_timeline.py) when present.
          Rule (PREREG section 3): 2h passes when mean over seeds of (AUC_2h - AUC_s) >= +0.05 and no seed's paired
          difference < -0.05; FAIL otherwise; INCOMPLETE if any cell has < 8 scored rollouts.
  choose  --results DIR --ep N --arm A --seeds "42 43" --h5 DIR --out J
          Seed choice (pack-9b PREREG section 2): each seed needs >= 8 scored training-box rollouts; higher mean sim_vs_ref;
          within 0.005 (4 decimals) the lower sd (ddof 1); then seed 42. Gate: chosen mean > the packed policy's H5p7
          fresh-draw mean (qa.py metric on DIR/r*/episode_*.parquet). Exit 0 = chosen and gate met (confirm), 3 = gate
          not met (NO-SWAP), 2 = INCOMPLETE.
  eval    --score S.json --choice C.json --table packed_refs.json --ep N --out J
          The pack-9b swap rule on tools/dr_score.py's sets vs P (conf = confirmation draws, packed = H5p7 draws, old = the
          old packed draw): (a) mean sim_vs_ref(conf) >= mean(packed); (b) share RPE > 5 cm (conf) <= (packed); (c) median
          RPE(conf) <= median(packed); (s) conf draw 1 >= old - 0.05; 1e-9 tolerance in favour of holds. INVALID if an
          own-reference check fails or a rollout names another checkpoint (conf: chosen sha256; packed / old: the table's).
          INCOMPLETE if n(conf) or n(packed) < 10. Inclusion bar (binding): mean(conf) - mean(packed) >= +0.02.
GT-free in choose / eval. Prints one line and writes JSON.
"""
import argparse, glob, hashlib, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); TOL = 1e-9


def summ(v):
    v = np.array(v, float)
    if not len(v): return dict(n=0)
    return dict(n=int(len(v)), mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 4),
                min=round(float(v.min()), 4), max=round(float(v.max()), 4), median=round(float(np.median(v)), 4))


def cell(results, arm, seed, ep):
    d = f'{results}/pf{arm}s{seed}_glock_public/ep{ep}/best'
    try: s = json.load(open(f'{d}/summary.json'))
    except Exception: return None
    rows = [r for r in s.get('rollouts', []) if 'sim_vs_ref' in r]
    out = dict(checkpoint=s.get('checkpoint'), dir=d, sim_vs_ref=summ([r['sim_vs_ref'] for r in rows]),
               auc=summ([r['auc'] for r in rows if 'auc' in r]), rows=rows)
    pl, sy = [], []
    for r in sorted(glob.glob(f'{d}/r*/timeline.json')):
        t = json.load(open(r)); pl.append(t['sim_vs_ref']); sy.append(t['sim_vs_ref_sym'])
    out['plain'] = summ(pl); out['sym'] = summ(sy)
    return out


def public(a):
    res = dict(rule='docs/research/work/pf-hands-20261101/PREREG.md section 3', eps={})
    lines = []
    for ep in a.eps.split():
        E = {arm: {s: cell(a.results, arm, s, ep) for s in a.seeds.split()} for arm in a.arms.split()}
        thin = [f'{arm}/s{s}' for arm in E for s, c in E[arm].items() if c is None or c['auc'].get('n', 0) < 8]
        r = dict(cells={arm: {s: (None if c is None else {k: c[k] for k in ('checkpoint', 'sim_vs_ref', 'auc', 'plain', 'sym')})
                              for s, c in E[arm].items()} for arm in E})
        if 's' in E and '2h' in E:
            if thin:
                r['label'] = 'INCOMPLETE'; r['why'] = f'cells with < 8 scored rollouts: {thin}'
            else:
                d = {s: E['2h'][s]['auc']['mean'] - E['s'][s]['auc']['mean'] for s in E['s']}
                m = float(np.mean(list(d.values())))
                r.update(paired_diff={s: round(v, 4) for s, v in d.items()}, mean_diff=round(m, 4),
                         label='PASS' if m >= 0.05 - TOL and min(d.values()) >= -0.05 - TOL else 'FAIL')
        res['eps'][ep] = r
        lines.append(f"ep{ep} {r.get('label', 'NO-RULE')} " + ' '.join(
            f"{arm}/s{s}: AUC {c['auc'].get('mean')} svr {c['sim_vs_ref'].get('mean')} sym {c['sym'].get('mean')}"
            for arm in E for s, c in E[arm].items() if c) + (f" mean_diff {r.get('mean_diff')}" if 'mean_diff' in r else ''))
    json.dump(res, open(a.out, 'w'), indent=1); print(' | '.join(lines))


def packed_mean(h5):
    sys.path.insert(0, HERE); from simref_timeline import timeline
    kit = os.environ.get('KIT', '/content/kit/v2d_submission_kit'); v = []
    for d in sorted(glob.glob(f'{h5}/r*/')):
        for f in glob.glob(f'{d}episode_*.parquet'):
            ep = int(os.path.basename(f)[8:14]); v.append(timeline(d, ep, kit)['sim_vs_ref'])
    return v


def choose(a):
    seeds = a.seeds.split(); C = {s: cell(a.results, a.arm, s, a.ep) for s in seeds}
    out = dict(ep=a.ep, arm=a.arm, rule='pack-9b PREREG section 2 + pf-hands PREREG section 4', seeds={s: (None if c is None else
               dict(checkpoint=c['checkpoint'], sim_vs_ref=c['sim_vs_ref'])) for s, c in C.items()})
    thin = [s for s, c in C.items() if c is None or c['sim_vs_ref'].get('n', 0) < 8]
    if thin:
        out['label'] = 'INCOMPLETE'; out['why'] = f'seeds with < 8 scored rollouts: {thin}'
        json.dump(out, open(a.out, 'w'), indent=1); print(out['label'], out['why']); sys.exit(2)
    def key(s):
        return (round(C[s]['sim_vs_ref']['mean'], 4), )
    best = max(seeds, key=lambda s: C[s]['sim_vs_ref']['mean'])
    others = [s for s in seeds if s != best and abs(round(C[s]['sim_vs_ref']['mean'], 4) - round(C[best]['sim_vs_ref']['mean'], 4)) <= 0.005]
    if others:
        cand = [best] + others; sd = {s: C[s]['sim_vs_ref']['sd'] for s in cand}; m = min(sd.values())
        tied = [s for s in cand if sd[s] == m]; best = '42' if '42' in tied else tied[0]
    pk = packed_mean(a.h5); out['packed_h5'] = summ(pk)
    ck = f"{C[best]['dir']}/policy.safetensors"
    out.update(chosen=best, checkpoint=ck, sha256=hashlib.sha256(open(ck, 'rb').read()).hexdigest() if os.path.exists(ck) else None,
               chosen_mean=C[best]['sim_vs_ref']['mean'])
    if len(pk) < 10:
        out['label'] = 'INCOMPLETE'; out['why'] = f'packed H5p7 draws scored: {len(pk)} < 10'
        json.dump(out, open(a.out, 'w'), indent=1); print(out['label'], out['why']); sys.exit(2)
    gate = out['chosen_mean'] > float(np.mean(pk)) or bool(a.nogate)
    out['gate'] = dict(bar=round(float(np.mean(pk)), 4), met=bool(gate), skipped=bool(a.nogate))
    out['label'] = 'CONFIRM' if gate else 'NO-SWAP'
    json.dump(out, open(a.out, 'w'), indent=1)
    print(out['label'], f"seed {best} mean {out['chosen_mean']} vs packed {out['gate']['bar']};",
          {s: C[s]['sim_vs_ref'] for s in seeds})
    sys.exit(0 if gate else 3)


def evaluate(a):
    S = json.load(open(a.score)); ch = json.load(open(a.choice)); T = json.load(open(a.table))['episodes'][str(a.ep)]
    refs = a.refs.split()
    out = dict(ep=a.ep, rule='pack-9b PREREG section 4 + pf-hands / pf-bridge PREREG section 4', refs=refs, choice=ch.get('label'),
               sides={}, clauses={})
    if ch.get('label') != 'CONFIRM':
        out['label'] = 'NO-SWAP' if ch.get('label') == 'NO-SWAP' else 'INCOMPLETE'; out['why'] = f"choice {ch.get('label')}: no confirmation"
    sides = {}; bad = []
    for name in ('conf', 'packed', 'old'):
        rows = S['sets'].get(name, {}).get('rollouts', [])
        want = ch.get('sha256') if name == 'conf' else T['packed_sha256']
        ok = []
        for r in rows:
            if not r.get('scored'): continue
            if not r.get('own_ref_check', {}).get('ok'): bad.append(f'{name} r{r["draw"]} own-reference check'); continue
            if want and r.get('checkpoint_sha256') and r['checkpoint_sha256'] != want: bad.append(f'{name} r{r["draw"]} checkpoint'); continue
            v = {X: r['vs'][X] for X in refs}
            if not all(np.isfinite([v[X][m] for X in refs for m in ('sim_vs_ref', 'RPE')])): continue
            ok.append(dict(draw=r['draw'], **{f'svr_{X}': v[X]['sim_vs_ref'] for X in refs}, **{f'rpe_{X}': v[X]['RPE'] for X in refs}))
        ok.sort(key=lambda x: x['draw']); sides[name] = ok
        out['sides'][name] = {X: dict(sim_vs_ref=summ([x[f'svr_{X}'] for x in ok]), RPE=summ([x[f'rpe_{X}'] for x in ok]),
                                      fails=int(sum(x[f'rpe_{X}'] > 5 for x in ok))) for X in refs}
    for k in S['sets']:
        if k.startswith('train'):
            out['sides'][k] = {X: dict(sim_vs_ref=summ([r['vs'][X]['sim_vs_ref'] for r in S['sets'][k]['rollouts'] if r.get('scored') and X in r.get('vs', {})]))
                               for X in refs}
    if 'label' not in out:
        N, K, O = sides['conf'], sides['packed'], sides['old']
        if bad: out['label'] = 'INVALID'; out['why'] = bad
        elif len(N) < 10 or len(K) < 10 or len(O) != 1: out['label'] = 'INCOMPLETE'; out['why'] = f'n conf {len(N)}, packed {len(K)}, old {len(O)}'
        else:
            for X in refs:
                mN, mK = np.mean([x[f'svr_{X}'] for x in N]), np.mean([x[f'svr_{X}'] for x in K])
                fN, fK = np.mean([x[f'rpe_{X}'] > 5 for x in N]), np.mean([x[f'rpe_{X}'] > 5 for x in K])
                cN, cK = np.median([x[f'rpe_{X}'] for x in N]), np.median([x[f'rpe_{X}'] for x in K])
                out['clauses'][X] = dict(a=dict(conf=round(mN, 4), packed=round(mK, 4), holds=bool(mN >= mK - TOL)),
                                         b=dict(conf=round(fN, 3), packed=round(fK, 3), holds=bool(fN <= fK + TOL)),
                                         c=dict(conf=round(cN, 3), packed=round(cK, 3), holds=bool(cN <= cK + TOL)),
                                         s=dict(conf_draw1=N[0][f'svr_{X}'], old=O[0][f'svr_{X}'], holds=bool(N[0][f'svr_{X}'] >= O[0][f'svr_{X}'] - 0.05 - TOL)),
                                         gain=round(mN - mK, 4))
            if refs == ['P']:          # pf-hands: the pack-9b rule on P
                C = out['clauses']['P']; ok_ = all(C[k]['holds'] for k in 'abcs'); gain = C['gain']
            else:                      # pf-bridge: the full rule on the candidate's own reference B, and clause (a) on P
                C = out['clauses']['B']; ok_ = all(C[k]['holds'] for k in 'abcs') and out['clauses']['P']['a']['holds']; gain = C['gain']
            out['label'] = 'PASS' if ok_ else 'NO-SWAP'
            out['inclusion'] = dict(bar=0.02, on=refs[-1], gain=gain, include=bool(ok_ and gain >= 0.02 - TOL))
    json.dump(out, open(a.out, 'w'), indent=1)
    print(out['label'], json.dumps({k: out[k] for k in ('clauses', 'inclusion', 'why') if k in out}),
          {k: {X: v[X]['sim_vs_ref'].get('mean') for X in v} for k, v in out['sides'].items()})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['public', 'choose', 'eval'])
    for k in ('results', 'eps', 'arms', 'seeds', 'out', 'arm', 'h5', 'score', 'choice', 'table'):
        ap.add_argument(f'--{k}', default=None)
    ap.add_argument('--ep', type=int, default=None)
    ap.add_argument('--refs', default='P', help='eval: "P" or "P B" (B = the candidate\'s own bridged reference)')
    ap.add_argument('--nogate', action='store_true', help='choose: confirm the chosen seed without the training-box gate')
    a = ap.parse_args()
    {'public': public, 'choose': choose, 'eval': evaluate}[a.mode](a)
