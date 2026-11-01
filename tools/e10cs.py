"""Eval-10 cavity-safe retrain: checks, seed choice, gate and verdict of ops/jobs/ev10_cs.sh (2026-11-01; pre-registered in
docs/research/work/eval10-cs4-20261101/PREREG.md before any result). Eval 10: no ground truth exists or is read. The
packed eval-10 recipe on e10v's stored V4p reference V (run 20261031-e10v-caf38fb), seeds 42 and 43, at the stock sim=rl
contact limits, with ONE changed input: the collision pieces (meshes/carve/<set>, set ev10cs4 | ev10cs5, by md5) and the
URDF mass properties that make_assets.py derives from them (their inertia.json). PACKABLE if it passes: nothing here is
oracle- or scan-derived and no sim limit changes (tools/no_oracle.py must accept every input and the chosen checkpoint).

  pieces   the set's folder: MD5SUMS md5 = the one pinned here for the set, tools/e10cs_pieces.py check (file set and md5s
           = MD5SUMS = FROZEN.md); ev10cs5 also clause (a) against ev10cs4 (tools/e10cs_pieces.py compare). Exit 1 on failure.
  assets   after make_assets.py: tools/e10cs_pieces.py assets (col_NN.obj = piece_NN.obj, URDF inertial = inertia.json) and
           each cup URDF's md5 = the one pinned here for the set (CPU build of 1 Nov; the same command on meshes/carve/ev10
           reproduces e10v's box URDFs). Records the URDF inertials used. Exit 1 on failure.
  arms     the seed copies of e10v's V: refs/perc2e10css<seed>_glockt/ep10/<hive>/ref_gl_ilc.parquet = byte copy of
           refs/perc2e10v_glockt/ep10/<hive>/ref_gl_ilc.parquet, base link refs/perc2e10css<seed>mck/ep10 ->
           refs/perc2e10vmck/ep10, results/perc2e10css<seed>_glock_public/ep10/{rest_check.json, zero_score.txt} (glock_public.sh
           REUSE_REF / REQUIRE_REUSE). V md5 / trajectory fingerprint / base md5 = e10v's arms.json AND the values pinned here;
           the URDFs V names exist, weigh 0.3 kg and have the set's pinned md5 (they differ from e10v's by design).
  cells    per seed (pack 9b PREREG 1.3 style): the chosen checkpoint as the evaluator loads it: saved config -> task.parquet
           -> this seed's copy (md5 = V) -> object_urdf_paths -> URDFs (the set's md5, 0.3 kg, under /content/assets); every
           saved-config key = the PACKED eval-10 checkpoint's (gl10A2, sha256 76a12265...) except output_dir, task.parquet,
           reference.parquet, reset.seed, env.reset.seed, training.seed; sim and env.sim njmax / nconmax = 512 / 256; steps;
           reset.seed; best/ = the curve's choice; the training-box rollouts name the checkpoint (sha256); their sim_vs_ref
           (qa_policy.json, vs the seed copy = V). Status per seed: VERIFIED | INVALID | MISSING (no chosen checkpoint).
  choose   pack 9b PREREG section 2 (= e10v's rule 2, the same function): over the two VERIFIED seeds with >= 8 scored
           training-box rollouts, the higher mean; within 0.005 (4-decimal means) the lower sd (ddof 1); still tied seed 42.
           An INVALID cell -> INVALID (no choice); a missing / thin seed -> INCOMPLETE (no single-seed fallback). Exit 1 if
           no seed is chosen.
  gate     the training-box gate (PREREG section 4): the confirmation runs only if at least one VERIFIED seed with >= 8 scored
           training-box rollouts has a mean sim_vs_ref vs V above 0.4632 (the packed policy's fresh-draw mean vs V, e10v
           summary [M]; strict, 1e-9 in favour of "not met"). Exit 0 if met, 3 if not met, 1 if it cannot be read.
  verify   the run's checks after scoring: pieces, assets, arms, cells (no INVALID), choice = the chosen cell, every
           confirmation draw names the chosen checkpoint, every scored rollout's own-reference check (score json), the
           no_oracle acceptance of the chosen checkpoint (when a confirmation ran). verify.json in e10v_verify's shape.
  verdict  the PREREG section 5 label (INVALID / INCOMPLETE / NO-SWAP (training-box gate not met) / the agreed swap rule
           on both references by tools/e10v_verdict.verdict: SWAP-ELIGIBLE / NO-SWAP / INCOMPLETE / INVALID), then the
           binding pack-10 inclusion rule (SWAP-ELIGIBLE and mean gain >= 0.02 on V AND on P), the overflow label ("pieces
           not clean in training" if a training log has > 1,000 dropped-row lines), the beige lift clause (r1 >= 5 cm at
           >= 1 checkpoint), the EQUAL FLOOR note, the piece set and its md5 manifest, the URDF inertials.
Usage (box paths): see ops/jobs/ev10_cs.sh.
"""
import argparse, glob, hashlib, json, math, os, shutil, statistics, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import md5                                                                        # noqa: E402
from mass_verify import ck_config, resolve_parquet, resolve_asset, flat, eval_timeouts, STEPS_KEY  # noqa: E402
from e11g_verify import urdfs_of, jsonish                                                       # noqa: E402
from e10v_verify import rule2 as rule2_e10v                                                     # noqa: E402
import e10v_verdict                                                                             # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP, SRC, PRE, BASE = 10, 'perc2e10v', 'perc2e10cs', 'mck'
PLACEHOLDER, STOCK = 0.3, (512, 256)
SIM_KEYS = ('sim.njmax', 'sim.nconmax', 'env.sim.njmax', 'env.sim.nconmax')
ALLOWED = {'output_dir', 'task.parquet', 'reference.parquet', 'reset.seed', 'env.reset.seed', 'training.seed'}
# e10v's stored V (arms.json of run 20261031-e10v-caf38fb) [M]
V_MD5, V_FP, BASE_MD5 = '5d22fc5782a919f2466988768d0708fa', '8f408d5101f108cda929fd3ee346e970', 'ca4ae8dcbc290d66ce09d6ad69a09410'
PACKED_SHA, PACKED_REF_MD5 = e10v_verdict.PACKED_SHA, e10v_verdict.PACKED_REF_MD5
# the piece sets, pinned (meshes/carve/<set>/MD5SUMS md5; URDF md5 of make_assets.py meshes/library_v3 --pieces <set>, CPU 1 Nov)
SETS = {
    'ev10cs4': dict(md5sums='c745ebc8c3e86cadc5301a7b2351c5c1', source='origin/claude/bold-albattani-6qmxsv fa2ec41 (built 7e4bc6a)',
                    urdf={'blue_cup': '8511f0d3fdc154c6e2dba609aa195c4c', 'beige_cup': '1a8cb9d813c7a8085b4759347a16a8ba'}),
    'ev10cs5': dict(md5sums='045d8921d5fe548ffebbee3cc21e798b', source='origin/claude/bold-albattani-6qmxsv 2b016b4 (built 7935261)',
                    urdf={'blue_cup': 'ac8d296b440ceeb24e895366f45365d8', 'beige_cup': '1a8cb9d813c7a8085b4759347a16a8ba'}),
}
PACKED_URDF = {'blue_cup': '82ff6cb8049b527a7ec770965128e37c', 'beige_cup': 'b994e584931ff45b8f162ff7891d49a6'}   # e10v / packed ev10
MIN_N, MIN_CONF = 8, 10
GATE_V = 0.4632            # the packed eval-10 policy's fresh-draw (H5p7) mean sim_vs_ref vs V, e10v summary.json [M]
INCL_BAR = 0.02            # binding pack-10 inclusion: mean gain >= 0.02 on V and on P (orchestrator, 1 Nov)
O_BAR = 1000               # overflow label: > 1,000 dropped-row lines in a training log
L_BAR_CM = 5.0             # beige r1 lift >= 5 cm at >= 1 curve checkpoint (reported clause; e10nj.py lift)
TOL = 1e-9


def js(f):
    try:
        return json.load(open(f)) if f and os.path.isfile(f) else None
    except Exception:
        return None


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def tool(*args):
    r = subprocess.run([sys.executable, '-I', os.path.join(REPO, 'tools', 'e10cs_pieces.py'), *args], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


# --------------------------------------------------------------------------------------------------------------- pieces
def cmd_pieces(a):
    fails = []; s = a.set
    if s not in SETS:
        sys.exit(f'pieces: unknown set {s!r} (one of {sorted(SETS)})')
    d = a.dir.rstrip('/'); r = dict(set=s, dir=os.path.abspath(d), pinned=SETS[s])
    if os.path.basename(d) != s:
        fails.append(f'folder {d} is not named {s}')
    man = f'{d}/MD5SUMS'; r['md5sums_md5'] = md5(man) if os.path.isfile(man) else None
    if r['md5sums_md5'] != SETS[s]['md5sums']:
        fails.append(f'MD5SUMS md5 {r["md5sums_md5"]} != pinned {SETS[s]["md5sums"]}')
    r['manifest'] = open(man).read().splitlines() if os.path.isfile(man) else None
    rc, out = tool('check', '--dir', d, '--out', f'{a.out}.check.json'); r['check'] = js(f'{a.out}.check.json'); r['check_line'] = out[-600:]
    if rc != 0:
        fails.append(f'e10cs_pieces check failed: {out[-300:]}')
    if s == 'ev10cs5':                                                    # PREREG 2.2 clause (a), re-checked on the box
        rc, out = tool('compare', '--base', os.path.join(os.path.dirname(d), 'ev10cs4'), '--cand', d, '--out', f'{a.out}.compare.json')
        r['clause_a'] = js(f'{a.out}.compare.json'); r['clause_a_line'] = out[-600:]
        if rc != 0:
            fails.append(f'clause (a) vs ev10cs4 failed: {out[-300:]}')
    r['ok'] = not fails; r['failures'] = fails
    json.dump(r, open(a.out, 'w'), indent=1)
    print(('PIECES OK' if not fails else 'PIECES FAILED: ' + ' | '.join(fails)) + f" :: set {s}, MD5SUMS {r['md5sums_md5']}, "
          + (r.get('check_line') or '')[:400])
    sys.exit(0 if not fails else 1)


def cmd_assets(a):
    fails = []; s = a.set
    rc, out = tool('assets', '--assets', a.assets, '--pieces', a.pieces, '--out', f'{a.out}.urdfs.json')
    u = js(f'{a.out}.urdfs.json') or {}
    if rc != 0:
        fails.append(f'e10cs_pieces assets failed: {out[-300:]}')
    for n, want in SETS[s]['urdf'].items():
        got = ((u.get('urdfs') or {}).get(n) or {}).get('urdf_md5')
        if got != want:
            fails.append(f'{n} URDF md5 {got} != pinned {want} for {s}')
    r = dict(set=s, assets=a.assets, pieces=os.path.abspath(a.pieces), urdfs=u.get('urdfs'), pinned_urdf_md5=SETS[s]['urdf'],
             packed_urdf_md5=PACKED_URDF, ok=not fails, failures=fails, line=out[-800:])
    json.dump(r, open(a.out, 'w'), indent=1)
    print(('ASSETS OK' if not fails else 'ASSETS FAILED: ' + ' | '.join(fails)) + f' :: {out[-700:]}')
    sys.exit(0 if not fails else 1)


# ----------------------------------------------------------------------------------------------------------------- arms
def cmd_arms(a):
    C = a.content.rstrip('/'); ex = json.load(open(a.e10v_arms)); fails = []; s_ = a.set
    src = glob.glob(f'{C}/refs/{SRC}_glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')
    if len(src) != 1:
        sys.exit(f'arms: {len(src)} references under refs/{SRC}_glockt/ep{EP} (one expected: e10v\'s V)')
    src = src[0]; R0 = f'{C}/refs/{SRC}{BASE}/ep{EP}'; hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/{SRC}_glockt/ep{EP}')
    base_pq = glob.glob(f'{R0}/{hive}/*.parquet')
    if len(base_pq) != 1:
        sys.exit(f'arms: {len(base_pq)} base references under {R0}/{hive}')
    res0 = f'{C}/results/{SRC}_glock_public/ep{EP}'
    if not os.path.isfile(f'{res0}/rest_check.json'):
        sys.exit(f'arms: {res0}/rest_check.json missing (glock_public.sh REUSE_REF needs it)')
    urd, fp = urdfs_of(src)
    man = dict(episode=EP, source_prefix=SRC, prefix=PRE, base=BASE, set=s_, source_parquet=src, source_md5=md5(src), traj_fingerprint=fp,
               hive=hive, base_parquet=base_pq[0], base_md5=md5(base_pq[0]), urdfs=urd,
               e10v_arms=dict(path=a.e10v_arms, source_md5=ex.get('source_md5'), traj_fingerprint=ex.get('traj_fingerprint'),
                              base_md5=ex.get('base_md5'), urdfs=ex.get('urdfs')),
               rest_check_e10v=jsonish(f'{res0}/rest_check.json'), seeds={},
               note='rest_check.json / zero_score.txt are e10v\'s records (zero-action replay with meshes/carve/ev10); copied only '
                    'because glock_public.sh REUSE_REF requires them; nothing reads their values')
    if not (man['source_md5'] == ex.get('source_md5') == V_MD5) or not (fp == ex.get('traj_fingerprint') == V_FP):
        fails.append(f'V {man["source_md5"]} / fingerprint {fp[:12]} != e10v {ex.get("source_md5")} / pinned {V_MD5}')
    if not (man['base_md5'] == ex.get('base_md5') == BASE_MD5):
        fails.append(f'base reference {man["base_md5"]} != e10v {ex.get("base_md5")} / pinned {BASE_MD5}')
    for n, u in urd.items():
        if u['md5'] is None:
            fails.append(f'{n} URDF {u["urdf"]} missing')
            continue
        if abs(u['mass'] - PLACEHOLDER) > 1e-9:
            fails.append(f'{n} mass {u["mass"]} != {PLACEHOLDER}')
        if u['md5'] != SETS[s_]['urdf'].get(n):
            fails.append(f'{n} URDF md5 {u["md5"]} != the {s_} build {SETS[s_]["urdf"].get(n)}')
        u['md5_equals_e10v'] = u['md5'] == ((ex.get('urdfs') or {}).get(n) or {}).get('md5')   # False by design (new pieces)
    for s in a.seeds.split():
        pre = f'{PRE}s{s}'; RD = f'{C}/refs/{pre}_glockt/ep{EP}'; dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'
        os.makedirs(os.path.dirname(dpq), exist_ok=True)
        if not (os.path.isfile(dpq) and md5(dpq) == man['source_md5']):
            shutil.copyfile(src, dpq)
        n_pq = len(glob.glob(f'{RD}/**/*.parquet', recursive=True))
        if n_pq != 1:
            fails.append(f'{RD} holds {n_pq} parquet files (FlashCHORD needs exactly one)')
        lk = f'{C}/refs/{pre}{BASE}/ep{EP}'; os.makedirs(os.path.dirname(lk), exist_ok=True)
        if os.path.islink(lk):
            os.remove(lk)
        elif os.path.lexists(lk):
            sys.exit(f'arms: {lk} exists and is not a link')
        os.symlink(R0, lk)
        O = f'{C}/results/{pre}_glock_public/ep{EP}'; os.makedirs(O, exist_ok=True)
        for f in ('rest_check.json', 'zero_score.txt'):
            if os.path.exists(f'{res0}/{f}'):
                shutil.copy(f'{res0}/{f}', f'{O}/{f}')
        man['seeds'][s] = dict(parquet=dpq, md5=md5(dpq), base_link=lk, results=O, pair=f'{EP}:local:{BASE}:{pre}')
        if man['seeds'][s]['md5'] != man['source_md5']:
            fails.append(f'seed {s}: the copy is not a byte copy of V')
    man['ok'] = not fails; man['failures'] = fails
    json.dump(man, open(a.out, 'w'), indent=1)
    print(('ARMS OK' if not fails else 'ARMS FAILED: ' + ' | '.join(fails[:5])) + f" :: V {man['source_md5']} (fingerprint {fp[:12]}), "
          f"base {man['base_md5']}, seeds {sorted(man['seeds'])}, " + ', '.join(f"{n} {u['mass']} kg URDF {str(u['md5'])[:8]} (e10v's: "
                                                                                  f"{u.get('md5_equals_e10v')})" for n, u in urd.items()))
    sys.exit(0 if not fails else 1)


# ---------------------------------------------------------------------------------------------------------------- cells
def config_diff(ck, packed_ck):
    """(diff keys, keys outside ALLOWED, sim limits of the checkpoint) of a checkpoint's stored config vs the packed one"""
    _, c1 = ck_config(ck); _, c0 = ck_config(packed_ck); f1, f0 = flat(c1), flat(c0)
    diff = sorted(k for k in set(f1) | set(f0) if f1.get(k) != f0.get(k))
    return diff, [k for k in diff if k not in ALLOWED], {k: f1.get(k) for k in SIM_KEYS}, c1


def stats(v):
    if not v:
        return {}
    m = sum(v) / len(v); sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
    return dict(mean=round(m, 4), sd=round(sd, 4), min=round(min(v), 4), max=round(max(v), 4), mean_raw=m, values=[round(x, 4) for x in v])


def cell(C, s, steps, packed_ck, set_):
    O = f'{C}/results/{PRE}s{s}_glock_public/ep{EP}'; ck = f'{O}/best/policy.safetensors'; fails = []
    row = dict(seed=s, results=O, eval_timeouts=eval_timeouts(O))
    if not (os.path.isfile(f'{O}/best/summary.json') and os.path.isfile(ck)):
        return dict(row, status='MISSING', n=0, failures=[])
    try:
        summ = json.load(open(f'{O}/best/summary.json')); row['chosen_by_curve'] = summ.get('checkpoint')
        if row['chosen_by_curve'] and os.path.exists(row['chosen_by_curve']) and md5(row['chosen_by_curve']) != md5(ck):
            fails.append('best/policy.safetensors is not the checkpoint the curve chose')
        row['checkpoint'] = ck; row['sha256'] = sha256(ck)
        diff, bad, sim, cfg = config_diff(ck, packed_ck); row.update(config_diff_vs_packed=diff, sim_limits=sim)
        if bad:
            fails.append(f'saved config differs from the packed gl10A2 checkpoint in {bad[:8]}')
        if [sim[k] for k in SIM_KEYS] != [STOCK[0], STOCK[1], STOCK[0], STOCK[1]]:
            fails.append(f'sim limits {sim} are not the stock {STOCK}')
        row['reset_seed'] = (cfg.get('reset') or {}).get('seed'); row['steps'] = flat(cfg).get(STEPS_KEY)
        if str(row['reset_seed']) != str(s):
            fails.append(f'reset.seed {row["reset_seed"]} != {s}')
        if str(row['steps']) != str(steps):
            fails.append(f'{STEPS_KEY} {row["steps"]} != {steps}')
        task = cfg['task']['parquet']; rp = resolve_parquet(task.strip("'")); row.update(task_parquet=task, reference_file=rp, reference_md5=md5(rp))
        want = os.path.realpath(f'{C}/refs/{PRE}s{s}_glockt/ep{EP}') + '/'
        if not os.path.realpath(rp).startswith(want):
            fails.append(f'trained on {rp}, not this seed\'s copy under {want}')
        if row['reference_md5'] != V_MD5:
            fails.append(f'reference md5 {row["reference_md5"]} != V {V_MD5}')
        urd, fp = urdfs_of(rp); row['loaded_urdfs'] = urd; row['traj_fingerprint'] = fp
        for n, u in urd.items():
            p, how = resolve_asset(u['urdf'])
            if p is None:
                fails.append(f'{n}: {u["urdf"]} {how}')
                continue
            if abs(u['mass'] - PLACEHOLDER) > 1e-9:
                fails.append(f'{n} loads {u["mass"]} kg')
            if u['md5'] != SETS[set_]['urdf'].get(n):
                fails.append(f'{n} loads URDF md5 {u["md5"]}, not the {set_} build {SETS[set_]["urdf"].get(n)}')
            if not os.path.realpath(p).startswith(os.path.realpath(f'{C}/assets') + '/'):
                fails.append(f'{n}: {p} is not under {C}/assets')
        v, ev = [], 0
        for r in sorted(glob.glob(f'{O}/best/r*/')):
            d = js(f'{r}episode_{EP:06d}.json')
            if d is not None:
                ev += 1
                if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != row['sha256']:
                    fails.append(f'{os.path.basename(r[:-1])} evaluated checkpoint {str(d["checkpoint_sha256"])[:12]} != chosen {row["sha256"][:12]}')
            q = (js(f'{r}qa_policy.json') or {}).get('sim_vs_ref')
            if fin(q):
                v.append(float(q))
        row.update(evaluations_checked=ev, n=len(v), **stats(v))
    except Exception as e:
        fails.append(f'{type(e).__name__}: {str(e)[:200]}')
    return dict(row, status='VERIFIED' if not fails else 'INVALID', failures=fails, n=row.get('n', 0))


def cmd_cells(a):
    C = a.content.rstrip('/'); seeds = a.seeds.split()
    cells = {s: cell(C, s, a.steps, a.packed_ck, a.set) for s in seeds}
    if len({json.dumps(sorted((n, u['md5']) for n, u in c.get('loaded_urdfs', {}).items())) for c in cells.values() if c['status'] != 'MISSING'}) > 1:
        for c in cells.values():
            if c['status'] == 'VERIFIED':
                c['status'] = 'INVALID'; c['failures'].append('the seeds load different URDF files')
    out = dict(rule='PREREG section 3.2 (pack 9b PREREG 1.3 style)', set=a.set, packed_ck=a.packed_ck, packed_sha256=sha256(a.packed_ck),
               allowed_config_diff=sorted(ALLOWED), seeds=cells)
    if out['packed_sha256'] != PACKED_SHA:
        for c in cells.values():
            if c['status'] == 'VERIFIED':
                c['status'] = 'INVALID'
            c['failures'].append(f'packed checkpoint sha256 {out["packed_sha256"][:12]} != {PACKED_SHA[:12]}')
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print('CELLS :: ' + ' | '.join(f"s{s} {c['status']} n {c['n']} mean {c.get('mean')} sd {c.get('sd')} min {c.get('min')}"
                                   + (f" FAIL {c['failures'][:3]}" if c['failures'] else '') + (f" config diff {c.get('config_diff_vs_packed')}" if c.get('config_diff_vs_packed') is not None else '')
                                   for s, c in cells.items()))
    sys.exit(0 if all(c['status'] != 'INVALID' for c in cells.values()) else 1)


# --------------------------------------------------------------------------------------------------------------- choose
def choose(cells, seeds):
    inv = [s for s in seeds if cells[s]['status'] == 'INVALID']
    thin = [s for s in seeds if cells[s]['status'] == 'MISSING' or cells[s].get('n', 0) < MIN_N]
    if inv:
        return None, 'INVALID', inv, thin
    if thin:
        return None, 'INCOMPLETE', inv, thin
    st = {s: dict(n=cells[s]['n'], mean=cells[s]['mean'], sd=cells[s]['sd']) for s in seeds}
    return rule2_e10v(st, seeds), 'CHOSEN', inv, thin


def cmd_choose(a):
    cells = json.load(open(a.cells))['seeds']; seeds = a.seeds.split()
    ch, status, inv, thin = choose(cells, seeds)
    out = dict(rule='PREREG section 3.3 = pack 9b PREREG section 2 (e10v rule 2): two VERIFIED seeds with n >= 8; the higher mean '
                    'sim_vs_ref vs V; within 0.005 (4-decimal means) the lower sd (ddof 1); still tied seed 42',
               min_n=MIN_N, status=status, invalid_seeds=inv, incomplete_seeds=thin, chosen=ch,
               checkpoint=cells[ch]['checkpoint'] if ch else None, sha256=cells[ch]['sha256'] if ch else None,
               seeds={s: dict(results=cells[s].get('results'), checkpoint=cells[s].get('checkpoint'), sha256=cells[s].get('sha256'), status=cells[s]['status'],
                              **{k: cells[s].get(k) for k in ('n', 'mean', 'sd', 'min', 'max', 'values', 'chosen_by_curve')}) for s in seeds})
    json.dump(out, open(a.out, 'w'), indent=1)
    print((f'CHOSEN seed {ch}' if ch else f'{status}: invalid {inv}, missing / thin {thin}') + ' :: '
          + '; '.join(f"s{s} {c['status']} n {c.get('n')} mean {c.get('mean')} sd {c.get('sd')}" for s, c in out['seeds'].items()))
    sys.exit(0 if ch else 1)


# ----------------------------------------------------------------------------------------------------------------- gate
def gate(cells):
    rows = {s: dict(status=c['status'], n=c.get('n', 0), mean=c.get('mean'), mean_raw=c.get('mean_raw'),
                    above=bool(c['status'] == 'VERIFIED' and c.get('n', 0) >= MIN_N and fin(c.get('mean_raw')) and c['mean_raw'] > GATE_V + TOL),
                    margin=round(c['mean_raw'] - GATE_V, 4) if fin(c.get('mean_raw')) else None) for s, c in cells.items()}
    return dict(rule=f'PREREG section 4: >= 1 VERIFIED seed (n >= {MIN_N}) with training-box mean sim_vs_ref vs V > {GATE_V}', bar=GATE_V,
                bar_source='the packed eval-10 policy\'s 10 fresh (H5p7) draws, mean sim_vs_ref vs V, e10v summary.json [M]',
                met=any(r['above'] for r in rows.values()), seeds=rows)


def cmd_gate(a):
    try:
        g = gate(json.load(open(a.cells))['seeds'])
    except Exception as e:
        print(f'GATE UNREADABLE: {type(e).__name__}: {e}'); sys.exit(1)
    json.dump(g, open(a.out, 'w'), indent=1)
    print(('GATE MET' if g['met'] else 'GATE NOT MET (training-box gate not met: no confirmation draws)') + f' (bar > {GATE_V} vs V) :: '
          + '; '.join(f"s{s} {r['status']} n {r['n']} mean {r['mean']} margin {r['margin']}" for s, r in g['seeds'].items()))
    sys.exit(0 if g['met'] else 3)


# --------------------------------------------------------------------------------------------------------------- verify
def cmd_verify(a):
    G = a.dir.rstrip('/'); fails, missing = [], []
    pcs, ast, arms, cells, ch, gt = (js(f'{G}/{x}.json') for x in ('pieces', 'assets', 'arms', 'cells', 'choice', 'gate'))
    for name, d in (('pieces', pcs), ('assets', ast), ('arms', arms)):
        if not d or not d.get('ok'):
            fails.append(f'{name}.json missing or not ok: {(d or {}).get("failures")}')
    if not cells:
        fails.append('cells.json missing')
    else:
        for s, c in cells['seeds'].items():
            if c['status'] == 'INVALID':
                fails.append(f's{s}: {c["failures"][:4]}')
            elif c['status'] == 'MISSING':
                missing.append(f's{s}')
    conf = dict(draws=0, checked=0)
    if ch and ch.get('chosen'):
        conf.update(chosen=ch['chosen'], sha256=ch['sha256'])
        if cells and ch['sha256'] != cells['seeds'][ch['chosen']].get('sha256'):
            fails.append('choice.json names a checkpoint that is not the chosen seed\'s best/policy.safetensors')
        for f in sorted(glob.glob(f'{G}/conf/r*/ep{EP}/episode_{EP:06d}.json')):
            conf['draws'] += 1; d = js(f)
            if d is None:
                continue
            conf['checked'] += 1
            if d.get('checkpoint_sha256') != ch['sha256']:
                fails.append(f'confirmation {os.path.relpath(f, G)}: checkpoint {str(d.get("checkpoint_sha256"))[:12]} != chosen {ch["sha256"][:12]}')
        rcs = [open(f).read().strip() for f in glob.glob(f'{G}/conf/r*/eval_rc.txt')]
        conf['eval_rc'] = {x: rcs.count(x) for x in sorted(set(rcs))}
        if conf['draws'] and not os.path.isfile(f'{G}/no_oracle_choice.txt'):
            fails.append('confirmation draws exist but the no_oracle check of the chosen checkpoint left no record')
    own = {}
    for f in sorted(glob.glob(f'{G}/score*.json')):
        for name, s_ in ((js(f) or {}).get('sets') or {}).items():
            for r in s_.get('rollouts', []):
                if r.get('scored') and s_.get('own') in ('V', 'P'):
                    c = r.get('own_ref_check') or {}; own[f'{name}/r{r.get("draw")}'] = c.get('ok')
                    if not c.get('ok'):
                        fails.append(f'{os.path.basename(f)} {name} r{r.get("draw")}: own-reference check failed {c}')
    out = dict(ok=not fails, failures=fails, missing=missing, set=(pcs or {}).get('set'), confirmation=conf, own_ref_checks=own,
               gate_met=(gt or {}).get('met'), choice={k: (ch or {}).get(k) for k in ('chosen', 'checkpoint', 'sha256', 'status', 'incomplete_seeds')},
               rule='docs/research/work/eval10-cs4-20261101/PREREG.md section 6')
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print(('VERIFIED' if out['ok'] else f'VERIFY FAILED ({len(fails)}): ' + ' | '.join(fails[:6])) + (f' :: MISSING {missing}' if missing else '')
          + f" :: set {out['set']} :: chosen {out['choice'].get('chosen')} :: confirmation draws {conf.get('draws')} (rc {conf.get('eval_rc')}) :: "
          f"own-reference checks {sum(1 for v in own.values() if v)}/{len(own)}")
    sys.exit(0 if out['ok'] else 1)


# -------------------------------------------------------------------------------------------------------------- verdict
def training_overflow(ov, seeds):
    g = (ov or {}).get('groups') or {}
    return {s: dict(dropped=(g.get(f'train_s{s}') or {}).get('dropped'), files=(g.get(f'train_s{s}') or {}).get('files'),
                    counts=(g.get(f'train_s{s}') or {}).get('counts'), njmax_requested=(g.get(f'train_s{s}') or {}).get('njmax_requested'))
            for s in seeds}


def cmd_verdict(a):
    G = a.dir.rstrip('/'); seeds = a.seeds.split()
    pcs, ast, cells, ch, gt, ver, ov = (js(f'{G}/{x}.json') for x in ('pieces', 'assets', 'cells', 'choice', 'gate', 'verify', 'overflow'))
    sets, refs_md5 = {}, {}
    for f in a.score or []:
        d_ = js(f) or {}
        for X, info in (d_.get('refs') or {}).items():
            refs_md5.setdefault(X, set()).add(info.get('md5'))
        sets.update(d_.get('sets') or {})
    refs_md5 = {X: (next(iter(v)) if X == 'P' and len(v) == 1 else v) for X, v in refs_md5.items()}
    clauses, sides, why = {}, {}, []
    if os.path.exists(f'{G}/STOPPED'):
        label, why = 'INVALID', [f'job stopped: {open(f"{G}/STOPPED").read().strip()[:300]}']
    elif not ver or not ver.get('ok'):
        label, why = 'INVALID', [f'verify failed: {(ver or {}).get("failures", ["verify.json missing"])[:6]}']
    elif not ch or not ch.get('chosen'):
        st = (ch or {}).get('status')
        label = 'INVALID' if st == 'INVALID' else 'INCOMPLETE'
        why = [f'no chosen seed ({st}; invalid {(ch or {}).get("invalid_seeds")}, missing / thin {(ch or {}).get("incomplete_seeds")})']
    elif not gt or not gt.get('met'):
        label = 'NO-SWAP'
        why = ['training-box gate not met: no seed\'s training-box mean sim_vs_ref vs V above '
               f'{GATE_V} ({ {s: r.get("mean") for s, r in ((gt or {}).get("seeds") or {}).items()} }); no confirmation draws']
    else:
        label, why, clauses, sides = e10v_verdict.verdict(sets, ver, ch, MIN_CONF, refs_md5)
    if not sides:                                                         # the packed side and the training-box draws, reported
        K = e10v_verdict.scored((sets.get('packed') or {}).get('rollouts', []))
        sides = {X: dict(packed=e10v_verdict.side(K, X)) for X in e10v_verdict.REFS} if K else {}
    gain = {X: (s_['new']['mean_raw'] - s_['packed']['mean_raw']) if s_.get('new', {}).get('mean_raw') is not None
            and s_.get('packed', {}).get('mean_raw') is not None else None for X, s_ in sides.items()}
    include = bool(label == 'SWAP-ELIGIBLE' and all(gain.get(X) is not None and gain[X] >= INCL_BAR - TOL for X in e10v_verdict.REFS))
    inclusion = dict(rule=f'binding: a SWAP-ELIGIBLE eval 10 enters pack 10 only if (new confirmation mean - packed fresh-draw mean) '
                          f'sim_vs_ref >= {INCL_BAR} on BOTH V and P', bar=INCL_BAR,
                     gain={X: round(v, 4) if v is not None else None for X, v in gain.items()}, include_in_pack10=include,
                     reading=('INCLUDE in pack 10' if include else ('SWAP-ELIGIBLE but below the 0.02 inclusion bar: NOT included in pack 10'
                                                                    if label == 'SWAP-ELIGIBLE' else 'not swap-eligible: not included')))
    tov = training_overflow(ov, seeds)
    unclean = [s for s, o in tov.items() if o['dropped'] is not None and o['dropped'] > O_BAR]
    lift = {}
    for s in seeds:
        lf = js(f'{G}/lift_s{s}.json') or {}
        lift[s] = dict(beige_r1_max_cm=lf.get('carried_lift_r1_max_cm'), beige_any_repeat_max_cm=lf.get('carried_lift_any_repeat_max_cm'),
                       holds=bool(lf.get('L')), checkpoints=[dict(ckpt_M=r['ckpt_M'], sim_vs_ref=r['sim_vs_ref'], beige_r1=r['carried_lift_r1_cm'],
                                                                   beige_max=r['carried_lift_max_cm'], blue_r1=r['resting_lift_r1_cm'])
                                                              for r in lf.get('checkpoints', [])],
                       controls={k: c.get('carried_lift_r1_max_cm') for k, c in (lf.get('controls') or {}).items()})
    fl = {X: (s_.get('new', {}).get('fail_raw'), s_.get('packed', {}).get('fail_raw')) for X, s_ in sides.items()}
    equal_floor = bool(fl) and all(x is not None and y is not None and x >= 0.9 and y >= 0.9 for x, y in fl.values())
    tb = {}
    for s in seeds:
        rows = e10v_verdict.scored((sets.get(f'train{s}') or {}).get('rollouts', []))
        tb[s] = {X: e10v_verdict.side(rows, X) for X in e10v_verdict.REFS} if rows else None
    out = dict(label=label, why=why, rule='docs/research/work/eval10-cs4-20261101/PREREG.md section 5',
               labels_attached=(['pieces not clean in training'] if unclean else []) + (['EQUAL FLOOR'] if equal_floor else []),
               pack10_inclusion=inclusion, clauses=clauses,
               sides={X: {k: {kk: vv for kk, vv in v.items() if not kk.endswith('_raw')} for k, v in s_.items() if v} for X, s_ in sides.items()},
               training_box_gate=gt, overflow=dict(bar=O_BAR, unclean_seeds=unclean, per_seed=tov,
                                                   other={k: dict(files=v.get('files'), dropped=v.get('dropped')) for k, v in ((ov or {}).get('groups') or {}).items()
                                                          if not k.startswith('train_s')},
                                                   baseline='e10v (ev10 pieces, same V and recipe): 6,010,501 (s42) / 5,846,480 (s43) nefc lines [M]'),
               lift=dict(rule=f'reported: beige r1 lift >= {L_BAR_CM} cm at >= 1 curve checkpoint (tools/e10nj.py lift)',
                         holds_any_seed=any(v['holds'] for v in lift.values()), per_seed=lift),
               training_box={s: {X: {k: v for k, v in (x or {}).items() if not k.endswith('_raw')} for X, x in (t or {}).items()} if t else None for s, t in tb.items()},
               choice={k: (ch or {}).get(k) for k in ('status', 'chosen', 'checkpoint', 'sha256', 'seeds', 'incomplete_seeds', 'invalid_seeds')},
               pieces=dict(set=(pcs or {}).get('set'), dir=(pcs or {}).get('dir'), md5sums_md5=(pcs or {}).get('md5sums_md5'),
                           manifest=(pcs or {}).get('manifest'), source=((pcs or {}).get('pinned') or {}).get('source'),
                           clause_a=((pcs or {}).get('clause_a') or {}).get('clause_a')),
               urdf_inertials={n: {k: u.get(k) for k in ('urdf_md5', 'mass', 'com_mm', 'inertia', 'collisions')} for n, u in ((ast or {}).get('urdfs') or {}).items()},
               verify=dict(ok=(ver or {}).get('ok'), failures=(ver or {}).get('failures'), confirmation=(ver or {}).get('confirmation')),
               equal_floor_note=('both policies fail >= 90 % of their draws on both references: the rule compares two floors; expected '
                                 'leaderboard effect about 0') if equal_floor else None,
               counts={k: dict(own=v.get('own'), n_files=v.get('n_files'), n_scored=v.get('n_scored')) for k, v in sets.items()})
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print(f"{label}{' [' + ', '.join(out['labels_attached']) + ']' if out['labels_attached'] else ''} :: pack 10: {inclusion['reading']} "
          f"(gain V {inclusion['gain'].get('V')}, P {inclusion['gain'].get('P')}; bar {INCL_BAR}) :: " + '; '.join(why)
          + ' :: ' + ' | '.join(f"{k} {'ok' if v['holds'] else 'FAIL'} margin {v.get('margin')}" for k, v in clauses.items())
          + f" :: gate {'met' if (gt or {}).get('met') else 'NOT met'} " + str({s: r.get('mean') for s, r in ((gt or {}).get('seeds') or {}).items()})
          + f" :: overflow lines per training log {{{', '.join(f's{s}: {o['dropped']}' for s, o in tov.items())}}} (bar {O_BAR})"
          + f" :: beige r1 lift max {{{', '.join(f's{s}: {v['beige_r1_max_cm']}' for s, v in lift.items())}}} cm (clause >= {L_BAR_CM}: {out['lift']['holds_any_seed']})"
          + f" :: chosen seed {(ch or {}).get('chosen')} :: set {out['pieces']['set']} (MD5SUMS {str(out['pieces']['md5sums_md5'])[:12]})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('pieces'); p.add_argument('--set', required=True); p.add_argument('--dir', required=True); p.add_argument('--out', required=True)
    s = sp.add_parser('assets'); s.add_argument('--set', required=True); s.add_argument('--assets', required=True); s.add_argument('--pieces', required=True)
    s.add_argument('--out', required=True)
    r = sp.add_parser('arms'); r.add_argument('--content', default='/content'); r.add_argument('--seeds', default='42 43'); r.add_argument('--set', required=True)
    r.add_argument('--e10v_arms', required=True); r.add_argument('--out', required=True)
    c = sp.add_parser('cells'); c.add_argument('--content', default='/content'); c.add_argument('--seeds', default='42 43'); c.add_argument('--set', required=True)
    c.add_argument('--steps', type=int, required=True); c.add_argument('--packed_ck', required=True); c.add_argument('--out', required=True)
    h = sp.add_parser('choose'); h.add_argument('--cells', required=True); h.add_argument('--seeds', default='42 43'); h.add_argument('--out', required=True)
    g = sp.add_parser('gate'); g.add_argument('--cells', required=True); g.add_argument('--out', required=True)
    v = sp.add_parser('verify'); v.add_argument('--dir', required=True); v.add_argument('--out', required=True)
    d = sp.add_parser('verdict'); d.add_argument('--dir', required=True); d.add_argument('--score', action='append'); d.add_argument('--seeds', default='42 43')
    d.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(pieces=cmd_pieces, assets=cmd_assets, arms=cmd_arms, cells=cmd_cells, choose=cmd_choose, gate=cmd_gate, verify=cmd_verify,
         verdict=cmd_verdict)[a.cmd](a)


if __name__ == '__main__':
    main()
