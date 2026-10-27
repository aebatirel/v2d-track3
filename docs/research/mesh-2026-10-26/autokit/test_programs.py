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
No scan, *_align file, mocap or parquet pose is opened; obs files go through autokit.io_gt.load_obs.
Usage: test_programs.py [--out DIR] [--only lid,pot,cup,rack,scale,scale_all,grid,dsl,cross_pot,cross_lid,
       cross_cup,cross_rack] [--reuse 1]
"""
import argparse, json, os, re, subprocess, sys, time

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit.io_gt import load_obs, obs_path, SCRATCH      # noqa: E402
from autokit.program import run_program, load_program, jsonable   # noqa: E402

OUT = f'{SCRATCH}/auto/stage1/parts-dsl'
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


def compare(mesh, inc_path, P):
    inc = trimesh.load(inc_path, force='mesh')
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
        mesh = trimesh.load(glb, force='mesh'); rep = json.load(open(glb[:-4] + '.json'))
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
    import autokit.parts as PT
    sref = dict(lid=PT.S_REF_SHEET, pot=PT.S_REF_POLAR, rack=PT.S_REF_TUBE)
    rows = []
    for key in keys:
        c = CASES[key]
        obs = load_obs(c.get('obs') or obs_path(c['obj'], c['ep']))
        P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
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
            run_program(bad, obs)
            rows.append(dict(test='dsl_error', expect=err, ok=False))
        except ValueError as e:
            rows.append(dict(test='dsl_error', expect=err, ok=err in str(e)))
    from autokit.program import validate_program
    for f in sorted(os.listdir(f'{HERE}/programs')):
        rows.append(dict(test='validate', program=f, problems=validate_program(load_program(f'{HERE}/programs/{f}')),
                         ok=not validate_program(load_program(f'{HERE}/programs/{f}'))))
    bad = dict(program='x', parts=[dict(name='a', type='lathe'), dict(name='b', type='plate', params=dict(host='c')),
                                   dict(name='a', type='ball')])
    pr = validate_program(bad)
    rows.append(dict(test='validate_bad', problems=pr, ok=len(pr) == 2))
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
    smoke = [
        ('plate_set', 'wooden_piece_1', 24, dict(program='smoke_plate_set', parts=[
            dict(name='plates', type='plate_set', assign=dict(rule='all'), params=dict(max_plates=2, min_pts=2000))])),
        ('rounded_box', 'wooden_piece_1', 24, dict(program='smoke_box', parts=[
            dict(name='box', type='rounded_box', assign=dict(rule='all'))])),
        ('tsdf_patch', 'white_pot_lid', 2, dict(program='smoke_tsdf', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all')),
            dict(name='rest', type='tsdf_patch', assign=dict(rule='all'), params={'of': ['sheet']})])),
        ('clusters_dir+splat_union', 'white_pot_lid', 2, dict(program='smoke_dir', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all')),
            dict(name='above', type='splat', assign=dict(rule='clusters_dir', of=['sheet'], dir='+axis', min_pts=100),
                 params=dict(combine='union'))])),
        ('strap_no_host', 'white_pot_lid', 2, dict(program='smoke_strap', parts=[
            dict(name='sheet', type='sheet_of_revolution', assign=dict(rule='all')),
            dict(name='strap', type='strap', assign=dict(rule='largest_cluster_extent', of=['sheet'], min_extent=0.7846,
                                                          min_pts=100))])),
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
                             watertight=bool(mesh.is_watertight), fid=fd, k=rep['k_total'],
                             params=[p.get('params') for p in rep['parts']], ok=True))
        except Exception as e:                      # report, do not hide
            rows.append(dict(test='smoke', part=name, obj=obj, ep=ep, ok=False, error=repr(e)))
    for r in rows:
        print(json.dumps(jsonable(r), default=float), flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--only', default='lid,pot,cup,rack,scale,grid,dsl')
    ap.add_argument('--reuse', type=int, default=0)
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
    with open(f'{a.out}/results_{"_".join(only)}.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(jsonable(r), default=float) + '\n')


if __name__ == '__main__':
    main()
