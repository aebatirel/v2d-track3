"""Applies the pre-registered adoption rule of the masses eval retrain, PLAN section 5 rules 4-9 (and the rule-10
report), to the confirmation box's results on CPU (2026-10-31, review F4; docs/research/work/masses-eval-20261031/PLAN.md,
JOBS.txt "C1"). Committed before C1 launches, so the rule is applied by code fixed in advance, not by hand. No ground
truth: every number is sim_vs_ref against our own stored reference.

Inputs:
  --h5     the C1 box's results/h5/h5_summary.json (ops/jobs/h5_reeval.sh: per evaluated episode n, mean, sd ddof 1, min,
           p20 and `packed` = PACKED_TXT's value, i.e. the board pack's packed draw);
  --merge  c1_merge.json (tools/mass_eval_merge.py: per retrained episode CANDIDATE / INCOMPLETE / OUT, both seeds'
           training-box stats, the chosen seed and run);
  --board  pack7 | pack8: the pack on the leaderboard when the rule is applied (pack 7 is uploaded; pack 8 only if the
           owner uploads it first);
  [--c1-run RUN] the confirmation run id, for the pack-9 input list (rule 8).
Fixed here, from PLAN section 1 (the levels and bars; asserted against the files they come from):
  - bars: the board pack's summary.txt (pack 7 results/submissions/20261030-track3g-candidate/summary.txt, pack 8
    .../20261030-track3h-candidate/summary.txt); eval 1 must also reach 0.9241 (rule 5: the c01s43 carve's 20-draw mean);
  - levels (mean, sd ddof 1): H5 of 29 Oct (docs/analysis/h5-20261029/h5_summary.json, 10 official draws of pack 6's
    policies), except eval 33 = c33B (runs/20261030-c33B-0202139/results/h5/h5_summary.json: 0.9344 +- 0.0076, n 10) and,
    with pack 8 on the board, eval 1 = e1conf2 (runs/20261030-e1conf2-d41382e/results/h5/h5_summary.json: 0.9241 +- 0.017,
    n 20); with pack 7 eval 1's level is H5's std0116 (0.8219 +- 0.2387);
  - spoon stratum 3, 5, 6, 15, 16, 32, 33, 35, 36, 37; pilots 33 and 15.
Per episode of the merge:
  - merge OUT (a training box INVALID, rule 3) -> KEEP; merge INCOMPLETE (a seed missing or n < 8, rule 2 as amended
    31 Oct) -> INCOMPLETE (training): the packed policy stays until the named seeds are retrained; neither is confirmed;
  - rule 4: a CANDIDATE missing from h5_summary.json, or with n < 8 scored draws -> INCOMPLETE (only the confirmation is
    repeated, never the training);
  - rule 5: BOARD SWAP iff mean >= bar (eval 1: also >= 0.9241);
  - rule 6: otherwise INSURANCE (offered; the owner decides) iff mean >= level + 0.03 and sd <= the level's sd; reported
    with its expected board effect (mean - packed draw) / 20 x 0.76 [E];
  - rule 7: otherwise KEEP.
  Thresholds are rounded to 4 decimals, as PLAN section 5 writes them (e.g. eval 3: >= 0.9339, sd <= 0.0717).
  - rule 8: the pack-9 inputs: a BOARD SWAP episode's rollout is C1's draw 1 (results/submission/results/
    episode_<N>.{json,parquet}, by position, never by score); every other episode keeps the board pack's rollout byte for
    byte; an INSURANCE swap enters only on the owner's word. The CPU repack itself (B7) is not built (BUILD.md).
  - rule 9 (spoon pilots 33 and 15): a pilot is "below" iff its confirmation mean < level - 0.02 (33: 0.9344 - 0.02 =
    0.9144, which PLAN section 5 writes rounded as 0.914; 15: 0.9397). Neither below -> PROPOSE wave 2 (5, 32, 6, 3; a
    separate owner GO); both below -> CLOSED; one below -> OWNER DECIDES. A pilot without a confirmation reading
    (INCOMPLETE, OUT, not retrained) -> NO READING (pending, or not covered by rule 9: the owner decides). A mean between
    the written 0.914 and the formula's 0.9144 -> AMBIGUOUS (the owner decides; the rule is not re-read after a result).
Refused (exit 2, nothing applied): an h5 episode that is not a merge CANDIDATE; an h5 `packed` value that is not the
board pack's packed draw (C1 ran with another PACKED_TXT, or --board is wrong).
Usage: mass_eval_rule.py --h5 H5.json --merge C1_MERGE.json --board pack7|pack8 [--c1-run RUN] --out RULE.json
"""
import argparse, hashlib, json, math, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_N = 8                                         # rule 4 (and rule 2 as amended 31 Oct)
INS_MARGIN, SPOON_MARGIN, LB = 0.03, 0.02, 0.76   # rule 6, rule 9, transfer 0.74-0.78 [M, pack 7]
EVAL1_CARVE = 0.9241                              # rule 5: c01s43's 20-draw mean (e1conf2)
H5_FILE, H5_MD5 = 'docs/analysis/h5-20261029/h5_summary.json', 'cff23c68795858d125e53a6d119aed05'
PACKS = {'pack7': ('results/submissions/20261030-track3g-candidate/summary.txt', '24e3c8c16483e14c4bccdd94ac1807e4'),
         'pack8': ('results/submissions/20261030-track3h-candidate/summary.txt', '2ee771517cf45d104f509566cb4cafcd')}
C33B = dict(mean=0.9344, sd=0.0076, n=10, src='runs/20261030-c33B-0202139/results/h5/h5_summary.json (md5 39a2f7c7...)')
E1CONF2 = dict(mean=0.9241, sd=0.017, n=20, src='runs/20261030-e1conf2-d41382e/results/h5/h5_summary.json (md5 1a2f7a1a...)')
SPOON = {'3', '5', '6', '15', '16', '32', '33', '35', '36', '37'}
PILOTS = ('33', '15')
WAVE2 = ('5', '32', '6', '3')
PLAN_WRITTEN_SPOON = {'33': 0.914, '15': 0.9397}  # rule 9 as written (33's is 0.9144 rounded)


def md5(f):
    return hashlib.md5(open(f, 'rb').read()).hexdigest()


def r4(x):
    return round(x + 0.0, 4)


def levels_and_bars(board, repo=REPO):
    """({ep: dict(mean, sd, n, src)}, {ep: packed draw}) for the board pack, from the files PLAN section 1 names."""
    f = os.path.join(repo, H5_FILE)
    if md5(f) != H5_MD5:
        sys.exit(f'{H5_FILE}: md5 {md5(f)} is not the one fixed with the rule ({H5_MD5})')
    lv = {e: dict(mean=v['mean'], sd=v['sd'], n=v['n'], src=f'{H5_FILE} (H5, pack 6 policy)') for e, v in json.load(open(f)).items()}
    lv['33'] = dict(C33B)
    if board == 'pack8':
        lv['1'] = dict(E1CONF2)
    pf, pm = PACKS[board]
    pf = os.path.join(repo, pf)
    if md5(pf) != pm:
        sys.exit(f'{pf}: md5 {md5(pf)} is not the {board} summary fixed with the rule ({pm})')
    bars = {e: float(v) for e, v in json.loads(open(pf).readline()).items()}
    return lv, bars


def apply(h5, merge, board, c1_run='', repo=REPO):
    """The rule over parsed inputs (h5 = h5_summary.json, merge = c1_merge.json); returns the result dict, or
    dict(refused=[...]) when the inputs do not belong together (nothing is applied then)."""
    lv, bars = levels_and_bars(board, repo)
    M = merge['episodes']
    cand = {e for e, x in M.items() if x['decision'] == 'CANDIDATE'}
    errors = []
    for e in h5:
        if e not in cand:
            errors.append(f'ep{e}: in h5_summary.json but not a merge CANDIDATE (the confirmation evaluated another episode)')
        elif h5[e].get('packed') is not None and abs(float(h5[e]['packed']) - bars[e]) > 1e-9:
            errors.append(f'ep{e}: h5 packed {h5[e]["packed"]} is not {board}\'s packed draw {bars[e]} (PACKED_TXT or --board)')
    if errors:
        return dict(refused=errors)
    out = {}
    for e in sorted(M, key=int):
        x = M[e]; L = lv[e]; bar = bars[e]
        bar_swap = max(bar, EVAL1_CARVE) if e == '1' else bar
        ins_mean, ins_sd = r4(L['mean'] + INS_MARGIN), L['sd']
        row = dict(stratum='spoon' if e in SPOON else 'masses', level=L, packed=bar, bar=bar_swap,
                   insurance_needs=dict(mean=ins_mean, sd=ins_sd), training=x.get('stats'), seed=x.get('seed'),
                   run=x.get('run'), merge=x['decision'])
        if x['decision'].startswith('OUT'):
            row.update(verdict='KEEP', rule='3', why=x['decision'])
        elif x['decision'].startswith('INCOMPLETE'):
            row.update(verdict='INCOMPLETE (training)', rule='2', why=x['decision'], todo=x.get('todo'))
        elif e not in h5:
            row.update(verdict='INCOMPLETE', rule='4', why='no confirmation result for this candidate: repeat only the confirmation')
        else:
            c = h5[e]; n = int(c['n'])
            row['confirmation'] = dict(n=n, mean=c['mean'], sd=c['sd'], min=c.get('min'),
                                       se=round(c['sd'] / math.sqrt(n), 4) if n > 0 else None)
            row['delta_vs_level'] = round(c['mean'] - L['mean'], 4)
            if n < MIN_N:
                row.update(verdict='INCOMPLETE', rule='4', why=f'{n} scored draws < {MIN_N}: repeat only the confirmation')
            elif c['mean'] >= bar_swap:
                row.update(verdict='BOARD SWAP', rule='5', why=f'mean {c["mean"]} >= bar {bar_swap}'
                           + (f' (packed {bar}, eval 1 also >= {EVAL1_CARVE})' if e == '1' else ''))
            elif c['mean'] >= ins_mean and c['sd'] <= ins_sd:
                row.update(verdict='INSURANCE (offered; the owner decides)', rule='6',
                           why=f'mean {c["mean"]} < bar {bar_swap}, >= level + {INS_MARGIN} = {ins_mean}, sd {c["sd"]} <= {ins_sd}')
            else:
                row.update(verdict='KEEP', rule='7', why=f'mean {c["mean"]} < bar {bar_swap}; insurance needs mean >= {ins_mean} '
                           f'and sd <= {ins_sd}')
            if row['verdict'] in ('BOARD SWAP', 'INSURANCE (offered; the owner decides)'):
                row['expected_board_effect'] = round((c['mean'] - bar) / 20 * LB, 5)
        out[e] = row
    # rule 9: the spoon pilots
    pil = {}
    for p in PILOTS:
        r = out.get(p)
        if not r or 'confirmation' not in r or r['verdict'].startswith('INCOMPLETE'):
            pil[p] = dict(reading=None, why=(r['verdict'] + ': ' + r['why']) if r else 'not retrained in this batch')
            continue
        m, thr = r['confirmation']['mean'], r4(r['level']['mean'] - SPOON_MARGIN)
        below, below_written = m < thr, m < PLAN_WRITTEN_SPOON[p]
        pil[p] = dict(reading='AMBIGUOUS' if below != below_written else ('below' if below else 'not below'),
                      mean=m, threshold=thr, written=PLAN_WRITTEN_SPOON[p])
    rd = [v['reading'] for v in pil.values()]
    if any(x is None for x in rd):
        spoon = 'NO READING: ' + '; '.join(f'pilot {p}: {v["why"]}' for p, v in pil.items() if v['reading'] is None) + \
                ' (pending the repeated confirmation or retrain; if a pilot cannot be read, rule 9 does not cover it: the owner decides)'
    elif 'AMBIGUOUS' in rd:
        spoon = 'AMBIGUOUS: a pilot mean lies between the written and the computed rule-9 threshold; the owner decides'
    elif rd.count('below') == 2:
        spoon = 'CLOSED: both pilots below level - 0.02; no more spoon retrains'
    elif rd.count('below') == 1:
        spoon = 'OWNER DECIDES: one pilot below level - 0.02'
    else:
        spoon = f'PROPOSE wave 2 ({", ".join(WAVE2)}) on a separate owner GO: neither pilot below level - 0.02'
    # rule 8: the pack-9 inputs
    swaps = [e for e, r in out.items() if r['verdict'] == 'BOARD SWAP']
    offered = [e for e, r in out.items() if r['verdict'].startswith('INSURANCE')]
    src = lambda e: f'runs/{c1_run or "<C1 run>"}/results/submission/results/episode_{int(e):06d}.{{json,parquet}} (C1 draw 1, by position)'
    pack9 = dict(board=board, swap={e: src(e) for e in swaps}, insurance_if_owner_accepts={e: src(e) for e in offered},
                 note='every other episode keeps the board pack\'s rollout byte for byte; CPU repack (B7, not built); the owner decides any upload'
                 if swaps or offered else 'no swap: no pack-9 candidate')
    strata = {}
    for k in ('masses', 'spoon'):
        rs = [r for r in out.values() if r['stratum'] == k]
        d = [r['delta_vs_level'] for r in rs if 'delta_vs_level' in r and not r['verdict'].startswith('INCOMPLETE')]
        strata[k] = dict(episodes=len(rs), verdicts={v: sum(r['verdict'] == v for r in rs) for v in sorted({r['verdict'] for r in rs})},
                         mean_delta_vs_level=round(sum(d) / len(d), 4) if d else None,
                         expected_board_effect_of_swaps=round(sum(r.get('expected_board_effect', 0) for r in rs if r['verdict'] == 'BOARD SWAP'), 5))
    return dict(board=board, rule='docs/research/work/masses-eval-20261031/PLAN.md section 5 rules 4-9 (amended 31 Oct)',
                episodes=out, spoon_pilots=pil, spoon_stratum=spoon, pack9=pack9, strata=strata,
                note='delta_vs_level is masses + seed + code, not masses alone; scores are sim_vs_ref vs our reference [M]; '
                     'board effects are estimates [E]')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--h5', required=True); ap.add_argument('--merge', required=True)
    ap.add_argument('--board', required=True, choices=sorted(PACKS)); ap.add_argument('--c1-run', default='')
    ap.add_argument('--out', required=True); ap.add_argument('--repo', default=REPO)
    a = ap.parse_args()
    R = apply(json.load(open(a.h5)), json.load(open(a.merge)), a.board, a.c1_run, a.repo)
    json.dump(R, open(a.out, 'w'), indent=1)
    if 'refused' in R:
        print('REFUSED (nothing applied): ' + ' | '.join(R['refused'])); sys.exit(2)
    for e, r in R['episodes'].items():
        c = r.get('confirmation')
        print(f'ep{e} [{r["stratum"]}] {r["verdict"]} (rule {r["rule"]}): {r["why"]}'
              + (f' :: confirmation n {c["n"]} mean {c["mean"]} sd {c["sd"]} min {c["min"]} se {c["se"]}; level {r["level"]["mean"]} '
                 f'+- {r["level"]["sd"]}; delta {r["delta_vs_level"]} (masses + seed + code)' if c else '')
              + (f'; board effect {r["expected_board_effect"]:+.5f} LB [E]' if 'expected_board_effect' in r else '')
              + (f' :: training {json.dumps(r["training"])}' if r.get('training') else ''))
    print(f'spoon stratum (rule 9): {R["spoon_stratum"]}')
    print(f'pack 9 (rule 8): swap {sorted(R["pack9"]["swap"], key=int)}, insurance offered {sorted(R["pack9"]["insurance_if_owner_accepts"], key=int)}; {R["pack9"]["note"]}')
    print('strata: ' + json.dumps(R['strata']))


if __name__ == '__main__':
    main()
