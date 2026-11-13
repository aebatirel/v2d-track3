"""$0 GT-free eval screen (tracker-fix PLAN §4 item 2), thresholds frozen in PLAN §3 / the four DIAGs.
Reads only our own stored eval perception outputs (det_f0.npz, vo.json, poses.npz, track_guard.json, hands_refined.npz)
and our meshes. Eval episodes have no ground truth; nothing here reads mocap, scans or observation.objects poses, and
nothing is changed or tuned. Every input path is passed through pipeline/refine.assert_inference_input first.
The public mode (--public) runs the same code on the 25 Oct public tracks (refine/in) and the Phase-1 P_o tracks, again
without any ground truth, only to check that this copy reproduces the GT-free numbers in the DIAGs.

Screens (thresholds as frozen):
  A  area ratio of the chosen frame-0 proposals (metric area / largest template silhouette; flag > 1.5)   ep0 DIAG F1
  B  S9 backfill trigger on guard re-acquisitions (jump > 5 cm or > 30 deg at k; [0,k) within 4 cm / 25 deg) ep0 F2
  C  vo.json keyframe burst (>= 4 switches in 25 frames) + rule K (S7) camera correction, gated at >= 1 cm  ep24 F2
  D  post-guard mask coverage of the rotation anchor (flag < 0.70: the S8/F1g gate)                          ep31 F1g
  E  S6 static hold (horizontal travel < 2 cm; non-axisymmetric also rotation < 10 deg)                      ep11 F1
  +  supplementary: frame-to-frame jumps > 5 cm / 30 deg; frames a TRACK_GUARD would call implausible (low 5 % of the
     surface > 2 cm under our frame-0 table plane), for tracks made without the guard.
Usage: python -I eval_screen.py OUT_JSON            (eval)
       python -I eval_screen.py OUT_JSON --public   (public reproduction check, no GT)
"""
import json, os, sys
import numpy as np, trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/pipeline')
import det_rules  # noqa: E402
from refine import assert_inference_input  # noqa: E402

EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
P6 = '20261026-pack6-5203d42'
SRC = {8: '20261025-evb0810-ee7ba8e', 14: '20261025-evb1420-ee7ba8e', 25: '20261026-c25s42-feb0407',
       30: '20261025-std30-ee7ba8e', 32: '20261026-fr32s46b-5e0e100', 33: '20261026-fr3233s43-6a8a0e2'}
# guard re-detection dumps present in the store listing (det_f<k>.npz names; frame k of each re-detection)
REDET = {14: [46], 32: [21, 34], 33: [91]}
DL = f'{S}/screen/dl/runs'
SYMOBJ = {'beige_cup', 'blue_cup'}                    # axisymmetric (S6 skips the rotation test; scorer: no rotation anchor)
NO_ANCHOR = {'beige_cup', 'blue_cup', 'white_pot_lid'}   # objects with a kit symmetry axis (cups: axial; lid: half turn)
AREA_SET = [1, 3, 5, 6, 8, 20, 28]; S9_SET = [8, 14, 32, 33]; COV_SET = [30, 19, 32, 33, 35, 36, 37]


def lib(ep, n, public=False):
    if not public and ep == 8 and n == 'beige_cup':
        return f'{REPO}/meshes/library_v3x'               # evb0810 tracked eval 8 with the v3x beige cup (template extent 0.188)
    return f'{REPO}/meshes/library_v3'


def inputs(ep, public):
    if public:
        R = f'{S}/refine/in/ep{ep}'
        d = dict(det=f'{R}/det_f0.npz', vo=f'{R}/vo.json', hands=f'{R}/hands_refined.npz', poses=f'{R}/poses.npz',
                 tg=f'{R}/track_guard.json', pw_po=f'{S}/leak/p1/oracle_roots/Po/ep{ep}/poses_world_vo.npz')
    else:
        r = SRC.get(ep, P6)
        pp = (f'{S}/daudit/dl_evsrc/runs/{r}/perc2/ep{ep}/poses.npz' if ep in SRC
              else f'{S}/daudit/dl_evposes/runs/{P6}/perc2/ep{ep}/poses.npz')
        d = dict(det=f'{DL}/{r}/perc2/ep{ep}/det_f0.npz', vo=f'{DL}/{r}/perc2/ep{ep}/vo.json',
                 hands=f'{DL}/{r}/refs/perc2mck/ep{ep}/hands_refined.npz', poses=pp,
                 tg=f'{DL}/{r}/perc2/ep{ep}/track_guard.json', run=r)
    for k, v in d.items():
        if k != 'run' and os.path.exists(v):
            assert_inference_input(v)
    return d


# ------------------------------------------------------------------ geometry helpers
_MS = {}
def mesh(path):
    if path not in _MS:
        _MS[path] = trimesh.load(path, force='mesh')
    return _MS[path]


def max_sil(path):            # ep0 scripts/area_gate.py, verbatim logic
    m = mesh(path); P = np.asarray(m.sample(6000)); P -= P.mean(0); best = 0
    for d in trimesh.creation.icosphere(subdivisions=2).vertices:
        d = d / np.linalg.norm(d); a = np.cross(d, [0, 0, 1.0] if abs(d[2]) < 0.9 else [0, 1.0, 0]); a /= np.linalg.norm(a); b = np.cross(d, a)
        best = max(best, ConvexHull(np.stack([P @ a, P @ b], 1)).volume)
    return best


def sym_axis(points):          # pipeline/mesh_gates.sym_axis('axial') without the kit: PCA axis most invariant under 90 deg
    P = points - points.mean(0); _, _, Vt = np.linalg.svd(P, full_matrices=False); tree = cKDTree(P); best = None
    for k in range(3):
        a = Vt[k]; R = Rot.from_rotvec(a * np.pi / 2).as_matrix(); dd = tree.query(P @ R.T)[0].mean()
        if best is None or dd < best[0]:
            best = (dd, a)
    return best[1]


def rotdeg(Ra, Rb):
    return np.degrees(Rot.from_matrix(np.einsum('...ji,...jk->...ik', Ra, Rb)).magnitude())


def world(P):
    W = P['world_T_cam'].astype(float)
    return {k[6:]: np.einsum('nij,njk->nik', W, P[k].astype(float)) for k in P.files if k.startswith('cam_T_')}


def plane_of(det):            # TRACK_GUARD / S6 plane: det_rules.table_plane on our frame-0 depth (half res) + K/2
    K2 = np.diag([0.5, 0.5, 1.0]) @ det['K'].astype(float)
    return det_rules.table_plane(det['depth'].astype(np.float32), K2)


# ------------------------------------------------------------------ A: area ratio (ep0 F1)
def screen_area(ep, det, public):
    sh = det['mask_shape']; mk = np.unpackbits(det['masks'], axis=-1)[:, :, :sh[2]].astype(bool)
    dep = det['depth'].astype(np.float32); fh = det['K'][0, 0] * 0.5
    A = np.array([float(((dep[m & (dep > 0)] / fh) ** 2).sum() * (m.sum() / max((m & (dep > 0)).sum(), 1))) for m in mk])
    Sr = det['score_rules']; out = {}
    for a, n in enumerate([str(x) for x in det['names']]):
        C = max_sil(f'{lib(ep, n, public)}/{n}.glb'); j = int(det['chosen'][a]); big = A / C > 1.5
        elig = big & (Sr[a] > -10); best_big = float(Sr[a][elig].max()) if elig.any() else None
        out[n] = dict(chosen=j, area_cm2=round(A[j] * 1e4, 0), tpl_max_sil_cm2=round(C * 1e4, 0), ratio=round(float(A[j] / C), 3),
                      flag=bool(A[j] / C > 1.5), score_chosen=round(float(Sr[a, j]), 3), n_oversized_eligible=int(elig.sum()),
                      best_oversized=(None if best_big is None else round(best_big, 3)),
                      margin=(None if best_big is None else round(float(Sr[a, j]) - best_big, 3)),
                      oversized=[(int(k), round(float(A[k] / C), 2), round(float(Sr[a, k]), 3)) for k in np.where(elig)[0]])
    return out


# ------------------------------------------------------------------ B: S9 trigger (ep0 F2) + supplementary jumps
def screen_s9(ep, Wd, names, frames, public):
    out = {}
    for n in names:
        P = Wd[n]; ks = frames.get(n, [])
        if not ks:
            continue
        k = ks[0]
        jt = float(np.linalg.norm(P[k, :3, 3] - P[k - 1, :3, 3]) * 100); jr = float(rotdeg(P[k - 1, :3, :3], P[k, :3, :3]))
        mt = float(np.linalg.norm(P[:k, :3, 3] - P[0, :3, 3], axis=1).max() * 100)
        mr = float(rotdeg(np.repeat(P[:1, :3, :3], k, 0), P[:k, :3, :3]).max())
        fire = (jt > 5 or jr > 30) and mt < 4 and mr < 25
        e = dict(k=k, all_k=ks, jump_cm=round(jt, 2), jump_deg=round(jr, 1), pre_motion_cm=round(mt, 2), pre_motion_deg=round(mr, 1),
                 fires=bool(fire))
        if n in SYMOBJ:            # spin-free reading for an axisymmetric object (side information; the frozen rule is above)
            ax = sym_axis(trimesh.sample.sample_surface(mesh(f'{lib(ep, n, public)}/{n}.glb'), 4000, seed=1)[0])
            A = np.einsum('nij,j->ni', P[:, :3, :3], ax)
            tilt = lambda a, b: float(np.degrees(np.arccos(np.clip(a @ b, -1, 1))))
            jr_ax = tilt(A[k - 1], A[k]); mr_ax = max(tilt(A[0], A[i]) for i in range(k))
            e.update(jump_axis_deg=round(jr_ax, 1), pre_motion_axis_deg=round(mr_ax, 1),
                     fires_spin_free=bool((jt > 5 or jr_ax > 30) and mt < 4 and mr_ax < 25))
        # per-frame translation after k for context: where the object goes next (cm from its frame-0 position)
        e['travel_after_k_cm'] = round(float(np.linalg.norm(P[k:, :3, 3] - P[0, :3, 3], axis=1).max() * 100), 1)
        out[n] = e
    return out


def jumps(Wd):
    hits = []
    for n, P in Wd.items():
        dt = 100 * np.linalg.norm(np.diff(P[:, :3, 3], axis=0), axis=1); da = rotdeg(P[:-1, :3, :3], P[1:, :3, :3])
        for k in np.where((dt > 5) | (da > 30))[0]:
            hits.append(f'{n}@f{k + 1} {dt[k]:.1f}cm {da[k]:.0f}deg')
    return hits


def implausible(ep, Wd, pl, public):
    if pl is None:
        return None
    nrm, c = np.asarray(pl[0], float), float(pl[1]); out = {}
    for n, P in Wd.items():
        G = trimesh.sample.sample_surface(mesh(f'{lib(ep, n, public)}/{n}.glb'), 400, seed=0)[0]
        X = np.einsum('nij,vj->nvi', P[:, :3, :3], G) + P[:, None, :3, 3]
        low = np.percentile(X @ nrm + c, 5, axis=1)
        bad = np.where(low < -0.02)[0]
        out[n] = dict(n_implausible=int(len(bad)), first=(int(bad[0]) if len(bad) else None), min_low5_cm=round(float(low.min() * 100), 2))
    return out


# ------------------------------------------------------------------ C: VO burst + rule K (ep24 F2), copied from vo_anchor_test2.py
def burst(kfs, W=25):
    sw = [x for x in kfs if x > 0]; best = (0, None)
    for a in sw:
        c = sum(1 for b in sw if a <= b < a + W)
        if c > best[0]:
            best = (c, a)
    return best


D_H = 0.03; REST_MIN = 5; V_REST = 0.0015; KW = 2; DEAD = 0.002; JUMP = 0.015; AGREE = 0.005   # primary setting h3_r5_w2


def lib_pts(ep, n, public, k=200):
    return trimesh.sample.sample_surface(mesh(f'{lib(ep, n, public)}/{n}.glb'), k, seed=3)[0]


def ruleK(T, P, J, Jv, names, kfs):
    N = len(T[names[0]])
    X = {n: np.einsum('nij,vj->nvi', T[n][:, :3, :3], P[n]) + T[n][:, None, :3, 3] for n in names}
    dh = {}
    for n in names:
        d = np.full(N, np.inf)
        for i in range(N):
            if Jv[i].any():
                d[i] = cKDTree(X[n][i]).query(J[i][Jv[i]], k=1)[0].min()
        dh[n] = d
    cen = {n: X[n].mean(1) for n in names}
    gap = {}
    for a in names:
        for b in names:
            if a < b:
                g = np.array([cKDTree(X[b][i]).query(X[a][i], k=1)[0].min() for i in range(N)])
                gap[(a, b)] = gap[(b, a)] = g
    spd = {n: np.r_[0, np.linalg.norm(np.diff(cen[n], axis=0), axis=1)] for n in names}
    cand = {}
    for n in names:                                    # windows(..., relay=True)
        ok = dh[n] >= D_H
        first = int(np.argmax(~ok)) if (~ok).any() else N
        st = np.arange(N) < first
        run = 0; inside = False
        for i in range(N):
            if not ok[i]:
                inside = False; run = 0; continue
            if inside:
                st[i] = True; continue
            run = run + 1 if spd[n][i] < V_REST else 0
            if run >= REST_MIN:
                st[i - REST_MIN + 1:i + 1] = True; inside = True
        cand[n] = st
    near = np.zeros(N, bool)                           # correct()
    for k in kfs[1:]:
        near[max(0, k - KW):min(N, k + KW + 1)] = True
    c = np.zeros(3); C = np.zeros((N, 3)); ref = {n: None for n in names}; banned = set(); log = []
    for i in range(N):
        act = []
        for n in names:
            if not cand[n][i]:
                ref[n] = None; banned.discard(n); continue
            if n in banned:
                continue
            if any(gap[(n, o)][i] < 0.01 and not cand[o][i] for o in names if o != n):
                ref[n] = None; banned.add(n); continue
            if ref[n] is None:
                ref[n] = np.mean([cen[n][j] + c for j in range(i, min(N, i + 3))], 0)
            act.append(n)
        if act and near[i]:
            rs = np.array([ref[n] - (cen[n][i] + c) for n in act]); r = rs.mean(0)
            agree = len(act) < 2 or np.linalg.norm(rs - r, axis=1).max() < AGREE
            if np.linalg.norm(r) > JUMP or not agree:
                banned.update(act); log.append((i, 'ban', act, np.round(r * 100, 2).tolist()))
            elif np.linalg.norm(r) > DEAD:
                c = c + r; log.append((i, 'absorb', act, np.round(r * 100, 2).tolist()))
        for n in act:
            if not near[i] and n not in banned:
                ref[n] = cen[n][i] + c
        C[i] = c
    mag = np.linalg.norm(C, axis=1) * 100
    return dict(corr_cm_max=round(float(mag.max()), 2), corr_cm_end=round(float(mag[-1]), 2),
                n_absorb=sum(1 for x in log if x[1] == 'absorb'), n_ban=sum(1 for x in log if x[1] == 'ban'),
                anchored_frames={n: int(cand[n].sum()) for n in names}, gate_1cm=bool(mag.max() >= 1.0),
                log=[[int(x[0]), x[1], x[2], x[3]] for x in log][:40])


# ------------------------------------------------------------------ D: mask coverage (ep31 scripts/coverage_all.py logic)
_SM = {}
def cov_pts(path, n):
    if path not in _SM:
        _SM[path] = trimesh.sample.sample_surface(mesh(path), 400000 if n == 'plastic_dish_rack' else 150000, seed=11)[0]
    return _SM[path]


def screen_cov(ep, det, Wd, W0, names, public):
    K2 = np.diag([0.5, 0.5, 1.0]) @ det['K'].astype(float)
    Hh, Ww = int(det['mask_shape'][1]), int(det['mask_shape'][2])
    masks = np.unpackbits(det['masks'], axis=-1)[:, :, :Ww].astype(bool)
    zb = np.full((Hh, Ww), np.inf); lab = np.full((Hh, Ww), -1)
    for s, n in enumerate(names):
        T = np.linalg.inv(W0) @ Wd[n][0]; X = cov_pts(f'{lib(ep, n, public)}/{n}.glb', n) @ T[:3, :3].T + T[:3, 3]; uv = X @ K2.T
        u = np.round(uv[:, 0] / uv[:, 2]).astype(int); v = np.round(uv[:, 1] / uv[:, 2]).astype(int); z = X[:, 2]
        for du in (0, 1):
            for dv in (0, 1):
                uu, vv = u + du, v + dv; ok = (uu >= 0) & (uu < Ww) & (vv >= 0) & (vv < Hh) & (z > 0)
                uu, vv, zz = uu[ok], vv[ok], z[ok]; o = np.argsort(-zz); uu, vv, zz = uu[o], vv[o], zz[o]
                up = zz < zb[vv, uu]; zb[vv[up], uu[up]] = zz[up]; lab[vv[up], uu[up]] = s
    e = {}
    anchor = next((n for n in names if n not in NO_ANCHOR), None)
    for s, n in enumerate(names):
        c = int(det['chosen'][s]); pred = lab == s
        if c < 0:
            e[n] = None; continue
        m = masks[c]
        e[n] = dict(slot=s, rotation_anchor=(n == anchor), mask_px=int(m.sum()), pred_px=int(pred.sum()),
                    coverage=round(float((m & pred).sum() / max(1, pred.sum())), 3),
                    iou=round(float((m & pred).sum() / max(1, (m | pred).sum())), 3),
                    s8_gate_open=bool(n == anchor and (m & pred).sum() / max(1, pred.sum()) < 0.70))
    return e


# ------------------------------------------------------------------ E: S6 static hold (ep11 scripts/static_hold_test.py logic)
def screen_s6(ep, Wd, names, pl, public):
    nrm = np.asarray(pl[0], float); out = {}; st = {}
    for n in names:
        cm = np.asarray(mesh(f'{lib(ep, n, public)}/{n}.glb').vertices, float).mean(0)
        T = Wd[n]; c = T[:, :3, :3] @ cm + T[:, :3, 3]; dc = c - c[0]
        v = dc @ nrm; h = np.linalg.norm(dc - v[:, None] * nrm, axis=1)
        r = rotdeg(np.repeat(T[:1, :3, :3], len(T), 0), T[:, :3, :3])
        st[n] = dict(c=c, v=v, h=h)
        out[n] = dict(hmax_cm=round(float(h.max() * 100), 2), vmax_cm=round(float(np.abs(v).max() * 100), 2),
                      vup_max_cm=round(float(v.max() * 100), 2), vup_argmax=int(v.argmax()), rmax_deg=round(float(r.max()), 1))
    rules = {}
    for hm in (1.0, 1.5, 2.0, 3.0):
        rules[f'h{hm}'] = [n for n in names if out[n]['hmax_cm'] < hm and (n in SYMOBJ or out[n]['rmax_deg'] < 10.0)]
    # M1 signature (descriptive, not a frozen threshold): a frozen object whose track rises while another roster object is
    # over its footprint (horizontal centre distance < the frozen object's own horizontal radius at that frame)
    for n in rules['h2.0']:
        m = mesh(f'{lib(ep, n, public)}/{n}.glb'); V = np.asarray(m.vertices, float)
        k = out[n]['vup_argmax']; T = Wd[n][k]; Xw = V @ T[:3, :3].T + T[:3, 3]; d = Xw - st[n]['c'][k]
        rad = float(np.percentile(np.linalg.norm(d - (d @ nrm)[:, None] * nrm, axis=1), 95))
        over = {}
        for o in names:
            if o == n:
                continue
            dd = st[o]['c'] - st[n]['c']; hd = np.linalg.norm(dd - (dd @ nrm)[:, None] * nrm, axis=1)
            inside = hd < rad
            over[o] = dict(h_dist_at_peak_cm=round(float(hd[k] * 100), 1), frames_over_footprint=int(inside.sum()),
                           first_over=(int(np.argmax(inside)) if inside.any() else None))
        # rise while another object is over the footprint vs while none is
        anyover = np.zeros(len(st[n]['v']), bool)
        for o in names:
            if o != n:
                dd = st[o]['c'] - st[n]['c']; anyover |= np.linalg.norm(dd - (dd @ nrm)[:, None] * nrm, axis=1) < rad
        out[n]['frozen_check'] = dict(radius_cm=round(rad * 100, 1), others=over,
                                      vup_max_while_other_over_cm=(round(float(st[n]['v'][anyover].max() * 100), 2) if anyover.any() else None),
                                      vup_max_while_none_over_cm=(round(float(st[n]['v'][~anyover].max() * 100), 2) if (~anyover).any() else None),
                                      v_end_cm=round(float(st[n]['v'][-1] * 100), 2))
    return dict(stats=out, frozen=rules)


def main():
    public = '--public' in sys.argv
    eps = PUB if public else EV
    res = {}
    for ep in eps:
        I = inputs(ep, public)
        det = np.load(I['det'], allow_pickle=True); names = [str(x) for x in det['names']]
        P = np.load(I['poses']); Wd = world(P); W0 = P['world_T_cam'][0].astype(float)
        assert list(Wd) == names, (ep, list(Wd), names)
        kfs = json.load(open(I['vo']))['keyframes']; N = len(Wd[names[0]])
        pl = plane_of(det)
        tg = json.load(open(I['tg'])) if os.path.exists(I['tg']) else None
        e = dict(names=names, frames=N, run=I.get('run', 'refine/in (25 Oct)'), guard_on=tg is not None, track_guard=tg,
                 plane=None if pl is None else [np.round(pl[0], 4).tolist(), round(float(pl[1]), 4)])
        # C
        b = burst(kfs)
        hz = np.load(I['hands'], allow_pickle=True)
        J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(np.float64)
        Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
        assert len(J) == N, (ep, len(J), N)
        Pp = {n: lib_pts(ep, n, public) for n in names}
        e['vo'] = dict(keyframes=kfs, n_keyframes=len(kfs), burst_max_in_25=b[0], burst_start=b[1], burst_flag=bool(b[0] >= 4),
                       median_inliers=int(np.median(json.load(open(I['vo']))['inliers'][1:])))
        e['ruleK'] = ruleK(Wd, Pp, J, Jv, names, kfs)
        if public and os.path.exists(I.get('pw_po', '')):          # reproduction check on the Phase-1 P_o tracks
            V = np.load(I['pw_po']); Tpo = {n: V[n].astype(float) for n in names}
            e['ruleK_Po'] = {k: v for k, v in ruleK(Tpo, Pp, J, Jv, names, kfs).items() if k != 'log'}
        # A
        if public or ep in AREA_SET:
            e['area'] = screen_area(ep, det, public)
        # B
        frames = {}
        if not public and ep in REDET:
            frames = {names[0]: REDET[ep]}                       # all eval re-acquisitions are slot 0's cup (track_guard.json)
        e['s9'] = screen_s9(ep, Wd, names, frames, public)
        e['jumps_gt5cm_or_30deg'] = jumps(Wd)
        e['implausible_frames'] = implausible(ep, Wd, pl, public)
        # D
        e['coverage'] = screen_cov(ep, det, Wd, W0, names, public)
        # E
        e['s6'] = screen_s6(ep, Wd, names, pl, public)
        res[str(ep)] = e
        s6 = e['s6']
        print(f"ep{ep} {names} guard={'on' if tg else 'off'} | burst {b[0]}@{b[1]} kf{len(kfs)} | K max {e['ruleK']['corr_cm_max']} end {e['ruleK']['corr_cm_end']}"
              + (f" (P_o {e['ruleK_Po']['corr_cm_max']}/{e['ruleK_Po']['corr_cm_end']})" if 'ruleK_Po' in e else '')
              + f" | area {({n: (v['ratio'], v['margin']) for n, v in e.get('area', {}).items()})}"
              + f" | s9 {({n: (v['jump_cm'], v['jump_deg'], v['pre_motion_cm'], v['pre_motion_deg'], v['fires']) for n, v in e['s9'].items()})}"
              + f" | cov {({n: (v['coverage'], v['rotation_anchor']) for n, v in e['coverage'].items() if v})}"
              + f" | S6 {s6['frozen']['h2.0']} " + ' '.join(f"{n}:h{v['hmax_cm']}/v{v['vmax_cm']}/r{v['rmax_deg']}" for n, v in s6['stats'].items())
              + f" | jumps {e['jumps_gt5cm_or_30deg'][:4]} | impl {({n: v['n_implausible'] for n, v in (e['implausible_frames'] or {}).items()})}", flush=True)
    json.dump(res, open(sys.argv[1], 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
