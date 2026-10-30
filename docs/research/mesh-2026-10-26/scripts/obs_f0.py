"""Observed points of one object from the frame-0 perception dump alone (det_f0.npz), no GT.

Eval episodes have no stored depth cache, but perc2.py's detection dump keeps frame 0: FoundationStereo depth at half
resolution (float16), the rectified-left K (full resolution), every SAM2 proposal mask (bit-packed) and the proposal
chosen for each object. The chosen mask, eroded by ERODE pixels and with depth edges removed, is back-projected and
moved into the object frame with our track's cam_T_<obj>[0]. Output has the obs_points.py layout (pts, cam, frame),
so lathe_obs.py and obs_fidelity.py take it unchanged.
Usage: obs_f0.py --det det_f0.npz --poses poses.npz --obj NAME --out OUT.npz [--erode 3] [--edge_thr 0.02]
"""
import argparse, json
import numpy as np
import cv2


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--det', required=True); p.add_argument('--poses', required=True)
    p.add_argument('--obj', required=True); p.add_argument('--out', required=True)
    p.add_argument('--erode', type=int, default=3); p.add_argument('--edge_thr', type=float, default=0.02)
    a = p.parse_args()
    d = np.load(a.det, allow_pickle=False)
    names = [str(n) for n in d['names']]
    if a.obj not in names:
        raise SystemExit(f'{a.obj} not in {names}')
    ci = int(d['chosen'][names.index(a.obj)])
    if ci < 0:
        raise SystemExit(f'{a.obj}: no proposal chosen at frame 0')
    shp = tuple(int(x) for x in d['mask_shape'])
    mask = np.unpackbits(d['masks'][ci], axis=-1)[..., :shp[2]].astype(bool)
    D = d['depth'].astype(np.float32)                       # half of the rectified grid
    if mask.shape != D.shape:                                # masks may be at full resolution
        mask = cv2.resize(mask.astype(np.uint8), (D.shape[1], D.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    K = d['K'].astype(np.float64)                           # rectified-left K at full resolution (1600 x 1000)
    step = round(2 * K[0, 2] / D.shape[1]) if K[0, 2] > 0.75 * D.shape[1] else 1   # dump = depth[::2, ::2] -> 2
    m = cv2.erode(mask.astype(np.uint8), np.ones((2 * a.erode + 1, 2 * a.erode + 1), np.uint8)) > 0
    Dz = np.where(np.isfinite(D), D, 0).astype(np.float32); k5 = np.ones((5, 5), np.uint8)
    edge = (cv2.dilate(Dz, k5) - cv2.erode(Dz, k5)) > a.edge_thr
    vv, uu = np.nonzero(m & ~edge & (Dz > 0.1) & (Dz < 2.0))
    z = Dz[vv, uu].astype(np.float64)
    uf, vf = uu * step, vv * step                          # pixel (u, v) of depth[::2, ::2] is (2u, 2v) at full res
    Pc = np.stack([(uf - K[0, 2]) * z / K[0, 0], (vf - K[1, 2]) * z / K[1, 1], z], 1)
    T = np.load(a.poses)[f'cam_T_{a.obj}'][0].astype(np.float64); Ti = np.linalg.inv(T)
    Po = Pc @ Ti[:3, :3].T + Ti[:3, 3]
    cam = np.repeat(Ti[:3, 3][None], len(Po), 0)
    np.savez_compressed(a.out, pts=Po.astype(np.float32), cam=cam.astype(np.float32), frame=np.zeros(len(Po), np.int32))
    print(json.dumps(dict(obj=a.obj, proposal=ci, mask_px=int(mask.sum()), kept=int(len(Po)), step=int(step))))


if __name__ == '__main__':
    main()
