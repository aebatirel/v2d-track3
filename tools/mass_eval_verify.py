"""Verification and training-box summary of one masses eval-retrain box (2026-10-31; ops/jobs/mass_eval.sh, plan
docs/research/work/masses-eval-20261031/PLAN.md, adoption rule section 5, build notes BUILD.md). Eval episodes: no ground
truth exists or is read; every score is sim_vs_ref against our own stored reference (pipeline/qa.py policy).

For every episode and seed the chosen checkpoint (grasp lock: results/mass1s<seed>_glock_public/ep<N>/best/
policy.safetensors; standard learner: results/hard_ab/ep<N>/mcks-s<seed>/summary.json "checkpoint", which must be the
checkpoint sweep's choice in results/perc2mcks/ep<N>-s<seed>/selection.json) is followed the way the official
evaluator loads it: saved config (safetensors header user.resolved_config_json) -> task.parquet -> the reference file
(exactly one .parquet) -> object_urdf_paths -> URDF inertials. Failures (the episode is INVALID; its packed policy
stays, PLAN section 5 rule 3):
  - reference: its fingerprint (tools/mass_arm.traj_fingerprint) is the packed policy's (packed_refs.json); standard
    learner: also its md5; grasp lock: also the md5 of mass_arm's per-seed copy, whose source md5 is the packed one;
  - URDFs: each resolves verbatim; mass = the props' mass_kg; COM unchanged and inertia = the 0.3 kg source x m / 0.3
    (grasp lock: the source asset folder in mass_arm's manifest; standard learner: --assets03, the same make_assets.py
    build without --physics); grasp lock: inside refs/mass1_sf/ep<N>/, standard learner: inside /content/assets;
  - mesh files (every non-URDF file) byte-identical to that 0.3 kg source, so collision pieces are the packed ones; each
    object's <collision> count equals the source's;
  - training.total_environment_steps = the packed run's (70,004,736 / 250,003,456); reset.seed = the seed;
  - the evaluated rollouts name the chosen checkpoint (checkpoint_sha256);
  - recipe: the saved config equals the packed checkpoint's (--packed DIR/ep<N>.safetensors, header only) in every key
    except output_dir, task.parquet, reference.parquet and the seed keys (reset.seed, env.reset.seed, training.seed);
    e.g. eval 33's curriculum.thresholds must be the CURR_SCALE 0.4 ones of its packed checkpoint;
  - support stage (review F2): the stage FlashCHORD resolves for the trained reference (<reference>/../../
    reconstructed_stage/<seq>[_<robot>]_support.usda, assets/registry.py support_usda_for_parquet) exists and has the md5
    of the packed reference's stage (grasp lock: the pulled refs/glockt/ep<N>/reconstructed_stage; standard learner: the
    pulled base refs/perc2mck/ep<N>/reconstructed_stage, of which the packed refs/perc2mcks copy is a byte copy).
Not failures (the episode is INCOMPLETE): a cell without a chosen checkpoint (missing); a standard-learner cell whose
main evaluation was cut by EVAL_TIMEOUT (results/perc2mcks/ep<N>-s<seed>/eval_rc.txt 124 / 137: no sweep, so no
selection.json; review F6); a cell with fewer than 8 scored training-box rollouts (thin; review F1); a packed checkpoint
or packed stage that could not be read (unchecked: re-run this tool on CPU once the files are there). Missing and thin
seeds are listed under retrain_seeds: per PLAN section 5 rule 2 (amended 31 Oct) only those seeds are retrained, on a
new box, same reference and commit. Evaluations cut by EVAL_TIMEOUT are also counted per cell.
Summary per episode and seed: n, mean, sd (ddof 1), min of the NREP training-box rollouts (sim_vs_ref). Candidate
(rule 2): over the seeds with n >= 8, the higher mean; within 0.005, the lower sd; still tied, the first seed listed
(42). Only a VERIFIED episode has a candidate. The confirmation strings (h5_reeval.sh RUNS_EXTRA / PICK_EXTRA / MASS_EPS ...) are
printed for the candidates; the confirmation and the swap rule (rules 4-6) come after this box.
Usage: mass_eval_verify.py --mode glock|std --eps "20 8" --seeds "42 43" --props P.json --table packed_refs.json
       --run RUN_ID --out V.json --summary S.json [--manifests "M20.json M8.json"] [--packed DIR] [--assets03 DIR]
       [--content /content]
"""
import argparse, glob, hashlib, json, os, re, sys
import numpy as np, pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import read_inertial, traj_fingerprint, md5, PLACEHOLDER          # noqa: E402
from mass_verify import ck_config, resolve_parquet, flat, rc_counts, TIMEOUT_RC  # noqa: E402
from mass_pack_check import localize                                              # noqa: E402

ALLOWED = {'output_dir', 'task.parquet', 'reference.parquet', 'reset.seed', 'env.reset.seed', 'training.seed'}
H5_PIECES = ('meshes/carve/ev25', 'meshes/carve/ev10')         # already in h5_reeval.sh's ASSET_PIECES
COLL = re.compile(r'<collision>')
MIN_N = 8                                                       # PLAN section 5 rule 2 (amended 31 Oct) and rule 4


def support_stage(parquet):
    """The support USDA FlashCHORD resolves for a reference parquet (assets/registry.py support_usda_for_parquet, its
    colocated branch): <sequence_id=...>/../../reconstructed_stage/<seq>_<robot>_support.usda or <seq>_support.usda.
    (name, path or None)."""
    p = os.path.realpath(parquet); parts = p.split('/')
    seq = next((x.split('=', 1)[1] for x in reversed(parts) if x.startswith('sequence_id=')), None)
    rob = next((x.split('=', 1)[1] for x in reversed(parts) if x.startswith('robot_name=')), None)
    if seq is None:
        return None, None
    i = max(k for k, x in enumerate(parts) if x.startswith('sequence_id='))
    sd = '/'.join(parts[:i - 1]) + '/reconstructed_stage'
    names = ([f'{seq}_{rob}_support.usda'] if rob else []) + [f'{seq}_support.usda']
    hit = next((n for n in names if os.path.isfile(f'{sd}/{n}')), None)
    return (hit or names[-1]), (f'{sd}/{hit}' if hit else None)


def files_md5(root):
    return {os.path.relpath(f, root): md5(f) for f in sorted(glob.glob(f'{root}/**/*', recursive=True))
            if os.path.isfile(f) and not f.endswith('.urdf')}


def timeouts(paths):
    rc = rc_counts([os.path.join(os.path.dirname(f), 'eval_rc.txt') for f in paths
                    if os.path.exists(os.path.join(os.path.dirname(f), 'eval_rc.txt'))])
    return dict(cut=sum(rc.get(x, 0) for x in TIMEOUT_RC), runs=len(paths), rc=rc, without_rc=len(paths) - sum(rc.values()))


def stats(rows):
    v = np.array([r['sim_vs_ref'] for r in rows], float)
    if not len(v):
        return dict(n=0)
    return dict(n=int(len(v)), mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)), 4) if len(v) > 1 else 0.0,
                min=round(float(v.min()), 4), values=[round(float(x), 4) for x in v])


def rule2(st, seeds):
    """PLAN section 5 rule 2: the seed with the higher training-box mean; within 0.005 the lower sd; still tied, the
    first seed listed (42). st = {seed: stats}; a seed with fewer than MIN_N (8) scored rollouts counts as missing (rule 2
    as amended 31 Oct, review F1: the callers then make the episode INCOMPLETE). None if no seed has MIN_N."""
    have = [s for s in seeds if st.get(s, {}).get('n', 0) >= MIN_N]
    if not have:
        return None
    best = max(have, key=lambda s: st[s]['mean'])
    # the gap is rounded like the means (review R1, 31 Oct): unrounded, an exact 0.0050 gap of 4-decimal means read as
    # larger in floating point and skipped the lower-sd tie-break PLAN asks for
    close = [s for s in have if round(abs(st[s]['mean'] - st[best]['mean']), 4) <= 0.005]
    return min(close, key=lambda s: (st[s]['sd'], seeds.index(s)))


def cell_paths(mode, C, e, s):
    """(results dir, chosen checkpoint or None, rollout dirs glob, curve/sweep eval logs) of one cell."""
    if mode == 'glock':
        O = f'{C}/results/mass1s{s}_glock_public/ep{e}'
        ck = f'{O}/best/policy.safetensors' if os.path.exists(f'{O}/best/summary.json') else None
        return O, ck, f'{O}/best/r*/', glob.glob(f'{O}/curve/policy_*/eval.log') + glob.glob(f'{O}/curve/policy_*/r*/eval.log')
    O = f'{C}/results/hard_ab/ep{e}/mcks-s{s}'
    ck = None
    if os.path.exists(f'{O}/summary.json'):
        ck = localize(json.load(open(f'{O}/summary.json')).get('checkpoint') or '', C) or None
    res = f'{C}/results/perc2mcks/ep{e}-s{s}'
    return O, ck, f'{O}/r*/', glob.glob(f'{res}/eval.log') + glob.glob(f'{res}/sweep/*/eval.log')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('--mode', '--eps', '--seeds', '--props', '--table', '--run', '--out', '--summary'):
        ap.add_argument(x, required=True)
    ap.add_argument('--manifests', default=''); ap.add_argument('--packed', default='')
    ap.add_argument('--assets03', default=''); ap.add_argument('--content', default='/content')
    a = ap.parse_args()
    C = a.content.rstrip('/'); tab = json.load(open(a.table))['episodes']
    props = {n: float(v['physics']['mass_kg']) for n, v in json.load(open(a.props)).items() if isinstance(v, dict) and 'physics' in v}
    man = {}
    for f in a.manifests.split():
        if os.path.exists(f):
            d = json.load(open(f)); man[str(d['episode'])] = d
    seeds = a.seeds.split(); eps = [str(int(x)) for x in a.eps.split()]
    V = dict(mode=a.mode, run=a.run, episodes={}, rule='docs/research/work/masses-eval-20261031/PLAN.md section 5')
    S = dict(mode=a.mode, run=a.run, episodes={})
    for e in eps:
        T = tab[e]; fails, missing, cells, unchecked, timed_out = [], [], {}, [], []
        if T['mode'] != a.mode:
            fails.append(f'ep{e}: table mode {T["mode"]} != --mode {a.mode}')
        M = man.get(e)
        if a.mode == 'glock':
            if not M:
                fails.append(f'ep{e}: no mass_arm manifest')
            elif M['traj_fingerprint'] != T['traj_fingerprint'] or M['source_md5'] != T['md5']:
                fails.append(f'ep{e}: mass_arm source {M["source_md5"]} / {M["traj_fingerprint"]} is not the packed reference '
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
        for s in seeds:
            key = f'ep{e}/s{s}'; row = cells[s] = {}
            O, ck, rglob, curve = cell_paths(a.mode, C, e, s)
            rdirs = sorted(glob.glob(rglob))
            row['eval_timeouts'] = dict(best=timeouts([f'{r}eval.log' for r in rdirs if os.path.exists(f'{r}eval.log')]),
                                        curve=timeouts(curve))
            if not ck or not os.path.exists(ck):
                row['missing'] = True; missing.append(key); continue
            if a.mode == 'std':                                  # review F6: main evaluation cut -> no sweep, no choice
                rcf = f'{C}/results/perc2mcks/ep{e}-s{s}/eval_rc.txt'
                rc = open(rcf).read().strip() if os.path.exists(rcf) else ''
                if rc in TIMEOUT_RC and not os.path.exists(f'{C}/results/perc2mcks/ep{e}-s{s}/selection.json'):
                    row.update(missing=True, main_eval_timeout=rc, checkpoint_fallback=ck)
                    missing.append(key); timed_out.append(key); continue
            try:
                row['checkpoint'] = ck
                if a.mode == 'std':
                    sel = f'{C}/results/perc2mcks/ep{e}-s{s}/selection.json'
                    chosen = localize(json.load(open(sel))['chosen'], C) if os.path.exists(sel) else None
                    if not chosen or os.path.realpath(chosen) != os.path.realpath(ck):
                        fails.append(f'{key}: checkpoint {ck} is not the sweep\'s choice ({chosen or "no selection.json"})')
                meta, cfg = ck_config(ck); F = flat(cfg)
                row['checkpoint_steps'] = meta.get('user.environment_steps')
                rp = resolve_parquet(os.path.realpath(localize(cfg['task']['parquet'], C)))
                t = pq.read_table(rp); fp, m5 = traj_fingerprint(t), md5(rp)
                row.update(reference_file=rp, reference_md5=m5, traj_fingerprint=fp)
                if fp != T['traj_fingerprint']:
                    fails.append(f'{key}: reference fingerprint {fp} is not the packed policy\'s {T["traj_fingerprint"]}')
                if a.mode == 'std' and m5 != T['md5']:
                    fails.append(f'{key}: reference md5 {m5} is not the packed reference\'s {T["md5"]}')
                if a.mode == 'glock' and M and m5 != M['arms']['mass1']['seeds'][s]['md5']:
                    fails.append(f'{key}: reference {rp} is not mass_arm\'s seed-{s} copy')
                names = t.column('object_body_names')[0].as_py(); loaded = {}
                if a.mode == 'glock':
                    root, srcroot = f'{C}/refs/mass1_sf/ep{e}/assets', (M or {}).get('source_asset_root', '')
                else:
                    root, srcroot = f'{C}/assets', a.assets03
                for n, u in zip(names, t.column('object_urdf_paths')[0].as_py()):
                    lu = localize(u, C)
                    if not os.path.isfile(lu):
                        fails.append(f'{key}: {n}: {u} is not a file (FlashCHORD would re-root it)'); continue
                    txt = open(lu).read(); m, com, I = read_inertial(txt)
                    loaded[n] = dict(urdf=lu, mass=m, com=com, ixx=I.get('ixx'), collisions=len(COLL.findall(txt)))
                    if n not in props or abs(m - props[n]) > 1e-9:
                        fails.append(f'{key}: {n} loads {m} kg from {lu}, props {props.get(n)}')
                    if not os.path.realpath(lu).startswith(os.path.realpath(root) + '/'):
                        fails.append(f'{key}: {n} URDF {lu} is not under {root}')
                    src = os.path.join(srcroot, os.path.relpath(lu, root)) if srcroot else ''
                    if not src or not os.path.isfile(src):
                        fails.append(f'{key}: {n}: no 0.3 kg source URDF ({src or "no source root"})'); continue
                    stxt = open(src).read(); m0, com0, I0 = read_inertial(stxt)
                    if abs(m0 - PLACEHOLDER) > 1e-9 or com != com0 or any(
                            abs(I[c] - I0[c] * m / m0) > 1e-6 * max(abs(I0[c] * m / m0), 1e-12) for c in I0):
                        fails.append(f'{key}: {n}: mass {m0} -> {m}, COM {com0} -> {com}, inertia not the source x m/0.3')
                    if len(COLL.findall(stxt)) != loaded[n]['collisions']:
                        fails.append(f'{key}: {n}: {loaded[n]["collisions"]} collision pieces, source {len(COLL.findall(stxt))}')
                row['loaded_urdfs'] = loaded
                sname, spath = support_stage(rp)                  # review F2: the support stage the training read
                pst = f'{C}/refs/{"glockt" if a.mode == "glock" else "perc2mck"}/ep{e}/reconstructed_stage/{sname}'
                row['support_stage'] = dict(file=spath, md5=md5(spath) if spath else None, packed=pst,
                                            packed_md5=md5(pst) if os.path.isfile(pst) else None)
                if not spath:
                    fails.append(f'{key}: no support stage {sname} next to {rp} (FlashCHORD reads one)')
                elif not os.path.isfile(pst):
                    unchecked.append(f'{key}: packed support stage {pst} not on this box (stage not compared)')
                elif row['support_stage']['md5'] != row['support_stage']['packed_md5']:
                    fails.append(f'{key}: support stage {spath} ({row["support_stage"]["md5"][:12]}) is not the packed '
                                 f'reference\'s {pst} ({row["support_stage"]["packed_md5"][:12]})')
                if srcroot and os.path.isdir(srcroot):
                    if files_md5(root) != files_md5(srcroot):
                        fails.append(f'{key}: mesh files under {root} differ from the 0.3 kg source {srcroot}')
                if a.mode == 'std' and T.get('pieces'):
                    pdir = os.path.join(C, 'v2d-track3', T['pieces'])
                    for n in names:
                        k = len(glob.glob(f'{pdir}/{n}/piece_*.obj'))
                        if k and loaded.get(n, {}).get('collisions') != k:
                            fails.append(f'{key}: {n}: {loaded.get(n, {}).get("collisions")} collisions, {k} pieces in {T["pieces"]}')
                st = F.get('training.total_environment_steps'); row['total_environment_steps'] = st
                if str(st) != str(T['steps']):
                    fails.append(f'{key}: training.total_environment_steps {st} != {T["steps"]}')
                row['reset_seed'] = F.get('reset.seed')
                if str(row['reset_seed']) != str(s):
                    fails.append(f'{key}: reset.seed {row["reset_seed"]} != {s}')
                sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest(); row['checkpoint_sha256'] = sha; rows = []
                for r in rdirs:
                    for j in glob.glob(f'{r}episode_*.json'):
                        d = json.load(open(j))
                        if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != sha:
                            fails.append(f'{key}: {j} evaluated {d["checkpoint_sha256"][:12]}, chosen {sha[:12]}')
                    if os.path.exists(f'{r}qa_policy.json'):
                        rows.append(dict(rollout=os.path.basename(r[:-1]), sim_vs_ref=json.load(open(f'{r}qa_policy.json'))['sim_vs_ref']))
                row['stats'] = stats(rows)
                if pcfg is not None:
                    diff = sorted(k for k in set(F) | set(pcfg) if F.get(k, '<none>') != pcfg.get(k, '<none>'))
                    row['packed_config_diff'] = {k: [str(pcfg.get(k, '<none>'))[:160], str(F.get(k, '<none>'))[:160]] for k in diff}
                    bad = [k for k in diff if k not in ALLOWED]
                    if bad:
                        fails.append(f'{key}: recipe differs from the packed checkpoint in {bad[:8]}')
            except Exception as x:
                row['error'] = f'{type(x).__name__}: {str(x)[:200]}'; fails.append(f'{key}: {row["error"]}')
        thin = [f'ep{e}/s{s}' for s in seeds if not cells[s].get('missing') and 'error' not in cells[s]
                and cells[s].get('stats', {}).get('n', 0) < MIN_N]     # review F1: n < 8 counts as missing
        status = 'INVALID' if fails else ('INCOMPLETE' if missing or unchecked or thin else 'VERIFIED')
        retrain = [s for s in seeds if f'ep{e}/s{s}' in missing + thin] if status != 'INVALID' else []
        V['episodes'][e] = dict(status=status, failures=fails, missing=missing, thin=thin, main_eval_timeout=timed_out,
                                unchecked=unchecked, retrain_seeds=retrain, cells=cells)
        st = {s: c.get('stats', dict(n=0)) for s, c in cells.items()}
        cand = rule2(st, seeds)
        note = ''
        if status == 'INVALID':
            note = 'no candidate: INVALID (rule 3, the packed policy stays)'
        elif status == 'INCOMPLETE':
            note = ('no candidate until VERIFIED' + (f'; retrain only seeds {retrain} on a new box (same reference and '
                                                     f'commit; rule 2 as amended 31 Oct)' if retrain else '')
                    + ('; re-run this tool once the unchecked files are there' if unchecked else ''))
        ent = dict(status=status, seeds={s: dict(st[s], eval_timeouts=cells[s]['eval_timeouts'],
                                                 checkpoint=cells[s].get('checkpoint'),
                                                 **({'main_eval_timeout': cells[s]['main_eval_timeout']} if 'main_eval_timeout' in cells[s] else {}))
                                         for s in seeds},
                   rule2_candidate=cand if status == 'VERIFIED' else None, missing=missing, thin=thin,
                   unchecked=unchecked, retrain_seeds=retrain, min_n=MIN_N, note=note)
        if status == 'VERIFIED' and cand:
            if a.mode == 'glock':
                ent['runs_extra'] = f'{a.run}@refs/mass1_sf/ep{e},refs/mass1s{cand}_glockt/ep{e}'
                ent['pick_extra'] = f'{e}:{a.run}:ck=results/mass1s{cand}_glock_public/ep{e}/best/policy.safetensors'
            else:
                rel = os.path.relpath(os.path.realpath(cells[cand]['checkpoint']), os.path.realpath(C))   # runs/perc2mcks/...
                ent['runs_extra'] = f'{a.run}@refs/perc2mcks/ep{e}'
                ent['pick_extra'] = f'{e}:{a.run}:ck={rel}'
                if T.get('pieces') and T['pieces'] not in H5_PIECES:
                    ent['asset_pieces_extra'] = f'/content/v2d-track3/{T["pieces"]}'
        S['episodes'][e] = ent
    ok = [e for e, x in S['episodes'].items() if x.get('pick_extra')]
    S['confirmation'] = dict(
        RUNS_EXTRA=' '.join(S['episodes'][e]['runs_extra'] for e in ok), PICK_EXTRA=' '.join(S['episodes'][e]['pick_extra'] for e in ok),
        MASS_EPS=' '.join(ok), EVAL_ONLY=' '.join(ok), EPS_ONLY=' '.join(ok),
        MA_ARGS='--physics /content/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json' if a.mode == 'std' and ok else '',
        ASSET_PIECES_EXTRA=' '.join(sorted({S['episodes'][e]['asset_pieces_extra'] for e in ok if S['episodes'][e].get('asset_pieces_extra')})),
        note='strings for ops/jobs/h5_reeval.sh (PLAN section 5 rule 4); merge boxes by joining their strings; a std '
             'candidate needs MA_ARGS, and no unchanged std episode may be evaluated beside it (KEEP_RESULTS + EVAL_ONLY)')
    V['ok'] = all(x['status'] == 'VERIFIED' for x in V['episodes'].values())
    json.dump(V, open(a.out, 'w'), indent=1); json.dump(S, open(a.summary, 'w'), indent=1)
    for e, x in V['episodes'].items():
        s_ = S['episodes'][e]
        print(f'ep{e} {x["status"]}' + (f' ({len(x["failures"])} failures: ' + ' | '.join(x['failures'][:4]) + ')' if x['failures'] else '')
              + (f' missing {x["missing"]}' if x['missing'] else '') + (f' unchecked {x["unchecked"]}' if x['unchecked'] else '')
              + (f' main evaluation cut {x["main_eval_timeout"]}' if x['main_eval_timeout'] else '')
              + (f' thin (n < {MIN_N}) {x["thin"]}' if x['thin'] else '')
              + (f' retrain seeds {x["retrain_seeds"]}' if x['retrain_seeds'] else '')
              + ' :: ' + '; '.join(f's{s} n {v.get("n")} mean {v.get("mean")} sd {v.get("sd")} min {v.get("min")} cut {v["eval_timeouts"]["best"]["cut"]}/{v["eval_timeouts"]["curve"]["cut"]}'
                                   for s, v in s_['seeds'].items())
              + f' :: candidate {s_["rule2_candidate"]}'
              + ' :: loads ' + '; '.join(f's{s} ' + ','.join(f'{n} {u["mass"]}' for n, u in c.get('loaded_urdfs', {}).items())
                                         for s, c in x['cells'].items()))
    print('confirmation: ' + json.dumps({k: v for k, v in S['confirmation'].items() if k != 'note'}))
    sys.exit(0 if V['ok'] else 1)


if __name__ == '__main__':
    main()
