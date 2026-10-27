"""Tests, calibration and the declared post-hoc validation of gates.py on real observed points (stage 1, builder
"gates"). GT-free: observations, tracks and calibration only through autokit/io_gt.py; meshes are our candidates,
the hand-kit incumbents and library_v3. No scan, no *_align file, no mocap, no parquet; mesh_metric.py is not run.

Stages (JSON lines under OUT = scratchpad/auto/stage1/gates/):
  unit      (a) integrity: gates.py contains no object name and no path to GT, and every file it opens in a run is
                an allow-listed kind (observations, tracks, calibration, refine corrections, meshes, kit code);
            (b) wiring: observed points re-project onto integer pixel centres with our track + K (cam_T_obj and K
                are the ones obs_points.py used; a refined copy with its correction file re-projects as well);
            (c) the obs_fidelity sum_mm of library_v3 on the old ep39 dust-pan file equals the P2 probe's 3.642;
            (d) sensitivity on synthetic edits of real meshes outside the validation set: deleting a patch of observed
                surface must lower
                dr_comp and raise dr_hole3d; adding a plate floating in front of observed surface must raise dr_viol;
                a rigid 10 mm shift must fail G_FRAME; a duplicated copy 1.5 extents away must fail G_CONN.
  noise     data-only calibration of the depth margins, run BEFORE any candidate is scored: leave-frames-out
            self-consistency of the observations (each selected frame against the other frames' points, frames
            within +-4 left out): per point, depth minus the median depth of the other frames' points in its cell
            (within +-20 mm), |dz| percentiles and the share within 3..10 mm; per-frame median offset (track jitter).
  audit     (e) runtime integrity: one full gates.py eval (flip check included) under strace; no successful open
            may match the GT patterns; the data files opened are listed.
  validate  the declared post-hoc validation (expected outcomes stated in EXPECT before the run): P2 negative
            controls, P2 picks, P1 fragmented picks, hand-kit incumbents and library_v3; then select() per group.
Object names appear only in the driver input tables below.
Usage: python test_gates.py {unit|noise|audit|validate} [--no-flip]
"""
import argparse, glob, hashlib, json, os, re, sys, time

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit import io_gt  # noqa: E402
from autokit import gates as G  # noqa: E402

S = io_gt.SCRATCH
OUT = f'{S}/auto/stage1/gates'
LIB = G.LIB_DIR
RES = '/home/user/v2d-track3/docs/research/mesh-2026-10-26/results/prim/meshes'
P1 = f'{S}/auto/probe_P1-pot-blind-rediscovery/run1'
P2 = f'{S}/auto/probe_P2-dustpan-new-object/dustpan'

# ---------------------------------------------------------------------------------------- driver input tables
NOISE_SET = [('mini_dust_pan', 39), ('white_pot', 41), ('white_pot_lid', 2), ('plastic_dish_rack', 13),
             ('blue_cup', 21), ('mini_sweeper', 31), ('water_pitcher', 22), ('wooden_piece_1', 23)]
# (group, obj, ep, mesh, kind, expectation) - expectations written before the validation run
VALIDATE = [
    ('dustpan', 'mini_dust_pan', 39, f'{LIB}/mini_dust_pan.glb', 'library', 'fallback'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_NC_no_largest_wall.glb', 'P2_negative_control', 'MUST_FAIL'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_NC_floor_only.glb', 'P2_negative_control', 'MUST_FAIL'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_PS_t2.5.glb', 'P2_pick', 'FAIL_OR_BELOW_LIBRARY'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_PS_t1.5.glb', 'P2_pick_t', 'FAIL_OR_BELOW_LIBRARY'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_PS_t4.0.glb', 'P2_pick_t', 'FAIL_OR_BELOW_LIBRARY'),
    ('dustpan', 'mini_dust_pan', 39, f'{P2}/dustpan_PS0_t2.5.glb', 'P2_plates_only', 'record'),
    ('pot', 'white_pot', 41, f'{LIB}/white_pot.glb', 'library', 'fallback'),
    ('pot', 'white_pot', 41, f'{RES}/white_pot_ep41_fit.glb', 'incumbent', 'MUST_PASS'),
    ('pot', 'white_pot', 41, f'{P1}/lathe_fap_f2.glb', 'P1_fragmented_pick', 'FAIL_OR_BELOW_LIBRARY'),
    ('pot', 'white_pot', 41, f'{P1}/lathe_pap_f0.glb', 'P1_fragmented', 'FAIL_OR_BELOW_LIBRARY'),
    ('pot', 'white_pot', 41, f'{P1}/lathe_pap_f2.glb', 'P1_fragmented', 'FAIL_OR_BELOW_LIBRARY'),
    ('pot', 'white_pot', 41, f'{P1}/lathe_fap_f1_ctl.glb', 'P1_control', 'record'),
    ('lid', 'white_pot_lid', 2, f'{LIB}/white_pot_lid.glb', 'library', 'fallback'),
    ('lid', 'white_pot_lid', 2, f'{RES}/white_pot_lid_ep2_fit_v2.glb', 'incumbent', 'MUST_PASS'),
    ('rack', 'plastic_dish_rack', 13, f'{LIB}/plastic_dish_rack.glb', 'library', 'fallback'),
    ('rack', 'plastic_dish_rack', 13, f'{S}/prim/clean/rack/t2.5_lean1/plastic_dish_rack/ep13_full.glb', 'incumbent',
     'MUST_PASS'),
    ('cup', 'blue_cup', 21, f'{LIB}/blue_cup.glb', 'library', 'fallback'),
    ('cup', 'blue_cup', 21, f'{S}/lathe/ep21_blue_cup_g1.glb', 'incumbent', 'MUST_PASS'),
]
FORBIDDEN_RE = re.compile(r'/loc/|/scan|_align|\.parquet|mocap', re.I)


def jl(path, d):
    with open(path, 'a') as f:
        f.write(json.dumps(d, default=str) + '\n')


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ---------------------------------------------------------------------------------------- unit
def unit():
    out = f'{OUT}/unit.jsonl'
    src = open(f'{HERE}/gates.py').read()
    # (a) no object names / object words in identifiers, string constants or comments; no GT path in any string
    #     constant that is not a docstring (the docstrings state the GT-free rules and name the refused kinds)
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
    text = '\n'.join(consts + idents + comments + [d for d in (ast.get_docstring(tree) or '',)])
    names = sorted({os.path.splitext(os.path.basename(p))[0] for p in glob.glob(f'{LIB}/*.glb')})
    hits = [n for n in names if n in text]
    words = [w for w in ('pot', 'lid', 'rack', 'cup', 'dust', 'sweeper', 'pitcher', 'board', 'wooden', 'spoon')
             if re.search(rf'\b{w}', text, re.I)]
    gt = [c for c in consts if FORBIDDEN_RE.search(c)]
    r = dict(test='a_integrity_static', object_names=hits, object_words=words, gt_path_constants=gt,
             **{'pass': not hits and not words and not gt})
    jl(out, r); print(json.dumps(r))
    # (b) wiring: observed points of a few frames land on integer pixel centres
    K = io_gt.load_calib()['K']
    rows = []
    for obj, ep, refined in (('mini_dust_pan', 39, False), ('white_pot', 41, False), ('white_pot', 41, True)):
        p = io_gt.obs_path(obj, ep, refined=refined)
        o = io_gt.load_obs(p, keys=('pts', 'frame'))
        T, nc = G.frame_cams(p, obj, ep)
        fr = G.pick_frames(o['frame'], 6)
        offs = []
        for f in fr:
            P = o['pts'][o['frame'] == f].astype(np.float64)
            Xc = P @ T[f][:3, :3].T + T[f][:3, 3]
            u = K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2]; v = K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2]
            offs.append(np.maximum(np.abs(u - np.round(u)), np.abs(v - np.round(v))))
        offs = np.concatenate(offs)
        rows.append(dict(obs=os.path.basename(p), refined=refined, corrections=nc,
                         px_off_p50=round(float(np.median(offs)), 4), px_off_p99=round(float(np.percentile(offs, 99)), 4),
                         share_on_centre=round(float((offs < 0.05).mean()), 4)))
    r = dict(test='b_wiring_reprojection', rows=rows, **{'pass': all(x['share_on_centre'] > 0.95 for x in rows)})
    jl(out, r); print(json.dumps(r))
    # (c) fidelity reproduction
    raw = G.load_raw(f'{LIB}/mini_dust_pan.glb')
    P = io_gt.load_obs(f'{S}/obs/ep39_mini_dust_pan.npz', keys=('pts',))['pts'].astype(np.float64)
    fid = G.fidelity(raw, P)
    r = dict(test='c_fidelity_reproduction', fid_sum_mm=round(fid['fid_sum_mm'], 3), expected=3.642,
             **{'pass': abs(fid['fid_sum_mm'] - 3.642) < 0.0015})
    jl(out, r); print(json.dumps(r))
    # (d) sensitivity on synthetic edits of real meshes that are NOT in the validation set (library dust pan, the
    #     ep22 blue-cup lathe g0 on its own episode), so the validation numbers stay unseen until the validate stage
    d = f'{OUT}/synthetic'; os.makedirs(d, exist_ok=True)
    sens = []
    for obj, ep, base in (('mini_dust_pan', 39, f'{LIB}/mini_dust_pan.glb'), ('blue_cup', 22, f'{S}/lathe/ep22_blue_cup_g0.glb')):
        m = G.load_raw(base)
        p = io_gt.obs_path(obj, ep)
        o = io_gt.load_obs(p, keys=('pts', 'frame'))
        Pm = o['pts'].astype(np.float64)
        # (d1) delete a patch: faces within 3 cm of a dense observed point (seeded), keep the rest (open mesh)
        c = Pm[np.random.default_rng(1).integers(len(Pm))]
        keep = np.linalg.norm(m.triangles_center - c, axis=1) > 0.03
        cut = trimesh.Trimesh(m.vertices, m.faces[keep], process=True)
        # (d2) a 6 x 6 cm, 2.5 mm plate 15 mm in front of observed surface (towards the camera of a seed point)
        o2 = io_gt.load_obs(p, keys=('pts', 'cam'))
        i = np.random.default_rng(2).integers(len(o2['pts']))
        q = o2['pts'][i].astype(np.float64); cam = o2['cam'][i].astype(np.float64)
        nrm = (cam - q) / np.linalg.norm(cam - q)
        plate = trimesh.creation.box(extents=(0.06, 0.06, 0.0025))
        Rz = trimesh.geometry.align_vectors([0, 0, 1], nrm); plate.apply_transform(Rz)
        plate.apply_translation(q + 0.015 * nrm)
        front = trimesh.util.concatenate([m, plate])
        # (d3) rigid 10 mm shift; (d4) a duplicated copy displaced by 1.5 x the mesh's largest extent (no contact)
        shift = m.copy(); shift.apply_translation([0.010, 0, 0])
        dup = trimesh.util.concatenate([m, m.copy().apply_translation([1.5 * float(m.extents.max()), 0, 0])])
        variants = dict(base=base)
        for nm, mm in (('cut3cm', cut), ('front_plate', front), ('shift10mm', shift), ('dup_far', dup)):
            path = f'{d}/{obj}_ep{ep}_{nm}.glb'; mm.export(path); variants[nm] = path
        res = {}
        for nm, path in variants.items():
            ev = G.evaluate(path, [p], obj, ep, flip=False)
            res[nm] = {k: ev['metrics'].get(k) for k in ('dr_comp', 'dr_hole3d', 'dr_hole3d_cm2', 'dr_viol', 'fs_frac',
                                                       'conn_share', 'frame_med_mm', 'topo_raw_watertight')}
            res[nm]['gates_failed'] = [k for k, v in ev['gates'].items() if not v and k != 'G_FLIP']
        b = res['base']
        checks = dict(cut_lowers_comp=res['cut3cm']['dr_comp'] < b['dr_comp'],
                      cut_raises_hole=res['cut3cm']['dr_hole3d'] > b['dr_hole3d'],
                      front_raises_viol=res['front_plate']['dr_viol'] > b['dr_viol'],
                      shift_fails_frame='G_FRAME' in res['shift10mm']['gates_failed'],
                      dup_fails_conn='G_CONN' in res['dup_far']['gates_failed'])
        r = dict(test='d_sensitivity', obj=obj, ep=ep, res=res, checks=checks, **{'pass': all(checks.values())})
        sens.append(r); jl(out, r); print(json.dumps(r))


# ---------------------------------------------------------------------------------------- noise
def consensus_dz(ks, zs, ko, zo, win=0.02):
    """Per observed point: signed depth offset to the MEDIAN depth of the other frames' points in the same cell within
    +-win (nan if none). Sorted (cell, depth) order: the window is a contiguous slice, its middle element the median."""
    o = np.lexsort((zs, ks)); comb = ks[o].astype(np.float64) * 16.0 + zs[o]; zsr = zs[o]
    lo = np.searchsorted(comb, ko * 16.0 + zo - win); hi = np.searchsorted(comb, ko * 16.0 + zo + win)
    n = hi - lo
    mid = np.clip((lo + hi - 1) // 2, 0, max(len(comb) - 1, 0))
    return np.where(n >= 3, zo - zsr[mid], np.nan), n


def noise():
    """Leave-frames-out self-consistency of the observations: no mesh involved. dz = frame depth minus the median
    depth of the other frames' points along the same cell (within +-20 mm): track jitter + stereo noise per frame."""
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
        dz_all, fr_rows = [], []
        for f in G.pick_frames(F):
            own = F == f
            other = np.nonzero(np.abs(F - f) > 4)[0]
            other = other[rng.choice(len(other), min(600_000, len(other)), replace=False)]
            io_, ko, cuo, cvo, zo = G._project(P[own], T[f], K, wc, hc)
            _, ks, _, _, zs = G._project(P[other], T[f], K, wc, hc)
            dz, n = consensus_dz(ks, zs, ko, zo)
            dz_all.append(dz)
            fin = dz[np.isfinite(dz)]
            fr_rows.append(float(np.median(fin)) if len(fin) else np.nan)
        dz = np.concatenate(dz_all); fin = np.abs(dz[np.isfinite(dz)])
        fm = np.abs(np.array(fr_rows)); fm = fm[np.isfinite(fm)]
        r = dict(obj=obj, ep=ep, obs=os.path.basename(p), n=int(len(dz)), judged=round(float(np.isfinite(dz).mean()), 4),
                 absdz_mm_p50=round(float(np.percentile(fin, 50)) * 1e3, 2), absdz_mm_p80=round(float(np.percentile(fin, 80)) * 1e3, 2),
                 absdz_mm_p90=round(float(np.percentile(fin, 90)) * 1e3, 2), absdz_mm_p95=round(float(np.percentile(fin, 95)) * 1e3, 2),
                 within={f'{m}mm': round(float(np.mean(fin <= m / 1000)), 4) for m in (3, 4, 6, 8, 10)},
                 frame_median_offset_mm_p50=round(float(np.median(fm)) * 1e3, 2),
                 frame_median_offset_mm_p90=round(float(np.percentile(fm, 90)) * 1e3, 2), sec=round(time.time() - t0, 1))
        jl(out, r); print(json.dumps(r), flush=True)


# ---------------------------------------------------------------------------------------- validate
def validate(flip=True, refined=False, tag='run'):
    out = f'{OUT}/validate_{tag}_rows.jsonl'
    meta = dict(stage='validate', tag=tag, refined=refined, gates_sha256=sha(f'{HERE}/gates.py'), thresholds=G.THRESHOLDS, flip=flip,
                start=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    jl(f'{OUT}/validate_{tag}_meta.jsonl', meta); print(json.dumps(meta))
    rows = {}
    for grp, obj, ep, mesh, kind, exp in VALIDATE:
        if not os.path.exists(mesh):
            print('missing', mesh); continue
        ev = G.evaluate(mesh, [io_gt.obs_path(obj, ep, refined=refined)], obj, ep, flip=flip)
        ev.update(group=grp, kind=kind, expect=exp, fallback=(kind == 'library'))
        per = ev.pop('per_frame')
        jl(out, ev)
        jl(f'{OUT}/validate_{tag}_per_frame.jsonl', dict(mesh=mesh, ep=ep, per_frame=per))
        rows.setdefault(grp, []).append(ev)
        m = ev['metrics']
        print(json.dumps(dict(group=grp, mesh=os.path.basename(mesh), kind=kind, expect=exp, passed=ev['pass'],
                              failed=[k for k, v in ev['gates'].items() if not v], rank=ev['rank_score'],
                              **{k: m.get(k) for k in ('dr_comp', 'dr_viol', 'dr_hole3d', 'dr_hole3d_cm2', 'fs_frac',
                                                       'fid_sum_mm', 'conn_share', 'conn_bodies', 'frame_med_mm',
                                                       'flips', 'drift_area', 'drift_rms')}, sec=ev['sec'])), flush=True)
    verdict = []
    for grp, rs in rows.items():
        sel = G.select(rs)
        lib_rank = next(v.get('rank') for k, v in sel['reasons'].items() if v['fallback'])
        for r in rs:
            rr = sel['reasons'][r['mesh']]
            below = rr.get('rank') is None or (lib_rank is not None and rr['rank'] > lib_rank)
            ok = dict(MUST_FAIL=not r['pass'], MUST_PASS=r['pass'], FAIL_OR_BELOW_LIBRARY=(not r['pass']) or below,
                      fallback=True, record=True)[r['expect']]
            verdict.append(dict(group=grp, mesh=os.path.basename(r['mesh']), kind=r['kind'], expect=r['expect'],
                                passed=r['pass'], failed=rr['failed'], rank=rr.get('rank'), rank_score=rr['rank_score'],
                                met=bool(ok)))
        jl(f'{OUT}/validate_{tag}_select.jsonl', dict(group=grp, pick=sel['pick'], reasons=sel['reasons']))
        print(json.dumps(dict(group=grp, pick=os.path.basename(sel['pick']))))
    for v in verdict:
        jl(f'{OUT}/validate_{tag}_verdict.jsonl', v); print(json.dumps(v))
    print(json.dumps(dict(all_expectations_met=all(v['met'] for v in verdict))))


# ---------------------------------------------------------------------------------------- diag (post hoc)
def diag(lat, shard='0/1', refined=False):
    """POST-HOC sensitivity (after validate run 2 missed 3 of 4 MUST_PASS): the validation rows re-measured with a
    lateral tolerance LAT (m) for both depth tests, no flip check (flip does not depend on LAT)."""
    i, n = map(int, shard.split('/'))
    G.LAT_PREC = G.LAT_COMP = lat                  # diag runs used one reach for both tests
    for k, (grp, obj, ep, mesh, kind, exp) in enumerate(VALIDATE):
        if k % n != i or not os.path.exists(mesh):
            continue
        ev = G.evaluate(mesh, [io_gt.obs_path(obj, ep, refined=refined)], obj, ep, flip=False)
        m = ev['metrics']
        r = dict(lat=lat, refined=refined, corrections=m.get('track_corrections'), group=grp, mesh=os.path.basename(mesh), kind=kind, expect=exp,
                 failed_nonflip=[g for g, v in ev['gates'].items() if not v and g != 'G_FLIP'], rank=ev['rank_score'],
                 r_cells=sorted({p['r_prec'] for p in ev['per_frame']}),
                 **{k2: m.get(k2) for k2 in ('dr_comp', 'dr_viol', 'dr_hole3d', 'dr_hole3d_cm2', 'dr_cdist_mm',
                                             'dr_pdist_mm', 'dr_viol_frame_p90', 'dr_hole2d_p90')}, sec=ev['sec'])
        jl(f'{OUT}/diag_lat.jsonl', r); print(json.dumps(r), flush=True)


def diag_viol(mesh, obj, ep, axis_json, refined=True):
    """POST-HOC, recorded only: where the precision violations of one mesh lie, in the frame of OUR lathe fit
    (axis_json: lathe_obs.py output, centre + axis; GT-free). Height along the axis and radius of the first mesh
    surface of violating vs all judged cells, pooled over the gate's frames (same code path as gates.depth_render)."""
    import math
    from scipy import ndimage
    ax = json.load(open(axis_json)); c0 = np.array(ax['centre']); d = np.array(ax['axis']); d /= np.linalg.norm(d)
    p = io_gt.obs_path(obj, ep, refined=refined)
    o = io_gt.load_obs(p, keys=('pts', 'frame')); T_co, _ = G.frame_cams(p, obj, ep)
    calib = io_gt.load_calib(); K, (W, H) = calib['K'], calib['size']
    wc, hc = int(math.ceil(W / G.CELL_PX)), int(math.ceil(H / G.CELL_PX))
    Sm = G._samples(G.load_budget(mesh))
    allp, vp = [], []
    for f in G.pick_frames(o['frame']):
        P = o['pts'][o['frame'] == f].astype(np.float64); T = T_co[int(f)]
        io_, ko, cuo, cvo, zo = G._project(P, T, K, wc, hc)
        if len(io_) < 50:
            continue
        _, ks, _, _, zs = G._project(Sm, T, K, wc, hc)
        rp = max(1, int(math.ceil(K[0, 0] * G.LAT_PREC / (float(np.median(zo)) * G.CELL_PX))))
        mk, mz = G._cell_min(ks, zs); okey, oz = G._cell_min(ko, zo)
        u0, v0 = cuo.min() - rp, cvo.min() - rp
        Gd = np.full((cvo.max() - v0 + rp + 1, cuo.max() - u0 + rp + 1), np.inf); Gd[okey // wc - v0, okey % wc - u0] = oz
        fp = np.zeros((2 * rp + 1, 2 * rp + 1), bool)
        for dv, du in G.disk(rp):
            fp[dv + rp, du + rp] = True
        Gm = ndimage.minimum_filter(Gd, footprint=fp, mode='constant', cval=np.inf)
        common, im, _ = np.intersect1d(mk, okey, assume_unique=True, return_indices=True)
        viol = (Gm[common // wc - v0, common % wc - u0] - mz[im]) > G.M_PREC
        uu = (common % wc + 0.5) * G.CELL_PX; vv = (common // wc + 0.5) * G.CELL_PX; z = mz[im]
        Xc = np.stack([(uu - K[0, 2]) * z / K[0, 0], (vv - K[1, 2]) * z / K[1, 1], z], 1)
        Ti = np.linalg.inv(T); X = Xc @ Ti[:3, :3].T + Ti[:3, 3]
        allp.append(X); vp.append(viol)
    X = np.concatenate(allp); V = np.concatenate(vp)
    h = (X - c0) @ d; r = np.linalg.norm((X - c0) - h[:, None] * d, axis=1)
    hb = np.percentile(h, [0, 20, 40, 60, 80, 100]); rb = np.percentile(r, [0, 20, 40, 60, 80, 100])
    out = dict(test='diag_viol', mesh=os.path.basename(mesh), ep=ep, n_judged=int(len(V)), viol=round(float(V.mean()), 4),
               by_height_quintile=[dict(h_mm=[round(hb[i] * 1e3, 1), round(hb[i + 1] * 1e3, 1)],
                                        viol=round(float(V[(h >= hb[i]) & (h <= hb[i + 1])].mean()), 4)) for i in range(5)],
               by_radius_quintile=[dict(r_mm=[round(rb[i] * 1e3, 1), round(rb[i + 1] * 1e3, 1)],
                                        viol=round(float(V[(r >= rb[i]) & (r <= rb[i + 1])].mean()), 4)) for i in range(5)])
    jl(f'{OUT}/diag_viol.jsonl', out); print(json.dumps(out, indent=1))


# ---------------------------------------------------------------------------------------- audit
def audit():
    """(e) runtime integrity: one full evaluate (flip check included) under strace; every openat that succeeded is
    listed; none may match the GT patterns. Data files opened are written out for the record."""
    import subprocess
    log = f'{OUT}/audit_strace.log'
    cmd = ['strace', '-f', '-qq', '-e', 'trace=openat', '-o', log, sys.executable, '-I', '-W', 'ignore',
           f'{HERE}/gates.py', 'eval', f'{P2}/dustpan_NC_no_largest_wall.glb', 'mini_dust_pan', '39']
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    opened = []
    for line in open(log):
        if 'openat(' in line and 'ENOENT' not in line:
            m = re.search(r'openat\([^"]*"([^"]+)"', line)
            if m:
                opened.append(m.group(1))
    opened = sorted(set(opened))
    # interpreter files are exempt from the pattern (json/__pycache__/scanner.*.pyc matches '/scan'); data files are not
    bad = [p for p in opened if FORBIDDEN_RE.search(p) and '/lib/python3' not in p and 'site-packages' not in p]
    data = [p for p in opened if re.search(r'\.(npz|npy|glb|json|jsonl|parquet|csv|mp4|png)$', p) and 'site-packages' not in p
            and '/lib/python' not in p]
    res = dict(test='e_integrity_strace', cmd=' '.join(cmd), rc=r.returncode, sec=round(time.time() - t0, 1),
               n_opened=len(opened), forbidden=bad, data_files=data, **{'pass': r.returncode == 0 and not bad})
    jl(f'{OUT}/unit.jsonl', res); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['unit', 'noise', 'validate', 'audit', 'diag', 'diag_viol'])
    ap.add_argument('--no-flip', action='store_true')
    ap.add_argument('--lat', type=float, default=0.006); ap.add_argument('--shard', default='0/1')
    ap.add_argument('--refined', action='store_true'); ap.add_argument('--tag', default='run')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    dict(unit=unit, noise=noise, audit=audit, diag=lambda: diag(None if a.lat <= 0 else a.lat, a.shard, a.refined),
         diag_viol=lambda: [diag_viol(m, 'blue_cup', 21, f'{S}/lathe/ep21_blue_cup_g1.lathe.json') for m in
                            (f'{S}/lathe/ep21_blue_cup_g1.glb', f'{LIB}/blue_cup.glb')],
         validate=lambda: validate(flip=not a.no_flip, refined=a.refined, tag=a.tag))[a.stage]()
