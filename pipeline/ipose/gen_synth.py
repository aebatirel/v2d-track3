"""Synthetic training crops for the pot network (arm R; GT-free).

Usage: python gen_synth.py OUT_DIR N [--mesh M] [--train_eps 0,26,41,42,43] [--bg_eps 11,12,...] [--seed S]
         [--control DIR] [--device cuda] [--shard 1000]
Writes OUT_DIR/synth_XXX.npz shards: img (n,256,256) uint8, xyz (n,64,64,3) f16 (object coords, m), vis / full
(n,64,64) bool, K (n,3,3), T (n,4,4), plus OUT_DIR/preview.jpg. Poses come from the train episodes' CONTROL tracks
(GT-free), perturbed; backgrounds are rectified-left frames of public episodes without the pot.
"""
import argparse, os, sys, time, json
import numpy as np, cv2, torch
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

p = argparse.ArgumentParser()
p.add_argument('out'); p.add_argument('n', type=int)
p.add_argument('--mesh', default=None)
p.add_argument('--train_eps', default='0,26,41,42,43')
p.add_argument('--bg_eps', default='11,12,13,18,21,22,23,24,31,39,40')
p.add_argument('--bg_per_ep', type=int, default=40)
p.add_argument('--control', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../../docs/analysis/ipose-20261103/control'))
p.add_argument('--seed', type=int, default=0)
p.add_argument('--points', type=int, default=1_000_000)
p.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
p.add_argument('--shard', type=int, default=1000)
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
rng = np.random.default_rng(a.seed)
MESH = a.mesh or f'{os.path.dirname(os.path.abspath(__file__))}/../../meshes/ipose/white_pot.glb'
pts, nrm, alb, mesh = C.load_points(MESH, a.points, seed=a.seed)
S = C.Splat(pts, nrm, alb, a.device)
sub = pts[::max(1, len(pts) // 3000)]
cen = (pts.min(0) + pts.max(0)) / 2
_, K = C.rectification()

poses = np.concatenate([np.load(f'{a.control}/ep{e}_poses.npz')['cam_T_white_pot'] for e in a.train_eps.split(',')])
print('train-track poses', len(poses), flush=True)

bgs = []
for e in a.bg_eps.split(','):
    try:
        n = int(cv2.VideoCapture(f'{C.T3}/v/ep{e}_c.mp4').get(cv2.CAP_PROP_FRAME_COUNT))
        F = C.rect_left_frames(int(e), idx=np.linspace(0, n - 1, a.bg_per_ep).astype(int))
        bgs += list(F.values())
    except Exception as x:
        print('bg ep', e, 'failed', x)
print('backgrounds', len(bgs), flush=True)


def rand_pose():
    T = poses[rng.integers(len(poses))].copy()
    R, t = T[:3, :3], T[:3, 3]
    c = R @ cen + t
    u = rng.random()
    if u < 0.15:
        Rn = Rot.random(random_state=int(rng.integers(1 << 31))).as_matrix()
    else:
        ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
        ang = np.radians(rng.uniform(0, 45) if u < 0.85 else rng.uniform(0, 10))
        Rn = Rot.from_rotvec(ax * ang).as_matrix() @ R
    c = c + np.array([rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.08), rng.uniform(-0.15, 0.2)])
    c[2] = np.clip(c[2], 0.3, 1.1)
    return C.se3(Rn, c - Rn @ cen)


def rand_light():
    dirs = []
    for _ in range(rng.integers(1, 4)):
        d = rng.normal(size=3); d[2] = abs(d[2]) + 0.3
        dirs.append((d, rng.uniform(0.2, 0.8)))
    return dict(amb=rng.uniform(0.2, 0.7), dirs=dirs, spec=rng.uniform(0, 0.5), shin=rng.uniform(5, 60))


def bg_crop():
    g = bgs[rng.integers(len(bgs))]
    s = rng.uniform(200, 800)
    cx, cy = rng.uniform(s / 2, g.shape[1] - s / 2), rng.uniform(min(s / 2, 499), max(g.shape[0] - s / 2, 501))
    b = C.crop_image(g, cx, cy, s, 256, border=int(rng.integers(256))).astype(np.float32) / 255
    return b[:, ::-1].copy() if rng.random() < 0.5 else b


def occluder(full):
    """Hand-like occluder (palm + fingers) near the object, or a distractor patch. Returns (alpha, grey)."""
    occ = np.zeros((256, 256), np.float32)
    ys, xs = np.nonzero(full)
    if len(ys) == 0:
        return occ, occ
    k = rng.integers(len(ys)); y0, x0 = ys[k], xs[k]
    if rng.random() < 0.75:                                     # hand
        ang = rng.uniform(0, 180)
        pr = rng.uniform(20, 55)
        off = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))]) * pr * rng.uniform(0.5, 1.5)
        palm = (int(x0 + off[0]), int(y0 + off[1]))
        cv2.ellipse(occ, palm, (int(pr), int(pr * rng.uniform(0.6, 1.0))), ang, 0, 360, 1, -1)
        for _ in range(rng.integers(1, 5)):
            fa = ang + 180 + rng.uniform(-50, 50)
            L = rng.uniform(25, 70); w = rng.uniform(6, 13)
            d = np.array([np.cos(np.radians(fa)), np.sin(np.radians(fa))])
            cc = np.array(palm) + d * (pr * 0.6 + L / 2)
            cv2.ellipse(occ, (int(cc[0]), int(cc[1])), (int(L / 2), int(w)), fa, 0, 360, 1, -1)
        base = rng.uniform(0.3, 0.8)
        yy, xx = np.mgrid[:256, :256]
        sh = base * (1 + 0.25 * np.sin(xx / rng.uniform(15, 40) + rng.uniform(0, 6)) * np.cos(yy / rng.uniform(15, 40)))
        tex = sh + rng.normal(0, 0.02, (256, 256))
    else:                                                        # distractor patch from another background
        r = rng.uniform(20, 70)
        if rng.random() < 0.5:
            cv2.ellipse(occ, (int(x0), int(y0)), (int(r), int(r * rng.uniform(0.3, 1))), rng.uniform(0, 180), 0, 360, 1, -1)
        else:
            cv2.rectangle(occ, (int(x0 - r), int(y0 - r * 0.6)), (int(x0 + r), int(y0 + r * 0.6)), 1, -1)
        tex = bg_crop()
    occ = cv2.GaussianBlur(occ, (5, 5), 1.0)
    return occ, tex.astype(np.float32)


def sample():
    for _ in range(50):
        T = rand_pose()
        cx, cy, side = C.roi_from_pose(K, T, sub, scale=rng.uniform(1.1, 1.5))
        cx += rng.normal(0, 0.08) * side; cy += rng.normal(0, 0.08) * side
        if side < 40: continue
        Kc = C.crop_K(K, cx, cy, side, 256)
        r = S.render(Kc, T, 256, 256, rand_light())
        full = r['mask']
        if full.sum() < 800: continue
        g = np.clip(r["grey"] * rng.uniform(0.9, 1.8), 0, 1)
        al = cv2.GaussianBlur(full.astype(np.float32), (3, 3), 0.7)
        img = bg_crop() * (1 - al) + g * al
        vis = full.copy()
        if rng.random() < 0.6:
            oa, ot = occluder(full)
            img = img * (1 - oa) + ot * oa
            vis = full & (oa < 0.5)
        if vis.sum() < 0.25 * full.sum(): continue
        img = np.clip(img, 0, 1) ** rng.uniform(0.7, 1.4)
        if rng.random() < 0.3:
            img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.5, 1.5))
        if rng.random() < 0.2:
            L = int(rng.integers(3, 9)); kk = np.zeros((L, L), np.float32)
            kk[L // 2] = 1; kk = cv2.warpAffine(kk, cv2.getRotationMatrix2D((L / 2 - .5, L / 2 - .5), rng.uniform(0, 180), 1), (L, L))
            img = cv2.filter2D(img, -1, kk / max(kk.sum(), 1e-6))
        img = img + rng.normal(0, rng.uniform(0, 6) / 255, img.shape)
        img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        ds = lambda x: x[1::4, 1::4]                               # 64-grid cell centre = 4j + 1.5 ~ pixel 4j+1..2
        return dict(img=img, xyz=ds(r['xyz']).astype(np.float16), vis=ds(vis), full=ds(full), K=Kc, T=T)
    raise RuntimeError('no valid sample in 50 tries')


t0 = time.time(); buf = []; k = 0; prev = []
for i in range(a.n):
    s = sample(); buf.append(s)
    if len(prev) < 16: prev.append(s['img'])
    if len(buf) == a.shard or i == a.n - 1:
        np.savez(f'{a.out}/synth_{a.seed:02d}_{k:03d}.npz', **{q: np.stack([b[q] for b in buf]) for q in buf[0]})
        k += 1; buf = []
        print(f'{i + 1}/{a.n} {time.time() - t0:.0f}s', flush=True)
cv2.imwrite(f'{a.out}/preview_{a.seed:02d}.jpg', np.vstack([np.hstack(prev[r * 4:(r + 1) * 4]) for r in range(len(prev) // 4)]))
json.dump(dict(n=a.n, mesh=MESH, seed=a.seed, train_eps=a.train_eps, bg_eps=a.bg_eps, secs=time.time() - t0),
          open(f'{a.out}/synth_{a.seed:02d}.json', 'w'))
