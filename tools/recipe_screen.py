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
  S  (2026-10-31, physics-solver.md section 9) C's recipe exactly (no override, no env) on the PHYSICS-SOLVED references
     that G3 trained on (store run 20261030-psolverl-04301a2: G2 refs/psolve2 for ep2 / ep12, G1 refs/psolve for ep18 /
     ep24; ref_ps.parquet). Only the reference differs from C; the S_vs_C verdict compares S with the screen's C cells.
     The registered md5 of every reference (REF_MD5) was measured on the CPU from the store on 31 Oct: the solved files
     equal G3's training copies (psolverl refs/glockt), their object columns equal the physS1 references' (the solver
     edits only robot_<side>_wrist_position / _wrist_wxyz / _finger_joints), and ep18's equals its input (G1 edited 0 frames).
Subcommands:
  args ARM STEPS                 Hydra overrides of the arm (one line)
  env ARM SEED DR                environment assignments of the arm's TRAINING process (one line; empty for C / K / S)
  ref ARM                        the arm's reference set: base (the physS1 references of C / K / D) or solved (S)
  solved_sub EP                  the store sub-folder of the episode's solved reference (refs/psolve2/ep2 ...)
  refmd5 SET EP                  the registered md5 of the episode's reference of that set (base | solved)
  ckcfg CKPT OUT.json [RUN]      the checkpoint's resolved settings (needs safetensors: FlashCHORD's venv)
  cell ARM EP SEED CELL_DIR RUN [STATUS]   one cell's record (JSON on stdout)
  summary RESULTS_DIR [--run ID] [--commit SHA] [--cells "arm:ep:seed ..."] [--meta K=V ...]   the box summary
  verdict SUMMARY.json|RESULTS_DIR ... [--out MERGED.json] [--ref-md5 MD5.json]   merge box summaries (or a box's
                                 results/recipe_screen directory: its cell.json files) and compute the pre-registered
                                 verdicts (K_vs_C, D_vs_C: section 8; S_vs_C: section 9; V_vs_C: section 10). --ref-md5 replaces REF_MD5
                                 ({"base": {"2": md5, ...}, "solved": {...}}; the CPU dry run's stub files only)
No ground truth is read here: AUC values come from the job's scoring (pipeline/score_registered.py, after inference)."""
import glob, hashlib, json, math, os, re, sys

WORLDS, UPC = 4096, 8.0                      # experiment=sharpa_flash_sac: scene.world_count, updates_per_collection
THRESHOLDS = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]
VOC = [1.0, 0.75, 0.5, 0.25, 0.1, 0.05, 0.025, 0.01, 0.0, 0.0, 0.0]   # tracking_250m_mixed_reset(_v2d) stage scales
LR_C = dict(learning_rate_initial=3e-4, learning_rate_peak=3e-4, learning_rate_end=1.5e-4, learning_rate_schedule_updates=None)
K_LR = dict(learning_rate_initial=6e-4, learning_rate_peak=6e-4, learning_rate_end=3e-5)
K_CURR = 2.0
ARMS, EPS, SEEDS = ('C', 'K', 'D'), (2, 12, 18, 24), (42, 43)   # the section-8 screen (its verdicts use these arms only)
S_ARM = 'S'                                  # section 9: C's recipe on the physics-solved references (verdict S_vs_C)
V_ARM = 'V'                                  # section 10: C's recipe + the actor sees object body velocity (verdict V_vs_C)
V_OVERRIDE = 'observation.object_body_velocity.enabled=true'
REF_SET = dict(C='base', K='base', D='base', S='solved', V='base')
REF_TREE = dict(base='glockt', solved='screenS')    # the job's task trees: $CROOT/refs/<tree>/ep<N>/<hive>/ref_gl_ilc.parquet
SOLVED_SUB = {2: 'refs/psolve2/ep2', 12: 'refs/psolve2/ep12', 18: 'refs/psolve/ep18', 24: 'refs/psolve/ep24'}  # G3's choice
# Registered reference files (md5 of the parquet the training reads), measured on the CPU from the store, 31 Oct 2026:
#   base   runs/20261030-physS1-6a814df/refs/glockt/ep<N>/processed/.../ref_gl_ilc.parquet (the screen's C / K / D; also
#          what both screen boxes recorded at 12:50 UTC: b4807f41 96ddc1ca f0f14155 699fe426)
#   solved runs/20261030-psolverl-04301a2/<SOLVED_SUB>/processed/.../ref_ps.parquet (= that run's refs/glockt copy G3 trained on)
REF_MD5 = dict(base={2: 'b4807f41fcf4b0b69eb8b27098d5bd80', 12: '96ddc1ca6d19e8e5321b4ef9c89c34bb',
                     18: 'f0f14155f35c5a2970de48e1a88aa23a', 24: '699fe4266a0a965aaf4472a1bfcc8828'},
               solved={2: '336917e37399fbc43cc2ef124adfc487', 12: '6e4c9448ac7e81da59314cc898c1e8a4',
                       18: 'f0f14155f35c5a2970de48e1a88aa23a', 24: '7edd70e352dd31a0db11c89938d12d10'})
MIN_DRAWS = 8                                # a cell counts as present iff >= 8 of its NREP (10) draws were scored
TOL = 1e-9                                   # rule bounds are inclusive as written (>= 0.03 etc.), up to float rounding


def total_updates(steps):
    return int((int(steps) // WORLDS) * UPC)


def k_thresholds():
    return [int(x * K_CURR) for x in THRESHOLDS]


def arm_overrides(arm, steps):
    if arm in ('C', 'D', 'S'):
        return []
    if arm == V_ARM:
        return [V_OVERRIDE]
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
    if arm in ('C', 'K', 'S', V_ARM):
        return []
    raise SystemExit(f'unknown arm {arm!r}')


def ref_set(arm):
    if arm not in REF_SET:
        raise SystemExit(f'unknown arm {arm!r}')
    return REF_SET[arm]


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
             task_parquet=str(c.get('task', {}).get('parquet')),
             actor_object_velocity=(((c.get('env') or {}).get('observation') or c.get('observation') or {})
                                    .get('object_body_velocity') or {}).get('enabled'),
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
    rec = dict(arm=arm, ep=int(ep), seed=int(seed), status=st, ref_set=REF_SET.get(arm), checkpoint=os.path.basename(ck) if ck else None,
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
    if rec['arm'] == V_ARM and c.get('actor_object_velocity') is not True:      # section 10: V must carry the override
        bad.append(f"actor object velocity {c.get('actor_object_velocity')} in a V checkpoint config (must be True)")
    elif rec['arm'] != V_ARM and c.get('actor_object_velocity'):                  # (older C/K/D/S records lack the field)
        bad.append(f"actor object velocity on in a {rec['arm']} checkpoint config")
    f = c.get('fdr', {})
    if (f.get('force_closure_enabled'), f.get('force_closure_weight'), f.get('wrench_weight'), f.get('unintended_weight')) != (True, 6, 3, -2):
        bad.append(f'FDR settings {f}')
    return bad


# ---------------------------------------------------------------------------------------------- verdicts
def key(arm, ep, seed):
    return f'{arm}/ep{ep}-s{seed}'


def verdicts(cells, steps, ref_md5=None, refs=None):
    """cells: {key: record}. The pre-registered rules (physics-solver.md section 8: K_vs_C, D_vs_C; section 9: S_vs_C);
    a missing cell -> INCOMPLETE. ref_md5: the registered reference md5s (default REF_MD5); refs: the boxes' reference
    records ({run: summary['refs']}), reported only."""
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
        md5 = {r['ref_md5'] for k, r in present.items() if r['ep'] == e and r['arm'] in ARMS + (V_ARM,)}   # (S: its own set)
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
    out['S_vs_C'] = s_vs_c(cells, present, invalid, auc_m, sd_m, ref_md5 or REF_MD5, refs)
    out['V_vs_C'] = v_vs_c(cells, present, invalid, auc_m, sd_m, ref_md5 or REF_MD5)
    return out


def v_vs_c(cells, present, invalid, auc_m, sd_m, exp):
    """Section 10's fixed rule: V (the actor sees object body velocity) vs the screen's C cells, both on the physS1 references."""
    pair = ('C', V_ARM)
    m_ = [dict(cell=key(a, e, s), status=(cells.get(key(a, e, s)) or {}).get('status', 'not in any summary'),
               draws=((cells.get(key(a, e, s)) or {}).get('auc') or {}).get('n', 0))
          for e in EPS for s in SEEDS for a in pair if key(a, e, s) not in present]
    inv = {k: list(v) for k, v in invalid.items() if k.startswith('ep') or k.split('/')[0] in pair}
    for e in EPS:
        for s in SEEDS:
            r = present.get(key(V_ARM, e, s))
            if r and r.get('ref_md5') != exp['base'][e]:
                inv.setdefault(key(V_ARM, e, s), []).append(f"reference md5 {r.get('ref_md5')} is not the registered base reference {exp['base'][e]}")
    r4 = lambda x: None if x is None else round(x, 4)  # noqa: E731
    one = lambda r: None if not r else dict(auc=r['auc']['mean'], auc_sd=r['auc']['sd'], auc_worst=r['auc']['min'], draws=r['auc']['n'],  # noqa: E731
                                            sim_vs_ref=(r.get('sim_vs_ref') or {}).get('mean'), checkpoint_steps=r.get('checkpoint_steps'),
                                            early_stop=r.get('early_stop'), notes=r.get('notes'))
    per = {}
    for e in EPS:
        c, v_ = auc_m('C', e), auc_m(V_ARM, e)
        per[f'ep{e}'] = dict(C=r4(c), V=r4(v_), delta=None if c is None or v_ is None else r4(v_ - c),
                             draw_sd_C=r4(sd_m('C', e)), draw_sd_V=r4(sd_m(V_ARM, e)),
                             seeds={f's{sd}': {a: one(present.get(key(a, e, sd))) for a in pair} for sd in SEEDS})
    ds = [(auc_m(V_ARM, e) - auc_m('C', e)) for e in EPS if auc_m(V_ARM, e) is not None and auc_m('C', e) is not None]
    rule = ('delta(ep) = seed-mean AUC(V) - seed-mean AUC(C) over seeds 42 / 43; signal iff the mean of delta over episodes '
            '2 / 12 / 18 / 24 >= +0.03 and no delta(ep) <= -0.05; harm iff that mean <= -0.03 or any delta(ep) <= -0.10; '
            'otherwise inconclusive; any missing V or C cell -> INCOMPLETE')
    if inv:
        v = 'INVALID'
    elif m_:
        v = 'INCOMPLETE'
    else:
        mu, lo = sum(ds) / len(ds), min(ds)             # TOL: a bound hit exactly is not lost to float rounding
        v = 'signal' if mu >= 0.03 - TOL and lo > -0.05 + TOL else 'harm' if mu <= -0.03 + TOL or lo <= -0.10 + TOL else 'inconclusive'
    act = ('report to the owner and the pack-10 session; adding V to pack 10 is a separate owner decision (cost stated)'
           if v == 'signal' else 'V is not used' if v in ('harm', 'inconclusive') else 'no verdict')
    return dict(rule=rule, verdict=v, action=act, missing=[x['cell'] for x in m_], missing_detail=m_, invalid=inv,
                mean_delta=None if m_ or not ds else r4(sum(ds) / len(ds)), min_delta=None if m_ or not ds else r4(min(ds)),
                provisional_mean_delta_on_complete_episodes=r4(sum(ds) / len(ds)) if ds else None, episodes=per)


def s_vs_c(cells, present, invalid, auc_m, sd_m, exp, refs=None):
    """Section 9's fixed rule: S (solved references) vs the screen's C cells, both C's recipe."""
    pair = ('C', S_ARM)
    m_ = [dict(cell=key(a, e, s), status=(cells.get(key(a, e, s)) or {}).get('status', 'not in any summary'),
               draws=((cells.get(key(a, e, s)) or {}).get('auc') or {}).get('n', 0))
          for e in EPS for s in SEEDS for a in pair if key(a, e, s) not in present]
    inv = {k: list(v) for k, v in invalid.items() if k.split('/')[0] in pair}     # config problems: S must carry C's config
    for e in EPS:
        sm = sorted({str(present[key(S_ARM, e, s)].get('ref_md5')) for s in SEEDS if key(S_ARM, e, s) in present})
        if len(sm) > 1:
            inv[f'S_ep{e}'] = [f'S cells of ep{e} trained on different reference files: {sm}']
        for s in SEEDS:
            for a in pair:
                r = present.get(key(a, e, s))
                if not r:
                    continue
                want = exp[REF_SET[a]][e]
                if r.get('ref_md5') != want:
                    inv.setdefault(key(a, e, s), []).append(f"reference md5 {r.get('ref_md5')} is not the registered {REF_SET[a]} reference {want}")
                tp = (r.get('config_check') or {}).get('task_parquet')   # recorded by ckcfg since arm S (absent in older cells)
                if tp and tp != 'None' and f'/refs/{REF_TREE[REF_SET[a]]}/ep{e}/' not in tp:
                    inv.setdefault(key(a, e, s), []).append(f'trained on {tp}, not on refs/{REF_TREE[REF_SET[a]]}/ep{e}')
    r4 = lambda x: None if x is None else round(x, 4)  # noqa: E731
    one = lambda r: None if not r else dict(auc=r['auc']['mean'], auc_sd=r['auc']['sd'], auc_worst=r['auc']['min'], draws=r['auc']['n'],  # noqa: E731
                                            sim_vs_ref=(r.get('sim_vs_ref') or {}).get('mean'), checkpoint_steps=r.get('checkpoint_steps'),
                                            early_stop=r.get('early_stop'))
    per = {}
    for e in EPS:
        c, s_ = auc_m('C', e), auc_m(S_ARM, e)
        per[f'ep{e}'] = dict(C=r4(c), S=r4(s_), delta=None if c is None or s_ is None else r4(s_ - c),
                             draw_sd_C=r4(sd_m('C', e)), draw_sd_S=r4(sd_m(S_ARM, e)),
                             seeds={f's{sd}': {a: one(present.get(key(a, e, sd))) for a in pair} for sd in SEEDS})
    ds = [(auc_m(S_ARM, e) - auc_m('C', e)) for e in EPS if auc_m(S_ARM, e) is not None and auc_m('C', e) is not None]
    rule = ('delta(ep) = seed-mean AUC(S) - seed-mean AUC(C) over seeds 42 / 43; signal iff the mean of delta over episodes '
            '2 / 12 / 18 / 24 >= +0.03 and no delta(ep) <= -0.05; otherwise no signal; any missing S or C cell -> INCOMPLETE '
            '(not a verdict: eval solving does not start)')
    if inv:
        v = 'INVALID'
    elif m_:
        v = 'INCOMPLETE'
    else:
        mu, lo = sum(ds) / len(ds), min(ds)             # TOL: a bound hit exactly is not lost to float rounding
        v = 'signal' if mu >= 0.03 - TOL and lo > -0.05 + TOL else 'no signal'
    act = ('eval solving starts (owner pre-approval, physics-solver.md section 9); pack 10 swap rule decides what is packed'
           if v == 'signal' else 'stop: solved references are not used for eval')
    rep = {}
    for run, rr in (refs or {}).items():                 # the boxes' own records (S box: solver input vs C's reference)
        for e in EPS:
            b, s_ = (rr or {}).get(f'ep{e}') or {}, (rr or {}).get(f'S_ep{e}') or {}
            if s_:
                rep.setdefault(f'ep{e}', []).append(dict(run=run, solved_md5=s_.get('md5'), solved_src=s_.get('src'),
                                                         solver_input_md5=s_.get('in_md5'), base_md5_on_box=b.get('md5'),
                                                         solver_input_is_registered_base=s_.get('in_md5') == exp['base'][e]))
    return dict(rule=rule, verdict=v, action=act, missing=[x['cell'] for x in m_], missing_detail=m_, invalid=inv,
                mean_delta=None if m_ or not ds else r4(sum(ds) / len(ds)), min_delta=None if m_ or not ds else r4(min(ds)),
                provisional_mean_delta_on_complete_episodes=r4(sum(ds) / len(ds)) if ds else None, episodes=per,
                registered_ref_md5={k: {str(e): m for e, m in v_.items()} for k, v_ in exp.items()}, box_reference_records=rep)


def table(cells):
    lines = ['cell          status   ckpt   draws  AUC mean   sd     worst   svr mean  sd     ES stop']
    arms = ARMS + tuple(x for x in (S_ARM, V_ARM) if any(k.startswith(x + '/') for k in cells))   # S / V rows only when they exist
    for e in EPS:
        for s in SEEDS:
            for a in arms:
                r = cells.get(key(a, e, s))
                if not r:
                    lines.append(f'{key(a, e, s):13s} (none)'); continue
                au, sv = r.get('auc') or {}, r.get('sim_vs_ref') or {}
                lines.append(f"{key(a, e, s):13s} {r['status'][:8]:8s} {(r.get('checkpoint_steps') or 0) / 1e6:4.0f}M  {au.get('n', 0):5d}  "
                             f"{au.get('mean', float('nan')):7.4f}  {au.get('sd', float('nan')):6.4f}  {au.get('min', float('nan')):6.4f}  "
                             f"{sv.get('mean', float('nan')):7.4f}  {sv.get('sd', float('nan')):6.4f}  {(r.get('early_stop') or '-')[:40]}")
    return '\n'.join(lines)


def ref_records(o):
    """The box's reference records ($O/refs/<name>.md5 / .hive / .src / .in_md5 / .zero_score.txt; name = ep<N> for the
    physS1 references, S_ep<N> for the solved ones), for the summary."""
    out = {}
    for f in sorted(glob.glob(f'{o}/refs/*.md5')):
        n = os.path.basename(f)[:-4]; rec = dict(md5=open(f).read().strip())
        for x in ('hive', 'src', 'in_md5'):
            if os.path.exists(f'{o}/refs/{n}.{x}'):
                rec[x] = open(f'{o}/refs/{n}.{x}').read().strip()
        if os.path.exists(f'{o}/refs/{n}.zero_score.txt'):
            rec['zero_action'] = [l.strip() for l in open(f'{o}/refs/{n}.zero_score.txt', errors='replace') if 'zero_action' in l][:1]
        out[n] = rec
    return out


def load_md5(path):
    d = json.load(open(path))
    return {k: {int(e): m for e, m in d[k].items()} for k in ('base', 'solved')}


def main(a):
    cmd = a[0] if a else ''
    if cmd == 'args':
        print(' '.join(arm_overrides(a[1], a[2])))
    elif cmd == 'env':
        print(' '.join(arm_env(a[1], a[2], a[3])))
    elif cmd == 'ref':
        print(ref_set(a[1]))
    elif cmd == 'solved_sub':
        if int(a[1]) not in SOLVED_SUB:
            raise SystemExit(f'no solved reference registered for ep{a[1]}')
        print(SOLVED_SUB[int(a[1])])
    elif cmd == 'refmd5':
        print(REF_MD5[a[1]][int(a[2])])
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
                   refs=ref_records(o),
                   note='box-local verdicts: cells run on other boxes count as missing here; merge every box with `verdict`')
        out['verdicts_box_local'] = verdicts(cells, int(opt['steps']), refs={opt['run']: out['refs']})
        print(json.dumps(out, indent=1))
    elif cmd == 'verdict':
        files, outp, md5f = [], None, None
        i = 1
        while i < len(a):
            if a[i] == '--out':
                outp = a[i + 1]; i += 2
            elif a[i] == '--ref-md5':
                md5f = a[i + 1]; i += 2
            else:
                files.append(a[i]); i += 1
        cells, dup, src, steps, refs = {}, [], {}, set(), {}
        load = lambda f: json.load(open(f)) if not os.path.isdir(f) else dict(  # noqa: E731
            run=f, steps=70004736, cells={key(c['arm'], c['ep'], c['seed']): c for c in (jl(x) for x in sorted(glob.glob(f'{f}/*/ep*-s*/cell.json'))) if c})
        for f in files:
            s = load(f); steps.add(int(s.get('steps', 70004736)))
            if s.get('refs'):
                refs[s.get('run') or f] = s['refs']
            for k, r in s['cells'].items():
                if k in cells and cells[k].get('present'):
                    if r.get('present'):
                        dup.append(dict(cell=k, kept=src[k], ignored=f))
                    continue
                cells[k] = r; src[k] = f
        if len(steps) != 1:
            raise SystemExit(f'the summaries disagree on STEPS: {sorted(steps)}')
        v = verdicts(cells, steps.pop(), ref_md5=load_md5(md5f) if md5f else None, refs=refs)
        out = dict(inputs=files, runs=[load(f).get('run') for f in files], duplicates=dup, cell_source=src,
                   ref_md5_file=md5f, cells=cells, verdicts=v)
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
        x = v['S_vs_C']
        print(f"S_vs_C: {x['verdict']}  mean delta {x['mean_delta']}  min delta {x['min_delta']}  (provisional on complete episodes "
              f"{x['provisional_mean_delta_on_complete_episodes']})" + (f"  missing {x['missing']}" if x['missing'] else '')
              + (f"  INVALID {x['invalid']}" if x['invalid'] else '') + f"  -> {x['action']}")
        for e, d in x['episodes'].items():
            print(f"   {e}: C {d['C']} S {d['S']} delta {d['delta']} draw sd C {d['draw_sd_C']} S {d['draw_sd_S']}  "
                  + '  '.join(f"{sd}: C {(q['C'] or {}).get('auc')} @{(q['C'] or {}).get('checkpoint_steps')} S {(q['S'] or {}).get('auc')} @{(q['S'] or {}).get('checkpoint_steps')}"
                              for sd, q in d['seeds'].items()))
        x = v['V_vs_C']
        print(f"V_vs_C: {x['verdict']}  mean delta {x['mean_delta']}  min delta {x['min_delta']}  (provisional on complete episodes "
              f"{x['provisional_mean_delta_on_complete_episodes']})" + (f"  missing {x['missing']}" if x['missing'] else '')
              + (f"  INVALID {x['invalid']}" if x['invalid'] else '') + f"  -> {x['action']}")
        for e, d in x['episodes'].items():
            print(f"   {e}: C {d['C']} V {d['V']} delta {d['delta']} draw sd C {d['draw_sd_C']} V {d['draw_sd_V']}  "
                  + '  '.join(f"{sd}: C {(q['C'] or {}).get('auc')} @{(q['C'] or {}).get('checkpoint_steps')} V {(q['V'] or {}).get('auc')} @{(q['V'] or {}).get('checkpoint_steps')}"
                              for sd, q in d['seeds'].items()))
        if dup:
            print('duplicates (first kept):', dup)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
