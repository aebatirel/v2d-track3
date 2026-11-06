"""ORACLE mechanism diagnostic (public, after inference): does our stereo depth prefer our tracked pose or the oracle-
corrected pose? For the Po arm, per (episode, object), at frame 0 and at up to 12 non-moving frames of the depth grid:
  track  = the scan mesh at our track in scan frames, T(t) inv(X*_geom)   (our pose, true shape)
  oracle = the scan mesh at T(t) inv(X_trk)  = the mocap pose mapped into our world by the trk fit's one world transform
Both rendered with every other roster object (same condition) as occluders and our hands masked; residual = |depth -
rendered z| on the object's front-most pixels with valid depth. Reads the mocap-fitted trk offsets: oracle only.
Usage: python -I diag_depth_truth.py OUT_JSON"""
import json, sys, types
import numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import offsetfix as OF  # noqa: E402
REPO = '/home/user/v2d-track3'; LD = f'{REPO}/docs/research/work/leak-decomp-20261030'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
T3D = f'{S}/map/scoring/t3'
XG = json.load(open(f'{LD}/tierA/xstar_geom.json'))['objects']
TRK = json.load(open(f'{LD}/phase1/scores/xstar_trk_Po.json'))['episodes']
sys.path.insert(0, f'{REPO}/tools'); import xstar_fit as XF  # noqa: E402
SC = {}


def scan_model(n):
    if n not in SC:
        m = trimesh.load(XF.scan_path(T3D, n), force='mesh')
        k = int(np.clip(m.area / 1.5e-6, 30000, 400000))
        p, fi = trimesh.sample.sample_surface(m, k, seed=11); SC[n] = np.asarray(p, float)
    return SC[n]


def resid(items, j, dep, hm, K2):
    zb, lab = OF.render(items, K2, dep.shape)
    m = (lab == j) & ~hm & (dep > 0)
    if m.sum() < 50:
        return None
    r = dep[m] - zb[m]
    return dict(px=int(m.sum()), med_cm=round(float(np.median(r) * 100), 3), mad_cm=round(float(np.median(np.abs(r)) * 100), 3),
                within1=round(float((np.abs(r) < 0.01).mean()), 3))


out = {}
for ep in XF.PUBLIC:
    root = f'{S}/leak/t1/in_Po/ep{ep}'
    P = np.load(f'{root}/poses.npz'); W = P['world_T_cam'].astype(float)
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    Tw = {n: np.einsum('tij,tjk->tik', W, P[f'cam_T_{n}'].astype(float)) for n in names}
    H = np.load(f'{root}/hands_refined.npz', allow_pickle=True); K2 = np.diag([0.5, 0.5, 1.0]) @ H['KR']
    ds = OF.DepthSource(f'{S}/offset/depth/ep{ep}/depth_grid.npz', len(W), np.load(f'{root}/depth0.npy'))
    lab_s = np.load(f'{S}/offset/runs/Po/V1/ep{ep}/pose_opt_aux.npz')
    Xg = {n: np.asarray(XG[n]['X_scan_T_lib']) for n in names}
    Xt = {n: np.asarray(TRK[str(ep)]['objects'][n]['X_scan_T_lib']) for n in names}
    a = types.SimpleNamespace(s11_hand_cm=2.0)
    e = {}
    for j, n in enumerate(names):
        mv = lab_s[f'{n}_moving']
        fr = [0] + [t for t in ds.frames if t > 0 and not mv[t]][:12]
        rows = []
        for t in fr:
            dep = ds.get(t); Wi = np.linalg.inv(W[t])
            hm = OF.hand_mask(H, t, Wi, K2, dep.shape, 2.0)
            r = {}
            for cond, X in (('track', Xg), ('oracle', Xt)):
                items = [(k, Wi @ Tw[m][t] @ np.linalg.inv(X[m]), scan_model(m)) for k, m in enumerate(names)]
                r[cond] = resid(items, j, dep, hm, K2)
            if r['track'] and r['oracle']:
                rows.append(dict(t=int(t), **r))
        if rows:
            f0 = rows[0] if rows[0]['t'] == 0 else None
            e[n] = dict(frames=len(rows), f0=f0,
                        track_mad_cm=round(float(np.median([x['track']['mad_cm'] for x in rows])), 3),
                        oracle_mad_cm=round(float(np.median([x['oracle']['mad_cm'] for x in rows])), 3),
                        track_med_cm=round(float(np.median([x['track']['med_cm'] for x in rows])), 3),
                        oracle_med_cm=round(float(np.median([x['oracle']['med_cm'] for x in rows])), 3),
                        track_within1=round(float(np.median([x['track']['within1'] for x in rows])), 3),
                        oracle_within1=round(float(np.median([x['oracle']['within1'] for x in rows])), 3),
                        d0_offset=TRK[str(ep)]['objects'][n]['trk_vs_geom'])
            print(ep, n, {k: v for k, v in e[n].items() if k not in ('f0', 'd0_offset')}, flush=True)
    out[str(ep)] = e
json.dump(out, open(sys.argv[1], 'w'), indent=1)
