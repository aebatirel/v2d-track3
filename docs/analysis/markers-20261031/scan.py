"""Per-frame stereo marker detections around one object, guided by our own perc2 track (GT-free).

For every frame: project our library_v3 mesh with the track pose into the rectified left image, take its bounding box
plus a margin of 4 cm, and run detect.stereo inside it (depth window = the mesh's depth range +- 8 cm).
The b/c vertical offset dv0 (rectification residual) is measured first on this episode's own detections.
Inputs: eval/public ego_cam_b/c videos, the public camera calibration, perc2 poses.npz, meshes/library_v3.
No ground truth, no scan. Output: JSON with per-frame detection lists (camera frame, metres).
Usage: python scan.py SPLIT EP OBJ OUT_JSON
"""
import json, sys, time
import numpy as np, trimesh
sys.path.insert(0, __import__('os').path.dirname(__file__))
import mlib, detect

LIB = '/home/user/v2d-track3/meshes/library_v3'


def main():
    split, ep, obj, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    t0 = time.time()
    rig = mlib.Rig()
    rc, rb = mlib.rectified(rig, split, ep)
    P = np.load(mlib.poses_path(split, ep)); T = P[f'cam_T_{obj}'].astype(np.float64)
    N = min(len(rc), len(T))
    V = np.asarray(trimesh.load(f'{LIB}/{obj}.glb', force='mesh').vertices)
    V = V[np.random.default_rng(0).choice(len(V), min(800, len(V)), replace=False)]

    def frame(t, dv0, tol):
        X = V @ T[t][:3, :3].T + T[t][:3, 3]
        if np.any(X[:, 2] < 0.1):
            return []
        uL, _ = rig.proj(X)
        zc = float(np.median(X[:, 2])); mpx = rig.FR * 0.04 / zc
        rect = (int(max(0, uL[:, 0].min() - mpx)), int(max(0, uL[:, 1].min() - mpx)),
                int(min(1599, uL[:, 0].max() + mpx)), int(min(999, uL[:, 1].max() + mpx)))
        if rect[2] - rect[0] < 10 or rect[3] - rect[1] < 10:
            return []
        area = (rect[2] - rect[0]) * (rect[3] - rect[1]); k = int(np.clip(area / 4000, 30, 80))
        return detect.stereo(rig, rc[t], rb[t], rect, (X[:, 2].min() - 0.08, X[:, 2].max() + 0.08), dv0, tol, k=k)

    # pass 1: vertical offset of the rectified pair from this episode's own detections
    dvs = []
    for t in range(0, N, max(1, N // 40)):
        for d in frame(t, 0.0, 4.0):
            if d['sup'] > 0.6 and d['ncc'] > 0.8:
                dvs.append(d['uL'][1] - d['uR'][1])
    dv0 = float(np.median(dvs)) if len(dvs) >= 10 else 0.0
    dets = [frame(t, dv0, 1.5) for t in range(N)]
    res = dict(split=split, ep=ep, obj=obj, N=N, dv0=dv0, n_dv=len(dvs), dv_sd=float(np.std(dvs)) if dvs else None,
               seconds=round(time.time() - t0, 1), dets=dets)
    json.dump(res, open(out, 'w'))
    print(f'{split} ep{ep} {obj}: N {N} dv0 {dv0:.2f} (n {len(dvs)}) dets/frame {np.mean([len(d) for d in dets]):.2f} '
          f'{time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    main()
