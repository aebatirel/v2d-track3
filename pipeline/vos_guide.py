"""Mask-guided tracking for perc2 (2026-11-02, tracking-perception session; [H], off by default).

Ground-truth-free. Idea from the literature on FoundationPose drift under fast motion and hand occlusion
(FoundationPose++ / RRTrack: a 2-D video-segmentation track keeps localising the object; ObjectForesight: re-register
when the silhouette disagrees; EgoGrasp / YOTO: hand pixels pull the refiner). Here:
  1. SAM2 video propagation of each object's frame-0 detection mask through the rectified left video (all objects in
     one pass), stored at half resolution;
  2. VOS_DEPTH: FoundationPose's tracking depth is restricted to the dilated propagated mask (hand / background depth no
     longer enters the refiner's crop);
  3. VOS_PRIOR: before tracking frame i, the previous pose is rendered; if less than VOS_COV of the propagated mask lies
     inside its silhouette, the pose's translation is moved by the offset between the two visible-surface centres
     (back-projected mask centroid at the median observed depth vs the rendered silhouette's centroid at its median
     rendered depth), so the refiner's crop contains the object again;
  4. VOS_RECOVER: after tracking, if the coverage is still below VOS_REC, the object is re-registered on the propagated
     mask (at most every VOS_EVERY frames) and the result is kept only if its coverage beats the tracked pose's by 0.2
     and it passes the track guard.
Inputs: the rectified frames, the frame-0 masks perc2 already chose, our depth, our templates. Nothing else.
"""
import os, shutil
import numpy as np, cv2, torch


def propagate(frames_gray, masks0, ckpt, cfg, tmpdir, log, step=2):
    """frames_gray: list of HxW uint8; masks0: list of HxW bool (frame 0, one per object).
    Returns a list (per object) of uint8 arrays [N, H/step, W/step] (1 = object)."""
    from sam2.build_sam import build_sam2_video_predictor
    os.makedirs(tmpdir, exist_ok=True)
    for i, g in enumerate(frames_gray):
        cv2.imwrite(f'{tmpdir}/{i:05d}.jpg', g, [cv2.IMWRITE_JPEG_QUALITY, 95])
    pred = build_sam2_video_predictor(cfg, ckpt, device='cuda')
    N = len(frames_gray); H, W = frames_gray[0].shape
    out = [np.zeros((N, H // step, W // step), np.uint8) for _ in masks0]
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
        st = pred.init_state(video_path=tmpdir, offload_video_to_cpu=True, offload_state_to_cpu=True)
        for a, m in enumerate(masks0):
            pred.add_new_mask(st, frame_idx=0, obj_id=a, mask=m.astype(bool))
        for fi, ids, logits in pred.propagate_in_video(st):
            for k, a in enumerate(ids):
                m = (logits[k, 0] > 0).float().cpu().numpy().astype(np.uint8)
                out[a][fi] = cv2.resize(m, (W // step, H // step), interpolation=cv2.INTER_NEAREST)
    del pred; torch.cuda.empty_cache(); shutil.rmtree(tmpdir, ignore_errors=True)
    log('vos: propagated', len(masks0), 'objects over', N, 'frames; mean area (px, half res)',
        [int(o.reshape(N, -1).sum(1).mean()) for o in out])
    return out


class Guide:
    def __init__(self, K, H, W, glctx, mesh, step=2):
        from Utils import nvdiffrast_render, make_mesh_tensors
        self.render_fn = nvdiffrast_render
        self.K, self.H, self.W, self.glctx, self.step = K, H, W, glctx, step
        self.mt = make_mesh_tensors(mesh)

    def render_depth(self, X):
        """Rendered depth of the template at pose X (camera frame, 4x4), half resolution."""
        P = torch.as_tensor(X[None], dtype=torch.float32, device='cuda')
        _, d, _ = self.render_fn(K=self.K, H=self.H, W=self.W, ob_in_cams=P, glctx=self.glctx, mesh_tensors=self.mt,
                                 get_normal=False)
        d = d[0].float().cpu().numpy()
        return d[::self.step, ::self.step]

    def coverage(self, X, m):
        """Share of the propagated (visible) mask m inside the rendered silhouette of X. Occlusion-robust: a hand
        hiding part of the object shrinks m, not the share."""
        s = self.render_depth(X) > 0
        return float((m & s).sum() / max(1, m.sum())), s

    def shift(self, X, m, dep):
        """Camera-frame translation moving X's visible-surface centre onto the mask's (None if undefined)."""
        rd = self.render_depth(X); s = rd > 0
        dh = dep[::self.step, ::self.step]
        mv = m & (dh > 0)
        if s.sum() < 20 or mv.sum() < 20:
            return None
        fx, cx, cy = self.K[0, 0] / self.step, self.K[0, 2] / self.step, self.K[1, 2] / self.step
        def c3(mask, z):
            v, u = np.nonzero(mask); zz = float(np.median(z[mask]))
            return np.array([(u.mean() - cx) * zz / fx, (v.mean() - cy) * zz / fx, zz])
        return c3(mv, dh) - c3(s, rd)


def dilate(m, px):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    return cv2.dilate(m.astype(np.uint8), k) > 0
