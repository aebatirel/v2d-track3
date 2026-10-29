#!/usr/bin/env python
"""Mesh acceptance metric for Track 3 (v5 round, 2026-10-22).

TWO KINDS OF NUMBERS - keep them apart:
  [D] DIAGNOSTIC (public scans as stand-ins for the hidden scans; never a method input, never a per-object switch):
      cdo_*   kit CD-O (metric_code/track_3/CD-O.py _object_chamfer_cm), cm
      add_*   static registration offset from the kit's AUC.py _register_object_body, mm
      rot_*   symmetry-aware rotation error of that registration, deg; flip = rot > 90 deg
  [M] GT-FREE (mesh alone):
      amb_*   self-ambiguity: the mesh ICP-registered to itself from every non-identity start the kit's
              _align_rigid would try (signed permutations of the PCA axes); smallest residual (symmetric mean
              distance, mm) among starts that stay > 90 deg away (declared kit symmetries excluded).
              Small amb = a flipped copy fits almost as well as the right one = registration-flip risk.

Exactly as the scorer sees it: candidate AND reference go through the kit packer's budget_mesh(4096, 4096)
(the CD-O solution carries 4096 reference vertices per object), seeds are the scorer's own
1_000_003*episode + 101*slot for every eval (episode, slot) of the object in data/track_3_evaluation_objects.json,
plus extra seeds (11,22,33,... ; max(2, 6 - n_eval) of them, so >= 6 seeds per object) for robustness. ADD points = the kit's canonical ADD vertex sample
(v2dlb/vertices.py: 500 vertices of the released scan, seed 0) about the anchor; the anchor is the scan's surface
centroid (_surface_moments) - the host's anchor{i} is not public (for a non-symmetric object and scale 1 the static
error does not depend on the anchor at all).

ADD_static (per seed) = min_S mean_q | d_anchor + (R^T - S) q |, q = ADD points - anchor, S over the declared
symmetry group (identity only for non-symmetric objects). Ideal = 0: our meshes live in the track frame, and the
tracks the variants were fused along were templated in the scan frame. For a mesh in its OWN frame (perc2m tracks)
pass --frame_tf with the known mesh->scan transform (estimated from mocap on public episodes only).

Usage
  mesh_metric.py run  --out RES.jsonl [--workers 2] [--seeds 11,22,...] [--raw] [--manifest M.tsv | label=obj=path ...]
  mesh_metric.py amb  label=obj=path ...            (GT-free ambiguity only; works for the spoon)
  mesh_metric.py table --res RES.jsonl [--md OUT.md]
  mesh_metric.py roster                              (eval pairs, weights, seeds)
Manifest lines: label<TAB>object<TAB>path[<TAB>group[<TAB>base_label]]
"""
import os
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
import sys, json, math, time, hashlib, argparse, importlib.util, itertools
import numpy as np

SCR = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
KIT = f'{SCR}/loc/kit/v2d_submission_kit'
SCANS = f'{SCR}/loc/t3/mesh'
CACHE = f'{SCR}/interact/v5/metric/cache'
EXTRA_SEEDS = (11, 22, 33, 44, 55, 66)
BUDGET = 4096


def _load_kit(name, rel):
    spec = importlib.util.spec_from_file_location(name, f'{KIT}/{rel}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


auc = _load_kit('kit_auc', 'metric_code/track_3/AUC.py')
cdo = _load_kit('kit_cdo', 'metric_code/track_3/CD-O.py')
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh          # noqa: E402  (kit packer)
from v2dlb.vertices import sample_vertices         # noqa: E402  (kit canonical ADD points)


# ----------------------------------------------------------------------------------------------- roster
def roster():
    """{object: [(episode, slot, seed), ...]} from the kit roster; seeds via the scorer's own _object_seed."""
    eps = json.load(open(f'{KIT}/data/track_3_evaluation_objects.json'))['episodes']
    out = {}
    for ep, names in eps.items():
        for slot, name in enumerate(names):
            seed = cdo._object_seed(int(ep), slot)
            assert seed == auc._object_seed(int(ep), slot) == 1_000_003 * int(ep) + 101 * slot
            out.setdefault(name, []).append((int(ep), slot, seed))
    return out


def symmetries():
    t = json.load(open(f'{KIT}/config/tracks.json'))['tracks']['track_3']
    sym = {n: 'axial' for n in t['axially_symmetric_objects']}
    sym.update({n: 'half' for n in t['half_turn_symmetric_objects']})
    return sym


ROSTER = roster()
SYM = symmetries()
N_PAIRS = sum(len(v) for v in ROSTER.values())          # 36


# ----------------------------------------------------------------------------------------------- geometry
def rot_about(axis, angle):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    x, y, z = axis
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * K + (1 - math.cos(angle)) * K @ K


def angle_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def sym_axis(points, kind):
    """GT-free choice of the symmetry axis among the PCA axes: the one the shape is most invariant under
    (90 deg turn for axial, 180 deg for half-turn). Same rule for scans and candidates."""
    if kind is None:
        return None
    from scipy.spatial import cKDTree
    basis = auc._pca_basis(points)
    ang = math.pi / 2 if kind == 'axial' else math.pi
    tree = cKDTree(points)
    best = None
    for k in range(3):
        d = tree.query(points @ rot_about(basis[:, k], ang).T)[0].mean()
        if best is None or d < best[0]:
            best = (d, basis[:, k].copy())
    return best[1]


def sym_rot_err(R, kind, axis):
    """Kit orientation error of a constant body rotation R (AUC.py _symmetry_orientation_errors, static)."""
    if kind is None:
        return angle_deg(R)
    if kind == 'half':
        return min(angle_deg(R), angle_deg(R @ rot_about(axis, math.pi)))
    a = R @ axis
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a, axis)), np.clip(a @ axis, -1, 1)))


def sym_group(kind, axis):
    if kind is None:
        return np.eye(3)[None]
    return auc._axial_rotations(axis, 2 if kind == 'half' else auc._SYMMETRY_ANGLES)


def add_static(da, R, q, group):
    """min_S mean_q |da + R^T q - S q| (AUC.py _symmetry_point_errors for a constant body offset)."""
    moved = q @ R + da                                   # rows: R^T q + da
    best = np.inf
    for S in group:
        best = min(best, float(np.linalg.norm(moved - q @ S.T, axis=1).mean()))
    return best


def icp_from(reference, candidate, start):
    """The kit's _align_rigid inner loop (trimmed ICP) from ONE start rotation."""
    from scipy.spatial import cKDTree
    tree = cKDTree(reference)
    rotation = start.copy()
    translation = reference.mean(axis=0) - rotation @ candidate.mean(axis=0)
    previous = math.inf
    for _ in range(auc._ICP_ITERATIONS):
        moved = candidate @ rotation.T + translation
        distances, indices = tree.query(moved, k=1)
        keep = max(3, int(math.ceil(len(distances) * auc._TRIM_FRACTION)))
        chosen = (np.argpartition(distances, keep - 1)[:keep] if keep < len(distances) else np.arange(len(distances)))
        step_rotation, step_translation = auc._kabsch(moved[chosen], reference[indices[chosen]])
        rotation = step_rotation @ rotation
        translation = step_rotation @ translation + step_translation
        error = float(np.mean(distances[chosen]))
        if math.isfinite(previous) and abs(previous - error) <= 1e-8 * max(previous, 1.0):
            break
        previous = error
    return rotation, translation, auc._symmetric_mean_distance(reference, candidate @ rotation.T + translation)


def ambiguity(v, f, kind):
    """GT-free self-ambiguity [M]. Two independent 3000-point surface samples of the same mesh (kit sampler);
    ICP from each of the kit's non-identity PCA starts; residual of the best start that stays a flip
    (symmetry-aware rotation > 90 deg). Returns mm values and the noise floor (identity residual)."""
    c, r = auc._surface_moments(v, f)
    a = auc._sample_mesh_surface(v, f, 3000, 101) - c
    b = auc._sample_mesh_surface(v, f, 3000, 202) - c
    axis = sym_axis(a, kind)
    floor = auc._symmetric_mean_distance(a, b)
    starts = auc._initial_rotations(a, b, 10 ** 6)[1:]           # all signed-permutation PCA starts, minus identity
    best, best90, best45 = None, math.inf, math.inf
    for R0 in starts:
        R, t, d = icp_from(a, b, R0)
        e = sym_rot_err(R, kind, axis)
        if e > 90 and d < best90:
            best90, best = d, (e, angle_deg(R0))
        if e > 45:
            best45 = min(best45, d)
    return dict(amb_mm=best90 * 1e3, amb45_mm=best45 * 1e3, amb_floor_mm=floor * 1e3, amb_rel=best90 / r,
                amb_rot=None if best is None else round(best[0], 1), radius_mm=r * 1e3, n_starts=len(starts))


# ----------------------------------------------------------------------------------------------- meshes
def sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_candidate(path, raw=False):
    """(vertices, faces) as the scorer decodes them: the kit packer's budget_mesh (weld, simplify, pad)."""
    import trimesh
    if not raw:
        try:
            v, f = budget_mesh(path, BUDGET, BUDGET)
            return np.asarray(v, np.float64), np.asarray(f, np.int64), 'budget'
        except Exception as err:                                   # noqa: BLE001
            print(f'  budget_mesh failed on {path}: {err}; using raw', file=sys.stderr)
    m = trimesh.load(path, force='mesh', process=False)
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64), 'raw'


def mesh_stats(path):
    import trimesh
    m = trimesh.load(path, force='mesh')                           # processed (welded) for topology
    return dict(faces_in=int(len(m.faces)), watertight=bool(m.is_watertight), bodies=int(m.body_count),
                euler=int(m.euler_number), volume_cm3=round(abs(float(m.volume)) * 1e6, 1) if m.is_watertight else None)


def scan_path(name):
    for c in (f'{SCANS}/{name}/{name}_visual.glb', f'{SCANS}/{name}/{name}.glb'):
        if os.path.exists(c):
            return c
    return None


_REF = {}


def reference(name, raw=False):
    """Budgeted public scan (cached npz), anchor, ADD points, symmetry axis. DIAGNOSTIC ONLY."""
    key = (name, raw)
    if key in _REF:
        return _REF[key]
    p = scan_path(name)
    if p is None:
        _REF[key] = None
        return None
    os.makedirs(CACHE, exist_ok=True)
    cp = f'{CACHE}/{name}_{"raw" if raw else "b4096"}.npz'
    if os.path.exists(cp):
        z = np.load(cp)
        v, f = z['v'], z['f']
    else:
        v, f, _ = load_candidate(p, raw=raw)
        np.savez(cp + '.part.npz', v=v, f=f)
        os.replace(cp + '.part.npz', cp)
    anchor, radius = auc._surface_moments(v, f)
    q = sample_vertices(p) - anchor                               # kit canonical ADD points (500, seed 0)
    kind = SYM.get(name)
    axis = sym_axis(auc._sample_mesh_surface(v, f, 3000, 7) - anchor, kind)
    _REF[key] = dict(v=v, f=f, anchor=anchor, radius=radius, q=q, kind=kind, axis=axis, path=p,
                     group=sym_group(kind, axis))
    return _REF[key]


# ----------------------------------------------------------------------------------------------- evaluate
def evaluate(label, name, path, group='', base='', seeds_extra=EXTRA_SEEDS, raw=False, frame_tf=None, do_amb=True,
             ref_raw=False, min_seeds=6, min_extra=2):
    t0 = time.time()
    rec = dict(label=label, object=name, path=path, group=group, base=base, sha=sha(path))
    rec.update(mesh_stats(path))
    v, f, mode = load_candidate(path, raw=raw)
    if frame_tf is not None:                                       # mesh frame -> scan frame (known transform)
        T = np.asarray(frame_tf, float).reshape(4, 4)
        v = v @ T[:3, :3].T + T[:3, 3]
    rec['mesh_mode'] = mode
    rec['faces_scored'] = int((0.5 * np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1) > 0).sum())
    kind = SYM.get(name)
    if do_amb:
        rec.update(ambiguity(v, f, kind))
    ref = reference(name, raw=raw or ref_raw)
    rec['ref_mode'] = 'raw' if (raw or ref_raw) else 'budget'
    pairs = ROSTER.get(name, [])
    rec['eval_pairs'] = len(pairs)
    if ref is None:
        rec['note'] = 'no public scan: GT-free statistics only'
        rec['secs'] = round(time.time() - t0, 1)
        return rec
    n_extra = max(min_extra, min_seeds - len(pairs))
    seeds = [(ep, sl, s) for ep, sl, s in pairs] + [(None, None, s) for s in seeds_extra[:n_extra]]
    rows = []
    cand = (v, f)
    refm = (ref['v'], ref['f'])
    for ep, sl, s in seeds:
        c = float(cdo._object_chamfer_cm(refm, cand, s))
        ca, R = auc._register_object_body(cand, refm, ref['anchor'], s)
        da = ca - ref['anchor']
        add = add_static(da, R, ref['q'], ref['group'])
        err = sym_rot_err(R, ref['kind'], ref['axis'])
        rows.append(dict(ep=ep, slot=sl, seed=s, cdo_cm=round(c, 4), add_mm=round(add * 1e3, 2),
                         anchor_mm=round(float(np.linalg.norm(da)) * 1e3, 2), rot_deg=round(err, 2),
                         rot_raw_deg=round(angle_deg(R), 2), flip=bool(err > 90)))
    ev = [r for r in rows if r['ep'] is not None]
    rec['seeds'] = rows
    rec['cdo_eval'] = float(np.mean([r['cdo_cm'] for r in ev])) if ev else None
    rec['cdo_all'] = float(np.mean([r['cdo_cm'] for r in rows]))
    rec['cdo_sd'] = float(np.std([r['cdo_cm'] for r in rows]))
    rec['add_eval'] = float(np.mean([r['add_mm'] for r in ev])) if ev else None
    rec['add_all'] = float(np.mean([r['add_mm'] for r in rows]))
    rec['add_med'] = float(np.median([r['add_mm'] for r in rows]))
    rec['add_max'] = float(np.max([r['add_mm'] for r in rows]))
    rec['rot_max'] = float(np.max([r['rot_deg'] for r in rows]))
    rec['flips_eval'] = int(sum(r['flip'] for r in ev))
    rec['flips_all'] = int(sum(r['flip'] for r in rows))
    rec['n_seeds'] = len(rows)
    rec['secs'] = round(time.time() - t0, 1)
    return rec


def _work(item):
    try:
        return evaluate(**item)
    except Exception as err:                                       # noqa: BLE001
        return dict(label=item['label'], object=item['name'], path=item['path'], error=repr(err))


def parse_items(args):
    items = []
    if args.manifest:
        for line in open(args.manifest):
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.rstrip('\n').split('\t')
            label, name, path = parts[:3]
            items.append(dict(label=label, name=name, path=path, group=parts[3] if len(parts) > 3 else '',
                              base=parts[4] if len(parts) > 4 else ''))
    for a in args.items:
        label, name, path = a.split('=', 2)
        items.append(dict(label=label, name=name, path=path))
    return items


def cmd_run(args):
    items = parse_items(args)
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            try:
                r = json.loads(line)
                if 'error' not in r:
                    done.add((r['label'], r['sha']))
            except json.JSONDecodeError:
                pass
    todo = []
    for it in items:
        if (it['label'], sha(it['path'])) in done:
            continue
        it.update(seeds_extra=tuple(int(s) for s in args.seeds.split(',')), raw=args.raw, ref_raw=args.ref_raw,
                  frame_tf=json.loads(args.frame_tf) if args.frame_tf else None)
        todo.append(it)
    print(f'{len(items)} items, {len(items) - len(todo)} already done, {len(todo)} to run, workers {args.workers}', flush=True)
    for name in sorted({it['name'] for it in todo}):               # warm the scan cache before forking
        reference(name, raw=args.raw or args.ref_raw)
    if args.workers > 1:
        import multiprocessing as mp
        pool = mp.get_context('fork').Pool(args.workers)
        it = pool.imap_unordered(_work, todo)
    else:
        it = map(_work, todo)
    with open(args.out, 'a') as fh:
        for i, rec in enumerate(it, 1):
            fh.write(json.dumps(rec) + '\n')
            fh.flush()
            if 'error' in rec:
                print(f'[{i}/{len(todo)}] ERROR {rec["label"]}: {rec["error"]}', flush=True)
            else:
                print(f'[{i}/{len(todo)}] {rec["label"]:60s} cdo_eval {fmt(rec.get("cdo_eval"), 3)} add_eval '
                      f'{fmt(rec.get("add_eval"), 1)} flips {rec.get("flips_all", "-")}/{rec.get("n_seeds", "-")} '
                      f'amb {fmt(rec.get("amb_mm"), 2)} ({rec["secs"]} s)', flush=True)


def cmd_amb(args):
    for a in args.items:
        label, name, path = a.split('=', 2)
        v, f, mode = load_candidate(path, raw=args.raw)
        r = ambiguity(v, f, SYM.get(name))
        print(json.dumps(dict(label=label, object=name, mesh_mode=mode, **{k: (round(x, 3) if isinstance(x, float) else x) for k, x in r.items()})), flush=True)


# ----------------------------------------------------------------------------------------------- table
def fmt(x, n):
    return '-' if x is None else f'{x:.{n}f}'


def load_res(path):
    recs = {}
    for line in open(path):
        r = json.loads(line)
        if 'error' in r:
            continue
        recs[r['label']] = r                                      # last write wins
    return recs


def cmd_table(args):
    recs = load_res(args.res)
    known = [n for n in ROSTER if scan_path(n)]
    w_known = sum(len(ROSTER[n]) for n in known)
    out = []
    P = out.append
    P(f'Eval pairs: {N_PAIRS} total; {w_known} on objects with a public scan; weights ' +
      ', '.join(f'{n} {len(ROSTER[n])}' for n in sorted(ROSTER, key=lambda n: -len(ROSTER[n]))))
    # library sets
    libs = sorted({r['group'] for r in recs.values() if r['group'].startswith('library_')})
    if libs:
        P('\n## Library sets: eval-pair-weighted over the %d known-object pairs [D]\n' % w_known)
        P('| set | CD-O_w (cm, eval seeds) | CD-O_w (all seeds) | ADD_w (mm, eval seeds) | ADD_w (all seeds) | flips eval/all seeds | objects |')
        P('|---|---|---|---|---|---|---|')
        for g in libs:
            rs = [r for r in recs.values() if r['group'] == g and r['object'] in known]
            w = {r['object']: len(ROSTER[r['object']]) for r in rs}
            W = sum(w.values())
            if not W:
                continue
            P(f'| {g} | {sum(w[r["object"]] * r["cdo_eval"] for r in rs) / W:.4f} | '
              f'{sum(w[r["object"]] * r["cdo_all"] for r in rs) / W:.4f} | '
              f'{sum(w[r["object"]] * r["add_eval"] for r in rs) / W:.2f} | '
              f'{sum(w[r["object"]] * r["add_all"] for r in rs) / W:.2f} | '
              f'{sum(r["flips_eval"] for r in rs)}/{sum(r["flips_all"] for r in rs)} | {len(rs)} |')
    # per mesh
    P('\n## Per mesh [D] (scan) + amb [M] (GT-free)\n')
    P('Delta columns: vs base (base_label; default library_v2 of the same object). wD = weight/%d x delta '
      '(contribution to the eval-weighted mean over known-object pairs). Verdict: ACCEPT only if wD_CD-O <= 0 and '
      'wD_ADD <= 0 (eval seeds) and no new flip on any seed.\n' % w_known)
    P('| object (w) | label | faces in/scored | wt/bodies | CD-O eval | CD-O all (sd) | ADD eval | ADD all/max | rot max | flips e/a | amb mm (floor) | base | dCD-O | dADD | verdict |')
    P('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    order = sorted(recs.values(), key=lambda r: (r['object'], r['group'], r['label']))
    for r in order:
        name = r['object']
        w = len(ROSTER.get(name, []))
        bl = r.get('base') or (f'library_v2/{name}' if not r['label'].startswith('library_v2/') else '')
        b = recs.get(bl)
        d1 = d2 = None
        verdict = ''
        if b is not None and r.get('cdo_eval') is not None and b.get('cdo_eval') is not None:
            d1 = r['cdo_eval'] - b['cdo_eval']
            d2 = r['add_eval'] - b['add_eval']
            newflip = r['flips_all'] > b['flips_all']
            verdict = 'ACCEPT' if (d1 <= 0 and d2 <= 0 and not newflip) else (
                'reject' + (' (CD-O)' if d1 > 0 else '') + (' (ADD)' if d2 > 0 else '') + (' (flip)' if newflip else ''))
        P(f'| {name} ({w}) | {r["label"]} | {r["faces_in"]}/{r["faces_scored"]} | {"y" if r["watertight"] else "n"}/{r["bodies"]} | '
          f'{fmt(r.get("cdo_eval"), 3)} | {fmt(r.get("cdo_all"), 3)} ({fmt(r.get("cdo_sd"), 3)}) | {fmt(r.get("add_eval"), 1)} | '
          f'{fmt(r.get("add_all"), 1)}/{fmt(r.get("add_max"), 1)} | {fmt(r.get("rot_max"), 0)} | '
          f'{r.get("flips_eval", "-")}/{r.get("flips_all", "-")} of {r.get("n_seeds", "-")} | {fmt(r.get("amb_mm"), 2)} ({fmt(r.get("amb_floor_mm"), 2)}) | '
          f'{bl if b is not None else "-"} | {fmt(d1, 3)} (w {fmt(None if d1 is None else d1 * w / w_known, 4)}) | '
          f'{fmt(d2, 1)} (w {fmt(None if d2 is None else d2 * w / w_known, 2)}) | {verdict} |')
    text = '\n'.join(out)
    print(text)
    if args.md:
        with open(args.md + '.part', 'w') as fh:
            fh.write(text + '\n')
        os.replace(args.md + '.part', args.md)


def cmd_roster(args):
    for n in sorted(ROSTER, key=lambda n: -len(ROSTER[n])):
        print(f'{n:18s} w={len(ROSTER[n]):2d} sym={SYM.get(n)} scan={"y" if scan_path(n) else "n"} '
              f'pairs(ep,slot,seed)={ROSTER[n]}')
    print('total pairs', N_PAIRS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('run')
    a.add_argument('--out', required=True)
    a.add_argument('--manifest')
    a.add_argument('--workers', type=int, default=1)
    a.add_argument('--seeds', default=','.join(map(str, EXTRA_SEEDS)), help='extra seeds besides the eval seeds')
    a.add_argument('--raw', action='store_true', help='skip the packer budget (candidate and scan)')
    a.add_argument('--ref_raw', action='store_true', help='score against the raw (unbudgeted) scan; candidate still budgeted')
    a.add_argument('--frame_tf', help='JSON 4x4 mesh->scan transform (row-major) for meshes not in the scan frame')
    a.add_argument('items', nargs='*', help='label=object=path')
    b = sub.add_parser('amb')
    b.add_argument('--raw', action='store_true')
    b.add_argument('items', nargs='+')
    c = sub.add_parser('table')
    c.add_argument('--res', required=True)
    c.add_argument('--md')
    sub.add_parser('roster')
    args = ap.parse_args()
    dict(run=cmd_run, amb=cmd_amb, table=cmd_table, roster=cmd_roster)[args.cmd](args)


if __name__ == '__main__':
    main()
