"""Object crops from the colour camera for image-to-3D generators (inference only: our tracks + our library mesh).

For stereo frame k the colour frame is j = k + A_OFFSET (pipeline/hands_mp.py). Our mesh, posed by our track
cam_T_<obj>[k] (rectified-left camera), is projected into ego_cam_a; its silhouette seeds OpenCV GrabCut, which
refines the mask on the colour image. Other tracked objects in the episode are z-buffered so occluded parts drop out.
Frame choice (GT-free): among candidate frames, the largest visible silhouette that stays inside the image with a
margin. Output: RGBA crop (object on transparent background, square, padded), the mask, and a JSON of the choice.

Usage: crops.py --video epN_a.mp4 --poses poses.npz --calib calib.json --lib MESHDIR --obj NAME --out DIR
                [--frames 0,5,10,...] [--a_offset 1]
"""
import argparse, json, os, sys
import numpy as np
import cv2
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'pipeline'))


def geometry(calib_path):
    """Same chain as pipeline/hands_mp.py geometry(): rectified-left -> ego_cam_a."""
    C = json.load(open(calib_path)); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float); R_lr, T_lr = E[:3, :3].copy(), E[:3, 3].copy()
    R1, _, P1, P2, _, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                               (1280, 800), R_lr, T_lr.reshape(3, 1), alpha=0,
                                               newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float); R_ab, t_ab = Eab[:3, :3], Eab[:3, 3]
    T_a_rect = np.eye(4); T_a_rect[:3, :3] = R_ab.T @ R_lr @ R1.T; T_a_rect[:3, 3] = R_ab.T @ (T_lr - t_ab)
    return K_('ego_cam_a'), D_('ego_cam_a'), T_a_rect


def render_ids(meshes, poses_a, Ka, Da, W, H, scale=0.5):
    """Per-pixel id of the nearest mesh (0 = none) at SCALE x resolution, by splatting dense surface samples."""
    w, h = int(W * scale), int(H * scale)
    zb = np.full(h * w, np.inf); idb = np.zeros(h * w, np.int32)
    for i, (pts, T) in enumerate(zip(meshes, poses_a), 1):
        X = pts @ T[:3, :3].T + T[:3, 3]
        X = X[X[:, 2] > 0.05]
        uv, _ = cv2.projectPoints(X.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
        uv = uv.reshape(-1, 2) * scale
        iu, iv = np.round(uv[:, 0]).astype(int), np.round(uv[:, 1]).astype(int)
        ok = (iu >= 0) & (iu < w) & (iv >= 0) & (iv < h)
        lin = iv[ok] * w + iu[ok]; z = X[ok, 2]
        order = np.argsort(-z)                                     # far first, near overwrites
        lin, z = lin[order], z[order]
        closer = z < zb[lin]
        zb[lin[closer]] = z[closer]; idb[lin[closer]] = i
    idb = idb.reshape(h, w)
    full = cv2.resize(idb.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
    return full


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--video', required=True); p.add_argument('--poses', required=True)
    p.add_argument('--calib', required=True); p.add_argument('--lib', required=True)
    p.add_argument('--obj', required=True); p.add_argument('--out', required=True)
    p.add_argument('--frames', default='0,10,20,30,40,60,80,100')
    p.add_argument('--a_offset', type=int, default=1); p.add_argument('--pad', type=float, default=0.12)
    p.add_argument('--margin', type=int, default=20); p.add_argument('--n', type=int, default=1)
    p.add_argument('--hands', default=None, help='hands.npz (hands_mp.py): frames with a hand on the object score 0')
    p.add_argument('--rest_mm', type=float, default=1.5); p.add_argument('--need_rest', type=int, default=1)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    Ka, Da, T_a_rect = geometry(a.calib)
    P = np.load(a.poses)
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    order = [a.obj] + [n for n in names if n != a.obj]
    pts = []
    for n in order:
        m = trimesh.load(os.path.join(a.lib, n + '.glb'), force='mesh')
        pts.append(trimesh.sample.sample_surface_even(m, 60000, seed=0)[0])
    hands = np.load(a.hands) if a.hands else None
    T_o = P['cam_T_' + a.obj]; W_C = P['world_T_cam']
    pos = np.stack([(W_C[t] @ T_o[t])[:3, 3] for t in range(len(T_o))])
    sp = np.r_[0.0, np.linalg.norm(np.diff(pos, axis=0), axis=1)]
    from scipy.ndimage import median_filter
    speed = median_filter(sp, size=7, mode='nearest')
    cap = cv2.VideoCapture(a.video)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    nfa = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cands = []
    for k in [int(x) for x in a.frames.split(',')]:
        j = k + a.a_offset
        if k >= len(P['cam_T_' + a.obj]) or j >= nfa:
            continue
        poses_a = [T_a_rect @ P['cam_T_' + n][k] for n in order]
        ids = render_ids(pts, poses_a, Ka, Da, W, H)
        vis = ids == 1
        full = render_ids(pts[:1], poses_a[:1], Ka, Da, W, H) == 1
        if vis.sum() < 500:
            continue
        ys, xs = np.nonzero(full)
        inside = xs.min() > a.margin and ys.min() > a.margin and xs.max() < W - a.margin and ys.max() < H - a.margin
        # hand joints (MediaPipe on this colour frame) inside the object's box grown by 15 %: a hand on the object
        nhand = 0
        if hands is not None:
            gx, gy = 0.15 * (xs.max() - xs.min()), 0.15 * (ys.max() - ys.min())
            for side in ('left', 'right'):
                if k < len(hands[f'valid_{side}']) and hands[f'valid_{side}'][k]:
                    uv = hands[f'uv_a_{side}'][k]
                    nhand += int(((uv[:, 0] > xs.min() - gx) & (uv[:, 0] < xs.max() + gx) &
                                  (uv[:, 1] > ys.min() - gy) & (uv[:, 1] < ys.max() + gy)).sum())
        # at rest in the world (our track: median speed over +-3 frames < REST_MM per frame): a resting object usually
        # has no hand on it, which MediaPipe alone misses often
        rest = bool(speed[k] < a.rest_mm * 1e-3)
        cands.append(dict(k=k, j=j, vis=int(vis.sum()), full=int(full.sum()), occl=float(1 - vis.sum() / full.sum()),
                          inside=bool(inside), hand_joints=nhand, rest=rest, speed_mm=round(float(speed[k]) * 1e3, 2),
                          score=float(vis.sum() * (1 - (1 - vis.sum() / full.sum())) * inside * (nhand == 0)
                                      * (rest or not a.need_rest))))
    cands.sort(key=lambda c: -c['score'])
    chosen = cands[:a.n]
    for c in chosen:
        cap.set(cv2.CAP_PROP_POS_FRAMES, c['j']); ok, img = cap.read()
        poses_a = [T_a_rect @ P['cam_T_' + n][c['k']] for n in order]
        ids = render_ids(pts, poses_a, Ka, Da, W, H)
        sil = (ids == 1).astype(np.uint8)
        sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        # GrabCut: eroded silhouette = probable foreground core, dilated band = probable, other objects = background
        gc = np.full((H, W), cv2.GC_BGD, np.uint8)
        dil = cv2.dilate(sil, np.ones((41, 41), np.uint8)); ero = cv2.erode(sil, np.ones((15, 15), np.uint8))
        gc[dil > 0] = cv2.GC_PR_BGD; gc[sil > 0] = cv2.GC_PR_FGD; gc[ero > 0] = cv2.GC_FGD
        gc[(ids > 1) & (ero == 0)] = cv2.GC_BGD
        ys, xs = np.nonzero(dil); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        sub = np.ascontiguousarray(img[y0:y1 + 1, x0:x1 + 1]); gsub = np.ascontiguousarray(gc[y0:y1 + 1, x0:x1 + 1])
        bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(sub, gsub, None, bg, fg, 5, cv2.GC_INIT_WITH_MASK)
        msub = ((gsub == cv2.GC_FGD) | (gsub == cv2.GC_PR_FGD)).astype(np.uint8)
        nl, lab, st, _ = cv2.connectedComponentsWithStats(msub)
        if nl > 1:
            msub = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
        mask = np.zeros((H, W), np.uint8); mask[y0:y1 + 1, x0:x1 + 1] = msub
        ys, xs = np.nonzero(mask); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        side = int(max(x1 - x0, y1 - y0) * (1 + 2 * a.pad)); cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        rgba = np.zeros((side, side, 4), np.uint8)
        sx0, sy0 = cx - side // 2, cy - side // 2
        X0, Y0 = max(sx0, 0), max(sy0, 0); X1, Y1 = min(sx0 + side, W), min(sy0 + side, H)
        rgba[Y0 - sy0:Y1 - sy0, X0 - sx0:X1 - sx0, :3] = img[Y0:Y1, X0:X1, ::-1]
        rgba[Y0 - sy0:Y1 - sy0, X0 - sx0:X1 - sx0, 3] = mask[Y0:Y1, X0:X1] * 255
        tag = f'{a.obj}_k{c["k"]}'
        cv2.imwrite(os.path.join(a.out, tag + '.png'), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        ov = img.copy(); ov[sil > 0] = (0.5 * ov[sil > 0] + [0, 0, 127]).astype(np.uint8)
        cnt, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(ov, cnt, -1, (0, 255, 0), 3)
        cv2.imwrite(os.path.join(a.out, tag + '_overlay.jpg'), cv2.resize(ov, (W // 2, H // 2)))
        c.update(tag=tag, sil_px=int(sil.sum()), mask_px=int(mask.sum()), iou_sil_mask=float(
            (sil & mask).sum() / max((sil | mask).sum(), 1)))
    json.dump(dict(obj=a.obj, candidates=cands, chosen=chosen), open(os.path.join(a.out, a.obj + '_crops.json'), 'w'),
              indent=1)
    print(json.dumps(chosen))


if __name__ == '__main__':
    main()
