#!/usr/bin/env python
"""Integration driver of the autokit engine (stage 1 builder "integ" 2026-10-27; stage 1b fixer "gates" 2026-10-29;
stage 1b integration v3 2026-10-30): one (object, episode) -> every candidate the engine can make -> GT-free gates v3
on that episode's own RAW points -> one pick by selector v3 from that episode alone (eval-like: an eval episode has no
second episode of its own), rendered next to a colour crop; plus a hold-out view on other episodes (report only).

Candidates (all built from ONE episode's observed points, as the owner's 22 Oct per-episode rule requires):
  prog_<family>_t{1.5,2.5,4.0}  route B, autokit.program.run_program(..., budget=BUDGET_SHIP) for every part program
                             listed for the object below (raw points). Families = program [+ variant] x balls
                             {free, none} (programs with a ball part; '+bnone' = ball mode 'none') x shell_patch
                             {no, yes} ('+patch' = a shell_patch part over the residual of every earlier part, A inside
                             B). kind 'program': selector v3 takes the 2.5 mm build of each family as the candidate (a
                             family whose every thickness was measured two-sided builds the same mesh at every t);
                             the other t builds are diagnostic (t is not chosen by the rank)
  prog_<program>+tprior_t*   the plain family (balls free, no patch) with every measured thickness forced to the prior
                             (program.variants): t-grid robustness, kind 'program_tprior' (diagnostic only)
  shell_raw_t{1.5,2.5,4.0}   route A, autokit.shell on the raw points (one sheet, solidified per t): kind 'shell',
                             DIAGNOSTIC ONLY (its rank cannot see unobserved surface: stage-1 audit blocker)
  shell_ref_t*               route A on refine.py's copy, only with --refined (diagnostic)
  library_v3                 our TSDF library mesh (selector fallback: always eligible, never gated)
  incumbent_<tag>            the hand-kit / lathe mesh of an earlier GT-free round (kind 'incumbent', diagnostic)
Identical meshes (same vertices and faces, e.g. balls 'none' where the free fit keeps no ball, or a patch with no
residual) are evaluated once; the copy's rows carry dup_of.
Evaluation: gates.evaluate(mesh, [obs], obj, ep) on RAW observations (gates v3 default).
  role 'own'      the build episode; flip check on the selectable rows (2.5 mm family builds, library_v3) and, with
                  --diag-flip, on the diagnostic rows (otherwise their G_FLIP is 'not run': pass_ex_flip is reported);
  role 'holdout'  selectable rows only, on the hold-out episodes (default: the next N_HOLDOUT public episodes of the
                  object in EPISODES, cyclic), flip reused from the 'own' row (flip_check compares the mesh with
                  library_v3 and does not depend on the episode). REPORT ONLY: never used to select;
  role 'refobs'   report only, with --refined: the build episode on refine.py's copy (obs='refined').
Selection: selection.json 'pick' = gates.select (v3) over the 'own' rows alone (what eval-time selection can see).
  'holdout_view' = gates.select over own + holdout rows of the selectable meshes (a mesh must pass on every episode),
  plus the own pick's verdict on each hold-out episode (report only).
Performance only: within one run, a part fit is memoised on (observations, t, part spec, assigned points, earlier
  parts, frame, budget) so families that share a program prefix reuse its fitted parts (PartMemo; results identical,
  checked on public dev episodes; --no-memo turns it off).
Outputs under OUT/<obj>_ep<N>/: cand/*.glb + *.json (build reports), candidates.jsonl (one row per candidate x
  episode x role, GT-free metrics only), per_frame.jsonl, selection.json, summary.tsv, qa_pick.jpg, run_meta.json
  (code sha256, and the sha256 of every input file opened through io_gt).

GT-free: observed points, tracks and calibration only through autokit.io_gt (deny-list /loc/, /scan, *_align, parquet,
mocap, hard links; allow-listed roots); meshes only through io_gt.load_mesh / io_gt.mesh_input (allow-listed roots
auto/**, meshes/library_v3, results/prim/meshes, prim/**, lathe/**). No scan is opened or scored here and
mesh_metric.py is not run. Object names appear only in the driver input tables below (they select programs,
incumbent files and the episode lists); the method modules carry none.

Usage:
  run_object.py run OBJ EP [--holdout 22,40] [--out DIR] [--ts 1.5,2.5,4.0] [--reuse] [--no-render] [--refined]
                  [--no-shells] [--no-tprior] [--no-balls-none] [--no-patch] [--diag-flip] [--no-memo]
                  [--main-variant]   (post hoc: also '<shell>+main', see main_group)
  run_object.py audit STRACE.log [STRACE2.log ...]     (counts opens of GT-pattern paths in strace logs)
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
from autokit.program import run_program, load_program, jsonable, variants, T_GRID   # noqa: E402

S = io_gt.SCRATCH
OUT_ROOT = f'{S}/auto/stage1b/integ'
PROG_DIR = f'{HERE}/programs'
REPO = G.REPO
T_MM = (1.5, 2.5, 4.0)
BUDGET_SHIP = 4000              # face budget of a shipped program mesh (< the kit's 4096: budget_mesh only welds)
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
# recommends 'union' (one watertight solid) for submission, so both are program families.
VARIANTS = {
    'lathe_splat.json': [('union', lambda p: [q['params'].update(combine='union') for q in p['parts']
                                              if q['type'] == 'splat'])],
}
# Incumbents of earlier GT-free rounds (built from this episode's points), diagnostic rows only. The lid's hand-kit
# meshes results/prim/meshes/white_pot_lid_ep2_fit_v1/v2.glb both used T_LID = 2.5 mm (the generic grid middle);
# fit_v2.glb is byte-identical (sha256 0bac47f4...) to the clean-up round's prim/clean/lid/t2.5_fit.glb used here.
INCUMBENTS = {
    ('white_pot_lid', 2): [('handkit_clean_t2.5', f'{S}/prim/clean/lid/t2.5_fit.glb')],
    ('blue_cup', 21): [('lathe_obs_g1', f'{S}/lathe/ep21_blue_cup_g1.glb')],
}
# Public episodes with observed points per object (obs_all). Hold-out view of a build episode: the next N_HOLDOUT
# episodes of its object in this list (cyclic). white_pot_lid ep0 is kept: its track is suspect on GT-free evidence
# (refine.py skipped all 24 of its frames; the lid program's sheet finds 0 of 36 edge sectors there), and the frame /
# track gates are expected to reject what it builds; it is the lid's only hold-out episode for ep2.
EPISODES = {
    'white_pot': [0, 2, 26, 27, 41, 42, 43, 44, 45],
    'white_pot_lid': [0, 2],
    'plastic_dish_rack': [12, 13, 26, 27, 31],
    'blue_cup': [11, 12, 13, 21, 22],
    'mini_dust_pan': [18, 39, 40],
    'water_pitcher': [21, 22],
    'mini_sweeper': [18, 31],
}
N_HOLDOUT = 2


def holdouts_of(obj, ep, n=N_HOLDOUT):
    eps = EPISODES.get(obj, [])
    if ep not in eps:
        return []
    i = eps.index(ep)
    return [eps[(i + k) % len(eps)] for k in range(1, min(n, len(eps) - 1) + 1)]


# ---------------------------------------------------------------------------------------- helpers
FLIP_KEYS = G.FLIP_KEYS
FORBIDDEN = io_gt.FORBIDDEN                                 # ('/loc/', '/scan', '_align', '.parquet', 'mocap')
MEASURED_SRC = ('two_sided', 'side')


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
    """(raw path, refined path or None) of one episode, through io_gt (deny-list + allow-listed roots)."""
    raw = io_gt.obs_path(obj, ep)
    ref = io_gt.obs_path(obj, ep, refined=True, must_exist=False)
    return raw, (ref if os.path.isfile(ref) else None)


def t_rule_of(report):
    """'measured' when every thickness-bearing part of a program build took its thickness from two-sided / side
    evidence (the build does not depend on the prior t), 'prior' when none did, 'mixed' otherwise, 'none' when no part
    reports a thickness source."""
    src = []
    for rec in (report or {}).get('parts', []):
        dg = rec.get('diag') or {}
        for k in ('t_src', 'T_src'):
            if k in dg:
                src.append(dg[k])
    if not src:
        return 'none'
    if all(s_ in MEASURED_SRC for s_ in src):
        return 'measured'
    if not any(s_ in MEASURED_SRC for s_ in src):
        return 'prior'
    return 'mixed'


def with_balls(prog, mode):
    """Generic program edit: every ball part takes params.mode = mode ('free' / 'none')."""
    pr = copy.deepcopy(prog)
    for q in pr['parts']:
        if q['type'] == 'ball':
            q.setdefault('params', {})['mode'] = mode
    return pr


def with_patch(prog):
    """Generic program edit (A inside B): a shell_patch part over the residual of every earlier part."""
    pr = copy.deepcopy(prog)
    pr['parts'].append(dict(name='patch', type='shell_patch', assign=dict(rule='residual')))
    return pr


def geo_hash(m):
    """sha256 of a mesh's vertex and face arrays (identical meshes are evaluated once)."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(m.vertices, np.float64)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(m.faces, np.int64)).tobytes())
    return h.hexdigest()[:24]


class PartMemo:
    """PERFORMANCE ONLY. Memoises part fits within one run: key = (observation dict, t, library path, budget, part
    spec, assigned point indices, earlier parts (by identity), program frame); a hit returns the same Part object and
    replays the fit's only context side effect (ctx.frame, set by tube_rrect align_frame). Valid because every family
    of one program runs the same prefix in the same order and later parts only read earlier ones (attach re-applies
    the same clip). Exceptions are memoised too. Checked bit-identical against fresh builds (integ/memo_check)."""

    def __init__(self):
        self.cache, self.hits, self.misses, self.on = {}, 0, 0, False
        self._orig = {}

    def install(self):
        from autokit import parts as PT
        for name, pt in PT.PART_TYPES.items():
            if name not in self._orig:
                self._orig[name] = pt.fit
                pt.fit = self._wrap(pt.fit)
        return self

    def reset(self):
        self.cache.clear(); self.hits = self.misses = 0

    @staticmethod
    def _fkey(fr):
        if fr is None:
            return None
        return hashlib.sha256(json.dumps(jsonable(fr), sort_keys=True, default=str).encode()).hexdigest()[:24]

    def _wrap(self, fn):
        def fit(ctx, idx, spec, done):
            if not self.on:
                return fn(ctx, idx, spec, done)
            key = (id(ctx.obs), round(float(ctx.t), 9), ctx.lib, getattr(ctx, 'budget', None),
                   json.dumps(jsonable(spec), sort_keys=True, default=str),
                   hashlib.sha256(np.ascontiguousarray(np.asarray(idx, np.int64)).tobytes()).hexdigest()[:24],
                   tuple((n, id(q)) for n, q in done.items()), self._fkey(ctx.frame))
            if key in self.cache:
                self.hits += 1
                kind, val, fr_after, changed = self.cache[key]
                if changed:
                    ctx.frame = fr_after
                if kind == 'exc':
                    raise val
                return val
            fr0 = ctx.frame
            try:
                part = fn(ctx, idx, spec, done)
            except Exception as e:  # noqa: BLE001 - re-raised, memoised as the fit's result
                self.misses += 1
                self.cache[key] = ('exc', e, ctx.frame, ctx.frame is not fr0)
                raise
            self.misses += 1
            self.cache[key] = ('ok', part, ctx.frame, ctx.frame is not fr0)
            return part
        return fit


MEMO = PartMemo()


# ---------------------------------------------------------------------------------------- candidates
def mesh_summary(m):
    bodies = G.components(m)
    return dict(faces=int(len(m.faces)), verts=int(len(m.vertices)), watertight=bool(m.is_watertight),
                bodies=int(len(bodies)), all_bodies_watertight=bool(len(bodies) > 0 and all(b.is_watertight for b in bodies)),
                area_cm2=round(float(m.area) * 1e4, 1))


def mesh_summary_of(path):
    """mesh_summary of an existing mesh file, loaded through the io_gt guard."""
    return mesh_summary(io_gt.load_mesh(path))


def main_group(m):
    """POST-HOC variant (stage 1, added after the production runs, when every shell of one dev object failed G_CONN at
    0.94-0.96): keeps exactly what G_CONN counts, with the gates' own constants (the same grouping as
    gates.connectivity), and drops the rest. Returns (mesh, info) or (None, info) when there is nothing to drop."""
    import math
    from scipy.spatial import cKDTree
    comps = G.components(m)
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


def program_families(pf, base):
    """(family name, program dict, plain) of one program file: [+variant] x balls {free, none} x patch {no, yes}."""
    out = []
    vlist = [('', None)] + VARIANTS.get(pf, [])
    has_ball = any(q['type'] == 'ball' for q in base['parts'])
    for vtag, patch_fn in vlist:
        prog = copy.deepcopy(base)
        if patch_fn:
            patch_fn(prog)
        for bm in (('free', 'none') if has_ball else ('-',)):
            for sp in (False, True):
                pr = with_balls(prog, bm) if bm != '-' else copy.deepcopy(prog)
                if sp:
                    pr = with_patch(pr)
                name = pf[:-5] + (f'+{vtag}' if vtag else '') + ('+bnone' if bm == 'none' else '') + ('+patch' if sp else '')
                out.append(dict(family=name, program=pr, plain=(bm != 'none' and not sp), vtag=vtag, balls=bm, patch=sp))
    return out


def build_candidates(obj, ep, cdir, ts=T_MM, reuse=False, main_variant=False, refined=False, shells=True, tprior=True,
                     balls_none=True, patch=True, memo=True):
    """Build every candidate of (obj, ep) into cdir. Returns a list of candidate dicts (name, kind, route, t_mm,
    family, t_rule, mesh, src, build, geo_hash, dup_of) - failures included, with build['error'] set and mesh None."""
    os.makedirs(cdir, exist_ok=True)
    raw, ref = obs_paths(obj, ep)
    cands, seen = [], {}

    def done(name, kind, route, t_mm, src, fn, family=None, extra=None):
        mp, jp = f'{cdir}/{name}.glb', f'{cdir}/{name}.json'
        c = dict(name=name, kind=kind, route=route, t_mm=t_mm, family=family, src=src, mesh=None, t_rule=None,
                 geo_hash=None, dup_of=None, **(extra or {}))
        if reuse and os.path.isfile(mp) and os.path.isfile(jp):
            c.update(mesh=mp, build=json.load(open(jp)), reused=True)
            c['geo_hash'] = c['build'].get('geo_hash')
        else:
            t0 = time.time()
            try:
                m, rep = fn()
                m.metadata.pop('shell_report', None)
                m.export(mp)
                b = dict(sec=round(time.time() - t0, 1), **mesh_summary(m), geo_hash=geo_hash(m), report=rep)
                json.dump(jsonable(b), open(jp, 'w'), indent=1, default=str)
                c.update(mesh=mp, build=b, geo_hash=b['geo_hash'])
                log('built', name, json.dumps({k: b[k] for k in ('sec', 'faces', 'watertight', 'bodies', 'area_cm2')}))
            except Exception as e:  # noqa: BLE001 - a failed candidate is a result, not a crash
                c.update(build=dict(sec=round(time.time() - t0, 1), error=f'{type(e).__name__}: {e}'[:500],
                                    trace=traceback.format_exc()[-1500:]))
                log('FAILED', name, c['build']['error'])
        if c['mesh'] and kind.startswith('program'):
            rep = c['build'].get('report') or {}
            c['t_rule'] = t_rule_of(rep)
            if rep.get('t_mm') is not None:                 # the t the program actually used (a program may fix it)
                c['t_mm'] = float(rep['t_mm'])
        if c['geo_hash']:
            first = seen.setdefault(c['geo_hash'], name)
            c['dup_of'] = first if first != name else None
        cands.append(c)

    # route B: part programs listed for the object (raw points), shipped within the face budget
    progs = PROGRAMS.get(obj, [])
    if progs:
        o = io_gt.load_obs(raw)
        MEMO.install(); MEMO.reset(); MEMO.on = bool(memo)
        try:
            for pf in progs:
                base = load_program(f'{PROG_DIR}/{pf}')
                for fam in program_families(pf, base):
                    if (fam['balls'] == 'none' and not balls_none) or (fam['patch'] and not patch):
                        continue
                    vlist = variants(fam['program']) if (fam['plain'] and tprior) else [('base', fam['program'])]
                    for vname, vprog in vlist:
                        kind = 'program' if vname == 'base' else f'program_{vname}'
                        pname = fam['family'] + ('' if vname == 'base' else f'+{vname}')
                        for t in ts:
                            done(f'prog_{pname}_t{t:.1f}', kind, 'B', t, raw,
                                 lambda vprog=vprog, t=t: run_program(vprog, o, t=t * 1e-3, lib=G.lib_path(obj),
                                                                      budget=BUDGET_SHIP), family=pname,
                                 extra=dict(balls=fam['balls'], patch=fam['patch'], variant=vname))
        finally:
            MEMO.on = False
            memo_stats = dict(hits=MEMO.hits, misses=MEMO.misses, on=bool(memo))
            MEMO.reset()
        log('part memo', json.dumps(memo_stats))
        del o
    else:
        memo_stats = None
    # route A: thin shells, diagnostic rows only (raw points; refined copy only on request); one sheet per obs file
    if shells:
        from autokit import shell as SH
        for tag, path in (('raw', raw), ('ref', ref if refined else None)):
            if path is None:
                continue
            o = io_gt.load_obs(path, keys=('pts', 'cam', 'frame'))
            t0 = time.time()
            try:
                sheet = SH.shell_sheet(o)
                sheet_err = None
            except Exception as e:  # noqa: BLE001
                sheet, sheet_err = None, e
            sec_sheet = round(time.time() - t0, 1)
            for t in ts:
                def mk(t=t):
                    if sheet is None:
                        raise sheet_err
                    m, rep = SH.solidify_sheet(sheet, t * 1e-3, return_report=True)
                    rep['sec_sheet_shared'] = sec_sheet
                    return m, rep
                done(f'shell_{tag}_t{t:.1f}', 'shell', 'A', t, path, mk)
            del o, sheet
        if main_variant:                                    # post hoc: G_CONN-consistent island policy
            for c in [c for c in cands if c['kind'] == 'shell' and c['mesh'] and c['build'].get('bodies', 1) > 1]:
                src_mesh = c['mesh']

                def mk(src_mesh=src_mesh):
                    mm, info = main_group(G.load_raw(src_mesh))
                    if mm is None:
                        raise RuntimeError(f'nothing to drop: {info}')
                    return mm, info
                done(c['name'] + '+main', 'shell', 'A', c['t_mm'], c['src'], mk)
    # library_v3 (fallback) and incumbents: existing meshes, referenced in place, loaded through the io_gt guard
    lp = G.lib_path(obj)
    cands.append(dict(name='library_v3', kind='library', route='fallback', t_mm=None, family=None, t_rule=None, src=None,
                      mesh=lp, build=dict(sec=0.0, **mesh_summary_of(lp)), geo_hash=None, dup_of=None))
    for tag, mp in INCUMBENTS.get((obj, ep), []):
        if os.path.isfile(mp):
            cands.append(dict(name=f'incumbent_{tag}', kind='incumbent', route='earlier', t_mm=None, family=None,
                              t_rule=None, src=None, mesh=mp, build=dict(sec=None, **mesh_summary_of(mp)),
                              geo_hash=None, dup_of=None))
        else:
            log('incumbent missing', mp)
    return cands, memo_stats


# ---------------------------------------------------------------------------------------- evaluation
def evaluate_candidate(c, obj, ep, holdouts, refined=False, flip=True):
    """gates.evaluate rows of one candidate: own (raw; flip check unless flip=False), holdouts (raw, flip reused;
    report only), refobs (report only)."""
    rows, per = [], []
    r = G.evaluate(c['mesh'], None, obj, ep, flip=flip, obs='raw')
    per.append(dict(cand=c['name'], ep=ep, role='own', per_frame=r.pop('per_frame')))
    r.update(role='own', flip_run=bool(flip))
    rows.append(r)
    flipm = {k: r['metrics'].get(k) for k in FLIP_KEYS}
    extra = [(h, 'holdout', 'raw') for h in holdouts]
    if refined and obs_paths(obj, ep)[1]:
        extra.append((ep, 'refobs', 'refined'))
    for e2, role, kind in extra:
        r2 = G.evaluate(c['mesh'], None, obj, e2, obs=kind, flip_metrics=flipm)
        per.append(dict(cand=c['name'], ep=e2, role=role, per_frame=r2.pop('per_frame')))
        r2['metrics']['flip_reused_from_ep'] = ep
        r2.update(role=role, flip_run=bool(flip))
        rows.append(r2)
    for r_ in rows:
        r_.pop('thresholds', None)
        r_.update(cand=c['name'], kind=c['kind'], route=c['route'], t_mm=c['t_mm'], family=c.get('family'),
                  t_rule=c.get('t_rule'), build_ep=ep, fallback=(c['kind'] == 'library'), balls=c.get('balls'),
                  patch=c.get('patch'), dup_of=c.get('dup_of'), geo_hash=c.get('geo_hash'),
                  pass_ex_flip=all(v for k, v in r_['gates'].items() if k != 'G_FLIP'))
    return rows, per


def copy_rows(rows, c, src_name, roles_keep):
    """Rows of an identical mesh evaluated earlier (src_name), re-labelled for candidate c (same gates and metrics);
    only the roles in roles_keep ('own', or ('holdout', ep)) are kept."""
    out = []
    for r in rows:
        if r['role'] != 'own' and ('holdout', r['ep']) not in roles_keep:
            continue
        r2 = copy.deepcopy(r)
        r2.update(cand=c['name'], mesh=os.path.abspath(c['mesh']), kind=c['kind'], route=c['route'], t_mm=c['t_mm'],
                  family=c.get('family'), t_rule=c.get('t_rule'), balls=c.get('balls'), patch=c.get('patch'),
                  dup_of=c.get('dup_of'), geo_hash=c.get('geo_hash'), eval_copied_from=src_name,
                  fallback=(c['kind'] == 'library'))
        out.append(r2)
    return out


def short_reasons(sel, name_of):
    out = {}
    for mesh, rr in sel['reasons'].items():
        out[name_of.get(mesh, mesh)] = rr
    return dict(pick=name_of.get(sel['pick'], sel['pick']), pick_mesh=sel['pick'],
                ranking=[name_of.get(m, m) for m in sel['ranking']], reasons=out)


# ---------------------------------------------------------------------------------------- render
def render_pick(obj, ep, holdouts, meshes, labels, out_path):
    """QA image [colour crop | meshes] from the crop's frame (our track). Uses the build episode's crop, else a
    held-out episode's, else any public episode's of the object (the object frame is shared), else the build
    episode's frame with most points."""
    import cv2
    from autokit import test_shell as TS
    ep_c = next((e for e in [ep] + list(holdouts) + EPISODES.get(obj, [])
                 if os.path.isfile(f'{TS.CROPS}/ep{e}/{obj}_crops.json')), ep)
    k = TS.qa_image(ep_c, obj, meshes, labels, out_path)
    img = cv2.imread(out_path)
    if img is not None:
        cv2.putText(img, f'{obj}: built ep{ep}, view ep{ep_c} frame {k}', (6, img.shape[0] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)
        cv2.imwrite(out_path, img)
    return dict(view_ep=ep_c, frame=k, image=out_path)


# ---------------------------------------------------------------------------------------- main run
SUM_KEYS = ('dr_comp', 'dr_hole3d', 'dr_viol', 'dr_fsv', 'dr_fsv_blob_p75_cm2', 'fs_frac', 'conn_share',
            'topo_budget_watertight', 'topo_area_change', 'topo_budget_faces', 'topo_weld_only', 'frame_med_mm',
            'align_t_mm', 'frame_t_mm', 'flips', 'flip_xadd_med_mm', 'dr_cdist_mm', 'dr_pdist_mm', 'fid_sum_mm',
            'area_cm2', 'drift_area', 'drift_rms')
CODE_FILES = ('run_object.py', 'io_gt.py', 'refine.py', 'shell.py', 'parts.py', 'program.py', 'gates.py')


def pre_roles(cands):
    """Selector-v3 roles of the built candidates before evaluation (gates.roles on their kind / family / t)."""
    by = {c['mesh']: [dict(mesh=c['mesh'], kind=c['kind'], family=c.get('family'), t_mm=c['t_mm'],
                           t_rule=c.get('t_rule'), fallback=(c['kind'] == 'library'))] for c in cands if c['mesh']}
    return G.roles(by)


def run(obj, ep, holdouts, out, ts=T_MM, reuse=False, render=True, refined=False, main_variant=False, shells=True,
        tprior=True, balls_none=True, patch=True, diag_flip=False, memo=True):
    t_all = time.time()
    odir = f'{out}/{obj}_ep{ep}'
    os.makedirs(odir, exist_ok=True)
    head = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', 'docs/research/mesh-2026-10-26/autokit'],
                           capture_output=True, text=True).stdout.strip().splitlines()
    meta = dict(obj=obj, ep=ep, holdouts=holdouts, ts=list(ts), start=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                repo_head=head, autokit_dirty=dirty, argv=sys.argv, host=os.uname().nodename,
                code_sha256={f: sha(f'{HERE}/{f}') for f in CODE_FILES}, obs_kind='raw', refined_report=refined,
                main_variant=main_variant, budget_ship=BUDGET_SHIP, gates_version=G.VERSION, thresholds=G.THRESHOLDS,
                diag_flip=diag_flip, memo=memo, balls_none=balls_none, patch=patch, tprior=tprior, shells=shells)
    json.dump(jsonable(meta), open(f'{odir}/run_meta.json', 'w'), indent=1, default=str)
    log('meta', json.dumps(jsonable(meta), default=str)[:600])
    # ---- build
    t_b = time.time()
    cands, memo_stats = build_candidates(obj, ep, f'{odir}/cand', ts=ts, reuse=reuse, main_variant=main_variant,
                                         refined=refined, shells=shells, tprior=tprior, balls_none=balls_none,
                                         patch=patch, memo=memo)
    sec_build = time.time() - t_b
    meta['part_memo'] = memo_stats
    role = pre_roles(cands)
    # ---- evaluate: selectable rows first (own with flip + hold-outs), then diagnostics (own only)
    cpath, ppath = f'{odir}/candidates.jsonl', f'{odir}/per_frame.jsonl'
    for p in (cpath, ppath):
        if os.path.exists(p):
            os.replace(p, p + f'.prev{int(time.time())}')
    t_e = time.time()
    rows, inputs, evals = [], {}, {}           # evals: geo_hash -> (cand name, rows, flip_run, hold-out set)
    order = sorted([c for c in cands if c['mesh']], key=lambda c: role[c['mesh']][0] == 'diagnostic')
    for c in [c for c in cands if c['mesh'] is None]:
        jl(cpath, dict(cand=c['name'], kind=c['kind'], route=c['route'], t_mm=c['t_mm'], family=c.get('family'),
                       build_ep=ep, build=c['build'], role='build_failed'))
    for c in order:
        rl = role[c['mesh']][0]
        sel_ = rl in ('candidate', 'fallback')
        need_flip, need_h = (True if sel_ else diag_flip), (list(holdouts) if sel_ else [])
        keep = {('holdout', h) for h in need_h}
        hit = evals.get(c['geo_hash']) if c.get('geo_hash') else None
        if hit and (hit[2] or not need_flip) and set(need_h) <= hit[3]:
            rs = copy_rows(hit[1], c, hit[0], keep); per = []
            log('eval', c['name'], 'copied from identical mesh', hit[0])
        else:
            try:
                rs, per = evaluate_candidate(c, obj, ep, need_h, refined=refined, flip=need_flip)
            except Exception as e:  # noqa: BLE001
                err = f'{type(e).__name__}: {e}'[:500]
                log('EVAL FAILED', c['name'], err)
                jl(cpath, dict(cand=c['name'], kind=c['kind'], build_ep=ep, role='eval_failed', error=err,
                               trace=traceback.format_exc()[-1500:]))
                continue
            if c.get('geo_hash'):
                evals[c['geo_hash']] = (c['name'], rs, need_flip, set(need_h))
        bsum = {k: v for k, v in c['build'].items() if k != 'report'}
        for r in rs:
            r['build'] = bsum
            r['selector_role'] = rl
            for x in r.get('inputs', []):
                inputs[x['path']] = dict(kind=x['kind'], sha256=x['sha256'], bytes=x['bytes'])
            jl(cpath, r)
        for p_ in per:
            jl(ppath, p_)
        rows += rs
        for r in rs:
            m = r['metrics']
            log('eval', c['name'], f"ep{r['ep']}", r['role'], rl, 'PASS' if r['pass'] else 'fail',
                [g for g, v in r['gates'].items() if not v], 'rank', r['rank_score'], 'sec', r['sec'],
                json.dumps({k: m.get(k) for k in ('dr_comp', 'dr_viol', 'dr_fsv', 'dr_hole3d', 'align_t_mm', 'conn_share')}))
    sec_eval = time.time() - t_e
    meta['inputs_sha256'] = inputs
    json.dump(jsonable(meta), open(f'{odir}/run_meta.json', 'w'), indent=1, default=str)
    # ---- select: own rows only (eval-like); hold-out view report only
    name_of = {r['mesh']: r['cand'] for r in rows}
    own = [r for r in rows if r['role'] == 'own']
    sel = short_reasons(G.select(own), name_of)
    hv_rows = [r for r in rows if r['role'] in ('own', 'holdout') and r.get('selector_role') in ('candidate', 'fallback')]
    hv = short_reasons(G.select(hv_rows), name_of) if holdouts else None
    pick_h = {}
    if sel['pick_mesh']:
        for r in rows:
            if r['mesh'] == sel['pick_mesh'] and r['role'] == 'holdout':
                pick_h[f"ep{r['ep']}"] = dict(passed=r['pass'], failed=[g for g, v in r['gates'].items() if not v],
                                              rank_score=r['rank_score'])
    ref_rows = [r for r in rows if r['role'] == 'refobs']
    sel_ref = short_reasons(G.select(ref_rows), name_of) if ref_rows else None
    diag_best = None
    dg = [r for r in own if r.get('selector_role') == 'diagnostic' and r.get('pass_ex_flip')]
    if dg:
        b_ = min(dg, key=lambda r: r['rank_score'])
        diag_best = dict(cand=b_['cand'], kind=b_['kind'], rank_score=b_['rank_score'], flip_run=b_.get('flip_run'))
    selection = dict(obj=obj, build_ep=ep, holdouts=holdouts,
                     rule='gates.select v3 over the OWN rows (raw obs) = eval-like; shells / incumbents / tprior / '
                          'off-middle t are diagnostic; hold-out view is report only', **sel,
                     holdout_view=(dict(rule='gates.select v3 over own + holdout rows of the selectable meshes '
                                             '(report only)', pick=hv['pick'], ranking=hv['ranking'],
                                        reasons=hv['reasons'], pick_own_on_holdouts=pick_h,
                                        agrees_with_pick=(hv['pick'] == sel['pick'])) if hv else None),
                     best_diagnostic_passing_ex_flip=diag_best,
                     pick_refobs_report_only=sel_ref['pick'] if sel_ref else None,
                     n_candidates=len(cands), n_built=sum(c['mesh'] is not None for c in cands),
                     build_failed={c['name']: c['build'].get('error') for c in cands if c['mesh'] is None},
                     n_identical_copies=sum(1 for c in cands if c.get('dup_of')), part_memo=memo_stats,
                     sec_build=round(sec_build, 1), sec_eval=round(sec_eval, 1))
    # ---- summary table (GT-free metrics only)
    with open(f'{odir}/summary.tsv', 'w') as f:
        f.write('\t'.join(['cand', 'kind', 'selector_role', 'family', 't_mm', 'ep', 'role', 'pass', 'pass_ex_flip',
                           'flip_run', 'failed', 'rank_score', *SUM_KEYS, 'dup_of', 'build_sec', 'eval_sec']) + '\n')
        for r in rows:
            m = r['metrics']
            f.write('\t'.join(str(x) for x in [r['cand'], r['kind'], r.get('selector_role'), r.get('family'), r['t_mm'],
                                                r['ep'], r['role'], r['pass'], r.get('pass_ex_flip'), r.get('flip_run'),
                                                ','.join(g for g, v in r['gates'].items() if not v), r['rank_score'],
                                                *[m.get(k) for k in SUM_KEYS], r.get('dup_of'), r['build'].get('sec'),
                                                r['sec']]) + '\n')
    # ---- render the pick next to a crop (as built and as the scorer decodes it), with library_v3
    if render and sel['pick_mesh']:
        try:
            bp = f'{odir}/pick_b4096.glb'
            G.load_budget(sel['pick_mesh']).export(bp)
            ms, labs = [sel['pick_mesh'], bp], [f"pick {sel['pick']}", 'pick, kit decode']
            if hv and hv['pick'] != sel['pick'] and hv['pick_mesh']:
                ms.append(hv['pick_mesh']); labs.append(f"hold-out view {hv['pick']}")
            best_prog = next((name_of.get(mm) for mm in sel['ranking'] if mm != sel['pick_mesh']
                              and sel['reasons'].get(name_of.get(mm), {}).get('role') == 'candidate'), None)
            if sel['pick'] == 'library_v3':
                fam25 = sorted((r for r in own if r.get('selector_role') == 'candidate'), key=lambda r: r['rank_score'])
                if fam25:
                    ms.append(fam25[0]['mesh']); labs.append(f"best program {fam25[0]['cand']} ({'pass' if fam25[0]['pass'] else 'FAIL'})")
            else:
                ms.append(G.lib_path(obj)); labs.append('library_v3')
            selection['render'] = render_pick(obj, ep, holdouts, ms, labs, f'{odir}/qa_pick.jpg')
            selection['render']['best_other_eligible'] = best_prog
        except Exception as e:  # noqa: BLE001
            selection['render'] = dict(error=f'{type(e).__name__}: {e}'[:300])
            log('RENDER FAILED', selection['render']['error'])
    selection['sec_total'] = round(time.time() - t_all, 1)
    json.dump(jsonable(selection), open(f'{odir}/selection.json', 'w'), indent=1, default=str)
    log('PICK', sel['pick'], '| hold-out view', hv['pick'] if hv else None, '| sec', selection['sec_total'])
    return selection


# ---------------------------------------------------------------------------------------- strace audit
LIB_PREFIXES = ('/usr/lib/', '/usr/local/lib/', '/usr/share/', f'{S}/venv/', '/proc/', '/sys/', '/dev/')


def audit(logs, quiet=False):
    """Count open / openat / openat2 / execve calls on paths that match the GT patterns of io_gt.FORBIDDEN
    (case-insensitive). Reports the raw count over every path, the count after excluding system / venv library files
    (e.g. json/scanner.py matches '/scan'), and the successful ones among those. /etc/ is NOT excluded."""
    out = []
    for lg in logs:
        n_open = 0; raw_hits, data_hits, ok_hits = [], [], []
        opened = set()
        for line in open(lg, errors='replace'):
            mm = re.search(r'(?:open(?:at2?)?|execve)\(.*?"([^"]*)"', line)
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
        r = dict(log=lg, open_calls=n_open, forbidden_pattern_any=len(raw_hits),
                 forbidden_pattern_any_examples=sorted(set(raw_hits))[:8], forbidden_non_library=len(data_hits),
                 forbidden_non_library_ok=len(ok_hits), forbidden_non_library_paths=sorted(set(data_hits))[:20],
                 data_files_opened=len(data_files), data_dirs=sorted({os.path.dirname(p) for p in data_files}))
        out.append(r)
        if not quiet:
            print(json.dumps(r))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('obj'); r.add_argument('ep', type=int)
    r.add_argument('--holdout', default=None, help=f'comma list of hold-out episodes (default: the next {N_HOLDOUT} '
                                                   'public episodes of the object; "" = none)')
    r.add_argument('--out', default=OUT_ROOT); r.add_argument('--ts', default=','.join(str(t) for t in T_MM))
    r.add_argument('--reuse', action='store_true'); r.add_argument('--no-render', action='store_true')
    r.add_argument('--refined', action='store_true', help='also refine.py-copy rows / shells (report only)')
    r.add_argument('--no-shells', action='store_true', help='skip the route-A diagnostic shells')
    r.add_argument('--no-tprior', action='store_true', help='skip the t-prior program variants (diagnostic)')
    r.add_argument('--no-balls-none', action='store_true', help="skip the ball mode 'none' families")
    r.add_argument('--no-patch', action='store_true', help='skip the shell_patch families')
    r.add_argument('--diag-flip', action='store_true', help='run the flip check on diagnostic rows too')
    r.add_argument('--no-memo', action='store_true', help='fit every part afresh (no part memo)')
    r.add_argument('--main-variant', action='store_true', help='post hoc: add <shell>+main (G_CONN-consistent islands)')
    a_ = sub.add_parser('audit'); a_.add_argument('logs', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'audit':
        audit(a.logs); return
    hold = holdouts_of(a.obj, a.ep) if a.holdout is None else [int(x) for x in a.holdout.split(',') if x]
    ts = tuple(float(x) for x in a.ts.split(','))
    run(a.obj, a.ep, hold, a.out, ts=ts, reuse=a.reuse, render=not a.no_render, refined=a.refined,
        main_variant=a.main_variant, shells=not a.no_shells, tprior=not a.no_tprior, balls_none=not a.no_balls_none,
        patch=not a.no_patch, diag_flip=a.diag_flip, memo=not a.no_memo)


if __name__ == '__main__':
    main()
