"""ORACLE DIAGNOSTIC (public episodes only): Tier A of the leak decomposition, reference level, CPU, deterministic
(docs/research/work/leak-decomp-20261030/PLAN.md §2-§3, build item B3). Reads GROUND TRUTH (public mocap and scans):
never a default anywhere, never an input of eval inference. Refuses eval episodes and SPLIT != public, and writes only
under paths that contain 'oracle' or 'leak-decomp'. Every number is a registered ADD-AUC vs mocap through the kit's own
chain (tools/xstar_fit.py score_track) in the three conventions of PLAN §2: lib (library_v3 at the kit registration
X_kit, the leaderboard convention), * (X*_geom, tierA/xstar_geom.json) and trk (X*_trk, tierA/xstar_trk.json).
Track = P_o, the perception track of ROOT/ep<N>/poses_world_vo.npz (lib frames; refine/in on 30 Oct).
  a1  L1 = T_lib - T* per (episode, object), the constant bias T_trk - T* beside it, and the host-scan perturbation
      test: 50 perturbed copies of each public scan (budget-free decimation to 30 % of the faces, then 1 mm Gaussian
      vertex noise, then 10 % of the area removed as 5 holes), each standing in for the hidden host scan (registration,
      anchor, scored points and symmetry axis all from the copy). Per copy: the kit registration of library_v3 at the
      episode's own seed, T_lib, T*, and a FLIP when that registration turns > 90 deg (cups: axis tilt; lid: modulo its
      180 deg turn) from the clean public-scan registration (pipeline/mesh_gates.py flip rule).
  a1seed  the same flip test with the CLEAN public scan as the host scan and only the kit's registration seed changed
      (1_000_003 q + 101 slot for pseudo episodes q = 10000 + k, k < --n_seed; an eval episode's index gives a seed no
      public episode has): flips vs the episode's own X_kit and the scene's T_lib on our track.
  a2  tracker phase split on * (L3 on P_o; PLAN §2): the AUC is a mean over frames and objects of a per-frame score
      (the kit's 9 ADD thresholds, trapezoid weights), so 1 - R* splits EXACTLY into per-frame losses. Phases per
      object from the MOCAP motion (refine.moving_labels thresholds 0.5 cm / 2 deg per frame, 3-frame closing; runs
      >= 3 frames): f0 (frame 0), rest_pre (untouched, before the first true motion), moving (inside a true motion run,
      +-2 frames), held_still (between the first and last motion, not moving), post (after the last motion). Crossed
      with hand occlusion [H proxy]: >= 20 % of the object's true-pose surface samples project inside a MEASURED hand's
      image silhouette (bone capsules, 1.0 cm radius) that lies in front of them. Mocap enters the perception world by
      G_mocap_T_perc of xstar_trk.json (the robust whole-track fit).
  a5  frame-0 re-anchor (init vs drift), same pass as a2: the track is moved, per object, so that frame 0 sits exactly
      at the mocap frame-0 pose: body form P'(t) = P(t) P(0)^-1 M(0) (one constant body offset, the form of X*_trk) and
      world form P'(t) = M(0) P(0)^-1 P(t). T_reanchor - T* is the init share; compared with T_trk - T* (H3).
  a3  reference construction stages (L4) on O and on P, from the stage files that 'a3prep' and tools/leak_settle.py
      write: raw -> a (mkref's own fit_table/table_frame and per-object snap, mkref defaults) -> IK (E2S + contacts:
      object poses pass through; checked on stored references) -> rest settle (contact_retarget.rest_settle with the
      FlashCHORD scene's hull SDFs, run by leak_settle.py) -> S2 (refine.step_S2 0.545-frame advance before mkref, as
      adopted). O = mocap taken to lib frames by X*_geom, gravity-aligned on P's camera (pipeline/oracle_poses.py
      --xform). Plus stored real references (older code; loaded / E2S / contact retarget / grasp lock) where local.
  a4  hand audit vs the mocap object motion: per object and true motion run, hand arrival (first frame a measured
      fingertip is within 2 cm of the true surface) and leave (last such frame) vs the true onset / end; the
      fingertip-to-true-surface gap during true motion.
  a6  scorer sanity and frame invariance: reads tierA/frames_check.json (tests (a), (b) of PLAN §7).
  a7  reads leak_settle.py's settle results: drift of every mocap rest configuration after 2 s hands-free under lib,
      lib+carve and scan collision; gate = drift <= 1 cm and <= 5 deg for every object (PLAN §3).
Usage: python -I leak_tierA.py MODE --perc ROOT --xgeom XG --xtrk XT --lib LIB --t3 T3 --kit KIT --work DIR --out JSON
       [--episodes 0,2,...] [--jobs 4] [--n_perturb 50] [--n_seed 50] [--a4_window 40]
       (DIR must contain 'oracle'; MODE in a1 a1seed a2 a3prep a3 a4 a6 a7prep a7)
(2026-10-30)
"""
import argparse, hashlib, json, os, subprocess, sys, time, types
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools')); sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import xstar_fit as XF       # noqa: E402
import frame_xform as FX     # noqa: E402

PUBLIC, EVAL = XF.PUBLIC, XF.EVAL
THR = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8      # kit ADD thresholds, trapezoid weights
FLIP_DEG = 90.0              # registration flip, as pipeline/mesh_gates.py
OCC_FRAC, OCC_R = 0.20, 0.010   # [H] occlusion proxy: covered fraction, bone-capsule radius (m)
NEAR_CM = 2.0                # [H] a fingertip this close to the true surface = hand at the object
PHASES = ('f0', 'rest_pre', 'moving', 'held_still', 'post')


# ---------------- shared
def guard(a):
    eps = [int(e) for e in a.episodes.split(',') if e]
    bad = [e for e in eps if e in EVAL]
    if bad or os.environ.get('SPLIT', 'public') != 'public':
        sys.exit(f'eval episodes {bad} / SPLIT={os.environ.get("SPLIT")}: this oracle diagnostic is for public episodes only')
    for q in (a.work, a.out):
        if q and not any(k in os.path.abspath(q) for k in ('oracle', 'leak-decomp')):
            sys.exit(f'{q}: oracle outputs must live under a path containing "oracle" or "leak-decomp"')
    return eps


def load(a, ep):
    """Track (lib frames), mocap (scan frames, its N first frames), host stand-ins, X*_geom, X*_trk, X_kit."""
    XF.kit(a.kit)
    V = np.load(f'{a.perc}/ep{ep}/poses_world_vo.npz'); N = len(V[V.files[0]])
    names, gt = XF.mocap(a.t3, ep, N)
    Tp = {n: V[n].astype(np.float64) for n in names}
    H = [XF.host_geometry(a.t3, n, s) for s, n in enumerate(names)]
    Xg = FX.load_xform(a.xgeom, ep, names)[0]; Xt = FX.load_xform(a.xtrk, ep, names)[0]
    Xk = [XF.kit_X(f'{a.lib}/{n}.glb', H[s], ep, s) for s, n in enumerate(names)]
    return types.SimpleNamespace(ep=ep, names=names, N=N, gt=gt, Tp=Tp, H=H, Xg=Xg, Xt=Xt, Xk={n: Xk[s][0] for s, n in enumerate(names)},
                                 REGk=[x[1] for x in Xk], REGg=[XF.reg_of_X(Xg[n], H[s]['anchor']) for s, n in enumerate(names)],
                                 REGt=[XF.reg_of_X(Xt[n], H[s]['anchor']) for s, n in enumerate(names)])


def frame_err(names, track, gt, H, REG):
    """(N, B) symmetric ADD (m) per frame and object after the kit's conversion and frame-0 scene alignment, i.e. the
    errors behind xstar_fit.score_track's AUC."""
    T3 = XF.K['T3']; N = len(track[names[0]]); B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy(); ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    ach = T3._align_registered_scene(ach, ref, [h['axis'] for h in H])
    return np.stack([T3._symmetry_point_errors(ach[:, :, s], ref[:, :, s], H[s]['points'], H[s]['axis'], H[s]['order'])[:, 0]
                     for s in range(B)], 1)


def frame_score(E):  # per-frame score in [0, 1]; its mean over frames is the kit's per-object ADD-AUC
    return ((E[..., None] < THR) * TW).sum(-1)


def auc(E):
    s = frame_score(E); return dict(AUC=round(float(s.mean()), 4), per_obj=np.round(s.mean(0), 4).tolist())


def auc_named(names, E):  # score_track's dict from per-frame errors
    s = frame_score(E)
    return dict(AUC=round(float(s.mean()), 4), per_obj_AUC={n: round(float(s[:, i].mean()), 4) for i, n in enumerate(names)})


def sym_rot_deg(R, H):  # rotation of a scan-frame change the scorer cannot absorb (mesh_gates.sym_rot_err)
    if H['order'] == 360:
        return XF.tilt_deg(R, H['axis'])
    if H['order'] == 2:
        return min(XF.rot_deg(R), XF.rot_deg(R @ Rot.from_rotvec(np.pi * H['axis']).as_matrix()))
    return XF.rot_deg(R)


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def code_version():
    try:
        sha = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', 'tools', 'pipeline'], capture_output=True, text=True).stdout.strip()
        return dict(commit=sha, tools_pipeline_dirty=bool(dirty), leak_tierA_md5=md5(os.path.abspath(__file__)))
    except Exception as e:                                           # noqa: BLE001
        return dict(error=str(e))


# ---------------- a1: L1 and host-scan perturbations
def perturb_scan(v, f, seed, keep=0.30, noise=0.001, holes=5, hole_area=0.10):
    """A stand-in for a different copy of the host scan: decimation to KEEP of the faces, Gaussian vertex noise, then
    HOLES patches (nearest faces to area-weighted random centres) that remove HOLE_AREA of the surface in total.
    The public scans are triangle soups (3 vertices per face): they are WELDED first, as the kit's budget_mesh does.
    Decimating the soup itself moves the centroid by 7-13 mm and the RMS radius by up to x1.27 (the 26 Oct review's
    invalid 'unwelded decimation'); the a1 run of 30 Oct 19:41 did that and is superseded by a1_v2 (31 Oct)."""
    import fast_simplification, trimesh
    w = trimesh.Trimesh(np.asarray(v, np.float64), np.asarray(f, np.int64), process=True)
    v2, f2 = fast_simplification.simplify(np.asarray(w.vertices, np.float32), np.asarray(w.faces, np.int32), target_reduction=1 - keep)
    v2 = np.asarray(v2, np.float64); f2 = np.asarray(f2, np.int64)
    rng = np.random.default_rng(seed)
    v2 = v2 + rng.normal(0, noise, v2.shape)
    tri = v2[f2]; area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    cen = tri.mean(1); drop = np.zeros(len(f2), bool)
    for c in rng.choice(len(f2), holes, replace=False, p=area / area.sum()):
        order = np.argsort(np.linalg.norm(cen - cen[c], axis=1))
        k = int(np.searchsorted(np.cumsum(area[order]), hole_area / holes * area.sum())) + 1
        drop[order[:k]] = True
    f2 = f2[~drop]
    used = np.unique(f2); remap = -np.ones(len(v2), np.int64); remap[used] = np.arange(len(used))
    return v2[used], remap[f2], dict(faces=int(len(f2)), removed_area_frac=round(float(area[drop].sum() / area.sum()), 4))


def host_from(v, f, n, slot):  # xstar_fit.host_geometry on given geometry
    c, r = XF.K['OM']._surface_moments(v, f)
    pts = XF.K['sample'](v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in XF.SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if XF.SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(mesh=(v, f), anchor=c, radius=r, points=pts, axis=axis, order=order)


def a1_episode(a, ep):
    D = load(a, ep); t0 = time.time()
    lib = XF.score_track(D.names, D.Tp, D.gt, D.H, D.REGk); star = XF.score_track(D.names, D.Tp, D.gt, D.H, D.REGg)
    trk = XF.score_track(D.names, D.Tp, D.gt, D.H, D.REGt)
    rec = json.load(open(a.xtrk))['episodes'][str(ep)]['scores']
    same = auc_named(D.names, frame_err(D.names, D.Tp, D.gt, D.H, D.REGk))         # the per-frame path == score_track
    assert max([abs(same['AUC'] - lib['AUC'])] + [abs(same['per_obj_AUC'][n] - lib['per_obj_AUC'][n]) for n in D.names]) <= 1e-4, (same, lib)
    r = dict(episode=ep, objects=D.names, lib=lib, star=star, trk=trk, trk_ls=rec['trk_ls'],
             recorded_delta=max(abs(lib['AUC'] - rec['lib']['AUC']), abs(star['AUC'] - rec['star']['AUC']), abs(trk['AUC'] - rec['trk']['AUC'])),
             L1=round(lib['AUC'] - star['AUC'], 4), bias=round(trk['AUC'] - star['AUC'], 4),
             L1_obj={n: round(lib['per_obj_AUC'][n] - star['per_obj_AUC'][n], 4) for n in D.names},
             bias_obj={n: round(trk['per_obj_AUC'][n] - star['per_obj_AUC'][n], 4) for n in D.names},
             E_kit={n: XF.compare(D.Xg[n] @ np.linalg.inv(D.Xk[n]), D.H[s]) for s, n in enumerate(D.names)})
    lib_b = {n: XF.K['budget'](f'{a.lib}/{n}.glb', 4096, 4096) for n in D.names}
    rows = []
    for k in range(a.n_perturb):
        Hp, REGp, flips = [], [], {}
        for s, n in enumerate(D.names):
            v, f = D.H[s]['mesh']
            vp, fp, info = perturb_scan(v, f, int(hashlib.md5(f'{n}:{k}'.encode()).hexdigest()[:8], 16))
            h = host_from(vp, fp, n, s); Hp.append(h)
            ca, R = XF.K['T3']._register_object_body(lib_b[n], (vp, fp), h['anchor'], 1_000_003 * ep + 101 * s)
            REGp.append((ca, R)); Xp = XF.rigid(R, h['anchor'] - R @ ca)
            E = Xp @ np.linalg.inv(D.Xk[n])
            flips[n] = dict(rot_vs_clean_deg=round(sym_rot_deg(E[:3, :3], D.H[s]), 2), add_vs_clean_cm=round(XF.sym_add_cm(E, D.H[s], 72), 3),
                            add_vs_xgeom_cm=round(XF.sym_add_cm(D.Xg[n] @ np.linalg.inv(Xp), D.H[s], 72), 3), faces=info['faces'],
                            hole_area=info['removed_area_frac'])
            flips[n]['flip'] = bool(flips[n]['rot_vs_clean_deg'] > FLIP_DEG)
        lp = auc_named(D.names, frame_err(D.names, D.Tp, D.gt, Hp, REGp))      # one error pass per object (score_track
        sp = auc_named(D.names, frame_err(D.names, D.Tp, D.gt, Hp, [XF.reg_of_X(D.Xg[n], Hp[s]['anchor'])   # makes two)
                                                                    for s, n in enumerate(D.names)]))
        rows.append(dict(k=k, lib=lp, star=sp, reg=flips))
    def per(n, key):
        return np.array([x[key]['per_obj_AUC'][n] for x in rows])
    r['perturb'] = dict(n=a.n_perturb, rows=rows, summary={n: dict(
        flips=int(sum(x['reg'][n]['flip'] for x in rows)),
        rot_vs_clean_deg_max=max(x['reg'][n]['rot_vs_clean_deg'] for x in rows),
        add_vs_clean_cm_median=round(float(np.median([x['reg'][n]['add_vs_clean_cm'] for x in rows])), 3),
        add_vs_clean_cm_max=max(x['reg'][n]['add_vs_clean_cm'] for x in rows),
        lib_mean=round(float(per(n, 'lib').mean()), 4), lib_sd=round(float(per(n, 'lib').std(ddof=1)), 4),
        lib_min=round(float(per(n, 'lib').min()), 4), lib_drop_ge_0p03=int((per(n, 'lib') <= lib['per_obj_AUC'][n] - 0.03).sum()),
        star_mean=round(float(per(n, 'star').mean()), 4), star_sd=round(float(per(n, 'star').std(ddof=1)), 4),
        L1_mean=round(float((per(n, 'lib') - per(n, 'star')).mean()), 4), L1_sd=round(float((per(n, 'lib') - per(n, 'star')).std(ddof=1)), 4))
        for n in D.names},
        scene=dict(lib_mean=round(float(np.mean([x['lib']['AUC'] for x in rows])), 4), lib_sd=round(float(np.std([x['lib']['AUC'] for x in rows], ddof=1)), 4),
                   star_mean=round(float(np.mean([x['star']['AUC'] for x in rows])), 4),
                   L1_mean=round(float(np.mean([x['lib']['AUC'] - x['star']['AUC'] for x in rows])), 4),
                   L1_sd=round(float(np.std([x['lib']['AUC'] - x['star']['AUC'] for x in rows], ddof=1)), 4)))
    r['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: lib {lib["AUC"]:.4f} * {star["AUC"]:.4f} trk {trk["AUC"]:.4f} L1 {r["L1"]:+.4f}  perturbed L1 '
          f'{r["perturb"]["scene"]["L1_mean"]:+.4f} +- {r["perturb"]["scene"]["L1_sd"]:.4f}  flips '
          f'{ {n: v["flips"] for n, v in r["perturb"]["summary"].items()} }  ({r["seconds"]} s)', flush=True)
    return r


def a1_summary(res):
    objs = sorted({n for r in res for n in r['objects']})
    per_obj = {}
    for n in objs:
        R = [r for r in res if n in r['objects']]
        L1 = [r['L1_obj'][n] for r in R]
        per_obj[n] = dict(eps=[r['episode'] for r in R], L1=L1, L1_mean=round(float(np.mean(L1)), 4),
                          eps_L1_le_m0p03=[r['episode'] for r in R if r['L1_obj'][n] <= -0.03],
                          eps_L1_ge_0p03=[r['episode'] for r in R if r['L1_obj'][n] >= 0.03],
                          bias_mean=round(float(np.mean([r['bias_obj'][n] for r in R])), 4),
                          flips=int(sum(r['perturb']['summary'][n]['flips'] for r in R)), draws=int(sum(r['perturb']['n'] for r in R)),
                          lib_sd_perturb_max=max(r['perturb']['summary'][n]['lib_sd'] for r in R),
                          L1_perturb_mean=round(float(np.mean([r['perturb']['summary'][n]['L1_mean'] for r in R])), 4))
    return dict(per_object=per_obj)


# ---------------- a1seed: registration flips from the scorer's seed alone (clean public scan as the host scan)
SEED_BASE = 10_000      # pseudo episode indices SEED_BASE + k: no real (public or eval) episode has one


def _a1seed_reg(args):
    """The kit's registration of library_v3 (budgeted as the packer does) to the CLEAN public scan at the kit's seed of
    pseudo episode Q, slot S: (name, slot, q) -> (candidate anchor, rotation)."""
    a, n, s, q = args
    XF.kit(a.kit); H = XF.host_geometry(a.t3, n, s)
    ca, R = XF.K['T3']._register_object_body(XF.K['budget'](f'{a.lib}/{n}.glb', 4096, 4096), H['mesh'], H['anchor'], 1_000_003 * q + 101 * s)
    return (n, s, q), (ca.tolist(), R.tolist())


def a1seed(a, eps):
    """A1 seed-only perturbation: the host scan IS the public scan; only the kit's registration seed changes (an eval
    episode's index gives a seed no public episode has). Per (episode, object) and pseudo episode: flip vs the
    episode's own registration X_kit (> 90 deg, symmetry-aware), ADD vs X_kit and X*_geom, and the scene's T_lib on
    our track (the scene alignment couples the objects)."""
    XF.kit(a.kit); t0 = time.time()
    slots = sorted({(n, s) for e in eps for s, n in enumerate(XF.names_of(a.t3, e))})
    jobs = [(a, n, s, SEED_BASE + k) for n, s in slots for k in range(a.n_seed)]
    with ProcessPoolExecutor(a.jobs) as ex:
        REG = dict(ex.map(_a1seed_reg, jobs, chunksize=4))
    print(f'a1seed: {len(jobs)} registrations ({round(time.time() - t0)} s)', flush=True)
    out = {}
    for ep in eps:
        D = load(a, ep); rows = []
        lib0 = auc_named(D.names, frame_err(D.names, D.Tp, D.gt, D.H, D.REGk))
        for k in range(a.n_seed):
            q = SEED_BASE + k; REGq = []; reg = {}
            for s, n in enumerate(D.names):
                ca, R = (np.asarray(x) for x in REG[(n, s, q)]); REGq.append((ca, R))
                Xq = XF.rigid(R, D.H[s]['anchor'] - R @ ca); E = Xq @ np.linalg.inv(D.Xk[n])
                reg[n] = dict(rot_vs_kit_deg=round(sym_rot_deg(E[:3, :3], D.H[s]), 2), add_vs_kit_cm=round(XF.sym_add_cm(E, D.H[s], 72), 3),
                              add_vs_xgeom_cm=round(XF.sym_add_cm(D.Xg[n] @ np.linalg.inv(Xq), D.H[s], 72), 3))
                reg[n]['flip'] = bool(reg[n]['rot_vs_kit_deg'] > FLIP_DEG)
            rows.append(dict(q=q, lib=auc_named(D.names, frame_err(D.names, D.Tp, D.gt, D.H, REGq)), reg=reg))
        sc = np.array([x['lib']['AUC'] for x in rows])
        out[str(ep)] = dict(episode=ep, objects=D.names, lib_own_seed=lib0, rows=rows, summary=dict(
            scene_lib_mean=round(float(sc.mean()), 4), scene_lib_min=round(float(sc.min()), 4),
            scene_drop_mean=round(float(lib0['AUC'] - sc.mean()), 4), scene_drops_ge_0p03=int((sc <= lib0['AUC'] - 0.03).sum()),
            flips={n: int(sum(x['reg'][n]['flip'] for x in rows)) for n in D.names},
            rot_vs_kit_deg_max={n: max(x['reg'][n]['rot_vs_kit_deg'] for x in rows) for n in D.names},
            add_vs_kit_cm_median={n: round(float(np.median([x['reg'][n]['add_vs_kit_cm'] for x in rows])), 3) for n in D.names}))
        print(f'ep{ep}: own-seed T_lib {lib0["AUC"]:.4f}; {a.n_seed} seeds: mean {sc.mean():.4f} min {sc.min():.4f}, flips '
              f'{out[str(ep)]["summary"]["flips"]}', flush=True)
    per_obj = {}
    for n, s in slots:
        rs = [x['reg'][n] for r in out.values() if n in r['objects'] and r['objects'].index(n) == s for x in r['rows']][:a.n_seed]
        per_obj[f'{n}@{s}'] = dict(draws=len(rs), flips=int(sum(x['flip'] for x in rs)), rot_vs_kit_deg_max=max(x['rot_vs_kit_deg'] for x in rs),
                                   add_vs_xgeom_cm_median=round(float(np.median([x['add_vs_xgeom_cm'] for x in rs])), 3))
    return out, dict(per_object_slot=per_obj, n_seed=a.n_seed, seed_base=SEED_BASE, seconds=round(time.time() - t0, 1))


# ---------------- a2 / a5: phase split of the tracker loss, frame-0 re-anchor
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13),
         (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20), (0, 9), (0, 13), (1, 5)]   # MediaPipe + palm
TIPS = [4, 8, 12, 16, 20]


def true_motion(gt_n, anchor):
    """Mocap motion labels of one object (refine.moving_labels thresholds) and its runs of >= 3 frames."""
    import refine
    mv = refine.moving_labels(gt_n, anchor)
    return mv, [(s, e) for s, e in refine.runs(mv) if e - s >= 3]


def phases(mv, runs_, N):
    ph = np.empty(N, object); ph[:] = 'held_still'
    if not runs_:
        ph[:] = 'rest_pre'
    else:
        on, end = runs_[0][0], runs_[-1][1]
        near = np.zeros(N, bool)
        for s, e in runs_:
            near[max(0, s - 2):min(N, e + 2)] = True
        ph[:on] = 'rest_pre'; ph[end:] = 'post'; ph[on:end][near[on:end]] = 'moving'
    ph[0] = 'f0'
    return ph


def hands(perc_dir):
    f = f'{perc_dir}/hands_refined.npz' if os.path.exists(f'{perc_dir}/hands_refined.npz') else f'{perc_dir}/hands.npz'
    Hn = np.load(f)
    return f, {s: (Hn[f'joints_{s}'].astype(np.float64), Hn[f'measured_{s}'].astype(bool)) for s in ('left', 'right')}, Hn['KR']


def occlusion(W_C, KR, Pw, pts, J):
    """(N,) fraction of the object's surface samples PTS (body frame), posed by Pw (N,4,4) in the world, that project
    inside a measured hand's silhouette (bone capsules of radius OCC_R) lying in front of them [H proxy]."""
    N = len(W_C); out = np.zeros(N); f = KR[0, 0]
    for t in range(N):
        Ci = np.linalg.inv(W_C[t])
        X = (pts @ Pw[t][:3, :3].T + Pw[t][:3, 3]) @ Ci[:3, :3].T + Ci[:3, 3]
        X = X[X[:, 2] > 0.05]
        if not len(X):
            continue
        uv = X[:, :2] / X[:, 2:] * f + KR[:2, 2]
        cov = np.zeros(len(X), bool)
        for jt, meas in J.values():
            if not meas[t]:
                continue
            Y = jt[t] @ Ci[:3, :3].T + Ci[:3, 3]
            if (Y[:, 2] <= 0.05).any():
                continue
            q = Y[:, :2] / Y[:, 2:] * f + KR[:2, 2]
            A, B = q[[i for i, _ in BONES]], q[[j for _, j in BONES]]; zA, zB = Y[[i for i, _ in BONES], 2], Y[[j for _, j in BONES], 2]
            d = B - A; L2 = np.maximum((d ** 2).sum(1), 1e-9)
            u = np.clip(((uv[:, None] - A[None]) * d[None]).sum(-1) / L2, 0, 1)            # (M, bones)
            dist = np.linalg.norm(uv[:, None] - (A[None] + u[..., None] * d[None]), axis=-1)
            z = zA[None] + u * (zB - zA)[None]
            cov |= ((dist < f * OCC_R / z) & (z < X[:, 2:3])).any(1)
        out[t] = cov.mean()
    return out


def split(loss, ph, occ, N):
    """Loss shares (contribution to 1 - AUC) and frame counts per phase x occlusion class, one object."""
    r = {}
    for p_ in PHASES:
        m = ph == p_
        r[p_] = dict(n=int(m.sum()), loss=round(float(loss[m].sum() / N), 5),
                     occ=dict(n=int((m & occ).sum()), loss=round(float(loss[m & occ].sum() / N), 5)),
                     clear=dict(n=int((m & ~occ).sum()), loss=round(float(loss[m & ~occ].sum() / N), 5)))
    return r


def a2_episode(a, ep):
    D = load(a, ep); t0 = time.time(); N, names = D.N, D.names
    G = np.asarray(json.load(open(a.xtrk))['episodes'][str(ep)]['fit']['G_mocap_T_perc']); Gi = np.linalg.inv(G)
    W_C = np.load(f'{a.perc}/ep{ep}/poses.npz')['world_T_cam'].astype(np.float64)
    hf, J, KR = hands(f'{a.perc}/ep{ep}')
    E = frame_err(names, D.Tp, D.gt, D.H, D.REGg); sc = frame_score(E); loss = 1 - sc
    star = XF.score_track(names, D.Tp, D.gt, D.H, D.REGg)
    assert abs(sc.mean() - star['AUC']) <= 1e-4, (sc.mean(), star)
    r = dict(episode=ep, objects=names, frames=N, hands_file=os.path.basename(hf), star=star, objects_detail={})
    Mw = {n: np.einsum('ij,tjk->tik', Gi, D.gt[n]) for n in names}                                  # mocap in the perception world
    A = {n: np.einsum('tij,jk->tik', D.Tp[n], np.linalg.inv(D.Xg[n])) for n in names}               # track, scan frames
    tracks = {'body': {}, 'world': {}}
    for s, n in enumerate(names):
        # the mocap frame-0 pose, taken modulo the scorer's symmetry (cup spin, lid flip) to the one nearest our frame 0:
        # an arbitrary spin would otherwise turn the whole world-form trajectory about the cup
        M0 = min((Mw[n][0] @ S_ for S_ in XF.sym_group(D.H[s])), key=lambda M: XF.rot_deg(np.linalg.inv(A[n][0])[:3, :3] @ M[:3, :3]))
        C = np.linalg.inv(A[n][0]) @ M0
        tracks['body'][n] = np.einsum('tij,jk->tik', A[n], C @ D.Xg[n])                             # back to lib frames
        tracks['world'][n] = np.einsum('ij,tjk->tik', M0 @ np.linalg.inv(A[n][0]), D.Tp[n])
    re = {}
    for k, tr in tracks.items():
        Ek = frame_err(names, tr, D.gt, D.H, D.REGg)
        re[k] = dict(star=auc_named(names, Ek), lib=XF.score_track(names, tr, D.gt, D.H, D.REGk), loss=1 - frame_score(Ek))
    trk = XF.score_track(names, D.Tp, D.gt, D.H, D.REGt)
    for s, n in enumerate(names):
        mv, runs_ = true_motion(D.gt[n], D.H[s]['anchor']); ph = phases(mv, runs_, N)
        pts = D.H[s]['points'][::3] + D.H[s]['anchor']
        frac = occlusion(W_C, KR, Mw[n], pts, J); occ = frac >= OCC_FRAC
        Rg = Rot.from_matrix(D.gt[n][:, :3, :3]); rot_span = float(np.degrees((Rg * Rg[0].inv()).magnitude()).max())
        c = D.gt[n][:, :3, :3] @ D.H[s]['anchor'] + D.gt[n][:, :3, 3]
        r['objects_detail'][n] = dict(
            true_runs=[list(map(int, x)) for x in runs_], true_rot_span_deg=round(rot_span, 1),
            true_travel_cm=round(float(np.linalg.norm(c - c[0], axis=1).max() * 100), 1),
            occluded_frames=int(occ.sum()), hand_measured_frames=int(np.any([m for _, m in J.values()], 0).sum()),
            add_cm_mean={p_: (round(float(E[ph == p_, s].mean() * 100), 2) if (ph == p_).any() else None) for p_ in PHASES},
            f0_add_cm=round(float(E[0, s] * 100), 2),
            star=star['per_obj_AUC'][n], loss=round(float(loss[:, s].mean()), 5), split=split(loss[:, s], ph, occ, N),
            trk=trk['per_obj_AUC'][n],
            reanchor={k: dict(star=re[k]['star']['per_obj_AUC'][n], lib=re[k]['lib']['per_obj_AUC'][n],
                              split=split(re[k]['loss'][:, s], ph, occ, N)) for k in re})
    r['trk'] = trk
    r['reanchor'] = {k: dict(star=v['star'], lib=v['lib']) for k, v in re.items()}
    r['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: * {star["AUC"]:.4f}  re-anchor body {re["body"]["star"]["AUC"]:.4f} world {re["world"]["star"]["AUC"]:.4f}  '
          f'trk {trk["AUC"]:.4f}  ' + ', '.join(f'{n} occ {d["occluded_frames"]}/{N}' for n, d in r['objects_detail'].items())
          + f'  ({r["seconds"]} s)', flush=True)
    return r


def a2_summary(res):
    def scene(r, key):  # scene loss share of one phase (mean over objects), optionally one occlusion class
        return float(np.mean([(d['split'][key[0]][key[1]]['loss'] if len(key) > 1 else d['split'][key[0]]['loss'])
                              for d in r['objects_detail'].values()]))
    out = {}
    for tag, sel in (('all', res), ('no_ep23', [r for r in res if r['episode'] != 23])):
        tot = float(np.mean([1 - r['star']['AUC'] for r in sel]))
        ph = {p_: round(float(np.mean([scene(r, (p_,)) for r in sel])), 5) for p_ in PHASES}
        occ = {p_: dict(occ=round(float(np.mean([scene(r, (p_, 'occ')) for r in sel])), 5),
                        clear=round(float(np.mean([scene(r, (p_, 'clear')) for r in sel])), 5)) for p_ in PHASES}
        rb = [r['reanchor']['body']['star']['AUC'] - r['star']['AUC'] for r in sel]
        rw = [r['reanchor']['world']['star']['AUC'] - r['star']['AUC'] for r in sel]
        bias = [r['trk']['AUC'] - r['star']['AUC'] for r in sel]
        out[tag] = dict(n_eps=len(sel), loss_1_minus_Rstar=round(tot, 5), phase_loss=ph,
                        phase_share={p_: round(v / tot, 3) for p_, v in ph.items()}, phase_occ_loss=occ,
                        reanchor_body_gain=round(float(np.mean(rb)), 4), reanchor_body_pos=int(sum(x > 0 for x in rb)),
                        reanchor_body_neg=int(sum(x < 0 for x in rb)),
                        reanchor_world_gain=round(float(np.mean(rw)), 4), reanchor_world_pos=int(sum(x > 0 for x in rw)),
                        bias_trk=round(float(np.mean(bias)), 4),
                        reanchor_body_over_bias=round(float(np.mean(rb) / np.mean(bias)), 3) if np.mean(bias) else None)
    # H3: on objects that truly turn more than 30 deg, does the re-anchor recover >= half of T_trk - T*? (per object)
    big = [(r['episode'], n, d['reanchor']['body']['star'] - d['star'], d['trk'] - d['star']) for r in res if r['episode'] != 23
           for n, d in r['objects_detail'].items() if d['true_rot_span_deg'] > 30]
    out['H3_objects_over_30deg'] = dict(n=len(big), reanchor_gain_sum=round(sum(x[2] for x in big), 4), bias_sum=round(sum(x[3] for x in big), 4),
                                        ratio=round(sum(x[2] for x in big) / sum(x[3] for x in big), 3) if big and sum(x[3] for x in big) else None,
                                        rows=[dict(ep=e, obj=n, reanchor_gain=round(g, 4), bias=round(b, 4)) for e, n, g, b in big])
    return out


# ---------------- a4: hand audit against the mocap object motion
def surface_tree(v, f, n=20000, seed=5):
    from scipy.spatial import cKDTree
    return cKDTree(XF.K['sample'](v, f, n, seed))


def tip_gap_cm(J, Pw, tree):
    """(N,) cm: nearest MEASURED fingertip (MediaPipe 4/8/12/16/20) to the surface (KD-tree of body-frame samples)
    posed by Pw (N,4,4); inf when no hand is measured."""
    N = len(Pw); out = np.full(N, np.inf)
    for jt, meas in J.values():
        for t in np.nonzero(meas)[0]:
            Q = (jt[t][TIPS] - Pw[t][:3, 3]) @ Pw[t][:3, :3]
            out[t] = min(out[t], float(tree.query(Q)[0].min() * 100))
    return out


def segments(runs_, merge=10):  # true motion runs closer than MERGE frames form one handling segment
    seg = []
    for s0, e0 in runs_:
        if seg and s0 - seg[-1][1] < merge:
            seg[-1][1] = e0
        else:
            seg.append([s0, e0])
    return seg


def a4_episode(a, ep):
    W = a.a4_window; D = load(a, ep); t0 = time.time(); N, names = D.N, D.names
    G = np.asarray(json.load(open(a.xtrk))['episodes'][str(ep)]['fit']['G_mocap_T_perc']); Gi = np.linalg.inv(G)
    hf, J, _ = hands(f'{a.perc}/ep{ep}')
    meas_any = np.any([m for _, m in J.values()], 0)
    r = dict(episode=ep, objects=names, frames=N, hands_file=os.path.basename(hf), hand_measured_frac=round(float(meas_any.mean()), 3),
             near_cm=NEAR_CM, window=W, objects_detail={})
    import refine
    for s, n in enumerate(names):
        v, f = D.H[s]['mesh']
        gap_true = tip_gap_cm(J, np.einsum('ij,tjk->tik', Gi, D.gt[n]), surface_tree(v, f))
        lv, lf = XF.load_vf(f'{a.lib}/{n}.glb')
        gap_perc = tip_gap_cm(J, D.Tp[n], surface_tree(lv, lf))                  # the same hands vs OUR track
        mv, runs_ = true_motion(D.gt[n], D.H[s]['anchor'])
        mp0 = refine.moving_labels(np.einsum('tij,jk->tik', D.Tp[n], np.linalg.inv(D.Xg[n])), D.H[s]['anchor'])  # our track,
        mp = np.zeros(N, bool)                                                                                   # runs >= 3
        for s0, e0 in refine.runs(mp0):
            mp[s0:e0] = e0 - s0 >= 3
        near = gap_true < NEAR_CM; seg = segments(runs_); ev = []
        for k, (s0, e0) in enumerate(seg):
            lo = max(0, s0 - W, seg[k - 1][1] if k else 0); hi = min(N, e0 + W, seg[k + 1][0] if k + 1 < len(seg) else N)
            idx = np.nonzero(near[lo:hi])[0] + lo; pm = np.nonzero(mp[lo:hi])[0] + lo
            ev.append(dict(segment=[int(s0), int(e0)], arrival_lag=(int(idx[0] - s0) if len(idx) else None),
                           leave_lag=(int(idx[-1] - (e0 - 1)) if len(idx) else None),
                           perc_onset_lag=(int(pm[0] - s0) if len(pm) else None), perc_end_lag=(int(pm[-1] - (e0 - 1)) if len(pm) else None),
                           measured_frac=round(float(meas_any[s0:e0].mean()), 3), leave_capped=bool(len(idx) and idx[-1] == hi - 1)))
        mvf = np.zeros(N, bool)
        for s0, e0 in runs_:
            mvf[s0:e0] = True
        gm, gp = gap_true[mvf & meas_any], gap_perc[mvf & meas_any]
        r['objects_detail'][n] = dict(
            segments=ev, true_runs=len(runs_), moving_frames=int(mvf.sum()), moving_frames_hand_measured=int((mvf & meas_any).sum()),
            gap_true_cm_median=(round(float(np.median(gm)), 2) if len(gm) else None),
            gap_true_cm_p90=(round(float(np.percentile(gm, 90)), 2) if len(gm) else None),
            gap_true_frac_over_3cm=(round(float((gm > 3).mean()), 3) if len(gm) else None),
            gap_perc_cm_median=(round(float(np.median(gp)), 2) if len(gp) else None),
            gap_true_rest_cm_median=(round(float(np.median(gap_true[~mvf & meas_any])), 2) if (~mvf & meas_any).any() else None))
    r['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: ' + '; '.join(f'{n} segs {len(d["segments"])} gap {d["gap_true_cm_median"]} (ours {d["gap_perc_cm_median"]}) lags '
                                 f'{[(x["arrival_lag"], x["leave_lag"], x["perc_onset_lag"], x["perc_end_lag"]) for x in d["segments"]][:3]}'
                                 for n, d in r['objects_detail'].items()) + f'  ({r["seconds"]} s)', flush=True)
    return r


def a4_summary(res):
    segs = [x for r in res if r['episode'] != 23 for d in r['objects_detail'].values() for x in d['segments']]
    first = [d['segments'][0] for r in res if r['episode'] != 23 for d in r['objects_detail'].values() if d['segments']]
    last = [d['segments'][-1] for r in res if r['episode'] != 23 for d in r['objects_detail'].values() if d['segments']]
    q = lambda x: dict(n=len(x), median=(float(np.median(x)) if x else None), p25=(float(np.percentile(x, 25)) if x else None),
                       p75=(float(np.percentile(x, 75)) if x else None))          # noqa: E731
    col = lambda L, k: [x[k] for x in L if x[k] is not None]                       # noqa: E731
    gaps = [d['gap_true_cm_median'] for r in res if r['episode'] != 23 for d in r['objects_detail'].values() if d['gap_true_cm_median'] is not None]
    gp = [d['gap_perc_cm_median'] for r in res if r['episode'] != 23 for d in r['objects_detail'].values() if d['gap_perc_cm_median'] is not None]
    return dict(note='ep23 (identity swap) excluded', segments=len(segs), segments_without_hand=int(sum(x['arrival_lag'] is None for x in segs)),
                leave_capped=int(sum(x['leave_capped'] for x in segs)),
                arrival_lag_all=q(col(segs, 'arrival_lag')), leave_lag_all=q(col(segs, 'leave_lag')),
                arrival_lag_first=q(col(first, 'arrival_lag')), leave_lag_last=q(col(last, 'leave_lag')),
                perc_onset_lag_all=q(col(segs, 'perc_onset_lag')), perc_end_lag_all=q(col(segs, 'perc_end_lag')),
                perc_onset_lag_first=q(col(first, 'perc_onset_lag')), perc_end_lag_last=q(col(last, 'perc_end_lag')),
                gap_true_cm_median_over_objects=q(gaps), gap_perc_cm_median_over_objects=q(gp))


# ---------------- a3: reference construction stages
MKA = dict(table_z=0.60, ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05,
           support_fallback=1, snap='per_object', snap_max=0.02, start_overlap=0.0, table_fit=1, table_radius=0.45,
           min_valid_frac=0.10, gap_fill='attach', attach_dist=0.03, depenetrate=0.006, hand_sep=0.04, lead_in=10,
           lead_in_speed=0.2, fps=20.0, bone_norm=False)       # mkref.py defaults (the pipeline adds only --wrist_cost: IK)


def mkref_ab(W_C, camT, names, depth0, KR, lib, Hn, depen=False):
    """mkref.py stages (a) and (b) on poses (world_T_cam, cam_T_<obj>), with mkref's own functions and defaults:
    table frame, support check (+ its fallback), per-object snap; then the hand joints as mkref writes them (table
    frame, invalid runs filled, parked sides, hand separation). Returns OBJ (T,B,4,4) table frame, {side: (T,21,3)},
    info. Stage (b) does not move objects; its joints feed contact_retarget.rest_settle, which only asks whether a
    fingertip is within 3 cm of an object. mkref's 6 mm joint depenetration (trimesh inside tests, ~2 s per frame on
    this VM) is therefore skipped unless DEPEN; its effect on the rest settle is measured on ep0 and ep2 (a3 'depen')."""
    import trimesh, mkref as MK
    a = types.SimpleNamespace(**MKA); T = len(W_C); B = len(names)
    vis = {n: trimesh.load(f'{lib}/{n}.glb', force='mesh') for n in names}
    n_, d_, frac, npts, rms = MK.fit_table(depth0, KR, W_C[0], {n: camT[n][0] for n in names}, vis, a)
    OBJw = np.stack([np.einsum('tij,tjk->tik', W_C, camT[n]) for n in names], 1)
    centroid = np.mean([OBJw[0, b, :3, :3] @ np.asarray(vis[n].vertices).mean(0) + OBJw[0, b, :3, 3] for b, n in enumerate(names)], 0)
    T_tab = MK.table_frame(n_, d_, W_C[0], centroid, a.table_z)
    obj_in = lambda Tt: np.einsum('ij,tbjk->tbik', Tt, OBJw)                       # noqa: E731
    bottoms = lambda O: np.array([(np.asarray(vis[n].vertices) @ O[0, b, :3, :3].T + O[0, b, :3, 3])[:, 2].min() - a.table_z
                                  for b, n in enumerate(names)])                   # noqa: E731
    OBJ = obj_in(T_tab); h = bottoms(OBJ); lifted = np.zeros(B); fallback = False
    if not -a.support_tol <= h.min() <= a.support_max and a.support_fallback:      # mkref's failure path, verbatim logic
        alt = []
        for c in a._plane_full:
            if c['tilt'] > 25:
                continue
            Tt = MK.table_frame(c['n'], c['d'], W_C[0], centroid, a.table_z); hh = bottoms(obj_in(Tt))
            alt.append((int(((hh >= -a.support_tol) & (hh <= a.support_max)).sum()), -float(np.abs(hh).sum()), c, Tt, hh))
        alt.sort(key=lambda x: x[:2], reverse=True)
        if alt and alt[0][0] > 0:
            _, _, c, T_tab, hh = alt[0]; n_, d_ = c['n'], c['d']; OBJ = obj_in(T_tab); fallback = True
            for b in range(B):
                if hh[b] < -a.support_tol:
                    lifted[b] = -hh[b]; OBJ[:, b, 2, 3] += lifted[b]
            h = bottoms(OBJ)
    support_ok = bool(-a.support_tol <= h.min() <= a.support_max)
    shifts = np.zeros(B)
    for b in range(B):
        if abs(h[b]) <= a.snap_max:
            shifts[b] = -h[b]; OBJ[:, b, 2, 3] += shifts[b]
    dm = MK.table_disc(depth0, KR, T_tab, a.table_z); disc = (0.0, 0.0, a.table_radius)
    if dm is not None:
        radius = [float(np.linalg.norm(np.asarray(vis[n].vertices) - np.asarray(vis[n].vertices).mean(0), axis=1).max()) for n in names]
        reach = float((np.linalg.norm(OBJ[0, :, :2, 3] - dm[:2], axis=-1) + np.array(radius) * 0.5).max())
        disc = (dm[0], dm[1], float(np.clip(max(dm[2], reach), 0.15, 0.6)))
    # stage (b): hand joints exactly as mkref writes them (only what rest_settle reads: the joint positions)
    queries = [MK.BodyQuery(vis[n]) for n in names]; J, hinfo = {}, {}
    obj_pos = OBJ[:, :, :3, 3]
    for sd in MK.SIDES:
        Js = Hn[f'joints_{sd}'].astype(np.float64) @ T_tab[:3, :3].T + T_tab[:3, 3]
        valid = Hn[f'valid_{sd}'].astype(bool); n_valid = int(valid.sum())
        if n_valid < max(10, a.min_valid_frac * T):
            c = obj_pos.reshape(-1, 3).mean(0); sgn = -1.0 if sd == 'right' else 1.0
            for extra in np.arange(0.0, 0.61, 0.1):
                pw = np.array([c[0] - 0.30, c[1] + sgn * (0.35 + extra), a.table_z + 0.25])
                if np.linalg.norm(obj_pos - pw, axis=-1).min() > 0.30:
                    break
            Rpark = np.column_stack([[-1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])
            Js = np.repeat((pw + (MK.TEMPLATE_RIGHT * (np.array([1, 1, -1.0]) if sd == 'left' else 1.0)) @ Rpark.T)[None], T, 0)
            hinfo[sd] = 'parked'
        else:
            Js, _ = MK.fill_invalid(Js, valid, OBJ, queries, a); hinfo[sd] = 'tracked'
            if depen and a.depenetrate > 0:
                Js, _ = MK.depenetrate(Js, OBJ, queries, a.table_z, a.depenetrate, disc)
        J[sd] = Js
    if a.hand_sep > 0 and all(v == 'tracked' for v in hinfo.values()):
        off, _ = MK.separate_hands(J, {sd: Hn[f'valid_{sd}'].astype(bool) for sd in MK.SIDES},
                                   {sd: Hn[f'measured_{sd}'].astype(bool) for sd in MK.SIDES}, a.hand_sep, a.lead_in, a.lead_in_speed / a.fps)
        for sd in MK.SIDES:
            J[sd] = J[sd] + off[sd][:, None, :]
            if depen and a.depenetrate > 0:
                J[sd], _ = MK.depenetrate(J[sd], OBJ, queries, a.table_z, a.depenetrate, disc)
    info = dict(plane_inlier_frac=round(float(frac), 3), plane_rms_mm=round(float(rms) * 1000, 2), support_ok=support_ok,
                support_fallback=fallback, fallback_lift_cm=np.round(lifted * 100, 2).tolist(), bottoms_cm=np.round(h * 100, 2).tolist(),
                snap_cm=np.round(shifts * 100, 2).tolist(), hands=hinfo, disc=np.round(disc, 3).tolist(), joint_depenetration=bool(depen))
    return OBJ, J, T_tab, info


def a3prep_episode(a, ep):
    """O (oracle_poses.py --xform X*_geom) and P, each without and with S2: stage (a)+(b) -> npz for leak_settle.py."""
    import refine
    XF.kit(a.kit); t0 = time.time(); W = f'{a.work}/a3/ep{ep}'; os.makedirs(W, exist_ok=True)
    pd = f'{a.perc}/ep{ep}'; ot3 = a.oracle_t3 or a.t3
    if not os.path.exists(f'{W}/O_raw/poses.npz'):
        cmd = [sys.executable, '-I', f'{REPO}/pipeline/oracle_poses.py', str(ep), pd, f'{W}/O_raw', '--meshes', a.lib, '--xform', a.xgeom,
               '--t3', ot3, '--kit', a.kit, '--depth', f'{pd}/depth0.npy']
        rr = subprocess.run(cmd, capture_output=True, text=True)
        open(f'{W}/O_raw.log', 'w').write(' '.join(cmd) + '\n' + rr.stdout[-20000:] + rr.stderr[-5000:])
        if rr.returncode:
            raise RuntimeError(f'oracle_poses ep{ep}: {rr.stderr[-800:]}')
    import mkref as MK
    KR = MK.rectified_K(f'{ot3}/calib.json'); depth0 = np.load(f'{pd}/depth0.npy')
    hf, _, KRh = hands(pd); Hn = np.load(hf)
    out = dict(episode=ep, KR_vs_hands_max=float(np.abs(KR - KRh).max()), hands_file=os.path.basename(hf), arms={})
    s2 = types.SimpleNamespace(s2_advance=0.545, s2_interp='se3', s2_hold_f0=False)
    for arm, src in (('P', pd), ('O', f'{W}/O_raw')):
        Pz = np.load(f'{src}/poses.npz'); W_C = Pz['world_T_cam'].astype(np.float64)
        names = [k[len('cam_T_'):] for k in Pz.files if k.startswith('cam_T_')]
        names = XF.names_of(a.t3, ep) if sorted(names) == sorted(XF.names_of(a.t3, ep)) else sys.exit(f'ep{ep}: names {names}')
        camT = {n: Pz[f'cam_T_{n}'].astype(np.float64) for n in names}
        for var in ('base', 'S2'):
            if var == 'S2':
                Ow, _ = refine.step_S2(s2, [np.einsum('tij,tjk->tik', W_C, camT[n]) for n in names])
                cT = {n: np.einsum('tij,tjk->tik', np.linalg.inv(W_C), Ow[b]) for b, n in enumerate(names)}
            else:
                cT = camT
            OBJ, J, T_tab, info = mkref_ab(W_C, cT, names, depth0, KR, a.lib, Hn)
            raw = np.stack([np.einsum('tij,tjk->tik', W_C, cT[n]) for n in names], 1)
            np.savez(f'{W}/{arm}_{var}.npz', names=np.array(names), raw_world=raw, OBJ_a=OBJ, J_left=J['left'], J_right=J['right'],
                     T_tab=T_tab, table_z=MKA['table_z'])
            out['arms'][f'{arm}_{var}'] = info
    out['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: a3prep ' + ', '.join(f'{k} snap {v["snap_cm"]} ok {v["support_ok"]}' for k, v in out['arms'].items()) + f' ({out["seconds"]} s)', flush=True)
    return out


def scored(names, M, gt, H, REGk, REGg):  # M (T,B,4,4) lib frames, any world -> lib and * scores
    tr = {n: M[:, b] for b, n in enumerate(names)}
    return dict(lib=XF.score_track(names, tr, gt, H, REGk), star=XF.score_track(names, tr, gt, H, REGg))


A3_STAGES = ('raw', 'a', 'ik', 'settle')


def a3_episode(a, ep):
    D = load(a, ep); W = f'{a.work}/a3/ep{ep}'; t0 = time.time()
    prep = json.load(open(f'{a.work}/a3prep.json'))['episodes'][str(ep)]
    r = dict(episode=ep, objects=D.names, arms={}, prep=prep['arms'])
    for arm in ('P', 'O'):
        for var in ('base', 'S2'):
            Z = np.load(f'{W}/{arm}_{var}.npz'); names = [str(x) for x in Z['names']]; assert names == D.names
            Zs = np.load(f'{W}/{arm}_{var}_settle.npz')
            st = {'raw': scored(names, Z['raw_world'], D.gt, D.H, D.REGk, D.REGg), 'a': scored(names, Z['OBJ_a'], D.gt, D.H, D.REGk, D.REGg)}
            st['ik'] = dict(st['a'], note='E2S + contacts leave object poses unchanged (checked on stored references, a3 stored)')
            st['settle'] = scored(names, Zs['OBJ_settle'], D.gt, D.H, D.REGk, D.REGg)
            st['settle_stats'] = json.loads(str(Zs['stats']))
            r['arms'][f'{arm}_{var}'] = st
    def g(k, stg, conv='star'):
        return r['arms'][k][stg][conv]['AUC']
    r['delta_star'] = {arm: dict(a=round(g(f'{arm}_base', 'a') - g(f'{arm}_base', 'raw'), 4),
                                 settle=round(g(f'{arm}_base', 'settle') - g(f'{arm}_base', 'a'), 4),
                                 S2=round(g(f'{arm}_S2', 'settle') - g(f'{arm}_base', 'settle'), 4),
                                 chain=round(g(f'{arm}_S2', 'settle') - g(f'{arm}_base', 'raw'), 4)) for arm in ('P', 'O')}
    r['delta_star_obj'] = {arm: {n: dict(a=round(r['arms'][f'{arm}_base']['a']['star']['per_obj_AUC'][n] - r['arms'][f'{arm}_base']['raw']['star']['per_obj_AUC'][n], 4),
                                        settle=round(r['arms'][f'{arm}_base']['settle']['star']['per_obj_AUC'][n] - r['arms'][f'{arm}_base']['a']['star']['per_obj_AUC'][n], 4),
                                        S2=round(r['arms'][f'{arm}_S2']['settle']['star']['per_obj_AUC'][n] - r['arms'][f'{arm}_base']['settle']['star']['per_obj_AUC'][n], 4))
                                 for n in D.names} for arm in ('P', 'O')}
    r['seconds'] = round(time.time() - t0, 1)
    print(f'ep{ep}: * O raw {g("O_base", "raw"):.4f} a {g("O_base", "a"):.4f} settle {g("O_base", "settle"):.4f} S2 {g("O_S2", "settle"):.4f} | '
          f'P raw {g("P_base", "raw"):.4f} a {g("P_base", "a"):.4f} settle {g("P_base", "settle"):.4f} S2 {g("P_S2", "settle"):.4f}', flush=True)
    return r


def verdict(d, n_total=None):
    """PLAN §4 reference-level rule on per-episode deltas: leaks (mean >= +0.01, >= 12/20 positive), truth worse (the
    same, negative), no leak (|mean| < 0.005), else inconclusive. 12/20 scales to 0.6 n for fewer episodes."""
    d = np.asarray(d, float); n = len(d); need = int(np.ceil(0.6 * n)); m = float(d.mean())
    pos, neg = int((d > 0).sum()), int((d < 0).sum())
    v = ('leaks' if m >= 0.01 and pos >= need else 'truth worse / construction defect' if m <= -0.01 and neg >= need
         else 'no leak' if abs(m) < 0.005 else 'inconclusive')
    return dict(n=n, mean=round(m, 4), pos=pos, neg=neg, zero=int(n - pos - neg), min=round(float(d.min()), 4), max=round(float(d.max()), 4), verdict=v)


def a3_summary(res):
    out = {}
    for arm in ('P', 'O'):
        out[arm] = {k: verdict([r['delta_star'][arm][k] for r in res]) for k in ('a', 'settle', 'S2', 'chain')}
        out[arm]['R_star_mean'] = {f'{var}:{stg}': round(float(np.mean([r['arms'][f'{arm}_{var}'][stg]['star']['AUC'] for r in res])), 4)
                                   for var in ('base', 'S2') for stg in A3_STAGES}
        out[arm]['R_lib_mean'] = {f'{var}:{stg}': round(float(np.mean([r['arms'][f'{arm}_{var}'][stg]['lib']['AUC'] for r in res])), 4)
                                  for var in ('base', 'S2') for stg in A3_STAGES}
    # PLAN §4 action rule for L4: a stage that costs >= 0.02 on O (per object) in >= 3 episodes
    out['O_stage_costs_ge_0p02'] = {k: [(r['episode'], n) for r in res for n, d in r['delta_star_obj']['O'].items() if d[k] <= -0.02]
                                    for k in ('a', 'settle', 'S2')}
    return out


def ref_track(parquet, warm=0):
    import pyarrow.parquet as pq
    t = pq.read_table(parquet, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = [str(x) for x in t.column('object_body_names')[0].as_py()]
    pos = np.array(t.column('object_body_position')[0].as_py(), float)[warm:]; q = np.array(t.column('object_body_wxyz')[0].as_py(), float)[warm:]
    M = np.repeat(np.eye(4)[None, None], len(pos), 0).repeat(len(names), 1)
    M[..., :3, :3] = Rot.from_quat(q[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(len(pos), len(names), 3, 3); M[..., :3, 3] = pos
    return names, M


def a3_stored(a):
    """Stored real references (older perception and code) where local: loaded (mkref a+b) / E2S (IK + contacts) /
    processed (contact retarget, rest_settle when the run set it) / grasp lock (the trained reference). P only."""
    import glob
    XF.kit(a.kit); out = []
    for e in json.load(open(a.stored)):
        ep = int(e['ep']); D = load(a, ep); rows = {}
        for stage, pat, warm in (('loaded', f'{e["tree"]}/loaded/*/*/*.parquet', 10), ('e2s', f'{e["tree"]}/e2s_reference.parquet', 0),
                                 ('processed', f'{e["tree"]}/processed/*/*/*.parquet', 0), ('glock', f'{e.get("glock", "-")}/processed/*/*/*.parquet', 0)):
            fs = sorted(glob.glob(pat))
            if stage == 'glock':
                fs = [f for f in fs if f.endswith('ref_gl_ilc.parquet')] or fs
            if not fs:
                continue
            names, M = ref_track(fs[0], warm)
            assert names == D.names, (names, D.names)
            N = min(len(M), D.N)
            if len(M) != D.N:
                rows[f'{stage}_frames'] = int(len(M))
            gt = {n: D.gt[n][:N] for n in names}
            rows[stage] = scored(names, M[:N], gt, D.H, D.REGk, D.REGg); rows[stage]['file'] = fs[0]; rows[f'_{stage}'] = M[:N]
        if '_loaded' in rows and '_e2s' in rows:
            rows['loaded_vs_e2s_max_cm'] = round(float(np.abs(rows['_loaded'][..., :3, 3] - rows['_e2s'][..., :3, 3]).max() * 100), 4)
        if '_loaded' in rows and '_processed' in rows:
            rows['loaded_vs_processed_max_cm'] = round(float(np.abs(rows['_loaded'][..., :3, 3] - rows['_processed'][..., :3, 3]).max() * 100), 4)
        out.append(dict(ep=ep, run=e['run'], **{k: v for k, v in rows.items() if not k.startswith('_')}))
        print(f'stored ep{ep} {e["run"]}: ' + ', '.join(f'{k} {v["star"]["AUC"]:.4f}' for k, v in rows.items() if isinstance(v, dict) and 'star' in v), flush=True)
    return out


def a6_check(a):
    F = json.load(open(a.frames_check)); s = F['summary']
    return dict(source=os.path.abspath(a.frames_check), source_md5=md5(a.frames_check), pass_flags=s['pass'], all_pass=all(s['pass'].values()),
                a1_mocap_scan_min=s['a1_min'], a2_mocap_Xkit_min=s['a2_min'], a3_mocap_Xgeom_lib_mean=s['a3_mean'], a3_min=s['a3_min'],
                a4_round_trip_max_abs=s['a4_round_trip_max_abs'], b1_two_ways_max_abs=s['b1_max_abs_delta'], b2_cup_spin_max_abs=s['b2_max_abs_delta'],
                b1b_budget_scan_max_abs=s['b1b_budget_scan_max_abs_delta'], rule=dict(a1_a2='>= 0.9995 (1.000)', b1_b2='<= 0.002'))


# ---------------- a7: hands-free settle of the mocap rest configurations (prep here, physics in leak_settle.py)
CARVES = {2: 'ev01', 11: 'ev10', 12: 'ev14', 13: 'ev14', 24: 'ev25', 27: 'ev28', 31: 'ev30'}   # meshes/carve/<eval twin>
SNAP_MAX, REST_MIN = 0.02, 10


def a7_assets(a):
    """Simulator assets (make_assets.py, placeholder 0.3 kg): lib = library_v3; lib+carve = library_v3 with the eval
    twin's placement-carve pieces (meshes/carve/ev*); scan = the public scans (boards and sweeper: their
    _collision.glb), the scanlib recipe of ops/jobs/physics_arms.sh."""
    A = f'{a.work}/a7/assets'; os.makedirs(A, exist_ok=True); mk = f'{REPO}/pipeline/make_assets.py'; out = {}

    def make(tag, lib, extra=()):
        d = f'{A}/{tag}'
        if not os.path.exists(f'{d}/urdf'):
            subprocess.run([sys.executable, '-I', mk, lib, d, *extra], check=True, capture_output=True)
        out[tag] = d
    make('lib', a.lib)
    for c in sorted(set(CARVES.values())):
        make(f'lib_{c}', a.lib, ('--pieces', f'{REPO}/meshes/carve/{c}'))
    sl = f'{A}/scanlib_src'; os.makedirs(sl, exist_ok=True)
    for n in sorted(os.listdir(f'{a.t3}/mesh')):
        f = f'{a.t3}/mesh/{n}/{n}.glb'
        f = f if os.path.exists(f) else f'{a.t3}/mesh/{n}/{n}_collision.glb'
        if os.path.exists(f) and n != 'wooden_spoon' and not os.path.lexists(f'{sl}/{n}.glb'):
            os.symlink(os.path.realpath(f), f'{sl}/{n}.glb')
    make('scan', sl)
    return out


def rest_configs(D):
    """Mocap frames where every object rests (no true motion, refine thresholds) for >= REST_MIN frames: frame 0, then the
    middle of each such segment that differs from the last kept one (> 1 cm or > 5 deg for some object). A
    configuration with an object > 2 cm above the table and not on another object (held in the air) is dropped."""
    from scipy.spatial import cKDTree
    N = D.N; mv = np.zeros(N, bool)
    for s, n in enumerate(D.names):
        mv |= true_motion(D.gt[n], D.H[s]['anchor'])[0]
    import refine
    cand = [0] + [int((s0 + e0 - 1) // 2) for s0, e0 in refine.runs(~mv) if e0 - s0 >= REST_MIN and (s0 + e0 - 1) // 2 > 0]
    V = {n: D.H[s]['mesh'][0][::5] for s, n in enumerate(D.names)}
    world = lambda n, t: V[n] @ D.gt[n][t][:3, :3].T + D.gt[n][t][:3, 3]           # noqa: E731
    z_t = min(world(n, 0)[:, 2].min() for n in D.names)                            # the table: lowest frame-0 bottom
    keep, dropped = [], []
    for t in cand:
        if keep and all(np.linalg.norm(D.gt[n][t][:3, 3] - D.gt[n][keep[-1]][:3, 3]) < 0.01 and
                        XF.rot_deg(D.gt[n][t][:3, :3] @ D.gt[n][keep[-1]][:3, :3].T) < 5 for n in D.names):
            continue
        ok = True
        for n in D.names:
            P = world(n, t); low = P[P[:, 2] < P[:, 2].min() + 0.005]
            if P[:, 2].min() - z_t <= SNAP_MAX:
                continue
            if not any(cKDTree(world(m, t)).query(low)[0].min() < 0.01 for m in D.names if m != n):
                ok = False
        (keep if ok else dropped).append(t)
    return keep, dropped, z_t


def a7prep_episode(a, ep):
    D = load(a, ep); W = f'{a.work}/a7/ep{ep}'; os.makedirs(W, exist_ok=True)
    assets = json.load(open(f'{a.work}/a7/assets.json'))
    keep, dropped, z_t = rest_configs(D)
    c = np.mean([D.gt[n][0][:3, 3] for n in D.names], 0)
    T_tab = np.eye(4); T_tab[:3, 3] = [-c[0], -c[1], MKA['table_z'] - z_t]           # mocap z is up (gravity)
    geoms = {'lib': assets['lib'], 'scan': assets['scan']}
    if ep in CARVES:
        geoms['lib_carve'] = assets[f'lib_{CARVES[ep]}']
    r = dict(episode=ep, objects=D.names, frames=keep, dropped_held=dropped, table_mocap_z=round(float(z_t), 4), geoms={})
    import trimesh
    for g, A in geoms.items():
        Xr = {n: (np.eye(4) if g == 'scan' else D.Xg[n]) for n in D.names}           # scan frames, or lib frames by X*_geom
        Cf = np.stack([np.stack([T_tab @ D.gt[n][t] @ Xr[n] for n in D.names]) for t in keep])
        vis = {n: np.asarray(trimesh.load(f'{A}/mesh/{n}/{n}.glb', force='mesh').vertices) for n in D.names}
        h = np.array([(vis[n] @ Cf[0, b, :3, :3].T + Cf[0, b, :3, 3])[:, 2].min() - MKA['table_z'] for b, n in enumerate(D.names)])
        snap = np.where(np.abs(h) <= SNAP_MAX, -h, 0.0); Cf[:, :, 2, 3] += snap[None]  # mkref's per-object snap (frame 0)
        f = f'{W}/{g}.npz'
        np.savez(f, names=np.array(D.names), configs=Cf, frames=np.array(keep), assets=A)
        r['geoms'][g] = dict(npz=f, assets=A, f0_bottom_cm=np.round(h * 100, 2).tolist(), snap_cm=np.round(snap * 100, 2).tolist())
    print(f'ep{ep}: rest configs {keep} (dropped as held {dropped}); geoms {list(geoms)}', flush=True)
    return r


def a7_hand_gaps(a, ep):
    """Per rest-configuration frame and object, the nearest measured fingertip to the true surface (cm): a settle failure
    with a hand within ~3 cm may be a configuration the hand was holding, not a geometry defect."""
    D = load(a, ep); P = json.load(open(f'{a.work}/a7prep.json'))['episodes'][str(ep)]
    Gi = np.linalg.inv(np.asarray(json.load(open(a.xtrk))['episodes'][str(ep)]['fit']['G_mocap_T_perc']))
    _, J, _ = hands(f'{a.perc}/ep{ep}'); out = {}
    for s, n in enumerate(D.names):
        g = tip_gap_cm(J, np.einsum('ij,tjk->tik', Gi, D.gt[n]), surface_tree(*D.H[s]['mesh']))
        for F in P['frames']:
            out.setdefault(str(F), {})[n] = (round(float(g[F]), 2) if np.isfinite(g[F]) else None)
    return str(ep), out


def a7_read(a, eps):
    prep = json.load(open(f'{a.work}/a7prep.json'))['episodes']; out = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        gaps = dict(ex.map(a7_hand_gaps, [a] * len(eps), eps))
    for ep in eps:
        P = prep[str(ep)]; out[str(ep)] = dict(objects=P['objects'], frames=P['frames'], dropped_held=P['dropped_held'], geoms={})
        for g, d in P['geoms'].items():
            f = d['npz'][:-4] + '_settle.json'
            if not os.path.exists(f):
                out[str(ep)]['geoms'][g] = dict(missing=f); continue
            S = json.load(open(f)); rows = {}
            for F, c in S['configs'].items():
                drift = {n: c[n]['at_2s'] for n in P['objects'] if n in c}
                ok = c['nan_at_step'] is None and len(drift) == len(P['objects']) and all(v[0] <= 1.0 and v[1] <= 5.0 for v in drift.values())
                rows[F] = dict(at_2s=drift, peak={n: c[n]['peak'] for n in P['objects'] if n in c}, nan=c['nan_at_step'], pass_=bool(ok),
                               hand_gap_cm=gaps[str(ep)].get(F))
            out[str(ep)]['geoms'][g] = dict(configs=rows, n=len(rows), n_pass=int(sum(x['pass_'] for x in rows.values())),
                                            gate_pass=bool(rows) and all(x['pass_'] for x in rows.values()),
                                            snap_cm=d['snap_cm'], build_sec=S.get('build_sec'), collide_shapes=S.get('collide_shapes'))
    summ = {g: dict(eps=sum(g in v['geoms'] for v in out.values()), gate_pass=[int(e) for e, v in out.items() if v['geoms'].get(g, {}).get('gate_pass')],
                    gate_fail=[int(e) for e, v in out.items() if g in v['geoms'] and not v['geoms'][g].get('gate_pass')])
            for g in ('lib', 'lib_carve', 'scan')}
    return dict(a7=out, summary=summ)


# ---------------- driver
def _run(args):
    fn, a, ep = args
    return fn(a, ep)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['a1', 'a1seed', 'a2', 'a3prep', 'a3', 'a4', 'a6', 'a7prep', 'a7'])
    p.add_argument('--perc', required=True); p.add_argument('--xgeom', required=True); p.add_argument('--xtrk', required=True)
    p.add_argument('--lib', required=True); p.add_argument('--t3', required=True); p.add_argument('--kit', required=True)
    p.add_argument('--work', required=True, help='scratch dir (must contain "oracle")'); p.add_argument('--out', required=True)
    p.add_argument('--episodes', default=','.join(map(str, PUBLIC))); p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--n_perturb', type=int, default=50)
    p.add_argument('--n_seed', type=int, default=50, help='a1seed: pseudo episode seeds per (object, slot)')
    p.add_argument('--a4_window', type=int, default=40, help='a4: frames searched before / after a true motion segment')
    p.add_argument('--oracle_t3', default=None, help='a3prep: T3 dir with calib.json for oracle_poses.py (default --t3)')
    p.add_argument('--stored', default=None, help='a3: json list of stored reference trees [{ep, stage, tree, lib}]')
    p.add_argument('--frames_check', default=None, help='a6: tierA/frames_check.json')
    p.add_argument('--settle', default=None, help='a3/a7: leak_settle.py output dir')
    a = p.parse_args()
    eps = guard(a)
    os.makedirs(a.work, exist_ok=True); t0 = time.time()
    fn = dict(a1=a1_episode, a2=a2_episode, a3prep=a3prep_episode, a3=a3_episode, a4=a4_episode, a7prep=a7prep_episode).get(a.mode)
    if a.mode == 'a7prep':
        json.dump(a7_assets(a), open(f'{a.work}/a7/assets.json', 'w'), indent=1)
    res = []
    if fn is not None:
        with ProcessPoolExecutor(a.jobs) as ex:
            res = list(ex.map(_run, [(fn, a, e) for e in eps]))
    out = dict(mode=a.mode, note='ORACLE DIAGNOSTIC (public mocap + scans), leak-decomp Tier A; never a default, never for eval inference',
               code=code_version(), inputs=dict(perc=os.path.abspath(a.perc), xgeom=os.path.abspath(a.xgeom), xgeom_md5=md5(a.xgeom),
                                                xtrk=os.path.abspath(a.xtrk), xtrk_md5=md5(a.xtrk), lib=os.path.abspath(a.lib),
                                                t3=os.path.abspath(a.t3), kit=os.path.abspath(a.kit)),
               argv=sys.argv, episodes={str(r['episode']): r for r in res})
    summ = dict(a1=a1_summary, a2=a2_summary, a3=a3_summary, a4=a4_summary).get(a.mode)
    if summ:
        out['summary'] = summ(res)
    if a.mode == 'a6':
        out['summary'] = a6_check(a)
    if a.mode == 'a7':
        out.update(a7_read(a, eps))
    if a.mode == 'a1seed':
        out['episodes'], out['summary'] = a1seed(a, eps)
    if a.mode == 'a3' and a.stored:
        out['stored'] = a3_stored(a)
    out['seconds'] = round(time.time() - t0, 1)
    json.dump(out, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps(out.get('summary', {}), indent=1, default=float)[:4000])
    print(f'wrote {a.out} ({out["seconds"]} s)')


if __name__ == '__main__':
    main()
