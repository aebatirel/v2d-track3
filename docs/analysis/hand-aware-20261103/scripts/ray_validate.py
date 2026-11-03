"""DIAGNOSTIC (reads mocap via the scorer dump): does the GT-free depth residual r(t) (ray_residual.py) predict the
mocap ray error? The predicted ray error is -r(t) (a track too close to the camera sees the real surface farther:
r > 0, ray < 0). Variants: raw; minus the object's median r over its first BASE_N tracked frames (a per-episode
template-bias baseline, GT-free). Reports, in mocap-held frames with a valid residual, the correlation, the mean |ray|
before, the mean |ray - pred| after, and the same restricted to frames where |pred| > GATE.
Usage: ray_validate.py RESID.npz DUMP.npz POSES.npz HELD_JSON EP [GATE_CM]"""
import sys, json, numpy as np
R = np.load(sys.argv[1]); D = np.load(sys.argv[2]); W = np.load(sys.argv[3])['world_T_cam']; H = json.load(open(sys.argv[4]))
ep = int(sys.argv[5]); GATE = float(sys.argv[6]) if len(sys.argv) > 6 else 1.5; BASE_N = 10
names = [str(x) for x in R['names']]
raw, ach = D['raw'][..., :3].reshape(-1, 3), D['ach'][..., :3].reshape(-1, 3)
cs, cd = raw.mean(0), ach.mean(0); U, _, Vt = np.linalg.svd((raw - cs).T @ (ach - cd)); Rm = Vt.T @ U.T
if np.linalg.det(Rm) < 0: Vt[-1] *= -1; Rm = Vt.T @ U.T
c = (W[:, :3, 3] - cs) @ Rm.T + cd
res = {}
for s, n in enumerate(names):
    ref = D['ref'][:, s, :3]; d = D['ach'][:, s, :3] - ref; u = ref - c[:len(ref)]; u /= np.linalg.norm(u, axis=1, keepdims=True)
    ray = (d * u).sum(1) * 100; r = R[f'r_{n}'][:len(ray)] * 100
    h = np.zeros(len(ray), bool)
    for x, y in H[f'{ep}:{n}']['held_runs']: h[x:y] = True
    base = np.nanmedian(r[:BASE_N])
    for tag, pred in (('raw', -r), ('base', -(r - base))):
        for sel_name, sel in (('held', h), ('all', np.ones_like(h))):
            m = sel & np.isfinite(pred)
            if m.sum() < 5: continue
            g = m & (np.abs(pred) > GATE)
            res[f'{n}|{tag}|{sel_name}'] = dict(
                n=int(m.sum()), corr=round(float(np.corrcoef(pred[m], ray[m])[0, 1]), 3),
                abs_ray=round(float(np.abs(ray[m]).mean()), 2), abs_after=round(float(np.abs(ray[m] - pred[m]).mean()), 2),
                gated_n=int(g.sum()), gated_abs_ray=round(float(np.abs(ray[g]).mean()), 2) if g.any() else None,
                gated_abs_after=round(float(np.abs(ray[g] - pred[g]).mean()), 2) if g.any() else None)
    blk = 5; nn = len(ray) // blk * blk
    print(f'ep{ep} {n} base {base:+.2f} cm, valid {np.isfinite(r).sum()}/{len(r)}')
    print('  ray :', ' '.join('%+.1f' % x for x in ray[:nn].reshape(-1, blk).mean(1)))
    print('  -r  :', ' '.join('%+.1f' % x for x in np.nanmean((-r[:nn]).reshape(-1, blk), 1)))
for k, v in res.items(): print(k, v)
