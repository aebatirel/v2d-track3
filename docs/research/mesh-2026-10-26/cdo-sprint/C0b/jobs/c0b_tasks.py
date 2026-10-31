"""C0b box task lists (PREREG cdo-sprint/C0b sections 2-5, 10, 11): one shell command per line, run in parallel by
c0b_box.sh (xargs -P). Each line: cd to the results folder, run, log to logs/<stage>/<label>.log, append
'OK|FAIL <label> <sec>s' to status/<stage>.txt.
Usage: c0b_tasks.py STAGE --plan plan.json --env env.json > tasks.txt
  STAGE in obsA, obsB, derive, measure, t0, markers, params, build, fid, check, report
  c0b_tasks.py candidates --plan plan.json --env env.json        (json list of built candidates)
env.json: {"PY", "REPO", "R" (results), "IN" (inputs), "DEPTH", "KIT", "STRIDE"}
Ground truth is never an input: tracks, depth, hands, calibration and our own outputs only. library_v3 and the C0
meshes appear only in the 'report' stage (fidelity reported, never deciding), which runs after the pick is written.
"""
import json, os, shlex, sys

import numpy as np

SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup',
         'beige_cup': 'beige'}
POT_VARIANTS = ['fit', 'nostem', 'nomk', 'thick']
LID_VARIANTS = ['fit', 'nostem', 'nomk', 'thick']
LID_TABLES = ['a6b1', 'a6b2']
CUP_VARIANTS = {'g1': [], 'g0': ['--appendages', '0']}
CLAMP = (0.0015, 0.008)
MIN_MEAS = 200
REPORT_MESH = {  # reported only (PREREG 5): C0's meshes, C1's adopted beige, library_v3
    'white_pot': 'docs/research/mesh-2026-10-26/results/prim/meshes/white_pot_ep41_fit.glb',
    'white_pot_lid': 'docs/research/mesh-2026-10-26/results/prim/meshes/white_pot_lid_ep2_fit_v2.glb',
    'plastic_dish_rack': 'docs/research/mesh-2026-10-26/results/prim/meshes/plastic_dish_rack_joint_v2.glb',
    'blue_cup': 'docs/research/mesh-2026-10-26/cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb',
    'beige_cup': 'docs/research/mesh-2026-10-26/cdo-sprint/C1/T1-beige-lathe/meshes/ep11_beige_cup_sep_g1.glb'}


def q(x):
    return shlex.quote(str(x))


def wrap(stage, label, cmd, env):
    lab = label.replace('/', '__')
    log = f'logs/{stage}/{lab}.log'
    return (f'cd {q(env["R"])} && s=$(date +%s) && ( {cmd} ) > {log} 2>&1 && echo "OK {label} $(( $(date +%s) - s ))s" '
            f'>> status/{stage}.txt || echo "FAIL {label} $(( $(date +%s) - s ))s" >> status/{stage}.txt')


def py(env, script, *args, iso=True):
    return ' '.join([q(env['PY'])] + (['-I'] if iso else []) + ['-W', 'ignore', q(script)] + [q(a) for a in args])


def paths(env):
    R, REPO = env['R'], env['REPO']
    MR = f'{REPO}/docs/research/mesh-2026-10-26'
    return dict(S=f'{MR}/scripts', JOB=f'{MR}/cdo-sprint/C0b/jobs', PREP=f'{MR}/cdo-sprint/C0b/jobs/c0b_prep.py',
                A=f'{R}/pts/A', B=f'{R}/pts/B', M=f'{R}/pts/M')


def obs_file(plan, env, o, e):
    """The C0b observed points of (object, episode) that builds and fidelity use (beige: the M_sep-masked file)."""
    p = paths(env)
    if o == 'beige_cup':
        return f'{p["B"]}/ep{e}_beige_cup_sep.npz'
    return f'{p["B"]}/ep{e}_{o}.npz'


def chain(rows, t0):
    """PREREG 3.3 steps 2-4: thickness.py median of the pooled measurements if >= 200, else t0_C0b; clamp."""
    T = np.concatenate([np.load(r) for r in rows]) if rows else np.zeros(0)
    T = T[np.isfinite(T)]
    if len(T) >= MIN_MEAS:
        t, src = float(np.median(T)), 'thickness.py'
    elif t0 is not None:
        t, src = float(t0), 't0_C0b'
    else:
        return None, 'FAIL: t0_C0b not fittable'
    return float(np.clip(t, *CLAMP)), f'{src} (n={len(T)})'


def params(plan, env):
    R = env['R']
    t0j = json.load(open(f'{R}/t0_c0b.json'))
    t0 = float(np.clip(t0j['t0_m'], *CLAMP)) if t0j.get('fittable') else None
    sig = lambda f: json.load(open(f'{R}/sigma/{os.path.basename(f)[:-4]}.json'))['sigma_m']       # noqa: E731
    th = lambda f: f'{R}/thick/{os.path.basename(f)[:-4]}.npy'                                    # noqa: E731
    out = dict(t0_c0b_m=t0, t0_fittable=bool(t0j.get('fittable')), clamp_m=list(CLAMP), targets={})
    ce = plan['candidate_eps']
    for o in ('white_pot', 'white_pot_lid'):
        for e in ce[o]:
            f = obs_file(plan, env, o, e)
            t, src = chain([th(f)], t0)
            d = dict(obs=f, sigma_m=sig(f), bar_t0_m=t0, bar_t0_src='t0_C0b')
            d.update({('t_fallback_m' if o == 'white_pot' else 't_lid_m'): t, 't_src': src})
            out['targets'][f'{SHORT[o]}/ep{e}'] = d
    fr = [obs_file(plan, env, 'plastic_dish_rack', e) for e in ce['plastic_dish_rack']]
    if fr:
        t, src = chain([th(f) for f in fr], t0)
        out['targets']['rack/run'] = dict(obs=fr, t_wall_m=t, t_src=src + ' pooled over the run episodes')
    for e in ce['blue_cup']:
        f = obs_file(plan, env, 'blue_cup', e)
        t, src = chain([th(f)], t0)
        out['targets'][f'cup/ep{e}'] = dict(obs=f, sigma_m=sig(f), app_d_m=3 * sig(f), t_fallback_m=t, t_src=src)
    if len(ce['blue_cup']) > 1:
        fs = [obs_file(plan, env, 'blue_cup', e) for e in ce['blue_cup']]
        s = float(np.median([sig(f) for f in fs]))
        t, src = chain([th(f) for f in fs], t0)
        out['targets']['cup/merged'] = dict(obs=f'{paths(env)["M"]}/merged_blue_cup.npz', parts=fs, sigma_m=s, app_d_m=3 * s,
                                            t_fallback_m=t, t_src=src + ' pooled over the merged episodes',
                                            sigma_src='median of the episodes sigma')
    for e in ce['beige_cup']:
        f = obs_file(plan, env, 'beige_cup', e)
        mj = json.load(open(f'{R}/msep_ep{e}.json'))
        if not mj['qualifies']:
            out['targets'][f'beige/ep{e}'] = dict(obs=f, qualifies=False, note='M_sep: < 10 kept frames or < 20,000 points')
            continue
        t, src = chain([th(f)], t0)
        out['targets'][f'beige/ep{e}'] = dict(obs=f, qualifies=True, sigma_m=sig(f), app_d_m=3 * sig(f), t_fallback_m=t,
                                              t_src=src)
    return out


def fmt(x):
    """thickness argument; -1 = 'needed but not available' (t0_C0b not fittable): the build fails if it needs it"""
    return '-1' if x is None else f'{x:.6g}'


def lathe_args(d, extra):
    return ['--tie', '1.0', '--floor', 'base_t', '--t_fallback', fmt(d['t_fallback_m']), '--tmax', '0.008',
            '--tmin', '0.0015', '--app_d', f'{d["app_d_m"]:.6g}'] + list(extra)


def candidates(plan, env):
    R = env['R']; ce = plan['candidate_eps']
    C = []
    for e in ce['white_pot']:
        for v in POT_VARIANTS:
            C.append(dict(object='white_pot', label=f'pot/ep{e}/{v}', episode=str(e), variant=v,
                          path=f'{R}/cand/white_pot/white_pot_ep{e}_{v}.glb'))
    for e in ce['white_pot_lid']:
        for tb in LID_TABLES:
            for v in LID_VARIANTS:
                C.append(dict(object='white_pot_lid', label=f'lid/ep{e}/{tb}_{v}', episode=str(e), variant=f'{tb}_{v}',
                              path=f'{R}/cand/white_pot_lid/white_pot_lid_ep{e}_{tb}_{v}.glb'))
    for e in ce['plastic_dish_rack']:
        for v in ('full', 'nomk'):
            C.append(dict(object='plastic_dish_rack', label=f'rack/ep{e}/{v}', episode=str(e), variant=v,
                          path=f'{R}/cand/rack/plastic_dish_rack/ep{e}_{v}.glb'))
    for v in ('joint', 'joint_nomk'):
        C.append(dict(object='plastic_dish_rack', label=f'rack/joint/{v}', episode='joint', variant=v,
                      path=f'{R}/cand/rack/plastic_dish_rack/joint_{v}.glb'))
    for e in ce['blue_cup']:
        for v in CUP_VARIANTS:
            C.append(dict(object='blue_cup', label=f'cup/ep{e}/{v}', episode=str(e), variant=v,
                          path=f'{R}/cand/blue_cup/ep{e}_blue_cup_{v}.glb'))
    if len(ce['blue_cup']) > 1:
        C.append(dict(object='blue_cup', label='cup/merged/g1', episode='merged', variant='g1',
                      path=f'{R}/cand/blue_cup/merged_blue_cup_g1.glb'))
    for e in ce['beige_cup']:
        for v in CUP_VARIANTS:
            C.append(dict(object='beige_cup', label=f'beige/ep{e}/{v}', episode=str(e), variant=v,
                          path=f'{R}/cand/beige_cup/ep{e}_beige_cup_sep_{v}.glb'))
    return C


def main():
    stage = sys.argv[1]
    a = dict(zip(sys.argv[2::2], sys.argv[3::2]))
    plan = json.load(open(a['--plan'])); env = json.load(open(a['--env']))
    R, IN, DEPTH = env['R'], env['IN'], env['DEPTH']
    p = paths(env); S, PREP = p['S'], p['PREP']
    E = plan['episodes']
    out = []

    def obs_cmd(e, o, oth, dst):
        ep = E[str(e)]
        hands = f'{IN}/sweep/ep{e}/hands.npz' if ep['hands'] else '-'
        return ' '.join(['bash', q(f'{p["JOB"]}/c0b_obs.sh'), q(env['PY']), q(PREP), q(f'{S}/obs_points.py'),
                         q(f'{IN}/sweep/ep{e}/poses.npz'), q(f'{DEPTH}/ep{e}/depths_fs0.5.npy'), q(hands),
                         q(f'{IN}/calib.json'), q(o), q(oth), q(dst), q(f'{R}/guard/{os.path.basename(dst)[:-4]}.jsonl')])
    if stage == 'obsA':
        for e, ep in sorted(E.items(), key=lambda kv: int(kv[0])):
            for o in ep['objects']:
                out.append(wrap('obsA', f'{SHORT.get(o, o)}/ep{e}', obs_cmd(e, o, '-', f'{p["A"]}/ep{e}_{o}.npz'), env))
    elif stage == 'obsB':
        for e, ep in sorted(E.items(), key=lambda kv: int(kv[0])):
            for o in ep['objects']:
                oth = [x for x in ep['objects'] if x != o]
                dst = f'{p["B"]}/ep{e}_{o}.npz'
                if not oth:   # no co-object: pass B = pass A (the same command; obs_points is deterministic)
                    cmd = f'cp {q(p["A"])}/ep{e}_{o}.npz {q(dst)} && echo "single object: pass B = pass A"'
                else:
                    cmd = obs_cmd(e, o, ','.join(f'{x}={p["A"]}/ep{e}_{x}.npz' for x in oth), dst)
                out.append(wrap('obsB', f'{SHORT.get(o, o)}/ep{e}', cmd, env))
    elif stage == 'derive':
        for e in plan['candidate_eps']['beige_cup']:
            oth = ','.join(f'{x}={p["A"]}/ep{e}_{x}.npz' for x in E[str(e)]['objects'] if x != 'beige_cup')
            cmd = py(env, PREP, 'msep', f'{IN}/sweep/ep{e}/poses.npz', 'beige_cup', f'{p["A"]}/ep{e}_beige_cup.npz', oth,
                     f'{p["B"]}/ep{e}_beige_cup.npz', f'{p["B"]}/ep{e}_beige_cup_sep.npz', f'{R}/msep_ep{e}.json')
            out.append(wrap('derive', f'beige/ep{e}/msep', cmd, env))
        if len(plan['candidate_eps']['blue_cup']) > 1:
            cmd = py(env, PREP, 'merge', f'{p["M"]}/merged_blue_cup.npz',
                     *[obs_file(plan, env, 'blue_cup', e) for e in plan['candidate_eps']['blue_cup']])
            out.append(wrap('derive', 'cup/merged', cmd, env))
    elif stage == 'measure':
        # thickness rows: every public object-episode (t0_C0b) + the beige masked file; sigma: every build input
        for e, ep in sorted(E.items(), key=lambda kv: int(kv[0])):
            for o in ep['objects']:
                f = f'{p["B"]}/ep{e}_{o}.npz'
                out.append(wrap('measure', f'thick/{SHORT.get(o, o)}/ep{e}', py(env, PREP, 'thick', f, f'{R}/thick/ep{e}_{o}.json'), env))
        for e in plan['candidate_eps']['beige_cup']:
            f = obs_file(plan, env, 'beige_cup', e)
            out.append(wrap('measure', f'thick/beige/ep{e}_sep', py(env, PREP, 'thick', f, f'{R}/thick/ep{e}_beige_cup_sep.json'), env))
        targets = set()
        for o, el in plan['candidate_eps'].items():
            for e in el:
                targets.add((o, int(e)))
        for o, e in sorted(targets):
            f = obs_file(plan, env, o, e)
            slot = ','.join(E[str(e)]['slot'])
            out.append(wrap('measure', f'sigma/{SHORT[o]}/ep{e}',
                            py(env, PREP, 'sigma', f, f'{IN}/sweep/ep{e}/poses.npz', o, slot,
                               f'{R}/sigma/{os.path.basename(f)[:-4]}.json'), env))
    elif stage == 't0':
        rows = [f'{R}/thick/ep{e}_{o}.json' for e, ep in sorted(E.items(), key=lambda kv: int(kv[0])) for o in ep['objects']]
        out.append(wrap('t0', 't0', py(env, PREP, 't0', f'{R}/t0_c0b.json', *rows), env))
    elif stage == 'markers':
        for e, objs in sorted(plan['marker_objects'].items(), key=lambda kv: int(kv[0])):
            specs = [f'{o}={obs_file(plan, env, o, e)}={R}/sigma/ep{e}_{o}.json' for o in objs]
            cmd = py(env, PREP, 'markers', e, f'{IN}/sweep/ep{e}/poses.npz', ','.join(E[str(e)]['slot']),
                     f'{R}/markers/ep{e}.json', *specs)
            out.append(wrap('markers', f'ep{e}', cmd, env))
    elif stage == 'params':
        json.dump(params(plan, env), open(f'{R}/params.json', 'w'), indent=1)
        print(f'{R}/params.json'); return
    elif stage == 'build':
        P = json.load(open(f'{R}/params.json'))['targets']
        ce = plan['candidate_eps']
        for e in ce['white_pot']:
            d = P[f'pot/ep{e}']
            def one(v, d=d, e=e):
                args = ['pot', d['obs'], f'{R}/cand/white_pot/white_pot_ep{e}_{v}.glb', '--variant', v, '--c0b',
                        '--sigma', f'{d["sigma_m"]:.6g}', '--t_fallback', fmt(d['t_fallback_m']),
                        '--bar_t0', fmt(d['bar_t0_m']), '--markers_json', f'{R}/markers/ep{e}.json',
                        '--axis_cache', f'{R}/axis/ep{e}_white_pot.json']
                return py(env, f'{S}/prim_potlid.py', *args)
            rest = ' '.join(f'( {one(v)} > logs/build/pot__ep{e}__{v}.log 2>&1; echo "{v} rc=$?" ) &' for v in POT_VARIANTS[1:])
            cmd = f'{one("fit")} > logs/build/pot__ep{e}__fit.log 2>&1; echo "fit rc=$?"; {rest} wait'
            out.append(wrap('build', f'pot/ep{e}', cmd, env))
        for e in ce['white_pot_lid']:
            d = P[f'lid/ep{e}']
            for tb in LID_TABLES:
                for v in LID_VARIANTS:
                    args = ['lid', d['obs'], f'{R}/cand/white_pot_lid/white_pot_lid_ep{e}_{tb}_{v}.glb', '--variant', v,
                            '--c0b', '--sigma', f'{d["sigma_m"]:.6g}', '--t_lid', fmt(d['t_lid_m']),
                            '--bar_t0', fmt(d['bar_t0_m']), '--lid_win', tb, '--markers_json', f'{R}/markers/ep{e}.json']
                    out.append(wrap('build', f'lid/ep{e}/{tb}_{v}', py(env, f'{S}/prim_potlid.py', *args), env))
        d = P.get('rack/run')
        cmd = '' if d is None else 'PRIM_CUP_LEAN=1 ' + py(env, f'{S}/prim_rack.py', 'run', '--obs_dir', p['B'], '--out', f'{R}/cand/rack',
                                      '--episodes', ','.join(str(e) for e in ce['plastic_dish_rack']),
                                      '--t_wall', fmt(d['t_wall_m']), '--s0_min_t', '--markers_dir', f'{R}/markers')
        if d is not None:
            out.append(wrap('build', 'rack/run', cmd, env))
        for e in ce['blue_cup']:
            d = P[f'cup/ep{e}']
            for v, extra in CUP_VARIANTS.items():
                cmd = py(env, f'{S}/lathe_obs.py', d['obs'], f'{R}/cand/blue_cup/ep{e}_blue_cup_{v}.glb', *lathe_args(d, extra))
                out.append(wrap('build', f'cup/ep{e}/{v}', cmd, env))
        if 'cup/merged' in P:
            d = P['cup/merged']
            cmd = py(env, f'{S}/lathe_obs.py', d['obs'], f'{R}/cand/blue_cup/merged_blue_cup_g1.glb', *lathe_args(d, []))
            out.append(wrap('build', 'cup/merged/g1', cmd, env))
        for e in ce['beige_cup']:
            d = P[f'beige/ep{e}']
            if not d.get('qualifies'):
                continue
            for v, extra in CUP_VARIANTS.items():
                cmd = py(env, f'{S}/lathe_obs.py', d['obs'], f'{R}/cand/beige_cup/ep{e}_beige_cup_sep_{v}.glb',
                         *lathe_args(d, extra))
                out.append(wrap('build', f'beige/ep{e}/{v}', cmd, env))
    elif stage == 'candidates':
        print(json.dumps([c for c in candidates(plan, env) if os.path.exists(c['path'])], indent=1)); return
    elif stage in ('fid', 'report'):
        # obs_fidelity.py with defaults (no --icp), one mesh per process, on ALL and (reported only) on each episode
        cands = [c for c in candidates(plan, env) if os.path.exists(c['path'])]
        if stage == 'report':
            cands = []
            for o in plan['all_set']:
                cands.append(dict(object=o, label=f'{SHORT[o]}/C0ref', path=f'{env["REPO"]}/{REPORT_MESH[o]}'))
                cands.append(dict(object=o, label=f'{SHORT[o]}/library_v3', path=f'{env["REPO"]}/meshes/library_v3/{o}.glb'))
        for c in cands:
            o = c['object']
            el = plan['all_set'][o]
            sets = [('all', el)] + [(f'ep{e}', [e]) for e in el]
            for sname, es in sets:
                obs = ','.join(obs_file(plan, env, o, e) for e in es)
                lab = f'{c["label"]}@{sname}'
                cmd = py(env, f'{S}/obs_fidelity.py', obs, c['path']) + f' > {stage}/{SHORT[o]}/' + lab.replace('/', '__') + '.jsonl'
                out.append(wrap(stage, lab, cmd, env))
    elif stage == 'check':
        for c in candidates(plan, env):
            if not os.path.exists(c['path']):
                continue
            outj = f'check/{SHORT[c["object"]]}/' + c['label'].replace('/', '__') + '.json'
            out.append(wrap('check', c['label'], py(env, f'{p["JOB"]}/c0b_check.py', env['KIT'], c['path'], outj), env))
    else:
        sys.exit(f'unknown stage {stage}')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
