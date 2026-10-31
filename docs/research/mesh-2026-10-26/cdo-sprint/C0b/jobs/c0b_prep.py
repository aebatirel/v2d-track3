"""C0b GT-free helpers for the box job (PREREG cdo-sprint/C0b sections 3.2-3.4, 10). Reads only our own files: observed
points (obs_points.py npz), our tracks (poses.npz), our json outputs. No scan, mocap, parquet pose, *_align file or
library mesh. The gmg modules are imported through gmg/guard.py (its audit hook refuses ground-truth paths in-process).

  cubeguard OBS HALF                         share of kept points within 8 mm of a cube face (PREREG 3.4 guard: > 0.1 %
                                             = rebuild once at 0.45 m); prints JSON, exit 0 = pass, 3 = rebuild
  thick OBS OUT.json                         gmg thickness.two_sided_measurements (A.1 per object-episode row);
                                             writes OUT.json and OUT.npy (the finite measurements, m)
  t0 OUT.json ROW.json ...                   gmg thickness.aggregate over the rows (A.1) = t0_C0b
  sigma OBS POSES OBJ SLOT OUT.json          gmg bundle._sigma (A.2) on the extraction frames range(0, T, stride),
                                             T = track length (min over world_T_cam and the slot's cam_T_*)
  markers EP POSES SLOT OUT.json OBJ=OBS=SIGMA_JSON ...
                                             gmg markers.detect_episode (frozen A.6 settings; sha asserted) on a thin
                                             bundle wrapper that passes the arrays unchanged (own = 0 for all points)
  msep POSES OBJ A_OBJ.npz OTHER=A_OTHER.npz[,...] B_OBJ.npz OUT.npz OUT.json
                                             M_sep(own) (PREREG 10): keep extraction frame t iff fewer than half of B
                                             (20,000 random pass-A points of OBJ, seed 0) posed at t lie within 12 mm of
                                             any co-object's 20,000 pass-A points posed at t; filters B_OBJ by frame
  merge OUT.npz IN1.npz IN2.npz ...          concatenation (pts, cam, frame), as the public ep21+22 cup points
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))          # docs/research/mesh-2026-10-26
if MR not in sys.path:
    sys.path.insert(0, MR)

FROZEN_MARKER_SHA = '488ac3b638aa7e68c12843a5b761ed8882106bc78d8307d9e3059932502aa128'   # gmg markers.py at 8174998
CLAMP = (0.0015, 0.008)


def load_obs(path):
    z = np.load(path)
    n = len(z['pts'])
    return dict(pts=np.asarray(z['pts'], np.float32), cam=np.asarray(z['cam'], np.float32),
                frame=np.asarray(z['frame'], np.int32), own=np.zeros(n, np.uint8),
                args=json.loads(str(z['args'])) if 'args' in z.files else {})


def track_T(poses, slot):
    P = np.load(poses)
    return int(min(len(P['world_T_cam']), *[len(P[f'cam_T_{o}']) for o in slot]))


def cmd_cubeguard(obs, half):
    half = float(half)
    z = np.load(obs)
    P = np.asarray(z['pts'], np.float64)
    near = np.any(np.abs(P) > half - 0.008, axis=1) if len(P) else np.zeros(0, bool)
    share = float(near.mean()) if len(P) else 0.0
    r = dict(file=obs, half_m=half, kept=int(len(P)), near_face=int(near.sum()), share=round(share, 6),
             max_abs_mm=round(float(np.abs(P).max()) * 1e3, 1) if len(P) else None, rebuild=bool(share > 0.001))
    print(json.dumps(r))
    sys.exit(3 if r['rebuild'] else 0)


def cmd_thick(obs, out):
    from gmg import thickness as TH
    t = time.time()
    z = load_obs(obs)
    T, info = TH.two_sided_measurements(z)
    base = os.path.basename(obs)[:-4]
    ep, obj = base.split('_', 1)
    r = dict(obj=obj.replace('_sep', ''), ep=int(ep[2:]), file=obs, n=int(len(T)),
             median_m=float(np.median(T)) if len(T) else None, info=info, sec=round(time.time() - t, 1))
    np.save(out[:-5] + '.npy', T.astype(np.float32))
    json.dump(r, open(out, 'w'), indent=1)
    print(json.dumps(r))


def cmd_t0(out, rows):
    from gmg import thickness as TH
    R = [json.load(open(f)) for f in rows]
    res = TH.aggregate(R)
    res.update(per_episode=R, statistic='t0_C0b (PREREG C0b 3.3 step 3: A.1 on the C0b observed points of the public '
               'object-episodes)', n_rows=len(R))
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(dict(t0_m=res['t0_m'], fittable=res['fittable'], raw=res['t0_raw_m'], origin=res.get('origin'),
                          objects={k: (v['n'], round(v['median_m'] * 1e3, 3)) for k, v in res['objects'].items()})))
    if not res['fittable']:
        sys.exit(4)


def cmd_sigma(obs, poses, obj, slot, out):
    from gmg import bundle as BU
    t = time.time()
    slot = slot.split(',')
    z = load_obs(obs)
    stride = int(z['args'].get('stride', 2))
    T = track_T(poses, slot)
    s, info = BU._sigma(z, list(range(0, T, stride)))
    r = dict(obj=obj, file=obs, sigma_m=float(s), T=T, stride=stride, info=info, sec=round(time.time() - t, 1))
    json.dump(r, open(out, 'w'), indent=1)
    print(json.dumps(r))


class _Bundle:
    """Thin stand-in for the gmg bundle (PREREG C0b 3.2): objects, meta T/ep, obs(o) = the arrays unchanged."""
    def __init__(self, ep, objects, obs, T):
        self.objects = list(objects)
        self.meta = dict(T=int(T), ep=int(ep), split='public', tier='C0b', stride=2)
        self._obs = obs

    def obs(self, o):
        return self._obs[o]

    def sigma(self, o):
        raise RuntimeError('C0b passes sigma explicitly')


def cmd_markers(ep, poses, slot, out, specs):
    from gmg import markers as MK
    if MK.SETTINGS_SHA256 != FROZEN_MARKER_SHA:
        sys.exit(f'markers settings sha {MK.SETTINGS_SHA256} != frozen {FROZEN_MARKER_SHA}')
    t = time.time()
    slot = slot.split(',')
    objs, obs, sig = [], {}, {}
    for sp in specs:
        o, f, sj = sp.split('=')
        objs.append(o); obs[o] = load_obs(f); sig[o] = float(json.load(open(sj))['sigma_m'])
    T = track_T(poses, slot)
    res = MK.detect_episode(_Bundle(ep, objs, obs, T), sigma=sig, objects=objs)
    res.update(files={o: sp.split('=')[1] for o, sp in zip(objs, specs)}, T=T, sec=round(time.time() - t, 1))
    json.dump(res, open(out, 'w'), indent=1, default=float)
    print(json.dumps(dict(ep=ep, n_balls=res['n_balls'], r_consensus_mm=res['r_consensus_mm'], sec=res['sec'],
                          radii_mm={o: [b['r_mm'] for b in res['balls'][o]] for o in objs})))


def cmd_msep(poses, obj, a_obj, others, b_obj, out, outj, stride=2, other_r=0.012):
    from scipy.spatial import cKDTree
    P = np.load(poses)
    rng = lambda: np.random.default_rng(0)                                   # noqa: E731
    A = np.load(a_obj)['pts'].astype(np.float64)
    B = A[rng().choice(len(A), min(20000, len(A)), replace=False)]
    Q = []
    for sp in others.split(','):
        nm, f = sp.split('=')
        X = np.load(f)['pts'].astype(np.float64)
        Q.append((nm, X[rng().choice(len(X), min(20000, len(X)), replace=False)]))
    Tb = P[f'cam_T_{obj}'].astype(np.float64)
    T = int(min(len(Tb), *[len(P[f'cam_T_{nm}']) for nm, _ in Q]))
    Z = np.load(b_obj)
    fr = np.asarray(Z['frame'])
    cnt = np.bincount(fr, minlength=T)
    rows, keep = [], []
    for t in range(0, T, stride):
        Bc = B @ Tb[t][:3, :3].T + Tb[t][:3, 3]
        near = np.zeros(len(B), bool)
        for nm, X in Q:
            To = P[f'cam_T_{nm}'][t].astype(np.float64)
            Xc = X @ To[:3, :3].T + To[:3, 3]
            near |= cKDTree(Xc).query(Bc, distance_upper_bound=other_r)[0] <= other_r
        frac = float(near.mean())
        ok = frac < 0.5
        rows.append(dict(t=t, near_frac=round(frac, 4), keep=bool(ok), n_obs=int(cnt[t]) if t < len(cnt) else 0))
        if ok:
            keep.append(t)
    keep = np.array(keep, int)
    m = np.isin(fr, keep)
    d = {k: Z[k] for k in Z.files}
    d['pts'], d['cam'], d['frame'] = Z['pts'][m], Z['cam'][m], Z['frame'][m]
    d['mask'] = json.dumps(dict(rule='M_sep(own)', frames=keep.tolist(), src=b_obj))
    np.savez_compressed(out, **d)
    kept_with_pts = int(sum(1 for r in rows if r['keep'] and r['n_obs'] > 0))
    res = dict(rule='M_sep(own) PREREG C0b 10', obj=obj, others=[nm for nm, _ in Q], T=T, stride=stride,
               frames_evaluated=len(rows), frames_kept=int(len(keep)), frames_kept_with_points=kept_with_pts,
               pts_in=int(len(fr)), pts_out=int(m.sum()),
               qualifies=bool(len(keep) >= 10 and int(m.sum()) >= 20000), rows=rows, out=out)
    json.dump(res, open(outj, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'rows'}))


def cmd_merge(out, ins):
    Z = [np.load(f) for f in ins]
    np.savez_compressed(out, **{k: np.concatenate([z[k] for z in Z]) for k in ('pts', 'cam', 'frame')})
    print(out, sum(len(z['pts']) for z in Z), 'points from', len(Z), 'files')


def main():
    c = sys.argv[1]
    a = sys.argv[2:]
    if c == 'cubeguard':
        cmd_cubeguard(*a)
    elif c == 'thick':
        cmd_thick(*a)
    elif c == 't0':
        cmd_t0(a[0], a[1:])
    elif c == 'sigma':
        cmd_sigma(*a)
    elif c == 'markers':
        cmd_markers(a[0], a[1], a[2], a[3], a[4:])
    elif c == 'msep':
        cmd_msep(*a)
    elif c == 'merge':
        cmd_merge(a[0], a[1:])
    else:
        sys.exit(f'unknown command {c}')


if __name__ == '__main__':
    main()
