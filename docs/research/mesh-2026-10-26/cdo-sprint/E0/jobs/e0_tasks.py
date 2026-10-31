"""E0 task lists: one shell command per line, run in parallel by e0_box.sh (xargs -P). Every command is the public
command of the C0 methods (docs/research/mesh-2026-10-26: prep_obs.sh, results/prim/potlid/run_fit.sh, the clean-up
round's lid and rack commands, lathe_obs.py defaults = the 'g1' lathe; PREREG.md section 2) with eval paths.
Each line: cd to the run folder, run, log to logs/<stage>/<label>.log, append 'OK|FAIL <label> <sec>s' to status/<stage>.txt.
Usage: e0_tasks.py STAGE --plan plan.json --env env.json > tasks.txt     STAGE in hands, obs, merge, build, fid, check
       e0_tasks.py candidates --plan plan.json --env env.json              (json list of built candidates + references)
env.json: {"PY", "MPPY", "REPO", "CODE" (jobs/frozen: the public scripts as of commit 2971a10), "R" (results),
          "IN" (inputs), "DEPTH", "KIT", "STRIDE", "EPS"}
"""
import glob, json, os, shlex, sys

OBJ_SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup'}
C0_MESH = {  # C0 MANIFEST.json swaps (repo paths); diagnostics only, never a candidate
    'white_pot': 'docs/research/mesh-2026-10-26/results/prim/meshes/white_pot_ep41_fit.glb',
    'white_pot_lid': 'docs/research/mesh-2026-10-26/results/prim/meshes/white_pot_lid_ep2_fit_v2.glb',
    'plastic_dish_rack': 'docs/research/mesh-2026-10-26/results/prim/meshes/plastic_dish_rack_joint_v2.glb',
    'blue_cup': 'docs/research/mesh-2026-10-26/cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb'}
POT_VARIANTS = ['fit', 'nostem', 'tsdf', 'thick']          # results/prim/potlid/run_fit.sh
LID_VARIANTS = ['fit', 'tsdf']                             # clean-up round (work log 2026-10-27), PRIM_T_LID=0.0025
CUP_VARIANTS = {'g1': [], 'g0': ['--appendages', '0']}     # lathe_obs.py defaults (g1) and body only (g0)


def q(x):
    return shlex.quote(str(x))


def wrap(stage, label, cmd, env):
    lab = label.replace('/', '__')
    log = f'logs/{stage}/{lab}.log'
    return (f'cd {q(env["R"])} && s=$(date +%s) && ( {cmd} ) > {log} 2>&1 && echo "OK {label} $(( $(date +%s) - s ))s" '
            f'>> status/{stage}.txt || echo "FAIL {label} $(( $(date +%s) - s ))s" >> status/{stage}.txt')


def py(env, script, *args):
    return ' '.join([q(env['PY']), '-I', '-W', 'ignore', q(script)] + [q(a) for a in args])


def main():
    stage = sys.argv[1]
    a = dict(zip(sys.argv[2::2], sys.argv[3::2]))
    plan = json.load(open(a['--plan'])); env = json.load(open(a['--env']))
    REPO, R, IN, DEPTH = env['REPO'], env['R'], env['IN'], env['DEPTH']
    S = f'{env["CODE"]}/docs/research/mesh-2026-10-26/scripts'; JOB = f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/E0/jobs'
    LIB = f'{REPO}/meshes/library_v3'
    by_obj = plan['episodes_by_object']
    only = set(int(e) for e in env.get('EPS', '').split()) if env.get('EPS') else None
    by_obj = {o: [e for e in v if only is None or e in only] for o, v in by_obj.items()}
    eps = sorted({e for v in by_obj.values() for e in v})
    out = []
    if stage == 'hands':
        # pipeline_ep.sh step 2 (how the public G1 refs hands.npz were made): hands_mp.py on the cam_a video, eval split
        for e in eps:
            cmd = ' '.join([q(env['MPPY']), '-I', q(f'{env["CODE"]}/pipeline/hands_mp.py'), '--ep', str(e), '--split', 'eval',
                            '--t3', q(IN), '--depth', q(f'{DEPTH}/ep{e}/depths_fs0.5.npy'),
                            '--poses', q(f'{IN}/eval/ep{e}/poses.npz'), '--video_a', q(f'{IN}/eval/ep{e}_a.mp4'),
                            '--out', q(f'{R}/hands/ep{e}')])
            out.append(wrap('hands', f'ep{e}', cmd, env))
    elif stage == 'obs':
        # prep_obs.sh: obs_points.py defaults (stride 2), --hands when the episode has hands, --others = the
        # episode's other tracked objects with their library_v3 meshes, --roi = library_v3 mesh of the object
        for o, el in by_obj.items():
            for e in el:
                objs = plan['episodes'][str(e)]['objects']
                oth = ','.join(f'{x}={LIB}/{x}.glb' for x in objs if x != o)
                hands = f'{R}/hands/ep{e}/hands.npz'
                args = ['--poses', f'{IN}/eval/ep{e}/poses.npz', '--depth', f'{DEPTH}/ep{e}/depths_fs0.5.npy',
                        '--calib', f'{IN}/calib.json', '--obj', o, '--roi', f'{LIB}/{o}.glb']
                if oth:
                    args += ['--others', oth]
                args += ['--out', f'{R}/obs/ep{e}_{o}.npz']
                if str(env.get('STRIDE', '2')) != '2':
                    args += ['--stride', str(env['STRIDE'])]          # dry run only (DRY flag in the run record)
                cmd = f'H=""; [ -s {q(hands)} ] && H="--hands {hands}"; ' + py(env, f'{S}/obs_points.py', *args).replace(
                    q(f'{IN}/eval/ep{e}/poses.npz'), q(f'{IN}/eval/ep{e}/poses.npz') + ' $H', 1)
                out.append(wrap('obs', f'{OBJ_SHORT[o]}/ep{e}', cmd, env))
    elif stage == 'build':
        if by_obj.get('white_pot'):
            for e in by_obj['white_pot']:
                f = f'{R}/obs/ep{e}_white_pot.npz'
                one = lambda v: py(env, f'{S}/prim_potlid.py', 'pot', f, f'{R}/cand/white_pot/white_pot_ep{e}_{v}.glb',
                                   '--variant', v, '--lib', f'{LIB}/white_pot.glb', '--axis_cache', f'{R}/axis/ep{e}_white_pot.json')
                # fit first (writes the episode's axis cache, as run_fit.sh did), then the three others reuse it
                rest = ' '.join(f'( {one(v)} > logs/build/pot__ep{e}__{v}.log 2>&1; echo "{v} rc=$?" ) &' for v in POT_VARIANTS[1:])
                cmd = f'{one("fit")}; echo "fit rc=$?"; {rest} wait'
                out.append(wrap('build', f'pot/ep{e}', cmd, env))
        for e in by_obj.get('white_pot_lid', []):
            for v in LID_VARIANTS:
                cmd = 'PRIM_T_LID=0.0025 ' + py(env, f'{S}/prim_potlid.py', 'lid', f'{R}/obs/ep{e}_white_pot_lid.npz',
                                                 f'{R}/cand/white_pot_lid/white_pot_lid_ep{e}_t2.5_{v}.glb', '--variant', v,
                                                 '--lib', f'{LIB}/white_pot_lid.glb')
                out.append(wrap('build', f'lid/ep{e}/t2.5_{v}', cmd, env))
        if by_obj.get('plastic_dish_rack'):
            cmd = 'PRIM_T_WALL=0.0025 PRIM_CUP_LEAN=1 ' + py(env, f'{S}/prim_rack.py', 'run', '--obs_dir', f'{R}/obs', '--out',
                                                             f'{R}/cand/rack/t2.5_lean1', '--episodes',
                                                             ','.join(str(e) for e in by_obj['plastic_dish_rack']))
            out.append(wrap('build', 'rack/run', cmd, env))
        for e in by_obj.get('blue_cup', []):
            for v, extra in CUP_VARIANTS.items():
                cmd = py(env, f'{S}/lathe_obs.py', f'{R}/obs/ep{e}_blue_cup.npz', f'{R}/cand/blue_cup/ep{e}_blue_cup_{v}.glb', *extra)
                out.append(wrap('build', f'cup/ep{e}/{v}', cmd, env))
        if len(by_obj.get('blue_cup', [])) > 1:   # public 'ep21+22' lathe: the episodes' points concatenated, g1
            m = f'{R}/obs/merged_blue_cup.npz'
            cmd = (py(env, f'{JOB}/e0_merge.py', m, *[f'{R}/obs/ep{e}_blue_cup.npz' for e in by_obj['blue_cup']]) + ' && '
                   + py(env, f'{S}/lathe_obs.py', m, f'{R}/cand/blue_cup/merged_blue_cup_g1.glb'))
            out.append(wrap('build', 'cup/merged/g1', cmd, env))
    elif stage == 'candidates':
        print(json.dumps(candidates(plan, env, by_obj, REPO, R, LIB), indent=1)); return
    elif stage == 'fid':
        # obs_fidelity.py as the public selections ran it (no --icp), one mesh per process (its result does not depend
        # on the other meshes of a call: fixed seeds), against ALL eval episodes' points of the object and each episode
        for c in candidates(plan, env, by_obj, REPO, R, LIB):
            o = c['object']
            sets = [('all', [e for e in by_obj[o] if os.path.exists(f'{R}/obs/ep{e}_{o}.npz')])]
            sets += [(f'ep{e}', [e]) for e in sets[0][1]]
            for sname, el in sets:
                if not el:
                    continue
                obs = ','.join(f'{R}/obs/ep{e}_{o}.npz' for e in el)
                lab = f'{c["label"]}@{sname}'
                cmd = (py(env, f'{S}/obs_fidelity.py', obs, c['path']) + f' > fid/{OBJ_SHORT[o]}/' +
                       lab.replace('/', '__') + '.jsonl')
                out.append(wrap('fid', lab, cmd, env))
    elif stage == 'check':
        # C0's GT-free frame + kit budget check (cdo-sprint/C0/scripts/frame_check.py), vs library_v3, per candidate
        for c in candidates(plan, env, by_obj, REPO, R, LIB):
            if c['kind'] == 'library_v3':
                continue
            o = c['object']
            outj = f'check/{OBJ_SHORT[o]}/' + c['label'].replace('/', '__') + '.json'
            cmd = py(env, f'{REPO}/docs/research/mesh-2026-10-26/cdo-sprint/C0/scripts/frame_check.py', env['KIT'], outj,
                     f'{o}:{c["path"]}:{LIB}/{o}.glb')
            out.append(wrap('check', c['label'], cmd, env))
    else:
        sys.exit(f'unknown stage {stage}')
    print('\n'.join(out))


def candidates(plan, env, by_obj, REPO, R, LIB):
    C = []
    for e in by_obj.get('white_pot', []):
        for v in POT_VARIANTS:
            C.append(dict(object='white_pot', label=f'pot/ep{e}/{v}', episode=str(e), variant=v, kind='e0',
                          path=f'{R}/cand/white_pot/white_pot_ep{e}_{v}.glb'))
    for e in by_obj.get('white_pot_lid', []):
        for v in LID_VARIANTS:
            C.append(dict(object='white_pot_lid', label=f'lid/ep{e}/t2.5_{v}', episode=str(e), variant=f't2.5_{v}', kind='e0',
                          path=f'{R}/cand/white_pot_lid/white_pot_lid_ep{e}_t2.5_{v}.glb'))
    if by_obj.get('plastic_dish_rack'):
        for e in by_obj['plastic_dish_rack']:
            for v in ('full', 'nomk'):
                C.append(dict(object='plastic_dish_rack', label=f'rack/ep{e}/{v}', episode=str(e), variant=v, kind='e0',
                              path=f'{R}/cand/rack/t2.5_lean1/plastic_dish_rack/ep{e}_{v}.glb'))
        for v in ('joint', 'joint_nomk'):
            C.append(dict(object='plastic_dish_rack', label=f'rack/joint/{v}', episode='joint', variant=v, kind='e0',
                          path=f'{R}/cand/rack/t2.5_lean1/plastic_dish_rack/joint_{v}.glb'))
    for e in by_obj.get('blue_cup', []):
        for v in CUP_VARIANTS:
            C.append(dict(object='blue_cup', label=f'cup/ep{e}/{v}', episode=str(e), variant=v, kind='e0',
                          path=f'{R}/cand/blue_cup/ep{e}_blue_cup_{v}.glb'))
    if len(by_obj.get('blue_cup', [])) > 1:
        C.append(dict(object='blue_cup', label='cup/merged/g1', episode='merged', variant='g1', kind='e0',
                      path=f'{R}/cand/blue_cup/merged_blue_cup_g1.glb'))
    C = [c for c in C if os.path.exists(c['path'])]          # failed builds have no file (status/build.txt says why)
    for o, el in by_obj.items():
        if el:
            C.append(dict(object=o, label=f'{OBJ_SHORT[o]}/C0', episode='public', variant='C0', kind='C0',
                          path=f'{REPO}/{C0_MESH[o]}'))
            C.append(dict(object=o, label=f'{OBJ_SHORT[o]}/library_v3', episode='public', variant='library_v3',
                          kind='library_v3', path=f'{LIB}/{o}.glb'))
    return C


if __name__ == '__main__':
    main()
