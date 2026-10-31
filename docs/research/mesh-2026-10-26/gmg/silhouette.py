"""Source (b) of the INTERLOCK stage: RGB silhouette votes (INTERLOCK.md 3.2, PREREG F-I1.2; build step BI1).

Stereo paints wood across a narrow slot; the RGB image of the same frame shows the background through it. Per object
and episode a two-class per-pixel colour model is fitted on that episode's own pixels; voxels of the target's grid
vote see-through in qualifying frames.

  geometry(calib) -> dict                cam_a chain (rectified-left -> ego_cam_a; pipeline/hands_mp.geometry, copied)
  read_frames(video, ks, offset)         cam_a frames for stereo frames ks (cam_a frame = k + offset)
  qualifying(b, obj, hands)              good frames, 2-D separated from every partner, hands <= 25 % of the mask and
                                         no hand pixel within 16 px of the target's projected mask
  classifier(b, obj, imgs, geo, ...)     positives / negatives, Lab + 5 x 5 texture features, two 3-component GMMs
                                         (cv2.ml.EM), held-out accuracy and the contrast gate inputs
  votes(b, obj, imgs, geo, model, ...)   NMV / NMF per 4 mm voxel; SIL = NMF >= 3 and NMF >= 0.5 NMV
  gate(...)                              accuracy >= 0.9 and false see-through <= 2 % on interior strongly observed voxels
  notches(sil, ev)                       N_b = SIL components inside the candidate occupancy (26-connected, >= 3 voxels)
  run(b, obj, video, calib, hands, ...)  all of the above -> dict(nmv, nmf, gate_ok, gate, notches, frames)

Deviation (stated in build/I.md): negatives are pixels 8-40 px outside the target's projected mask and outside every
other object's (dilated 8 px) and the hands' masks, instead of "depth more than 20 mm behind the target" (the depth
caches were deleted by build 1's batch to save disk; the colour model only needs background colour samples).
Inputs are read through the guard: video (role video), hands (role own or dev_hands), calib (role calib).
"""
from __future__ import annotations

import json

import numpy as np
from scipy import ndimage

from gmg import guard, interlock as IL

STATE_OBSERVED = 2
C = dict(
    hand_mask_max=(0.25, 'generic:F-I1.2 hands <= 25 % of the mask'),
    hand_px=(16, 'generic:F-I1.2 no hand pixel within 16 px'),
    pos_inset_px=(3, 'generic:F-I1.2 positives >= 3 px from the outline'),
    neg_band_px=((8, 40), 'generic:background band around the target (deviation, see header)'),
    gmm_k=(3, 'generic:F-I1.14 GMM 3 components'),
    tex_win=(5, 'generic:F-I1.14 5 x 5 texture'),
    holdout=(0.2, 'generic:F-I1.14 20 % pixel split'),
    acc_min=(0.9, 'generic:F-I1.2 held-out pixel accuracy >= 0.9'),
    false_free_max=(0.02, 'informed:F-I1.14 2 % false-free gate (22 Oct S2 design)'),
    nmf_min=(3, 'informed:F-I1.14 NMF >= 3 (22 Oct S2 design)'),
    nmf_share=(0.5, 'informed:F-I1.14 NMF >= 0.5 NMV (22 Oct S2 design)'),
    interior_hits=(10, 'generic:F-I1.2 strongly observed: hits >= 10'),
    max_pixels=(60000, 'generic:numerical cap of training pixels per class'),
    max_frames=(24, 'generic:numerical cap of qualifying frames used (evenly spaced)'),
)


def k_(name):
    v, o = C[name]
    if o.startswith(('generic', 'sensor')) and not isinstance(v, tuple):
        guard.constant(f'sil.{name}', v, o)
    return v


def geometry(calib_path):
    """pipeline/hands_mp.geometry (copied; no mediapipe import): T_a_rect maps rectified-left camera coordinates to
    ego_cam_a coordinates; Ka, Da project in cam_a."""
    import cv2
    Cj = guard.load_json(calib_path, 'calib')
    cam = Cj['cameras']
    sp = [p for p in Cj['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
    E = np.array(sp['left_to_right'], float)
    R_lr, T_lr = E[:3, :3].copy(), E[:3, 3].copy()
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, (1280, 800), R_lr, T_lr.reshape(3, 1), alpha=0,
                                                newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    Ka, Da = K_('ego_cam_a'), D_('ego_cam_a')
    Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float)
    R_ab, t_ab = Eab[:3, :3], Eab[:3, 3]
    T = np.eye(4)
    T[:3, :3] = R_ab.T @ R_lr @ R1.T
    T[:3, 3] = R_ab.T @ (T_lr - t_ab)
    return dict(Ka=Ka, Da=Da, T_a_rect=T, size=tuple(cam['ego_cam_a']['resolution']))


def project_a(geo, Xrect):
    """cam_a pixels (n,2) and cam_a depth (n,) of rectified-left camera points."""
    import cv2
    Xa = Xrect @ geo['T_a_rect'][:3, :3].T + geo['T_a_rect'][:3, 3]
    uv = np.full((len(Xa), 2), np.nan)
    ok = Xa[:, 2] > 0.05
    if ok.any():
        p, _ = cv2.projectPoints(Xa[ok].reshape(-1, 1, 3), np.zeros(3), np.zeros(3), geo['Ka'], geo['Da'])
        uv[ok] = p.reshape(-1, 2)
    return uv, Xa[:, 2]


def read_frames(video, ks, offset=1):
    import cv2
    rp = guard.open_input(video, 'video')
    want = {int(k) + int(offset): int(k) for k in ks}
    cap = cv2.VideoCapture(rp)
    out, j = {}, 0
    last = max(want) if want else -1
    while j <= last:
        ok, fr = cap.read()
        if not ok:
            break
        if j in want:
            out[want[j]] = fr
        j += 1
    cap.release()
    return out


def _mask(uv, size, r):
    import cv2
    W, H = size
    m = np.zeros((H, W), np.uint8)
    ok = np.isfinite(uv).all(1)
    u, v = uv[ok, 0].astype(int), uv[ok, 1].astype(int)
    k = (u >= 0) & (u < W) & (v >= 0) & (v < H)
    m[v[k], u[k]] = 1
    if r > 0:
        m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    return m.astype(bool)


def _obj_points(b, obj, which='observed'):
    """Dense object-frame points of an object's evidence for projection: OBSERVED voxels as 1 mm lattices."""
    ob = b.obs(obj)
    g = IL.Grid(ob['lo'], ob['vox'], np.asarray(ob['state']).shape)
    st = np.asarray(ob['state']).ravel()
    lin = np.nonzero(st == STATE_OBSERVED)[0]
    Cc = g.centres(lin)
    t = (-1.5, -0.5, 0.5, 1.5)
    off = np.array([[a, bb, c] for a in t for bb in t for c in t]) * (g.vox / 4)
    return (Cc[:, None, :] + off[None]).reshape(-1, 3)


def _cam(b, obj, f, X):
    T = b.poses[f'cam_T_{obj}'][f].astype(np.float64)
    return X @ T[:3, :3].T + T[:3, 3]


def hand_pixels(hands, f, size):
    """Hand mask in cam_a (convex hull of the 21 joints of each valid hand, dilated 12 px); None if no hands file."""
    import cv2
    if hands is None:
        return None
    W, H = size
    m = np.zeros((H, W), np.uint8)
    for side in ('left', 'right'):
        if f < len(hands[f'valid_{side}']) and hands[f'valid_{side}'][f]:
            uv = np.asarray(hands[f'uv_a_{side}'][f], np.float64)
            uv = uv[np.isfinite(uv).all(1)]
            if len(uv) >= 3:
                hull = cv2.convexHull(uv.astype(np.int32))
                cv2.fillConvexPoly(m, hull, 1)
    m = cv2.dilate(m, np.ones((25, 25), np.uint8))
    return m.astype(bool)


def qualifying(b, obj, geo, hands=None):
    """Good frames of OBJ, 2-D separated from every partner (SPEC section 4 census), hands <= 25 % of the projected
    mask and no hand pixel within 16 px of it. Returns (frames, info)."""
    from gmg import contact as CT
    good = set(b.good_frames(obj))
    parts = b.partners(obj)
    sep = set(CT.separated_for(b.meta['contact'], obj, parts)) if parts else set(b.frames())
    fr = sorted(good & sep)
    X = _obj_points(b, obj)[::4]
    out, rej = [], dict(hand_cover=0, hand_near=0)
    for f in fr:
        if hands is None:
            out.append(f); continue
        uv, _ = project_a(geo, _cam(b, obj, f, X))
        m = _mask(uv, geo['size'], 3)
        hm = hand_pixels(hands, f, geo['size'])
        if hm is None or not m.any():
            out.append(f); continue
        if (hm & m).sum() > k_('hand_mask_max') * m.sum():
            rej['hand_cover'] += 1; continue
        near = ndimage.binary_dilation(m, iterations=k_('hand_px'))
        if (hm & near).any():
            rej['hand_near'] += 1; continue
        out.append(f)
    return out, dict(good_sep=len(fr), kept=len(out), rejected=rej, hands=hands is not None)


def features(img):
    """Per-pixel features: Lab colour (3) and the 5 x 5 local standard deviation of L (1)."""
    import cv2
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[:, :, 0]
    w = k_('tex_win')
    m1 = cv2.blur(L, (w, w)); m2 = cv2.blur(L * L, (w, w))
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0))
    return np.dstack([lab, sd[:, :, None]])


class GMM2:
    """Two-class colour model: one cv2.ml.EM (k components, diagonal... full covariance) per class; posterior of
    class 'background' with the training class priors."""

    def __init__(self, k):
        self.k = k

    def fit(self, Xf, Xb):
        import cv2
        self.m = []
        for X in (Xf, Xb):
            em = cv2.ml.EM_create()
            em.setClustersNumber(self.k)
            em.setCovarianceMatrixType(cv2.ml.EM_COV_MAT_GENERIC)
            em.setTermCriteria((cv2.TERM_CRITERIA_COUNT + cv2.TERM_CRITERIA_EPS, 100, 1e-3))
            em.trainEM(X.astype(np.float64))
            self.m.append(em)
        self.prior = np.array([len(Xf), len(Xb)], np.float64) / (len(Xf) + len(Xb))
        return self

    def _loglik(self, em, X):
        w = em.getWeights().ravel(); mu = em.getMeans(); covs = em.getCovs()
        ll = []
        for j in range(len(w)):
            S = covs[j] + np.eye(X.shape[1]) * 1e-3
            Si = np.linalg.inv(S); _, ld = np.linalg.slogdet(S)
            D = X - mu[j]
            ll.append(np.log(max(w[j], 1e-12)) - 0.5 * (np.einsum('ij,jk,ik->i', D, Si, D) + ld +
                                                        X.shape[1] * np.log(2 * np.pi)))
        ll = np.stack(ll, 1)
        mx = ll.max(1, keepdims=True)
        return (mx + np.log(np.exp(ll - mx).sum(1, keepdims=True))).ravel()

    def p_bg(self, X):
        X = np.asarray(X, np.float64)
        lf = self._loglik(self.m[0], X) + np.log(self.prior[0])
        lb = self._loglik(self.m[1], X) + np.log(self.prior[1])
        mx = np.maximum(lf, lb)
        return np.exp(lb - mx) / (np.exp(lf - mx) + np.exp(lb - mx))


def _proj_masks(b, obj, f, geo, Xo, others, hands):
    uv, _ = project_a(geo, _cam(b, obj, f, Xo))
    m = _mask(uv, geo['size'], 2)
    import cv2
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
    om = np.zeros_like(m)
    for p, Xp in others.items():
        uvp, _ = project_a(geo, _cam(b, p, f, Xp))
        om |= _mask(uvp, geo['size'], 8)
    hm = hand_pixels(hands, f, geo['size'])
    if hm is not None:
        om |= hm
    return m, om


def classifier(b, obj, imgs, geo, hands=None, seed=0):
    """Positives = pixels of the projected OBSERVED target >= 3 px inside its outline; negatives = background band
    (header). Returns (model, info with held-out accuracy)."""
    rng = np.random.default_rng(seed)
    Xo = _obj_points(b, obj)[::2]
    others = {p: _obj_points(b, p)[::4] for p in b.partners(obj)}
    pos, neg = [], []
    lo, hi = C['neg_band_px'][0]
    for f, img in imgs.items():
        m, om = _proj_masks(b, obj, f, geo, Xo, others, hands)
        if m.sum() < 50:
            continue
        F = features(img)
        inner = ndimage.binary_erosion(m, iterations=k_('pos_inset_px'))
        band = ndimage.binary_dilation(m, iterations=hi) & ~ndimage.binary_dilation(m, iterations=lo) & ~om
        pos.append(F[inner]); neg.append(F[band])
    if not pos or not neg:
        return None, dict(reason='no training pixels')
    P, N = np.concatenate(pos), np.concatenate(neg)
    cap = k_('max_pixels')
    P = P[rng.choice(len(P), min(cap, len(P)), replace=False)]
    N = N[rng.choice(len(N), min(cap, len(N)), replace=False)]
    ho = k_('holdout')
    ip, ineg = rng.random(len(P)) < ho, rng.random(len(N)) < ho
    model = GMM2(k_('gmm_k')).fit(P[~ip], N[~ineg])
    acc_p = float((model.p_bg(P[ip]) <= 0.5).mean()); acc_n = float((model.p_bg(N[ineg]) > 0.5).mean())
    acc = float(((model.p_bg(P[ip]) <= 0.5).sum() + (model.p_bg(N[ineg]) > 0.5).sum()) / max(ip.sum() + ineg.sum(), 1))
    return model, dict(pos=int(len(P)), neg=int(len(N)), heldout_acc=round(acc, 4), heldout_acc_pos=round(acc_p, 4),
                       heldout_acc_neg=round(acc_n, 4), frames=len(imgs))


def votes(b, obj, imgs, geo, model, ev, hands=None):
    """NMV / NMF per voxel of ev's 4 mm grid (only voxels inside the candidate occupancy are voted): a voxel counts in a
    frame if its centre projects inside the image, outside every other object's and the hands' masks; NMF if the
    pixel's background probability exceeds 0.5."""
    g = ev.grid
    lin = np.nonzero(ev.occ)[0]
    Cc = g.centres(lin)
    nmv = np.zeros(g.size, np.int32); nmf = np.zeros(g.size, np.int32)
    others = {p: _obj_points(b, p)[::4] for p in b.partners(obj)}
    Xo = _obj_points(b, obj)[::2]
    W, H = geo['size']
    for f, img in imgs.items():
        uv, za = project_a(geo, _cam(b, obj, f, Cc))
        ok = np.isfinite(uv).all(1)
        u = np.round(uv[:, 0]).astype(int); v = np.round(uv[:, 1]).astype(int)
        ok &= (u >= 0) & (u < W) & (v >= 0) & (v < H)
        _, om = _proj_masks(b, obj, f, geo, Xo, others, hands)
        ok[ok] &= ~om[v[ok], u[ok]]
        if not ok.any():
            continue
        F = features(img)[v[ok], u[ok]]
        pb = model.p_bg(F.reshape(-1, 4))
        nmv[lin[ok]] += 1
        nmf[lin[ok][pb > 0.5]] += 1
    return nmv, nmf


def sil_mask(nmv, nmf):
    return (nmf >= k_('nmf_min')) & (nmf >= k_('nmf_share') * nmv)


def gate(info, nmv, nmf, ev):
    """F-I1.2 contrast gate: held-out accuracy >= 0.9 and false see-through share <= 2 % on strongly OBSERVED interior
    voxels (hits >= 10; interior = at least 2 voxels from the boundary of the OBSERVED set in the 2-D projection along
    the object's thinnest axis, i.e. away from the object's outline as seen face-on)."""
    g = ev.grid
    obs = (ev.state == STATE_OBSERVED) & (ev.hits >= k_('interior_hits')) & ev.occ
    O = obs.reshape(g.shape)
    # interior in the face-on projection: collapse along the thinnest grid-aligned PCA axis of the observed voxels
    Cc = g.centres(np.nonzero(obs)[0])
    if len(Cc) < 10:
        return False, dict(reason='too few strongly observed voxels')
    ax = IL.axes_of(Cc)[1][2]
    k = int(np.argmax(np.abs(ax)))
    proj = O.any(axis=k)
    inner2 = ndimage.binary_erosion(proj, iterations=2)
    idx = np.indices(g.shape)
    other = [a for a in range(3) if a != k]
    keep = inner2[idx[other[0]], idx[other[1]]] & O
    lin = np.nonzero(keep.ravel())[0]
    testable = nmv[lin] >= 3
    ff = float(sil_mask(nmv, nmf)[lin][testable].mean()) if testable.any() else float('nan')
    acc = info.get('heldout_acc') if info else None
    ok = acc is not None and acc >= k_('acc_min') and np.isfinite(ff) and ff <= k_('false_free_max')
    return bool(ok), dict(heldout_acc=acc, false_free=None if not np.isfinite(ff) else round(ff, 4),
                          interior_voxels=int(len(lin)), interior_testable=int(testable.sum()))


def notches(nmv, nmf, ev, min_vox=3):
    S = sil_mask(nmv, nmf) & ev.occ
    lab, n = ndimage.label(S.reshape(ev.grid.shape), structure=np.ones((3, 3, 3)))
    lab = lab.ravel()
    out = []
    for i in range(1, n + 1):
        l = np.nonzero(lab == i)[0]
        if len(l) >= min_vox:
            out.append(l)
    return out


def run(b, obj, ev, video, calib, hands=None, offset=1):
    """Source (b) for one object: qualifying frames, classifier, votes, gate, notches."""
    geo = geometry(calib)
    fr, qinfo = qualifying(b, obj, geo, hands)
    nmax = k_('max_frames')
    if len(fr) > nmax:
        fr = [fr[i] for i in np.linspace(0, len(fr) - 1, nmax).round().astype(int)]
    if not fr:
        return dict(gate_ok=False, gate=dict(reason='no qualifying frame'), frames=[], qualifying=qinfo)
    imgs = read_frames(video, fr, offset)
    model, cinfo = classifier(b, obj, imgs, geo, hands)
    if model is None:
        return dict(gate_ok=False, gate=cinfo, frames=fr, qualifying=qinfo)
    nmv, nmf = votes(b, obj, imgs, geo, model, ev, hands)
    ok, ginfo = gate(cinfo, nmv, nmf, ev)
    ginfo.update(cinfo)
    N = notches(nmv, nmf, ev) if ok else []
    return dict(nmv=nmv, nmf=nmf, gate_ok=ok, gate=ginfo, frames=fr, qualifying=qinfo,
                notches=N, sil_voxels=int((sil_mask(nmv, nmf) & ev.occ).sum()), _model=model, _geo=geo)
