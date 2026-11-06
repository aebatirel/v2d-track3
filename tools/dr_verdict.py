"""Verdict of the pack 9b D arm under the agreed swap rule (2026-10-31; rule fixed in docs/research/work/pack9b-20261031/
PREREG.md sections 4 and 6 before any D result). GT-free throughout; one reference (the packed one, P). The logic is
tools/e10v_verdict.py's, per episode and on one reference.

Inputs:
  --merge C.json        tools/dr_eval_merge.py's output: per episode CANDIDATE (run, seed, checkpoint sha256, packed sha256),
                        INCOMPLETE or OUT (a training box INVALID);
  --table packed_refs   the packed reference md5 / fingerprint and the packed checkpoint sha256 per episode;
  --score S.json ...    tools/dr_score.py outputs (one or more per episode; later files win a set name of their episode):
                        conf = the candidate's confirmation draws, packed = the packed policy's H5p7 draws, old = the old
                        packed draw; every set scored against P (own P);
  --pack-check F.json   the confirmation box's tools/dr_pack_check.py outputs (results/final_eval/dr_pack_check.json
                        before draw 1, results/h5/dr_pack_check.json before draws 2..N); both are required.
Per CANDIDATE episode, N = conf's scored draws, K = packed's scored draws (a rollout counts only if dr_score marked it
scored and its sim_vs_ref, RPE, MPPE and AUC are finite):
  (a) mean sim_vs_ref(N) >= mean sim_vs_ref(K)
  (b) share of N with RPE > 5 cm <= that share of K
  (c) median RPE(N) <= median RPE(K)
  (s) sim_vs_ref(N's draw 1) >= sim_vs_ref(old packed draw) - 0.05; draw 1 = the lowest r<i> with a scored rollout
  each with a 1e-9 tolerance in favour of "holds".
Labels:
  INVALID     merge OUT (a training box INVALID); a pack check missing, refused, or not showing this episode evaluated
              with the candidate checkpoint; P's md5 not the table's; a scored rollout failing the own-reference check
              or naming another checkpoint (conf: the candidate's sha256; packed / old: the table's packed sha256); a
              clause value NaN / inf;
  INCOMPLETE  merge INCOMPLETE; n(N) < 10, n(K) < 10, the old packed draw not scored exactly once, no scored draw 1;
  PASS        every clause holds (the episode's D draw-1 rollout replaces its packed rollout in pack 9b; the upload is
              decided outside this job);
  NO-SWAP     otherwise.
Reported, not gating: n / mean / sd / min / max / median per side and metric, fail counts, audit.py's own flag, per-object
AUC means, each clause's margin, an EQUAL FLOOR note (both sides fail >= 90 % of draws), the sd reading of [H-dr] (PREREG
section 5), the old draw against pack 7's summary value.
Usage: dr_verdict.py --merge C.json --table packed_refs.json --score S.json [...] --pack-check F.json [...] --out V.json [--min_n 10]
"""
import argparse, json, math, os, statistics, sys

TOL, SEC_DROP, RPE_FAIL = 1e-9, 0.05, 5.0
OLD_P7 = {'14': 0.9094, '16': 0.9079, '25': 0.8937, '30': 0.9229, '33': 0.9401}   # pack 7 summary.txt (= pack 9a+'s draws)


def fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def stats(v):
    if not v:
        return None
    m = sum(v) / len(v); sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
    return dict(n=len(v), mean=round(m, 4), sd=round(sd, 4), min=round(min(v), 4), max=round(max(v), 4), median=round(statistics.median(v), 4))


def scored(rows):
    """rollouts dr_score marked scored, with every score on P finite (a non-finite one is 'not scored', PREREG 4)"""
    return [r for r in rows if r.get('scored') and 'P' in r.get('vs', {})
            and all(fin(r['vs']['P'].get(k)) for k in ('sim_vs_ref', 'RPE', 'MPPE', 'AUC'))]


def side(rows):
    s = [r['vs']['P'] for r in rows]
    return dict(n=len(s), sim_vs_ref=stats([x['sim_vs_ref'] for x in s]), RPE=stats([x['RPE'] for x in s]),
                MPPE=stats([x['MPPE'] for x in s]), AUC=stats([x['AUC'] for x in s]),
                fails=sum(1 for x in s if x['RPE'] > RPE_FAIL), fail_rate=round(sum(1 for x in s if x['RPE'] > RPE_FAIL) / len(s), 4) if s else None,
                audit_fails=sum(1 for x in s if x.get('audit_fail')),
                objects={o: round(sum(x['objects'][o]['AUC'] for x in s) / len(s), 4) for o in (s[0].get('objects') or {} if s else {})},
                draws=[r.get('draw') for r in rows],
                mean_raw=sum(x['sim_vs_ref'] for x in s) / len(s) if s else None,
                fail_raw=sum(1 for x in s if x['RPE'] > RPE_FAIL) / len(s) if s else None,
                median_rpe_raw=statistics.median([x['RPE'] for x in s]) if s else None)


def clauses_of(n, k, d1, old):
    """the four clauses from raw values; None (and the clause name) if any value is not finite"""
    vals = dict(a=(n['mean_raw'], k['mean_raw']), b=(n['fail_raw'], k['fail_raw']), c=(n['median_rpe_raw'], k['median_rpe_raw']),
                s=(d1, None if old is None else old - SEC_DROP))
    for c, (x, y) in vals.items():
        if not (fin(x) and fin(y)):
            return None, f'clause {c} is not finite ({x}, {y})'
    return dict(
        a=dict(new_mean=round(vals['a'][0], 4), packed_mean=round(vals['a'][1], 4), holds=vals['a'][0] >= vals['a'][1] - TOL,
               margin=round(vals['a'][0] - vals['a'][1], 4)),
        b=dict(new_fail_rate=round(vals['b'][0], 4), packed_fail_rate=round(vals['b'][1], 4), holds=vals['b'][0] <= vals['b'][1] + TOL,
               margin=round(vals['b'][1] - vals['b'][0], 4)),
        c=dict(new_median_rpe=round(vals['c'][0], 4), packed_median_rpe=round(vals['c'][1], 4), holds=vals['c'][0] <= vals['c'][1] + TOL,
               margin=round(vals['c'][1] - vals['c'][0], 4)),
        s=dict(new_draw1=round(d1, 4), old_packed_draw=round(old, 4), bar=round(old - SEC_DROP, 4), holds=d1 >= old - SEC_DROP - TOL,
               margin=round(d1 - (old - SEC_DROP), 4))), None


def episode(e, M, T, sets, ref_md5s, checks, min_n):
    """(label, why, clauses, sides, extra) of one episode"""
    if not M:
        return 'INCOMPLETE', ['no merge entry (the episode was not trained or not merged)'], {}, {}, {}
    dec = M.get('decision', '')
    if dec.startswith('OUT'):
        return 'INVALID', [f'training: {dec}'], {}, {}, {}
    if dec.startswith('INCOMPLETE'):
        return 'INCOMPLETE', [f'training: {dec}', json.dumps(M.get('todo', {}))[:300]], {}, {}, {}
    sha = M.get('sha256')
    N = scored((sets.get('conf') or {}).get('rollouts', [])); K = scored((sets.get('packed') or {}).get('rollouts', []))
    O = scored((sets.get('old') or {}).get('rollouts', []))
    sides = dict(new=side(N), packed=side(K))
    bad = []
    if len(checks) < 2:
        bad.append(f'pack-side check files: {len(checks)} of 2 (before draw 1 and before draws 2..N; PREREG 3)')
    for name, c in checks:
        row = (c.get('episodes') or {}).get(e)
        if not c.get('ok'):
            bad.append(f'{name}: dr_pack_check refused: {(c.get("failures") or [])[:3]}')
        elif e not in [str(x) for x in c.get('dr_eps', [])] or not row:
            bad.append(f'{name}: ep{e} not checked as a D candidate (dr_eps {c.get("dr_eps")})')
        elif row.get('checkpoint_sha256') != sha:
            bad.append(f'{name}: ep{e} evaluated checkpoint {str(row.get("checkpoint_sha256"))[:12]}, the candidate is {str(sha)[:12]}')
    if not sha:
        bad.append('the merge names no candidate sha256')
    for X, s_ in ref_md5s.items():
        if s_ != {T['md5']}:
            bad.append(f'reference {X} md5 across score files {sorted(s_)} != the packed reference {T["md5"]}')
    for name, s_ in sets.items():
        want = sha if name == 'conf' else T['packed_sha256'] if name in ('packed', 'old') else None
        for r in s_.get('rollouts', []):
            if not r.get('scored'):
                continue
            if s_.get('own') != 'P' or not (r.get('own_ref_check') or {}).get('ok'):
                bad.append(f'{name}/r{r.get("draw")}: own-reference check not ok (own {s_.get("own")})')
            if want and r.get('checkpoint_sha256') != want:
                bad.append(f'{name}/r{r.get("draw")}: checkpoint {str(r.get("checkpoint_sha256"))[:12]} != {str(want)[:12]}')
    if bad:
        return 'INVALID', bad[:8], {}, sides, {}
    draw1 = min(N, key=lambda r: r.get('draw', 0), default=None)
    inc = []
    if len(N) < min_n:
        inc.append(f'{len(N)} scored confirmation draws (< {min_n}; top up the same checkpoint, PREREG 6)')
    if len(K) < min_n:
        inc.append(f'{len(K)} scored packed-policy draws (< {min_n}; top up the packed checkpoint, PREREG 6)')
    if len(O) != 1:
        inc.append(f'old packed draw scored {len(O)} times (1 needed)')
    if draw1 is None:
        inc.append('no scored confirmation draw')
    if inc:
        return 'INCOMPLETE', inc, {}, sides, {}
    old = O[0]['vs']['P']['sim_vs_ref']; d1 = draw1['vs']['P']['sim_vs_ref']
    cl, err = clauses_of(sides['new'], sides['packed'], d1, old)
    if cl is None:
        return 'INVALID', [err], {}, sides, {}
    cl['s'].update(new_draw1_r=draw1.get('draw'), new_draw1_path=draw1.get('path'))
    extra = dict(old_vs_pack7_summary=dict(scored=round(old, 4), pack7=OLD_P7.get(e),
                                           matches=OLD_P7.get(e) is not None and abs(round(old, 4) - OLD_P7[e]) <= 1e-4),
                 draw1=dict(r=draw1.get('draw'), path=draw1.get('path'), checkpoint_sha256=draw1.get('checkpoint_sha256')))
    failed = [c for c, v in cl.items() if not v['holds']]
    if not failed:
        return 'PASS', ['every clause holds'], cl, sides, extra
    return 'NO-SWAP', [f'fails: {failed}'], cl, sides, extra


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--merge', required=True); ap.add_argument('--table', required=True)
    ap.add_argument('--score', action='append', default=[]); ap.add_argument('--pack-check', action='append', default=[])
    ap.add_argument('--out', required=True); ap.add_argument('--min_n', type=int, default=10)
    ap.add_argument('--eps', default='14 16 25 30 33')
    a = ap.parse_args()
    js = lambda f: json.load(open(f)) if f and os.path.isfile(f) else None
    merge = js(a.merge) or {}; tab = json.load(open(a.table))['episodes']
    sets, refs = {}, {}
    for f in a.score:
        d_ = js(f) or {}
        e = str(d_.get('ep'))
        for X, info in d_.get('refs', {}).items():
            refs.setdefault(e, {}).setdefault(X, set()).add(info.get('md5'))
        for k, v in d_.get('sets', {}).items():
            sets.setdefault(e, {})[k] = v
    checks = [(f, js(f)) for f in a.pack_check if js(f) is not None]
    out = dict(rule='docs/research/work/pack9b-20261031/PREREG.md sections 4 and 6', min_n=a.min_n, episodes={})
    for e in a.eps.split():
        M = (merge.get('episodes') or {}).get(e)
        label, why, cl, sides, extra = episode(e, M, tab[e], sets.get(e, {}), refs.get(e, {}), checks, a.min_n)
        fl = (sides.get('new') or {}).get('fail_raw'), (sides.get('packed') or {}).get('fail_raw')
        equal_floor = all(x is not None and x >= 0.9 for x in fl)
        sdn, sdk = ((sides.get('new') or {}).get('sim_vs_ref') or {}).get('sd'), ((sides.get('packed') or {}).get('sim_vs_ref') or {}).get('sd')
        out['episodes'][e] = dict(
            label=label, why=why, clauses=cl,
            sides={k: {kk: vv for kk, vv in v.items() if not kk.endswith('_raw')} for k, v in sides.items()},
            equal_floor_note=('both sides fail >= 90 % of their draws: the rule compares two floors; a PASS here has an '
                              'expected effect of about 0') if equal_floor else None,
            h_dr_sd_reading=dict(new_sd=sdn, packed_sd=sdk, lower=(sdn < sdk) if sdn is not None and sdk is not None else None),
            candidate={k: (M or {}).get(k) for k in ('decision', 'run', 'seed', 'sha256', 'store_checkpoint', 'stats')},
            counts={k: dict(own=v.get('own'), n_files=v.get('n_files'), n_scored=v.get('n_scored')) for k, v in sets.get(e, {}).items()},
            **extra)
    out['pack9b'] = {e: x['draw1'] for e, x in out['episodes'].items() if x['label'] == 'PASS'}
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    for e, x in out['episodes'].items():
        s = x['sides']
        print(f'ep{e} {x["label"]}' + (' [EQUAL FLOOR]' if x['equal_floor_note'] else '') + ' :: ' + '; '.join(x['why'])
              + (' :: ' + ' | '.join(f"{c} {'ok' if v['holds'] else 'FAIL'} margin {v['margin']}" for c, v in x['clauses'].items()) if x['clauses'] else '')
              + (f" :: new {(s['new'].get('sim_vs_ref') or {}).get('mean')} (n {s['new']['n']}, RPE med {(s['new'].get('RPE') or {}).get('median')}, fails {s['new']['fails']})"
                 f" vs packed {(s['packed'].get('sim_vs_ref') or {}).get('mean')} (n {s['packed']['n']}, RPE med {(s['packed'].get('RPE') or {}).get('median')}, fails {s['packed']['fails']})"
                 if s.get('new') else ''))
    print(f'pack 9b swaps (PASS): {sorted(out["pack9b"], key=int) or "none"}')


if __name__ == '__main__':
    main()
