"""Read the pre-registered ep13 gate (docs/research/grasp-ep13-20261101/PREREG.md) from the jitter checks.
Usage: python -I gate.py S/ep13 INPUTS_DIR OUT.json
Primary: jittered mean sim_vs_ref (copies 1..16 of jitter_check --k 17 --seed 0) per arm; d_b = grasp - anneal on the
perceived reference P, d_a = the same on the oracle reference O. PASS iff d_b >= +0.05 and neither d_a nor d_b < -0.05.
Report-only: paired per-copy differences (common noise draws) with a bootstrap 95 % interval, nominal copy 0, and the
cup's tracking per copy against the input reference (frames within 3 cm, first lasting loss, ADD at f110 and f189).
Our references only (no ground truth)."""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq

E, INP, OUT = sys.argv[1:4]


def quat_mat(q):
    x, y, z, w = (q[..., i] for i in range(4))
    return np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 2 * (x * y + z * w), 1 - 2 * (x * x + z * z),
                     2 * (y * z - x * w), 2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1).reshape(q.shape[:-1] + (3, 3))


res = {}; pts = np.random.default_rng(0).normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True)
for ref in ('P', 'O'):
    t = pq.read_table(glob.glob(f'{INP}/ep13_{ref}/processed/*/*/ref_in.parquet')[0])
    names = t.column('object_body_names')[0].as_py(); B = len(names); T = len(t.column('robot_left_wrist_position')[0].as_py())
    OP = np.array(t.column('object_body_position')[0].as_py()).reshape(T, B, 3)
    OQ = np.array(t.column('object_body_wxyz')[0].as_py()).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    cup = names.index('blue_cup')
    for arm in ('input', 'anneal', 'grasp'):
        d = f'{E}/{ref}_{arm}'
        if not os.path.exists(f'{d}/jitter.json'):
            continue
        j = json.load(open(f'{d}/jitter.json')); z = np.load(f'{d}/jitter.npz'); sc = z['scores']; q = z['q'].astype(np.float64)  # (T, K, B, 7)
        dd = np.einsum('tkij,vj->tkvi', quat_mat(q[:, :, cup, 3:7]) - quat_mat(OQ[:, None, cup]), pts) + (q[:, :, cup, :3] - OP[:, None, cup])[:, :, None]
        add = np.linalg.norm(dd, axis=-1).mean(-1)                      # (T, K) cup ADD (m) vs the input reference
        lost = []
        for k in range(add.shape[1]):
            far = add[:, k] > 0.03; f = next((i for i in range(T - 8) if far[i:i + 8].all()), None); lost.append(f)
        res[f'{ref}_{arm}'] = dict(nominal=j['nominal'], jit_mean=j['mean'], jit_sd=j['sd'], jit_min=j['min'], jit_max=j['max'],
                                   scores=[round(float(x), 4) for x in sc], cup_within_3cm=round(float((add[:, 1:] <= 0.03).mean()), 3),
                                   cup_first_lasting_loss=lost[1:], cup_add_cm_f110=np.round(100 * add[110, 1:], 1).tolist(),
                                   cup_add_cm_end=np.round(100 * add[-1, 1:], 1).tolist())
G = {}
for ref in ('P', 'O'):
    a, g = res.get(f'{ref}_anneal'), res.get(f'{ref}_grasp')
    if a and g:
        diff = np.array(g['scores'][1:]) - np.array(a['scores'][1:]); rng = np.random.default_rng(0)
        bs = [rng.choice(diff, len(diff)).mean() for _ in range(10000)]
        G[ref] = dict(delta=round(float(diff.mean()), 4), ci95=np.round(np.percentile(bs, [2.5, 97.5]), 4).tolist(),
                      wins=int((diff > 0).sum()), n=len(diff), delta_nominal=round(g['nominal'] - a['nominal'], 4))
ok = 'P' in G and 'O' in G
verdict = ('PASS' if ok and G['P']['delta'] >= 0.05 and min(G['P']['delta'], G['O']['delta']) >= -0.05 else 'FAIL') if ok else 'INCOMPLETE'
out = dict(arms=res, deltas=G, verdict=verdict, rule='d_b = jit_mean(grasp,P) - jit_mean(anneal,P) >= +0.05 and neither d_a nor d_b < -0.05')
json.dump(out, open(OUT, 'w'), indent=1)
for k, v in res.items():
    print(f"{k:10s} nominal {v['nominal']:.4f} jittered {v['jit_mean']:.4f} ± {v['jit_sd']:.4f} [{v['jit_min']:.4f}, {v['jit_max']:.4f}] "
          f"cup<=3cm {v['cup_within_3cm']:.3f} lost@ {v['cup_first_lasting_loss']}")
print('deltas', json.dumps(G)); print('VERDICT', verdict)
