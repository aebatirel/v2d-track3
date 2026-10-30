"""Leak decomposition, CPU test (g) of PLAN.md §7 for B7 tools/leak_read.py: synthetic data with known effects, the
config refusals, the two real summary formats, then the Monte Carlo of the plan's design. No ground truth is read
(the real-format cases use the CPU mocks' fake scores). Synthetic records go to WORK (scratch), results to OUT.
  1 units: Shapley closed form vs brute force over all orders (v(K) = v(T,K), v(K,G) = v(T,K,G)); the SE rule by hand;
    Welch df 2(s-1); Holm; exact sign-flip p; paired t vs scipy; LB by hand; refrule / refconv.
  2 exact recovery: 10 twins x c1-c8 x 2-3 seeds x 10 draws whose noise sums to zero per seed and per cell, with
    per-twin true effects; every per-twin and pooled contrast must equal the truth to the report's rounding, dT = dS +
    dg, AOI / LOO / Shapley / interaction, LB, copy ceiling and the verdicts the truths imply.
  3 one noisy realisation (the MC generator), the same effects: estimates within 3 SE of the truth.
  4 config refusals (exit 2, the record named) and --drop-refused; 5 formats: an oracle_twins summary (orcB mock) and a
    glock_public per-episode summary (orcB mock), crash handling.
  6 the Monte Carlo: python -I tools/leak_read.py mc --reps N --noise NOISE --out OUT_MC.
Usage: python -I reader_test.py --repo REPO --work DIR --noise NOISE_DIR --mock ORCB_MOCK_CONTENT --out reader_test.json
       --mc-out reader_mc.json [--reps 4000]
"""
import argparse, copy, importlib.util, itertools, json, math, os, shutil, subprocess, sys

import numpy as np
from scipy import stats

ap = argparse.ArgumentParser()
for k in ('repo', 'work', 'noise', 'mock', 'out', 'mc_out'):
    ap.add_argument('--' + k.replace('_', '-'), required=True)
ap.add_argument('--reps', type=int, default=4000)
A = ap.parse_args()
spec = importlib.util.spec_from_file_location('leak_read', f'{A.repo}/tools/leak_read.py')
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
TOOL = [sys.executable, '-I', f'{A.repo}/tools/leak_read.py']
res, fails = {}, []


def need(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)
    if not ok:
        fails.append(what)
    return ok


# ------------------------------------------------------------------ 1 units
rng = np.random.default_rng(1)
cells6 = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']
err = 0.0
for _ in range(200):
    c = dict(zip(cells6, rng.uniform(0.3, 1.0, 6)))
    v = {frozenset(): c['c1'], frozenset('T'): c['c2'], frozenset('K'): c['c3'], frozenset('TK'): c['c3'],
         frozenset('G'): c['c4'], frozenset('TG'): c['c5'], frozenset('KG'): c['c6'], frozenset('TKG'): c['c6']}
    phi = dict.fromkeys('TKG', 0.0)
    for order in itertools.permutations('TKG'):
        S = set()
        for p in order:
            phi[p] += (v[frozenset(S | {p})] - v[frozenset(S)]) / 6; S.add(p)
    for p in 'TKG':
        err = max(err, abs(phi[p] - sum(w * c[x] for x, w in L.CONTRASTS[f'phi_{p}'][0].items())))
    err = max(err, abs(sum(phi.values()) - (c['c6'] - c['c1'])))
need(err < 1e-12, f'Shapley closed form = brute force over all 6 orders, and efficiency (max err {err:.1e})')
m, se, df, ss, sd = L.arm([0.90, 0.80], [0.0004, 0.0004], [10, 10], L.FLOOR['hard'])
hand = math.sqrt(max(0.005 - 0.0004 / 10, 0.10 ** 2) / 2 + 0.0004 / 20)
need(abs(se - hand) < 1e-12 and df == 1, f'SE rule (hard floor binds): {float(se):.6f} = {hand:.6f}, df 1')
m, se, df, ss, sd = L.arm([0.90, 0.80], [0.0004, 0.0004], [10, 10], L.FLOOR['stable'])
hand = math.sqrt((0.005 - 0.00004) / 2 + 0.0004 / 20)
need(abs(se - hand) < 1e-12 and abs(ss - math.sqrt(0.00496)) < 1e-12, f'SE rule (observed seed var binds): {float(se):.6f}')
m, se, df, ss, sd = L.arm([0.90], [0.0004], [10], L.FLOOR['typical'])
need(abs(se - math.sqrt(0.03 ** 2 + 0.0004 / 10)) < 1e-12 and np.isinf(df), 'SE rule, one seed: class floor, df inf')
d, s2, df = L.combine([(1, 0.9, 0.05, 2), (-1, 0.8, 0.05, 2)])
need(abs(df - 4) < 1e-9 and abs(s2 - math.sqrt(0.005)) < 1e-12, 'Welch df of two equal 3-seed arms = 2(s-1) = 4')
need(np.allclose(L.holm(np.array([0.01, 0.04, 0.03])), [0.03, 0.06, 0.06]), 'Holm (0.01, 0.04, 0.03) -> (0.03, 0.06, 0.06)')
P = L.pooled(np.full(10, 0.05) + rng.normal(0, 0.01, 10))
need(abs(P['q_up'] - 1 / 1024) < 1e-12, f"exact sign-flip p of 10 positive twins = 1/1024 ({P['q_up']:.6f})")
x = rng.normal(0.01, 0.03, 10); P = L.pooled(x)
need(abs(P['p_up'] - stats.ttest_1samp(x, 0, alternative='greater').pvalue) < 1e-12, 'paired t = scipy ttest_1samp')
dt = {t: 0.01 * (i + 1) for i, t in enumerate(L.TWINS)}; st = dict.fromkeys(L.TWINS, 0.02)
hand = sum(np.mean([dt[t] for t in tw]) for tw in L.EVAL_TWINS.values())
lbr = L.lb(dt, st)
need(abs(lbr['c0.74']['L'] - round(0.74 / 20 * hand, 5)) < 1e-9 and abs(lbr['c1.0']['L'] - round(hand / 20, 5)) < 1e-9,
     f"LB by hand: c 0.74 {lbr['c0.74']['L']}, c 1.0 {lbr['c1.0']['L']} (evals {lbr['evals']})")
lbm = L.lb({t: v for t, v in dt.items() if t != 'ep13'}, st)
need(14 in lbm['missing_evals'] and 14 not in lbm['evals'], 'LB: eval 14 needs both ep12 and ep13 (never imputed)')
rr = [L.ref_rule({e: 0.02 for e in range(20)})['verdict'], L.ref_rule({e: 0.001 for e in range(20)})['verdict'],
      L.ref_rule({e: (0.05 if e < 11 else -0.01) for e in range(20)})['verdict'],
      L.ref_rule({e: 0.02 for e in range(20)}, noise=0.015)['verdict'], L.ref_rule({e: -0.02 for e in range(20)})['verdict']]
need(rr == ['leaks', 'no leak', 'inconclusive', 'inconclusive', 'truth worse'], f'refrule: {rr}')
rc = L.ref_conv({3: dict(dR=0.02, S=0.9), 5: dict(dR=0.02, S=0.7), 7: dict(dR=0.05, S=0.95, spoon=True)})
need(abs(rc['L_c1.0'] - round(1.025 * 0.9 * 0.02 / 20, 5)) < 1e-12 and not rc['rows'][5]['counted']
     and not rc['rows'][7]['counted'], f'refconv: S >= 0.8 only, spoon apart: {rc}')
res['units'] = dict(shapley_max_err=err, lb=lbr, refrule=rr, refconv=rc)

# ------------------------------------------------------------------ 2 exact recovery (files, the CLI)
W = A.work; shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
TRUE = {}
for i, (tw, cls) in enumerate(L.TWINS.items()):          # heterogeneous truths: phi_T = a/2, phi_K = a/2 + b, phi_G = gam
    TRUE[tw] = dict(a=0.12 + 0.004 * (i - 4.5), b=0.001 * (i - 4.5), gam=-0.035 + 0.0015 * (i - 4.5), h=0.0005 * (i - 4.5),
                    base=0.70 if tw == 'ep24' else min(L.GEN[cls]['base'], 0.91))      # every cell stays below 1
DRAW = np.array([-0.03, -0.02, -0.01, -0.005, -0.001, 0.001, 0.005, 0.01, 0.02, 0.03])  # sums to 0
GDRAW = DRAW * 0.3
SOFF = {2: (0.01, -0.01), 3: (0.01, 0.0, -0.01)}


def cell_values(t):
    T, G = L.truth(t['a'], t['b'], t['gam'], t['base'])
    T.update(c7=T['c1'] + t['h'], c8=T['c6'] + t['h']); G.update(c7=G['c1'], c8=G['c6'])
    return T, G


def config(tw, cell, seed):
    pose, sim, hands = L.CELLS[cell]
    return dict(commit='l0sha00', learner='glock', STEPS=70004736, CURVE_REP=3, NREP=10, GL_ARGS=f'--recipe {tw}', seed=seed,
                pose=dict(source=pose, md5=f'{tw}-{pose}-md5'), sim=dict(geom=sim, SF=0 if sim == 'scan' else 1,
                assets_md5=f'{sim}-assets'), hands=dict(md5=f'{tw}-hands-{hands}'),
                ref=dict(md5=f'{tw}-{cell}-{seed}'), run=dict(id=f'20261031-orcL{cell}s{seed}-l0sha00', box=f'box{seed}'))


def write(root, tw, cell, seed, T, G, cfg, extra_rows=()):
    d = f'{root}/{tw}/{cell}/s{seed}'; os.makedirs(d, exist_ok=True)
    rows = [dict(rollout=f'r{j + 1}', auc_star=round(T + x, 10), sim_vs_ref=round(T + x - (G + gx), 10),
                 auc=round(T + x - 0.01, 10)) for j, (x, gx) in enumerate(zip(DRAW, GDRAW))] + list(extra_rows)
    json.dump(dict(checkpoint='stub', n=len(rows), rollouts=rows), open(f'{d}/summary.json', 'w'))
    json.dump(dict(twin=tw, cell=cell, seed=seed, summary='summary.json', config=cfg, cost_usd=1.0), open(f'{d}/cell.json', 'w'))


def build(root, mutate=lambda tw, cell, seed, cfg: cfg):
    for tw, cls in L.TWINS.items():
        T, G = cell_values(TRUE[tw]); ss = L.SEEDS[cls]
        for cell in L.CELLS:
            for seed, off in zip(ss, SOFF[len(ss)]):
                cfg = mutate(tw, cell, seed, config(tw, cell, seed))
                if cfg is not False:
                    write(root, tw, cell, seed, T[cell] + off, G[cell], cfg)


def run(*args):
    p = subprocess.run(TOOL + list(args), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


build(f'{W}/exact')
rc, out, errs = run('read', f'{W}/exact', '--out', f'{W}/exact.json')
need(rc == 0, f'exact: read rc {rc} {errs[-300:]}')
print(out)
R = json.load(open(f'{W}/exact.json')); C = R['contrasts']
truth = {tw: {n: sum(x * cell_values(TRUE[tw])[0][c] for c, x in w.items()) for n, (w, *_) in L.CONTRASTS.items()}
         for tw in L.TWINS}
gtruth = {tw: {n: sum(x * cell_values(TRUE[tw])[1][c] for c, x in w.items()) for n, (w, *_) in L.CONTRASTS.items()}
          for tw in L.TWINS}
e1 = max(abs(C[n]['twins'][tw]['dT'] - truth[tw][n]) for n in C for tw in C[n]['twins'])
e2 = max(abs(C[n]['dT'] - np.mean([truth[tw][n] for tw in L.TWINS])) for n in C)
e3 = max(abs(C[n]['dg'] - np.mean([gtruth[tw][n] for tw in L.TWINS])) for n in C)
e4 = max(abs(C[n]['additivity']) for n in C)
need(e1 <= 6e-6 and e2 <= 6e-6, f'exact: every per-twin and pooled contrast = truth to rounding (max {e1:.1e}, {e2:.1e})')
need(e3 <= 6e-6 and e4 < 1e-9, f'exact: dg = truth ({e3:.1e}); dT - dS - dg = {e4:.1e}')
need(all(len(C[n]['twins_used']) == 10 for n in C) and C['L6_AOI']['family'].startswith('primary'),
     'exact: all 10 twins in every contrast; L6 AOI joins the Holm family when c7 ran')
mean = lambda k: float(np.mean([TRUE[t][k] for t in L.TWINS]))
pl = R['players']
need(abs(pl['T']['shapley'] - mean('a') / 2) < 6e-6 and abs(pl['K']['shapley'] - mean('a') / 2 - mean('b')) < 6e-6
     and abs(pl['G']['shapley'] - mean('gam')) < 6e-6 and abs(pl['T']['AOI'] - mean('a')) < 6e-6
     and abs(pl['K']['AOI'] - mean('a') - mean('b')) < 6e-6 and abs(pl['K']['LOO'] - mean('b')) < 6e-6
     and abs(pl['G']['LOO'] - mean('gam')) < 6e-6 and abs(pl['T']['interaction'] + mean('a')) < 6e-6,
     f'exact: players {pl}')
need(abs(sum(pl[p]['shapley'] for p in 'TKG') - C['total']['dT']) < 2e-5, 'exact: phi_T + phi_K + phi_G = c6 - c1')
vv = {n: C[n]['verdict'] for n in C}
need(vv['phi_T'] == 'leaks' and vv['phi_K'] == 'leaks' and vv['phi_G'] == 'truth worse' and vv['L3_AOI'] == 'no leak'
     and vv['L6_AOI'] == 'no leak' and vv['L2_AOI'] == 'leaks' and vv['L5_AOI'] == 'truth worse', f'exact: verdicts {vv}')
hand = {c: c / 20 * sum(np.mean([truth[t]['phi_T'] for t in tw]) for tw in L.EVAL_TWINS.values()) for c in L.C_LB}
need(all(abs(C['phi_T']['LB'][f'c{c}']['L'] - hand[c]) < 1e-5 for c in L.C_LB), f"exact: LB phi_T {C['phi_T']['LB']}")
cc = R['copy_ceiling']
need(cc['ep24']['call'].startswith('robot') and cc['ep11']['call'].startswith('copyable'), 'exact: copy ceiling calls')
need(abs(R['cells']['ep2 c1']['L1_lib_minus_star'] + 0.01) < 1e-9, 'exact: L1 column (lib - star) per cell = -0.01')
res['exact'] = dict(max_err_twin=e1, max_err_pooled=e2, verdicts=vv, players=pl, explained=R.get('explained_total'))

# ------------------------------------------------------------------ 3 one noisy realisation (MC generator)
g = np.random.default_rng(11); dr, _ = L.drops(A.noise)
for tw, cls in L.TWINS.items():
    T, G = cell_values(TRUE[tw]); s = len(L.SEEDS[cls])
    for cell in L.CELLS:
        x, gg = L.simulate(g, cls, T[cell], G[cell], s, 10, 1, dr)
        for j, seed in enumerate(L.SEEDS[cls]):
            d = f'{W}/noisy/{tw}/{cell}/s{seed}'; os.makedirs(d, exist_ok=True)
            rows = [dict(rollout=f'r{i + 1}', auc_star=float(x[0, j, i]), sim_vs_ref=float(x[0, j, i] - gg[0, j, i]))
                    for i in range(10)]
            json.dump(dict(rollouts=rows), open(f'{d}/summary.json', 'w'))
            json.dump(dict(twin=tw, cell=cell, seed=seed, summary='summary.json', config=config(tw, cell, seed)),
                      open(f'{d}/cell.json', 'w'))
rc, out, errs = run('read', f'{W}/noisy', '--out', f'{W}/noisy.json')
print(out)
Rn = json.load(open(f'{W}/noisy.json'))['contrasts']
z = {n: (Rn[n]['dT'] - np.mean([truth[t][n] for t in L.TWINS])) / Rn[n]['se_paired'] for n in ('phi_T', 'phi_K', 'phi_G', 'L2_AOI', 'L5_AOI')}
need(rc == 0 and all(abs(v) < 3 for v in z.values()), f'noisy: estimates within 3 SE of the truth: { {k: round(v, 2) for k, v in z.items()} }')
res['noisy'] = {n: dict(dT=Rn[n]['dT'], ci90=Rn[n]['ci90'], verdict=Rn[n]['verdict']) for n in Rn}

# ------------------------------------------------------------------ 4 config refusals
def mut(f):
    return lambda tw, cell, seed, cfg: f(tw, cell, seed, copy.deepcopy(cfg))


def m_gl(tw, cell, seed, c):
    if (tw, cell, seed) == ('ep12', 'c3', 43):
        c['GL_ARGS'] += ' --snap 0'
    return c


def m_hands(tw, cell, seed, c):
    if (tw, cell, seed) == ('ep2', 'c4', 44):
        c['hands']['md5'] = 'other'
    return c


def m_noop(tw, cell, seed, c):
    if tw == 'ep21' and L.CELLS[cell][0] == 'P_s':
        c['pose']['md5'] = f'{tw}-P_o-md5'
    return c


def m_steps(tw, cell, seed, c):
    if tw == 'ep31':
        c['STEPS'] = 50003968
    return c


def m_seed(tw, cell, seed, c):
    if (tw, cell, seed) == ('ep11', 'c1', 42):
        c['seed'] = 43
    return c


def m_none(tw, cell, seed, c):
    return None if (tw, cell, seed) == ('ep39', 'c5', 43) else c


def m_nohands(tw, cell, seed, c):
    if (tw, cell, seed) == ('ep27', 'c2', 42):
        c.pop('hands')
    return c


def m_tie(tw, cell, seed, c):
    if tw == 'ep18' and cell == 'c6' and seed == 43:
        c['pose']['md5'] = 'tie-a'
    return c


cases = [('GL_ARGS on one arm', m_gl, ['ep12 c3 s43'], 'a fixed field'),
         ('hands md5 of one c1-c6 arm', m_hands, ['ep2 c4 s44'], 'hands.* at bundle'),
         ('P_s pose = P_o pose (no-op swap)', m_noop, ['ep21 c2 s42', 'ep21 c5 s43'], 'did not change'),
         ('STEPS on one twin', m_steps, ['ep31 c1 s42', 'ep31 c8 s44'], 'study key'),
         ('config seed != record seed', m_seed, ['ep11 c1 s42'], 'config seed'),
         ('no config', m_none, ['ep39 c5 s43'], 'no config'),
         ('no hands.* fields', m_nohands, ['ep27 c2 s42'], 'cannot be checked'),
         ('mocap pose md5 of one c6 seed', m_tie, ['ep18 c6 s43'], 'pose.* at O')]
res['refusals'] = {}
for name, f, who, why in cases:
    root = f'{W}/refuse_{f.__name__}'; build(root, mut(f))
    rc, out, errs = run('read', root)
    hit = all(any(w.split()[0] in l and f' {w.split()[1]} {w.split()[2]} ' in l and why in l for l in errs.splitlines())
              for w in who)
    rc2, out2, _ = run('read', root, '--drop-refused')
    n_ref = sum(1 for l in errs.splitlines() if l.startswith('  '))
    need(rc == 2 and hit and rc2 == 0, f'refuse: {name}: rc {rc}, names {who} ({why}); --drop-refused rc {rc2}')
    res['refusals'][name] = dict(rc=rc, refused_lines=n_ref, first=errs.splitlines()[1:3], drop_rc=rc2)
rc, out, errs = run('read', f'{W}/exact', '--no-config-check')
need(rc == 0 and 'config skipped' in out, 'refuse: --no-config-check reads, and says so')

# ------------------------------------------------------------------ 5 real summary formats (CPU mocks, fake scores)
ot = f'{A.mock}/results/oracle_twins/summary.json'
idx = [dict(twin=e, cell=c, seed=42, summary=ot, arm=a) for e in ('ep11', 'ep13', 'ep31') for c, a in (('c1', 'P'), ('c3', 'O'))]
json.dump(idx, open(f'{W}/orc_index.json', 'w'))
rc, out, errs = run('read', f'{W}/orc_index.json', '--metric', 'auc', '--no-config-check', '--out', f'{W}/orc.json')
O = json.load(open(ot))['episodes']; Ro = json.load(open(f'{W}/orc.json'))['contrasts']['K_AOI']['twins']
ok = rc == 0 and all(abs(Ro[e]['dT'] - O[e]['delta_O_minus_P']) < 1e-4 and abs(Ro[e]['dS'] - O[e]['sim_vs_ref_O_minus_P']) < 1e-4
                     for e in O)
need(ok, f'format: oracle_twins summary (orcB mock): c3 - c1 = delta_O_minus_P per twin '
     f'{ {e: (Ro[e]["dT"], O[e]["delta_O_minus_P"]) for e in O} }')
gp = f'{A.mock}/results/glock_public/ep11/best/summary.json'; S0 = json.load(open(gp))
os.makedirs(f'{W}/glock/c1', exist_ok=True)
json.dump(dict(twin=11, cell='c1', seed=42, summary=gp), open(f'{W}/glock/c1/cell.json', 'w'))
rc, out, errs = run('read', f'{W}/glock', '--metric', 'auc', '--no-config-check', '--out', f'{W}/glock.json')
cl = json.load(open(f'{W}/glock.json'))['cells']['ep11 c1']
need(rc == 0 and abs(cl['T']['mean'] - S0['auc']['mean']) < 1e-4 and cl['k'] == [S0['n']],
     f"format: glock_public per-episode summary: T {cl['T']['mean']:.4f} = summary auc mean {S0['auc']['mean']}, k {cl['k']}")
os.makedirs(f'{W}/crash/c1', exist_ok=True)
rows = [dict(rollout='r1', auc_star=0.9, sim_vs_ref=0.88), dict(rollout='r2', auc_star=0.8, sim_vs_ref=0.79),
        dict(rollout='r3', error='evaluator crashed')]
json.dump(dict(rollouts=rows), open(f'{W}/crash/c1/summary.json', 'w'))
json.dump(dict(twin='ep11', cell='c1', seed=42, summary='summary.json'), open(f'{W}/crash/c1/cell.json', 'w'))
cr = {}
for mode in ('drop', 'zero'):
    rc, out, errs = run('read', f'{W}/crash', '--no-config-check', '--crash', mode, '--out', f'{W}/crash_{mode}.json')
    cr[mode] = json.load(open(f'{W}/crash_{mode}.json'))['cells']['ep11 c1']
need(cr['drop']['crashes'] == 1 and abs(cr['drop']['T']['mean'] - 0.85) < 1e-9 and abs(cr['zero']['T']['mean'] - 0.5667) < 1e-4,
     f"format: an evaluation error is counted; drop -> {cr['drop']['T']['mean']}, zero -> {cr['zero']['T']['mean']:.4f}")
res['formats'] = dict(oracle_twins={e: (Ro[e]['dT'], O[e]['delta_O_minus_P']) for e in O}, glock=cl['T'], crash=cr)

# ------------------------------------------------------------------ 6 Monte Carlo of the plan's design
p = subprocess.run(TOOL + ['mc', '--reps', str(A.reps), '--noise', A.noise, '--out', A.mc_out], capture_output=True, text=True)
print(p.stdout[-3000:], p.stderr[-2000:])
mc = json.load(open(A.mc_out)); nul = mc['scenarios']['null']
need(p.returncode == 0 and nul['familywise_reject_up'] <= 0.05 + 2 * math.sqrt(0.05 * 0.95 / A.reps),
     f"MC: family-wise false 'leaks' rejection under the null {nul['familywise_reject_up']} (<= 0.05 + 2 MC SE)")
bias = max(abs(x['bias']) for s in mc['scenarios'].values() for x in s['tests'].values())
need(bias < 0.006, f'MC: max |bias| of the pooled estimates over all scenarios {bias} (< 0.006; clipping at 1 aside)')
cov = [x['cover90'] for s in mc['scenarios'].values() for x in s['tests'].values()]
need(min(cov) >= 0.85, f'MC: paired-t 90 % CI coverage {min(cov)}-{max(cov)} (>= 0.85)')
res['mc'] = dict(power=mc['power'], null=nul)
res['fails'] = fails
json.dump(res, open(A.out, 'w'), indent=1, default=float)
print('RESULT:', 'ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails}')
sys.exit(1 if fails else 0)
