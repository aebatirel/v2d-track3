"""GT-only test of mocap world-yaw constancy across episodes. If the world frame were re-rotated by w_e per episode,
every yaw and every inter-object bearing in episode e would shift by the SAME w_e. Compare per-quantity differences
between twin episodes, and fit a per-episode common shift. Research only."""
from c11 import *
import json
pub = {ep: load_episode(ep) for ep in PUBLIC}
def quants(e, f):
    p = e['pose']; nm = e['names']; q = {}
    for j, n in enumerate(nm):
        y, t = yaw_tilt(p[f, j, 3:], n)
        up = R_of(p[f, j, 3:]) @ np.array(UP[n], float)
        q[f'yaw:{n}'] = float(y) if up[2] > 0.9 else None  # only on the nominal rest face
    if len(nm) == 2:
        d = p[f, 1, :2] - p[f, 0, :2]
        q[f'bearing:{nm[0]}->{nm[1]}'] = float(np.degrees(np.arctan2(d[1], d[0]))) if np.linalg.norm(d) > 0.08 else None
    return q
by_task = {}
for ep in PUBLIC: by_task.setdefault(pub[ep]['task'], []).append(ep)
res = []
for task, eps in by_task.items():
    if len(eps) < 2: continue
    for f, tag in ((0, 'start'), (-1, 'end')):
        Q = {ep: quants(pub[ep], f) for ep in eps}
        keys = [k for k in Q[eps[0]] if all(Q[e].get(k) is not None for e in eps)]
        for k in keys:
            v = np.array([Q[e][k] for e in eps]); m = np.degrees(np.angle(np.exp(1j * np.radians(v)).mean()))
            dev = wrap(v - m)
            res.append(dict(task=task, when=tag, q=k, eps=eps, val=np.round(v, 1).tolist(), dev=np.round(dev, 1).tolist()))
            print(f"{task:18s} {tag:5s} {k:42s} vals {np.round(v,1).tolist()} dev-from-mean {np.round(dev,1).tolist()}")
# common-shift test on START quantities: per-episode shift estimate = mean dev of its quantities; residual after shift
print('\n== per-episode common shift (start quantities)')
dev_by_ep = {}
for r in res:
    if r['when'] != 'start': continue
    for e, d in zip(r['eps'], r['dev']): dev_by_ep.setdefault(e, []).append((r['q'], d))
summary = {}
for e, L in sorted(dev_by_ep.items()):
    d = np.array([x[1] for x in L]); summary[e] = dict(devs=L, mean=float(d.mean()), spread=float(d.std()))
    print(e, pub[e]['task'], [(q.split(':')[0][:4] + ':' + q.split(':')[1][:14], x) for q, x in L], f"mean {d.mean():.1f} sd {d.std():.1f}")
# rack across tasks (static, start)
print('\n== static rack yaw across 3 tasks')
ry = {ep: quants(pub[ep], 0).get('yaw:plastic_dish_rack') for ep in PUBLIC if 'plastic_dish_rack' in pub[ep]['names']}
print(ry)
json.dump(dict(res=res, ep_shift=summary, rack=ry), open('s12_worldyaw.json', 'w'), indent=1)
