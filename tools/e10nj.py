"""Eval-10 njmax diagnostic: tools of ops/jobs/ev10_nj.sh (2026-11-01; pre-registered in
docs/research/work/eval10-njmax-20261101/PREREG.md before any result). DIAGNOSTIC ONLY: a checkpoint trained or evaluated
with sim.njmax 1024 takes changed physics into evaluation, so nothing this job makes may enter a pack (tools/no_oracle.py
refuses its names and its checkpoints' stored configs). Eval 10: no ground truth exists or is read here.

  arms      the seed copy of e10v's stored V4p reference V (run 20261031-e10v-caf38fb): refs/<pre>s<seed>_glockt/ep10/<hive>/
            ref_gl_ilc.parquet = a byte copy of refs/perc2e10v_glockt/ep10/<hive>/ref_gl_ilc.parquet, the base link
            refs/<pre>s<seed>mck/ep10 -> refs/perc2e10vmck/ep10, results/<pre>s<seed>_glock_public/ep10/{rest_check.json,
            zero_score.txt} (what glock_public.sh REUSE_REF / REQUIRE_REUSE needs). V's md5 and trajectory fingerprint,
            the base reference's md5 and each URDF's mass / COM must equal e10v's arms.json (--e10v_arms). Exit 1 on failure.
  overflow  per group of log files (NAME=GLOB): MuJoCo-Warp's "nefc overflow - please increase njmax to N" lines (N's
            median / p95 / p99 / max), "broadphase overflow", "narrowphase overflow", "njmax_nnz overflow", "CCD overflow"
            and Newton's "exceeded MJWarp limit" lines; the first and last line number of each kind.
  lift      per curve checkpoint (tools/ckpt_curve.sh REP=3: curve/policy_<steps>/r<k>/episode_000010.parquet): sim_vs_ref
            per repeat and the curve value, and per cup the max lift above its first-frame height (cm, the definition of
            tools/ckpt_curve_summary.py), the reference lift, the share of frames within 3 cm, "lost at"; r1 is the
            repeat that curve.json and the job log's curve line show. --control NAME=curve.json adds e10v's curves.
  cksim     a copy of a FlashCHORD checkpoint whose stored resolved config (safetensors header, user.resolved_config_json)
            has other sim limits: sim.njmax / sim.nconmax and env.sim.njmax / env.sim.nconmax (env.sim = ${sim}, resolved).
            Only that header value changes; the header is re-serialised canonically (checked: an unmodified re-serialisation
            reproduces the input header byte for byte) and the tensor buffer is copied byte for byte. Checks: the input
            reads --from, the output reads --to, the flattened config differs in exactly those four keys, every other
            header entry and the buffer are identical. Exit 1 on failure (no output left).
  identity  the diagnostic checkpoint's stored config vs the control checkpoint (e10v seed 43's chosen one): only
            output_dir, task.parquet, reference.parquet and the four sim limits may differ, and the limits must read
            --want (1024 512) vs stock (512 256); reset.seed, training steps; task.parquet -> this seed's copy, md5 = V;
            the URDFs it loads exist and weigh 0.3 kg.
  guard     tools/no_oracle.py must REFUSE each given path as is and a byte copy of it under a neutral name.
  verdict   the PREREG section 4 label (INVALID / INCONCLUSIVE / FALSIFIED / SUPPORTED / PARTIAL / INCOMPLETE) plus the
            reported numbers (the 512 evaluation of the same checkpoint alongside; never gating).
Usage (box paths): see ops/jobs/ev10_nj.sh.
"""
import argparse, glob, hashlib, json, math, os, re, shutil, statistics, struct, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import md5                                                    # noqa: E402
from mass_verify import ck_config, flat, resolve_parquet, STEPS_KEY        # noqa: E402
from e11g_verify import urdfs_of, jsonish                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP, SRC_PRE, BASE = 10, 'perc2e10v', 'mck'
PLACEHOLDER = 0.3
SIM_KEYS = ('sim.njmax', 'sim.nconmax', 'env.sim.njmax', 'env.sim.nconmax')
STOCK = (512, 256)                                     # FlashCHORD configs/sim/rl.yaml (the sharpa_flash_sac experiment)
PATH_KEYS = ('output_dir', 'task.parquet', 'reference.parquet')
CARRIED, RESTING = 'beige_cup', 'blue_cup'             # the reference lifts the beige cup ~23.5 cm into the blue cup
# PREREG section 4 bars (fixed before any result)
O_BAR = 1000                 # overflow lines in the 1024 training's train.log
L_BAR_CM = 5.0               # carried-cup lift at >= 1 curve checkpoint (r1); e10v control max 2.5 cm over 14 [M]
A_BAR = 0.4593               # e10v's official confirmation mean sim_vs_ref vs V (10 draws) [M]
MIN_N = 10

KINDS = {
    'nefc': re.compile(rb'nefc overflow - please increase njmax to (\d+)'),
    'broadphase': re.compile(rb'broadphase overflow - please increase nconmax to (\d+) or naconmax to (\d+)'),
    'narrowphase': re.compile(rb'narrowphase overflow - please increase nconmax to (\d+) or naconmax to (\d+)'),
    'njmax_nnz': re.compile(rb'njmax_nnz overflow - please increase njmax_nnz to (\d+)'),
    'ccd': re.compile(rb'CCD overflow - please increase naccdmax to (\d+)'),
    'newton_contacts': re.compile(rb'Number of Newton contacts \((\d+)\) exceeded MJWarp limit \((\d+)\)'),
}
DROPPED = ('nefc', 'broadphase', 'narrowphase')        # the PREREG overflow count O (rows or contacts dropped)


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def pct(sorted_v, q):
    """numpy's default (linear) percentile of an already sorted list"""
    if not sorted_v:
        return None
    k = (len(sorted_v) - 1) * q / 100.0; lo = math.floor(k); hi = math.ceil(k)
    return float(sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (k - lo))


# ----------------------------------------------------------------------------------------------------------------- arms
def cmd_arms(a):
    C = a.content.rstrip('/'); ex = json.load(open(a.e10v_arms)); fails = []
    src = glob.glob(f'{C}/refs/{SRC_PRE}_glockt/ep{EP}/processed/*/*/ref_gl_ilc.parquet')
    if len(src) != 1:
        sys.exit(f'arms: {len(src)} references under refs/{SRC_PRE}_glockt/ep{EP} (one expected: e10v\'s V)')
    src = src[0]; R0 = f'{C}/refs/{SRC_PRE}{BASE}/ep{EP}'; hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/{SRC_PRE}_glockt/ep{EP}')
    base_pq = glob.glob(f'{R0}/{hive}/*.parquet')
    if len(base_pq) != 1:
        sys.exit(f'arms: {len(base_pq)} base references under {R0}/{hive}')
    res0 = f'{C}/results/{SRC_PRE}_glock_public/ep{EP}'
    if not os.path.isfile(f'{res0}/rest_check.json'):
        sys.exit(f'arms: {res0}/rest_check.json missing (glock_public.sh REUSE_REF needs it)')
    urd, fp = urdfs_of(src)
    man = dict(episode=EP, source_prefix=SRC_PRE, prefix=a.prefix, base=BASE, source_parquet=src, source_md5=md5(src),
               traj_fingerprint=fp, hive=hive, base_parquet=base_pq[0], base_md5=md5(base_pq[0]), urdfs=urd,
               e10v_arms=dict(path=a.e10v_arms, source_md5=ex.get('source_md5'), traj_fingerprint=ex.get('traj_fingerprint'),
                              base_md5=ex.get('base_md5')), rest_check=jsonish(f'{res0}/rest_check.json'), seeds={})
    if man['source_md5'] != ex.get('source_md5') or fp != ex.get('traj_fingerprint'):
        fails.append(f'V {man["source_md5"]} / fingerprint {fp[:12]} != e10v {ex.get("source_md5")} / {str(ex.get("traj_fingerprint"))[:12]}')
    if man['base_md5'] != ex.get('base_md5'):
        fails.append(f'base reference {man["base_md5"]} != e10v {ex.get("base_md5")}')
    for n, u in urd.items():
        eu = (ex.get('urdfs') or {}).get(n) or {}
        if u['md5'] is None:
            fails.append(f'{n} URDF {u["urdf"]} missing')
        elif abs(u['mass'] - PLACEHOLDER) > 1e-9:
            fails.append(f'{n} mass {u["mass"]} != {PLACEHOLDER}')
        if u['mass'] != eu.get('mass') or u['com'] != eu.get('com'):
            fails.append(f'{n} URDF differs from e10v\'s (mass {u["mass"]} vs {eu.get("mass")}, COM {u["com"]} vs {eu.get("com")})')
        u['md5_equals_e10v'] = u['md5'] == eu.get('md5')                # reported (e10v's re-run gate was mass / COM)
    s = str(a.seed); pre = f'{a.prefix}s{s}'; RD = f'{C}/refs/{pre}_glockt/ep{EP}'; dpq = f'{RD}/{hive}/ref_gl_ilc.parquet'
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
        fails.append('the seed copy is not a byte copy of V')
    man['ok'] = not fails; man['failures'] = fails
    json.dump(man, open(a.out, 'w'), indent=1)
    print(('ARMS OK' if not fails else 'ARMS FAILED: ' + ' | '.join(fails[:5])) + f" :: V {man['source_md5']} (fingerprint "
          f"{fp[:12]}; e10v {ex.get('source_md5')}), base {man['base_md5']}, copy {dpq}, "
          + ', '.join(f"{n} {u['mass']} kg md5=e10v {u['md5_equals_e10v']}" for n, u in urd.items()))
    sys.exit(0 if not fails else 1)


# ------------------------------------------------------------------------------------------------------------- overflow
def count_file(path):
    out = {k: dict(lines=0, first_line=None, last_line=None) for k in KINDS}; req = []; n = 0
    with open(path, 'rb') as f:
        for n, line in enumerate(f, 1):
            if b'overflow' not in line and b'exceeded MJWarp' not in line:
                continue
            for k, rx in KINDS.items():
                m = rx.search(line)
                if m:
                    o = out[k]; o['lines'] += 1; o['last_line'] = n
                    if o['first_line'] is None:
                        o['first_line'] = n
                    if k == 'nefc':
                        req.append(int(m.group(1)))
    return out, req, n


def cmd_overflow(a):
    res = dict(rule='docs/research/work/eval10-njmax-20261101/PREREG.md section 4 (O = nefc + broadphase + narrowphase lines '
                    'of the 1024 training train.log)', groups={})
    for spec in a.group:
        name, g = spec.split('=', 1)
        files = sorted(set(sum((glob.glob(x) for x in g.split(',')), [])))
        agg = {k: 0 for k in KINDS}; req = []; per = {}; total_lines = 0
        for f in files:
            o, r, n = count_file(f); total_lines += n; req += r
            per[f] = dict(lines_total=n, **{k: v['lines'] for k, v in o.items()},
                          first_line={k: v['first_line'] for k, v in o.items() if v['first_line']},
                          last_line={k: v['last_line'] for k, v in o.items() if v['last_line']})
            for k in KINDS:
                agg[k] += o[k]['lines']
        req.sort()
        res['groups'][name] = dict(glob=g, files=len(files), lines_total=total_lines, counts=agg,
                                   dropped=sum(agg[k] for k in DROPPED),
                                   njmax_requested=dict(n=len(req), median=pct(req, 50), p95=pct(req, 95), p99=pct(req, 99),
                                                        max=req[-1] if req else None, min=req[0] if req else None),
                                   per_file=per)
    json.dump(res, open(a.out, 'w'), indent=1)
    for name, g in res['groups'].items():
        r = g['njmax_requested']
        print(f"overflow {name}: {g['files']} files, {g['lines_total']} lines; nefc {g['counts']['nefc']} (requested median {r['median']} "
              f"p95 {r['p95']} max {r['max']}), broadphase {g['counts']['broadphase']}, narrowphase {g['counts']['narrowphase']}, "
              f"njmax_nnz {g['counts']['njmax_nnz']}, ccd {g['counts']['ccd']}, newton {g['counts']['newton_contacts']}")


# ----------------------------------------------------------------------------------------------------------------- lift
def lifts(pqf):
    """per object: max lift above the first frame (cm), reference lift, within-3 cm share, lost at (ckpt_curve_summary.py)"""
    import numpy as np, pyarrow.parquet as pq
    t = pq.read_table(pqf).to_pandas(); t = t[t.environment_id == t.environment_id.min()]; out = {}
    for n, g in t.groupby('object_body_name'):
        g = g.sort_values('step'); A = g[['achieved_position_x', 'achieved_position_y', 'achieved_position_z']].values
        R = g[['reference_position_x', 'reference_position_y', 'reference_position_z']].values; e = np.linalg.norm(A - R, axis=1)
        moving = np.nonzero(np.linalg.norm(R - R[0], axis=1) > 0.03)[0]; start = int(moving[0]) if len(moving) else 0
        lost = np.nonzero(e[start:] > 0.10)[0]
        out[str(n)] = dict(lift_cm=round(100 * float((A[:, 2] - A[0, 2]).max()), 1), ref_lift_cm=round(100 * float((R[:, 2] - R[0, 2]).max()), 1),
                           within3cm=round(float((e < 0.03).mean()), 2), lost_at=int(start + lost[0]) if len(lost) else None, frames=len(e))
    return out


def steps_of(d):
    m = re.findall(r'\d+', os.path.basename(d.rstrip('/')))
    return int(m[0]) if m else -1


def cmd_lift(a):
    rows = []
    for d in sorted(glob.glob(f'{a.curve}/policy_*/'), key=steps_of):
        row = dict(checkpoint=os.path.basename(d[:-1]), steps=steps_of(d), ckpt_M=round(steps_of(d) / 1e6), repeats={})
        try:
            row['sim_vs_ref'] = json.load(open(f'{d}qa_policy.json')).get('sim_vs_ref')
        except Exception:
            row['sim_vs_ref'] = None
        reps = sorted(glob.glob(f'{d}r*/'), key=lambda x: int(re.findall(r'r(\d+)/$', x)[0]))
        if not reps and glob.glob(f'{d}episode_*.parquet'):
            reps = [d]                                                  # REP=1 layout
        for r in reps:
            k = os.path.basename(r[:-1]) if r != d else 'r1'
            try:
                q = json.load(open(f'{r}qa_policy.json')).get('sim_vs_ref')
            except Exception:
                q = None
            try:
                ob = lifts(sorted(glob.glob(f'{r}episode_*.parquet'))[0])
            except Exception as e:
                ob = dict(error=f'{type(e).__name__}: {str(e)[:160]}')
            row['repeats'][k] = dict(sim_vs_ref=q, objects=ob)
        r1 = (row['repeats'].get('r1') or {}).get('objects') or {}
        row['carried_lift_r1_cm'] = (r1.get(CARRIED) or {}).get('lift_cm')
        allr = [x['objects'][CARRIED]['lift_cm'] for x in row['repeats'].values() if CARRIED in (x.get('objects') or {})]
        row['carried_lift_max_cm'] = max(allr) if allr else None
        row['resting_lift_r1_cm'] = (r1.get(RESTING) or {}).get('lift_cm')
        rows.append(row)
    ctrl = {}
    for spec in a.control or []:
        name, f = spec.split('=', 1)
        try:
            c = json.load(open(f))
            ctrl[name] = dict(path=f, rows=[dict(ckpt_M=r['ckpt_M'], sim_vs_ref=r['sim_vs_ref'],
                                                 carried_lift_r1_cm=(r.get(CARRIED) or {}).get('lift_cm'),
                                                 resting_lift_r1_cm=(r.get(RESTING) or {}).get('lift_cm'),
                                                 carried_ref_lift_cm=(r.get(CARRIED) or {}).get('ref_lift_cm')) for r in c])
            v = [x['carried_lift_r1_cm'] for x in ctrl[name]['rows'] if x['carried_lift_r1_cm'] is not None]
            ctrl[name]['carried_lift_r1_max_cm'] = max(v) if v else None
        except Exception as e:
            ctrl[name] = dict(path=f, error=f'{type(e).__name__}: {str(e)[:160]}')
    v = [r['carried_lift_r1_cm'] for r in rows if r['carried_lift_r1_cm'] is not None]
    vm = [r['carried_lift_max_cm'] for r in rows if r['carried_lift_max_cm'] is not None]
    obs = [((r['repeats'].get('r1') or {}).get('objects') or {}) for r in rows]
    refl = {}
    for n in (CARRIED, RESTING):
        x = [o[n]['ref_lift_cm'] for o in obs if 'ref_lift_cm' in (o.get(n) or {})]
        refl[n] = max(x) if x else None
    out = dict(rule=f'PREREG section 4 clause L: {CARRIED} r1 lift >= {L_BAR_CM} cm at >= 1 curve checkpoint', carried=CARRIED,
               reference_lift_cm=refl, checkpoints=rows, n_checkpoints=len(rows),
               carried_lift_r1_max_cm=max(v) if v else None, carried_lift_any_repeat_max_cm=max(vm) if vm else None,
               L=bool(v) and max(v) >= L_BAR_CM - 1e-9, controls=ctrl)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f"lift: {len(rows)} checkpoints; " + '; '.join(
        f"{r['ckpt_M']}M s_v_r {r['sim_vs_ref']} {CARRIED} r1 {r['carried_lift_r1_cm']} (max of {len(r['repeats'])} {r['carried_lift_max_cm']}) "
        f"{RESTING} r1 {r['resting_lift_r1_cm']}" for r in rows)
        + f" :: L {out['L']} (r1 max {out['carried_lift_r1_max_cm']} cm, bar {L_BAR_CM}); controls "
        + ', '.join(f"{k} r1 max {c.get('carried_lift_r1_max_cm')}" for k, c in ctrl.items()))


# ---------------------------------------------------------------------------------------------------------------- cksim
def read_header(path):
    with open(path, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; raw = f.read(n)
    return n, raw, json.loads(raw)


def sim_limits(cfg):
    fl = flat(cfg)
    return {k: fl.get(k) for k in SIM_KEYS}


def cmd_cksim(a):
    frm, to = tuple(a.frm), tuple(a.to); fails = []
    n, raw, h = read_header(a.src)
    canon = json.dumps(h, separators=(',', ':')).encode()
    if canon != raw.rstrip(b' '):
        sys.exit('cksim: the input header does not re-serialise byte for byte (refusing to rewrite it)')
    meta = h['__metadata__']; cfg_s = meta['user.resolved_config_json']; cfg = json.loads(cfg_s)
    if json.dumps(cfg, sort_keys=True, separators=(',', ':')) != cfg_s:
        sys.exit('cksim: the stored resolved config is not canonical JSON (refusing to rewrite it)')
    before = sim_limits(cfg)
    want_before = {'sim.njmax': frm[0], 'sim.nconmax': frm[1], 'env.sim.njmax': frm[0], 'env.sim.nconmax': frm[1]}
    if before != want_before:
        sys.exit(f'cksim: input sim limits {before} != --from {want_before}')
    new = json.loads(cfg_s)
    for blk in (new['sim'], new['env']['sim']):
        blk['njmax'], blk['nconmax'] = to[0], to[1]
    h2 = json.loads(raw); h2['__metadata__']['user.resolved_config_json'] = json.dumps(new, sort_keys=True, separators=(',', ':'))
    hb = json.dumps(h2, separators=(',', ':')).encode(); hb += b' ' * (-len(hb) % 8)
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    tmp = a.dst + '.tmp'
    with open(a.src, 'rb') as fi, open(tmp, 'wb') as fo:
        fi.seek(8 + n); fo.write(struct.pack('<Q', len(hb))); fo.write(hb)
        for b in iter(lambda: fi.read(1 << 22), b''):
            fo.write(b)
    # checks on the written file
    n2, raw2, h3 = read_header(tmp); c3 = json.loads(h3['__metadata__']['user.resolved_config_json'])
    f0, f1 = flat(cfg), flat(c3); diff = sorted(k for k in set(f0) | set(f1) if f0.get(k) != f1.get(k))
    if diff != sorted(SIM_KEYS):
        fails.append(f'config diff {diff} != the four sim limits')
    if sim_limits(c3) != {'sim.njmax': to[0], 'sim.nconmax': to[1], 'env.sim.njmax': to[0], 'env.sim.nconmax': to[1]}:
        fails.append(f'output sim limits {sim_limits(c3)} != --to {to}')
    other = sorted(k for k in set(h) | set(h3) if k != '__metadata__' and h.get(k) != h3.get(k))
    other_meta = sorted(k for k in set(meta) | set(h3['__metadata__']) if k != 'user.resolved_config_json' and meta.get(k) != h3['__metadata__'].get(k))
    if other or other_meta:
        fails.append(f'other header entries differ: tensors {other[:5]}, metadata {other_meta[:5]}')
    with open(a.src, 'rb') as f:
        f.seek(8 + n); hb_src = hashlib.sha256(f.read()).hexdigest()
    with open(tmp, 'rb') as f:
        f.seek(8 + n2); hb_dst = hashlib.sha256(f.read()).hexdigest()
    if hb_src != hb_dst:
        fails.append('tensor buffer differs')
    if (n2 - 0) % 8:
        fails.append(f'header length {n2} is not a multiple of 8')
    rep = dict(src=os.path.abspath(a.src), dst=os.path.abspath(a.dst), src_sha256=sha256(a.src), dst_sha256=sha256(tmp),
               src_sim=before, dst_sim=sim_limits(c3), config_diff=diff, header_bytes=[n, n2], buffer_sha256=hb_src,
               buffer_identical=hb_src == hb_dst, other_header_entries_differ=other, other_metadata_differ=other_meta,
               tensors=sum(1 for k in h if k != '__metadata__'), ok=not fails, failures=fails)
    if fails:
        os.remove(tmp)
    else:
        os.replace(tmp, a.dst)
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1)
    print(('CKSIM OK' if not fails else 'CKSIM FAILED: ' + ' | '.join(fails)) + f" :: {before} -> {sim_limits(c3)}; config diff {diff}; "
          f"buffer identical {hb_src == hb_dst} ({rep['tensors']} tensors); sha256 {rep['src_sha256'][:12]} -> {rep['dst_sha256'][:12]}")
    sys.exit(0 if not fails else 1)


# ------------------------------------------------------------------------------------------------------------- identity
def cmd_identity(a):
    C = a.content.rstrip('/'); fails = []; want = tuple(a.want)
    man = json.load(open(a.arms)) if a.arms and os.path.isfile(a.arms) else {}
    m1, c1 = ck_config(a.ck); m0, c0 = ck_config(a.control)
    f1, f0 = flat(c1), flat(c0); diff = sorted(k for k in set(f1) | set(f0) if f1.get(k) != f0.get(k))
    bad = [k for k in diff if k not in PATH_KEYS and k not in SIM_KEYS]
    if bad:
        fails.append(f'stored config differs from the control in {bad[:8]} (only {list(PATH_KEYS)} and the sim limits may)')
    s1, s0 = sim_limits(c1), sim_limits(c0)
    if s1 != {'sim.njmax': want[0], 'sim.nconmax': want[1], 'env.sim.njmax': want[0], 'env.sim.nconmax': want[1]}:
        fails.append(f'diagnostic checkpoint sim limits {s1} != {want} (the training override did not reach the stored config)')
    if s0 != {'sim.njmax': STOCK[0], 'sim.nconmax': STOCK[1], 'env.sim.njmax': STOCK[0], 'env.sim.nconmax': STOCK[1]}:
        fails.append(f'control sim limits {s0} are not stock {STOCK}')
    seed = (c1.get('reset') or {}).get('seed')
    if str(seed) != str(a.seed) or str((c0.get('reset') or {}).get('seed')) != str(a.seed):
        fails.append(f'reset.seed {seed} / control {(c0.get("reset") or {}).get("seed")} != {a.seed}')
    if str(f1.get(STEPS_KEY)) != str(a.steps):
        fails.append(f'{STEPS_KEY} {f1.get(STEPS_KEY)} != {a.steps}')
    row = dict(ck=a.ck, ck_sha256=sha256(a.ck), ck_steps=m1.get('user.environment_steps'), control=a.control,
               control_sha256=sha256(a.control), config_diff=diff, sim=s1, control_sim=s0, reset_seed=seed)
    try:
        task = c1['task']['parquet']; rp = resolve_parquet(task.strip("'")); row.update(task_parquet=task, reference_file=rp, reference_md5=md5(rp))
        want_dir = os.path.realpath(f'{C}/refs/{a.prefix}s{a.seed}_glockt/ep{EP}') + '/'
        if not os.path.realpath(rp).startswith(want_dir):
            fails.append(f'trained on {rp}, not this seed\'s copy under {want_dir}')
        if row['reference_md5'] != man.get('source_md5'):
            fails.append(f'reference md5 {row["reference_md5"]} != V {man.get("source_md5")}')
        urd, _ = urdfs_of(rp); row['loaded_urdfs'] = urd
        for n, u in urd.items():
            if u['md5'] is None:
                fails.append(f'{n}: {u["urdf"]} missing')
            elif abs(u['mass'] - PLACEHOLDER) > 1e-9:
                fails.append(f'{n} loads {u["mass"]} kg')
    except Exception as e:
        fails.append(f'reference chain: {type(e).__name__}: {str(e)[:200]}')
    row['ok'] = not fails; row['failures'] = fails
    json.dump(row, open(a.out, 'w'), indent=1, default=str)
    print(('IDENTITY OK' if not fails else 'IDENTITY FAILED: ' + ' | '.join(fails[:5])) + f" :: config diff vs e10v s{a.seed} {diff}; "
          f"sim {s1} vs control {s0}; reference md5 {row.get('reference_md5')}")
    sys.exit(0 if not fails else 1)


# ---------------------------------------------------------------------------------------------------------------- guard
def cmd_guard(a):
    guard = os.path.join(a.repo, 'tools', 'no_oracle.py'); rows = []
    tmp = os.path.join(a.neutral_dir or tempfile.gettempdir(), 'nj_guard_neutral')   # a fixed name without any guarded token
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    for i, p in enumerate(a.paths):
        cases = [('as is', p)]
        if os.path.isfile(p):
            q = os.path.join(tmp, f'n{i}', os.path.basename(p)); os.makedirs(os.path.dirname(q)); shutil.copyfile(p, q)
            cases.append(('neutral byte copy', q))
            j = os.path.join(tmp, f'n{i}', 'checkpoints.json'); json.dump({'10': q}, open(j, 'w'))
            cases.append(('kit checkpoints JSON naming the neutral copy', j))
        for how, w in cases:
            r = subprocess.run([sys.executable, '-I', guard, w], capture_output=True, text=True, cwd=a.repo)
            rows.append(dict(path=p, how=how, word=w, rc=r.returncode, refused=r.returncode != 0,
                             why=(r.stderr or r.stdout).strip().splitlines()[-1][:300] if (r.stderr or r.stdout).strip() else ''))
    shutil.rmtree(tmp, ignore_errors=True)
    out = dict(ok=all(r['refused'] for r in rows), cases=rows)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(('GUARD OK' if out['ok'] else 'GUARD FAILED') + f": {sum(r['refused'] for r in rows)}/{len(rows)} refused :: "
          + '; '.join(f"{os.path.basename(r['path'])} {r['how']}: {'REFUSED' if r['refused'] else 'ACCEPTED'}" for r in rows))
    sys.exit(0 if out['ok'] else 1)


# -------------------------------------------------------------------------------------------------------------- verdict
def fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def stats(v):
    if not v:
        return None
    m = sum(v) / len(v); sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
    return dict(n=len(v), mean=round(m, 4), sd=round(sd, 4), min=round(min(v), 4), max=round(max(v), 4),
                median=round(statistics.median(v), 4), mean_raw=m)


def side(rows, X):
    s = [r['vs'][X] for r in rows if X in r.get('vs', {})]
    if not s:
        return None
    return dict(n=len(s), sim_vs_ref=stats([x['sim_vs_ref'] for x in s]), RPE=stats([x['RPE'] for x in s]),
                AUC=stats([x['AUC'] for x in s]), fail_rate=round(sum(1 for x in s if x['RPE'] > 5.0) / len(s), 4),
                objects={o: dict(AUC=round(sum(x['objects'][o]['AUC'] for x in s) / len(s), 4),
                                 sim_travel_cm=round(sum(x['objects'][o]['sim_travel_cm'] for x in s) / len(s), 2),
                                 ref_travel_cm=s[0]['objects'][o]['ref_travel_cm']) for o in s[0]['objects']})


def js(f):
    try:
        return json.load(open(f)) if f and os.path.isfile(f) else None
    except Exception:
        return None


def conf_check(G, name, sha):
    """official draws of a set: count, return codes, every episode json names the expected checkpoint sha256"""
    eps = sorted(glob.glob(f'{G}/{name}/r*/ep{EP}/episode_{EP:06d}.json')); bad = []
    for f in eps:
        d = js(f) or {}
        if d.get('checkpoint_sha256') != sha:
            bad.append(f'{os.path.relpath(f, G)} names {str(d.get("checkpoint_sha256"))[:12]}')
    rcs = [open(f).read().strip() for f in glob.glob(f'{G}/{name}/r*/eval_rc.txt')]
    return dict(calls=len(rcs), eval_rc={x: rcs.count(x) for x in sorted(set(rcs))}, episode_jsons=len(eps), wrong_checkpoint=bad)


def cmd_verdict(a):
    G = a.dir.rstrip('/'); inv, notes = [], []
    if os.path.exists(f'{G}/STOPPED'):
        inv.append(f'job stopped: {open(f"{G}/STOPPED").read().strip()[:300]}')
    arms, ov, lf, idn, cks, sol, grd, sc = (js(f'{G}/{x}.json') for x in ('arms', 'overflow', 'lift', 'identity', 'ck512', 'solver_check', 'guard', 'score'))
    if not arms or not arms.get('ok'):
        inv.append(f'arms (V identity) not ok: {(arms or {}).get("failures", "arms.json missing")}')
    ck = a.ck1024 if a.ck1024 and os.path.isfile(a.ck1024) else None
    if not ck:
        inv.append('no chosen 1024 checkpoint (training or curve failed)')
    if not idn or not idn.get('ok'):
        inv.append(f'identity not ok: {(idn or {}).get("failures", "identity.json missing")}')
    tr = ((ov or {}).get('groups') or {}).get('train')
    if not tr or not tr.get('files'):
        inv.append('no training log counted (overflow.json group train)')
    O = tr['dropped'] if tr else None
    sha1024 = sha256(ck) if ck else None
    sha512 = sha256(a.ck512) if a.ck512 and os.path.isfile(a.ck512) else None
    sets = (sc or {}).get('sets') or {}
    def scored(name, sha, own='V'):
        rows = [r for r in (sets.get(name) or {}).get('rollouts', []) if r.get('scored') and all(X in r.get('vs', {}) for X in ('V', 'P'))]
        bad = [f'{name}/r{r.get("draw")}' for r in rows if not (r.get('own_ref_check') or {}).get('ok')]
        if sha:
            bad += [f'{name}/r{r.get("draw")} checkpoint {str(r.get("checkpoint_sha256"))[:12]}' for r in rows if r.get('checkpoint_sha256') != sha]
        return rows, bad
    c1024, bad1024 = scored('conf1024', sha1024)
    if bad1024:
        inv.append(f'1024 draws failing the own-reference / checkpoint check: {bad1024[:5]}')
    cc1024 = conf_check(G, 'conf1024', sha1024)
    if cc1024['wrong_checkpoint']:
        inv.append(f'1024 draws of another checkpoint: {cc1024["wrong_checkpoint"][:3]}')
    vals = [r['vs']['V']['sim_vs_ref'] for r in c1024]
    if any(not fin(x) for x in vals):
        inv.append('a non-finite score among the scored 1024 draws')
    # main label (PREREG section 4)
    L = (lf or {}).get('L'); n1024 = len(c1024); A_mean = (sum(vals) / n1024) if n1024 else None
    if inv:
        label = 'INVALID'
    elif O > O_BAR:
        label = 'INCONCLUSIVE'
    elif not L:
        label = 'FALSIFIED'
    elif n1024 < MIN_N:
        label = 'INCOMPLETE'
    elif A_mean > A_BAR + 1e-9:
        label = 'SUPPORTED'
    else:
        label = 'PARTIAL'
    # the 512 readout of the same checkpoint (reported alongside; never gating)
    c512, bad512 = scored('conf512', sha512); cc512 = conf_check(G, 'conf512', sha512)
    s512 = []
    if not cks or not cks.get('ok'):
        s512.append('ck512 copy check not ok')
    sol_rows = (sol or {}).get('checkpoints') or {}
    sv = sol_rows.get('ck512') or {}
    if sv.get('env_config_sim') != [STOCK[0], STOCK[1]]:
        s512.append(f'evaluator config chain of the copy reads {sv.get("env_config_sim")} (want {list(STOCK)})')
    if sv.get('solver') and sv['solver'].get('njmax') is not None and sv['solver'].get('njmax') != STOCK[0]:
        s512.append(f'the copy\'s solver was built with njmax {sv["solver"].get("njmax")}')
    if bad512 or cc512['wrong_checkpoint']:
        s512.append(f'512 draws failing the own-reference / checkpoint check: {(bad512 + cc512["wrong_checkpoint"])[:4]}')
    if not c512:
        s512.append('no scored 512 draw')
    v512 = [r['vs']['V']['sim_vs_ref'] for r in c512]
    status512 = 'VALID' if not s512 else ('INVALID' if not (len(s512) == 1 and s512[0] == 'no scored 512 draw') else 'MISSING')
    if sv.get('solver') is None:
        notes.append('512 copy: solver-level check not done on the box (config chain only); see solver_check.json')
    ctl = scored('e10vconf', None)[0]; tr1024 = scored('train1024', None)[0]
    out = dict(label=label, rule='docs/research/work/eval10-njmax-20261101/PREREG.md section 4', diagnostic_only=True,
               never_packed='tools/no_oracle.py refuses every name of this run (-e10nj-, perc2e10nj*, ev10_nj) and any checkpoint '
                            'whose stored sim limits are not stock',
               invalid_reasons=inv, notes=notes,
               clauses=dict(O=dict(value=O, bar=O_BAR, holds=O is not None and O <= O_BAR,
                                   nefc=(tr or {}).get('counts', {}).get('nefc'), broadphase=(tr or {}).get('counts', {}).get('broadphase'),
                                   narrowphase=(tr or {}).get('counts', {}).get('narrowphase'),
                                   njmax_requested=(tr or {}).get('njmax_requested'),
                                   baseline_e10v='6,010,501 (s42) / 5,846,480 (s43) nefc lines; requested median 580, p95 752, max ~1,050 [M]'),
                            L=dict(value_cm=(lf or {}).get('carried_lift_r1_max_cm'), any_repeat_cm=(lf or {}).get('carried_lift_any_repeat_max_cm'),
                                   bar_cm=L_BAR_CM, holds=bool(L), object=CARRIED,
                                   controls={k: c.get('carried_lift_r1_max_cm') for k, c in ((lf or {}).get('controls') or {}).items()}),
                            A=dict(n=n1024, mean=round(A_mean, 4) if A_mean is not None else None, bar=A_BAR,
                                   holds=A_mean is not None and n1024 >= MIN_N and A_mean > A_BAR + 1e-9)),
               sets={k: dict(V=side(v, 'V'), P=side(v, 'P')) for k, v in (('conf1024', c1024), ('conf512', c512), ('train1024', tr1024),
                                                                           ('e10v_conf_control', ctl))},
               readout_512=dict(status=status512, problems=s512, n=len(c512),
                                mean_V=round(sum(v512) / len(v512), 4) if v512 else None,
                                delta_vs_1024_V=round(sum(v512) / len(v512) - A_mean, 4) if v512 and A_mean is not None else None,
                                checkpoint_sha256=sha512, solver=sv, ck512=cks),
               checkpoints=dict(ck1024=ck, sha256_1024=sha1024, ck512=a.ck512, sha256_512=sha512),
               official_draws=dict(conf1024=cc1024, conf512=cc512),
               overflow_other={k: dict(files=g.get('files'), dropped=g.get('dropped'), counts=g.get('counts'))
                               for k, g in ((ov or {}).get('groups') or {}).items() if k != 'train'},
               lift_curve=[dict(ckpt_M=r['ckpt_M'], sim_vs_ref=r['sim_vs_ref'], carried_r1=r['carried_lift_r1_cm'],
                                carried_max=r['carried_lift_max_cm'], resting_r1=r['resting_lift_r1_cm']) for r in (lf or {}).get('checkpoints', [])],
               guard=dict(ok=(grd or {}).get('ok'), refused=sum(1 for c in (grd or {}).get('cases', []) if c.get('refused')),
                          cases=len((grd or {}).get('cases', []))),
               identity=dict(ok=(idn or {}).get('ok'), config_diff=(idn or {}).get('config_diff')))
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    cl = out['clauses']
    print(f"{label} :: O {cl['O']['value']} (bar {O_BAR}; nefc {cl['O']['nefc']}, broadphase {cl['O']['broadphase']}, narrowphase "
          f"{cl['O']['narrowphase']}; requested median {(cl['O']['njmax_requested'] or {}).get('median')} max {(cl['O']['njmax_requested'] or {}).get('max')}) "
          f"| L {CARRIED} r1 max {cl['L']['value_cm']} cm (bar {L_BAR_CM}; any repeat {cl['L']['any_repeat_cm']}; e10v control {cl['L']['controls']}) "
          f"| A n {n1024} mean sim_vs_ref vs V {cl['A']['mean']} (bar > {A_BAR})"
          + (f" | INVALID: {' | '.join(inv[:4])}" if inv else '')
          + f" || 512 readout {status512}: n {len(c512)} mean vs V {out['readout_512']['mean_V']} (delta vs 1024 {out['readout_512']['delta_vs_1024_V']})"
          + (f" problems {s512[:3]}" if s512 else '')
          + f" || vs P: 1024 {((out['sets']['conf1024']['P'] or {}).get('sim_vs_ref') or {}).get('mean')}, 512 {((out['sets']['conf512']['P'] or {}).get('sim_vs_ref') or {}).get('mean')}"
          + f" || e10v control re-scored: {((out['sets']['e10v_conf_control']['V'] or {}).get('sim_vs_ref') or {}).get('mean')} vs V"
          + f" || guard {out['guard']['refused']}/{out['guard']['cases']} refused || DIAGNOSTIC ONLY, NEVER PACKED")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('arms'); r.add_argument('--content', default='/content'); r.add_argument('--prefix', default='perc2e10nj')
    r.add_argument('--seed', type=int, default=43); r.add_argument('--e10v_arms', required=True); r.add_argument('--out', required=True)
    o = sp.add_parser('overflow'); o.add_argument('--group', action='append', required=True, help='NAME=GLOB[,GLOB...]'); o.add_argument('--out', required=True)
    li = sp.add_parser('lift'); li.add_argument('--curve', required=True); li.add_argument('--control', action='append'); li.add_argument('--out', required=True)
    c = sp.add_parser('cksim'); c.add_argument('--src', required=True); c.add_argument('--dst', required=True)
    c.add_argument('--from', dest='frm', type=int, nargs=2, required=True); c.add_argument('--to', type=int, nargs=2, required=True)
    c.add_argument('--out', default=None)
    i = sp.add_parser('identity'); i.add_argument('--content', default='/content'); i.add_argument('--prefix', default='perc2e10nj')
    i.add_argument('--ck', required=True); i.add_argument('--control', required=True); i.add_argument('--seed', type=int, default=43)
    i.add_argument('--steps', type=int, required=True); i.add_argument('--want', type=int, nargs=2, default=[1024, 512])
    i.add_argument('--arms', required=True); i.add_argument('--out', required=True)
    g = sp.add_parser('guard'); g.add_argument('--repo', default=REPO); g.add_argument('--neutral_dir', default=None)
    g.add_argument('--out', required=True); g.add_argument('paths', nargs='+')
    v = sp.add_parser('verdict'); v.add_argument('--dir', required=True); v.add_argument('--ck1024', default=None)
    v.add_argument('--ck512', default=None); v.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(arms=cmd_arms, overflow=cmd_overflow, lift=cmd_lift, cksim=cmd_cksim, identity=cmd_identity, guard=cmd_guard,
         verdict=cmd_verdict)[a.cmd](a)


if __name__ == '__main__':
    main()
