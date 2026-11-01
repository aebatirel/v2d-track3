"""Leak decomposition, CPU tests (a) and (b) of PLAN.md §7 for the frame tools (B1 tools/xstar_fit.py, B2
pipeline/frame_xform.py). ORACLE SIDE: reads mocap and the public scans; public episodes only; nothing here feeds inference.
(a) 1. mocap (scan frames) with the public scan as the submitted mesh, packed by the kit's own pack_object_meshes and
       scored by the UNMODIFIED official metric metric_code/track_3/AUC.py score() against a host solution built from
       mocap + scan (stand-ins as score_registered.py; its 16 MB decode limit raised only for this full-resolution
       stand-in, as refcheck/scorer/kit_e2e.py does): must be 1.000.
    2. mocap @ X_kit (lib frames) with library_v3 submitted: must be 1.000 (the kit's registration inverts exactly).
    3. mocap @ X*_geom (lib frames) with library_v3 submitted: the leaderboard (lib) score of PERFECT motion, i.e. L1 of
       a perfect track. Reported, no pass rule.
    4. lib -> scan -> lib round trip through frame_xform.py on refine/in poses.npz + poses_world_vo.npz: max |delta| < 1e-6,
       world_T_cam byte-identical.
(b) 1. T* two ways on the refine/in tracks: (i) frame_xform.py --to scan writes scan-frame poses, scored by the kit's
       chain with the full-resolution scan as the candidate mesh (the kit's own _register_object_body then returns the
       identity, checked); (ii) in process, lib-frame poses with X*_geom itself as the registration
       (xstar_fit.score_track). Rule: |delta| <= 0.002 per episode and object. Reported beside it, no rule: (i') the same
       file through pipeline/score_registered.py, whose candidate is the 4096-face budgeted scan, so the kit's scan->scan
       registration noise is included. Also (0): the in-process chain with the kit registration ==
       score_registered.py --meshes LIB (the lib column).
    2. cup spin: (ii) with X*_geom spun by 45/90/145/180 deg about the scan axis: |delta T*| <= 0.002.
    3. ambiguity, no rule: T* with an object's X*_geom replaced by each rival surface-fit minimum within xstar_fit.AMBIG
       of the best. X*_geom keeps the best whatever this says (a choice made from mocap would be X*_trk, not X*_geom).
    4. with --xtrk: the same two ways for T_trk (frame_xform.py on xstar_trk.json vs in process), |delta| <= 0.002, and
       equal to the trk score recorded in xstar_trk.json; plus the round trip of (a) 4 through the trk file.
(a) 3 is also recomputed in process (the lib chain of xstar_fit.score_track on the full mocap): must equal the official.
Usage: python -I frames_check.py --xgeom xstar_geom.json --perc REFINE_IN --lib LIB --t3 T3 --kit KIT --work DIR
       --out frames_check.json [--xtrk xstar_trk.json] [--episodes 0,2,...] [--jobs 4]
       (DIR must contain 'oracle', see frame_xform.py)
(2026-10-30; (a) 3 in process, (b) 3-4 and --xtrk added 2026-10-30 evening)
"""
import argparse, importlib.util, json, os, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools')); sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import xstar_fit as XF       # noqa: E402
import frame_xform as FX     # noqa: E402

PUBLIC = XF.PUBLIC
CUPS = {'beige_cup', 'blue_cup'}
POSE = ['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']
PROV = dict(eval_script_sha256='0' * 64, eval_code_sha256='0' * 64, checkpoint_sha256='0' * 64, packer_script_sha256='0' * 64,
            uploader_script_sha256='0' * 64, code_commit_url='https://github.com/example/example/commit/' + '0' * 40)
p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--xgeom', required=True); p.add_argument('--perc', required=True); p.add_argument('--lib', required=True)
p.add_argument('--t3', required=True); p.add_argument('--kit', required=True); p.add_argument('--work', required=True)
p.add_argument('--out', required=True); p.add_argument('--episodes', default=','.join(map(str, PUBLIC)))
p.add_argument('--jobs', type=int, default=4)
p.add_argument('--xtrk', default=None, help='xstar_trk.json: also check the trk path (b) 4')
a = p.parse_args()
if 'oracle' not in os.path.abspath(a.work):
    sys.exit('--work must contain "oracle" (frame_xform.py writes there)')


def auc_module():  # the official metric file, unmodified; only its decode limit is raised for the full public scans
    spec = importlib.util.spec_from_file_location('kaggle_auc', f'{a.kit}/metric_code/track_3/AUC.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    orig = mod._decode_archive
    mod._decode_archive = lambda text, maximum_bytes=2_000_000, _o=orig: _o(text, max(maximum_bytes, 10 ** 9))
    return mod


def solution(ep, names, gt, H):  # host side: mocap reference rows + one geometry payload (kit_e2e.py's stand-ins)
    geo = {'names': np.array(names)}
    for i, n in enumerate(names):
        v, f = H[i]['mesh']
        geo.update({f'v{i}': v, f'f{i}': f, f'anchor{i}': H[i]['anchor'], f'points{i}': H[i]['points'] + H[i]['anchor'],
                    f'axis{i}': H[i]['axis'], f'order{i}': np.int64(H[i]['order'])})
    N = len(gt[names[0]]); rows = []
    for fr in range(N):
        for s, n in enumerate(names):
            q = XF.to7(gt[n][fr])
            rows.append(dict(row_id=f'track_3/e{ep:06d}/w000/f{fr:06d}/o{s}', episode_index=ep, world_index=0, frame_index=fr,
                             object_slot=s, object_name=n, **{f'ref_{c}': q[j] for j, c in enumerate(POSE)}))
    sol = pd.DataFrame(rows); sol['reference_geometry_b64'] = ''
    sol.loc[0, 'reference_geometry_b64'] = XF.K['T3']._encode_archive(**geo)
    return sol


def submission(ep, names, track, mesh_root):  # participant side: pose rows + the kit's own mesh packing
    from v2dlb.track3_pose import pack_object_meshes
    N = len(track[names[0]]); rows = []
    for fr in range(N):
        for s, n in enumerate(names):
            q = XF.to7(track[n][fr])
            rows.append(dict(row_id=f'track_3/e{ep:06d}/w000/f{fr:06d}/o{s}', **{c: q[j] for j, c in enumerate(POSE)}, **PROV))
    return pack_object_meshes(pd.DataFrame(rows), mesh_root, {str(ep): names})


def link_meshes(root, ep, names, src):  # ROOT/episode_XXXXXX/<name>.glb -> src(name)
    d = f'{root}/episode_{ep:06d}'; os.makedirs(d, exist_ok=True)
    for n in names:
        if not os.path.lexists(f'{d}/{n}.glb'):
            os.symlink(os.path.abspath(src(n)), f'{d}/{n}.glb')
    return root


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'{" ".join(cmd)}\n{r.stdout[-1500:]}{r.stderr[-1500:]}')
    return r.stdout


def episode(ep):
    import contextlib, io
    XF.kit(a.kit); t0 = time.time()
    W = f'{a.work}/ep{ep}'; os.makedirs(W, exist_ok=True)
    V = np.load(f'{a.perc}/ep{ep}/poses_world_vo.npz')
    names, gt_full = XF.mocap(a.t3, ep)
    H = [XF.host_geometry(a.t3, n, s) for s, n in enumerate(names)]
    Xg, _ = FX.load_xform(a.xgeom, ep, names)
    Xk = {n: XF.kit_X(f'{a.lib}/{n}.glb', H[s], ep, s)[0] for s, n in enumerate(names)}
    r = dict(episode=ep, objects=names, frames_mocap=len(gt_full[names[0]]))
    # (a) 1-3: official metric on perfect motion
    mod = auc_module(); sol = solution(ep, names, gt_full, H)
    roots = dict(scan=link_meshes(f'{W}/kit_meshes_scan', ep, names, lambda n: XF.scan_path(a.t3, n)),
                 lib=link_meshes(f'{W}/kit_meshes_lib', ep, names, lambda n: f'{a.lib}/{n}.glb'))
    arms = {'a1_mocap_scan_mesh': (gt_full, 'scan'),
            'a2_mocap_at_Xkit_lib_mesh': ({n: np.einsum('tij,jk->tik', gt_full[n], Xk[n]) for n in names}, 'lib'),
            'a3_mocap_at_Xgeom_lib_mesh': ({n: np.einsum('tij,jk->tik', gt_full[n], Xg[n]) for n in names}, 'lib')}
    r['a_official_AUC'] = {}
    for k, (tr, mesh) in arms.items():
        with contextlib.redirect_stdout(io.StringIO()):
            sub = submission(ep, names, tr, roots[mesh])
        r['a_official_AUC'][k] = round(float(mod.score(sol.copy(), sub, 'row_id')), 6)
    a3i = XF.score_track(names, arms['a3_mocap_at_Xgeom_lib_mesh'][0], gt_full, H,
                         [XF.kit_X(f'{a.lib}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)])
    r['a3_inprocess'] = dict(a3i, delta=round(a3i['AUC'] - r['a_official_AUC']['a3_mocap_at_Xgeom_lib_mesh'], 4))
    # (a) 4: round trip through frame_xform.py (both files)
    fx = [sys.executable, '-I', f'{REPO}/pipeline/frame_xform.py', str(ep)]
    run(fx + [f'{a.perc}/ep{ep}', f'{W}/scan', '--xform', a.xgeom, '--to', 'scan'])
    run(fx + [f'{W}/scan', f'{W}/back', '--xform', a.xgeom, '--to', 'lib'])
    P0, P2 = np.load(f'{a.perc}/ep{ep}/poses.npz'), np.load(f'{W}/back/poses.npz')
    V2 = np.load(f'{W}/back/poses_world_vo.npz')
    r['a4_round_trip'] = dict(poses_npz_max_abs=float(max(np.abs(P2[f'cam_T_{n}'].astype(np.float64) - P0[f'cam_T_{n}']).max() for n in names)),
                              poses_npz_dtype=str(P2[f'cam_T_{names[0]}'].dtype),
                              world_vo_max_abs=float(max(np.abs(V2[n] - V[n]).max() for n in names)),
                              world_T_cam_identical=bool(np.array_equal(P2['world_T_cam'], P0['world_T_cam'])))
    # (b) 1: T* two ways, plus the lib column both ways
    N = len(V[names[0]]); gt = {n: gt_full[n][:N] for n in names}; Tp = {n: V[n].astype(np.float64) for n in names}
    sr = [sys.executable, '-I', f'{REPO}/pipeline/score_registered.py', str(ep)]
    run(sr + [f'{W}/scan/poses_world_vo.npz', '--t3', a.t3, '--kit', a.kit, '--out', f'{W}/star_way1.json'])
    run(sr + [f'{a.perc}/ep{ep}/poses_world_vo.npz', '--meshes', a.lib, '--t3', a.t3, '--kit', a.kit, '--out', f'{W}/lib_file.json'])
    w1 = json.load(open(f'{W}/star_way1.json'))['perception']; lf = json.load(open(f'{W}/lib_file.json'))['perception']
    star = XF.score_track(names, Tp, gt, H, [XF.reg_of_X(Xg[n], H[s]['anchor']) for s, n in enumerate(names)])
    Vs = np.load(f'{W}/scan/poses_world_vo.npz'); Ts = {n: Vs[n].astype(np.float64) for n in names}
    REGf = [XF.K['T3']._register_object_body(H[s]['mesh'], H[s]['mesh'], H[s]['anchor'], 1_000_003 * ep + 101 * s) for s in range(len(names))]
    reg_id = max(max(float(np.abs(c - H[s]['anchor']).max()), float(np.abs(R - np.eye(3)).max())) for s, (c, R) in enumerate(REGf))
    w1f = XF.score_track(names, Ts, gt, H, REGf)
    libp = XF.score_track(names, Tp, gt, H, [XF.kit_X(f'{a.lib}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)])
    r['b1_star'] = dict(way1_file_full_scan=w1f, full_scan_self_registration_max_abs=reg_id, way2_inprocess_X=star,
                        delta=round(w1f['AUC'] - star['AUC'], 4),
                        delta_per_obj={n: round(w1f['per_obj_AUC'][n] - star['per_obj_AUC'][n], 4) for n in names},
                        way1b_score_registered_budget_scan=dict(AUC=w1['AUC'], per_obj_AUC=w1['per_obj_AUC'],
                                                                registration=json.load(open(f'{W}/star_way1.json'))['registration']),
                        delta_budget=round(w1['AUC'] - star['AUC'], 4),
                        delta_budget_per_obj={n: round(w1['per_obj_AUC'][n] - star['per_obj_AUC'][n], 4) for n in names})
    r['b0_lib'] = dict(score_registered=dict(AUC=lf['AUC'], per_obj_AUC=lf['per_obj_AUC']), inprocess=libp,
                       delta=round(lf['AUC'] - libp['AUC'], 4))
    # (b) 2: cup spin
    if CUPS & set(names):
        r['b2_spin'] = {}
        for deg in (45, 90, 145, 180):
            Xs = {n: (XF.about(H[s]['axis'], np.radians(deg), H[s]['anchor']) @ Xg[n] if n in CUPS else Xg[n]) for s, n in enumerate(names)}
            sc = XF.score_track(names, Tp, gt, H, [XF.reg_of_X(Xs[n], H[s]['anchor']) for s, n in enumerate(names)])
            r['b2_spin'][str(deg)] = dict(AUC=sc['AUC'], delta=round(sc['AUC'] - star['AUC'], 4),
                                          delta_per_obj={n: round(sc['per_obj_AUC'][n] - star['per_obj_AUC'][n], 4) for n in names})
    # (b) 3: rival surface-fit minima (no rule; X*_geom keeps the best)
    G = json.load(open(a.xgeom))['objects']; r['b3_rivals'] = {}
    for s, n in enumerate(names):
        for k, m in enumerate(G[n]['minima'][1:], 1):
            if m['ratio_to_best'] > XF.AMBIG:
                continue
            Xr = dict(Xg); Xr[n] = np.asarray(m['X_scan_T_lib'])
            sc = XF.score_track(names, Tp, gt, H, [XF.reg_of_X(Xr[q], H[i]['anchor']) for i, q in enumerate(names)])
            r['b3_rivals'][f'{n}#{k}'] = dict(ratio_to_best=m['ratio_to_best'], rot_from_best_deg=m['rot_from_best_deg'],
                                              add_from_best_cm=m['add_from_best_cm'], AUC=sc['per_obj_AUC'][n],
                                              delta_obj=round(sc['per_obj_AUC'][n] - star['per_obj_AUC'][n], 4))
    # (b) 4: the trk path, two ways, and against the score xstar_trk.json recorded
    if a.xtrk:
        Xt, _ = FX.load_xform(a.xtrk, ep, names)
        run(fx + [f'{a.perc}/ep{ep}', f'{W}/scan_trk', '--xform', a.xtrk, '--to', 'scan'])
        run(fx + [f'{W}/scan_trk', f'{W}/back_trk', '--xform', a.xtrk, '--to', 'lib'])
        Pt, Vt = np.load(f'{W}/back_trk/poses.npz'), np.load(f'{W}/back_trk/poses_world_vo.npz')
        Vst = np.load(f'{W}/scan_trk/poses_world_vo.npz')
        t1 = XF.score_track(names, {n: Vst[n].astype(np.float64) for n in names}, gt, H, REGf)
        t2 = XF.score_track(names, Tp, gt, H, [XF.reg_of_X(Xt[n], H[s]['anchor']) for s, n in enumerate(names)])
        rec = json.load(open(a.xtrk))['episodes'][str(ep)]['scores']['trk']['AUC']
        r['b4_trk'] = dict(way1_file_full_scan=t1, way2_inprocess_X=t2, delta=round(t1['AUC'] - t2['AUC'], 4),
                           delta_per_obj={n: round(t1['per_obj_AUC'][n] - t2['per_obj_AUC'][n], 4) for n in names},
                           recorded_in_xtrk=rec, delta_recorded=round(t2['AUC'] - rec, 4),
                           round_trip_max_abs=float(max(max(np.abs(Pt[f'cam_T_{n}'].astype(np.float64) - P0[f'cam_T_{n}']).max(),
                                                            np.abs(Vt[n] - V[n]).max()) for n in names)))
    r['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: a {r["a_official_AUC"]}  rt {r["a4_round_trip"]["poses_npz_max_abs"]:.1e}/{r["a4_round_trip"]["world_vo_max_abs"]:.1e}  '
          f'T* {w1f["AUC"]:.4f} vs {star["AUC"]:.4f} (budget {w1["AUC"]:.4f})  lib {lf["AUC"]:.4f} vs {libp["AUC"]:.4f}  ({r["seconds"]} s)', flush=True)
    return r


def _group(pairs):  # 'name#k' -> per-name list (rivals of one object pooled over episodes)
    out = {}
    for q, x in pairs:
        out.setdefault(q, []).append(x)
    return out


eps = [int(e) for e in a.episodes.split(',') if e]
with ProcessPoolExecutor(a.jobs) as ex:
    res = list(ex.map(episode, eps))
R = {str(r['episode']): r for r in res}
rt = max(max(r['a4_round_trip']['poses_npz_max_abs'], r['a4_round_trip']['world_vo_max_abs']) for r in res)
summary = dict(
    a1_min=min(r['a_official_AUC']['a1_mocap_scan_mesh'] for r in res),
    a2_min=min(r['a_official_AUC']['a2_mocap_at_Xkit_lib_mesh'] for r in res),
    a3_mean=round(float(np.mean([r['a_official_AUC']['a3_mocap_at_Xgeom_lib_mesh'] for r in res])), 4),
    a3_min=min(r['a_official_AUC']['a3_mocap_at_Xgeom_lib_mesh'] for r in res),
    a4_round_trip_max_abs=rt, a4_world_T_cam_identical=all(r['a4_round_trip']['world_T_cam_identical'] for r in res),
    b1_max_abs_delta=max(max([abs(r['b1_star']['delta'])] + [abs(v) for v in r['b1_star']['delta_per_obj'].values()]) for r in res),
    b1_full_scan_self_registration_max_abs=max(r['b1_star']['full_scan_self_registration_max_abs'] for r in res),
    b1b_budget_scan_max_abs_delta=max(max([abs(r['b1_star']['delta_budget'])] + [abs(v) for v in r['b1_star']['delta_budget_per_obj'].values()]) for r in res),
    b1b_budget_scan_mean_delta=round(float(np.mean([r['b1_star']['delta_budget'] for r in res])), 4),
    b0_max_abs_delta=max(abs(r['b0_lib']['delta']) for r in res),
    b2_max_abs_delta=max([abs(v['delta']) for r in res for v in r.get('b2_spin', {}).values()] +
                         [abs(x) for r in res for v in r.get('b2_spin', {}).values() for x in v['delta_per_obj'].values()] or [0.0]),
    a3_inprocess_max_abs_delta=max(abs(r['a3_inprocess']['delta']) for r in res),
    b3_rivals={k: dict(n_eps=len(v), mean_delta_obj=round(float(np.mean(v)), 4), min=min(v), max=max(v))
               for k, v in _group([(q, x['delta_obj']) for r in res for q, x in r['b3_rivals'].items()]).items()},
    means=dict(lib=round(float(np.mean([r['b0_lib']['score_registered']['AUC'] for r in res])), 4),
               star=round(float(np.mean([r['b1_star']['way2_inprocess_X']['AUC'] for r in res])), 4),
               star_budget_scan=round(float(np.mean([r['b1_star']['way1b_score_registered_budget_scan']['AUC'] for r in res])), 4)))
summary['pass'] = dict(a1=summary['a1_min'] >= 0.9995, a2=summary['a2_min'] >= 0.9995, a4=rt < 1e-6 and summary['a4_world_T_cam_identical'],
                       a3_inprocess=summary['a3_inprocess_max_abs_delta'] <= 0.0001,
                       b1=summary['b1_max_abs_delta'] <= 0.002, b2=summary['b2_max_abs_delta'] <= 0.002, b0=summary['b0_max_abs_delta'] == 0)
if a.xtrk:
    summary.update(b4_max_abs_delta=max(max([abs(r['b4_trk']['delta'])] + [abs(v) for v in r['b4_trk']['delta_per_obj'].values()]) for r in res),
                   b4_max_abs_delta_recorded=max(abs(r['b4_trk']['delta_recorded']) for r in res),
                   b4_round_trip_max_abs=max(r['b4_trk']['round_trip_max_abs'] for r in res))
    summary['pass'].update(b4=summary['b4_max_abs_delta'] <= 0.002 and summary['b4_max_abs_delta_recorded'] == 0,
                           a4_trk=summary['b4_round_trip_max_abs'] < 1e-6)
out = dict(note='ORACLE SIDE (mocap + scans), public episodes; tests (a)/(b) of leak-decomp PLAN.md §7', xgeom=os.path.abspath(a.xgeom),
           xgeom_md5=XF.md5(a.xgeom), xtrk=a.xtrk and os.path.abspath(a.xtrk), xtrk_md5=a.xtrk and XF.md5(a.xtrk), perc=os.path.abspath(a.perc), lib=os.path.abspath(a.lib), summary=summary, episodes=R)
json.dump(out, open(a.out, 'w'), indent=1)
print(json.dumps(summary, indent=1))
