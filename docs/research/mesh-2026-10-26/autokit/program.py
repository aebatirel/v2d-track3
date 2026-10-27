#!/usr/bin/env python
"""Part-program runner of the autokit DSL: a JSON program names the parts, how the observed points are assigned to
them, how they attach, and which unseen-thickness prior t (generic grid T_GRID) is used; run_program fits every part
in order (parts.py), unions the solids with manifold3d and reports per-part residuals, free parameters and bound hits.

GT-free by construction: the only inputs are one episode's observed points (autokit.io_gt.load_obs: pts, cam, frame,
vote grids, obs_points arguments), optionally our own library mesh (tsdf_patch) and the prior t. No scan, *_align
file, mocap or parquet pose is read; there are no object names or per-object constants here (programs are the
per-object part; object names appear only in the CLI arguments that locate the observation file).
The DSL is documented in DSL.md; example programs are in programs/.

Usage (library):
    from autokit.program import run_program, load_program, validate_program
    from autokit.io_gt import load_obs, obs_path
    mesh, report = run_program(load_program('programs/lathe_bar_balls.json'), load_obs(obs_path(OBJ, EP)), t=0.0025)
CLI:
    program.py PROGRAM.json OBJ EP OUT.glb [--t 0.0025] [--refined 0] [--obs PATH] [--lib LIB.glb]
    (writes OUT.glb and OUT.json, the report)
"""
import argparse, json, math, os, sys, time

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
from autokit import parts as PT                          # noqa: E402
from autokit.io_gt import load_obs, obs_path             # noqa: E402
import manifold3d as mf                                  # noqa: E402

T_GRID = (0.0015, 0.0025, 0.004)    # generic unseen-thickness grid (m); never a scan-measured value
CL_VOX = 0.003                      # cluster connectivity voxel of the assignment rules (sensor scale, m)
RULES = ('all', 'residual', 'largest_cluster_beyond', 'largest_cluster_extent', 'clusters_dir', 'slab', 'cavity')


def load_program(path):
    with open(path) as f:
        return json.load(f)


PART_REFS = ('host', 'above', 'top_from', 'reject_inside')       # params naming an earlier part


def validate_program(program):
    """Static checks before any fitting: unique part names, known part types and assignment rules, every referenced
    part defined EARLIER in the list, the prior on the grid. Returns a list of problems (empty = valid)."""
    errs, seen = [], []
    if not program.get('parts'):
        return ['program has no parts']
    tp = program.get('prior', {}).get('t')
    if tp not in (None, 'arg') and not any(abs(float(tp) - g) < 1e-9 for g in T_GRID):
        errs.append(f'prior t={tp} is not on the grid {T_GRID}')
    for i, sp in enumerate(program['parts']):
        nm = sp.get('name')
        if not nm or nm in seen:
            errs.append(f'part {i}: missing or duplicate name {nm!r}')
        if sp.get('type') not in PT.PART_TYPES:
            errs.append(f'part {nm}: unknown part type {sp.get("type")!r}')
        a = sp.get('assign', {'rule': 'all'})
        if a.get('rule', 'all') not in RULES:
            errs.append(f'part {nm}: unknown assignment rule {a.get("rule")!r}')
        refs = list(a.get('of', [])) if isinstance(a.get('of', []), list) else [a.get('of')]
        refs += [a[k] for k in ('reach_of', 'frame_of', 'host') if k in a]
        p = sp.get('params', {})
        refs += [p[k] for k in PART_REFS if k in p] + list(p.get('of', []))
        at = sp.get('attach')
        refs += [r.get('to') for r in (at if isinstance(at, list) else [at])] if at else []
        for r in refs:
            if r not in seen:
                errs.append(f'part {nm}: refers to {r!r}, which is not an earlier part')
        if sp.get('type') in ('tube_rrect', 'cone_array') or a.get('rule') == 'slab':
            if not program.get('frame'):
                errs.append(f'part {nm}: needs "frame": {{"type": "support"}}')
        seen.append(nm)
    return errs


# ------------------------------------------------------------------------------------------------ assignment
def resid_min(done, names, X):
    """Smallest 'outside distance' of points X over the named parts (a point is explained if any part explains it)."""
    ds = [done[n].resid(X) for n in names if n in done and done[n].resid is not None]
    if not ds:
        return np.full(len(X), np.inf)
    return np.min(ds, axis=0)


def band_of(ctx, a):
    v = a.get('band')
    if v is None:
        return PT.APP_D
    if isinstance(v, dict):
        return float(v['abs']) if 'abs' in v else max(float(v.get('floor', 0.0)), float(v['frac']) * ctx.s)
    return float(v) * ctx.s


def assign(ctx, spec, done):
    """Indices (into ctx.P) of the points a part is fitted to, by its 'assign' rule (DSL.md, section Assignment)."""
    a = spec.get('assign', {'rule': 'all'})
    rule = a.get('rule', 'all')
    N = len(ctx.P)
    if rule not in RULES:
        raise ValueError(f'unknown assignment rule {rule!r}; known: {RULES}')
    if rule == 'all':
        idx = np.arange(N)
    elif rule in ('residual', 'clusters_dir') or rule.startswith('largest_cluster'):
        band = band_of(ctx, a)
        res = resid_min(done, a.get('of', []), ctx.P) > band
        idx = np.nonzero(res)[0]
        if rule == 'clusters_dir':
            # every residual cluster whose centroid lies beyond the host's centre along a direction by > min_offset*s
            # (dir: '+axis' / '-axis' = the host's axis d, '+up' / '-up' / '+x' / '-x' / '+y' / '-y' = support frame)
            host = done[a.get('host', a['of'][0])]
            dname = a.get('dir', '+axis')
            sign = -1.0 if dname.startswith('-') else 1.0
            key = dname.lstrip('+-')
            if key == 'axis':
                u, c0 = host.geo['d'], host.geo['c']
            else:
                fr = ctx.frame
                u = dict(up=fr['up'], x=fr['L'], y=fr['w'])[key]
                c0 = host.geo['c'] if 'c' in host.geo else ctx.c0
            cl = PT.PL.clusters(ctx.P[idx], vox=float(a.get('cluster_vox', CL_VOX)), min_pts=int(a.get('min_pts', 60)))
            keep = [q for q in cl if sign * ((ctx.P[idx[q]].mean(0) - c0) @ u) > float(a.get('min_offset', 0.0)) * ctx.s]
            idx = idx[np.concatenate(keep)] if keep else np.zeros(0, int)
        elif rule != 'residual':
            cl = PT.PL.clusters(ctx.P[idx], vox=float(a.get('cluster_vox', CL_VOX)), min_pts=int(a.get('min_pts', 200)))
            pick = None
            for q in cl:                                     # largest first
                X = ctx.P[idx[q]]
                if rule == 'largest_cluster_beyond':
                    host = done[a.get('reach_of', a['of'][0])]
                    if np.percentile(host.reach(X), 99) > float(a.get('k', 0.5)) * ctx.s:
                        pick = q; break
                else:
                    host = done.get(a.get('frame_of', a['of'][0] if a.get('of') else None))
                    if host is not None and 'e1' in host.geo:
                        Y = X - host.geo['c']
                        ext = max(np.ptp(Y @ host.geo['e1']), np.ptp(Y @ host.geo['e2']))
                    else:
                        Y = X - X.mean(0); ext = float(np.ptp(Y @ np.linalg.eigh(np.cov(Y.T))[1][:, -1]))
                    if ext > float(a.get('min_extent', 0.5)) * ctx.s:
                        pick = q; break
            idx = idx[pick] if pick is not None else np.zeros(0, int)
    elif rule == 'slab':
        fr = ctx.frame
        if fr is None:
            raise RuntimeError('rule slab needs a support frame')
        x, y, h = PT.frame_xyh(ctx.P, fr)
        coord = dict(x=x, y=y, h=h)[a.get('axis', 'x')]
        m = np.ones(N, bool)
        for key, op in (('min_from', np.greater), ('max_from', np.less)):
            if key in a:
                ref = a[key]
                v = dict(tall_lo=fr['tall'][0], tall_hi=fr['tall'][1])[ref] if isinstance(ref, str) else float(ref) * ctx.s
                m &= op(coord, v + float(a.get(key.split('_')[0] + '_margin', 0.0)) * ctx.s)
        idx = np.nonzero(m)[0]
    elif rule == 'cavity':
        host = done[a['of']]
        inset = float(a.get('inset', 0.0)) * ctx.s
        m = host.geo['cavity_mask'](ctx.P, inset)
        if 'beyond_margin' in a:
            x = PT.frame_xyh(ctx.P, host.geo['frame'])[0]
            m &= x > host.geo['x_clip'] + float(a['beyond_margin']) * ctx.s
        idx = np.nonzero(m)[0]
    return idx


# ------------------------------------------------------------------------------------------------ attachment
def attach(ctx, part, spec, done):
    """Attachment rules applied right after a part is fitted (DSL.md, section Attachment)."""
    at = spec.get('attach')
    if not at:
        return
    for rule in (at if isinstance(at, list) else [at]):
        if rule.get('mode') == 'clip_cavity':
            # this tube ends the host tube's cavity: the host's cavity keeps only x beyond this part's outer face
            # (on the side given by 'face', at the host's top height), as the hand kit C trims its basin at the holder face
            host = done[rule['to']]
            q = part.geo['q']; H = host.geo['H_med']
            cx, cy, ex, ey = PT.tube_section(q, part.geo['wall'], H, None)
            side = 1 if rule.get('face', '+x') == '+x' else -1
            host.geo['x_clip'] = float(cx + side * ex)
            PT.tube_build(host)
            part.diag['clip_face_x_mm'] = round(host.geo['x_clip'] * 1e3, 2)
        else:
            raise ValueError(f"unknown attach mode {rule.get('mode')!r}")


# ------------------------------------------------------------------------------------------------ run
def owned_residuals(ctx, done, n=200000):
    """Per-part residuals by ownership: every observed point (subsample of n) belongs to the part whose surface is
    nearest; per part the number of owned points and the median / p90 distance (mm) of those points to it. Also
    the whole model's obs->model median / p90 (all points to the nearest part)."""
    from scipy.spatial import cKDTree
    X = ctx.P
    if len(X) > n:
        X = X[np.random.default_rng(0).choice(len(X), n, replace=False)]
    D, names = [], []
    for name, p in done.items():
        tm = PT.from_mf(p.solid) if p.solid is not None else p.mesh
        if tm is None or len(tm.faces) == 0:
            continue
        S = trimesh.sample.sample_surface(tm, 100000, seed=0)[0]
        D.append(cKDTree(S).query(X)[0]); names.append(name)
    if not D:
        return {}, {}
    D = np.array(D); own = np.argmin(D, 0); dmin = D.min(0)
    per = {}
    for j, name in enumerate(names):
        m = own == j
        per[name] = dict(n_owned=int(m.sum()), med_mm=round(float(np.median(dmin[m])) * 1e3, 3) if m.any() else None,
                         p90_mm=round(float(np.percentile(dmin[m], 90)) * 1e3, 3) if m.any() else None)
    return per, dict(med_mm=round(float(np.median(dmin)) * 1e3, 3), p90_mm=round(float(np.percentile(dmin, 90)) * 1e3, 3))


def run_program(program, obs, t=0.0025, lib=None, verbose=False):
    """Fit a part program to one episode's observed points. program: dict (DSL.md); obs: dict from io_gt.load_obs;
    t: unseen-thickness prior (m, from T_GRID unless the program says 'two_sided' evidence decides); lib: our
    library mesh path for tsdf_patch. Returns (watertight-if-possible trimesh, report dict)."""
    t0 = time.time()
    errs = validate_program(program)
    if errs:
        raise ValueError('invalid program: ' + '; '.join(errs))
    tp = program.get('prior', {}).get('t')
    if tp is not None and tp != 'arg':
        t = float(tp)
    if not any(abs(t - g) < 1e-9 for g in T_GRID):
        raise ValueError(f'prior t={t} is not on the generic grid {T_GRID}')
    ctx = PT.Ctx(obs, t=t, lib=lib, vox=float(program.get('preprocess', {}).get('vox', PT.VOX)))
    report = dict(program=program.get('program'), n_pts=int(len(ctx.P)), s_mm=round(ctx.s * 1e3, 2),
                  t_mm=round(t * 1e3, 2), parts=[])
    if program.get('frame'):
        fs = program['frame']
        if fs.get('type', 'support') != 'support':
            raise ValueError('only frame type "support" is defined')
        ctx.frame = PT.support_frame(ctx, fs)
        report['frame'] = dict(tall_mm=[round(v * 1e3, 1) for v in ctx.frame['tall']] if ctx.frame['tall'] else None)
    done = {}
    for spec in program['parts']:
        ts = time.time()
        typ = spec['type']
        if typ not in PT.PART_TYPES:
            raise ValueError(f'unknown part type {typ!r}; known: {sorted(PT.PART_TYPES)}')
        idx = assign(ctx, spec, done)
        rec = dict(name=spec['name'], type=typ, n_assigned=int(len(idx)))
        if len(idx) == 0 and spec.get('optional', True) and typ not in ('ball', 'tsdf_patch'):
            rec['skipped'] = 'no points assigned'
            report['parts'].append(rec)
            continue
        if typ == 'ball':
            spec = dict(spec); spec['_band'] = band_of(ctx, spec.get('assign', {}))
        try:
            part = PT.PART_TYPES[typ](ctx, idx, spec, done)
        except RuntimeError as e:
            if spec.get('optional', True) and spec.get('name') != program['parts'][0]['name']:
                rec['failed'] = str(e); report['parts'].append(rec)
                continue
            raise
        part.idx = idx
        done[spec['name']] = part
        attach(ctx, part, spec, done)
        report['parts'].append(rec)
        rec.update(k=part.k, params=part.params, bounds_hit=part.bounds_hit, sec=round(time.time() - ts, 1))
        if verbose:
            print(json.dumps(dict(part=spec['name'], n=len(idx), k=part.k, sec=rec['sec'])), flush=True)
    per, tot = owned_residuals(ctx, done)
    for rec in report['parts']:
        part = done.get(rec['name'])
        if part is not None:
            rec['residual'] = per.get(rec['name'])
            rec['diag'] = part.diag
    report['obs_to_model'] = tot
    solids = [p.solid for p in done.values() if p.solid is not None]
    U = PT.mf_union(solids)
    for p in done.values():
        if p.cavity is not None and p.params.get('carve') == 'all':
            U = U - p.cavity
    mesh = PT.from_mf(U)
    patches = [p.mesh for p in done.values() if p.mesh is not None and len(p.mesh.faces)]
    if patches:
        mesh = trimesh.util.concatenate([mesh] + patches)
    report.update(faces=int(len(mesh.faces)), watertight=bool(mesh.is_watertight), bodies=int(mesh.body_count),
                  area_cm2=round(float(mesh.area) * 1e4, 1), k_total=int(sum(p.k for p in done.values())),
                  bounds_hit={n: p.bounds_hit for n, p in done.items() if p.bounds_hit},
                  sec=round(time.time() - t0, 1))
    return mesh, report


def jsonable(o):
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items() if not callable(v)}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('program'); ap.add_argument('obj'); ap.add_argument('ep', type=int); ap.add_argument('out')
    ap.add_argument('--t', type=float, default=0.0025); ap.add_argument('--refined', type=int, default=0)
    ap.add_argument('--obs', default=None, help='explicit observation file (checked by io_gt like any other)')
    ap.add_argument('--lib', default=None)
    a = ap.parse_args()
    path = a.obs or obs_path(a.obj, a.ep, refined=bool(a.refined))
    obs = load_obs(path)
    mesh, rep = run_program(load_program(a.program), obs, t=a.t, lib=a.lib, verbose=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    mesh.export(a.out)
    rep.update(obs=path, out=a.out)
    json.dump(jsonable(rep), open(a.out.rsplit('.', 1)[0] + '.json', 'w'), indent=1, default=float)
    print(json.dumps({k: rep[k] for k in ('program', 'faces', 'watertight', 'bodies', 'area_cm2', 'k_total', 'sec')}))


if __name__ == '__main__':
    main()
