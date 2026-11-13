"""GT-free physical check of the spoon's roll at rest: which marker-to-body placement agrees with the table?

At rest the spoon lies on the table in one of our mesh's statically stable rests (body 'down' = +x rotated about the
handle axis z by roll 0, -13.8 or +15.8 deg; docs/research/spoon-2026-10-25/spoon_anchor.out). For every rest frame
without a hand within 4 cm that has a >= 3-marker fix, this compares the body roll and height implied by
  track      our perc2 track (FoundationPose),
  layout_b   the 3 triangulated markers fitted with the layout placed by our tracks (census.py, the correction layer's),
  layout_a   the same markers fitted with our template's modelled markers (spoon/params.json, note 20 video layout),
with the stable rests, and the lowest mesh point with the table plane (our own mkref table_frame.npz).
Inputs: our tracks, detections, table frames, hands, our meshes. No ground truth.
Usage: python spoon_rest.py EPS(comma) OUT_JSON
"""
import json, os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(__file__))
import mlib, mklayout as L

RESTS = {'r0': 0.0, 'r-14': -13.8, 'r+16': 15.8}


def table(e):
    run = mlib.PERC_EVAL[e]
    for v in ('perc2mck', 'perc2mcks'):
        p = f'{mlib.S}/eg/dl/runs/{run}/refs/{v}/ep{e}/table_frame.npz'
        if os.path.exists(p):
            t = np.load(p); return t['plane_n'].astype(float), float(t['plane_d'])
    return None


def roll_and_height(Rw, tw, n, d, V):
    down = Rw.T @ (-n)
    roll = float(np.degrees(np.arctan2(down[1], down[0])))
    tilt = float(np.degrees(np.arcsin(np.clip(down[2], -1, 1))))
    h = float(((V @ Rw.T + tw) @ n + d).min())
    return roll, tilt, h


def main():
    eps, outp = [int(x) for x in sys.argv[1].split(',')], sys.argv[2]
    V = np.asarray(trimesh.load('/home/user/v2d-track3/meshes/library_v3/wooden_spoon.glb', force='mesh').vertices)
    Ma = np.array(json.load(open('/home/user/v2d-track3/spoon/params.json'))['markers_canonical_m'])
    rep = {}
    for e in eps:
        F = np.load(f'{mlib.S}/mk/scan/fix_eval{e}_wooden_spoon.npz'); Lb = F['layout']; labs = json.loads(str(F['labs']))
        J = json.load(open(f'{mlib.S}/mk/scan/eval{e}_wooden_spoon_g.json'))
        P = np.load(mlib.poses_path('eval', e)); T = P['cam_T_wooden_spoon'].astype(float); W = P['world_T_cam'].astype(float)
        tb = table(e)
        if tb is None:
            continue
        n, d = tb; rows = []
        hand = F['hand'] if len(F['hand']) else np.zeros(len(F['n']), bool)
        for t in range(len(F['n'])):
            if not (F['rest'][t] and not hand[t] and F['n'][t] >= 3):
                continue
            lab = {int(k): v for k, v in labs[t].items()}; ks = sorted(lab)
            X = np.array([J['dets'][t][lab[k]]['X'] for k in ks])
            r = {}
            Tw = W[t] @ T[t]; r['track'] = roll_and_height(Tw[:3, :3], Tw[:3, 3], n, d, V)
            for name, lay in (('layout_b', Lb), ('layout_a', Ma)):
                R, p = L.kabsch(lay[ks], X); Fw = W[t] @ np.r_[np.c_[R, p], [[0, 0, 0, 1]]]
                r[name] = roll_and_height(Fw[:3, :3], Fw[:3, 3], n, d, V)
            rows.append((t, r))
        if not rows:
            rep[str(e)] = dict(frames=0); continue
        out = dict(frames=len(rows), first=rows[0][0])
        for k in ('track', 'layout_b', 'layout_a'):
            roll = np.array([r[k][0] for _, r in rows]); tilt = np.array([r[k][1] for _, r in rows])
            h = np.array([r[k][2] for _, r in rows])
            near = {nm: float(np.median(np.abs(roll - v))) for nm, v in RESTS.items()}
            out[k] = dict(roll_med=round(float(np.median(roll)), 2), roll_sd=round(float(np.std(roll)), 2),
                          tilt_med=round(float(np.median(tilt)), 2), min_height_mm_med=round(float(np.median(h) * 1000), 1),
                          nearest_rest=min(near, key=near.get), dist_to_nearest_deg=round(min(near.values()), 2))
        rep[str(e)] = out
        print(e, json.dumps(out))
    json.dump(rep, open(outp, 'w'), indent=1)


if __name__ == '__main__':
    main()
