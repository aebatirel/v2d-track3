"""E0b box task lists (C0b PREREG section 9, 10): the C0b public task lists of ../../C0b/jobs/c0b_tasks.py on the eval
episodes. One shell command per line (run in parallel by e0b_box.sh, xargs -P); each line logs to
logs/<stage>/<label>.log and appends 'OK|FAIL <label> <sec>s' to status/<stage>.txt.
Usage: e0b_tasks.py STAGE --plan plan.json --env env.json > tasks.txt
  STAGE in obsA, obsB, derive, derive2, measure, markers, params, build, check, fref, frame, fid, report
  e0b_tasks.py candidates --plan plan.json --env env.json          (json list of built candidates)
What differs from the public task lists (and why):
  - tracks / hands are inputs/eval/ep<N>/{poses,hands}.npz (PREREG 9 (a));
  - pass A builds every tracked object of the eval episodes (co-object surfaces, M_sep); pass B, thickness and sigma
    only the targets (pot, lid, rack, blue cup, beige cup): t0_C0b is not refitted, the public value is frozen
    (inputs/t0_c0b.json, PREREG 3.3 step 3 / 9 (b));
  - beige: merged g1 over the masked points of eval 8 + 10 when both qualify (PREREG 9 table, 10); its ALL set is
    the qualifying episodes only (PREREG 9 (d));
  - frame check vs the C0b public pick (PREREG 9 (c)): 'fref' (references vs pick) -> thresholds -> 'frame'
    (eval candidates vs pick);
  - 'fid' also scores the C0b public picks on the eval points (needed by PREREG 9 (e)); 'report' (reported only):
    C0's meshes, library_v3 (+ library_v3x beige), E0's picks.
Ground truth is never an input. library_v3 / C0 / E0 meshes appear only in 'report', which runs after the pick.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'C0b', 'jobs')))
import c0b_tasks as CT  # noqa: E402
from c0b_tasks import SHORT, POT_VARIANTS, LID_VARIANTS, LID_TABLES, CUP_VARIANTS, q, wrap, py, fmt, lathe_args  # noqa: E402,F401

import numpy as np  # noqa: E402

REPORT_EXTRA = {  # reported only: E0's picks (cdo-sprint/E0/MANIFEST.json), library_v3x beige (eval 8's pack mesh)
    'white_pot': [('E0pick', 'docs/research/mesh-2026-10-26/cdo-sprint/E0/meshes/white_pot_eval3_fit.glb')],
    'white_pot_lid': [('E0pick', 'docs/research/mesh-2026-10-26/cdo-sprint/E0/meshes/white_pot_lid_eval1_t2.5_fit.glb')],
    'plastic_dish_rack': [('E0pick', 'docs/research/mesh-2026-10-26/cdo-sprint/E0/meshes/plastic_dish_rack_eval_joint_joint.glb')],
    'blue_cup': [('E0pick', 'docs/research/mesh-2026-10-26/cdo-sprint/E0/meshes/blue_cup_eval32_g1.glb')],
    'beige_cup': [('library_v3x', 'meshes/library_v3x/beige_cup.glb')]}


def paths(env):
    p = CT.paths(env)
    MR = f'{env["REPO"]}/docs/research/mesh-2026-10-26'
    p.update(EJOB=f'{MR}/cdo-sprint/E0b/jobs', EPREP=f'{MR}/cdo-sprint/E0b/jobs/e0b_prep.py',
             FC=f'{MR}/cdo-sprint/E0b/jobs/frame_check_b.py')   # C0's frame_check.py, closest_point chunked (same numbers)
    return p


obs_file = CT.obs_file


def beige_qual(plan, env):
    """eval episodes whose M_sep(own) mask qualifies (PREREG 10); None before the derive stage ran"""
    out = []
    for e in plan['candidate_eps']['beige_cup']:
        f = f'{env["R"]}/msep_ep{e}.json'
        if not os.path.exists(f):
            return None
        if json.load(open(f))['qualifies']:
            out.append(e)
    return out


def all_set(plan, env, o):
    if o == 'beige_cup':
        return beige_qual(plan, env) or []
    return plan['all_set'][o]


def targets(plan):
    return sorted({(o, int(e)) for o, el in plan['candidate_eps'].items() for e in el})


def params(plan, env):
    out = CT.params(plan, env)                       # pot, lid, rack run, blue cup (+ merged), beige per episode
    out['t0_note'] = 'public t0_C0b, frozen (inputs/t0_c0b.json); not refitted on eval (PREREG 9 (b))'
    bq = beige_qual(plan, env) or []
    if len(bq) == len(plan['candidate_eps']['beige_cup']) and len(bq) > 1:
        R = env['R']
        sig = lambda f: json.load(open(f'{R}/sigma/{os.path.basename(f)[:-4]}.json'))['sigma_m']   # noqa: E731
        th = lambda f: f'{R}/thick/{os.path.basename(f)[:-4]}.npy'                                # noqa: E731
        t0 = out['t0_c0b_m']
        fs = [obs_file(plan, env, 'beige_cup', e) for e in bq]
        s = float(np.median([sig(f) for f in fs]))
        t, src = CT.chain([th(f) for f in fs], t0)
        out['targets']['beige/merged'] = dict(obs=f'{paths(env)["M"]}/merged_beige_cup_sep.npz', parts=fs, qualifies=True,
                                              sigma_m=s, app_d_m=3 * s, t_fallback_m=t,
                                              t_src=src + ' pooled over the merged episodes',
                                              sigma_src='median of the episodes sigma')
    return out


def candidates(plan, env):
    C = CT.candidates(plan, env)
    for c in C:
        c['kind'] = 'e0b'
    bq = beige_qual(plan, env) or []
    if len(bq) == len(plan['candidate_eps']['beige_cup']) and len(bq) > 1:
        C.append(dict(object='beige_cup', label='beige/merged/g1', episode='merged', variant='g1', kind='e0b',
                      path=f'{env["R"]}/cand/beige_cup/merged_beige_cup_sep_g1.glb'))
    return C


def main():
    stage = sys.argv[1]
    a = dict(zip(sys.argv[2::2], sys.argv[3::2]))
    plan = json.load(open(a['--plan'])); env = json.load(open(a['--env']))
    R, IN, DEPTH, REPO = env['R'], env['IN'], env['DEPTH'], env['REPO']
    p = paths(env); S, PREP = p['S'], p['EPREP']
    E = plan['episodes']
    out = []

    def obs_cmd(e, o, oth, dst):
        hands = f'{IN}/eval/ep{e}/hands.npz' if E[str(e)]['hands'] else '-'
        return ' '.join(['bash', q(f'{p["JOB"]}/c0b_obs.sh'), q(env['PY']), q(PREP), q(f'{S}/obs_points.py'),
                         q(f'{IN}/eval/ep{e}/poses.npz'), q(f'{DEPTH}/ep{e}/depths_fs0.5.npy'), q(hands),
                         q(f'{IN}/calib.json'), q(o), q(oth), q(dst), q(f'{R}/guard/{os.path.basename(dst)[:-4]}.jsonl')])
    if stage == 'obsA':
        for e, ep in sorted(E.items(), key=lambda kv: int(kv[0])):
            for o in ep['objects']:
                out.append(wrap('obsA', f'{SHORT.get(o, o)}/ep{e}', obs_cmd(e, o, '-', f'{p["A"]}/ep{e}_{o}.npz'), env))
    elif stage == 'obsB':
        for o, e in targets(plan):
            oth = [x for x in E[str(e)]['objects'] if x != o]
            dst = f'{p["B"]}/ep{e}_{o}.npz'
            if not oth:
                cmd = f'cp {q(p["A"])}/ep{e}_{o}.npz {q(dst)} && echo "single object: pass B = pass A"'
            else:
                cmd = obs_cmd(e, o, ','.join(f'{x}={p["A"]}/ep{e}_{x}.npz' for x in oth), dst)
            out.append(wrap('obsB', f'{SHORT[o]}/ep{e}', cmd, env))
    elif stage == 'derive':
        for e in plan['candidate_eps']['beige_cup']:
            oth = ','.join(f'{x}={p["A"]}/ep{e}_{x}.npz' for x in E[str(e)]['objects'] if x != 'beige_cup')
            cmd = py(env, PREP, 'msep', f'{IN}/eval/ep{e}/poses.npz', 'beige_cup', f'{p["A"]}/ep{e}_beige_cup.npz', oth,
                     f'{p["B"]}/ep{e}_beige_cup.npz', f'{p["B"]}/ep{e}_beige_cup_sep.npz', f'{R}/msep_ep{e}.json')
            out.append(wrap('derive', f'beige/ep{e}/msep', cmd, env))
        if len(plan['candidate_eps']['blue_cup']) > 1:
            cmd = py(env, PREP, 'merge', f'{p["M"]}/merged_blue_cup.npz',
                     *[obs_file(plan, env, 'blue_cup', e) for e in plan['candidate_eps']['blue_cup']])
            out.append(wrap('derive', 'cup/merged', cmd, env))
    elif stage == 'derive2':     # merged beige (masked points of every eval episode), only if all of them qualify
        bq = beige_qual(plan, env) or []
        if len(bq) == len(plan['candidate_eps']['beige_cup']) and len(bq) > 1:
            cmd = py(env, PREP, 'merge', f'{p["M"]}/merged_beige_cup_sep.npz', *[obs_file(plan, env, 'beige_cup', e) for e in bq])
            out.append(wrap('derive2', 'beige/merged', cmd, env))
    elif stage == 'measure':     # thickness rows + sigma of every build input (targets only; t0 is frozen)
        for o, e in targets(plan):
            f = obs_file(plan, env, o, e)
            b = os.path.basename(f)[:-4]
            out.append(wrap('measure', f'thick/{SHORT[o]}/ep{e}', py(env, PREP, 'thick', f, f'{R}/thick/{b}.json'), env))
            out.append(wrap('measure', f'sigma/{SHORT[o]}/ep{e}',
                            py(env, PREP, 'sigma', f, f'{IN}/eval/ep{e}/poses.npz', o, ','.join(E[str(e)]['slot']),
                               f'{R}/sigma/{b}.json'), env))
    elif stage == 'markers':
        for e, objs in sorted(plan['marker_objects'].items(), key=lambda kv: int(kv[0])):
            specs = [f'{o}={obs_file(plan, env, o, e)}={R}/sigma/ep{e}_{o}.json' for o in objs]
            cmd = py(env, PREP, 'markers', e, f'{IN}/eval/ep{e}/poses.npz', ','.join(E[str(e)]['slot']),
                     f'{R}/markers/ep{e}.json', *specs)
            out.append(wrap('markers', f'ep{e}', cmd, env))
    elif stage == 'params':
        json.dump(params(plan, env), open(f'{R}/params.json', 'w'), indent=1)
        print(f'{R}/params.json'); return
    elif stage == 'build':
        # the public build lines (c0b_tasks build stage, same arguments) + the merged beige g1
        import contextlib, io
        buf = io.StringIO()
        argv = sys.argv
        try:
            sys.argv = ['c0b_tasks.py', 'build', '--plan', a['--plan'], '--env', a['--env']]
            with contextlib.redirect_stdout(buf):
                CT.main()
        finally:
            sys.argv = argv
        out = [l for l in buf.getvalue().split('\n') if l.strip()]
        P = json.load(open(f'{R}/params.json'))['targets']
        if 'beige/merged' in P:
            d = P['beige/merged']
            cmd = py(env, f'{S}/lathe_obs.py', d['obs'], f'{R}/cand/beige_cup/merged_beige_cup_sep_g1.glb', *lathe_args(d, []))
            out.append(wrap('build', 'beige/merged/g1', cmd, env))
    elif stage == 'candidates':
        print(json.dumps([c for c in candidates(plan, env) if os.path.exists(c['path'])], indent=1)); return
    elif stage == 'check':
        for c in candidates(plan, env):
            if os.path.exists(c['path']):
                outj = f'check/{SHORT[c["object"]]}/' + c['label'].replace('/', '__') + '.json'
                out.append(wrap('check', c['label'], py(env, f'{p["JOB"]}/c0b_check.py', env['KIT'], c['path'], outj), env))
    elif stage == 'fref':        # frame-check references vs the C0b public pick (thresholds; public meshes only)
        for o, fr in plan['frame_refs'].items():
            pick = f'{REPO}/{fr["pick_repo_path"]}'
            for r in fr['references']:
                outj = f'fref/{SHORT[o]}/' + r['label'].replace('/', '__') + '.json'
                cmd = py(env, p['FC'], env['KIT'], outj, f'{o}:{IN}/{r["input"]}:{pick}')
                out.append(wrap('fref', r['label'], cmd, env))
    elif stage == 'frame':       # every eval candidate vs the C0b public pick of its object
        for c in candidates(plan, env):
            o = c['object']
            if o not in plan['frame_refs'] or not os.path.exists(c['path']):
                continue
            pick = f'{REPO}/{plan["frame_refs"][o]["pick_repo_path"]}'
            outj = f'frame/{SHORT[o]}/' + c['label'].replace('/', '__') + '.json'
            out.append(wrap('frame', c['label'], py(env, p['FC'], env['KIT'], outj, f'{o}:{c["path"]}:{pick}'), env))
    elif stage in ('fid', 'report'):
        # obs_fidelity.py with defaults (no --icp), one mesh per process, on ALL and (reported only) each episode
        if stage == 'fid':
            cands = [c for c in candidates(plan, env) if os.path.exists(c['path'])]
            for o, rp in plan['report_meshes']['c0b_public'].items():      # PREREG 9 (e) needs these
                cands.append(dict(object=o, label=f'{SHORT[o]}/C0bpub', path=f'{REPO}/{rp}', kind='c0b_public'))
        else:
            cands = []
            for o in plan['all_set']:
                cands.append(dict(object=o, label=f'{SHORT[o]}/C0ref', path=f'{REPO}/{CT.REPORT_MESH[o]}'))
                cands.append(dict(object=o, label=f'{SHORT[o]}/library_v3', path=f'{REPO}/meshes/library_v3/{o}.glb'))
                for k, rp in REPORT_EXTRA.get(o, []):
                    cands.append(dict(object=o, label=f'{SHORT[o]}/{k}', path=f'{REPO}/{rp}'))
        for c in cands:
            o = c['object']
            el = all_set(plan, env, o)
            if not el:
                continue
            for sname, es in [('all', el)] + [(f'ep{e}', [e]) for e in el]:
                obs = ','.join(obs_file(plan, env, o, e) for e in es)
                lab = f'{c["label"]}@{sname}'
                cmd = py(env, f'{S}/obs_fidelity.py', obs, c['path']) + f' > {stage}/{SHORT[o]}/' + lab.replace('/', '__') + '.jsonl'
                out.append(wrap(stage, lab, cmd, env))
    else:
        sys.exit(f'unknown stage {stage}')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
