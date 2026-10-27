#!/usr/bin/env python
"""Integration driver of the autokit engine (stage 1, builder "integ", 2026-10-27): one (object, episode) ->
every candidate the engine can make -> GT-free gates on that episode's own points (and on held-out episodes of the
same object when they exist) -> one pick, rendered next to a colour crop.

Candidates (all built from ONE episode's observed points, as the owner's 22 Oct per-episode rule requires):
  shell_raw_t{1.5,2.5,4.0}   route A, autokit.shell.thin_shell on the raw observed points (obs_all / obs)
  shell_ref_t{1.5,2.5,4.0}   route A on refine.py's per-frame-corrected copy (auto/stage1/refined), when it exists
  dsl_<program>[+variant]_t{1.5,2.5,4.0}   route B, autokit.program.run_program for every part program listed for the
                             object in the driver table below (raw points; the programs' own default windows)
  library_v3                 our TSDF library mesh (gates.select's fallback: always eligible, never gated)
  incumbent_<tag>            the hand-kit / lathe mesh of an earlier round, when one exists and is leak-free
Evaluation: gates.evaluate(mesh, [obs], obj, ep) per (candidate, episode).
  role 'own'      the build episode, on the refined observation copy (gates v2 levels were checked only there;
                  evaluate() composes refine.py's per-frame correction into our track), flip check included;
  role 'holdout'  every held-out episode, refined copy, flip check reused from the 'own' row (flip_check compares the
                  mesh with library_v3 and does not depend on the episode), gates recomputed with gates.gates_of;
  role 'rawobs'   report only: the build episode on the RAW observation file (refined-vs-raw self-consistency check:
                  a mesh built from refined points is favoured when judged on refined points, and vice versa).
Selection: gates.select over the 'own' + 'holdout' rows (a mesh must pass on every episode; rank = mean rank score).
  Also reported: pick_own_only = gates.select over the 'own' rows alone, which is what eval-time selection can see
  (an eval episode has no second episode of its own).
Outputs under OUT/<obj>_ep<N>/: cand/*.glb + *.json (build reports), candidates.jsonl (one row per candidate x
  episode x role, GT-free metrics only), per_frame.jsonl, selection.json, summary.tsv, qa_pick.jpg, run_meta.json.

GT-free: observed points, tracks and calibration only through autokit.io_gt (refuses /loc/, /scan, *_align, parquet,
mocap); meshes are our candidates, library_v3 and earlier GT-free rounds. No scan is opened or scored here and
mesh_metric.py is not run. Object names appear only in the driver input tables below (they select programs,
incumbent files and default hold-out episodes); the method modules carry none.

Usage:
  run_object.py run OBJ EP [--holdout 22,40] [--out DIR] [--ts 1.5,2.5,4.0] [--reuse] [--no-render] [--no-rawobs]
                  [--main-variant]   (post hoc: also '<shell>+main', see main_group)
  run_object.py audit STRACE.log [STRACE2.log ...]     (counts opens of GT-pattern paths in strace -e openat logs)
"""
import argparse, copy, hashlib, json, os, re, subprocess, sys, time, traceback

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
from autokit import io_gt                                  # noqa: E402
from autokit import gates as G                             # noqa: E402
from autokit.shell import thin_shell                       # noqa: E402
from autokit.program import run_program, load_program, jsonable, T_GRID   # noqa: E402

S = io_gt.SCRATCH
OUT_ROOT = f'{S}/auto/stage1/integ'
PROG_DIR = f'{HERE}/programs'
REPO = G.REPO
RES = f'{REPO}/docs/research/mesh-2026-10-26/results/prim/meshes'
T_MM = (1.5, 2.5, 4.0)
assert all(any(abs(t * 1e-3 - g) < 1e-9 for g in T_GRID) for t in T_MM)

# ---------------------------------------------------------------------------------------- driver input tables
# The only place object names appear. Programs: the part programs written for an object (stage 2 adds more).
PROGRAMS = {
    'white_pot_lid': ['sheet_strap_balls.json'],
    'white_pot': ['lathe_bar_balls.json'],
    'blue_cup': ['lathe_splat.json'],
    'plastic_dish_rack': ['tray_holder_pegs_balls.json'],
}
# Program variants (generic edits of an existing program, keyed by program file; no object knowledge):
# lathe_splat's 'concat' keeps overlapping separate shells (reproduction of the lathe_obs incumbent); the DSL builder
# recommends 'union' (one watertight solid) for submission, so both are candidates.
VARIANTS = {
    'lathe_splat.json': [('union', lambda p: [q['params'].update(combine='union') for q in p['parts']
                                              if q['type'] == 'splat'])],
}
# Incumbents of earlier GT-free rounds (built from this episode's points). The lid's first hand-kit meshes
# (results/prim/meshes/white_pot_lid_ep2_fit_v*.glb) used scan-measured thicknesses (leak found 27 Oct) and are NOT
# candidates; the pre-registered clean-up round rebuilt the lid on the generic t grid (prim/clean/lid).
INCUMBENTS = {
    ('white_pot_lid', 2): [('handkit_clean_t2.5', f'{S}/prim/clean/lid/t2.5_fit.glb')],
    ('blue_cup', 21): [('lathe_obs_g1', f'{S}/lathe/ep21_blue_cup_g1.glb')],
}
# Default held-out episodes (public episodes of the same object with observed points). white_pot_lid ep0 is left out:
# its track is 23-26 mm off the object frame (known bad track, refine.py skipped all its frames).
HOLDOUTS = {
    ('white_pot_lid', 2): [],
    ('blue_cup', 21): [22],
    ('mini_dust_pan', 39): [18, 40],
    ('water_pitcher', 22): [21],
    ('mini_sweeper', 31): [18],
}

# ---------------------------------------------------------------------------------------- helpers
FLIP_KEYS = ('flip_n', 'flips', 'flip_xadd_med_mm', 'flip_rot', 'flip_sec')
FORBIDDEN = io_gt.FORBIDDEN                                 # ('/loc/', '/scan', '_align', '.parquet', 'mocap')


def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:n]


def jl(path, row):
    with open(path, 'a') as f:
        f.write(json.dumps(jsonable(row), default=str) + '\n')


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def obs_paths(obj, ep):
    """(raw path, refined path or None) of one episode, through io_gt (which refuses GT paths)."""
    raw = io_gt.obs_path(obj, ep)
    ref = io_gt.obs_path(obj, ep, refined=True, must_exist=False)
    return raw, (ref if os.path.isfile(ref) else None)


def eval_obs(obj, ep):
    """Observation file the gates judge on: the refined copy (gates v2) when it exists, else the raw file."""
    raw, ref = obs_paths(obj, ep)
    return ref or raw, ('refined' if ref else 'raw')


# ---------------------------------------------------------------------------------------- candidates
def mesh_summary(m):
    bodies = m.split(only_watertight=False)
    return dict(faces=int(len(m.faces)), watertight=bool(m.is_watertight), bodies=int(len(bodies)),
                all_bodies_watertight=bool(len(bodies) > 0 and all(b.is_watertight for b in bodies)),
                area_cm2=round(float(m.area) * 1e4, 1))


def main_group(m):
    """POST-HOC variant (added 2026-10-27 after the production runs, when every shell of one dev object failed G_CONN at
    0.94-0.96): shell.clean_islands keeps islands within NEAR = 30 mm of the body that were seen in enough frames,
    while gates.G_CONN counts only the touching group (TOUCH) plus small compact balls. This keeps exactly what
    G_CONN counts, with the gates' own constants (the same grouping as gates.connectivity), and drops the rest.
    Returns (mesh, info) or (None, info) when there is nothing to drop. Generic: no object knowledge."""
    import math
    from scipy.spatial import cKDTree
    comps = m.split(only_watertight=False)
    if len(comps) <= 1:
        return None, dict(bodies=len(comps))
    areas = np.array([c.area for c in comps])
    smp, trees = [], []
    for i, c in enumerate(comps):
        n = int(np.clip(c.area * 1e6, 300, 200_000))
        smp.append(np.vstack([trimesh.sample.sample_surface(c, n, seed=i)[0], c.vertices])); trees.append(cKDTree(smp[-1]))
    parent = list(range(len(comps)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    bmin = np.array([c.bounds[0] for c in comps]); bmax = np.array([c.bounds[1] for c in comps])
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            if np.any(bmin[i] > bmax[j] + G.TOUCH) or np.any(bmin[j] > bmax[i] + G.TOUCH):
                continue
            if find(i) != find(j) and np.isfinite(trees[i].query(smp[j], distance_upper_bound=G.TOUCH)[0]).any():
                parent[find(i)] = find(j)
    roots = np.array([find(i) for i in range(len(comps))])
    g_area = {r: areas[roots == r].sum() for r in set(roots.tolist())}
    main = max(g_area, key=g_area.get)
    keep = set(np.nonzero(roots == main)[0].tolist())
    mtree = cKDTree(np.vstack([smp[i] for i in keep]))
    for r in g_area:
        mem = np.nonzero(roots == r)[0]
        if r == main or len(mem) != 1:
            continue
        c = comps[mem[0]]
        if not c.is_watertight or c.volume <= 0:
            continue
        d_eq = (6 * c.volume / math.pi) ** (1 / 3); spher = math.pi ** (1 / 3) * (6 * c.volume) ** (2 / 3) / c.area
        if d_eq <= G.BALL_D_MAX and spher >= G.BALL_SPHER_MIN and \
                np.isfinite(mtree.query(smp[mem[0]], distance_upper_bound=G.BALL_LINK)[0]).any():
            keep.add(int(mem[0]))
    if len(keep) == len(comps):
        return None, dict(bodies=len(comps), dropped=0)
    out = trimesh.util.concatenate([comps[i] for i in sorted(keep)])
    return out, dict(bodies=len(comps), kept=len(keep), dropped_area_cm2=round(float(areas.sum() - areas[sorted(keep)].sum()) * 1e4, 2),
                     dropped_share=round(float(1 - areas[sorted(keep)].sum() / areas.sum()), 4))


def build_candidates(obj, ep, cdir, ts=T_MM, reuse=False, main_variant=False):
    """Build every candidate of (obj, ep) into cdir. Returns a list of candidate dicts (name, kind, route, t_mm,
    mesh, src, build) - failures included, with build['error'] set and mesh None. main_variant (post hoc): add
    '<shell>+main' = main_group() of every multi-body shell."""
    os.makedirs(cdir, exist_ok=True)
    raw, ref = obs_paths(obj, ep)
    cands = []

    def done(name, kind, route, t_mm, src, fn):
        mp, jp = f'{cdir}/{name}.glb', f'{cdir}/{name}.json'
        c = dict(name=name, kind=kind, route=route, t_mm=t_mm, src=src, mesh=None)
        if reuse and os.path.isfile(mp) and os.path.isfile(jp):
            c.update(mesh=mp, build=json.load(open(jp)), reused=True)
            log('reuse', name); cands.append(c); return
        t0 = time.time()
        try:
            m, rep = fn()
            m.metadata.pop('shell_report', None)
            m.export(mp)
            b = dict(sec=round(time.time() - t0, 1), **mesh_summary(m), report=rep)
            json.dump(jsonable(b), open(jp, 'w'), indent=1, default=str)
            c.update(mesh=mp, build=b)
            log('built', name, json.dumps({k: b[k] for k in ('sec', 'faces', 'watertight', 'bodies', 'area_cm2')}))
        except Exception as e:  # noqa: BLE001 - a failed candidate is a result, not a crash
            c.update(build=dict(sec=round(time.time() - t0, 1), error=f'{type(e).__name__}: {e}'[:500],
                                trace=traceback.format_exc()[-1500:]))
            log('FAILED', name, c['build']['error'])
        cands.append(c)

    # route A: thin shell on raw and refined points
    for tag, path in (('raw', raw), ('ref', ref)):
        if path is None:
            log(f'no refined copy for {obj} ep{ep}: shell_ref skipped'); continue
        o = io_gt.load_obs(path, keys=('pts', 'cam', 'frame'))
        for t in ts:
            done(f'shell_{tag}_t{t:.1f}', 'shell', 'A', t, path,
                 lambda o=o, t=t: thin_shell(o, t=t * 1e-3, return_report=True))
        del o
    if main_variant:                                    # post hoc: G_CONN-consistent island policy
        for c in [c for c in cands if c['kind'] == 'shell' and c['mesh'] and c['build'].get('bodies', 1) > 1]:
            src_mesh = c['mesh']

            def mk(src_mesh=src_mesh):
                mm, info = main_group(G.load_raw(src_mesh))
                if mm is None:
                    raise RuntimeError(f'nothing to drop: {info}')
                return mm, info
            done(c['name'] + '+main', 'shell', 'A', c['t_mm'], c['src'], mk)
    # route B: part programs listed for the object (raw points)
    progs = PROGRAMS.get(obj, [])
    if progs:
        o = io_gt.load_obs(raw)
        for pf in progs:
            base = load_program(f'{PROG_DIR}/{pf}')
            vlist = [('', None)] + VARIANTS.get(pf, [])
            for vtag, patch in vlist:
                prog = copy.deepcopy(base)
                if patch:
                    patch(prog)
                pname = pf[:-5] + (f'+{vtag}' if vtag else '')
                for t in ts:
                    done(f'dsl_{pname}_t{t:.1f}', 'dsl', 'B', t, raw,
                         lambda prog=prog, t=t: run_program(prog, o, t=t * 1e-3, lib=G.lib_path(obj)))
        del o
    # library_v3 (fallback) and incumbents: existing meshes, referenced in place (gates.is_fallback keys on LIB_DIR)
    lp = G.lib_path(obj)
    cands.append(dict(name='library_v3', kind='library', route='fallback', t_mm=None, src=None, mesh=lp,
                      build=dict(sec=0.0, **mesh_summary(G.load_raw(lp)))))
    for tag, mp in INCUMBENTS.get((obj, ep), []):
        if os.path.isfile(mp):
            cands.append(dict(name=f'incumbent_{tag}', kind='incumbent', route='earlier', t_mm=None, src=None,
                              mesh=mp, build=dict(sec=None, **mesh_summary(G.load_raw(mp)))))
        else:
            log('incumbent missing', mp)
    return cands


# ---------------------------------------------------------------------------------------- evaluation
def evaluate_candidate(c, obj, ep, holdouts, rawobs=True):
    """gates.evaluate rows of one candidate: own (refined, flip), holdouts (refined, flip reused), rawobs (report)."""
    rows, per = [], []
    own_path, own_kind = eval_obs(obj, ep)
    r = G.evaluate(c['mesh'], [own_path], obj, ep, flip=True)
    per.append(dict(cand=c['name'], ep=ep, role='own', per_frame=r.pop('per_frame')))
    r.update(role='own', obs_kind=own_kind)
    rows.append(r)
    flipm = {k: r['metrics'].get(k) for k in FLIP_KEYS}
    extra = [(h, 'holdout') for h in holdouts]
    if rawobs and own_kind == 'refined':
        extra.append((ep, 'rawobs'))
    for e2, role in extra:
        p2, k2 = (eval_obs(obj, e2) if role == 'holdout' else (obs_paths(obj, e2)[0], 'raw'))
        r2 = G.evaluate(c['mesh'], [p2], obj, e2, flip=False)
        per.append(dict(cand=c['name'], ep=e2, role=role, per_frame=r2.pop('per_frame')))
        r2['metrics'].update(flipm); r2['metrics']['flip_reused_from_ep'] = ep
        r2['gates'] = G.gates_of(r2['metrics']); r2['pass'] = all(r2['gates'].values())
        r2.update(role=role, obs_kind=k2)
        rows.append(r2)
    for r_ in rows:
        r_.pop('thresholds', None)
        r_.update(cand=c['name'], kind=c['kind'], route=c['route'], t_mm=c['t_mm'], build_ep=ep,
                  fallback=(c['kind'] == 'library'))
    return rows, per


def short_reasons(sel, name_of):
    out = {}
    for mesh, rr in sel['reasons'].items():
        out[name_of.get(mesh, mesh)] = rr
    return dict(pick=name_of.get(sel['pick'], sel['pick']), pick_mesh=sel['pick'],
                ranking=[name_of.get(m, m) for m in sel['ranking']], reasons=out)


# ---------------------------------------------------------------------------------------- render
def render_pick(obj, ep, holdouts, meshes, labels, out_path):
    """QA image [colour crop | meshes] from the crop's frame (our track). Uses the build episode's crop, else the
    first held-out episode's (the object frame is shared), else the build episode's frame with most points."""
    import cv2
    from autokit import test_shell as TS
    ep_c = next((e for e in [ep] + list(holdouts) if os.path.isfile(f'{TS.CROPS}/ep{e}/{obj}_crops.json')), ep)
    k = TS.qa_image(ep_c, obj, meshes, labels, out_path)
    img = cv2.imread(out_path)
    if img is not None:
        cv2.putText(img, f'{obj}: built ep{ep}, view ep{ep_c} frame {k}', (6, img.shape[0] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)
        cv2.imwrite(out_path, img)
    return dict(view_ep=ep_c, frame=k, image=out_path)


# ---------------------------------------------------------------------------------------- main run
SUM_KEYS = ('dr_comp', 'dr_hole3d', 'dr_viol', 'fs_frac', 'conn_share', 'topo_raw_watertight', 'topo_budget_faces',
            'frame_med_mm', 'flips', 'dr_cdist_mm', 'dr_pdist_mm', 'fid_sum_mm', 'area_cm2', 'drift_area', 'drift_rms')


def run(obj, ep, holdouts, out, ts=T_MM, reuse=False, render=True, rawobs=True, main_variant=False):
    t_all = time.time()
    odir = f'{out}/{obj}_ep{ep}'
    os.makedirs(odir, exist_ok=True)
    head = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', 'docs/research/mesh-2026-10-26/autokit'],
                           capture_output=True, text=True).stdout.strip().splitlines()
    meta = dict(obj=obj, ep=ep, holdouts=holdouts, ts=list(ts), start=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                repo_head=head, autokit_dirty=dirty, argv=sys.argv, host=os.uname().nodename,
                code_sha256={f: sha(f'{HERE}/{f}') for f in ('run_object.py', 'io_gt.py', 'refine.py', 'shell.py',
                                                             'parts.py', 'program.py', 'gates.py')},
                eval_obs={e: eval_obs(obj, e) for e in [ep] + list(holdouts)}, main_variant=main_variant,
                thresholds=G.THRESHOLDS)
    json.dump(jsonable(meta), open(f'{odir}/run_meta.json', 'w'), indent=1, default=str)
    log('meta', json.dumps(jsonable(meta), default=str)[:600])
    # ---- build
    t_b = time.time()
    cands = build_candidates(obj, ep, f'{odir}/cand', ts=ts, reuse=reuse, main_variant=main_variant)
    sec_build = time.time() - t_b
    # ---- evaluate
    cpath, ppath = f'{odir}/candidates.jsonl', f'{odir}/per_frame.jsonl'
    for p in (cpath, ppath):
        if os.path.exists(p):
            os.replace(p, p + f'.prev{int(time.time())}')
    t_e = time.time()
    rows = []
    for c in cands:
        if c['mesh'] is None:
            jl(cpath, dict(cand=c['name'], kind=c['kind'], route=c['route'], t_mm=c['t_mm'], build_ep=ep,
                           build=c['build'], role='build_failed'))
            continue
        try:
            rs, per = evaluate_candidate(c, obj, ep, holdouts, rawobs=rawobs)
        except Exception as e:  # noqa: BLE001
            err = f'{type(e).__name__}: {e}'[:500]
            log('EVAL FAILED', c['name'], err)
            jl(cpath, dict(cand=c['name'], kind=c['kind'], build_ep=ep, role='eval_failed', error=err,
                           trace=traceback.format_exc()[-1500:]))
            continue
        bsum = {k: v for k, v in c['build'].items() if k != 'report'}
        for r in rs:
            r['build'] = bsum
            jl(cpath, r)
        for p in per:
            jl(ppath, p)
        rows += rs
        for r in rs:
            m = r['metrics']
            log('eval', c['name'], f"ep{r['ep']}", r['role'], 'PASS' if r['pass'] else 'fail',
                [g for g, v in r['gates'].items() if not v], 'rank', r['rank_score'], 'sec', r['sec'],
                json.dumps({k: m.get(k) for k in ('dr_comp', 'dr_viol', 'dr_hole3d', 'fid_sum_mm', 'conn_share')}))
    sec_eval = time.time() - t_e
    # ---- select
    name_of = {r['mesh']: r['cand'] for r in rows}
    sel_rows = [r for r in rows if r['role'] in ('own', 'holdout')]
    sel = short_reasons(G.select(sel_rows), name_of)
    sel_own = short_reasons(G.select([r for r in rows if r['role'] == 'own']), name_of)
    raw_rows = [r for r in rows if r['role'] == 'rawobs']
    sel_raw = short_reasons(G.select(raw_rows), name_of) if raw_rows else None
    selection = dict(obj=obj, build_ep=ep, holdouts=holdouts, rule='gates.select over own + holdout rows (refined obs)',
                     **sel, pick_own_only=sel_own['pick'], ranking_own_only=sel_own['ranking'],
                     reasons_own_only=sel_own['reasons'],
                     pick_rawobs_report_only=sel_raw['pick'] if sel_raw else None,
                     ranking_rawobs_report_only=sel_raw['ranking'] if sel_raw else None,
                     n_candidates=len(cands), n_built=sum(c['mesh'] is not None for c in cands),
                     build_failed=[c['name'] for c in cands if c['mesh'] is None],
                     sec_build=round(sec_build, 1), sec_eval=round(sec_eval, 1))
    # ---- summary table (GT-free metrics only)
    with open(f'{odir}/summary.tsv', 'w') as f:
        f.write('\t'.join(['cand', 'ep', 'role', 'pass', 'failed', 'rank_score', *SUM_KEYS, 'build_sec', 'eval_sec']) + '\n')
        for r in rows:
            m = r['metrics']
            f.write('\t'.join(str(x) for x in [r['cand'], r['ep'], r['role'], r['pass'],
                                                ','.join(g for g, v in r['gates'].items() if not v), r['rank_score'],
                                                *[m.get(k) for k in SUM_KEYS], r['build'].get('sec'), r['sec']]) + '\n')
    # ---- render the pick next to a crop (as built and as the scorer decodes it), with library_v3
    if render and sel['pick_mesh']:
        try:
            bp = f'{odir}/pick_b4096.glb'
            G.load_budget(sel['pick_mesh']).export(bp)
            ms, labs = [sel['pick_mesh'], bp], [f"pick {sel['pick']}", 'pick, budget 4096']
            if sel_own['pick'] != sel['pick'] and sel_own['pick_mesh']:
                ms.append(sel_own['pick_mesh']); labs.append(f"own-only {sel_own['pick']}")
            if sel['pick'] != 'library_v3':
                ms.append(G.lib_path(obj)); labs.append('library_v3')
            selection['render'] = render_pick(obj, ep, holdouts, ms, labs, f'{odir}/qa_pick.jpg')
        except Exception as e:  # noqa: BLE001
            selection['render'] = dict(error=f'{type(e).__name__}: {e}'[:300])
            log('RENDER FAILED', selection['render']['error'])
    selection['sec_total'] = round(time.time() - t_all, 1)
    json.dump(jsonable(selection), open(f'{odir}/selection.json', 'w'), indent=1, default=str)
    log('PICK', sel['pick'], '| own-only', sel_own['pick'], '| rawobs', selection['pick_rawobs_report_only'],
        '| sec', selection['sec_total'])
    return selection


# ---------------------------------------------------------------------------------------- strace audit
LIB_PREFIXES = ('/usr/lib/', '/usr/local/lib/', '/usr/share/', f'{S}/venv/', '/proc/', '/sys/', '/dev/', '/etc/')


def audit(logs):
    """Count openat calls on paths that match the GT patterns of io_gt.FORBIDDEN (case-insensitive). Reports the raw
    count over every path, the count after excluding system / venv library files (e.g. json/scanner.py matches
    '/scan'), and the successful ones among those."""
    out = []
    for lg in logs:
        n_open = 0; raw_hits, data_hits, ok_hits = [], [], []
        opened = set()
        for line in open(lg, errors='replace'):
            mm = re.search(r'open(?:at2?)?\(.*?"([^"]*)"', line)
            if not mm:
                continue
            n_open += 1
            p = mm.group(1)
            failed = bool(re.search(r'= -1 E[A-Z]+', line))
            if not failed:
                opened.add(p)
            if any(b in p.lower() for b in FORBIDDEN):
                raw_hits.append(p)
                if not p.startswith(LIB_PREFIXES):
                    data_hits.append(p)
                    if not failed:
                        ok_hits.append(p)
        data_files = sorted(p for p in opened if p.startswith('/') and not p.startswith(LIB_PREFIXES)
                            and not p.endswith(('.so', '.pyc', '.py')) and '/__pycache__/' not in p
                            and not re.search(r'\.so(\.\d+)*$', p) and os.path.isfile(p))
        r = dict(log=lg, openat_calls=n_open, forbidden_pattern_any=len(raw_hits),
                 forbidden_pattern_any_examples=sorted(set(raw_hits))[:8], forbidden_non_library=len(data_hits),
                 forbidden_non_library_ok=len(ok_hits), forbidden_non_library_paths=sorted(set(data_hits))[:20],
                 data_files_opened=len(data_files), data_dirs=sorted({os.path.dirname(p) for p in data_files}))
        out.append(r)
        print(json.dumps(r))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('obj'); r.add_argument('ep', type=int)
    r.add_argument('--holdout', default=None, help='comma list of held-out episodes (default: driver table; "" = none)')
    r.add_argument('--out', default=OUT_ROOT); r.add_argument('--ts', default=','.join(str(t) for t in T_MM))
    r.add_argument('--reuse', action='store_true'); r.add_argument('--no-render', action='store_true')
    r.add_argument('--no-rawobs', action='store_true')
    r.add_argument('--main-variant', action='store_true', help='post hoc: add <shell>+main (G_CONN-consistent islands)')
    a_ = sub.add_parser('audit'); a_.add_argument('logs', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'audit':
        audit(a.logs); return
    hold = HOLDOUTS.get((a.obj, a.ep), []) if a.holdout is None else [int(x) for x in a.holdout.split(',') if x]
    ts = tuple(float(x) for x in a.ts.split(','))
    run(a.obj, a.ep, hold, a.out, ts=ts, reuse=a.reuse, render=not a.no_render, rawobs=not a.no_rawobs,
        main_variant=a.main_variant)


if __name__ == '__main__':
    main()
