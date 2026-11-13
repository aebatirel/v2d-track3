"""Occluder masks for the masking re-track (perception sprint "mask10", option a; 31 Oct 2026) [H until its GPU test].
GT-free and renderer-agnostic: the caller renders every roster object at its latest tracked pose (perc2: nvdiffrast on
the GPU; the CPU mock: offsetfix.render splats) and passes the per-object depth maps. For object a, the occluder mask is
every pixel whose front-most rendered surface belongs to ANOTHER roster object (mode 'render'), or only those of them
whose measured depth agrees with that other object's render (mode 'depth', the default in the perc2 patch), dilated by
DIL pixels. perc2 then hides
those pixels from FoundationPose's track_one for object a: depth set to 0 (invalid) and the gray image set to the
frame's median intensity. Purpose: when a cup is lowered into another, the inner cup's surfaces (inside the outer cup's
opening and above its rim) are fitted as the outer cup's interior and drag its track up its axis (ep11 DIAG [H]; the CPU
proxy in docs/research/work/perception-sprint-20261031/mask10 reproduces the drag with depth alone [M, proxy]).
"""
import numpy as np


def front_labels(depth_maps):
    """depth_maps: (K, H, W) rendered depth per object (0 or non-finite = no surface). Returns (H, W) index of the
    front-most object, -1 where no object is rendered."""
    D = np.asarray(depth_maps, np.float32)
    D = np.where(np.isfinite(D) & (D > 0), D, np.inf)
    lab = np.argmin(D, axis=0).astype(np.int32)
    lab[~np.isfinite(D.min(axis=0))] = -1
    return lab


def occluder_masks(depth_maps, dil_px=3, measured=None, tol=0.01):
    """(K, H, W) bool: mask[a] = pixels whose front-most render is another object, dilated by dil_px.
    With MEASURED (H, W) depth (mode 'depth'): only pixels where the measured depth agrees with that other object's
    render within TOL (m) and better than with object a's own render (where a is rendered) are hidden, then dilated.
    This keeps object a's own visible surface when the other object's template or pose is wrong (fat or partial
    templates interpenetrating a)."""
    import cv2
    lab = front_labels(depth_maps)
    K = len(depth_maps)
    D = np.asarray(depth_maps, np.float32)
    out = np.zeros((K,) + lab.shape, bool)
    ker = np.ones((2 * dil_px + 1, 2 * dil_px + 1), np.uint8) if dil_px > 0 else None
    if measured is not None:
        z = np.asarray(measured, np.float32)
        ok = np.isfinite(z) & (z > 0)
    for a in range(K):
        m = (lab >= 0) & (lab != a)
        if measured is not None:
            Do = np.where(m, np.take_along_axis(D, np.clip(lab, 0, K - 1)[None], 0)[0], 0)
            eo = np.abs(z - Do)
            ea = np.where(D[a] > 0, np.abs(z - D[a]), np.inf)
            m = m & ok & (eo < tol) & (eo < ea)
        m = m.astype(np.uint8)
        if ker is not None:
            m = cv2.dilate(m, ker)
        out[a] = m.astype(bool)
    return out


def apply_mask(depth, gray, mask):
    """Copies of depth (H, W) and gray (H, W) or (H, W, 3) with mask hidden: depth 0, gray = the frame's median."""
    d = np.array(depth, copy=True)
    g = np.array(gray, copy=True)
    d[mask] = 0
    g[mask] = np.median(gray).astype(g.dtype)
    return d, g
