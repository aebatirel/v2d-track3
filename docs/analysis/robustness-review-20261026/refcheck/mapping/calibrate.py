"""Calibrate the loss-budget model on PUBLIC episodes (diagnostics only; mocap is read only to score, after inference).

For every distinct stored evaluator rollout of a public episode (store results dirs with episode_XXXXXX.parquet,
deduplicated by the parquet's sha256) this computes three numbers:
  T = the simulated object path vs mocap, registered Track 3 ADD AUC with the meshes the run simulated
      (pipeline/score_registered.py's computation; leaderboard-like truth score);
  S = sim_vs_ref, the simulated path vs OUR reference (the rollout's reference_xyzw columns), computed exactly as
      pipeline/qa.py policy does (kit AUC, frame-0 warp, 500 points on a 5 cm sphere per object; no mesh);
  R = our reference vs mocap, registered, same meshes as T.
then fits the loss-budget models (T = k*S, T = S*R, T = a*S*R, T = a + b*S) per rollout and per policy mean
(policy = checkpoint sha256 + reference), and measures how much of a sim_vs_ref gain transfers to T on pairs of
policies of the same episode and reference.

Steps (each resumable; WORK holds the bulky state; OUT gets small json / md / png):
  python -I calibrate.py inventory   # list public rollout parquets in the HF store, sha256 via the HF API, dedupe
  python -I calibrate.py fetch       # download one copy of each distinct parquet + its small sibling jsons + job.log
  python -I calibrate.py libs        # mesh library each run simulated (make_assets fingerprint in job.log)
  python -I calibrate.py verify      # our in-process scorer == pipeline/score_registered.py on a few rollouts
  python -I calibrate.py score [--max N] [--recent N]   # T, R, S per distinct rollout (registration cached)
  python -I calibrate.py fit         # fits, residuals, transfer; writes OUT/calibration.json, tables.md, ...
  python -I calibrate.py frames      # frame-local loss model (per-frame shares; diagnostic, adds to calibration.json)
  python -I calibrate.py symS        # GT-free symmetric yardstick S_mesh per rollout (hypothesis test; then re-run fit)
  python -I calibrate.py plot        # OUT/calibration.png (any python with numpy + matplotlib)
Paths: --sp (refcheck scratch root), --repo (this repository), --out (this folder).
Scoring with cached registration reproduces score_registered.py exactly (checked by `verify`): the registration and
the reference score depend only on (episode, meshes) and (episode, meshes, reference path), so each is done once.
"""
import argparse, collections, glob, hashlib, json, os, re, sys, time

import numpy as np

REPO_ID = 'aebatirel/v2d-store'
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
HERE = os.path.dirname(os.path.abspath(__file__))
SP_DEFAULT = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
LIBS = ['library_v2', 'library_v3', 'library_v3x', 'library_v4', 'library_v3p']


def args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('step', choices=['inventory', 'fetch', 'libs', 'verify', 'score', 'fit', 'frames', 'symS', 'plot', 'all'])
    p.add_argument('--sp', default=os.environ.get('REFCHECK_SP', SP_DEFAULT))
    p.add_argument('--repo', default=os.path.abspath(os.path.join(HERE, '../../../../..')))
    p.add_argument('--out', default=HERE)
    p.add_argument('--files', default=None, help='store file list json (default: list the HF repo, cached in WORK)')
    p.add_argument('--max', type=int, default=0, help='score at most N distinct rollouts (0 = all)')
    p.add_argument('--recent', type=int, default=0, help='keep only the N most recent distinct rollouts (by run name)')
    p.add_argument('--include_curves', type=int, default=1, help='also score checkpoint-curve / sweep rollouts')
    a = p.parse_args()
    a.sp = os.path.abspath(a.sp); a.work = os.path.join(a.sp, 'work', 'mapping'); a.store = os.path.join(a.sp, 'store')
    a.t3 = os.path.join(a.sp, 't3'); a.kit = os.path.join(a.sp, 'kit', 'v2d_submission_kit')
    os.makedirs(a.work, exist_ok=True)
    return a


def jload(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def jdump(o, p):
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(o, f, indent=1)
    os.replace(tmp, p)


def ep_of(path):
    m = re.search(r'/episode_(\d{6})\.parquet$', path)
    return int(m.group(1)) if m else None


def run_of(path):
    return path.split('/')[1]


def kind_of(path):
    """What the rollout is: 'best' (repeat evaluation of the chosen checkpoint), 'curve' / 'sweep' (one evaluation per
    checkpoint along training), 'final' (pack / one-off), 'other'."""
    rel = path.split('/results/', 1)[-1]
    if '/curve/' in rel:
        return 'curve'
    if '/sweep/' in rel:
        return 'sweep'
    if re.search(r'/best/r\d+/', rel) or re.search(r'/r\d+/episode_', rel):
        return 'repeat'
    return 'single'


# ---------------------------------------------------------------- inventory
def step_inventory(a):
    from huggingface_hub import HfApi
    api = HfApi()
    if a.files:
        files = json.load(open(a.files))
    else:
        cache = os.path.join(a.work, 'store_files.json')
        if not os.path.exists(cache):
            jdump(api.list_repo_files(REPO_ID, repo_type='dataset'), cache)
        files = json.load(open(cache))
    fs = set(files)
    pq = sorted(p for p in files if '/results/' in p and ep_of(p) in PUBLIC)
    print(f'{len(files)} store files, {len(pq)} public evaluator parquets', flush=True)
    meta = jload(os.path.join(a.work, 'paths_info.json'), {})
    todo = [p for p in pq if p not in meta]
    for i in range(0, len(todo), 400):
        for r in api.get_paths_info(REPO_ID, todo[i:i + 400], repo_type='dataset'):
            meta[r.path] = dict(size=r.size, sha256=r.lfs.sha256 if r.lfs else None, blob=r.blob_id)
        jdump(meta, os.path.join(a.work, 'paths_info.json'))
    rows = []
    for p in pq:
        d = os.path.dirname(p); e = ep_of(p)
        sib = {k: f'{d}/{n}' for k, n in (('json', f'episode_{e:06d}.json'), ('qa', 'qa_policy.json'),
                                         ('sr', f'score_registered_ep{e}.json')) if f'{d}/{n}' in fs}
        rows.append(dict(path=p, ep=e, run=run_of(p), kind=kind_of(p), sha256=meta[p]['sha256'] or meta[p]['blob'],
                         size=meta[p]['size'], **{f'has_{k}': v for k, v in sib.items()}))
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r['sha256']].append(r)
    distinct = []
    for h, g in groups.items():
        g = sorted(g, key=lambda r: (r['run'][:8], r['run'], r['path']))     # earliest run first = likely producer
        c = dict(g[0]); c['copies'] = [r['path'] for r in g[1:]]
        for r in g:                                                        # any copy's siblings will do
            for k in ('has_json', 'has_qa', 'has_sr'):
                c.setdefault(k, r.get(k))
        distinct.append(c)
    distinct.sort(key=lambda r: (r['run'][:8], r['run'], r['path']))
    inv = dict(n_files=len(pq), n_distinct=len(distinct), distinct=distinct)
    jdump(inv, os.path.join(a.work, 'inventory.json'))
    by_ep = collections.Counter(r['ep'] for r in distinct)
    print('distinct', len(distinct), dict(sorted(by_ep.items())))
    print('kinds', collections.Counter(r['kind'] for r in distinct))


# ---------------------------------------------------------------- fetch
def step_fetch(a):
    from huggingface_hub import snapshot_download
    inv = jload(os.path.join(a.work, 'inventory.json'))
    pats = set()
    for r in inv['distinct']:
        pats.add(r['path'])
        for k in ('has_json', 'has_qa', 'has_sr'):
            if r.get(k):
                pats.add(r[k])
        run = r['run']; pats.add(f'runs/{run}/job.log'); pats.add(f'runs/{run}/COMMIT')
    need = sorted(p for p in pats if not os.path.exists(os.path.join(a.store, p)))
    print(f'{len(pats)} files wanted, {len(need)} to download', flush=True)
    for i in range(0, len(need), 300):
        snapshot_download(repo_id=REPO_ID, repo_type='dataset', allow_patterns=need[i:i + 300], local_dir=a.store)
        print(f'  {min(i + 300, len(need))}/{len(need)}', flush=True)
    miss = [p for p in pats if not os.path.exists(os.path.join(a.store, p)) and not p.endswith(('job.log', 'COMMIT'))]
    print('missing after download:', len(miss), miss[:5])


# ---------------------------------------------------------------- mesh library per run
def lib_fingerprints(a):
    import trimesh
    fp = {}
    for lib in LIBS:
        for g in glob.glob(f'{a.repo}/meshes/{lib}/*.glb'):
            n = os.path.basename(g)[:-4]
            m = trimesh.load(g, force='mesh')
            fp.setdefault(n, {})[lib] = dict(verts=len(m.vertices), ext=np.round(m.extents * 100, 1).tolist(),
                                           md5=hashlib.md5(open(g, 'rb').read()).hexdigest())
    return fp


def step_libs(a):
    """make_assets prints 'NAME: N verts, watertight B, extents cm [x y z], ...' for each simulated object. Match the
    extents (0.1 cm) to the library meshes; objects identical across libraries are 'any'."""
    fp = lib_fingerprints(a)
    inv = jload(os.path.join(a.work, 'inventory.json'))
    runs = sorted({r['run'] for r in inv['distinct']})
    pat = re.compile(r'(\w+): (\d+) verts, watertight \w+, extents cm \[\s*([-\d. ]+)\]')
    out = {}
    for run in runs:
        log = os.path.join(a.store, 'runs', run, 'job.log'); seen = collections.defaultdict(set)
        if os.path.exists(log):
            for line in open(log, errors='replace'):
                for m in pat.finditer(line):
                    seen[m.group(1)].add((int(m.group(2)), tuple(float(x) for x in m.group(3).split())))
        per = {}
        for n, s in seen.items():
            if n not in fp:
                continue
            hits = set()
            for verts, ext in s:
                for lib, f in fp[n].items():
                    if np.allclose(sorted(f['ext']), sorted(ext), atol=0.11):
                        hits.add(lib)
            per[n] = sorted(hits) if hits else ['UNMATCHED ' + str(sorted(s))]
        out[run] = per
    jdump(dict(fingerprints=fp, runs=out), os.path.join(a.work, 'run_libs.json'))
    for run, per in out.items():
        print(run, {n: v for n, v in per.items()})


ROUTE_A_FIRST_RUN = '20261021-auto'      # route A (our meshes in the simulator) from 21 Oct ~10:20 UTC (work log)


def choose_lib(a, run, names, run_libs, box_meshes):
    """Mesh library this run simulated for these objects (None = the public scans). Order of evidence:
    'assets: PUBLIC scans' in job.log (hard_ab ASSET_SRC=public); the make_assets fingerprint in job.log (agrees with
    the box's own score_registered 'meshes' field wherever both exist); no fingerprint and a run before route A
    (simulator on the public scans); else default library_v3 (the submitted library)."""
    per = run_libs['runs'].get(run, {})
    log = os.path.join(a.store, 'runs', run, 'job.log')
    if os.path.exists(log) and 'assets: PUBLIC scans' in open(log, errors='replace').read():
        return 'scan', 'job.log: assets PUBLIC scans'
    if not per and run < ROUTE_A_FIRST_RUN:
        return 'scan', 'before route A, no make_assets fingerprint: simulator on the public scans'
    cands = None
    for n in names:
        if n in per and not per[n][0].startswith('UNMATCHED'):
            s = set(per[n])
            cands = s if cands is None else cands & s
    if cands:
        for lib in ('library_v3', 'library_v3x', 'library_v2', 'library_v4', 'library_v3p'):
            if lib in cands:
                bm = os.path.basename((box_meshes or '').rstrip('/'))
                agree = '' if not box_meshes else (', box meshes ' + (bm or box_meshes) +
                                                   (' agrees' if mesh_key(a, bm, names) == mesh_key(a, lib, names) else ' DISAGREES')
                                                   if bm in LIBS else ', box scored with ' + box_meshes)
                return lib, 'make_assets fingerprint (' + '/'.join(sorted(cands)) + ')' + agree
    return 'library_v3', 'default (no fingerprint)'


def mesh_key(a, lib, names):
    """Libraries are identical for most objects: key the cache by the md5s of the meshes actually used."""
    if lib == 'scan':
        return 'scan'
    return '|'.join(hashlib.md5(open(f'{a.repo}/meshes/{lib}/{n}.glb', 'rb').read()).hexdigest()[:10] for n in names)


# ---------------------------------------------------------------- scorer (same computation as score_registered.py)
class Scorer:
    SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}

    def __init__(self, a):
        self.a = a
        sys.path.insert(0, a.kit); sys.path.insert(0, f'{a.kit}/metric_code/track_3')
        import importlib
        import pyarrow.parquet as pq
        from v2dlb import track3_pose as T3
        from v2dlb.mesh_budget import budget_mesh
        from v2dlb.object_mesh import _surface_moments
        from v2dlb.mesh_common import _sample_mesh_surface
        from v2dlb.submission_parquet import read_trajectory
        self.T3, self.budget_mesh, self.sm, self.sample = T3, budget_mesh, _surface_moments, _sample_mesh_surface
        self.read_trajectory, self.pq = read_trajectory, pq
        self.A = importlib.import_module('AUC')
        self.gt_cache, self.reg_cache, self.ref_cache = {}, {}, {}

    def scan_path(self, n):
        q = f'{self.a.t3}/mesh/{n}/{n}.glb'
        return q if os.path.exists(q) else f'{self.a.t3}/mesh/{n}/{n}_visual.glb'

    def episode(self, ep):
        if ep not in self.gt_cache:
            import trimesh
            tab = self.pq.read_table(f'{self.a.t3}/ep{ep}.parquet').to_pandas()
            names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
            objs = tab['observation.objects']

            def gt_xyzw(o):
                q = np.array(o['pose'], float)
                return np.r_[q[:3], q[4:7], q[3]]
            gt = np.stack([[gt_xyzw([o for o in objs.iloc[fr] if o['name'] == n][0]) for n in names]
                           for fr in range(len(tab))])
            H = []
            for s, n in enumerate(names):
                m = trimesh.load(self.scan_path(n), force='mesh')
                v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
                c, _ = self.sm(v, f)
                pts = self.sample(v, f, 1000, 7 + s) - c
                axis, order = np.zeros(3), 0
                if n in self.SYM:
                    w, U = np.linalg.eigh(np.cov(pts.T))
                    if self.SYM[n] == 'half':
                        axis, order = U[:, 0], 2
                    else:
                        k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
                        axis, order = U[:, k], 360
                H.append(dict(mesh=(v, f), anchor=c, points=pts, axis=axis, order=order))
            self.gt_cache[ep] = (names, gt, H)
        return self.gt_cache[ep]

    def registration(self, ep, lib):
        names, gt, H = self.episode(ep)
        key = (ep, mesh_key(self.a, lib, names))
        if key not in self.reg_cache:
            REG = []
            for s, n in enumerate(names):
                cand = self.budget_mesh(self.scan_path(n) if lib == 'scan' else f'{self.a.repo}/meshes/{lib}/{n}.glb', 4096, 4096)
                REG.append(self.T3._register_object_body(cand, H[s]['mesh'], H[s]['anchor'], 1_000_003 * ep + 101 * s))
            self.reg_cache[key] = REG
        return self.reg_cache[key]

    def grids(self, path, B):
        tr = self.read_trajectory(path)
        w0 = tr.world_index == tr.world_index.min()
        frames = np.unique(tr.frame_index[w0])

        def grid(Q):
            G = np.full((len(frames), B, 7), np.nan)
            for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], Q[w0]):
                G[np.searchsorted(frames, fr), s] = q
            return G
        return frames, grid(tr.pose_xyzw), (grid(tr.reference_xyzw) if tr.reference_xyzw is not None else None)

    def registered(self, ep, lib, traj, frames, return_err=False):
        """AUC and per-object AUC exactly as score_registered.py (per-object point errors computed once)."""
        T3 = self.T3
        names, gt_all, H = self.episode(ep)
        REG = self.registration(ep, lib); B = len(names)
        ach = traj[:, None].copy(); ref = gt_all[frames][:, None].copy()
        for s in range(B):
            ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
            ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
        axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
        ach = T3._align_registered_scene(ach, ref, axes)
        err = [T3._symmetry_point_errors(ach[:, :, i], ref[:, :, i], pts[i], axes[i], orders[i]) for i in range(B)]
        auc = round(float(T3._add_auc(np.stack(err, axis=-1))), 4)
        per = {n: round(float(T3._add_auc(np.stack([err[s]], axis=-1))), 4) for s, n in enumerate(names)}
        sp = round(float(T3._registered_pose_metric('spider_sr', ach, ref, pts, axes, orders)), 4)
        mp = round(float(T3._registered_pose_metric('maniptrans_sr', ach, ref, pts, axes, orders)), 4)
        if return_err:
            return np.stack(err, axis=-1)[:, 0]                            # [T, B] mean point error (m)
        return dict(AUC=auc, per_obj_AUC=per, SP_SR=sp, MP_SR=mp)

    def sphere_add(self, sim, ref):
        """Per-frame, per-object ADD (m) of the qa.py yardstick (sim warped to the reference at frame 0)."""
        A = self.A; B = sim.shape[1]
        rng = np.random.default_rng(0); p = rng.normal(size=(500, 3)); p = 0.05 * p / np.linalg.norm(p, axis=1, keepdims=True)
        V = np.repeat(p[None], B, 0)
        return A._object_add(A._warp_to_reference_start(sim[:, None], ref[:, None]), ref[:, None], V)[:, 0]

    def qa_sim_vs_ref(self, sim, ref):
        """pipeline/qa.py policy: kit AUC, frame-0 warp, 500 points on a 5 cm sphere per object."""
        A = self.A; B = sim.shape[1]
        rng = np.random.default_rng(0); p = rng.normal(size=(500, 3)); p = 0.05 * p / np.linalg.norm(p, axis=1, keepdims=True)
        V = np.repeat(p[None], B, 0)

        def auc(x, r):
            x, r = x[:, None], r[:, None]
            return float(A._add_auc(A._object_add(A._warp_to_reference_start(x, r), r, V)))
        return round(auc(sim, ref), 4), round(auc(np.repeat(ref[:1], len(ref), 0), ref), 4)


def ref_digest(ref):
    return hashlib.sha256(np.round(np.nan_to_num(ref), 6).tobytes()).hexdigest()[:16]


# ---------------------------------------------------------------- verify against score_registered.py
def step_verify(a):
    import subprocess
    rows = [json.loads(l) for l in open(os.path.join(a.work, 'rows.jsonl'))] if os.path.exists(os.path.join(a.work, 'rows.jsonl')) else []
    if not rows:
        raise SystemExit('score first (verify picks scored rollouts)')
    rng = np.random.default_rng(1)
    eps = sorted({r['ep'] for r in rows})
    pick = [next(r for r in rows if r['ep'] == e) for e in eps]
    res = []
    for r in pick:
        d = os.path.dirname(os.path.join(a.store, r['path'])); o = os.path.join(a.work, 'verify', f"ep{r['ep']}.json")
        os.makedirs(os.path.dirname(o), exist_ok=True)
        if not os.path.exists(o):
            mesh = [] if r['lib'] == 'scan' else ['--meshes', f"{a.repo}/meshes/{r['lib']}"]
            subprocess.run([sys.executable, '-I', f'{a.repo}/pipeline/score_registered.py', str(r['ep']), d, *mesh,
                            '--t3', a.t3, '--kit', a.kit, '--out', o],
                           check=True, stdout=subprocess.DEVNULL)
        s = json.load(open(o))
        res.append(dict(ep=r['ep'], path=r['path'], lib=r['lib'], T_ours=r['T'], T_script=s['sim']['AUC'],
                        R_ours=r['R'], R_script=s['reference']['AUC'],
                        per_obj_match=s['sim']['per_obj_AUC'] == r['T_obj'],
                        match=(s['sim']['AUC'] == r['T'] and s['reference']['AUC'] == r['R'])))
        print(res[-1], flush=True)
    jdump(res, os.path.join(a.out, 'verify.json'))


# ---------------------------------------------------------------- score
def step_score(a):
    inv = jload(os.path.join(a.work, 'inventory.json'))
    run_libs = jload(os.path.join(a.work, 'run_libs.json'))
    if run_libs is None:
        raise SystemExit('run `libs` first')
    D = [r for r in inv['distinct'] if a.include_curves or r['kind'] in ('repeat', 'single')]
    D = [r for r in D if os.path.exists(os.path.join(a.store, r['path']))]
    D = D[::-1]                                                            # most recent run first
    if a.recent:
        D = D[:a.recent]
    if a.max:
        D = D[:a.max]
    out = os.path.join(a.work, 'rows.jsonl')
    done = {json.loads(l)['sha256'] for l in open(out)} if os.path.exists(out) else set()
    sc = Scorer(a); t0 = time.time(); n = 0
    with open(out, 'a') as fo:
        for r in D:
            if r['sha256'] in done:
                continue
            ep = r['ep']; names, _, _ = sc.episode(ep)
            ej = jload(os.path.join(a.store, r['has_json'])) if r.get('has_json') else None
            qa = jload(os.path.join(a.store, r['has_qa'])) if r.get('has_qa') else None
            sr = jload(os.path.join(a.store, r['has_sr'])) if r.get('has_sr') else None
            lib, why = choose_lib(a, r['run'], names, run_libs, (sr or {}).get('meshes'))
            try:
                frames, sim, ref = sc.grids(os.path.join(a.store, r['path']), len(names))
            except Exception as e:
                fo.write(json.dumps(dict(sha256=r['sha256'], path=r['path'], ep=ep, error=f'read: {e}'[:200])) + '\n'); continue
            if ref is None or np.isnan(sim).any() or np.isnan(ref).any():
                fo.write(json.dumps(dict(sha256=r['sha256'], path=r['path'], ep=ep, error='no reference or NaN')) + '\n'); continue
            S, S_floor = sc.qa_sim_vs_ref(sim, ref)
            rd = ref_digest(ref)
            tk = sc.registered(ep, lib, sim, frames)
            rkey = (ep, mesh_key(a, lib, names), rd)
            if rkey not in sc.ref_cache:
                sc.ref_cache[rkey] = sc.registered(ep, lib, ref, frames)
            rk = sc.ref_cache[rkey]
            m = (ej or {}).get('metrics', {})
            row = dict(sha256=r['sha256'], path=r['path'], copies=len(r.get('copies', [])), ep=ep, run=r['run'],
                       kind=r['kind'], objects=names, frames=int(len(frames)), lib=lib, lib_evidence=why,
                       checkpoint=(ej or {}).get('checkpoint'), checkpoint_sha256=(ej or {}).get('checkpoint_sha256'),
                       steps=(ej or {}).get('environment_steps'), ref_parquet=(ej or {}).get('parquet'), ref_digest=rd,
                       T=tk['AUC'], T_obj=tk['per_obj_AUC'], T_SP=tk['SP_SR'], T_MP=tk['MP_SR'],
                       R=rk['AUC'], R_obj=rk['per_obj_AUC'], S=S, S_floor=S_floor,
                       S_box=(qa or {}).get('sim_vs_ref'), T_box=((sr or {}).get('sim') or {}).get('AUC'),
                       R_box=((sr or {}).get('reference') or {}).get('AUC'), box_meshes=(sr or {}).get('meshes'),
                       eval_add_auc=m.get('add_auc'))
            fo.write(json.dumps(row) + '\n'); fo.flush(); n += 1
            print(f"[{time.time() - t0:5.0f}s] {n} ep{ep} {r['run']} {r['path'].split('/results/')[-1][:60]} "
                  f"lib {lib} T {row['T']} R {row['R']} S {S} (box S {row['S_box']} T {row['T_box']})", flush=True)


# ---------------------------------------------------------------- fit
def fit_models(T, S, R, Rbar=None):
    """Loss-budget models of the truth score T from sim_vs_ref S and the reference score R (all in [0, 1])."""
    T, S, R = (np.asarray(x, float) for x in (T, S, R))
    out = dict(n=int(len(T)))

    def stats(pred, name, params):
        res = T - pred
        out[name] = dict(params=params, rmse=round(float(np.sqrt(np.mean(res ** 2))), 4),
                         mae=round(float(np.mean(np.abs(res))), 4), max_abs=round(float(np.max(np.abs(res))), 4),
                         bias=round(float(np.mean(res)), 4),
                         r2=round(float(1 - np.sum(res ** 2) / np.sum((T - T.mean()) ** 2)), 4) if len(T) > 1 and T.std() > 0 else None)
    k = float(np.sum(T * S) / np.sum(S * S))
    stats(k * S, 'T=k*S', dict(k=round(k, 4)))
    stats(0.979 * S, 'T=0.979*S', {})
    stats(S * R, 'T=S*R', {})
    SR = S * R; aa = float(np.sum(T * SR) / np.sum(SR * SR))
    stats(aa * SR, 'T=a*S*R', dict(a=round(aa, 4)))
    if Rbar is not None:
        stats(S * np.asarray(Rbar, float), 'T=S*Rbar', {})
    if len(T) > 2 and S.std() > 0:
        b, c = np.polyfit(S, T, 1)
        stats(b * S + c, 'T=b*S+c', dict(b=round(float(b), 4), c=round(float(c), 4)))
    stats(S, 'T=S', {})
    out['sum_T_over_sum_S'] = round(float(np.sum(T) / np.sum(S)), 4)
    out['median_T_over_S'] = round(float(np.median(T / np.maximum(S, 1e-6))), 4)
    out['corr_T_S'] = round(float(np.corrcoef(T, S)[0, 1]), 4) if len(T) > 2 and T.std() > 0 and S.std() > 0 else None
    return out


MODELS = ('T=k*S', 'T=0.979*S', 'T=S*R', 'T=a*S*R', 'T=S*Rbar', 'T=b*S+c', 'T=S')


def s_per_object(a, rows):
    """Per-object sim_vs_ref (qa.py yardstick, one object at a time; cached)."""
    cp = os.path.join(a.work, 's_obj.json'); cache = jload(cp, {})
    todo = [r for r in rows if r['sha256'] not in cache]
    if todo:
        sc = Scorer(a); A = sc.A
        rng = np.random.default_rng(0); p = rng.normal(size=(500, 3)); p = 0.05 * p / np.linalg.norm(p, axis=1, keepdims=True)
        for r in todo:
            B = len(r['objects']); _, sim, ref = sc.grids(os.path.join(a.store, r['path']), B)
            V = np.repeat(p[None], B, 0)
            add = A._object_add(A._warp_to_reference_start(sim[:, None], ref[:, None]), ref[:, None], V)
            cache[r['sha256']] = {n: round(float(A._add_auc(add[:, :, b:b + 1])), 4) for b, n in enumerate(r['objects'])}
        jdump(cache, cp)
    for r in rows:
        r['S_obj'] = cache[r['sha256']]


def policies(rows):
    """Policy = one checkpoint (sha256; the rollout dir when the json is missing) against one reference and mesh set."""
    pol = collections.defaultdict(list)
    for r in rows:
        ck = r.get('checkpoint_sha256') or (r['run'] + ':' + re.sub(r'/r\d+$', '', os.path.dirname(r['path'])))
        pol[(r['ep'], ck, r['ref_digest'], r['lib'])].append(r)
    P = []
    for (ep, ck, rd, lib), g in pol.items():
        g = sorted(g, key=lambda x: x['path'])
        P.append(dict(ep=ep, checkpoint_sha256=ck, ref_digest=rd, lib=lib, n=len(g), run=g[0]['run'], path=g[0]['path'],
                      runs=sorted({x['run'] for x in g}), kinds=sorted({x['kind'] for x in g}), steps=g[0].get('steps'),
                      T=float(np.mean([x['T'] for x in g])), S=float(np.mean([x['S'] for x in g])), R=g[0]['R'],
                      Rbar=float(np.mean(list(g[0]['R_obj'].values()))),
                      T_sd=float(np.std([x['T'] for x in g])), S_sd=float(np.std([x['S'] for x in g])),
                      objects=g[0]['objects'],
                      T_obj={n: float(np.mean([x['T_obj'][n] for x in g])) for n in g[0]['objects']},
                      S_obj={n: float(np.mean([x['S_obj'][n] for x in g])) for n in g[0]['objects']},
                      R_obj=g[0]['R_obj']))
    return P


def within_slope(items, key=lambda x: (x['ep'], x['ref_digest'], x['lib'])):
    """Fixed-effects slope of T on S inside groups (same episode, reference, meshes): how much of a sim_vs_ref
    difference shows up in T. Returns pooled slope, n groups used, and per-group slopes."""
    G = collections.defaultdict(list)
    for x in items:
        G[key(x)].append(x)
    num = den = 0.0; per = {}
    for k, g in G.items():
        if len(g) < 2:
            continue
        S = np.array([x['S'] for x in g]); T = np.array([x['T'] for x in g])
        dS, dT = S - S.mean(), T - T.mean()
        if np.sum(dS ** 2) < 1e-6:
            continue
        num += float(np.sum(dS * dT)); den += float(np.sum(dS ** 2))
        per[k] = dict(n=len(g), slope=round(float(np.sum(dS * dT) / np.sum(dS ** 2)), 3), R=g[0]['R'],
                      S_range=[round(float(S.min()), 3), round(float(S.max()), 3)],
                      resid_sd=round(float(np.std(dT - dS * np.sum(dS * dT) / np.sum(dS ** 2))), 4))
    return dict(slope=round(num / den, 4) if den else None, n_groups=len(per), n_items=int(sum(v['n'] for v in per.values()))), per


def pair_transfer(items, min_dS=0.02):
    """All pairs inside a group (same ep, reference, meshes) with dS >= min_dS: sum dT / sum dS."""
    G = collections.defaultdict(list)
    for x in items:
        G[(x['ep'], x['ref_digest'], x['lib'])].append(x)
    pr = []
    for k, g in G.items():
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                lo, hi = sorted((g[i], g[j]), key=lambda x: x['S'])
                if hi['S'] - lo['S'] >= min_dS:
                    pr.append(dict(ep=k[0], R=lo['R'], dS=hi['S'] - lo['S'], dT=hi['T'] - lo['T']))
    if not pr:
        return dict(n=0), pr
    dS = np.array([x['dS'] for x in pr]); dT = np.array([x['dT'] for x in pr])
    return dict(n=len(pr), n_eps=len({x['ep'] for x in pr}), sum_ratio=round(float(dT.sum() / dS.sum()), 4),
                median_ratio=round(float(np.median(dT / dS)), 4), share_dT_pos=round(float(np.mean(dT > 0)), 3)), pr


def step_fit(a):
    rows = [json.loads(l) for l in open(os.path.join(a.work, 'rows.jsonl'))]
    bad = [r for r in rows if 'error' in r]; rows = [r for r in rows if 'error' not in r]
    seen = set(); rows = [r for r in rows if not (r['sha256'] in seen or seen.add(r['sha256']))]
    s_per_object(a, rows)
    for r in rows:
        r['Rbar'] = float(np.mean(list(r['R_obj'].values())))
    P = policies(rows)
    own = lambda x: x['lib'] != 'scan'
    res = dict(n_rollouts=len(rows), n_errors=len(bad), errors=[(r['path'], r['error']) for r in bad], n_policies=len(P),
               n_policies_own_mesh=sum(own(p) for p in P), episodes=sorted({r['ep'] for r in rows}),
               libs=dict(collections.Counter(r['lib'] for r in rows)),
               lib_evidence=dict(collections.Counter(r['lib_evidence'].split(' (')[0].split(',')[0] for r in rows)))
    # consistency with the box records
    sb = []                                                                # qa_policy.json of a curve dir holds
    for r in rows:                                                         # the mean of its repeats; 'rep'[0] is its own
        q = jload(os.path.join(a.store, os.path.dirname(r['path']), 'qa_policy.json'))
        if q and 'sim_vs_ref' in q:
            sb.append((r['S'], q['rep'][0] if q.get('rep') else q['sim_vs_ref']))
    tb = [(r['T'], r['T_box']) for r in rows if r.get('T_box') is not None and r.get('box_meshes', '').endswith(r['lib'])]
    res['box_check'] = dict(S_n=len(sb), S_exact=sum(abs(x - y) < 1e-4 for x, y in sb),
                            S_maxdiff=round(max((abs(x - y) for x, y in sb), default=0), 4),
                            T_n=len(tb), T_exact=sum(abs(x - y) < 1e-4 for x, y in tb),
                            T_maxdiff=round(max((abs(x - y) for x, y in tb), default=0), 4))
    sets = {
        'rollouts_all': rows, 'rollouts_own_mesh': [r for r in rows if own(r)],
        'rollouts_own_R>=0.95': [r for r in rows if own(r) and r['R'] >= 0.95],
        'rollouts_own_R<0.95': [r for r in rows if own(r) and r['R'] < 0.95],
        'policies_all': P, 'policies_own_mesh': [p for p in P if own(p)],
        'policies_own_R>=0.95': [p for p in P if own(p) and p['R'] >= 0.95],
        'policies_own_R>=0.95_n>=3': [p for p in P if own(p) and p['R'] >= 0.95 and p['n'] >= 3],
        'policies_own_R<0.95': [p for p in P if own(p) and p['R'] < 0.95],
        'policies_own_S>=0.8': [p for p in P if own(p) and p['S'] >= 0.8],
        'policies_own_S>=0.8_R>=0.95': [p for p in P if own(p) and p['S'] >= 0.8 and p['R'] >= 0.95],
        'policies_scan': [p for p in P if not own(p)],
        f'recent{a.recent or 60}_rollouts': sorted(rows, key=lambda r: (r['run'][:8], r['run'], r['path']))[-(a.recent or 60):],
    }
    res['fits'] = {k: (fit_models([x['T'] for x in v], [x['S'] for x in v], [x['R'] for x in v], [x['Rbar'] for x in v])
                       if len(v) >= 2 else None) for k, v in sets.items()}
    res['set_episodes'] = {k: dict(sorted(collections.Counter(x['ep'] for x in v).items())) for k, v in sets.items()}
    # the GT-free symmetric yardstick S_mesh (step symS), where computed: same models with S -> S_mesh
    sm = jload(os.path.join(a.work, 's_mesh.json'), {})
    if sm:
        for r in rows:
            if r['sha256'] in sm:
                r['S_mesh'] = sm[r['sha256']]['S_mesh']
        Pm = collections.defaultdict(list)
        for r in rows:
            if 'S_mesh' in r:
                ck = r.get('checkpoint_sha256') or (r['run'] + ':' + re.sub(r'/r\d+$', '', os.path.dirname(r['path'])))
                Pm[(r['ep'], ck, r['ref_digest'], r['lib'])].append(r)
        PM = [dict(ep=k[0], T=np.mean([x['T'] for x in g]), S=np.mean([x['S_mesh'] for x in g]), S_qa=np.mean([x['S'] for x in g]),
                   R=g[0]['R'], Rbar=np.mean(list(g[0]['R_obj'].values())), n=len(g)) for k, g in Pm.items()]
        rm = [r for r in rows if 'S_mesh' in r]
        msets = {'rollouts_own': [dict(T=r['T'], S=r['S_mesh'], R=r['R'], Rbar=r['Rbar'], ep=r['ep']) for r in rm],
                 'policies_own': PM, 'policies_own_R>=0.95': [p for p in PM if p['R'] >= 0.95],
                 'policies_own_S>=0.8': [p for p in PM if p['S'] >= 0.8]}
        res['fits_S_mesh'] = {k: fit_models([x['T'] for x in v], [x['S'] for x in v], [x['R'] for x in v], [x['Rbar'] for x in v])
                              if len(v) >= 2 else None for k, v in msets.items()}
        res['per_episode_S_mesh'] = {ep: dict(n_pol=len(g), S_qa=round(float(np.mean([p['S_qa'] for p in g])), 4),
                                              S_mesh=round(float(np.mean([p['S'] for p in g])), 4),
                                              T=round(float(np.mean([p['T'] for p in g])), 4),
                                              sumT_sumSqa=round(float(sum(p['T'] for p in g) / sum(p['S_qa'] for p in g)), 4),
                                              sumT_sumSmesh=round(float(sum(p['T'] for p in g) / sum(p['S'] for p in g)), 4),
                                              res_SR_qa=round(float(np.mean([p['T'] - p['S_qa'] * p['R'] for p in g])), 4),
                                              res_SR_mesh=round(float(np.mean([p['T'] - p['S'] * p['R'] for p in g])), 4))
                                     for ep in sorted({p['ep'] for p in PM}) for g in [[p for p in PM if p['ep'] == ep]]}
        ws, _ = within_slope([dict(x, ref_digest=k[2], lib=k[3]) for k, g in Pm.items()
                              for x in [dict(ep=k[0], T=np.mean([y['T'] for y in g]), S=np.mean([y['S_mesh'] for y in g]), R=g[0]['R'])]])
        res['transfer_S_mesh_policies_own'] = ws
    k95 = res['fits']['policies_own_R>=0.95']['T=k*S']['params']['k'] if res['fits']['policies_own_R>=0.95'] else 0.979
    res['k_policies_own_R>=0.95'] = k95
    # per episode (own-mesh policies): residuals of each model
    per_ep = {}
    for ep in res['episodes']:
        g = [p for p in P if p['ep'] == ep and own(p)]
        if not g:
            continue
        T = np.array([p['T'] for p in g]); S = np.array([p['S'] for p in g]); R = np.array([p['R'] for p in g])
        w = np.array([p['n'] for p in g], float)
        e = dict(n_pol=len(g), n_roll=int(w.sum()), objects=g[0]['objects'], libs=sorted({p['lib'] for p in g}),
                 n_refs=len({p['ref_digest'] for p in g}), R_min=round(float(R.min()), 4), R_max=round(float(R.max()), 4),
                 S_mean=round(float(S.mean()), 4), T_mean=round(float(T.mean()), 4),
                 sumT_sumS=round(float(T.sum() / S.sum()), 4))
        for m, pred in (('kS', k95 * S), ('0.979S', 0.979 * S), ('SR', S * R)):
            e[f'res_{m}_mean'] = round(float(np.mean(T - pred)), 4)
            e[f'res_{m}_rmse'] = round(float(np.sqrt(np.mean((T - pred) ** 2))), 4)
        hi = S >= 0.8
        e['n_pol_S>=0.8'] = int(hi.sum())
        e['res_SR_mean_S>=0.8'] = round(float(np.mean(T[hi] - S[hi] * R[hi])), 4) if hi.any() else None
        e['res_kS_mean_S>=0.8'] = round(float(np.mean(T[hi] - k95 * S[hi])), 4) if hi.any() else None
        e['T_over_S_S>=0.8'] = round(float(T[hi].sum() / S[hi].sum()), 4) if hi.any() else None
        e['R_of_S>=0.8'] = round(float(np.mean(R[hi])), 4) if hi.any() else None
        per_ep[ep] = e
    res['per_episode'] = per_ep
    # per object: T_obj vs S_obj * R_obj on own-mesh policies with S >= 0.8
    po = collections.defaultdict(list)
    for p in P:
        if own(p) and p['S'] >= 0.8:
            for n in p['objects']:
                po[(p['ep'], n)].append((p['T_obj'][n], p['S_obj'][n], p['R_obj'][n]))
    res['per_object_S>=0.8'] = {f'ep{ep} {n}': dict(n=len(v), T=round(float(np.mean([x[0] for x in v])), 4),
                                                    S=round(float(np.mean([x[1] for x in v])), 4),
                                                    R=round(float(np.mean([x[2] for x in v])), 4),
                                                    res_SR=round(float(np.mean([x[0] - x[1] * x[2] for x in v])), 4))
                                for (ep, n), v in sorted(po.items())}
    # transfer of sim_vs_ref differences into T (same episode, reference, meshes)
    tr = {}
    for name, items in (('rollouts_own', [r for r in rows if own(r)]), ('policies_own', [p for p in P if own(p)]),
                        ('policies_own_R>=0.95', [p for p in P if own(p) and p['R'] >= 0.95]),
                        ('policies_own_R<0.95', [p for p in P if own(p) and p['R'] < 0.95]),
                        ('policies_own_S>=0.6', [p for p in P if own(p) and p['S'] >= 0.6]),
                        ('rollouts_scan', [r for r in rows if not own(r)])):
        ws, per = within_slope(items)
        pt, _ = pair_transfer(items, 0.02)
        Rw = [v['R'] for v in per.values()]
        tr[name] = dict(
            within_slope=ws['slope'], n_groups=ws['n_groups'], n_items=ws['n_items'],
            mean_R_of_groups=round(float(np.mean(Rw)), 4) if Rw else None, pairs=pt,
            groups={f'ep{k[0]} {k[1][:6]} {k[2].replace("library_", "")}': v for k, v in per.items()})
    res['transfer'] = tr
    jdump(res, os.path.join(a.out, 'calibration.json'))
    jdump(sorted([{k: v for k, v in p.items()} for p in P], key=lambda p: (p['ep'], p['run'], p['path'])),
          os.path.join(a.out, 'policies.json'))
    jdump([{k: r[k] for k in ('ep', 'run', 'path', 'kind', 'lib', 'lib_evidence', 'checkpoint_sha256', 'steps', 'ref_digest',
                              'T', 'R', 'S', 'S_floor', 'T_obj', 'R_obj', 'S_obj', 'S_box', 'T_box', 'R_box', 'eval_add_auc', 'copies')}
           for r in rows], os.path.join(a.out, 'rollouts.json'))
    box_claim(a, res)
    lb_transfer(a, res)
    write_tables(a, res, P, rows)
    plot(a, rows, P, k95)
    print(json.dumps({k: res[k] for k in ('n_rollouts', 'n_policies', 'n_policies_own_mesh', 'box_check', 'k_policies_own_R>=0.95')}, indent=1))


def box_claim(a, res):
    """The forensics' 0.979 claim used box-recorded policy means; recompute it from the box summary.json files
    (sim_vs_ref mean and registered AUC mean per evaluated checkpoint), deduplicated by content."""
    from huggingface_hub import snapshot_download
    files = jload(os.path.join(a.work, 'store_files.json'), [])
    L = [p for p in files if p.endswith('/summary.json') and '/results/' in p
         and re.search(r'/ep(\d+)[/-]', p) and int(re.search(r'/ep(\d+)[/-]', p).group(1)) in PUBLIC]
    need = [p for p in L if not os.path.exists(os.path.join(a.store, p))]
    if need:
        snapshot_download(repo_id=REPO_ID, repo_type='dataset', allow_patterns=need, local_dir=a.store)
    seen = {}
    for p in sorted(L, key=lambda p: (run_of(p)[:8], run_of(p), p)):
        b = open(os.path.join(a.store, p), 'rb').read(); d = json.loads(b)
        s, t = d.get('sim_vs_ref'), d.get('auc')
        if isinstance(s, dict) and isinstance(t, dict):
            seen.setdefault((round(s['mean'], 4), round(t['mean'], 4), d.get('n')), dict(
                ep=int(re.search(r'/ep(\d+)[/-]', p).group(1)), path=p, S=s['mean'], T=t['mean'], n=d.get('n'),
                checkpoint=d.get('checkpoint')))
    B = list(seen.values())
    out = dict(n_summary_files=len(L), n_distinct_policy_means=len(B), episodes=dict(sorted(collections.Counter(x['ep'] for x in B).items())))
    if len(B) >= 2:
        T = np.array([x['T'] for x in B]); S = np.array([x['S'] for x in B])
        out.update(sum_T_over_sum_S=round(float(T.sum() / S.sum()), 4), mean_T_over_S=round(float(np.mean(T / S)), 4),
                   k_ls=round(float(np.sum(T * S) / np.sum(S * S)), 4))
        # join with our own R (per episode + reference) through the rollouts' policy means where the dir matches
        out['policies'] = B
    res['box_summaries'] = {k: v for k, v in out.items() if k != 'policies'}
    jdump(out, os.path.join(a.out, 'box_summaries.json'))


LEADERBOARD = {'20261025-track3c': 0.78893, '20261026-track3d': 0.81056}   # Kaggle Track 3 AUC (work log 26 Oct, [doc])


def lb_transfer(a, res):
    """The one leaderboard transfer measurement: pack 3 -> pack 4 changed 7 episodes' packed rollouts. Measured
    dLB / (sum dS / 20), and what T = k*S and T = S*acc (loss_budget.py per-object accuracies) predict."""
    import importlib.util
    sub = os.path.join(a.repo, 'results', 'submissions')
    S = {}
    for pk in LEADERBOARD:
        txt = open(os.path.join(sub, pk, 'summary.txt')).read()
        S[pk] = {int(k): v for k, v in json.loads(re.search(r'\{.*\}', txt).group(0)).items()}
    s3, s4 = S['20261025-track3c'], S['20261026-track3d']
    d = {e: round(s4[e] - s3[e], 4) for e in s3 if abs(s4[e] - s3[e]) > 1e-9}
    dlb = LEADERBOARD['20261026-track3d'] - LEADERBOARD['20261025-track3c']
    spec = importlib.util.spec_from_file_location('loss_budget', os.path.join(a.repo, 'docs/analysis/robustness-review-20261026/loss_budget.py'))
    lb = importlib.util.module_from_spec(spec); spec.loader.exec_module(lb)
    out = dict(changed_episodes=d, sum_dS_over_20=round(sum(d.values()) / 20, 4), dLB=round(dlb, 5),
               measured_transfer=round(dlb / (sum(d.values()) / 20), 3), predicted={})
    for spoon in (0.80, 0.813, 0.95):
        acc = dict(lb.ACC, spoon=spoon)
        pr = sum(v * np.mean([acc[o] for o in lb.OBJS[e]]) for e, v in d.items()) / 20
        out['predicted'][f'T=S*acc (spoon {spoon})'] = dict(dT=round(pr, 4), transfer=round(pr / (sum(d.values()) / 20), 3))
    k = res.get('k_policies_own_R>=0.95') or 0.979
    out['predicted'][f'T=k*S (k={k})'] = dict(dT=round(k * sum(d.values()) / 20, 4), transfer=k)
    res['leaderboard_transfer'] = out


def write_tables(a, res, P, rows):
    f4 = lambda x: '' if x is None else (f'{x:.4f}' if isinstance(x, float) else str(x))
    L = ['# mapping: tables (generated by `calibrate.py fit`; all numbers measured here unless marked)', '']
    L += ['## Fits of T (truth, registered vs mocap) from S (sim_vs_ref) and R (reference vs mocap)', '',
          'RMSE / bias = T - prediction. Rbar = mean of the per-object reference AUCs (loss_budget.py form).', '',
          '| set | n | model | params | RMSE | MAE | max abs | bias | R2 |', '|---|---|---|---|---|---|---|---|---|']
    for k, f in res['fits'].items():
        if not f:
            continue
        for m in MODELS:
            if m in f:
                x = f[m]
                L.append(f"| {k} | {f['n']} | {m} | {', '.join(f'{u}={v}' for u, v in x['params'].items())} | {x['rmse']} | "
                         f"{x['mae']} | {x['max_abs']} | {x['bias']:+.4f} | {x['r2']} |")
        L.append(f"| {k} | {f['n']} | sum T / sum S = {f['sum_T_over_sum_S']}, median T/S = {f['median_T_over_S']}, corr = {f['corr_T_S']} | | | | | | |")
    L += ['', '## Per episode (own-mesh policy means)', '',
          f"k = {res['k_policies_own_R>=0.95']} (fit on own-mesh policies with R >= 0.95).", '',
          '| ep | objects | libs | refs | policies | rollouts | R min-max | mean S | mean T | sumT/sumS | resid kS mean / rmse | resid 0.979S mean | resid SR mean / rmse | policies S>=0.8 | T/S (S>=0.8) | R (S>=0.8) | resid SR (S>=0.8) | resid kS (S>=0.8) |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for ep, e in res['per_episode'].items():
        L.append(f"| {ep} | {'+'.join(e['objects'])} | {','.join(x.replace('library_', '') for x in e['libs'])} | {e['n_refs']} | {e['n_pol']} | {e['n_roll']} | "
                 f"{e['R_min']}-{e['R_max']} | {e['S_mean']} | {e['T_mean']} | {e['sumT_sumS']} | {e['res_kS_mean']:+.4f} / {e['res_kS_rmse']} | "
                 f"{e['res_0.979S_mean']:+.4f} | {e['res_SR_mean']:+.4f} / {e['res_SR_rmse']} | {e['n_pol_S>=0.8']} | {f4(e['T_over_S_S>=0.8'])} | "
                 f"{f4(e['R_of_S>=0.8'])} | {f4(e['res_SR_mean_S>=0.8'])} | {f4(e['res_kS_mean_S>=0.8'])} |")
    L += ['', '## Per object (own-mesh policies with S >= 0.8): T_obj vs S_obj * R_obj', '',
          '| episode object | policies | T_obj | S_obj | R_obj | T_obj - S_obj*R_obj |', '|---|---|---|---|---|---|']
    for k, v in res['per_object_S>=0.8'].items():
        L.append(f"| {k} | {v['n']} | {v['T']} | {v['S']} | {v['R']} | {v['res_SR']:+.4f} |")
    L += ['', '## Transfer of sim_vs_ref differences into T (inside groups: same episode, reference and meshes)', '',
          '| items | within-group slope dT/dS | groups | items used | mean R of groups | pairs dS>=0.02 | sum dT / sum dS | median dT/dS | share dT>0 |',
          '|---|---|---|---|---|---|---|---|---|']
    for k, t in res['transfer'].items():
        p = t['pairs']
        L.append(f"| {k} | {t['within_slope']} | {t['n_groups']} | {t['n_items']} | {t['mean_R_of_groups']} | {p.get('n')} | "
                 f"{p.get('sum_ratio')} | {p.get('median_ratio')} | {p.get('share_dT_pos')} |")
    L += ['', '### Per group (own-mesh policies)', '', '| group (ep, ref digest, meshes) | policies | R | S range | slope dT/dS | resid sd |', '|---|---|---|---|---|---|']
    for k, v in res['transfer']['policies_own']['groups'].items():
        L.append(f"| {k} | {v['n']} | {v['R']} | {v['S_range'][0]}-{v['S_range'][1]} | {v['slope']} | {v['resid_sd']} |")
    if res.get('fits_S_mesh'):
        L += ['', '## Same models with the GT-free symmetric yardstick S_mesh in place of S (hypothesis H-yard; `symS` step)', '',
              '| set | n | model | params | RMSE | MAE | max abs | bias | R2 |', '|---|---|---|---|---|---|---|---|---|']
        for k, f in res['fits_S_mesh'].items():
            if not f:
                continue
            for m in ('T=k*S', 'T=S*R', 'T=b*S+c', 'T=S'):
                if m in f:
                    x = f[m]
                    L.append(f"| {k} | {f['n']} | {m.replace('S', 'Sm').replace('Sm*R', 'Sm*R')} | {', '.join(f'{u}={v}' for u, v in x['params'].items())} | "
                             f"{x['rmse']} | {x['mae']} | {x['max_abs']} | {x['bias']:+.4f} | {x['r2']} |")
            L.append(f"| {k} | {f['n']} | sum T / sum Sm = {f['sum_T_over_sum_S']}, corr = {f['corr_T_S']} | | | | | | |")
        L += ['', '| ep | policies | mean S (qa) | mean S_mesh | mean T | sumT/sumS | sumT/sumSm | resid T-S*R | resid T-Sm*R |', '|---|---|---|---|---|---|---|---|---|']
        for ep, e in res['per_episode_S_mesh'].items():
            L.append(f"| {ep} | {e['n_pol']} | {e['S_qa']} | {e['S_mesh']} | {e['T']} | {e['sumT_sumSqa']} | {e['sumT_sumSmesh']} | {e['res_SR_qa']:+.4f} | {e['res_SR_mesh']:+.4f} |")
        L.append(f"\nWithin-group transfer slope dT/dS_mesh (own-mesh policies): {res['transfer_S_mesh_policies_own']}")
    if 'leaderboard_transfer' in res:
        t = res['leaderboard_transfer']
        L += ['', '## Leaderboard transfer, pack 3 -> pack 4 (Kaggle AUCs [doc]; summaries from results/submissions)', '',
              f"changed episodes dS: {t['changed_episodes']}; sum dS / 20 = {t['sum_dS_over_20']}; dLB = {t['dLB']}; "
              f"measured transfer = {t['measured_transfer']}.", '', '| model | predicted dLB | predicted transfer |', '|---|---|---|']
        for k, v in t['predicted'].items():
            L.append(f"| {k} | {v['dT']} | {v['transfer']} |")
    if 'box_summaries' in res:
        b = res['box_summaries']
        L += ['', '## Box-recorded policy means (summary.json; [doc] values recomputed into a ratio here)', '',
              f"{b['n_distinct_policy_means']} distinct policy means from {b['n_summary_files']} files, episodes {b['episodes']}: "
              f"sum T / sum S = {b.get('sum_T_over_sum_S')}, mean T/S = {b.get('mean_T_over_S')}, least-squares k = {b.get('k_ls')}."]
    L += ['', '## Policies (mean over distinct rollouts)', '', '| ep | first run | first rollout dir | lib | n | R | Rbar | mean S | mean T | T/S | T - S*R |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for p in sorted(P, key=lambda p: (p['ep'], p['run'], p['path'])):
        L.append(f"| {p['ep']} | {p['run']} | {re.sub(r'/r[0-9]+$', '', os.path.dirname(p['path']).split('/results/')[-1])} | {p['lib'].replace('library_', '')} | {p['n']} | "
                 f"{p['R']} | {p['Rbar']:.4f} | {p['S']:.4f} | {p['T']:.4f} | {p['T'] / max(p['S'], 1e-6):.3f} | {p['T'] - p['S'] * p['R']:+.4f} |")
    open(os.path.join(a.out, 'tables.md'), 'w').write('\n'.join(L) + '\n')


def plot(a, rows, P, k):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        print('matplotlib not available: no plot'); return
    Q = [p for p in P if p['lib'] != 'scan']
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.5))
    eps = sorted({p['ep'] for p in Q}); cmap = plt.get_cmap('tab10')
    for i, ep in enumerate(eps):
        g = [p for p in Q if p['ep'] == ep]; c = cmap(i % 10)
        sz = [8 + 5 * p['n'] for p in g]
        ax[0].scatter([p['S'] for p in g], [p['T'] for p in g], s=sz, color=c, label=f'ep{ep}', edgecolor='k', linewidth=0.3, alpha=0.8)
        ax[1].scatter([p['S'] * p['R'] for p in g], [p['T'] for p in g], s=sz, color=c, edgecolor='k', linewidth=0.3, alpha=0.8)
        ax[2].scatter([p['R'] for p in g], [p['T'] - k * p['S'] for p in g], s=sz, color=c, edgecolor='k', linewidth=0.3, alpha=0.8)
    x = np.linspace(0, 1, 2)
    ax[0].plot(x, x, 'k:', lw=0.8, label='T = S')
    ax[0].plot(x, k * x, 'r-', lw=0.8, label=f'T = {k:.3f} S (fit, R>=0.95)')
    ax[0].plot(x, 0.979 * x, 'b--', lw=0.8, label='T = 0.979 S (forensics)')
    ax[1].plot(x, x, 'k:', lw=0.8, label='T = S*R')
    ax[2].axhline(0, color='k', lw=0.8); ax[2].axvline(0.95, color='grey', lw=0.6, ls='--')
    ax[0].set_xlabel('S = sim_vs_ref (qa.py)'); ax[0].set_ylabel('T = registered sim vs mocap (simulated meshes)')
    ax[1].set_xlabel('S x R (R = registered reference vs mocap)'); ax[1].set_ylabel('T')
    ax[2].set_xlabel('R'); ax[2].set_ylabel(f'T - {k:.3f} S')
    ax[0].set_title('own-mesh policy means (size ~ rollouts)'); ax[1].set_title('multiplicative model'); ax[2].set_title('residual of T = kS vs R')
    for z in ax[:2]:
        z.set_xlim(0, 1.02); z.set_ylim(0, 1.02)
    for z in ax:
        z.grid(alpha=0.3)
    ax[0].legend(fontsize=7, ncol=2); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(a.out, 'calibration.png'), dpi=100)


def frame_share(add):
    """Per-frame share of the kit ADD AUC: mean over frames of g(ADD) = _add_auc (trapezoid over the thresholds)."""
    from v2dlb.object_pose import _ADD_THRESHOLDS_M as TH
    x = np.linspace(0.0, 1.0, TH.size); w = np.zeros(TH.size); dx = np.diff(x)
    w[:-1] += dx / 2; w[1:] += dx / 2
    return (np.asarray(add)[..., None] < TH).astype(float) @ w


def step_frames(a):
    """Frame-local test of the loss model. Per frame f and object b: e_s = sim-vs-reference ADD (qa.py yardstick),
    e_r = reference-vs-mocap registered point error (the R computation). Predicted T:
      prod: mean g(e_s) * g(e_r)        (frame-local version of T = S * R)
      quad: mean g(sqrt(e_s^2 + e_r^2)) (independent errors)
      sum:  mean g(e_s + e_r)           (aligned errors: lower bound on T up to alignment differences)
    with g the kit's per-frame AUC share. Diagnostic only: e_r per frame needs mocap."""
    rows = [json.loads(l) for l in open(os.path.join(a.work, 'rows.jsonl'))]
    rows = [r for r in rows if 'error' not in r]
    seen = set(); rows = [r for r in rows if not (r['sha256'] in seen or seen.add(r['sha256']))]
    sc = Scorer(a); cdir = os.path.join(a.work, 'ref_err'); os.makedirs(cdir, exist_ok=True)
    cp = os.path.join(a.work, 'frames.json'); out = jload(cp, {})
    rows.sort(key=lambda r: (r['ep'], r['lib'], r['ref_digest']))
    if a.max:
        rows = rows[:a.max]
    t0 = time.time()
    for i, r in enumerate(rows):
        if r['sha256'] in out:
            continue
        names = r['objects']; frames, sim, ref = sc.grids(os.path.join(a.store, r['path']), len(names))
        cf = os.path.join(cdir, f"ep{r['ep']}_{mesh_key(a, r['lib'], names).replace('|', '-')}_{r['ref_digest']}.npy")
        if not os.path.exists(cf):
            np.save(cf, sc.registered(r['ep'], r['lib'], ref, frames, return_err=True))
        er = np.load(cf); es = sc.sphere_add(sim, ref)
        gs, gr = frame_share(es), frame_share(er)
        out[r['sha256']] = dict(prod=round(float(np.mean(gs * gr)), 4), quad=round(float(np.mean(frame_share(np.hypot(es, er)))), 4),
                                sum=round(float(np.mean(frame_share(es + er))), 4), S_chk=round(float(np.mean(gs)), 4),
                                R_chk=round(float(np.mean(gr)), 4),
                                cov=round(float(np.mean(gs * gr) - np.mean(gs) * np.mean(gr)), 4))
        if i % 25 == 0:
            jdump(out, cp); print(f'[{time.time() - t0:5.0f}s] {i}/{len(rows)}', flush=True)
    jdump(out, cp)
    # fit summary
    res = jload(os.path.join(a.out, 'calibration.json'), {})
    own = [r for r in rows if r['lib'] != 'scan']
    T = np.array([r['T'] for r in own]); S = np.array([r['S'] for r in own]); R = np.array([r['R'] for r in own])
    fr = {}
    for name, sel in (('all', np.ones(len(own), bool)), ('S>=0.8', S >= 0.8), ('S<0.8', S < 0.8),
                      ('R>=0.95', R >= 0.95), ('R<0.95', R < 0.95)):
        if sel.sum() < 2:
            continue
        d = dict(n=int(sel.sum()))
        for m in ('prod', 'quad', 'sum'):
            pr = np.array([out[r['sha256']][m] for r in own])[sel]
            e = T[sel] - pr
            d[m] = dict(rmse=round(float(np.sqrt(np.mean(e ** 2))), 4), bias=round(float(np.mean(e)), 4))
        e = T[sel] - S[sel] * R[sel]; d['S*R'] = dict(rmse=round(float(np.sqrt(np.mean(e ** 2))), 4), bias=round(float(np.mean(e)), 4))
        cv = np.array([out[r['sha256']]['cov'] for r in own])[sel]
        d['mean_cov_gs_gr'] = round(float(np.mean(cv)), 4)
        fr[name] = d
    res['frame_local'] = fr
    jdump(res, os.path.join(a.out, 'calibration.json'))
    print(json.dumps(fr, indent=1))


def fast_sym_err(T3, achieved, reference, points, axis, order):
    """Same quantity as the kit's _symmetry_point_errors for one object ([T, W] mean point error, min over the
    approved axial rotations), computed in the reference body frame with cylindrical coordinates (all rotations at
    once). Differs from the kit only by float rounding (checked in step symS). Used only for the S_mesh yardstick."""
    if not np.any(axis) or order <= 1:
        return T3._symmetry_point_errors(achieved, reference, points, axis, order)
    ra, rr = T3._rotation_matrix(achieved[..., 3:]), T3._rotation_matrix(reference[..., 3:])
    moved = np.einsum('...ij,vj->...vi', ra, points) + achieved[..., None, :3]
    q = np.einsum('...ji,...vj->...vi', rr, moved - reference[..., None, :3])      # into the reference body frame
    u = axis / np.linalg.norm(axis); e1 = np.eye(3)[np.argmin(np.abs(u))]; e1 = e1 - u * (e1 @ u); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)

    def cyl(x):
        return x @ u, np.hypot(x @ e1, x @ e2), np.arctan2(x @ e2, x @ e1)
    hp, rp, tp = cyl(points); hq, rq, tq = cyl(q)
    ang = np.arange(order) * (2 * np.pi / order)
    best = np.full(achieved.shape[:-1], np.inf)
    flat_hq, flat_rq, flat_tq = (x.reshape(-1, len(points)) for x in (hq, rq, tq))
    out = best.reshape(-1)
    for s0 in range(0, len(flat_hq), 16):
        sl = slice(s0, s0 + 16)
        d2 = ((flat_hq[sl, :, None] - hp[None, :, None]) ** 2 + flat_rq[sl, :, None] ** 2 + rp[None, :, None] ** 2
              - 2 * flat_rq[sl, :, None] * rp[None, :, None] * np.cos(flat_tq[sl, :, None] - tp[None, :, None] - ang[None, None, :]))
        out[sl] = np.sqrt(np.maximum(d2, 0)).mean(axis=1).min(axis=1)
    return out.reshape(achieved.shape[:-1])


def step_symS(a):
    """GT-free alternative yardstick (hypothesis H-yard): S_mesh = the leaderboard's registered computation with OUR
    reference standing in for the truth and OUR simulated mesh standing in for the scan: 1000 surface points of our
    mesh about its surface centroid, cup axes (order 360) / lid normal (order 2) from our mesh's principal axes, the
    leaderboard's scene alignment. No mocap is read. Cached in WORK/s_mesh.json."""
    import trimesh
    rows = [json.loads(l) for l in open(os.path.join(a.work, 'rows.jsonl'))]
    rows = [r for r in rows if 'error' not in r and r['lib'] != 'scan']
    seen = set(); rows = [r for r in rows if not (r['sha256'] in seen or seen.add(r['sha256']))]
    if a.max:
        rows = rows[:a.max]
    sc = Scorer(a); T3 = sc.T3
    cp = os.path.join(a.work, 's_mesh.json'); out = jload(cp, {}); geo = {}; checked = False
    t0 = time.time()
    for i, r in enumerate(sorted(rows, key=lambda r: (r['ep'], r['lib']))):
        if r['sha256'] in out:
            continue
        names = r['objects']; B = len(names)
        G = []
        for slot, n in enumerate(names):
            key = (r['lib'], n, slot)
            if key not in geo:
                m = trimesh.load(f"{a.repo}/meshes/{r['lib']}/{n}.glb", force='mesh')
                v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
                c, _ = sc.sm(v, f); pts = sc.sample(v, f, 1000, 7 + slot) - c
                axis, order = np.zeros(3), 0
                if n in Scorer.SYM:
                    w, U = np.linalg.eigh(np.cov(pts.T))
                    if Scorer.SYM[n] == 'half':
                        axis, order = U[:, 0], 2
                    else:
                        k = int(np.argmax([abs(w[j] - np.mean(np.delete(w, j))) for j in range(3)]))
                        axis, order = U[:, k], 360
                geo[key] = dict(c=c, pts=pts, axis=axis, order=order)
            G.append(geo[key])
        frames, sim, ref = sc.grids(os.path.join(a.store, r['path']), B)
        ach, rf = sim[:, None].copy(), ref[:, None].copy()
        for b in range(B):                                             # poses of the centroid frame (axis through it)
            ach[:, :, b] = T3._convert_object_body(ach[:, :, b], G[b]['c'], np.eye(3))
            rf[:, :, b] = T3._convert_object_body(rf[:, :, b], G[b]['c'], np.eye(3))
        axes = [g['axis'] for g in G]
        ach = T3._align_registered_scene(ach, rf, axes)
        err = [fast_sym_err(T3, ach[:, :, b], rf[:, :, b], G[b]['pts'], G[b]['axis'], G[b]['order']) for b in range(B)]
        if not checked and any(g['order'] == 360 for g in G):                # once: fast path == kit function
            b = next(j for j, g in enumerate(G) if g['order'] == 360)
            ref_err = T3._symmetry_point_errors(ach[:, :, b], rf[:, :, b], G[b]['pts'], G[b]['axis'], G[b]['order'])
            checked = float(np.max(np.abs(ref_err - err[b])))
            print(f'fast_sym_err vs kit _symmetry_point_errors: max abs diff {checked:.2e} m', flush=True)
            out['_check_fast_vs_kit_m'] = checked
            assert checked < 1e-9
        out[r['sha256']] = dict(S_mesh=round(float(T3._add_auc(np.stack(err, axis=-1))), 4),
                                S_mesh_obj={n: round(float(T3._add_auc(np.stack([err[b]], axis=-1))), 4) for b, n in enumerate(names)})
        if i % 25 == 0:
            jdump(out, cp); print(f"[{time.time() - t0:5.0f}s] {i}/{len(rows)} ep{r['ep']} S {r['S']} S_mesh {out[r['sha256']]['S_mesh']} T {r['T']}", flush=True)
    jdump(out, cp)


def step_plot(a):
    """Plot from the fit outputs (needs only numpy + matplotlib; the scoring venv may lack matplotlib)."""
    P = jload(os.path.join(a.out, 'policies.json')); res = jload(os.path.join(a.out, 'calibration.json'))
    plot(a, None, P, res['k_policies_own_R>=0.95'])


def main():
    a = args()
    steps = ['inventory', 'fetch', 'libs', 'score', 'verify', 'symS', 'fit', 'frames'] if a.step == 'all' else [a.step]
    for s in steps:
        globals()[f'step_{s}'](a)


if __name__ == '__main__':
    main()
