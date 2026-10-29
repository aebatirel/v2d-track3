"""verify_timing: collect the official-scorer JSONs written by run_scores.sh / run_sim.sh and tabulate deltas vs the
unshifted path (27 Oct 2026). Usage: python -I vt_summarize.py OUT.json"""
import sys, os, json, glob, re
import numpy as np
W = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/work/verify_timing'
TIMING_COST = '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/timing/cost.json'


def main():
    S = {}
    for f in glob.glob(f'{W}/scores/*.json'):
        m = re.match(r'ep(\d+)_(perc|ref|pre)_(.+)\.json$', os.path.basename(f))
        if not m:
            continue
        d = json.load(open(f))['perception']
        S.setdefault((int(m[1]), m[2]), {})[m[3]] = dict(AUC=d['AUC'], per_obj=d['per_obj_AUC'])
    theirs = json.load(open(TIMING_COST))['episodes']
    out = {'per_source': {}, 'means': {}}
    for (ep, src), v in sorted(S.items()):
        if 's0' not in v:
            continue
        b = v['s0']['AUC']
        row = {k: round(x['AUC'] - b, 4) for k, x in v.items() if k != 's0'}
        row['base'] = b
        th = theirs.get(str(ep), {}).get(src)
        if th:
            row['theirs_base'] = th['base']; row['theirs_shift_pool_delta'] = round(th['shift_pool'] - th['base'], 4)
        row['per_obj'] = {k: x['per_obj'] for k, x in v.items()}
        out['per_source'][f'{ep}:{src}'] = row
    for src in ('perc', 'ref'):
        rows = {k: r for k, r in out['per_source'].items() if k.endswith(':' + src) and not k.startswith('23:')}
        keys = sorted({kk for r in rows.values() for kk in r if kk not in ('base', 'per_obj', 'theirs_base', 'theirs_shift_pool_delta')})
        m = {}
        for kk in keys:
            vals = [r[kk] for r in rows.values() if kk in r]
            m[kk] = dict(n=len(vals), mean=round(float(np.mean(vals)), 4), improved=int(sum(x > 0 for x in vals)))
        out['means'][src] = m
    sim = {}
    for f in glob.glob(f'{W}/sim/*.json'):
        m = re.match(r'ep(\d+)_(r\d)_(.+)\.json$', os.path.basename(f))
        if m:
            sim.setdefault(f'{m[1]}:{m[2]}', {})[m[3]] = json.load(open(f))['perception']['AUC']
    out['sim'] = {k: dict(v, **{f'd_{kk}': round(vv - v['s0'], 4) for kk, vv in v.items() if kk != 's0'}) for k, v in sim.items() if 's0' in v}
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    for k, r in out['per_source'].items():
        print(k, {kk: vv for kk, vv in r.items() if kk != 'per_obj'})
    print(json.dumps(out['means'], indent=1))
    print(json.dumps(out['sim'], indent=1))


if __name__ == '__main__':
    main()
