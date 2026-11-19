"""MetricTrail (ViPE) outputs -> perc2's conventions (2026-11-19, camera-arms test,
docs/analysis/camarms-20261119/PREREG.md). GT-free.

pose mode:  python vipe_cam.py pose ART_DIR NAME N OUT.npz [--perc2 poses.npz]
  ART_DIR/pose/NAME.npz holds ViPE's OpenCV camera-to-world poses ('data' [n,4,4], 'inds' or 'source_frame_ids').
  Writes OUT.npz: world_T_cam [N,4,4] re-based so frame 0 = identity (perc2: world = rectified-left camera at frame
  0), have [N] bool (frame had its own pose; missing frames are filled from the nearest earlier pose, then later),
  n_keyframes, runtime_s. With --perc2, logs the median rotation gap to perc2's own camera for the pose as written and
  for an OpenGL-style axis flip diag(1,-1,-1): an axis-convention sanity check. The flip is applied only when the
  as-written gap exceeds 2 deg and the flipped one is 5x smaller (logged as CONVENTION FLIP).
depth mode: python vipe_cam.py depth ART_DIR NAME N OUT.npy
  ART_DIR/depth/NAME.zip (one HALF 'Z' EXR per frame, metres) -> OUT.npy float32 [N,1000,1600] on perc2's rectified
  grid, the same 0.15-2.0 m validity clip as perc2's FoundationStereo depth (0 = invalid).
"""
import sys, os, json, zipfile, io
import numpy as np

def rot_deg(R):
    return np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))

def load_pose(art, name, N):
    z = np.load(f'{art}/pose/{name}.npz')
    data = np.asarray(z['data'], float)
    if data.ndim == 2 and data.shape[1] == 16: data = data.reshape(-1, 4, 4)
    if data.ndim == 2 and data.shape[1] == 12: data = np.concatenate([data.reshape(-1, 3, 4), np.tile([[[0, 0, 0, 1]]], (len(data), 1, 1))], 1)
    assert data.ndim == 3 and data.shape[1:] == (4, 4), f'unexpected pose array {data.shape}'
    ids = np.asarray(z['source_frame_ids'] if 'source_frame_ids' in z.files else z['inds'], int)
    assert len(ids) == len(data), (len(ids), len(data))
    kf = len(z['keyframe_ids']) if 'keyframe_ids' in z.files else -1
    rt = float(z['runtime']) if 'runtime' in z.files else -1.0
    P = np.full((N, 4, 4), np.nan); have = np.zeros(N, bool)
    for i, M in zip(ids, data):
        if 0 <= i < N and np.isfinite(M).all(): P[i] = M; have[i] = True
    assert have[0], 'no pose for frame 0'
    last = None
    for i in range(N):                                   # fill gaps: hold the last pose (then back-fill the start)
        if have[i]: last = P[i]
        elif last is not None: P[i] = last
    return P, have, kf, rt

def pose_mode(art, name, N, out, perc2=None):
    P, have, kf, rt = load_pose(art, name, N)
    W = np.linalg.inv(P[0])[None] @ P                     # world = camera at frame 0
    info = dict(frames=N, have=int(have.sum()), n_keyframes=kf, runtime_s=rt, flip=False)
    if perc2 and os.path.exists(perc2):
        WC = np.load(perc2)['world_T_cam'][:N]
        F = np.diag([1., -1., -1., 1.])
        Wf = F[None] @ W @ F[None]
        g0 = float(np.median([rot_deg(WC[i][:3, :3].T @ W[i][:3, :3]) for i in range(N)]))
        g1 = float(np.median([rot_deg(WC[i][:3, :3].T @ Wf[i][:3, :3]) for i in range(N)]))
        info.update(rot_gap_deg_as_written=g0, rot_gap_deg_flipped=g1)
        if g0 > 2.0 and g1 * 5 < g0:
            W = Wf; info['flip'] = True; print('CONVENTION FLIP applied', g0, g1)
        tr = float(np.median(np.linalg.norm(WC[:, :3, 3] - W[:, :3, 3], axis=1)) * 1000)
        info['trans_gap_mm_median_vs_perc2'] = tr
    np.savez(out, world_T_cam=W.astype(np.float64), have=have, n_keyframes=kf, runtime_s=rt)
    print(json.dumps(info))

def depth_mode(art, name, N, out):
    import OpenEXR, Imath, cv2
    zf = zipfile.ZipFile(f'{art}/depth/{name}.zip')
    D = np.zeros((N, 1000, 1600), np.float32); got = 0
    for fn in sorted(zf.namelist()):
        i = int(fn.split('.')[0])
        if not 0 <= i < N: continue
        f = OpenEXR.InputFile(io.BytesIO(zf.read(fn)))
        dw = f.header()['dataWindow']; w, h = dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1
        z = np.frombuffer(f.channel('Z', Imath.PixelType(Imath.PixelType.HALF)), np.float16).astype(np.float32).reshape(h, w)
        z[~np.isfinite(z)] = 0
        valid = (z > 0).astype(np.float32)
        zu = cv2.resize(z, (1600, 1000), interpolation=cv2.INTER_LINEAR)
        vu = cv2.resize(valid, (1600, 1000), interpolation=cv2.INTER_LINEAR)
        zu[vu < 0.999] = 0                                # no blending across invalid pixels
        zu[(zu < 0.15) | (zu > 2.0)] = 0                  # perc2's validity clip
        D[i] = zu; got += 1
    np.save(out, D)
    print(json.dumps(dict(frames=N, depth_frames=got, valid_frac=float((D > 0).mean()))))

if __name__ == '__main__':
    mode, art, name, N, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    if mode == 'pose':
        perc2 = sys.argv[sys.argv.index('--perc2') + 1] if '--perc2' in sys.argv else None
        pose_mode(art, name, N, out, perc2)
    else:
        depth_mode(art, name, N, out)
