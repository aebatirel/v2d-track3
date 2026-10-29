#!/usr/bin/env python
"""Validation of the part DSL (parts.py + program.py) on real observed points, GT-free.

1. Reproduction [M]: the example programs in programs/ must reproduce the hand-kit incumbents on the episodes they
   were developed on - white_pot ep41 (lathe + bar plate + balls), white_pot_lid ep2 (sheet + strap + balls),
   plastic_dish_rack ep13 single episode (tube_rrect tray + tube_rrect holder + cone_array + balls), blue_cup ep21
   (lathe 'height' + splat). Compared with the incumbent mesh: median symmetric mesh-to-mesh distance and the
   GT-free obs_fidelity (obs_fidelity.py's algorithm: trimmed means obs->mesh and mesh->obs, on the episode's own
   points). Pass: fidelity sum within 5 % of the incumbent's (or lower) and median symmetric distance <= 1 mm (the
   stereo noise floor of our points; [D] 0.85-1.9 mm median point-to-surface).
2. Scale test [M]: the cup program on points scaled by 1.3 about the frame origin; 'windows' mode scales the sensor
   voxel too (same point sample), so the output scaled back must match the unscaled output (all windows relative);
   'physical' mode keeps the 1.5 mm voxel (denser sample of a larger object) and is reported only.
3. Thickness grid [M]: the lid program at t = 1.5 / 2.5 / 4.0 mm against the clean-up round's lid meshes.
4. DSL checks: program validation, unknown part / rule, t off the grid -> ValueError; integrity grep (no object
   names or ground-truth path literals in the method code); smoke runs of the parts and rules the reproductions do
   not use (plate_set, rounded_box, tsdf_patch, plate occupancy, clusters_dir + splat union, strap without host,
   lathe open floor).
5. Cross-episode [M]: each example program unchanged on the object's other public episodes (cross_*).
6. scale_all [M]: windows-mode scale test of the lid, pot and rack programs (balls removed, bands relative).
7. Stage 1b (s1b_<case>) [M]: each example program on its development episode over the matrix
   {base, tprior (t_src = prior) variant} x t in {1.5, 2.5, 4.0} mm x balls {free, none} x shell_patch {no, yes},
   plus a 'legacy cells' run (lathe cell_min_pts = 8, the stage-1 rule) at t = 2.5. Compared GT-free with the
   stage-1 DSL mesh (scratchpad/auto/stage1/parts-dsl/final): obs fidelity on the episode's own points (raw mesh and
   as the kit decodes it), symmetric mesh-to-mesh distance, ball count / radii / stems, patch size, kit decode
   (budget_mesh 4096) area change / watertight / weld-only. Rows with a shell_patch run in budget mode
   (run_program budget=BUDGET=4000: patch within its share, solid union decimated, so the decode only welds).
8. schema / pan (in dsl): every window the code reads is declared; DSL.md's generated block equals the schema; unknown
   keys rejected; plate_set plane segmentation and keep_holes on the dust pan (ep39); shell_patch smoke.
No scan, *_align file, mocap or parquet pose is opened; obs files go through autokit.io_gt.load_obs, meshes through
the io_gt guard (parts.load_mesh_guarded).
Usage: test_programs.py [--out DIR] [--only lid,pot,cup,rack,scale,scale_all,grid,dsl,cross_pot,cross_lid,
       cross_cup,cross_rack,s1b_lid,s1b_cup,s1b_pot,s1b_rack] [--reuse 1]
"""
import argparse, json, os, re, subprocess, sys, time

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit.io_gt import load_obs, obs_path, SCRATCH      # noqa: E402
from autokit.program import run_program, load_program, jsonable, variants, T_GRID   # noqa: E402
from autokit import parts as PT                             # noqa: E402

OUT = f'{SCRATCH}/auto/stage1b/parts'
BUDGET = 4000                                               # shipped face budget of A-inside-B (patch) rows
STAGE1 = f'{SCRATCH}/auto/stage1/parts-dsl/final'          # stage-1 DSL meshes (reference for stage 1b)
KIT = f'{SCRATCH}/kit/v2d_submission_kit'
INC = '/home/user/v2d-track3/docs/research/mesh-2026-10-26/results/prim/meshes'
LIB = '/home/user/v2d-track3/meshes/library_v3'
# driver input list: object names appear only here (and in the incumbents' file names)
CASES = {
    'lid': dict(obj='white_pot_lid', ep=2, program='sheet_strap_balls.json', inc=f'{INC}/white_pot_lid_ep2_fit_v2.glb'),
    'pot': dict(obj='white_pot', ep=41, program='lathe_bar_balls.json', inc=f'{INC}/white_pot_ep41_fit.glb'),
    'cup': dict(obj='blue_cup', ep=21, program='lathe_splat.json', inc=f'{SCRATCH}/lathe/ep21_blue_cup_g1.glb',
                obs=f'{SCRATCH}/obs/ep21_blue_cup.npz'),
    'rack': dict(obj='plastic_dish_rack', ep=13, program='tray_holder_pegs_balls.json',
                 inc=f'{SCRATCH}/prim/clean/rack/t2.5_lean1/plastic_dish_rack/ep13_full.glb'),
}
OBJECT_NAMES = ('white_pot', 'pot_lid', 'blue_cup', 'beige_cup', 'dish_rack', 'water_pitcher', 'dust_pan', 'sweeper',
                'wooden_piece', r'\bpots?\b', r'\blids?\b', r'\bcups?\b', r'\bracks?\b', r'\bpitchers?\b',
                r'\bboards?\b', r'\bmugs?\b')    # part words (handle, peg, tray, holder) are generic, not names


def fidelity(P, mesh, trim=0.9, n_obs=300000, n_s=200000):
    """obs_fidelity.py's measure (GT-free): trimmed mean obs->mesh and mesh->obs (mesh samples inside the
    observations' bounding box), mm."""
    P = P[np.random.default_rng(0).choice(len(P), min(n_obs, len(P)), replace=False)]
    S = trimesh.sample.sample_surface(mesh, n_s, seed=0)[0]
    lo, hi = P.min(0), P.max(0)

    def tmean(d):
        d = np.sort(d); return float(d[:int(trim * len(d))].mean() * 1e3)
    om = tmean(cKDTree(S).query(P)[0])
    inb = np.all((S > lo) & (S < hi), axis=1)
    mo = tmean(cKDTree(P).query(S[inb])[0])
    return dict(obs_to_mesh_mm=round(om, 3), mesh_to_obs_mm=round(mo, 3), sum_mm=round(om + mo, 3))


def area_rms(m):
    A = m.area_faces; c = m.triangles_center
    cen = (A[:, None] * c).sum(0) / A.sum()
    return float(m.area), float(np.sqrt((A * ((c - cen) ** 2).sum(1)).sum() / A.sum()))


def mesh_dist(a, b, n=20000):
    """Symmetric mesh-to-mesh distances (mm): n surface samples of each mesh, exact closest-point distance to the
    other mesh's surface; medians of a->b and b->a, median and p90 of both pooled."""
    Sa = trimesh.sample.sample_surface(a, n, seed=1)[0]; Sb = trimesh.sample.sample_surface(b, n, seed=2)[0]
    dab = trimesh.proximity.closest_point(b, Sa)[1]; dba = trimesh.proximity.closest_point(a, Sb)[1]
    both = np.r_[dab, dba]
    return dict(a_to_b_med_mm=round(float(np.median(dab)) * 1e3, 3), b_to_a_med_mm=round(float(np.median(dba)) * 1e3, 3),
                sym_med_mm=round(float(np.median(both)) * 1e3, 3), sym_p90_mm=round(float(np.percentile(both, 90)) * 1e3, 3),
                sym_mean_mm=round(float(np.mean(both)) * 1e3, 3))


def load_ref(path):
    return PT.load_mesh_guarded(path)


def budget_check(mesh, tmp, return_mesh=False):
    """The mesh as the scorer decodes it (kit budget_mesh to 4096 faces / vertices): area change, watertight,
    bodies, non-degenerate faces, and whether budget_mesh only welded (input already within 4096 faces and
    vertices after welding). return_mesh: also the decoded trimesh."""
    if KIT not in sys.path:
        sys.path.insert(0, KIT)
    from v2dlb.mesh_budget import budget_mesh
    mesh.export(tmp)
    try:
        v, f = budget_mesh(tmp, 4096, 4096)
    except Exception as e:                                # report, do not hide
        return (dict(error=repr(e)[:200]), None) if return_mesh else dict(error=repr(e)[:200])
    d = trimesh.Trimesh(v, f, process=True)
    if hasattr(d, 'nondegenerate_faces'):
        d.update_faces(d.nondegenerate_faces())
    elif hasattr(d, 'remove_degenerate_faces'):
        d.remove_degenerate_faces()
    w = trimesh.Trimesh(mesh.vertices, mesh.faces, process=True)
    r = dict(faces=int(len(d.faces)), area_change=round(float(d.area / mesh.area - 1), 4),
             watertight=bool(d.is_watertight), bodies=int(d.body_count),
             weld_only=bool(len(w.faces) <= 4096 and len(w.vertices) <= 4096))
    return (r, d) if return_mesh else r


def compare(mesh, inc_path, P):
    inc = load_ref(inc_path)
    fd, fi = fidelity(P, mesh), fidelity(P, inc)
    (A1, R1), (A0, R0) = area_rms(mesh), area_rms(inc)
    md = mesh_dist(mesh, inc)
    ratio = fd['sum_mm'] / fi['sum_mm']
    return dict(fid_dsl=fd, fid_inc=fi, fid_ratio=round(ratio, 4), mesh_dist=md,
                area_ratio=round(A1 / A0, 4), rms_radius_ratio=round(R1 / R0, 4),
                faces=[int(len(mesh.faces)), int(len(inc.faces))], watertight=[bool(mesh.is_watertight), bool(inc.is_watertight)],
                bodies=[int(mesh.body_count), int(inc.body_count)],
                pass_fid=bool(ratio <= 1.05), pass_dist=bool(md['sym_med_mm'] <= 1.0))


def run_case(key, out, t=0.0025, reuse=False, tag=''):
    c = CASES[key]
    path = c.get('obs') or obs_path(c['obj'], c['ep'])
    obs = load_obs(path)
    glb = f'{out}/{key}_ep{c["ep"]}{tag}.glb'
    if reuse and os.path.exists(glb) and os.path.exists(glb[:-4] + '.json'):
        mesh = load_ref(glb); rep = json.load(open(glb[:-4] + '.json'))
    else:
        t0 = time.time()
        mesh, rep = run_program(load_program(f'{HERE}/programs/{c["program"]}'), obs, t=t, lib=f'{LIB}/{c["obj"]}.glb')
        rep['wall_sec'] = round(time.time() - t0, 1)
        rep['obs'] = path
        mesh.export(glb)
        json.dump(jsonable(rep), open(glb[:-4] + '.json', 'w'), indent=1, default=float)
    return obs, mesh, rep, glb


def test_reproduce(keys, out, reuse):
    rows = []
    for key in keys:
        obs, mesh, rep, glb = run_case(key, out, reuse=reuse)
        P = np.asarray(obs['pts'], np.float64)
        cmp_ = compare(mesh, CASES[key]['inc'], P)
        row = dict(test='reproduce', case=key, obj=CASES[key]['obj'], ep=CASES[key]['ep'], dsl=glb, inc=CASES[key]['inc'],
                   s_mm=rep['s_mm'], k_total=rep['k_total'], sec=rep.get('wall_sec', rep.get('sec')),
                   parts=[dict(name=p['name'], type=p['type'], n=p['n_assigned'], k=p.get('k'),
                               residual=p.get('residual'), bounds_hit=p.get('bounds_hit'),
                               skipped=p.get('skipped') or p.get('failed')) for p in rep['parts']], **cmp_)
        print(json.dumps(row), flush=True)
        rows.append(row)
    return rows


def test_scale(out, f=1.3):
    """Relative-window check: cup program on points (and camera centres) scaled by f about the frame origin.
    'windows': the sensor voxel is scaled too (preprocess.vox = f x 1.5 mm), so the point sample is the same up to
    scale and every relative window must give the same shape: the output scaled back must match (pass: median
    symmetric distance <= 0.25 mm and |area ratio - 1| <= 1 %). 'physical': the voxel stays 1.5 mm (a larger
    object seen by the same sensor) - reported, not a pass criterion (point density per window changes)."""
    c = CASES['cup']
    obs = load_obs(c['obs'])
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
    m0 = np.zeros(3)          # scale about the frame origin: the voxel lattice scales with the points (same sample)
    prog = load_program(f'{HERE}/programs/{c["program"]}')
    mesh0, rep0 = run_program(prog, dict(pts=P, cam=C, frame=obs['frame']), t=0.0025)
    obs_s = dict(pts=m0 + f * (P - m0), cam=m0 + f * (C - m0), frame=obs['frame'])
    rows = []
    for mode in ('windows', 'physical'):
        pr = dict(prog)
        if mode == 'windows':
            pr['preprocess'] = dict(vox=0.0015 * f)
        mesh1, rep1 = run_program(pr, obs_s, t=0.0025)
        mesh1b = mesh1.copy(); mesh1b.apply_translation(-m0); mesh1b.apply_scale(1 / f); mesh1b.apply_translation(m0)
        mesh1b.export(f'{out}/scale_{mode}_back.glb')
        md = mesh_dist(mesh1b, mesh0)
        b0 = [p for p in rep0['parts'] if p['name'] == 'body'][0]['params']
        b1 = [p for p in rep1['parts'] if p['name'] == 'body'][0]['params']
        ar = mesh1b.area / mesh0.area
        row = dict(test='scale', mode=mode, f=f, s_mm=[rep0['s_mm'], rep1['s_mm']], n_pts=[rep0['n_pts'], rep1['n_pts']],
                   mesh_dist_scaled_back=md, t_mm=[b0['t_mm'], b1['t_mm']], rmax_mm=[b0['rmax_mm'], b1['rmax_mm']],
                   area_ratio_scaled_back=round(ar, 4),
                   splat_n=[[p['params'] for p in r['parts'] if p['name'] == 'appendages'][0] for r in (rep0, rep1)],
                   pass_=bool(md['sym_med_mm'] <= 0.25 and abs(ar - 1) <= 0.01) if mode == 'windows' else None)
        print(json.dumps(row), flush=True)
        rows.append(row)
    return rows


def test_scale_all(out, f=1.3, keys=('lid', 'pot', 'rack')):
    """Windows-mode scale test of the other three programs (points, cameras and the sensor voxel scaled by f about
    the frame origin). The marker hardware (balls) and the absolute residual noise band are absolute by design, so
    the ball parts are removed and every residual band is given relative (APP_D at the kit's reference s); the
    robust-loss scale F_SCALE stays absolute (tube_rrect, cone_array). Reported: scaled-back distance to the
    unscaled output; pass <= 0.25 mm median and area within 1 %."""
    rows = []
    for key in keys:
        c = CASES[key]
        obs = load_obs(c.get('obs') or obs_path(c['obj'], c['ep']))
        P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
        sref = {key: PT.Ctx(obs, t=0.0025).s}           # this episode's own s (GT-free): APP_D as a fraction
        prog = load_program(f'{HERE}/programs/{c["program"]}')
        prog['parts'] = [p for p in prog['parts'] if p['type'] != 'ball']
        for p in prog['parts']:
            if p.get('assign', {}).get('rule') in ('residual', 'largest_cluster_beyond', 'largest_cluster_extent'):
                p['assign']['band'] = PT.APP_D / sref[key]
                p['assign']['cluster_vox'] = 0.003                  # scaled below with the points
        o0 = dict(pts=P, cam=C, frame=obs['frame'])
        if 'args' in obs:
            o0['args'] = obs['args']
        mesh0, rep0 = run_program(prog, o0, t=0.0025)
        pr = json.loads(json.dumps(prog)); pr['preprocess'] = dict(vox=0.0015 * f)
        for p in pr['parts']:
            if 'cluster_vox' in p.get('assign', {}):
                p['assign']['cluster_vox'] = 0.003 * f
        o1 = dict(pts=f * P, cam=f * C, frame=obs['frame'])
        if 'args' in obs:
            a_ = json.loads(str(obs['args'])); a_['table_band'] = f * float(a_.get('table_band', 0.008))
            o1['args'] = np.array(json.dumps(a_))
        mesh1, rep1 = run_program(pr, o1, t=0.0025)
        mesh1b = mesh1.copy(); mesh1b.apply_scale(1 / f)
        mesh1b.export(f'{out}/scale_windows_{key}_back.glb')
        md = mesh_dist(mesh1b, mesh0)
        ar = mesh1b.area / mesh0.area
        row = dict(test='scale_all', case=key, mode='windows_noballs', f=f, s_mm=[rep0['s_mm'], rep1['s_mm']],
                   mesh_dist_scaled_back=md, area_ratio_scaled_back=round(ar, 4),
                   pass_=bool(md['sym_med_mm'] <= 0.25 and abs(ar - 1) <= 0.01))
        print(json.dumps(row), flush=True)
        rows.append(row)
    return rows


CROSS = {   # other public episodes of the same objects (driver input list); hand-kit candidate where one exists
    'pot': [(e, f'{SCRATCH}/prim/potlid/cand/white_pot_ep{e}_fit.glb') for e in (42, 43, 44, 45)],
    'lid': [(0, None)],
    'cup': [(22, f'{SCRATCH}/lathe/ep22_blue_cup_g1.glb'), (12, None), (13, None)],
    'rack': [(e, f'{SCRATCH}/prim/clean/rack/t2.5_lean1/plastic_dish_rack/ep{e}_full.glb') for e in (12, 26, 27, 31)],
}


def test_cross(out, key):
    """The example program, unchanged, on the object's other public episodes (no per-episode tuning): runs or fails,
    bound hits, owned residuals, fidelity on the episode's own points; vs the hand-kit candidate where one exists
    (rack candidates used the 5-episode shared floor depth, so their lower block differs by design)."""
    c = CASES[key]
    rows = []
    for ep, inc in CROSS[key]:
        row = dict(test='cross', case=key, obj=c['obj'], ep=ep)
        try:
            obs = load_obs(obs_path(c['obj'], ep))
            t0 = time.time()
            mesh, rep = run_program(load_program(f'{HERE}/programs/{c["program"]}'), obs, t=0.0025)
            glb = f'{out}/cross_{key}_ep{ep}.glb'; mesh.export(glb)
            json.dump(jsonable(rep), open(glb[:-4] + '.json', 'w'), indent=1, default=float)
            P = np.asarray(obs['pts'], np.float64)
            row.update(ok=True, sec=round(time.time() - t0, 1), s_mm=rep['s_mm'], faces=rep['faces'],
                       watertight=rep['watertight'], bodies=rep['bodies'], k_total=rep['k_total'],
                       bounds_hit=rep['bounds_hit'], obs_to_model=rep['obs_to_model'],
                       parts=[dict(name=p['name'], n=p['n_assigned'], residual=p.get('residual'),
                                   skipped=p.get('skipped') or p.get('failed')) for p in rep['parts']],
                       fid_dsl=fidelity(P, mesh))
            if inc and os.path.exists(inc):
                row['vs_hand_kit'] = compare(mesh, inc, P)
        except Exception as e:                              # report every failure
            row.update(ok=False, error=repr(e)[:500])
        print(json.dumps(jsonable(row), default=float), flush=True)
        rows.append(row)
    return rows


def test_grid(out):
    rows = []
    obs = load_obs(obs_path('white_pot_lid', 2))
    P = np.asarray(obs['pts'], np.float64)
    prog = load_program(f'{HERE}/programs/sheet_strap_balls.json')
    for t in (0.0015, 0.0025, 0.004):
        mesh, rep = run_program(prog, obs, t=t)
        inc = f'{SCRATCH}/prim/clean/lid/t{t * 1e3:.1f}_fit.glb'
        mesh.export(f'{out}/lid_ep2_t{t * 1e3:.1f}.glb')
        row = dict(test='grid', case='lid', t_mm=t * 1e3, inc=inc, **compare(mesh, inc, P))
        print(json.dumps(row), flush=True)
        rows.append(row)
    return rows


def test_dsl(out):
    rows = []
    obs = load_obs(obs_path('white_pot_lid', 2))
    for bad, err in ((dict(program='x', parts=[dict(name='a', type='nope')]), 'unknown part type'),
                     (dict(program='x', parts=[dict(name='a', type='lathe', assign=dict(rule='nope'))]), 'unknown assignment rule')):
        try:
            run_program(bad, obs, t=0.0025)
            rows.append(dict(test='dsl_error', expect=err, ok=False))
        except ValueError as e:
            rows.append(dict(test='dsl_error', expect=err, ok=err in str(e)))
    from autokit.program import validate_program
    for f in sorted(os.listdir(f'{HERE}/programs')):
        rows.append(dict(test='validate', program=f, problems=validate_program(load_program(f'{HERE}/programs/{f}')),
                         ok=not validate_program(load_program(f'{HERE}/programs/{f}'))))
    bad = dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='height')),
                                   dict(name='b', type='plate', params=dict(host='c', outline='occupancy')),
                                   dict(name='a', type='ball')])
    pr = validate_program(bad)
    rows.append(dict(test='validate_bad', problems=pr, ok=len(pr) == 2))
    # stage 1b schema checks: unknown keys, enum values, required windows, 'of' as a string
    cases = [
        (dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='height', bogus=1))]), 'unknown parameter'),
        (dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='height'), assign=dict(rule='all', k=1))]), 'has no field'),
        (dict(program='x', extra=1, parts=[dict(name='a', type='lathe', params=dict(method='height'))]), 'unknown key'),
        (dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='height'), colour='red')]), 'unknown key'),
        (dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='spline'))]), 'not in'),
        (dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='polar'))]), "required window 'rim_w'"),
        (dict(program='x', parts=[dict(name='a', type='lathe', params=dict(method='height', dh={'abs': 0.003, 'frac': 0.1}))]), 'window dict'),
        (dict(program='x', frame=dict(type='support', cel=0.1), parts=[dict(name='a', type='rounded_box')]), "frame: unknown key"),
    ]
    for prog, expect in cases:
        pr = validate_program(prog)
        rows.append(dict(test='validate_schema', expect=expect, problems=pr, ok=any(expect in e for e in pr)))
    ok_str = validate_program(dict(program='x', parts=[dict(name='a', type='rounded_box'),
                                                        dict(name='b', type='ball', params=dict(of='a'),
                                                             assign=dict(rule='residual', of='a'))]))
    rows.append(dict(test='validate_of_string', problems=ok_str, ok=not ok_str))
    # every window / param the code reads is declared in its part type's schema (static), DSL.md block in sync
    import inspect
    from autokit.program import schema_markdown
    reads = {}
    for name, ptp in PT.PART_TYPES.items():
        fns = [ptp.fit] + {'lathe': [PT.lathe_polar, PT.lathe_height, PT.axis_search, PT.cell_threshold],
                           'plate': [PT.fit_plate_bar, PT.plane_outline], 'plate_set': [PT.plane_outline],
                           'tube_rrect': [PT.tube_fit_once]}.get(name, [])
        code = '\n'.join(inspect.getsource(f) for f in fns)
        used = set(re.findall(r"ctx\.[wp]\(spec, '(\w+)'", code)) | set(re.findall(r"\bW\('(\w+)'\)", code)) | \
            set(re.findall(r"p\.get\('(\w+)'", code))
        missing = sorted(u for u in used if u not in ptp.schema)
        reads[name] = missing
    rows.append(dict(test='schema_covers_code', missing=reads, ok=not any(reads.values())))
    dsl = open(f'{HERE}/DSL.md').read()
    blk = dsl[dsl.index('<!-- schema:begin'):dsl.index('<!-- schema:end -->') + len('<!-- schema:end -->')] \
        if '<!-- schema:begin' in dsl else ''
    rows.append(dict(test='dsl_md_in_sync', ok=blk == schema_markdown()))
    try:
        run_program(load_program(f'{HERE}/programs/sheet_strap_balls.json'), obs, t=0.0018)
        rows.append(dict(test='t_off_grid', ok=False))
    except ValueError as e:
        rows.append(dict(test='t_off_grid', ok='grid' in str(e)))
    # integrity grep of the method code
    pat = re.compile('|'.join(OBJECT_NAMES), re.I)
    for f in ('parts.py', 'program.py'):
        src = open(f'{HERE}/{f}').read()
        names = sorted(set(m.group(0) for m in pat.finditer(src)))
        loads = re.findall(r'np\.load\(|open\(|trimesh\.load\(', src)
        gt_paths = re.findall(r'[\'"][^\'"\n]*(?:/loc/|/scan|_align\b|\.parquet|mocap)[^\'"\n]*[\'"]', src)
        rows.append(dict(test='integrity_grep', file=f, object_names=names, file_access=loads, gt_path_literals=gt_paths,
                         ok=(not names) and (not gt_paths)))
    # smoke runs of the parts not used by the reproductions
    lidp = load_program(f'{HERE}/programs/sheet_strap_balls.json')
    SHEET = [p for p in lidp['parts'] if p['name'] == 'sheet'][0]['params']
    STRAP = {k: v for k, v in [p for p in lidp['parts'] if p['name'] == 'strap'][0]['params'].items() if k != 'host'}
    smoke = [
        ('plate_set', 'wooden_piece_1', 24, dict(program='smoke_plate_set', parts=[
            dict(name='plates', type='plate_set', assign=dict(rule='all'), params=dict(max_plates=2, min_pts=2000))])),
        ('rounded_box', 'wooden_piece_1', 24, dict(program='smoke_box', parts=[
            dict(name='box', type='rounded_box', assign=dict(rule='all'))])),
        ('tsdf_patch', 'white_pot_lid', 2, dict(program='smoke_tsdf', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all'), params=SHEET),
            dict(name='rest', type='tsdf_patch', assign=dict(rule='all'), params={'of': ['sheet']})])),
        ('clusters_dir+splat_union', 'white_pot_lid', 2, dict(program='smoke_dir', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all'), params=SHEET),
            dict(name='above', type='splat', assign=dict(rule='clusters_dir', of=['sheet'], dir='+axis', min_pts=100),
                 params=dict(combine='union'))])),
        ('strap_no_host', 'white_pot_lid', 2, dict(program='smoke_strap', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all'), params=SHEET),
            dict(name='strap', type='strap', assign=dict(rule='largest_cluster_extent', of=['sheet'], min_extent=0.7846,
                                                          min_pts=100), params=STRAP)])),
        ('ball_none', 'white_pot_lid', 2, dict(program='smoke_ball_none', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all'), params=SHEET),
            dict(name='balls', type='ball', assign=dict(rule='residual', of=['sheet']), params=dict(of=['sheet'], mode='none'))])),
        ('shell_patch', 'white_pot_lid', 2, dict(program='smoke_patch', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all'), params=SHEET),
            dict(name='rest', type='shell_patch', assign=dict(rule='residual'))])),
        ('plate_set_plane_pan', 'mini_dust_pan', 39, dict(program='smoke_pan_planes', parts=[
            dict(name='plates', type='plate_set', assign=dict(rule='all'), params=dict(max_plates=6, keep_holes=True))])),
        ('plate_set_cluster_pan', 'mini_dust_pan', 39, dict(program='smoke_pan_cluster', parts=[
            dict(name='plates', type='plate_set', assign=dict(rule='all'), params=dict(max_plates=6, segment='cluster'))])),
        ('lathe_open_floor', 'blue_cup', 21, dict(program='smoke_open', parts=[
            dict(name='body', type='lathe', assign=dict(rule='all'), params=dict(method='height', floor='open'))])),
        ('plate_occupancy', 'wooden_piece_1', 24, dict(program='smoke_plate', parts=[
            dict(name='board', type='plate', assign=dict(rule='all'), params=dict(outline='occupancy'))])),
    ]
    for name, obj, ep, prog in smoke:
        o = load_obs(obs_path(obj, ep))
        try:
            mesh, rep = run_program(prog, o, t=0.0025, lib=f'{LIB}/{obj}.glb')
            mesh.export(f'{out}/smoke_{name}.glb')
            fd = fidelity(np.asarray(o['pts'], np.float64), mesh)
            rows.append(dict(test='smoke', part=name, obj=obj, ep=ep, faces=int(len(mesh.faces)),
                             watertight=bool(mesh.is_watertight), bodies=int(mesh.body_count), fid=fd,
                             k=rep['k_total'], params=[p.get('params') for p in rep['parts']],
                             diag=[{k: v for k, v in (p.get('diag') or {}).items() if k in ('plates', 'segmentation', 'impl', 'note', 'faces', 'area_cm2', 'n_raw')}
                                   for p in rep['parts']], ok=True))
        except Exception as e:                      # report, do not hide
            rows.append(dict(test='smoke', part=name, obj=obj, ep=ep, ok=False, error=repr(e)))
    for r in rows:
        print(json.dumps(jsonable(r), default=float), flush=True)
    return rows


# ------------------------------------------------------------------------------------------------ synthetic (stage 1b)
def _synth_obs(pieces, seed=0, noise=0.0005, nfr=20):
    """pieces: list of (points (N,3), outward-ish view hint) -> obs dict; every point is seen by the camera above it
    (0.5 m up, small lateral offset per frame), frame ids random in [0, nfr)."""
    rng = np.random.default_rng(seed)
    P = np.concatenate(pieces) + rng.normal(0, noise, (sum(len(p) for p in pieces), 3))
    F = rng.integers(0, nfr, len(P))
    off = np.stack([np.cos(F * 0.7), np.sin(F * 0.7)], 1) * 0.15
    C = np.c_[P[:, 0] + off[:, 0], P[:, 1] + off[:, 1], np.full(len(P), 0.5)]
    return dict(pts=P, cam=C, frame=F)


def _grid(x0, x1, y0, y1, step, z=0.0, keep=None):
    xs, ys = np.meshgrid(np.arange(x0, x1, step), np.arange(y0, y1, step))
    Q = np.c_[xs.ravel(), ys.ravel(), np.full(xs.size, z)]
    return Q if keep is None else Q[keep(Q)]


def _cap(c, r, step, upper=True):
    """Points on the upper (visible from above) or lower hemisphere of a sphere, ~step spacing."""
    n = int(2 * np.pi * r * r / step ** 2)
    u = np.random.default_rng(1).normal(size=(4 * n, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
    u = u[u[:, 2] > 0.05] if upper else u[u[:, 2] < -0.05]
    return np.asarray(c) + r * u[:n]


def test_synth(out):
    """GT-free synthetic checks of the stage-1b parts (known geometry, no observation file):
    balls - a 4.5 mm and an 11 mm sphere cap (two arbitrary radii inside the generic 3-15 mm window, chosen to test
    the window, not any object's balls) are kept with their free radii; a flat disc, a rod (one-way curvature), a
    concave bowl and a 25 mm sphere cap are rejected; mode none gives none; both fits ('lsq', 'ransac') are run;
    keep_holes - a 30 mm hole in a plate survives;
    plate_set - two perpendicular connected plates give 2 plates by plane, 1 by connectivity."""
    rows = []
    st = 0.0012
    plane = _grid(-0.08, 0.08, -0.08, 0.08, st)
    ball = _cap((0.04, 0.04, 0.020), 0.0045, st * 0.6)
    ball2 = _cap((0.04, -0.01, 0.020), 0.011, st * 0.8)
    disc = _grid(-0.006, 0.006, -0.006, 0.006, st * 0.7, z=0.020, keep=lambda Q: np.hypot(Q[:, 0], Q[:, 1]) < 0.006)
    disc[:, 0] -= 0.04; disc[:, 1] += 0.04
    th = np.random.default_rng(2).uniform(0, np.pi, 3000); xx = np.random.default_rng(3).uniform(-0.02, 0.02, 3000)
    rod = np.c_[xx, -0.04 + 0.005 * np.cos(th), 0.020 + 0.005 * np.sin(th)]
    bowl = _cap((-0.04, -0.04, 0.030), 0.008, st * 0.7, upper=False)
    big = _cap((0.0, 0.0, 0.060), 0.025, st)
    big = big[big[:, 2] > 0.075]
    obs = _synth_obs([plane, ball, ball2, disc, rod, bowl, big])
    base = dict(name='base', type='plate', assign=dict(rule='all'), params=dict(outline='rect'))
    for mode, fit in (('free', 'lsq'), ('free', 'ransac'), ('none', 'lsq')):
        prog = dict(program='synth_balls', parts=[base, dict(name='balls', type='ball', assign=dict(rule='residual', of=['base']),
                                                            params=dict(of=['base'], mode=mode, fit=fit))])
        try:
            mesh, rep = run_program(prog, obs, t=0.0025)
            b = [p for p in rep['parts'] if p['name'] == 'balls'][0]
            mk = b['diag']['markers']
            acc = sorted([m for m in mk if not m.get('rejected')], key=lambda m: m['r_mm'])
            ok = (len(acc) == 2 and abs(acc[0]['r_mm'] - 4.5) < 0.5 and abs(acc[1]['r_mm'] - 11.0) < 1.0
                  and abs(acc[0]['centre'][1] - 0.04) < 0.002 and abs(acc[1]['centre'][1] + 0.01) < 0.002) if mode == 'free' else not acc
            rows.append(dict(test='synth_balls', mode=mode, fit=fit, accepted=[{k: m.get(k) for k in ('r_mm', 'centre', 'res_mm', 'spread', 'convex', 'iso', 'frames')} for m in acc],
                             rejected=[{k: m.get(k) for k in ('rejected', 'r_mm', 'centre', 'spread', 'convex', 'iso', 'diag_mm', 'n')} for m in mk if m.get('rejected')],
                             ok=bool(ok)))
        except Exception as e:
            rows.append(dict(test='synth_balls', mode=mode, ok=False, error=repr(e)))
    # keep_holes: 120 x 80 mm plate with a 30 mm hole
    holed = _grid(-0.06, 0.06, -0.04, 0.04, st, keep=lambda Q: np.hypot(Q[:, 0] - 0.02, Q[:, 1]) > 0.015)
    oh = _synth_obs([holed])
    areas = {}
    for kh in (False, True):
        prog = dict(program='synth_holes', parts=[dict(name='p', type='plate', assign=dict(rule='all'),
                                                         params=dict(outline='occupancy', keep_holes=kh))])
        mesh, rep = run_program(prog, oh, t=0.0025)
        d = rep['parts'][0]['diag']
        areas[kh] = (d['area_cm2'], d.get('holes'))
    rows.append(dict(test='synth_keep_holes', area_cm2_fill=areas[False][0], area_cm2_keep=areas[True][0],
                     holes=areas[True][1], expected_hole_cm2=round(np.pi * 1.5 ** 2, 2),
                     ok=bool(areas[True][1] == 1 and abs((areas[False][0] - areas[True][0]) - np.pi * 1.5 ** 2) < 2.0)))
    # plate_set: an L of two perpendicular plates sharing an edge
    p1 = _grid(-0.05, 0.05, -0.04, 0.04, st)
    p2 = np.c_[np.full(4000, 0.05), np.random.default_rng(4).uniform(-0.04, 0.04, 4000),
               np.random.default_rng(5).uniform(0.0, 0.05, 4000)]
    oL = _synth_obs([p1, p2])
    oL['cam'][len(p1):] = oL['pts'][len(p1):] + np.array([0.5, 0.0, 0.2])     # the wall is seen from its +x side
    res = {}
    for seg in ('plane', 'cluster'):
        prog = dict(program='synth_L', parts=[dict(name='ps', type='plate_set', assign=dict(rule='all'),
                                                      params=dict(segment=seg, min_pts=500))])
        mesh, rep = run_program(prog, oL, t=0.0025)
        res[seg] = rep['parts'][0]['params']['n_plates']
    rows.append(dict(test='synth_plate_set', n_plates=res, ok=bool(res['plane'] == 2 and res['cluster'] == 1)))
    for r in rows:
        print(json.dumps(jsonable(r), default=float), flush=True)
    return rows


# ------------------------------------------------------------------------------------------------ stage 1b matrix
def with_balls(prog, mode):
    pr = json.loads(json.dumps(prog))
    for p in pr['parts']:
        if p['type'] == 'ball':
            p.setdefault('params', {})['mode'] = mode
    return pr


def with_patch(prog):
    """A + B: the program plus a shell_patch over the residual of every earlier part (rule 'residual', no 'of')."""
    pr = json.loads(json.dumps(prog))
    pr['parts'].append(dict(name='patch', type='shell_patch', assign=dict(rule='residual')))
    return pr


def with_legacy_cells(prog):
    pr = json.loads(json.dumps(prog))
    for p in pr['parts']:
        if p['type'] == 'lathe':
            p.setdefault('params', {})['cell_min_pts'] = 8
    return pr


def stage1_ref(key, t):
    c = CASES[key]
    alt = f'{STAGE1}/{key}_ep{c["ep"]}_t{t * 1e3:.1f}.glb'
    if abs(t - 0.0025) > 1e-9 and os.path.exists(alt):
        return alt, True
    return f'{STAGE1}/{key}_ep{c["ep"]}.glb', abs(t - 0.0025) < 1e-9


def part_summary(rep):
    out = {}
    for p in rep['parts']:
        d = p.get('diag') or {}
        s = dict(type=p['type'], n=p['n_assigned'], params=p.get('params'), skipped=p.get('skipped') or p.get('failed'),
                 residual=p.get('residual'))
        for k in ('t_src', 't_src_evidence', 'cell_min_pts', 'cell_median', 't_mm', 'T_src', 'impl', 'n_raw', 'note'):
            if k in d:
                s[k] = d[k]
        if p['type'] == 'ball':
            mk = d.get('markers', [])
            s['rejected'] = {r: sum(1 for m in mk if m.get('rejected') == r) for r in sorted({m.get('rejected') for m in mk if m.get('rejected')})}
            s['accepted'] = [{k: m.get(k) for k in ('r_mm', 'res_mm', 'gap_mm', 'frames', 'spread', 'convex', 'iso', 'stem', 'stem_r_mm', 'n')}
                             for m in mk if not m.get('rejected')]
        out[p['name']] = s
    return out


def test_s1b(out, key, balls=('free', 'none'), budget_all=False, legacy=True):
    """Stage-1b matrix on the case's development episode (see module doc, item 7). GT-free."""
    c = CASES[key]
    path = c.get('obs') or obs_path(c['obj'], c['ep'])
    obs = load_obs(path)
    P = np.asarray(obs['pts'], np.float64)
    prog0 = load_program(f'{HERE}/programs/{c["program"]}')
    has_ball = any(p['type'] == 'ball' for p in prog0['parts'])
    d = f'{out}/s1b/{key}'; os.makedirs(d, exist_ok=True)
    s1rep = json.load(open(f'{STAGE1}/{key}_ep{c["ep"]}.json'))
    s1par = {p['name']: p.get('params') for p in s1rep['parts']}
    refs, rows = {}, []
    combos = []
    for vtag, vprog in variants(prog0):
        for t in T_GRID:
            for bm in (tuple(balls) if has_ball else ('-',)):
                for patch in (False, True):
                    combos.append((vtag, vprog, t, bm, patch, False))
    if legacy and any(p['type'] == 'lathe' for p in prog0['parts']):
        combos.append(('base', prog0, 0.0025, 'free' if has_ball else '-', False, True))
    sh = os.path.join(HERE, 'shell.py')
    for vtag, vprog, t, bm, patch, legacy in combos:
        pr = vprog
        if bm != '-':
            pr = with_balls(pr, bm)
        if patch:
            pr = with_patch(pr)
        if legacy:
            pr = with_legacy_cells(pr)
        tag = f'{vtag}_t{t * 1e3:.1f}_balls-{bm}_patch-{int(patch)}' + ('_legacycells' if legacy else '')
        if os.environ.get('S1B_RESUME') == '1' and os.path.exists(f'{d}/{tag}.glb') and os.path.exists(f'{d}/{tag}.json'):
            continue                                      # resumed run: the row is in the earlier run's log
        row = dict(test='s1b', case=key, obj=c['obj'], ep=c['ep'], variant=vtag, t_mm=t * 1e3, balls=bm, patch=patch,
                   legacy_cells=legacy, tag=tag)
        try:
            import hashlib
            row['shell_sha'] = hashlib.sha256(open(sh, 'rb').read()).hexdigest()[:12]
            t0 = time.time()
            mesh, rep = run_program(pr, obs, t=t, lib=f'{LIB}/{c["obj"]}.glb', budget=BUDGET if (patch or budget_all) else None)
            row['sec'] = round(time.time() - t0, 1)
            glb = f'{d}/{tag}.glb'; mesh.export(glb)
            json.dump(jsonable(rep), open(glb[:-4] + '.json', 'w'), indent=1, default=float)
            ref, same_t = stage1_ref(key, t)
            if ref not in refs:
                refs[ref] = load_ref(ref)
            row.update(faces=rep['faces'], watertight=rep['watertight'], bodies=rep['bodies'], area_cm2=rep['area_cm2'],
                       k_total=rep['k_total'], obs_to_model=rep['obs_to_model'], fid=fidelity(P, mesh),
                       stage1_ref=os.path.basename(ref), stage1_ref_same_t=same_t, vs_stage1=mesh_dist(mesh, refs[ref]),
                       area_ratio_vs_stage1=round(float(mesh.area / refs[ref].area), 4), parts=part_summary(rep),
                       program_budget=rep.get('budget'))
            row['budget'], dec = budget_check(mesh, f'{d}/_tmp_{key}.glb', return_mesh=True)
            if dec is not None:
                row['fid_decoded'] = fidelity(P, dec)       # what the scorer sees (kit decode to 4096 faces)
            if abs(t - 0.0025) < 1e-9 and vtag == 'base':
                row['params_equal_stage1'] = {n: (s['params'] == s1par.get(n)) for n, s in row['parts'].items()
                                              if n in s1par and s['type'] != 'ball'}
            row['ok'] = True
        except Exception as e:                              # report every failure
            import traceback
            row.update(ok=False, error=repr(e)[:400], tb=traceback.format_exc()[-1500:])
        print(json.dumps(jsonable(row), default=float), flush=True)
        rows.append(row)
    if os.path.exists(f'{d}/_tmp_{key}.glb'):
        os.remove(f'{d}/_tmp_{key}.glb')
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--only', default='lid,pot,cup,rack,scale,grid,dsl')
    ap.add_argument('--reuse', type=int, default=0)
    ap.add_argument('--balls', default='free,none', help='s1b: ball modes of the matrix')
    ap.add_argument('--budget_all', type=int, default=0, help='s1b: every row in budget mode (not only patch rows)')
    ap.add_argument('--legacy', type=int, default=1, help='s1b: include the legacy-cells row')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    only = a.only.split(',')
    rows = []
    rep_keys = [k for k in ('lid', 'pot', 'cup', 'rack') if k in only]
    if rep_keys:
        rows += test_reproduce(rep_keys, a.out, bool(a.reuse))
    if 'scale' in only:
        rows += test_scale(a.out)
    for key in ('pot', 'lid', 'cup', 'rack'):
        if f'cross_{key}' in only:
            rows += test_cross(a.out, key)
    if 'scale_all' in only:
        rows += test_scale_all(a.out)
    if 'grid' in only:
        rows += test_grid(a.out)
    if 'dsl' in only:
        rows += test_dsl(a.out)
    if 'synth' in only:
        rows += test_synth(a.out)
    for key in ('lid', 'cup', 'pot', 'rack'):
        if f's1b_{key}' in only:
            rows += test_s1b(a.out, key, balls=a.balls.split(','), budget_all=bool(a.budget_all), legacy=bool(a.legacy))
    with open(f'{a.out}/results_{"_".join(only)}.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(jsonable(r), default=float) + '\n')


if __name__ == '__main__':
    main()
