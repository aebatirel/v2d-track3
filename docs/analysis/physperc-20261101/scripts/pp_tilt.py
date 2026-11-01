"""pp_tilt (GT-free inference transform): fuse the tracker's frame-0 tilt with the physics prior (nearest stable resting
pose of our mesh on OUR table plane), as two sensors. Reads only our tracks, our meshes, our episode bundle (table
plane from frame-0 depth) and our hands. Never reads a parquet or mocap.
  For each selected object resting at frame 0 (gate below):
    g  = R0^T (-up)           tracker's down axis in the body frame
    n  = nearest stable-pose down axis of our mesh (thin-shell COM, trimesh quasi-static)
    gf = slerp(g, n, W)       fused down axis (W = 0 tracker only, 1 = physics only)
    C  = swing(g -> gf);  R'(t) = R(t) C^T for EVERY frame (constant body-frame bias, as refine.py S3 and the +0.016
         oracle), pivot about the mesh surface centroid c: p'(t) = p(t) + R(t) c - R'(t) c (no translation push).
  Gate (all must hold, else unchanged): |our hand to mesh| > HAND_MM at f0; lowest point of our mesh within
    [GAP_LO, GAP_HI] of our table at f0; match angle(g, n) <= MATCH_DEG (the tracker agrees the object sits on that
    facet; otherwise the prior is wrong, e.g. dust pan 13 deg, pitcher 60 deg in D1).
  SEL = anchor: the scorer's alignment object only (first slot whose name has no declared symmetry, else slot 0);
        all: every gated object.
Usage: python -I pp_tilt.py SCRATCH MESHDIR TRACKS_IN OUT_ROOT W SEL [EPS...]"""
import json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL

HAND_MM, GAP_LO, GAP_HI, MATCH_DEG = 50.0, -20.0, 10.0, 6.0
SYM = {'beige_cup', 'blue_cup', 'white_pot_lid'}   # names with a declared symmetry axis (kit); from the object list
S, MD, TIN, OUT, W, SEL = sys.argv[1:7]
W = float(W)
EPS = [int(x) for x in sys.argv[7:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
for p in (TIN, MD):
    assert 'parquet' not in p and '/t3' not in p, p


def slerp_dir(a, b, w):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    th = np.arccos(np.clip(a @ b, -1, 1))
    if th < 1e-9:
        return a
    return (np.sin((1 - w) * th) * a + np.sin(w * th) * b) / np.sin(th)


for e in EPS:
    E = json.load(open(f'{S}/data/b4/ep{e}/episode.json'))
    names = list(E['objects']) if isinstance(E['objects'], list) else None
    P = dict(np.load(f'{TIN}/ep{e}/poses_world_vo.npz'))
    names = [n if isinstance(n, str) else n['name'] for n in names] if names else list(P)
    assert sorted(names) == sorted(P), (names, list(P))
    up, d = PL.table_up(S, e, P, MD)
    J = PL.hand_joints(S, e)
    anchor = next((n for n in names if n not in SYM), names[0])
    rec = {'anchor': anchor, 'W': W, 'SEL': SEL, 'objects': {}}
    for n in names:
        r = rec['objects'][n] = {}
        if SEL == 'anchor' and n != anchor:
            r['skip'] = 'not anchor'; continue
        mp = f'{MD}/{n}.glb'
        X0 = P[n][0]
        hd = PL.hand_dist(J, 0, mp, X0) * 1000; gap = PL.lowest_gap(mp, X0, up, d) * 1000
        g = X0[:3, :3].T @ -up
        sp = PL.stable_poses(mp); k, match = PL.nearest_stable(sp, g)
        r.update(hand_mm=round(hd, 1), gap_mm=round(gap, 1), match_deg=round(match, 2))
        if not (hd > HAND_MM and GAP_LO <= gap <= GAP_HI and match <= MATCH_DEG):
            r['skip'] = 'gate'; continue
        gf = slerp_dir(g, sp['down'][k], W)
        C = PL.swing(g, gf)
        c = PL.shell_com(mp)
        Rn = np.einsum('tij,kj->tik', P[n][:, :3, :3], C)          # R(t) C^T
        Q = P[n].copy()
        Q[:, :3, :3] = Rn
        Q[:, :3, 3] = P[n][:, :3, 3] + np.einsum('tij,j->ti', P[n][:, :3, :3], c) - np.einsum('tij,j->ti', Rn, c)
        P[n] = Q
        r['tilt_deg'] = round(float(np.degrees(np.arccos(np.clip((np.trace(C) - 1) / 2, -1, 1)))), 3)
    os.makedirs(f'{OUT}/ep{e}', exist_ok=True)
    np.savez(f'{OUT}/ep{e}/poses_world_vo.npz', **P)
    json.dump(rec, open(f'{OUT}/ep{e}/pp_tilt.json', 'w'), indent=1)
    print(e, json.dumps(rec['objects']), flush=True)
