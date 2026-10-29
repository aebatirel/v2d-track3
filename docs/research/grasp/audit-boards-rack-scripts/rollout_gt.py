"""DIAGNOSTIC WITH GROUND TRUTH (mocap; after inference). Per-object per-frame ADD of a rollout (pose = simulated,
reference = ours) vs mocap after one frame-0 rigid warp on slot 0 (kit style; mesh registration ignored), and the
per-frame AUC contribution clip((9 cm - ADD)/8 cm, 0, 1). Segment means over given windows."""
import sys, json, numpy as np, pyarrow.parquet as pq, trimesh
from pathlib import Path
from scipy.spatial.transform import Rotation as R
kit, gtp, lib = sys.argv[1], sys.argv[2], sys.argv[3]; windows = json.loads(sys.argv[4]); rolls = sys.argv[5:]
sys.path.insert(0, kit); from v2dlb.submission_parquet import read_trajectory
rows = pq.read_table(gtp).column('observation.objects').to_pylist(); names = [o['name'] for o in rows[0]]; T = len(rows)
GT = {n: np.array([[o['pose'] for o in r if o['name'] == n][0] for r in rows]) for n in names}
GT = {n: np.concatenate([v[:, :3], v[:, [4, 5, 6, 3]]], 1) for n, v in GT.items()}  # xyz + xyzw
PTS = {}
for n in names:
    m = trimesh.load(f'{lib}/{n}.glb', force='mesh'); v = m.vertices
    PTS[n] = v[np.random.default_rng(0).choice(len(v), min(500, len(v)), replace=False)]
def tf(p): return R.from_quat(p[3:7]), p[:3]
def add(a, b, n):
    ra, ta = tf(a); rb, tb = tf(b); return float(np.linalg.norm(ra.apply(PTS[n]) + ta - rb.apply(PTS[n]) - tb, axis=1).mean())
res = {}
for rp in rolls:
    tr = read_trajectory(Path(rp)); w = tr.world_valid
    out = {}
    for which in ('sim', 'ref'):
        arr = tr.pose_xyzw if which == 'sim' else tr.reference_xyzw
        S = {}
        for k, n in enumerate(names):
            sel = (tr.object_slot == k)
            fr = tr.frame_index[sel]; o = np.argsort(fr); S[n] = arr[sel][o]
        # warp from slot 0 at frame 0
        r0, t0 = tf(S[names[0]][0]); g0r, g0t = tf(GT[names[0]][0])
        Wr = g0r * r0.inv(); Wt = g0t - Wr.apply(t0)
        for n in names:
            P = S[n]; Pw = np.concatenate([Wr.apply(P[:, :3]) + Wt, (Wr * R.from_quat(P[:, 3:7])).as_quat()], 1)
            e = np.array([add(Pw[f], GT[n][f], n) for f in range(min(len(Pw), T))])
            sc = np.clip((0.09 - e) / 0.08, 0, 1)
            out[f'{which}:{n}'] = dict(add=e, score=sc)
    res[rp] = out
    line = Path(rp).parent.name
    for n in names:
        s, r = out[f'sim:{n}']['score'], out[f'ref:{n}']['score']
        seg = ' '.join(f'{k}:{s[a:b].mean():.2f}/{r[a:b].mean():.2f}' for k, (a, b) in windows[n].items())
        print(f'{line} {n[-7:]} sim {s.mean():.3f} (ref {r.mean():.3f}) | seg sim/ref {seg}')
np.save(sys.argv[0].replace('.py', '_last.npy'), {k: {kk: {a: b.tolist() for a, b in vv.items()} for kk, vv in v.items()} for k, v in res.items()}, allow_pickle=True)
