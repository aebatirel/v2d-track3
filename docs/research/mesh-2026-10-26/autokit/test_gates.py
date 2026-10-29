"""Tests and the PRE-REGISTERED held-out validation of gates.py v3 (stage 1b, fixer "gates", 2026-10-29).
GT-free: observations, tracks and calibration only through autokit/io_gt.py; meshes through io_gt.load_mesh (allow-listed
roots); edits are synthetic and defined from our own observed points only. No scan, no *_align file, no mocap, no
parquet; mesh_metric.py is not run; no label comes from a scan score.

Stages (outputs under OUT = scratchpad/auto/stage1b/gates/):
  unit      (a) static integrity of gates.py (no object name or object word, no GT path constant);
            (b) wiring: observed points re-project onto integer pixel centres with our track + K, and the v3 cell
                index floor((u + 0.5) / CELL_PX) keeps every observed point in the cell of its pixel;
            (f) guard: a dummy mesh under a /scan/ directory, a hard link to it, a mesh outside the allow-listed roots and
                a refined obs copy under obs='raw' are refused at every entry point (io_gt.load_mesh / mesh_input,
                gates.load_raw / load_budget / evaluate, parts.load_mesh_guarded, run_object.build_candidates);
            (g) selector v3 on synthetic rows: shells, incumbents and off-middle t builds are never picked, whatever
                their rank; the library is the fallback; a measured-thickness family is represented by its build
                closest to 2.5 mm.
  dev       DEVELOPMENT check of the new v3 terms on dev episodes that were used for v1/v2 (lid 2, pot 41, cup 21,
            rack 13): existing program / shell / library meshes and the pre-registered edit kinds, no flip. Run before
            the pre-registration; its numbers are reported as development, not validation.
  prereg    writes prereg_gates_v3.json (cases, edits, expected verdicts, gates.py sha256); refuses to overwrite.
  heldout   the pre-registered run: checks gates.py against the frozen sha256, builds the base meshes, makes the edits,
            evaluates every row, writes rows / verdicts; no threshold is changed afterwards.
  noise     (v2, kept) data-only depth-margin calibration (leave-frames-out self-consistency).
  audit     (e) runtime integrity: one full gates.py eval under strace -f -e trace=openat,open,openat2,execve.
  legacy_validate  v2's post-hoc validation set (its MUST_PASS labels came from earlier SCAN-SCORED rounds; kept only
            for the record, never used by v3).
Object names appear only in the driver input tables below.
Usage: python test_gates.py {unit|dev|prereg|heldout|noise|audit|legacy_validate} [--shard i/n] [--stage build|eval]
"""
import argparse, glob, hashlib, json, os, re, sys, time

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit import io_gt  # noqa: E402
from autokit import gates as G  # noqa: E402

S = io_gt.SCRATCH
OUT = f'{S}/auto/stage1b/gates'
LIB = G.LIB_DIR
PROG_DIR = f'{HERE}/programs'
PREREG = f'{OUT}/prereg_gates_v3.json'
FORBIDDEN_RE = re.compile(r'/loc/|/scan|_align|\.parquet|mocap', re.I)

# ---------------------------------------------------------------------------------------- driver input tables
NOISE_SET = [('mini_dust_pan', 39), ('white_pot', 41), ('white_pot_lid', 2), ('plastic_dish_rack', 13),
             ('blue_cup', 21), ('mini_sweeper', 31), ('water_pitcher', 22), ('wooden_piece_1', 23)]
# held-out cases (objects / episodes not used to tune v1 / v2): (case, obj, ep, base kind, program file, frame split)
#   base 'program': the part program as written, t = 2.5 mm, budget 4000, built from this episode's own points;
#   base 'shell':   no program exists for the object: route-A thin shell, t = 2.5 mm (diagnostic kind; on the observed
#                   surface by construction, so it is a GT-free positive for the observed-surface gates);
#   split 'even/odd': built from the even-rank observed frames, judged on the odd-rank frames of the same episode.
HELDOUT = [
    ('pot43', 'white_pot', 43, 'program', 'lathe_bar_balls.json', None),
    ('pot45', 'white_pot', 45, 'program', 'lathe_bar_balls.json', None),
    ('rack27', 'plastic_dish_rack', 27, 'program', 'tray_holder_pegs_balls.json', None),
    ('rack31', 'plastic_dish_rack', 31, 'program', 'tray_holder_pegs_balls.json', None),
    ('cup12', 'blue_cup', 12, 'program', 'lathe_splat.json', None),
    ('cup13', 'blue_cup', 13, 'program', 'lathe_splat.json', None),
    ('lid2odd', 'white_pot_lid', 2, 'program', 'sheet_strap_balls.json', 'even/odd'),
    ('boards24', 'wooden_piece_1', 24, 'shell', None, None),
    ('sweeper31', 'mini_sweeper', 31, 'shell', None, None),
    ('pitcher21', 'water_pitcher', 21, 'shell', None, None),
]
# development check (episodes used for v1 / v2): existing meshes of earlier stages
DEV = [
    ('lid2', 'white_pot_lid', 2, f'{S}/auto/stage1/integ/white_pot_lid_ep2/cand/dsl_sheet_strap_balls_t2.5.glb', 'program'),
    ('lid2', 'white_pot_lid', 2, f'{S}/auto/stage1/integ/white_pot_lid_ep2/cand/shell_raw_t2.5.glb', 'shell'),
    ('pot41', 'white_pot', 41, f'{S}/auto/stage1b/parts/final/pot_ep41.glb', 'program'),
    ('cup21', 'blue_cup', 21, f'{S}/auto/stage1b/parts/final/cup_ep21.glb', 'program'),
    ('rack13', 'plastic_dish_rack', 13, f'{S}/auto/stage1b/parts/final/rack_ep13.glb', 'program'),
]
# edit kinds (pre-registered; definitions in make_edits) and the gates that must detect each
EDITS = dict(
    cut=dict(detect=['G_HOLE', 'G_COMP'], define='delete every face whose centre lies within 0.6 s of the seed: the '
             'observed point with the largest (p - c0).d among the points within 0.25 s of the view axis c0 + l d'),
    plate=dict(detect=['G_PREC'], define='add a closed box L x L x 2.5 mm (L = s), axes (u, w, d), whose inner edge '
               'overlaps the extreme vertex x_e of the mesh along u by 2 mm (centre x_e + (L/2 - 2 mm) u): a fin outside '
               'the observed silhouette, touching the mesh'),
    shift5=dict(detect=['G_FRAME', 'G_PREC', 'G_COMP'], define='rigid translation by 5 mm along (1, 1, 1)/sqrt(3) of the '
                'object frame'),
    dup_far=dict(detect=['G_CONN'], define='add a copy of the largest connected component translated by 1.5 x the '
                 'largest mesh extent along u (no contact)'),
    dup_near=dict(detect=['G_PREC'], define='add a copy of the largest connected component translated by 0.25 s along u '
                  '(overlapping duplicate part)'),
)
EDIT_FRAME = ('c0 = mean of the episode\'s observed points (the build points; for a frame split the build half), s = '
              'their RMS radius about c0, d = unit mean of unit(cam - p) over the points (mean viewing direction), '
              'e = the object-frame axis with the smallest |d_k|, u = unit(d x e), w = d x u; 200k points, rng(0)')

# legacy v2 validation (labels from earlier scan-scored rounds: NOT used by v3)
RES = '/home/user/v2d-track3/docs/research/mesh-2026-10-26/results/prim/meshes'
P1 = f'{S}/auto/probe_P1-pot-blind-rediscovery/run1'
P2 = f'{S}/auto/probe_P2-dustpan-new-object/dustpan'
LEGACY_VALIDATE = [
    ('dustpan', 'mini_dust_pan', 39, f'{LIB}/mini_dust_pan.glb', 'library', 'fallback'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_NC_no_largest_wall.glb', 'P2_negative_control', 'MUST_FAIL'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_NC_floor_only.glb', 'P2_negative_control', 'MUST_FAIL'),
    ('pot', 'white_pot', 41, f'{LIB}/white_pot.glb', 'library', 'fallback'),
    ('pot', 'white_pot', 41, f'{RES}/white_pot_ep41_fit.glb', 'incumbent', 'MUST_PASS (scan-derived label)'),
    ('lid', 'white_pot_lid', 2, f'{RES}/white_pot_lid_ep2_fit_v2.glb', 'incumbent', 'MUST_PASS (scan-derived label)'),
    ('cup', 'blue_cup', 21, f'{S}/lathe/ep21_blue_cup_g1.glb', 'incumbent', 'MUST_PASS (scan-derived label)'),
]


def jl(path, d):
    with open(path, 'a') as f:
        f.write(json.dumps(d, default=str) + '\n')


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def code_sha():
    return {f: sha(f'{HERE}/{f}') for f in ('gates.py', 'io_gt.py', 'shell.py', 'parts.py', 'program.py', 'run_object.py',
                                            'test_gates.py') if os.path.isfile(f'{HERE}/{f}')}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------------------------------- edits
def view_frame(P, C):
    """GT-free edit frame of one episode's observed points (EDIT_FRAME)."""
    rng = np.random.default_rng(0)
    i = rng.choice(len(P), min(200_000, len(P)), replace=False)
    P = P[i].astype(np.float64); C = C[i].astype(np.float64)
    c0 = P.mean(0); s = float(np.sqrt(((P - c0) ** 2).sum(1).mean()))
    v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
    d = v.mean(0); d /= np.linalg.norm(d)
    e = np.eye(3)[int(np.argmin(np.abs(d)))]
    u = np.cross(d, e); u /= np.linalg.norm(u); w = np.cross(d, u)
    return dict(P=P, c0=c0, s=s, d=d, u=u, w=w)


def make_edits(base_path, P, C, out_dir, tag):
    """The pre-registered edits (EDITS) of one base mesh, written to out_dir/tag_<edit>.glb. Returns {edit: path} and
    the frame numbers used."""
    os.makedirs(out_dir, exist_ok=True)
    m = io_gt.load_mesh(base_path)
    F = view_frame(P, C); c0, s, d, u, w, Pp = F['c0'], F['s'], F['d'], F['u'], F['w'], F['P']
    out, info = {}, dict(c0=c0.round(5).tolist(), s_mm=round(s * 1e3, 2), d=d.round(4).tolist(), u=u.round(4).tolist())
    # cut
    q = Pp - c0; al = q @ d; perp = np.linalg.norm(q - al[:, None] * d, axis=1)
    cand = np.nonzero(perp < 0.25 * s)[0]
    seed = Pp[cand[np.argmax(al[cand])]]
    keep = np.linalg.norm(m.triangles_center - seed, axis=1) > 0.6 * s
    cut = trimesh.Trimesh(m.vertices, m.faces[keep], process=True)
    info.update(cut_seed=seed.round(5).tolist(), cut_faces_removed=int((~keep).sum()),
                cut_area_removed_cm2=round(float(m.area_faces[~keep].sum()) * 1e4, 2))
    # plate
    pu = (m.vertices - c0) @ u
    xe = m.vertices[int(np.argmax(pu))]
    L = s
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = u, w, d; M[:3, 3] = xe + (L / 2 - 0.002) * u
    plate = trimesh.creation.box(extents=(L, L, 0.0025), transform=M)
    info.update(plate_L_mm=round(L * 1e3, 2), plate_area_cm2=round(float(plate.area) * 1e4, 2))
    # shift
    sh = m.copy(); sh.apply_translation(0.005 * np.ones(3) / np.sqrt(3))
    # duplicates of the largest component
    comps = G.components(m)
    big = max(comps, key=lambda c: c.area)
    far = big.copy(); far.apply_translation(1.5 * float(m.extents.max()) * u)
    near = big.copy(); near.apply_translation(0.25 * s * u)
    info.update(dup_area_cm2=round(float(big.area) * 1e4, 2))
    for nm, mm in (('cut', cut), ('plate', trimesh.util.concatenate([m, plate])), ('shift5', sh),
                   ('dup_far', trimesh.util.concatenate([m, far])), ('dup_near', trimesh.util.concatenate([m, near]))):
        p = f'{out_dir}/{tag}_{nm}.glb'; mm.export(p); out[nm] = p
    return out, info


# ---------------------------------------------------------------------------------------- unit
def unit():
    out = f'{OUT}/unit.jsonl'
    res = []
    src = open(f'{HERE}/gates.py').read()
    # (a) static integrity
    import ast, io, tokenize
    tree = ast.parse(src)
    docs = set()
    for node in [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]:
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            docs.add(id(node.body[0].value))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
              and id(n) not in docs]
    idents = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)] + \
             [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)] + \
             [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    comments = [t.string for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type == tokenize.COMMENT]
    text = '\n'.join(consts + idents + comments + [ast.get_docstring(tree) or ''] +
                     [ast.get_docstring(n) or '' for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
    names = sorted({os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f'{LIB}/*.glb')})
    hits = [n for n in names if n in text]
    words = [w for w in ('pot', 'lid', 'rack', 'cup', 'dust', 'sweeper', 'pitcher', 'board', 'wooden', 'spoon',
                         'marker', 'handle') if re.search(rf'\b{w}', text, re.I)]
    gt = [c for c in consts if FORBIDDEN_RE.search(c)]
    r = dict(test='a_integrity_static', object_names=hits, object_words=words, gt_path_constants=gt,
             **{'pass': not hits and not words and not gt})
    res.append(r); jl(out, r); print(json.dumps(r))
    # (b) wiring + v3 cell index
    K = io_gt.load_calib()['K']
    calib = io_gt.load_calib(); W, H = calib['size']; wc, hc = int(np.ceil(W / G.CELL_PX)), int(np.ceil(H / G.CELL_PX))
    rows = []
    for obj, ep in (('mini_dust_pan', 39), ('white_pot', 41), ('blue_cup', 12)):
        p = io_gt.obs_path(obj, ep)
        o = io_gt.load_obs(p, keys=('pts', 'frame'))
        T, nc = G.frame_cams(p, obj, ep)
        offs, same = [], []
        for f in G.pick_frames(o['frame'], 6):
            P = o['pts'][o['frame'] == f].astype(np.float64)
            Xc = P @ T[f][:3, :3].T + T[f][:3, 3]
            u = K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2]; v = K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2]
            offs.append(np.maximum(np.abs(u - np.round(u)), np.abs(v - np.round(v))))
            idx, key, cu, cv, z = G._project(P, T[f], K, wc, hc)
            same.append((cu == np.round(u[idx]).astype(np.int64) // G.CELL_PX) & (cv == np.round(v[idx]).astype(np.int64) // G.CELL_PX))
        offs = np.concatenate(offs); same = np.concatenate(same)
        rows.append(dict(obs=os.path.basename(p), corrections=nc, px_off_p50=round(float(np.median(offs)), 4),
                         share_on_centre=round(float((offs < 0.05).mean()), 4),
                         share_cell_of_pixel=round(float(same.mean()), 5)))
    r = dict(test='b_wiring_reprojection_v3_cells', rows=rows,
             **{'pass': all(x['share_on_centre'] > 0.95 and x['share_cell_of_pixel'] > 0.999 for x in rows)})
    res.append(r); jl(out, r); print(json.dumps(r))
    # (f) guard: refusals at every mesh entry point (dummy meshes written here; no real scan exists or is opened)
    d = f'{OUT}/refusal'
    os.makedirs(f'{d}/scan', exist_ok=True); os.makedirs(f'{d}/innocent', exist_ok=True)
    fake = f'{d}/scan/fake_scan.glb'
    trimesh.creation.icosphere(subdivisions=2, radius=0.05).export(fake)
    hard = f'{d}/innocent/hard.glb'
    if os.path.exists(hard):
        os.remove(hard)
    os.link(fake, hard)
    outside = f'{S}/refusal_outside_roots.glb'
    trimesh.creation.icosphere(subdivisions=2, radius=0.05).export(outside)
    sys.path.insert(0, HERE)
    from autokit import parts as PT
    from autokit import run_object as RO
    checks = {}
    for nm, path in (('scan_dir', fake), ('hard_link', hard), ('outside_roots', outside)):
        for ep_name, fn in (('io_gt.load_mesh', lambda p: io_gt.load_mesh(p)),
                            ('io_gt.mesh_input', lambda p: io_gt.mesh_input(p)),
                            ('gates.load_raw', lambda p: G.load_raw(p)),
                            ('gates.load_budget', lambda p: G.load_budget(p)),
                            ('gates.evaluate', lambda p: G.evaluate(p, None, 'mini_dust_pan', 39, flip=False)),
                            ('parts.load_mesh_guarded', lambda p: PT.load_mesh_guarded(p)),
                            ('run_object.mesh_summary_of', lambda p: RO.mesh_summary_of(p))):
            try:
                fn(path); ok = False; msg = 'NOT REFUSED'
            except ValueError as e:
                ok = 'integrity' in str(e); msg = str(e)[:90]
            except Exception as e:  # noqa: BLE001
                ok = False; msg = f'{type(e).__name__}: {e}'[:90]
            checks[f'{nm}:{ep_name}'] = dict(refused=ok, msg=msg)
    os.remove(outside)
    # refined copy under obs='raw' must raise; under obs='refined' it is accepted (not run here)
    ref = io_gt.obs_path('white_pot', 41, refined=True, must_exist=False)
    try:
        G.evaluate(f'{LIB}/white_pot.glb', [ref], 'white_pot', 41, flip=False, obs='raw'); okr = False
    except ValueError as e:
        okr = 'only on request' in str(e)
    checks['refined_under_raw'] = dict(refused=okr)
    # an obs file outside the obs roots, a poses path outside its root
    try:
        io_gt.load_obs(f'{LIB}/white_pot.glb'); oko = False
    except ValueError as e:
        oko = 'allow-listed' in str(e)
    checks['obs_outside_roots'] = dict(refused=oko)
    r = dict(test='f_guard_refusals', checks=checks, **{'pass': all(v['refused'] for v in checks.values())})
    res.append(r); jl(out, r); print(json.dumps(r))
    # (g) selector v3 on synthetic rows
    r = selector_synthetic()
    res.append(r); jl(out, r); print(json.dumps(r))
    print(json.dumps(dict(unit_all_pass=all(x['pass'] for x in res))))


def _row(mesh, kind, rank, passed=True, t_mm=None, family=None, t_rule=None, ep=1):
    g = {k: True for k in G.GATE_NAMES}
    if not passed:
        g['G_HOLE'] = False
    return dict(mesh=mesh, kind=kind, rank_score=rank, gates=g, ep=ep, metrics=dict(fid_sum_mm=1.0),
                t_mm=t_mm, family=family, t_rule=t_rule, **{'pass': passed})


def selector_synthetic():
    L = f'{LIB}/x.glb'
    cases = []
    # 1 shell best rank, program t2.5 passes, library: pick program
    rows = [_row('/a/shell_t1.5.glb', 'shell', 0.1), _row('/a/prog_t1.5.glb', 'program', 0.2, t_mm=1.5, family='p'),
            _row('/a/prog_t2.5.glb', 'program', 0.5, t_mm=2.5, family='p'), _row('/a/prog_t4.0.glb', 'program', 0.9, t_mm=4.0, family='p'),
            _row(L, 'library', 0.8), _row('/a/inc.glb', 'incumbent', 0.05)]
    cases.append(('shell_t_incumbent_not_picked', G.select(rows)['pick'] == '/a/prog_t2.5.glb'))
    # 2 program t2.5 fails, t1.5 passes and ranks best: pick library
    rows = [_row('/a/prog_t1.5.glb', 'program', 0.2, t_mm=1.5, family='p'),
            _row('/a/prog_t2.5.glb', 'program', 0.5, passed=False, t_mm=2.5, family='p'), _row(L, 'library', 0.8),
            _row('/a/shell.glb', 'shell', 0.1)]
    cases.append(('fallback_when_mid_fails', G.select(rows)['pick'] == L))
    # 3 measured family without a 2.5 build: closest to 2.5 stands for it
    rows = [_row('/a/m_t1.5.glb', 'program', 0.3, t_mm=1.5, family='m', t_rule='measured'),
            _row('/a/m_t4.0.glb', 'program', 0.2, t_mm=4.0, family='m', t_rule='measured'), _row(L, 'library', 0.8)]
    cases.append(('measured_family_closest', G.select(rows)['pick'] == '/a/m_t1.5.glb'))
    # 4 unmeasured family without a 2.5 build: nothing selectable but the library
    rows = [_row('/a/n_t1.5.glb', 'program', 0.3, t_mm=1.5, family='n'), _row(L, 'library', 0.8)]
    cases.append(('no_mid_build_library', G.select(rows)['pick'] == L))
    # 5 two programs at 2.5: the better rank wins; a row with no kind is diagnostic
    rows = [_row('/a/p_t2.5.glb', 'program', 0.5, t_mm=2.5, family='p'), _row('/a/q_t2.5.glb', 'dsl', 0.4, t_mm=2.5, family='q'),
            _row('/a/nokind.glb', None, 0.01), _row(L, 'library', 0.8)]
    cases.append(('two_programs_rank', G.select(rows)['pick'] == '/a/q_t2.5.glb'))
    # 6 multi-episode: must pass on every episode
    rows = [_row('/a/p_t2.5.glb', 'program', 0.5, t_mm=2.5, family='p', ep=1),
            _row('/a/p_t2.5.glb', 'program', 0.5, passed=False, t_mm=2.5, family='p', ep=2), _row(L, 'library', 0.8)]
    cases.append(('multi_episode_all_pass', G.select(rows)['pick'] == L))
    return dict(test='g_selector_v3_synthetic', cases=dict(cases), **{'pass': all(v for _, v in cases)})


# ---------------------------------------------------------------------------------------- dev (development check)
def dev():
    out = f'{OUT}/dev_rows.jsonl'
    ddir = f'{OUT}/dev_edits'
    meta = dict(stage='dev', start=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), code_sha256=code_sha(),
                thresholds=G.THRESHOLDS)
    jl(f'{OUT}/dev_meta.jsonl', meta)
    libs_done = set()
    for case, obj, ep, mesh, kind in DEV:
        if not os.path.isfile(mesh):
            log('missing', mesh); continue
        o = io_gt.load_obs(io_gt.obs_path(obj, ep), keys=('pts', 'cam'))
        tag = f'{case}_{kind}'
        edits, info = make_edits(mesh, o['pts'], o['cam'], ddir, tag)
        todo = [('base', mesh)] + list(edits.items())
        if obj not in libs_done:
            todo.append(('library', G.lib_path(obj))); libs_done.add(obj)
        for nm, p in todo:
            ev = G.evaluate(p, None, obj, ep, flip=False)
            ev.pop('per_frame'); ev.pop('thresholds')
            m = ev['metrics']
            row = dict(case=case, base_kind=kind, edit=nm, mesh=p, failed=[g for g, v in ev['gates'].items() if not v and g != 'G_FLIP'],
                       rank=ev['rank_score'], edit_info=info if nm == 'base' else None,
                       **{k: m.get(k) for k in ('dr_comp', 'dr_hole3d', 'dr_viol', 'dr_fsv', 'dr_out_share', 'dr_fsv_of_out',
                                                'fs_frac', 'align_t_mm', 'align_rot_deg', 'align_res_mm', 'frame_med_mm',
                                                'conn_share', 'topo_budget_watertight', 'topo_area_change',
                                                'topo_budget_bodies', 'topo_raw_bodies', 'topo_budget_faces')},
                       sec=ev['sec'])
            jl(out, row); log(json.dumps(row, default=str))


# ---------------------------------------------------------------------------------------- prereg
def prereg():
    if os.path.exists(PREREG):
        raise SystemExit(f'{PREREG} exists: the pre-registration is frozen; write a new version instead')
    cases = []
    for case, obj, ep, base, prog, split in HELDOUT:
        exp = []
        if base == 'program':
            exp.append(dict(row='base', expect='MUST_PASS', rule='pass is True (all 8 gates, flip check run)'))
        else:
            exp.append(dict(row='base', expect='MUST_PASS_OBSERVED', rule='G_COMP, G_HOLE, G_PREC, G_FS, G_FRAME pass '
                            '(on the observed surface by construction); G_CONN, G_TOPO, G_FLIP recorded'))
        for e, spec in EDITS.items():
            exp.append(dict(row=e, expect='MUST_FAIL', rule=f'pass is False AND at least one of {spec["detect"]} fails '
                            'on the edit while it passed on the base (detected by the intended gate)'))
        exp.append(dict(row='library', expect='FALLBACK', rule='always eligible; gates recorded'))
        sel = ('pick in {base, library}; never an edit; pick = base when base passes and ranks above the library'
               if base == 'program' else 'pick = library (the base shell is diagnostic, edits of it too)')
        exp.append(dict(row='select', expect=sel))
        cases.append(dict(case=case, obj=obj, ep=ep, base=base, program=prog, split=split, expectations=exp))
    doc = dict(
        name='prereg_gates_v3', written=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        gates_py_sha256=sha(f'{HERE}/gates.py'), test_gates_py_sha256=sha(f'{HERE}/test_gates.py'),
        io_gt_py_sha256=sha(f'{HERE}/io_gt.py'), thresholds=G.THRESHOLDS,
        held_out_rule='objects / episodes not used to tune v1 / v2 (v1/v2 tuning and validation used dust pan 39, pot '
                      '41, lid 2 (all frames), rack 13, cup 21 / 22; the v2 noise study used 8 episodes of which sweeper '
                      '31 and pitcher 22 / boards 23 overlap in object only); lid 2 is held out by a frame split',
        observations='RAW obs files (gates v3 default); lid2odd: build on even-rank frames of ep2, judge on odd-rank frames',
        base_build=dict(program='autokit.program.run_program(program as written, obs, t=0.0025, lib=library_v3, budget=4000)',
                        shell='autokit.shell.thin_shell(obs, t=0.0025) (default max_faces 4000)'),
        edit_frame=EDIT_FRAME, edits=EDITS,
        flip='flip check run on base and library rows; edit rows reuse the base row\'s flip result (no edit is meant '
             'for G_FLIP)',
        selector='gates.select v3 over {base, edits (kind program, own family, t 2.5), library} per case; shell bases '
                 'and their edits carry kind shell (diagnostic)',
        verdict_rule='each row met / not met as stated; reported in full, expected vs observed; thresholds and code '
                     'are NOT changed after the run (a mismatch of gates.py sha256 aborts the run)',
        labels='synthetic, GT-free; no label from any scan score', cases=cases)
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, open(PREREG, 'w'), indent=1)
    print(json.dumps(dict(prereg=PREREG, gates_py_sha256=doc['gates_py_sha256'], n_cases=len(cases))))


# ---------------------------------------------------------------------------------------- heldout
def split_frames(frame):
    u = np.unique(frame)
    return u[0::2], u[1::2]


def build_base(case, obj, ep, base, prog, split, bdir):
    """Base mesh of one held-out case (pre-registered build). Returns (path, report)."""
    p = f'{bdir}/{case}_base.glb'; jp = p[:-4] + '.json'
    if os.path.isfile(p) and os.path.isfile(jp):
        return p, json.load(open(jp))
    o = io_gt.load_obs(io_gt.obs_path(obj, ep))
    if split:
        ev, _ = split_frames(o['frame'])
        sel = np.isin(o['frame'], ev)
        o = {k: (v[sel] if k in ('pts', 'cam', 'frame') else v) for k, v in o.items()}
    t0 = time.time()
    if base == 'program':
        from autokit.program import run_program, load_program, jsonable
        m, rep = run_program(load_program(f'{PROG_DIR}/{prog}'), o, t=0.0025, lib=G.lib_path(obj), budget=4000)
        rep = jsonable(rep)
    else:
        from autokit.shell import thin_shell
        m, rep = thin_shell(o, t=0.0025, return_report=True)
        rep = json.loads(json.dumps(rep, default=str))
    m.metadata.pop('shell_report', None)
    m.export(p)
    rep = dict(sec=round(time.time() - t0, 1), faces=int(len(m.faces)), verts=int(len(m.vertices)),
               watertight=bool(m.is_watertight), area_cm2=round(float(m.area) * 1e4, 2), report=rep)
    json.dump(rep, open(jp, 'w'), indent=1, default=str)
    return p, rep


def heldout(stage='all', shard='0/1'):
    pre = json.load(open(PREREG))
    cur = sha(f'{HERE}/gates.py')
    if cur != pre['gates_py_sha256']:
        raise SystemExit(f'gates.py sha256 {cur} != pre-registered {pre["gates_py_sha256"]}: aborting')
    i_sh, n_sh = map(int, shard.split('/'))
    bdir, edir = f'{OUT}/heldout/base', f'{OUT}/heldout/edits'
    os.makedirs(bdir, exist_ok=True)
    meta = dict(stage=f'heldout:{stage}', shard=shard, start=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                gates_py_sha256=cur, code_sha256=code_sha(), argv=sys.argv, host=os.uname().nodename)
    jl(f'{OUT}/heldout_meta.jsonl', meta); log(json.dumps(meta))
    for k, (case, obj, ep, base, prog, split) in enumerate(HELDOUT):
        if k % n_sh != i_sh:
            continue
        if stage in ('all', 'build'):
            t0 = time.time()
            try:
                p, rep = build_base(case, obj, ep, base, prog, split, bdir)
                log('built', case, json.dumps({k2: rep[k2] for k2 in ('sec', 'faces', 'verts', 'watertight', 'area_cm2')}))
                jl(f'{OUT}/heldout_builds.jsonl', dict(case=case, mesh=p, **{k2: rep[k2] for k2 in ('sec', 'faces', 'verts', 'watertight', 'area_cm2')}))
            except Exception as e:  # noqa: BLE001
                import traceback
                jl(f'{OUT}/heldout_builds.jsonl', dict(case=case, error=f'{type(e).__name__}: {e}'[:500],
                                                       trace=traceback.format_exc()[-1500:], sec=round(time.time() - t0, 1)))
                log('BUILD FAILED', case, e)
        if stage in ('all', 'eval'):
            eval_case(case, obj, ep, base, prog, split, bdir, edir)


def eval_case(case, obj, ep, base, prog, split, bdir, edir):
    bp = f'{bdir}/{case}_base.glb'
    rows_path = f'{OUT}/heldout_rows.jsonl'
    if not os.path.isfile(bp):
        jl(rows_path, dict(case=case, row='base', error='no base mesh (build failed)')); return
    o = io_gt.load_obs(io_gt.obs_path(obj, ep), keys=('pts', 'cam', 'frame'))
    frames = None
    if split:
        ev_f, od_f = split_frames(o['frame'])
        sel = np.isin(o['frame'], ev_f)
        Pb, Cb = o['pts'][sel], o['cam'][sel]
        frames = od_f.tolist()
    else:
        Pb, Cb = o['pts'], o['cam']
    edits, info = make_edits(bp, Pb, Cb, edir, case)
    kind = 'program' if base == 'program' else 'shell'
    rows = []

    def ev_row(rowname, path, flip_metrics=None, rkind=kind, family=None):
        r = G.evaluate(path, None, obj, ep, flip=flip_metrics is None, frames=frames, flip_metrics=flip_metrics)
        r.pop('per_frame'); r.pop('thresholds')
        r.update(case=case, row=rowname, kind=rkind, t_mm=2.5 if rkind == 'program' else None,
                 family=family, fallback=(rkind == 'library'))
        jl(rows_path, r)
        m = r['metrics']
        log(case, rowname, 'PASS' if r['pass'] else 'fail', [g for g, v in r['gates'].items() if not v], 'rank',
            r['rank_score'], json.dumps({k: m.get(k) for k in ('dr_comp', 'dr_hole3d', 'dr_viol', 'dr_fsv', 'align_t_mm',
                                                                'frame_med_mm', 'conn_share', 'topo_area_change')}), r['sec'])
        rows.append(r)
        return r
    fam = (prog or 'shell')[:-5] if prog else 'shell'
    b = ev_row('base', bp, family=fam)
    flipm = {k: b['metrics'].get(k) for k in G.FLIP_KEYS}
    for e, p in edits.items():
        ev_row(e, p, flip_metrics=flipm, family=f'{fam}+edit_{e}')
    ev_row('library', G.lib_path(obj), rkind='library')
    sel = G.select(rows)
    name_of = {r['mesh']: r['row'] for r in rows}
    jl(f'{OUT}/heldout_select.jsonl', dict(case=case, edit_info=info, pick=name_of.get(sel['pick']),
                                           ranking=[name_of.get(x) for x in sel['ranking']],
                                           reasons={name_of[k]: v for k, v in sel['reasons'].items()}))
    log(case, 'PICK', name_of.get(sel['pick']), [name_of.get(x) for x in sel['ranking']])


def verdicts():
    """Expected vs observed for every pre-registered row (reads heldout_rows / heldout_select; no evaluation)."""
    pre = json.load(open(PREREG))
    rows = {}
    for l in open(f'{OUT}/heldout_rows.jsonl'):
        r = json.loads(l); rows[(r['case'], r['row'])] = r
    sels = {json.loads(l)['case']: json.loads(l) for l in open(f'{OUT}/heldout_select.jsonl')}
    out = []
    obs_gates = ('G_COMP', 'G_HOLE', 'G_PREC', 'G_FS', 'G_FRAME')
    for c in pre['cases']:
        base = rows.get((c['case'], 'base'))
        for e in c['expectations']:
            nm = e['row']; v = dict(case=c['case'], row=nm, expect=e['expect'])
            if nm == 'select':
                s = sels.get(c['case'])
                if s is None:
                    v.update(observed='missing', met=False)
                else:
                    pick = s['pick']
                    if c['base'] == 'program':
                        lib_rank = s['reasons'].get('library', {}).get('rank')
                        b_r = s['reasons'].get('base', {})
                        want = 'base' if (b_r.get('passed') and b_r.get('rank') is not None and
                                          (lib_rank is None or b_r['rank'] < lib_rank)) else None
                        met = pick in ('base', 'library') and (want is None or pick == want)
                    else:
                        met = pick == 'library'
                    v.update(observed=dict(pick=pick, ranking=s['ranking']), met=bool(met))
                out.append(v); continue
            r = rows.get((c['case'], nm))
            if r is None or 'gates' not in r:
                v.update(observed='missing' if r is None else r.get('error'), met=False); out.append(v); continue
            failed = [g for g, ok in r['gates'].items() if not ok]
            if e['expect'] == 'MUST_PASS':
                met = r['pass']
            elif e['expect'] == 'MUST_PASS_OBSERVED':
                met = all(r['gates'][g] for g in obs_gates)
            elif e['expect'] == 'MUST_FAIL':
                det = EDITS[nm]['detect']
                bgates = base['gates'] if base and 'gates' in base else {}
                hit = [g for g in det if not r['gates'][g] and bgates.get(g, False)]
                met = (not r['pass']) and bool(hit)
                v['detected_by'] = hit
            else:
                met = True
            m = r['metrics']
            v.update(observed=dict(passed=r['pass'], failed=failed, rank=r['rank_score'],
                                   **{k: m.get(k) for k in ('dr_comp', 'dr_hole3d', 'dr_viol', 'dr_fsv', 'align_t_mm',
                                                            'frame_med_mm', 'conn_share', 'fs_frac', 'topo_area_change',
                                                            'topo_budget_watertight', 'flips')}), met=bool(met))
            out.append(v)
    p = f'{OUT}/heldout_verdicts.jsonl'
    if os.path.exists(p):
        os.replace(p, p + f'.prev{int(time.time())}')
    for v in out:
        jl(p, v)
    n = len(out); k = sum(v['met'] for v in out)
    summ = dict(n_expectations=n, met=k, not_met=[(v['case'], v['row'], v['expect']) for v in out if not v['met']])
    json.dump(summ, open(f'{OUT}/heldout_summary.json', 'w'), indent=1)
    print(json.dumps(summ, indent=1))


# ---------------------------------------------------------------------------------------- noise (v2, kept)
def consensus_dz(ks, zs, ko, zo, win=0.02):
    """Per observed point: signed depth offset to the MEDIAN depth of the other frames' points in the same cell within
    +-win (nan if none). Sorted (cell, depth) order: the window is a contiguous slice, its middle element the median."""
    o = np.lexsort((zs, ks)); comb = ks[o].astype(np.float64) * 16.0 + zs[o]; zsr = zs[o]
    lo = np.searchsorted(comb, ko * 16.0 + zo - win); hi = np.searchsorted(comb, ko * 16.0 + zo + win)
    n = hi - lo
    mid = np.clip((lo + hi - 1) // 2, 0, max(len(comb) - 1, 0))
    return np.where(n >= 3, zo - zsr[mid], np.nan), n


def noise():
    """Leave-frames-out self-consistency of the observations: no mesh involved."""
    out = f'{OUT}/noise.jsonl'
    calib = io_gt.load_calib(); K, (W, H) = calib['K'], calib['size']
    wc, hc = int(np.ceil(W / G.CELL_PX)), int(np.ceil(H / G.CELL_PX))
    for obj, ep in NOISE_SET:
        t0 = time.time()
        p = io_gt.obs_path(obj, ep)
        o = io_gt.load_obs(p, keys=('pts', 'frame'))
        P = o['pts'].astype(np.float64); F = o['frame']
        T, _ = G.frame_cams(p, obj, ep)
        rng = np.random.default_rng(0)
        dz_all = []
        for f in G.pick_frames(F):
            own = F == f
            other = np.nonzero(np.abs(F - f) > 4)[0]
            other = other[rng.choice(len(other), min(600_000, len(other)), replace=False)]
            io_, ko, cuo, cvo, zo = G._project(P[own], T[f], K, wc, hc)
            _, ks, _, _, zs = G._project(P[other], T[f], K, wc, hc)
            dz, n = consensus_dz(ks, zs, ko, zo)
            dz_all.append(dz)
        dz = np.concatenate(dz_all); fin = np.abs(dz[np.isfinite(dz)])
        r = dict(obj=obj, ep=ep, obs=os.path.basename(p), n=int(len(dz)), judged=round(float(np.isfinite(dz).mean()), 4),
                 absdz_mm_p50=round(float(np.percentile(fin, 50)) * 1e3, 2), absdz_mm_p90=round(float(np.percentile(fin, 90)) * 1e3, 2),
                 sec=round(time.time() - t0, 1))
        jl(out, r); print(json.dumps(r), flush=True)


# ---------------------------------------------------------------------------------------- audit
def audit():
    """(e) runtime integrity: one full gates.py eval (flip check included) under strace; no successful open may
    match the GT patterns. Data files opened are listed."""
    import subprocess
    lg = f'{OUT}/audit_strace.log'
    mesh = f'{S}/auto/stage1/integ/white_pot_lid_ep2/cand/dsl_sheet_strap_balls_t2.5.glb'
    cmd = ['strace', '-f', '-qq', '-e', 'trace=openat,open,openat2,execve', '-o', lg, sys.executable, '-I', '-W', 'ignore',
           f'{HERE}/gates.py', 'eval', mesh, 'white_pot_lid', '2', '--kind', 'program', '--t-mm', '2.5']
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    from autokit import run_object as RO
    a = RO.audit([lg], quiet=True)[0]
    res = dict(test='e_integrity_strace', cmd=' '.join(cmd), rc=r.returncode, sec=round(time.time() - t0, 1), **a,
               **{'pass': r.returncode == 0 and a['forbidden_non_library_ok'] == 0})
    jl(f'{OUT}/unit.jsonl', res); print(json.dumps(res, indent=1))


# ---------------------------------------------------------------------------------------- legacy
def legacy_validate():
    """v2's post-hoc validation rows re-evaluated with v3 for the record. Its MUST_PASS labels came from earlier
    SCAN-SCORED rounds (audit finding): they are reported, never used to set or judge v3."""
    out = f'{OUT}/legacy_validate_rows.jsonl'
    for grp, obj, ep, mesh, kind, exp in LEGACY_VALIDATE:
        if not os.path.exists(mesh):
            continue
        ev = G.evaluate(mesh, None, obj, ep, flip=False)
        ev.pop('per_frame'); ev.pop('thresholds')
        ev.update(group=grp, kind=kind, expect_legacy_scan_derived=exp)
        jl(out, ev)
        print(json.dumps(dict(group=grp, mesh=os.path.basename(mesh), failed=[k for k, v in ev['gates'].items() if not v])))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['unit', 'dev', 'prereg', 'heldout', 'verdicts', 'noise', 'audit', 'legacy_validate'])
    ap.add_argument('--shard', default='0/1'); ap.add_argument('--part', default='all', choices=['all', 'build', 'eval'])
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    dict(unit=unit, dev=dev, prereg=prereg, heldout=lambda: heldout(a.part, a.shard), verdicts=verdicts, noise=noise,
         audit=audit, legacy_validate=legacy_validate)[a.stage]()
