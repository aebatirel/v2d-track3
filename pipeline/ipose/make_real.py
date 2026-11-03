"""R+M arm only: real training crops of the TRAIN episodes with mocap-derived labels (labels_rm.py output).
ROI = the control track's box x U(1.1, 1.5) with centre jitter (as synth). XYZ / amodal mask = render of the label pose;
visible mask = amodal & stereo depth within 1.5 cm of the rendered depth.
Usage: python make_real.py LABELS.npz OUT_DIR --eps 0,26,41,42,43 [--per_frame 2]
"""
import argparse, os, sys
import numpy as np, cv2, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

p = argparse.ArgumentParser()
p.add_argument('labels'); p.add_argument('out'); p.add_argument('--eps', default='0,26,41,42,43')
p.add_argument('--per_frame', type=int, default=2)
p.add_argument('--control', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../../docs/analysis/ipose-20261103/control'))
p.add_argument('--mesh', default=f'{os.path.dirname(os.path.abspath(__file__))}/../../meshes/ipose/white_pot.glb')
p.add_argument('--depth_fmt', default='/content/cache/depth/ep{e}/depths_fs0.5.npy')
a = p.parse_args()
assert not {2, 27, 44, 45} & {int(e) for e in a.eps.split(',')}
os.makedirs(a.out, exist_ok=True)
rng = np.random.default_rng(1)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
pts, nrm, alb, _ = C.load_points(a.mesh, 1_000_000 if dev == 'cuda' else 300_000)
S = C.Splat(pts, nrm, alb, dev); sub = pts[::max(1, len(pts) // 3000)]
_, K = C.rectification()
L = np.load(a.labels)
for e in a.eps.split(','):
    e = int(e); lab = L[f'ep{e}']; Ttr = np.load(f'{a.control}/ep{e}_poses.npz')['cam_T_white_pot']
    F = C.rect_left_frames(e); D = np.load(a.depth_fmt.format(e=e), mmap_mode='r')
    n = min(len(lab), len(Ttr), len(F), len(D)); buf = []
    for i in range(n):
        for _ in range(a.per_frame):
            cx, cy, side = C.roi_from_pose(K, Ttr[i], sub, rng.uniform(1.1, 1.5))
            cx += rng.normal(0, 0.05) * side; cy += rng.normal(0, 0.05) * side
            Kc = C.crop_K(K, cx, cy, side, 256)
            r = S.render(Kc, lab[i], 256, 256)
            dz = C.crop_image(np.ascontiguousarray(D[i]), cx, cy, side, 256, interp=cv2.INTER_NEAREST)
            vis = r['mask'] & (np.abs(dz - r['depth']) < 0.015)
            if r['mask'].sum() < 800 or vis.sum() < 0.2 * r['mask'].sum(): continue
            ds = lambda x: x[1::4, 1::4]
            buf.append(dict(img=C.crop_image(F[i], cx, cy, side, 256), xyz=ds(r['xyz']).astype(np.float16), vis=ds(vis),
                            full=ds(r['mask']), K=Kc, T=lab[i]))
    np.savez(f'{a.out}/real_ep{e}.npz', **{q: np.stack([b[q] for b in buf]) for q in buf[0]})
    print('ep', e, 'frames', n, 'crops', len(buf), 'vis frac', round(float(np.mean([b['vis'].sum() / max(b['full'].sum(), 1) for b in buf])), 3), flush=True)
    prev = [cv2.cvtColor(b['img'], cv2.COLOR_GRAY2BGR) for b in buf[::max(1, len(buf) // 8)][:8]]
    for im, b in zip(prev, buf[::max(1, len(buf) // 8)][:8]):
        im[cv2.resize(b['vis'].astype(np.uint8), (256, 256), interpolation=cv2.INTER_NEAREST) > 0, 2] = 255
    cv2.imwrite(f'{a.out}/preview_real_ep{e}.jpg', np.hstack(prev))
