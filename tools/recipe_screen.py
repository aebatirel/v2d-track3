"""Recipe screen (2026-10-31; pre-registered in docs/research/physics-2026-10-30/physics-solver.md section 8): arm
definitions, per-cell records, the box summary and the merge / verdict tool. One source of truth for the arms: the box
job (ops/jobs/recipe_screen.sh) and the CPU tests (tools/recipe_screen_tests/) take the overrides from here.

Arms (everything else = the frozen glock_public recipe of rounds 1-3: FDR rewards + VOC fix, S1 scan assets, the same
stored reference per episode, ES on, cap STEPS, checkpoint chosen by sim_vs_ref):
  C  control: no extra override (curriculum thresholds unscaled; LR 3e-4 -> 1.5e-4 cosine over the run's own updates)
  K  keep-the-peak: learning_rate_initial = peak 6e-4, end 3e-5, learning_rate_schedule_updates pinned to the cap's total
     optimizer updates (int(STEPS / 4096) * 8 = 136728 for 70,004,736 steps); curriculum thresholds x K_CURR (2.0):
     every assist stage lasts twice as long (VOC >= 0.25 until 127.8M instead of 63.9M)
  D  start-state randomization: training env FC_DR_RESET (ops/box/patch_flashchord_dr.py) and FC_DR_SEED = the seed; no
     config field
Subcommands:
  args ARM STEPS                 Hydra overrides of the arm (one line)
  env ARM SEED DR                environment assignments of the arm's TRAINING process (one line; empty for C / K)
  ckcfg CKPT OUT.json [RUN]      the checkpoint's resolved settings (needs safetensors: FlashCHORD's venv)
  cell ARM EP SEED CELL_DIR RUN [STATUS]   one cell's record (JSON on stdout)
  summary RESULTS_DIR [--run ID] [--commit SHA] [--cells "arm:ep:seed ..."] [--meta K=V ...]   the box summary
  verdict SUMMARY.json|RESULTS_DIR ... [--out MERGED.json]   merge box summaries (or a box's results/recipe_screen
                                 directory: its cell.json files) and compute the pre-registered verdicts
No ground truth is read here: AUC values come from the job's scoring (pipeline/score_registered.py, after inference)."""
import glob, hashlib, json, math, os, re, sys

WORLDS, UPC = 4096, 8.0                      # experiment=sharpa_flash_sac: scene.world_count, updates_per_collection
THRESHOLDS = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]
VOC = [1.0, 0.75, 0.5, 0.25, 0.1, 0.05, 0.025, 0.01, 0.0, 0.0, 0.0]   # tracking_250m_mixed_reset(_v2d) stage scales
LR_C = dict(learning_rate_initial=3e-4, learning_rate_peak=3e-4, learning_rate_end=1.5e-4, learning_rate_schedule_updates=None)
K_LR = dict(learning_rate_initial=6e-4, learning_rate_peak=6e-4, learning_rate_end=3e-5)
K_CURR = 2.0
ARMS, EPS, SEEDS = ('C', 'K', 'D'), (2, 12, 18, 24), (42, 43)
MIN_DRAWS = 8                                # a cell counts as present iff >= 8 of its NREP (10) draws were scored
TOL = 1e-9                                   # rule bounds are inclusive as written (>= 0.03 etc.), up to float rounding


def total_updates(steps):
    return int((int(steps) // WORLDS) * UPC)


def k_thresholds():
    return [int(x * K_CURR) for x in THRESHOLDS]


def arm_overrides(arm, steps):
    if arm in ('C', 'D'):
        return []
    if arm == 'K':
        o = 'training.optimization.'
        return [f'{o}{k}={v}' for k, v in K_LR.items()] + [f'{o}learning_rate_schedule_updates={total_updates(steps)}',
                                                         'curriculum.thresholds=[' + ','.join(map(str, k_thresholds())) + ']']
    raise SystemExit(f'unknown arm {arm!r}')


def arm_env(arm, seed, dr):
    if arm == 'D':
        if not re.fullmatch(r'[0-9.,]+', dr):
            raise SystemExit(f'DR_RESET must be pos_mm,rot_rad,joint_rad without spaces, got {dr!r}')
        return [f'FC_DR_RESET={dr}', f'FC_DR_SEED={int(seed)}']
    if arm in ('C', 'K'):
        return []
    raise SystemExit(f'unknown arm {arm!r}')


def expected(arm, steps, seed):
    lr = dict(LR_C)
    if arm == 'K':
        lr.update(K_LR, learning_rate_schedule_updates=total_updates(steps))
    return dict(total_environment_steps=int(steps), seed=int(seed), thresholds=k_thresholds() if arm == 'K' else THRESHOLDS, **lr)


# ---------------------------------------------------------------------------------------------- per-cell records
def ckcfg(ck, out, run=None):
    from safetensors import safe_open
    with safe_open(ck, 'np') as f:
        m = dict(f.metadata())
    c = json.loads(m['user.resolved_config_json']); tr = c.get('training', {}); o = tr.get('optimization', {})
    text = json.dumps(c, sort_keys=True)
    norm = text.replace(run, '<RUN>') if run else text
    norm = re.sub(r'"output_dir": "[^"]*"', '"output_dir": "<RUN>"', norm)
    fc = c.get('objective', {}).get('force_closure', {})
    d = dict(checkpoint=os.path.basename(ck), environment_steps=int(m.get('user.environment_steps', -1)),
             curriculum_stage=int(m.get('user.curriculum_stage', -1)), voc_scale=float(m.get('user.voc_scale', 'nan')),
             total_environment_steps=tr.get('total_environment_steps'), seed=c.get('reset', {}).get('seed'),
             thresholds=c.get('curriculum', {}).get('thresholds'), **{k: o.get(k) for k in LR_C},
             fdr=dict(force_closure_enabled=fc.get('enabled'), force_closure_weight=fc.get('weight'),
                      wrench_weight=c.get('objective', {}).get('contact_wrench_support', {}).get('weight'),
                      unintended_weight=c.get('objective', {}).get('unintended_contact', {}).get('weight')),
             dr_strings=sorted(set(re.findall(r'(?i)fc_dr\w*|v2d_dr\w*|dr_reset\w*', text))),
             cfg_sha256=hashlib.sha256(norm.encode()).hexdigest()[:16])
    json.dump(d, open(out, 'w'), indent=1)
    return d


def jl(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def dr_line(run):
    """The DR hook's start line in the training log (ops/box/patch_flashchord_dr.py prints it only when active)."""
    try:
        for line in open(f'{run}/train.log', errors='replace'):
            if 'v2d FC_DR_RESET:' in line:
                return line.strip()[:200]
    except OSError:
        return None
    return ''


def cell(arm, ep, seed, cd, run, status=None):
    """The record of one (arm, episode, seed) cell from the job's files (no ground truth is read here)."""
    st = status or (open(f'{cd}/status').read().strip() if os.path.exists(f'{cd}/status') else 'not_run')
    best = jl(f'{cd}/best/summary.json') or {}
    rows = best.get('rollouts', [])
    auc = [r['auc'] for r in rows if 'auc' in r]; svr = [r['sim_vs_ref'] for r in rows if 'sim_vs_ref' in r]
    stats = lambda v: None if not v else dict(mean=round(sum(v) / len(v), 4), sd=round(math.sqrt(sum((x - sum(v) / len(v)) ** 2 for x in v) / len(v)), 4),  # noqa: E731
                                              min=round(min(v), 4), max=round(max(v), 4), n=len(v))
    curve = []
    for d in sorted(glob.glob(f'{cd}/curve/policy_*'), key=lambda x: int(re.findall(r'\d+', os.path.basename(x))[0])):
        es, q = jl(f'{d}/es.json'), jl(f'{d}/qa_policy.json')
        s = es['mean'] if es else (q or {}).get('sim_vs_ref')
        curve.append([int(re.findall(r'\d+', os.path.basename(d))[0]), s, 'es' if es else 'curve'])
    es_stop = open(f'{run}/EARLY_STOPPED').read().strip() if os.path.exists(f'{run}/EARLY_STOPPED') else None
    ck = best.get('checkpoint')
    rec = dict(arm=arm, ep=int(ep), seed=int(seed), status=st, checkpoint=os.path.basename(ck) if ck else None,
               checkpoint_steps=int(re.findall(r'policy_(\d+)', ck)[0]) if ck and re.findall(r'policy_(\d+)', ck) else None,
               trained_checkpoints=len(glob.glob(f'{run}/policy_*.safetensors')), early_stop=es_stop,
               auc=stats(auc), sim_vs_ref=stats(svr), draws_failed=[r['rollout'] for r in rows if 'auc' not in r],
               curve=curve, config_check=jl(f'{cd}/config_check.json'),
               ref_md5=open(f'{cd}/ref_md5').read().strip() if os.path.exists(f'{cd}/ref_md5') else None,
               dr_active=dr_line(run), times=jl(f'{cd}/times.json'),
               notes=open(f'{cd}/notes').read().strip().splitlines() if os.path.exists(f'{cd}/notes') else [])
    rec['present'] = bool(st == 'scored' and rec['auc'] and rec['auc']['n'] >= MIN_DRAWS)
    return rec


def config_problems(rec, steps):
    """Deviations of a cell's checkpoint config from its arm's registered settings ([] = as registered)."""
    c = rec.get('config_check')
    if not c:
        return ['no config check']
    e = expected(rec['arm'], steps, rec['seed']); bad = []
    for k, v in e.items():
        got = c.get(k)
        if isinstance(v, float) and isinstance(got, (int, float)):
            if not math.isclose(got, v, rel_tol=1e-9):
                bad.append(f'{k} {got} != {v}')
        elif got != v:
            bad.append(f'{k} {got} != {v}')
    if c.get('dr_strings'):
        bad.append(f"DR strings in the config: {c['dr_strings']}")
    if rec.get('dr_active') is not None and bool(rec['dr_active']) != (rec['arm'] == 'D'):
        bad.append(f"DR hook {'active' if rec['dr_active'] else 'not active'} in a {rec['arm']} training")
    f = c.get('fdr', {})
    if (f.get('force_closure_enabled'), f.get('force_closure_weight'), f.get('wrench_weight'), f.get('unintended_weight')) != (True, 6, 3, -2):
        bad.append(f'FDR settings {f}')
    return bad


# ---------------------------------------------------------------------------------------------- verdicts
def key(arm, ep, seed):
    return f'{arm}/ep{ep}-s{seed}'


def verdicts(cells, steps):
    """cells: {key: record}. The pre-registered rules (physics-solver.md section 8); a missing cell -> INCOMPLETE."""
    present = {k: r for k, r in cells.items() if r.get('present')}
    missing = [dict(cell=key(a, e, s), status=(cells.get(key(a, e, s)) or {}).get('status', 'not in any summary'),
                    draws=((cells.get(key(a, e, s)) or {}).get('auc') or {}).get('n', 0))
               for e in EPS for s in SEEDS for a in ARMS if key(a, e, s) not in present]
    invalid = {}
    for k, r in present.items():
        p = config_problems(r, steps)
        if p:
            invalid[k] = p
    for e in EPS:                                   # one stored reference per episode across all arms, seeds, boxes
        md5 = {r['ref_md5'] for k, r in present.items() if r['ep'] == e}
        if len(md5) > 1:
            invalid[f'ep{e}'] = [f'reference md5 differs between cells: {sorted(md5)}']
    for e in EPS:                                   # D adds no config field: its config equals C's (same ep, seed)
        for s in SEEDS:
            c, d = present.get(key('C', e, s)), present.get(key('D', e, s))
            if c and d and (c['config_check'] or {}).get('cfg_sha256') != (d['config_check'] or {}).get('cfg_sha256'):
                invalid[key('D', e, s)] = invalid.get(key('D', e, s), []) + ['resolved config differs from C (same ep, seed)']
    sm = lambda a, e, f: [f(present[key(a, e, s)]) for s in SEEDS if key(a, e, s) in present]  # noqa: E731
    mean = lambda v: sum(v) / len(v)  # noqa: E731
    auc_m = lambda a, e: mean(sm(a, e, lambda r: r['auc']['mean'])) if len(sm(a, e, lambda r: 0)) == len(SEEDS) else None  # noqa: E731
    sd_m = lambda a, e: mean(sm(a, e, lambda r: r['auc']['sd'])) if len(sm(a, e, lambda r: 0)) == len(SEEDS) else None  # noqa: E731
    miss_of = lambda arms: [m['cell'] for m in missing if m['cell'].split('/')[0] in arms]  # noqa: E731
    inv_of = lambda arms: {k: v for k, v in invalid.items() if k.startswith('ep') or k.split('/')[0] in arms}  # noqa: E731
    out = {}
    # K vs C
    per = {f'ep{e}': dict(C=auc_m('C', e), K=auc_m('K', e)) for e in EPS}
    for v in per.values():
        v['delta'] = None if v['C'] is None or v['K'] is None else v['K'] - v['C']
    ds = [v['delta'] for v in per.values() if v['delta'] is not None]
    rule = 'signal iff mean over 4 episodes of (seed-mean AUC K - seed-mean AUC C) >= +0.03 and no episode <= -0.05; ' \
           'harm iff mean <= -0.03 or any episode <= -0.10; else inconclusive; a missing cell -> INCOMPLETE'
    m_, inv = miss_of(('C', 'K')), inv_of(('C', 'K'))
    if inv:
        v = 'INVALID'
    elif m_:
        v = 'INCOMPLETE'
    else:
        mu, lo = mean(ds), min(ds)                  # TOL: a bound hit exactly is not lost to float rounding
        v = 'signal' if mu >= 0.03 - TOL and lo > -0.05 + TOL else 'harm' if mu <= -0.03 + TOL or lo <= -0.10 + TOL else 'inconclusive'
    out['K_vs_C'] = dict(rule=rule, verdict=v, missing=m_, invalid=inv,
                         mean_delta=None if m_ or not ds else round(mean(ds), 4),
                         provisional_mean_delta_on_complete_episodes=round(mean(ds), 4) if ds else None,
                         episodes={k: {a: None if x is None else round(x, 4) for a, x in vv.items()} for k, vv in per.items()})
    # D vs C
    per = {}
    for e in EPS:
        c, d, sc, sd = auc_m('C', e), auc_m('D', e), sd_m('C', e), sd_m('D', e)
        drop = None if sc is None or sd is None or sc <= 0 else (sc - sd) / sc
        per[f'ep{e}'] = dict(C=c, D=d, delta=None if c is None or d is None else d - c, sd_C=sc, sd_D=sd, sd_drop=drop,
                             sd_falls_40pct=None if drop is None and (sc is None or sd is None) else bool(drop is not None and drop >= 0.40 - TOL))
    ds = [v['delta'] for v in per.values() if v['delta'] is not None]
    falls = sum(1 for v in per.values() if v['sd_falls_40pct'])
    rule = 'signal iff the 10-draw AUC sd (seed-mean) falls by >= 40 % on >= 2 of 4 episodes and the 4-episode mean AUC ' \
           'is not lower by more than 0.02; harm iff the mean AUC is lower by >= 0.03; else inconclusive; a missing cell -> INCOMPLETE'
    m_, inv = miss_of(('C', 'D')), inv_of(('C', 'D'))
    if inv:
        v = 'INVALID'
    elif m_:
        v = 'INCOMPLETE'
    else:
        mu = mean(ds)
        v = 'signal' if falls >= 2 and mu >= -0.02 - TOL else 'harm' if mu <= -0.03 + TOL else 'inconclusive'
    out['D_vs_C'] = dict(rule=rule, verdict=v, missing=m_, invalid=inv, episodes_sd_falls_40pct=falls,
                         mean_delta=None if m_ or not ds else round(mean(ds), 4),
                         provisional_mean_delta_on_complete_episodes=round(mean(ds), 4) if ds else None,
                         episodes={k: {a: (None if x is None else round(x, 4)) if not isinstance(x, bool) else x for a, x in vv.items()}
                                   for k, vv in per.items()})
    # reports (no rule): seed selection by sim_vs_ref, rank agreement
    sel, agree = {}, []
    for a in ARMS:
        rows = []
        for e in EPS:
            r = [present.get(key(a, e, s)) for s in SEEDS]
            if not all(r):
                continue
            pick = max(r, key=lambda x: x['sim_vs_ref']['mean']); m2 = mean([x['auc']['mean'] for x in r])
            rows.append(dict(ep=e, picked_seed=pick['seed'], picked_auc=pick['auc']['mean'], two_seed_mean=round(m2, 4),
                             gain=round(pick['auc']['mean'] - m2, 4), oracle_best=max(x['auc']['mean'] for x in r)))
            dv, da = r[0]['sim_vs_ref']['mean'] - r[1]['sim_vs_ref']['mean'], r[0]['auc']['mean'] - r[1]['auc']['mean']
            agree.append(dict(cell=f'{a}/ep{e}', svr_42_minus_43=round(dv, 4), auc_42_minus_43=round(da, 4),
                              same_order=None if dv == 0 or da == 0 else (dv > 0) == (da > 0)))
        sel[a] = dict(episodes=rows, mean_gain=round(mean([x['gain'] for x in rows]), 4) if rows else None, n=len(rows))
    out['report_seed_selection_by_sim_vs_ref'] = sel
    ok = [x for x in agree if x['same_order'] is not None]
    out['report_sim_vs_ref_ranks_seeds_like_auc'] = dict(agree=sum(x['same_order'] for x in ok), of=len(ok), cells=agree)
    out['missing_cells'] = missing
    return out


def table(cells):
    lines = ['cell          status   ckpt   draws  AUC mean   sd     worst   svr mean  sd     ES stop']
    for e in EPS:
        for s in SEEDS:
            for a in ARMS:
                r = cells.get(key(a, e, s))
                if not r:
                    lines.append(f'{key(a, e, s):13s} (none)'); continue
                au, sv = r.get('auc') or {}, r.get('sim_vs_ref') or {}
                lines.append(f"{key(a, e, s):13s} {r['status'][:8]:8s} {(r.get('checkpoint_steps') or 0) / 1e6:4.0f}M  {au.get('n', 0):5d}  "
                             f"{au.get('mean', float('nan')):7.4f}  {au.get('sd', float('nan')):6.4f}  {au.get('min', float('nan')):6.4f}  "
                             f"{sv.get('mean', float('nan')):7.4f}  {sv.get('sd', float('nan')):6.4f}  {(r.get('early_stop') or '-')[:40]}")
    return '\n'.join(lines)


def main(a):
    cmd = a[0] if a else ''
    if cmd == 'args':
        print(' '.join(arm_overrides(a[1], a[2])))
    elif cmd == 'env':
        print(' '.join(arm_env(a[1], a[2], a[3])))
    elif cmd == 'ckcfg':
        ckcfg(a[1], a[2], a[3] if len(a) > 3 else None)
    elif cmd == 'cell':
        print(json.dumps(cell(a[1], a[2], a[3], a[4], a[5], a[6] if len(a) > 6 else None), indent=1))
    elif cmd == 'summary':
        o = a[1]; opt = dict(run=None, commit=None, cells='', steps='70004736'); meta = {}
        i = 2
        while i < len(a):
            if a[i] == '--meta':
                k, v = a[i + 1].split('=', 1); meta[k] = v
            else:
                opt[a[i].lstrip('-')] = a[i + 1]
            i += 2
        assigned = opt['cells'].split()
        cells = {}
        for c in assigned:
            arm, ep, seed = c.split(':'); j = jl(f'{o}/{arm}/ep{ep}-s{seed}/cell.json')
            cells[key(arm, ep, seed)] = j or dict(arm=arm, ep=int(ep), seed=int(seed), status='no record', present=False)
        out = dict(run=opt['run'], commit=opt['commit'], steps=int(opt['steps']), assigned=assigned, meta=meta, cells=cells,
                   note='box-local verdicts: cells run on other boxes count as missing here; merge every box with `verdict`')
        out['verdicts_box_local'] = verdicts(cells, int(opt['steps']))
        print(json.dumps(out, indent=1))
    elif cmd == 'verdict':
        files, outp = [], None
        i = 1
        while i < len(a):
            if a[i] == '--out':
                outp = a[i + 1]; i += 2
            else:
                files.append(a[i]); i += 1
        cells, dup, src, steps = {}, [], {}, set()
        load = lambda f: json.load(open(f)) if not os.path.isdir(f) else dict(  # noqa: E731
            run=f, steps=70004736, cells={key(c['arm'], c['ep'], c['seed']): c for c in (jl(x) for x in sorted(glob.glob(f'{f}/*/ep*-s*/cell.json'))) if c})
        for f in files:
            s = load(f); steps.add(int(s.get('steps', 70004736)))
            for k, r in s['cells'].items():
                if k in cells and cells[k].get('present'):
                    if r.get('present'):
                        dup.append(dict(cell=k, kept=src[k], ignored=f))
                    continue
                cells[k] = r; src[k] = f
        if len(steps) != 1:
            raise SystemExit(f'the summaries disagree on STEPS: {sorted(steps)}')
        v = verdicts(cells, steps.pop())
        out = dict(inputs=files, runs=[load(f).get('run') for f in files], duplicates=dup, cell_source=src,
                   cells=cells, verdicts=v)
        if outp:
            json.dump(out, open(outp, 'w'), indent=1)
        print(table(cells))
        for name in ('K_vs_C', 'D_vs_C'):
            x = v[name]
            print(f"{name}: {x['verdict']}  mean delta {x['mean_delta']}  (provisional on complete episodes "
                  f"{x['provisional_mean_delta_on_complete_episodes']})" + (f"  sd falls >=40 % on {x['episodes_sd_falls_40pct']} episodes" if name == 'D_vs_C' else '')
                  + (f"  missing {x['missing']}" if x['missing'] else '') + (f"  INVALID {x['invalid']}" if x['invalid'] else ''))
            for e, d in x['episodes'].items():
                print(f'   {e}: {d}')
        print('seed selection by sim_vs_ref (gain of the picked seed over the 2-seed mean, AUC):',
              {a_: s_['mean_gain'] for a_, s_ in v['report_seed_selection_by_sim_vs_ref'].items()})
        r = v['report_sim_vs_ref_ranks_seeds_like_auc']; print(f"sim_vs_ref orders the two seeds like AUC in {r['agree']} of {r['of']} (arm, episode) pairs")
        if v['missing_cells']:
            print('missing cells:', [f"{m['cell']} ({m['status']}, {m['draws']} draws)" for m in v['missing_cells']])
        if dup:
            print('duplicates (first kept):', dup)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
