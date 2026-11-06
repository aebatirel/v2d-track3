"""Checks and seed choice of the eval-10 V4p retrain (2026-10-31; ops/jobs/ev10_v4p.sh; pre-registered in
docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md sections 3 and 6). Eval 10: no ground truth exists
or is read. One arm (prefix perc2e10v: the V4p reference), seeds 42 and 43.

  b0      the V4p track rebuilt on the box (tools/e10v_track.sh OUT: V/ep10) vs the CPU rebuild committed in
          ev10retrain/expect/ (expect.json + V_poses.npz; only for this comparison, never an input): IDENTICAL | NUMERIC |
          DIFFERS (within 5 mm / 2 deg) | MISMATCH (tools/e11g_verify.py's compare / band). Exit 0 = go on, 2 = stop.
  arms    after glock_public.sh REF_ONLY=1 built refs/perc2e10v_glockt/ep10 once: byte copies per seed
          refs/perc2e10vs<seed>_glockt/ep10/<hive>/ref_gl_ilc.parquet (the only .parquet there), base links
          refs/perc2e10vs<seed>mck/ep10 -> refs/perc2e10vmck/ep10 and results/perc2e10vs<seed>_glock_public/ep10/
          {rest_check.json, zero_score.txt} (REUSE_REF / REQUIRE_REUSE). URDFs must exist and load 0.3 kg.
          --expect_manifest (re-run): the copies must equal the earlier run's manifest.
  identity  identity by content (PREREG 6): the pre-contact-retargeting mkref output refs/perc2e10vmck/ep10/
          e2s_reference.parquet carries the V4p track's blue cup over the S12 window [53, 161): closer to the V4p track
          than to the stored (unrefined) track, both mapped by that reference's table frame. Reported: the trained V vs
          the packed reference P (both cups, window and hands-off f122-160). Exit 1 on failure.
  choose  rule 2 (PREREG 3.4): per seed the NREP training-box rollouts (best/r*/qa_policy.json sim_vs_ref vs V, finite
          only); over seeds with >= 8, the higher mean; within 0.005 (4-decimal means) the lower sd (ddof 1); still tied,
          the first seed (42). Both seeds needed: a missing / thin seed -> INCOMPLETE (exit 1, no choice).
  verify  after scoring (any failure -> INVALID): B0 band; the reference build (rc 0; mkref read the B0 track: md5
          before = after = B0's; the chosen depth cache: realpath and frame-0 sha256; the stored hands md5); arms.json ok;
          identity; per seed the chain the official evaluator loads (saved config task.parquet -> the seed copy, md5 =
          V's -> object_urdf_paths -> URDFs, 0.3 kg, the same files in both seeds), reset.seed, steps, the training-box
          rollouts name the chosen checkpoint; the saved config equals the PACKED checkpoint's (--packed_ck) in every key
          but output_dir, task.parquet, reference.parquet, reset.seed, env.reset.seed, training.seed; every confirmation
          draw names the chosen checkpoint's sha256; every scored rollout's own-reference check (score json).
          Missing seeds / thin draw counts are NOT failures (INCOMPLETE, e10v_verdict.py).
Usage:
  e10v_verify.py b0 --tracks OUT --expect DIR --out B0.json
  e10v_verify.py arms --content /content --seeds "42 43" --out ARMS.json [--expect_manifest M]
  e10v_verify.py identity --content /content --track V/ep10/poses.npz --stored IN/poses.npz --packed_ref P.parquet --out I.json
  e10v_verify.py choose --content /content --seeds "42 43" --out CHOICE.json
  e10v_verify.py verify --content /content --seeds "42 43" --steps 70004736 --dir G --packed_ck CK --out V.json
                 (G = results/ev10_v4p: b0.json, build.json, depth_check.json, arms.json, identity.json, choice.json,
                  conf/, score*.json)
"""
import argparse, glob, hashlib, json, math, os, shutil, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import md5                                                                  # noqa: E402
from mass_verify import ck_config, resolve_parquet, resolve_asset, flat, eval_timeouts, STEPS_KEY   # noqa: E402
from e11g_verify import compare, band, world, urdfs_of, jsonish, ref_track              # noqa: E402

EP, PRE, BASE = 10, 'perc2e10v', 'mck'
PLACEHOLDER = 0.3
WINDOW = (53, 161)                      # S12's eval-10 nest window (mask10 / expect.json; GT-free)
HANDS_OFF = (122, 161)                  # nest_physics's settled run on eval 10 (expect.json)
ALLOWED = {'output_dir', 'task.parquet', 'reference.parquet', 'reset.seed', 'env.reset.seed', 'training.seed'}
HANDS_MD5 = dict(hands='15196aaf02dd9fa7c0b076ccd0e4c463', hands_refined='419c230800b727240663597916cba59e')
MIN_N = 8


def cmd_b0(a):
    exp = json.load(open(f'{a.expect}/expect.json')); f = f'{a.tracks}/V/ep{EP}/poses.npz'
    r = dict(track='V', poses=f, expect=os.path.abspath(a.expect))
    try:
        r['tracks_json'] = json.load(open(f'{a.tracks}/tracks.json'))
    except Exception as e:
        r['tracks_json'] = dict(error=repr(e)[:200])
    if not os.path.isfile(f):
        r.update(band='MISMATCH', why='no rebuilt track')
    else:
        r['md5_box'] = md5(f); r['md5_expected'] = exp['tracks']['V']['poses.npz']; r['md5_expected_file'] = md5(f'{a.expect}/V_poses.npz')
        r['compare'] = c = compare(f, f'{a.expect}/V_poses.npz')
        if r['md5_expected_file'] != r['md5_expected']:
            r.update(band='MISMATCH', why='committed expected file does not match expect.json')
        else:
            r['band'] = band(r['md5_box'] == r['md5_expected'], c, allow_differs=True)
    r['go'] = r['band'] in ('IDENTICAL', 'NUMERIC', 'DIFFERS')
    json.dump(r, open(a.out, 'w'), indent=1)
    ob = (r.get('compare') or {}).get('objects') or {}
    print(('GO' if r['go'] else 'STOP') + f": V {r['band']}" + (f" (max {max(o['max_mm'] for o in ob.values()):.4f} mm, "
          f"{max(o['max_deg'] for o in ob.values()):.4f} deg)" if ob and r['band'] != 'IDENTICAL' else '') + f" md5 {r.get('md5_box')}")
    sys.exit(0 if r['go'] else 2)


def cmd_arms(a):
    C = a.content.rstrip('/'); ex = json.load(open(a.expect_manifest)) if a.expect_manifest else None; fails = []
    src = glob.glob(f'{C}/refs/{PRE}_glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')
    if len(src) != 1:
        sys.exit(f'arms: {len(src)} finished references under refs/{PRE}_glockt/ep{EP} (one expected)')
    src = src[0]; R0 = f'{C}/refs/{PRE}{BASE}/ep{EP}'; hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/{PRE}_glockt/ep{EP}')
    base_pq = glob.glob(f'{R0}/{hive}/*.parquet')
    if len(base_pq) != 1:
        sys.exit(f'arms: {len(base_pq)} base references under {R0}/{hive}')
    res0 = f'{C}/results/{PRE}_glock_public/ep{EP}'
    if not os.path.isfile(f'{res0}/rest_check.json'):
        sys.exit(f'arms: {res0}/rest_check.json missing (glock_public.sh REUSE_REF needs it)')
    urd, fp = urdfs_of(src)
    for n, u in urd.items():
        if u['md5'] is None:
            fails.append(f'{n} URDF {u["urdf"]} missing')
        elif abs(u['mass'] - PLACEHOLDER) > 1e-9:
            fails.append(f'{n} mass {u["mass"]} != {PLACEHOLDER}')
    man = dict(episode=EP, prefix=PRE, base=BASE, source_parquet=src, source_md5=md5(src), traj_fingerprint=fp, hive=hive,
               base_parquet=base_pq[0], base_md5=md5(base_pq[0]), urdfs=urd,
               zero_score=open(f'{res0}/zero_score.txt').read().strip()[-400:] if os.path.isfile(f'{res0}/zero_score.txt') else None,
               rest_check=jsonish(f'{res0}/rest_check.json'), seeds={})
    for s in a.seeds.split():
        pre = f'{PRE}s{s}'; RD = f'{C}/refs/{pre}_glockt/ep{EP}'; dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'
        os.makedirs(os.path.dirname(dpq), exist_ok=True)
        if not (os.path.isfile(dpq) and md5(dpq) == man['source_md5']):
            shutil.copyfile(src, dpq)
        n_pq = len(glob.glob(f'{RD}/**/*.parquet', recursive=True))
        if n_pq != 1:
            sys.exit(f'arms: {RD} holds {n_pq} parquet files (FlashCHORD needs exactly one)')
        lk = f'{C}/refs/{pre}{BASE}/ep{EP}'; os.makedirs(os.path.dirname(lk), exist_ok=True)
        if os.path.islink(lk):
            os.remove(lk)
        elif os.path.lexists(lk):
            sys.exit(f'arms: {lk} exists and is not a link')
        os.symlink(R0, lk)
        O = f'{C}/results/{pre}_glock_public/ep{EP}'; os.makedirs(O, exist_ok=True)       # never moved: a re-run keeps best/
        for f in ('rest_check.json', 'zero_score.txt'):
            if os.path.exists(f'{res0}/{f}'):
                shutil.copy(f'{res0}/{f}', f'{O}/{f}')
        man['seeds'][s] = dict(parquet=dpq, md5=md5(dpq), base_link=lk, results=O, pair=f'{EP}:local:{BASE}:{pre}')
    if ex:
        if man['source_md5'] != ex.get('source_md5') or man['base_md5'] != ex.get('base_md5'):
            fails.append(f'reference differs from the earlier run (source {man["source_md5"]} vs {ex.get("source_md5")}, base {man["base_md5"]} vs {ex.get("base_md5")})')
        for n, u in urd.items():                     # make_assets.py rebuilt /content/assets on this box: same inertials
            eu = ex.get('urdfs', {}).get(n) or {}
            if u['mass'] != eu.get('mass') or u['com'] != eu.get('com'):
                fails.append(f'{n} URDF differs from the earlier run (mass {u["mass"]} vs {eu.get("mass")}, COM {u["com"]} vs {eu.get("com")})')
    man['ok'] = not fails; man['failures'] = fails
    json.dump(man, open(a.out, 'w'), indent=1)
    print(('ARMS OK' if not fails else 'ARMS FAILED: ' + ' | '.join(fails[:5])) + f" :: V {man['source_md5']} (fingerprint "
          f"{man['traj_fingerprint'][:12]}), base {man['base_md5']}, seeds {sorted(man['seeds'])}, "
          + ', '.join(f"{n} {u['mass']} kg" for n, u in urd.items()))
    sys.exit(0 if not fails else 1)


def med_cm(p, q, lo, hi):
    n = min(len(p), len(q)); hi = min(hi, n)
    return round(float(np.median(np.linalg.norm(p[lo:hi] - q[lo:hi], axis=-1))) * 100, 3)


def identity(C, track, stored, packed_ref):
    out = {}
    try:
        R = f'{C}/refs/{PRE}{BASE}/ep{EP}'; Tt = np.load(f'{R}/table_frame.npz')['T_table_from_world']
        e2s = ref_track(f'{R}/e2s_reference.parquet')['blue_cup']; e = {}
        for k, f in (('V4p_track', track), ('stored_track', stored)):
            W, _ = world(f); p = (Tt[:3, :3] @ W['blue_cup'][:, :3, 3].T).T + Tt[:3, 3]
            e[k] = med_cm(p, e2s, *WINDOW)
        out['e2s_blue_vs_tracks_cm'] = e; out['e2s_ok'] = bool(e['V4p_track'] < e['stored_track'])
        tr = glob.glob(f'{C}/refs/{PRE}_glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')
        if tr and packed_ref and os.path.isfile(packed_ref):
            v, p = ref_track(tr[0]), ref_track(packed_ref)
            out['trained_V_vs_packed_P_cm'] = {n: dict(window=med_cm(v[n], p[n], *WINDOW), hands_off=med_cm(v[n], p[n], *HANDS_OFF))
                                               for n in ('blue_cup', 'beige_cup')}
            out['blue_height_V_minus_P_cm'] = dict(window=round(float(np.median(v['blue_cup'][WINDOW[0]:WINDOW[1], 2] - p['blue_cup'][WINDOW[0]:WINDOW[1], 2])) * 100, 3))
        out['ok'] = out['e2s_ok']
    except Exception as x:
        out.update(ok=False, error=f'{type(x).__name__}: {str(x)[:200]}')
    return out


def cmd_identity(a):
    r = identity(a.content.rstrip('/'), a.track, a.stored, a.packed_ref)
    json.dump(r, open(a.out, 'w'), indent=1)
    print(('IDENTITY OK' if r.get('ok') else 'IDENTITY FAILED') + f": e2s blue vs tracks {r.get('e2s_blue_vs_tracks_cm')} cm; trained V vs packed P "
          f"{r.get('trained_V_vs_packed_P_cm')}; blue height V - P {r.get('blue_height_V_minus_P_cm')}" + (f" ERROR {r['error']}" if 'error' in r else ''))
    sys.exit(0 if r.get('ok') else 1)


def fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def seed_stats(C, s):
    O = f'{C}/results/{PRE}s{s}_glock_public/ep{EP}'; ck = f'{O}/best/policy.safetensors'
    if not (os.path.isfile(f'{O}/best/summary.json') and os.path.isfile(ck)):
        return dict(n=0, missing=True, results=O)
    v = []
    for f in sorted(glob.glob(f'{O}/best/r*/qa_policy.json')):
        try:
            x = json.load(open(f)).get('sim_vs_ref')
        except Exception:
            x = None
        if fin(x):
            v.append(float(x))
    st = dict(n=len(v), results=O, checkpoint=ck, sha256=hashlib.sha256(open(ck, 'rb').read()).hexdigest(),
              chosen_by_curve=json.load(open(f'{O}/best/summary.json')).get('checkpoint'))
    if v:
        m = sum(v) / len(v); sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
        st.update(mean=round(m, 4), sd=round(sd, 4), min=round(min(v), 4), max=round(max(v), 4), values=[round(x, 4) for x in v])
    return st


def rule2(st, seeds):
    """mass_eval_verify.rule2 (local copy, same logic): seeds with >= MIN_N; the higher mean; within 0.005 (rounded gap
    of 4-decimal means) the lower sd; still tied the first seed listed. None if no seed has MIN_N."""
    have = [s for s in seeds if st.get(s, {}).get('n', 0) >= MIN_N]
    if not have:
        return None
    best = max(have, key=lambda s: st[s]['mean'])
    close = [s for s in have if round(abs(st[s]['mean'] - st[best]['mean']), 4) <= 0.005]
    return min(close, key=lambda s: (st[s]['sd'], seeds.index(s)))


def cmd_choose(a):
    C = a.content.rstrip('/'); seeds = a.seeds.split(); st = {s: seed_stats(C, s) for s in seeds}
    thin = [s for s in seeds if st[s]['n'] < MIN_N]
    ch = None if thin else rule2(st, seeds)
    out = dict(rule='PREREG 3.4 (rule 2): higher mean sim_vs_ref vs V; within 0.005 the lower sd; else the first seed (42)',
               min_n=MIN_N, seeds=st, incomplete_seeds=thin, chosen=ch,
               checkpoint=st[ch]['checkpoint'] if ch else None, sha256=st[ch]['sha256'] if ch else None)
    json.dump(out, open(a.out, 'w'), indent=1)
    print((f'CHOSEN seed {ch}' if ch else f'INCOMPLETE: seeds without {MIN_N} scored training-box rollouts {thin}') + ' :: '
          + '; '.join(f"s{s} n {v['n']} mean {v.get('mean')} sd {v.get('sd')} min {v.get('min')}" for s, v in st.items()))
    sys.exit(0 if ch else 1)


def cmd_verify(a):
    C = a.content.rstrip('/'); G = a.dir.rstrip('/'); seeds = a.seeds.split(); fails, cells, missing = [], {}, []
    js = lambda f: json.load(open(f)) if os.path.isfile(f) else None
    b0, bd, dc, man, idn, ch = (js(f'{G}/{x}.json') for x in ('b0', 'build', 'depth_check', 'arms', 'identity', 'choice'))
    if not b0 or b0.get('band') not in ('IDENTICAL', 'NUMERIC', 'DIFFERS'):
        fails.append(f'B0 band {(b0 or {}).get("band")}')
    if not bd:
        fails.append('build.json missing')
    else:
        if bd.get('rc') != 0:
            fails.append(f'reference build rc {bd.get("rc")}')
        if not (bd.get('poses_md5_before') == bd.get('poses_md5_after') == (b0 or {}).get('md5_box')):
            fails.append(f'mkref input track md5 {bd.get("poses_md5_before")}/{bd.get("poses_md5_after")} != B0 {(b0 or {}).get("md5_box")}')
        if os.path.realpath(bd.get('depth') or '') != os.path.realpath(bd.get('depth_expected') or '-'):
            fails.append(f'mkref depth {bd.get("depth")} is not the pulled eval-10 cache {bd.get("depth_expected")}')
        if bd.get('hands_md5') != HANDS_MD5['hands'] or bd.get('hands_refined_md5') != HANDS_MD5['hands_refined']:
            fails.append(f'reference hands md5 {bd.get("hands_md5")}/{bd.get("hands_refined_md5")} != {HANDS_MD5}')
    if not dc or not dc.get('ok'):
        fails.append('depth_check.json missing or not ok')
    if not man or not man.get('ok'):
        fails.append('arms.json missing or not ok')
    if not idn or not idn.get('ok'):
        fails.append(f'identity check failed {idn}')
    try:
        _, pcfg = ck_config(a.packed_ck); pflat = flat(pcfg)
    except Exception as e:
        pflat = None; fails.append(f'packed checkpoint config unreadable: {type(e).__name__}: {str(e)[:160]}')
    urdf_sets = {}
    for s in seeds:
        key = f's{s}'; row = cells[key] = {}; O = f'{C}/results/{PRE}s{s}_glock_public/ep{EP}'; ck = f'{O}/best/policy.safetensors'
        row['eval_timeouts'] = eval_timeouts(O)
        if not (os.path.exists(f'{O}/best/summary.json') and os.path.exists(ck)):
            row['missing'] = True; missing.append(key); continue
        try:
            summ = json.load(open(f'{O}/best/summary.json')); row['checkpoint'] = summ.get('checkpoint')
            if row['checkpoint'] and os.path.exists(row['checkpoint']) and md5(row['checkpoint']) != md5(ck):
                fails.append(f'{key}: best/policy.safetensors is not the checkpoint the summary names')
            meta, cfg = ck_config(ck); row['checkpoint_steps'] = meta.get('user.environment_steps')
            task = cfg['task']['parquet']; row['task_parquet'] = task
            rp = resolve_parquet(task); row['reference_file'] = rp; row['reference_md5'] = md5(rp)
            want = os.path.realpath(f'{C}/refs/{PRE}s{s}_glockt/ep{EP}') + '/'
            if not os.path.realpath(rp).startswith(want):
                fails.append(f'{key}: trained on {rp}, not this seed\'s copy under {want}')
            if row['reference_md5'] != (man or {}).get('source_md5'):
                fails.append(f'{key}: reference md5 {row["reference_md5"]} != V {(man or {}).get("source_md5")}')
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
            if pflat is not None:
                f1 = flat(cfg); diff = sorted(k for k in set(f1) | set(pflat) if f1.get(k) != pflat.get(k))
                row['config_diff_vs_packed'] = diff; bad = [k for k in diff if k not in ALLOWED]
                if bad:
                    fails.append(f'{key}: saved config differs from the packed gl10A2 checkpoint in {bad[:8]}')
            sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest(); row['checkpoint_sha256'] = sha; ev = 0
            for f in sorted(glob.glob(f'{O}/best/r*/episode_*.json')):
                d = json.load(open(f)); ev += 1
                if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != sha:
                    fails.append(f'{key}: {f} evaluated checkpoint sha256 {d["checkpoint_sha256"][:12]} != chosen {sha[:12]}')
            row['evaluations_checked'] = ev
        except Exception as e:
            row['error'] = f'{type(e).__name__}: {str(e)[:200]}'; fails.append(f'{key}: {row["error"]}')
    if len({json.dumps(v) for v in urdf_sets.values()}) > 1:
        fails.append('the seeds load different URDF files')
    conf = dict(draws=0, checked=0)
    if ch and ch.get('chosen'):
        conf['chosen'] = ch['chosen']; conf['sha256'] = ch['sha256']
        if ch['sha256'] != cells.get(f's{ch["chosen"]}', {}).get('checkpoint_sha256'):
            fails.append('choice.json names a checkpoint that is not the chosen seed\'s best/policy.safetensors')
        for f in sorted(glob.glob(f'{G}/conf/r*/ep{EP}/episode_{EP:06d}.json')):
            conf['draws'] += 1
            try:
                d = json.load(open(f))
            except Exception:
                continue
            conf['checked'] += 1
            if d.get('checkpoint_sha256') != ch['sha256']:
                fails.append(f'confirmation {f}: evaluated checkpoint sha256 {str(d.get("checkpoint_sha256"))[:12]} != chosen {ch["sha256"][:12]}')
        rcs = [open(f).read().strip() for f in glob.glob(f'{G}/conf/r*/eval_rc.txt')]
        conf['eval_rc'] = {x: rcs.count(x) for x in sorted(set(rcs))}
    own = {}
    for f in sorted(glob.glob(f'{G}/score*.json')):
        for name, s_ in (js(f) or {}).get('sets', {}).items():
            for r in s_.get('rollouts', []):
                if r.get('scored') and s_.get('own') in ('V', 'P'):
                    c = r.get('own_ref_check') or {}
                    own[f'{name}/r{r.get("draw")}'] = c.get('ok')
                    if not c.get('ok'):
                        fails.append(f'{os.path.basename(f)} {name} r{r.get("draw")}: own-reference check failed {c}')
    out = dict(ok=not fails, failures=fails, missing=missing, b0_band=(b0 or {}).get('band'), build=bd, depth_check=dc, identity=idn,
               choice={k: (ch or {}).get(k) for k in ('chosen', 'checkpoint', 'sha256', 'incomplete_seeds')}, confirmation=conf,
               own_ref_checks=own, cells=cells, allowed_config_diff=sorted(ALLOWED),
               rule='docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md section 6')
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print(('VERIFIED' if out['ok'] else f'VERIFY FAILED ({len(fails)}): ' + ' | '.join(fails[:6]))
          + (f' :: MISSING seeds (no chosen checkpoint; INCOMPLETE unless a failure above): {missing}' if missing else '')
          + f" :: B0 {out['b0_band']} :: identity e2s {(idn or {}).get('e2s_blue_vs_tracks_cm')} :: chosen {out['choice'].get('chosen')}"
          + f" :: confirmation draws {conf.get('draws')} (rc {conf.get('eval_rc')}) :: own-reference checks {sum(1 for v in own.values() if v)}/{len(own)}")
    sys.exit(0 if out['ok'] else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('b0'); b.add_argument('--tracks', required=True); b.add_argument('--expect', required=True); b.add_argument('--out', required=True)
    r = sp.add_parser('arms'); r.add_argument('--content', default='/content'); r.add_argument('--seeds', default='42 43')
    r.add_argument('--out', required=True); r.add_argument('--expect_manifest', default=None)
    i = sp.add_parser('identity'); i.add_argument('--content', default='/content'); i.add_argument('--track', required=True)
    i.add_argument('--stored', required=True); i.add_argument('--packed_ref', default=None); i.add_argument('--out', required=True)
    c = sp.add_parser('choose'); c.add_argument('--content', default='/content'); c.add_argument('--seeds', default='42 43'); c.add_argument('--out', required=True)
    v = sp.add_parser('verify'); v.add_argument('--content', default='/content'); v.add_argument('--seeds', default='42 43')
    v.add_argument('--steps', type=int, required=True); v.add_argument('--dir', required=True); v.add_argument('--packed_ck', required=True)
    v.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(b0=cmd_b0, arms=cmd_arms, identity=cmd_identity, choose=cmd_choose, verify=cmd_verify)[a.cmd](a)


if __name__ == '__main__':
    main()
