"""Swap submitted object meshes into a built Track 3 pack and check the result (2026-10-31, pack 9a = pack 8 with the
mesh session's C0 meshes; results/submissions/20261031-track3i-candidate/README.md). Rollouts and simulator assets are
NOT touched: only the packed object_mesh_b64 payloads of the named objects change (CD-O board, and the pose boards'
mesh registration).

CAUTION, frames: every pose board registers the submitted mesh to the confidential scan and moves the rollout's body
poses with that registration (kit metric_code/track_3/AUC.py _register_object_body / _convert_object_body). A
replacement must therefore be in the body frame of the mesh the simulator built the body from (library_v3 here;
ops/jobs/submit_pack.sh): a replacement offset by d mm in its own coordinates moves every scored pose by about d mm.
The frame report measures that before anything is uploaded.

Steps:
 1. guards: OUT must not exist; --replace holds <object>.<glb|obj|ply|stl|off> named after roster objects;
    tools/no_oracle.py on the replacement folder, the results and the base meshes (refuses mocap/scan-derived inputs);
 2. copies --results (episode_XXXXXX.{json,parquet}) and --meshes to OUT/results and OUT/meshes;
 3. for every roster episode (kit data/track_3_evaluation_objects.json) that has a named object, writes the replacement
    to OUT/meshes/episode_XXXXXX/<object>.glb: a byte copy when the source is a .glb and no transform is given for it,
    else trimesh.load(force='mesh', process=False) (as the packer's budget_mesh) -> optional 4x4 from --transform
    (JSON {object: 4x4 row-major}; maps replacement coordinates INTO the base mesh's body frame, e.g. C0 -> library_v3)
    -> .glb export (geometry only). md5 before/after of every (episode, object) goes to OUT/swap_manifest.json;
 4. frame report per distinct (object, base file, written file), on the full-resolution files: AABB centre/extent,
    exact area-weighted surface centroid (the kit's _surface_moments, the registration's centre), symmetric surface
    distance (median/p95/max mm; nearest neighbour between dense surface samples, so it overestimates by about the
    reported sample spacing), a point-to-point ICP from identity (the rigid correction aligning the replacement to the
    base), and a kit-registration proxy: the kit's own _register_object_body of the packed (budgeted) replacement onto
    the packed base mesh with the base centroid as anchor, i.e. how far the scorer's body conversion would move if the
    scan were the base mesh (pose shift mm, rotation deg). Rotations about a symmetry axis (blue/beige cup) or a half
    turn (lid) are not pose errors. FLAG (exit 2) when centroid offset > --max-centre-mm, ICP correction > --max-icp-mm
    or > --max-icp-deg, median distance > --max-median-mm, kit proxy shift > --max-icp-mm, or an extent ratio leaves
    [1/(1+tol), 1+tol] (scale or axis permutation). Large offsets mean a frame mismatch, not a better shape;
 5. the kit packer (tools/pack_submission.py; cwd = kit; --python, default this interpreter, with -I) ->
    OUT/track3_submission.parquet and OUT/pack.log;
 6. checks against --base (e.g. pack 8): same row count and row_id order, same columns; every column identical except
    code_commit_url (must equal --code-commit on every row) and object_mesh_b64, which may differ only on the payload
    row (first row) of a swapped (episode, slot); every swapped payload decodes to the kit's budget_mesh of the written
    file (the packed mesh IS the replacement); MESH WARNING lines in pack.log are counted and listed;
 7. the uploader's offline steps (kit submit/v2d_submit.py validate_submission, then cd_o_submission ->
    OUT/track3_submission.cd-o.parquet validated as track_3_mesh; no Kaggle call): the CD-O rows may change only for
    the swapped objects whose payload changed. The real upload re-derives that CD-O file next to the parquet.
Exit 0: checks pass, no flags. 2: checks pass but frame flags or MESH WARNINGs need a human. 1: a hard failure.
Packing only: no ground truth is read (the packer reads row_id from the kit's sample submission plus the roster).
Run it with the packing venv (pandas 3.0.6 / pyarrow 26.0.0 / numpy 2.5.4 / trimesh 5.2.0 / fast_simplification 0.2.0
rebuilds pack 8 byte for byte; pandas 3.1.0 changes only the pandas_version string in the schema metadata):
  PY -I tools/pack_swap_meshes.py --kit KIT --results DIR --meshes DIR --replace DIR [--objects a,b,...]
     [--transform T.json] --base BASE.parquet --code-commit URL -o OUT
"""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUFFIXES = ('.glb', '.obj', '.ply', '.stl', '.off')             # the packer's find_mesh order
MESH_COL, COMMIT_COL = 'object_mesh_b64', 'code_commit_url'
ROW_RE = r'^track_3/e(\d+)/w\d+/f\d+/o(\d+)$'
SYMMETRY = {'blue_cup': 'axial', 'beige_cup': 'axial', 'white_pot_lid': 'half-turn'}   # kit config/tracks.json


def digest(path, algo='md5'):
    h = hashlib.new(algo)
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load_mesh(path):
    import trimesh
    m = trimesh.load(path, force='mesh', process=False)
    return np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64)


def read_transforms(path):
    if not path:
        return {}
    raw = json.load(open(path))
    out = {}
    for name, value in raw.items():
        if name.startswith('_'):
            continue
        T = np.asarray(value.get('matrix') if isinstance(value, dict) else value, dtype=np.float64)
        if T.shape != (4, 4) or not np.allclose(T[3], [0, 0, 0, 1]) or not np.isfinite(T).all():
            raise SystemExit(f'--transform {name}: need a finite 4x4 with last row 0 0 0 1')
        A = T[:3, :3]
        scale = abs(np.linalg.det(A)) ** (1 / 3)
        if np.linalg.det(A) <= 0 or not np.allclose(A.T @ A, scale ** 2 * np.eye(3), atol=1e-6 * max(1, scale ** 2)):
            raise SystemExit(f'--transform {name}: upper 3x3 must be a rotation times a uniform scale (no reflection)')
        out[name] = T
    return out


def write_mesh(src, dst, T):
    import trimesh
    v, f = load_mesh(src)
    mesh = trimesh.Trimesh(v, f, process=False)
    if T is not None:
        mesh.apply_transform(T)
    mesh.export(dst)


def area_sample(v, f, n, rng):
    tri = v[f]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    idx = rng.choice(len(f), n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    pts = (1 - s)[:, None] * tri[idx, 0] + (s * (1 - r2))[:, None] * tri[idx, 1] + (s * r2)[:, None] * tri[idx, 2]
    return pts, float(area.sum())


def kabsch(src, dst):
    cs, cd = src.mean(0), dst.mean(0)
    U, _, Vt = np.linalg.svd((src - cs).T @ (dst - cd))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cd - R @ cs


def angle_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def frame_report(base_path, new_path, seed, kit_seed, args):
    """Base (the mesh being replaced) vs the written replacement, both in their file coordinates (metres)."""
    from scipy.spatial import cKDTree
    from v2dlb.object_mesh import _surface_moments
    from v2dlb.track3_pose import _register_object_body
    from v2dlb.mesh_budget import budget_mesh
    rng = np.random.default_rng(seed)
    (bv, bf), (nv, nf) = load_mesh(base_path), load_mesh(new_path)
    r = {}
    for tag, v in (('base', bv), ('new', nv)):
        lo, hi = v.min(0), v.max(0)
        r[f'{tag}_aabb_centre_mm'] = ((lo + hi) / 2 * 1000).round(2).tolist()
        r[f'{tag}_extent_mm'] = ((hi - lo) * 1000).round(2).tolist()
    bc, br = _surface_moments(bv, bf)
    nc, nr = _surface_moments(nv, nf)
    r['base_centroid_mm'], r['new_centroid_mm'] = (bc * 1000).round(2).tolist(), (nc * 1000).round(2).tolist()
    r['centroid_offset_mm'] = round(float(np.linalg.norm(nc - bc) * 1000), 2)
    r['aabb_centre_offset_mm'] = round(float(np.linalg.norm(
        (np.array(r['new_aabb_centre_mm']) - np.array(r['base_aabb_centre_mm'])))), 2)
    r['rms_radius_ratio'] = round(float(nr / br), 4)
    ratio = np.array(r['new_extent_mm']) / np.maximum(np.array(r['base_extent_mm']), 1e-9)
    r['extent_ratio'] = ratio.round(4).tolist()
    nb, ab = area_sample(bv, bf, args.dense, rng)
    nn, an = area_sample(nv, nf, args.dense, rng)
    qb, qn = nb[:args.query], nn[:args.query]
    tb, tn = cKDTree(nb), cKDTree(nn)
    d = np.concatenate([tn.query(qb)[0], tb.query(qn)[0]]) * 1000
    r['surface_mm'] = {'median': round(float(np.median(d)), 3), 'p95': round(float(np.percentile(d, 95)), 3),
                       'max': round(float(d.max()), 3), 'mean': round(float(d.mean()), 3)}
    r['sample_spacing_mm'] = round(float(math.sqrt(max(ab, an) / args.dense) * 1000), 3)
    # ICP from identity (point-to-point, trimmed 90 %): the rigid correction replacement -> base.
    R, t, src = np.eye(3), np.zeros(3), qn.copy()
    for _ in range(60):
        moved = src @ R.T + t
        dist, idx = tb.query(moved)
        keep = dist <= np.percentile(dist, 90)
        dR, dt = kabsch(moved[keep], nb[idx[keep]])
        R, t = dR @ R, dR @ t + dt
        if angle_deg(dR) < 1e-4 and np.linalg.norm(dt) < 1e-7:
            break
    r['icp_centroid_shift_mm'] = round(float(np.linalg.norm(R @ nc + t - nc) * 1000), 2)
    r['icp_rotation_deg'] = round(angle_deg(R), 3)
    after = tb.query(qn @ R.T + t)[0] * 1000
    r['icp_median_after_mm'] = round(float(np.median(after)), 3)
    r['icp_suggested_T_new_to_base'] = np.vstack([np.hstack([R, t[:, None]]), [0, 0, 0, 1]]).round(8).tolist()
    # Kit-registration proxy on the packed (budgeted) meshes: the base stands in for the scan.
    cand, ref = budget_mesh(new_path, 4096, 4096), budget_mesh(base_path, 4096, 4096)
    anchor = _surface_moments(*ref)[0]
    kanchor, krot = _register_object_body(cand, ref, anchor, kit_seed)
    r['kit_proxy_pose_shift_mm'] = round(float(np.linalg.norm(kanchor - anchor) * 1000), 2)
    r['kit_proxy_rotation_deg'] = round(angle_deg(krot), 3)
    flags = []
    if r['centroid_offset_mm'] > args.max_centre_mm:
        flags.append(f"surface centroid moved {r['centroid_offset_mm']} mm > {args.max_centre_mm}")
    if r['icp_centroid_shift_mm'] > args.max_icp_mm or r['icp_rotation_deg'] > args.max_icp_deg:
        flags.append(f"ICP corrects {r['icp_centroid_shift_mm']} mm / {r['icp_rotation_deg']} deg "
                     f"(limits {args.max_icp_mm} mm / {args.max_icp_deg} deg)")
    if r['surface_mm']['median'] > args.max_median_mm:
        flags.append(f"median surface distance {r['surface_mm']['median']} mm > {args.max_median_mm}")
    if r['kit_proxy_pose_shift_mm'] > args.max_icp_mm:
        flags.append(f"kit-registration proxy moves the body {r['kit_proxy_pose_shift_mm']} mm > {args.max_icp_mm}")
    if np.any(ratio > 1 + args.extent_tol) or np.any(ratio < 1 / (1 + args.extent_tol)):
        flags.append(f"extent ratio {r['extent_ratio']} outside +-{args.extent_tol:.0%} (scale or axis order?)")
    r['flags'] = flags
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', required=True, help='v2d_submission_kit root (packer, roster, v2dlb)')
    ap.add_argument('--results', required=True, help='built rollouts: episode_XXXXXX.{json,parquet}')
    ap.add_argument('--meshes', required=True, help='base meshes: episode_XXXXXX/<object>.glb (copied, never modified)')
    ap.add_argument('--replace', required=True, help='folder of replacement meshes named <object>.glb')
    ap.add_argument('--objects', help='comma list to swap (each must be in --replace); default: every mesh there')
    ap.add_argument('--transform', help='JSON {object: 4x4} mapping replacement coords into the base body frame')
    ap.add_argument('--base', required=True, help='base packed parquet to check against (e.g. pack 8)')
    ap.add_argument('--code-commit', required=True)
    ap.add_argument('--python', default=sys.executable, help='interpreter for the kit packer')
    ap.add_argument('-o', '--out', required=True, help='new output folder (must not exist)')
    ap.add_argument('--max-centre-mm', type=float, default=5.0)
    ap.add_argument('--max-icp-mm', type=float, default=5.0)
    ap.add_argument('--max-icp-deg', type=float, default=5.0)
    ap.add_argument('--max-median-mm', type=float, default=5.0)
    ap.add_argument('--extent-tol', type=float, default=0.15)
    ap.add_argument('--dense', type=int, default=200_000, help='surface samples per mesh for distances')
    ap.add_argument('--query', type=int, default=20_000, help='query points per side')
    ap.add_argument('--skip-no-oracle', action='store_true', help='tests only')
    args = ap.parse_args()

    kit, out = os.path.abspath(args.kit), os.path.abspath(args.out)
    sys.path.insert(0, kit)
    if os.path.exists(out):
        raise SystemExit(f'error: {out} exists; runs are never overwritten, pick a new folder')
    roster = json.load(open(os.path.join(kit, 'data', 'track_3_evaluation_objects.json')))['episodes']
    known = {o for objs in roster.values() for o in objs}
    files = {}
    for name in sorted(os.listdir(args.replace)):
        stem, suffix = os.path.splitext(name)
        if suffix.lower() in SUFFIXES:
            if stem not in known:
                raise SystemExit(f'error: {name} in --replace is not a roster object ({sorted(known)})')
            if stem in files:
                raise SystemExit(f'error: two replacement files for {stem}')
            files[stem] = os.path.abspath(os.path.join(args.replace, name))
    objects = [o.strip() for o in args.objects.split(',')] if args.objects else sorted(files)
    missing = [o for o in objects if o not in files]
    if missing or not objects:
        raise SystemExit(f'error: no replacement file for {missing or "any object"} in {args.replace}')
    transforms = read_transforms(args.transform)
    stray = sorted(set(transforms) - set(objects))
    if stray:
        raise SystemExit(f'error: --transform names objects that are not swapped: {stray}')
    if not re.match(r'^https://github\.com/[\w.-]+/[\w.-]+/commit/[0-9a-f]{40}$', args.code_commit.strip()):
        raise SystemExit('error: --code-commit must be https://github.com/<owner>/<repo>/commit/<40-hex sha>')
    commit = args.code_commit.strip()

    if not args.skip_no_oracle:
        guard = subprocess.run([sys.executable, '-I', os.path.join(REPO, 'tools', 'no_oracle.py'),
                                os.path.abspath(args.replace), os.path.abspath(args.results),
                                os.path.abspath(args.meshes), *[files[o] for o in objects]],
                               capture_output=True, text=True)
        print(guard.stdout.strip() or guard.stderr.strip())
        if guard.returncode:
            raise SystemExit('error: tools/no_oracle.py refused an input; nothing was built')

    os.makedirs(out)
    shutil.copytree(args.results, os.path.join(out, 'results'))
    shutil.copytree(args.meshes, os.path.join(out, 'meshes'))
    results = {n: digest(os.path.join(out, 'results', n)) for n in sorted(os.listdir(os.path.join(out, 'results')))}
    eps_results = sorted(int(m.group(1)) for n in results for m in [re.match(r'episode_(\d+)\.parquet$', n)] if m)
    if eps_results != sorted(int(e) for e in roster):
        raise SystemExit(f'error: results episodes {eps_results} differ from the roster {sorted(map(int, roster))}')

    pairs, written = [], {}
    for ep in sorted(roster, key=int):
        for slot, obj in enumerate(roster[ep]):
            d = os.path.join(out, 'meshes', f'episode_{int(ep):06d}')
            present = [s for s in SUFFIXES if os.path.exists(os.path.join(d, obj + s))]
            if not present:
                raise SystemExit(f'error: base meshes lack episode {ep} {obj}')
            path = os.path.join(d, obj + present[0])
            entry = {'episode': int(ep), 'slot': slot, 'object': obj, 'file': os.path.relpath(path, out),
                     'md5_before': digest(path), 'swapped': obj in objects}
            if obj in objects:
                if present != ['.glb']:
                    raise SystemExit(f'error: episode {ep} {obj}: base is {present}, expected one .glb')
                entry['base_copy'] = os.path.join(out, 'base_meshes', f'episode_{int(ep):06d}', obj + '.glb')
                os.makedirs(os.path.dirname(entry['base_copy']), exist_ok=True)
                shutil.copy2(path, entry['base_copy'])
                src, T = files[obj], transforms.get(obj)
                if src.lower().endswith('.glb') and T is None:
                    shutil.copyfile(src, path)
                    entry['method'] = 'byte copy'
                else:
                    if obj not in written:
                        tmp = os.path.join(out, 'replacements_written', obj + '.glb')
                        os.makedirs(os.path.dirname(tmp), exist_ok=True)
                        write_mesh(src, tmp, T)
                        written[obj] = tmp
                    shutil.copyfile(written[obj], path)
                    entry['method'] = 'trimesh export' + (' with transform' if T is not None else '')
                entry['source'], entry['source_md5'] = src, digest(src)
            entry['md5_after'] = digest(path)
            pairs.append(entry)
    swapped = [p for p in pairs if p['swapped']]
    lib = os.path.join(REPO, 'meshes', 'library_v3')

    # Frame report: one per distinct (object, base md5, written md5).
    reports, seen = [], {}
    for p in swapped:
        key = (p['object'], p['md5_before'], p['md5_after'])
        if key in seen:
            seen[key]['episodes'].append(p['episode'])
            continue
        libmd5 = digest(os.path.join(lib, p['object'] + '.glb')) if os.path.exists(os.path.join(lib, p['object'] + '.glb')) else None
        rep = {'object': p['object'], 'episodes': [p['episode']], 'base_md5': p['md5_before'],
               'base_is_library_v3': p['md5_before'] == libmd5, 'new_md5': p['md5_after'],
               'symmetry': SYMMETRY.get(p['object'], 'none')}
        rep.update(frame_report(p['base_copy'], os.path.join(out, p['file']), 7,
                                1_000_003 * p['episode'] + 101 * p['slot'], args))
        seen[key] = rep
        reports.append(rep)

    # Pack with the kit's packer, exactly as pack 7/8 were packed.
    parquet = os.path.join(out, 'track3_submission.parquet')
    cmd = [args.python, '-I', 'tools/pack_submission.py', '--track', 'track_3', '--results', os.path.join(out, 'results'),
           '--meshes', os.path.join(out, 'meshes'), '--code-commit', commit,
           '--eval-script', os.path.join(kit, 'flash_chord', 'scripts', 'evaluate_policy.py'), '-o', parquet]
    with open(os.path.join(out, 'pack.log'), 'w') as log:
        rc = subprocess.run(cmd, cwd=kit, stdout=log, stderr=subprocess.STDOUT).returncode
    packlog = open(os.path.join(out, 'pack.log')).read()
    warnings = [l for l in packlog.splitlines() if 'MESH WARNING' in l]
    hard, info = [], []
    if rc or not os.path.exists(parquet):
        hard.append(f'packer exit {rc}: ' + ' | '.join(packlog.strip().splitlines()[-3:]))

    check = {}
    if not hard:
        import pyarrow.parquet as pq
        from v2dlb.track3_pose import _decode_object_mesh
        from v2dlb.mesh_budget import budget_mesh
        ta, tb = pq.read_table(args.base), pq.read_table(parquet)
        a, b = ta.to_pandas(), tb.to_pandas()
        check['rows'] = [len(a), len(b)]
        if len(a) != len(b):
            hard.append(f'row count {len(b)} != base {len(a)}')
        elif not (a.row_id.values == b.row_id.values).all():
            hard.append('row_id order differs from the base')
        if list(a.columns) != list(b.columns) or ta.schema.remove_metadata() != tb.schema.remove_metadata():
            hard.append(f'columns/schema differ: {list(a.columns)} vs {list(b.columns)}')
        if not hard:
            keys = b.row_id.str.extract(ROW_RE).astype(int)
            ep, sl = keys[0].values, keys[1].values
            diff_cols = {}
            for c in b.columns:
                x, y = a[c].values, b[c].values
                if x.dtype.kind == 'f':
                    same = (x == y) | (np.isnan(x) & np.isnan(y))
                else:
                    same = x == y
                if (~same).any():
                    diff_cols[c] = int((~same).sum())
                if c == MESH_COL:
                    mesh_diff = ~same
            check['columns_differing'] = diff_cols
            for c in diff_cols:
                if c not in (MESH_COL, COMMIT_COL):
                    hard.append(f'column {c} differs on {diff_cols[c]} rows (only {MESH_COL} and {COMMIT_COL} may)')
            if not (b[COMMIT_COL] == commit).all():
                hard.append(f'{COMMIT_COL} is not {commit} on every row')
            payload_a = a[MESH_COL].fillna('').str.strip() != ''
            payload_b = b[MESH_COL].fillna('').str.strip() != ''
            if not (payload_a.values == payload_b.values).all():
                hard.append('the rows carrying a mesh payload moved')
            allowed = np.zeros(len(b), bool)
            for p in swapped:
                allowed |= (ep == p['episode']) & (sl == p['slot']) & payload_b.values
            bad = mesh_diff & ~allowed
            if bad.any():
                hard.append(f'{MESH_COL} changed on {int(bad.sum())} rows outside the swapped objects: '
                            + ', '.join(sorted({f'e{e}/o{s}' for e, s in zip(ep[bad], sl[bad])})))
            changed, unchanged = [], []
            budget_cache = {}
            for p in swapped:
                row = np.flatnonzero((ep == p['episode']) & (sl == p['slot']) & payload_b.values)
                if len(row) != 1:
                    hard.append(f"episode {p['episode']} {p['object']}: {len(row)} payload rows")
                    continue
                (changed if mesh_diff[row[0]] else unchanged).append(f"{p['episode']}:{p['object']}")
                v, f = _decode_object_mesh(b[MESH_COL].iloc[row[0]])
                if p['md5_after'] not in budget_cache:
                    budget_cache[p['md5_after']] = budget_mesh(os.path.join(out, p['file']), 4096, 4096)
                ev, ef = budget_cache[p['md5_after']]
                if not (np.array_equal(v, ev) and np.array_equal(f, ef)):
                    hard.append(f"episode {p['episode']} {p['object']}: packed payload is not budget_mesh(written file)")
                p['payload_changed'] = bool(mesh_diff[row[0]])
            check['payload_changed'], check['payload_unchanged'] = changed, unchanged
            for p in swapped:
                if p['md5_after'] != p['md5_before'] and not p.get('payload_changed'):
                    info.append(f"episode {p['episode']} {p['object']}: file changed but packed geometry is identical")
                if p['md5_after'] == p['md5_before'] and p.get('payload_changed'):
                    hard.append(f"episode {p['episode']} {p['object']}: file identical but payload changed")
            ma = json.loads(ta.schema.metadata[b'pandas']).get('pandas_version') if ta.schema.metadata else None
            mb = json.loads(tb.schema.metadata[b'pandas']).get('pandas_version') if tb.schema.metadata else None
            check['pandas_version'] = [ma, mb]
            if ma != mb:
                info.append(f'schema metadata pandas_version {mb} vs base {ma} (metadata only; table content compared)')
        # The uploader's own offline steps (kit submit/v2d_submit.py main, no network): validate_submission, then the
        # CD-O file it derives and uploads to the sixth board, compared with the one derived from the base.
        try:
            import importlib.util
            from pathlib import Path
            spec = importlib.util.spec_from_file_location('v2d_submit_offline', os.path.join(kit, 'submit', 'v2d_submit.py'))
            sub = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sub)
            from v2dlb.track3_pose import cd_o_submission
            import pandas as pd
            config = json.load(open(os.path.join(kit, 'config', 'tracks.json')))
            frame = sub.validate_submission(Path(parquet), 'track_3', config)
            sample = pd.read_parquet(os.path.join(kit, 'data', 'track_3_mesh_sample_submission.parquet'))
            cdo = cd_o_submission(frame, sample, roster)
            cdo_path = os.path.join(out, 'track3_submission.cd-o.parquet')
            cdo.to_parquet(cdo_path, index=False)
            sub.validate_submission(Path(cdo_path), 'track_3_mesh', config)
            cdo_base = cd_o_submission(pd.read_parquet(args.base), sample, roster)
            k = cdo.row_id.str.extract(r'^t3m_(\d+)_(.+)_[01]_\d+$')
            dif = (cdo[['x', 'y', 'z']].values != cdo_base[['x', 'y', 'z']].values).any(axis=1)
            cdo_changed = sorted({f'{int(e)}:{n}' for e, n in zip(k[0][dif], k[1][dif])}, key=lambda s: (int(s.split(':')[0]), s))
            check['uploader_validation'] = 'pass (offline validate_submission; CD-O file derived and validated)'
            check['cd_o_file'] = {'path': cdo_path, 'rows': len(cdo), 'sha256': digest(cdo_path, 'sha256'),
                                  'pairs_changed_vs_base': cdo_changed}
            expected = sorted(check.get('payload_changed', []), key=lambda s: (int(s.split(':')[0]), s))
            if cdo_changed != expected:
                hard.append(f'CD-O rows changed for {cdo_changed}, expected exactly the changed payloads {expected}')
        except SystemExit as error:
            hard.append(f'uploader offline validation failed: {error}')
        check['sha256'] = digest(parquet, 'sha256')
        check['base_sha256'] = digest(args.base, 'sha256')
        check['bytes'] = os.path.getsize(parquet)
        check['byte_identical_to_base'] = check['sha256'] == check['base_sha256']
    check['mesh_warnings'] = warnings
    frame_flags = [f"{r['object']} (episodes {r['episodes']}): {f}" for r in reports for f in r['flags']]
    status = 1 if hard else (2 if frame_flags or warnings else 0)

    import importlib.metadata as md
    versions = {}
    for pkg in ('pandas', 'pyarrow', 'numpy', 'scipy', 'trimesh', 'fast_simplification'):
        try:
            versions[pkg] = md.version(pkg)
        except Exception:
            versions[pkg] = None
    manifest = {'tool': 'tools/pack_swap_meshes.py', 'argv': sys.argv, 'python': sys.version.split()[0],
                'versions': versions, 'kit': kit, 'results': os.path.abspath(args.results),
                'meshes': os.path.abspath(args.meshes), 'replace': os.path.abspath(args.replace),
                'replacement_files': {o: {'path': files[o], 'md5': digest(files[o])} for o in objects},
                'transforms': {o: T.tolist() for o, T in transforms.items()}, 'base': os.path.abspath(args.base),
                'code_commit': commit, 'packer_command': cmd, 'packer_cwd': kit, 'results_md5': results,
                'pairs': [{k: v for k, v in p.items() if k != 'base_copy'} for p in pairs],
                'frame_report': reports, 'check': check, 'hard_failures': hard, 'frame_flags': frame_flags,
                'info': info, 'status': status}
    json.dump(manifest, open(os.path.join(out, 'swap_manifest.json'), 'w'), indent=1)

    moved = [f"{p['episode']}:{p['object']} {p['md5_before'][:8]}->{p['md5_after'][:8]}"
             for p in swapped if p['md5_before'] != p['md5_after']]
    lines = [f'pack_swap_meshes: {out}',
             f"swapped {len(swapped)} (episode, object) pairs of {len(pairs)}: "
             + ', '.join(f"{o} -> eps {[p['episode'] for p in swapped if p['object'] == o]}" for o in objects),
             'file md5 changed: ' + (', '.join(moved) if moved else 'none (byte-identical files)'),
             'frame report (mm; base = the mesh being replaced):']
    for r in reports:
        lines.append(f"  {r['object']:18s} eps {r['episodes']} base {'library_v3' if r['base_is_library_v3'] else r['base_md5'][:8]}"
                     f" | centroid offset {r['centroid_offset_mm']} | AABB centre offset {r['aabb_centre_offset_mm']}"
                     f" | extent base {r['base_extent_mm']} new {r['new_extent_mm']}"
                     f" | surface median/p95/max {r['surface_mm']['median']}/{r['surface_mm']['p95']}/{r['surface_mm']['max']}"
                     f" (spacing {r['sample_spacing_mm']}) | ICP {r['icp_centroid_shift_mm']} mm {r['icp_rotation_deg']} deg"
                     f" (median after {r['icp_median_after_mm']}) | kit proxy {r['kit_proxy_pose_shift_mm']} mm"
                     f" {r['kit_proxy_rotation_deg']} deg (symmetry {r['symmetry']}) | "
                     + ('FLAG: ' + '; '.join(r['flags']) if r['flags'] else 'ok'))
    if check:
        lines.append(f"parquet: {check.get('bytes')} B sha256 {check.get('sha256')} | byte-identical to base: "
                     f"{check.get('byte_identical_to_base')} | rows {check.get('rows')} | columns differing from base: "
                     f"{check.get('columns_differing')}")
        lines.append(f"mesh payloads changed: {check.get('payload_changed')} | unchanged: {check.get('payload_unchanged')}")
        if 'cd_o_file' in check:
            c = check['cd_o_file']
            lines.append(f"uploader offline validation: {check['uploader_validation']} | CD-O file {c['rows']} rows "
                         f"sha256 {c['sha256'][:16]}... | CD-O pairs changed vs base: {c['pairs_changed_vs_base']}")
    lines.append(f'pack.log MESH WARNINGs: {len(warnings)}' + ''.join('\n  ' + w for w in warnings))
    lines += ['info: ' + i for i in info] + ['HARD FAIL: ' + h for h in hard] + ['FLAG: ' + f for f in frame_flags]
    lines.append(f"STATUS {['OK', 'HARD FAIL', 'NEEDS REVIEW (flags)'][status]} (exit {status})")
    text = '\n'.join(lines)
    open(os.path.join(out, 'summary.txt'), 'w').write(text + '\n')
    print(text)
    return status


if __name__ == '__main__':
    sys.exit(main())
