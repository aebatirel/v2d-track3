"""Phase-1 readings (PLAN.md §2, §4) and the markdown tables of RESULTS.md, from the scored Phase-1 tracks.
ORACLE SIDE: every input holds mocap-derived scores of public episodes; nothing here feeds eval inference.
Inputs (this folder): scores/xstar_trk_{Po,Ps,Po2}.json (tools/xstar_fit.py trk on the Phase-1 tracks: lib = library_v3
at the kit registration X_kit, * = X*_geom, trk = X*_trk refitted to mocap per track, trk_ls), scores/p1_check.json
(p1_check.py), ../tierA/xstar_trk.json (the refine-baseline P, 25 Oct tracks), docs/analysis/h5-20261029/h5_summary.json.
Readings, all on identical poses per convention:
  L2 template   R*(P_s) - R*(P_o). Rule: tools/leak_read.py ref_rule (PLAN §4 reference level: leaks = mean >= 0.01,
                >= 60 % of episodes that sign, > 2x the P_o-repeat noise; no leak = |mean| < 0.005). Beside it: lib - lib,
                trk - trk, and R*(P_s) - R_lib(P_o) (the true-shape mesh tracked AND submitted, vs ours: a mesh swap in
                the leaderboard convention, = L2 on * minus L1 on P_o)
  noise         mean |R*(P_o) - R*(P_o2)| over the 10 twins (the noise value of the rule; max and RMS beside it)
  L3 tracker    1 - R*(P_s): constant part R_trk(P_s) - R*(P_s), varying part 1 - R_trk(P_s)
  L1 registr.   R_lib - R* (PLAN §2); the verdict row is the loss R* - R_lib, as tierA/results_tables.py
  drift         R*(P_o) - R*(refine P): the 30 Oct code (87fc869, library_v3) vs the 25 Oct tracks (library_v2)
Per object class: the same rules on the per-object AUCs (the kit pins the scene on slot 0's frame 0, so a per-object
AUC also depends on the slot-0 track). LB [E] (PLAN §2, fixed before any reading; as tierA/results_tables.py):
dT_e = a S_e dR(twin(e)) for the evals with H5 S_e >= 0.8, L = (c/20) sum_e dT_e, c in {0.74, 1.0}; the 10 spoon
evals get an [E-analogy] row from the spoon-proxy class (sweeper, dust pan), never added to the twin total.
Usage: python -I p1_tables.py [--json OUT]
(2026-10-30)
"""
import argparse, json, os, sys
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(D, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools'))
from leak_read import ref_rule, ref_conv, EVAL_TWINS, A_REF, C_LB, S_MIN  # noqa: E402

SC = {k: json.load(open(f'{D}/scores/xstar_trk_{k}.json'))['episodes'] for k in ('Po', 'Ps', 'Po2')}
SC['ref'] = json.load(open(f'{D}/../tierA/xstar_trk.json'))['episodes']
CHK = json.load(open(f'{D}/scores/p1_check.json'))['episodes']
H5 = json.load(open(f'{REPO}/docs/analysis/h5-20261029/h5_summary.json'))
EPS = sorted(int(e) for e in SC['Po'])
TWINS = sorted(int(e) for e in SC['Po2'])
SPOON_EVALS = (3, 5, 6, 15, 16, 32, 33, 35, 36, 37)
OUTLIERS = {0: 'P_s frame-0 failure (scan templates)', 23: 'identity swap of the two boards in our tracks'}
CLASSES = {'cups': ('blue_cup', 'beige_cup'), 'rack': ('plastic_dish_rack',), 'pitcher': ('water_pitcher',),
           'boards': ('wooden_piece_1', 'wooden_piece_2'), 'spoon proxies': ('mini_sweeper', 'mini_dust_pan'),
           'pot/lid': ('white_pot', 'white_pot_lid')}
SHORT = dict(beige_cup='beige', blue_cup='blue', mini_dust_pan='pan', mini_sweeper='sweeper', plastic_dish_rack='rack',
             water_pitcher='pitcher', white_pot='pot', white_pot_lid='lid', wooden_piece_1='board1', wooden_piece_2='board2')


def R(arm, ep, conv='star', obj=None):
    s = SC[arm][str(ep)]['scores'][conv]
    return s['AUC'] if obj is None else s['per_obj_AUC'][obj]


def objs(ep):
    return list(SC['Po'][str(ep)]['scores']['star']['per_obj_AUC'])


def per_obj(f, eps=EPS, names=None):  # {(ep, obj): f(ep, obj)}
    return {(e, n): f(e, n) for e in eps for n in objs(e) if names is None or n in names}


def rule(d, noise=None):  # tools/leak_read.py ref_rule on a dict, plus the mean without the known outliers
    r = ref_rule({str(k): v for k, v in d.items()}, noise)
    ex = [v for k, v in d.items() if (k[0] if isinstance(k, tuple) else k) not in OUTLIERS]
    r['mean_wo_0_23'] = round(float(np.mean(ex)), 5) if ex else None
    r['wo_0_23'] = ref_rule({str(i): v for i, v in enumerate(ex)}, noise)['verdict'] if ex else None
    r['min'], r['max'] = round(float(min(d.values())), 4), round(float(max(d.values())), 4)
    return r


def noise_of(pairs):
    x = np.abs(np.array(list(pairs.values()), float))
    return dict(mean_abs=round(float(x.mean()), 5), max_abs=round(float(x.max()), 5), rms=round(float(np.sqrt((x ** 2).mean())), 5),
                n=len(x), zero=int((x == 0).sum()))


def lb(dR_ep, spoon_dR=None):
    """PLAN §2 LB map [E]: twin evals by a S_e dR (S_e >= 0.8); spoon evals [E-analogy] from the proxy class."""
    ev = {}
    for e, tw in EVAL_TWINS.items():
        ev[str(e)] = dict(dR=float(np.mean([dR_ep[int(t[2:])] for t in tw])), S=H5[str(e)]['mean'])
    out = ref_conv(ev)
    for e in out['rows']:
        out['rows'][e]['dR'] = round(ev[e]['dR'], 5); out['rows'][e]['S'] = ev[e]['S']
    if spoon_dR is not None:
        tot = sum(A_REF * H5[str(e)]['mean'] * spoon_dR for e in SPOON_EVALS)
        out['spoon_E_analogy'] = dict(dR_proxy=round(spoon_dR, 5), **{f'L_c{c}': round(c / 20 * tot, 5) for c in C_LB})
    return out


def f4(x):
    return '–' if x is None else f'{x:.4f}'


def s4(x):
    return '–' if x is None else f'{x:+.4f}'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--json'); a = ap.parse_args()
    out = {}
    # ---------------------------------------------------------------- checks
    print('## Checks [M]\n')
    print('| ep | camera vs refine: max entry, max shift cm | P_o repeat: objects bit-identical; max shift cm, rot ° | '
          'P_s native \\* | P_s via lib frames \\* | Δ | perc2 vo AUC (other scorer) | frames |')
    print('|---|---|---|---|---|---|---|---|')
    inv = []
    for e in EPS:
        c = CHK[str(e)]; cam = c['camera_vs_refine']; nat = c['Ps_native_star']['AUC']; via = R('Ps', e); inv.append(abs(nat - via))
        rp = c.get('repeat')
        rps = (f"{sum(v['identical'] for v in rp.values())}/{len(rp)}; {max(v['t_max_cm'] for v in rp.values()):.3f}, "
               f"{max(v['r_max_deg'] for v in rp.values()):.2f}") if rp else '–'
        print(f"| {e} | {cam['max_abs']:.1e}, {cam['t_max_cm']:.3f} | {rps} | {nat:.4f} | {via:.4f} | {nat - via:+.4f} "
              f"| {c['Ps_perc2_vo_auc_scan_frame']:.4f} | {SC['Po'][str(e)]['frames']} |")
    out['checks'] = dict(frame_invariance_max_abs=round(max(inv), 5),
                         camera_max_shift_cm=round(max(CHK[str(e)]['camera_vs_refine']['t_max_cm'] for e in EPS), 4),
                         repeat_objects_identical=sum(v['identical'] for e in TWINS for v in CHK[str(e)]['repeat'].values()),
                         repeat_objects=sum(len(CHK[str(e)]['repeat']) for e in TWINS))
    print(f"\nframe invariance max |native − via lib| = {out['checks']['frame_invariance_max_abs']:.4f} (rule ≤ 0.002)\n")

    # ---------------------------------------------------------------- per episode
    print('## Per episode [M]\n')
    print('| ep | objects | refine P lib / \\* | P_o lib / \\* / trk | P_o repeat \\* | P_s lib / \\* / trk | L2 = \\*(P_s) − \\*(P_o) '
          '| L3 = 1 − \\*(P_s) | L1 on P_o: lib − \\* | drift \\*(P_o) − \\*(refine) |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    rows = {}
    for e in EPS:
        r = dict(objects=objs(e), ref={k: R('ref', e, k) for k in ('lib', 'star', 'trk')}, Po={k: R('Po', e, k) for k in ('lib', 'star', 'trk', 'trk_ls')},
                 Ps={k: R('Ps', e, k) for k in ('lib', 'star', 'trk', 'trk_ls')}, Po2={k: R('Po2', e, k) for k in ('lib', 'star', 'trk')} if e in TWINS else None)
        r['L2'] = r['Ps']['star'] - r['Po']['star']; r['L3'] = 1 - r['Ps']['star']; r['L1_Po'] = r['Po']['lib'] - r['Po']['star']
        r['drift'] = r['Po']['star'] - r['ref']['star']
        r['per_obj'] = {n: dict(Po={k: R('Po', e, k, n) for k in ('lib', 'star', 'trk')}, Ps={k: R('Ps', e, k, n) for k in ('lib', 'star', 'trk')},
                                Po2=R('Po2', e, 'star', n) if e in TWINS else None, ref=R('ref', e, 'star', n)) for n in objs(e)}
        rows[e] = r
        print(f"| {e}{' †' if e in OUTLIERS else ''} | {' + '.join(SHORT[n] for n in r['objects'])} | {r['ref']['lib']:.4f} / {r['ref']['star']:.4f} "
              f"| {r['Po']['lib']:.4f} / {r['Po']['star']:.4f} / {r['Po']['trk']:.4f} | {f4(r['Po2']['star'] if r['Po2'] else None)} "
              f"| {r['Ps']['lib']:.4f} / {r['Ps']['star']:.4f} / {r['Ps']['trk']:.4f} | {r['L2']:+.4f} | {r['L3']:.4f} | {r['L1_Po']:+.4f} | {r['drift']:+.4f} |")
    m = lambda f, eps=EPS: float(np.mean([f(e) for e in eps]))  # noqa: E731
    ex = [e for e in EPS if e not in OUTLIERS]
    for lab, eps in (('mean 20', EPS), ('mean 18 (no ep0, ep23)', ex)):
        print(f"| {lab} | | {m(lambda e: R('ref', e, 'lib'), eps):.4f} / {m(lambda e: R('ref', e), eps):.4f} | {m(lambda e: R('Po', e, 'lib'), eps):.4f} / "
              f"{m(lambda e: R('Po', e), eps):.4f} / {m(lambda e: R('Po', e, 'trk'), eps):.4f} | | {m(lambda e: R('Ps', e, 'lib'), eps):.4f} / "
              f"{m(lambda e: R('Ps', e), eps):.4f} / {m(lambda e: R('Ps', e, 'trk'), eps):.4f} | {m(lambda e: rows[e]['L2'], eps):+.4f} "
              f"| {m(lambda e: rows[e]['L3'], eps):.4f} | {m(lambda e: rows[e]['L1_Po'], eps):+.4f} | {m(lambda e: rows[e]['drift'], eps):+.4f} |")
    tw = TWINS
    print(f"| mean 10 twins | | | {m(lambda e: R('Po', e, 'lib'), tw):.4f} / {m(lambda e: R('Po', e), tw):.4f} / {m(lambda e: R('Po', e, 'trk'), tw):.4f} "
          f"| {m(lambda e: R('Po2', e), tw):.4f} | {m(lambda e: R('Ps', e, 'lib'), tw):.4f} / {m(lambda e: R('Ps', e), tw):.4f} / {m(lambda e: R('Ps', e, 'trk'), tw):.4f} "
          f"| {m(lambda e: rows[e]['L2'], tw):+.4f} | {m(lambda e: rows[e]['L3'], tw):.4f} | {m(lambda e: rows[e]['L1_Po'], tw):+.4f} | {m(lambda e: rows[e]['drift'], tw):+.4f} |")
    out['episodes'] = {str(e): {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()} for e, r in rows.items()}

    # ---------------------------------------------------------------- noise and verdicts
    rep = {e: R('Po2', e) - R('Po', e) for e in TWINS}
    nz = noise_of(rep); noise = nz['mean_abs']
    rep_conv = {c: noise_of({e: R('Po2', e, c) - R('Po', e, c) for e in TWINS}) for c in ('lib', 'trk')}
    out['noise'] = dict(star=nz, **rep_conv, note='episode-level |R(P_o2) - R(P_o)| over the 10 twins; the rule uses star mean_abs')
    print(f"\n## Noise floor (P_o repeat, same box and cache) [M]\n\n\\*: mean |Δ| {nz['mean_abs']:.5f}, max {nz['max_abs']:.5f}, RMS {nz['rms']:.5f}, "
          f"{nz['zero']}/{nz['n']} episodes exactly 0; lib: mean {rep_conv['lib']['mean_abs']:.5f}, max {rep_conv['lib']['max_abs']:.5f}; "
          f"trk: mean {rep_conv['trk']['mean_abs']:.5f}, max {rep_conv['trk']['max_abs']:.5f}. Per twin \\*: "
          + ', '.join(f'ep{e} {v:+.4f}' for e, v in rep.items()) + '\n')

    V = {}
    V['L2 template, \\*: R\\*(P_s) − R\\*(P_o)'] = (rule({e: rows[e]['L2'] for e in EPS}, noise), 'tracking arms; noise rule applies', {e: rows[e]['L2'] for e in EPS})
    V['L2 template, lib: R_lib(P_s) − R_lib(P_o)'] = (rule({e: R('Ps', e, 'lib') - R('Po', e, 'lib') for e in EPS}, rep_conv['lib']['mean_abs']), 'beside: leaderboard convention', None)
    V['L2 template, trk: R_trk(P_s) − R_trk(P_o)'] = (rule({e: R('Ps', e, 'trk') - R('Po', e, 'trk') for e in EPS}, rep_conv['trk']['mean_abs']), 'beside: after a constant offset per (ep, object) [oracle]', None)
    V['L2 with the template also submitted: R\\*(P_s) − R_lib(P_o)'] = (rule({e: R('Ps', e) - R('Po', e, 'lib') for e in EPS}, rep_conv['lib']['mean_abs']), 'beside: leaderboard convention when the true-shape mesh is tracked AND submitted (= L2 \\* − L1 on P_o)', None)
    V['L3 tracker given a true template: 1 − R\\*(P_s)'] = (rule({e: rows[e]['L3'] for e in EPS}, noise), 'tracking arm', {e: rows[e]['L3'] for e in EPS})
    V['  L3 constant part: R_trk(P_s) − R\\*(P_s)'] = (rule({e: R('Ps', e, 'trk') - R('Ps', e) for e in EPS}, noise), 'oracle fit, upper bound', None)
    V['  L3 varying part: 1 − R_trk(P_s)'] = (rule({e: 1 - R('Ps', e, 'trk') for e in EPS}, noise), '', None)
    V['L2 + L3 = 1 − R\\*(P_o) (all tracking loss)'] = (rule({e: 1 - R('Po', e) for e in EPS}, noise), 'for scale', None)
    V['L1 registration loss on P_o: R\\* − R_lib'] = (rule({e: -rows[e]['L1_Po'] for e in EPS}), 'identical poses; no noise rule', {e: -rows[e]['L1_Po'] for e in EPS})
    V['L1 registration loss on P_s: R\\* − R_lib'] = (rule({e: R('Ps', e) - R('Ps', e, 'lib') for e in EPS}), 'P_s taken to lib frames by X\\*_geom', {e: R('Ps', e) - R('Ps', e, 'lib') for e in EPS})
    V['L1 registration loss on refine P: R\\* − R_lib'] = (rule({e: R('ref', e) - R('ref', e, 'lib') for e in EPS}), 'Tier A input (FRAMES.md)', None)
    V['drift: R\\*(P_o) − R\\*(refine P)'] = (rule({e: rows[e]['drift'] for e in EPS}, noise), 'code 87fc869 + library_v3 vs 25 Oct tracks', None)
    print('## Verdicts, reference-level rule (PLAN §4) [M]\n')
    print('| reading | n | mean | mean w/o ep0, ep23 | + / − | min, max | noise ×2 | verdict (20) | verdict w/o ep0, ep23 | note |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    out['verdicts'] = {}
    for k, (r, note, _) in V.items():
        n2 = '–' if r['noise'] is None else f"{2 * r['noise']:.4f}"
        print(f"| {k} | {r['n']} | {r['mean']:+.4f} | {r['mean_wo_0_23']:+.4f} | {r['positive']} / {r['negative']} | {r['min']:+.4f}, {r['max']:+.4f} "
              f"| {n2} | **{r['verdict']}** | {r['wo_0_23']} | {note} |")
        out['verdicts'][k.replace('\\', '').strip()] = r

    # ---------------------------------------------------------------- per object class
    print('\n## Per object class [M]\n')
    print('| class | reading | (ep, object) pairs | mean | mean w/o ep0, ep23 | + / − | min, max | repeat noise mean \\|Δ\\| | verdict | per pair |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    out['classes'] = {}
    for cl, names in CLASSES.items():
        nzc = noise_of({k: v for k, v in per_obj(lambda e, n: R('Po2', e, 'star', n) - R('Po', e, 'star', n), TWINS, names).items()})
        reads = {'L2 \\*': (per_obj(lambda e, n: R('Ps', e, 'star', n) - R('Po', e, 'star', n), names=names), nzc['mean_abs']),
                 'L3 = 1 − \\*(P_s)': (per_obj(lambda e, n: 1 - R('Ps', e, 'star', n), names=names), nzc['mean_abs']),
                 'L1 loss on P_o \\* − lib': (per_obj(lambda e, n: R('Po', e, 'star', n) - R('Po', e, 'lib', n), names=names), None),
                 'drift \\*(P_o) − \\*(refine)': (per_obj(lambda e, n: R('Po', e, 'star', n) - R('ref', e, 'star', n), names=names), nzc['mean_abs'])}
        out['classes'][cl] = dict(noise=nzc)
        for lab, (d, nzv) in reads.items():
            r = rule(d, nzv); out['classes'][cl][lab.replace('\\', '')] = dict(r, pairs={f'ep{e}:{n}': round(v, 4) for (e, n), v in d.items()})
            pp = ', '.join(f"{e}{' ' + SHORT[n] if len(names) > 1 else ''} {v:+.3f}" for (e, n), v in d.items())
            print(f"| {cl} | {lab} | {r['n']} | {r['mean']:+.4f} | {s4(r['mean_wo_0_23'])} | {r['positive']} / {r['negative']} | {r['min']:+.3f}, {r['max']:+.3f} "
                  f"| {'–' if nzv is None else f'{nzv:.4f}'} | **{r['verdict']}** | {pp} |")

    # ---------------------------------------------------------------- LB
    print('\n## Leaderboard terms [E] (PLAN §2 map: a = 1.025, H5 S_e, c 0.74–1.0; S_e < 0.8 not converted)\n')
    spo = lambda f: float(np.mean(list(per_obj(f, names=CLASSES['spoon proxies']).values())))  # noqa: E731
    LB = {'L2 template (\\*)': lb({e: rows[e]['L2'] for e in EPS}, spo(lambda e, n: R('Ps', e, 'star', n) - R('Po', e, 'star', n))),
          'L2 template (lib, library_v3 submitted)': lb({e: R('Ps', e, 'lib') - R('Po', e, 'lib') for e in EPS}, spo(lambda e, n: R('Ps', e, 'lib', n) - R('Po', e, 'lib', n))),
          'L2 with the template also submitted (\\*(P_s) − lib(P_o))': lb({e: R('Ps', e) - R('Po', e, 'lib') for e in EPS}, spo(lambda e, n: R('Ps', e, 'star', n) - R('Po', e, 'lib', n))),
          'L3 tracker given a true template (1 − \\*(P_s))': lb({e: rows[e]['L3'] for e in EPS}, spo(lambda e, n: 1 - R('Ps', e, 'star', n))),
          'L1 registration loss on P_o (\\* − lib)': lb({e: -rows[e]['L1_Po'] for e in EPS}),
          'all tracking loss on P_o (1 − \\*(P_o))': lb({e: 1 - R('Po', e) for e in EPS}, spo(lambda e, n: 1 - R('Po', e, 'star', n)))}
    evs = list(EVAL_TWINS)
    print('| reading | ' + ' | '.join(f'eval {e}' for e in evs) + ' | L_LB twin evals, c 0.74 / 1.0 | spoon evals [E-analogy], c 0.74 / 1.0 |')
    print('|---|' + '---|' * len(evs) + '---|---|')
    print('| S_e (H5 mean) | ' + ' | '.join(f"{H5[str(e)]['mean']:.3f}" for e in evs) + ' | | |')
    print('| twin | ' + ' | '.join('+'.join(t[2:] for t in EVAL_TWINS[e]) for e in evs) + ' | | |')
    out['lb'] = {}
    for k, o in LB.items():
        cells = []
        for e in evs:
            rr = o['rows'][str(e)]
            cells.append(f"dR {rr['dR']:+.3f} → {rr['dT']:+.3f}" if rr['counted'] else f"dR {rr['dR']:+.3f} (–)")
        sp = o.get('spoon_E_analogy')
        print(f"| {k} | " + ' | '.join(cells) + f" | {o['L_c0.74']:+.4f} / {o['L_c1.0']:+.4f} | "
              + (f"{sp['L_c0.74']:+.4f} / {sp['L_c1.0']:+.4f} (proxy dR {sp['dR_proxy']:+.4f})" if sp else '–') + ' |')
        out['lb'][k.replace('\\', '')] = o
    if a.json:
        out['inputs'] = dict(scores={k: f'scores/xstar_trk_{k}.json' for k in ('Po', 'Ps', 'Po2')}, refine='../tierA/xstar_trk.json',
                             check='scores/p1_check.json', h5='docs/analysis/h5-20261029/h5_summary.json')
        out['note'] = 'ORACLE DIAGNOSTIC (public episodes; mocap and scans). Phase-1 readings; see p1_tables.py docstring.'
        json.dump(out, open(a.json, 'w'), indent=1, default=float)
        print(f'\nwrote {a.json}')


if __name__ == '__main__':
    main()
