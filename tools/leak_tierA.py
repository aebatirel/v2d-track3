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
       [--episodes 0,2,...] [--jobs 4] [--n_perturb 50]      (DIR must contain 'oracle'; MODE in a1 a2 a3prep a3 a4 a6 a7)
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
    HOLES patches (nearest faces to area-weighted random centres) that remove HOLE_AREA of the surface in total."""
    import fast_simplification
    v2, f2 = fast_simplification.simplify(np.asarray(v, np.float32), np.asarray(f, np.int32), target_reduction=1 - keep)
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
    for n in names:
        C = np.linalg.inv(A[n][0]) @ Mw[n][0]
        tracks['body'][n] = np.einsum('tij,jk->tik', A[n], C @ D.Xg[n])                             # back to lib frames
        tracks['world'][n] = np.einsum('ij,tjk->tik', Mw[n][0] @ np.linalg.inv(A[n][0]), D.Tp[n])
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


def a4_episode(a, ep, W=40):
    D = load(a, ep); t0 = time.time(); N, names = D.N, D.names
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
        mp = refine.moving_labels(np.einsum('tij,jk->tik', D.Tp[n], np.linalg.inv(D.Xg[n])), D.H[s]['anchor'])   # our track
        near = gap_true < NEAR_CM; seg = segments(runs_); ev = []
        for k, (s0, e0) in enumerate(seg):
            lo = max(0, s0 - W, seg[k - 1][1] if k else 0); hi = min(N, e0 + W, seg[k + 1][0] if k + 1 < len(seg) else N)
            idx = np.nonzero(near[lo:hi])[0] + lo; pm = np.nonzero(mp[lo:hi])[0] + lo
            ev.append(dict(segment=[int(s0), int(e0)], arrival_lag=(int(idx[0] - s0) if len(idx) else None),
                           leave_lag=(int(idx[-1] - (e0 - 1)) if len(idx) else None),
                           perc_onset_lag=(int(pm[0] - s0) if len(pm) else None), perc_end_lag=(int(pm[-1] - (e0 - 1)) if len(pm) else None),
                           measured_frac=round(float(meas_any[s0:e0].mean()), 3)))
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
                arrival_lag_all=q(col(segs, 'arrival_lag')), leave_lag_all=q(col(segs, 'leave_lag')),
                arrival_lag_first=q(col(first, 'arrival_lag')), leave_lag_last=q(col(last, 'leave_lag')),
                perc_onset_lag_all=q(col(segs, 'perc_onset_lag')), perc_end_lag_all=q(col(segs, 'perc_end_lag')),
                perc_onset_lag_first=q(col(first, 'perc_onset_lag')), perc_end_lag_last=q(col(last, 'perc_end_lag')),
                gap_true_cm_median_over_objects=q(gaps), gap_perc_cm_median_over_objects=q(gp))


a3prep_episode = a3_episode = a3_summary = a6_check = a7_read = a3_stored = None  # STUBS


# ---------------- driver
def _run(args):
    fn, a, ep = args
    return fn(a, ep)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['a1', 'a2', 'a3prep', 'a3', 'a4', 'a6', 'a7'])
    p.add_argument('--perc', required=True); p.add_argument('--xgeom', required=True); p.add_argument('--xtrk', required=True)
    p.add_argument('--lib', required=True); p.add_argument('--t3', required=True); p.add_argument('--kit', required=True)
    p.add_argument('--work', required=True, help='scratch dir (must contain "oracle")'); p.add_argument('--out', required=True)
    p.add_argument('--episodes', default=','.join(map(str, PUBLIC))); p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--n_perturb', type=int, default=50)
    p.add_argument('--oracle_t3', default=None, help='a3prep: T3 dir with calib.json for oracle_poses.py (default --t3)')
    p.add_argument('--stored', default=None, help='a3: json list of stored reference trees [{ep, stage, tree, lib}]')
    p.add_argument('--frames_check', default=None, help='a6: tierA/frames_check.json')
    p.add_argument('--settle', default=None, help='a3/a7: leak_settle.py output dir')
    a = p.parse_args()
    eps = guard(a)
    os.makedirs(a.work, exist_ok=True); t0 = time.time()
    fn = dict(a1=a1_episode, a2=a2_episode, a3prep=a3prep_episode, a3=a3_episode, a4=a4_episode).get(a.mode)
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
    if a.mode == 'a3' and a.stored:
        out['stored'] = a3_stored(a)
    out['seconds'] = round(time.time() - t0, 1)
    json.dump(out, open(a.out, 'w'), indent=1, default=float)
    print(json.dumps(out.get('summary', {}), indent=1, default=float)[:4000])
    print(f'wrote {a.out} ({out["seconds"]} s)')


if __name__ == '__main__':
    main()
