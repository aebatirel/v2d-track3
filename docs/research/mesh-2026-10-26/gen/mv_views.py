"""Posed multi-view inputs for Pixal3D-MV from our own data only (batch-2 generative probe, 2026-10-29).

Inputs (all available for eval episodes too): the ego colour video, our tracks (poses.npz: cam_T_<obj> in the
rectified-left camera per stereo frame), our MediaPipe hands (hands.npz), our calibration and our library mesh (used,
as in crops.py, for the silhouette seed, the z-buffer against the episode's other objects and the object's centre and
extent). No scan, no mocap, no parquet pose.

Per stereo frame k the colour frame is j = k + a_offset (pipeline/hands_mp.py); T_a_obj = T_a_rect @ cam_T_obj[k]
(crops.geometry: rectified-left -> ego_cam_a). Frame choice (GT-free): candidates with the object fully inside the
image, no other tracked object in front of it (occlusion < OCCL), no MediaPipe hand joint in its box grown by 15 %
and low track speed; view 0 = the largest visible silhouette; then greedy farthest-point sampling of the viewing
direction on the object-frame sphere (>= MIN_DEG apart), up to N views.
Each view is a virtual recentred pinhole camera (rotation only about the colour camera centre, optical axis through
the object centre c, no roll w.r.t. the colour camera, principal point at the image centre, FOV such that our mesh
spans ~75 % of the frame as in Pixal3D's training renders), made with cv2.initUndistortRectifyMap; the mask is
GrabCut seeded by our posed mesh, as in crops.py.
World for Pixal3D (Z-up, NeRF/Blender c2w): p_world = s * A @ (p_obj - c) with A chosen so that view 0 IS the
canonical front view F (camera at (0,-d,0) looking at the origin, +Z up) and s so that our mesh fills the [-0.5,0.5]^3
generation cube up to FILL (abs max). Output: OUT/transforms.json, OUT/view<i>_k<k>.png (RGBA), OUT/probe_meta.json,
OUT/montage.jpg.
Usage: mv_views.py --video epN_a.mp4 --poses poses.npz --hands hands.npz --calib calib.json --lib MESHDIR --obj NAME
                   --out DIR [--n 6] [--size 1024] [--step 2]
"""
import argparse, json, math, os, sys
import numpy as np
import cv2
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from crops import geometry  # noqa: E402

R_F = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])        # rotation of Pixal3D's canonical front view F
GL = np.diag([1.0, -1.0, -1.0])                                  # OpenCV camera axes -> OpenGL/Blender camera axes


def zbuf_ids(pts_list, Ts, K, D, W, H, scale=0.5):
    """Nearest-object id per pixel (0 = none) by splatting surface samples; D=None for a pinhole camera."""
    w, h = int(W * scale), int(H * scale)
    zb = np.full(h * w, np.inf); idb = np.zeros(h * w, np.int32)
    Ks = K.copy(); Ks[:2] *= scale
    for i, (pts, T) in enumerate(zip(pts_list, Ts), 1):
        X = pts @ T[:3, :3].T + T[:3, 3]
        X = X[X[:, 2] > 0.05]
        if D is None:
            uv = (X[:, :2] / X[:, 2:3]) * [Ks[0, 0], Ks[1, 1]] + [Ks[0, 2], Ks[1, 2]]
        else:
            uv = cv2.projectPoints(X.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K, D)[0].reshape(-1, 2) * scale
        iu, iv = np.round(uv[:, 0]).astype(int), np.round(uv[:, 1]).astype(int)
        ok = (iu >= 0) & (iu < w) & (iv >= 0) & (iv < h)
        lin = iv[ok] * w + iu[ok]; z = X[ok, 2]
        o = np.argsort(-z); lin, z = lin[o], z[o]
        closer = z < zb[lin]
        zb[lin[closer]] = z[closer]; idb[lin[closer]] = i
    return cv2.resize(idb.reshape(h, w).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)


def grabcut_mask(img, ids):
    """crops.py's GrabCut: our posed silhouette seeds it; other objects are background."""
    H, W = ids.shape
    sil = (ids == 1).astype(np.uint8)
    sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    gc = np.full((H, W), cv2.GC_BGD, np.uint8)
    dil = cv2.dilate(sil, np.ones((41, 41), np.uint8)); ero = cv2.erode(sil, np.ones((15, 15), np.uint8))
    gc[dil > 0] = cv2.GC_PR_BGD; gc[sil > 0] = cv2.GC_PR_FGD; gc[ero > 0] = cv2.GC_FGD
    gc[(ids > 1) & (ero == 0)] = cv2.GC_BGD
    ys, xs = np.nonzero(dil); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    sub = np.ascontiguousarray(img[y0:y1 + 1, x0:x1 + 1]); gsub = np.ascontiguousarray(gc[y0:y1 + 1, x0:x1 + 1])
    bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(sub, gsub, None, bg, fg, 5, cv2.GC_INIT_WITH_MASK)
    msub = ((gsub == cv2.GC_FGD) | (gsub == cv2.GC_PR_FGD)).astype(np.uint8)
    nl, lab, st, _ = cv2.connectedComponentsWithStats(msub)
    if nl > 1:
        msub = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    mask = np.zeros((H, W), np.uint8); mask[y0:y1 + 1, x0:x1 + 1] = msub
    return mask, sil


def skin(img):
    """Skin-coloured pixels (YCrCb box rule); used only for objects whose own colour is not skin-like."""
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    return ((ycc[:, :, 1] >= 135) & (ycc[:, :, 1] <= 175) & (ycc[:, :, 2] >= 85) & (ycc[:, :, 2] <= 130)
            & (ycc[:, :, 0] > 60)).astype(np.uint8)


class Reader:
    """Sequential colour-frame reader (seeking an mp4 per frame is slow)."""
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path); self.i = -1; self.img = None

    def get(self, j):
        if j < self.i:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, j); self.i = j - 1
        while self.i < j:
            ok, self.img = self.cap.read(); self.i += 1
            if not ok:
                return None
        return self.img


def virtual_cam(T_a_obj, c, verts, size, span):
    """Rotation R_v (colour cam -> virtual cam), intrinsics K_v and FOV for a recentred pinhole view of the object."""
    Xc = T_a_obj[:3, :3] @ c + T_a_obj[:3, 3]
    z = Xc / np.linalg.norm(Xc)
    y = np.array([0.0, 1.0, 0.0]); y = y - (y @ z) * z; y /= np.linalg.norm(y)
    x = np.cross(y, z)
    R_v = np.stack([x, y, z])
    Xv = (verts @ T_a_obj[:3, :3].T + T_a_obj[:3, 3]) @ R_v.T
    h = np.abs(Xv[:, :2] / Xv[:, 2:3]).max()                      # half-extent in normalised image coordinates
    half = math.atan(h / span)
    f = size / (2 * math.tan(half))
    K_v = np.array([[f, 0, size / 2], [0, f, size / 2], [0, 0, 1.0]])
    return R_v, K_v, 2 * half, float(np.linalg.norm(Xc))


def main():
    ap = argparse.ArgumentParser()
    for k in ('video', 'poses', 'hands', 'calib', 'lib', 'obj', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--n', type=int, default=6); ap.add_argument('--size', type=int, default=1024)
    ap.add_argument('--step', type=int, default=2); ap.add_argument('--min_deg', type=float, default=20.0)
    ap.add_argument('--occl', type=float, default=0.02); ap.add_argument('--speed_mm', type=float, default=1.5)
    ap.add_argument('--span', type=float, default=0.75, help='object half-extent / image half-size (training ~0.75)')
    ap.add_argument('--fill', type=float, default=0.46, help='abs max of the mesh in the generation cube')
    ap.add_argument('--margin', type=int, default=20)
    ap.add_argument('--held_speed_mm', type=float, default=0.0,
                    help='also accept moving (held) frames up to this speed if skin covers < --skin_max of our '
                         'eroded silhouette (needs --skin 1); 0 = at-rest frames only')
    ap.add_argument('--skin', type=int, default=0, help='1: object colour is not skin-like; skin pixels are '
                                                        'removed from masks and gate held frames')
    ap.add_argument('--skin_max', type=float, default=0.01)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    Ka, Da, T_a_rect = geometry(a.calib)
    P = np.load(a.poses); Hd = np.load(a.hands)
    a_off = int(Hd['a_offset'])
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    order = [a.obj] + [n for n in names if n != a.obj]
    meshes = [trimesh.load(os.path.join(a.lib, n + '.glb'), force='mesh') for n in order]
    pts = [trimesh.sample.sample_surface_even(m, 60000, seed=0)[0] for m in meshes]
    verts = np.asarray(meshes[0].vertices, float)
    c = 0.5 * (verts.min(0) + verts.max(0))                       # our mesh's box centre, object frame
    T_o = P['cam_T_' + a.obj]; W_C = P['world_T_cam']
    pos = np.stack([(W_C[t] @ T_o[t])[:3, 3] for t in range(len(T_o))])
    from scipy.ndimage import median_filter
    speed = median_filter(np.r_[0.0, np.linalg.norm(np.diff(pos, axis=0), axis=1)], size=7, mode='nearest')
    cap = cv2.VideoCapture(a.video)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    nfa = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    rd = Reader(a.video)
    cands = []
    for k in range(0, len(T_o), a.step):
        if k + a_off >= nfa:
            break
        Ts = [T_a_rect @ P['cam_T_' + n][k] for n in order]
        ids = zbuf_ids(pts, Ts, Ka, Da, W, H)
        full = zbuf_ids(pts[:1], Ts[:1], Ka, Da, W, H) == 1
        vis = ids == 1
        if full.sum() < 2000:
            continue
        ys, xs = np.nonzero(full)
        inside = xs.min() > a.margin and ys.min() > a.margin and xs.max() < W - a.margin and ys.max() < H - a.margin
        occl = float(1 - vis.sum() / full.sum())
        gx, gy = 0.15 * (xs.max() - xs.min()), 0.15 * (ys.max() - ys.min())
        nhand = 0
        for side in ('left', 'right'):
            if k < len(Hd[f'valid_{side}']) and Hd[f'valid_{side}'][k]:
                uv = Hd[f'uv_a_{side}'][k]
                nhand += int(((uv[:, 0] > xs.min() - gx) & (uv[:, 0] < xs.max() + gx) &
                              (uv[:, 1] > ys.min() - gy) & (uv[:, 1] < ys.max() + gy)).sum())
        R, t = Ts[0][:3, :3], Ts[0][:3, 3]
        o = -R.T @ t                                               # colour camera centre, object frame
        u = (o - c) / np.linalg.norm(o - c)
        base = inside and occl < a.occl and nhand == 0
        rest = speed[k] < a.speed_mm * 1e-3
        skin_frac = None
        if a.skin and base and (rest or speed[k] < a.held_speed_mm * 1e-3):
            img = rd.get(k + a_off)
            core = cv2.erode(vis.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
            skin_frac = float(skin(img)[core].mean()) if img is not None and core.any() else 1.0
        held_ok = (not rest) and skin_frac is not None and skin_frac < a.skin_max
        ok = base and ((rest and (skin_frac is None or skin_frac < a.skin_max)) or held_ok)
        cands.append(dict(k=k, vis=int(vis.sum()), occl=round(occl, 4), inside=bool(inside), hand_joints=nhand,
                          speed_mm=round(float(speed[k]) * 1e3, 2), rest=bool(rest),
                          skin=None if skin_frac is None else round(skin_frac, 4), ok=bool(ok), u=u.round(5).tolist()))
    good = [cd for cd in cands if cd['ok']]
    if not good:
        raise SystemExit(f'no usable frame for {a.obj}')
    vmax = max(cd['vis'] for cd in good)
    good = [cd for cd in good if cd['vis'] >= 0.4 * vmax]
    chosen = [max(good, key=lambda cd: cd['vis'])]
    while len(chosen) < a.n:
        U = np.array([cd['u'] for cd in chosen])
        best, bd = None, -1
        for cd in good:
            dmin = math.degrees(math.acos(np.clip((U @ np.array(cd['u'])).max(), -1, 1)))
            if dmin > bd:
                best, bd = cd, dmin
        if bd < a.min_deg:
            break
        best['sep_deg'] = round(bd, 1)
        chosen.append(best)
    # world: view 0 is F; s fills the cube
    T0 = T_a_rect @ T_o[chosen[0]['k']]
    R_v0, _, _, _ = virtual_cam(T0, c, verts, a.size, a.span)
    A = R_F @ GL @ R_v0 @ T0[:3, :3]
    q = (verts - c) @ A.T
    s = a.fill / np.abs(q).max()
    frames, tiles = [], []
    for i, cd in enumerate(chosen):
        k = cd['k']
        Ts = [T_a_rect @ P['cam_T_' + n][k] for n in order]
        R_v, K_v, fov, dist = virtual_cam(Ts[0], c, verts, a.size, a.span)
        img = rd.get(k + a_off)
        if img is None:
            raise SystemExit(f'cannot read colour frame {k + a_off}')
        m1, m2 = cv2.initUndistortRectifyMap(Ka, Da, R_v, K_v, (a.size, a.size), cv2.CV_32FC1)
        vimg = cv2.remap(img, m1, m2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        Tv = [np.block([[R_v @ T[:3, :3], (R_v @ T[:3, 3])[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]) for T in Ts]
        ids = zbuf_ids(pts, Tv, K_v, None, a.size, a.size, scale=1.0)
        mask, sil = grabcut_mask(vimg, ids)
        if a.skin:                                                 # hand pixels never count as object
            sk = cv2.dilate(skin(vimg), np.ones((7, 7), np.uint8))
            cd['skin_removed_px'] = int((mask & sk).sum())
            mask = mask & (1 - sk)
        rgba = np.dstack([vimg[:, :, ::-1], mask * 255]).astype(np.uint8)
        fn = f'view{i:02d}_k{k}.png'
        cv2.imwrite(os.path.join(a.out, fn), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        # c2w (OpenCV axes) in the object frame, then into the Pixal3D world, then OpenGL axes
        Rc = Ts[0][:3, :3].T @ R_v.T
        oc = -Ts[0][:3, :3].T @ Ts[0][:3, 3]
        c2w = np.eye(4); c2w[:3, :3] = A @ Rc @ GL; c2w[:3, 3] = s * A @ (oc - c)
        cd.update(file=fn, fov_deg=round(math.degrees(fov), 3), dist_m=round(dist, 4),
                  mask_px=int(mask.sum()), sil_px=int(sil.sum()),
                  iou_sil_mask=round(float((sil & mask).sum() / max((sil | mask).sum(), 1)), 4))
        frames.append(dict(file_path=fn, name=f'k{k}', camera_angle_x=fov, transform_matrix=c2w.tolist()))
        ov = vimg.copy()
        cnt, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(ov, cnt, -1, (0, 255, 0), 3)
        cv2.putText(ov, f'{i} k{k}', (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
        tiles.append(cv2.resize(ov, (320, 320)))
    F0 = np.array(frames[0]['transform_matrix'])
    json.dump(dict(camera_angle_x=frames[0]['camera_angle_x'], mesh_scale=1.0, frames=frames),
              open(os.path.join(a.out, 'transforms.json'), 'w'), indent=1)
    json.dump(dict(obj=a.obj, video=os.path.basename(a.video), s=float(s), c=c.tolist(), A=A.tolist(),
                   front_check=dict(rot_err=float(np.abs(F0[:3, :3] - R_F).max()), pos=F0[:3, 3].round(5).tolist()),
                   chosen=chosen, n_candidates=len(cands), n_good=len(good), args=vars(a)),
              open(os.path.join(a.out, 'probe_meta.json'), 'w'), indent=1)
    cv2.imwrite(os.path.join(a.out, 'montage.jpg'), np.hstack(tiles))
    print(json.dumps(dict(obj=a.obj, n=len(chosen), good=len(good), cands=len(cands), s=round(float(s), 3),
                          views=[(cd['k'], cd.get('sep_deg'), cd['fov_deg'], cd['iou_sil_mask']) for cd in chosen])))


if __name__ == '__main__':
    main()
