"""Reader of the leak decomposition's rollouts (2026-10-30; PLAN.md §2, §4, §7 B7). Public episodes only, after inference.

Plan: docs/research/work/leak-decomp-20261030/PLAN.md; tests and results: .../tierA/READER.md. It reads rollout
summaries (scores vs mocap computed on the box after inference) and writes a report; nothing here feeds inference.

Input: one record per (twin, cell, seed) = one training and its NREP official evaluations, a cell.json
  {"twin": "ep11", "cell": "c1".."c8", "seed": 42, "summary": "summary.json", "config": {...}, "cost_usd": 1.3,
   "class": optional (default PLAN §3), "arm": "P"|"O" and "episode" (oracle_twins summaries only)}
given as a file, found under a directory (every **/cell.json), or as the entries of a JSON list / JSONL index.
'summary' (relative to the record's file) is a per-episode rollout summary (glock_public ep<N>/best/summary.json,
hard_ab ep<N>/<var>/summary.json: per-draw rows) or an ops/jobs/oracle_twins.sh summary.json (arm aggregates only).
Per draw: T = row[--metric] (default auc_star, the * convention of PLAN §2; auc = lib), S = sim_vs_ref, g = T - S.
A draw without both (an evaluation error) is dropped and counted (--crash zero scores it 0 instead).
Config check (refuses arms whose config hashes differ outside the declared fields): 'config' is flattened ('a.b');
  run.*   free (run id, box, times);   seed   must equal the record's seed;
  pose.*  one hash per pose source (P_o / P_s / O);   sim.*  one per geometry (lib / scan: SF, PIECES, assets);
  hands.* one per hand timing (bundle / hT: c1-c6 byte-identical);   ref.*  free (references built from the above);
  every other key (GL_ARGS, STEPS, commit, learner, NREP, CURVE_REP, ...) one hash per twin, and STUDY_KEYS one hash
  across twins. A record whose group hash differs from the group's modal hash, or a declared stage that did not change
  (the same pose / sim / hands hash on two levels), is refused: exit 2 (--drop-refused: analysed without it).
Readings (PLAN §4): arm = mean of seed means, SE^2 = max(seed var, sigma_s,class^2)/s + sigma_d^2/(s k), df s-1
(seed var = between-seed part: var of seed means minus the draw part); per-twin contrasts Welch-Satterthwaite; pooled
= equal-weight mean over twins, paired t (df E-1) and exact sign-flip permutation, Holm over the primary tests (phi_T,
phi_K, phi_G, + L6 AOI if c7 ran); verdicts leaks / no leak / truth worse / inconclusive; dT = dS + dg; Shapley,
AOI and LOO over {template T, motion K, geometry G} from c1-c6 (v(T,K,.) = v(K,.)); copy ceiling; LB with the twin
map and c in [0.74, 1.0]; explained total vs 0.185.
  read INPUT... [--metric M] [--crash drop|zero] [--class-noise F] [--drop-refused] [--no-config-check] [--out F]
  mc [--reps N] [--draws K] [--noise DIR] [--rng N] [--out F]   Monte Carlo of the plan's design (10 twins, 2-3 seeds,
                    k draws, classes as PLAN §3) through the same estimators: recovery, type I, power at d 0.03/0.05/0.10
  refrule F.json    reference-level rule (Tier A): {"dR": {ep: x}, "noise": x (P_o-repeat, tracking arms only)}
  refconv F.json    reference-level dR -> LB: {"evals": {eval: {"dR": x, "S": x, "spoon": bool}}}
"""
import argparse, glob, hashlib, itertools, json, math, os, sys
from collections import Counter

import numpy as np
from scipy import stats

CELLS = {'c1': ('P_o', 'lib', 'bundle'), 'c2': ('P_s', 'lib', 'bundle'), 'c3': ('O', 'lib', 'bundle'),
         'c4': ('P_o', 'scan', 'bundle'), 'c5': ('P_s', 'scan', 'bundle'), 'c6': ('O', 'scan', 'bundle'),
         'c7': ('P_o', 'lib', 'hT'), 'c8': ('O', 'scan', 'hT')}                 # PLAN §3 Phase 2
FACTOR = {'pose': 0, 'sim': 1, 'hands': 2}                                     # config groups that follow a cell factor
TWINS = {'ep11': 'stable', 'ep39': 'stable', 'ep12': 'typical', 'ep21': 'typical', 'ep27': 'typical',
         'ep2': 'hard', 'ep13': 'hard', 'ep18': 'hard', 'ep24': 'hard', 'ep31': 'hard'}
SEEDS = {'stable': (42, 43), 'typical': (42, 43), 'hard': (42, 43, 44)}
# (sigma_s, sigma_d) of T vs mocap per class: scratchpad/noise/power.py (from seed_groups.json, pub_policies.json) [M/E]
FLOOR = {'stable': (0.010, 0.008), 'typical': (0.030, 0.035), 'hard': (0.10, 0.15)}
FLOOR_G = (0.010, 0.017)                                                       # g = T - S: seed sd, draw sd [M, PLAN §2]
EVAL_TWINS = {1: ('ep2',), 8: ('ep27', 'ep39'), 10: ('ep11',), 14: ('ep12', 'ep13'), 19: ('ep18',), 20: ('ep21',),
              25: ('ep24',), 28: ('ep27',), 30: ('ep31',), 38: ('ep39',)}      # PLAN §2, fixed before any reading
C_LB, A_REF, S_MIN, GAP, ALPHA = (0.74, 1.0), 1.025, 0.8, 0.185, 0.05
STUDY_KEYS = ('commit', 'learner', 'STEPS', 'CURVE_REP', 'NREP')
# name: (weights over cells, what (PLAN §2), primary (Holm family), g rule: L2/L3 also need dg >= 0.02, CI excluding 0)
CONTRASTS = {
    'phi_T': (dict(c2=1 / 3, c1=-1 / 3, c5=1 / 6, c4=-1 / 6), 'L2 template, Shapley', True, True),
    'phi_K': (dict(c3=1 / 2, c1=-1 / 3, c2=-1 / 6, c6=1 / 2, c4=-1 / 6, c5=-1 / 3), 'L3 motion, Shapley', True, True),
    'phi_G': (dict(c4=1 / 3, c1=-1 / 3, c5=1 / 6, c2=-1 / 6, c6=1 / 2, c3=-1 / 2), 'L5 sim geometry, Shapley', True, False),
    'L6_AOI': (dict(c7=1, c1=-1), 'L6 hand timing, AOI c7-c1', True, False),
    'L2_AOI': (dict(c2=1, c1=-1), 'L2 template, AOI c2-c1', False, True),
    'L2_scan': (dict(c5=1, c4=-1), 'L2 template at scan geometry, c5-c4', False, True),
    'L3_AOI': (dict(c3=1, c2=-1), 'L3 tracker given a true template, c3-c2', False, True),
    'L3_LOO': (dict(c6=1, c5=-1), 'L3 tracker, LOO c6-c5', False, True),
    'K_AOI': (dict(c3=1, c1=-1), 'true motion alone, AOI of K c3-c1', False, True),
    'L5_AOI': (dict(c4=1, c1=-1), 'L5 sim geometry, AOI c4-c1', False, False),
    'L5_LOO': (dict(c6=1, c3=-1), 'L5 sim geometry, LOO c6-c3', False, False),
    'L6_LOO': (dict(c8=1, c6=-1), 'L6 hand timing, LOO c8-c6', False, False),
    'total': (dict(c6=1, c1=-1), 'everything true, c6-c1 (= phi_T + phi_K + phi_G)', False, False)}
PLAYERS = {'T': ('L2_AOI', None, 'phi_T'), 'K': ('K_AOI', 'L3_LOO', 'phi_K'), 'G': ('L5_AOI', 'L5_LOO', 'phi_G')}
VERDICTS = ('leaks', 'no leak', 'truth worse', 'inconclusive')


# ---------------------------------------------------------------- estimators (vectorised: leading axes = replicates)
def arm(m, v, k, floor):
    """One arm (twin, cell) by the plan's SE rule. m, v, k: seed means, within-seed draw variances (ddof 1, NaN if
    unknown) and draw counts, shape (..., s); floor = (sigma_s, sigma_d) of the class.
    Returns mean, se, df (s-1; inf for one seed: the variance is then the class floor), sigma_s seen, sigma_d used."""
    m, v, k = np.broadcast_arrays(np.asarray(m, float), np.asarray(v, float), np.asarray(k, float))
    s = m.shape[-1]
    w = np.where(np.isfinite(v) & (k > 1), k - 1, 0)
    sd2 = np.where(w.sum(-1) > 0, (np.where(w > 0, v, 0) * w).sum(-1) / np.maximum(w.sum(-1), 1), floor[1] ** 2)
    ik = (1 / k).sum(-1)
    seed = np.maximum(m.var(-1, ddof=1) - sd2 * ik / s, 0) if s > 1 else np.full(m.shape[:-1], np.nan)
    se2 = np.fmax(seed, floor[0] ** 2) / s + sd2 * ik / s ** 2
    return m.mean(-1), np.sqrt(se2), (s - 1.0 if s > 1 else np.inf), np.sqrt(seed), np.sqrt(sd2)


def combine(parts):
    """Linear contrast of independent arms [(w, mean, se, df)] -> d, se, df (Welch-Satterthwaite; 2(s-1) for two arms)."""
    d = sum(w * m for w, m, _, _ in parts)
    v = sum((w * s) ** 2 for w, _, s, _ in parts)
    q = sum(0 if np.isinf(f) else (w * s) ** 4 / f for w, _, s, f in parts)
    with np.errstate(divide='ignore', invalid='ignore'):
        df = np.where(np.asarray(q) > 0, np.asarray(v) ** 2 / np.where(np.asarray(q) > 0, q, 1), np.inf)
    return d, np.sqrt(v), df


_SIGNS = {}


def signs(E):  # every sign pattern over E twins (exact test), or 65536 random ones beyond 16 twins
    if E not in _SIGNS:
        _SIGNS[E] = np.array(list(itertools.product((1.0, -1.0), repeat=E))) if E <= 16 else \
            np.random.default_rng(0).choice((1.0, -1.0), (1 << 16, E))
    return _SIGNS[E]


def pooled(d):
    """Equal-weight mean over twins (last axis): paired t (df E-1) and sign-flip permutation, one-sided both ways,
    90 % and 95 % two-sided CIs from t."""
    d = np.asarray(d, float); E = d.shape[-1]; mu = d.mean(-1)
    if E < 2:
        nan = np.full(mu.shape, np.nan)
        return dict(E=E, d=mu, sd=nan, se=nan, df=0, p_up=nan, p_dn=nan, q_up=nan, q_dn=nan, ci90=(nan, nan), ci95=(nan, nan))
    sd = d.std(-1, ddof=1); se = sd / math.sqrt(E); df = E - 1
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(se > 0, mu / np.where(se > 0, se, 1), np.where(mu > 0, np.inf, np.where(mu < 0, -np.inf, 0.0)))
    f = d @ signs(E).T / E
    q_up = (f >= mu[..., None] - 1e-12).mean(-1); q_dn = (f <= mu[..., None] + 1e-12).mean(-1)
    t90, t95 = stats.t.ppf(0.95, df), stats.t.ppf(0.975, df)
    return dict(E=E, d=mu, sd=sd, se=se, df=df, p_up=stats.t.sf(t, df), p_dn=stats.t.cdf(t, df), q_up=q_up, q_dn=q_dn,
                ci90=(mu - t90 * se, mu + t90 * se), ci95=(mu - t95 * se, mu + t95 * se))


def holm(p):
    """Holm-adjusted p values over the last axis (step-down, monotone)."""
    p = np.asarray(p, float); m = p.shape[-1]
    o = np.argsort(p, -1); ps = np.take_along_axis(p, o, -1)
    a = np.minimum(np.maximum.accumulate(ps * (m - np.arange(m)), -1), 1.0)
    out = np.empty_like(a); np.put_along_axis(out, o, a, -1)
    return out


def verdict(d, ci90, up_ok, dn_ok, g_ok=True):
    """PLAN §4 rollout rule. Leaks: d >= +0.03 and the (Holm-adjusted) one-sided test and permutation agree (and, for
    L2/L3, the g rule); truth worse: d <= -0.03, mirrored; no leak: |d| <= 0.02 and the 90 % CI within +-0.04."""
    d = np.asarray(d, float)
    leak = (d >= 0.03) & up_ok & g_ok
    worse = (d <= -0.03) & dn_ok
    none = (np.abs(d) <= 0.02) & (ci90[0] >= -0.04) & (ci90[1] <= 0.04)
    return np.select([leak, worse, none], ['leaks', 'truth worse', 'no leak'], 'inconclusive')


def g_rule(pg):  # L2/L3: dg >= 0.02 with its 95 % CI excluding 0
    return (pg['d'] >= 0.02) & (pg['ci95'][0] > 0)


def ref_rule(dR, noise=None):
    """PLAN §4 reference-level rule (CPU, deterministic): leaks = mean dR >= 0.01 and >= 12/20 episodes of that sign
    (scaled to n) and, for tracking arms, |mean| > 2x the P_o-repeat noise; no leak = |mean| < 0.005."""
    x = np.array(list(dR.values()), float); mu = float(x.mean()); need = math.ceil(0.6 * len(x))
    big = noise is None or abs(mu) > 2 * noise
    v = 'leaks' if mu >= 0.01 and (x > 0).sum() >= need and big else \
        'truth worse' if mu <= -0.01 and (x < 0).sum() >= need and big else 'no leak' if abs(mu) < 0.005 else 'inconclusive'
    return dict(n=len(x), mean=round(mu, 5), positive=int((x > 0).sum()), negative=int((x < 0).sum()), need=need,
                noise=noise, verdict=v)


def lb(dt, st):
    """PLAN §2 LB conversion of per-twin deltas dt (with SEs st): L = (c/20) sum_e d(twin(e)) over the evals whose
    twins all ran, at c = 0.74 and 1.0, with a normal 90 % band; evals without a twin add nothing ([M] total only)."""
    mult, used, missing = Counter(), [], []
    for e, tw in EVAL_TWINS.items():
        if all(t in dt for t in tw):
            used.append(e); mult.update({t: 1 / len(tw) for t in tw})
        else:
            missing.append(e)
    s = sum(mult[t] * dt[t] for t in mult); v = sum((mult[t] * st[t]) ** 2 for t in mult)
    out = dict(evals=used, missing_evals=missing)
    for c in C_LB:
        L, se = c / 20 * s, c / 20 * math.sqrt(v)
        out[f'c{c}'] = dict(L=round(L, 5), lo90=round(L - 1.645 * se, 5), hi90=round(L + 1.645 * se, 5))
    lo, hi = out[f'c{C_LB[0]}'], out[f'c{C_LB[1]}']
    out['action'] = 'top priority (>= 0.010 at c 0.74)' if lo['L'] >= 0.010 else 'worth eval work (>= 0.005 at c 0.74)' \
        if lo['L'] >= 0.005 else 'drop the stage (< 0.002, upper < 0.004 at c 1.0)' if hi['L'] < 0.002 and hi['hi90'] < 0.004 \
        else 'below action, not dropped'
    return out


def ref_conv(evals):
    """PLAN §2: reference-level dR on non-rollout evals -> LB by (c/20) a S_e dR_e, only S_e >= 0.8; spoon evals are
    [E-analogy] rows, never in the [M] total."""
    rows, tot = {}, 0.0
    for e, x in evals.items():
        ok = x.get('S', 0) >= S_MIN and not x.get('spoon')
        r = A_REF * x.get('S', 0) * x['dR']
        rows[e] = dict(dT=round(r, 5), counted=ok, label='[E-analogy] spoon' if x.get('spoon') else
                       '[M]' if ok else f'S < {S_MIN}: not converted')
        tot += r if ok else 0
    return dict(rows=rows, **{f'L_c{c}': round(c / 20 * tot, 5) for c in C_LB})


# ---------------------------------------------------------------- records
def flat(d, pre=''):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flat(v, f'{pre}{k}.'))
        else:
            out[f'{pre}{k}'] = v
    return out


def jhash(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:12]


def entries(inputs):
    out = []
    for x in inputs:
        if os.path.isdir(x):
            out += [(json.load(open(f)), os.path.dirname(f)) for f in sorted(glob.glob(f'{x}/**/cell.json', recursive=True))]
        elif x.endswith('.jsonl'):
            out += [(json.loads(line), os.path.dirname(x)) for line in open(x) if line.strip()]
        else:
            j = json.load(open(x))
            out += [(e, os.path.dirname(x)) for e in (j if isinstance(j, list) else j.get('records', [j]))]
    return out


def load(e, base, metric, crash):
    """One record: per-draw T, S, g (or arm aggregates from an oracle_twins summary)."""
    twin = e['twin'] if str(e['twin']).startswith('ep') else f"ep{e['twin']}"
    f = e['summary'] if os.path.isabs(e['summary']) else os.path.join(base, e['summary'])
    s = json.load(open(f)); cfg = e.get('config')
    if cfg is None and e.get('config_file'):
        cfg = json.load(open(os.path.join(base, e['config_file'])))
    r = dict(twin=twin, cell=e['cell'], seed=int(e['seed']), cls=e.get('class') or TWINS.get(twin, 'hard'),
             config=None if cfg is None else flat(cfg), cost=e.get('cost_usd'), file=f, crashes=0)
    if r['cell'] not in CELLS:
        sys.exit(f'{f}: unknown cell {r["cell"]}')
    if 'rollouts' in s:
        T, S = [], []
        for x in s['rollouts']:
            if isinstance(x.get(metric), (int, float)) and isinstance(x.get('sim_vs_ref'), (int, float)):
                T.append(x[metric]); S.append(x['sim_vs_ref'])
            else:
                r['crashes'] += 1
                if crash == 'zero':
                    T.append(0.0); S.append(0.0)
        T, S = np.array(T, float), np.array(S, float); G = T - S
        if not len(T):
            sys.exit(f'{f}: no draw has {metric} and sim_vs_ref')
        k = len(T); var = lambda x: float(x.var(ddof=1)) if k > 1 else float('nan')
        r.update(k=k, T=float(T.mean()), S=float(S.mean()), g=float(G.mean()), vT=var(T), vS=var(S), vg=var(G),
                 draws=T.tolist(), fail70=int((T < 0.70).sum()), fail_med=int((T < np.median(T) - 0.10).sum()),
                 lib=float(np.mean([x['auc'] for x in s['rollouts'] if isinstance(x.get('auc'), (int, float))]))
                 if metric != 'auc' and any('auc' in x for x in s['rollouts']) else None,
                 trk=float(np.mean([x['auc_trk'] for x in s['rollouts'] if 'auc_trk' in x]))
                 if any('auc_trk' in x for x in s['rollouts']) else None)
    elif 'episodes' in s:                                       # ops/jobs/oracle_twins.sh: one seed, aggregates only
        a = s['episodes'][e.get('episode', twin)][e['arm']]
        t, sv, n = a[metric], a['sim_vs_ref'], a['n']
        sdT = t.get('sd', t.get('std', 0) * math.sqrt(n / max(n - 1, 1)) if 'std' in t else float('nan'))
        r.update(k=n, T=t['mean'], S=sv['mean'], g=t['mean'] - sv['mean'], vT=sdT ** 2,
                 vS=(sv['std'] ** 2 * n / max(n - 1, 1)) if n > 1 else float('nan'), vg=float('nan'), draws=None,
                 fail70=t.get('below_0_70'), fail_med=None, lib=None, trk=None)
    else:
        sys.exit(f'{f}: neither a rollout summary nor an oracle_twins summary')
    return r


LEVELS = {'pose': ('P_o', 'P_s', 'O'), 'sim': ('lib', 'scan'), 'hands': ('bundle', 'hT')}


def check_configs(R):
    """Refuse records whose config hashes differ outside the declared fields (module doc). -> [(record, why)]"""
    bad = []
    part = lambda g: (lambda r: {k: v for k, v in r['config'].items() if k.split('.')[0] == g})
    fixed = lambda r: {k: v for k, v in r['config'].items() if k.split('.')[0] not in ('run', 'seed', 'ref', *FACTOR)}
    study = lambda r: {k: r['config'].get(k) for k in STUDY_KEYS}
    content = lambda d: {k: v for k, v in d.items() if any(t in k.lower() for t in ('md5', 'sha', 'hash'))} or d

    def modal(rs, sub, what):  # the group's majority hash; every other record is refused (all of them on a tie)
        c = Counter(jhash(sub(r)) for r in rs).most_common()
        if len(c) > 1:
            top = c[0][0] if c[0][1] > c[1][1] else None
            ref = next((x for x in rs if jhash(sub(x)) == top), None)
            for r in rs:
                if top is None:
                    bad.append((r, f'{what}: no majority among {len(rs)} arms ({len(c)} different hashes)'))
                elif jhash(sub(r)) != top:
                    x, y = sub(r), sub(ref)
                    keys = sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))
                    bad.append((r, f'{what} differs from the modal arm ({ref["cell"]} s{ref["seed"]}) in {keys[:6]}'))
        return c[0][0] if c else None

    ok = []
    for r in R:
        c = r['config']
        if c is None:
            bad.append((r, 'no config (the arm cannot be checked)'))
        elif 'seed' in c and int(c['seed']) != r['seed']:
            bad.append((r, f"config seed {c['seed']} != record seed {r['seed']}"))
        elif any(not part(g)(r) for g in FACTOR):
            bad.append((r, 'no ' + ' / '.join(f'{g}.*' for g in FACTOR if not part(g)(r)) + ' fields: the declared stages cannot be checked'))
        else:
            ok.append(r)
    modal(ok, study, 'a study key (' + ', '.join(STUDY_KEYS) + ')')
    for tw in sorted({r['twin'] for r in ok}):
        rt = [r for r in ok if r['twin'] == tw]
        modal(rt, fixed, f'{tw}: a fixed field')
        for g, i in FACTOR.items():
            lv = {}
            for lev in LEVELS[g]:
                rl = [r for r in rt if CELLS[r['cell']][i] == lev]
                if rl:
                    modal(rl, part(g), f'{tw}: {g}.* at {lev}')
                    lv[lev] = Counter(jhash(content(part(g)(r))) for r in rl).most_common(1)[0][0]
            for (l1, h1), (l2, h2) in itertools.combinations(lv.items(), 2):
                if h1 == h2:                                    # the files are the same: no swap happened
                    bad += [(r, f'{tw}: the declared stage did not change ({g}.* content identical at {l1} and {l2})')
                            for r in rt if CELLS[r['cell']][i] == l2]
    seen, out = set(), []
    for r, w in bad:
        if (id(r), w) not in seen:
            seen.add((id(r), w)); out.append((r, w))
    return out


# ---------------------------------------------------------------- read
def cell_stats(R, floors):
    """(twin, cell) -> arm stats of T, S, g, plus the record bookkeeping."""
    out = {}
    for key in sorted({(r['twin'], r['cell']) for r in R}):
        rs = sorted((r for r in R if (r['twin'], r['cell']) == key), key=lambda r: r['seed'])
        fl = floors[rs[0]['cls']]; k = [r['k'] for r in rs]
        a = {}
        for q, f in (('T', fl), ('S', fl), ('g', FLOOR_G)):
            mean, se, df, ss, sd = arm([r[q] for r in rs], [r['v' + q] for r in rs], k, f)
            a[q] = dict(mean=float(mean), se=float(se), df=float(df), sigma_s_seen=None if np.isnan(ss) else float(ss),
                        sigma_d=float(sd))
        sm = [r['T'] for r in rs]
        a.update(cls=rs[0]['cls'], seeds=[r['seed'] for r in rs], seed_means=[round(x, 4) for x in sm], k=k,
                 crashes=sum(r['crashes'] for r in rs), fail70=sum(r['fail70'] or 0 for r in rs),
                 fail_med=sum(r['fail_med'] or 0 for r in rs) if all(r['fail_med'] is not None for r in rs) else None,
                 weak_seeds=[r['seed'] for r in rs if len(rs) > 1 and r['T'] <= max(sm) - 0.10],
                 min_draw=min(min(r['draws']) for r in rs) if all(r['draws'] for r in rs) else None,
                 L1_lib_minus_star=round(float(np.mean([r['lib'] - r['T'] for r in rs])), 4) if all(r['lib'] is not None for r in rs) else None,
                 trk_minus_star=round(float(np.mean([r['trk'] - r['T'] for r in rs])), 4) if all(r['trk'] is not None for r in rs) else None,
                 cost_usd=round(sum(r['cost'] or 0 for r in rs), 2) if any(r['cost'] for r in rs) else None)
        out[key] = a
    return out


def per_twin(cs, w):
    """Per-twin contrast of T, S, g for the twins that have every cell the contrast needs."""
    out = {}
    for tw in sorted({t for t, _ in cs}, key=lambda t: int(t[2:])):
        if all((tw, c) in cs for c in w):
            out[tw] = {q: combine([(x, cs[tw, c][q]['mean'], cs[tw, c][q]['se'], cs[tw, c][q]['df']) for c, x in w.items()])
                       for q in 'TSg'}
    return out


def rnd(x, n=5):
    if isinstance(x, (tuple, list)):
        return [rnd(v, n) for v in x]
    x = float(x)
    return None if math.isnan(x) else x if math.isinf(x) else round(x, n)


def read(a):
    floors = dict(FLOOR, **(json.load(open(a.class_noise)) if a.class_noise else {}))
    R = [load(e, b, a.metric, a.crash) for e, b in entries(a.inputs)]
    refused = [] if a.no_config_check else check_configs(R)
    if refused:
        msg = '\n  '.join(f"{r['twin']} {r['cell']} s{r['seed']} ({r['file']}): {w}" for r, w in refused)
        print(f'leak_read: REFUSED {len({id(r) for r, _ in refused})} arm(s), config differs outside the declared fields:'
              f'\n  {msg}', file=sys.stderr)
        if not a.drop_refused:
            sys.exit(2)
        drop = {id(r) for r, _ in refused}; R = [r for r in R if id(r) not in drop]
    cs = cell_stats(R, floors)
    have = {c for _, c in cs}
    rep = dict(metric=a.metric, crash=a.crash, config_check='skipped' if a.no_config_check else 'passed' if not refused
               else 'refused arms dropped', refused=[dict(twin=r['twin'], cell=r['cell'], seed=r['seed'], why=w) for r, w in refused],
               records=len(R), floors=floors, contrasts={}, players={}, cells={f'{t} {c}': v for (t, c), v in cs.items()})
    prim = [n for n, (w, _, p, _) in CONTRASTS.items() if p and set(w) <= have]
    pt, pp = {}, {}
    for n, (w, what, p, gr) in CONTRASTS.items():
        if not set(w) <= have:
            continue
        tw = per_twin(cs, w)
        if not tw:
            continue
        pt[n] = tw; pp[n] = {q: pooled(np.array([tw[t][q][0] for t in tw])) for q in 'TSg'}
    hp = {k: dict(zip([n for n in prim if n in pp], holm(np.array([pp[n]['T'][k] for n in prim if n in pp]))))
          for k in ('p_up', 'p_dn', 'q_up', 'q_dn')} if any(n in pp for n in prim) else {}
    for n, tw in pt.items():
        w, what, p, gr = CONTRASTS[n]; P = pp[n]; T = P['T']; isp = n in hp.get('p_up', {})
        adj = {k: (hp[k][n] if isp else T[k]) for k in ('p_up', 'p_dn', 'q_up', 'q_dn')}
        g_ok = bool(g_rule(P['g'])) if gr else True
        up = adj['p_up'] <= ALPHA and adj['q_up'] <= ALPHA; dn = adj['p_dn'] <= ALPHA and adj['q_dn'] <= ALPHA
        v = str(verdict(T['d'], T['ci90'], up, dn, g_ok)) if T['E'] > 1 else 'inconclusive'
        note = 'dT passes, dg does not (L2/L3 g rule)' if v == 'inconclusive' and gr and not g_ok and \
            str(verdict(T['d'], T['ci90'], up, dn, True)) == 'leaks' else ''
        ext = v == 'inconclusive' and abs(float(T['d'])) >= 0.03
        cells = [f'{t} {c}' for t in tw for c in w]
        twins = {}
        for t, x in tw.items():
            d, se, df = x['T']; D = stats.t(df) if np.isfinite(df) else stats.norm; tq = D.ppf(0.95)
            pu, pd = (D.sf(d / se), D.cdf(d / se)) if se > 0 else (float(d <= 0), float(d >= 0))
            twins[t] = dict(dT=rnd(d), dS=rnd(x['S'][0]), dg=rnd(x['g'][0]), se=rnd(se), df=rnd(df, 2),
                            lb95=rnd(d - tq * se), ub95=rnd(d + tq * se), verdict_per_twin=str(verdict(
                                d, (d - tq * se, d + tq * se), pu <= ALPHA, pd <= ALPHA,
                                (x['g'][0] >= 0.02) and (x['g'][0] - 1.96 * x['g'][1] > 0) if gr else True)))
        rep['contrasts'][n] = dict(
            what=what, weights=w, family='primary (Holm)' if isp else 'secondary (unadjusted)', twins_used=list(tw),
            twins_missing=[t for t in sorted({t for t, _ in cs}, key=lambda t: int(t[2:])) if t not in tw],
            dT=rnd(T['d']), dS=rnd(P['S']['d']), dg=rnd(P['g']['d']), additivity=rnd(T['d'] - P['S']['d'] - P['g']['d'], 12),
            sd_twins=rnd(T['sd']), min_twin=rnd(min(x['T'][0] for x in tw.values())), se_paired=rnd(T['se']), df=T['df'],
            ci90=rnd(T['ci90']), ci95=rnd(T['ci95']), dg_ci95=rnd(P['g']['ci95']),
            se_rule_pooled=rnd(math.sqrt(sum(x['T'][1] ** 2 for x in tw.values())) / len(tw)),
            p_t_up=rnd(T['p_up']), p_perm_up=rnd(T['q_up']), p_t_dn=rnd(T['p_dn']), p_perm_dn=rnd(T['q_dn']),
            p_adj=dict((k, rnd(v)) for k, v in adj.items()), verdict=v, note=note,
            extension='seeds 45-46 on the hard twins for these cells (pre-set, |d| >= 0.03)' if ext else '',
            failure_draws=dict(below_0_70=sum(cs[tuple(c.split())]['fail70'] for c in cells),
                               below_median_minus_0_10=sum(cs[tuple(c.split())]['fail_med'] or 0 for c in cells),
                               crashes=sum(cs[tuple(c.split())]['crashes'] for c in cells)),
            weak_seeds=[f"{c} s{s}" for c in cells for s in cs[tuple(c.split())]['weak_seeds']],
            cost_usd=rnd(sum(cs[tuple(c.split())]['cost_usd'] or 0 for c in cells), 2),
            LB=lb({t: x['T'][0] for t, x in tw.items()}, {t: x['T'][1] for t, x in tw.items()}), twins=twins)
    for pl, (aoi, loo, phi) in PLAYERS.items():
        g = lambda n: rep['contrasts'].get(n, {}).get('dT')
        rep['players'][pl] = dict(AOI=g(aoi), LOO=0.0 if loo is None and phi in pt else g(loo), shapley=g(phi),
                                  interaction=None if g(aoi) is None or (loo and g(loo) is None) else
                                  round((g(loo) if loo else 0.0) - g(aoi), 5))
    if 'c6' in have:                                            # copy ceiling (L7) per twin and its LB loss
        ceil = {}
        for (t, c), x in cs.items():
            if c == 'c6':
                low = sum(m <= 0.75 for m in x['seed_means'])
                ceil[t] = dict(T_c6=round(x['T']['mean'], 4), seed_means=x['seed_means'], L7=round(1 - x['T']['mean'], 4),
                               call='copyable (>= 0.90)' if x['T']['mean'] >= 0.90 else
                               'robot/learner limit (<= 0.75 on >= 2 seeds)' if low >= 2 else 'between')
        rep['copy_ceiling'] = ceil
        loss = lb({t: x['L7'] for t, x in ceil.items()}, {t: cs[t, 'c6']['T']['se'] for t in ceil})
        phis = [rep['contrasts'][n]['LB'] for n in ('phi_T', 'phi_K', 'phi_G') if n in rep['contrasts']]
        if len(phis) == 3:
            rep['explained_total'] = {f'c{c}': dict(sum_phi=round(sum(p[f'c{c}']['L'] for p in phis), 5),
                                                    ceiling=loss[f'c{c}']['L'],
                                                    total=round(sum(p[f'c{c}']['L'] for p in phis) + loss[f'c{c}']['L'], 5),
                                                    gap_vs_0_185=round(GAP - sum(p[f'c{c}']['L'] for p in phis) - loss[f'c{c}']['L'], 5))
                                      for c in C_LB}
            rep['explained_total']['note'] = ('only the evals with a twin (' + ', '.join(map(str, loss['evals'])) +
                                              ') enter; a gap > 0.03 means the twin map or the spoon proxy is wrong '
                                              '(reported, not forced closed)')
    return rep


def show(rep):
    f4 = lambda x, n=4: 'n/a' if x is None else f'{x:.{n}f}'
    print(f"leak_read: {rep['records']} records, metric {rep['metric']}, crashes {rep['crash']}, config {rep['config_check']}")
    print(f"{'contrast':<8} {'fam':<4} {'E':>2} {'dT':>8} {'dS':>8} {'dg':>8} {'90% CI':>17} {'p_t':>7} {'p_perm':>7} "
          f"{'verdict':<13} {'LB c.74':>8} {'LB c1':>8}  action")
    for n, c in rep['contrasts'].items():
        print(f"{n:<8} {'P' if c['family'].startswith('primary') else 's':<4} {len(c['twins_used']):>2} {f4(c['dT']):>8} "
              f"{f4(c['dS']):>8} {f4(c['dg']):>8} {str(c['ci90']):>17.17} {f4(c['p_adj']['p_up']):>7} {f4(c['p_adj']['q_up']):>7} "
              f"{c['verdict']:<13} {f4(c['LB']['c0.74']['L'], 5):>8} {f4(c['LB']['c1.0']['L'], 5):>8}  {c['LB']['action']}"
              + (f"  [{c['note']}]" if c['note'] else '') + (f"  [{c['extension']}]" if c['extension'] else ''))
    for p, x in rep['players'].items():
        print(f'player {p}: AOI {x["AOI"]}  LOO {x["LOO"]}  Shapley {x["shapley"]}  interaction (LOO - AOI) {x["interaction"]}')
    for t, x in rep.get('copy_ceiling', {}).items():
        print(f"copy ceiling {t}: T*(c6) {x['T_c6']} seeds {x['seed_means']} -> {x['call']}")
    if 'explained_total' in rep:
        print('explained total:', {k: v for k, v in rep['explained_total'].items() if k != 'note'})


# ---------------------------------------------------------------- Monte Carlo of the plan's design (test g)
GEN = {'stable': dict(base=0.97, s0=0.010, q=0.0, g=0.008, p=0.0),           # scratchpad/noise/sim.py's generator
       'typical': dict(base=0.90, s0=0.030, q=0.0, g=0.025, p=0.03),
       'hard': dict(base=0.85, s0=0.030, q=0.25, g=0.020, p=0.13)}
DROPS_SIM = (0.104, 0.759, 0.218, 0.102, 0.135, 0.304, 0.655, 0.545, 0.196, 0.300, 0.341)


def drops(noise):
    """Failure drops (median - draw for draws > 0.10 below their checkpoint's median) of the H5 official draws
    (noise/h5_draws.json) if present, else sim.py's constants."""
    f = os.path.join(noise or '', 'h5_draws.json')
    if noise and os.path.exists(f):
        d = [float(np.median(v) - x) for v in json.load(open(f))['h5'].values() for x in v if x < np.median(v) - 0.10]
        return np.array(d), f
    return np.array(DROPS_SIM), 'scratchpad/noise/sim.py constants'


def simulate(rng, cls, mu, gmu, s, k, R, dr):
    """Draws of one arm, R replicates: T (R, s, k) with sim.py's heavy-tailed classes, and g = T - S."""
    a = GEN[cls]
    seed = rng.normal(0, a['s0'], (R, s, 1)) - (rng.random((R, s, 1)) < a['q']) * rng.uniform(0.08, 0.32, (R, s, 1))
    x = mu + seed + rng.normal(0, a['g'], (R, s, k))
    fail = rng.random((R, s, k)) < a['p']
    x = x - fail * (rng.uniform(0.10, 0.25, (R, s, k)) if cls == 'typical' else dr[rng.integers(0, len(dr), (R, s, k))])
    g = gmu + rng.normal(0, FLOOR_G[0], (R, s, 1)) + rng.normal(0, FLOOR_G[1], (R, s, k))
    return np.clip(x, 0, 1), g


def truth(a, b, gam, base):
    """Cell means for template effect a, motion effect b, geometry effect gam (all-true cell c6 = base), and the
    reference-side part of g (a and b move the reference, gam the simulator)."""
    T = dict(c1=base - a - b - gam, c2=base - b - gam, c3=base - gam, c4=base - a - b, c5=base - b, c6=base)
    G = dict(c1=-a - b, c2=-b, c3=0.0, c4=-a - b, c5=-b, c6=0.0)
    return T, G


def mc(a):
    rng = np.random.default_rng(a.rng); dr, src = drops(a.noise); R, k = a.reps, a.draws
    names = ['phi_T', 'phi_K', 'phi_G', 'L2_AOI', 'L3_AOI', 'K_AOI', 'L5_AOI', 'L5_LOO', 'total']
    prim = ['phi_T', 'phi_K', 'phi_G']

    def run(a_, b_, g_):
        dd = {n: [] for n in names}; gg = {n: [] for n in names}; true = {}
        pr = {n: {c: [] for c in FLOOR} for n in names}               # per-twin one-sided call by the SE rule, by class
        for tw, cls in TWINS.items():
            Tm, Gm = truth(a_, b_, g_, GEN[cls]['base']); s = len(SEEDS[cls]); st = {}
            for c in Tm:
                x, g = simulate(rng, cls, Tm[c], Gm[c], s, k, R, dr)
                st[c] = {q: arm(y.mean(-1), y.var(-1, ddof=1), np.full(s, k), f)[:3]
                         for q, y, f in (('T', x, FLOOR[cls]), ('g', g, FLOOR_G))}
            for n in names:
                w = CONTRASTS[n][0]
                d, se, df = combine([(x, *st[c]['T']) for c, x in w.items()])
                dd[n].append(d); pr[n][cls].append(d - stats.t.ppf(1 - ALPHA, df) * se > 0)
                gg[n].append(combine([(x, *st[c]['g']) for c, x in w.items()])[0])
                true[n] = sum(x * Tm[c] for c, x in w.items())       # same on every twin (clipping aside)
        P = {n: pooled(np.stack(dd[n], -1)) for n in names}; Pg = {n: pooled(np.stack(gg[n], -1)) for n in names}
        H = {kk: holm(np.stack([P[n][kk] for n in prim], -1)) for kk in ('p_up', 'p_dn', 'q_up', 'q_dn')}
        out = {}
        for n in names:
            i = prim.index(n) if n in prim else None
            adj = {kk: H[kk][:, i] if i is not None else P[n][kk] for kk in H}
            up = (adj['p_up'] <= ALPHA) & (adj['q_up'] <= ALPHA); dn = (adj['p_dn'] <= ALPHA) & (adj['q_dn'] <= ALPHA)
            gok = g_rule(Pg[n]) if CONTRASTS[n][3] else True
            v = verdict(P[n]['d'], P[n]['ci90'], up, dn, gok)
            lo, hi = P[n]['ci90']
            out[n] = dict(true=round(true[n], 4), mean=round(float(P[n]['d'].mean()), 4),
                          bias=round(float(P[n]['d'].mean() - true[n]), 4),
                          rmse=round(float(np.sqrt(((P[n]['d'] - true[n]) ** 2).mean())), 4),
                          cover90=round(float(((lo <= true[n]) & (true[n] <= hi)).mean()), 3),
                          reject_up=round(float(up.mean()), 3), g_rule=round(float(np.mean(gok)), 3),
                          per_twin_reject_up={c: round(float(np.mean(v)), 3) for c, v in pr[n].items()},
                          **{f'P_{x}': round(float((v == x).mean()), 3) for x in VERDICTS})
        fw = np.zeros(R, bool)
        for n in prim:
            i = prim.index(n)
            fw |= (H['p_up'][:, i] <= ALPHA) & (H['q_up'][:, i] <= ALPHA)
        return out, round(float(fw.mean()), 3)

    rep = dict(design=dict(twins=TWINS, seeds={t: SEEDS[c] for t, c in TWINS.items()}, draws=k, reps=R,
                           generator='scratchpad/noise/sim.py classes', failure_drops=src, n_drops=len(dr),
                           floors=FLOOR, g_noise=FLOOR_G, primaries=prim), scenarios={})
    null, fw = run(0, 0, 0)
    rep['scenarios']['null'] = dict(params=dict(a=0, b=0, gamma=0), familywise_reject_up=fw, tests=null)
    power = {}
    for d in a.ds:                                  # each test's own contrast = d (phi_T = a/2: a = 2d)
        for lab, (pa, pb, pg) in (('a=d', (d, 0, 0)), ('a=2d', (2 * d, 0, 0)), ('b=d', (0, d, 0)), ('gamma=d', (0, 0, d))):
            out, fw = run(pa, pb, pg)
            rep['scenarios'][f'd={d} {lab}'] = dict(params=dict(a=pa, b=pb, gamma=pg), familywise_reject_up=fw, tests=out)
        sc = rep['scenarios']
        power[d] = {n: dict(scenario=s, reject=sc[f'd={d} {s}']['tests'][n]['reject_up'],
                            leaks=sc[f'd={d} {s}']['tests'][n]['P_leaks'], true=sc[f'd={d} {s}']['tests'][n]['true'])
                    for n, s in (('phi_T', 'a=2d'), ('phi_K', 'b=d'), ('phi_G', 'gamma=d'), ('L2_AOI', 'a=d'),
                                 ('L3_AOI', 'b=d'), ('L5_AOI', 'gamma=d'))}
    rep['power'] = power
    print(f"leak_read mc: {R} replicates x 10 twins x 6 cells x 2-3 seeds x {k} draws; drops: {src} ({len(dr)})")
    print(f"null: family-wise 'leaks' rejection over {prim}: {rep['scenarios']['null']['familywise_reject_up']}; "
          + '; '.join(f"{n} P(no leak) {x['P_no leak']} P(leaks) {x['P_leaks']}" for n, x in null.items() if n in prim))
    print(f"{'test':<8} " + ' '.join(f'd={d}: reject / P(leaks)'.rjust(26) for d in a.ds))
    for n in power[a.ds[0]]:
        print(f'{n:<8} ' + ' '.join(f"{power[d][n]['reject']:>12.3f} / {power[d][n]['leaks']:<11.3f}" for d in a.ds))
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('read'); r.add_argument('inputs', nargs='+'); r.add_argument('--metric', default='auc_star')
    r.add_argument('--crash', choices=('drop', 'zero'), default='drop'); r.add_argument('--class-noise')
    r.add_argument('--drop-refused', action='store_true'); r.add_argument('--no-config-check', action='store_true')
    r.add_argument('--out')
    m = sub.add_parser('mc'); m.add_argument('--reps', type=int, default=2000); m.add_argument('--draws', type=int, default=10)
    m.add_argument('--noise'); m.add_argument('--rng', type=int, default=7); m.add_argument('--out')
    m.add_argument('--ds', type=lambda s: [float(x) for x in s.split(',')], default=[0.03, 0.05, 0.10])
    for n in ('refrule', 'refconv'):
        x = sub.add_parser(n); x.add_argument('file'); x.add_argument('--out')
    a = ap.parse_args()
    if a.cmd == 'read':
        rep = read(a); show(rep)
    elif a.cmd == 'mc':
        rep = mc(a)
    elif a.cmd == 'refrule':
        j = json.load(open(a.file)); rep = ref_rule(j['dR'], j.get('noise')); print(rep)
    else:
        rep = ref_conv(json.load(open(a.file))['evals']); print(rep)
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x))


if __name__ == '__main__':
    main()
