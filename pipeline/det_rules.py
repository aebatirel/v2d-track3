"""Frame-k detection rules shared by pipeline/perc2.py (inference) and tools/det_replay.py (offline replay), so the
replayed rule and the shipped rule are the same code (2026-10-23).

Chosen on the 20 public episodes only (tools/det_replay.py, grid and selection rule fixed before the replay; 116
reference instances at frames 0 and the quarter points): the pipeline's choice was right on 78; with these rules 93,
no instance lost (reach alone 90, + size 92, + grounding 93). docs/work-log.md 2026-10-23.
  reach   a proposal whose 3-D centroid is farther than REACH (1.0 m) from the head camera is barred: objects a person
          manipulates are within arm's reach (public frame 0: real objects 0.46-0.78 m away; the misses were blobs at
          1.0-1.4 m on people, chairs and the floor)
  size    score - LAM_S (0.05) * |log(extent / template extent)|, extent on the proposal's eroded mask
  ground  score + LAM_G (0.2) * G: Grounding DINO tiny on the colour camera a (frame k+1), prompted with the roster
          name (underscores as spaces, trailing digits dropped), top-5 boxes; G = max over the object's boxes of
          IoU(box, proposal projected into camera a) x score / best score of that prompt; off for an object when any of
          its gated proposals is < 80 % inside camera a
No ground truth is read here.
"""
from __future__ import annotations

import json
import re

import numpy as np

LAM_S, EXT_SRC, REACH, LAM_G = 0.05, 'eroded', 1.0, 0.2
GDINO = 'IDEA-Research/grounding-dino-tiny'
A_OFFSET = 1                                   # stereo frame k pairs with camera-a frame k + 1 (hands_mp.py)


def prompt(name: str) -> str:
    return re.sub(r'\s*\d+$', '', name.replace('_', ' ')).strip()


def size_penalty(pext, template_extent, lam_s=LAM_S, dz=1.0):
    return lam_s * np.maximum(0.0, np.abs(np.log(np.maximum(pext, 1e-3) / template_extent)) - np.log(dz))


def reach_ok(centroids, reach=REACH):
    if reach is None:
        return np.ones(len(centroids), bool)
    return np.nan_to_num(np.linalg.norm(centroids, axis=1), nan=9.0) <= reach


def make_cam(calib_path, R1):
    """Map rectified-left camera-c points (m) to camera-a pixels: rectified -> raw c (R1^T) -> camera a, distortion."""
    import cv2
    C = json.load(open(calib_path))['cameras']
    ext = lambda n: np.array(C[n]['extrinsics_to_stereo_left'], float)  # noqa: E731
    T_a_c = np.linalg.inv(ext('ego_cam_a')) @ ext('ego_cam_c')
    Ka, Da = np.array(C['ego_cam_a']['intrinsic_matrix'], float), np.array(C['ego_cam_a']['distortion_coefficients'], float)
    W, H = 2028, 1520

    def cam(X):
        Xa = (X @ R1) @ T_a_c[:3, :3].T + T_a_c[:3, 3]; ok = Xa[:, 2] > 0.05
        uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da); uv = uv.reshape(-1, 2)
        ok &= (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
        return uv, ok
    return cam


def ground_scores(masks, depth, K, names, gdet, cam):
    """G (n_obj, n_props) and each proposal's share of points inside camera a. masks / depth / K at one resolution."""
    P = len(masks); G = np.zeros((len(names), P)); inside = np.zeros(P); bb = np.zeros((P, 4))
    fx, cx, cy = K[0, 0], K[0, 2], K[1, 2]
    for j, m in enumerate(masks):
        v, u = np.nonzero(m & (depth > 0))
        if len(v) < 20:
            continue
        sel = np.linspace(0, len(v) - 1, min(len(v), 400)).astype(int); v, u = v[sel], u[sel]; z = depth[v, u]
        uv, ok = cam(np.stack([(u - cx) * z / fx, (v - cy) * z / fx, z], 1)); inside[j] = ok.mean()
        if ok.sum() >= 10:
            bb[j] = [*uv[ok].min(0), *uv[ok].max(0)]
    for a, n in enumerate(names):
        g = gdet.get(n)
        if not g or not g['scores']:
            continue
        best = max(g['scores'])
        for box, sc in zip(g['boxes'], g['scores']):
            ix = np.clip(np.minimum(bb[:, 2], box[2]) - np.maximum(bb[:, 0], box[0]), 0, None)
            iy = np.clip(np.minimum(bb[:, 3], box[3]) - np.maximum(bb[:, 1], box[1]), 0, None)
            inter = ix * iy; uni = (bb[:, 2] - bb[:, 0]) * (bb[:, 3] - bb[:, 1]) + (box[2] - box[0]) * (box[3] - box[1]) - inter
            G[a] = np.maximum(G[a], np.where(uni > 0, inter / np.maximum(uni, 1e-9), 0) * sc / best)
    return G, inside


def ground_term(G, inside, gated_ok, lam_g=LAM_G):
    """lam_g * G per object, zero for an object with a gated proposal < 80 % inside camera a."""
    out = np.zeros_like(G)
    for a in range(len(G)):
        if lam_g > 0 and (inside[gated_ok[a]] >= 0.8).all():
            out[a] = lam_g * G[a]
    return out


class GroundingDino:
    """Grounding DINO tiny, one call per prompt, top-5 boxes (same post-processing as the 2026-10-22 CPU study)."""

    def __init__(self, device='cuda'):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        self.torch, self.device = torch, device
        self.proc = AutoProcessor.from_pretrained(GDINO)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(GDINO).to(device).eval()

    def __call__(self, image_rgb, names):
        from PIL import Image
        torch = self.torch; img = Image.fromarray(image_rgb); W, H = img.size; out = {}
        with torch.inference_mode():
            for n in names:
                txt = prompt(n).lower() + '.'
                inp = self.proc(images=img, text=txt, return_tensors='pt').to(self.device)
                o = self.model(**inp)
                ids = inp['input_ids'][0].tolist(); tok = self.proc.tokenizer
                special = set(tok.all_special_ids) | set(tok.convert_tokens_to_ids(['.']))
                keep = torch.tensor([i not in special for i in ids], device=self.device)
                sc = torch.sigmoid(o.logits[0])[:, :len(ids)][:, keep].max(-1).values.float().cpu().numpy()
                b = o.pred_boxes[0].float().cpu().numpy() * np.array([W, H, W, H])
                xyxy = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1)
                top = np.argsort(-sc)[:5]
                out[n] = {'boxes': [[float(v) for v in xyxy[i]] for i in top], 'scores': [float(sc[i]) for i in top]}
        return out
