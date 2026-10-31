"""Checks of the ep11 rollout gate (2026-10-31; ops/jobs/ep11_gate.sh; pre-registered in
docs/research/work/perception-sprint-20261031/ep11gate/PREREG.md sections 2.2 and 2.6). Nothing here reads ground truth.

  b0      the two refined tracks rebuilt on the box (tools/e11g_tracks.sh OUT: C/ep11, T/ep11) vs the CPU outputs committed
          in ep11gate/expect/ (expect.json + C_poses.npz, T_poses.npz; used only for this comparison, never as an input).
          Per arm over every frame and object: IDENTICAL (same md5) | NUMERIC (world_T_cam byte-identical, every object
          pose within 0.01 mm and 0.001 deg) | DIFFERS (arm T only: within 5 mm and 2 deg; MuJoCo's settle need not be
          bit-reproducible on another machine) | MISMATCH. Exit 0 when every arm may go on, 2 otherwise.
  arms    after glock_public.sh REF_ONLY=1 built refs/perc2<arm>_glockt/ep<N> once per arm: byte copies per seed
          (refs/perc2<arm>s<seed>_glockt/ep<N>/<hive>/ref_gl_ilc.parquet, the only .parquet there), the base reference link
          refs/perc2<arm>s<seed><base>/ep<N> -> refs/perc2<arm><base>/ep<N>, and results/perc2<arm>s<seed>_glock_public/
          ep<N>/{rest_check.json, zero_score.txt}, so glock_public.sh REUSE_REF=1 REQUIRE_REUSE=1 trains each seed in its own
          folders on its arm's one reference. Never moves or deletes an existing results folder (a re-run keeps the other
          cells' results). Refuses arms whose references name different URDF files (md5) or not the 0.3 kg placeholder.
          --expect_manifest (re-run): every copy and URDF must equal the earlier run's manifest.
  verify  after training (any failure -> the verdict is INVALID; a cell without a chosen checkpoint is "missing" ->
          INCOMPLETE): B0 bands; each arm's mkref read its own rebuilt track (md5 before = after = B0's) and both arms the
          same depth cache and hands; arm identity by content (each arm's trained reference carries its own track's blue cup
          in the nest window better than the other arm's); per cell the chain the official evaluator loads (checkpoint
          config task.parquet -> the arm x seed copy, md5 = the arm's reference -> object_urdf_paths -> the same URDFs in
          both arms, 0.3 kg); per seed the two arms' saved configs differ only in output_dir / task.parquet /
          reference.parquet or by the arm's name (tools/mass_verify.py pair_diff); reset.seed; steps; evaluated checkpoint
          sha256; evaluation timeouts counted (reported, not a failure). --prior VERIFY.json (re-run): timeouts of cells
          whose evaluation folders were not pulled are taken from the earlier run.
Usage:
  e11g_verify.py b0 --tracks OUT --expect DIR --out B0.json
  e11g_verify.py arms --content /content --arms "e11c e11t" --seeds "42 43" --base mck --out ARMS.json [--expect_manifest M]
  e11g_verify.py verify --content /content --arms "e11c e11t" --seeds "42 43" --base mck --steps 70004736 --gate G --out V.json
                 [--prior PRIOR_VERIFY.json]   (G = results/ep11_gate: b0.json, build_<arm>.json, arms.json, tracks/)
"""
import argparse, glob, hashlib, json, os, shutil, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import read_inertial, traj_fingerprint, md5                                   # noqa: E402
from mass_verify import ck_config, resolve_parquet, resolve_asset, flat, pair_diff, eval_timeouts, STEPS_KEY   # noqa: E402

EP = 11
TRK = {'e11c': 'C', 'e11t': 'T'}                     # arm -> track folder of tools/e11g_tracks.sh
NUM_MM, NUM_DEG, DIF_MM, DIF_DEG = 0.01, 0.001, 5.0, 2.0
PLACEHOLDER = 0.3
WINDOW = (42, 137)                                   # S12's ep11 nest window (mask10; GT-free) for the identity check


def world(npz):
    """{object: (T,4,4) float64 world pose} and world_T_cam of a perception/refine poses.npz."""
    z = np.load(npz); W = z['world_T_cam']
    return {k[6:]: W.astype(float) @ z[k].astype(float) for k in z.files if k.startswith('cam_T_')}, W


def compare(a, b):
    """Per object: frames differing, max translation (mm) and rotation (deg) between two poses.npz; world_T_cam equal."""
    A, wa = world(a); B, wb = world(b); out = dict(world_T_cam_identical=bool(wa.shape == wb.shape and np.array_equal(wa, wb)),
                                                   objects={})
    if sorted(A) != sorted(B) or any(A[k].shape != B[k].shape for k in A):
        out['shape_mismatch'] = True; return out
    for k in A:
        dt = np.linalg.norm(A[k][:, :3, 3] - B[k][:, :3, 3], axis=1) * 1000
        R = np.einsum('tij,tkj->tik', A[k][:, :3, :3], B[k][:, :3, :3])
        # small angles from the skew part (exactly 0 for equal float32 matrices, which are not exactly orthonormal: the
        # arccos of the trace reads ~0.02 deg there); arccos of the trace above ~11 deg
        cs = np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1)
        sk = np.linalg.norm(np.stack([R[:, 2, 1] - R[:, 1, 2], R[:, 0, 2] - R[:, 2, 0], R[:, 1, 0] - R[:, 0, 1]], 1), axis=1) / 2
        ang = np.degrees(np.where(cs < 0.98, np.arccos(cs), np.arcsin(np.clip(sk, 0, 1))))
        z = np.load(a)[f'cam_T_{k}'], np.load(b)[f'cam_T_{k}']
        out['objects'][k] = dict(frames_differing=int((~np.all(z[0] == z[1], axis=(1, 2))).sum()),
                                 max_mm=round(float(dt.max()), 6), max_deg=round(float(ang.max()), 6))
    return out


def band(same_md5, c, allow_differs):
    if same_md5:
        return 'IDENTICAL'
    if c.get('shape_mismatch'):
        return 'MISMATCH'
    mm = max(o['max_mm'] for o in c['objects'].values()); dg = max(o['max_deg'] for o in c['objects'].values())
    if c['world_T_cam_identical'] and mm <= NUM_MM and dg <= NUM_DEG:
        return 'NUMERIC'
    if allow_differs and c['world_T_cam_identical'] and mm <= DIF_MM and dg <= DIF_DEG:
        return 'DIFFERS'
    return 'MISMATCH'


def cmd_b0(a):
    exp = json.load(open(f'{a.expect}/expect.json')); res = dict(expect=os.path.abspath(a.expect), arms={},
                                                                  bands=dict(numeric_mm=NUM_MM, numeric_deg=NUM_DEG, differs_mm=DIF_MM, differs_deg=DIF_DEG))
    try:
        res['tracks_json'] = json.load(open(f'{a.tracks}/tracks.json'))
    except Exception as e:
        res['tracks_json'] = dict(error=repr(e)[:200])
    for arm, t in TRK.items():
        f = f'{a.tracks}/{t}/ep{EP}/poses.npz'; r = res['arms'][arm] = dict(track=t, poses=f)
        if not os.path.isfile(f):
            r.update(band='MISMATCH', why='no rebuilt track'); continue
        r['md5_box'] = md5(f); r['md5_expected'] = exp['tracks'][t]['poses.npz']
        c = compare(f, f'{a.expect}/{t}_poses.npz'); r['compare'] = c
        r['md5_expected_file'] = md5(f'{a.expect}/{t}_poses.npz')
        if r['md5_expected_file'] != r['md5_expected']:
            r.update(band='MISMATCH', why='committed expected file does not match expect.json'); continue
        r['band'] = band(r['md5_box'] == r['md5_expected'], c, allow_differs=(t == 'T'))
    res['go'] = all(r['band'] in ('IDENTICAL', 'NUMERIC', 'DIFFERS') for r in res['arms'].values())
    json.dump(res, open(a.out, 'w'), indent=1)
    print(('GO' if res['go'] else 'STOP') + ': ' + '; '.join(
        f"{arm} {r['band']}" + (f" (max {max(o['max_mm'] for o in r['compare']['objects'].values()):.4f} mm, "
                                f"{max(o['max_deg'] for o in r['compare']['objects'].values()):.4f} deg)"
                                if r.get('compare', {}).get('objects') and r['band'] != 'IDENTICAL' else '')
        + f" md5 {r.get('md5_box')}" for arm, r in res['arms'].items()))
    sys.exit(0 if res['go'] else 2)


def urdfs_of(pqf):
    import pyarrow.parquet as pq
    t = pq.read_table(pqf); out = {}
    for n, u in zip(t.column('object_body_names')[0].as_py(), t.column('object_urdf_paths')[0].as_py()):
        m, com, _ = read_inertial(open(u).read()) if os.path.isfile(u) else (None, None, None)
        out[n] = dict(urdf=u, md5=md5(u) if os.path.isfile(u) else None, mass=m, com=com)
    return out, traj_fingerprint(t)


def jsonish(f):
    """A JSON file, or its text when it is not JSON (rest_check.py's output file also holds its stderr)."""
    try:
        return json.load(open(f))
    except Exception:
        return dict(raw=open(f, errors='replace').read()[-600:])


def cmd_arms(a):
    C = a.content.rstrip('/'); man = dict(episode=EP, base=a.base, arms={}); ex = json.load(open(a.expect_manifest)) if a.expect_manifest else None
    fails, warns = [], []
    for arm in a.arms.split():
        src = glob.glob(f'{C}/refs/perc2{arm}_glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')
        if len(src) != 1:
            sys.exit(f'arms {arm}: {len(src)} finished references under refs/perc2{arm}_glockt/ep{EP} (one expected)')
        src = src[0]; R0 = f'{C}/refs/perc2{arm}{a.base}/ep{EP}'
        hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/perc2{arm}_glockt/ep{EP}')
        base_pq = glob.glob(f'{R0}/{hive}/*.parquet')
        if len(base_pq) != 1:
            sys.exit(f'arms {arm}: {len(base_pq)} base references under {R0}/{hive}')
        res0 = f'{C}/results/perc2{arm}_glock_public/ep{EP}'
        if not os.path.isfile(f'{res0}/rest_check.json'):
            sys.exit(f'arms {arm}: {res0}/rest_check.json missing (glock_public.sh REUSE_REF needs it)')
        urd, fp = urdfs_of(src)
        for n, u in urd.items():
            if u['md5'] is None:
                fails.append(f'{arm}: {n} URDF {u["urdf"]} missing')
            elif abs(u['mass'] - PLACEHOLDER) > 1e-9:
                fails.append(f'{arm}: {n} mass {u["mass"]} != {PLACEHOLDER}')
        m = man['arms'][arm] = dict(source_parquet=src, source_md5=md5(src), traj_fingerprint=fp, hive=hive,
                                    base_parquet=base_pq[0], base_md5=md5(base_pq[0]), urdfs=urd,
                                    zero_score=open(f'{res0}/zero_score.txt').read().strip()[-400:] if os.path.isfile(f'{res0}/zero_score.txt') else None,
                                    rest_check=jsonish(f'{res0}/rest_check.json'),
                                    seeds={})
        for s in a.seeds.split():
            pre = f'perc2{arm}s{s}'; RD = f'{C}/refs/{pre}_glockt/ep{EP}'; dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'
            os.makedirs(os.path.dirname(dpq), exist_ok=True)
            if not (os.path.isfile(dpq) and md5(dpq) == m['source_md5']):
                shutil.copyfile(src, dpq)
            n_pq = len(glob.glob(f'{RD}/**/*.parquet', recursive=True))
            if n_pq != 1:
                sys.exit(f'arms: {RD} holds {n_pq} parquet files (FlashCHORD needs exactly one)')
            lk = f'{C}/refs/{pre}{a.base}/ep{EP}'; os.makedirs(os.path.dirname(lk), exist_ok=True)
            if os.path.islink(lk):
                os.remove(lk)
            elif os.path.lexists(lk):
                sys.exit(f'arms: {lk} exists and is not a link')
            os.symlink(R0, lk)
            O = f'{C}/results/{pre}_glock_public/ep{EP}'; os.makedirs(O, exist_ok=True)   # never moved: a re-run keeps best/
            for f in ('rest_check.json', 'zero_score.txt'):
                if os.path.exists(f'{res0}/{f}'):
                    shutil.copy(f'{res0}/{f}', f'{O}/{f}')
            m['seeds'][s] = dict(parquet=dpq, md5=md5(dpq), base_link=lk, results=O, pair=f'{EP}:local:{a.base}:{pre}')
    names = [sorted((n, u['urdf'], u['md5']) for n, u in v['urdfs'].items()) for v in man['arms'].values()]
    if any(x != names[0] for x in names[1:]):
        fails.append(f'the arms name different URDFs: {names}')
    if ex:
        for arm, v in man['arms'].items():
            e = ex['arms'].get(arm, {})
            if v['source_md5'] != e.get('source_md5') or v['base_md5'] != e.get('base_md5'):
                fails.append(f'{arm}: reference differs from the earlier run (source {v["source_md5"]} vs {e.get("source_md5")}, base {v["base_md5"]} vs {e.get("base_md5")})')
            for n, u in v['urdfs'].items():                     # make_assets.py rebuilt /content/assets on this box
                eu = e.get('urdfs', {}).get(n)
                if not eu or u['md5'] == eu['md5']:
                    if not eu:
                        fails.append(f'{arm}: {n} not in the earlier run\'s manifest')
                    continue
                if u['mass'] != eu['mass'] or u['com'] != eu['com']:   # inertial text differs: a real difference
                    fails.append(f'{arm}: {n} URDF differs from the earlier run (mass {u["mass"]} vs {eu["mass"]}, COM {u["com"]} vs {eu["com"]})')
                else:
                    warns.append(f'{arm}: {n} URDF bytes differ from the earlier run, same mass and COM')
    man['ok'] = not fails; man['failures'] = fails; man['warnings'] = warns
    json.dump(man, open(a.out, 'w'), indent=1)
    print(('ARMS OK' if not fails else 'ARMS FAILED: ' + ' | '.join(fails[:5])) + ' :: ' + '; '.join(
        f"{arm}: reference {v['source_md5']} (fingerprint {v['traj_fingerprint'][:12]}), base {v['base_md5']}, "
        + ', '.join(f"{n} {u['mass']} kg" for n, u in v['urdfs'].items()) for arm, v in man['arms'].items()))
    sys.exit(0 if not fails else 1)


def ref_track(pqf):
    """{object: (T,3)} object positions of a reference parquet (table frame)."""
    import pyarrow.parquet as pq
    t = pq.read_table(pqf, columns=['object_body_names', 'object_body_position', 'robot_left_wrist_position'])
    names = t.column('object_body_names')[0].as_py()
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    pos = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    return {n: pos[:, i] for i, n in enumerate(names)}


def med_cm(p, q, lo=WINDOW[0], hi=WINDOW[1]):
    n = min(len(p), len(q)); hi = min(hi, n)
    return round(float(np.median(np.linalg.norm(p[lo:hi] - q[lo:hi], axis=-1))) * 100, 3)


def identity(C, arms, base, tracks):
    """Arm identity by content (cm, median over the S12 window f42-136):
      e2s:     the arm's mkref output before contact retargeting (refs/perc2<arm><base>/ep11/e2s_reference.parquet; the
               track in mkref's table frame plus a constant per-object snap) vs both rebuilt tracks mapped by that arm's
               table frame: the blue cup must be closer to its own track (hard check);
      trained: the arm's grasp-lock reference vs both arms' base references (after contact retargeting), both cups: not
               farther from its own (hard check);
      arms_apart: the two trained references' blue-cup distance over the window and over the hands-off frames f101-136
               (reported: if contact retargeting's rest settle had erased the treatment, this would be ~0)."""
    out, trained = {}, {}
    for arm in arms:
        r = out[arm] = {}
        try:
            R = f'{C}/refs/perc2{arm}{base}/ep{EP}'; Tt = np.load(f'{R}/table_frame.npz')['T_table_from_world']
            e2s = ref_track(f'{R}/e2s_reference.parquet')['blue_cup']; e = {}
            for other, t in TRK.items():
                W, _ = world(f'{tracks}/{t}/ep{EP}/poses.npz'); p = (Tt[:3, :3] @ W['blue_cup'][:, :3, 3].T).T + Tt[:3, 3]
                e[other] = med_cm(p, e2s)
            r['e2s_vs_tracks_cm'] = e; r['e2s_ok'] = bool(e[arm] < min(v for k, v in e.items() if k != arm))
            trained[arm] = ref_track(glob.glob(f'{C}/refs/perc2{arm}_glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')[0]); e = {}
            for other in arms:
                b = ref_track(glob.glob(f'{C}/refs/perc2{other}{base}/ep{EP}/processed/*/*/*.parquet')[0])
                e[other] = round(sum(med_cm(trained[arm][n], b[n]) for n in ('blue_cup', 'beige_cup')), 3)
            r['trained_vs_bases_cm'] = e; r['trained_ok'] = bool(e[arm] <= min(v for k, v in e.items() if k != arm))
            r['ok'] = r['e2s_ok'] and r['trained_ok']
        except Exception as x:
            r.update(ok=False, error=f'{type(x).__name__}: {str(x)[:200]}')
    if len(trained) == 2:
        a0, a1 = list(trained)
        out['arms_apart_blue_cm'] = dict(window=med_cm(trained[a0]['blue_cup'], trained[a1]['blue_cup']),
                                         hands_off_f101_136=med_cm(trained[a0]['blue_cup'], trained[a1]['blue_cup'], 101, 137))
        # review F4 (31 Oct): the beige cup too (rest settle can bring the blue cups together while the beige still differs)
        out['arms_apart_beige_cm'] = dict(window=med_cm(trained[a0]['beige_cup'], trained[a1]['beige_cup']),
                                          hands_off_f101_136=med_cm(trained[a0]['beige_cup'], trained[a1]['beige_cup'], 101, 137))
    return out


def cmd_verify(a):
    C = a.content.rstrip('/'); G = a.gate.rstrip('/'); arms = a.arms.split(); seeds = a.seeds.split()
    fails, cells, cfgs, missing = [], {}, {}, []
    js = lambda f: json.load(open(f)) if os.path.isfile(f) else None
    b0, man = js(f'{G}/b0.json'), js(f'{G}/arms.json'); prior = js(a.prior) if a.prior else None
    # B0 and the reference build inputs
    if not b0:
        fails.append('b0.json missing')
    else:
        for arm in arms:
            bd = b0['arms'].get(arm, {}).get('band')
            if bd not in ('IDENTICAL', 'NUMERIC', 'DIFFERS') or (bd == 'DIFFERS' and arm != 'e11t'):
                fails.append(f'{arm}: B0 band {bd}')
    builds = {arm: js(f'{G}/build_{arm}.json') for arm in arms}
    for arm, bdj in builds.items():
        if not bdj:
            fails.append(f'{arm}: build_{arm}.json missing'); continue
        m_b0 = (b0 or {}).get('arms', {}).get(arm, {}).get('md5_box')
        if bdj.get('rc') != 0:
            fails.append(f'{arm}: reference build rc {bdj.get("rc")}')
        if not (bdj.get('poses_md5_before') == bdj.get('poses_md5_after') == m_b0):
            fails.append(f'{arm}: mkref input track md5 {bdj.get("poses_md5_before")}/{bdj.get("poses_md5_after")} != B0 {m_b0}')
        if os.path.realpath(bdj.get('depth') or '') != os.path.realpath(bdj.get('depth_expected') or '-'):
            fails.append(f'{arm}: mkref depth {bdj.get("depth")} is not the ep11 cache')
    if all(builds.values()):
        for k in ('depth', 'hands_md5', 'hands_refined_md5', 'mkref_args', 'cr_args'):
            if len({json.dumps(b.get(k)) for b in builds.values()}) != 1:
                fails.append(f'the arms\' reference builds differ in {k}')
    if not man or not man.get('ok'):
        fails.append('arms.json missing or not ok')
    ident = identity(C, arms, a.base, f'{G}/tracks')
    for arm in arms:
        if not ident.get(arm, {}).get('ok'):
            fails.append(f'{arm}: identity check failed {ident.get(arm)}')
    # cells: the chain the official evaluator loads
    urdf_sets = {}
    for arm in arms:
        for s in seeds:
            key = f'{arm}/s{s}'; row = cells[key] = {}
            O = f'{C}/results/perc2{arm}s{s}_glock_public/ep{EP}'; ck = f'{O}/best/policy.safetensors'
            row['eval_timeouts'] = eval_timeouts(O)
            if not row['eval_timeouts']['best_runs'] and prior and key in prior.get('cells', {}):
                row['eval_timeouts'] = prior['cells'][key].get('eval_timeouts'); row['eval_timeouts_from'] = 'prior run'
            if not (os.path.exists(f'{O}/best/summary.json') and os.path.exists(ck)):
                row['missing'] = True; missing.append(key); continue
            try:
                summ = json.load(open(f'{O}/best/summary.json')); row['checkpoint'] = summ.get('checkpoint')
                if row['checkpoint'] and os.path.exists(row['checkpoint']) and md5(row['checkpoint']) != md5(ck):
                    fails.append(f'{key}: best/policy.safetensors is not the checkpoint the summary names')
                meta, cfg = ck_config(ck); cfgs[key] = cfg
                row['checkpoint_steps'] = meta.get('user.environment_steps')
                task = cfg['task']['parquet']; row['task_parquet'] = task
                rp = resolve_parquet(task); row['reference_file'] = rp; row['reference_md5'] = md5(rp)
                want_dir = os.path.realpath(f'{C}/refs/perc2{arm}s{s}_glockt/ep{EP}') + '/'
                if not os.path.realpath(rp).startswith(want_dir):
                    fails.append(f'{key}: trained on {rp}, not this cell\'s copy under {want_dir}')
                src_md5 = ((man or {}).get('arms', {}).get(arm) or {}).get('source_md5')
                if row['reference_md5'] != src_md5:
                    fails.append(f'{key}: reference md5 {row["reference_md5"]} != the arm\'s grasp-lock reference {src_md5}')
                urd, _ = urdfs_of(rp); row['loaded_urdfs'] = urd
                for n, u in urd.items():
                    p, how = resolve_asset(u['urdf'])
                    if p is None:
                        fails.append(f'{key}: {n}: {u["urdf"]} {how}')
                    elif abs(u['mass'] - PLACEHOLDER) > 1e-9:
                        fails.append(f'{key}: {n} loads {u["mass"]} kg')
                urdf_sets[key] = sorted((n, u['urdf'], u['md5']) for n, u in urd.items())
                row['reset_seed'] = cfg.get('reset', {}).get('seed')
                if str(row['reset_seed']) != str(s):
                    fails.append(f'{key}: reset.seed {row["reset_seed"]} != {s}')
                st = flat(cfg).get(STEPS_KEY); row['total_environment_steps'] = st
                if str(st) != str(a.steps):
                    fails.append(f'{key}: {STEPS_KEY} {st} != {a.steps}')
                sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest(); ev = 0
                for f in sorted(glob.glob(f'{O}/best/r*/episode_*.json')):
                    d = json.load(open(f)); ev += 1
                    if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != sha:
                        fails.append(f'{key}: {f} evaluated checkpoint sha256 {d["checkpoint_sha256"][:12]} != chosen {sha[:12]}')
                row['evaluations_checked'] = ev; row['checkpoint_sha256'] = sha
            except Exception as e:
                row['error'] = f'{type(e).__name__}: {str(e)[:200]}'; fails.append(f'{key}: {row["error"]}')
    if len({json.dumps(v) for v in urdf_sets.values()}) > 1:
        fails.append('cells load different URDF files')
    pairs, arm_named = {}, {}
    for s in seeds:
        ks = [f'{arm}/s{s}' for arm in arms]
        if all(k in cfgs for k in ks):
            d, dn = {}, {}
            for k in ks[1:]:
                d[k], dn[k], bad = pair_diff(cfgs[ks[0]], cfgs[k], f'perc2{ks[0].split("/")[0]}s{s}', f'perc2{k.split("/")[0]}s{s}')
                if bad:
                    fails.append(f'{ks[0]} vs {k}: saved configs differ in {bad[:8]}')
            pairs[f's{s}'] = d; arm_named[f's{s}'] = dn
        elif not any(k in missing for k in ks):
            fails.append(f's{s}: not every arm has a chosen checkpoint')
    tmo = {k: c['eval_timeouts'] for k, c in cells.items() if c.get('eval_timeouts') and
           (c['eval_timeouts'].get('best') or c['eval_timeouts'].get('curve') or c['eval_timeouts'].get('best_without_rc'))}
    out = dict(ok=not fails, failures=fails, missing=missing, b0_bands={arm: (b0 or {}).get('arms', {}).get(arm, {}).get('band') for arm in arms},
               identity=ident, builds=builds, pair_config_differences=pairs, pair_config_equal_after_arm_name=arm_named,
               eval_timeouts=tmo, cells=cells, rule='docs/research/work/perception-sprint-20261031/ep11gate/PREREG.md')
    json.dump(out, open(a.out, 'w'), indent=1)
    print(('VERIFIED' if out['ok'] else f'VERIFY FAILED ({len(fails)}): ' + ' | '.join(fails[:6]))
          + (f' :: MISSING cells (no chosen checkpoint; INCOMPLETE unless a failure above): {missing}' if missing else '')
          + f" :: B0 {out['b0_bands']} :: identity " + '; '.join(f"{k} e2s {ident.get(k, {}).get('e2s_vs_tracks_cm')} trained {ident.get(k, {}).get('trained_vs_bases_cm')}" for k in arms)
          + f" :: trained references' blue cups apart {ident.get('arms_apart_blue_cm')} cm"
          + ' :: eval timeouts: ' + ('; '.join(f'{k} best {v.get("best")}/{v.get("best_runs")} curve {v.get("curve")}/{v.get("curve_runs")}'
                                              for k, v in tmo.items()) or 'none'))
    sys.exit(0 if out['ok'] else 1)


UNTESTABLE_CM = 0.5   # review proposal (31 Oct) [H]: both cups' trained references this close over the S12 window = no S12 left


def cmd_identity_pre(a):
    """Arm identity before training (review F3/F4, 31 Oct; PREREG section 7): identity() on the trained-reference stages
    that exist after the arm copies. Exit 1 (the job stops before any training) if an arm fails its content checks, or
    UNTESTABLE: both cups' trained references within UNTESTABLE_CM of each other over the S12 window."""
    arms = a.arms.split()
    r = identity(a.content.rstrip('/'), arms, a.base, a.tracks)
    bad = [x for x in arms if not (r.get(x) or {}).get('ok')]
    apart = [(r.get(k) or {}).get('window') for k in ('arms_apart_blue_cm', 'arms_apart_beige_cm')]
    untestable = None not in apart and all(x < UNTESTABLE_CM for x in apart)
    ok = not bad and not untestable and None not in apart
    r['pre_training'] = dict(bad_arms=bad, untestable=untestable, untestable_cm=UNTESTABLE_CM, ok=ok)
    json.dump(r, open(a.out, 'w'), indent=1, default=str)
    print(('GO' if ok else 'UNTESTABLE' if untestable else 'STOP') + f': bad arms {bad}, apart window blue/beige cm {apart}')
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('b0'); b.add_argument('--tracks', required=True); b.add_argument('--expect', required=True); b.add_argument('--out', required=True)
    r = sp.add_parser('arms')
    v = sp.add_parser('verify')
    i = sp.add_parser('identity_pre')
    for p in (r, v):
        p.add_argument('--content', default='/content'); p.add_argument('--arms', default='e11c e11t'); p.add_argument('--seeds', default='42 43')
        p.add_argument('--base', default='mck'); p.add_argument('--out', required=True)
    i.add_argument('--content', default='/content'); i.add_argument('--arms', default='e11c e11t'); i.add_argument('--base', default='mck')
    i.add_argument('--tracks', required=True); i.add_argument('--out', required=True)
    r.add_argument('--expect_manifest', default=None)
    v.add_argument('--steps', type=int, required=True); v.add_argument('--gate', required=True); v.add_argument('--prior', default=None)
    a = ap.parse_args()
    dict(b0=cmd_b0, arms=cmd_arms, verify=cmd_verify, identity_pre=cmd_identity_pre)[a.cmd](a)


if __name__ == '__main__':
    main()
