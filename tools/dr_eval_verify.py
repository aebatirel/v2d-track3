"""Verification and training-box summary of one D-arm box (2026-10-31, pack 9b; ops/jobs/mass_eval.sh ARM=dr;
docs/research/work/pack9b-20261031/PREREG.md sections 1.2, 1.3 and 2). Eval episodes: no ground truth exists or is read;
every score is sim_vs_ref against our own stored reference (pipeline/qa.py policy). tools/mass_eval_verify.py's checks
with the masses replaced by "nothing changed", plus the D training-log line.

Cells (episode x seed) and their chosen checkpoint:
  grasp lock  results/drs<seed>_glock_public/ep<N>/best/policy.safetensors (training log runs/drs<seed>_glock/ep<N>-s<seed>/
              train.log), trained on the byte copy refs/drs<seed>_glockt/ep<N> (tools/dr_arm.py manifest --manifests);
  standard    results/hard_ab/ep<N>/mckdr-s<seed>/summary.json "checkpoint", which must be the sweep's choice in
              results/perc2mckdr/ep<N>-s<seed>/selection.json (training log runs/perc2mckdr/ep<N>-s<seed>/train.log).
Each chosen checkpoint is followed as the official evaluator loads it (saved config -> task.parquet -> reference ->
URDFs). Failures (the episode is INVALID, its packed policy stays):
  - the reference's md5 and fingerprint are not the packed policy's (packed_refs.json); grasp lock: not dr_arm's copy;
  - a URDF that does not resolve verbatim, does not carry the 0.3 kg placeholder, or lies outside the expected root
    (grasp lock: the table's asset_root, every file there md5-identical to what dr_arm recorded before training;
    standard learner: /content/assets, every file md5-identical to --assets03, the same make_assets.py build); a table
    piece set (eval 25: meshes/carve/ev25) whose <collision> count is not one per piece;
  - the support stage the training read is not the packed reference's (md5);
  - steps != the packed run's, reset.seed != the seed, a rollout naming another checkpoint, a std checkpoint that is not
    the sweep's choice, a saved-config key that differs from the packed checkpoint's except output_dir, task.parquet,
    reference.parquet and the seed keys (D adds no config field; eval 33's CURR_SCALE 0.4 thresholds must match);
  - the D line (PREREG 1.2) missing from the cell's training log, or any "v2d FC_DR_RESET" line in it that is not
        v2d FC_DR_RESET: sampled resets perturbed by +-1.5 mm, +-0.015 rad (rotation vector per axis), fingers +-0.01 rad;
        <k> objects, <j> finger joints, <W> worlds, seed <s>[; skip immediate starts (FC_DR_SKIP_IMMEDIATE: deployment-
        exact starts not perturbed)]
    with <s> the cell's seed, <k> the reference's object count, the skip tail present for the standard learner (25, 30)
    and absent for the grasp lock (14, 16, 33);
  - a training log on the box that is not a D cell's (every training on a D box is a D cell: a non-D training there is
    an error), or a patched FlashCHORD tree (--fc) without the hook or with a lifecycle/v2d_dr.py that is not what the
    repo's ops/box/patch_flashchord_dr.py writes (it is re-run on a scratch copy to compare).
Not failures (INCOMPLETE): a cell without a chosen checkpoint, a std main evaluation cut by EVAL_TIMEOUT, fewer than 8
scored training-box rollouts, a packed checkpoint or packed stage that could not be read. Missing and thin seeds are
listed under retrain_seeds (retrain only those, new box, same commit).
Summary per episode and seed: n, mean, sd (ddof 1), min of the NREP training-box rollouts. Candidate (PREREG section 2 =
tools/mass_eval_verify.rule2): over the seeds with n >= 8 the higher mean; within 0.005 the lower sd; still tied 42.
Only a VERIFIED episode has a candidate; its confirmation strings (h5_reeval.sh RUNS_EXTRA / PICK_EXTRA / DR_EPS) and the
candidate checkpoint's sha256 are written for tools/dr_eval_merge.py.
Usage: dr_eval_verify.py --mode glock|std --eps "14 16 33" --seeds "42 43" --table packed_refs.json --run RUN_ID
       --out V.json --summary S.json [--manifests "M14.json ..."] [--packed DIR] [--assets03 DIR] [--fc FLASHCHORD_DIR]
       [--content /content]
"""
import argparse, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from mass_arm import read_inertial, traj_fingerprint, md5, PLACEHOLDER                   # noqa: E402
from mass_verify import ck_config, resolve_parquet, flat, TIMEOUT_RC                       # noqa: E402
from mass_pack_check import localize                                                       # noqa: E402
from mass_eval_verify import support_stage, timeouts, stats, rule2, ALLOWED, MIN_N, H5_PIECES   # noqa: E402

COLL = re.compile(r'<collision>')
DR_TAG = '# v2d patch: FC_DR_RESET'
DR_ANY = 'v2d FC_DR_RESET'
SKIP_TAIL = '; skip immediate starts (FC_DR_SKIP_IMMEDIATE: deployment-exact starts not perturbed)'
DR_LINE = re.compile(r'^v2d FC_DR_RESET: sampled resets perturbed by \+-1\.5 mm, \+-0\.015 rad \(rotation vector per axis\), '
                     r'fingers \+-0\.01 rad; (\d+) objects, (\d+) finger joints, (\d+) worlds, seed (-?\d+)(.*)$')
SKIP_EPS = {'25', '30'}                                         # PREREG 1.2: FC_DR_SKIP_IMMEDIATE=1 (standard learner)


def tab_path(p, C):
    """a table path (/content/... or /workspace/...) under this box's content root (regex, see tools/dr_arm.py)"""
    return re.sub(r'^/(?:content|workspace)/', C.rstrip('/') + '/', p)


def tree_md5(root):
    return {os.path.relpath(f, root): md5(f) for f in sorted(glob.glob(f'{root}/**/*', recursive=True)) if os.path.isfile(f)}


def dr_lines(log, seed, n_obj, skip):
    """(ok, problems, lines) of the D line check of one training log"""
    if not os.path.isfile(log):
        return False, [f'training log {log} missing'], []
    lines = [x.strip() for x in open(log, errors='replace') if DR_ANY in x]
    bad = []
    if not lines:
        bad.append(f'no "{DR_ANY}" line in {log} (the D hook did not run in this training)')
    for x in lines:
        m = DR_LINE.match(x)
        if not m:
            bad.append(f'unexpected D line in {log}: {x[:200]}'); continue
        k, _, _, s, tail = m.groups()
        if s != str(seed):
            bad.append(f'D line seed {s} != the cell seed {seed} ({log})')
        if int(k) != n_obj:
            bad.append(f'D line names {k} objects, the reference has {n_obj} ({log})')
        if skip and tail != SKIP_TAIL:
            bad.append(f'D line without the skip-immediate tail (FC_DR_SKIP_IMMEDIATE=1 expected) in {log}: ...{tail[:120]}')
        if not skip and tail != '':
            bad.append(f'D line with an unexpected tail (no FC_DR_SKIP_IMMEDIATE expected) in {log}: ...{tail[:120]}')
    return not bad, bad, lines


def expected_hook():
    """md5 of the lifecycle/v2d_dr.py the repo's ops/box/patch_flashchord_dr.py writes (run on a scratch tree)"""
    d = tempfile.mkdtemp(prefix='drhook_')
    try:
        L = f'{d}/src/flash_chord/lifecycle'; os.makedirs(L)
        open(f'{L}/reset.py', 'w').write('import newton\n\nclass ReferenceResetTable:\n    pass\n\n\nclass ReferenceReset:\n'
                                         '    def sample(self, reset_mask, curriculum_voc_scale):\n        pass\n\n'
                                         '    def prepare_explicit(self, reset_mask, curriculum_voc_scale):\n        pass\n\n\n'
                                         'def reset_worlds(model, table, state, reset_mask=None):\n    pass\n')
        r = subprocess.run([sys.executable, '-I', f'{REPO}/ops/box/patch_flashchord_dr.py', d], capture_output=True, text=True)
        f = f'{L}/v2d_dr.py'
        return (md5(f) if r.returncode == 0 and os.path.isfile(f) else None), (r.stdout + r.stderr)[-300:]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cell_paths(mode, C, e, s):
    """(results dir, chosen checkpoint or None, rollout dirs glob, curve/sweep eval logs, run dir) of one D cell"""
    if mode == 'glock':
        O = f'{C}/results/drs{s}_glock_public/ep{e}'
        ck = f'{O}/best/policy.safetensors' if os.path.exists(f'{O}/best/summary.json') else None
        return (O, ck, f'{O}/best/r*/', glob.glob(f'{O}/curve/policy_*/eval.log') + glob.glob(f'{O}/curve/policy_*/r*/eval.log'),
                f'{C}/runs/drs{s}_glock/ep{e}-s{s}')
    O = f'{C}/results/hard_ab/ep{e}/mckdr-s{s}'
    ck = None
    if os.path.exists(f'{O}/summary.json'):
        ck = localize(json.load(open(f'{O}/summary.json')).get('checkpoint') or '', C) or None
    res = f'{C}/results/perc2mckdr/ep{e}-s{s}'
    return O, ck, f'{O}/r*/', glob.glob(f'{res}/eval.log') + glob.glob(f'{res}/sweep/*/eval.log'), f'{C}/runs/perc2mckdr/ep{e}-s{s}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('--mode', '--eps', '--seeds', '--table', '--run', '--out', '--summary'):
        ap.add_argument(x, required=True)
    ap.add_argument('--manifests', default=''); ap.add_argument('--packed', default='')
    ap.add_argument('--assets03', default=''); ap.add_argument('--content', default='/content')
    ap.add_argument('--fc', default='')
    a = ap.parse_args()
    C = a.content.rstrip('/'); tab = json.load(open(a.table))['episodes']
    man = {}
    for f in a.manifests.split():
        if os.path.exists(f):
            d = json.load(open(f)); man[str(d['episode'])] = d
    seeds = a.seeds.split(); eps = [str(int(x)) for x in a.eps.split()]
    patch_md5 = md5(f'{REPO}/ops/box/patch_flashchord_dr.py')
    V = dict(mode=a.mode, run=a.run, arm='dr', episodes={}, patch_md5=patch_md5,
             rule='docs/research/work/pack9b-20261031/PREREG.md sections 1.2, 1.3, 2')
    S = dict(mode=a.mode, run=a.run, arm='dr', episodes={}, patch_md5=patch_md5)
    box_fails = []                                       # failures of the whole box: every episode is INVALID with them
    want_hook, hook_log = expected_hook()
    hook = dict(expected_md5=want_hook, patch_run=hook_log[-160:])
    if a.fc:
        L = f'{a.fc}/src/flash_chord/lifecycle'
        hook.update(installed_md5=md5(f'{L}/v2d_dr.py') if os.path.isfile(f'{L}/v2d_dr.py') else None,
                    reset_tagged=os.path.isfile(f'{L}/reset.py') and DR_TAG in open(f'{L}/reset.py').read())
        if not hook['reset_tagged']:
            box_fails.append(f'{L}/reset.py has no "{DR_TAG}" hook (the DR patch was not applied)')
        if not want_hook or hook['installed_md5'] != want_hook:
            box_fails.append(f'{L}/v2d_dr.py md5 {hook["installed_md5"]} != what the repo patch writes ({want_hook})')
    else:
        hook['note'] = 'no --fc: the patched tree was not checked'
    V['hook'] = hook
    cell_runs = {}
    for e in eps:
        for s in seeds:
            cell_runs[f'ep{e}/s{s}'] = cell_paths(a.mode, C, e, s)[4]
    others = []                                          # training logs on this box that belong to no D cell
    for f in sorted(glob.glob(f'{C}/runs/**/train.log', recursive=True)):
        d = os.path.dirname(f)
        if not any(d == r or re.fullmatch(re.escape(r) + r'\.oom\d+', d) for r in cell_runs.values()):
            others.append(f)
    if others:
        box_fails.append(f'training logs of non-D trainings on this D box: {others[:4]}')
    V['other_training_logs'] = others
    for e in eps:
        T = tab[e]; fails, missing, cells, unchecked, timed_out = list(box_fails), [], {}, [], []
        if T['mode'] != a.mode:
            fails.append(f'ep{e}: table mode {T["mode"]} != --mode {a.mode}')
        M = man.get(e)
        if a.mode == 'glock':
            if not M:
                fails.append(f'ep{e}: no dr_arm manifest')
            elif M['traj_fingerprint'] != T['traj_fingerprint'] or M['source_md5'] != T['md5']:
                fails.append(f'ep{e}: dr_arm source {M["source_md5"]} / {M["traj_fingerprint"]} is not the packed reference '
                             f'{T["md5"]} / {T["traj_fingerprint"]}')
        pk = f'{a.packed}/ep{e}.safetensors' if a.packed else ''
        pcfg = None
        if pk and os.path.exists(pk):
            try:
                pcfg = flat(ck_config(pk)[1])
            except Exception as x:
                unchecked.append(f'packed checkpoint header unreadable: {x}')
        else:
            unchecked.append(f'packed checkpoint {T["recipe_checkpoint"]} not on this box (config diff not done)')
        skip = e in SKIP_EPS
        for s in seeds:
            key = f'ep{e}/s{s}'; row = cells[s] = {}
            O, ck, rglob, curve, rund = cell_paths(a.mode, C, e, s)
            rdirs = sorted(glob.glob(rglob))
            row['eval_timeouts'] = dict(best=timeouts([f'{r}eval.log' for r in rdirs if os.path.exists(f'{r}eval.log')]),
                                        curve=timeouts(curve))
            if not ck or not os.path.exists(ck):
                row['missing'] = True; missing.append(key); continue
            if a.mode == 'std':                                  # as mass_eval_verify (F6): main evaluation cut -> no choice
                rcf = f'{C}/results/perc2mckdr/ep{e}-s{s}/eval_rc.txt'
                rc = open(rcf).read().strip() if os.path.exists(rcf) else ''
                if rc in TIMEOUT_RC and not os.path.exists(f'{C}/results/perc2mckdr/ep{e}-s{s}/selection.json'):
                    row.update(missing=True, main_eval_timeout=rc, checkpoint_fallback=ck)
                    missing.append(key); timed_out.append(key); continue
            try:
                row['checkpoint'] = ck
                if a.mode == 'std':
                    sel = f'{C}/results/perc2mckdr/ep{e}-s{s}/selection.json'
                    chosen = localize(json.load(open(sel))['chosen'], C) if os.path.exists(sel) else None
                    if not chosen or os.path.realpath(chosen) != os.path.realpath(ck):
                        fails.append(f'{key}: checkpoint {ck} is not the sweep\'s choice ({chosen or "no selection.json"})')
                meta, cfg = ck_config(ck); F = flat(cfg)
                row['checkpoint_steps'] = meta.get('user.environment_steps')
                rp = resolve_parquet(os.path.realpath(localize(cfg['task']['parquet'], C)))
                t = pq.read_table(rp); fp, m5 = traj_fingerprint(t), md5(rp)
                row.update(reference_file=rp, reference_md5=m5, traj_fingerprint=fp)
                if fp != T['traj_fingerprint'] or m5 != T['md5']:
                    fails.append(f'{key}: reference {m5} / {fp} is not the packed reference {T["md5"]} / {T["traj_fingerprint"]}')
                if a.mode == 'glock':
                    want_dir = f'{C}/refs/drs{s}_glockt/ep{e}'
                    if not os.path.realpath(rp).startswith(os.path.realpath(want_dir) + '/'):
                        fails.append(f'{key}: trained on {rp}, not dr_arm\'s seed-{s} copy under {want_dir}')
                    if M and m5 != M['seeds'].get(s, {}).get('md5'):
                        fails.append(f'{key}: reference md5 {m5} is not dr_arm\'s seed-{s} copy')
                else:
                    want_dir = f'{C}/refs/perc2mckdr/ep{e}'
                    if not os.path.realpath(rp).startswith(os.path.realpath(want_dir) + '/'):
                        fails.append(f'{key}: trained on {rp}, not the D copy under {want_dir}')
                names = t.column('object_body_names')[0].as_py(); loaded = {}
                root = (M or {}).get('asset_root') or tab_path(T['asset_root'], C) if a.mode == 'glock' else f'{C}/assets'
                for n, u in zip(names, t.column('object_urdf_paths')[0].as_py()):
                    lu = localize(u, C)
                    if not os.path.isfile(lu):
                        fails.append(f'{key}: {n}: {u} is not a file (FlashCHORD would re-root it)'); continue
                    txt = open(lu).read(); m, com, I = read_inertial(txt)
                    loaded[n] = dict(urdf=lu, md5=md5(lu), mass=m, collisions=len(COLL.findall(txt)))
                    if abs(m - PLACEHOLDER) > 1e-9:
                        fails.append(f'{key}: {n} loads {m} kg from {lu}; the D arm keeps the {PLACEHOLDER} kg placeholder')
                    if not os.path.realpath(lu).startswith(os.path.realpath(root) + '/'):
                        fails.append(f'{key}: {n} URDF {lu} is not under {root}')
                    if a.mode == 'glock' and M and loaded[n]['md5'] != M['urdfs'].get(n, {}).get('md5'):
                        fails.append(f'{key}: {n} URDF {lu} changed since dr_arm recorded it')
                row['loaded_urdfs'] = loaded
                if a.mode == 'glock' and M:
                    if tree_md5(root) != M.get('asset_md5'):
                        fails.append(f'{key}: files under {root} differ from what dr_arm recorded before training')
                elif a.mode == 'std':
                    if not a.assets03 or not os.path.isdir(a.assets03):
                        unchecked.append(f'{key}: no 0.3 kg twin (--assets03): /content/assets not compared')
                    elif tree_md5(root) != tree_md5(a.assets03):
                        fails.append(f'{key}: files under {root} differ from the same make_assets.py build {a.assets03}')
                if T.get('pieces'):
                    pdir = os.path.join(REPO, T['pieces'])
                    for n in names:
                        k = len(glob.glob(f'{pdir}/{n}/piece_*.obj'))
                        if k and loaded.get(n, {}).get('collisions') != k:
                            fails.append(f'{key}: {n}: {loaded.get(n, {}).get("collisions")} collisions, {k} pieces in {T["pieces"]}')
                sname, spath = support_stage(rp)
                pst = f'{C}/refs/{"glockt" if a.mode == "glock" else "perc2mck"}/ep{e}/reconstructed_stage/{sname}'
                row['support_stage'] = dict(file=spath, md5=md5(spath) if spath else None, packed=pst,
                                            packed_md5=md5(pst) if os.path.isfile(pst) else None)
                if not spath:
                    fails.append(f'{key}: no support stage {sname} next to {rp} (FlashCHORD reads one)')
                elif not os.path.isfile(pst):
                    unchecked.append(f'{key}: packed support stage {pst} not on this box (stage not compared)')
                elif row['support_stage']['md5'] != row['support_stage']['packed_md5']:
                    fails.append(f'{key}: support stage {spath} is not the packed reference\'s {pst}')
                st = F.get('training.total_environment_steps'); row['total_environment_steps'] = st
                if str(st) != str(T['steps']):
                    fails.append(f'{key}: training.total_environment_steps {st} != {T["steps"]}')
                row['reset_seed'] = F.get('reset.seed')
                if str(row['reset_seed']) != str(s):
                    fails.append(f'{key}: reset.seed {row["reset_seed"]} != {s}')
                ok_, bad_, lines_ = dr_lines(f'{rund}/train.log', s, len(names), skip)
                row['dr_log'] = dict(log=f'{rund}/train.log', ok=ok_, lines=lines_[:4], n_lines=len(lines_), skip_expected=skip)
                fails += [f'{key}: {b}' for b in bad_]
                sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest(); row['checkpoint_sha256'] = sha; rows = []
                for r in rdirs:
                    for j in glob.glob(f'{r}episode_*.json'):
                        d = json.load(open(j))
                        if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != sha:
                            fails.append(f'{key}: {j} evaluated {d["checkpoint_sha256"][:12]}, chosen {sha[:12]}')
                    if os.path.exists(f'{r}qa_policy.json'):
                        rows.append(dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=json.load(open(f'{r}qa_policy.json'))['sim_vs_ref']))
                row['stats'] = stats(rows)
                if sha == T.get('packed_sha256'):
                    fails.append(f'{key}: the chosen checkpoint IS the packed checkpoint (sha256 {sha[:12]})')
                if pcfg is not None:
                    diff = sorted(k for k in set(F) | set(pcfg) if F.get(k, '<none>') != pcfg.get(k, '<none>'))
                    row['packed_config_diff'] = {k: [str(pcfg.get(k, '<none>'))[:160], str(F.get(k, '<none>'))[:160]] for k in diff}
                    bad = [k for k in diff if k not in ALLOWED]
                    if bad:
                        fails.append(f'{key}: recipe differs from the packed checkpoint in {bad[:8]}')
            except Exception as x:
                row['error'] = f'{type(x).__name__}: {str(x)[:200]}'; fails.append(f'{key}: {row["error"]}')
        thin = [f'ep{e}/s{s}' for s in seeds if not cells[s].get('missing') and 'error' not in cells[s]
                and cells[s].get('stats', {}).get('n', 0) < MIN_N]
        status = 'INVALID' if fails else ('INCOMPLETE' if missing or unchecked or thin else 'VERIFIED')
        retrain = [s for s in seeds if f'ep{e}/s{s}' in missing + thin] if status != 'INVALID' else []
        V['episodes'][e] = dict(status=status, failures=fails, missing=missing, thin=thin, main_eval_timeout=timed_out,
                                unchecked=unchecked, retrain_seeds=retrain, cells=cells)
        st = {s: c.get('stats', dict(n=0)) for s, c in cells.items()}
        cand = rule2(st, seeds)
        note = ''
        if status == 'INVALID':
            note = 'no candidate: INVALID (PREREG section 6: the packed policy stays)'
        elif status == 'INCOMPLETE':
            note = ('no candidate until VERIFIED' + (f'; retrain only seeds {retrain} on a new box (same reference and '
                                                     f'commit; PREREG section 6)' if retrain else '')
                    + ('; re-run this tool once the unchecked files are there' if unchecked else ''))
        ent = dict(status=status, seeds={s: dict(st[s], eval_timeouts=cells[s]['eval_timeouts'],
                                                 checkpoint=cells[s].get('checkpoint'), checkpoint_sha256=cells[s].get('checkpoint_sha256'),
                                                 dr_log_ok=(cells[s].get('dr_log') or {}).get('ok'),
                                                 **({'main_eval_timeout': cells[s]['main_eval_timeout']} if 'main_eval_timeout' in cells[s] else {}))
                                         for s in seeds},
                   rule2_candidate=cand if status == 'VERIFIED' else None, missing=missing, thin=thin,
                   unchecked=unchecked, retrain_seeds=retrain, min_n=MIN_N, note=note)
        if status == 'VERIFIED' and cand:
            ent['candidate_sha256'] = cells[cand].get('checkpoint_sha256')
            if a.mode == 'glock':
                ent['runs_extra'] = f'{a.run}@refs/drs{cand}_glockt/ep{e}'
                ent['pick_extra'] = f'{e}:{a.run}:ck=results/drs{cand}_glock_public/ep{e}/best/policy.safetensors'
            else:
                rel = os.path.relpath(os.path.realpath(cells[cand]['checkpoint']), os.path.realpath(C))   # runs/perc2mckdr/...
                ent['runs_extra'] = f'{a.run}@refs/perc2mckdr/ep{e}'
                ent['pick_extra'] = f'{e}:{a.run}:ck={rel}'
                if T.get('pieces') and T['pieces'] not in H5_PIECES:
                    ent['asset_pieces_extra'] = f'/content/v2d-track3/{T["pieces"]}'
        S['episodes'][e] = ent
    ok = [e for e, x in S['episodes'].items() if x.get('pick_extra')]
    S['confirmation'] = dict(
        RUNS_EXTRA=' '.join(S['episodes'][e]['runs_extra'] for e in ok), PICK_EXTRA=' '.join(S['episodes'][e]['pick_extra'] for e in ok),
        DR_EPS=' '.join(ok), EVAL_ONLY=' '.join(ok), EPS_ONLY=' '.join(ok),
        ASSET_PIECES_EXTRA=' '.join(sorted({S['episodes'][e]['asset_pieces_extra'] for e in ok if S['episodes'][e].get('asset_pieces_extra')})),
        note='strings for ops/jobs/h5_reeval.sh (PREREG section 3); join the boxes with tools/dr_eval_merge.py')
    V['ok'] = all(x['status'] == 'VERIFIED' for x in V['episodes'].values())
    json.dump(V, open(a.out, 'w'), indent=1); json.dump(S, open(a.summary, 'w'), indent=1)
    for e, x in V['episodes'].items():
        s_ = S['episodes'][e]
        print(f'ep{e} {x["status"]}' + (f' ({len(x["failures"])} failures: ' + ' | '.join(x['failures'][:4]) + ')' if x['failures'] else '')
              + (f' missing {x["missing"]}' if x['missing'] else '') + (f' unchecked {x["unchecked"]}' if x['unchecked'] else '')
              + (f' main evaluation cut {x["main_eval_timeout"]}' if x['main_eval_timeout'] else '')
              + (f' thin (n < {MIN_N}) {x["thin"]}' if x['thin'] else '')
              + (f' retrain seeds {x["retrain_seeds"]}' if x['retrain_seeds'] else '')
              + ' :: ' + '; '.join(f's{s} n {v.get("n")} mean {v.get("mean")} sd {v.get("sd")} min {v.get("min")} cut {v["eval_timeouts"]["best"]["cut"]}/{v["eval_timeouts"]["curve"]["cut"]} D-line {"ok" if v.get("dr_log_ok") else v.get("dr_log_ok")}'
                                   for s, v in s_['seeds'].items())
              + f' :: candidate {s_["rule2_candidate"]}')
    print(f'hook: {json.dumps({k: v for k, v in hook.items() if k != "patch_run"})}; other training logs: {len(others)}')
    print('confirmation: ' + json.dumps({k: v for k, v in S['confirmation'].items() if k != 'note'}))
    sys.exit(0 if V['ok'] else 1)


if __name__ == '__main__':
    main()
