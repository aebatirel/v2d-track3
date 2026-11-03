"""DIAGNOSTIC / ORACLE (reads mocap): AUC ceiling of a ray-only translation correction. For each object, the camera-ray
component of the position error is removed (a) in held frames, (b) in held frames only where |ray| > GATE cm, then the
kit AUC is recomputed from the per-frame symmetric ADD approximated as sqrt(ADD^2 - ray^2) (position-dominated errors).
Usage: ray_ceiling.py DIAG_DIR CTRL_DIR HELD_JSON T3 EP..."""
import sys, json, numpy as np, pyarrow.parquet as pq
DG, C, HJ, T3 = sys.argv[1:5]; EPS = [int(x) for x in sys.argv[5:]]; H = json.load(open(HJ))
TH = np.arange(1, 10); WT = np.r_[0.5, np.ones(7), 0.5] / 8
auc = lambda a: 1 - float(((a[:, None] >= TH) @ WT).mean())
tot = {'ctrl': [], 'held': [], 'held_gate1.5': [], 'all': []}
for e in EPS:
    D = np.load(f'{DG}/dump_ep{e}.npz'); W = np.load(f'{C}/ep{e}/poses.npz')['world_T_cam']; pf = np.load(f'{DG}/Ct_ep{e}_pf.npz')
    names = list(pf['names']); A = pf['perception_adds_cm']
    raw, ach = D['raw'][..., :3].reshape(-1, 3), D['ach'][..., :3].reshape(-1, 3)
    cs, cd = raw.mean(0), ach.mean(0); U, _, Vt = np.linalg.svd((raw - cs).T @ (ach - cd)); R = Vt.T @ U.T
    if np.linalg.det(R) < 0: Vt[-1] *= -1; R = Vt.T @ U.T
    c = (W[:, :3, 3] - cs) @ R.T + cd
    row = {k: [] for k in tot}
    for s, n in enumerate(names):
        ref = D['ref'][:, s, :3]; d = D['ach'][:, s, :3] - ref; u = ref - c[:len(ref)]; u /= np.linalg.norm(u, axis=1, keepdims=True)
        ray = (d * u).sum(1) * 100; a = A[:, s]; fix = np.sqrt(np.maximum(a ** 2 - ray ** 2, 0))
        h = np.zeros(len(a), bool)
        for x, y in H[f'{e}:{n}']['held_runs']: h[x:y] = True
        row['ctrl'].append(auc(a)); row['all'].append(auc(fix))
        row['held'].append(auc(np.where(h, fix, a))); row['held_gate1.5'].append(auc(np.where(h & (np.abs(ray) > 1.5), fix, a)))
    for k in tot: tot[k].append(np.mean(row[k]))
    print(e, ' '.join(f'{k} {np.mean(v):.4f}' for k, v in row.items()))
print('MEAN', ' '.join(f'{k} {np.mean(v):.4f}' for k, v in tot.items()))
